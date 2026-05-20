from pydantic import BaseModel, Field
from src.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from src.utils.paths import resolve_path, is_binary_file
from src.utils.text import count_tokens, truncate_text


class ShellParams(BaseModel):
    command: str = Field(
        ...,
        description="The shell command to execute",
    )
    timeout: int = Field(
        120,
        ge=1,
        le=600,
        description="Timeout in seconds (default: 120)"
    )
    cwd: str | None = Field(
        None,
        description="The working directory for the command."
    )


class ShellTool(Tool):
    name = "shell"
    description = (
        "Execute a shell command. Use this for running system commands, script and CLI tools."
    )
    kind = ToolKind.SHELL
    schema = ShellParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)
        cwd = resolve_path(invocation.cwd, params.cwd)




        