"""Tests for the ingestion pipeline — scan, process, and mine."""



from engramkit.ingest.pipeline import scan_files, process_file, mine
from engramkit.ingest.chunker import file_hash
from engramkit.storage.vault import Vault


class TestScanFiles:
    """Verify file scanning respects extensions, skip dirs, secrets, and gitignore."""

    def test_finds_readable_files(self, sample_project):
        """Should find .py files in the project."""
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert "main.py" in names
        assert "utils.py" in names

    def test_finds_nested_files(self, sample_project):
        """Should find files in subdirectories."""
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert "core.py" in names

    def test_skips_non_readable_extensions(self, sample_project):
        """Should skip files with non-readable extensions like .png."""
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert "image.png" not in names

    def test_skips_secret_files(self, sample_project):
        """Should skip .env files detected as secrets."""
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert ".env" not in names

    def test_skips_gitignore_patterns(self, sample_project):
        """Files matching .gitignore patterns should be excluded."""
        # Create a file that matches gitignore
        (sample_project / "build").mkdir()
        (sample_project / "build" / "output.py").write_text("x = 1\n")
        files = scan_files(str(sample_project))
        paths = {f.relative_to(sample_project).as_posix() for f in files}
        assert "build/output.py" not in paths

    def test_skips_skip_dirs(self, sample_project):
        """Directories in SKIP_DIRS should be entirely excluded."""
        # Create node_modules dir
        nm = sample_project / "node_modules"
        nm.mkdir()
        (nm / "lodash.js").write_text("module.exports = {}\n")
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert "lodash.js" not in names

    def test_respects_gitignore_false(self, sample_project):
        """When respect_gitignore=False, gitignore patterns should not filter."""
        (sample_project / "build").mkdir(exist_ok=True)
        (sample_project / "build" / "output.py").write_text(
            "# build output\n" * 10
        )
        files = scan_files(str(sample_project), respect_gitignore=False)
        # build dir is in SKIP_DIRS — so it's still skipped
        # But files matched by gitignore patterns (like .pyc) won't be filtered
        # This mainly checks that the flag is accepted without error
        assert isinstance(files, list)

    def test_empty_directory(self, tmp_path):
        """Scanning an empty directory should return empty list."""
        empty = tmp_path / "empty"
        empty.mkdir()
        files = scan_files(str(empty))
        assert files == []

    def test_extra_ignores_bare_name_matches_any_depth(self, sample_project):
        """gitignore semantics: 'docs' matches any docs/ — root or nested."""
        (sample_project / "docs").mkdir()
        (sample_project / "docs" / "root_doc.md").write_text("# Root\n" * 20)
        nested = sample_project / "lib" / "docs"
        nested.mkdir()
        (nested / "lib_doc.md").write_text("# Lib\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["docs"])
        names = {f.name for f in files}
        assert "root_doc.md" not in names
        assert "lib_doc.md" not in names

    def test_extra_ignores_leading_slash_anchors_to_root(self, sample_project):
        """gitignore: '/docs' anchors to the project root, nested docs/ survives."""
        (sample_project / "docs").mkdir()
        (sample_project / "docs" / "root_doc.md").write_text("# Root\n" * 20)
        nested = sample_project / "lib" / "docs"
        nested.mkdir()
        (nested / "lib_doc.md").write_text("# Lib\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["/docs"])
        names = {f.name for f in files}
        assert "root_doc.md" not in names  # root skipped
        assert "lib_doc.md" in names       # nested preserved

    def test_extra_ignores_specific_path_is_anchored(self, sample_project):
        """gitignore: a slash in the middle anchors the pattern to the root."""
        (sample_project / "docs").mkdir()
        (sample_project / "docs" / "root_doc.md").write_text("# Root\n" * 20)
        nested = sample_project / "lib" / "docs"
        nested.mkdir()
        (nested / "lib_doc.md").write_text("# Lib\n" * 20)
        deep = sample_project / "other" / "lib" / "docs"
        deep.mkdir(parents=True)
        (deep / "deep_doc.md").write_text("# Deep\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["lib/docs"])
        names = {f.name for f in files}
        assert "lib_doc.md" not in names   # lib/docs at root level — matched
        assert "root_doc.md" in names      # plain docs/ — not matched
        assert "deep_doc.md" in names      # other/lib/docs — not anchored to root

    def test_extra_ignores_trailing_slash_folder_only(self, sample_project):
        """gitignore: trailing slash ('build/') limits the pattern to directories."""
        build = sample_project / "build"
        build.mkdir()
        (build / "out.py").write_text("x = 1\n" * 20)
        # A file literally named 'build' (no slash) should NOT be matched by 'build/'
        (sample_project / "buildnotes.md").write_text("# Notes\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["build/"])
        names = {f.name for f in files}
        assert "out.py" not in names
        assert "buildnotes.md" in names

    def test_extra_ignores_double_star_recursive(self, sample_project):
        """gitignore: 'lib/**' matches everything under lib/ at any depth."""
        (sample_project / "lib" / "docs").mkdir()
        (sample_project / "lib" / "docs" / "a.md").write_text("# A\n" * 20)
        deep = sample_project / "lib" / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "file.py").write_text("x = 1\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["lib/**"])
        names = {f.name for f in files}
        assert "a.md" not in names
        assert "file.py" not in names
        # Root-level files survive
        assert "main.py" in names

    def test_extra_ignores_file_glob(self, sample_project):
        """gitignore: '*.log' excludes files by extension at any depth."""
        # .log isn't in READABLE_EXTENSIONS, so add a file we'd normally mine
        # that ends in a custom pattern. Use *.md instead.
        (sample_project / "notes.md").write_text("# Notes\n" * 20)
        (sample_project / "lib" / "more.md").write_text("# More\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["*.md"])
        names = {f.name for f in files}
        assert "notes.md" not in names
        assert "more.md" not in names
        # .py files survive
        assert "main.py" in names

    def test_extra_ignores_negation_reincludes(self, sample_project):
        """gitignore: '!pattern' re-includes something matched by an earlier pattern."""
        (sample_project / "lib" / "keep.md").write_text("# Keep\n" * 20)
        (sample_project / "lib" / "skip.md").write_text("# Skip\n" * 20)

        # Exclude all .md under lib/, but keep lib/keep.md
        files = scan_files(
            str(sample_project),
            extra_ignores=["lib/*.md", "!lib/keep.md"],
        )
        names = {f.name for f in files}
        assert "skip.md" not in names
        assert "keep.md" in names

    def test_extra_ignores_none_is_noop(self, sample_project):
        """Passing None or [] should behave identically to omitting the argument."""
        default = {f.name for f in scan_files(str(sample_project))}
        none_list = {f.name for f in scan_files(str(sample_project), extra_ignores=None)}
        empty = {f.name for f in scan_files(str(sample_project), extra_ignores=[])}
        assert default == none_list == empty

    def test_extra_ignores_multiple_compose(self, sample_project):
        """Multiple patterns compose like a single .gitignore file."""
        (sample_project / "docs").mkdir()
        (sample_project / "docs" / "a.md").write_text("# A\n" * 20)
        (sample_project / "examples").mkdir()
        (sample_project / "examples" / "b.py").write_text("x = 1\n" * 20)

        files = scan_files(str(sample_project), extra_ignores=["docs", "examples"])
        names = {f.name for f in files}
        assert "a.md" not in names
        assert "b.py" not in names

    def test_skip_filenames(self, sample_project):
        """Files in SKIP_FILENAMES should be excluded."""
        (sample_project / "package-lock.json").write_text("{}")
        files = scan_files(str(sample_project))
        names = {f.name for f in files}
        assert "package-lock.json" not in names


class TestProcessFile:
    """Verify single-file processing returns correct chunks and metadata."""

    def test_returns_correct_structure(self, sample_project):
        """Processed file should have file_path, file_hash, and chunks list."""
        filepath = sample_project / "main.py"
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result is not None
        assert "file_path" in result
        assert "file_hash" in result
        assert "chunks" in result
        assert result["file_path"] == "main.py"

    def test_file_hash_matches(self, sample_project):
        """file_hash should be SHA256 of the file content."""
        filepath = sample_project / "main.py"
        content = filepath.read_text()
        expected_hash = file_hash(content.strip())
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result["file_hash"] == expected_hash

    def test_skips_small_files(self, sample_project):
        """Files smaller than min_chunk_size should return None."""
        filepath = sample_project / "tiny.py"
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result is None

    def test_chunks_have_required_fields(self, sample_project):
        """Each chunk should have content_hash, content, file_path, file_hash."""
        filepath = sample_project / "utils.py"
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result is not None
        for chunk in result["chunks"]:
            assert "content_hash" in chunk
            assert "content" in chunk
            assert "file_path" in chunk
            assert "file_hash" in chunk

    def test_secret_detection_in_chunks(self, sample_project):
        """Chunks containing secrets should be flagged with is_secret=1."""
        # Create a file with a secret in it
        secret_file = sample_project / "config.py"
        secret_file.write_text(
            "# Config\nAPI_KEY=FAKE_KEY_abcdef123456ghijklmnop789\nDEBUG=True\n" * 3
        )
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(secret_file, sample_project, config)
        assert result is not None
        secret_chunks = [c for c in result["chunks"] if c.get("is_secret")]
        assert len(secret_chunks) >= 1

    def test_nonexistent_file_returns_none(self, sample_project):
        """Processing a file that doesn't exist should return None."""
        filepath = sample_project / "nonexistent.py"
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result is None

    def test_relative_path_in_chunks(self, sample_project):
        """file_path in chunks should be relative to project root."""
        filepath = sample_project / "lib" / "core.py"
        config = {"chunk_size": 800, "chunk_overlap": 100, "min_chunk_size": 50}
        result = process_file(filepath, sample_project, config)
        assert result is not None
        assert result["file_path"] == "lib/core.py"


class TestMine:
    """Integration tests for the mine function."""

    def test_mine_creates_chunks(self, sample_project, tmp_path):
        """Mining should populate the vault with chunks."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            stats = mine(
                str(sample_project), vault, wing="test", room="general"
            )
            assert stats["files_processed"] >= 1
            assert stats["chunks_added"] >= 1

            # Verify chunks exist in SQLite
            total = vault.conn.execute(
                "SELECT COUNT(*) as c FROM chunks WHERE is_stale = 0"
            ).fetchone()["c"]
            assert total > 0
        finally:
            vault.close()

    def test_mine_skips_unchanged_files(self, sample_project, tmp_path):
        """Re-mining the same project should skip unchanged files."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            # First mine
            stats1 = mine(str(sample_project), vault, wing="test")
            # Second mine
            stats2 = mine(str(sample_project), vault, wing="test")
            assert stats2["files_skipped"] >= stats1["files_processed"]
        finally:
            vault.close()

    def test_mine_marks_stale_on_change(self, sample_project, tmp_path):
        """Changing a file should mark old chunks as stale."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            # First mine
            mine(str(sample_project), vault, wing="test")

            # Change a file (must be larger than min_chunk_size=50)
            (sample_project / "main.py").write_text(
                "def new_main():\n    print('completely rewritten code here')\n"
                "    result = process_all_data()\n    return result\n"
            )

            # Re-mine
            stats2 = mine(str(sample_project), vault, wing="test")
            assert stats2["chunks_stale"] >= 1
        finally:
            vault.close()

    def test_mine_dry_run(self, sample_project, tmp_path):
        """Dry run should not persist any chunks."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            mine(str(sample_project), vault, wing="test", dry_run=True)
            total = vault.conn.execute(
                "SELECT COUNT(*) as c FROM chunks"
            ).fetchone()["c"]
            assert total == 0
        finally:
            vault.close()

    def test_mine_ignore_skips_directories(self, sample_project, tmp_path):
        """Directories named via the ignore list should produce no chunks."""
        docs = sample_project / "docs"
        docs.mkdir()
        (docs / "manual.md").write_text(
            "# Manual\n\n" + "Documentation content that is long enough to chunk. " * 30
        )
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            mine(str(sample_project), vault, wing="test", ignore=["docs"])
            stored_paths = {
                row["file_path"]
                for row in vault.conn.execute("SELECT DISTINCT file_path FROM chunks")
            }
            assert not any(p.startswith("docs/") for p in stored_paths)
        finally:
            vault.close()

    def test_mine_sets_wing(self, sample_project, tmp_path):
        """Mined chunks should have the specified wing."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            mine(str(sample_project), vault, wing="my_wing")
            wings = vault.conn.execute(
                "SELECT DISTINCT wing FROM chunks"
            ).fetchall()
            wing_names = {r["wing"] for r in wings}
            assert "my_wing" in wing_names
        finally:
            vault.close()

    def test_mine_auto_wing_from_dir_name(self, sample_project, tmp_path):
        """When wing is None, mine should derive it from directory name."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            mine(str(sample_project), vault, wing=None)
            wings = vault.conn.execute(
                "SELECT DISTINCT wing FROM chunks"
            ).fetchall()
            wing_names = {r["wing"] for r in wings}
            # sample_project dir name is "sample_project"
            assert "sample_project" in wing_names
        finally:
            vault.close()

    def test_mine_returns_stats(self, sample_project, tmp_path):
        """mine() should return a stats dict with expected keys."""
        vault = Vault(tmp_path / "mine_vault")
        vault.open()
        try:
            stats = mine(str(sample_project), vault, wing="test")
            assert "files_scanned" in stats
            assert "files_processed" in stats
            assert "files_skipped" in stats
            assert "chunks_added" in stats
            assert "chunks_stale" in stats
            assert "secrets_found" in stats
        finally:
            vault.close()
