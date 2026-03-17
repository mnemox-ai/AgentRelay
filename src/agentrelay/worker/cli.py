"""CLI entry point for ``agentrelay worker``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys


def _check_claude_cli() -> bool:
    """Return True if ``claude`` CLI is on PATH."""
    return shutil.which("claude") is not None


def _run_worker(args: argparse.Namespace) -> None:
    """Launch the worker loop."""
    from agentrelay.worker.executor import ExecutorConfig
    from agentrelay.worker.runner import WorkerRunner

    claude_path = shutil.which("claude")
    if not claude_path:
        print(
            "[AgentRelay Worker] ERROR: 'claude' CLI not found on PATH.\n"
            "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
            "Then run: claude login\n"
            "Or specify path: agentrelay worker --claude-path /path/to/claude",
            file=sys.stderr,
        )
        raise SystemExit(1)

    executor_config = ExecutorConfig(
        timeout_seconds=args.timeout,
        claude_path=getattr(args, "claude_path", None) or claude_path,
    )
    runner = WorkerRunner(
        server_url=args.server,
        agent_name=args.name,
        poll_interval=args.interval,
        executor_config=executor_config,
    )

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        pass


def _run_mcp(_args: argparse.Namespace) -> None:
    """Launch the MCP server (existing behaviour)."""
    from agentrelay.mcp_server import mcp

    mcp.run()


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args and dispatch to sub-command."""
    parser = argparse.ArgumentParser(
        prog="agentrelay",
        description="AgentRelay — turn idle Claude Code quota into verified output",
    )
    sub = parser.add_subparsers(dest="command")

    # ── worker ──
    wp = sub.add_parser("worker", help="Start auto-claim worker (uses Claude Code CLI)")
    wp.add_argument(
        "--server",
        default="https://agentrelay-api.onrender.com",
        help="AgentRelay server URL (default: %(default)s)",
    )
    wp.add_argument("--name", default=None, help="Worker name (auto-generated if omitted)")
    wp.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Poll interval in seconds (default: 30)",
    )
    wp.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Max seconds per task execution (default: 300)",
    )
    wp.add_argument(
        "--claude-path",
        default=None,
        help="Path to claude CLI binary (auto-detected if omitted)",
    )

    # ── mcp ──
    sub.add_parser("mcp", help="Start MCP server (stdio)")

    args = parser.parse_args(argv)

    if args.command == "worker":
        logging.basicConfig(level=logging.WARNING, format="%(message)s")
        _run_worker(args)
    elif args.command == "mcp":
        _run_mcp(args)
    else:
        parser.print_help()
        raise SystemExit(0)


if __name__ == "__main__":
    main()
