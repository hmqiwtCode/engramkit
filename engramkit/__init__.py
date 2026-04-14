"""EngramKit — AI memory system with hybrid search, git-aware ingestion, and garbage collection."""

import logging
from importlib.metadata import PackageNotFoundError, version as _pkg_version

# ChromaDB 0.6.x has a buggy Posthog telemetry client — silence it
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

try:
    __version__ = _pkg_version("engramkit")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
