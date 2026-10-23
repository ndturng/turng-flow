"""Part 1 of /turng-flow:trial: gather every instruction source active for this project into one file,
and check that the permission table in the working rules matches guard.py.

Writes .turng-flow/reports/trial-sources-<time>.md and prints its path and the table check result.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from guard import allowed, plugin_roots  # noqa: E402
from rules import problems as rules_problems  # noqa: E402
from mode import state_dir  # noqa: E402

HOME = Path.home()
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MANDATORY = re.compile(r"\b(MUST|ALWAYS|NEVER|before ANY|EXTREMELY)\b")
TABLE_SAMPLES = [
    "agent-workspace/BACKLOG.md",
    "AGENTS.md",
    "agent-workspace/tasks/T/decisions.tsv",
    ".turng-flow/mode.json",
    "app/main.py",
]


def fenced(text: str) -> str:
    """Text from another source, verbatim, inside a fence longer than any tilde run in it."""
    fence = "~" * max(4, max((len(m) for m in re.findall(r"~+", text)), default=0) + 1)
    return f"{fence}\n{text.strip()}\n{fence}"


def section(title: str, body: str, verbatim: bool = True) -> str:
    """One source. Its text is fenced, so its own headings stay inside the section."""
    if not body.strip():
        return f"\n\n## {title}\n\n(empty)\n"
    return f"\n\n## {title}\n\n{fenced(body) if verbatim else body.strip()}\n"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def with_imports(path: Path) -> str:
    text = read(path)
    for line in text.splitlines():
        if line.startswith("@") and len(line) > 1:
            target = (path.parent / line[1:].strip()).resolve()
            text += f"\n\n### imported from {line.strip()}\n\n{read(target)}"
    return text


def enabled_plugins() -> list[tuple[str, Path]]:
    enabled = {}
    for settings in (HOME / ".claude/settings.json", ROOT / ".claude/settings.json", ROOT / ".claude/settings.local.json"):
        try:
            enabled.update(json.loads(read(settings) or "{}").get("enabledPlugins") or {})
        except ValueError:
            continue
    try:
        installed = json.loads(read(HOME / ".claude/plugins/installed_plugins.json")).get("plugins", {})
    except ValueError:
        installed = {}
    result = []
    for name, on in enabled.items():
        if not on:
            continue
        entries = installed.get(name) or []
        entry = next((e for e in entries if e.get("projectPath") == str(ROOT)), None) or next(
            (e for e in entries if e.get("scope") == "user"), None) or (entries[0] if entries else None)
        if entry:
            result.append((name, Path(entry["installPath"])))
    return result


def context_text(stdout: str) -> str:
    """The text a SessionStart hook adds to the context: plain stdout, or additionalContext when it prints JSON."""
    try:
        data = json.loads(stdout)
    except ValueError:
        return stdout
    if not isinstance(data, dict):
        return stdout
    return (data.get("hookSpecificOutput") or {}).get("additionalContext") or data.get("additional_context") or stdout


def session_start_output(name: str, root: Path) -> str:
    try:
        hooks = json.loads(read(root / "hooks/hooks.json") or "{}").get("hooks", {})
    except ValueError:
        return ""
    out = []
    for group in hooks.get("SessionStart", []):
        for hook in group.get("hooks", []):
            if hook.get("type") != "command":
                continue
            env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(root), CLAUDE_PROJECT_DIR=str(ROOT))
            try:
                run = subprocess.run(["bash", "-c", hook["command"]], input='{"source":"startup"}', env=env,
                                     cwd=ROOT, capture_output=True, text=True, timeout=30)
                out.append(context_text(run.stdout))
            except subprocess.TimeoutExpired:
                out.append("(timed out)")
    return "\n".join(out)


def mandatory_skills(plugin: str, root: Path, startup: str) -> str:
    """Full text of each skill whose description uses mandatory wording or that the session-start output names
    (`<plugin>:<skill>` or `<skill>` in backticks): the agent is told to run these, so their steps can conflict
    with turng-flow as much as the startup text. A skill whose body is already in the startup output is skipped.
    Each skill is fenced, so its headings stay inside it and quotes from it stay verbatim."""
    short = plugin.split("@")[0]
    parts = []
    for skill in sorted(root.glob("skills/*/SKILL.md")):
        name, text = skill.parent.name, read(skill)
        head = text.split("---", 2)
        description, body = (head[1], head[2]) if len(head) == 3 else ("", text)
        named = f"{short}:{name}" in startup or f"`{name}`" in startup
        if not (MANDATORY.search(description) or named) or body.strip()[:500] in startup:
            continue
        parts.append(f"### Skill `{short}:{name}`\n\n{fenced(text)}")
    return "\n\n".join(parts)


def table_check() -> list[str]:
    rules = read(PLUGIN_ROOT / "hooks/session-start-rules.md")
    marker = "**Files each mode may change.**"
    if marker not in rules:
        return [f"the working rules have no '{marker}' table"]
    rows = []
    for line in rules.split(marker, 1)[1].splitlines()[1:]:
        if rows and not line.strip().startswith("|"):
            break
        if line.strip().startswith("|"):
            rows.append(line)
    rows = [r for r in rows[1:] if not set(r.replace("|", "").strip()) <= set("-: ")]
    problems = rules_problems()
    for root in plugin_roots():
        sample = str(root / "skills/x/SKILL.md")
        if allowed(sample, "plan") or allowed(sample, "work"):
            problems.append(f"{root}: rules say the agent never writes to the plugin; guard.py allows it")
    if len(rows) != len(TABLE_SAMPLES):
        return [f"expected {len(TABLE_SAMPLES)} table rows in the working rules, found {len(rows)}"]
    for row, sample in zip(rows, TABLE_SAMPLES):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        for mode, cell in (("plan", cells[1]), ("work", cells[2])):
            documented = cell.startswith("yes")
            if documented != allowed(sample, mode):
                problems.append(f"{cells[0]} / {mode} mode: rules say {cell!r}, guard.py says "
                                f"{'yes' if allowed(sample, mode) else 'no'}")
    return problems


def main() -> None:
    parts = ["# turng-flow trial: instruction sources", f"Project: {ROOT}"]
    parts.append(section("User CLAUDE.md (~/.claude/CLAUDE.md)", read(HOME / ".claude/CLAUDE.md")))
    loaded = ""
    for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
        if (ROOT / name).exists():
            text = with_imports(ROOT / name)
            loaded += text
            parts.append(section(f"Project {name}", text))
    if (ROOT / "AGENTS.md").exists() and "@AGENTS.md" not in loaded:
        parts.append(section("Project AGENTS.md (not imported by CLAUDE.md, so Claude Code does not load it)",
                             read(ROOT / "AGENTS.md")))
    memory = HOME / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT)) / "memory"
    parts.append(section("Project memory", "\n\n".join(f"### {p.name}\n\n{read(p)}" for p in sorted(memory.glob("*.md")))))
    for settings in (HOME / ".claude/settings.json", ROOT / ".claude/settings.json", ROOT / ".claude/settings.local.json"):
        try:
            hooks = json.loads(read(settings) or "{}").get("hooks")
        except ValueError:
            hooks = None
        if hooks:
            parts.append(section(f"Hooks in {settings}", json.dumps(hooks, indent=1)))
    for name, root in enabled_plugins():
        if root.resolve() == PLUGIN_ROOT:
            continue
        startup = session_start_output(name, root)
        parts.append(section(f"Plugin {name}: session-start output", startup))
        parts.append(section(f"Plugin {name}: skills the agent is told to run (full text)",
                             mandatory_skills(name, root, startup), verbatim=False))
    problems = table_check()
    parts.append(section("Self-check: permission table vs guard.py",
                         "\n".join(f"- {p}" for p in problems) or "Matches.", verbatim=False))
    out_dir = state_dir() / "reports"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"trial-sources-{datetime.now():%Y%m%d-%H%M%S-%f}.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"sources: {out}")
    print("table check: " + ("matches" if not problems else "; ".join(problems)))


ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()

if __name__ == "__main__":
    main()
