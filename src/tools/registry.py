from typing import Any
from pathlib import Path

from src.config.config import Config
from src.tools.base import Tool, ToolResult, ToolInvocation

from src.tools.builtin import get_all_builtin_tools
from src.tools.subagents import get_default_subagent_definitions, SubagentTool
from src.tools.skills.skill_tool import Skill
from src.safety.approval import ApprovalManager, ApprovalContext, ApprovalDecision
from src.hooks.hook_system import HookSystem
import logging


logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, config: Config):
        self._tools: dict[str, Tool] = {}
        self._skills: dict[str, Skill] = {}
        self._mcp_tools: dict[str, Tool] = {}
        self.config = config
        
    @property
    def connected_mcp_servers(self) -> list[Tool]:
        return self._mcp_tools.values()

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registerd tool: {tool.name}")
        
    def register_mcp_tool(self, tool: Tool) -> None:
        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registerd MCP tool: {tool.name}")

    def register_skill(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        logger.debug(f"Registerd Skill: {skill.name}")

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True

        return False

    def get(self, name: str) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        elif name in self._mcp_tools:
            return self._mcp_tools[name]
        elif name in self._skills:
            return self._skills[name]
        return None

    def get_tools(self) -> list[Tool]:
        tools: list[Tool] = []
        for tool in self._tools.values():
            tools.append(tool)
        for mcp_tool in self._mcp_tools.values():
            tools.append(mcp_tool)
        
        if self.config.allowed_tools:
            allow_set = set(self.config.allowed_tools)
            tools = [t for t in tools if t.name in allow_set]
        
        return tools

    def get_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        for skill in self._skills.values():
            skills.append(skill)
        
        return skills

    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    def get_skills_schemas(self) -> list[dict[str, Any]]:
        return [skill.to_skill_openai_schema() for skill in self.get_skills()]

    async def invoke(
        self,
        name: str,
        params: dict[str, Any],
        cwd: Path,
        hook_system: HookSystem,
        approval_manager: ApprovalManager | None = None,
    ) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            result = ToolResult.error_result(
                f"Unknown tool: {name}",
                metadata = {
                    "tool_name": name
                }
            )
            await hook_system.trigger_after_tool(name, params, result)
            return result
        
        validation_errors = tool.validate_params(params)
        if validation_errors:
            result =  ToolResult.error_result(
                f"Invalid parameters: {'; '.join(validation_errors)}",
                metadata = {
                    "tool_name": name,
                    "validation_errors": validation_errors
                }
            )
            await hook_system.trigger_after_tool(name, params, result)
            return result
        
        await hook_system.trigger_before_tool(name, params)
        invocation = ToolInvocation(
            params=params,
            cwd=cwd,
        )
        if approval_manager:
            confirmation = await tool.get_confirmation(invocation)
            if confirmation:
                context = ApprovalContext(
                    tool_name=name,
                    params=params,
                    is_mutating=tool.is_mutating(params),
                    affected_paths=confirmation.affected_paths,
                    command=confirmation.command,
                    is_dangerous=confirmation.is_dangerous,
                )
                
                decision = await approval_manager.check_approval(context)
                if decision == ApprovalDecision.REJECTED:
                    result = ToolResult.error_result(f"Operation rejected by safety policy for command : {confirmation.command}")
                    await hook_system.trigger_after_tool(name, params, result)
                    return result
                
                elif decision == ApprovalDecision.NEEDS_CONFIRMATION:
                    approved = approval_manager.request_confirmation(confirmation)
                    if not approved:
                        result = ToolResult.error_result("User rejected the operation")
                        await hook_system.trigger_after_tool(name, params, result)
                        return result
        try:
            result = await tool.execute(invocation)
        except Exception as e:
            logger.exception(f"Tool {name} raised unexpected error")
            result = ToolResult.error_result(
                f"Interal errors: {str(e)}",
                metadata = {
                    "tool_name": name
                }
            )
        await hook_system.trigger_after_tool(name, params, result)
        return result

        
def create_default_registry(config: Config) -> ToolRegistry:
    registry = ToolRegistry(config)
    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config))
    for subagent_def in get_default_subagent_definitions():
        registry.register(SubagentTool(config, subagent_def))
    return registry