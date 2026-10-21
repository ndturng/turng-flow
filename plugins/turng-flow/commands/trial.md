---
description: Check whether other rules, configuration, or plugins in this environment interfere with turng-flow.
disable-model-invocation: true
---

Run the turng-flow trial and report the result to the owner. It has two parts.

**Part 1: instruction sources.**

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/trial_collect.py"`. It prints the path of a sources file and the result of the permission-table self-check.
2. Spawn one subagent with model `opus`. Give it the path of the sources file and of `${CLAUDE_PLUGIN_ROOT}/hooks/session-start-rules.md`. Ask it to list every place where a source would make the agent act against a turng-flow rule. For each conflict it quotes both texts verbatim, names the source, and says which turng-flow rule is affected. It reports only conflicts it can quote; no guesses.

**Part 2: live checks.**

3. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/trial_live.py"`. It runs six checks in a temporary git worktree on the cheap model `haiku`, removes the worktree, and prints pass or FAIL per check and the path of its report.

**Report.**

4. Write `.turng-flow/reports/trial-<date>.md` with: the permission-table self-check, the conflicts from part 1, and the table from part 2. State at the top that the trial checks the mechanisms and whether the rules are loaded, not how well a model follows them.
5. Reply to the owner with the same content, the item the owner must handle first, and the report path.
