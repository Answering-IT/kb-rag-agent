"""
Agent Orchestrator
Clean orchestration layer for ProcessApp Agent using Strands SDK.
"""

import re
import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from strands import Agent
from strands_tools import retrieve, http_request

from .config import AgentConfig
from .tools.metadata_filter import MetadataFilterBuilder, RequestMetadata
from .tools.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates agent operations with clean separation of concerns.

    Responsibilities:
        - Configure Strands agent with tools
        - Handle metadata filtering
        - Manage conversation sessions
        - Stream responses to clients
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize orchestrator.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.session_manager = SessionManager(
            max_messages=config.max_session_messages,
            context_messages=config.context_messages
        )

        # Load system prompt
        system_prompt = config.load_system_prompt()

        # Initialize Strands agent with tools
        self.agent = Agent(
            model=config.model_id,
            tools=[retrieve, http_request],
            system_prompt=system_prompt
        )

        logger.info('✅ Agent orchestrator initialized')

    def extract_metadata(self, headers: Dict[str, str], body: Dict[str, Any]) -> RequestMetadata:
        """
        Extract metadata from request.

        Args:
            headers: HTTP request headers
            body: Request body

        Returns:
            RequestMetadata object
        """
        metadata = MetadataFilterBuilder.extract_from_request(headers, body)

        logger.info(f'[Request] Extracted metadata: tenant={metadata.tenant_id}, '
                   f'project={metadata.project_id}, task={metadata.task_id}')

        return metadata

    def build_filter(self, metadata: RequestMetadata) -> Optional[Dict[str, Any]]:
        """
        Build Bedrock KB retrieveFilter from metadata.

        Args:
            metadata: Request metadata

        Returns:
            Filter dict compatible with Strands retrieve tool, or None
        """
        kb_filter = MetadataFilterBuilder.build_filter(metadata)

        if kb_filter:
            logger.info(f'[Filter] Built: {json.dumps(kb_filter, indent=2)}')
        else:
            logger.info('[Filter] No filter (unrestricted access)')

        return kb_filter

    def build_prompt(
        self,
        input_text: str,
        session_id: str,
        kb_filter: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build enhanced prompt with conversation context and filter instructions.

        Args:
            input_text: User input
            session_id: Session identifier
            kb_filter: Optional KB filter to inject

        Returns:
            Enhanced prompt string
        """
        # Get conversation context
        context = self.session_manager.get_context(session_id)

        # Build prompt with context
        if context:
            prompt = f"Contexto de conversación reciente:\n{context}\nUsuario actual: {input_text}"
        else:
            prompt = input_text

        # Add filter instructions if present (internal only, not shown to user)
        if kb_filter:
            filter_json = json.dumps(kb_filter, indent=2)
            prompt += f"""

METADATA FILTERING ACTIVA:
Cuando uses la herramienta 'retrieve', DEBES incluir este parámetro exacto:
retrieveFilter={filter_json}

Esto filtrará los resultados según los permisos del usuario. NO omitas este parámetro."""

        return prompt

    @staticmethod
    def remove_thinking_tags(text: str) -> str:
        """
        Remove <thinking>...</thinking> tags from model responses.

        Args:
            text: Response text

        Returns:
            Cleaned text without thinking tags
        """
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove extra blank lines
        return cleaned.strip()

    async def process_request(
        self,
        input_text: str,
        session_id: str,
        metadata: RequestMetadata
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user request and stream response.

        Args:
            input_text: User input
            session_id: Session identifier
            metadata: Request metadata

        Yields:
            Response chunks: {"type": "chunk", "data": "..."}
            Completion: {"type": "complete", "sessionId": "..."}
        """
        try:
            # Build KB filter
            kb_filter = self.build_filter(metadata)

            # Build prompt with context and filter
            prompt = self.build_prompt(input_text, session_id, kb_filter)

            # Add user message to session
            self.session_manager.add_message(session_id, 'user', input_text)

            # Call agent
            logger.info(f'[Agent] Calling model with prompt length: {len(prompt)} chars')
            result = self.agent(prompt)

            # Extract response text
            response_text = self._extract_response(result)

            # Clean response
            response_text = self.remove_thinking_tags(response_text)

            # Limit response length
            if len(response_text) > self.config.max_response_length:
                response_text = response_text[:self.config.max_response_length]
                logger.warning(f'[Response] Truncated to {self.config.max_response_length} chars')

            # Store assistant response in session
            self.session_manager.add_message(session_id, 'assistant', response_text)

            # Stream response in chunks
            words = response_text.split()
            chunk_size = self.config.response_chunk_size

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                yield {"type": "chunk", "data": chunk}

            # Completion marker
            yield {"type": "complete", "sessionId": session_id}

            logger.info(f'[Response] Completed for session {session_id}')

        except Exception as e:
            logger.error(f'[Error] Processing request: {e}', exc_info=True)

            # User-friendly error message
            yield {
                "type": "chunk",
                "data": "Disculpa, tuve un problema procesando tu pregunta."
            }
            yield {"type": "complete", "sessionId": session_id}

    @staticmethod
    def _extract_response(result) -> str:
        """
        Extract response text from agent result.

        Args:
            result: Agent result object

        Returns:
            Response text string
        """
        if hasattr(result, 'output'):
            return result.output
        elif hasattr(result, 'content'):
            return result.content
        elif hasattr(result, 'text'):
            return result.text
        else:
            return str(result)

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get agent health status.

        Returns:
            Health status dict
        """
        return {
            "status": "healthy",
            "model": self.config.model_id,
            "region": self.config.region,
            "kb_id": self.config.kb_id,
            "tools": ["retrieve", "http_request"],
            "provider": "bedrock",
            "sessions": self.session_manager.get_session_count(),
            "version": "2.0.0"
        }
