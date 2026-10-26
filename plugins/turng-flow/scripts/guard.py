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
| the turng-flow plugin: its repository and the installed | no        | no        |
|   copy (when the project is not the plugin repository)  |           |           |

Shell commands are checked for signs of writing files; that check cannot see every way of writing,
so plan_check.py also compares git status at the end of each turn in plan mode.

In plan mode the agent may invoke only turng-flow skills with the Skill tool; a command the owner types
does not go through this hook. Known limits of the shell
check in work mode: a command that reaches the plugin repository only through a relative path or a quoted
"$HOME" passes; a command that only names the plugin repository (a read with a redirect to /tmp, a commit
message) is denied.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import current_mode, project_root, state_dir  # noqa: E402

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
    r"|\bgit\s+(?:-[cC]\s+\S+\s+|--\S+\s+)*(add|commit|push|checkout|switch|reset|restore|stash|merge|rebase|apply|am|cherry-pick|rm|mv)\b"
)


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


def plugin_repo() -> Path | None:
    try:
        return Path(json.loads((Path.home() / ".claude/turng-flow.json").read_text(encoding="utf-8"))["repo"]).expanduser().resolve()
    except (OSError, ValueError, KeyError):
        return None


def in_plugin_repo() -> bool:
    """Whether the project is a checkout of the turng-flow plugin repository."""
    try:
        market = json.loads((project_root() / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return market.get("name") == "turng-flow"


def plugin_roots() -> list[Path]:
    """The installed copy of the plugin, and the plugin repository when ~/.claude/turng-flow.json names it."""
    roots = [Path(__file__).resolve().parent.parent]
    repo = plugin_repo()
    if repo:
        roots.append(repo)
    return [r for r in roots if not same_repo(r, project_root()) and not project_root().is_relative_to(r)]


def plugin_file(path: str) -> bool:
    """An absolute path inside the plugin, seen from another project. The agent never writes there: the skill
    turng-flow:update-plugin hands the owner a change package instead."""
    return Path(path).is_absolute() and any(Path(path).resolve().is_relative_to(r) for r in plugin_roots())


def same_repo(repo: Path, project: Path) -> bool:
    """Whether the project is the plugin repository or one of its git worktrees."""
    out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=project,
                         capture_output=True, text=True)
    return project == repo or (out.returncode == 0 and Path(out.stdout.strip()).resolve() == (repo / ".git").resolve())


def names_plugin_repo(command: str) -> bool:
    """Whether a shell command names the plugin repository, in any of the forms an agent writes it."""
    roots = plugin_roots()
    if not roots:
        return False
    forms = set() if in_plugin_repo() else {"plugins/turng-flow"}
    for root in roots:
        forms.add(str(root))
        if root.is_relative_to(Path.home()):
            rest = root.relative_to(Path.home()).as_posix()
            forms |= {f"~/{rest}", f"$HOME/{rest}", f"${{HOME}}/{rest}"}
    return any(f in command for f in forms)


REQUIRED_SKILLS = [
    ("agent-workspace/BACKLOG.md", "turng-flow:backlog-write"),
    ("agent-workspace/HISTORY.tsv", "turng-flow:project-history"),
    ("agent-workspace/tasks/*/TASK_SPEC.md", "turng-flow:task-record"),
]
HISTORY_SCRIPT_ADD = re.compile(r"\bhistory\.py[\"']?\s+add\b")


def required_skill(rel: str) -> str | None:
    return next((skill for pattern, skill in REQUIRED_SKILLS if fnmatch.fnmatch(rel, pattern)), None)


def skills_since_owner(transcript: str | None) -> set[str] | None:
    """Skills the agent ran since the owner's last message; None when the transcript cannot be read."""
    try:
        lines = open(transcript, encoding="utf-8").readlines() if transcript else None
    except OSError:
        return None
    if lines is None:
        return None
    ran: set[str] = set()
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("isSidechain"):
            continue
        if rec.get("type") == "user" and (rec.get("origin") or {}).get("kind") == "human":
            ran = set()
        elif rec.get("type") == "assistant":
            for block in (rec.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                    ran.add(str((block.get("input") or {}).get("skill", "")))
    return ran


def require_skill(skill: str, target: str, transcript: str | None) -> None:
    ran = skills_since_owner(transcript)
    if ran is not None and skill not in ran:
        deny(f"turng-flow: run the skill {skill} before changing {target}. Run it each time, even if it ran "
             "earlier in the session: its text may have been summarized out of the context.")


def allowed(rel: str, mode: str) -> bool:
    if Path(rel).is_absolute():
        return not plugin_file(rel)
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
            skill = required_skill(rel)
            if skill:
                require_skill(skill, rel, data.get("transcript_path"))
            return
        if plugin_file(rel):
            deny(f"turng-flow: {rel} is inside the turng-flow plugin. The agent does not write to the plugin; "
                 "use the skill turng-flow:update-plugin to hand the owner a change package.")
        k = kind(rel)
        if k == "owner-state":
            deny("turng-flow: .turng-flow/ is controlled by the owner's commands. "
                 "Ask the owner to run /turng-flow:plan-mode or /turng-flow:work-mode.")
        if mode == "plan":
            deny(f"turng-flow plan mode: {rel} cannot be changed in plan mode. Propose the approach; "
                 "when the owner agrees, ask the owner to run /turng-flow:work-mode.")
        deny(f"turng-flow work mode: {rel} is a {k.replace('-', ' ')} file and cannot be changed in work mode. "
             "If it needs to change, stop and ask the owner to run /turng-flow:plan-mode.")

    if tool == "Skill" and mode == "plan":
        skill = str(tool_input.get("skill", ""))
        if not skill.startswith("turng-flow:"):
            deny(f"turng-flow plan mode: the agent does not run other plugins' skills ({skill}) in plan mode. "
                 "Continue the discussion with the owner; the owner can still run a skill by typing its command.")
        return

    if tool == "Bash":
        command = tool_input.get("command", "")
        if HISTORY_SCRIPT_ADD.search(command):
            require_skill("turng-flow:project-history", "agent-workspace/HISTORY.tsv", data.get("transcript_path"))
        if not writes_files(command):
            return
        if ".turng-flow" in command:
            deny("turng-flow: .turng-flow/ is controlled by the owner's commands.")
        if mode == "plan":
            deny("turng-flow plan mode: shell commands that change files or git state are blocked. "
                 "Use the Edit tool for decision logs; ask the owner to run /turng-flow:work-mode for code.")
        if names_plugin_repo(command):
            deny("turng-flow: this command seems to change the turng-flow plugin. The agent does not write to the "
                 "plugin; use the skill turng-flow:update-plugin to hand the owner a change package.")
        protected = DECISION_LOGS + RULES_AND_DESIGN
        names = {Path(p).name.replace("*", "") for p in protected}
        # Inside the plugin repository, templates/AGENTS.md and templates/CLAUDE.md are code, as for the Edit tool.
        checked = re.sub(r"(?<!\S)(?:(?!\.\.)\S)*plugins/turng-flow/templates/(?:(?!\.\.)\S)*(?!\S)", "", command)
        if any(n and n in checked for n in names) or "design-notes" in checked:
            deny("turng-flow work mode: this command seems to change a decision log, rule file, or design "
                 "note. Those cannot change in work mode; ask the owner to run /turng-flow:plan-mode.")


if __name__ == "__main__":
    main()
