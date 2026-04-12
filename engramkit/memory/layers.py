"""Memory layers — L0 identity, L1 essential, L2 on-demand, L3 deep search."""


from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.vault import Vault
from engramkit.search.hybrid import hybrid_search
from engramkit.memory.token_budget import (
    TokenBudget, BudgetReport, count_tokens, select_within_budget,
)


class MemoryStack:
    """4-layer memory system with token-aware loading."""

    def __init__(self, vault: Vault, budget: TokenBudget = None):
        self.vault = vault
        self.budget = budget or TokenBudget()

    def wake_up(self, wing: str = None) -> dict:
        """
        Load L0 + L1 context for session start.

        Returns {text, l0_report, l1_report, total_tokens}.
        """
        l0_text, l0_report = self._load_l0()
        l1_text, l1_report = self._load_l1(wing)

        combined = ""
        if l0_text:
            combined += f"## Identity\n{l0_text}\n\n"
        if l1_text:
            combined += f"## Recent Context\n{l1_text}\n"

        return {
            "text": combined.strip(),
            "l0_report": l0_report,
            "l1_report": l1_report,
            "total_tokens": l0_report.tokens_used + l1_report.tokens_used,
        }

    def recall(self, wing: str = None, room: str = None, n_results: int = 10) -> dict:
        """
        L2 — on-demand recall filtered by wing/room.

        Returns {text, report, results}.
        """
        # Fetch chunks from SQLite with filters
        sql = """SELECT content_hash, content, file_path, wing, room,
                        importance, created_at, updated_at, access_count
                 FROM chunks WHERE is_stale = 0 AND is_secret = 0"""
        params = []
        if wing:
            sql += " AND wing = ?"
            params.append(wing)
        if room:
            sql += " AND room = ?"
            params.append(room)
        sql += " ORDER BY updated_at DESC LIMIT 100"

        rows = self.vault.conn.execute(sql, params).fetchall()
        chunks = [dict(r) for r in rows]

        selected, report = select_within_budget(chunks, self.budget.l2_max)
        report.layer = "L2"

        text = self._format_chunks(selected)
        return {"text": text, "report": report, "results": selected}

    def search(self, query: str, wing: str = None, room: str = None, n_results: int = 5) -> dict:
        """
        L3 — deep hybrid search.

        Returns {text, report, results}.
        """
        results = hybrid_search(
            query=query,
            vault=self.vault,
            n_results=n_results,
            wing=wing,
            room=room,
        )

        tokens_used = sum(count_tokens(r.get("content", "")) for r in results)
        report = BudgetReport(
            layer="L3",
            tokens_used=tokens_used,
            tokens_budget=self.budget.l3_max,
            chunks_loaded=len(results),
        )

        text = self._format_search_results(results)
        return {"text": text, "report": report, "results": results}

    # -- Internal ---

    def _load_l0(self) -> tuple[str, BudgetReport]:
        """Load identity from ~/.engramkit/identity.txt."""
        identity_path = ENGRAMKIT_HOME / "identity.txt"
        text = ""
        if identity_path.exists():
            try:
                text = identity_path.read_text(encoding="utf-8").strip()
            except OSError:
                pass

        # Truncate to budget
        tokens = count_tokens(text) if text else 0
        if tokens > self.budget.l0_max and text:
            # Rough truncation by ratio
            ratio = self.budget.l0_max / tokens
            text = text[:int(len(text) * ratio)].rsplit(" ", 1)[0] + "..."
            tokens = count_tokens(text)

        report = BudgetReport(
            layer="L0",
            tokens_used=tokens,
            tokens_budget=self.budget.l0_max,
            chunks_loaded=1 if text else 0,
        )
        return text, report

    def _load_l1(self, wing: str = None) -> tuple[str, BudgetReport]:
        """
        Load essential context — top chunks by recency + importance score.
        Deduplicated and fitted to token budget.
        """
        # Fetch recent + important chunks
        sql = """SELECT content_hash, content, file_path, wing, room,
                        importance, created_at, updated_at, access_count
                 FROM chunks WHERE is_stale = 0 AND is_secret = 0"""
        params = []
        if wing:
            sql += " AND wing = ?"
            params.append(wing)
        sql += " ORDER BY updated_at DESC LIMIT 200"

        rows = self.vault.conn.execute(sql, params).fetchall()
        chunks = [dict(r) for r in rows]

        selected, report = select_within_budget(chunks, self.budget.l1_max)
        report.layer = "L1"

        text = self._format_chunks(selected)
        return text, report

    def _format_chunks(self, chunks: list[dict]) -> str:
        """Format chunks for context injection."""
        if not chunks:
            return ""
        parts = []
        for c in chunks:
            header = f"[{c.get('wing', '?')}/{c.get('room', '?')}] {c.get('file_path', '?')}"
            content = c.get("content", "").strip()
            # Truncate very long chunks
            if len(content) > 500:
                content = content[:497] + "..."
            parts.append(f"{header}\n{content}")
        return "\n\n---\n\n".join(parts)

    def _format_search_results(self, results: list[dict]) -> str:
        """Format search results for context injection."""
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            header = f"[{i}] {r.get('wing', '?')}/{r.get('room', '?')} — {r.get('file_path', '?')}"
            content = r.get("content", "").strip()
            score = r.get("score", 0)
            sources = ", ".join(r.get("sources", []))
            parts.append(f"{header}\nScore: {score:.4f} ({sources})\n{content}")
        return "\n\n---\n\n".join(parts)
