"""
Base Agricultural Tool Interface
All tools must be strictly read-only.
Hardware actuation (pumps, valves, motorized equipment) is explicitly prohibited.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """
    Abstract read-only diagnostic or context tool.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for tool invocation."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool provides and what parameters it accepts."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Executes the read-only inspection and returns a structured dictionary.
        """
        pass
