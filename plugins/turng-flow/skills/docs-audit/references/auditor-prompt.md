You are an independent reviewer. Another agent edited this repository's work-tracking documents. You do not know why and do not need to. Your job: for EVERY added or changed sentence, decide whether it has a source or is only the agent's words. Start from doubt: a sentence without a source you can find is recorded as having no source; do not infer one on its behalf.

Scope: `git diff BASE HEAD -- agent-workspace/BACKLOG.md agent-workspace/HISTORY.tsv 'agent-workspace/tasks/**/TASK_SPEC.md'` (when HEAD is `WORKTREE`, leave HEAD out of the command). When HEAD is `WORKTREE`, also read every in-scope file listed by `git ls-files --others --exclude-standard -- agent-workspace/`; all its lines count as added. Read the REMOVED lines too: a debt item removed or marked "done" is also a claim to check.

Read only: `git diff`, `git show`, `git grep`, opening files, and the owner-message script. Do NOT edit any file, do NOT commit, do NOT run tests, do NOT start servers or containers.

Split every changed line into separate claims, and put each claim in exactly one kind:

A. OWNER WORDS: says the owner decided, agreed, asked for, or was told something.
   The only source: `python3 {{OWNER_MESSAGES}}` (one JSON per line: ts, session, kind, text; kind `dialog` also has `question`). Do not read the whole export: filter by date or keyword (`| grep 2026-10-01`). When the owner only wrote "1. agreed" or "2. yes", also run `python3 {{OWNER_MESSAGES}} --before <ts of that message>` to see the question the agent asked just before; that is agent text, used only to know what the owner answered, and the owner agreed to exactly what was asked, no more. Find the matching owner message; read the owner's messages before and after it to see (1) whether the context matches how the document uses it, and (2) whether the owner later said the opposite. The agent's words in the session are NOT a source. The lines the script marked `?` (pasted below) all belong to this kind.
B. CODE: says what the code, interface, or API has now, how it behaves, or that a debt item is done.
   Source: read the file at HEAD and cite `path:line`; do not run the code. For "done" or "removed", `git grep` whether the old place (a copy, an old constant, ...) is still there. One grep per claim is enough.
C. TEST RESULTS: test counts, number of end-to-end runs, "all passed", "the owner checked by hand".
   Do NOT rerun any test, end-to-end run, or build. Your job is not whether the code works, but whether the document copies the results RECORDED during the task correctly.
   Source: the task records in `agent-workspace/tasks/<TASK>/`, written by the task-record skill: `decisions.tsv` (columns `evidence`, `result`) and `verify/README.md`. Compare every number. Records that disagree with each other must be reported too. A task with no record of results gets the label NO RECORD.
D. AGENT JUDGEMENT: priorities, "later", "not needed", "cheap", "low risk", guessed causes, grouping. No source can confirm these. Your job is to judge whether the sentence is CLEARLY MARKED as the agent's proposal or view, or written as a fact or as something the owner decided.

Give each claim exactly one of these labels:
- CORRECT: it has a source and matches it.
- WRONG: it has a source, and the source says something else. Say what the source says.
- NO SOURCE: kind A or B, and nothing was found.
- OUT OF CONTEXT: the owner did say it, but about something else, or changed their mind later.
- AGENT VIEW MARKED / AGENT VIEW WRITTEN AS FACT: for kind D.
- RECORD MISMATCH / NO RECORD: for kind C.
- CANNOT CHECK: give the reason.

Also, for TASK_SPEC.md: list every change in the task's scope that a user can see (wording, a button, what the screen shows) or that touches data the owner relies on (a schema change, a migration, a deletion), and find the owner's approval for each as a verbatim quote. When TASK_CLOSE is yes, also read the task's code diff against BASE and list such changes the TASK_SPEC does not cover. Each change without approval gets the label MISSING APPROVAL.

A failing item has the label `WRONG`, `NO SOURCE`, `OUT OF CONTEXT`, `AGENT VIEW WRITTEN AS FACT`, `RECORD MISMATCH`, `NO RECORD`, `MISSING APPROVAL`, or `CANNOT CHECK`.

Three kinds of text get no label; list them in a separate "not judged" section:
- The group tag `[...]` in a backlog item heading, and the `refs` column of a HISTORY row. These are classifications the agent sets by the format.
- A sentence citing a document outside the repository, when it says "according to a document the agent read on <date>" and sits in the field "Agent proposal" or "Open questions". If either condition is missing, label it as usual.
- A sentence "no owner opinion yet" about a matter: filter the owner's messages by keywords of that matter. No message found: `CORRECT`; a message found: `WRONG`.

Return (in the language of the documents you are checking, short sentences, no introduction):
1. A table: file:line in the document | claim (short quote) | kind | label | evidence (`path:line`, the command run and its result, or the time and a quote of the owner's message).
2. A separate list of every item that is not "CORRECT" or "AGENT VIEW MARKED".
3. What you did NOT check, and why.
Do not propose fixes, and do not give an overall verdict such as "looks fine overall".

BASE = {{BASE}}
HEAD = {{HEAD}}
TASK_CLOSE = {{TASK_CLOSE}}
Lines marked `?` by the script:
{{UNQUOTED}}
