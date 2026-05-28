import uuid
from datetime import datetime
from src.client.llm_client import LLMClient
from src.config.config import Config
from src.config.loader import get_data_dir
from src.context.manager import ContextManager
from src.tools.registry import create_default_registry
import json


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(
            config=self.config,
        )
        self.tool_registry = create_default_registry(config=config)
        self.context_manager = ContextManager(
            config=config,
            user_memory=self._load_memory(),
            tools=self.tool_registry.get_tools(),
        )
        self.session_id = str(uuid.uuid4())
        self.create_at = datetime.now()
        self.update_at = datetime.now()

        self._turn_count = 0

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
