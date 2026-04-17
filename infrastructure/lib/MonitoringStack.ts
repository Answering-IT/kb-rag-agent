/**
 * MonitoringStack - Observability and cost tracking
 *
 * Creates:
 * - CloudWatch dashboards
 * - Custom metrics
 * - Alarms (error rates, latency, costs)
 * - X-Ray tracing configuration
 * - Budget alerts
 */

import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as budgets from 'aws-cdk-lib/aws-budgets';
import { Construct } from 'constructs';
import { MonitoringConfig, CostConfig } from '../config/environments';

export interface MonitoringStackProps extends cdk.StackProps {
  stage: string;
  accountId: string;
  ocrProcessor?: lambda.IFunction;
  embedder?: lambda.IFunction;
  chunksQueue?: sqs.IQueue;
  knowledgeBaseId?: string;
}

export class MonitoringStack extends cdk.Stack {
  public readonly alarmTopic: sns.Topic;
  public readonly dashboard: cloudwatch.Dashboard;

  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // Apply cost allocation tags
    cdk.Tags.of(this).add('Environment', props.stage);
    cdk.Tags.of(this).add('Application', 'processapp');
    cdk.Tags.of(this).add('Component', 'rag-monitoring');

    // ========================================
    // SNS TOPIC FOR ALARMS
    // ========================================

    this.alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: `processapp-alarms-${props.stage}`,
      displayName: 'ProcessApp RAG Alarms',
    });

    // Add email subscription (optional - configure via console or CLI)
    // this.alarmTopic.addSubscription(
    //   new subscriptions.EmailSubscription('team@example.com')
    // );

    // ========================================
    // CLOUDWATCH DASHBOARD
    // ========================================

    this.dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: `ProcessApp-RAG-${props.stage}`,
    });

    // ========================================
    // LAMBDA METRICS & ALARMS
    // ========================================

    if (props.ocrProcessor) {
      // OCR Processor metrics
      const ocrErrors = props.ocrProcessor.metricErrors({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      const ocrDuration = props.ocrProcessor.metricDuration({
        period: cdk.Duration.minutes(5),
        statistic: 'Average',
      });

      const ocrInvocations = props.ocrProcessor.metricInvocations({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      // OCR Error alarm
      const ocrErrorAlarm = new cloudwatch.Alarm(this, 'OCRErrorAlarm', {
        alarmName: `processapp-ocr-errors-${props.stage}`,
        metric: ocrErrors,
        threshold: 5,
        evaluationPeriods: 2,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });

      ocrErrorAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

      // Add to dashboard
      this.dashboard.addWidgets(
        new cloudwatch.GraphWidget({
          title: 'OCR Processor',
          left: [ocrInvocations, ocrErrors],
          right: [ocrDuration],
        })
      );
    }

    if (props.embedder) {
      // Embedder metrics
      const embedderErrors = props.embedder.metricErrors({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      const embedderDuration = props.embedder.metricDuration({
        period: cdk.Duration.minutes(5),
        statistic: 'Average',
      });

      const embedderInvocations = props.embedder.metricInvocations({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      // Embedder error alarm
      const embedderErrorAlarm = new cloudwatch.Alarm(
        this,
        'EmbedderErrorAlarm',
        {
          alarmName: `processapp-embedder-errors-${props.stage}`,
          metric: embedderErrors,
          threshold: 5,
          evaluationPeriods: 2,
          comparisonOperator:
            cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
          treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
        }
      );

      embedderErrorAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

      // Add to dashboard
      this.dashboard.addWidgets(
        new cloudwatch.GraphWidget({
          title: 'Embedder',
          left: [embedderInvocations, embedderErrors],
          right: [embedderDuration],
        })
      );
    }

    // ========================================
    // SQS QUEUE METRICS
    // ========================================

    if (props.chunksQueue) {
      const queueDepth = props.chunksQueue.metricApproximateNumberOfMessagesVisible({
        period: cdk.Duration.minutes(5),
        statistic: 'Average',
      });

      const messagesSent = props.chunksQueue.metricNumberOfMessagesSent({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      const messagesDeleted = props.chunksQueue.metricNumberOfMessagesDeleted({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      });

      // Queue depth alarm
      const queueDepthAlarm = new cloudwatch.Alarm(this, 'QueueDepthAlarm', {
        alarmName: `processapp-queue-depth-${props.stage}`,
        metric: queueDepth,
        threshold: 1000,
        evaluationPeriods: 2,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });

      queueDepthAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

      // Add to dashboard
      this.dashboard.addWidgets(
        new cloudwatch.GraphWidget({
          title: 'Chunks Queue',
          left: [queueDepth],
          right: [messagesSent, messagesDeleted],
        })
      );
    }

    // ========================================
    // KNOWLEDGE BASE METRICS
    // ========================================

    if (props.knowledgeBaseId) {
      // Custom metrics for KB queries
      const kbQueryMetric = new cloudwatch.Metric({
        namespace: MonitoringConfig.metrics.namespace,
        metricName: 'KBQueryLatency',
        dimensionsMap: {
          KnowledgeBaseId: props.knowledgeBaseId,
          Environment: props.stage,
        },
        statistic: 'Average',
        period: cdk.Duration.minutes(5),
      });

      const kbQueryCount = new cloudwatch.Metric({
        namespace: MonitoringConfig.metrics.namespace,
        metricName: 'KBQueryCount',
        dimensionsMap: {
          KnowledgeBaseId: props.knowledgeBaseId,
          Environment: props.stage,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      // KB query latency alarm
      const kbLatencyAlarm = new cloudwatch.Alarm(this, 'KBLatencyAlarm', {
        alarmName: `processapp-kb-latency-${props.stage}`,
        metric: kbQueryMetric,
        threshold: MonitoringConfig.alarms.kbQueryLatencyThreshold,
        evaluationPeriods: 2,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });

      kbLatencyAlarm.addAlarmAction(new actions.SnsAction(this.alarmTopic));

      // Add to dashboard
      this.dashboard.addWidgets(
        new cloudwatch.GraphWidget({
          title: 'Knowledge Base',
          left: [kbQueryCount],
          right: [kbQueryMetric],
        })
      );
    }

    // ========================================
    // COST TRACKING
    // ========================================

    // Add cost widget to dashboard
    this.dashboard.addWidgets(
      new cloudwatch.SingleValueWidget({
        title: 'Estimated Monthly Cost',
        metrics: [
          new cloudwatch.Metric({
            namespace: 'AWS/Billing',
            metricName: 'EstimatedCharges',
            dimensionsMap: {
              Currency: 'USD',
            },
            statistic: 'Maximum',
            period: cdk.Duration.hours(6),
          }),
        ],
        width: 6,
        height: 3,
      })
    );

    // ========================================
    // AWS BUDGETS
    // ========================================

    const monthlyBudget =
      CostConfig.budgets[props.stage as keyof typeof CostConfig.budgets] || 50;

    new budgets.CfnBudget(this, 'MonthlyBudget', {
      budget: {
        budgetName: `processapp-${props.stage}-monthly`,
        budgetType: 'COST',
        timeUnit: 'MONTHLY',
        budgetLimit: {
          amount: monthlyBudget,
          unit: 'USD',
        },
        costFilters: {
          TagKeyValue: [
            `user:Application$processapp`,
            `user:Environment$${props.stage}`,
          ],
        },
      },
      notificationsWithSubscribers: [
        {
          notification: {
            notificationType: 'ACTUAL',
            comparisonOperator: 'GREATER_THAN',
            threshold: MonitoringConfig.alarms.costBudgetPercentage,
            thresholdType: 'PERCENTAGE',
          },
          subscribers: [
            {
              subscriptionType: 'SNS',
              address: this.alarmTopic.topicArn,
            },
          ],
        },
        {
          notification: {
            notificationType: 'FORECASTED',
            comparisonOperator: 'GREATER_THAN',
            threshold: 100,
            thresholdType: 'PERCENTAGE',
          },
          subscribers: [
            {
              subscriptionType: 'SNS',
              address: this.alarmTopic.topicArn,
            },
          ],
        },
      ],
    });

    // ========================================
    // DOCUMENT PROCESSING PIPELINE VIEW
    // ========================================

    this.dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: `# ProcessApp RAG Infrastructure - ${props.stage}

## Document Processing Pipeline
1. **Upload** → S3 documents bucket
2. **OCR** → Textract extraction
3. **Chunking** → SQS queue
4. **Embedding** → Titan v2
5. **Storage** → S3 vectors bucket
6. **Indexing** → Knowledge Base sync

## Current Status
- Environment: ${props.stage}
- Region: ${region}
- Account: ${props.accountId}

## Key Resources
- Knowledge Base ID: ${props.knowledgeBaseId || 'N/A'}
- Monthly Budget: $${monthlyBudget}
`,
        width: 24,
        height: 6,
      })
    );

    // ========================================
    // OUTPUTS
    // ========================================

    new cdk.CfnOutput(this, 'DashboardURL', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${region}#dashboards:name=${this.dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL',
      exportName: `processapp-dashboard-url-${props.stage}-${region}`,
    });

    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: this.alarmTopic.topicArn,
      description: 'Alarm SNS topic ARN',
      exportName: `processapp-alarm-topic-arn-${props.stage}-${region}`,
    });
  }
}
