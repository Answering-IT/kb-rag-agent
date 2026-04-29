/**
 * BedrockStreamApiStack - Lambda Function URL with Response Streaming
 *
 * Uses Lambda Function URLs with RESPONSE_STREAM invoke mode
 * for real-time streaming from Agent Core Runtime V2
 */

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from 'path';
import { Construct } from 'constructs';

export interface BedrockStreamApiStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  runtimeId: string;
  memoryId: string;
  knowledgeBaseId: string;
}

export class BedrockStreamApiStack extends cdk.Stack {
  public readonly functionUrl: string;
  public readonly streamingHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: BedrockStreamApiStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'bedrock-stream-api');

    // ========================================
    // IAM ROLE FOR LAMBDA
    // ========================================

    const streamingHandlerRole = new iam.Role(this, 'StreamingHandlerRole', {
      roleName: `processapp-streaming-handler-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for Bedrock Streaming API Lambda handler',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
      ],
    });

    // Grant permissions to invoke Agent Core Runtime
    streamingHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock-agentcore:InvokeAgentRuntime',
          'bedrock-agentcore:InvokeRuntime',
          'bedrock-agentcore:GetRuntime',
          'bedrock-agent-runtime:InvokeAgent',
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['*'],
      })
    );

    // ========================================
    // LAMBDA FUNCTION (Python)
    // ========================================

    this.streamingHandler = new lambda.Function(this, 'StreamingHandler', {
      functionName: `processapp-streaming-chat-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset(path.join(__dirname as any, '../lambdas/streaming-handler')),
      handler: 'index.lambda_handler',
      timeout: cdk.Duration.seconds(300),
      memorySize: 512,
      role: streamingHandlerRole,
      environment: {
        AGENT_ID: props.runtimeId,
        AGENT_ALIAS_ID: 'TSTALIASID',
        STAGE: props.stage,
        AWS_ACCOUNT_ID: props.accountId,
      },
      description: 'Calls Agent Core Runtime and returns response',
    });

    // CloudWatch Log Group - Lambda creates this automatically
    // No need to create it explicitly to avoid conflicts

    // ========================================
    // FUNCTION URL WITH STREAMING
    // ========================================

    const functionUrl = this.streamingHandler.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE, // Public access
      invokeMode: lambda.InvokeMode.RESPONSE_STREAM, // Enable streaming with SSE
      cors: {
        allowedOrigins: ['*'],
        allowedMethods: [lambda.HttpMethod.ALL],
        allowedHeaders: ['*'],
        allowCredentials: false,
      },
    });

    this.functionUrl = functionUrl.url;

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'StreamingFunctionUrl', {
      value: this.functionUrl,
      description: 'Lambda Function URL for streaming chat',
      exportName: `processapp-streaming-url-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: this.streamingHandler.functionName,
      description: 'Streaming Lambda function name',
      exportName: `processapp-streaming-lambda-${props.stage}`,
    });

    new cdk.CfnOutput(this, 'TestCurlCommand', {
      value: `curl -X POST "${this.functionUrl}" -H "Content-Type: application/json" -d '{"prompt":"Hola","sessionId":"test-123"}'`,
      description: 'Test command using curl',
    });
  }
}
