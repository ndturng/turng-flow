"""Collect the material for /turng-flow:review-task.

  review_collect.py [--since ISO] [--until ISO] [--transcripts DIR] [--part-chars N]
  review_collect.py --list [N]
  review_collect.py --session ID

The period starts where the last review ended (.turng-flow/reports/review-history.tsv); the first
review starts at the first line of .turng-flow/mode-log.tsv. Writes one or more input files
.turng-flow/reports/review-input-<stamp>-<n>.md and a manifest .json, and prints the manifest path.

--list prints the N most recent sessions (default 20) with times in UTC+7 and does not collect.
--session reviews one session (ID or the first characters of it); its period runs from its first
to its last event.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN = timezone(timedelta(hours=7))
DEFAULT_LIST = 20

sys.path.insert(0, str(Path(__file__).parent))
from guard import DECISION_LOGS, RULES_AND_DESIGN  # noqa: E402
from mode import state_dir  # noqa: E402
from transcripts import events, now, parse_time, transcript_dir  # noqa: E402


def git(root: Path, *args: str) -> str:
    run = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return run.stdout if run.returncode == 0 else ""


def read_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, line.split("\t"))) for line in lines[1:] if line.strip()]


def default_since(d: Path):
    history = read_tsv(d / "reports" / "review-history.tsv")
    if history:
        return parse_time(history[-1]["until"])
    log = read_tsv(d / "mode-log.tsv")
    return parse_time(log[0]["time"]) if log else None


def mode_periods(d: Path, since, until) -> str:
    rows = read_tsv(d / "mode-log.tsv")
    lines, previous = [], None
    for row in rows:
        t = parse_time(row["time"])
        if since and t <= since:
            previous = row
            continue
        if t > until:
            break
        lines.append(f"- {row['time']} -> {row['mode']} ({row['set_by']})")
    start = f"- at the start of the period: {previous['mode']}" if previous else "- at the start of the period: plan"
    return "\n".join([start, *lines])


def approvals(d: Path, since, until) -> str:
    path = d / "approvals.md"
    if not path.exists():
        return ""
    chunks = path.read_text(encoding="utf-8").split("\n## ")[1:]
    keep = []
    for chunk in chunks:
        stamp = chunk.splitlines()[0].strip()
        try:
            t = parse_time(stamp)
        except ValueError:
            continue
        if (not since or t > since) and t <= until:
            keep.append("### " + chunk.strip())
    return "\n\n".join(keep)


def git_changes(root: Path, since, until) -> str:
    since_arg = [f"--since={since.isoformat()}"] if since else []
    log = git(root, "log", "--date=iso-strict", "--stat", "--format=%n### %h %ad %s", *since_arg,
              f"--until={until.isoformat()}")
    protected = [p.replace("*", "") for p in DECISION_LOGS + RULES_AND_DESIGN]
    first = git(root, "log", "--format=%H", "--reverse", *since_arg, f"--until={until.isoformat()}").split()
    base = f"{first[0]}~1" if first else "HEAD"
    protected_diff = git(root, "diff", base, "--", *[p for p in protected if p])
    status = git(root, "status", "--porcelain")
    return (f"### Commits in the period\n{log or '(none)'}\n\n### Uncommitted changes (git status)\n"
            f"{status or '(none)'}\n\n### Diff of decision logs, rule files, and design notes since the "
            f"period started (committed and uncommitted)\n```diff\n{protected_diff or '(none)'}\n```")


def conversation(evts: list[dict]) -> list[str]:
    out = []
    for e in evts:
        stamp = e["time"].isoformat(timespec="seconds")
        if e["kind"] == "owner":
            out.append(f"[OWNER {stamp}]\n{e['text']}")
        elif e["kind"] == "dialog":
            out.append(f"[OWNER ANSWER {stamp}] question: {e.get('question', '')} | answer: {e['text']}")
        elif e["kind"] == "agent":
            out.append(f"[AGENT {stamp}]\n{e['text']}")
        else:
            out.append(f"[TOOL {stamp}] {e['tool']} {e['text']}")
    return out


def list_sessions(evts: list[dict], limit: int) -> None:
    by_session: dict[str, list[dict]] = {}
    for e in evts:
        by_session.setdefault(e["session"], []).append(e)
    rows = []
    for sid, items in by_session.items():
        owners = [e for e in items if e["kind"] == "owner"]
        first = owners[0]["text"].replace("\n", " ")[:80] if owners else "(no owner message)"
        rows.append((items[0]["time"], items[-1]["time"], sid, len(owners), first))
    rows.sort(key=lambda r: r[1], reverse=True)
    print(f"{'ID':8}  {'start (UTC+7)':16}  {'end (UTC+7)':16}  {'owner':>5}  first owner message")
    for start, end, sid, n, first in rows[:limit]:
        print(f"{sid[:8]}  {start.astimezone(VN):%Y-%m-%d %H:%M}  {end.astimezone(VN):%Y-%m-%d %H:%M}  "
              f"{n:>5}  {first}")


def pick_session(evts: list[dict], prefix: str) -> list[dict]:
    ids = sorted({e["session"] for e in evts if e["session"].startswith(prefix)})
    if not ids:
        sys.exit(f"No session starts with {prefix!r}. Run with --list to see the sessions.")
    if len(ids) > 1:
        sys.exit(f"{prefix!r} matches {len(ids)} sessions: {', '.join(i[:12] for i in ids)}. Use more characters.")
    return [e for e in evts if e["session"] == ids[0]]


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"{value!r} is not a positive whole number")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--transcripts")
    parser.add_argument("--part-chars", type=int, default=250_000)
    parser.add_argument("--list", nargs="?", const=DEFAULT_LIST, type=positive_int, metavar="N")
    parser.add_argument("--session")
    args = parser.parse_args()
    d = state_dir()
    root = d.parent
    folder = Path(args.transcripts) if args.transcripts else transcript_dir(root)
    session_id = None
    if args.list is not None:
        list_sessions(events(folder), args.list)
        return
    if args.session:
        evts = pick_session(events(folder), args.session)
        session_id = evts[0]["session"]
        since, until = evts[0]["time"] - timedelta(seconds=1), evts[-1]["time"]
    else:
        since = parse_time(args.since) if args.since else default_since(d)
        until = parse_time(args.until) if args.until else now()
        evts = events(folder, since, until)
    owner_count = sum(1 for e in evts if e["kind"] == "owner")
    subagents = [e for e in evts if e["kind"] == "tool" and e["tool"] in ("Agent", "Task")]
    skills = [e for e in evts if e["kind"] == "tool" and e["tool"] == "Skill"]

    header = [
        "# turng-flow review input",
        f"Period: {since.isoformat() if since else '(start)'} to {until.isoformat()}",
        f"Owner messages in the period: {owner_count}",
        *([f"Session review: only session {session_id} is read. Mode periods, approvals, and git changes "
           "cover its whole time span, so they may include work of other sessions that ran at the same time."]
          if session_id else []),
        "\n## Working rules\n", (Path(__file__).resolve().parent.parent / "hooks/session-start-rules.md").read_text(encoding="utf-8"),
        "\n## Mode periods\n", mode_periods(d, since, until),
        "\n## Approved approaches in the period\n", approvals(d, since, until) or "(none)",
        "\n## Subagent calls\n", "\n".join(f"- {e['time'].isoformat(timespec='seconds')} {e['text']}" for e in subagents) or "(none)",
        "\n## Skill calls\n", "\n".join(f"- {e['time'].isoformat(timespec='seconds')} {e['text']}" for e in skills) or "(none)",
        "\n## Git changes\n", git_changes(root, since, until),
    ]
    header_text = "\n".join(header)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = d / "reports"
    out_dir.mkdir(exist_ok=True)
    parts, chunk = [], ""
    for block in conversation(evts):
        if chunk and len(chunk) + len(block) > args.part_chars:
            parts.append(chunk)
            chunk = ""
        chunk += ("\n\n" if chunk else "") + block
    if chunk or not parts:
        parts.append(chunk)
    files = []
    for n, part in enumerate(parts, 1):
        f = out_dir / f"review-input-{stamp}-{n}.md"
        f.write_text(f"{header_text}\n\n## Conversation (part {n} of {len(parts)})\n\n{part}\n", encoding="utf-8")
        files.append(str(f))
    manifest = out_dir / f"review-input-{stamp}.json"
    manifest.write_text(json.dumps({
        "since": since.isoformat() if since else None, "until": until.isoformat(),
        "owner_messages": owner_count, "parts": files, "session": session_id,
    }, indent=1), encoding="utf-8")
    print(f"manifest: {manifest}")
    print(f"period: {since.isoformat() if since else '(start)'} to {until.isoformat()}; "
          f"owner messages: {owner_count}; parts: {len(files)}")


if __name__ == "__main__":
    main()
