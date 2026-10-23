"""Print the working rules for the SessionStart hooks, in parts that Claude Code does not cut.

  rules.py part <n>   print part n (1-based); prints nothing when the rules have fewer parts
  rules.py check      list problems: a part over the limit, or more parts than hooks.json prints

Claude Code keeps the full output of a SessionStart hook only up to about 10,000 characters; a longer
output is saved to a file and the model sees a 2 KB preview (measured 2026-10-22: 9,500 kept, 10,500 cut,
JSON output cut the same way, two hooks of 8,000 each both kept). hooks/session-start-rules.md stays one
file; this script splits it at its "## " sections into parts of at most LIMIT characters, one part per hook.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RULES = PLUGIN_ROOT / "hooks/session-start-rules.md"
LIMIT = 8000
HEADER = 64  # room for the "part N of M" line added to parts after the first


def parts(text: str) -> list[str]:
    sections = re.split(r"(?m)^(?=## )", text)
    result = [sections[0]]
    for section in sections[1:]:
        if len(result[-1]) + len(section) <= LIMIT - HEADER:
            result[-1] += section
        else:
            result.append(section)
    total = len(result)
    return [p if i == 0 else f"# turng-flow working rules, part {i + 1} of {total}\n\n{p}" for i, p in enumerate(result)]


def hook_parts() -> int:
    hooks = json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    return sum("rules.py\" part" in h.get("command", "") for group in hooks for h in group.get("hooks", []))


def problems() -> list[str]:
    found = []
    split = parts(RULES.read_text(encoding="utf-8"))
    for i, part in enumerate(split, 1):
        if len(part) > LIMIT:
            found.append(f"part {i} of the working rules has {len(part)} characters, over {LIMIT}: "
                         "split its section")
    if len(split) > hook_parts():
        found.append(f"the working rules need {len(split)} parts but hooks/hooks.json prints {hook_parts()}: "
                     "add a SessionStart hook for each missing part")
    return found


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "part":
        split = parts(RULES.read_text(encoding="utf-8"))
        n = int(sys.argv[2])
        if n <= len(split):
            print(split[n - 1], end="")
    elif sys.argv[1:] == ["check"]:
        found = problems()
        print("\n".join(found) or "ok")
        sys.exit(1 if found else 0)
    else:
        sys.exit(__doc__)
