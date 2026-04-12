"""
EngramKit Claude Code Hook Handler

Handles Claude Code lifecycle events.
- SessionStart: Loads wake-up context (identity + essential memory) into the session.
- Stop: Every N messages, analyzes importance and blocks Claude to force a save.
- PreCompact: Emergency save before context compression.

Usage:
    python -m engramkit.hooks.claude_hook_handler session-start
    python -m engramkit.hooks.claude_hook_handler stop
    python -m engramkit.hooks.claude_hook_handler precompact
"""

import json
import sys
import os
from pathlib import Path

from engramkit.hooks.hook_manager import calculate_importance

SAVE_INTERVAL = 15
STATE_DIR = Path.home() / ".engramkit" / "hook_state"


def handle_stop():
    """Called on every Claude Code Stop event."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Read JSON input from stdin
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        input_data = {}

    session_id = input_data.get("session_id", "unknown")
    # Sanitize
    session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not session_id:
        session_id = "unknown"

    stop_hook_active = input_data.get("stop_hook_active", False)
    transcript_path = input_data.get("transcript_path", "")

    # If already in a save cycle, let Claude stop normally
    if stop_hook_active in (True, "True", "true"):
        print(json.dumps({}))
        return

    # Count human messages in transcript
    exchange_count = 0
    new_text = ""
    if transcript_path:
        transcript_path = os.path.expanduser(transcript_path)
        if os.path.isfile(transcript_path):
            try:
                with open(transcript_path) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            msg = entry.get("message", {})
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                content = msg.get("content", "")
                                if isinstance(content, str) and "<command-message>" not in content:
                                    exchange_count += 1
                                    new_text += content + "\n"
                            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                                content = msg.get("content", "")
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            new_text += block.get("text", "") + "\n"
                                elif isinstance(content, str):
                                    new_text += content + "\n"
                        except json.JSONDecodeError:
                            pass
            except OSError:
                pass

    # Track last save point
    last_save_file = STATE_DIR / f"{session_id}_last_save"
    last_save = 0
    if last_save_file.exists():
        try:
            last_save = int(last_save_file.read_text().strip())
        except (ValueError, OSError):
            pass

    since_last = exchange_count - last_save

    # Log
    log_file = STATE_DIR / "hook.log"
    try:
        with open(log_file, "a") as f:
            f.write(f"Session {session_id}: {exchange_count} exchanges, {since_last} since last save\n")
    except OSError:
        pass

    # Check if we should save
    should_save = False
    reason = ""

    if since_last >= SAVE_INTERVAL:
        should_save = True
        reason = f"Message threshold ({since_last}/{SAVE_INTERVAL})"
    elif since_last >= 5:
        # Check content importance
        result = calculate_importance(new_text[-5000:])  # last 5000 chars
        if result["should_save"]:
            should_save = True
            reason = result["reason"]

    if should_save:
        # Update last save point
        try:
            last_save_file.write_text(str(exchange_count))
        except OSError:
            pass

        # Block Claude and tell it to save
        print(json.dumps({
            "decision": "block",
            "reason": f"""AUTO-SAVE ({reason}).

Save the key content from this session to your memory:

1. Call engramkit_save with important decisions, architecture changes, or insights.
   Use importance=5 for critical decisions, importance=3 for general notes.
   Tag with appropriate wing and room.

2. Call engramkit_diary_write with a brief session summary.

3. If any facts changed (people, tools, relationships), update the knowledge graph:
   - engramkit_kg_add for new facts
   - engramkit_kg_invalidate for changed facts

After saving, continue the conversation normally."""
        }))
    else:
        # Not time yet
        print(json.dumps({}))


def handle_precompact():
    """Called before context compression. Always save everything."""
    print(json.dumps({
        "decision": "block",
        "reason": """CONTEXT COMPRESSION IMMINENT — Save ALL important content now.

1. Call engramkit_save for EVERY decision, insight, code change, and important discussion.
   Be thorough — after compression, detailed context will be lost.

2. Call engramkit_diary_write with a comprehensive session summary.

3. Update the knowledge graph with any new or changed facts.

Save everything, then allow compression to proceed."""
    }))


def handle_session_start():
    """Load wake-up context at session start and inject it into Claude's context.

    Silent when there's no engramkit vault for the current directory — the
    hook should never break a session.
    """
    try:
        json.load(sys.stdin)  # drain stdin (session_id, etc.); not used here
    except Exception:
        pass

    try:
        from engramkit.storage.vault import VaultManager
        from engramkit.memory.layers import MemoryStack
        from engramkit.memory.token_budget import TokenBudget

        cwd = os.getcwd()
        vaults = VaultManager.list_vaults() or []
        match = next((v for v in vaults if v.get("repo_path") == cwd), None)
        if match is None:
            print(json.dumps({}))
            return

        vault = VaultManager.get_vault(cwd)
        try:
            stack = MemoryStack(vault, TokenBudget(l1_max=1000))
            result = stack.wake_up()
            context = result.get("text", "").strip()
        finally:
            vault.close()

        if not context:
            print(json.dumps({}))
            return

        body = (
            "EngramKit memory — identity + essential recent context loaded for this project.\n\n"
            f"{context}\n\n"
            "PROTOCOL:\n"
            "- Before answering about past decisions, architecture, or code history, "
            "call engramkit_search (or engramkit_recall / engramkit_kg_query).\n"
            "- After important decisions or insights, call engramkit_save.\n"
            "- Never guess about facts in memory — verify."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": body,
            }
        }))
    except Exception:
        # Never let a failing hook break the session.
        print(json.dumps({}))


def main():
    if len(sys.argv) < 2:
        print(json.dumps({}))
        return

    action = sys.argv[1].replace("_", "-")
    if action == "stop":
        handle_stop()
    elif action == "precompact":
        handle_precompact()
    elif action == "session-start":
        handle_session_start()
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
