from pathlib import Path
import os
from src.config.config import MCPServerConfig
from enum import Enum
from fastmcp import Client
from fastmcp.client.transports import StdioTransport, SSETransport
from dataclasses import dataclass, field
from typing import Any


class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPToolInfo:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


class MCPClient:
    def __init__(
        self,
        name: str,
        config: MCPServerConfig,
        cwd: Path,
    ):  # init cannot be async function
        self.name = name
        self.config = config
        self.cwd = cwd
        self.status = MCPServerStatus.DISCONNECTED
        self._client: Client | None = None

        self._tools: dict[str, MCPToolInfo] = dict()

    @property
    def tools(self) -> list[MCPToolInfo]:
        return list(self._tools.values())

    def _create_transport(self) -> StdioTransport | SSETransport:
        if self.config.command:
            env = os.environ.copy()
            env.update(self.config.env)
            return StdioTransport(
                command=self.config.command,
                args=list(self.config.args),
                env=env,
                cwd=str(self.config.cwd or self.cwd),
                log_file=Path(os.devnull),
            )
        else:
            return SSETransport(
                url=self.config.url,
            )

    async def connect(self) -> None:
        if self.status == MCPServerStatus.CONNECTED:
            return

        self.status = MCPServerStatus.CONNECTING
        try:
            self._client = Client(transport=self._create_transport())
            # the reason we call await aenter here because we want to persist the connection when connect() is call, and we will explicit call aexit later when it done, else it will create new conection every time the agent call this tool
            await self._client.__aenter__()
            tool_results = await self._client.list_tools()
            for tool in tool_results:
                self._tools[tool.name] = MCPToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=(
                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                    ),
                    server_name=self.name,
                )

            self.status = MCPServerStatus.CONNECTED
        except Exception:
            self.status = MCPServerStatus.ERROR
            raise

    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        self._tools.clear()
        self.status = MCPServerStatus.DISCONNECTED

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self._client or self.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Not connected to server {self.name}")

        result = await self._client.call_tool(tool_name, arguments) # call actual tool name regrading dup with the other tool or not because it have register as a MCP withit prefix already

        output = []
        for item in result.content:
            if hasattr(item, "text"):
                output.append(item.text)
            else:
                output.append(str(item))
        return {
            "output": "\n".join(output),
            "is_error": result.is_error,
        }
