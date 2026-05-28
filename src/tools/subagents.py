from __future__ import annotations
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum

from src.agent.agent import Agent
from src.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from src.config.config import Config


class Subagentparams(BaseModel):
    goal: str = Field(
        ...,
        description="The specific task or goal for the subagent to accomplish",
    )


@dataclass
class SubagentDefinition:
    name: str
    description: str
    goal_prompt: str
    allowed_tools: list[str] | None = None
    max_turns: int = 20
    timeout_seconds: float = 600


class SubagentTool(Tool):
    def __init__(self, config: Config, definition: SubagentDefinition):
        super().__init__(config)
        self.definition = definition

    @property
    def name(self) -> str:
        return f"subagent_{self.definition.name}"

    @property
    def description(self) -> str:
        return f"subagent_{self.definition.description}"

    schema = Subagentparams

    def is_mutating(self, params: dict[str, Any]) -> bool:
        return True
    
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = Subagentparams(**invocation.params)
        if not params.goal:
            return ToolResult.error_result("No goal specified for sub-agent")
        
        try:
            async with Agent(config=self.config) as agent:
                self.agent = agent
                return await self._process_message(params.goal)

        except Exception as e:
            ...