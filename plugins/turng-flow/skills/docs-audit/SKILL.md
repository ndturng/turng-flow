---
name: docs-audit
description: Check what the agent just wrote in BACKLOG.md, HISTORY.tsv, or TASK_SPEC.md: whether each sentence matches what the owner decided and what the code says, or is the agent's own conclusion. Use when the owner asks for it, and always after every edit to those files, before handing the owner the commit commands.
---

# docs-audit

Purpose: decide whether the documents were put together objectively from existing facts, or contain inference or invention. It does not check whether the code works and does not rerun tests. It separates four kinds of statement and checks each against a source other than the agent that wrote it:

| Kind of statement | Source checked | Who checks |
|---|---|---|
| Owner words (verbatim `*"..."*`) | Session transcripts: only messages the owner typed and answers the owner chose | Script |
| What the code has now | Reading the code, with `file:line` (no running) | Independent reviewer |
| Test results | Task records written by `turng-flow:task-record`: `decisions.tsv`, `verify/README.md` (no rerunning tests) | Independent reviewer |
| Judgements, priorities, "later", "not needed" | No source, so they must be marked as the agent's view | Independent reviewer |

## Rules

1. The agent that wrote the change does not check the CODE and TEST RESULTS kinds (B and C in the reviewer prompt) in place of the reviewer. The first check of a change goes to a new subagent, told nothing about why the change was made: give it only `${CLAUDE_SKILL_DIR}/references/auditor-prompt.md` and the scope of the diff. Later checks of the same change go to that same reviewer (step 4).
2. Do not edit the documents while the reviewer runs. After the check, the agent fixes the items it wrote wrongly, then reruns steps 0, 1, and 4, without asking the owner. Fix by removing the wrong sentence or making it match its source; do not add new content. A HISTORY row that is not yet committed may be corrected in place. Ask the owner only when an item needs the owner's words and the transcripts do not have them. Report to the owner once at the end: what was fixed, and the result of the last check.
3. Report the script output and the reviewer's table verbatim. Do not summarise away failing items or add defences between them. Any view of the writing agent goes in a separate section at the end.
4. An item that could not be checked is labelled `CANNOT CHECK` with the reason. It never counts as passed.
5. Run before handing the owner the `git add` and `git commit` commands. If it is already committed, use `--head <branch>`.
6. A matter the owner has not answered is recorded as "no owner opinion yet (checked <sources>, <date>)". Ask the owner for a clear answer when it is either an important decision about direction, or something the next step cannot proceed without. The question must stand on its own, so the owner can answer without searching the conversation: state the problem, the context (the related `B-xxx` or `H-xxxx`, the current state, what the owner already decided), and the options if any. Otherwise do not ask; record it in "Open issues".
7. Edits made to fix audit findings happen in plan mode, like every edit to the decision logs (`BACKLOG.md`, `HISTORY.tsv`, `TASK_SPEC.md`).

## Failing items and items not judged

A failing item has the label `WRONG`, `NO SOURCE`, `OUT OF CONTEXT`, `AGENT VIEW WRITTEN AS FACT`, `RECORD MISMATCH`, `NO RECORD`, `MISSING APPROVAL`, `MISSING ISSUE`, or `CANNOT CHECK`.

A sentence that claims something is absent ("no owner opinion yet", "no open issue recorded") names the sources it searched. The reviewer searches exactly those sources. Nothing found: `CORRECT`. Something found: `WRONG`, naming what was found. No sources named: `NO SOURCE`.

Two kinds of text get no label; the reviewer lists them in a separate "not judged" section:
- The group tag `[...]` in a backlog item heading, and the `refs` column of a HISTORY row. These are classifications the agent sets by the format.
- A sentence citing a document outside the repository, when it says "according to a document the agent read on <date>" and sits in the field "Agent proposal" or "Open issues". If either condition is missing, label it as usual.

## Steps

Default scope: changes, compared with the default branch, to `agent-workspace/BACKLOG.md`, `agent-workspace/HISTORY.tsv`, and every `agent-workspace/tasks/**/TASK_SPEC.md`.

**Step 0: format (script, seconds).** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_backlog.py"` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" check`. On errors, stop and report to the owner.

**Step 1: owner words (script).**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_quotes.py"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_quotes.py" --head <branch>
```

The first line checks the files on disk, the second a committed branch.

- `FOUND`: the quote appears verbatim in an owner message; with the time and session id so the owner can look it up.
- `MISSING`: no owner message contains it. The nearest owner message is shown for comparison.
- `?`: the line mentions the owner ("the owner decided", "told the owner", ...) without a verbatim quote. The script cannot check it; it goes to the reviewer in step 3.
- A quote with `…` must have every fragment on either side inside the same owner message.

**Step 2: self-check (by the agent that wrote the change, before calling the reviewer).** Read every added or changed line again. Fix at once any of these:
- The field "Work needed", "Owner decided", or "Schedule", or a HISTORY row, contains an idea that is not in the quoted owner words.
- A sentence about code lacks `path:line`, or leaves out a condition the code has (a switch, a default value).
- The agent's view appears outside the field "Agent proposal" without the word "agent".
- A sentence citing a document outside the repository lacks "according to a document the agent read on <date>".
- "Sources" cites an `H-xxxx` whose HISTORY row does not name this item in `refs`.
- A sentence claims the agent asked, did not ask, or told the owner something. Replace it with "no owner opinion yet".

The self-check does not replace step 3.

**Step 3: first check (a new subagent).** First save a copy of each file in scope with the Write tool to `.turng-flow/reports/docs-audit/<same relative path>` (plan mode blocks shell copies). Get the model with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/models.py" doc-audit` and spawn one subagent with that model (for `inherit`, omit the model). Its prompt is `${CLAUDE_SKILL_DIR}/references/auditor-prompt.md` with `BASE`, `HEAD`, `TASK_CLOSE` (`yes` when the check is part of closing a task, otherwise `no`), the `?` lines from step 1, and `OWNER_MESSAGES` (the absolute path `${CLAUDE_PLUGIN_ROOT}/scripts/owner_messages.py`) filled in. `BASE` is the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD` without `origin/`, otherwise `main` or `master`); `HEAD` is `WORKTREE` for files not yet committed, otherwise the branch name.

**Step 4: recheck the changed lines (the same reviewer).** After fixing, list the changed lines with `diff` between the copy in `.turng-flow/reports/docs-audit/` and the current file, then save the new version there with the Write tool. Send the step 3 reviewer `${CLAUDE_SKILL_DIR}/references/recheck-prompt.md` with that list. Do not explain why the lines changed. The reviewer judges only the listed lines; the labels of unchanged lines carry over.
Call a new reviewer and check everything again (step 3) when any of these holds: new code was committed since the last check; the owner said something new about an item being checked; the previous reviewer can no longer be reached.

**Step 5: report to the owner**, in this order: (a) the script output verbatim, (b) the reviewer's table, (c) the first item the owner must decide; give the next one only after the owner has handled it (working rule 2). If a script exits with a non-zero code or the reviewer has failing items, do not hand over the commit commands until the owner answers.

## Limits (tell the owner when relevant)

- The script reads only the Claude Code session transcripts on this machine (`~/.claude/projects/<project path with every non-alphanumeric character as "-">/*.jsonl`). A decision the owner made elsewhere (spoken, another machine, a deleted session) shows as `MISSING` even if it is real.
- `FOUND` only proves the owner once typed those exact words. It does not prove the sentence uses them in the right context, or that the owner did not change their mind later; the reviewer reads the owner's messages around that time to judge this (`${CLAUDE_PLUGIN_ROOT}/scripts/owner_messages.py` prints every owner message as one JSON per line).
- A sentence the agent wrote in its own words and attributed to the owner, without `*"..."*` and without the word "owner", is invisible to the script. Only the reviewer can catch it.
- The reviewer is also a model and can be wrong. Every conclusion it gives includes `file:line` or the command it ran, so the owner can check it.
