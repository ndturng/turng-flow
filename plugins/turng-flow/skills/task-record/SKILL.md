---
name: task-record
description: Keep the record of how a task (TASK-xxx) was done, so a later session can look it up. Use when starting, continuing, or finishing a task ("TASK-039", "task 39", "start task N", "continue task N"), including while pstack:poteto-mode or another playbook leads the work; when asked how a task or an earlier session was done; when asked to record, trace, or review past task work; and when handing over a pull request. Runs alongside pstack:poteto-mode and does not replace it.
---

# Task record

pstack keeps no lasting record inside the repository (transcripts live outside it, and `decisions.tsv` is not committed by default). This skill keeps that record in the repository. Commits and pull requests cover the rest; this skill adds no other files.

## Folder

`agent-workspace/tasks/TASK-<id>-<short-name>/`, created when the task starts:

| File | Content | When |
|---|---|---|
| `TASK_SPEC.md` | The owner's requirements, the questions asked, the owner's answers, the scope limits | Before handing out work or writing code, in plan mode. Record exactly what the owner decided, with no added interpretation. If the owner decides something new while in work mode, stop and ask the owner to run `/turng-flow:plan-mode` before updating it. |
| `decisions.tsv` | One decision per row, in the format of the skill `pstack:show-me-your-work` (use `scripts/log.sh` inside that skill's folder, not in this plugin) | As it happens: the approach chosen, work handed out, changes of direction, verification, the agent's own mistakes. When a row is wrong, add a new row with `phase` set to `correction` whose `decision` names the `ts` of the row it replaces; never edit an old row. |
| `ISSUES.tsv` | One row per issue. Columns: `id` (`I-01`, `I-02`, …), `raised` (date), `by` (`owner`, `agent`, `reviewer`, `test`), `source` (`owner:<time>`, a `decisions.tsv` `ts`, a reviewer report, a test name), `issue`, `status` (`open`, `fixed`, `answered`, `deferred`), `evidence` | As soon as an issue appears: an owner question or request not yet answered, a defect, a debt, anything not covered or not yet checked, a reviewer finding. Later edits change only `status` and `evidence`; never delete a row. `fixed` names a commit or a test; `answered` quotes the owner verbatim with the time; `deferred` names a backlog item `B-xxx` that quotes the owner. |
| `verify/` | `README.md` (how to run, results, what is not covered) and the scripts that set up this task's test state | When verification is done. Do not leave scripts in a temporary scratchpad. Scripts that the project's `verify` skill keeps in another location stay there; `README.md` gives their paths. |

## Rules

- Before setting up a test environment, or when the owner asks how an earlier task or session was done: first read `agent-workspace/tasks/TASK-<earlier task>-*/verify/README.md` and `decisions.tsv`. Read those folders before searching containers or old transcripts, and do not answer "there is none" before reading them.
- State every claim at the level of its evidence: separate "I ran it" from "an agent reported it". Every test count says who ran it.
- Anything not covered (cannot be checked, not yet checked) is written in `verify/README.md` and as a row in `ISSUES.tsv`.
- The task's verification requirements win over older notes. If a note (in a skill, a CLAUDE.md, or another document) contradicts a clear requirement of the task, follow the task and report that the note is outdated.
- At the end of the task, `turng-flow:docs-audit` with `TASK_CLOSE` set to `yes` checks `decisions.tsv` and `ISSUES.tsv` against the transcripts of the sessions that worked on the task (`~/.claude/projects/<project path with every non-alphanumeric character as "-">/<session>.jsonl`). Do not run a separate check. Record corrections as new rows in `decisions.tsv` and as new or updated rows in `ISSUES.tsv`.
- Do not commit or push until the owner says so. Never commit `TASK_SPEC.md` yourself (rule 8): give the owner the `git add` and `git commit` commands. Task records go in commits separate from code, on the task's branch (rule 7). In the report, say what was written where and what is still uncommitted.
- **Handing over a pull request:** if a push fails because this machine has no GitHub access (no `gh`, credential helper, or SSH key), stop retrying. Put the push command, the pull request title, and the description directly in the chat as copyable blocks, not in a file. When the owner says it is merged, check it yourself with `git fetch`, `git log origin/<default branch>`, and `git status -sb`. If `git fetch` also fails for lack of access, say that the merge is unverified (rule 3); do not ask the owner to confirm again.
- **Closing a task:** the closing documents go on the task branch, into the task's own pull request, before it is opened (working rules, "End of a task").
- For a long multi-phase task, or while the owner is away: write the log as you go, not afterwards.
