"""
Base Specialist Agent Interface
Specialist agents reason about specific agricultural domains using permitted read-only tools.
They must adhere to strict principles:
- Zero fabrication of telemetry, weather readings, or diagnostic certainty.
- Explicit disclosure of limitations and missing grower inputs.
- Read-only tool access; zero actuation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.conversation import AgentResult
from app.tools.base import BaseTool


class AgentContext(BaseModel):
    query: str
    language: str = "en-US"
    session_id: Optional[str] = None
    zone_id: Optional[str] = "DEMO-ZONE-001"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract interface for specialist agents.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique machine identifier for the agent."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable specialist agent name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Purpose and capabilities of this agent."""
        pass

    @property
    @abstractmethod
    def permitted_tools(self) -> List[str]:
        """List of tool names this agent is allowed to execute."""
        pass

    @abstractmethod
    async def execute(
        self,
        context: AgentContext,
        tools: Dict[str, BaseTool],
    ) -> AgentResult:
        """
        Executes reasoning for the specialist domain and returns a structured AgentResult.
        """
        pass
