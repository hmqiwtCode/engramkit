"""Smart 800-char chunker — breaks at function/paragraph boundaries."""

import hashlib


def content_hash(text: str) -> str:
    """SHA256-based content-addressed ID."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def file_hash(content: str) -> str:
    """SHA256 hash of entire file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def smart_chunk(content: str, max_chars: int = 800, overlap: int = 100, min_size: int = 50) -> list[dict]:
    """
    Chunk text into ~800 char pieces, preferring to break at:
      1. Blank lines (paragraph/function boundaries)
      2. Function/class definitions
      3. Any newline

    Returns list of {"content": str, "content_hash": str}
    """
    content = content.strip()
    if not content:
        return []

    # Too small
    if len(content) < min_size:
        return []

    # Small file — single chunk
    if len(content) <= max_chars:
        return [{"content": content, "content_hash": content_hash(content)}]

    chunks = []
    start = 0

    while start < len(content):
        end = min(start + max_chars, len(content))

        if end < len(content):
            # Try to find a good break point in the second half of the window
            half = start + max_chars // 2
            best_break = -1

            # Priority 1: blank line
            pos = content.rfind("\n\n", half, end)
            if pos > start:
                best_break = pos + 1  # keep one newline

            # Priority 2: function/class definition
            if best_break == -1:
                for marker in ("\ndef ", "\nclass ", "\nasync def "):
                    pos = content.rfind(marker, half, end)
                    if pos > start:
                        best_break = pos + 1  # break before the def
                        break

            # Priority 3: any newline
            if best_break == -1:
                pos = content.rfind("\n", half, end)
                if pos > start:
                    best_break = pos + 1

            if best_break > start:
                end = best_break

        chunk_text = content[start:end].strip()
        if len(chunk_text) >= min_size:
            chunks.append({
                "content": chunk_text,
                "content_hash": content_hash(chunk_text),
            })

        # Move forward with overlap
        if end >= len(content):
            break
        start = end - overlap if end < len(content) else end

    return chunks
