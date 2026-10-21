"""Check every owner quote in the changed lines of the decision logs against what the owner actually
typed or chose.

Owner quotes are written as *"..."* (italic, in double quotes).

  check_quotes.py [--base <branch>] [--head WORKTREE] [file ...]   base default: the default branch

Without files, checks agent-workspace/BACKLOG.md, agent-workspace/HISTORY.tsv, and every TASK_SPEC.md.
`--head WORKTREE` compares base with the files on disk, including uncommitted changes.
Exit code 1 when a quote is not found.
"""
from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gitbase import default_branch  # noqa: E402
from owner_messages import owner_messages, repo_root  # noqa: E402

DEFAULT_FILES = ["agent-workspace/BACKLOG.md", "agent-workspace/HISTORY.tsv",
                 ":(glob)agent-workspace/tasks/**/TASK_SPEC.md"]
QUOTE = re.compile(r'\*"(.+?)"\*')
# An omission inside a quote: every fragment on either side must still appear in the SAME owner message.
ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")
MIN_FRAGMENT = 6
# A line that says the owner decided or agreed to something. Without a quote the script cannot check it.
ATTRIBUTION = re.compile(r"\bowner\b|\b(decided|approved|agreed)\b", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def added_lines(base: str, head: str, files: list[str]) -> list[tuple[str, str]]:
    cmd = ["git", "diff", "--unified=0", base] + ([] if head == "WORKTREE" else [head]) + ["--"] + files
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    current, lines = "", []
    for line in out.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            lines.append((current, line[1:]))
    if head == "WORKTREE":
        # A new file not yet added to git does not show in `git diff`; every line of it counts as added.
        new = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--"] + files,
                             capture_output=True, text=True, check=True).stdout
        for path in new.splitlines():
            lines += [(path, line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    return lines


def find(quote: str, messages: list[dict]) -> dict | None:
    fragments = [f for f in (norm(p) for p in ELLIPSIS.split(quote)) if len(f) >= MIN_FRAGMENT] or [norm(quote)]
    for msg in messages:
        if all(fragment in msg["norm"] for fragment in fragments):
            return msg
    return None


def nearest(quote: str, messages: list[dict]) -> tuple[float, dict | None]:
    target, best, best_msg = norm(quote), 0.0, None
    for msg in messages:
        text = msg["norm"]
        if len(text) > 4000:
            continue
        match = difflib.SequenceMatcher(None, target, text, autojunk=False).find_longest_match(0, len(target), 0, len(text))
        ratio = match.size / max(len(target), 1)
        if ratio > best:
            best, best_msg = ratio, msg
    return best, best_msg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=None, help="default: the default branch of the repository")
    parser.add_argument("--head", default="WORKTREE")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    messages = [{**m, "norm": norm(m["text"])} for m in owner_messages(repo_root())]
    if not messages:
        print("NO owner messages could be read (session transcripts missing?); no conclusion is possible.")
        return 2

    seen, missing, total, unquoted = set(), 0, 0, []
    base = args.base or default_branch(repo_root())
    for path, line in added_lines(base, args.head, args.files or DEFAULT_FILES):
        if ATTRIBUTION.search(line) and not QUOTE.search(line):
            unquoted.append((path, line.strip()))
        for quote in QUOTE.findall(line):
            if (path, quote) in seen:
                continue
            seen.add((path, quote))
            total += 1
            hit = find(quote, messages)
            if hit:
                print(f"FOUND    {path}: \"{quote[:90]}\"\n         -> owner {hit['kind']} {hit['ts']} session {hit['session'][:8]}")
            else:
                missing += 1
                ratio, near = nearest(quote, messages)
                print(f"MISSING  {path}: \"{quote[:200]}\"")
                if near:
                    print(f"         -> nearest ({ratio:.0%} contiguous match) {near['ts']} session {near['session'][:8]}: "
                          f"\"{near['norm'][:200]}\"")
    if unquoted:
        print(f"\nMENTIONS THE OWNER WITHOUT A VERBATIM QUOTE ({len(unquoted)} lines); the script cannot check these, "
              "the reviewer must:")
        for path, line in unquoted:
            print(f"  ?      {path}: {line[:260]}")
    print(f"\n{total - missing}/{total} quotes found verbatim in the owner's messages ({len(messages)} owner messages read).")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
