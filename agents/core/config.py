"""
Agent Configuration Management
Centralized configuration for the ProcessApp Agent.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AgentConfig:
    """Configuration manager for ProcessApp Agent"""

    def __init__(self):
        # AWS Configuration
        self.kb_id = os.environ.get('KB_ID', '')
        self.model_id = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')

        # Server Configuration
        self.port = int(os.environ.get('PORT', '8080'))
        self.debug = os.environ.get('DEBUG', 'false').lower() == 'true'

        # Agent Configuration
        self.max_session_messages = 8  # Keep last 8 messages (4 exchanges)
        self.context_messages = 6  # Use last 6 for context
        self.response_chunk_size = 3  # Words per streaming chunk
        self.max_response_length = 4000  # Max characters in response

        # Paths
        self.base_dir = Path(__file__).parent.parent
        self.prompts_dir = self.base_dir / 'prompts'

        # Set required environment variables for Strands
        os.environ['KNOWLEDGE_BASE_ID'] = self.kb_id
        os.environ['AWS_REGION'] = self.region

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate required configuration"""
        if not self.kb_id:
            logger.warning('KB_ID not set - retrieve tool may fail')

        logger.info(f'🚀 ProcessApp Agent Configuration:')
        logger.info(f'   Model: {self.model_id}')
        logger.info(f'   KB ID: {self.kb_id}')
        logger.info(f'   Region: {self.region}')
        logger.info(f'   Port: {self.port}')
        logger.info(f'   Debug: {self.debug}')

    def load_system_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_file = self.prompts_dir / 'system_prompt.md'

        if not prompt_file.exists():
            logger.warning(f'System prompt file not found: {prompt_file}')
            return self._get_default_prompt()

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f'✅ Loaded system prompt from {prompt_file}')
            return content
        except Exception as e:
            logger.error(f'Error loading system prompt: {e}')
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Fallback default prompt"""
        return """Eres un asistente que ayuda con información de la base de conocimiento.
Usa la herramienta 'retrieve' para buscar información.
Responde de forma clara y profesional en español."""
