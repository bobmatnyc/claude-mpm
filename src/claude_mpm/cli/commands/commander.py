"""Commander command handler for CLI."""

import asyncio
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Optional

from claude_mpm.commander.port_manager import (
    CommanderPortManager,
    check_and_handle_port_conflict,
)

logger = logging.getLogger(__name__)

# ANSI colors
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def _get_terminal_width() -> int:
    """Get terminal width with reasonable bounds."""
    try:
        width = shutil.get_terminal_size().columns
        return max(80, min(width, 120))
    except Exception:
        return 100


def _get_version() -> str:
    """Get Commander version."""
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


def display_commander_banner():
    """Display Commander-specific startup banner."""
    width = _get_terminal_width()
    version = _get_version()

    # Commander ASCII art banner
    banner = f"""
{CYAN}╭{"─" * (width - 2)}╮{RESET}
{CYAN}│{RESET}{BOLD}  ⚡ MPM Commander {RESET}{DIM}v{version}{RESET}{" " * (width - 24 - len(version))}│
{CYAN}│{RESET}{DIM}  Multi-Project AI Orchestration{RESET}{" " * (width - 36)}│
{CYAN}├{"─" * (width - 2)}┤{RESET}
{CYAN}│{RESET}  {YELLOW}ALPHA{RESET} - APIs may change                                {" " * (width - 55)}│
{CYAN}╰{"─" * (width - 2)}╯{RESET}
"""
    print(banner)


def _count_cached_agents() -> int:
    """Count cached agents from ~/.claude-mpm/cache/agents/."""
    try:
        cache_agents_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
        if not cache_agents_dir.exists():
            return 0
        # Recursively find all .md files excluding base/README files
        agent_files = [
            f
            for f in cache_agents_dir.rglob("*.md")
            if f.is_file()
            and not f.name.startswith(".")
            and f.name not in ("README.md", "BASE-AGENT.md", "INSTRUCTIONS.md")
        ]
        return len(agent_files)
    except Exception:
        return 0


def _count_cached_skills() -> int:
    """Count cached skills from ~/.claude-mpm/cache/skills/."""
    try:
        cache_skills_dir = Path.home() / ".claude-mpm" / "cache" / "skills"
        if not cache_skills_dir.exists():
            return 0
        # Recursively find all directories containing SKILL.md
        skill_files = list(cache_skills_dir.rglob("SKILL.md"))
        return len(skill_files)
    except Exception:
        return 0


def load_agents_and_skills():
    """Load agents and skills for Commander sessions."""
    try:
        print(f"{DIM}Loading agents...{RESET}", end=" ", flush=True)
        agent_count = _count_cached_agents()
        print(f"{GREEN}✓{RESET} {agent_count} agents")

        print(f"{DIM}Loading skills...{RESET}", end=" ", flush=True)
        skill_count = _count_cached_skills()
        print(f"{GREEN}✓{RESET} {skill_count} skills")

        return agent_count, skill_count
    except Exception as e:
        logger.warning(f"Could not load agents/skills: {e}")
        print(f"{YELLOW}⚠{RESET} Could not load agents/skills")
        return 0, 0


def handle_commander_command(args) -> int:
    """Handle the commander command with auto-starting daemon.

    Args:
        args: Parsed command line arguments with:
            - port: Port for daemon (default: 8766)
            - host: Host for daemon (default: 127.0.0.1)
            - state_dir: Optional state directory path
            - debug: Enable debug logging
            - no_chat: Start daemon only without interactive chat
            - daemon_only: Alias for no_chat
            - force: Force kill any process on the port

    Returns:
        Exit code (0 for success, 1 for error)
    """
    port_manager: Optional[CommanderPortManager] = None

    try:
        # Import here to avoid circular dependencies
        import requests

        from claude_mpm.commander.chat.cli import run_commander
        from claude_mpm.commander.config import DaemonConfig
        from claude_mpm.commander.daemon import main as daemon_main

        # Setup debug logging if requested
        if getattr(args, "debug", False):
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        # Display Commander banner
        display_commander_banner()

        # Load agents and skills
        load_agents_and_skills()

        print()  # Blank line after loading

        # Get arguments
        port = getattr(args, "port", 8766)  # NetworkPorts.COMMANDER_DEFAULT
        host = getattr(args, "host", "127.0.0.1")
        state_dir = getattr(args, "state_dir", None)
        no_chat = getattr(args, "no_chat", False) or getattr(args, "daemon_only", False)
        force = getattr(args, "force", False)

        # Pre-startup port conflict check
        print(f"{DIM}Checking port {port}...{RESET}", end=" ", flush=True)
        can_proceed, message, existing_pid = check_and_handle_port_conflict(
            port=port, host=host, force=force
        )
        print()  # Newline after checking message
        print(message)

        if not can_proceed:
            return 1

        # Initialize port manager for PID file management
        port_manager = CommanderPortManager(port=port, host=host)

        # If there's a healthy existing daemon, use it
        daemon_running = existing_pid is not None
        if daemon_running:
            # Existing healthy daemon found, no need to start new one
            pass
        else:
            # Start daemon since no healthy existing daemon
            print(
                f"{DIM}Starting daemon on {host}:{port}...{RESET}", end=" ", flush=True
            )

            # Create daemon config
            config_kwargs = {"host": host, "port": port}
            if state_dir:
                config_kwargs["state_dir"] = state_dir
            config = DaemonConfig(**config_kwargs)

            # Start daemon in background thread
            daemon_thread = threading.Thread(
                target=lambda: asyncio.run(daemon_main(config)), daemon=True
            )
            daemon_thread.start()

            # Wait for daemon to be ready (max 3 seconds)
            for _ in range(30):
                time.sleep(0.1)
                try:
                    resp = requests.get(f"http://{host}:{port}/api/health", timeout=1)
                    if resp.status_code == 200:
                        print(f"{GREEN}✓{RESET}")
                        daemon_running = True
                        # Write PID file for the new daemon
                        # Note: We get the actual daemon PID from the process on port
                        process_info = port_manager.get_process_on_port()
                        if process_info:
                            port_manager.write_pid_file(process_info.pid)
                        break
                except (requests.RequestException, requests.ConnectionError):
                    pass
            else:
                print(f"{RED}✗{RESET} Failed (timeout)")
                return 1

        # If daemon-only mode, keep running until interrupted
        if no_chat:
            print(f"\n{CYAN}Daemon running.{RESET} API at http://{host}:{port}")
            print(f"{DIM}Press Ctrl+C to stop{RESET}\n")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n{DIM}Shutting down...{RESET}")
                # Cleanup PID file on shutdown
                if port_manager:
                    port_manager.cleanup_pid_file()
                return 0

        # Launch interactive chat
        print(f"\n{CYAN}Entering Commander chat...{RESET}\n")
        asyncio.run(run_commander(port=port, state_dir=state_dir))

        return 0

    except KeyboardInterrupt:
        logger.info("Commander interrupted by user")
        # Cleanup PID file on interrupt
        if port_manager:
            port_manager.cleanup_pid_file()
        return 0
    except Exception as e:
        logger.error(f"Commander error: {e}", exc_info=True)
        print(f"{RED}Error:{RESET} {e}")
        return 1
