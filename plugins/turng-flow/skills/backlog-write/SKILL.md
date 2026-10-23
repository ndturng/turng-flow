---
name: backlog-write
description: Write an item in agent-workspace/BACKLOG.md in a fixed format, only from facts that can be checked (current code, the owner's verbatim words, what was decided, what is still open, whether it is scheduled). Use whenever adding, editing, or closing a backlog item (recording a debt, deferring work, recording a question the owner has not decided, updating after a task) before typing anything into BACKLOG.md.
---

# backlog-write

The backlog answers one question: **what is still to do, and is it scheduled.** A later session reading an item must know at once what the problem is, where the code is, what the owner decided, and what is still undecided, without searching again.

History (why, since when, how it was done) is not in the backlog. It is in `HISTORY.tsv` (skill `turng-flow:project-history`) and in the task folders. The backlog only points to them with `H-xxxx`.

## Scope

Every item in `agent-workspace/BACKLOG.md` follows this format and sits under a heading `## Structured items: <group>`. Groups are kinds of work, not priorities.

A project that moved from an older backlog may keep it as `agent-workspace/BACKLOG-old*.md` (the "old backlog"), for reference only, never edited. With several such files, `old:N` is checked against the longest one. Items carried over from it may use two things new items must not:
- "Sources" may add `old:<line number>`, pointing into the old backlog.
- When the old backlog says the owner decided something but the owner's words cannot be found in the session transcripts, the field "Owner decided" or "Schedule" starts with `source not traced; old backlog line N says ...`. Those are the old backlog's words, not the owner's; when the owner is available, ask again and replace them with a real quote.

## Item format

A heading `### B-001 [tag] Short name`, then exactly 7 lines, in this order, each at most 400 characters:

| Field | What it holds | The only allowed source | With no information, write |
|---|---|---|---|
| **Code state** | What the code is like now | The file, just opened and read; cite `path:line` and `checked YYYY-MM-DD` | `not checked` |
| **Work needed** | What to do, in one sentence | What the owner asked for, or a defect seen in the code | (required) |
| **Owner decided** | Verbatim `*"..."*` with the date | The owner's words in the session transcripts | `not decided` |
| **Open questions** | Questions without an answer yet | A question the owner asked and has not decided, or one the agent needs to ask | `none` |
| **Schedule** | When the owner scheduled it, or after what | The owner's verbatim words | `not scheduled` |
| **Agent proposal** | The agent's own view, if any | The agent; always kept here | `none` |
| **Sources** | `H-xxxx`, task folders | HISTORY.tsv | (required) |

Item ids `B-xxx` increase and are never reused.

## Rules

1. **No source, no fact.** A field without information gets exactly the wording in the last column. Do not fill it in or guess.
2. **The agent's judgement goes only in "Agent proposal".** Priority, "later", "small debt", "low risk", "cheap" are all judgements. The tag `[...]` only says the kind of work (`tech-debt`, `feature`, `security-debt`, ...), not how important it is.
3. **Only the owner sets "Schedule".** The agent does not schedule work or write "after MVP" on its own.
4. **The owner's words are verbatim**, and when the owner agrees to something, record exactly that, no wider.
5. **Read the code again when writing "Code state"**; do not copy it from memory or from an older item.
6. **HISTORY first, backlog second.** Before adding an item there must be a `debt-recorded`, `open-question`, or `owner-decision` row; "Sources" points to it.
7. **Remove a finished item completely**: no strike-through, no "done" mark. Before removing it there must be a HISTORY row `debt-closed`, `task-closed`, or `dropped` whose `refs` names the item. Remove it only when nothing in it still applies: an item with an unanswered "Open questions" stays, and is edited to keep only what still applies.
8. **Do not record test results, how the work was done, or the item's change history.** Those belong in the task folder.
9. **Edit the backlog in plan mode.** In work mode it is read only; if an item needs to change, ask the owner to run `/turng-flow:plan-mode`.

## Steps

1. Gather the facts: read the related code (get `path:line`); find the owner's words with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/owner_messages.py" | grep <keyword or date>`.
2. Write the HISTORY row (skill `turng-flow:project-history`).
3. Write the item in the format, under a `## Structured items: <group>` heading.
4. Run the checks and fix until they are clean:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_backlog.py"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" check
```

5. Before handing the owner the `git add` and `git commit` commands, run the skill `turng-flow:backlog-audit`.

## What the script can and cannot check

It checks: all 7 fields present and in order, lengths, the `checked YYYY-MM-DD` date in "Code state", owner quotes only in "Owner decided", "Open questions", or "Schedule" and found verbatim in the owner's messages, files and line numbers exist, at least one existing `H-xxxx` in "Sources", `old:N` within the old backlog, and that an item removed since the default branch has a `debt-closed`, `task-closed`, or `dropped` HISTORY row.

It cannot check: whether "Code state" describes the file correctly; whether a quote is used in the right context; whether "Work needed" is what the owner wants. The skill `turng-flow:backlog-audit` reviews these.
