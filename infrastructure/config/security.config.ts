/**
 * Security configuration for RAG infrastructure
 * Defines KMS policies, IAM policies, S3 bucket policies, and Guardrails
 */

import * as iam from 'aws-cdk-lib/aws-iam';
import { GuardrailsConfig } from './environments';

/**
 * KMS Key Policy Configuration
 */
export interface KMSKeyPolicyConfig {
  allowBedrockAccess: boolean;
  allowLambdaAccess: boolean;
  allowTextractAccess: boolean;
  allowS3Access: boolean;
}

/**
 * Get KMS key policy statements
 */
export function getKMSKeyPolicyStatements(
  accountId: string,
  region: string,
  config: KMSKeyPolicyConfig
): iam.PolicyStatement[] {
  const statements: iam.PolicyStatement[] = [
    // Enable IAM User Permissions
    new iam.PolicyStatement({
      sid: 'Enable IAM User Permissions',
      effect: iam.Effect.ALLOW,
      principals: [new iam.AccountRootPrincipal()],
      actions: ['kms:*'],
      resources: ['*'],
    }),
  ];

  // Bedrock service access
  if (config.allowBedrockAccess) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'Allow Bedrock to use the key',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
        actions: [
          'kms:Decrypt',
          'kms:Encrypt',
          'kms:GenerateDataKey',
          'kms:DescribeKey',
        ],
        resources: ['*'],
        conditions: {
          StringEquals: {
            'kms:ViaService': [`bedrock.${region}.amazonaws.com`],
          },
        },
      })
    );
  }

  // Lambda service access
  if (config.allowLambdaAccess) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'Allow Lambda to use the key',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('lambda.amazonaws.com')],
        actions: ['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey'],
        resources: ['*'],
        conditions: {
          StringEquals: {
            'kms:ViaService': [`lambda.${region}.amazonaws.com`],
          },
        },
      })
    );
  }

  // Textract service access
  if (config.allowTextractAccess) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'Allow Textract to use the key',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('textract.amazonaws.com')],
        actions: ['kms:Decrypt', 'kms:GenerateDataKey'],
        resources: ['*'],
        conditions: {
          StringEquals: {
            'kms:ViaService': [`textract.${region}.amazonaws.com`],
          },
        },
      })
    );
  }

  // S3 service access
  if (config.allowS3Access) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'Allow S3 to use the key',
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('s3.amazonaws.com')],
        actions: ['kms:Decrypt', 'kms:GenerateDataKey'],
        resources: ['*'],
      })
    );
  }

  return statements;
}

/**
 * S3 Bucket Policy Configuration
 */
export function getS3BucketPolicyStatements(
  bucketArn: string,
  accountId: string
): iam.PolicyStatement[] {
  return [
    // Deny unencrypted uploads
    new iam.PolicyStatement({
      sid: 'DenyUnencryptedObjectUploads',
      effect: iam.Effect.DENY,
      principals: [new iam.AnyPrincipal()],
      actions: ['s3:PutObject'],
      resources: [`${bucketArn}/*`],
      conditions: {
        StringNotEquals: {
          's3:x-amz-server-side-encryption': 'aws:kms',
        },
      },
    }),

    // Enforce HTTPS only
    new iam.PolicyStatement({
      sid: 'DenyInsecureTransport',
      effect: iam.Effect.DENY,
      principals: [new iam.AnyPrincipal()],
      actions: ['s3:*'],
      resources: [bucketArn, `${bucketArn}/*`],
      conditions: {
        Bool: {
          'aws:SecureTransport': 'false',
        },
      },
    }),

    // Block public access
    new iam.PolicyStatement({
      sid: 'BlockPublicAccess',
      effect: iam.Effect.DENY,
      principals: [new iam.AnyPrincipal()],
      actions: ['s3:GetObject', 's3:PutObject'],
      resources: [`${bucketArn}/*`],
      conditions: {
        StringNotEquals: {
          'aws:PrincipalAccount': accountId,
        },
      },
    }),
  ];
}

/**
 * Bedrock Knowledge Base IAM Policy
 */
export function getBedrockKBPolicy(
  docsBucketArn: string,
  vectorsBucketArn: string | undefined, // Made optional (Phase 2) - regular S3 bucket removed
  kmsKeyArn: string,
  region: string,
  accountId?: string,
  vectorsBucketName?: string
): iam.PolicyDocument {
  const statements = [
    // S3 read access for docs bucket
    new iam.PolicyStatement({
      sid: 'ReadDocumentsBucket',
      effect: iam.Effect.ALLOW,
      actions: ['s3:GetObject', 's3:ListBucket'],
      resources: [docsBucketArn, `${docsBucketArn}/*`],
    }),

    // Bedrock model access
    new iam.PolicyStatement({
      sid: 'InvokeBedrockModels',
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
      resources: [
        `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`,
        `arn:aws:bedrock:${region}::foundation-model/anthropic.claude-sonnet-3-5-v2:0`,
      ],
    }),

    // KMS access
    new iam.PolicyStatement({
      sid: 'UseKMSKey',
      effect: iam.Effect.ALLOW,
      actions: [
        'kms:Decrypt',
        'kms:Encrypt',
        'kms:GenerateDataKey',
        'kms:DescribeKey',
      ],
      resources: [kmsKeyArn],
    }),

    // CloudWatch Logs
    new iam.PolicyStatement({
      sid: 'WriteCloudWatchLogs',
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [
        `arn:aws:logs:${region}:*:log-group:/aws/bedrock/knowledgebases/*`,
      ],
    }),
  ];

  // S3 write access for vectors bucket - REMOVED (Phase 2)
  // Regular S3 vectors bucket no longer used, Bedrock uses AWS::S3Vectors instead
  if (vectorsBucketArn) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'WriteVectorsBucket',
        effect: iam.Effect.ALLOW,
        actions: [
          's3:PutObject',
          's3:DeleteObject',
          's3:GetObject',
          's3:ListBucket',
        ],
        resources: [vectorsBucketArn, `${vectorsBucketArn}/*`],
      })
    );
  }

  // S3 Vectors access (all vector indices in the bucket)
  if (accountId && vectorsBucketName) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'ManageS3Vectors',
        effect: iam.Effect.ALLOW,
        actions: [
          's3vectors:CreateIndex',
          's3vectors:DeleteIndex',
          's3vectors:DescribeIndex',
          's3vectors:UpdateIndex',
          's3vectors:QueryVectors',
          's3vectors:PutVectors',
          's3vectors:DeleteVectors',
          's3vectors:GetVectors',
        ],
        resources: [
          `arn:aws:s3vectors:${region}:${accountId}:bucket/${vectorsBucketName}/index/*`,
        ],
      })
    );
  }

  return new iam.PolicyDocument({ statements });
}

/**
 * Lambda Document Processor IAM Policy
 */
export function getLambdaOCRProcessorPolicy(
  docsBucketArn: string,
  sqsQueueArn: string | undefined, // Made optional (Phase 2) - OCR doesn't use SQS
  kmsKeyArn: string,
  region: string
): iam.PolicyDocument {
  const statements = [
    // S3 read/write access
    new iam.PolicyStatement({
      sid: 'AccessDocumentsBucket',
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:GetObjectVersion',
        's3:PutObject',  // Allow writing processed text back to S3
      ],
      resources: [`${docsBucketArn}/*`],
    }),

    // Textract access
    new iam.PolicyStatement({
      sid: 'StartTextractJobs',
      effect: iam.Effect.ALLOW,
      actions: [
        'textract:StartDocumentTextDetection',
        'textract:StartDocumentAnalysis',
        'textract:GetDocumentTextDetection',
        'textract:GetDocumentAnalysis',
      ],
      resources: ['*'],
    }),
  ];

  // SQS send message - REMOVED (Phase 2)
  // OCR processor doesn't send messages to SQS
  if (sqsQueueArn) {
    statements.push(
      new iam.PolicyStatement({
        sid: 'SendToSQSQueue',
        effect: iam.Effect.ALLOW,
        actions: ['sqs:SendMessage', 'sqs:GetQueueAttributes'],
        resources: [sqsQueueArn],
      })
    );
  }

  statements.push(
    // KMS encrypt/decrypt (for S3 objects)
    new iam.PolicyStatement({
      sid: 'EncryptDecryptWithKMS',
      effect: iam.Effect.ALLOW,
      actions: [
        'kms:Decrypt',
        'kms:Encrypt',
        'kms:GenerateDataKey',  // Required for PutObject with KMS
        'kms:DescribeKey',
      ],
      resources: [kmsKeyArn],
    }),

    // CloudWatch Logs
    new iam.PolicyStatement({
      sid: 'WriteCloudWatchLogs',
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [
        `arn:aws:logs:${region}:*:log-group:/aws/lambda/*`,
      ],
    }),

    // X-Ray tracing
    new iam.PolicyStatement({
      sid: 'WriteXRayTraces',
      effect: iam.Effect.ALLOW,
      actions: [
        'xray:PutTraceSegments',
        'xray:PutTelemetryRecords',
      ],
      resources: ['*'],
    })
  );

  return new iam.PolicyDocument({ statements });
}

/**
 * Lambda Embedder IAM Policy
 */
export function getLambdaEmbedderPolicy(
  vectorsBucketArn: string,
  sqsQueueArn: string,
  kmsKeyArn: string,
  region: string
): iam.PolicyDocument {
  return new iam.PolicyDocument({
    statements: [
      // Bedrock model access
      new iam.PolicyStatement({
        sid: 'InvokeTitanEmbeddings',
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`,
        ],
      }),

      // S3 write access
      new iam.PolicyStatement({
        sid: 'WriteVectorsBucket',
        effect: iam.Effect.ALLOW,
        actions: ['s3:PutObject'],
        resources: [`${vectorsBucketArn}/*`],
      }),

      // SQS receive and delete
      new iam.PolicyStatement({
        sid: 'ReceiveFromSQSQueue',
        effect: iam.Effect.ALLOW,
        actions: [
          'sqs:ReceiveMessage',
          'sqs:DeleteMessage',
          'sqs:GetQueueAttributes',
          'sqs:ChangeMessageVisibility',
        ],
        resources: [sqsQueueArn],
      }),

      // KMS encrypt (for S3 objects)
      new iam.PolicyStatement({
        sid: 'EncryptWithKMS',
        effect: iam.Effect.ALLOW,
        actions: ['kms:Encrypt', 'kms:GenerateDataKey', 'kms:DescribeKey'],
        resources: [kmsKeyArn],
      }),

      // CloudWatch Logs
      new iam.PolicyStatement({
        sid: 'WriteCloudWatchLogs',
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: [
          `arn:aws:logs:${region}:*:log-group:/aws/lambda/*`,
        ],
      }),

      // X-Ray tracing
      new iam.PolicyStatement({
        sid: 'WriteXRayTraces',
        effect: iam.Effect.ALLOW,
        actions: [
          'xray:PutTraceSegments',
          'xray:PutTelemetryRecords',
        ],
        resources: ['*'],
      }),
    ],
  });
}

/**
 * Textract SNS Topic Policy
 */
export function getTextractSNSPolicy(accountId: string): iam.PolicyStatement[] {
  return [
    new iam.PolicyStatement({
      sid: 'AllowTextractPublish',
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('textract.amazonaws.com')],
      actions: ['sns:Publish'],
      resources: ['*'],
      conditions: {
        StringEquals: {
          'aws:SourceAccount': accountId,
        },
      },
    }),
  ];
}

/**
 * Guardrails Configuration
 */
export interface GuardrailConfig {
  name: string;
  description: string;
  blockedInputMessaging: string;
  blockedOutputMessaging: string;
  contentPolicyConfig: {
    filtersConfig: Array<{
      type: string;
      inputStrength: string;
      outputStrength: string;
    }>;
  };
  sensitiveInformationPolicyConfig: {
    piiEntitiesConfig: Array<{
      type: string;
      action: string;
    }>;
    regexesConfig: Array<{
      name: string;
      description: string;
      pattern: string;
      action: string;
    }>;
  };
  topicPolicyConfig: {
    topicsConfig: Array<{
      name: string;
      definition: string;
      examples: string[];
      type: string;
    }>;
  };
  wordPolicyConfig?: {
    wordsConfig: Array<{
      text: string;
    }>;
    managedWordListsConfig: Array<{
      type: string;
    }>;
  };
}

/**
 * Get Guardrails Configuration
 */
export function getGuardrailConfig(): GuardrailConfig {
  return {
    name: GuardrailsConfig.name,
    description: GuardrailsConfig.description,
    blockedInputMessaging:
      'Your request contains sensitive information that cannot be processed. Please remove any personal or confidential information and try again.',
    blockedOutputMessaging:
      'I cannot provide that information as it may contain sensitive data.',

    // Content filters
    contentPolicyConfig: {
      filtersConfig: [
        {
          type: 'SEXUAL',
          inputStrength: GuardrailsConfig.contentFilters.sexual,
          outputStrength: GuardrailsConfig.contentFilters.sexual,
        },
        {
          type: 'VIOLENCE',
          inputStrength: GuardrailsConfig.contentFilters.violence,
          outputStrength: GuardrailsConfig.contentFilters.violence,
        },
        {
          type: 'HATE',
          inputStrength: GuardrailsConfig.contentFilters.hate,
          outputStrength: GuardrailsConfig.contentFilters.hate,
        },
        {
          type: 'INSULTS',
          inputStrength: GuardrailsConfig.contentFilters.insults,
          outputStrength: GuardrailsConfig.contentFilters.insults,
        },
        {
          type: 'MISCONDUCT',
          inputStrength: GuardrailsConfig.contentFilters.misconduct,
          outputStrength: GuardrailsConfig.contentFilters.misconduct,
        },
        {
          type: 'PROMPT_ATTACK',
          inputStrength: GuardrailsConfig.contentFilters.promptAttack,
          outputStrength: 'NONE', // Bedrock requirement: PROMPT_ATTACK output must be NONE
        },
      ],
    },

    // PII detection
    sensitiveInformationPolicyConfig: {
      piiEntitiesConfig: GuardrailsConfig.piiEntities.map((entity) => ({
        type: entity,
        action: 'BLOCK',
      })),
      regexesConfig: GuardrailsConfig.regexPatterns.map((pattern) => ({
        name: pattern.name,
        description: `Detect ${pattern.name} pattern`,
        pattern: pattern.pattern,
        action: pattern.action,
      })),
    },

    // Blocked topics
    topicPolicyConfig: {
      topicsConfig: GuardrailsConfig.blockedTopics.map((topic) => ({
        name: topic.replace(/\s+/g, '_'),
        definition: `Block discussions about ${topic.toLowerCase()}`,
        examples: [`Provide ${topic.toLowerCase()}`, `What is ${topic.toLowerCase()}`],
        type: 'DENY',
      })),
    },
  };
}

/**
 * VPC Endpoint Policy for S3
 */
export function getS3VPCEndpointPolicy(): iam.PolicyDocument {
  return new iam.PolicyDocument({
    statements: [
      new iam.PolicyStatement({
        sid: 'AllowS3Access',
        effect: iam.Effect.ALLOW,
        principals: [new iam.AnyPrincipal()],
        actions: [
          's3:GetObject',
          's3:PutObject',
          's3:ListBucket',
          's3:DeleteObject',
        ],
        resources: ['*'],
      }),
    ],
  });
}

/**
 * CloudFormation Custom Resource Execution Role Policy
 */
export function getCustomResourcePolicy(region: string): iam.PolicyDocument {
  return new iam.PolicyDocument({
    statements: [
      // Bedrock Knowledge Base and Guardrail operations
      new iam.PolicyStatement({
        sid: 'ManageBedrockKnowledgeBase',
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:CreateKnowledgeBase',
          'bedrock:GetKnowledgeBase',
          'bedrock:UpdateKnowledgeBase',
          'bedrock:DeleteKnowledgeBase',
          'bedrock:CreateDataSource',
          'bedrock:GetDataSource',
          'bedrock:UpdateDataSource',
          'bedrock:DeleteDataSource',
          'bedrock:CreateGuardrail',
          'bedrock:GetGuardrail',
          'bedrock:UpdateGuardrail',
          'bedrock:DeleteGuardrail',
          'bedrock:CreateGuardrailVersion',  // Added: Required for versioning
          'bedrock:GetGuardrailVersion',
          'bedrock:DeleteGuardrailVersion',
        ],
        resources: ['*'],
      }),

      // IAM pass role
      new iam.PolicyStatement({
        sid: 'PassRoleToBedrockKB',
        effect: iam.Effect.ALLOW,
        actions: ['iam:PassRole'],
        resources: ['*'],
        conditions: {
          StringEquals: {
            'iam:PassedToService': 'bedrock.amazonaws.com',
          },
        },
      }),

      // CloudWatch Logs
      new iam.PolicyStatement({
        sid: 'WriteCloudWatchLogs',
        effect: iam.Effect.ALLOW,
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        resources: [
          `arn:aws:logs:${region}:*:log-group:/aws/lambda/*`,
        ],
      }),
    ],
  });
}
