"""Tests for secret detection."""

from engramkit.ingest.secret_scanner import is_secret_file, contains_secret


class TestSecretFiles:
    def test_env_files(self):
        assert is_secret_file(".env")
        assert is_secret_file(".env.local")
        assert is_secret_file(".env.production")

    def test_key_files(self):
        assert is_secret_file("server.pem")
        assert is_secret_file("private.key")

    def test_credentials(self):
        assert is_secret_file("credentials.json")
        assert is_secret_file("secrets.yaml")

    def test_normal_files(self):
        assert not is_secret_file("main.py")
        assert not is_secret_file("README.md")
        assert not is_secret_file("config.toml")


class TestSecretPatterns:
    def test_api_key(self):
        assert contains_secret("API_KEY=FAKE_KEY_abc123def456ghi789jkl012mno")

    def test_password(self):
        assert contains_secret("password=SuperSecret123!")

    def test_aws_key(self):
        assert contains_secret("aws_access_key_id=AKIAIOSFODNN7EXAMPLE")

    def test_github_token(self):
        assert contains_secret("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")

    def test_openai_key(self):
        assert contains_secret("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456")

    def test_private_key(self):
        assert contains_secret("-----BEGIN RSA PRIVATE KEY-----")

    def test_normal_code(self):
        assert not contains_secret("def calculate_total(items, discount):")
        assert not contains_secret("import os\nprint('hello')")

    def test_short_password_no_match(self):
        """Short values shouldn't trigger (avoid false positives on 'password=x')."""
        assert not contains_secret("password=x")
