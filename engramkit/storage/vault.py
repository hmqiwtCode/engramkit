"""VaultManager — per-repo vault lifecycle."""

import hashlib
import os
from datetime import datetime
from pathlib import Path

from engramkit.config import ENGRAMKIT_HOME
from engramkit.storage.schema import init_db
from engramkit.storage.chromadb_backend import ChromaBackend


class Vault:
    """A single vault representing one repository's memory."""

    def __init__(self, vault_path: Path, repo_path: str = None):
        self.vault_path = vault_path
        self.repo_path = repo_path
        self.db_path = vault_path / "meta.sqlite3"
        self.vectors_path = vault_path / "vectors"
        self.conn = None
        self.chroma = None

    def open(self):
        """Open database connections."""
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(self.vectors_path, exist_ok=True)
        self.conn = init_db(str(self.db_path))
        self.chroma = ChromaBackend(str(self.vectors_path))
        return self

    def close(self):
        """Close database connections."""
        if self.conn:
            self.conn.close()
            self.conn = None
        self.chroma = None

    # -- Metadata ---

    def get_meta(self, key: str, default: str = None) -> str:
        row = self.conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO vault_meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    # -- Generation tracking ---

    def current_generation(self) -> int:
        val = self.get_meta("generation", "0")
        return int(val)

    def next_generation(self) -> int:
        gen = self.current_generation() + 1
        self.set_meta("generation", str(gen))
        return gen

    # -- File tracking ---

    def get_file_hash(self, file_path: str) -> str | None:
        row = self.conn.execute(
            "SELECT file_hash FROM files WHERE file_path = ? AND is_deleted = 0",
            (file_path,),
        ).fetchone()
        return row["file_hash"] if row else None

    def upsert_file(self, file_path: str, file_hash: str, chunk_count: int, commit: str = None):
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT INTO files (file_path, file_hash, last_mined_at, last_commit, chunk_count, is_deleted)
               VALUES (?, ?, ?, ?, ?, 0)
               ON CONFLICT(file_path) DO UPDATE SET
                   file_hash = excluded.file_hash,
                   last_mined_at = excluded.last_mined_at,
                   last_commit = excluded.last_commit,
                   chunk_count = excluded.chunk_count,
                   is_deleted = 0""",
            (file_path, file_hash, now, commit, chunk_count),
        )

    def mark_file_deleted(self, file_path: str):
        self.conn.execute("UPDATE files SET is_deleted = 1 WHERE file_path = ?", (file_path,))
        self.conn.execute(
            "UPDATE chunks SET is_stale = 1, updated_at = ? WHERE file_path = ?",
            (datetime.now().isoformat(), file_path),
        )

    # -- Chunk operations ---

    def get_chunk_hashes_for_file(self, file_path: str) -> set:
        rows = self.conn.execute(
            "SELECT content_hash FROM chunks WHERE file_path = ? AND is_stale = 0",
            (file_path,),
        ).fetchall()
        return {row["content_hash"] for row in rows}

    def batch_upsert_chunks(self, chunks: list[dict]):
        """Insert or update chunks in both SQLite and ChromaDB."""
        if not chunks:
            return

        now = datetime.now().isoformat()

        # SQLite batch
        for chunk in chunks:
            self.conn.execute(
                """INSERT INTO chunks
                   (content_hash, content, file_path, file_hash, wing, room,
                    generation, created_at, updated_at, git_commit, git_branch, is_secret)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(content_hash) DO UPDATE SET
                       file_path = excluded.file_path,
                       generation = excluded.generation,
                       updated_at = excluded.updated_at,
                       git_commit = excluded.git_commit,
                       git_branch = excluded.git_branch,
                       is_stale = 0""",
                (
                    chunk["content_hash"],
                    chunk["content"],
                    chunk["file_path"],
                    chunk["file_hash"],
                    chunk.get("wing", "default"),
                    chunk.get("room", "general"),
                    chunk.get("generation", 1),
                    now,
                    now,
                    chunk.get("git_commit"),
                    chunk.get("git_branch"),
                    chunk.get("is_secret", 0),
                ),
            )
        self.conn.commit()

        # ChromaDB batch — only non-secret chunks
        chroma_chunks = [c for c in chunks if not c.get("is_secret", 0)]
        if chroma_chunks:
            self.chroma.batch_upsert(
                ids=[c["content_hash"] for c in chroma_chunks],
                documents=[c["content"] for c in chroma_chunks],
                metadatas=[
                    {
                        "file_path": c["file_path"],
                        "wing": c.get("wing", "default"),
                        "room": c.get("room", "general"),
                    }
                    for c in chroma_chunks
                ],
            )

    def mark_stale(self, content_hashes: set):
        """Mark chunks as stale (candidates for GC)."""
        if not content_hashes:
            return
        now = datetime.now().isoformat()
        for h in content_hashes:
            self.conn.execute(
                "UPDATE chunks SET is_stale = 1, updated_at = ? WHERE content_hash = ?",
                (now, h),
            )
        self.conn.commit()

    # -- Stats ---

    def stats(self) -> dict:
        total = self.conn.execute(
            "SELECT COUNT(*) as c FROM chunks WHERE is_stale = 0"
        ).fetchone()["c"]
        stale = self.conn.execute(
            "SELECT COUNT(*) as c FROM chunks WHERE is_stale = 1"
        ).fetchone()["c"]
        files = self.conn.execute(
            "SELECT COUNT(*) as c FROM files WHERE is_deleted = 0"
        ).fetchone()["c"]
        secret = self.conn.execute(
            "SELECT COUNT(*) as c FROM chunks WHERE is_secret = 1"
        ).fetchone()["c"]

        wing_rooms = {}
        rows = self.conn.execute(
            """SELECT wing, room, COUNT(*) as c FROM chunks
               WHERE is_stale = 0 GROUP BY wing, room ORDER BY c DESC"""
        ).fetchall()
        for row in rows:
            wing_rooms.setdefault(row["wing"], {})[row["room"]] = row["c"]

        return {
            "total_chunks": total,
            "stale_chunks": stale,
            "secret_chunks": secret,
            "total_files": files,
            "generation": self.current_generation(),
            "wing_rooms": wing_rooms,
        }


class VaultManager:
    """Manages vault discovery and lifecycle."""

    @staticmethod
    def vault_id(repo_path: str) -> str:
        """Deterministic vault ID from repo path."""
        canonical = str(Path(repo_path).expanduser().resolve())
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    @staticmethod
    def get_vault(repo_path: str) -> Vault:
        """Get or create a vault for a repository."""
        vid = VaultManager.vault_id(repo_path)
        vault_path = ENGRAMKIT_HOME / "vaults" / vid
        vault = Vault(vault_path, repo_path=repo_path)
        vault.open()

        # Store repo path mapping
        vault.set_meta("repo_path", str(Path(repo_path).expanduser().resolve()))
        return vault

    @staticmethod
    def list_vaults() -> list[dict]:
        """List all registered vaults."""
        vaults_dir = ENGRAMKIT_HOME / "vaults"
        if not vaults_dir.exists():
            return []
        results = []
        for entry in vaults_dir.iterdir():
            if entry.is_dir() and entry.name != "_cross":
                meta_db = entry / "meta.sqlite3"
                if meta_db.exists():
                    vault = Vault(entry)
                    vault.open()
                    repo_path = vault.get_meta("repo_path", "unknown")
                    stats = vault.stats()
                    vault.close()
                    results.append({"vault_id": entry.name, "repo_path": repo_path, **stats})
        return results
