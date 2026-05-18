from __future__ import annotations
import json
from typing import AsyncGenerator
from src.agent.events import AgentEvent, AgentEventType
from src.client.response import StreamEventType, ToolCall, ToolResultMessage
from src.config.config import Config
from src.agent.session import Session

class Agent:
    def __init__(self, config: Config):
        self.config = config
        # all of params encapsulated in session.
        self.session: Session | None = Session(self.config)

    async def run(self, message: str):
        yield AgentEvent.agent_start(message)

        # add user message to context
        self.session.context_manager.add_user_message(message)

        final_response: str | None = None
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        # agent will have microscopic detail that need to send to the UI in differnet actions
        # like start turning conversation, Ending turn conversation, tool calling
        max_turns = self.config.max_turns

        for turn_num in range(max_turns): # turns used for multi sequence of task like do 1 then 2 then 3 and stop when 3 complete
            self.session.increment_turn()
            response_text = ""
            tools_schemas = self.session.tool_registry.get_schemas()
            tool_calls: list[ToolCall] = []
            
            async for event in self.session.client.chat_completion(
                self.session.context_manager.get_messages(), 
                tools=tools_schemas if tools_schemas else None, 
            ):
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

    
            self.session.context_manager.add_assistant_message(
                    response_text or None,
                    (
                        [
                            {
                                "id": tc.call_id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in tool_calls
                        ]
                        if tool_calls
                        else None
                    ),
                )
            if response_text:
                yield AgentEvent.text_complete(response_text)
            
            if not tool_calls:
                return
            
            tool_call_results: list[ToolResultMessage] = []
            
            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(
                    call_id=tool_call.call_id,
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                )
                
                result = await self.session.tool_registry.invoke(
                    name=tool_call.name,
                    params=tool_call.arguments,
                    cwd=self.config.cwd,
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
                
            
            for tool_result in tool_call_results:
                self.session.context_manager.add_tool_result(
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
        if self.session and self.session.client:
            await self.session.client.close()
            self.session = None
