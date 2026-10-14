# turng-flow working rules

These rules apply to every reply and every task in this session.

## Working with the owner

1. **Wording.** Applies in every language, to every reply and every text the agent writes: documents, rules, notes, commit messages.
   - Use plain words, one meaning per word. No figurative speech, no wordplay.
   - Words must be objective. Where a technical term is needed, use the term the industry uses.
   - Call each thing by the exact name the project uses.
   - When writing content from the owner's words, rephrase it in neutral wording; do not reuse emotionally loaded words. Verbatim quotes kept as evidence in the backlog and the history log are outside the scope of this rule.
   - State whether a piece of work belongs to the current task or is separate work.
2. **One item per turn.** A reply gives the owner only one item to handle. Give the next item only after the owner has handled the current one.
3. **Verify before asserting.** Before saying that something is committed, pushed, merged, enabled, or disabled, run a command that checks the real state and report its result. Do not ask the owner anything a command can answer.
4. **Hand over runnable commands.** A code block contains only runnable commands: no comments, no long lines that need horizontal scrolling. When handing over commits, give the full `git add` and `git commit` commands for each commit.
5. **Do not add problems.** In all work, solve only the problem that needs solving now. Do not raise problems that do not need solving now. Do not make a simple job complex. Do not drift from the original request.
6. **Answer question by question.** Applies when the owner discusses a task or a solution with the agent; does not apply while pstack is running a task. When the owner asks several questions, answer them in order: question, problem, solution. Put anything the owner did not ask in a separate section.
7. **No commits on `main`.** Always create a branch first, even for a small documentation commit.
8. **Owner-supervised files.**
   Group A (rule files): `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`, `.claude/settings*.json`, `.claude/hooks/`. Write to group A only after the owner has approved the exact text to be written.
   Group B (decision logs): `agent-workspace/BACKLOG.md`, `agent-workspace/HISTORY.tsv`, `agent-workspace/tasks/**/TASK_SPEC.md`.
   For both groups, do not run `git commit`; give the owner the `git add` and `git commit` commands. Do not put files of these two groups in the same commit as code.
9. **Test run scope.** After each edit, run only the related tests, and search carefully so that none are missed. After a small cluster of related changes, run the full suite once.
10. **UI defects: reproduce them yourself.** Add timestamped logs and run Playwright to find the cause. Ask the owner only for what the machine cannot do.
11. **Fix the root cause.** When a defect is found, do both: fix that defect, and identify its root cause and remove it so that the defect does not recur. A defect counts as handled only when both are done and verified.

## General rules

- Do not change the tech stack without a clear reason and the owner's approval.
- Do not start implementing "future" features while the MVP is unfinished.
- When the owner's intent cannot be inferred from context, ask; do not assume.
- **Verify before reporting done.** A task that touches the user interface or a main user flow MUST run the project's `verify` skill and attach evidence (script results, server logs) when reporting done. Ask the owner to check by hand only the items that skill lists as needing a manual check.

## Development principles

- Measure before optimizing.
- Build the quality-evaluation system before handling edge cases.
- Every improvement must be verifiable with a real test case.

## Technical rules

- Each test proves only one thing.
- A business rule that exists only in the frontend has no effect; the server must enforce it.

## Required skills

| Event | Skill to run |
|---|---|
| Adding, editing, or closing a backlog item | `turng-flow:backlog-write` |
| After every edit to a group B file, before handing over the commit | `turng-flow:backlog-audit` |
| The owner decides or changes something that holds beyond the current task; a task closes; a debt is recorded or closed | `turng-flow:project-history` |
| Starting, continuing, or closing a task | `turng-flow:task-record` |
