"""
ProcessApp Agent Core Module
Provides orchestration and tool management for the agent.
"""

from .orchestrator import AgentOrchestrator
from .config import AgentConfig

__all__ = ['AgentOrchestrator', 'AgentConfig']
__version__ = '2.0.0'
