---
description: Switch turng-flow to work mode: the agent carries out the approach the owner just approved.
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mode.py" set work`

Reply with the line above that starts with "turng-flow mode is now", and nothing else.
