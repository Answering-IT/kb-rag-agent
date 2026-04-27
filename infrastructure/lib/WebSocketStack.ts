/**
 * WebSocketStack - Real-time streaming API for Bedrock Agent responses
 *
 * Creates:
 * - WebSocket API Gateway
 * - Message handler Lambda (for $default route)
 * - Connect/Disconnect handlers
 * - Integration with Bedrock Agent streaming
 */

import * as cdk from 'aws-cdk-lib';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { WebSocketLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';
import * as path from 'path';

export interface WebSocketStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  agentId: string;
  agentAliasId: string;
  knowledgeBaseId: string;
  conversationTableName?: string;
}

export class WebSocketStack extends cdk.Stack {
  public readonly webSocketApi: apigatewayv2.WebSocketApi;
  public readonly webSocketUrl: string;
  public readonly messageHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: WebSocketStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-websocket');

    // ========================================
    // IAM ROLE FOR LAMBDA
    // ========================================

    const wsHandlerRole = new iam.Role(this, 'WebSocketHandlerRole', {
      roleName: `processapp-ws-handler-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for WebSocket message handler Lambda',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'AWSXRayDaemonWriteAccess'
        ),
      ],
    });

    // Grant permissions to invoke Bedrock Agent
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:InvokeAgent',
          'bedrock:Retrieve',
          'bedrock:RetrieveAndGenerate',
        ],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:agent/${props.agentId}`,
          `arn:aws:bedrock:${region}:${props.accountId}:agent-alias/${props.agentId}/${props.agentAliasId}`,
          `arn:aws:bedrock:${region}:${props.accountId}:knowledge-base/${props.knowledgeBaseId}`,
        ],
      })
    );

    // Grant permissions to invoke foundation model (required by retrieve_and_generate)
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${region}::foundation-model/amazon.nova-pro-v1:0`,
        ],
      })
    );

    // Grant permissions to post to WebSocket connections
    // Note: Cannot specify specific API ARN here, will grant * and rely on IAM best practices
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['execute-api:ManageConnections'],
        resources: [
          `arn:aws:execute-api:${region}:${props.accountId}:*/@connections/*`,
        ],
      })
    );

    // Grant DynamoDB permissions if conversation table is provided
    if (props.conversationTableName) {
      wsHandlerRole.addToPolicy(
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            'dynamodb:GetItem',
            'dynamodb:PutItem',
            'dynamodb:Query',
            'dynamodb:UpdateItem',
          ],
          resources: [
            `arn:aws:dynamodb:${region}:${props.accountId}:table/${props.conversationTableName}`,
            `arn:aws:dynamodb:${region}:${props.accountId}:table/${props.conversationTableName}/index/*`,
          ],
        })
      );
    }

    // ========================================
    // LAMBDA FUNCTIONS
    // ========================================

    // Message handler (for $default route)
    this.messageHandler = new lambda.Function(this, 'MessageHandler', {
      functionName: `processapp-ws-message-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'message_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/websocket-handler')
      ),
      role: wsHandlerRole,
      timeout: cdk.Duration.seconds(300), // 5 minutes for streaming
      memorySize: 512,
      environment: {
        AGENT_ID: props.agentId,
        AGENT_ALIAS_ID: props.agentAliasId,
        KNOWLEDGE_BASE_ID: props.knowledgeBaseId,
        CONVERSATION_TABLE: props.conversationTableName || '',
        STAGE: props.stage,
        FOUNDATION_MODEL: 'amazon.nova-pro-v1:0',
        ENABLE_METADATA_FILTERING: 'true',
      },
      description: 'WebSocket message handler with Bedrock Agent streaming',
      tracing: lambda.Tracing.ACTIVE,
    });

    // Connect handler (optional - for connection management)
    const connectHandler = new lambda.Function(this, 'ConnectHandler', {
      functionName: `processapp-ws-connect-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'connect_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/websocket-handler')
      ),
      timeout: cdk.Duration.seconds(10),
      memorySize: 256,
      environment: {
        STAGE: props.stage,
      },
      description: 'WebSocket connect handler',
    });

    // Disconnect handler (optional - for cleanup)
    const disconnectHandler = new lambda.Function(this, 'DisconnectHandler', {
      functionName: `processapp-ws-disconnect-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'disconnect_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/websocket-handler')
      ),
      timeout: cdk.Duration.seconds(10),
      memorySize: 256,
      environment: {
        STAGE: props.stage,
      },
      description: 'WebSocket disconnect handler',
    });

    // ========================================
    // WEBSOCKET API
    // ========================================

    this.webSocketApi = new apigatewayv2.WebSocketApi(this, 'WebSocketApi', {
      apiName: `processapp-agent-ws-${props.stage}`,
      description: 'WebSocket API for real-time Bedrock Agent streaming',
      connectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          'ConnectIntegration',
          connectHandler
        ),
      },
      disconnectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          'DisconnectIntegration',
          disconnectHandler
        ),
      },
      defaultRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          'DefaultIntegration',
          this.messageHandler
        ),
      },
    });

    // Create WebSocket stage
    const wsStage = new apigatewayv2.WebSocketStage(this, 'WebSocketStage', {
      webSocketApi: this.webSocketApi,
      stageName: props.stage,
      autoDeploy: true,
      throttle: {
        rateLimit: 100, // requests per second
        burstLimit: 200,
      },
    });

    // Enable CloudWatch logging
    const logGroup = new logs.LogGroup(this, 'WebSocketApiLogs', {
      logGroupName: `/aws/apigateway/processapp-ws-${props.stage}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Store WebSocket URL
    this.webSocketUrl = wsStage.url;

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'WebSocketURL', {
      value: this.webSocketUrl,
      description: 'WebSocket API URL for streaming',
      exportName: `processapp-ws-url-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'WebSocketApiId', {
      value: this.webSocketApi.apiId,
      description: 'WebSocket API ID',
      exportName: `processapp-ws-api-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'MessageHandlerArn', {
      value: this.messageHandler.functionArn,
      description: 'WebSocket message handler Lambda ARN',
      exportName: `processapp-ws-message-handler-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'WebSocketConnectionCommand', {
      value: `wscat -c ${this.webSocketUrl}`,
      description: 'Command to connect to WebSocket (requires wscat)',
    });
  }
}
