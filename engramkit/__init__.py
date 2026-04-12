"""EngramKit — AI memory system with hybrid search, git-aware ingestion, and garbage collection."""

import logging

# ChromaDB 0.6.x has a buggy Posthog telemetry client — silence it
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

__version__ = "0.1.0"
