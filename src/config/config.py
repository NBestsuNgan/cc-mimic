from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv
from pathlib import Path
import os
from typing import Any
from enum import Enum

load_dotenv(Path.cwd() / ".env")

class ModelConfig(BaseModel): # separate for "Modle" configuration params, easily to extendable in the future
    name: str = "openrouter/owl-alpha" 
    temperature: float = Field(default=1, ge=0.0, le=2.0) 
    context_window: int = 1_000_000

class ShellEnvironmentPolicy(BaseModel):
    ignore_default_excludes: bool = False
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*SECRET*", "*PASSWORD*", "*TOKEN*"]
    )
    set_vars: dict[str, str] = Field(default_factory=dict)

class MCPServerConfig(BaseModel):
    enabled: bool = True
    startup_timeout_sec: float = 10

    # stdio transport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None
    
    # http/sse transport
    url: str | None = None # http://localhost:8000/sse
    
    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        has_command = self.command is not None
        has_url = self.url is not None
        
        if not has_command and not has_url:
            raise ValueError("MCP Server must have either 'command' (stdio) or 'url' (http/sse)")

        if has_command and has_url:
            raise ValueError("MCP Server cannot have both 'command' (stdio) or 'url' (http/sse)")

        return self
        
class ApprovalPolicy(str, Enum):
    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edit"
    NEVER = "never"
    YOLO = "yolo"
    
class HookTrigger(str, Enum):
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"

    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"

    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"

    ON_ERROR = "on_error"
    
class HookConfig(BaseModel):
    name: str
    trigger: HookTrigger 
    command: str | None = None #python3 test.py
    script: str | None = None # shell-script -> echo
    timeout_sec: float = 30
    enabled: bool = True
    
    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:
        if not self.command and not self.script:
            raise ValueError("Hook must either have 'command' or 'script'")
        return self


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    shell_environment: ShellEnvironmentPolicy = Field(default_factory=ShellEnvironmentPolicy)
    hooks_enabled: bool = False
    hooks: list[HookConfig] = Field(default_factory=list)
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    max_turns: int = 100
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    
    allowed_tools: list[str] | None =  Field(
        None,
        description="If set, only this tools will be available to agent",
    )
    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False

    @property
    def api_key(self) -> str | None:
        return os.environ.get("API_KEY")
    
    @property
    def base_url(self) -> str | None:
        return os.environ.get("BASE_URL")
    
    @property
    def model_name(self) -> str:
        return self.model.name
    
    @model_name.setter
    def model_name(self, value: str) -> None:
        #re-write the model name in the config
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        self.model.temperature = value

    def validate(self) -> list[str]:
        # usage in validating the config
        errors: list[str] = []

        if not self.api_key:
            errors.append("NO API key found. Set API_KEY environment variables.")

        if not self.cwd.exists():
            errors.append(f"Current working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def initial_start_dir(self) -> None:
        # pwd/.ai-agent
        config_path = self.cwd / ".ai-agent"
        config_path.mkdir(parents=True, exist_ok=True)
        
        # pwd/.ai-agent/config.toml
        config_toml_path = config_path / "config.toml"
        CONFIG_TOML_CONTENT = """# initial config dir

hooks_enabled=true

# Object
[model]
name="openrouter/owl-alpha"
temperature=0

# List of Object
[[hooks]]
name='log_before_agent_hook'
trigger='before_agent'
command = 'python .ai-agent/hooks/test_hook.py' 

[[hooks]]
name='log_after_agent_hook'
trigger='after_agent'
command = 'python .ai-agent/hooks/test_hook.py' 

[[hooks]]
name='log_before_llm_hook'
trigger='before_llm'
command = 'python .ai-agent/hooks/test_hook.py' 

[[hooks]]
name='log_after_llm_hook'
trigger='after_llm'
command = 'python .ai-agent/hooks/test_hook.py' 

[[hooks]]
name='log_before_tool_hook'
trigger='before_tool'
command = 'python .ai-agent/hooks/test_hook.py' 

[[hooks]]
name='log_after_tool_hook'
trigger='after_tool'
command = 'python .ai-agent/hooks/test_hook.py' 



# [mcp_servers.filesystem]
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-filesystem", "/Users/nbest/Desktop/cc-mimic/.ai-agent", "/tmp"]

# [mcp_servers.github]
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-github"]
# env = { GITHUB_PERSONAL_ACCESS_TOKEN = "your_token" }
"""
        if not config_toml_path.exists():
            config_toml_path.write_text(CONFIG_TOML_CONTENT, encoding="utf-8")
        
        # discovery tools
        discovery_tools_path = config_path / "tools"
        discovery_tools_path.mkdir(parents=True, exist_ok=True)
        
        # discovery tools execute file
        discovery_tool_file_path = discovery_tools_path / "test_tool.py"
        DISCOVERY_TOOL_CONTENT = """from pydantic import BaseModel, Field
from src.tools.base import Tool, ToolInvocation, ToolResult, ToolKind

# discovery tool of sub agent
class TestToolParams(BaseModel):
    message: str = Field(..., description="The message to echo back")

class TestTool(Tool):
    name = "test_tool"
    description = (
        "A test tool that echoes back the input message. "
        "This tool is discovered from .unified_agent/tool/test_tool.py"
    )
    kind = ToolKind.READ
    schema = TestToolParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = TestToolParams(**invocation.params)
        message = params.message
        
        output = f"Test tool received: {message}\\n"
        output += "Tool was discovered from: .ai-agent/tool/test_tool.py"
        
        return ToolResult.success_result(output)
"""

        if not discovery_tool_file_path.exists():
            discovery_tool_file_path.write_text(DISCOVERY_TOOL_CONTENT, encoding="utf-8")
        
        # configureable hook execute files
        hooks_path = config_path / "hooks"
        hooks_path.mkdir(parents=True, exist_ok=True)
        
        # hook logs execute file
        hook_file_path = hooks_path / "test_hook.py"
        HOOK_CONTENT = """#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from pathlib import Path

def main():
    trigger = os.environ.get("AI_AGENT_TRIGGER")
    cwd = os.environ.get("AI_AGENT_CWD")
    tool_name = os.environ.get("AI_AGENT_TOOL_NAME")
    user_message = os.environ.get("AI_AGENT_USER_MESSAGE")
    llm_response = os.environ.get("AI_AGENT_LLM_RESPONSE")
    error = os.environ.get("AI_AGENT_ERROR")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "cwd": cwd,
        "tool_name": tool_name,
        "user_message": user_message,
        "llm_response": llm_response,
        "error": error,
    }

    # Clean cross-platform pathlib alternative to your string replace lines
    log_path = Path(cwd) / ".ai-agent" / "hook.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[HOOK] {json.dumps(log_data)}\\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
"""

        if not hook_file_path.exists():
            hook_file_path.write_text(HOOK_CONTENT, encoding="utf-8")
        
        # hook logs
        hook_log_path = config_path / "hook.log"
        hook_log_path.touch()
        