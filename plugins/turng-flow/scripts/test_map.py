#!/usr/bin/env python3
"""Test map for turng-flow:test-scope-audit.

  build     read per-test coverage data (pytest-cov, --cov-context=test) and write the map file
  check     list the test files a change needs and say SET or FULL
  backtest  replay the rule on the last merged tasks

Only the Python standard library. Exit code of `check`: 0 = SET, 1 = FULL, 2 = error.
"""
import argparse
import collections
import datetime
import fnmatch
import json
import re
import sqlite3
import subprocess
import sys

DEFAULT_MAP = "agent-workspace/test-map.json"
DEFAULT_IGNORE = ["*.md", "agent-workspace/*", ".turng-flow/*", ".claude/*", ".gitignore"]
DEFAULT_FULL = ["*migrations/*", "*.sql", "requirements*.txt", "pyproject.toml", "setup.cfg", "setup.py", "*.ini",
                "*.toml", "Dockerfile*", "Makefile", "*.env", ".env*", "*conftest.py"]


def git(*args):
    r = subprocess.run(["git", "--no-pager"] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def match(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def is_test_file(path):
    base = path.rsplit("/", 1)[-1]
    return base.startswith("test_") and base.endswith(".py")


def is_test_helper(path):
    parts = path.split("/")
    return ("tests" in parts[:-1] or "test" in parts[:-1]) and not is_test_file(path) and path.endswith(".py")


def build(a):
    c = sqlite3.connect("file:%s?mode=ro" % a.coverage, uri=True)
    files = dict(c.execute("select id, path from file"))
    ctx = dict(c.execute("select id, context from context"))
    tab = collections.defaultdict(set)
    tests = collections.defaultdict(set)
    for fid, cid in c.execute("select distinct file_id, context_id from line_bits"):
        name = ctx.get(cid) or ""
        if "::" not in name:
            continue
        test_file = a.test_root + name.split("::")[0]
        code = files[fid]
        if a.strip and code.startswith(a.strip):
            code = code[len(a.strip):]
        if not code.startswith(a.include):
            continue
        tab[code].add(test_file)
        tests[test_file].add(name.split("|")[0])
    if not tab:
        raise SystemExit("no per-test contexts found: run the tests with --cov-context=test, "
                         "and check --strip and --include")
    core = sorted(p for p, v in tab.items() if len(v) >= a.core_threshold)
    out = {
        "version": 1,
        "commit": git("rev-parse", "HEAD").strip(),
        "generated": datetime.date.today().isoformat(),
        "core_threshold": a.core_threshold,
        "ignore": DEFAULT_IGNORE + a.ignore,
        "full": DEFAULT_FULL + a.full,
        "files": {k: sorted(v) for k, v in sorted(tab.items())},
        "core": core,
        "test_counts": {k: len(v) for k, v in sorted(tests.items())},
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("map written to %s: %d code files, %d test files, %d core files (>= %d test files)" % (
        a.out, len(tab), len(tests), len(core), a.core_threshold))
    for p in core:
        print("  core %3d  %s" % (len(tab[p]), p))


def classify(changed, m):
    """Return (set of test files, added/changed test files, reasons that force FULL, notes)."""
    run, own, full, notes = set(), set(), [], []
    for p in changed:
        if match(p, m["ignore"]):
            notes.append("ignored   " + p)
        elif is_test_file(p):
            own.add(p)
        elif is_test_helper(p) or match(p, m["full"]):
            full.append("shared or untracked file changed: " + p)
        elif p in m["files"]:
            run |= set(m["files"][p])
            if p in m["core"]:
                full.append("core file changed: %s (%d test files run it)" % (p, len(m["files"][p])))
            else:
                notes.append("in map    %s -> %d test files" % (p, len(m["files"][p])))
        else:
            full.append("changed file not in the map: " + p)
    return run, own, full, notes


def load_map(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError) as e:
        raise SystemExit("cannot read the map %s: %s" % (path, e))


def check(a):
    try:
        m = load_map(a.map)
    except SystemExit as e:
        print("VERDICT: FULL\n  reason: %s" % e)
        return 1
    base = git("merge-base", a.base, "HEAD").strip()
    changed = set(git("diff", "--name-only", base).split("\n")) | set(
        git("ls-files", "--others", "--exclude-standard").split("\n"))
    changed = sorted(x for x in changed if x)
    reasons = []
    r = subprocess.run(["git", "merge-base", "--is-ancestor", m["commit"], "HEAD"], capture_output=True)
    if r.returncode != 0:
        reasons.append("the map commit %s is not in the history of this branch" % m["commit"][:10])
    run, own, full, notes = classify(changed, m)
    reasons += full
    print("changed files: %d (base %s, map commit %s, built %s)" % (len(changed), base[:10], m["commit"][:10],
                                                                    m["generated"]))
    for n in notes:
        print("  " + n)
    print("test files the task added or changed: %s" % (sorted(own) or "none"))
    runall = sorted(run | own)
    print("test files to run (%d): %s" % (len(runall), " ".join(runall)))
    if reasons:
        print("VERDICT: FULL")
        for x in reasons:
            print("  reason: " + x)
        return 1
    print("VERDICT: SET")
    return 0


def backtest(a):
    m = load_map(a.map)
    durations = json.load(open(a.durations)) if a.durations else {}
    total_tests = sum(m["test_counts"].values())
    total_time = sum(durations.values())
    merges = git("log", "--first-parent", "--merges", "--format=%H %s", "-n", str(a.merges), a.base).strip().split("\n")
    for line in merges:
        if not line:
            continue
        h, subject = line.split(" ", 1)
        changed = [x for x in git("diff", "--name-only", h + "^1", h).split("\n") if x]
        run, own, full, _ = classify(changed, m)
        missed = sorted(o for o in own if o not in run)
        n = sum(m["test_counts"].get(t, 0) for t in run | own)
        txt = "%-4s %3d test files %5d tests (%3.0f%% of tests)" % ("FULL" if full else "SET", len(run | own), n,
                                                                    100.0 * n / max(total_tests, 1))
        if durations:
            t = sum(durations.get(x, 0) for x in run | own)
            txt += " %5.0fs (%3.0f%% of time)" % (t, 100.0 * t / max(total_time, 1))
        print("%s | %s" % (txt, subject[:60]))
        if full:
            print("       because: " + "; ".join(full)[:200])
        if own and not full:
            print("       task's own test files selected by the map alone: %d/%d%s" % (
                len(own) - len(missed), len(own), "; missed: %s" % missed if missed else ""))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    b = s.add_parser("build", help="write the map from per-test coverage data")
    b.add_argument("--coverage", required=True, help="coverage data file (sqlite), from --cov-context=test")
    b.add_argument("--out", default=DEFAULT_MAP)
    b.add_argument("--strip", default="", help="prefix to cut from code paths in the data file, e.g. /app/")
    b.add_argument("--include", default="", help="keep code paths that start with this after --strip")
    b.add_argument("--test-root", default="", help="prefix to add to test paths (relative to the pytest rootdir)")
    b.add_argument("--core-threshold", type=int, default=20)
    b.add_argument("--ignore", action="append", default=[], help="extra glob of files that need no test")
    b.add_argument("--full", action="append", default=[], help="extra glob of files that always force FULL")
    c = s.add_parser("check", help="verdict for the current change")
    c.add_argument("--base", default="main")
    c.add_argument("--map", default=DEFAULT_MAP)
    t = s.add_parser("backtest", help="replay the rule on the last merged tasks")
    t.add_argument("--base", default="main")
    t.add_argument("--map", default=DEFAULT_MAP)
    t.add_argument("--merges", type=int, default=8)
    t.add_argument("--durations", help="JSON file {test file: seconds}, optional; "
                                              "take it from the same recent run as the map, old times mislead")
    a = p.parse_args()
    if a.cmd == "build":
        build(a)
    elif a.cmd == "check":
        sys.exit(check(a))
    else:
        backtest(a)


if __name__ == "__main__":
    main()
