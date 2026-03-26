"""CLI commands for the multi-channel connection manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def add_channels_subcommand(subparsers: argparse._SubParsersAction) -> None:
    ch = subparsers.add_parser(
        "channels", help="Manage multi-channel connection manager"
    )
    ch_sub = ch.add_subparsers(dest="channels_cmd")

    # setup
    setup = ch_sub.add_parser("setup", help="Initialize channels.yaml with defaults")
    setup.add_argument("--force", action="store_true", help="Overwrite existing config")

    # auth (Phase 2 -- pairing)
    auth = ch_sub.add_parser(
        "auth", help="Confirm a pairing code from a remote channel"
    )
    auth.add_argument(
        "--code",
        required=True,
        metavar="CODE",
        help="Pairing code (e.g. MPM-7X3K-9PQ2)",
    )

    # revoke
    revoke = ch_sub.add_parser("revoke", help="Revoke a remote user's authorization")
    revoke.add_argument("--channel", required=True, choices=["telegram", "slack"])
    revoke.add_argument("--user", required=True, metavar="USER_ID")

    # list
    ch_sub.add_parser("list", help="List active sessions")


def handle_channels_command(args: argparse.Namespace) -> int:
    cmd = getattr(args, "channels_cmd", None)
    if cmd == "setup":
        from claude_mpm.services.channels.channel_config import (
            write_default_channels_config,
        )

        path = write_default_channels_config()
        print(f"Channels config written to {path}")
        return 0
    if cmd == "auth":
        return channels_auth_command(args)
    if cmd == "revoke":
        from claude_mpm.services.channels.auth_manager import AuthManager

        AuthManager().revoke(args.channel, args.user)
        print(f"Revoked auth for {args.channel}:{args.user}")
        return 0
    if cmd == "list":
        return channels_list_command()
    print("Usage: claude-mpm channels [setup|auth|revoke|list]")
    return 1


def channels_list_command() -> int:
    """List active hub sessions by reading hub-state.json."""
    try:
        from claude_mpm.services.channels.channel_hub import read_hub_state
    except ImportError:
        print("Channels feature not available.")
        return 1

    state = read_hub_state()
    if state is None:
        print("Hub is not running.")
        print("Start with: claude-mpm --sdk --channels terminal")
        return 0

    import os
    import time

    pid = state.get("pid", "?")
    started_at = state.get("started_at", 0)
    version = state.get("version", "unknown")
    sessions = state.get("sessions", [])

    # Check if the hub process is still alive
    try:
        os.kill(int(pid), 0)
        hub_alive = True
    except (OSError, ValueError):
        hub_alive = False

    if not hub_alive:
        print("Hub state file found but process is not running (stale state).")
        return 0

    uptime_s = int(time.time() - started_at) if started_at else 0
    uptime_str = f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m {uptime_s % 60}s"

    print(f"Hub running (pid={pid}, version={version}, uptime={uptime_str})")
    print(f"Sessions: {len(sessions)}")
    if sessions:
        print()
        print(f"  {'NAME':<20} {'STATE':<12} {'CWD'}")
        print(f"  {'-' * 20} {'-' * 12} {'-' * 40}")
        for sess in sessions:
            name = sess.get("name", "?")
            state_val = sess.get("state", "?")
            cwd = sess.get("cwd", "?")
            print(f"  {name:<20} {state_val:<12} {cwd}")
    else:
        print("  (no active sessions)")
    return 0


def channels_auth_command(args: argparse.Namespace) -> int:
    """Confirm a pairing code, with hub-state awareness."""
    try:
        from claude_mpm.services.channels.channel_hub import read_hub_state
    except ImportError:
        pass
    else:
        state = read_hub_state()
        if state is None:
            print(
                "Warning: Hub does not appear to be running. "
                "Start with: claude-mpm --sdk --channels terminal"
            )

    from claude_mpm.services.channels.auth_manager import AuthManager

    mgr = AuthManager()
    user = mgr.confirm_pairing(args.code)
    if user:
        print(f"Paired {user.channel} user '{user.user_display}' ({user.user_id})")
    else:
        print("Invalid or expired pairing code.")
        return 1
    return 0
