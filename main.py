from typing import Any
import asyncio
import click
import sys
from src.agent.events import AgentEventType
from src.agent.agent import Agent
from src.client.llm_client import LLMClient
from src.ui.tui import TUI, get_console

console = get_console()

class CLI:
    def __init__(self):
        self.agent: Agent | None = None
        self.tui = TUI(console)

    async def run_single(self, message: str) -> str | None:
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)
            
    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None
        
        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            print(event)
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                # first message that user have
                if not assistant_streaming: 
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
                
        
        return final_response
        
        

@click.command()  # denote that this is a command executable
@click.argument("prompt", required=False)
def main(prompt: str | None):
    cli = CLI()
    # messages = [{"role": "user", "content": prompt}]
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)

main()
