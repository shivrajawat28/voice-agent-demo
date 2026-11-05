"""
Base LLM Provider Interface
Defines strict, typed abstractions for LLM reasoning backends:
1. BaseLLMProvider (Protocol/ABC for text and structured generation)
2. Custom exceptions for LLM authentication and inference failures.
"""
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Any, Dict
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM API credentials are missing, invalid, or blocked."""
    pass


class LLMInferenceError(LLMError):
    """Raised when LLM inference, JSON parsing, or network communication fails."""
    pass


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM reasoning engines.
    Allows swappable implementations (MockLLMProvider, GeminiLLMProvider, OpenAILLMProvider)
    without coupling the orchestrator to any specific vendor.
    """

    def __init__(self):
        self.last_usage: Optional[Dict[str, Any]] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Vendor/adapter identifier (e.g. 'mock', 'gemini', 'openai')."""
        pass

    @property
    @abstractmethod
    def provider_status(self) -> str:
        """Current operational status: 'live', 'mock', or 'unavailable'."""
        pass

    @abstractmethod
    def is_live_ready(self) -> bool:
        """Returns True if the provider is fully configured with credentials for live inference."""
        pass

    def get_last_usage(self) -> Optional[Dict[str, Any]]:
        """Returns token usage metadata from the most recent request if available."""
        return getattr(self, "last_usage", None)

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Generates freeform text response given a user prompt and optional system context.
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Generates a validated structured Pydantic object conforming to `schema`.
        """
        pass
