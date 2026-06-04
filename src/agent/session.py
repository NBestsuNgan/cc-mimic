import uuid
from datetime import datetime
from src.hooks.hook_system import HookSystem
from src.client.llm_client import LLMClient
from src.config.config import Config
from src.config.loader import get_data_dir
from src.context.manager import ContextManager
from src.context.loop_detector import LoopDetector
from src.tools.registry import create_default_registry
from src.tools.discovery import ToolDiscoveryManager
from src.tools.mcp.mcp_manager import MCPManager
from src.context.compaction import ChatCompactor
from src.safety.approval import ApprovalManager, ApprovalContext, ApprovalDecision

import json


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(
            config=self.config,
        )
        self.tool_registry = create_default_registry(config=config) # register built-in tool and sub-agent
        self.context_manager: ContextManager | None = None
        
        self.discovery_manager = ToolDiscoveryManager(
            config=config,
            registry=self.tool_registry,
        )
        self.mcp_manager = MCPManager(self.config)
        self.chat_compactor = ChatCompactor(self.client)
        self.approval_manager = ApprovalManager(
            self.config.approval, 
            self.config.cwd,
        )
        self.loop_detector = LoopDetector()
        self.hook_system = HookSystem(config=self.config)
        self.session_id = str(uuid.uuid4())
        self.create_at = datetime.now()
        self.update_at = datetime.now()

         
        self._turn_count = 0
        
    async def initialize(self) -> None:
        # register MCP
        await self.mcp_manager.initialize() # initial all mcp client connection
        self.mcp_manager.register_tools(self.tool_registry) # register mcp tool in self.tool_registry 
        
        # register hidden(discovery) tool of subagent
        self.discovery_manager.discover_all()  # get hidden(discovery) tool of subagent
        
        # load built-in tools, MCP tools, hiddent ool of subagent -> into context manager
        self.context_manager = ContextManager(
            config=self.config,
            user_memory=self._load_memory(),
            tools=self.tool_registry.get_tools(),
        )

    def _load_memory(self) -> str | None:
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"

        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.load(content)
            entries = data.get("entries")
            if not entries:
                return None

            lines = ["Stored Memories:"]
            for key, value in sorted(entries.items()):
                lines.append(f"  {key}: {value}")

            return "\n".join(lines)

        except Exception:
            return None

    def increment_turn(self) -> int:
        self._turn_count += 1
        self.update_at = datetime.now()

        return self._turn_count
