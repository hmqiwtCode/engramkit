"""
Temporal Knowledge Graph — entity-relationship graph with time validity.

Adapted from MemPalace. Per-vault KG stored in knowledge_graph.sqlite3.

Usage:
    kg = KnowledgeGraph("/path/to/vault/knowledge_graph.sqlite3")
    kg.add_triple("ServiceA", "calls", "ServiceB", valid_from="2026-01-01")
    kg.query_entity("ServiceA")
    kg.timeline("ServiceA")
"""

import hashlib
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'unknown',
    properties TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS triples (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject) REFERENCES entities(id),
    FOREIGN KEY (object) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject);
CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object);
CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
CREATE INDEX IF NOT EXISTS idx_triples_valid ON triples(valid_from, valid_to);
"""


class KnowledgeGraph:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _eid(self, name: str) -> str:
        return name.lower().replace(" ", "_").replace("'", "")

    # -- Write --

    def add_entity(self, name: str, entity_type: str = "unknown", properties: dict = None) -> str:
        eid = self._eid(name)
        self.conn.execute(
            "INSERT OR REPLACE INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)",
            (eid, name, entity_type, json.dumps(properties or {})),
        )
        self.conn.commit()
        return eid

    def add_triple(
        self, subject: str, predicate: str, obj: str,
        valid_from: str = None, valid_to: str = None,
        confidence: float = 1.0, source: str = None,
    ) -> str:
        sub_id = self._eid(subject)
        obj_id = self._eid(obj)
        pred = predicate.lower().replace(" ", "_")

        # Auto-create entities
        self.conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", (sub_id, subject))
        self.conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", (obj_id, obj))

        # Dedup: skip if identical active triple exists
        existing = self.conn.execute(
            "SELECT id FROM triples WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
            (sub_id, pred, obj_id),
        ).fetchone()
        if existing:
            return existing["id"]

        triple_id = f"t_{sub_id}_{pred}_{obj_id}_{hashlib.md5(f'{valid_from}{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}"
        self.conn.execute(
            "INSERT INTO triples (id, subject, predicate, object, valid_from, valid_to, confidence, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (triple_id, sub_id, pred, obj_id, valid_from, valid_to, confidence, source),
        )
        self.conn.commit()
        return triple_id

    def invalidate(self, subject: str, predicate: str, obj: str, ended: str = None):
        sub_id = self._eid(subject)
        obj_id = self._eid(obj)
        pred = predicate.lower().replace(" ", "_")
        ended = ended or date.today().isoformat()
        self.conn.execute(
            "UPDATE triples SET valid_to=? WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
            (ended, sub_id, pred, obj_id),
        )
        self.conn.commit()

    # -- Query --

    def query_entity(self, name: str, as_of: str = None, direction: str = "both") -> list[dict]:
        eid = self._eid(name)
        results = []

        if direction in ("outgoing", "both"):
            sql = """SELECT t.predicate, e.name as obj_name, t.valid_from, t.valid_to, t.confidence
                     FROM triples t JOIN entities e ON t.object = e.id WHERE t.subject = ?"""
            params = [eid]
            if as_of:
                sql += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                params.extend([as_of, as_of])
            for row in self.conn.execute(sql, params).fetchall():
                results.append({
                    "direction": "outgoing", "subject": name,
                    "predicate": row["predicate"], "object": row["obj_name"],
                    "valid_from": row["valid_from"], "valid_to": row["valid_to"],
                    "confidence": row["confidence"], "current": row["valid_to"] is None,
                })

        if direction in ("incoming", "both"):
            sql = """SELECT t.predicate, e.name as sub_name, t.valid_from, t.valid_to, t.confidence
                     FROM triples t JOIN entities e ON t.subject = e.id WHERE t.object = ?"""
            params = [eid]
            if as_of:
                sql += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                params.extend([as_of, as_of])
            for row in self.conn.execute(sql, params).fetchall():
                results.append({
                    "direction": "incoming", "subject": row["sub_name"],
                    "predicate": row["predicate"], "object": name,
                    "valid_from": row["valid_from"], "valid_to": row["valid_to"],
                    "confidence": row["confidence"], "current": row["valid_to"] is None,
                })

        return results

    def timeline(self, entity_name: str = None) -> list[dict]:
        if entity_name:
            eid = self._eid(entity_name)
            rows = self.conn.execute(
                """SELECT s.name as sub, t.predicate, o.name as obj, t.valid_from, t.valid_to
                   FROM triples t JOIN entities s ON t.subject=s.id JOIN entities o ON t.object=o.id
                   WHERE t.subject=? OR t.object=? ORDER BY t.valid_from ASC NULLS LAST LIMIT 100""",
                (eid, eid),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT s.name as sub, t.predicate, o.name as obj, t.valid_from, t.valid_to
                   FROM triples t JOIN entities s ON t.subject=s.id JOIN entities o ON t.object=o.id
                   ORDER BY t.valid_from ASC NULLS LAST LIMIT 100""",
            ).fetchall()
        return [{"subject": r["sub"], "predicate": r["predicate"], "object": r["obj"],
                 "valid_from": r["valid_from"], "valid_to": r["valid_to"],
                 "current": r["valid_to"] is None} for r in rows]

    def stats(self) -> dict:
        entities = self.conn.execute("SELECT COUNT(*) as c FROM entities").fetchone()["c"]
        triples = self.conn.execute("SELECT COUNT(*) as c FROM triples").fetchone()["c"]
        current = self.conn.execute("SELECT COUNT(*) as c FROM triples WHERE valid_to IS NULL").fetchone()["c"]
        preds = [r["predicate"] for r in self.conn.execute("SELECT DISTINCT predicate FROM triples").fetchall()]
        return {"entities": entities, "triples": triples, "current_facts": current,
                "expired_facts": triples - current, "relationship_types": preds}
