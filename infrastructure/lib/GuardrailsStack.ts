/**
 * GuardrailsStack - Content filtering and PII protection
 *
 * Creates:
 * - Bedrock Guardrail (via custom resource)
 * - PII detection and blocking
 * - Content policy filters
 * - Topic blocking
 */

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cr from 'aws-cdk-lib/custom-resources';
import { Construct } from 'constructs';
import * as path from 'path';
import { getGuardrailConfig } from '../config/security.config';
import { getCustomResourcePolicy } from '../config/security.config';

export interface GuardrailsStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
}

export class GuardrailsStack extends cdk.Stack {
  public readonly guardrailId: string;
  public readonly guardrailArn: string;

  constructor(scope: Construct, id: string, props: GuardrailsStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-guardrails');

    // ========================================
    // CUSTOM RESOURCE EXECUTION ROLE
    // ========================================

    const customResourceRole = new iam.Role(this, 'GuardrailCustomResourceRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for Guardrail custom resource',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole'
        ),
      ],
      inlinePolicies: {
        GuardrailPolicy: getCustomResourcePolicy(region),
      },
    });

    // ========================================
    // GUARDRAIL CUSTOM RESOURCE LAMBDA
    // ========================================

    const guardrailCreatorFunction = new lambda.Function(
      this,
      'GuardrailCreatorFunction',
      {
        functionName: `processapp-guardrail-creator-${props.stage}`,
        runtime: lambda.Runtime.PYTHON_3_11,
        handler: 'index.handler',
        code: lambda.Code.fromAsset(
          path.join(__dirname, '../lambdas/guardrail-creator')
        ),
        role: customResourceRole,
        timeout: cdk.Duration.minutes(5),
        memorySize: 256,
        environment: {
          STAGE: props.stage,
        },
        description: 'Custom resource for creating Bedrock Guardrail',
      }
    );

    // ========================================
    // CREATE GUARDRAIL (Custom Resource)
    // ========================================

    const guardrailConfig = getGuardrailConfig();

    const guardrailProvider = new cr.Provider(this, 'GuardrailProvider', {
      onEventHandler: guardrailCreatorFunction,
    });

    const guardrail = new cdk.CustomResource(this, 'Guardrail', {
      serviceToken: guardrailProvider.serviceToken,
      properties: {
        Name: `${guardrailConfig.name}-${props.stage}`,
        Description: guardrailConfig.description,
        BlockedInputMessaging: guardrailConfig.blockedInputMessaging,
        BlockedOutputsMessaging: guardrailConfig.blockedOutputMessaging,

        // Content filters
        ContentPolicyConfig: guardrailConfig.contentPolicyConfig,

        // PII detection
        SensitiveInformationPolicyConfig:
          guardrailConfig.sensitiveInformationPolicyConfig,

        // Topic blocking
        TopicPolicyConfig: guardrailConfig.topicPolicyConfig,

        // Word filters (optional)
        WordPolicyConfig: guardrailConfig.wordPolicyConfig || {},
      },
    });

    this.guardrailId = guardrail.getAttString('GuardrailId');
    this.guardrailArn = guardrail.getAttString('GuardrailArn');

    // ========================================
    // CREATE GUARDRAIL VERSION
    // ========================================

    // Guardrails require a version to be used
    const versionFunction = new lambda.Function(this, 'GuardrailVersionFunction', {
      functionName: `processapp-guardrail-version-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import boto3
import json

bedrock = boto3.client('bedrock')

def handler(event, context):
    request_type = event['RequestType']
    guardrail_id = event['ResourceProperties']['GuardrailId']

    if request_type == 'Create' or request_type == 'Update':
        try:
            # Create a version of the guardrail
            response = bedrock.create_guardrail_version(
                guardrailIdentifier=guardrail_id,
                description=f'Version created for {context.function_name}'
            )

            version = response['version']
            print(f'Created guardrail version: {version}')

            return {
                'PhysicalResourceId': f'{guardrail_id}-v{version}',
                'Data': {
                    'Version': version,
                    'GuardrailId': guardrail_id
                }
            }
        except Exception as e:
            print(f'Error creating version: {str(e)}')
            raise

    elif request_type == 'Delete':
        # No action needed on delete
        return {
            'PhysicalResourceId': event['PhysicalResourceId']
        }
      `),
      role: customResourceRole,
      timeout: cdk.Duration.minutes(2),
      memorySize: 128,
    });

    const versionProvider = new cr.Provider(this, 'GuardrailVersionProvider', {
      onEventHandler: versionFunction,
    });

    const guardrailVersion = new cdk.CustomResource(this, 'GuardrailVersion', {
      serviceToken: versionProvider.serviceToken,
      properties: {
        GuardrailId: this.guardrailId,
      },
    });

    guardrailVersion.node.addDependency(guardrail);

    const version = guardrailVersion.getAttString('Version');

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'GuardrailId', {
      value: this.guardrailId,
      description: 'Bedrock Guardrail ID',
      exportName: `processapp-guardrail-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'GuardrailArn', {
      value: this.guardrailArn,
      description: 'Bedrock Guardrail ARN',
      exportName: `processapp-guardrail-arn-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'GuardrailVersionOutput', {
      value: version,
      description: 'Bedrock Guardrail version',
      exportName: `processapp-guardrail-version-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'GuardrailIdentifierOutput', {
      value: `${this.guardrailId}:${version}`,
      description: 'Bedrock Guardrail identifier with version',
      exportName: `processapp-guardrail-identifier-${props.stage}-${region}`,
    });
  }
}
