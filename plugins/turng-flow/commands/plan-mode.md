---
description: Switch turng-flow to plan mode: the agent analyses and proposes, and cannot edit files.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mode.py" set plan`

Reply with the line above that starts with "turng-flow mode is now". Then, if your reply just before this command named a next step that the new mode allows, carry it out now. Otherwise stop after that line.
