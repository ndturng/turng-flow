"""Build a change package for the turng-flow plugin, for the owner to apply in the plugin repository.

  plugin_package.py start <short-name>    copy the installed plugin into a new package; print its new/ folder
  plugin_package.py finish <package>      write changes.patch and CHANGES.md, validate new/, print the package

The agent never writes to the plugin repository. It edits the copy under new/, and the owner applies
changes.patch (or the full texts in CHANGES.md) in the repository, on any machine.
"""
from __future__ import annotations

import difflib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import state_dir  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
IN_REPO = "plugins/turng-flow"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def version(plugin: Path) -> str:
    return json.loads((plugin / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]


def files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if text and not text[-1].endswith("\n"):
        text[-1] += "\n\\ No newline at end of file\n"
    return text


def start(name: str) -> None:
    package = state_dir() / "reports" / f"plugin-update-{date.today()}-{name}"
    if package.exists():
        sys.exit(f"{package} already exists")
    for side in ("base", "new"):
        shutil.copytree(PLUGIN_ROOT, package / side / IN_REPO, ignore=IGNORE)
    print(package / "new" / IN_REPO)


def finish(package: Path) -> None:
    base, new = package / "base" / IN_REPO, package / "new" / IN_REPO
    patch, changed = [], []
    for rel in sorted(files(base) | files(new)):
        a, b = base / rel, new / rel
        if a.exists() and b.exists() and a.read_bytes() == b.read_bytes():
            continue
        changed.append((rel, "deleted" if not b.exists() else "new" if not a.exists() else "changed"))
        patch += difflib.unified_diff(lines(a), lines(b),
                                      f"a/{IN_REPO}/{rel}" if a.exists() else "/dev/null",
                                      f"b/{IN_REPO}/{rel}" if b.exists() else "/dev/null")
    if not changed:
        sys.exit("no file under new/ differs from the installed plugin")
    (package / "changes.patch").write_text("".join(patch), encoding="utf-8")
    doc = [f"# turng-flow plugin change: {package.name}", "",
           f"Base: installed plugin version {version(base)}. New version: {version(new)}.", "",
           "## Steps for the owner, in the plugin repository", "",
           "1. Create a branch from the default branch.",
           f"2. Run `git apply {package / 'changes.patch'}`.",
           "3. Check that `git diff` shows the same changes as this file.",
           "4. Commit, merge, push. Then update the installed plugin (`claude plugin marketplace update turng-flow`, "
           "`claude plugin update turng-flow@turng-flow`).",
           "", "If `git apply` fails, the repository is not at the base version: apply the texts below by hand.", "",
           "## Changed files", ""]
    for rel, how in changed:
        doc += [f"### `{IN_REPO}/{rel}` ({how})", ""]
        if how != "deleted":
            text = (new / rel).read_text(encoding="utf-8")
            fence = "~" * max(4, max((len(r) for r in text.split() if set(r) == {"~"}), default=0) + 1)
            doc += [fence, text.rstrip("\n"), fence, ""]
    (package / "CHANGES.md").write_text("\n".join(doc), encoding="utf-8")
    check = subprocess.run(["claude", "plugin", "validate", str(new)], capture_output=True, text=True)
    print(check.stdout.strip().splitlines()[-1] if check.stdout.strip() else check.stderr.strip())
    if version(new) == version(base):
        print("warning: the version in new/.claude-plugin/plugin.json was not raised")
    print(package)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "start":
        start(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "finish":
        finish(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
