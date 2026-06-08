from src.tools.base import ToolResult

BLOCLED_FILES = [
    ".env",
    "key",
    "keys"
]

class BlockedFile:
    def __init__(
            self,
            search_params: str,
            tool_name: str
        ):
        self.search_params = search_params
        self.tool_name = tool_name
    

    async def execute(self) -> ToolResult | None:
        for blcok_file in BLOCLED_FILES:
            if blcok_file in self.search_params:
                if self.tool_name == "read_file":
                    return ToolResult.error_result(f"Cannot read {blcok_file} file")
                elif self.tool_name == "shell":
                    return ToolResult.error_result(f"Command contain {blcok_file} related, Command cannot access {blcok_file} file")
                
        return None