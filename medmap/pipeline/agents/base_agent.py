"""Base agent class for the multi-agent system (BONUS)."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standard result returned by all agents."""
    agent_name: str
    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for pipeline agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    def run(self, context: dict) -> AgentResult:
        """Execute the agent's task.

        Args:
            context: shared pipeline context dict.

        Returns:
            AgentResult with outcome.
        """

    def _ok(self, data: Any = None, **stats) -> AgentResult:
        return AgentResult(agent_name=self.name, success=True, data=data, stats=stats)

    def _fail(self, error: str, data: Any = None) -> AgentResult:
        self.logger.error("%s failed: %s", self.name, error)
        return AgentResult(agent_name=self.name, success=False, data=data, errors=[error])
