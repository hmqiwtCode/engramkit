"""Secret detection — prevents credentials from entering the knowledge base."""

import re
from pathlib import Path


SECRET_FILES = {
    ".env", ".env.local", ".env.production", ".env.staging", ".env.development",
    "credentials.json", "secrets.yaml", "secrets.yml", "secrets.json",
    ".netrc", ".pgpass", ".my.cnf",
}

SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}

SECRET_PATTERNS = [
    re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[\w\-]{20,}", re.I),
    re.compile(r"(?:secret|password|passwd|pwd|token)\s*[:=]\s*['\"]?[\w\-]{8,}", re.I),
    re.compile(r"(?:aws_access_key_id|aws_secret_access_key)\s*[:=]\s*[\w/+=]{16,}", re.I),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),           # GitHub PAT
    re.compile(r"gho_[a-zA-Z0-9]{36}"),           # GitHub OAuth
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),           # OpenAI / Stripe
    re.compile(r"AKIA[0-9A-Z]{16}"),              # AWS access key
    re.compile(r"xox[bpras]-[a-zA-Z0-9\-]{10,}"), # Slack tokens
]


def is_secret_file(filepath: str) -> bool:
    """Check if a file should be entirely excluded."""
    p = Path(filepath)
    if p.name.lower() in SECRET_FILES:
        return True
    if p.suffix.lower() in SECRET_EXTENSIONS:
        return True
    return False


def contains_secret(text: str) -> bool:
    """Check if text contains secret patterns."""
    return any(p.search(text) for p in SECRET_PATTERNS)
