"""Print every message the owner typed or chose in this project's Claude Code sessions, one JSON per line.

  owner_messages.py                 all owner messages
  owner_messages.py --before <ts>   the end of the agent reply just before the owner message at <ts>,
                                    to see what the owner was answering ("1. agreed" agreed to what).
                                    That text is context, never a source for quotes.

Source: ~/.claude/projects/<checkout path with every non-alphanumeric character as "-">/*.jsonl, for the
repository and every worktree of it. Claude Code deletes transcripts older than cleanupPeriodDays, so every
read also appends the owner messages it finds to ARCHIVE in the main checkout, and reads them back from there.
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
ARCHIVE = ".turng-flow/owner-messages.jsonl"


def repo_root(strict: bool = False) -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode == 0:
        return Path(out.stdout.strip())
    if strict:
        raise SystemExit("not inside a git repository")
    return Path.cwd()


def checkouts(repo: Path) -> list[Path]:
    """The repository and every worktree of it: sessions of one project are stored per checkout path."""
    out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=repo, capture_output=True, text=True)
    paths = [Path(line[len("worktree "):]) for line in out.stdout.splitlines() if line.startswith("worktree ")]
    return paths or [repo]


def archive(repo: Path) -> Path:
    """The archive in the main checkout (the first entry of git worktree list), shared by all worktrees."""
    path = checkouts(repo)[0] / ARCHIVE
    path.parent.mkdir(exist_ok=True)
    ignore = path.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    return path


def owner_messages(repo: Path, with_agent: bool = False):
    found = list(transcript_messages(repo, with_agent))
    path = archive(repo)
    kept = []
    if path.exists():
        kept = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    known = {(m["session"], m["ts"], m["text"]) for m in kept}
    new = [m for m in found if (m["session"], m["ts"], m["text"]) not in known]
    if new:
        with path.open("a", encoding="utf-8") as f:
            for m in new:
                f.write(json.dumps({k: v for k, v in m.items() if k != "agent_before"}, ensure_ascii=False) + "\n")
    live = {(m["session"], m["ts"], m["text"]) for m in found}
    yield from sorted(found + [m for m in kept if (m["session"], m["ts"], m["text"]) not in live],
                      key=lambda m: m["ts"])


def earliest(messages: list[dict]) -> str:
    """The date of the oldest owner message still readable; a quote dated before it cannot be checked."""
    return min((m["ts"][:10] for m in messages), default="")


def transcript_messages(repo: Path, with_agent: bool = False):
    last_agent = ""
    evts = []
    for checkout in checkouts(repo):
        evts += events(transcript_dir(checkout))
    evts.sort(key=lambda e: e["time"])
    for e in evts:
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
