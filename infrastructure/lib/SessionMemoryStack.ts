/**
 * SessionMemoryStack - DynamoDB for conversation history
 *
 * Creates:
 * - DynamoDB table for storing conversation sessions
 * - TTL for automatic cleanup after 90 days
 * - GSI for querying by userId
 */

import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface SessionMemoryStackProps extends cdk.StackProps {
  stage: string;
}

export class SessionMemoryStack extends cdk.Stack {
  public readonly conversationTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: SessionMemoryStackProps) {
    super(scope, id, props);

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'session-memory');

    // ========================================
    // DYNAMODB TABLE FOR CONVERSATION HISTORY
    // ========================================

    this.conversationTable = new dynamodb.Table(this, 'ConversationHistory', {
      tableName: `processapp-conversations-${props.stage}`,
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // On-demand pricing
      partitionKey: {
        name: 'sessionId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.NUMBER,
      },
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Change to RETAIN for production
      timeToLiveAttribute: 'expirationTime', // Auto-cleanup after 90 days
    });

    // ========================================
    // GLOBAL SECONDARY INDEX FOR USER QUERIES
    // ========================================

    this.conversationTable.addGlobalSecondaryIndex({
      indexName: 'UserIdIndex',
      partitionKey: {
        name: 'userId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.NUMBER,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'ConversationTableName', {
      value: this.conversationTable.tableName,
      description: 'DynamoDB table for conversation history',
      exportName: `processapp-conversation-table-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'ConversationTableArn', {
      value: this.conversationTable.tableArn,
      description: 'DynamoDB table ARN',
      exportName: `processapp-conversation-table-arn-${props.stage}`,
    });
  }
}
