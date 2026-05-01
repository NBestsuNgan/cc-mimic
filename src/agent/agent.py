from __future__ import annotations
from pathlib import Path
from typing import AsyncGenerator
from src.context.manager import ContextManager
from src.agent.events import AgentEvent, AgentEventType
from src.client.llm_client import LLMClient
from src.client.response import StreamEventType, ToolCall, ToolResultMessage
from src.tools.registry import create_default_registry


class Agent:
    def __init__(self):
        # all of params encapsulated in session.
        self.client = LLMClient()
        self.context_manager = ContextManager()
        self.tool_registry = create_default_registry()

    async def run(self, message: str):
        yield AgentEvent.agent_start(message)

        # add user message to context
        self.context_manager.add_user_message(message)

        final_response: str | None = None
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        # agent will have microscopic detail that need to send to the UI in differnet actions
        # like start turning conversation, Ending turn conversation, tool calling

        response_text = ""
        tools_schemas = self.tool_registry.get_schemas()
        tool_calls: list[ToolCall] = []
        
        async for event in self.client.chat_completion(
            self.context_manager.get_messages(), 
            tools=tools_schemas if tools_schemas else None, 
        ):
            print("="*50)
            print(event.type)
            print("="*50)
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(
                        content
                    )  # connect class from llm_client into agentevent seemlessly
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)
                    
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(
                    event.error or "Unkown error occured."
                )

        print("="*50)
        print(f"tool_calls : {tool_calls}")
        print("="*50)
        self.context_manager.add_assistant_message(
            response_text or None,
        )
        if response_text:
            yield AgentEvent.text_complete(response_text)
        
        tool_call_results: list[ToolResultMessage] = []
        
        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(
                call_id=tool_call.call_id,
                name=tool_call.name,
                arguments=tool_call.argument,
            )
            
            result = await self.tool_registry.invoke(
                name=tool_call.name,
                params=tool_call.argument,
                cwd=Path.cwd(),
            )
            
            yield AgentEvent.tool_call_complete(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result=result
            )
            
            tool_call_results.append(
                ToolResultMessage(
                    tool_call_id=tool_call.call_id,
                    content=result.to_model_output(),
                    is_error=not result.success
                )
            )
            
        print("="*50)
        print(tool_call_results)
        print("="*50)
        for tool_result in tool_call_results:
            self.context_manager.add_tool_result(
                tool_result.tool_call_id,
                tool_result.content,
            )

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(
        self,
        exc_type,  # exception type
        exc_val,  # exception value
        exc_tb,  # exception traceback
    ) -> None:
        if self.client:
            await self.client.close()
            self.client = None
