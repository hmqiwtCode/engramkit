"""Tests for git-aware change detection."""

import os
import subprocess
from pathlib import Path

import pytest

from engramkit.ingest.git_differ import (
    is_git_repo,
    get_head_commit,
    get_current_branch,
    get_changed_files,
    get_all_tracked_files,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with an initial commit."""
    repo = tmp_path / "git_test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True)

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, capture_output=True)
    return repo


class TestIsGitRepo:
    """Verify git repository detection."""

    def test_git_dir_returns_true(self, git_repo):
        """A directory with .git should be recognized as a git repo."""
        assert is_git_repo(str(git_repo)) is True

    def test_non_git_dir_returns_false(self, tmp_path):
        """A plain directory should not be recognized as a git repo."""
        plain = tmp_path / "not_git"
        plain.mkdir()
        assert is_git_repo(str(plain)) is False

    def test_nonexistent_dir(self, tmp_path):
        """A nonexistent directory should return False, not raise."""
        assert is_git_repo(str(tmp_path / "does_not_exist")) is False

    def test_subdirectory_of_git_repo(self, git_repo):
        """Subdirectories inside a git repo should also return True."""
        sub = git_repo / "subdir"
        sub.mkdir()
        assert is_git_repo(str(sub)) is True


class TestGetHeadCommit:
    """Verify HEAD commit SHA retrieval."""

    def test_returns_sha(self, git_repo):
        """Should return a 40-char hex SHA."""
        sha = get_head_commit(str(git_repo))
        assert sha is not None
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_non_git_dir_returns_none(self, tmp_path):
        """Non-git directories should return None."""
        plain = tmp_path / "no_git"
        plain.mkdir()
        assert get_head_commit(str(plain)) is None

    def test_changes_after_new_commit(self, git_repo):
        """SHA should change after a new commit."""
        sha1 = get_head_commit(str(git_repo))
        (git_repo / "new_file.txt").write_text("hello\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Second commit"], cwd=git_repo, capture_output=True)
        sha2 = get_head_commit(str(git_repo))
        assert sha1 != sha2


class TestGetCurrentBranch:
    """Verify branch name retrieval."""

    def test_returns_branch_name(self, git_repo):
        """Should return a non-empty branch name."""
        branch = get_current_branch(str(git_repo))
        assert branch is not None
        assert len(branch) > 0
        # Default branch is typically 'main' or 'master'
        assert branch in ("main", "master")

    def test_non_git_dir_returns_none(self, tmp_path):
        """Non-git directories should return None."""
        plain = tmp_path / "no_git"
        plain.mkdir()
        assert get_current_branch(str(plain)) is None


class TestGetChangedFiles:
    """Verify changed file detection between commits."""

    def test_added_files(self, git_repo):
        """New files should be reported with status 'A'."""
        first_sha = get_head_commit(str(git_repo))

        # Add a new file
        (git_repo / "added.py").write_text("def foo(): pass\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add file"], cwd=git_repo, capture_output=True)

        changes = get_changed_files(str(git_repo), first_sha)
        assert "added.py" in changes
        assert changes["added.py"] == "A"

    def test_modified_files(self, git_repo):
        """Modified files should be reported with status 'M'."""
        first_sha = get_head_commit(str(git_repo))

        # Modify existing file
        (git_repo / "README.md").write_text("# Updated Test Repo\nNew content.\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify readme"], cwd=git_repo, capture_output=True)

        changes = get_changed_files(str(git_repo), first_sha)
        assert "README.md" in changes
        assert changes["README.md"] == "M"

    def test_deleted_files(self, git_repo):
        """Deleted files should be reported with status 'D'."""
        first_sha = get_head_commit(str(git_repo))

        # Delete a file
        os.remove(git_repo / "README.md")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Delete readme"], cwd=git_repo, capture_output=True)

        changes = get_changed_files(str(git_repo), first_sha)
        assert "README.md" in changes
        assert changes["README.md"] == "D"

    def test_no_changes(self, git_repo):
        """If HEAD hasn't moved, should return empty dict."""
        sha = get_head_commit(str(git_repo))
        changes = get_changed_files(str(git_repo), sha)
        assert changes == {}

    def test_non_git_dir_returns_empty(self, tmp_path):
        """Non-git directory should return empty dict."""
        plain = tmp_path / "no_git"
        plain.mkdir()
        changes = get_changed_files(str(plain), "abc123")
        assert changes == {}

    def test_invalid_commit_returns_empty(self, git_repo):
        """Invalid commit SHA should return empty dict."""
        changes = get_changed_files(str(git_repo), "0000000000000000000000000000000000000000")
        assert changes == {}


class TestGetAllTrackedFiles:
    """Verify retrieval of all tracked files."""

    def test_returns_tracked_files(self, git_repo):
        """Should return a list including committed files."""
        files = get_all_tracked_files(str(git_repo))
        assert "README.md" in files

    def test_non_git_dir_returns_empty(self, tmp_path):
        """Non-git directory should return empty list."""
        plain = tmp_path / "no_git"
        plain.mkdir()
        files = get_all_tracked_files(str(plain))
        assert files == []

    def test_includes_new_tracked_files(self, git_repo):
        """Newly committed files should appear in the list."""
        (git_repo / "new.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new.py"], cwd=git_repo, capture_output=True)

        files = get_all_tracked_files(str(git_repo))
        assert "new.py" in files
        assert "README.md" in files
