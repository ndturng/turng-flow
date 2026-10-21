"""UserPromptExpansion hook: when the owner runs /turng-flow:work-mode, store the agent's last
proposal as the approved scope in .turng-flow/approved-scope.md."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import state_dir  # noqa: E402


def last_agent_text(transcript: str) -> str:
    last = ""
    for line in open(transcript, encoding="utf-8"):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("type") != "assistant" or record.get("isSidechain"):
            continue
        content = (record.get("message") or {}).get("content") or []
        text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        if text.strip():
            last = text
    return last


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("command_name") != "turng-flow:work-mode":
        return
    scope = last_agent_text(data["transcript_path"]) if data.get("transcript_path") else ""
    stamp = datetime.now().isoformat(timespec="seconds")
    (state_dir() / "approved-scope.md").write_text(
        f"Approved by the owner's /turng-flow:work-mode at {stamp}.\n\n{scope}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
