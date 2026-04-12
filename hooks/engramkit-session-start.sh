#!/bin/bash
# EngramKit SessionStart hook — injects wake-up context into Claude's session.
# Silent if engramkit isn't installed or no vault exists for this repo.
set -e
INPUT=$(cat)
if ! command -v python3 >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi
echo "$INPUT" | python3 -m engramkit.hooks.claude_hook_handler session-start 2>/dev/null || echo '{}'
