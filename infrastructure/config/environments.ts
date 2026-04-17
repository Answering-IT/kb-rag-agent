/**
 * Environment configuration for ProcessApp RAG Infrastructure
 * Defines account settings, regions, and deployment parameters
 */

export interface SDLCAccount {
  id: string;
  stage: string;
  profile: string;
}

/**
 * AWS Account Configuration
 * Add additional accounts (staging, prod) as needed
 */
export const SDLCAccounts: SDLCAccount[] = [
  {
    id: '708819485463',
    stage: 'dev',
    profile: 'default',
  },
];

/**
 * Target regions for deployment
 * Phase 1: Single region (us-east-1)
 * Future: Add 'us-east-2', 'us-west-2' for multi-region
 */
export const TargetRegions: string[] = ['us-east-1'];

/**
 * Global resource region
 * S3 buckets and global IAM roles created here
 */
export const GlobalResourceRegion = 'us-east-1';

/**
 * Bedrock Model Configuration
 */
export const BedrockConfig = {
  // Embedding model for vector generation
  embeddingModel: 'amazon.titan-embed-text-v2:0',
  embeddingDimensions: 1536,

  // LLM model for RAG queries
  llmModel: 'anthropic.claude-sonnet-3-5-v2:0',

  // Storage optimization (reduces costs by ~50%)
  storageOptimization: true,
};

/**
 * S3 Configuration
 */
export const S3Config = {
  // Document bucket configuration
  docsBucket: {
    prefix: 'processapp-docs-v2',
    versioningEnabled: true,
    lifecycleRules: {
      archiveAfterDays: 90,
      deleteAfterDays: 365,
    },
  },

  // Vector storage bucket configuration (regular S3 bucket - deprecated)
  vectorsBucket: {
    prefix: 'processapp-vectors-v2',
    intelligentTiering: true,
    lifecycleRules: {
      archiveAfterDays: 90,
      deleteAfterDays: 365,
    },
  },

  // S3 Vector Bucket configuration (for Bedrock KB S3_VECTORS storage)
  s3VectorBucket: {
    prefix: 'processapp-vectors',
  },

  // Document patterns
  includePatterns: ['**/*.pdf', '**/*.docx', '**/*.txt'],
  excludePatterns: ['**/temp/**', '**/.git/**', '**/node_modules/**'],
};

/**
 * Document Processing Configuration
 */
export const ProcessingConfig = {
  // Chunking strategy
  chunking: {
    strategy: 'FIXED_SIZE',
    maxTokens: 512,
    overlapPercentage: 20,
  },

  // Lambda configuration
  lambda: {
    ocrProcessor: {
      memoryMB: 1024,
      timeoutSeconds: 300, // 5 minutes
      runtime: 'python3.11',
    },
    embedder: {
      memoryMB: 512,
      timeoutSeconds: 60,
      runtime: 'python3.11',
    },
    kbCreator: {
      memoryMB: 256,
      timeoutSeconds: 300,
      runtime: 'python3.11',
    },
  },

  // SQS configuration
  sqs: {
    visibilityTimeoutSeconds: 360, // 6 minutes
    retentionPeriodSeconds: 1209600, // 14 days
    maxReceiveCount: 3,
  },

  // Textract configuration
  textract: {
    featureTypes: ['TABLES', 'FORMS'],
    outputFormat: 'JSON',
  },
};

/**
 * Knowledge Base Configuration
 */
export const KnowledgeBaseConfig = {
  name: 'processapp-kb',
  description: 'ProcessApp document knowledge base for RAG',

  // Sync schedule (every 6 hours)
  syncSchedule: 'rate(6 hours)',

  // Search configuration
  search: {
    numberOfResults: 5,
    overrideSearchType: 'HYBRID', // SEMANTIC, HYBRID
  },
};

/**
 * Guardrails Configuration
 */
export const GuardrailsConfig = {
  name: 'processapp-pii-filter',
  description: 'Filter PII and sensitive information',

  // PII entities to detect and block
  piiEntities: [
    'EMAIL',
    'PHONE',
    'SSN',
    'CREDIT_CARD',
    'PERSON',
    'ORGANIZATION',
    'ADDRESS',
    'DATE_OF_BIRTH',
  ],

  // Regex patterns
  regexPatterns: [
    {
      name: 'SSN',
      pattern: '\\d{3}-\\d{2}-\\d{4}',
      action: 'BLOCK',
    },
    {
      name: 'Email',
      pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
      action: 'BLOCK',
    },
  ],

  // Content filters
  contentFilters: {
    sexual: 'HIGH',
    violence: 'HIGH',
    hate: 'HIGH',
    insults: 'MEDIUM',
    misconduct: 'MEDIUM',
    promptAttack: 'HIGH',
  },

  // Topics to block
  blockedTopics: [
    'Financial advice',
    'Medical diagnosis',
    'Legal advice',
  ],
};

/**
 * Monitoring Configuration
 */
export const MonitoringConfig = {
  // CloudWatch Logs retention
  logRetentionDays: 30,

  // Alarms
  alarms: {
    lambdaErrorThreshold: 5, // percentage
    kbQueryLatencyThreshold: 2000, // milliseconds
    costBudgetPercentage: 80, // alert at 80% of budget
  },

  // Metrics
  metrics: {
    namespace: 'ProcessApp/RAG',
    enabled: true,
  },

  // X-Ray tracing
  xray: {
    enabled: true,
    samplingRate: 0.1, // 10% of requests
  },
};

/**
 * Cost Configuration
 */
export const CostConfig = {
  // Monthly budget by environment
  budgets: {
    dev: 50, // USD
    staging: 100,
    prod: 200,
  },

  // Cost allocation tags
  tags: {
    Application: 'processapp',
    Component: 'rag-infrastructure',
    ManagedBy: 'cdk',
  },
};

/**
 * Security Configuration
 */
export const SecurityConfig = {
  // KMS key rotation
  kmsKeyRotation: true,

  // S3 encryption
  s3Encryption: 'KMS', // 'KMS' or 'AES256'

  // VPC endpoints
  vpcEndpoints: {
    s3: false, // Disabled - no default VPC in account
    bedrock: false, // Not available in all regions
  },

  // IAM
  enforceIMDSv2: true,
  requireMFA: false, // Set to true for prod
};

/**
 * Feature Flags
 */
export const FeatureFlags = {
  // Enable Bedrock Agent integration
  enableBedrockAgent: false,

  // Enable cross-region replication
  enableCrossRegionReplication: false,

  // Enable enhanced monitoring
  enableEnhancedMonitoring: true,

  // Enable data quality checks
  enableDataQualityChecks: false,
};

/**
 * Helper function to get bucket name
 */
export function getBucketName(prefix: string, stage: string, accountId: string): string {
  return `${prefix}-${stage}-${accountId}`;
}

/**
 * Helper function to get stack name
 */
export function getStackName(baseName: string, stage: string, region: string): string {
  return `${baseName}-${stage}-${region}`;
}

/**
 * Helper function to check if region is global resource region
 */
export function isGlobalResourceRegion(region: string): boolean {
  return region === GlobalResourceRegion;
}

/**
 * Helper function to get cost allocation tags
 */
export function getCostAllocationTags(stage: string, additionalTags?: Record<string, string>): Record<string, string> {
  return {
    ...CostConfig.tags,
    Environment: stage,
    ...additionalTags,
  };
}
