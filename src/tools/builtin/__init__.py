from src.tools.builtin.read_file import ReadFileTool
from src.tools.builtin.write_file import WriteFileTool
from src.tools.builtin.edit_file import EditTool
from src.tools.builtin.shell import ShellTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
]

def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
    ]