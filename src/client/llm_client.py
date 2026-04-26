from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from typing import Any, AsyncGenerator
from src.client.response import (
    StreamEventType,
    StreamEvent,
    TextDelta,
    TokenUsage,
)
import asyncio
import os

load_dotenv()

CC_API_KEY = os.getenv("CC_API_KEY")


class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retires: int = 3

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=CC_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
        return self._client

    # Helper function
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(
        self,
        messages: list[
            dict[str, Any]
        ],  # list of invocation message interaction will be send to llm
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        ### return vs yield ###
        # return — runs the function once, gives back one value, and the function is done forever.
        # yield — pauses the function, hands a value to the caller, then resumes from that exact point next time the caller asks for the next value. It can do this many times.
        client = self.get_client()
        kwargs = {
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "messages": messages,
            "stream": stream,
        }
        for attempt in range(self._max_retires + 1):
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
                if attempt < self._max_retires:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate limit exceeded {e}",
                    )
                    return
            except APIConnectionError as e:
                if attempt < self._max_retires:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Connection error: {e}",
                    )
                    return
            except APIError as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"API error: {e}",
                )
                return

    async def _stream_response(
        self, client: AsyncOpenAI, kwargs: dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:
        response = await client.chat.completions.create(**kwargs)

        finish_reason: str | None = None
        usage: TokenUsage | None = None

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

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def _non_stream_response(
        self, client: AsyncOpenAI, kwargs: dict[str, Any]
    ) -> StreamEvent:
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text_delta = None  # it gonna be really helpful with stream response, _delta refer to change so text_delta meaning text changed
        if message.content:
            text_delta = TextDelta(content=message.content)

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
