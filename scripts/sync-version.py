#!/usr/bin/env python3
"""Keep .claude-plugin/plugin.json and marketplace.json in sync with pyproject.toml.

pyproject.toml is the single source of truth for the version. This script reads
it and rewrites the two plugin manifests if they drift.

Usage:
    python scripts/sync-version.py              # patch files if needed
    python scripts/sync-version.py --check      # exit 1 if drift, for CI
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
TARGETS = [
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "marketplace.json",
]


def read_project_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text())
    return data["project"]["version"]


def _patch_json_version(text: str, new_version: str) -> tuple[str, bool]:
    """Rewrite every "version": "..." occurrence while preserving formatting."""
    pattern = re.compile(r'("version"\s*:\s*)"([^"]+)"')
    changed = False

    def _sub(match: re.Match[str]) -> str:
        nonlocal changed
        if match.group(2) != new_version:
            changed = True
        return f'{match.group(1)}"{new_version}"'

    return pattern.sub(_sub, text), changed


def sync(check_only: bool = False) -> int:
    version = read_project_version()
    drift_found = False

    for target in TARGETS:
        if not target.exists():
            print(f"skip: {target} (missing)")
            continue

        text = target.read_text()
        new_text, changed = _patch_json_version(text, version)

        # Sanity: every target must parse as JSON after the patch.
        try:
            json.loads(new_text)
        except json.JSONDecodeError as e:
            print(f"ERROR: {target} would become invalid JSON: {e}", file=sys.stderr)
            return 2

        if not changed:
            print(f"ok:   {target.relative_to(ROOT)} @ {version}")
            continue

        drift_found = True
        if check_only:
            print(
                f"drift: {target.relative_to(ROOT)} needs version {version}",
                file=sys.stderr,
            )
        else:
            target.write_text(new_text)
            print(f"wrote: {target.relative_to(ROOT)} @ {version}")

    if check_only and drift_found:
        print(
            "\nRun `python scripts/sync-version.py` to fix, then commit the changes.",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift and exit 1 without modifying files (for CI).",
    )
    args = parser.parse_args()
    sys.exit(sync(check_only=args.check))


if __name__ == "__main__":
    main()
