---
name: init-project
description: Set up a repository for the turng-flow workflow: AGENTS.md, CLAUDE.md, and agent-workspace/ with the backlog, the history log, and the task and design-note folders. Use when a project other than the plugin repository has no AGENTS.md or no agent-workspace/ folder, or when the owner asks to set up a new project for turng-flow.
---

# init-project

Every turng-flow project keeps its own facts and decisions in the same layout, so the plugin's skills and checks work in it without changes.

## Steps

Run every step in plan mode. If `.turng-flow/mode.json` says work mode, ask the owner to run `/turng-flow:plan-mode` first.

1. Show the owner the result of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_project.py" --dry-run` and the full text of `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md` and `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md`. These are rule files (rule 8): the owner approves this text before step 2. Existing files are never overwritten; the script lists them as kept.
2. Hand the owner the command that creates a branch (rules 4 and 7). After the owner runs it, create the files: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_project.py"`.
3. Fill the placeholders `<...>` in `AGENTS.md` and `CLAUDE.md`:
   - Facts the machine can find (tech stack, folders, commands, containers, ports, what `.gitignore` excludes): read the repository and run commands yourself (rule 10). Write the date of the checks in place of `<date>`; a fact checked on another date names its own date in its line.
   - Facts only the owner knows (the product's goal, the architecture decisions, the project rules, the areas where the agent must stop and ask): ask the owner, one item per turn (rule 2).
   - Replace or delete every placeholder `<...>` in a line that describes this project. Leave the folder patterns in the table "Where documents are".
   - The owner approves the exact text of each change to `AGENTS.md` and `CLAUDE.md` before it is written (rule 8).
4. If the project has a user interface or a main user flow and no `verify` skill, propose creating one with `pstack:create-verification-skill`.
5. Hand the owner the `git add` and `git commit` commands for the new files (rules 4 and 7). Do not commit. The empty `BACKLOG.md` and `HISTORY.tsv` hold no claims, so `turng-flow:backlog-audit` is not needed for them; it applies from the first item or row written.

## Notes

- The project files hold only what is specific to the project. A rule that applies to any project belongs in the plugin; use the skill `turng-flow:update-plugin` to move it there.
- `.turng-flow/` (the owner's mode state and reports) ignores itself in git; nothing needs to be added to `.gitignore`.
- A change to the plugin's templates does not reach projects set up earlier.
