---
name: verify-audit
description: Check what a subagent wrote in the project's `.claude/skills/verify/` (feature files and drive scripts): every line matches what the owner decided and what the code does, no check was removed or weakened, and every behaviour the owner decided has an entry. Use after a subagent changed files there, before giving the owner the commit commands.
---

# verify-audit

Purpose: the owner cannot read every line a subagent writes in `.claude/skills/verify/`. An independent reviewer checks each line against sources other than the agent that wrote it, and the owner sees only the failing items. It does not rerun the drives and does not judge whether the app works.

The files in `.claude/skills/verify/` are the result of carrying out a task, so this check runs in work mode and a failing item is fixed in work mode, without switching mode.

## Rules

1. The agent that wrote or briefed the change does not check it. The first check goes to a new subagent that is told nothing about why the change was made: give it only `${CLAUDE_SKILL_DIR}/references/auditor-prompt.md`, the task id, and the values it names.
2. Do not edit the files while the reviewer runs.
3. Save the reviewer's table verbatim in `.turng-flow/reports/verify-audit-<TASK>.md`; give the owner the list of failing items and that path. A view of the writing agent goes in a separate section at the end.
4. An item that could not be checked is labelled `CANNOT CHECK` with the reason. It never counts as passed.
5. Run before giving the owner the `git add` and `git commit` commands.

## Steps

**Step 1: scope.** `git diff <default branch> -- .claude/skills/verify/ ':!.claude/skills/verify/evidence'`, plus the untracked files in that folder except `evidence/`. If nothing changed, stop.

**Step 2: first check (a new subagent).** Get the model with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/models.py" doc-audit` and spawn one subagent with that model (for `inherit`, omit the model). Its prompt is `${CLAUDE_SKILL_DIR}/references/auditor-prompt.md` with `BASE`, `TASK`, and `OWNER_MESSAGES` (the absolute path `${CLAUDE_PLUGIN_ROOT}/scripts/owner_messages.py`) filled in.

**Step 3: fix.** For each failing item, the subagent that wrote the files (or a new one) removes the wrong line or makes it match its source; it adds no new content. An item that needs the owner's words (keep or remove a line that has no source) goes to the owner, one item per turn. Record the owner's answer with `turng-flow:task-record`.

**Step 4: recheck.** Send the same reviewer only the changed lines, and ask for the labels of those lines and the complete list of failing items still open. Call a new reviewer and check everything again when the previous one can no longer be reached or when the owner said something new about an item.

**Step 5: report to the owner**, in this order: (a) the list of failing items and the path of the saved table, (b) the first item the owner must decide. If an item is failing, do not give the commit commands until it is handled.

## Limits (tell the owner when relevant)

- The reviewer is also a model and can be wrong. Every label includes `path:line`, the command it ran, or the time and quote of the owner's message, so the owner can check it.
- `COVERED` proves the entry and the step exist, not that the step is sufficient. Whether a step checks enough is a judgement the reviewer marks as its own view.
- The reviewer reads the owner's messages from the transcripts on this machine only. A decision the owner made elsewhere shows as `NO SOURCE`.
