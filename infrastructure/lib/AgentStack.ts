/**
 * AgentStack - Bedrock Agent Core for RAG Queries
 *
 * Creates:
 * - Bedrock Agent with Knowledge Base integration
 * - IAM role for agent execution
 * - Agent alias for deployment
 * - Guardrails integration for content safety
 */

import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';
import { AgentConfig } from '../config/environments';
import * as path from 'path';

export interface AgentStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  knowledgeBaseId: string;
  guardrailId: string;
  guardrailVersion: string;
  docsBucket: s3.IBucket;
}

export class AgentStack extends cdk.Stack {
  public readonly agentId: string;
  public readonly agentArn: string;
  public readonly agentAliasId: string;
  public readonly agentAliasArn: string;

  constructor(scope: Construct, id: string, props: AgentStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;
    const agentName = `${AgentConfig.name}-${props.stage}`;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-agent');

    // ========================================
    // IAM ROLE FOR AGENT
    // ========================================

    const agentRole = new iam.Role(this, 'AgentRole', {
      roleName: `processapp-agent-role-${props.stage}`,
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com', {
        conditions: {
          StringEquals: {
            'aws:SourceAccount': props.accountId,
          },
          ArnLike: {
            'aws:SourceArn': `arn:aws:bedrock:${region}:${props.accountId}:agent/*`,
          },
        },
      }),
      description: 'Execution role for ProcessApp Bedrock Agent',
      maxSessionDuration: cdk.Duration.hours(1),
    });

    // Grant permissions to invoke foundation model
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${region}::foundation-model/${AgentConfig.foundationModel}`,
        ],
      })
    );

    // Grant permissions to retrieve from Knowledge Base
    agentRole.addToPolicy(
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

    // Grant permissions to apply guardrails
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:ApplyGuardrail'],
        resources: [
          `arn:aws:bedrock:${region}:${props.accountId}:guardrail/${props.guardrailId}`,
        ],
      })
    );

    // ========================================
    // ACTION GROUP: GET PROJECT INFO TOOL
    // ========================================

    // Create Lambda for GetProjectInfo tool
    const getProjectInfoTool = new lambda.Function(this, 'GetProjectInfoTool', {
      functionName: `processapp-get-project-info-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'get_project_info.handler',
      code: lambda.Code.fromAsset(
        path.join(__dirname, '../lambdas/agent-tools')
      ),
      timeout: cdk.Duration.seconds(15),
      memorySize: 256,
      environment: {
        ECS_BASE_URL: 'https://dev.app.colpensiones.procesapp.com',
        STAGE: props.stage,
      },
      description: 'Action group tool to get project information from ECS service',
      // Disable automatic LogGroup creation by CDK
      logRetention: undefined,
    });

    // Grant agent role permission to invoke tool Lambda
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['lambda:InvokeFunction'],
        resources: [getProjectInfoTool.functionArn],
      })
    );

    // Grant Lambda permission to be invoked by Bedrock
    getProjectInfoTool.addPermission('BedrockInvoke', {
      principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      action: 'lambda:InvokeFunction',
      sourceAccount: props.accountId,
      sourceArn: `arn:aws:bedrock:${region}:${props.accountId}:agent/*`,
    });

    // ========================================
    // BEDROCK AGENT
    // ========================================

    const agent = new bedrock.CfnAgent(this, 'Agent', {
      agentName: agentName,
      description: AgentConfig.description,
      agentResourceRoleArn: agentRole.roleArn,
      foundationModel: AgentConfig.foundationModel,
      instruction: AgentConfig.instructions,

      // Idle session TTL (in seconds)
      idleSessionTtlInSeconds: AgentConfig.idleSessionTTL,

      // Guardrail configuration
      guardrailConfiguration: {
        guardrailIdentifier: props.guardrailId,
        guardrailVersion: props.guardrailVersion,
      },

      // Knowledge bases to use
      knowledgeBases: [
        {
          knowledgeBaseId: props.knowledgeBaseId,
          description: 'ProcessApp document knowledge base',
          knowledgeBaseState: 'ENABLED',
        },
      ],

      // Action groups (tools)
      actionGroups: [
        {
          actionGroupName: 'GetProjectInfo',
          description: 'Retrieve project information from ECS service including budget, status, and users',
          actionGroupState: 'ENABLED',
          actionGroupExecutor: {
            lambda: getProjectInfoTool.functionArn,
          },
          apiSchema: {
            payload: JSON.stringify({
              openapi: '3.0.0',
              info: {
                title: 'Project Information API',
                version: '1.0.0',
                description: 'API to retrieve project information from ECS service',
              },
              paths: {
                '/organization/{orgId}/projects/{projectId}': {
                  get: {
                    summary: 'Get project information by ID',
                    description: 'Retrieves detailed information about a specific project',
                    operationId: 'getProjectInfo',
                    parameters: [
                      {
                        name: 'orgId',
                        in: 'path',
                        description: 'Organization ID',
                        required: true,
                        schema: { type: 'string' },
                      },
                      {
                        name: 'projectId',
                        in: 'path',
                        description: 'Project ID',
                        required: true,
                        schema: { type: 'string' },
                      },
                    ],
                    responses: {
                      '200': {
                        description: 'Project information retrieved successfully',
                        content: {
                          'application/json': {
                            schema: {
                              type: 'object',
                              properties: {
                                id: { type: 'string' },
                                name: { type: 'string' },
                                budget: { type: 'number' },
                                status: { type: 'string' },
                              },
                            },
                          },
                        },
                      },
                    },
                  },
                },
              },
            }),
          },
        },
      ],

      // Prompt override configuration (optional)
      promptOverrideConfiguration: AgentConfig.promptOverride.enabled
        ? {
            promptConfigurations: [
              {
                promptType: 'PRE_PROCESSING',
                promptCreationMode: 'OVERRIDDEN',
                promptState: 'ENABLED',
                basePromptTemplate: AgentConfig.instructions,
                inferenceConfiguration: {
                  temperature: AgentConfig.inference.temperature,
                  topP: AgentConfig.inference.topP,
                  maximumLength: AgentConfig.inference.maxTokens,
                  stopSequences: AgentConfig.inference.stopSequences,
                },
              },
            ],
          }
        : undefined,

      // Auto-prepare agent (create DRAFT version)
      autoPrepare: true,
    });

    this.agentId = agent.attrAgentId;
    this.agentArn = agent.attrAgentArn;

    // ========================================
    // AGENT ALIAS
    // ========================================

    // Create agent alias for deployment
    // An alias points to a specific version of the agent
    // Note: routingConfiguration is omitted - AWS will automatically
    // route to the latest PREPARED version (not DRAFT)
    const agentAlias = new bedrock.CfnAgentAlias(this, 'AgentAlias', {
      agentId: this.agentId,
      agentAliasName: 'live',
      description: `Live alias for ${agentName}`,

      // Removed routingConfiguration - Bedrock aliases cannot point to DRAFT
      // The alias will automatically route to the latest prepared version
    });

    agentAlias.addDependency(agent);

    this.agentAliasId = agentAlias.attrAgentAliasId;
    this.agentAliasArn = agentAlias.attrAgentAliasArn;

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'AgentId', {
      value: this.agentId,
      description: 'Bedrock Agent ID',
      exportName: `processapp-agent-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'AgentArn', {
      value: this.agentArn,
      description: 'Bedrock Agent ARN',
      exportName: `processapp-agent-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'AgentAliasId', {
      value: this.agentAliasId,
      description: 'Bedrock Agent Alias ID',
      exportName: `processapp-agent-alias-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'AgentAliasArn', {
      value: this.agentAliasArn,
      description: 'Bedrock Agent Alias ARN',
      exportName: `processapp-agent-alias-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'AgentInvocationCommand', {
      value: `aws bedrock-agent-runtime invoke-agent --agent-id ${this.agentId} --agent-alias-id ${this.agentAliasId} --session-id <session-id> --input-text "<your question>"`,
      description: 'CLI command to invoke the agent',
    });
  }
}
