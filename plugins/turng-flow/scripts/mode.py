"""Mode state for turng-flow, kept in <project>/.turng-flow/.

  mode.py set plan|work     called by the owner's /turng-flow:plan-mode and /turng-flow:work-mode
  mode.py reset             called at session startup: back to plan mode

Only the owner's commands and the plugin's hooks call this script. The guard hook blocks the agent
from writing into .turng-flow/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MODES = ("plan", "work")


def state_dir() -> Path:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    d = root / ".turng-flow"
    d.mkdir(exist_ok=True)
    ignore = d / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    return d


def current_mode(d: Path) -> str:
    try:
        mode = json.loads((d / "mode.json").read_text(encoding="utf-8"))["mode"]
    except (OSError, ValueError, KeyError):
        return "plan"
    return mode if mode in MODES else "plan"


def git_status(root: Path) -> str:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def set_mode(mode: str, source: str) -> None:
    d = state_dir()
    record = {"mode": mode, "set_at": datetime.now().isoformat(timespec="seconds"), "set_by": source}
    (d / "mode.json").write_text(json.dumps(record) + "\n", encoding="utf-8")
    if mode == "plan":
        (d / "plan-snapshot.txt").write_text(git_status(d.parent), encoding="utf-8")
    print(f"turng-flow mode is now: {mode}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "set" and sys.argv[2] in MODES:
        set_mode(sys.argv[2], "owner command")
    elif len(sys.argv) == 2 and sys.argv[1] == "reset":
        set_mode("plan", "session start")
    else:
        sys.exit("usage: mode.py set plan|work | mode.py reset")
