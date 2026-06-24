from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from dataclasses import dataclass
from src.config.config import Config
from src.tools.base import Tool, ToolKind, ToolInvocation, ToolResult
from src.config.config import Config
from typing import Any
from pydantic import BaseModel, Field
from src.utils.paths import resolve_path
from src.utils.text import count_tokens, truncate_text
from src.safety.blocked_file import BlockedFile
from pathlib import Path
from src.utils.paths import load_frontmatter
from pydantic.json_schema import model_json_schema

class SkillParams(BaseModel):
    name: str = Field(
        ...,
        description="The name of the skill to execute",
    )

@dataclass
class SkillInfo:
    name: str
    description: str
    path: Path

class Skill(Tool):
    def __init__(
            self, 
            config: Config,
            skill_info: SkillInfo
        ) -> None:
        super().__init__(config)
        self.config=config
        self._skill_info=skill_info
        self._name=self._skill_info.name
        self._path=self._skill_info.path
        self._description=self._skill_info.description
        
    kind = ToolKind.SHELL
    schema = SkillParams
    MAX_FILE_SIZE = 1024 * 1024 * 10  # 10 MB
    MAX_OUTPUT_TOKENS = 25000
    

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def description(self) -> str:
        return self._description
    
    @description.setter
    def description(self, value: str):
        self._description = value

    @property
    def path(self) -> str:
        return self._path
    
    @path.setter
    def path(self, value: str):
        self._path = value
    
    def is_mutable(self, params) -> bool:
        return False

    def to_skill_openai_schema(self) -> dict[str, Any]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema = model_json_schema(schema, mode="serialization")

            return {
                "name": self._name,
                "description": self._description,
            }
        
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        path = self._path

        if not path.exists():
            # technically, we try to execute the command but whatever
            # the llm give us was kind of hallucination or it did not
            # understand the folder structure really well.
            # that why we returning an error and that will be given to the llm
            return ToolResult.error_result(f"File not found: {path}")

        if not path.is_file():
            return ToolResult.error_result(f"Path is not a file: {path}")
        
        if path.name.lower() not in {"skill.md"}:
            return ToolResult.error_result(f"Skill is not in the right format 'skill.md' or 'SKILL.md': {path.name}")
        
        is_contain_block_file = await BlockedFile(path.name, self.name).execute()
        if is_contain_block_file:
            return is_contain_block_file

        try:
            metadata, content = load_frontmatter(path)
            token_count = count_tokens(content)

            truncated = False
            output = content
            if token_count > self.MAX_OUTPUT_TOKENS:
                output = truncate_text(
                    content,
                    self.config.model_name, 
                    self.MAX_OUTPUT_TOKENS,
                )
                truncated = True

            return ToolResult.success_result(
                output=output,
                truncated=truncated,
                metadata={
                    "name": metadata["name"] or None,
                    "path": str(path)
                },
            )
        except Exception as e:
            return ToolResult.error_result(f"Failed to read skill: {e}")