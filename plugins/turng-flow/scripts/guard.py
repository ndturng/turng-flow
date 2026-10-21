"""PreToolUse guard for turng-flow modes.

Which files each mode may change:

| Files                                                  | plan mode | work mode |
|--------------------------------------------------------|-----------|-----------|
| decision logs: BACKLOG.md, HISTORY.tsv, TASK_SPEC.md   | yes       | no        |
| rule files and design notes                            | yes       | no        |
| task records: other files in agent-workspace/tasks/    | yes       | yes       |
| .turng-flow/reports/ (trial and review reports)        | yes       | yes       |
| .turng-flow/ (owner's mode state)                      | no        | no        |
| everything else (code)                                 | no        | yes       |
| files outside the project (scratchpad, /tmp)           | yes       | yes       |

Shell commands are checked for signs of writing files; that check cannot see every way of writing,
so plan_check.py also compares git status at the end of each turn in plan mode.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import current_mode, state_dir  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DECISION_LOGS = ["agent-workspace/BACKLOG.md", "agent-workspace/HISTORY.tsv", "agent-workspace/tasks/*/TASK_SPEC.md"]
RULES_AND_DESIGN = ["AGENTS.md", "CLAUDE.md", ".claude/skills/*", ".claude/settings*.json", ".claude/hooks/*",
                    "agent-workspace/design-notes/*"]
TASK_RECORDS = ["agent-workspace/tasks/*"]
REPORTS = [".turng-flow/reports/*"]
OWNER_STATE = [".turng-flow/*", ".turng-flow"]

REDIRECT = re.compile(r"\d*>>?\s*(\S+)")
SHELL_WRITES = re.compile(
    r"\btee\b|\bsed\s+(-\w*\s+)*-i|\brm\b|\bmv\b|\bcp\b|\btouch\b|\bmkdir\b|\bpatch\b"
    r"|\bgit\s+(add|commit|push|checkout|switch|reset|restore|stash|merge|rebase|apply|am|cherry-pick|rm|mv)\b"
)


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def relative(path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(project_root()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def matches(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def kind(rel: str) -> str:
    if matches(rel, REPORTS):
        return "report"
    if matches(rel, OWNER_STATE):
        return "owner-state"
    if matches(rel, DECISION_LOGS):
        return "decision-log"
    if matches(rel, RULES_AND_DESIGN):
        return "rules-or-design"
    if matches(rel, TASK_RECORDS):
        return "task-record"
    return "code"


def allowed(rel: str, mode: str) -> bool:
    if Path(rel).is_absolute():
        return True
    k = kind(rel)
    if k == "owner-state":
        return False
    if k in ("task-record", "report"):
        return True
    if mode == "plan":
        return k in ("decision-log", "rules-or-design")
    return k == "code"


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
    mode = current_mode(state_dir())

    if tool in EDIT_TOOLS:
        rel = relative(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if allowed(rel, mode):
            return
        k = kind(rel)
        if k == "owner-state":
            deny("turng-flow: .turng-flow/ is controlled by the owner's commands. "
                 "Ask the owner to run /turng-flow:plan-mode or /turng-flow:work-mode.")
        if mode == "plan":
            deny(f"turng-flow plan mode: {rel} cannot be changed in plan mode. Propose the approach; "
                 "when the owner agrees, ask the owner to run /turng-flow:work-mode.")
        deny(f"turng-flow work mode: {rel} is a {k.replace('-', ' ')} file and cannot be changed in work mode. "
             "If it needs to change, stop and ask the owner to run /turng-flow:plan-mode.")

    if tool == "Bash":
        command = tool_input.get("command", "")
        if not writes_files(command):
            return
        if ".turng-flow" in command:
            deny("turng-flow: .turng-flow/ is controlled by the owner's commands.")
        if mode == "plan":
            deny("turng-flow plan mode: shell commands that change files or git state are blocked. "
                 "Use the Edit tool for decision logs; ask the owner to run /turng-flow:work-mode for code.")
        protected = DECISION_LOGS + RULES_AND_DESIGN
        names = {Path(p).name.replace("*", "") for p in protected}
        if any(n and n in command for n in names) or "design-notes" in command:
            deny("turng-flow work mode: this command seems to change a decision log, rule file, or design "
                 "note. Those cannot change in work mode; ask the owner to run /turng-flow:plan-mode.")


if __name__ == "__main__":
    main()
