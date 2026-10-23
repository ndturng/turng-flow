"""Model for each turng-flow role.

  models.py <role>     print the model for a role
  models.py --list     print every role and its model

Defaults come from the plugin's models.json. The owner overrides any role in
~/.claude/turng-flow-models.json, for example {"task-review": "sonnet"}. "inherit" means: use the
model of the running session (omit the model argument).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULTS = Path(__file__).resolve().parent.parent / "models.json"
OVERRIDES = Path.home() / ".claude/turng-flow-models.json"


def resolved() -> dict[str, str]:
    data = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    roles, allowed = dict(data["roles"]), set(data["allowed"])
    if OVERRIDES.exists():
        try:
            overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        except ValueError as exc:
            sys.exit(f"{OVERRIDES}: not valid JSON ({exc})")
        for role, model in overrides.items():
            if role not in roles:
                sys.exit(f"{OVERRIDES}: unknown role {role!r}; known roles: {', '.join(sorted(roles))}")
            if model not in allowed:
                sys.exit(f"{OVERRIDES}: model {model!r} for {role!r} is not one of {', '.join(sorted(allowed))}")
            roles[role] = model
    return roles


if __name__ == "__main__":
    roles = resolved()
    if sys.argv[1:] == ["--list"]:
        for role, model in sorted(roles.items()):
            print(f"{role}: {model}")
    elif len(sys.argv) == 2 and sys.argv[1] in roles:
        print(roles[sys.argv[1]])
    else:
        sys.exit(f"usage: models.py <role> | --list; known roles: {', '.join(sorted(roles))}")
