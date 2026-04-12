"""Git hook handlers — post-commit, post-merge, and Claude Code auto-save."""

import json
import os
import stat
import sys
from pathlib import Path


POST_COMMIT_HOOK = """\
#!/bin/bash
# EngramKit post-commit hook — auto-mine changed files
# Installed by: engramkit hooks install
python3 -m engramkit mine "$(git rev-parse --show-toplevel)" 2>/dev/null &
"""

POST_MERGE_HOOK = """\
#!/bin/bash
# EngramKit post-merge hook — auto-mine after git pull
# Installed by: engramkit hooks install
python3 -m engramkit mine "$(git rev-parse --show-toplevel)" 2>/dev/null &
"""


def install_hooks(repo_path: str):
    """Install post-commit and post-merge hooks in a git repo."""
    repo = Path(repo_path).expanduser().resolve()
    hooks_dir = repo / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"\n  Error: {repo} is not a git repository (no .git/hooks)\n")
        return

    installed = []

    for name, content in [("post-commit", POST_COMMIT_HOOK), ("post-merge", POST_MERGE_HOOK)]:
        hook_path = hooks_dir / name

        # Don't overwrite existing hooks — append or skip
        if hook_path.exists():
            existing = hook_path.read_text()
            if "engramkit" in existing:
                print(f"  {name}: already installed, skipping")
                continue
            # Append to existing hook
            with open(hook_path, "a") as f:
                f.write(f"\n# --- EngramKit hook (appended) ---\n")
                f.write(content.split("\n", 2)[2])  # Skip shebang
            print(f"  {name}: appended to existing hook")
        else:
            hook_path.write_text(content)
            print(f"  {name}: installed")

        # Make executable
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
        installed.append(name)

    if installed:
        print(f"\n  Git hooks active. On commit/pull, EngramKit will auto-mine changed files.")

    # Also install Claude Code hooks
    install_claude_hooks(repo_path)
    print()


def install_claude_hooks(repo_path: str):
    """Install Claude Code auto-save hooks."""
    repo = Path(repo_path).expanduser().resolve()
    claude_dir = repo / ".claude"
    settings_file = claude_dir / "settings.local.json"

    # Use full path to the Python that has engramkit installed
    import shutil
    engramkit_bin = shutil.which("engramkit")
    if engramkit_bin:
        # Use the same Python that engramkit was installed with
        import sysconfig
        python_path = Path(engramkit_bin).parent / "python3"
        if not python_path.exists():
            python_path = Path(sys.executable)
        hook_command = f"{python_path} -m engramkit.hooks.claude_hook_handler"
    else:
        hook_command = f"{sys.executable} -m engramkit.hooks.claude_hook_handler"

    hooks_config = {
        "hooks": {
            "Stop": [{
                "matcher": "*",
                "hooks": [{
                    "type": "command",
                    "command": f"{hook_command} stop",
                    "timeout": 30
                }]
            }],
            "PreCompact": [{
                "hooks": [{
                    "type": "command",
                    "command": f"{hook_command} precompact",
                    "timeout": 30
                }]
            }]
        }
    }

    # Merge with existing settings
    claude_dir.mkdir(parents=True, exist_ok=True)
    existing = {}
    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Check if already installed
    existing_hooks = existing.get("hooks", {})
    if "Stop" in existing_hooks:
        stop_hooks = existing_hooks["Stop"]
        if any("engramkit" in str(h) for h in stop_hooks):
            print("  Claude hooks: already installed")
            return

    # Merge hooks
    existing.setdefault("hooks", {})
    existing["hooks"].update(hooks_config["hooks"])

    settings_file.write_text(json.dumps(existing, indent=2))
    print("  Claude hooks: installed (Stop + PreCompact auto-save)")
    print("")
    print("  Next: register MCP server for your AI tool:")
    print("    Claude Code: claude mcp add engramkit -- engramkit-mcp")
    print("    Codex:       (coming soon)")


def on_commit(repo_path: str, commit: str = None):
    """Handler called by post-commit hook. Runs incremental mine."""
    from engramkit.storage.vault import VaultManager
    from engramkit.ingest.pipeline import mine

    vault = VaultManager.get_vault(repo_path)
    try:
        wing = vault.get_meta("wing") or Path(repo_path).name.lower().replace("-", "_")
        mine(project_dir=repo_path, vault=vault, wing=wing)
    finally:
        vault.close()


def on_pull(repo_path: str):
    """Handler called by post-merge hook. Runs incremental mine."""
    on_commit(repo_path)  # Same logic — git differ handles the diff
