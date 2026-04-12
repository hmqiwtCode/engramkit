#!/bin/bash
# EngramKit PreCompact hook — always blocks to force a full save before compaction.
set -e
INPUT=$(cat)
if ! command -v python3 >/dev/null 2>&1; then
  echo '{}'
  exit 0
fi
echo "$INPUT" | python3 -m engramkit.hooks.claude_hook_handler precompact 2>/dev/null || echo '{}'
