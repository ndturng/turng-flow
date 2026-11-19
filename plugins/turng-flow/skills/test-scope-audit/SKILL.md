---
name: test-scope-audit
description: Decide whether the tests a task ran cover the code it changed, so the full test suite runs only when needed. Use before reporting a task done, and when the project has no test map yet.
---

# test-scope-audit

Purpose: a full test run can take 20 minutes or more. Most tasks change a small part of the code, so a smaller set of tests is enough. The set is chosen from data (a test map), not from a guess. The agent that wrote the code does not decide alone that its tests are enough: the main agent of the session checks, as docs-audit does for documents.

The map is the file `agent-workspace/test-map.json`. It lists, for each code file, the test files that run it, the list of "core" files (run by many test files), and the commit it was built from. Scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/test_map.py` (`build`, `check`, `backtest`).

## Rules

1. The agent that wrote the code reports; the main agent audits. The report is not proof. The proof is the output of `check` and the test results.
2. The full suite runs when any one of these is true: a migration or any file the map does not track (SQL, settings, fixtures, dependency files, Docker files); a core file changed; a changed code file is not in the map; the map is missing or its commit is not in the history of the current branch.
3. A task that is not in rule 2 runs the test files `check` lists, plus every test the agent added or changed. That run replaces the full run before reporting done.
4. The full suite also runs every 5 closed tasks, with coverage on, and rebuilds the map from that run.
5. A map is trusted only after `backtest` and a mutation check passed (step 1). Until then, the project runs the full suite as before.
6. The report and the audit result are saved in `.turng-flow/reports/test-scope-<TASK>.md`.

## Step 1: no map yet

1. Ask the owner, as the one item of that turn. State the cost: one full run with coverage per test (usually 30 to 40 percent slower than a normal run), and any development dependency to add. Do nothing before the owner agrees.
2. In work mode, on its own branch (rule 7): run the full suite once with coverage per test, then `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/test_map.py" build ...` (see the script's `--help`). A core file is one that at least 20 test files run. Pass `--ignore` for the files that no test in the suite can run (for example front-end files that a separate check covers). A wrong entry makes the map skip tests it should run.
3. `backtest`: for the last merged tasks, check that the test files each task added or changed are in the map's set for that task, and show each set's size and, when known, its run time. Compare run time, not test count: the tests of one area can be slower than the average.
4. Mutation check: on a copy of the project outside the repository, make at least 20 small deliberate faults (flip a comparison, swap `and` and `or`, change a constant, drop a condition in SQL) in code files with a small set, and run only that set. Run it with the same language version as the test environment. Report how many faults the set caught and read each fault that survived: say whether it is harmless or a real gap.
5. Show the owner the sizes, the survivors, the core list and the ignore list. Use the map only after the owner agrees. Say in the report that this proves the set catches small faults in a sample, not that the set is always enough.
6. This procedure is checked only for Python with pytest and per-test coverage. For another stack, find a way to record which test runs which file, and pass the same two checks before trusting the map.

## Step 2: brief

When the agent that writes the code is briefed, give it the changed-file rule above and ask it to report: the files changed; the tests run with their results; for each new behaviour or error branch, the test that covers it; the tests it added; any changed file it thinks the map misses and why.

## Step 3: audit

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/test_map.py" check --base <default branch>`. It prints the changed files, which are in the map, core, or not tracked, the test files to run, and the verdict `FULL` or `SET` with reasons.
2. Read the diff yourself. For each new behaviour, error branch or data rule, find a test that would fail if it were wrong. When there is none, the result is `ADD TESTS`; when the test exists outside the set, the result is `RUN MORE`.
3. Compare the report with the diff and the output of `check`. Anything in the diff that the report does not mention is a failing item.
4. Result for the owner: `FULL`, `SET OK`, `ADD TESTS` or `RUN MORE`, the failing items, and the path of the saved report. Do not hand the owner commit commands while an item is failing.

## Limits (tell the owner when relevant)

- Coverage shows which lines ran, not which data or schema a test depends on. This is why migrations and untracked files always run the full suite.
- A fault the map does not catch is found at the next full run. The full run in rule 4 exists for that.
- The main agent and the agent that wrote the code are the same kind of model and can miss the same thing. The output of `check` does not depend on the model; the judgement in step 3.2 does.
