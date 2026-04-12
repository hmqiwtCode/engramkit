"""
Content-Aware Hooks Demo — Shows how importance scoring works.

Instead of counting to 15 messages (like MemPalace), EngramKit
analyzes conversation content to decide when to auto-save.

Usage:
    python examples/08_content_hooks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.hooks.hook_manager import calculate_importance, should_trigger_save


def main():
    print("=== Importance Scoring ===\n")

    samples = [
        ("Trivial chat", "ok\nsounds good\nyes\nthanks\nyep"),
        ("Architecture decision", """
            We decided to switch from REST to GraphQL for the API layer.
            The new architecture uses Apollo Federation as the gateway.
            We figured out the N+1 query problem by using DataLoader.
        """),
        ("Bug fix", "The root cause was a race condition in the auth middleware. We fixed it with a mutex lock."),
        ("Code review", "```python\ndef calculate_total(items, discount):\n    return sum(items) * (1 - discount)\n```"),
        ("Planning", "The roadmap for Q3 includes 3 milestones: auth rewrite, API v2, and dashboard launch."),
        ("Small talk", "how are you\nfine thanks\ngreat weather today"),
    ]

    for label, text in samples:
        result = calculate_importance(text)
        signals = [k for k, v in result["signals"].items() if v["count"] > 0]
        print(f"  [{label}]")
        print(f"    Score: {result['total_score']:.1f}/10  Save: {'YES' if result['should_save'] else 'no'}")
        if signals:
            print(f"    Signals: {', '.join(signals)}")
        print()

    print("=== Trigger Logic ===\n")

    cases = [
        ("Too early (3 msgs)", "Important architecture decision", 3),
        ("Important at msg 7", "We decided to migrate to PostgreSQL. The architecture redesign is complete.", 7),
        ("Trivial at msg 15", "ok yes thanks sure", 15),
        ("Forced at msg 20", "nothing special just chatting", 20),
    ]

    for label, text, count in cases:
        save, reason = should_trigger_save(text, message_count=count)
        print(f"  {label:25} → {'SAVE' if save else 'skip':5}  {reason}")


if __name__ == "__main__":
    main()
