"""Check the structured backlog items (the "## Structured items" sections of agent-workspace/BACKLOG.md).

  check_backlog.py [--base <branch>]   base default: the default branch of the repository

Checks: all 7 fields in order, one short line each, empty fields use the fixed wording, owner quotes
appear verbatim in the session transcripts, code references exist, every item points to at least one
existing HISTORY row, and an item that disappeared since the base needs a closing row in HISTORY.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_quotes import QUOTE, find, norm  # noqa: E402
from gitbase import default_branch  # noqa: E402
from history import HISTORY, read_rows  # noqa: E402
from owner_messages import earliest, owner_messages, repo_root  # noqa: E402

REPO = repo_root(strict=True)
REL = "agent-workspace/BACKLOG.md"
SECTION = "## Structured items"
HEADING = re.compile(r"^### (B-\d{3}) \[([^\]]+)\] (.+)$")
# (field name, the wording to use when there is no information yet)
FIELDS = [
    ("Code state", "not checked"),
    ("Work needed", None),
    ("Owner decided", "not decided"),
    ("Open issues", "no open issue recorded (checked <sources>, <date>)"),
    ("Schedule", "not scheduled"),
    ("Agent proposal", "none"),
    ("Sources", None),
]
# Field names used before 0.1.4, still accepted so older backlogs keep passing.
OLD_NAMES = {"Open issues": "Open questions"}
NO_ISSUE = "no open issue recorded"
FIELD_MAX = 400
# An item carried over from an old backlog whose owner decision could not be found in the transcripts.
UNTRACED = "source not traced"
CODE_REF = re.compile(r"`([\w./-]+\.\w+):(\d+)`")
CLOSING = {"debt-closed", "task-closed", "dropped"}


def old_backlog_lines() -> int | None:
    """Line count of the longest old backlog (agent-workspace/BACKLOG-old*.md), or None when there is none."""
    files = list((REPO / "agent-workspace").glob("BACKLOG-old*.md"))
    if not files:
        return None
    return max(len(f.read_text(encoding="utf-8").splitlines()) for f in files)


def entries(text: str) -> dict[str, dict]:
    found, current, inside = {}, None, False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            inside, current = line.startswith(SECTION), None
            continue
        if not inside:
            continue
        match = HEADING.match(line)
        if match:
            current = {"line": number, "fields": [], "dup": match.group(1) in found}
            found[match.group(1)] = current
        elif line.startswith("### "):
            current = {"line": number, "fields": [], "bad_heading": line}
            found[f"?{number}"] = current
        elif current is not None and line.strip():
            current["fields"].append((number, line))
    return found


SOURCE_DELETED = "SOURCE DELETED: "


def entry_problems(entry: dict, owner: list[dict], history_ids: set[str], old_lines: int | None) -> list[str]:
    if "bad_heading" in entry:
        return ["the heading must look like '### B-001 [tag] Name'"]
    problems = ["duplicate id"] if entry["dup"] else []
    if len(entry["fields"]) != len(FIELDS):
        return problems + [f"needs exactly {len(FIELDS)} field lines ({', '.join(n for n, _ in FIELDS)}), "
                           f"has {len(entry['fields'])}"]
    for (name, empty), (number, line) in zip(FIELDS, entry["fields"]):
        prefix = f"- **{name}:** "
        old_prefix = f"- **{OLD_NAMES[name]}:** " if name in OLD_NAMES else None
        if old_prefix and line.startswith(old_prefix):
            prefix = old_prefix
        elif not line.startswith(prefix):
            problems.append(f"line {number}: must start with '{prefix}'")
            continue
        value = line[len(prefix):].strip()
        if name == "Open issues" and (value == "none" or (value.startswith(NO_ISSUE) and "(checked " not in value)):
            problems.append(f"line {number}: name the sources searched, as '{empty}'")
        if not value:
            problems.append(f"line {number}: field '{name}' is empty" + (f"; with no information write '{empty}'" if empty else ""))
        if len(line) > FIELD_MAX:
            problems.append(f"line {number}: field '{name}' is {len(line)} characters, at most {FIELD_MAX}")
        if name == "Code state" and value != empty:
            refs = CODE_REF.findall(value)
            if not refs:
                problems.append(f"line {number}: cite at least one `path:line`, or write '{empty}'")
            for path, lineno in refs:
                target = REPO / path
                if not target.is_file():
                    problems.append(f"line {number}: no file {path}")
                elif int(lineno) > len(target.read_text(encoding="utf-8", errors="replace").splitlines()):
                    problems.append(f"line {number}: {path} is shorter than line {lineno}")
            if not re.search(r"checked \d{4}-\d{2}-\d{2}", value):
                problems.append(f"line {number}: the date of the code check is missing, as 'checked 2026-10-01'")
        if name == "Owner decided" and value != empty and not QUOTE.search(value) and not value.startswith(UNTRACED):
            problems.append(f"line {number}: quote the owner verbatim as *\"...\"* with a date, or write '{empty}', "
                            f"or start with '{UNTRACED}'")
        if name not in ("Owner decided", "Open issues", "Schedule") and QUOTE.search(value):
            problems.append(f"line {number}: owner quotes belong only in 'Owner decided', 'Open issues', or 'Schedule'")
        for quote in QUOTE.findall(value):
            if find(quote, owner):
                continue
            dated = re.search(re.escape(quote) + r'"\*.*?\((\d{4}-\d{2}-\d{2})', value)
            if dated and dated.group(1) < earliest(owner):
                problems.append(f"{SOURCE_DELETED}line {number}: quote \"{quote[:60]}\" ({dated.group(1)}) is older "
                                f"than the oldest owner message still readable ({earliest(owner)})")
            else:
                problems.append(f"line {number}: quote \"{quote[:60]}\" is not in the owner's messages")
        if name == "Sources":
            ids = re.findall(r"H-\d{4}", value)
            if not ids:
                problems.append(f"line {number}: must point to at least one HISTORY row (H-0001)")
            problems += [f"line {number}: {i} is not in HISTORY.tsv" for i in ids if i not in history_ids]
            for n in re.findall(r"\bold:(\d+)", value):
                if old_lines is None:
                    problems.append(f"line {number}: old:{n} cites an old backlog, but agent-workspace has no BACKLOG-old*.md")
                elif int(n) > old_lines:
                    problems.append(f"line {number}: no old backlog has a line {n}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=None, help="default: the default branch of the repository")
    args = parser.parse_args()
    base = args.base or default_branch(REPO)

    history = read_rows(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    history_ids = {row["id"] for row in history}
    owner = [{**m, "norm": norm(m["text"])} for m in owner_messages(REPO)]
    old_lines = old_backlog_lines()
    now = entries((REPO / REL).read_text(encoding="utf-8"))

    bad = deleted = 0
    for key, entry in now.items():
        for problem in entry_problems(entry, owner, history_ids, old_lines):
            if problem.startswith(SOURCE_DELETED):
                deleted += 1
                print(f"NOTE   {REL}:{entry['line']} {key}: {problem}")
                continue
            bad += 1
            print(f"WRONG  {REL}:{entry['line']} {key}: {problem}")

    old = subprocess.run(["git", "show", f"{base}:{REL}"], cwd=REPO, capture_output=True, text=True)
    if old.returncode != 0:
        print(f"NOTE   cannot read {REL} on {base}; removed items were not checked")
    closed = {ref for row in history if row["type"] in CLOSING for ref in re.findall(r"B-\d{3}", row["refs"])}
    for key in (entries(old.stdout) if old.returncode == 0 else {}):
        if key not in now and key not in closed:
            bad += 1
            print(f"WRONG  {REL}: item {key} exists on {base} but is gone, and no debt-closed / task-closed / "
                  "dropped row in HISTORY points to it")
    print(f"{len(now)} structured items, {bad} problems, {deleted} quotes whose source transcript was deleted.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
