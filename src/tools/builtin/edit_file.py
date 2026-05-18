from pydantic import BaseModel, Field
from pathlib import Path
from src.tools.base import FileDiff, Tool, ToolInvocation, ToolKind, ToolResult
from src.utils.paths import (
    ensure_parent_directory,
    resolve_path,
    is_binary_file,
)
from src.utils.text import count_tokens, truncate_text


class EditParams(BaseModel):
    path: str = Field(
        ...,  # ... mean this field is required
        description="Path to the file to edit (relative to working directory or absolute path)",
    )
    old_string: str = Field(
        "",
        description="The exact text to find and replace. Must match exactly including all whitespace and indentation. For new files, leave this empty.",
    )
    new_string: str = Field(
        ...,
        description="The text to replace the old string with. Can be empty to delete text.",
    )
    replace_all: bool = Field(
        False,
        description="Replace all occurrences of old_string (default: false)",
    )


class EditTool(Tool):
    name = "edit"
    description = (
        "Edit a file by replacing text. The old_string must match exactly "
        "(including whitespace and indentation) and must be unique in the file "
        "unless replace_all is true. Use this for precise, surgical edits. "
        "For creating new files or complete rewrites, use write_file instead."
    )
    kind = ToolKind.WRITE
    schema = EditParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = EditParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            if params.old_string:
                return ToolResult.error_result(
                    f"File does not exist: {path}. To create a new file, use an empty old_string."
                )

            ensure_parent_directory(path)
            path.write_text(params.new_string, encoding="utf-8")
            line_count = len(params.new_string.splitlines())
            return ToolResult.success_result(
                f"Created {path} ({line_count} lines)",
                diff=FileDiff(
                    path=str(path),
                    old_content="",
                    new_content=params.new_string,
                    is_new_file=True,
                ),
                metadata={
                    "path": str(path),
                    "is_new_file": True,
                    "line_count": line_count,
                },
            )

        old_content = path.read_text(encoding="utf-8")

        if not params.old_string: # if model return old_string is empty but file already exist, we should not edit it because we don't know what to edit, so we return error
            return ToolResult.error_result(
                f"Old string is empty but file already exists. Provide old_string to edit, or use write_file to overwrite."
            )
        
        occurrences_count = old_content.count(params.old_string) 
        if occurrences_count == 0:# old_string not found in file
            # → the file may have changed since the model last read it -> so it need to read again
            #   or the model hallucinated/mis-remembered the text
            return self._no_match_error(params.old_string, old_content, path)
    
    def _no_match_error(self, old_string: str, content: str, path: Path) -> ToolResult:
        lines = content.splitlines()

        partial_matches = []
        search_terms = old_string.split()[:5]

        if search_terms:
            first_term = search_terms[0]
            for i, line in enumerate(lines, 1):
                if first_term in line:
                    partial_matches.append((i, line.strip()[:80]))
                    if len(partial_matches) >= 3:
                        break

        error_msg = f"old_string not found in {path}."

        if partial_matches:
            error_msg += "\n\nPossible similar lines:"
            for line_num, line_preview in partial_matches:
                error_msg += f"\n  Line {line_num}: {line_preview}"
            error_msg += "\n\nMake sure old_string matches exactly (including whitespace and indentation)."
        else:
            error_msg += (
                " Make sure the text matches exactly, including:\n"
                "- All whitespace and indentation\n"
                "- Line breaks\n"
                "- Any invisible characters\n"
                "Try re-reading the file using read_file tool and then editing."
            )

        return ToolResult.error_result(error_msg)
