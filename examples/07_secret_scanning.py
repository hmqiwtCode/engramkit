"""
Secret Scanning Demo — Shows how EngramKit auto-detects and excludes secrets.

Usage:
    python examples/07_secret_scanning.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engramkit.ingest.secret_scanner import is_secret_file, contains_secret


def main():
    print("=== File-Level Detection ===")
    files = [".env", ".env.local", "credentials.json", "server.pem", "main.py", "README.md", "config.toml"]
    for f in files:
        blocked = is_secret_file(f)
        status = "BLOCKED" if blocked else "allowed"
        print(f"  {f:25} → {status}")

    print("\n=== Content-Level Detection ===")
    samples = [
        ("API key", "API_KEY=FAKE_KEY_abc123def456ghi789jkl012mno"),
        ("AWS key", "aws_access_key_id=AKIAIOSFODNN7EXAMPLE"),
        ("GitHub token", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"),
        ("Private key", "-----BEGIN RSA PRIVATE KEY-----"),
        ("Password", "database_password=SuperSecret123!"),
        ("Normal code", "def calculate_total(items, discount): pass"),
        ("Normal config", "DEBUG=true\nLOG_LEVEL=info"),
        ("Import", "from datetime import datetime"),
    ]
    for label, text in samples:
        detected = contains_secret(text)
        status = "SECRET DETECTED" if detected else "clean"
        print(f"  {label:20} → {status}")

    print("\nSecrets are automatically excluded during mining.")
    print("They get is_secret=1 in the database and are hidden from search results.")


if __name__ == "__main__":
    main()
