"""ChromaDB wrapper — handles vector storage with batch operations."""

import os
import chromadb


COLLECTION_NAME = "engramkit_chunks"
BATCH_SIZE = 500


class ChromaBackend:
    """Wrapper around ChromaDB for vector search with batching."""

    def __init__(self, persist_path: str):
        os.makedirs(persist_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_path)
        try:
            self.collection = self.client.get_collection(COLLECTION_NAME)
        except Exception:
            self.collection = self.client.create_collection(COLLECTION_NAME)

    def batch_upsert(self, ids: list, documents: list, metadatas: list):
        """Upsert one-at-a-time. Batching is SLOWER on CPU due to HNSW overhead."""
        seen = set()
        for uid, doc, meta in zip(ids, documents, metadatas):
            if uid in seen:
                continue
            seen.add(uid)
            self.collection.upsert(
                ids=[uid],
                documents=[doc],
                metadatas=[meta],
            )

    def search(self, query: str, n_results: int = 10, where: dict = None) -> list[dict]:
        """Semantic search. Returns list of {content_hash, content, distance, metadata}."""
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = self.collection.query(**kwargs)
        except Exception:
            return []

        hits = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                hits.append({
                    "content_hash": doc_id,
                    "content": results["documents"][0][i],
                    "distance": results["distances"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                })
        return hits

    def delete(self, ids: list):
        """Delete vectors by ID."""
        if ids:
            for i in range(0, len(ids), BATCH_SIZE):
                batch = ids[i : i + BATCH_SIZE]
                try:
                    self.collection.delete(ids=batch)
                except Exception:
                    pass

    def count(self) -> int:
        return self.collection.count()
