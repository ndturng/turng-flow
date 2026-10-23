---
name: update-plugin
description: Move a new or changed working rule, skill, script, or check from the current project into the turng-flow plugin, so every project gets it. Use when, during any project other than the plugin repository itself, the owner states a new way of working, a rule file or skill is added or changed, or the agent notices that a project file now holds something that applies to any project. Ask the owner before starting.
---

# update-plugin

The turng-flow plugin holds everything that applies to any project. Each project keeps only what is specific to it. This skill moves a candidate from a project into the plugin, so the owner never copies files by hand.

## When to start

A candidate appears when one of these happens in a project:
- The owner states a new rule for how the agent works, or changes one.
- A rule file (`AGENTS.md`, `CLAUDE.md`), a skill, a script, or a hook is added or changed in the project.
- A memory note records a way of working that is not tied to the project.

Do not start the work on your own. Ask the owner, as the one item of that turn (rule 2): "This looks like it applies to any project. Run the plugin update process for it?" State the candidate in one or two sentences. If a task is in progress and the owner did not start this process, note the candidate and ask after the task's last item is handled (rule 5).

## Step 1: analyse each candidate

For each candidate, write one row:

| Candidate | Shared or project-specific | Why | Where in the plugin | Overlaps |
|---|---|---|---|---|

- **Shared or project-specific.** It is project-specific when it names something that exists only in this project: a product, a code path, a container, a command, a task id, a data set, a decision about this product. Otherwise it is shared.
- **Where in the plugin.** One of: a rule in `hooks/session-start-rules.md` (name the section), a skill in `skills/`, a script in `scripts/`, a hook, a reference file, or a project template in `templates/`. A template change reaches only projects set up later; existing projects are updated by hand in step 5.
- **Overlaps.** Compare with every existing plugin rule and skill. Name each overlap or conflict and propose how to merge, so one fact lives in one place.

Show the table for all candidates, with what you propose to move, leave, or drop and why, and a self-critique (rule 13). Then ask the owner to decide one candidate per turn.

## Step 2: wording

After the owner has decided step 1 for a candidate, write the exact English text to add or change in the plugin, following rule 1. When a skill moves from a project, its name becomes `turng-flow:<name>`: list every file that names it (the project's `AGENTS.md`, `CLAUDE.md`, other skills, the plugin's "Required skills" table) and include those changes. The owner approves the exact text before anything is written (rule 8 applies to the plugin's rule files and skills).

## Step 3: hand the owner the change package

The agent never writes to the plugin repository; the owner applies the change there. The owner may do this on another machine, or another person may maintain the plugin, so the package must work without the agent and without the plugin repository on this machine.

1. Base: the installed copy at `${CLAUDE_PLUGIN_ROOT}` (read only). Its version is in `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plugin_package.py" start <short-name>`. It copies the installed plugin into `.turng-flow/reports/plugin-update-<date>-<short-name>/new/plugins/turng-flow/` and prints that folder.
3. Write the approved text into the files under `new/`. Raise the patch number of the version in `new/plugins/turng-flow/.claude-plugin/plugin.json` once; installed copies update only when the version changes.
4. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plugin_package.py" finish <package folder>`. It writes `changes.patch` (paths relative to the plugin repository root) and `CHANGES.md` (each changed file with its full new text, the base version, and the owner's steps below), runs `claude plugin validate` on `new/`, and prints the package folder.
5. Give the owner the package folder and these steps (rule 4), and say whether the change touches rules, modes, or hooks (then propose `/turng-flow:trial` after updating):
   - In the plugin repository: create a branch from the default branch, run `git apply <package>/changes.patch`, check that `git diff` matches `CHANGES.md`, commit, merge, push.
   - If `git apply` fails because the repository is not at the base version, apply the full texts in `CHANGES.md` by hand.

## Step 4: update the installed plugin

After the owner has merged and pushed the change, hand the owner the update commands. On success `claude plugin list` shows the new version:

```bash
cd /
claude plugin marketplace update turng-flow
claude plugin update turng-flow@turng-flow
```

If `claude plugin list` does not show `turng-flow@turng-flow`, hand over the first-install commands instead: `claude plugin marketplace add <marketplace source>` and `claude plugin install turng-flow@turng-flow --scope <scope>`.

A running session keeps the old rules; a new session loads the new ones. The same two update commands apply on every machine that uses the plugin. Memory notes exist only on the machine that wrote them.

## Step 5: remove the copy from the project

After `claude plugin list` shows the new version installed, propose removing the project's copy from `AGENTS.md`, `CLAUDE.md`, the project skill, or the memory note, so one fact lives in one place. Show the exact lines to remove; the owner approves them (rule 8). The removal happens in plan mode, on a branch of the project repository, in its own documentation commit (rule 7). If the removal changes a decision recorded in `HISTORY.tsv`, add a row with `turng-flow:project-history`.
