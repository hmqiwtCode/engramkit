"""Content-aware hook triggers — replaces MemPalace's dumb counter."""

import re


# Signal patterns with importance weights
IMPORTANCE_SIGNALS = {
    "decisions": {
        "patterns": [
            r"\b(?:decided|chose|went with|switched to|let's use|let's go with)\b",
            r"\b(?:we'll use|picked|selected|agreed on|committed to)\b",
        ],
        "weight": 5,
    },
    "architecture": {
        "patterns": [
            r"\b(?:design|architect\w*|pattern|schema|migration|redesign)\b",
            r"\b(?:refactor|restructure|new approach|breaking change|gateway|federation)\b",
        ],
        "weight": 4,
    },
    "problems_solved": {
        "patterns": [
            r"\b(?:fixed|solved|figured out|root cause|the issue was)\b",
            r"\b(?:the bug was|workaround|resolution|resolved)\b",
        ],
        "weight": 4,
    },
    "code_changes": {
        "patterns": [
            r"```[\s\S]{50,}?```",  # Code blocks with substantial content
        ],
        "weight": 3,
    },
    "planning": {
        "patterns": [
            r"\b(?:roadmap|milestone|deadline|sprint|phase \d)\b",
            r"\b(?:next step|action item|TODO|priority)\b",
        ],
        "weight": 3,
    },
}

# Minimum message count before we even check content
MIN_MESSAGES_BEFORE_CHECK = 5

# Score threshold to trigger save
SCORE_THRESHOLD = 10

# Fallback: max messages before forced save regardless of content
MAX_MESSAGES_FALLBACK = 20


def calculate_importance(text: str) -> dict:
    """
    Score conversation text for importance.

    Returns {total_score, signals_found, should_save, reason}.
    """
    score = 0
    signals = {}

    for signal_name, config in IMPORTANCE_SIGNALS.items():
        count = 0
        for pattern in config["patterns"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        if count > 0:
            signal_score = count * config["weight"]
            signals[signal_name] = {"count": count, "score": signal_score}
            score += signal_score

    # Word count bonus: substantial discussion gets credit
    word_count = len(text.split())
    word_bonus = word_count / 200  # 1 point per ~200 words
    score += word_bonus

    # Build reason
    active_signals = [k for k, v in signals.items() if v["count"] > 0]
    if score >= SCORE_THRESHOLD:
        reason = f"High-value content: {', '.join(active_signals)} (score: {score:.1f})"
        should_save = True
    else:
        reason = f"Below threshold (score: {score:.1f}/{SCORE_THRESHOLD})"
        should_save = False

    return {
        "total_score": round(score, 1),
        "signals": signals,
        "word_count": word_count,
        "should_save": should_save,
        "reason": reason,
    }


def should_trigger_save(
    new_text: str,
    message_count: int = 0,
) -> tuple[bool, str]:
    """
    Decide whether to trigger an auto-save.

    Args:
        new_text: Text since last save
        message_count: Number of messages since last save

    Returns:
        (should_save, reason)
    """
    # Too early — not enough messages to judge
    if message_count < MIN_MESSAGES_BEFORE_CHECK:
        return False, f"Too early ({message_count}/{MIN_MESSAGES_BEFORE_CHECK} messages)"

    # Check content importance
    result = calculate_importance(new_text)
    if result["should_save"]:
        return True, result["reason"]

    # Fallback: force save after many messages
    if message_count >= MAX_MESSAGES_FALLBACK:
        return True, f"Message threshold reached ({message_count}/{MAX_MESSAGES_FALLBACK})"

    return False, result["reason"]
