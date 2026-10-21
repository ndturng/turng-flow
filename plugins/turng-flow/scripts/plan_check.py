"""Stop hook: in plan mode, detect code files changed since the owner switched to plan mode.

The guard cannot see every way a shell command writes a file. This check compares git status with
the snapshot taken at the switch, ignores files that plan mode may change (decision logs, rule files,
design notes, task records), and makes the agent report any other change to the owner once.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from guard import allowed  # noqa: E402
from mode import current_mode, git_status, state_dir  # noqa: E402


def entry_path(line: str) -> str:
    path = line[3:].strip()
    return path.split(" -> ")[-1].strip('"')


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return
    d = state_dir()
    if current_mode(d) != "plan":
        return
    snapshot_file = d / "plan-snapshot.txt"
    before = snapshot_file.read_text(encoding="utf-8") if snapshot_file.exists() else ""
    now = git_status(d.parent)
    if now == before:
        return
    snapshot_file.write_text(now, encoding="utf-8")
    changed = sorted(set(now.splitlines()) - set(before.splitlines()))
    changed = [line for line in changed if not allowed(entry_path(line), "plan")]
    if not changed:
        return
    print(json.dumps({
        "decision": "block",
        "reason": "turng-flow plan mode: files changed during plan mode. Tell the owner exactly which "
                  "files changed and how, and do not change anything else. Changed entries in git status: "
                  + "; ".join(changed),
    }))


if __name__ == "__main__":
    main()
