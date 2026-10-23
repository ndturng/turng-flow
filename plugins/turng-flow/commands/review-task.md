---
description: Review how the agent worked since the last review, and record the correction rate.
disable-model-invocation: true
---

Run the turng-flow task review and report the result to the owner.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_collect.py"`. It prints the path of a manifest that lists one or more input files for the period since the last review.
2. Get the model with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/models.py" task-review`.
3. For each input file, spawn one subagent with that model (for `inherit`, omit the model). Give it the input file path, the instructions file `${CLAUDE_PLUGIN_ROOT}/reference/review-instructions.md`, and an output path `.turng-flow/reports/review-result-part-<n>.json`. Run the subagents in parallel.
4. When all have finished, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_record.py" <manifest> <each output path>`. It rejects findings whose quotes are not in the input, merges the parts, and records the period and the counts.
5. Write `.turng-flow/reports/review-<date>.md` from the merged result: the period, the correction rate and counts per category, then each finding with its quotes. List rejected findings separately.
6. Reply to the owner with the same content, the item the owner must handle first, and the report path.
