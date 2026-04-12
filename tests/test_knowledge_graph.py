"""Tests for temporal knowledge graph."""

import pytest

from engramkit.graph.knowledge_graph import KnowledgeGraph


@pytest.fixture
def kg(tmp_path):
    g = KnowledgeGraph(str(tmp_path / "test_kg.sqlite3"))
    yield g
    g.close()


class TestKnowledgeGraph:
    def test_add_and_query_entity(self, kg):
        kg.add_triple("Alice", "works_at", "Acme Corp", valid_from="2024-01-01")
        results = kg.query_entity("Alice")
        assert len(results) == 1
        assert results[0]["predicate"] == "works_at"
        assert results[0]["object"] == "Acme Corp"
        assert results[0]["current"] is True

    def test_dedup_triple(self, kg):
        id1 = kg.add_triple("A", "likes", "B")
        id2 = kg.add_triple("A", "likes", "B")
        assert id1 == id2  # Deduped

    def test_invalidate(self, kg):
        kg.add_triple("Max", "plays", "chess")
        kg.invalidate("Max", "plays", "chess", ended="2026-03-01")
        results = kg.query_entity("Max")
        assert results[0]["current"] is False

    def test_temporal_filter(self, kg):
        kg.add_triple("Max", "plays", "chess", valid_from="2025-01-01", valid_to="2025-12-31")
        kg.add_triple("Max", "plays", "tennis", valid_from="2026-01-01")

        mid_2025 = kg.query_entity("Max", as_of="2025-06-01")
        assert len(mid_2025) == 1
        assert mid_2025[0]["object"] == "chess"

        mid_2026 = kg.query_entity("Max", as_of="2026-06-01")
        assert len(mid_2026) == 1
        assert mid_2026[0]["object"] == "tennis"

    def test_timeline(self, kg):
        kg.add_triple("Alice", "joined", "Company", valid_from="2024-01-01")
        kg.add_triple("Alice", "promoted", "Senior", valid_from="2025-06-01")
        timeline = kg.timeline("Alice")
        assert len(timeline) == 2
        assert timeline[0]["valid_from"] <= timeline[1]["valid_from"]

    def test_stats(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("B", "knows", "C")
        s = kg.stats()
        assert s["entities"] == 3
        assert s["triples"] == 2
        assert s["current_facts"] == 2

    def test_bidirectional_query(self, kg):
        kg.add_triple("Alice", "manages", "Bob")
        incoming = kg.query_entity("Bob", direction="incoming")
        assert len(incoming) == 1
        assert incoming[0]["subject"] == "Alice"
