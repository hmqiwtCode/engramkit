"""Tests for token budget manager."""

from datetime import datetime, timedelta

from engramkit.memory.token_budget import (
    count_tokens, score_chunk, deduplicate_chunks, select_within_budget,
)


class TestCountTokens:
    def test_empty(self):
        assert count_tokens("") == 0

    def test_simple(self):
        tokens = count_tokens("hello world")
        assert tokens == 2

    def test_code(self):
        tokens = count_tokens("def foo():\n    return 42")
        assert tokens > 5


class TestScoreChunk:
    def test_recent_high_importance_scores_high(self):
        chunk = {"importance": 5.0, "updated_at": datetime.now().isoformat(), "access_count": 10}
        score = score_chunk(chunk)
        assert score > 4.0

    def test_old_chunk_scores_lower(self):
        now = datetime.now()
        recent = {"importance": 3.0, "updated_at": now.isoformat(), "access_count": 0}
        old = {"importance": 3.0, "updated_at": (now - timedelta(days=30)).isoformat(), "access_count": 0}
        assert score_chunk(recent, now) > score_chunk(old, now)

    def test_importance_matters(self):
        now = datetime.now()
        high = {"importance": 5.0, "updated_at": now.isoformat(), "access_count": 0}
        low = {"importance": 1.0, "updated_at": now.isoformat(), "access_count": 0}
        assert score_chunk(high, now) > score_chunk(low, now)

    def test_access_boost(self):
        now = datetime.now()
        used = {"importance": 3.0, "updated_at": now.isoformat(), "access_count": 100}
        unused = {"importance": 3.0, "updated_at": now.isoformat(), "access_count": 0}
        assert score_chunk(used, now) > score_chunk(unused, now)


class TestDeduplicate:
    def test_removes_near_duplicates(self):
        chunks = [
            {"content": "def calculate_total(items, discount): validate(items)"},
            {"content": "def calculate_total(items, discount): validate(items)"},  # exact dup
        ]
        result = deduplicate_chunks(chunks)
        assert len(result) == 1

    def test_keeps_different_chunks(self):
        chunks = [
            {"content": "def calculate_total(items, discount): pass"},
            {"content": "class DatabaseConnection: pool = create_pool()"},
        ]
        result = deduplicate_chunks(chunks)
        assert len(result) == 2


class TestSelectWithinBudget:
    def test_respects_budget(self):
        chunks = [
            {"content": "word " * 100, "importance": 3.0,
             "updated_at": datetime.now().isoformat(), "access_count": 0, "content_hash": "a"},
            {"content": "word " * 100, "importance": 3.0,
             "updated_at": datetime.now().isoformat(), "access_count": 0, "content_hash": "b"},
        ]
        # Each chunk is ~100 tokens. Budget of 120 should fit only 1.
        selected, report = select_within_budget(chunks, max_tokens=120, deduplicate=False)
        assert len(selected) == 1
        assert report.tokens_used <= 120
        assert report.chunks_skipped_budget == 1

    def test_empty_input(self):
        selected, report = select_within_budget([], max_tokens=1000)
        assert selected == []
        assert report.chunks_loaded == 0
