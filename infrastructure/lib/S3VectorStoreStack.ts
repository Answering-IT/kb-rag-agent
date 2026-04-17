/**
 * S3VectorStoreStack - S3-based vector index management
 *
 * Creates:
 * - S3 prefix structure for vectors
 * - Lambda indexer (updates manifest and shards)
 * - EventBridge rules for triggering indexer
 * - S3 Inventory configuration
 */

import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';
import * as path from 'path';

export interface S3VectorStoreStackProps extends cdk.StackProps {
  stage: string;
  vectorsBucket: s3.IBucket;
  kmsKey: kms.IKey;
}

export class S3VectorStoreStack extends cdk.Stack {
  public readonly indexerFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: S3VectorStoreStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-vector-store');

    // ========================================
    // S3 PREFIX STRUCTURE
    // ========================================

    // S3 prefix structure is defined by convention:
    // - index/manifest.json - Central index
    // - index/shards/0001.json, 0002.json, ... - Shards (10K vectors each)
    // - embeddings/{chunk-uuid}.json - Individual vector files
    // - metadata/sync-status.json - Ingestion tracking
    // Structure will be created by the indexer Lambda on first run

    // ========================================
    // LAMBDA INDEXER
    // ========================================

    // IAM role for indexer Lambda
    const indexerRole = new iam.Role(this, 'IndexerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for S3 vector indexer Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
      ],
    });

    // Grant S3 access
    props.vectorsBucket.grantReadWrite(indexerRole);

    // Grant KMS access
    props.kmsKey.grantEncryptDecrypt(indexerRole);

    // Create Lambda function for indexing
    this.indexerFunction = new lambda.Function(this, 'IndexerFunction', {
      functionName: `processapp-vector-indexer-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/vector-indexer')
      ),
      role: indexerRole,
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        VECTORS_BUCKET: props.vectorsBucket.bucketName,
        STAGE: props.stage,
        SHARD_SIZE: '10000', // 10K vectors per shard
      },
      description: 'Updates vector index manifest and shards',
    });

    // ========================================
    // EVENTBRIDGE RULES
    // ========================================

    // Rule: Trigger indexer when new vectors are uploaded
    const vectorUploadRule = new events.Rule(this, 'VectorUploadRule', {
      ruleName: `processapp-vector-upload-${props.stage}`,
      description: 'Trigger indexer when vectors are uploaded',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [props.vectorsBucket.bucketName],
          },
          object: {
            key: [{ prefix: 'embeddings/' }],
          },
        },
      },
    });

    vectorUploadRule.addTarget(
      new targets.LambdaFunction(this.indexerFunction, {
        retryAttempts: 2,
      })
    );

    // ========================================
    // S3 INVENTORY (Optional)
    // ========================================

    // S3 Inventory provides scheduled reports on bucket contents
    // Useful for monitoring vector count and storage costs

    // Create inventory destination bucket (or use existing)
    const inventoryBucket = new s3.Bucket(this, 'InventoryBucket', {
      bucketName: `${props.vectorsBucket.bucketName}-inventory`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      lifecycleRules: [
        {
          id: 'delete-old-inventory',
          enabled: true,
          expiration: cdk.Duration.days(30),
        },
      ],
      removalPolicy:
        props.stage === 'prod'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    // Grant S3 inventory access
    inventoryBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'AllowS3InventoryWrite',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('s3.amazonaws.com')],
        actions: ['s3:PutObject'],
        resources: [`${inventoryBucket.bucketArn}/*`],
        conditions: {
          StringEquals: {
            's3:x-amz-acl': 'bucket-owner-full-control',
            'aws:SourceAccount': this.account,
          },
          ArnLike: {
            'aws:SourceArn': props.vectorsBucket.bucketArn,
          },
        },
      })
    );

    // Add inventory configuration to vectors bucket
    const cfnBucket = props.vectorsBucket.node.defaultChild as s3.CfnBucket;
    cfnBucket.inventoryConfigurations = [
      {
        id: 'weekly-inventory',
        enabled: true,
        destination: {
          bucketArn: inventoryBucket.bucketArn,
          format: 'CSV',
          prefix: 'inventory',
        },
        includedObjectVersions: 'Current',
        scheduleFrequency: 'Weekly',
        optionalFields: ['Size', 'LastModifiedDate', 'StorageClass', 'ETag'],
      },
    ];

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'IndexerFunctionArn', {
      value: this.indexerFunction.functionArn,
      description: 'Vector indexer Lambda function ARN',
      exportName: `processapp-indexer-function-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'IndexerFunctionName', {
      value: this.indexerFunction.functionName,
      description: 'Vector indexer Lambda function name',
      exportName: `processapp-indexer-function-name-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'InventoryBucketName', {
      value: inventoryBucket.bucketName,
      description: 'S3 Inventory bucket name',
      exportName: `processapp-inventory-bucket-${props.stage}-${region}`,
    });
  }
}
