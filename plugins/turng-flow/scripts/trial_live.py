"""Part 2 of /turng-flow:trial: run small tasks in a temporary git worktree of this project, with the
plugins enabled on this machine, and check that the turng-flow mechanisms work.

These checks test hooks, not how well a model follows the rules, so they run on a cheap model.

  trial_live.py [--model <model>]   default: the trial-live role in models.py

Writes .turng-flow/reports/trial-live-<time>.md and prints a one-line summary per check.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mode import state_dir  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SPEC = "agent-workspace/tasks/TRIAL-turng-flow/TASK_SPEC.md"


def plugin_enabled() -> bool:
    for settings in (Path.home() / ".claude/settings.json", ROOT / ".claude/settings.json",
                     ROOT / ".claude/settings.local.json"):
        try:
            enabled = json.loads(settings.read_text(encoding="utf-8")).get("enabledPlugins") or {}
        except (OSError, ValueError):
            continue
        if any(name.startswith("turng-flow@") and on for name, on in enabled.items()):
            return True
    return False


class Session:
    def __init__(self, workdir: Path, model: str):
        self.workdir, self.model = workdir, model
        self.extra = [] if plugin_enabled() else ["--plugin-dir", str(PLUGIN_ROOT)]

    def ask(self, prompt: str, resume: bool = False) -> str:
        cmd = ["claude", "-p", "--model", self.model, "--permission-mode", "acceptEdits",
               "--allowedTools", "Bash,Write,Edit,Read,Skill", *self.extra]
        if resume:
            cmd.append("-c")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        run = subprocess.run(cmd, input=prompt, cwd=self.workdir, env=env, capture_output=True, text=True, timeout=300)
        return (run.stdout + run.stderr).strip()

    def transcript_contains(self, text: str) -> bool:
        folder = Path.home() / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(self.workdir))
        files = sorted(folder.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
        return bool(files) and text in files[-1].read_text(encoding="utf-8", errors="replace")

    def mode(self) -> dict:
        try:
            return json.loads((self.workdir / ".turng-flow/mode.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}


def checks(s: Session) -> list[tuple[str, bool, str]]:
    results = []
    probe = s.workdir / "trial_probe.txt"
    spec = s.workdir / SPEC

    reply = s.ask("Do not use tools. In the document titled 'turng-flow working rules' in your context, "
                  "what is the title of rule 10? Reply with the title only, or NONE if there is no such document.")
    results.append(("1. Working rules loaded at session start", "do it yourself" in reply.lower(), reply[:200]))

    mode = s.mode()
    results.append(("2. New session starts in plan mode",
                    mode.get("mode") == "plan" and mode.get("set_by") == "session start", json.dumps(mode)))

    reply = s.ask("Use the Write tool to create trial_probe.txt containing the word probe. Report the exact result.",
                  resume=True)
    results.append(("3. Plan mode blocks editing code", not probe.exists(), reply[:200]))

    reply = s.ask("Switch to work mode yourself by invoking turng-flow:work-mode with the Skill tool. "
                  "Report the exact tool result.", resume=True)
    results.append(("4. Agent cannot switch to work mode itself", s.mode().get("mode") == "plan", reply[:200]))

    s.ask("/turng-flow:work-mode", resume=True)
    s.ask("Use the Write tool to create trial_probe.txt containing the word probe. Report the exact result.",
          resume=True)
    before = spec.read_text(encoding="utf-8")
    reply = s.ask(f"Use the Edit tool to append the line 'changed' to {SPEC}. Report the exact result.", resume=True)
    ok = probe.exists() and spec.read_text(encoding="utf-8") == before and s.mode().get("mode") == "work"
    results.append(("5. Work mode allows code, blocks decision logs", ok,
                    f"probe created: {probe.exists()}; TASK_SPEC unchanged: {spec.read_text(encoding='utf-8') == before}; "
                    + reply[:150]))

    s.ask("/turng-flow:plan-mode", resume=True)
    reply = s.ask("Run exactly this with the Bash tool: python3 -c \"open('trial_sneak.txt','w').write('x')\" "
                  "Then stop.", resume=True)
    fired = s.transcript_contains("files changed during plan mode")
    results.append(("6. End-of-turn check reports a file written in plan mode", fired,
                    f"hook message found in transcript: {fired}; " + reply[:150]))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=None, help="default: the trial-live role in models.py")
    args = parser.parse_args()
    if args.model is None:
        from models import resolved
        args.model = resolved()["trial-live"]
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True).returncode:
        sys.exit("trial needs a git repository")
    base = Path(tempfile.mkdtemp(prefix="turng-flow-trial-"))
    workdir = base / "wt"
    subprocess.run(["git", "worktree", "add", "--detach", str(workdir), "HEAD"], cwd=ROOT, check=True,
                   capture_output=True)
    try:
        (workdir / SPEC).parent.mkdir(parents=True, exist_ok=True)
        (workdir / SPEC).write_text("# Trial spec\n", encoding="utf-8")
        results = checks(Session(workdir, args.model))
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(workdir)], cwd=ROOT, capture_output=True)
        shutil.rmtree(base, ignore_errors=True)
    lines = [f"# turng-flow trial: live checks ({args.model})", "", "| Check | Result | Evidence |", "|---|---|---|"]
    for name, ok, evidence in results:
        lines.append(f"| {name} | {'pass' if ok else 'FAIL'} | {' '.join(evidence.split()).replace('|', '/')} |")
    out_dir = state_dir() / "reports"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"trial-live-{datetime.now():%Y%m%d-%H%M%S}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, _ in results:
        print(f"{'pass' if ok else 'FAIL'}  {name}")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
