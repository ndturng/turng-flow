---
description: Switch turng-flow to work mode: the agent carries out the approach the owner just approved.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mode.py" set work`

Reply with the line above that starts with "turng-flow mode is now". Then, if your reply just before this command named a next step that the new mode allows, carry it out now. Otherwise stop after that line.
