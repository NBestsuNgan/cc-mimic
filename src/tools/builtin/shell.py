import fnmatch
import os
import sys
import asyncio
import signal
from pydantic import BaseModel, Field
from src.tools.base import Tool, ToolInvocation, ToolKind, ToolResult, ToolConfirmation
from pathlib import Path

BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

class ShellParams(BaseModel):
    command: str = Field(
        ...,
        description="The shell command to execute",
    )
    timeout: int = Field(
        120,
        ge=1,
        le=600,
        description="Timeout in seconds (default: 120)"
    )
    cwd: str | None = Field(
        None,
        description="The working directory for the command."
    )


class ShellTool(Tool):
    name = "shell"
    description = (
        "Execute a shell command. Use this for running system commands, script and CLI tools."
    )
    kind = ToolKind.SHELL
    schema = ShellParams

    async def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation | None:
        params = ShellParams(**invocation.params)
        command = params.command.lower().strip()
        
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return ToolConfirmation(
                    tool_name=self.name,
                    params=invocation.params,
                    description=f"Execute (BLOCKED): {command}",
                    command=command,
                    is_dangerous=True, 
                )
        
        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute: {command}",
            command=command,
        )
    
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)
        command = params.command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult(
                    f"Command blocked for safety: {params.command}",
                    metadata={"blocked": True}
                )

        if params.cwd:
            cwd = Path(params.cwd)
            if not cwd.is_absolute():
                cwd = invocation.cwd / cwd
        else:
            cwd = invocation.cwd

        if not cwd.exists(): # Check if the directory exists or not bacause it can not exist due to LLM hallucination
            return ToolResult(
                f"Working directory does not exist: {cwd}",
            )
        

        env = self._build_environment()
        if sys.platform == "win32":
            shell_cmd = ["cmd.exe", "/c", params.command]
        else:
            shell_cmd = ["/bin/bash", "-c", params.command]

        process = await asyncio.create_subprocess_exec(
            # spawn a new operating system process
            # benefit: it does not block the event loop
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE, # it allows us to capture the output of the command via 'process.stdout'
            stderr=asyncio.subprocess.PIPE, # it allows us to capture the error output of the command via 'process.stderr'
            cwd=cwd,
            env=env,
            start_new_session=True, # it allows us to kill the process and its children if timeout happens
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), # as soon as this coroutine is complete we will get 2 things which is bytes
                timeout=params.timeout,
            )
        except asyncio.TimeoutError:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL) # SIGKILL mean we want to kill this unix operating system
            else:
                process.kill() # for windows we just kill the process, it will automatically kill the children processes as well
            await process.wait() # wait for the process
            return ToolResult.error_result(f"Command timed out after {params.timeout}s")

        stdout = stdout_data.decode("utf-8", errors="replace") # if some byte have issue when decoding, instead of returning Unicode error, just replace that byte that will cause the error for us
        stderr = stderr_data.decode("utf-8", errors="replace")
        exit_code = process.returncode # 0 -> sucess, else -> failure
        output = ""
        if stdout.strip():
            output += stdout.rstrip()

        if stderr.strip():
            output += "\n--- stderr ---\n"
            output += stderr.rstrip()

        if exit_code != 0:
            output += f"\nExit code: {exit_code}"

        if len(output) > 100*1024: # greate than 100 kb
            output = output[:100*1024] + "\n... [output truncated]"

        return ToolResult(
            success=exit_code==0,
            output=output,
            error=stderr if exit_code != 0 else None,
            exit_code=exit_code,
        )


    def _build_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        shell_environment = self.config.shell_environment
        if not shell_environment.ignore_default_excludes:
            for pattern in shell_environment.exclude_patterns:
                keys_to_remove = [k for k in env.keys() if fnmatch.fnmatch(k.upper(), pattern.upper())]

                for k in keys_to_remove:
                    del env[k] 

        if shell_environment.set_vars:
            env.update(shell_environment.set_vars)
        return env
