from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from typing import Any, AsyncGenerator
from src.client.response import (
    StreamEventType,
    StreamEvent,
    TextDelta,
    TokenUsage,
    ToolCall,
    ToolCallDelta,
    parse_tool_call_arguments,
)
import asyncio
import json
import os
from src.config.config import Config


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retries: int = 3
        self.config = config

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    # Helper function
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    def _build_tools(self, tools: list[dict[str, Any]]):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for tool in tools
        ]

    async def chat_completion(
        self,
        messages: list[
            dict[str, Any]
        ],  # list of invocation message interaction will be send to llm
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        ### return vs yield ###
        # return — runs the function once, gives back one value, and the function is done forever.
        # yield — pauses the function, hands a value to the caller, then resumes from that exact point next time the caller asks for the next value. It can do this many times.
        client = self.get_client()
        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": stream,
        }

        if tools:
            kwargs["tools"] = self._build_tools(tools)
            kwargs["tool_choice"] = "auto"

        # print("\n===== OUTGOING API PAYLOAD =====", flush=True)
        # print(json.dumps(kwargs, indent=2, default=str), flush=True)
        # print("===== END PAYLOAD =====\n", flush=True)

        for attempt in range(self._max_retries + 1):
            try:
                if stream:
                    async for event in self._stream_response(
                        client, kwargs
                    ):  # private method
                        yield event
                else:
                    event = await self._non_stream_response(
                        client, kwargs
                    )  # private method
                    yield event  # different between yield and return is yield will go back to control(caller) and do what ever function need to complete the task then give the result and continue doing it until there no event
                return
            except RateLimitError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate limit exceeded: {e}",
                    )
                    return
            except APIConnectionError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Connection error: {e}",
                    )
                    return
            except APIError as e:
                error_detail = f"API error: {e} | status={getattr(e, 'status_code', '?')} | body={getattr(e, 'body', '?')} | message={getattr(e, 'message', '?')}"
                print(
                    error_detail, flush=True
                )  # print directly to stderr so you see it in CLI
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=error_detail,
                )
                return

    async def _stream_response(
        self, client: AsyncOpenAI, kwargs: dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:
        response = await client.chat.completions.create(**kwargs)

        finish_reason: str | None = None
        usage: TokenUsage | None = None
        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens,  # system prompt must be static because of KV-cache architect inside the model // WOW
                )

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )

            # open ai sdk .tool_calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index

                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                    # instead of taping indentation into idx not in tool_calls -> we will use this instead because of
                    # case1: argument attach with the same chunk that return tool_name calling -> taping indentation work because it is the same chunk
                    # case2: argument attach with the next chunk that return tool_name calling -> taping indentation not work because it is the next chunk and need to extent taping to catch arguments variable
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls[idx][
                                "name"
                            ] = tool_call_delta.function.name
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_START,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]["id"],
                                    name=tool_call_delta.function.name,
                                ),
                            )

                    if tool_call_delta.function.arguments:
                        tool_calls[idx][
                            "arguments"
                        ] += tool_call_delta.function.arguments

                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta=ToolCallDelta(
                                call_id=tool_calls[idx]["id"],
                                name=tool_call_delta.function.name,
                                arguments_delta=tool_call_delta.function.arguments,
                            ),
                        )

        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parse_tool_call_arguments(tc["arguments"]),
                ),
            )

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def _non_stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> StreamEvent:
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text_delta = None  # it gonna be really helpful with stream response, _delta refer to change so text_delta meaning text changed
        if message.content:
            text_delta = TextDelta(content=message.content)

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parse_tool_call_arguments(
                            tc.function.arguments
                        ),
                    )
                )

        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens,  # system prompt must be static because of KV-cache architect inside the model // WOW
            )

        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,  # message complet because it non-streaming response so that whole meta data come at once
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage,
        )
