from src.tools.builtin.read_file import ReadFileTool
from src.tools.builtin.write_file import WriteFileTool

__all_ = [
    'ReadFileTool',
    'WriteFileTool'
]

def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool
    ]