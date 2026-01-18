"""Commander command handler for CLI."""

import asyncio
import logging
import shutil
import threading
import time
from pathlib import Path

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
{CYAN}╭{'─' * (width - 2)}╮{RESET}
{CYAN}│{RESET}{BOLD}  ⚡ MPM Commander {RESET}{DIM}v{version}{RESET}{' ' * (width - 24 - len(version))}│
{CYAN}│{RESET}{DIM}  Multi-Project AI Orchestration{RESET}{' ' * (width - 36)}│
{CYAN}├{'─' * (width - 2)}┤{RESET}
{CYAN}│{RESET}  {YELLOW}ALPHA{RESET} - APIs may change                                {' ' * (width - 55)}│
{CYAN}╰{'─' * (width - 2)}╯{RESET}
"""
    print(banner)


def _count_deployed_agents() -> int:
    """Count deployed agents from .claude/agents/."""
    try:
        deploy_target = Path.cwd() / ".claude" / "agents"
        if not deploy_target.exists():
            return 0
        agent_files = [
            f
            for f in deploy_target.glob("*.md")
            if not f.name.startswith(("README", "INSTRUCTIONS", "."))
        ]
        return len(agent_files)
    except Exception:
        return 0


def _count_mpm_skills() -> int:
    """Count user-level MPM skills from ~/.claude/skills/."""
    try:
        user_skills_dir = Path.home() / ".claude" / "skills"
        if not user_skills_dir.exists():
            return 0
        skill_count = 0
        for item in user_skills_dir.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skill_count += 1
            elif item.is_file() and item.suffix == ".md" and item.name != "README.md":
                skill_count += 1
        return skill_count
    except Exception:
        return 0


def load_agents_and_skills():
    """Load agents and skills for Commander sessions."""
    try:
        print(f"{DIM}Loading agents...{RESET}", end=" ", flush=True)
        agent_count = _count_deployed_agents()
        print(f"{GREEN}✓{RESET} {agent_count} agents")

        print(f"{DIM}Loading skills...{RESET}", end=" ", flush=True)
        skill_count = _count_mpm_skills()
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
            - port: Port for daemon (default: 8765)
            - host: Host for daemon (default: 127.0.0.1)
            - state_dir: Optional state directory path
            - debug: Enable debug logging
            - no_chat: Start daemon only without interactive chat
            - daemon_only: Alias for no_chat

    Returns:
        Exit code (0 for success, 1 for error)
    """
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
        port = getattr(args, "port", 8765)
        host = getattr(args, "host", "127.0.0.1")
        state_dir = getattr(args, "state_dir", None)
        no_chat = getattr(args, "no_chat", False) or getattr(args, "daemon_only", False)

        # Check if daemon already running
        daemon_running = False
        try:
            resp = requests.get(f"http://{host}:{port}/api/health", timeout=1)
            if resp.status_code == 200:
                print(f"{GREEN}✓{RESET} Daemon already running on {host}:{port}")
                daemon_running = True
        except (requests.RequestException, requests.ConnectionError):
            pass

        # Start daemon if not running
        if not daemon_running:
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
                return 0

        # Launch interactive chat
        print(f"\n{CYAN}Entering Commander chat...{RESET}\n")
        asyncio.run(run_commander(port=port, state_dir=state_dir))

        return 0

    except KeyboardInterrupt:
        logger.info("Commander interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Commander error: {e}", exc_info=True)
        print(f"{RED}Error:{RESET} {e}")
        return 1
