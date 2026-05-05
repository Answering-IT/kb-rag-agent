"""
Session Manager
Handles conversation session state and history.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user conversation sessions with context"""

    def __init__(self, max_messages: int = 8, context_messages: int = 6):
        """
        Initialize session manager.

        Args:
            max_messages: Maximum messages to store per session
            context_messages: Number of recent messages to use for context
        """
        self._sessions: Dict[str, List[dict]] = {}
        self.max_messages = max_messages
        self.context_messages = context_messages

    def add_message(self, session_id: str, role: str, content: str):
        """
        Add message to session history.

        Args:
            session_id: Unique session identifier
            role: 'user' or 'assistant'
            content: Message content
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append({
            'role': role,
            'content': content
        })

        # Trim to max messages
        if len(self._sessions[session_id]) > self.max_messages:
            self._sessions[session_id] = self._sessions[session_id][-self.max_messages:]

    def get_context(self, session_id: str) -> str:
        """
        Get conversation context for session.

        Returns formatted string with recent conversation history.
        """
        if session_id not in self._sessions:
            return ""

        recent = self._sessions[session_id][-self.context_messages:]

        if not recent:
            return ""

        context_lines = []
        for msg in recent:
            role_label = "Usuario" if msg['role'] == 'user' else "Asistente"
            context_lines.append(f"{role_label}: {msg['content']}")

        return "\n".join(context_lines)

    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self._sessions)

    def clear_session(self, session_id: str):
        """Clear a specific session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f'[Session] Cleared session: {session_id}')
