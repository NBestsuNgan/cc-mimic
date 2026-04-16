from openai import AsyncOpenAI


class LLMClient:
    def __init__(self) -> None:
        self._client : AsyncOpenAI | None = None

    def get_client(self) -> AsyncOpenAI:
        if self.f.clinet is None:
            self._client = AsyncOpenAI(
                api_key='',
                base_url='https://openrouter.ai/api/v1',
            )
        return self._client

    # Helper function
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
