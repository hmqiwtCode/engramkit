#!/bin/bash
# EngramKit Auto-Save Hook for Claude Code
#
# Fires on Claude Code "Stop" event. Analyzes conversation importance
# and tells Claude to save key content to the vault.
#
# INSTALL: Add to .claude/settings.local.json:
#
#   "hooks": {
#     "Stop": [{
#       "matcher": "*",
#       "hooks": [{
#         "type": "command",
#         "command": "python3 -m engramkit.hooks.claude_hook_handler stop",
#         "timeout": 30
#       }]
#     }],
#     "PreCompact": [{
#       "hooks": [{
#         "type": "command",
#         "command": "python3 -m engramkit.hooks.claude_hook_handler precompact",
#         "timeout": 30
#       }]
#     }]
#   }
#
echo "EngramKit hook loaded"
