"""Commander CLI entry point."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from claude_mpm.commander.instance_manager import InstanceManager
from claude_mpm.commander.llm.openrouter_client import (
    OpenRouterClient,
    OpenRouterConfig,
)
from claude_mpm.commander.llm.summarizer import OutputSummarizer
from claude_mpm.commander.proxy.formatter import OutputFormatter
from claude_mpm.commander.proxy.output_handler import OutputHandler
from claude_mpm.commander.proxy.relay import OutputRelay
from claude_mpm.commander.session.manager import SessionManager
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator

from .repl import CommanderREPL

logger = logging.getLogger(__name__)


async def run_commander(
    port: int = 8765,
    state_dir: Optional[Path] = None,
) -> None:
    """Run Commander in interactive mode.

    Args:
        port: Port for internal services (unused currently).
        state_dir: Directory for state persistence (optional).

    Example:
        >>> asyncio.run(run_commander())
        # Starts interactive Commander REPL
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize components
    logger.info("Initializing Commander...")

    # Create tmux orchestrator
    orchestrator = TmuxOrchestrator()

    # Create instance manager
    instance_manager = InstanceManager(orchestrator)

    # Create session manager
    session_manager = SessionManager()

    # Try to initialize LLM client (optional)
    llm_client: Optional[OpenRouterClient] = None
    try:
        config = OpenRouterConfig()
        llm_client = OpenRouterClient(config)
        logger.info("LLM client initialized")
    except ValueError as e:
        logger.warning(f"LLM client not available: {e}")
        logger.warning("Output summarization will be disabled")

    # Create output relay (optional)
    output_relay: Optional[OutputRelay] = None
    if llm_client:
        try:
            summarizer = OutputSummarizer(llm_client)
            handler = OutputHandler(orchestrator, summarizer)
            formatter = OutputFormatter()
            output_relay = OutputRelay(handler, formatter)
            logger.info("Output relay initialized")
        except Exception as e:
            logger.warning(f"Output relay setup failed: {e}")

    # Create REPL
    repl = CommanderREPL(
        instance_manager=instance_manager,
        session_manager=session_manager,
        output_relay=output_relay,
        llm_client=llm_client,
    )

    # Run REPL
    try:
        await repl.run()
    except KeyboardInterrupt:
        logger.info("Commander interrupted by user")
    except Exception as e:
        logger.error(f"Commander error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down Commander...")
        if output_relay:
            await output_relay.stop_all()


def main() -> None:
    """Entry point for command-line execution."""
    asyncio.run(run_commander())


if __name__ == "__main__":
    main()
