"""
Conversation Service
Coordinates NLU providers, session management, and response formatting.
"""
from typing import Optional
from ai_agronomist.config import CONVERSATION_PROVIDER
from ai_agronomist.models.conversation import ChatResponse
from ai_agronomist.providers.base import BaseConversationProvider
from ai_agronomist.providers.deterministic import DeterministicProvider
from ai_agronomist.services.orchestrator import orchestrator


class ConversationService:
    def __init__(self, provider: Optional[BaseConversationProvider] = None):
        if provider:
            self._provider = provider
        elif CONVERSATION_PROVIDER == "deterministic":
            self._provider = DeterministicProvider()
        else:
            self._provider = orchestrator

    def set_provider(self, provider: BaseConversationProvider) -> None:
        """Swap provider dynamically (e.g. for future Gnani AI integration)"""
        self._provider = provider

    def get_provider(self) -> BaseConversationProvider:
        return self._provider

    async def handle_message(
        self,
        message: str,
        language: str = "en-US",
        session_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> ChatResponse:
        return await self._provider.process_message(
            message=message,
            language=language,
            session_id=session_id,
            zone_id=zone_id,
        )

    def clear_session(self, session_id: Optional[str] = None) -> None:
        """Clear session conversational memory and greeting history."""
        if hasattr(self._provider, "clear_session"):
            self._provider.clear_session(session_id)


# Global singleton instance
conversation_service = ConversationService()
