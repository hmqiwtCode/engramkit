"""Git-aware change detection — use git as source of truth for what changed."""

import subprocess
from pathlib import Path


def is_git_repo(repo_path: str) -> bool:
    """Check if directory is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_head_commit(repo_path: str) -> str | None:
    """Get current HEAD commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_current_branch(repo_path: str) -> str | None:
    """Get current branch name."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_changed_files(repo_path: str, since_commit: str) -> dict[str, str]:
    """
    Get files changed between since_commit and HEAD.

    Returns {relative_path: status} where status is:
        'A' = added
        'M' = modified
        'D' = deleted
        'R' = renamed
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", since_commit, "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    changes = {}
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0][0]  # First char: A, M, D, R, C, etc.
            filepath = parts[-1]   # Last element (handles renames: R100\told\tnew)
            changes[filepath] = status
    return changes


def get_all_tracked_files(repo_path: str) -> list[str]:
    """Get all tracked files in the repo (for full mine)."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_path, capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []
