from src.client.llm_client import LLMClient
import asyncio


async def main():
    client = LLMClient()
    messages = [{
        'role': 'user',
        'content': 'what up!'
    }]
    async for event in client.chat_completion(messages, False):
        print(event)

    print('done')
    
asyncio.run(main())