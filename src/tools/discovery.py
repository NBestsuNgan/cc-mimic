from pathlib import Path
import importlib.util
import inspect
from src.config.config import Config
from src.config.loader import get_config_dir
from src.tools.registry import ToolRegistry
from src.tools.base import Tool
from typing import Any
import sys


class ToolDiscoveryManager:
    def __init__(self, config: Config, registry: ToolRegistry):
        self.config = config
        self.registry = registry

    def _load_tool_modules(self, file_path: Path) -> Any:
        module_name = f"discovered_tool_{file_path.stem}"  # .ai-agent/tools/test_tool.py -> test_tool
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        if spec is None or spec.loader is None:
            return ImportError(f"Could not load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(
            module
        )  # read python file, execute all the code in it, and put all the classed, fucntion, variables into our module object

        # after this "module.TestTool" -> "discovered_tool_test_tool.TestTool" is be able to.
        return module

    def _find_tools_classes(self, module: Any) -> list[Tool]:
        tools: list[Tool] = []
        for name in dir(module):
            obj = getattr(module, name)  # discovered_tool_test_tool.TestTool
            if (
                inspect.isclass(obj)
                and issubclass(obj, Tool)
                and obj is not Tool                     # make sure it's not the base Tool class itself
                and obj.__module__ == module.__name__  # make sure the class is defined in the current module, not imported from somewhere else
            ):
                tools.append(obj)
        
        return tools

    def discovery_from_directory(self, directory: Path) -> None:
        tool_dir = directory / ".ai-agent" / "tools"

        if not tool_dir.exists() or not tool_dir.is_dir():
            return

        for py_file in tool_dir.glob("*.py"):  # **/.*py
            try:
                if py_file.name.startswith("__"):
                    continue

                module = self._load_tool_modules(py_file)
                tool_classes = self._find_tools_classes(module)
                
                if not tool_classes:
                    continue
            
                for tool_class in tool_classes:
                    tool = tool_class(self.config)  
                    self.registry.register(tool)
                    
            except Exception as e:
                print(f"Error loading tools from {py_file}: {e}")
                continue

    def discover_all(self) -> None:  # register all tools after discovering them
        self.discovery_from_directory(self.config.cwd)
        self.discovery_from_directory(get_config_dir())