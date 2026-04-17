from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Any, AsyncGenerator
from src.client.response import EventType, StreamEvent, TextDelta, TokenUsage

import os

load_dotenv()

CC_API_KEY = os.getenv("CC_API_KEY")

class LLMClient:
    def __init__(self) -> None:
        self._client : AsyncOpenAI | None = None

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=CC_API_KEY,
                base_url='https://openrouter.ai/api/v1',
            )
        return self._client

    # Helper function
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(
            self, 
            messages: list[dict[str, Any]], # list of invocation message interaction will be send to llm
            stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        ### return vs yield ###
        # return — runs the function once, gives back one value, and the function is done forever.
        # yield — pauses the function, hands a value to the caller, then resumes from that exact point next time the caller asks for the next value. It can do this many times.
        
        client = self.get_client()
        kwargs = {
            "model": "openrouter/elephant-alpha",
            "messages": messages,
            "stream": stream,
        }
        if stream:
            async for event in self._stream_response(client, kwargs): # private method
                yield event
        else:
            event = await self._non_stream_response(client, kwargs) # private method
            yield event # different between yield and return is yield will go back to control(caller) and do what ever function need to complete the task then give the result and continue doing it until there no event
        return
    
            
    async def _stream_response(
        self, 
        client: AsyncOpenAI, 
        kwargs: dict[str, Any]
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
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens # system prompt must be static because of KV-cache architect inside the model // WOW
                )
                
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            
            if delta.content:
                yield StreamEvent(
                    type=EventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )
                
        yield StreamEvent(
            type=EventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )
            

    async def _non_stream_response(
        self, 
        client: AsyncOpenAI, 
        kwargs: dict[str, Any]
    ) -> StreamEvent:
        response = await client.chat.completions.create(**kwargs) 
        choice = response.choices[0]
        message = choice.message
        
        text_delta = None # it gonna be really helpful with stream response, _delta refer to change so text_delta meaning text changed
        if message.content:
            text_delta = TextDelta(content=message.content)
        
        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens # system prompt must be static because of KV-cache architect inside the model // WOW
            )
            
        return StreamEvent(
            type=EventType.MESSAGE_COMPLETE, # message complet because it non-streaming response so that whole meta data come at once
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage,
        )
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        