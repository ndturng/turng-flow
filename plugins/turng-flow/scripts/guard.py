"""PreToolUse guard for turng-flow modes.

Always: the agent may not write into .turng-flow/ (the owner switches modes by command).
Plan mode: the agent may not edit files, change files through the shell, or change git state.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import current_mode, state_dir  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
REDIRECT = re.compile(r"\d*>>?\s*(\S+)")
SHELL_WRITES = re.compile(
    r"\btee\b|\bsed\s+(-\w*\s+)*-i|\brm\b|\bmv\b|\bcp\b|\btouch\b|\bmkdir\b|\bpatch\b"
    r"|\bgit\s+(add|commit|push|checkout|switch|reset|restore|stash|merge|rebase|apply|am|cherry-pick|rm|mv)\b"
)


def writes_files(command: str) -> bool:
    for target in REDIRECT.findall(command):
        if not target.startswith("&") and target != "/dev/null":
            return True
    return bool(SHELL_WRITES.search(command))


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def main() -> None:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    command = tool_input.get("command", "") if tool == "Bash" else ""

    if (tool in EDIT_TOOLS and ".turng-flow" in path) or (".turng-flow" in command and writes_files(command)):
        deny("turng-flow: .turng-flow/ is controlled by the owner's commands. "
             "Ask the owner to run /turng-flow:plan-mode or /turng-flow:work-mode.")

    if current_mode(state_dir()) != "plan":
        return
    if tool in EDIT_TOOLS:
        deny("turng-flow plan mode: editing files is blocked. Propose the approach; "
             "when the owner agrees, ask the owner to run /turng-flow:work-mode.")
    if command and writes_files(command):
        deny("turng-flow plan mode: shell commands that change files or git state are blocked. "
             "Ask the owner to run /turng-flow:work-mode if this change is part of an agreed approach.")


if __name__ == "__main__":
    main()
