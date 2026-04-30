from src.tools.builtin.read_file import ReadFileTool

__all_ = [
    'ReadFileTool'
]

def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        
    ]