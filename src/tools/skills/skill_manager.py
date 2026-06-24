from src.config.config import Config
from src.tools.registry import ToolRegistry
from src.tools.skills.skill_tool import Skill, SkillInfo
from src.utils.paths import load_frontmatter
import asyncio
from pathlib import Path
from typing import Any
import yaml
import os

class SkillManager:
    def __init__(self, config: Config):
        self.config = config
        self._initialized = False
        self._skills: list[Skill] = []
        self._valid_skills_folder: list[Path] = []
    
    async def initialize(self) -> None:
        # list all available skill in the repository
        EXCEPT_STRUCTURE = [
            ".venv",
            "src|tools|skills",
        ]
        if self._initialized:
            return
        
        skills_folders = list(self.config.cwd.rglob("skills"))
        for folder in skills_folders:
            count_except = 0
            search_folder = str(folder).replace("/", "|").replace("\\", "|")
            for skip_search in EXCEPT_STRUCTURE:
                if skip_search in search_folder:
                    count_except += 1
                    break
            if count_except > 0:
                continue
            self._valid_skills_folder.append(folder)
        self._initialized = True

    def register_skills(self, registry: ToolRegistry) -> int:
        count = 0

        for skill_folder in self._valid_skills_folder:
            name=""
            description=""
            path=""
            for item in skill_folder.rglob("*.md"):
                meta_data, _ = load_frontmatter(item)
                name = meta_data["name"]
                description = meta_data["description"]
                path = item
                
            if name and description and path:
                skill_info = SkillInfo(name, description, path)
                skill = Skill(self.config, skill_info)
                self._skills.append(skill)

        for skill in self._skills:      
            registry.register_skill(skill) 
            count += 1

        return count
