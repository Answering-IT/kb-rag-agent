"""
Retrieve Tool Wrapper Module
Drop-in replacement for strands_tools.retrieve that injects retrieveFilter automatically.

This module mimics the structure of strands_tools.retrieve:
- Exposes TOOL_SPEC at module level
- Provides retrieve() function with same signature
- Automatically injects metadata filters from global state

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


def retrieve(tool: ToolUse, **kwargs: Any) -> ToolResult:
    """
    Wrapper around strands_tools.retrieve that automatically injects retrieveFilter.

    This follows the Strands test format and uses the correct Strands type signature:
    https://github.com/strands-agents/tools/blob/main/tests/test_retrieve.py#L508

    Args:
        tool: ToolUse dict from Strands agent (has 'input' key, not attribute)
        **kwargs: Additional keyword arguments

    Returns:
        ToolResult dict
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

    # Call original retrieve tool with proper signature
    try:
        result = _original_retrieve.retrieve(tool=tool, **kwargs)
        logger.info('[RetrieveWrapper] ✅ Retrieve call succeeded')
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
