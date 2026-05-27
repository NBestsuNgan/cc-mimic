from src.tools.builtin.read_file import ReadFileTool
from src.tools.builtin.write_file import WriteFileTool
from src.tools.builtin.edit_file import EditTool
from src.tools.builtin.shell import ShellTool
from src.tools.builtin.list_dir import ListDirTool
from src.tools.builtin.grep import GrepTool
from src.tools.builtin.glob import GlobTool
from src.tools.builtin.web_search import WebSearchTool
from src.tools.builtin.web_fetch import WebFetchTool
from src.tools.builtin.todo import TodosTool
from src.tools.builtin.memory import MemoryTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
    "GlobTool",
    "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool"
]

def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]