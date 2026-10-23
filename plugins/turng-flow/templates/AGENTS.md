# AGENTS.md: <project name>

Claude Code loads this file at the start of every session. It holds what is specific to this project. The working rules that apply to every project come from the turng-flow plugin.

## Project overview

- **Goal:** <what the product is for, and for whom>
- **Tech stack:** <languages, frameworks, services>
- **Repository layout:** <main folders and what each holds>

## Status

Task status (done, in progress, not started, priority) is in `agent-workspace/BACKLOG.md`, the single source of truth. This file does not repeat the task list, so nothing has to be edited in two places.

## Architecture (do not change without the owner's approval)

<the main data flow, as a short diagram or list>

## Project rules

- Do not overfit to <one user or one use case>.
- Only one place stores <a kind of data>, and only one place calls <the call that creates it>; later tasks do not add another path.
- Do not implement features outside the current priorities while the first usable version (MVP) is unfinished.
- <if the product's output quality is judged, for example by a model> Build the quality-evaluation system before handling edge cases.

## When to stop and ask the owner

- <areas of this project where the agent must stop and ask the owner>
