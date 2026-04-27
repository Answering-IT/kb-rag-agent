/**
 * DocumentProcessingStack - Document ingestion pipeline
 *
 * Creates:
 * - OCR Lambda (Textract integration)
 * - Embedder Lambda (Titan v2)
 * - SQS queue for chunks
 * - SNS topic for Textract notifications
 * - EventBridge rules for triggers
 */

import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';
import * as path from 'path';
import {
  getLambdaOCRProcessorPolicy,
  getLambdaEmbedderPolicy,
  getTextractSNSPolicy,
} from '../config/security.config';
import { ProcessingConfig } from '../config/environments';

export interface DocumentProcessingStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  docsBucket: s3.IBucket;
  vectorsBucket?: s3.IBucket; // REMOVED (Phase 2) - only used by Embedder (will be removed in Phase 3)
  kmsKey: kms.IKey;
}

export class DocumentProcessingStack extends cdk.Stack {
  public readonly ocrProcessor: lambda.Function;
  // public readonly embedder: lambda.Function; // REMOVED (Phase 2) - not used
  // public readonly chunksQueue: sqs.Queue; // REMOVED (Phase 2) - not used

  constructor(scope: Construct, id: string, props: DocumentProcessingStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-document-processing');

    // ========================================
    // SQS QUEUE FOR TEXT CHUNKS - COMMENTED OUT (Phase 2)
    // ========================================
    // This queue is not used - no messages are sent to it.
    // Will be fully removed in Phase 3 when we deploy stack changes.
    /*
    // Dead Letter Queue
    const dlq = new sqs.Queue(this, 'ChunksDLQ', {
      queueName: `processapp-chunks-dlq-${props.stage}`,
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: props.kmsKey,
      retentionPeriod: cdk.Duration.days(14),
    });

    // Main chunks queue
    this.chunksQueue = new sqs.Queue(this, 'ChunksQueue', {
      queueName: `processapp-chunks-${props.stage}`,
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: props.kmsKey,
      visibilityTimeout: cdk.Duration.seconds(
        ProcessingConfig.sqs.visibilityTimeoutSeconds
      ),
      retentionPeriod: cdk.Duration.seconds(
        ProcessingConfig.sqs.retentionPeriodSeconds
      ),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: ProcessingConfig.sqs.maxReceiveCount,
      },
    });
    */

    // ========================================
    // SNS TOPIC FOR TEXTRACT NOTIFICATIONS
    // ========================================

    const textractTopic = new sns.Topic(this, 'TextractTopic', {
      topicName: `processapp-textract-${props.stage}`,
      displayName: 'Textract completion notifications',
      masterKey: props.kmsKey,
    });

    // Add SNS topic policy for Textract
    const textractSNSPolicy = getTextractSNSPolicy(props.accountId);
    textractSNSPolicy.forEach((statement) => {
      textractTopic.addToResourcePolicy(statement);
    });

    // ========================================
    // TEXTRACT IAM ROLE
    // ========================================

    // IAM role for Textract to publish job completion notifications to SNS
    const textractRole = new iam.Role(this, 'TextractRole', {
      assumedBy: new iam.ServicePrincipal('textract.amazonaws.com'),
      description: 'Role for Textract to publish job completion notifications to SNS',
    });

    // Grant Textract role permission to publish to SNS topic
    textractTopic.grantPublish(textractRole);

    // ========================================
    // OCR PROCESSOR LAMBDA
    // ========================================

    // IAM role
    const ocrRole = new iam.Role(this, 'OCRProcessorRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for OCR processor Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'AWSXRayDaemonWriteAccess'
        ),
      ],
      inlinePolicies: {
        OCRProcessorPolicy: getLambdaOCRProcessorPolicy(
          props.docsBucket.bucketArn,
          undefined, // chunksQueue removed (Phase 2) - OCR doesn't send messages to SQS
          props.kmsKey.keyArn,
          region
        ),
      },
    });

    // Grant SNS publish
    textractTopic.grantPublish(ocrRole);

    // Create Lambda function
    this.ocrProcessor = new lambda.Function(this, 'OCRProcessor', {
      functionName: `processapp-ocr-processor-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/ocr-processor')
      ),
      role: ocrRole,
      timeout: cdk.Duration.seconds(
        ProcessingConfig.lambda.ocrProcessor.timeoutSeconds
      ),
      memorySize: ProcessingConfig.lambda.ocrProcessor.memoryMB,
      environment: {
        DOCS_BUCKET: props.docsBucket.bucketName,
        // CHUNKS_QUEUE_URL: this.chunksQueue.queueUrl, // REMOVED (Phase 2) - not used
        TEXTRACT_SNS_TOPIC_ARN: textractTopic.topicArn,
        TEXTRACT_ROLE_ARN: textractRole.roleArn,
        KMS_KEY_ID: props.kmsKey.keyId,
        STAGE: props.stage,
      },
      description: 'Process documents with Textract and queue chunks',
      tracing: lambda.Tracing.ACTIVE,
    });

    // Subscribe OCR processor to Textract SNS topic
    textractTopic.addSubscription(
      new subscriptions.LambdaSubscription(this.ocrProcessor)
    );

    // ========================================
    // EVENTBRIDGE RULE: TRIGGER ON S3 UPLOAD
    // ========================================

    const documentUploadRule = new events.Rule(this, 'DocumentUploadRule', {
      ruleName: `processapp-document-upload-${props.stage}`,
      description: 'Trigger OCR when documents are uploaded',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [props.docsBucket.bucketName],
          },
          object: {
            key: [{ prefix: 'documents/' }],
          },
        },
      },
    });

    documentUploadRule.addTarget(
      new targets.LambdaFunction(this.ocrProcessor, {
        retryAttempts: 2,
      })
    );

    // ========================================
    // EMBEDDER LAMBDA - COMMENTED OUT (Phase 2)
    // ========================================
    // This Lambda is not used - Bedrock KB handles embeddings internally.
    // Will be fully removed in Phase 3 when we deploy stack changes.
    // For now, we keep it commented to prevent compilation errors.
    /*
    // IAM role
    const embedderRole = new iam.Role(this, 'EmbedderRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for embedder Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'AWSXRayDaemonWriteAccess'
        ),
      ],
      inlinePolicies: {
        EmbedderPolicy: getLambdaEmbedderPolicy(
          props.vectorsBucket.bucketArn,
          this.chunksQueue.queueArn,
          props.kmsKey.keyArn,
          region
        ),
      },
    });

    // Create Lambda function
    this.embedder = new lambda.Function(this, 'Embedder', {
      functionName: `processapp-embedder-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/embedder')
      ),
      role: embedderRole,
      timeout: cdk.Duration.seconds(
        ProcessingConfig.lambda.embedder.timeoutSeconds
      ),
      memorySize: ProcessingConfig.lambda.embedder.memoryMB,
      environment: {
        VECTORS_BUCKET: props.vectorsBucket.bucketName,
        EMBEDDING_MODEL: 'amazon.titan-embed-text-v2:0',
        STAGE: props.stage,
      },
      description: 'Generate embeddings using Titan v2 and store in S3',
      tracing: lambda.Tracing.ACTIVE,
      reservedConcurrentExecutions: 10, // Limit concurrent executions
    });

    // Add SQS trigger to embedder
    this.embedder.addEventSource(
      new lambdaEventSources.SqsEventSource(this.chunksQueue, {
        batchSize: 10, // Process up to 10 messages at once
        maxBatchingWindow: cdk.Duration.seconds(5),
        reportBatchItemFailures: true,
      })
    );
    */

    // ========================================
    // EVENTBRIDGE RULE: TRIGGER KB SYNC - COMMENTED OUT (Phase 2)
    // ========================================
    // This rule was never connected to a target and is not used.
    // Will be fully removed in Phase 3 when we deploy stack changes.
    /*
    // After embeddings are created, trigger KB sync
    const embeddingsCreatedRule = new events.Rule(
      this,
      'EmbeddingsCreatedRule',
      {
        ruleName: `processapp-embeddings-created-${props.stage}`,
        description: 'Notify when embeddings are created',
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
      }
    );

    // This will be connected to KB sync function in BedrockStack
    // For now, just create the rule - target will be added later
    */

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'OCRProcessorArn', {
      value: this.ocrProcessor.functionArn,
      description: 'OCR processor Lambda ARN',
      exportName: `processapp-ocr-processor-arn-${props.stage}-${region}`,
    });

    // Embedder and ChunksQueue outputs - REMOVED (Phase 2)
    /*
    new cdk.CfnOutput(this, 'EmbedderArn', {
      value: this.embedder.functionArn,
      description: 'Embedder Lambda ARN',
      exportName: `processapp-embedder-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'ChunksQueueUrl', {
      value: this.chunksQueue.queueUrl,
      description: 'Chunks SQS queue URL',
      exportName: `processapp-chunks-queue-url-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'ChunksQueueArn', {
      value: this.chunksQueue.queueArn,
      description: 'Chunks SQS queue ARN',
      exportName: `processapp-chunks-queue-arn-${props.stage}-${region}`,
    });
    */

    new cdk.CfnOutput(this, 'TextractTopicArn', {
      value: textractTopic.topicArn,
      description: 'Textract SNS topic ARN',
      exportName: `processapp-textract-topic-arn-${props.stage}-${region}`,
    });
  }
}
