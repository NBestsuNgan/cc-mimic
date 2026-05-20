from src.tools.builtin.read_file import ReadFileTool
from src.tools.builtin.write_file import WriteFileTool
from src.tools.builtin.edit_file import EditTool

__all__ = [
    'ReadFileTool',
    'WriteFileTool',
    'EditTool',
]

def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
    ]