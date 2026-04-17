from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass
class TextDelta: # can be extend later, like content is not enough and want to add more
    content: str
    def __str__(self):
        return self.content

@dataclass
class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"

@dataclass
class TokenUsage:
    prompt_tokens: int = 0 # system prompt will also count as prompt_tokens
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    
    def __add__(self, other: TokenUsage): # other represent to another instance of TokenUsage class that will be perform calculation together
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )

@dataclass
class StreamEvent:
    type: EventType
    text_delta: TextDelta | None = None # text delta is any text text that model has provide to you
    error: str | None = None
    finish_reason : str | None = None
    usage: TokenUsage | None = None
    
    
    
    
    
    
    
    
    
    
    