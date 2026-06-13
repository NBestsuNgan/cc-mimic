#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from pathlib import Path

def main():
    trigger = os.environ.get("AI_AGENT_TRIGGER")
    cwd = os.environ.get("AI_AGENT_CWD")
    tool_name = os.environ.get("AI_AGENT_TOOL_NAME")
    user_message = os.environ.get("AI_AGENT_USER_MESSAGE")
    llm_response = os.environ.get("AI_AGENT_LLM_RESPONSE")
    error = os.environ.get("AI_AGENT_ERROR")

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "cwd": cwd,
        "tool_name": tool_name,
        "user_message": user_message,
        "llm_response": llm_response,
        "error": error,
    }

    # Clean cross-platform pathlib alternative to your string replace lines
    log_path = Path(cwd) / ".ai-agent" / "hook.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[HOOK] {json.dumps(log_data)}\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
