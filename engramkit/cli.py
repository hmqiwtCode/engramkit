"""EngramKit CLI — init, mine, search, status, gc."""

import argparse
import sys
from pathlib import Path

from engramkit.config import ENGRAMKIT_HOME


def cmd_init(args):
    """Initialize a vault for a repository."""
    from engramkit.storage.vault import VaultManager

    repo_path = str(Path(args.directory).expanduser().resolve())
    print(f"\n  Initializing vault for: {repo_path}")

    vault = VaultManager.get_vault(repo_path)
    vault.set_meta("wing", args.wing or Path(repo_path).name.lower().replace("-", "_"))
    print(f"  Vault ID:    {VaultManager.vault_id(repo_path)}")
    print(f"  Vault path:  {vault.vault_path}")
    print(f"  Wing:        {vault.get_meta('wing')}")
    print(f"\n  Ready. Run: engramkit mine {args.directory}\n")
    vault.close()


def cmd_mine(args):
    """Mine a project directory into its vault."""
    from engramkit.storage.vault import VaultManager
    from engramkit.ingest.pipeline import mine

    repo_path = str(Path(args.directory).expanduser().resolve())
    vault = VaultManager.get_vault(repo_path)

    wing = args.wing or vault.get_meta("wing") or Path(repo_path).name.lower().replace("-", "_")

    try:
        mine(
            project_dir=repo_path,
            vault=vault,
            wing=wing,
            room=args.room or "general",
            full=args.full,
            dry_run=args.dry_run,
        )
    finally:
        vault.close()


def cmd_search(args):
    """Hybrid search across a vault."""
    from engramkit.storage.vault import VaultManager
    from engramkit.search.hybrid import hybrid_search

    repo_path = str(Path(args.directory).expanduser().resolve()) if args.directory else None

    if repo_path:
        vault = VaultManager.get_vault(repo_path)
    else:
        # Try to find vault from current directory
        cwd = str(Path.cwd())
        vault = VaultManager.get_vault(cwd)

    try:
        results = hybrid_search(
            query=args.query,
            vault=vault,
            n_results=args.results,
            wing=args.wing,
            room=args.room,
        )

        if not results:
            print(f'\n  No results for: "{args.query}"\n')
            return

        print(f"\n{'=' * 60}")
        print(f'  Results for: "{args.query}"')
        if args.wing:
            print(f"  Wing: {args.wing}")
        print(f"{'=' * 60}\n")

        for i, r in enumerate(results, 1):
            sources = ", ".join(r.get("sources", []))
            print(f"  [{i}] {r['wing']} / {r['room']}")
            print(f"      File:    {r['file_path']}")
            print(f"      Score:   {r['score']:.4f}  ({sources})")
            if r.get("git_branch"):
                print(f"      Branch:  {r['git_branch']}")
            print()
            for line in r["content"].strip().split("\n")[:10]:
                print(f"      {line}")
            if r["content"].count("\n") > 10:
                print(f"      ... ({r['content'].count(chr(10)) - 10} more lines)")
            print(f"\n  {'─' * 56}")

        print()
    finally:
        vault.close()


def cmd_status(args):
    """Show vault status."""
    from engramkit.storage.vault import VaultManager

    if args.all:
        vaults = VaultManager.list_vaults()
        if not vaults:
            print("\n  No vaults found.\n")
            return
        print(f"\n{'=' * 60}")
        print(f"  EngramKit — {len(vaults)} vault(s)")
        print(f"{'=' * 60}\n")
        for v in vaults:
            print(f"  {v['vault_id']}  {v['repo_path']}")
            print(f"    Chunks: {v['total_chunks']}  Stale: {v['stale_chunks']}  "
                  f"Files: {v['total_files']}  Gen: {v['generation']}")
            print()
        return

    repo_path = str(Path(args.directory).expanduser().resolve()) if args.directory else str(Path.cwd())
    vault = VaultManager.get_vault(repo_path)
    try:
        s = vault.stats()
        print(f"\n{'=' * 55}")
        print(f"  EngramKit Status — {s['total_chunks']} chunks")
        print(f"{'=' * 55}")
        print(f"  Generation:  {s['generation']}")
        print(f"  Files:       {s['total_files']}")
        print(f"  Stale:       {s['stale_chunks']}")
        print(f"  Secrets:     {s['secret_chunks']} (excluded from search)")
        print()
        for wing, rooms in s["wing_rooms"].items():
            print(f"  WING: {wing}")
            for room, count in sorted(rooms.items(), key=lambda x: -x[1]):
                print(f"    {room:20} {count:5} chunks")
            print()
        print(f"{'=' * 55}\n")
    finally:
        vault.close()


def cmd_wakeup(args):
    """Show L0 + L1 wake-up context."""
    from engramkit.storage.vault import VaultManager
    from engramkit.memory.layers import MemoryStack
    from engramkit.memory.token_budget import TokenBudget

    repo_path = str(Path(args.directory).expanduser().resolve()) if args.directory else str(Path.cwd())
    vault = VaultManager.get_vault(repo_path)
    try:
        budget = TokenBudget(
            l0_max=args.l0_tokens,
            l1_max=args.l1_tokens,
        )
        stack = MemoryStack(vault, budget)
        result = stack.wake_up(wing=args.wing)

        print(f"\n{'=' * 55}")
        print(f"  EngramKit Wake-Up — {result['total_tokens']} tokens")
        print(f"{'=' * 55}")
        l0 = result["l0_report"]
        l1 = result["l1_report"]
        print(f"  L0 (identity):  {l0.tokens_used}/{l0.tokens_budget} tokens  ({l0.chunks_loaded} loaded)")
        print(f"  L1 (essential): {l1.tokens_used}/{l1.tokens_budget} tokens  "
              f"({l1.chunks_loaded} loaded, {l1.chunks_skipped_dedup} deduped, "
              f"{l1.chunks_skipped_budget} over budget)")
        print(f"{'─' * 55}\n")
        if result["text"]:
            print(result["text"][:2000])
            if len(result["text"]) > 2000:
                print(f"\n  ... ({len(result['text']) - 2000} more chars)")
        else:
            print("  (empty — run `engramkit mine` first)")
        print()
    finally:
        vault.close()


def cmd_gc(args):
    """Run garbage collection."""
    from engramkit.storage.vault import VaultManager
    from engramkit.storage.gc import run_gc

    repo_path = str(Path(args.directory).expanduser().resolve()) if args.directory else str(Path.cwd())
    vault = VaultManager.get_vault(repo_path)
    try:
        run_gc(vault, dry_run=args.dry_run, retention_days=args.retention)
    finally:
        vault.close()


def cmd_hooks(args):
    """Install git hooks."""
    from engramkit.hooks.git_hooks import install_hooks

    repo_path = str(Path(args.directory).expanduser().resolve()) if args.directory else str(Path.cwd())
    install_hooks(repo_path)


def _find_free_port(start=3000, end=3100):
    """Find an available port."""
    import socket
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


def _find_running_engramkit() -> int | None:
    """Check if EngramKit dashboard is already running. Returns port or None."""
    import urllib.request
    import json
    # Check a PID file first
    pid_file = ENGRAMKIT_HOME / "dashboard.pid"
    if pid_file.exists():
        try:
            data = json.loads(pid_file.read_text())
            port = data.get("port", 0)
            # Verify it's actually running
            resp = urllib.request.urlopen(f"http://localhost:{port}/api/config", timeout=1)
            if resp.status == 200:
                return port
        except Exception:
            pid_file.unlink(missing_ok=True)
    return None


def cmd_dashboard(args):
    """Start the dashboard — API serves static frontend. No Node.js needed."""
    import os
    import json
    import webbrowser
    import time
    import threading

    # Check if already running
    existing_port = _find_running_engramkit()
    if existing_port:
        print(f"\n  EngramKit dashboard already running at http://localhost:{existing_port}")
        print("  Opening browser...\n")
        webbrowser.open(f"http://localhost:{existing_port}")
        return

    print("""
  ┌─────────────────────────────────────────┐
  │  EngramKit Dashboard                    │
  │  Currently supports Claude Code only    │
  └─────────────────────────────────────────┘
""")

    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        print("  \033[33mNote:\033[0m RAG chat is disabled — optional dependency not installed.")
        print("        Enable with: \033[36mpipx install 'engramkit[chat]' --force\033[0m\n")

    port = _find_free_port(8000, 8100)
    os.environ["UVICORN_PORT"] = str(port)
    os.environ["ENGRAMKIT_SERVE_DASHBOARD"] = "1"

    # Save PID file so we can detect it later
    pid_file = ENGRAMKIT_HOME / "dashboard.pid"
    ENGRAMKIT_HOME.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(json.dumps({"port": port, "pid": os.getpid()}))

    print(f"  http://localhost:{port}")
    print("  Press Ctrl+C to stop\n")

    # Open browser after short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://localhost:{port}")
    threading.Thread(target=open_browser, daemon=True).start()

    from engramkit.api.server import main as start_server
    try:
        start_server()
    finally:
        # Clean up PID file on exit
        pid_file.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        prog="engramkit",
        description="AI memory system with hybrid search and git-aware ingestion",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p = sub.add_parser("init", help="Initialize vault for a repo")
    p.add_argument("directory", help="Project directory")
    p.add_argument("--wing", help="Wing name (default: directory name)")

    # mine
    p = sub.add_parser("mine", help="Mine a project into its vault")
    p.add_argument("directory", help="Project directory")
    p.add_argument("--wing", help="Wing name override")
    p.add_argument("--room", default="general", help="Room name (default: general)")
    p.add_argument("--full", action="store_true", help="Full re-mine (ignore cache)")
    p.add_argument("--dry-run", action="store_true", help="Preview without storing")

    # search
    p = sub.add_parser("search", help="Hybrid search")
    p.add_argument("query", help="Search query")
    p.add_argument("--directory", "-d", help="Project directory (default: cwd)")
    p.add_argument("--wing", help="Filter by wing")
    p.add_argument("--room", help="Filter by room")
    p.add_argument("--results", "-n", type=int, default=5, help="Number of results")

    # status
    p = sub.add_parser("status", help="Show vault status")
    p.add_argument("--directory", "-d", help="Project directory (default: cwd)")
    p.add_argument("--all", action="store_true", help="Show all vaults")

    # wake-up
    p = sub.add_parser("wake-up", help="Show L0+L1 wake-up context")
    p.add_argument("--directory", "-d", help="Project directory (default: cwd)")
    p.add_argument("--wing", help="Filter by wing")
    p.add_argument("--l0-tokens", type=int, default=150, help="L0 token budget")
    p.add_argument("--l1-tokens", type=int, default=1000, help="L1 token budget")

    # gc
    p = sub.add_parser("gc", help="Garbage collection")
    p.add_argument("--directory", "-d", help="Project directory (default: cwd)")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--retention", type=int, default=30, help="Days to keep stale data")

    # hooks
    p = sub.add_parser("hooks", help="Install git hooks")
    p.add_argument("action", choices=["install"], help="Action to perform")
    p.add_argument("--directory", "-d", help="Project directory (default: cwd)")

    # dashboard
    p = sub.add_parser("dashboard", help="Start the web dashboard (API + frontend)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Ensure home exists
    ENGRAMKIT_HOME.mkdir(parents=True, exist_ok=True)

    commands = {
        "init": cmd_init,
        "mine": cmd_mine,
        "search": cmd_search,
        "status": cmd_status,
        "wake-up": cmd_wakeup,
        "gc": cmd_gc,
        "hooks": cmd_hooks,
        "dashboard": cmd_dashboard,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
