"""Tests for smart 800-char chunker."""

from engramkit.ingest.chunker import smart_chunk, content_hash


class TestContentHash:
    def test_deterministic(self):
        assert content_hash("hello") == content_hash("hello")

    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_length_24(self):
        assert len(content_hash("test")) == 24


class TestSmartChunk:
    def test_small_file_single_chunk(self):
        """Files under 800 chars → single chunk."""
        text = "def foo():\n    return 42\n\ndef bar():\n    return 99\n# end of file"
        chunks = smart_chunk(text)
        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_empty_content(self):
        assert smart_chunk("") == []
        assert smart_chunk("   ") == []

    def test_below_min_size(self):
        assert smart_chunk("hi", min_size=50) == []

    def test_breaks_at_blank_line(self):
        """Should prefer breaking at paragraph boundaries."""
        text = ("x" * 400) + "\n\n" + ("y" * 400)
        chunks = smart_chunk(text, max_chars=500, overlap=50)
        # Should break at \n\n, not mid-word
        assert len(chunks) >= 2
        assert chunks[0]["content"].endswith("x" * 10)  # ends with x's

    def test_breaks_at_def(self):
        """Should prefer breaking at function definitions."""
        block1 = "# comment\n" * 40  # ~400 chars
        block2 = "def my_func():\n    pass\n" + ("# more\n" * 40)
        text = block1 + block2
        chunks = smart_chunk(text, max_chars=500, overlap=50)
        assert len(chunks) >= 2
        # Second chunk should start with or near the def
        assert any("def my_func" in c["content"] for c in chunks)

    def test_content_hash_unique_per_chunk(self):
        text = ("a" * 500) + "\n\n" + ("b" * 500)
        chunks = smart_chunk(text, max_chars=600, overlap=50)
        hashes = [c["content_hash"] for c in chunks]
        assert len(hashes) == len(set(hashes))  # All unique

    def test_overlap_exists(self):
        """Chunks should overlap by ~100 chars."""
        text = "\n".join(f"line {i}: " + "x" * 70 for i in range(20))
        chunks = smart_chunk(text, max_chars=400, overlap=100)
        if len(chunks) >= 2:
            end_of_first = chunks[0]["content"][-50:]
            start_of_second = chunks[1]["content"][:100]
            # Some overlap should exist
            assert end_of_first[-20:] in chunks[1]["content"] or \
                   any(word in start_of_second for word in end_of_first.split()[-3:])
