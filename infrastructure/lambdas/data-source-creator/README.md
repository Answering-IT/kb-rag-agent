# ⚠️ DEPRECATED - Data Source Creator

**Status**: LEGACY - No longer used in current architecture

## Why Deprecated

This Lambda function was originally created as a CloudFormation custom resource to create Bedrock Data Sources.

**Replacement**: Native CDK construct `aws-cdk-lib.aws-bedrock.CfnDataSource`

See `BedrockStack.ts` line 134 for current implementation.

## Migration Path

The native CDK construct provides:
- Better type safety
- Native CloudFormation integration
- Automatic updates with CDK upgrades
- No custom resource maintenance

## Removal Timeline

- **Deprecated**: 2026-04-17
- **Planned Removal**: After Phase 1 verification complete
- **No longer deployed**: Confirmed not referenced in `bin/app.ts`

## References

- Current implementation: `infrastructure/lib/BedrockStack.ts`
- Lambda inventory: `/LAMBDA_INVENTORY.md`
