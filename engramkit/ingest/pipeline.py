"""Ingestion pipeline — scan, chunk, diff, store."""

import os
import fnmatch
from pathlib import Path

from engramkit.config import READABLE_EXTENSIONS, SKIP_DIRS, SKIP_FILENAMES
from engramkit.ingest.chunker import smart_chunk, file_hash
from engramkit.ingest.secret_scanner import is_secret_file, contains_secret
from engramkit.storage.vault import Vault


def _parse_extra_ignores(extra_ignores: list[str]) -> list[str]:
    """Normalize user-supplied ignores to anchored project-relative patterns.

    All patterns are matched via fnmatch against each candidate's POSIX
    path, anchored at the project root. That means ``docs`` matches only
    the top-level ``docs/`` folder — it does NOT match ``lib/docs/``.
    Use ``**/docs`` (or a glob) if you want nested matches too.

    Trailing ``/``, ``/*``, and ``/**`` are stripped so ``lib/docs``,
    ``lib/docs/``, ``lib/docs/*``, and ``lib/docs/**`` all mean the same
    thing: skip the ``lib/docs`` folder and everything inside it.
    """
    patterns: list[str] = []
    for raw in extra_ignores or []:
        pat = (raw or "").strip()
        if not pat:
            continue
        norm = pat.rstrip("/")
        for suffix in ("/**", "/*"):
            if norm.endswith(suffix):
                norm = norm[: -len(suffix)]
        if norm:
            patterns.append(norm)
    return patterns


def _matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    return bool(patterns) and any(fnmatch.fnmatch(rel_path, p) for p in patterns)


def scan_files(
    project_dir: str,
    respect_gitignore: bool = True,
    extra_ignores: list[str] = None,
) -> list[Path]:
    """Walk directory tree and return list of mineable files.

    ``extra_ignores`` accepts project-relative path patterns (see
    :func:`_parse_extra_ignores`). Patterns match both directories
    (pruning the walk) and individual files.
    """
    project_path = Path(project_dir).expanduser().resolve()
    gitignore_patterns = []

    if respect_gitignore:
        gitignore_path = project_path / ".gitignore"
        if gitignore_path.exists():
            gitignore_patterns = _load_gitignore(gitignore_path)

    ignore_patterns = _parse_extra_ignores(extra_ignores or [])

    files = []
    for root, dirs, filenames in os.walk(project_path):
        try:
            root_rel = Path(root).relative_to(project_path).as_posix()
        except ValueError:
            root_rel = ""
        if root_rel == ".":
            root_rel = ""

        kept = []
        for d in dirs:
            if d in SKIP_DIRS:
                continue
            rel_child = f"{root_rel}/{d}" if root_rel else d
            if _matches_ignore(rel_child, ignore_patterns):
                continue
            kept.append(d)
        dirs[:] = kept

        root_path = Path(root)
        for filename in filenames:
            filepath = root_path / filename

            # Skip by filename
            if filename in SKIP_FILENAMES:
                continue

            # Skip by extension
            if filepath.suffix.lower() not in READABLE_EXTENSIONS:
                continue

            # Skip secret files
            if is_secret_file(str(filepath)):
                continue

            # Skip against user-supplied ignore patterns (covers files under
            # e.g. `lib/*` so the flag matches folders *and* their contents).
            try:
                rel_file = filepath.relative_to(project_path).as_posix()
            except ValueError:
                rel_file = filename
            if _matches_ignore(rel_file, ignore_patterns):
                continue

            # Skip gitignored files
            if gitignore_patterns and _is_gitignored(rel_file, gitignore_patterns):
                continue

            files.append(filepath)

    return files


def _load_gitignore(gitignore_path: Path) -> list[str]:
    """Load patterns from .gitignore."""
    patterns = []
    try:
        for line in gitignore_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    except OSError:
        pass
    return patterns


def _is_gitignored(relative_path: str, patterns: list[str]) -> bool:
    """Simple gitignore check — matches filename or path against patterns."""
    parts = relative_path.split("/")
    filename = parts[-1]
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        # Match against filename
        if fnmatch.fnmatch(filename, pattern):
            return True
        # Match against full relative path
        if fnmatch.fnmatch(relative_path, pattern):
            return True
        # Match against any path component
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def process_file(filepath: Path, project_path: Path, config: dict) -> dict:
    """Read, chunk, and hash a single file. Returns file processing result."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None

    if len(content) < config.get("min_chunk_size", 50):
        return None

    relative_path = filepath.relative_to(project_path).as_posix()
    fhash = file_hash(content)

    # Chunk the file
    chunks = smart_chunk(
        content,
        max_chars=config.get("chunk_size", 800),
        overlap=config.get("chunk_overlap", 100),
        min_size=config.get("min_chunk_size", 50),
    )

    if not chunks:
        return None

    # Check each chunk for secrets
    for chunk in chunks:
        chunk["is_secret"] = 1 if contains_secret(chunk["content"]) else 0
        chunk["file_path"] = relative_path
        chunk["file_hash"] = fhash

    return {
        "file_path": relative_path,
        "file_hash": fhash,
        "chunks": chunks,
    }


def mine(
    project_dir: str,
    vault: Vault,
    wing: str = None,
    room: str = "general",
    full: bool = False,
    max_workers: int = 4,
    dry_run: bool = False,
    ignore: list[str] = None,
) -> dict:
    """
    Mine a project directory into a vault.

    Uses git diff for incremental mining when available.
    ``ignore`` is an optional list of extra directory names to skip on top
    of the built-in SKIP_DIRS and the project .gitignore.
    Returns stats dict with counts.
    """
    from engramkit.ingest.git_differ import (
        is_git_repo, get_head_commit, get_current_branch, get_changed_files,
    )

    project_path = Path(project_dir).expanduser().resolve()
    config = {
        "chunk_size": 800,
        "chunk_overlap": 100,
        "min_chunk_size": 50,
    }

    if wing is None:
        wing = project_path.name.lower().replace(" ", "_").replace("-", "_")

    # Git-aware: detect changes since last mine
    git_mode = False
    git_commit = None
    git_branch = None
    git_deleted = []
    last_commit = vault.get_meta("last_commit")

    if not full and is_git_repo(str(project_path)):
        git_commit = get_head_commit(str(project_path))
        git_branch = get_current_branch(str(project_path))

        if last_commit and git_commit and last_commit != git_commit:
            # Incremental: only mine files changed since last commit
            changes = get_changed_files(str(project_path), last_commit)
            if changes:
                git_mode = True
                git_deleted = [fp for fp, st in changes.items() if st == "D"]
                changed_paths = {fp for fp, st in changes.items() if st in ("A", "M", "R")}

                # Mark deleted files
                for dpath in git_deleted:
                    vault.mark_file_deleted(dpath)

                # Only scan changed files
                all_files = scan_files(project_dir, extra_ignores=ignore)
                files = [f for f in all_files if f.relative_to(project_path).as_posix() in changed_paths]
            else:
                # No changes since last commit
                files = []
                git_mode = True
        else:
            # No last_commit stored or same commit — full scan with file-hash skip
            files = scan_files(project_dir, extra_ignores=ignore)
    else:
        files = scan_files(project_dir, extra_ignores=ignore)

    generation = vault.next_generation()

    stats = {
        "files_scanned": len(files),
        "files_processed": 0,
        "files_skipped": 0,
        "files_deleted": len(git_deleted),
        "chunks_added": 0,
        "chunks_updated": 0,
        "chunks_stale": 0,
        "secrets_found": 0,
    }

    print(f"\n{'=' * 55}")
    print("  EngramKit Mine")
    print(f"{'=' * 55}")
    print(f"  Wing:       {wing}")
    print(f"  Source:     {project_path}")
    if git_mode:
        print(f"  Mode:       git incremental ({last_commit[:8]}..{git_commit[:8]})")
        print(f"  Changed:    {len(files)} files  Deleted: {len(git_deleted)}")
    else:
        print(f"  Files:      {len(files)}")
    print(f"  Generation: {generation}")
    if git_branch:
        print(f"  Branch:     {git_branch}")
    if dry_run:
        print("  DRY RUN")
    print(f"{'─' * 55}\n")

    # Process and store per-file (stream, not collect-all-then-flush)
    import time
    mine_start = time.perf_counter()
    total_files = len(files)
    first_file = True

    for i, filepath in enumerate(files, 1):
        result = process_file(filepath, project_path, config)
        if not result:
            continue

        if first_file:
            print("  Loading embedding model...", end="", flush=True)
            first_file = False

        fpath = result["file_path"]
        fhash = result["file_hash"]

        # Check if file changed (skip if hash matches)
        if not full:
            stored_hash = vault.get_file_hash(fpath)
            if stored_hash == fhash:
                stats["files_skipped"] += 1
                continue

        # Get existing chunks for this file
        old_hashes = vault.get_chunk_hashes_for_file(fpath)
        new_hashes = {c["content_hash"] for c in result["chunks"]}

        # Stale: old chunks not in new set
        stale = old_hashes - new_hashes
        if stale:
            vault.mark_stale(stale)
            stats["chunks_stale"] += len(stale)

        # Tag chunks with metadata
        for chunk in result["chunks"]:
            chunk["wing"] = wing
            chunk["room"] = room
            chunk["generation"] = generation
            chunk["git_commit"] = git_commit
            chunk["git_branch"] = git_branch
            if chunk["content_hash"] in old_hashes:
                stats["chunks_updated"] += 1
            else:
                stats["chunks_added"] += 1
            if chunk.get("is_secret"):
                stats["secrets_found"] += 1

        # Store immediately per-file (not batching 500)
        if not dry_run:
            vault.batch_upsert_chunks(result["chunks"])
            vault.upsert_file(fpath, fhash, len(result["chunks"]))

        stats["files_processed"] += 1

        # Clear "Loading embedding model..." on first file completion
        if stats["files_processed"] == 1:
            print(" done.\n")

        # Progress with percentage and ETA
        pct = i * 100 // total_files
        elapsed = time.perf_counter() - mine_start
        if i > 1:
            eta = (elapsed / i) * (total_files - i)
            eta_str = f"  ETA: {eta:.0f}s" if eta >= 1 else ""
        else:
            eta_str = ""
        print(f"  [{i:4}/{total_files}] {pct:3}%  +{len(result['chunks']):3} chunks  {fpath[:40]}{eta_str}")

    # Store last-mined commit for incremental mining
    if git_commit and not dry_run:
        vault.set_meta("last_commit", git_commit)
        if git_branch:
            vault.set_meta("last_branch", git_branch)

    # Summary
    total_time = time.perf_counter() - mine_start
    print(f"\n{'=' * 55}")
    print(f"  Done in {total_time:.1f}s")
    print(f"{'─' * 55}")
    print(f"  Files scanned:    {stats['files_scanned']}")
    print(f"  Files processed:  {stats['files_processed']}")
    print(f"  Files skipped:    {stats['files_skipped']} (unchanged)")
    if stats["files_deleted"]:
        print(f"  Files deleted:    {stats['files_deleted']}")
    print(f"  Chunks added:     {stats['chunks_added']}")
    print(f"  Chunks stale:     {stats['chunks_stale']}")
    print(f"  Secrets flagged:  {stats['secrets_found']}")
    if git_commit:
        print(f"  Git commit:       {git_commit[:12]}")
    print(f"{'=' * 55}\n")

    return stats
