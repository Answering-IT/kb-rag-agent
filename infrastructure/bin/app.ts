#!/usr/bin/env node

/**
 * Main CDK App Entry Point
 * Simplified deployment - creates all stacks in a single stage per account/region
 */

import * as cdk from 'aws-cdk-lib';
import {
  SDLCAccounts,
  TargetRegions,
  GlobalResourceRegion,
  isGlobalResourceRegion,
  getCostAllocationTags,
} from '../config/environments';
import { PrereqsStack } from '../lib/PrereqsStack';
import { SecurityStack } from '../lib/SecurityStack';
import { BedrockStack } from '../lib/BedrockStack';
import { DocumentProcessingStack } from '../lib/DocumentProcessingStack';
import { GuardrailsStack } from '../lib/GuardrailsStack';
import { MonitoringStack } from '../lib/MonitoringStack';
import { AgentStackV2 } from '../lib/AgentStackV2';
import { WebSocketStackV2 } from '../lib/WebSocketStackV2';
import { BedrockStreamApiStack } from '../lib/BedrockStreamApiStack';
// import { StreamingAPIStack } from '../lib/StreamingAPIStack'; // Commented out - using WebSocket instead

/**
 * Main App
 */
const app = new cdk.App();

// Deploy to all accounts and regions
SDLCAccounts.forEach((account) => {
  TargetRegions.forEach((region) => {
    const env = {
      account: account.id,
      region: region,
    };

    // Create PrereqsStack ONLY in GlobalResourceRegion
    if (isGlobalResourceRegion(region)) {
      // Creating global resources for this stage

      // Global resources (S3 buckets, IAM roles)
      const prereqsStack = new PrereqsStack(
        app,
        `${account.stage}-${region}-prereqs`,
        {
          stage: account.stage,
          accountId: account.id,
          env,
          ...getCostAllocationTags(account.stage),
        }
      );

      // Regional resources
      const securityStack = new SecurityStack(
        app,
        `${account.stage}-${region}-security`,
        {
          stage: account.stage,
          accountId: account.id,
          docsBucket: prereqsStack.docsBucket,
          bedrockKBRole: prereqsStack.bedrockKBRole,
          kmsKey: prereqsStack.kmsKey,
          env,
        }
      );
      securityStack.addDependency(prereqsStack);

      const bedrockStack = new BedrockStack(
        app,
        `${account.stage}-${region}-bedrock`,
        {
          stage: account.stage,
          accountId: account.id,
          docsBucket: prereqsStack.docsBucket,
          bedrockKBRole: prereqsStack.bedrockKBRole,
          kmsKey: prereqsStack.kmsKey,
          env,
        }
      );
      bedrockStack.addDependency(securityStack);

      const docProcessingStack = new DocumentProcessingStack(
        app,
        `${account.stage}-${region}-document-processing`,
        {
          stage: account.stage,
          accountId: account.id,
          docsBucket: prereqsStack.docsBucket,
          kmsKey: prereqsStack.kmsKey,
          env,
        }
      );
      docProcessingStack.addDependency(securityStack);

      const guardrailsStack = new GuardrailsStack(
        app,
        `${account.stage}-${region}-guardrails`,
        {
          stage: account.stage,
          accountId: account.id,
          env,
        }
      );

      // ========================================
      // AGENT V2 (Agent Core Runtime with Strand SDK)
      // ========================================

      const agentStackV2 = new AgentStackV2(
        app,
        `${account.stage}-${region}-agent-v2`,
        {
          stage: account.stage,
          accountId: account.id,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          env,
        }
      );
      agentStackV2.addDependency(bedrockStack);

      // WebSocket API for Agent Core Runtime V2
      const webSocketStackV2 = new WebSocketStackV2(
        app,
        `${account.stage}-${region}-websocket-v2`,
        {
          stage: account.stage,
          accountId: account.id,
          runtimeId: agentStackV2.runtimeId,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          env,
        }
      );
      webSocketStackV2.addDependency(agentStackV2);

      // REST Streaming API for Agent Core Runtime V2
      const bedrockStreamApiStack = new BedrockStreamApiStack(
        app,
        `${account.stage}-${region}-bedrock-stream-api`,
        {
          stage: account.stage,
          accountId: account.id,
          runtimeId: agentStackV2.runtimeId,
          memoryId: agentStackV2.memoryId,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          env,
        }
      );
      bedrockStreamApiStack.addDependency(agentStackV2);

      // Streaming API for Agent Core Runtime V2 (REST with streaming)
      // COMMENTED OUT - Using WebSocket instead for now
      /*
      const streamingAPIStack = new StreamingAPIStack(
        app,
        `${account.stage}-${region}-streaming-api`,
        {
          stage: account.stage,
          accountId: account.id,
          runtimeId: agentStackV2.runtimeId,
          memoryId: agentStackV2.memoryId,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          runtimeEndpointUrl: agentStackV2.endpointUrl,
          env,
        }
      );
      streamingAPIStack.addDependency(agentStackV2);
      */

      const monitoringStack = new MonitoringStack(
        app,
        `${account.stage}-${region}-monitoring`,
        {
          stage: account.stage,
          accountId: account.id,
          ocrProcessor: docProcessingStack.ocrProcessor,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          env,
        }
      );
      monitoringStack.addDependency(bedrockStack);
      monitoringStack.addDependency(docProcessingStack);

      // Apply tags to all stacks
      Object.entries(getCostAllocationTags(account.stage)).forEach(([key, value]) => {
        cdk.Tags.of(prereqsStack).add(key, value);
        cdk.Tags.of(securityStack).add(key, value);
        cdk.Tags.of(bedrockStack).add(key, value);
        cdk.Tags.of(docProcessingStack).add(key, value);
        cdk.Tags.of(guardrailsStack).add(key, value);
        cdk.Tags.of(agentStackV2).add(key, value);
        cdk.Tags.of(webSocketStackV2).add(key, value);
        cdk.Tags.of(bedrockStreamApiStack).add(key, value);
        cdk.Tags.of(monitoringStack).add(key, value);
      });
    }
  });
});

// Synthesize
app.synth();
