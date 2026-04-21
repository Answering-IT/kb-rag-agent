/**
 * APIStack - REST API Gateway for agent queries
 *
 * Creates:
 * - API Gateway REST API
 * - Lambda handler for agent invocations
 * - API Key for authentication
 * - CORS configuration
 */

import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface APIStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  agentId: string;
  agentAliasId: string;
}

export class APIStack extends cdk.Stack {
  public readonly apiUrl: string;
  public readonly apiKeyId: string;

  constructor(scope: Construct, id: string, props: APIStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-api');

    // ========================================
    // IAM ROLE FOR API HANDLER LAMBDA
    // ========================================

    const apiHandlerRole = new iam.Role(this, 'APIHandlerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for API handler Lambda to invoke Bedrock Agent',
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
    apiHandlerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'InvokeBedrockAgent',
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:InvokeAgent',
          'bedrock:Retrieve',
          'bedrock:RetrieveAndGenerate',
        ],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:agent/${props.agentId}`,
          `arn:aws:bedrock:${region}:${props.accountId}:agent-alias/${props.agentId}/*`,
        ],
      })
    );

    // ========================================
    // API HANDLER LAMBDA
    // ========================================

    const apiHandler = new lambda.Function(this, 'APIHandler', {
      functionName: `processapp-api-handler-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/api-handler')
      ),
      role: apiHandlerRole,
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        AGENT_ID: props.agentId,
        AGENT_ALIAS_ID: props.agentAliasId,
        STAGE: props.stage,
      },
      description: 'API Gateway handler for Bedrock Agent queries',
      tracing: lambda.Tracing.ACTIVE,
    });

    // ========================================
    // API GATEWAY REST API
    // ========================================

    // CloudWatch log group for API Gateway
    const apiLogGroup = new logs.LogGroup(this, 'APILogs', {
      logGroupName: `/aws/apigateway/processapp-${props.stage}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Create REST API
    const api = new apigateway.RestApi(this, 'AgentAPI', {
      restApiName: `processapp-agent-api-${props.stage}`,
      description: 'REST API for Bedrock Agent queries',
      deployOptions: {
        stageName: props.stage,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(apiLogGroup),
        accessLogFormat: apigateway.AccessLogFormat.clf(),
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
      },
      endpointConfiguration: {
        types: [apigateway.EndpointType.REGIONAL],
      },
    });

    // ========================================
    // API RESOURCES AND METHODS
    // ========================================

    // /query endpoint
    const queryResource = api.root.addResource('query');

    // Lambda integration
    const lambdaIntegration = new apigateway.LambdaIntegration(apiHandler, {
      proxy: true,
      integrationResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        },
      ],
    });

    // POST /query method
    const queryMethod = queryResource.addMethod('POST', lambdaIntegration, {
      apiKeyRequired: true,
      methodResponses: [
        {
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
          },
        },
      ],
    });

    // ========================================
    // API KEY AND USAGE PLAN
    // ========================================

    // Create API key
    const apiKey = new apigateway.ApiKey(this, 'APIKey', {
      apiKeyName: `processapp-api-key-${props.stage}`,
      description: 'API key for ProcessApp agent queries',
      enabled: true,
    });

    // Create usage plan
    const usagePlan = new apigateway.UsagePlan(this, 'UsagePlan', {
      name: `processapp-usage-plan-${props.stage}`,
      description: 'Usage plan for ProcessApp API',
      throttle: {
        rateLimit: 100, // requests per second
        burstLimit: 200, // max concurrent requests
      },
      quota: {
        limit: 10000, // requests per month
        period: apigateway.Period.MONTH,
      },
    });

    // Associate API key with usage plan
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({
      stage: api.deploymentStage,
    });

    // Store API key ID
    this.apiKeyId = apiKey.keyId;
    this.apiUrl = api.url;

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'APIEndpoint', {
      value: `${api.url}query`,
      description: 'API Gateway endpoint for agent queries',
      exportName: `processapp-api-endpoint-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'APIKeyId', {
      value: apiKey.keyId,
      description: 'API Key ID (use AWS CLI to get actual key value)',
      exportName: `processapp-api-key-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'APIHandlerArn', {
      value: apiHandler.functionArn,
      description: 'API Handler Lambda ARN',
      exportName: `processapp-api-handler-arn-${props.stage}-${region}`,
    });

    // Output command to retrieve API key value
    new cdk.CfnOutput(this, 'GetAPIKeyCommand', {
      value: `aws apigateway get-api-key --api-key ${apiKey.keyId} --include-value --query 'value' --output text`,
      description: 'Command to retrieve API key value',
    });
  }
}
