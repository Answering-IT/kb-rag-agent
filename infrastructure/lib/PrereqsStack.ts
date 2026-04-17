/**
 * PrereqsStack - Global resources created once in us-east-1
 *
 * Creates:
 * - S3 docs bucket (source documents)
 * - S3 vectors bucket (embeddings storage)
 * - IAM roles (Bedrock KB, Lambda, Textract)
 * - CloudWatch log groups
 */

import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';
import {
  getBucketName,
  getCostAllocationTags,
  S3Config,
  MonitoringConfig,
  SecurityConfig,
} from '../config/environments';

export interface PrereqsStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
}

export class PrereqsStack extends cdk.Stack {
  public readonly docsBucket: s3.Bucket;
  public readonly vectorsBucket: s3.Bucket;
  public readonly bedrockKBRole: iam.Role;
  public readonly lambdaExecutionRole: iam.Role;
  public readonly textractRole: iam.Role;
  public readonly kmsKey: kms.Key;

  constructor(scope: Construct, id: string, props: PrereqsStackProps) {
    super(scope, id, props);

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-prereqs');

    // ========================================
    // KMS KEY
    // ========================================

    this.kmsKey = new kms.Key(this, 'DataEncryptionKey', {
      alias: `alias/processapp-bedrock-data-${props.stage}`,
      description: 'Encryption key for ProcessApp RAG data',
      enableKeyRotation: SecurityConfig.kmsKeyRotation,
      removalPolicy:
        props.stage === 'prod'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      pendingWindow:
        props.stage === 'prod'
          ? cdk.Duration.days(30)
          : cdk.Duration.days(7),
    });

    // ========================================
    // S3 BUCKETS
    // ========================================

    // Documents bucket - stores source documents
    this.docsBucket = new s3.Bucket(this, 'DocumentsBucket', {
      bucketName: getBucketName(S3Config.docsBucket.prefix, props.stage, props.accountId),

      // Versioning for document history
      versioned: S3Config.docsBucket.versioningEnabled,

      // Server-side encryption with KMS
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,

      // Block all public access
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,

      // Lifecycle rules
      lifecycleRules: [
        {
          id: 'archive-old-documents',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(
                S3Config.docsBucket.lifecycleRules.archiveAfterDays
              ),
            },
          ],
          expiration: cdk.Duration.days(
            S3Config.docsBucket.lifecycleRules.deleteAfterDays
          ),
        },
        {
          id: 'cleanup-incomplete-uploads',
          enabled: true,
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
      ],

      // Enable event notifications for Lambda triggers
      eventBridgeEnabled: true,

      // Removal policy (retain in prod)
      removalPolicy:
        props.stage === 'prod'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    // Vectors bucket - stores embeddings
    this.vectorsBucket = new s3.Bucket(this, 'VectorsBucket', {
      bucketName: getBucketName(S3Config.vectorsBucket.prefix, props.stage, props.accountId),

      // Versioning for vector history
      versioned: false, // Vectors are regenerated, no need for versions

      // Server-side encryption with KMS
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,

      // Block all public access
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,

      // Intelligent Tiering for cost optimization
      intelligentTieringConfigurations: S3Config.vectorsBucket.intelligentTiering
        ? [
            {
              name: 'vectors-intelligent-tiering',
              archiveAccessTierTime: cdk.Duration.days(90),
              deepArchiveAccessTierTime: cdk.Duration.days(180),
            },
          ]
        : undefined,

      // Lifecycle rules
      lifecycleRules: [
        {
          id: 'archive-old-vectors',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(
                S3Config.vectorsBucket.lifecycleRules.archiveAfterDays
              ),
            },
          ],
          expiration: cdk.Duration.days(
            S3Config.vectorsBucket.lifecycleRules.deleteAfterDays
          ),
        },
      ],

      // Enable event notifications
      eventBridgeEnabled: true,

      // Removal policy
      removalPolicy:
        props.stage === 'prod'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    // ========================================
    // IAM ROLES
    // ========================================

    // Bedrock Knowledge Base execution role
    this.bedrockKBRole = new iam.Role(this, 'BedrockKBRole', {
      roleName: `processapp-bedrock-kb-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'Execution role for Bedrock Knowledge Base',
      maxSessionDuration: cdk.Duration.hours(1),
    });

    // Note: Policies will be added in SecurityStack after KMS key is created

    // Lambda execution role (basic, policies added later)
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `processapp-lambda-execution-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Lambda functions',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'AWSXRayDaemonWriteAccess'
        ),
      ],
    });

    // Textract execution role
    this.textractRole = new iam.Role(this, 'TextractRole', {
      roleName: `processapp-textract-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('textract.amazonaws.com'),
      description: 'Execution role for Textract service',
    });

    // Grant Textract role S3 read access
    this.docsBucket.grantRead(this.textractRole);

    // ========================================
    // CLOUDWATCH LOG GROUPS
    // ========================================

    // Knowledge Base log group
    const kbLogGroup = new logs.LogGroup(this, 'KBLogGroup', {
      logGroupName: `/aws/bedrock/knowledgebases/${props.stage}`,
      retention:
        props.stage === 'prod'
          ? logs.RetentionDays.SIX_MONTHS
          : logs.RetentionDays.ONE_MONTH,
      removalPolicy:
        props.stage === 'prod'
          ? cdk.RemovalPolicy.RETAIN
          : cdk.RemovalPolicy.DESTROY,
    });

    // Lambda log group (pattern-based, actual groups created by Lambda)
    const lambdaLogGroupPrefix = new logs.LogGroup(this, 'LambdaLogGroup', {
      logGroupName: `/aws/lambda/processapp-${props.stage}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ========================================
    // OUTPUTS (for cross-stack references)
    // ========================================

    new cdk.CfnOutput(this, 'DocsBucketName', {
      value: this.docsBucket.bucketName,
      description: 'Documents S3 bucket name',
      exportName: `processapp-docs-bucket-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'DocsBucketArn', {
      value: this.docsBucket.bucketArn,
      description: 'Documents S3 bucket ARN',
      exportName: `processapp-docs-bucket-arn-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'VectorsBucketName', {
      value: this.vectorsBucket.bucketName,
      description: 'Vectors S3 bucket name',
      exportName: `processapp-vectors-bucket-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'VectorsBucketArn', {
      value: this.vectorsBucket.bucketArn,
      description: 'Vectors S3 bucket ARN',
      exportName: `processapp-vectors-bucket-arn-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'BedrockKBRoleArn', {
      value: this.bedrockKBRole.roleArn,
      description: 'Bedrock Knowledge Base role ARN',
      exportName: `processapp-bedrock-kb-role-arn-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: this.lambdaExecutionRole.roleArn,
      description: 'Lambda execution role ARN',
      exportName: `processapp-lambda-role-arn-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'TextractRoleArn', {
      value: this.textractRole.roleArn,
      description: 'Textract role ARN',
      exportName: `processapp-textract-role-arn-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'KBLogGroupName', {
      value: kbLogGroup.logGroupName,
      description: 'Knowledge Base log group name',
      exportName: `processapp-kb-loggroup-${props.stage}`,
    });
  }
}
