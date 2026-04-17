/**
 * Bedrock-specific configuration for Knowledge Base and Data Sources
 */

import { BedrockConfig, ProcessingConfig, KnowledgeBaseConfig, S3Config } from './environments';

/**
 * Knowledge Base Storage Configuration
 */
export interface KnowledgeBaseStorageConfig {
  type: 'S3';
  s3Configuration: {
    bucketArn: string;
  };
}

/**
 * Embedding Model Configuration
 */
export interface EmbeddingModelConfig {
  modelArn: string;
  dimensions: number;
  storageOptimization: boolean;
}

/**
 * Chunking Configuration
 */
export interface ChunkingConfig {
  chunkingStrategy: 'FIXED_SIZE_CHUNKING' | 'SEMANTIC_CHUNKING' | 'NONE';
  fixedSizeChunkingConfiguration?: {
    maxTokens: number;
    overlapPercentage: number;
  };
  semanticChunkingConfiguration?: {
    maxTokens: number;
    bufferSize: number;
    breakpointPercentileThreshold: number;
  };
}

/**
 * Parsing Configuration
 */
export interface ParsingConfig {
  parsingStrategy: 'BEDROCK_FOUNDATION_MODEL';
  bedrockFoundationModelConfiguration: {
    modelArn: string;
    parsingPrompt?: string;
  };
}

/**
 * Data Source Configuration
 */
export interface DataSourceConfig {
  name: string;
  description: string;
  dataSourceConfiguration: {
    type: 'S3';
    s3Configuration: {
      bucketArn: string;
      inclusionPrefixes?: string[];
    };
  };
  vectorIngestionConfiguration: {
    chunkingConfiguration: ChunkingConfig;
    parsingConfiguration?: ParsingConfig;
  };
}

/**
 * Get Embedding Model Configuration
 */
export function getEmbeddingModelConfig(region: string): EmbeddingModelConfig {
  return {
    modelArn: `arn:aws:bedrock:${region}::foundation-model/${BedrockConfig.embeddingModel}`,
    dimensions: BedrockConfig.embeddingDimensions,
    storageOptimization: BedrockConfig.storageOptimization,
  };
}

/**
 * Get Knowledge Base Storage Configuration
 */
export function getKnowledgeBaseStorageConfig(vectorsBucketArn: string): KnowledgeBaseStorageConfig {
  return {
    type: 'S3',
    s3Configuration: {
      bucketArn: vectorsBucketArn,
    },
  };
}

/**
 * Get Chunking Configuration
 */
export function getChunkingConfig(): ChunkingConfig {
  if (ProcessingConfig.chunking.strategy === 'FIXED_SIZE') {
    return {
      chunkingStrategy: 'FIXED_SIZE_CHUNKING',
      fixedSizeChunkingConfiguration: {
        maxTokens: ProcessingConfig.chunking.maxTokens,
        overlapPercentage: ProcessingConfig.chunking.overlapPercentage,
      },
    };
  }

  // Default to fixed size chunking
  return {
    chunkingStrategy: 'FIXED_SIZE_CHUNKING',
    fixedSizeChunkingConfiguration: {
      maxTokens: 512,
      overlapPercentage: 20,
    },
  };
}

/**
 * Get Parsing Configuration (for Textract integration)
 */
export function getParsingConfig(region: string): ParsingConfig {
  return {
    parsingStrategy: 'BEDROCK_FOUNDATION_MODEL',
    bedrockFoundationModelConfiguration: {
      modelArn: `arn:aws:bedrock:${region}::foundation-model/${BedrockConfig.llmModel}`,
      parsingPrompt: `Extract all text content from this document.
Preserve the document structure, including:
- Headings and sections
- Tables and their contents
- Lists (numbered and bulleted)
- Key-value pairs from forms
- Image captions and alt text

Format the output as clean, structured text that preserves semantic meaning.`,
    },
  };
}

/**
 * Get Data Source Configuration
 */
export function getDataSourceConfig(
  name: string,
  docsBucketArn: string,
  region: string
): DataSourceConfig {
  return {
    name,
    description: `Data source for ${name} - scans S3 bucket for documents`,
    dataSourceConfiguration: {
      type: 'S3',
      s3Configuration: {
        bucketArn: docsBucketArn,
        inclusionPrefixes: ['documents/'], // Optional: limit to specific prefixes
      },
    },
    vectorIngestionConfiguration: {
      chunkingConfiguration: getChunkingConfig(),
      parsingConfiguration: getParsingConfig(region),
    },
  };
}

/**
 * Vector Search Configuration
 */
export interface VectorSearchConfig {
  numberOfResults: number;
  overrideSearchType?: 'HYBRID' | 'SEMANTIC';
}

/**
 * Get Vector Search Configuration
 */
export function getVectorSearchConfig(): VectorSearchConfig {
  return {
    numberOfResults: KnowledgeBaseConfig.search.numberOfResults,
    overrideSearchType: KnowledgeBaseConfig.search.overrideSearchType as 'HYBRID' | 'SEMANTIC',
  };
}

/**
 * Knowledge Base Configuration for Custom Resource
 */
export interface KnowledgeBaseConfigForCustomResource {
  name: string;
  description: string;
  roleArn: string;
  storageConfiguration: {
    type: 'OPENSEARCH_SERVERLESS' | 'PINECONE' | 'REDIS_ENTERPRISE_CLOUD' | 'RDS' | 'MONGO_DB_ATLAS';
    opensearchServerlessConfiguration?: {
      collectionArn: string;
      vectorIndexName: string;
      fieldMapping: {
        vectorField: string;
        textField: string;
        metadataField: string;
      };
    };
  };
  knowledgeBaseConfiguration: {
    type: 'VECTOR';
    vectorKnowledgeBaseConfiguration: {
      embeddingModelArn: string;
      embeddingModelConfiguration?: {
        bedrockEmbeddingModelConfiguration?: {
          dimensions?: number;
        };
      };
    };
  };
}

/**
 * Data Source Configuration for Custom Resource
 */
export interface DataSourceConfigForCustomResource {
  name: string;
  description: string;
  knowledgeBaseId: string;
  dataSourceConfiguration: {
    type: 'S3';
    s3Configuration: {
      bucketArn: string;
      inclusionPrefixes?: string[];
    };
  };
  vectorIngestionConfiguration: {
    chunkingConfiguration: {
      chunkingStrategy: string;
      fixedSizeChunkingConfiguration?: {
        maxTokens: number;
        overlapPercentage: number;
      };
    };
  };
}

/**
 * Bedrock Agent Configuration (optional)
 */
export interface BedrockAgentConfig {
  agentName: string;
  foundationModel: string;
  instruction: string;
  idleSessionTTLInSeconds: number;
  knowledgeBases: Array<{
    knowledgeBaseId: string;
    description: string;
  }>;
  actionGroups?: Array<{
    actionGroupName: string;
    description: string;
    apiSchema: any;
  }>;
}

/**
 * Get Bedrock Agent Configuration (if enabled)
 */
export function getBedrockAgentConfig(
  agentName: string,
  knowledgeBaseId: string,
  region: string
): BedrockAgentConfig {
  return {
    agentName,
    foundationModel: BedrockConfig.llmModel,
    instruction: `You are a helpful document analysis copilot for ProcessApp.
You have access to a knowledge base containing various documents.
When answering questions:
1. Search the knowledge base for relevant information
2. Provide accurate answers with source citations
3. If information is not found, clearly state that
4. Never make up information not present in the documents
5. Be concise and professional in your responses`,
    idleSessionTTLInSeconds: 600, // 10 minutes
    knowledgeBases: [
      {
        knowledgeBaseId,
        description: 'Document knowledge base for ProcessApp',
      },
    ],
  };
}

/**
 * Model Permissions
 */
export interface BedrockModelPermissions {
  embeddingModel: string;
  llmModel: string;
  parsingModel: string;
}

/**
 * Get required Bedrock model permissions
 */
export function getRequiredModelPermissions(): BedrockModelPermissions {
  return {
    embeddingModel: BedrockConfig.embeddingModel,
    llmModel: BedrockConfig.llmModel,
    parsingModel: BedrockConfig.llmModel, // Same as LLM for parsing
  };
}

/**
 * Get Bedrock model ARNs for IAM policies
 */
export function getBedrockModelArns(region: string): string[] {
  const permissions = getRequiredModelPermissions();
  return [
    `arn:aws:bedrock:${region}::foundation-model/${permissions.embeddingModel}`,
    `arn:aws:bedrock:${region}::foundation-model/${permissions.llmModel}`,
  ];
}
