from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agent_skills import Skill as AgentSkill

from src.config.config import Config
from src.tools.registry import ToolRegistry
from src.tools.skills.skill_tool import Skill, SkillInfo

logger = logging.getLogger(__name__)

SKILL_FILENAMES = {"skill.md"}
EXCLUDE_DIRS = {".venv", "node_modules", "__pycache__", ".git", "build"}


class SkillManager:
    def __init__(self, config: Config):
        self.config = config
        self._initialized = False
        self._skills: list[Skill] = []
        self._valid_skill_files: list[Path] = []

    async def initialize(self) -> None:
        if self._initialized:
            return

        for path in sorted(self.config.cwd.rglob("*.md")):
            if path.name.lower() not in SKILL_FILENAMES:
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            self._valid_skill_files.append(path)

        self._initialized = True

    def _validate(self, path: Path) -> SkillInfo | None:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Skill unreadable, skipping %s: %s", path, e)
            return None

        try:
            agent_skill = AgentSkill.from_skill_md(content)
        except (ValueError, Exception) as e:
            logger.warning("Invalid skill structure, skipping %s: %s", path, e)
            return None

        metadata = agent_skill.metadata
        if not metadata.name or not metadata.description:
            logger.warning(
                "Skill missing name/description, skipping %s", path
            )
            return None

        return SkillInfo(metadata.name, metadata.description, path)

    def register_skills(self, registry: ToolRegistry) -> int:
        if not self._initialized:
            return 0

        count = 0
        for path in self._valid_skill_files:
            info = self._validate(path)
            if info is None:
                continue

            skill = Skill(self.config, info)
            self._skills.append(skill)
            registry.register_skill(skill)
            count += 1

        return count
