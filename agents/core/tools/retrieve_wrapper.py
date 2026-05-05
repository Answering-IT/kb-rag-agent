"""
Retrieve Tool Wrapper
Wraps Strands retrieve tool to inject retrieveFilter automatically.
"""

import logging
from typing import Dict, Any, Optional
from strands_tools import retrieve as _original_retrieve

logger = logging.getLogger(__name__)

# Global variable to store the current filter
_current_filter: Optional[Dict[str, Any]] = None


def set_retrieve_filter(kb_filter: Optional[Dict[str, Any]]):
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


def retrieve_with_filter(tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper around strands_tools.retrieve that automatically injects retrieveFilter.

    This follows the Strands test format:
    https://github.com/strands-agents/tools/blob/main/tests/test_retrieve.py#L508

    Args:
        tool: Tool use dict from Strands agent

    Returns:
        Tool result dict
    """
    global _current_filter

    # Get tool input
    tool_input = tool.get('input', {})

    # Inject retrieveFilter if we have one and it's not already set
    if _current_filter and 'retrieveFilter' not in tool_input:
        tool_input['retrieveFilter'] = _current_filter
        tool['input'] = tool_input
        logger.info(f'[RetrieveWrapper] Injected filter into retrieve call')
        logger.info(f'[RetrieveWrapper] Filter: {_current_filter}')

    # Call original retrieve tool
    result = _original_retrieve.retrieve(tool=tool)

    return result


# Create the tool schema that Strands expects
retrieve_with_filter.tool_schema = _original_retrieve.tool_schema
retrieve_with_filter.__name__ = 'retrieve'  # Keep same name for compatibility
