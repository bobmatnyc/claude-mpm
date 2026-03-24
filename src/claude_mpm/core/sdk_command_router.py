"""Slash command router for SDK interactive sessions."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandResult:
    """Result of a slash command execution."""

    handled: bool  # True if command was recognized and handled
    output: str | None = None  # Output to display to user
    should_exit: bool = False  # True if session should end


class SDKCommandRouter:
    """Routes slash commands to appropriate handlers in SDK mode.

    Three tiers:
    1. Local commands - handled in Python (exit, quit, help, clear, cost)
    2. SDK API commands - mapped to ClaudeSDKClient methods (model, permissions, mcp)
    3. External CLI commands - run via subprocess (login, logout, doctor)
    """

    # Commands that require shelling out to ``claude`` CLI
    EXTERNAL_COMMANDS: dict[str, list[str]] = field(default_factory=dict)

    # Commands that are REPL-only and cannot be supported
    UNSUPPORTED_COMMANDS: dict[str, str] = field(default_factory=dict)

    def __init__(self, client: Any = None, tracker: Any = None) -> None:
        """Initialize with optional SDK client and session tracker."""
        self._client = client
        self._tracker = tracker

        # Mapping from slash command to CLI args
        self.EXTERNAL_COMMANDS = {
            "/login": ["claude", "auth", "login"],
            "/logout": ["claude", "auth", "logout"],
            "/doctor": ["claude", "doctor"],
        }

        self.UNSUPPORTED_COMMANDS = {
            "/compact": "Context compaction is a REPL-only feature",
            "/vim": "Vim mode is a REPL-only feature",
            "/theme": "Themes are a REPL-only feature",
            "/terminal-setup": "Terminal setup is a REPL-only feature",
        }

    def route(self, user_input: str) -> CommandResult:
        """Route a slash command.

        Returns CommandResult with handled=False if not a command.
        """
        stripped = user_input.strip()

        if not stripped.startswith("/"):
            return CommandResult(handled=False)

        # Parse command and args
        parts = stripped.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Session exit
        if cmd in ("/exit", "/quit"):
            return CommandResult(
                handled=True, output="Session ended.", should_exit=True
            )

        # Help
        if cmd == "/help":
            return self._handle_help()

        # Clear screen
        if cmd == "/clear":
            print("\033[2J\033[H", end="", flush=True)
            return CommandResult(handled=True)

        # Cost (from tracker)
        if cmd == "/cost":
            return self._handle_cost()

        # SDK API commands
        if cmd == "/model" and self._client is not None:
            return self._handle_model(args)

        if cmd == "/permissions" and self._client is not None:
            return self._handle_permissions(args)

        if cmd == "/mcp" and self._client is not None:
            return self._handle_mcp(args)

        # External CLI commands
        if cmd in self.EXTERNAL_COMMANDS:
            return self._handle_external(cmd)

        # Unsupported REPL-only commands
        if cmd in self.UNSUPPORTED_COMMANDS:
            return CommandResult(
                handled=True,
                output=f"Not available in SDK mode: {self.UNSUPPORTED_COMMANDS[cmd]}",
            )

        # Unknown slash command -- don't handle, let it pass through to LLM
        return CommandResult(handled=False)

    def _handle_help(self) -> CommandResult:
        help_text = """SDK Mode Commands:
  /exit, /quit     End session
  /clear           Clear screen
  /cost            Show session cost
  /model [name]    Show or change model
  /permissions     Show or change permission mode
  /mcp             Show MCP server status
  /login           Authenticate with Anthropic
  /logout          Log out
  /doctor          Run diagnostics

REPL-only (not available): /compact, /vim, /theme"""
        return CommandResult(handled=True, output=help_text)

    def _handle_cost(self) -> CommandResult:
        if self._tracker is None:
            return CommandResult(handled=True, output="Cost tracking not available.")
        state = self._tracker.get_session_state()
        cost = state.get("total_cost_usd")
        turns = state.get("turn_count", 0)
        if cost is not None:
            return CommandResult(
                handled=True, output=f"Session cost: ${cost:.4f} ({turns} turns)"
            )
        return CommandResult(
            handled=True,
            output=f"Session: {turns} turns (cost not yet reported)",
        )

    def _handle_model(self, args: str) -> CommandResult:
        if not args.strip():
            # Show current model
            try:
                if self._tracker:
                    state = self._tracker.get_session_state()
                    model = state.get("model", "unknown")
                    return CommandResult(handled=True, output=f"Current model: {model}")
            except Exception:
                pass
            return CommandResult(handled=True, output="Use: /model <model-name>")
        try:
            self._client.set_model(args.strip())
            return CommandResult(handled=True, output=f"Model set to: {args.strip()}")
        except Exception as e:
            return CommandResult(handled=True, output=f"Failed to set model: {e}")

    def _handle_permissions(self, args: str) -> CommandResult:
        if not args.strip():
            return CommandResult(
                handled=True,
                output="Use: /permissions <mode> (e.g., bypassPermissions, default)",
            )
        try:
            self._client.set_permission_mode(args.strip())
            return CommandResult(
                handled=True, output=f"Permission mode set to: {args.strip()}"
            )
        except Exception as e:
            return CommandResult(handled=True, output=f"Failed to set permissions: {e}")

    def _handle_mcp(self, _args: str) -> CommandResult:
        try:
            status = self._client.get_mcp_status()
            lines = ["MCP Servers:"]
            if hasattr(status, "servers") and status.servers:
                for srv in status.servers:
                    name = getattr(srv, "name", "unknown")
                    state = getattr(srv, "status", "unknown")
                    lines.append(f"  {name}: {state}")
            else:
                lines.append("  (none configured)")
            return CommandResult(handled=True, output="\n".join(lines))
        except Exception as e:
            return CommandResult(handled=True, output=f"MCP status error: {e}")

    def _handle_external(self, cmd: str) -> CommandResult:
        """Run an external Claude CLI command."""
        cli_args = self.EXTERNAL_COMMANDS[cmd]
        try:
            print(f"Running: {' '.join(cli_args)}")
            result = subprocess.run(
                cli_args,
                check=False,
                capture_output=False,  # Let it interact with terminal
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return CommandResult(
                    handled=True, output=f"{cmd} completed successfully."
                )
            return CommandResult(
                handled=True, output=f"{cmd} exited with code {result.returncode}"
            )
        except FileNotFoundError:
            return CommandResult(
                handled=True,
                output="Error: 'claude' CLI not found. Install it first.",
            )
        except subprocess.TimeoutExpired:
            return CommandResult(handled=True, output=f"{cmd} timed out after 120s")
        except Exception as e:
            return CommandResult(handled=True, output=f"{cmd} error: {e}")
