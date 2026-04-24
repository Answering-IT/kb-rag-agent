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
import { AgentStack } from '../lib/AgentStack';
import { APIStack } from '../lib/APIStack';

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
      console.log(`Creating global resources in ${region} for stage ${account.stage}`);

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
          // vectorsBucket: prereqsStack.vectorsBucket, // REMOVED (Phase 2)
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
          // vectorsBucket: prereqsStack.vectorsBucket, // REMOVED (Phase 2) - BedrockStack creates own AWS::S3Vectors bucket
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
          // vectorsBucket: prereqsStack.vectorsBucket, // REMOVED (Phase 2) - only used by Embedder (Phase 3)
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

      const agentStack = new AgentStack(
        app,
        `${account.stage}-${region}-agent`,
        {
          stage: account.stage,
          accountId: account.id,
          knowledgeBaseId: bedrockStack.knowledgeBaseId,
          guardrailId: guardrailsStack.guardrailId,
          guardrailVersion: guardrailsStack.guardrailVersion,
          env,
        }
      );
      agentStack.addDependency(bedrockStack);
      agentStack.addDependency(guardrailsStack);

      const apiStack = new APIStack(
        app,
        `${account.stage}-${region}-api`,
        {
          stage: account.stage,
          accountId: account.id,
          agentId: agentStack.agentId,
          agentAliasId: agentStack.agentAliasId,
          env,
        }
      );
      apiStack.addDependency(agentStack);

      const monitoringStack = new MonitoringStack(
        app,
        `${account.stage}-${region}-monitoring`,
        {
          stage: account.stage,
          accountId: account.id,
          ocrProcessor: docProcessingStack.ocrProcessor,
          // embedder: docProcessingStack.embedder, // REMOVED (Phase 2)
          // chunksQueue: docProcessingStack.chunksQueue, // REMOVED (Phase 2)
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
        cdk.Tags.of(agentStack).add(key, value);
        cdk.Tags.of(apiStack).add(key, value);
        cdk.Tags.of(monitoringStack).add(key, value);
      });
    } else {
      console.log(`Skipping ${region} - not the global resource region`);
      console.warn(
        `Multi-region deployment not fully implemented. Deploy to ${GlobalResourceRegion} first.`
      );
    }
  });
});

// Synthesize
app.synth();
