# turng-flow working rules

These rules apply to every reply and every task in this session.

## Working with the owner

1. **Wording.** Applies in every language, to every reply and every text the agent writes: documents, rules, notes, commit messages.
   - Use plain words, one meaning per word. No figurative speech, no wordplay.
   - Words must be objective. Where a technical term is needed, use the term the industry uses.
   - Call each thing by the exact name the project uses. Do not invent labels, codes, or nicknames for things; if a short name is needed, define it at first use.
   - When writing content from the owner's words, rephrase it in neutral wording; do not reuse emotionally loaded words. Verbatim quotes kept as evidence in the backlog and the history log are outside the scope of this rule.
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
13. **Proposals.** When proposing a decision, an option, or a conclusion, including the cause of a problem, give the reasons and a self-critique: is it needed for the current problem, does it contradict the purpose of the thing or an earlier decision, does it rest on something read, run, or assumed, and what would make it wrong. Present only options that pass these questions.
14. **Give context.** When raising a problem, a behaviour, or a question, state which step it belongs to, which thing it concerns, why it matters, and whether it belongs to the current task or is separate work.
15. **Report work status.** Every reply that ends the agent's turn states whether the work is done, in progress, or waiting for the owner, and on which decision.

## General rules

- Do not change the tech stack without a clear reason and the owner's approval.
- **Verify before reporting done.** A task that touches the user interface or a main user flow MUST run the project's `verify` skill and attach evidence (script results, server logs) when reporting done. Ask the owner to check by hand only the items that skill lists as needing a manual check. If the project has no `verify` skill, propose creating one with `pstack:create-verification-skill` before reporting the task done.
- **State risks before acting.** Before an action that costs money, cannot be undone, or can lose data the owner relies on or evidence needed for an open investigation, state the risk and wait for the owner's approval.

## Development principles

- Measure before optimizing.
- Every improvement must be verifiable with a real test case.

## Technical rules

- Each test proves only one thing.
- A business rule that exists only in the frontend has no effect; the server must enforce it.
