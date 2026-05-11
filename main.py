from typing import Any
import asyncio
import click
import sys
from pathlib import Path
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

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            title="AI Agent",
            lines=[
                f"model: openrouter/owl-alpha",
                f"cwd: {Path.cwd()}",
                f"command: /help /config /approve /model /exit",
            ],
        )
        async with Agent() as agent:
            self.agent = agent
            while True:
                try:
                    user_input = console.input("\n[user]> [/user]").strip()
                    if not user_input:
                        continue
                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break

        console.print("\n[dim]Goodbye![/dim]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool_kind = None
        tool = self.agent.tool_registry.get(tool_name)
        if not tool:
            tool_kind = None
        tool_kind = tool.kind.value
        return tool_kind

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None

        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
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
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    call_id=event.data.get("call_id", ""),
                    name=tool_name,
                    tool_kind=tool_kind,
                    arguments=event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    call_id=event.data.get("call_id", ""),
                    name=tool_name,
                    tool_kind=tool_kind,
                    success=event.data.get("success", False),
                    output=event.data.get("output", ""),
                    error=event.data.get("error"),
                    metadata=event.data.get("metadata"),
                    truncated=event.data.get("truncated", False),
                )

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
    else:
        asyncio.run(cli.run_interactive())


main()
