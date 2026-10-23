---
name: project-history
description: Record the project's history in agent-workspace/HISTORY.tsv: what the owner decided, changes of direction, open questions, debts recorded or closed, tasks closed, corrections. Use as soon as the owner decides or changes something that holds beyond the current task, when a task closes, when a debt is recorded or closed, when correcting something recorded wrongly, and when looking up why or since when the project works a certain way.
---

# project-history

`agent-workspace/HISTORY.tsv` answers one question: what happened to the project, who decided, when, and on what basis.

## Boundary with other files

| Information | Lives in | Not in |
|---|---|---|
| Work still to do, current state, scheduled or not | `BACKLOG.md` (skill `turng-flow:backlog-write`) | HISTORY |
| Events that happened, owner decisions | `HISTORY.tsv` | BACKLOG (it only points to `H-xxxx`) |
| How a task was done, test results | `tasks/<TASK>/decisions.tsv`, `verify/README.md` | HISTORY (it only points with `task:`) |
| How the owner wants the agent to work and present things | the agent's memory | HISTORY |

Each fact lives in one place. Other places point to it and do not copy it.

## What to record

Events that take effect outside the current task. A decision that only matters inside one task stays in that task's `decisions.tsv`.

| Type | When | Required |
|---|---|---|
| `owner-decision` | The owner decides something | Verbatim quote + `owner:<time>` |
| `direction-change` | The owner changes the order of work or drops a direction | Same |
| `open-question` | The owner asks or requests something not yet decided | Same; say "not decided" |
| `dropped` | The owner drops a piece of work or a backlog item | Same; `refs` names the item |
| `debt-recorded` | A debt item is added to the backlog | `refs` names `B-xxx` |
| `debt-closed` | A debt item is resolved | `git:` or `task:`; `refs` names `B-xxx` |
| `task-closed` | A task is merged | `git:<merge sha>` and `task:` |
| `correction` | An earlier row or document was wrong | `refs` names the `H-xxxx` corrected |

## Rules

1. **Write only through the script.** It refuses rows whose sources or owner quotes cannot be checked; do not edit the file by hand. The other entries in the "Required" column are conventions the script does not check; `turng-flow:backlog-audit` reviews them.
2. **Append only.** Never change or delete an old row. When the owner changes their mind, add a new row whose `refs` points to the old one.
3. **Owner words are verbatim**, as `*"..."*`, taken from the owner's message at the time cited in `source`. Do not restate the owner's intent in the agent's words and record it as an owner decision. If the owner only answered "agreed" or "1. a", quote exactly that and describe the question outside the quote.
4. **Do not record the agent's opinions.** An agent proposal belongs in the "Agent proposal" field of a backlog item, not in the log.
5. **One sentence, at most 300 characters.** Details stay in the source.
6. **Record when it happens**, not in a batch at the end of the session.
7. **Record in plan mode.** In work mode the log is read only; if a decision needs recording, ask the owner to run `/turng-flow:plan-mode`.

## Commands

Find the time of an owner message (filter by date or keyword; do not read the whole export):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/owner_messages.py" | grep <YYYY-MM-DD>
```

Add a row (the id is assigned; the date defaults to today; add `--date` for an older event):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" add \
  --type owner-decision \
  --what 'Release order: *"<owner words, verbatim>"*.' \
  --source "owner:<YYYY-MM-DDTHH:MM>"
```

Check the whole log (format, consecutive ids, sources exist, quotes match, no old row changed compared with the base branch; `--base` defaults to the repository's default branch):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" check
```

To look something up, grep `agent-workspace/HISTORY.tsv` by task id, item `B-xxx`, or keyword.

## Limits

- The script sees the owner's words only in the Claude Code session transcripts on this machine. A decision the owner made elsewhere cannot be recorded as `owner-decision`; ask the owner to confirm it in the session.
- The script checks that a quote is real, not that the text outside the quote summarizes the context correctly. The `turng-flow:backlog-audit` skill reviews that.
- Owner message times are in UTC.
