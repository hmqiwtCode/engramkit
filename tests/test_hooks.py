"""Tests for content-aware hooks."""

from engramkit.hooks.hook_manager import should_trigger_save, calculate_importance


class TestCalculateImportance:
    def test_trivial_conversation(self):
        result = calculate_importance("ok\nsounds good\nyes\nthanks")
        assert result["total_score"] < 5
        assert result["should_save"] is False

    def test_architecture_decisions(self):
        text = """
        We decided to switch from REST to GraphQL.
        The new architecture uses Apollo Federation as the gateway.
        We figured out the N+1 problem using DataLoader.
        """
        result = calculate_importance(text)
        assert result["should_save"] is True
        assert "decisions" in result["signals"]
        assert "architecture" in result["signals"]

    def test_problem_solving(self):
        text = "The root cause was a race condition. We fixed it with a mutex lock."
        result = calculate_importance(text)
        assert "problems_solved" in result["signals"]

    def test_code_blocks(self):
        text = "Here's the fix:\n```python\ndef fixed_function():\n    return correct_value\n```\n"
        result = calculate_importance(text)
        assert "code_changes" in result["signals"]


class TestShouldTriggerSave:
    def test_too_early(self):
        save, reason = should_trigger_save("important stuff", message_count=2)
        assert save is False
        assert "Too early" in reason

    def test_important_content_triggers(self):
        text = "We decided to migrate to PostgreSQL. The architecture redesign is complete."
        save, reason = should_trigger_save(text, message_count=7)
        assert save is True

    def test_trivial_no_trigger(self):
        save, reason = should_trigger_save("ok\nyes\nthanks", message_count=10)
        assert save is False

    def test_fallback_message_count(self):
        save, reason = should_trigger_save("nothing special", message_count=20)
        assert save is True
        assert "threshold" in reason.lower()
