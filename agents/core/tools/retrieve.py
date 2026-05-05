"""
Retrieve Tool Wrapper Module
Drop-in replacement for strands_tools.retrieve that injects retrieveFilter automatically.

This module mimics the structure of strands_tools.retrieve:
- Exposes TOOL_SPEC at module level
- Provides retrieve() function with same signature
- Automatically injects metadata filters from global state
- Implements hierarchical fallback: project → tenant (if results < threshold)

Usage in orchestrator:
    from .tools import retrieve_wrapper as retrieve
    agent = Agent(tools=[retrieve, http_request])
"""

import logging
from typing import Any, Optional
from strands.types.tools import ToolUse, ToolResult
from strands_tools import retrieve as _original_retrieve

logger = logging.getLogger(__name__)

# Global variable to store the current filter
_current_filter: Optional[dict] = None

# Minimum results threshold for fallback (if results < this, fallback to tenant-level)
MIN_RESULTS_THRESHOLD = 2


def set_retrieve_filter(kb_filter: Optional[dict]):
    """
    Set the global retrieve filter to be injected into all retrieve calls.

    Args:
        kb_filter: Bedrock KB filter in Strands format
    """
    global _current_filter
    _current_filter = kb_filter
    logger.info(f'[RetrieveWrapper] Filter set: {kb_filter is not None}')


def clear_retrieve_filter():
    """Clear the global retrieve filter."""
    global _current_filter
    _current_filter = None
    logger.info('[RetrieveWrapper] Filter cleared')


def _extract_partition_key(kb_filter: dict) -> Optional[str]:
    """
    Extract partition_key value from KB filter.

    Args:
        kb_filter: Bedrock KB filter dict

    Returns:
        partition_key string or None
    """
    try:
        # Navigate filter structure: {"andAll": [{"equals": {"key": "partition_key", "value": "t100001_p1"}}]}
        and_all = kb_filter.get('andAll', [])
        for condition in and_all:
            if 'equals' in condition:
                equals = condition['equals']
                if equals.get('key') == 'partition_key':
                    return equals.get('value')
    except Exception as e:
        logger.warning(f'[Fallback] Could not extract partition_key: {e}')
    return None


def _build_tenant_filter(partition_key: str) -> Optional[dict]:
    """
    Build tenant-level filter from project/task partition_key.

    Args:
        partition_key: Original partition key (e.g., "t100001_p1", "t100001_p1_t5")

    Returns:
        Tenant-level filter dict or None
    """
    if not partition_key or not partition_key.startswith('t'):
        return None

    # Extract tenant_id: "t100001_p1" → "t100001"
    parts = partition_key.split('_')
    if len(parts) < 2:
        # Already tenant-level, no fallback needed
        return None

    tenant_key = parts[0]  # "t100001"

    logger.info(f'[Fallback] Building tenant filter: {partition_key} → {tenant_key}')

    return {
        "andAll": [
            {
                "equals": {
                    "key": "partition_key",
                    "value": tenant_key
                }
            }
        ]
    }


def _count_results(result: ToolResult) -> int:
    """
    Count number of results in ToolResult.

    Args:
        result: ToolResult from retrieve call

    Returns:
        Number of results found
    """
    try:
        if isinstance(result, dict) and 'content' in result:
            content = result['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text = item.get('text', '')
                        # Count result markers in text
                        return text.count('Result ')
        return 0
    except Exception as e:
        logger.warning(f'[Fallback] Could not count results: {e}')
        return 0


def retrieve(tool: ToolUse, **kwargs: Any) -> ToolResult:
    """
    Wrapper around strands_tools.retrieve with hierarchical fallback.

    Implements fallback strategy:
    1. Try with project/task-level filter (e.g., t100001_p1)
    2. If results < MIN_RESULTS_THRESHOLD, fallback to tenant-level (t100001)
    3. Combine results (project-level prioritized)

    Args:
        tool: ToolUse dict from Strands agent (has 'input' key, not attribute)
        **kwargs: Additional keyword arguments

    Returns:
        ToolResult dict (may contain combined results from both levels)
    """
    global _current_filter

    # ToolUse is a dict, not an object - access via ['input']
    tool_input = tool.get('input', {})

    # Inject retrieveFilter if we have one and it's not already set
    if _current_filter and 'retrieveFilter' not in tool_input:
        tool_input['retrieveFilter'] = _current_filter
        tool['input'] = tool_input
        logger.info('[RetrieveWrapper] ✅ Injected filter into retrieve call')
        logger.info(f'[RetrieveWrapper] Filter: {_current_filter}')
    else:
        if _current_filter:
            logger.info('[RetrieveWrapper] Filter already in tool.input, not injecting')
        else:
            logger.info('[RetrieveWrapper] No filter set, calling retrieve without filter')

    # Call original retrieve tool
    try:
        result = _original_retrieve.retrieve(tool=tool, **kwargs)
        result_count = _count_results(result)
        logger.info(f'[RetrieveWrapper] ✅ Retrieve call succeeded ({result_count} results)')

        # Check if fallback is needed
        if _current_filter and result_count < MIN_RESULTS_THRESHOLD:
            logger.info(f'[Fallback] Threshold check: {result_count} < {MIN_RESULTS_THRESHOLD}')
            partition_key = _extract_partition_key(_current_filter)
            logger.info(f'[Fallback] Extracted partition_key: {partition_key}')
            tenant_filter = _build_tenant_filter(partition_key) if partition_key else None
            logger.info(f'[Fallback] Built tenant_filter: {tenant_filter}')

            if tenant_filter:
                logger.info(f'[Fallback] Only {result_count} results found, attempting tenant-level fallback')

                # Create fallback tool call with tenant filter
                fallback_tool = tool.copy()
                fallback_input = tool_input.copy()
                fallback_input['retrieveFilter'] = tenant_filter
                fallback_tool['input'] = fallback_input

                try:
                    fallback_result = _original_retrieve.retrieve(tool=fallback_tool, **kwargs)
                    fallback_count = _count_results(fallback_result)
                    logger.info(f'[Fallback] ✅ Tenant-level search succeeded ({fallback_count} results)')

                    # If fallback found more results, combine them
                    if fallback_count > 0:
                        # Simple strategy: append fallback results to original
                        # (agent will prioritize based on relevance scores)
                        if isinstance(result, dict) and isinstance(fallback_result, dict):
                            result_text = result.get('content', [{}])[0].get('text', '')
                            fallback_text = fallback_result.get('content', [{}])[0].get('text', '')

                            combined_text = (
                                f"{result_text}\n\n"
                                f"[Additional context from organization-level documents]:\n"
                                f"{fallback_text}"
                            )

                            result['content'] = [{'type': 'text', 'text': combined_text}]
                            logger.info(f'[Fallback] ✅ Combined results: {result_count} project + {fallback_count} tenant')

                except Exception as e:
                    logger.warning(f'[Fallback] Tenant-level search failed: {e}')
                    # Return original result even if fallback fails

        return result

    except Exception as e:
        logger.error(f'[RetrieveWrapper] ❌ Retrieve call failed')
        logger.error(f'[RetrieveWrapper] Error type: {type(e).__name__}')
        logger.error(f'[RetrieveWrapper] Error message: {str(e)}')
        logger.error(f'[RetrieveWrapper] Tool input: {tool.get("input", {})}')
        raise


# Expose the TOOL_SPEC from the original retrieve module
# This allows Strands to recognize our wrapper as a valid tool
TOOL_SPEC = _original_retrieve.TOOL_SPEC
