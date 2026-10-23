"""The default branch of the repository, used as the base for comparisons."""
from __future__ import annotations

import subprocess
from pathlib import Path


def default_branch(repo: Path | None = None) -> str:
    out = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo,
                         capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip():
        return out.stdout.strip().split("/", 1)[-1]
    for name in ("main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "--quiet", name], cwd=repo,
                          capture_output=True).returncode == 0:
            return name
    return "HEAD"
