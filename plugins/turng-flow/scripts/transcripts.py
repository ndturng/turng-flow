"""Read Claude Code session transcripts of a project.

Transcripts live in ~/.claude/projects/<project path with every non-alphanumeric character as "-">/.
Only the main conversation is read (no subagent side chains).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Blocks the editor or harness inserts into an owner message; they are not the owner's words.
INJECTED = re.compile(r"<(ide_[a-z_]+|system-reminder|local-command-[a-z]+)>.*?</\1>", re.S)


def transcript_dir(project: Path) -> Path:
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(project.resolve()))


def parse_time(value: str) -> datetime:
    """Parse an ISO time; a time without an offset is taken as local time."""
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return t if t.tzinfo else t.astimezone()


def _text(content) -> str:
    if not isinstance(content, str):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return INJECTED.sub("", content).strip()


def events(folder: Path, since: datetime | None = None, until: datetime | None = None):
    """Yield owner messages, agent replies, and agent tool calls in time order.

    Each event: {"time", "session", "kind": "owner" | "dialog" | "agent" | "tool", "text", ...}.
    """
    found = []
    for path in sorted(folder.glob("*.jsonl")):
        for line in path.open(encoding="utf-8"):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("isSidechain") or rec.get("isMeta") or not rec.get("timestamp"):
                continue
            t = parse_time(rec["timestamp"])
            if (since and t <= since) or (until and t > until):
                continue
            base = {"time": t, "session": path.stem}
            msg = rec.get("message") or {}
            if rec.get("type") == "user":
                if (rec.get("origin") or {}).get("kind") == "human":
                    text = _text(msg.get("content", ""))
                    if text:
                        found.append({**base, "kind": "owner", "text": text})
                result = rec.get("toolUseResult")
                if isinstance(result, dict) and isinstance(result.get("answers"), dict):
                    for question, answer in result["answers"].items():
                        found.append({**base, "kind": "dialog", "text": str(answer), "question": str(question)})
            elif rec.get("type") == "assistant":
                text = _text(msg.get("content", ""))
                if text:
                    found.append({**base, "kind": "agent", "text": text})
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        found.append({**base, "kind": "tool", "tool": block.get("name", ""),
                                      "text": json.dumps(block.get("input", {}), ensure_ascii=False)[:300]})
    found.sort(key=lambda e: e["time"])
    return found


def now() -> datetime:
    return datetime.now(timezone.utc)
