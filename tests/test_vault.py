"""Tests for vault storage layer."""


import pytest

from engramkit.storage.vault import Vault, VaultManager


@pytest.fixture
def tmp_vault(tmp_path):
    vault = Vault(tmp_path / "test_vault")
    vault.open()
    yield vault
    vault.close()


class TestVault:
    def test_open_creates_dirs(self, tmp_path):
        vault = Vault(tmp_path / "new_vault")
        vault.open()
        assert (tmp_path / "new_vault" / "meta.sqlite3").exists()
        assert (tmp_path / "new_vault" / "vectors").is_dir()
        vault.close()

    def test_meta_get_set(self, tmp_vault):
        tmp_vault.set_meta("foo", "bar")
        assert tmp_vault.get_meta("foo") == "bar"

    def test_meta_default(self, tmp_vault):
        assert tmp_vault.get_meta("missing") is None
        assert tmp_vault.get_meta("missing", "default") == "default"

    def test_generation(self, tmp_vault):
        assert tmp_vault.current_generation() == 0
        g1 = tmp_vault.next_generation()
        assert g1 == 1
        g2 = tmp_vault.next_generation()
        assert g2 == 2

    def test_batch_upsert_and_stats(self, tmp_vault):
        chunks = [
            {"content_hash": "aaa", "content": "hello world", "file_path": "test.py",
             "file_hash": "fff", "wing": "test", "room": "general", "generation": 1},
            {"content_hash": "bbb", "content": "goodbye world", "file_path": "test.py",
             "file_hash": "fff", "wing": "test", "room": "general", "generation": 1},
        ]
        tmp_vault.batch_upsert_chunks(chunks)
        stats = tmp_vault.stats()
        assert stats["total_chunks"] == 2
        assert stats["wing_rooms"]["test"]["general"] == 2

    def test_mark_stale(self, tmp_vault):
        chunks = [
            {"content_hash": "aaa", "content": "hello", "file_path": "t.py",
             "file_hash": "f", "wing": "w", "room": "r", "generation": 1},
        ]
        tmp_vault.batch_upsert_chunks(chunks)
        tmp_vault.mark_stale({"aaa"})
        stats = tmp_vault.stats()
        assert stats["stale_chunks"] == 1
        assert stats["total_chunks"] == 0  # stale excluded from active count

    def test_file_hash_tracking(self, tmp_vault):
        assert tmp_vault.get_file_hash("test.py") is None
        tmp_vault.upsert_file("test.py", "abc123", 5)
        assert tmp_vault.get_file_hash("test.py") == "abc123"

    def test_chunk_hashes_for_file(self, tmp_vault):
        chunks = [
            {"content_hash": "h1", "content": "a", "file_path": "a.py",
             "file_hash": "f", "wing": "w", "room": "r", "generation": 1},
            {"content_hash": "h2", "content": "b", "file_path": "a.py",
             "file_hash": "f", "wing": "w", "room": "r", "generation": 1},
            {"content_hash": "h3", "content": "c", "file_path": "b.py",
             "file_hash": "f", "wing": "w", "room": "r", "generation": 1},
        ]
        tmp_vault.batch_upsert_chunks(chunks)
        hashes = tmp_vault.get_chunk_hashes_for_file("a.py")
        assert hashes == {"h1", "h2"}


class TestVaultManager:
    def test_vault_id_deterministic(self):
        id1 = VaultManager.vault_id("/some/path")
        id2 = VaultManager.vault_id("/some/path")
        assert id1 == id2

    def test_vault_id_different_paths(self):
        id1 = VaultManager.vault_id("/path/a")
        id2 = VaultManager.vault_id("/path/b")
        assert id1 != id2
