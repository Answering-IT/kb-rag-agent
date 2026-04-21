/**
 * SecurityStack - Per-region encryption and access control
 *
 * Creates:
 * - KMS customer-managed key
 * - IAM policies for Bedrock KB, Lambda, Textract
 * - S3 bucket policies (enforce encryption, HTTPS)
 * - VPC S3 gateway endpoint
 */

import * as cdk from 'aws-cdk-lib';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import {
  getKMSKeyPolicyStatements,
  getS3BucketPolicyStatements,
  getBedrockKBPolicy,
  getS3VPCEndpointPolicy,
} from '../config/security.config';
import { SecurityConfig } from '../config/environments';

export interface SecurityStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  docsBucket: s3.IBucket;
  vectorsBucket: s3.IBucket;
  bedrockKBRole: iam.IRole;
  kmsKey: kms.IKey;
}

export class SecurityStack extends cdk.Stack {
  public readonly vpcEndpoint?: ec2.IGatewayVpcEndpoint;

  constructor(scope: Construct, id: string, props: SecurityStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-security');

    // Add KMS key policies
    const keyPolicyStatements = getKMSKeyPolicyStatements(
      props.accountId,
      region,
      {
        allowBedrockAccess: true,
        allowLambdaAccess: true,
        allowTextractAccess: true,
        allowS3Access: true,
      }
    );

    keyPolicyStatements.forEach((statement) => {
      props.kmsKey.addToResourcePolicy(statement);
    });

    // ========================================
    // S3 BUCKET POLICIES
    // ========================================

    // Update S3 buckets to use KMS encryption
    // Note: Buckets already exist from PrereqsStack, we just add policies

    // Docs bucket policy
    const docsBucketPolicyStatements = getS3BucketPolicyStatements(
      props.docsBucket.bucketArn,
      props.accountId
    );

    docsBucketPolicyStatements.forEach((statement) => {
      props.docsBucket.addToResourcePolicy(statement);
    });

    // Allow specific IAM user to upload documents (for testing)
    props.docsBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'AllowUserUpload',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ArnPrincipal(`arn:aws:iam::${props.accountId}:user/qohat.prettel`)],
        actions: ['s3:PutObject', 's3:GetObject', 's3:ListBucket'],
        resources: [
          props.docsBucket.bucketArn,
          `${props.docsBucket.bucketArn}/*`,
        ],
      })
    );

    // Grant KMS key access to docs bucket and specific user
    props.kmsKey.grantEncryptDecrypt(
      new iam.ServicePrincipal('s3.amazonaws.com')
    );
    props.kmsKey.grantEncryptDecrypt(
      new iam.ArnPrincipal(`arn:aws:iam::${props.accountId}:user/qohat.prettel`)
    );

    // Vectors bucket policy
    const vectorsBucketPolicyStatements = getS3BucketPolicyStatements(
      props.vectorsBucket.bucketArn,
      props.accountId
    );

    vectorsBucketPolicyStatements.forEach((statement) => {
      props.vectorsBucket.addToResourcePolicy(statement);
    });

    // ========================================
    // IAM POLICIES
    // ========================================

    // Bedrock Knowledge Base policy
    // Note: S3 vector bucket is created in BedrockStack, so we construct the name here
    const vectorBucketName = `processapp-vectors-${props.stage}-${props.accountId}`;

    const bedrockKBPolicy = getBedrockKBPolicy(
      props.docsBucket.bucketArn,
      props.vectorsBucket.bucketArn,
      props.kmsKey.keyArn,
      region,
      props.accountId,
      vectorBucketName
    );

    props.bedrockKBRole.attachInlinePolicy(
      new iam.Policy(this, 'BedrockKBPolicy', {
        policyName: `processapp-bedrock-kb-policy-${props.stage}`,
        document: bedrockKBPolicy,
      })
    );

    // Grant Bedrock KB role access to buckets
    props.docsBucket.grantRead(props.bedrockKBRole);
    props.vectorsBucket.grantReadWrite(props.bedrockKBRole);

    // Grant Bedrock KB role KMS access
    props.kmsKey.grantEncryptDecrypt(props.bedrockKBRole);

    // ========================================
    // VPC ENDPOINT (Optional)
    // ========================================

    // Create VPC endpoint for S3 if enabled
    // Note: This requires a VPC. If no VPC exists, skip this step.
    if (SecurityConfig.vpcEndpoints.s3) {
      // Check if there's a default VPC
      const defaultVpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
        isDefault: true,
      });

      if (defaultVpc) {
        // Create S3 gateway endpoint (no charge)
        this.vpcEndpoint = new ec2.GatewayVpcEndpoint(this, 'S3VPCEndpoint', {
          vpc: defaultVpc,
          service: ec2.GatewayVpcEndpointAwsService.S3,
        });

        new cdk.CfnOutput(this, 'S3VPCEndpointId', {
          value: this.vpcEndpoint.vpcEndpointId,
          description: 'S3 VPC Endpoint ID',
          exportName: `processapp-s3-vpc-endpoint-${props.stage}-${region}`,
        });
      }
    }

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'KMSKeyId', {
      value: props.kmsKey.keyId,
      description: 'KMS Key ID',
      exportName: `processapp-kms-key-id-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'KMSKeyArn', {
      value: props.kmsKey.keyArn,
      description: 'KMS Key ARN',
      exportName: `processapp-kms-key-arn-${props.stage}-${region}`,
    });
  }
}
