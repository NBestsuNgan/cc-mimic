from __future__ import annotations
import abc
from enum import Enum
from typing import Any
from pydantic import BaseModel, ValidationError
from pydantic.json_schema import model_json_schema
from dataclasses import dataclass, field
from pathlib import Path


class ToolKind(Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MEMORY = "memory"
    MCP = "mcp"


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    truncated: bool = False

    @classmethod
    def error_result(
        cls, # mean the class it self "cls(...)  is the same as  ToolResult(...)"
        error: str,
        output: str = "",
        **kwargs: Any
    ):
        return cls(
            success=False,
            output=output,
            error=error,
            **kwargs,
        )
        # # without classmethod — verbose, repeating success=False every time
        # result = ToolResult(success=False, output="", error="something went wrong")

        # # with classmethod — cleaner shortcut
        # result = ToolResult.error_result(error="something went wrong")

    @classmethod
    def success_result(
        cls, 
        output: str,
        **kwargs: Any,
    ):
        return cls(
            success=True,
            output=output,
            error=None,
            **kwargs,
        )
    
@dataclass
class ToolConfirmation:
    tool_name: str
    params: dict[str, Any]
    description: str


@dataclass
class ToolInvocation:
    params: dict[str, Any]
    cwd: Path


class  Tool(abc.ABC):
    name: str = "base_tool"
    description: str = "Base tool"
    kind: ToolKind = ToolKind.READ

    def __init__(self) -> None:
        pass

    @property
    def schema(self) -> dict[str, Any] | type["BaseModel"]:
        raise NotImplementedError(
            "Tool must define schema property or class atttribute"
        )

    @abc.abstractmethod
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        schema = self.schema

        # pydantic schema validation
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                schema(**params)
            except ValidationError as e:
                errors = []
                for error in e.errors():
                    field = ".".join(
                        str(x) for x in error.get("loc", [])
                    )  # "loc" stand for location, finding where validation error occur in?
                    msg = error.get("msg", "Validation error")
                    errors.append(f"Parameter '{field}' : '{msg}'")

                return errors
            except Exception as e:
                return [str(e)]

        return []

    def is_mutating(self, params: dict[str, Any]) -> bool:
        return self.kind in {
            ToolKind.WRITE,
            ToolKind.SHELL,
            ToolKind.NETWORK,
            ToolKind.MEMORY,
        }

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolInvocation | None:
        if not self.is_mutating(invocation.params):
            return False

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Exceute {self.name}",
        )

    def to_openai_schema(self) -> dict[str, Any]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema = model_json_schema(schema, mode="serialization")
            
            # OpenAI Expecting tool passing schema
            return { 
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": json_schema.get("properties", {}),
                    "required": json_schema.get("required", []),
                }
            }
            
        # mcp cases
        if isinstance(schema, dict):
            result = {
                "name": self.name,
                "description": self.description,
            }
            
            if "parameters" in schema:
                result["parameters"] = schema["parameters"]
            else:
                result["parameters"] = schema
        
            return result
        
        raise ValueError(f"Invalid schema type for tool {schema}: {type(schema)}")
        
            
    