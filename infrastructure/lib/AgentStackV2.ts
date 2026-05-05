/**
 * AgentStackV2 - Phase 2: REAL Agent Core with Strand Agents SDK
 *
 * This stack deploys:
 * - Custom agent using Strand Agents SDK (TypeScript)
 * - Agent Core Runtime (managed compute)
 * - Agent Core Memory (conversation history)
 * - Runtime Endpoint (HTTPS invocation)
 *
 * Benefits over Phase 1:
 * - Custom agent logic (full control)
 * - Strand SDK handles tool calling automatically
 * - Native MCP protocol support
 * - No Lambda intermediary
 * - Automatic conversation memory
 * - Lower latency and cost
 */

import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as path from 'path';
import { Construct } from 'constructs';
import { AgentConfig } from '../config/environments';

export interface AgentStackV2Props extends cdk.StackProps {
  stage: string;
  accountId: string;
  knowledgeBaseId: string;
}

export class AgentStackV2 extends cdk.Stack {
  public readonly runtimeId: string;
  public readonly runtimeArn: string;
  public readonly runtime: agentcore.Runtime;
  public readonly memoryId: string;
  public readonly memoryArn: string;
  public readonly endpointUrl: string;

  constructor(scope: Construct, id: string, props: AgentStackV2Props) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;
    const runtimeName = `processapp_agent_runtime_${props.stage}`;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-agent-strand');

    // ========================================
    // IAM ROLE FOR RUNTIME
    // ========================================

    const runtimeRole = new iam.Role(this, 'RuntimeRole', {
      roleName: `processapp-runtime-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
      description: 'Execution role for ProcessApp Agent Core Runtime (Strand)',
      maxSessionDuration: cdk.Duration.hours(1),
    });

    // Grant permissions to invoke foundation model or inference profile
    // When using inference profiles, we need to grant access to BOTH:
    // 1. The inference profile ARN (what we configure)
    // 2. The underlying foundation model ARN (what the SDK actually invokes)
    const modelResources: string[] = [];

    if (AgentConfig.foundationModel.startsWith('us.') || AgentConfig.foundationModel.startsWith('global.')) {
      // Inference profile - add both inference profile and underlying model
      modelResources.push(
        `arn:aws:bedrock:${region}:${props.accountId}:inference-profile/${AgentConfig.foundationModel}`
      );
      // Extract underlying model ID (e.g., us.anthropic.claude-sonnet-4-5-20250929-v1:0 -> anthropic.claude-sonnet-4-5-20250929-v1:0)
      const underlyingModelId = AgentConfig.foundationModel.replace(/^(us|global)\./, '');
      modelResources.push(
        `arn:aws:bedrock:${region}::foundation-model/${underlyingModelId}`
      );
    } else {
      // Direct model ID
      modelResources.push(
        `arn:aws:bedrock:${region}::foundation-model/${AgentConfig.foundationModel}`
      );
    }

    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: ['*'],
      })
    );

    // Grant permissions to retrieve from Knowledge Base
    runtimeRole.addToPolicy(
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

    // Grant permissions to use Agent Core Memory
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:GetMemory',
          'bedrock:PutMemory',
          'bedrock:DeleteMemory',
        ],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:memory/*`,
        ],
      })
    );

    // Note: CloudWatch Logs permissions are granted via runtimeLogGroup.grantWrite()
    // (see CloudWatch Logs section below)

    // ========================================
    // AGENT CORE MEMORY
    // ========================================
    // SHORT_TERM: Raw event memory with 7-day retention (minimum allowed by AWS)
    // No long-term extraction strategies - only raw conversation events
    const memory = new agentcore.Memory(this, 'AgentMemoryV2', {
      memoryName: `processapp_agent_memory_${props.stage}`,
      description: 'Short-term conversation memory for ProcessApp Agent  (Strand)',
      expirationDuration: cdk.Duration.days(7), // Minimum: 7 days, Maximum: 365 days
    });

    this.memoryId = memory.memoryId;
    this.memoryArn = memory.memoryArn;

    // Grant runtime access to memory (read and write)
    memory.grantRead(runtimeRole);
    memory.grantWrite(runtimeRole);

    // ========================================
    // CLOUDWATCH LOGS FOR OBSERVABILITY
    // ========================================

    // Create CloudWatch Log Group for Agent Runtime logs
    const runtimeLogGroup = new logs.LogGroup(this, 'RuntimeLogGroup', {
      logGroupName: `/aws/bedrock/agentcore/runtime/${runtimeName}`,
      retention: logs.RetentionDays.ONE_WEEK, // 7 days retention
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Delete logs when stack is deleted
    });

    // Grant runtime permission to write logs
    runtimeLogGroup.grantWrite(runtimeRole);

    // ========================================
    // AGENT RUNTIME ARTIFACT
    // ========================================
    // Direct code deployment (no Docker needed)

    // Package agent code for deployment using Docker
    // Docker ensures all dependencies (OpenTelemetry) are installed
    const agentCode = agentcore.AgentRuntimeArtifact.fromAsset(
      path.join(__dirname as any, '../../agents')
    );

    // ========================================
    // AGENT CORE RUNTIME
    // ========================================

    const runtime = new agentcore.Runtime(this, 'AgentRuntimeV2', {
      runtimeName: runtimeName,
      description: 'ProcessApp Agent Core Runtime  using Strand Agents SDK',
      agentRuntimeArtifact: agentCode,
      executionRole: runtimeRole,

      // Environment variables for the agent
      environmentVariables: {
        KB_ID: props.knowledgeBaseId,
        MODEL_ID: AgentConfig.foundationModel,
        MEMORY_ID: memory.memoryId,
        REGION: region,
        STAGE: props.stage,
        ECS_BASE_URL: 'https://dev.app.colpensiones.procesapp.com',
        PORT: '8080',
      },

      // Network configuration (public for now - can be VPC later)
      networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),

      // Authorization (IAM by default)
      authorizerConfiguration: agentcore.RuntimeAuthorizerConfiguration.usingIAM(),

      // Protocol (HTTP for REST API)
      protocolConfiguration: agentcore.ProtocolType.HTTP,

      // Disable X-Ray tracing (requires additional account setup)
      // Keep this false until X-Ray CloudWatch Logs destination is configured
      tracingEnabled: false,

      // CloudWatch Logs configuration for observability
      // Application logs and usage logs will be sent to CloudWatch
      loggingConfigs: [
        {
          logType: agentcore.LogType.APPLICATION_LOGS, // Agent invocations
          destination: agentcore.LoggingDestination.cloudWatchLogs(runtimeLogGroup),
        },
        {
          logType: agentcore.LogType.USAGE_LOGS, // Session-level resource consumption
          destination: agentcore.LoggingDestination.cloudWatchLogs(runtimeLogGroup),
        },
      ],
    });

    this.runtimeId = runtime.agentRuntimeId;
    this.runtimeArn = runtime.agentRuntimeArn;
    this.runtime = runtime;

    // ========================================
    // RUNTIME ENDPOINT (HTTPS Endpoint for Agent)
    // ========================================
    // Creates a public HTTPS endpoint to invoke the agent
    // RuntimeEndpoint exposes the runtime via HTTPS with IAM auth

    const runtimeEndpoint = new agentcore.RuntimeEndpoint(this, 'RuntimeEndpointV2', {
      agentRuntimeId: runtime.agentRuntimeId,
      endpointName: `processapp_endpoint_${props.stage}`,
    });

    // The endpoint URL is constructed from the endpoint ID
    this.endpointUrl = `https://${runtimeEndpoint.endpointId}.bedrock-agentcore.${region}.amazonaws.com`;

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'RuntimeIdV2', {
      value: this.runtimeId,
      description: 'Agent Core Runtime  ID (Strand)',
      exportName: `processapp-runtime-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'RuntimeArnV2', {
      value: this.runtimeArn,
      description: 'Agent Core Runtime  ARN',
      exportName: `processapp-runtime-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'RuntimeEndpointUrlV2', {
      value: this.endpointUrl,
      description: 'Agent Core Runtime  HTTPS Endpoint URL',
      exportName: `processapp-runtime-endpoint-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'RuntimeNameV2', {
      value: this.runtime.agentRuntimeName,
      description: 'Agent Core Runtime  Name',
      exportName: `processapp-runtime-name-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'MemoryIdV2', {
      value: this.memoryId,
      description: 'Agent Core Memory  ID',
      exportName: `processapp-memory-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'MemoryArnV2', {
      value: this.memoryArn,
      description: 'Agent Core Memory  ARN',
      exportName: `processapp-memory-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'RuntimeLogGroupV2', {
      value: runtimeLogGroup.logGroupName,
      description: 'CloudWatch Log Group for Agent Runtime ',
      exportName: `processapp-runtime-loggroup-${props.stage}-${region}`,
    });

    // ========================================
    // NOTES
    // ========================================
    // Phase 2 Implementation with Agent Core + Strand:
    //
    // 1. Custom Agent (Strand SDK):
    //    - TypeScript-based agent logic
    //    - Tools defined with Zod schemas
    //    - Automatic tool calling
    //    - Native MCP protocol support
    //
    // 2. Runtime:
    //    - Managed compute environment
    //    - Direct code deployment (no Docker)
    //    - Auto-scaling and lifecycle management
    //    - X-Ray tracing enabled
    //
    // 3. Memory:
    //    - Automatic conversation storage (90 days)
    //    - Summarization extraction strategy
    //    - No manual DynamoDB management
    //
    // 4. Endpoint:
    //    - Stable HTTPS endpoint for invocation
    //    - Version management (can deploy , v3, etc.)
    //    - IAM authentication
    //
    // 5. Integration:
    //    - Same Knowledge Base as Phase 1
    //    - Both agents can run in parallel
    //    - Independent deployment and testing
    //
    // 6. Tools:
    //    - getProjectInfo: HTTP call to ECS service
    //    - searchKnowledge: Query Bedrock KB
    //    - Strand SDK handles orchestration
    //
    // 7. Invocation:
    //    POST to runtime endpoint:
    //    {
    //      "inputText": "What is project 1?",
    //      "sessionId": "user-123"
    //    }
    //
    // 8. Testing:
    //    - Deploy: npx cdk deploy dev-us-east-1-agent-v2 --profile default
    //    - Test via HTTPS endpoint (AWS Sig4 auth)
    //    - Monitor: X-Ray traces, CloudWatch logs
    //
    // 9. Benefits over Phase 1:
    //    - Full control over agent logic
    //    - Simpler architecture (no API Gateway, no Lambda action groups)
    //    - Native Strand SDK tool calling
    //    - Better observability
    //    - Lower latency
    //    - Native MCP protocol
  }
}
