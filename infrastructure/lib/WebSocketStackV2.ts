/**
 * WebSocketStackV2 - WebSocket API for Agent Core v2
 *
 * Simplified WebSocket handler - no DynamoDB session memory needed
 * Agent Core CfnMemory handles conversation history automatically
 */

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigatewayv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';
import * as path from 'path';

export interface WebSocketStackV2Props extends cdk.StackProps {
  stage: string;
  accountId: string;
  runtimeId: string;  // Agent Core Runtime ID
  knowledgeBaseId: string;
}

export class WebSocketStackV2 extends cdk.Stack {
  public readonly webSocketApi: apigatewayv2.WebSocketApi;
  public readonly webSocketUrl: string;
  public readonly messageHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: WebSocketStackV2Props) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-websocket');

    // ========================================
    // IAM ROLE FOR LAMBDA (v2)
    // ========================================

    const wsHandlerRole = new iam.Role(this, 'WebSocketHandlerRole', {
      roleName: `processapp-ws-handler-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for WebSocket message handler Lambda (Agent Core)',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'AWSXRayDaemonWriteAccess'
        ),
      ],
    });

    // Grant permissions to invoke Agent Core Runtime
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock-agentcore:InvokeAgentRuntime',
          'bedrock-agentcore:InvokeRuntime',
          'bedrock-agentcore:GetRuntime',
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${region}:${props.accountId}:runtime/${props.runtimeId}`,
          `arn:aws:bedrock-agentcore:${region}:${props.accountId}:runtime/${props.runtimeId}/*`,
          `arn:aws:bedrock-agentcore:${region}:${props.accountId}:runtime/${props.runtimeId}/runtime-endpoint/*`,
        ],
      })
    );

    // Grant permissions to manage WebSocket connections
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'execute-api:ManageConnections',
          'execute-api:Invoke',
        ],
        resources: [
          `arn:aws:execute-api:${region}:${props.accountId}:*/*`,
        ],
      })
    );

    // Grant permissions to use Knowledge Base (for direct retrieve if needed)
    wsHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:Retrieve',
          'bedrock:RetrieveAndGenerate',
        ],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:knowledge-base/${props.knowledgeBaseId}`,
        ],
      })
    );

    // ========================================
    // MESSAGE HANDLER LAMBDA (v2)
    // ========================================

    this.messageHandler = new lambda.Function(this, 'MessageHandler', {
      functionName: `processapp-ws-message-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'message_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname as any, '../lambdas/websocket-handler-v2')
      ),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      role: wsHandlerRole,
      environment: {
        RUNTIME_ID: props.runtimeId,
        KNOWLEDGE_BASE_ID: props.knowledgeBaseId,
        STAGE: props.stage,
        AWS_ACCOUNT_ID: props.accountId,
        // No CONVERSATION_TABLE needed - Agent Core Memory handles it
      },
      description: 'WebSocket message handler for Agent Core (no manual memory)',
      tracing: lambda.Tracing.ACTIVE,
    });

    // ========================================
    // CONNECT HANDLER LAMBDA (v2)
    // ========================================

    const connectHandler = new lambda.Function(this, 'ConnectHandler', {
      functionName: `processapp-ws-connect-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'connect_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname as any, '../lambdas/websocket-handler-v2')
      ),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
      environment: {
        STAGE: props.stage,
      },
      description: 'WebSocket connect handler',
    });

    // ========================================
    // DISCONNECT HANDLER LAMBDA (v2)
    // ========================================

    const disconnectHandler = new lambda.Function(this, 'DisconnectHandler', {
      functionName: `processapp-ws-disconnect-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'disconnect_handler.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname as any, '../lambdas/websocket-handler-v2')
      ),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
      environment: {
        STAGE: props.stage,
      },
      description: 'WebSocket disconnect handler',
    });

    // ========================================
    // WEBSOCKET API (v2)
    // ========================================

    this.webSocketApi = new apigatewayv2.WebSocketApi(this, 'AgentWebSocket', {
      apiName: `processapp-agent-ws-${props.stage}`,
      description: 'WebSocket API for Bedrock Agent Core streaming',
      connectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'ConnectIntegration',
          connectHandler
        ),
      },
      disconnectRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'DisconnectIntegration',
          disconnectHandler
        ),
      },
      defaultRouteOptions: {
        integration: new apigatewayv2_integrations.WebSocketLambdaIntegration(
          'MessageIntegration',
          this.messageHandler
        ),
      },
    });

    // ========================================
    // WEBSOCKET STAGE (v2)
    // ========================================

    const wsStage = new apigatewayv2.WebSocketStage(this, 'WebSocketStage', {
      webSocketApi: this.webSocketApi,
      stageName: props.stage,
      autoDeploy: true,
      throttle: {
        rateLimit: 1000,
        burstLimit: 2000,
      },
    });

    this.webSocketUrl = wsStage.url;

    // ========================================
    // CLOUDWATCH LOG GROUPS
    // ========================================
    // Lambda functions automatically create log groups
    // We don't need to create them explicitly

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'WebSocketURL', {
      value: this.webSocketUrl,
      description: 'WebSocket URL for Agent Core',
      exportName: `processapp-websocket-url-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'WebSocketApiId', {
      value: this.webSocketApi.apiId,
      description: 'WebSocket API ID',
      exportName: `processapp-websocket-api-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'WebSocketConnectionCommand', {
      value: `wscat -c ${this.webSocketUrl}`,
      description: 'Command to connect to WebSocket',
    });

    new cdk.CfnOutput(this, 'MessageHandlerArn', {
      value: this.messageHandler.functionArn,
      description: 'Message handler Lambda ARN',
      exportName: `processapp-ws-message-arn-${props.stage}-${region}`,
    });
  }
}
