"""UserPromptExpansion hook: when the owner runs /turng-flow:work-mode, store the agent's last
proposal as the approved scope in .turng-flow/approved-scope.md, and append it to
.turng-flow/approvals.md so /turng-flow:review-task can match each work-mode period to its approval."""
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
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    entry = f"Approved by the owner's /turng-flow:work-mode at {stamp}.\n\n{scope}\n"
    d = state_dir()
    (d / "approved-scope.md").write_text(entry, encoding="utf-8")
    with (d / "approvals.md").open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {stamp}\n\n{entry}")


if __name__ == "__main__":
    main()
