/**
 * BedrockStack - Core RAG Orchestration with Knowledge Base
 *
 * Creates:
 * - S3 Vector Index (native vector storage in S3)
 * - Bedrock Knowledge Base (using CfnKnowledgeBase with S3 vectors)
 * - Data Source configuration (S3)
 * - Sync schedule (EventBridge)
 */

import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import { Construct } from 'constructs';
import { KnowledgeBaseConfig } from '../config/environments';

export interface BedrockStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  docsBucket: s3.IBucket;
  vectorsBucket: s3.IBucket;
  bedrockKBRole: iam.IRole;
  kmsKey: kms.IKey;
}

export class BedrockStack extends cdk.Stack {
  public readonly knowledgeBaseId: string;
  public readonly dataSourceId: string;
  public readonly knowledgeBase: bedrock.CfnKnowledgeBase;

  constructor(scope: Construct, id: string, props: BedrockStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-bedrock');

    const kbName = `${KnowledgeBaseConfig.name}-${props.stage}`;

    // ========================================
    // S3 VECTOR BUCKET AND INDEX
    // ========================================

    const vectorBucketName = `processapp-vectors-${props.stage}-${props.accountId}`;
    const vectorIndexName = `${kbName}-vector-index`;

    // Create S3 Vector Bucket using native CloudFormation
    const vectorBucket = new cdk.CfnResource(this, 'VectorBucket', {
      type: 'AWS::S3Vectors::VectorBucket',
      properties: {
        VectorBucketName: vectorBucketName,
        Tags: [
          { Key: 'Environment', Value: props.stage },
          { Key: 'Application', Value: 'processapp' },
          { Key: 'Component', Value: 'rag-vectors' },
        ],
      },
    });

    // Create S3 Vector Index using native CloudFormation
    const vectorIndex = new cdk.CfnResource(this, 'VectorIndex', {
      type: 'AWS::S3Vectors::Index',
      properties: {
        VectorBucketName: vectorBucketName,
        IndexName: vectorIndexName,
        DataType: 'float32',
        Dimension: 1024, // Titan v2 embeddings dimension
        DistanceMetric: 'cosine',
        Tags: [
          { Key: 'Environment', Value: props.stage },
          { Key: 'Application', Value: 'processapp' },
          { Key: 'Component', Value: 'rag-vectors' },
        ],
      },
    });

    // Ensure index is created after bucket
    vectorIndex.addDependency(vectorBucket);

    // Get the index ARN
    const vectorIndexArn = vectorIndex.getAtt('IndexArn').toString();

    // Note: s3vectors permissions are granted in SecurityStack

    // ========================================
    // BEDROCK KNOWLEDGE BASE
    // ========================================

    // Create Knowledge Base with S3 vector storage
    this.knowledgeBase = new bedrock.CfnKnowledgeBase(this, 'KnowledgeBase', {
      name: kbName,
      description: KnowledgeBaseConfig.description,
      roleArn: props.bedrockKBRole.roleArn,

      // Storage configuration - S3 Vectors (native S3 storage!)
      storageConfiguration: {
        type: 'S3_VECTORS',
        s3VectorsConfiguration: {
          indexArn: vectorIndexArn,
        },
      },

      // Knowledge Base configuration
      knowledgeBaseConfiguration: {
        type: 'VECTOR',
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`,
          embeddingModelConfiguration: {
            bedrockEmbeddingModelConfiguration: {
              dimensions: 1024,
            },
          },
        },
      },
    });

    // Ensure KB is created after vector resources
    this.knowledgeBase.addDependency(vectorIndex);

    this.knowledgeBaseId = this.knowledgeBase.attrKnowledgeBaseId;

    // ========================================
    // DATA SOURCE (S3)
    // ========================================

    const dataSource = new bedrock.CfnDataSource(this, 'DataSource', {
      name: `${kbName}-datasource`,
      description: 'S3 data source for document ingestion',
      knowledgeBaseId: this.knowledgeBaseId,

      // S3 data source configuration
      dataSourceConfiguration: {
        type: 'S3',
        s3Configuration: {
          bucketArn: props.docsBucket.bucketArn,
          inclusionPrefixes: ['documents/'],
        },
      },

      // Vector ingestion configuration
      vectorIngestionConfiguration: {
        chunkingConfiguration: {
          chunkingStrategy: 'FIXED_SIZE',
          fixedSizeChunkingConfiguration: {
            maxTokens: 512,
            overlapPercentage: 20,
          },
        },
      },
    });

    dataSource.addDependency(this.knowledgeBase);
    this.dataSourceId = dataSource.attrDataSourceId;

    // ========================================
    // SYNC SCHEDULE (EventBridge)
    // ========================================

    // Lambda function to trigger KB sync
    const syncFunction = new lambda.Function(this, 'SyncFunction', {
      functionName: `processapp-kb-sync-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import boto3
import os
import json

bedrock_agent = boto3.client('bedrock-agent')

def handler(event, context):
    kb_id = os.environ['KNOWLEDGE_BASE_ID']
    ds_id = os.environ['DATA_SOURCE_ID']

    print(f'Starting sync for KB: {kb_id}, DataSource: {ds_id}')

    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )

        print(f'Sync started: {json.dumps(response)}')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Sync started successfully',
                'ingestionJobId': response.get('ingestionJob', {}).get('ingestionJobId')
            })
        }
    except Exception as e:
        print(f'Error starting sync: {str(e)}')
        raise
      `),
      environment: {
        KNOWLEDGE_BASE_ID: this.knowledgeBaseId,
        DATA_SOURCE_ID: this.dataSourceId,
      },
      timeout: cdk.Duration.minutes(1),
      memorySize: 128,
    });

    // Grant permissions to sync function
    syncFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:StartIngestionJob',
          'bedrock:GetIngestionJob',
          'bedrock:ListIngestionJobs',
        ],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:knowledge-base/${this.knowledgeBaseId}`,
        ],
      })
    );

    // EventBridge rule for scheduled sync
    const syncRule = new events.Rule(this, 'SyncScheduleRule', {
      ruleName: `processapp-kb-sync-schedule-${props.stage}`,
      description: 'Trigger Knowledge Base sync every 6 hours',
      schedule: events.Schedule.expression(
        KnowledgeBaseConfig.syncSchedule
      ),
    });

    syncRule.addTarget(new targets.LambdaFunction(syncFunction));

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'VectorIndexArn', {
      value: vectorIndexArn,
      description: 'S3 Vector Index ARN',
      exportName: `processapp-vector-index-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: this.knowledgeBaseId,
      description: 'Bedrock Knowledge Base ID',
      exportName: `processapp-kb-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'DataSourceId', {
      value: this.dataSourceId,
      description: 'Bedrock Data Source ID',
      exportName: `processapp-datasource-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseArn', {
      value: this.knowledgeBase.attrKnowledgeBaseArn,
      description: 'Bedrock Knowledge Base ARN',
      exportName: `processapp-kb-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'SyncFunctionArn', {
      value: syncFunction.functionArn,
      description: 'KB sync function ARN',
      exportName: `processapp-kb-sync-function-${props.stage}-${region}`,
    });
  }
}
