"""Create the turng-flow project files in a repository, from the plugin's templates.

  init_project.py [--dry-run]

Copies AGENTS.md, CLAUDE.md, and agent-workspace/ (BACKLOG.md, HISTORY.tsv, tasks/, design-notes/) into
the project root. An existing file is never overwritten; it is listed as kept.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode:
        print("not inside a git repository; run this from the project's repository")
        return 1
    root = Path(out.stdout.strip())
    created, kept = [], []
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file()):
        rel = src.relative_to(TEMPLATES)
        dst = root / rel
        if dst.exists():
            kept.append(f"{rel} (file already exists)")
            continue
        if rel.name == ".gitkeep" and dst.parent.exists():
            kept.append(f"{rel.parent} (folder already exists)")
            continue
        created.append(str(rel))
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    verb = "would create" if args.dry_run else "created"
    for rel in created:
        print(f"{verb}: {rel}")
    for rel in kept:
        print(f"kept: {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
