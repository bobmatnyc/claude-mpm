"""Commander CLI entry point."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from claude_mpm.commander.env_loader import load_env
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

# Load environment variables at module import
load_env()

logger = logging.getLogger(__name__)


@dataclass
class CommanderCLIConfig:
    """Configuration for Commander CLI mode.

    Attributes:
        summarize_responses: Whether to use LLM to summarize instance responses
        port: Port for internal services (reserved for future use)
        state_dir: Directory for state persistence (optional)

    Example:
        >>> config = CommanderCLIConfig(summarize_responses=False)
    """

    summarize_responses: bool = True
    port: int = 8765
    state_dir: Optional[Path] = None


async def run_commander(
    port: int = 8765,
    state_dir: Optional[Path] = None,
    config: Optional[CommanderCLIConfig] = None,
) -> None:
    """Run Commander in interactive mode.

    Args:
        port: Port for internal services (unused currently).
        state_dir: Directory for state persistence (optional).
        config: Commander CLI configuration (optional, uses defaults if None).

    Example:
        >>> asyncio.run(run_commander())
        # Starts interactive Commander REPL
        >>> config = CommanderCLIConfig(summarize_responses=False)
        >>> asyncio.run(run_commander(config=config))
        # Starts Commander without response summarization
    """
    # Use default config if not provided
    if config is None:
        config = CommanderCLIConfig(port=port, state_dir=state_dir)

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
        llm_config = OpenRouterConfig()
        llm_client = OpenRouterClient(llm_config)
        logger.info("LLM client initialized")
    except ValueError as e:
        logger.warning(f"LLM client not available: {e}")
        logger.warning("Output summarization will be disabled")

    # Create output relay (optional)
    output_relay: Optional[OutputRelay] = None
    if llm_client:
        try:
            # Only create summarizer if summarize_responses is enabled
            summarizer = None
            if config.summarize_responses:
                summarizer = OutputSummarizer(llm_client)
                logger.info("Response summarization enabled")
            else:
                logger.info("Response summarization disabled")

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
