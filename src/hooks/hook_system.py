import asyncio
import os
import sys
import signal
import tempfile
import logging
from typing import Any
import json
from src.config.config import Config, HookConfig, HookTrigger
from src.tools.base import ToolResult

logger = logging.getLogger(__name__)


class HookSystem:
    def __init__(self, config: Config):
        self.config = config
        self.hooks: list[HookConfig] = []
        # logger.info(f"HookSystem init: hooks_enabled={config.hooks_enabled}, hooks_count={len(config.hooks)}, cwd={config.cwd}")

        if self.config.hooks_enabled:
            self.hooks = [hook for hook in self.config.hooks if hook.enabled]
            # logger.info(f"Loaded {len(self.hooks)} enabled hooks")
        else:
            logger.warning("Hooks are DISABLED - no hooks will be triggered")

    async def _run_hook(self, hook: HookConfig, env: dict[str, str]) -> None:
        # logger.info(f"Triggering hook: {hook.name} ({hook.trigger.value})")
        try: 
            if hook.command:
                await self._run_command(hook.command, hook.timeout_sec, env)
            else:
                # .sh -> script
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".sh", delete=True
                ) as f:
                    f.write("#!/bin/bash\n")
                    f.write(hook.script)
                    script_path = f.name
                    try:
                        # chmod = change mode
                        os.chmod(
                            script_path, 0o755
                        )  # 0o(oct number) + 7(user permission read, write, execute) + 5(group permission but no write acess) + 5(same)
                        await self._run_command(script_path, hook.timeout_sec, env)
                    finally:
                        pass

            # # .sh -> script
            # with tempfile.NamedTemporaryFile(
            #     mode="w", suffix=".sh", delete=False
            # ) as f:
            #     f.write("#!/bin/bash\n")
            #     f.write(hook.script)
            #     script_path = f.name
            # try:
            #     # chmod = change mode
            #     os.chmod(
            #         script_path, 0o755
            #     )  # 0o(oct number) + 7(user permission read, write, execute) + 5(group permission but no write acess) + 5(same)
            #     await self._run_command(script_path, hook.timeout_sec, env)
            # finally:
            #     os.unlink(script_path)
        except Exception as e:
            logger.error(f"Hook {hook.name} failed: {e}")


            

    async def _run_command(
        self, command: str, timeout: float, env: dict[str, str]
    ) -> None:
        # logger.info(f"Running hook command: {command}, cwd={self.config.cwd}")

        # If the user wrote 'python ...' in config.toml, swap to sys.executable
        # so the hook uses the same Python interpreter as the agent.
        resolved = command
        use_exec = False
        exec_args = None

        if resolved.startswith("python ") or resolved.startswith("python3 "):
            python_path = sys.executable
            # On Windows, always use exec to handle special characters like
            # parentheses in the path (e.g., username with parentheses)
            if sys.platform == "win32":
                args = resolved[resolved.index(" "):].strip().split()
                exec_args = [python_path] + args
                use_exec = True
                # logger.info(f"Using exec with args: {exec_args}")
            else:
                if " " in python_path:
                    python_path = f'"{python_path}"'
                resolved = python_path + resolved[resolved.index(" "):]

        # logger.info(f"Resolved hook command: {resolved}")

        try:
            if use_exec:
                process = await asyncio.create_subprocess_exec(
                    *exec_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.config.cwd,
                    env=env,
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    resolved,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.config.cwd,
                    env=env,
                    start_new_session=(sys.platform != "win32"),
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                if process.returncode != 0:
                    logger.warning(f"Hook command failed (rc={process.returncode}): {stderr.decode()}")
                else:
                    pass
                    # logger.info(f"Hook command succeeded: {stdout.decode().strip()}")
            except asyncio.TimeoutError:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
                await process.wait()
                logger.warning(f"Hook command timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Hook command error: {e}")

    def _build_env(
        self,
        trigger: HookTrigger,
        tool_name: str | None = None,
        user_message: str | None = None,
        error: Exception | None = None,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env["AI_AGENT_TRIGGER"] = trigger.value
        env["AI_AGENT_CWD"] = str(self.config.cwd)
        if tool_name:
            env["AI_AGENT_TOOL_NAME"] = tool_name
        if user_message:
            env["AI_AGENT_USER_MESSAGE"] = user_message
        if error:
            env["AI_AGENT_ERROR"] = str(error)
        return env

    async def trigger_before_agent(
        self,
        user_message: str,
    ) -> None:
        env = self._build_env(
            HookTrigger.BEFORE_AGENT, user_message=user_message
        )
        for hook in self.hooks:
            if hook.trigger == HookTrigger.BEFORE_AGENT:
                await self._run_hook(hook, env)

    async def trigger_after_agent(
        self,
        user_message: str,
        agent_response: str,
    ) -> None:
        env = self._build_env(
            HookTrigger.AFTER_AGENT, user_message=user_message
        )
        env["AI_AGENT_RESPONSE"] = agent_response
        for hook in self.hooks:
            if hook.trigger == HookTrigger.AFTER_AGENT:
                await self._run_hook(hook, env)

    async def trigger_before_llm(
        self,
        user_message: str,
    ) -> None:
        env = self._build_env(
            HookTrigger.BEFORE_LLM, user_message=user_message
        )
        for hook in self.hooks:
            if hook.trigger == HookTrigger.BEFORE_LLM:
                await self._run_hook(hook, env)

    async def trigger_after_llm(
        self,
        user_message: str,
        llm_response: str,
    ) -> None:
        env = self._build_env(
            HookTrigger.AFTER_LLM, user_message=user_message
        )
        env["AI_AGENT_LLM_RESPONSE"] = llm_response
        for hook in self.hooks:
            if hook.trigger == HookTrigger.AFTER_LLM:
                await self._run_hook(hook, env)

    async def trigger_before_tool(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
    ) -> None:
        env = self._build_env(HookTrigger.BEFORE_TOOL, tool_name=tool_name)
        env["AI_AGENT_TOOL_PARAMS"] = json.dumps(tool_params)
        for hook in self.hooks:
            if hook.trigger == HookTrigger.BEFORE_TOOL:
                await self._run_hook(hook, env)

    async def trigger_after_tool(
        self,
        tool_name: str,
        tool_params: str,
        tool_result: ToolResult,
    ) -> None:
        env = self._build_env(HookTrigger.AFTER_TOOL, tool_name=tool_name)
        env["AI_AGENT_TOOL_PARAMS"] = json.dumps(tool_params)
        env["AI_AGENT_TOOL_RESULT"] = tool_result.to_model_output()
        for hook in self.hooks:
            if hook.trigger == HookTrigger.AFTER_TOOL:
                await self._run_hook(hook, env)

    async def trigger_on_error(
        self,
        error: Exception,
    ) -> None:
        env = self._build_env(HookTrigger.ON_ERROR, error=error)
        for hook in self.hooks:
            if hook.trigger == HookTrigger.ON_ERROR:
                await self._run_hook(hook, env)