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
    profile: 'ans-super',
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

  // LLM model for RAG queries (using available Claude Sonnet 4.5)
  llmModel: 'anthropic.claude-sonnet-4-5-20250929-v1:0',

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
    maxTokens: 2000,       // Increased from 512 to reduce chunk count (fewer chunks = less metadata overhead)
    overlapPercentage: 10, // Reduced from 20 to minimize redundancy
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
  // Using valid Bedrock Guardrail PII entity types
  piiEntities: [
    'EMAIL',
    'PHONE',
    'US_SOCIAL_SECURITY_NUMBER', // Was: SSN
    'CREDIT_DEBIT_CARD_NUMBER',  // Was: CREDIT_CARD
    'NAME',                       // Was: PERSON
    'ADDRESS',
    'US_PASSPORT_NUMBER',
    'US_BANK_ACCOUNT_NUMBER',
    'AGE',
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
  // Note: promptAttack can only filter INPUT, not OUTPUT (Bedrock requirement)
  contentFilters: {
    sexual: 'HIGH',
    violence: 'HIGH',
    hate: 'HIGH',
    insults: 'MEDIUM',
    misconduct: 'MEDIUM',
    promptAttack: 'HIGH', // Only applies to input; output is automatically NONE
  },

  // Topics to block
  blockedTopics: [
    'Financial advice',
    'Medical diagnosis',
    'Legal advice',
  ],
};

/**
 * Bedrock Agent Configuration
 */
export const AgentConfig = {
  name: 'processapp-agent',
  description: 'ProcessApp RAG Agent - answers questions using document knowledge base',

  // System instructions for the agent
  instructions: `You are ProcessApp, a helpful AI assistant with access to a comprehensive document knowledge base.

Your capabilities:
- Search and retrieve information from uploaded documents
- Answer questions based on document content
- Provide accurate citations and sources
- Handle technical documentation and business content

Guidelines for responses:
1. Always search the knowledge base before answering
2. Provide accurate answers with source citations when available
3. If information is not found in the documents, clearly state that
4. Never make up information or hallucinate facts
5. Be concise and professional in your responses
6. When relevant, provide specific document references
7. If a question is ambiguous, ask for clarification

Content Safety:
- PII and sensitive information is automatically filtered
- You have guardrails for content safety and appropriateness
- If you detect harmful or inappropriate requests, politely decline

Remember: Your knowledge comes from the documents in the knowledge base. Always ground your responses in the actual content available.`,

  // Foundation model (using Amazon Nova Pro - available without marketplace subscription)
  foundationModel: 'amazon.nova-pro-v1:0',

  // Session configuration
  idleSessionTTL: 900, // 15 minutes

  // Model parameters
  inference: {
    maxTokens: 4096,
    temperature: 0.7,
    topP: 0.9,
    stopSequences: [],
  },

  // Action groups configuration
  actionGroups: [
    {
      name: 'QueryKnowledgeBase',
      description: 'Search and retrieve information from the ProcessApp Knowledge Base',
      enabled: true,
    },
  ],

  // Prompt override configuration (optional)
  promptOverride: {
    enabled: false,
    // Custom prompt template if needed
  },
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

/**
 * Multi-Tenant Configuration
 */
export const MultiTenantConfig = {
  enableMetadataFiltering: true,
  filteringOrder: ['tenantId', 'roles', 'projectId', 'users'],
  denyByDefault: true,
  headerNames: {
    tenantId: 'X-Tenant-Id',
    userId: 'X-User-Id',
    userRoles: 'X-User-Roles',
  },
  sessionMemoryTtlDays: 90,
  metadataSource: 's3-metadata', // Read metadata from S3 object metadata (x-amz-meta-*)
};

/**
 * Agent Tools Configuration
 */
export const AgentToolsConfig = {
  tools: [
    {
      name: 'GetProjectInfo',
      type: 'HTTP',
      baseUrl: 'https://dev.app.colpensiones.procesapp.com',
      endpoint: 'GET /organization/{orgId}/projects/{projectId}',
      description: 'Retrieve project information',
      enabled: true,
    },
  ],
};

/**
 * Streaming Configuration
 */
export const StreamingConfig = {
  enabled: false, // Enable in future iteration
  type: 'websocket',
  chunkTimeoutMs: 100,
};
