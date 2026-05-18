import uuid
from datetime import datetime
from src.client.llm_client import LLMClient
from src.config.config import Config
from src.context.manager import ContextManager
from src.tools.registry import create_default_registry


class Session:
    def __init__(self, config: Config):
        self.config=config
        self.client = LLMClient(
            config=self.config,
        )
        self.context_manager = ContextManager(config=config)
        self.tool_registry = create_default_registry()
        self.session_id = str(uuid.uuid4())
        self.create_at = datetime.now()
        self.update_at = datetime.now()

        self._turn_count = 0
    
    def increment_turn(self) -> int:
        self._turn_count += 1
        self.update_at = datetime.now()
        
        return self._turn_count