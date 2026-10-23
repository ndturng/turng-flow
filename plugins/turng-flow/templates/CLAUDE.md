# CLAUDE.md: <project name>

@AGENTS.md

## What this file holds

- The rules are in `AGENTS.md` (imported above) and in the turng-flow plugin. This file holds no rules.
- It records facts about the machine, containers, commands, and where documents are. Each fact was checked by a command on <date>, unless a line names another source.

## Machine and access

- <GitHub access from this machine: yes or no; who pushes and opens pull requests>

## Containers and ports

- <name, port, what each runs; how a change reaches it>

## Commands

| Task | Command |
|---|---|
| Run tests | <command> |
| Build | <command> |
| Start the app | <command> |

## Not in git

- <files and folders in .gitignore that a new worktree will not have, such as .env>

## Where documents are

| Need to know | Look in |
|---|---|
| Work still to do | `agent-workspace/BACKLOG.md` |
| Decisions, changes of direction, closed work | `agent-workspace/HISTORY.tsv` |
| Records of each task | `agent-workspace/tasks/TASK-<id>-<short-name>/` (skill `turng-flow:task-record`) |
| Design notes | `agent-workspace/design-notes/` |
