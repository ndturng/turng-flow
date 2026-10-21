"""Print every message the owner typed or chose in this project's Claude Code sessions, one JSON per line.

  owner_messages.py                 all owner messages
  owner_messages.py --before <ts>   the end of the agent reply just before the owner message at <ts>,
                                    to see what the owner was answering ("1. agreed" agreed to what).
                                    That text is context, never a source for quotes.

Source: ~/.claude/projects/<project path with every non-alphanumeric character as "-">/*.jsonl.
"message" = a message the owner typed; "dialog" = an answer the owner chose in a question box.
Agent text, tool results, system notices, and session summaries are not owner words.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from transcripts import events, transcript_dir  # noqa: E402

AGENT_TAIL = 3000


def repo_root(strict: bool = False) -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode == 0:
        return Path(out.stdout.strip())
    if strict:
        raise SystemExit("not inside a git repository")
    return Path.cwd()


def owner_messages(repo: Path, with_agent: bool = False):
    last_agent = ""
    for e in events(transcript_dir(repo)):
        if e["kind"] == "agent":
            last_agent = e["text"]
            continue
        if e["kind"] not in ("owner", "dialog"):
            continue
        msg = {"session": e["session"], "ts": e["time"].isoformat(), "text": e["text"],
               "kind": "message" if e["kind"] == "owner" else "dialog"}
        if e["kind"] == "dialog":
            msg["question"] = e["question"]
        if with_agent and e["kind"] == "owner":
            msg["agent_before"] = last_agent[-AGENT_TAIL:]
        yield msg


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--before":
        for msg in owner_messages(repo_root(), with_agent=True):
            if msg["ts"].startswith(sys.argv[2]) and msg["kind"] == "message":
                print(f"--- AGENT TEXT just before {msg['ts']} (not a source) ---\n{msg['agent_before']}\n"
                      f"--- OWNER ---\n{msg['text']}\n")
        sys.exit(0)
    for msg in owner_messages(repo_root()):
        print(json.dumps(msg, ensure_ascii=False))
