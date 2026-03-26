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
        from claude_mpm.services.channels.auth_manager import AuthManager

        mgr = AuthManager()
        user = mgr.confirm_pairing(args.code)
        if user:
            print(f"Paired {user.channel} user '{user.user_display}' ({user.user_id})")
        else:
            print("Invalid or expired pairing code.")
            return 1
        return 0
    if cmd == "revoke":
        from claude_mpm.services.channels.auth_manager import AuthManager

        AuthManager().revoke(args.channel, args.user)
        print(f"Revoked auth for {args.channel}:{args.user}")
        return 0
    if cmd == "list":
        print(
            "Hub must be running to list sessions. Start with: claude-mpm --sdk --channels terminal"
        )
        return 0
    print("Usage: claude-mpm channels [setup|auth|revoke|list]")
    return 1
