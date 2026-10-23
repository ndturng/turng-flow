"""Project history log: agent-workspace/HISTORY.tsv. Append only; old rows are never changed.

  history.py add --type <type> --what "<one sentence>" --source "<source>[; <source>]" [--refs "B-001, TASK-046"] [--date YYYY-MM-DD]
  history.py check [--base <branch>]   default: the default branch of the repository

A row is written only when every source can be checked by machine:
  owner:<time>          an owner message in the session transcripts, e.g. owner:2026-09-30T09:20 (to the minute, UTC)
  git:<sha>             an existing commit
  task:<TASK-046>       a folder agent-workspace/tasks/TASK-046*
  code:<path>[:<line>]  an existing file, and line
An owner quote is written as *"..."* and must appear verbatim in the owner message at the cited time.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gitbase import default_branch  # noqa: E402
from check_quotes import ELLIPSIS, MIN_FRAGMENT, QUOTE, norm  # noqa: E402
from owner_messages import owner_messages, repo_root  # noqa: E402

REPO = repo_root(strict=True)
REL = "agent-workspace/HISTORY.tsv"
HISTORY = REPO / REL
COLUMNS = ["id", "date", "type", "what", "source", "refs"]
# Types that must quote the owner verbatim.
OWNER_TYPES = {"owner-decision", "direction-change", "open-question", "dropped"}
TYPES = OWNER_TYPES | {"debt-recorded", "debt-closed", "task-closed", "correction"}
WHAT_MAX = 300
ID = re.compile(r"^H-(\d{4})$")


def read_rows(text: str) -> list[dict]:
    lines = text.splitlines()
    if not lines or lines[0].split("\t") != COLUMNS:
        raise SystemExit(f"{REL}: the first line must be {COLUMNS}")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != len(COLUMNS):
            raise SystemExit(f"{REL}:{number}: needs {len(COLUMNS)} columns, has {len(cells)}")
        rows.append(dict(zip(COLUMNS, cells)) | {"line": number})
    return rows


_owner_cache: list[dict] | None = None


def owner_at(stamp: str) -> list[str]:
    global _owner_cache
    if _owner_cache is None:
        _owner_cache = list(owner_messages(REPO))
    return [norm(m["text"]) for m in _owner_cache if m["ts"].startswith(stamp)]


def source_problems(source: str) -> tuple[list[str], list[str]]:
    """Return (problems, the owner messages cited)."""
    problems, owner_texts = [], []
    for item in (s.strip() for s in source.split(";")):
        kind, _, value = item.partition(":")
        if kind == "owner":
            if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", value):
                problems.append(f"source '{item}': the time must go to the minute")
                continue
            found = owner_at(value)
            if not found:
                problems.append(f"source '{item}': no owner message at this time")
            owner_texts += found
        elif kind == "git":
            if subprocess.run(["git", "cat-file", "-e", f"{value}^{{commit}}"], cwd=REPO, capture_output=True).returncode:
                problems.append(f"source '{item}': no such commit")
        elif kind == "task":
            if not list((REPO / "agent-workspace/tasks").glob(f"{value}*")):
                problems.append(f"source '{item}': no such task folder")
        elif kind == "code":
            path, _, line = value.partition(":")
            target = REPO / path
            if not target.is_file():
                problems.append(f"source '{item}': no such file")
            elif line and int(line) > len(target.read_text(encoding="utf-8", errors="replace").splitlines()):
                problems.append(f"source '{item}': the file is shorter than line {line}")
        else:
            problems.append(f"source '{item}': must start with owner: / git: / task: / code:")
    return problems, owner_texts


def row_problems(row: dict) -> list[str]:
    problems = []
    if not ID.match(row["id"]):
        problems.append("id must look like H-0001")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", row["date"]):
        problems.append("date must be YYYY-MM-DD")
    if row["type"] not in TYPES:
        problems.append(f"type must be one of: {', '.join(sorted(TYPES))}")
    if not row["what"].strip() or len(row["what"]) > WHAT_MAX:
        problems.append(f"what must have text and at most {WHAT_MAX} characters (now {len(row['what'])})")
    if not row["source"].strip():
        return problems + ["source is missing"]
    source_errors, owner_texts = source_problems(row["source"])
    problems += source_errors
    quotes = QUOTE.findall(row["what"])
    if row["type"] in OWNER_TYPES and not quotes:
        problems.append(f"type '{row['type']}' must quote the owner verbatim as *\"...\"*")
    for quote in quotes:
        fragments = [f for f in (norm(p) for p in ELLIPSIS.split(quote)) if len(f) >= MIN_FRAGMENT] or [norm(quote)]
        if not any(all(f in text for f in fragments) for text in owner_texts):
            problems.append(f"quote \"{quote[:60]}\" is not in the owner message at the cited time")
    return problems


def check(base: str) -> int:
    if not HISTORY.exists():
        print(f"{REL} does not exist yet")
        return 0
    text = HISTORY.read_text(encoding="utf-8")
    rows, bad = read_rows(text), 0
    for index, row in enumerate(rows, start=1):
        problems = row_problems(row)
        if row["id"] != f"H-{index:04d}":
            problems.append(f"id must be H-{index:04d} (consecutive, nothing inserted)")
        for problem in problems:
            bad += 1
            print(f"WRONG  {REL}:{row['line']} {row['id']}: {problem}")
    old = subprocess.run(["git", "show", f"{base}:{REL}"], cwd=REPO, capture_output=True, text=True)
    if old.returncode != 0:
        print(f"NOTE   cannot read {REL} on {base}; changes to old rows were not checked")
    elif not text.startswith(old.stdout):
        bad += 1
        print(f"WRONG  {REL}: a row that exists on {base} was changed or removed. The log is append only; "
              "to correct a row, add a 'correction' row that points to its id.")
    print(f"{len(rows)} rows, {bad} problems.")
    return 1 if bad else 0


def add(args) -> int:
    if any(c in value for value in (args.what, args.source, args.refs) for c in "\t\n"):
        raise SystemExit("tabs and line breaks are not allowed in the content")
    rows = read_rows(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    row = {"id": f"H-{len(rows) + 1:04d}", "date": args.date, "type": args.type, "what": args.what,
           "source": args.source, "refs": args.refs}
    problems = row_problems(row)
    if problems:
        print("NOT WRITTEN:\n  " + "\n  ".join(problems))
        return 1
    if not HISTORY.exists():
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text("\t".join(COLUMNS) + "\n", encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write("\t".join(row[c] for c in COLUMNS) + "\n")
    print(f"written {row['id']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--type", required=True)
    a.add_argument("--what", required=True)
    a.add_argument("--source", required=True)
    a.add_argument("--refs", default="")
    a.add_argument("--date", default=date.today().isoformat())
    c = sub.add_parser("check")
    c.add_argument("--base", default=None, help="default: the default branch of the repository")
    args = parser.parse_args()
    sys.exit(add(args) if args.cmd == "add" else check(args.base or default_branch(REPO)))
