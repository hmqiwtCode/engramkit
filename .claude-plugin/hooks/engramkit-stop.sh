#!/bin/bash
# EngramKit Stop hook — blocks Claude to save when importance threshold crossed.
set -e
INPUT=$(cat)
if ! command -v python3 >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi
echo "$INPUT" | python3 -m engramkit.hooks.claude_hook_handler stop 2>/dev/null || echo '{}'
