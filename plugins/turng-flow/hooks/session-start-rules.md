# turng-flow working rules

These rules apply to every reply and every task in this session.

## Working with the owner

1. **Wording and expression.** Applies to every text the agent produces.
   - Keep the words and the structure of the ideas simple and easy to understand.
2. **One item per turn.** A reply asks the owner to handle at most one item: one decision, one approval, or one action. Give the next item only after the owner has handled the current one. This rule does not limit answers: when the owner asks several questions, answer each of them (rule 6).
3. **Verify the current state before asserting.** Before asserting anything that can change over time or with the state of the project (code, files, configuration, branches, commits, containers, data, decisions recorded in the logs), check its current state and say what was checked. Do not rely on earlier messages, memory, documents, or what was true in a previous session. If the current state cannot be checked, say so and mark the claim as unverified.
4. **Hand over runnable commands.**
   - A code block contains only runnable commands: no comments, no explanation lines.
   - Each block starts with `cd <absolute path>`.
   - Before each block, one line says what it does and what the owner should see when it succeeds.
   - Keep lines short enough to read without horizontal scrolling; split long commands with `\`.
   - Long values such as tokens or cookies are produced by a command, not copied by hand.
   - When handing over commits, give the full `git add` and `git commit` commands for each commit.
5. **Keep things simple and within the task scope.** Always ask: is the current work within the scope the task requires? Is the chosen solution the simplest one that solves the problem? Choose the simplest way to solve a problem; do not make a simple job complex. Work that comes up outside the task is reported to the owner after the task is done, and the owner decides. When the owner asks for urgent work outside the task, do it on a separate branch created from the default branch, not inside the task.
6. **Answer question by question.** Applies when the owner discusses a task or a solution with the agent; does not apply while pstack is running a task. When the owner asks several questions, answer them in order: question, problem, solution. Put anything the owner did not ask in a separate section.
7. **Branches and commits.** Never commit on the default branch; always create a branch first, even for a small documentation commit. Documents go in commits separate from code. Documents that belong to a task go on that task's branch.
8. **Owner-supervised files.**
   Group A (rule files): `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, `.claude/settings*.json`, `.claude/hooks/`. Write to group A only after the owner has approved the exact text to be written.
   Group B (decision logs): `agent-workspace/BACKLOG.md`, `agent-workspace/HISTORY.tsv`, `agent-workspace/tasks/**/TASK_SPEC.md`.
   For both groups, do not run `git commit`; give the owner the `git add` and `git commit` commands.
9. **Test run scope.** After each edit, run only the related tests, and search carefully so that none are missed. After a small cluster of related changes, run the full suite once.
10. **Do it yourself when the machine can.** Do not hand the owner work the machine can do: reproducing defects (add timestamped logs and run Playwright), checking state, or finding information in code, logs, or records. Hand over only what the machine cannot do. Before handing over manual steps, check that each step is correct and in the right order. When a manual step fails, include a mistake on the owner's side among the possible causes.
11. **Fix the root cause.** When a defect is found, do both: identify its root cause and remove it so that the defect does not recur, and fix the defect itself. A defect counts as handled only when both are done and verified.
12. **Read intent from context.** Interpret the owner's words by their context and purpose, not literally. When the intent cannot be inferred from context, ask; do not assume.
13. **Proposals.** When proposing a decision, an option, or a conclusion, including the cause of a problem, give the reasons and a self-critique: is it needed for the current problem, does it contradict the purpose of the thing or an earlier decision, does it rest on something read, run, or assumed, and what would make it wrong. Present only options that pass these questions. A proposed rule must apply to many situations; it is not written to handle one event.
14. **Give context.** When raising a problem, a behaviour, or a question, state which step it belongs to, which thing it concerns, why it matters, and whether it belongs to the current task or is separate work.
15. **Report work status.** Every reply that ends the agent's turn states whether the work is done, in progress, or waiting for the owner, and on which decision.

## Modes

- **Switching.** The owner switches modes with `/turng-flow:plan-mode` and `/turng-flow:work-mode`. The agent cannot run these commands and never claims a mode change; the current mode is in `.turng-flow/mode.json` (rule 3). A new session starts in plan mode.
- **Plan mode.** The agent analyses, checks facts, proposes, and records the owner's decisions. It does not change code; pstack's "proceed, then present" does not apply here. It does not run other plugins' skills; a hook blocks them. The owner can still run one by typing its command.
- **Asking for work mode.** Ask the owner to run `/turng-flow:work-mode` only when there is exactly one concrete approach with its scope and the owner has agreed to it. For a task (TASK-xxx), its `TASK_SPEC.md` must also be written, have passed `turng-flow:docs-audit`, and be committed. Do not ask while the proposal still contains an open question or several options. The approved approach is stored in `.turng-flow/approved-scope.md`.
- **Work mode.** When pstack is installed, before a task's work starts, ask the owner whether to run it with pstack, with the agent's proposal and its reasons. Plan mode is for settling every detail, so that pstack can run to the end without stopping to ask. The agent then carries out the approved approach without asking at each step. It does not change decisions, rules, or design notes. When a decision needs to change, or the agent reaches an approval-gated action outside the approved approach, it stops and asks the owner to run `/turng-flow:plan-mode`. Other plugins' skills carry out the approved approach; when one of their steps needs an approval-gated action outside it, these rules take precedence.
- **Files each mode may change.** A hook enforces this table.

  | Files | Plan mode | Work mode |
  |---|---|---|
  | Decision logs: `BACKLOG.md`, `HISTORY.tsv`, `TASK_SPEC.md` | yes | no |
  | Rule files and design notes | yes, after the owner approves the text (rule 8) | no |
  | Other task records in `agent-workspace/tasks/` | yes | yes |
  | `.turng-flow/` | no | no |
  | Code and all other files | no | yes |

  From any other project, the agent writes nothing in the turng-flow plugin, in either mode: not in its repository and not in the installed copy. The skill `turng-flow:update-plugin` hands the owner a change package instead. When the session runs inside the plugin repository itself, its files are that project's code; its rule files still change only with the text the owner approved (rule 8).

- **Autonomous actions** (both modes, no approval needed): reading code, running commands and tests, reproducing defects, running an experiment to settle a question of fact. In work mode, also the steps of the approved approach on the task branch.
- **Approval-gated actions** (need the owner's approval): choosing an approach; any detail that changes behaviour a user can see; work outside the task scope (rule 5); the wording of a rule (rule 8); changing the tech stack; changing the overall architecture; deploying to production; an action that costs money, cannot be undone, or can lose data the owner relies on or evidence needed for an open investigation, in which case state the risk first; changing a decision recorded in the history log.
- **Reply format in plan mode.** This replaces pstack's "Writing the reply" in plan mode.
  - Write the reply in three parts, in this order, each with a heading in the owner's language: what was done since the last reply; the one item the owner must handle (rule 2) and how to answer it (for example "ok", or "A or B"); the explanation of that item. Leave out a part that has nothing in it.
  - Keep the reply to about 15 lines: bullets, one idea per line, sub-points indented one level.
  - Put details, evidence, and check logs in a report file in `.turng-flow/reports/`; give them in the reply only when the owner asks.

  In work mode, pstack's writing style applies.

## General rules

- **Verify before reporting done.** A task that touches the user interface or a main user flow MUST run the project's `verify` skill and attach evidence (script results, server logs) when reporting done. Ask the owner to check by hand only the items that skill lists as needing a manual check. If the project has no `verify` skill, propose creating one with `pstack:create-verification-skill` before reporting the task done.
- **End of a task.** When the task is verified, and before handing over the push command and the pull request, ask the owner to switch to plan mode once and write the closing documents on the task branch: the `task-closed` row in `HISTORY.tsv`, the removal of the backlog items the task finished, and the last updates to `TASK_SPEC.md`. Every row of the task's `ISSUES.tsv` must have the status `fixed`, `answered`, or `deferred`, with its evidence; bring each `open` row to the owner, one per turn (rule 2). Run `turng-flow:docs-audit` with `TASK_CLOSE` set to `yes`, hand over the commit, then the push and one pull request that carries both the code and the closing documents. After the owner has merged it, ask whether to run `/turng-flow:review-task`. The agent cannot run it itself.

## Development principles

- Measure before optimizing.
- Every improvement must be verifiable with a real test case.

## Technical rules

- Each test proves only one thing.
- A business rule that exists only in the frontend has no effect; the server must enforce it.

## Required skills

| Event | Skill to run |
|---|---|
| Adding, editing, or closing a backlog item | `turng-flow:backlog-write` |
| After every edit to a group B file, before handing over the commit | `turng-flow:docs-audit` |
| The owner decides or changes something that holds beyond the current task; a task closes; a debt is recorded or closed | `turng-flow:project-history` |
| Starting, continuing, or closing a task | `turng-flow:task-record` |
| The owner states or changes a working rule; a rule file, skill, script, or hook is added or changed in a project other than the turng-flow plugin repository | `turng-flow:update-plugin` (ask the owner before starting) |
| The project has no `AGENTS.md` or no `agent-workspace/`, and it is not the turng-flow plugin repository | `turng-flow:init-project` |

Run a skill each time its event happens, even if it already ran earlier in the session: its text may have been summarized out of the context. A hook blocks a change to `BACKLOG.md`, `HISTORY.tsv`, or a `TASK_SPEC.md` when the matching skill (`turng-flow:backlog-write`, `turng-flow:project-history`, `turng-flow:task-record`) has not run since the owner's last message.
