"""Relays output from instances to user."""

import asyncio
import logging
from typing import Awaitable, Callable

from .formatter import OutputFormatter
from .output_handler import OutputHandler

logger = logging.getLogger(__name__)


class OutputRelay:
    """Relays instance output to user with summarization."""

    def __init__(
        self,
        handler: OutputHandler,
        formatter: OutputFormatter,
        on_output: Callable[[str], Awaitable[None]] | None = None,
    ):
        """Initialize OutputRelay.

        Args:
            handler: OutputHandler for capturing output.
            formatter: OutputFormatter for display formatting.
            on_output: Optional callback to display output.
        """
        self.handler = handler
        self.formatter = formatter
        self.on_output = on_output
        self._monitoring: dict[str, asyncio.Task] = {}

    async def _monitor_output(
        self, instance_name: str, pane_target: str, poll_interval: float
    ) -> None:
        """Monitor output from an instance continuously.

        Args:
            instance_name: Name of the instance.
            pane_target: Tmux pane target.
            poll_interval: Seconds between polls.
        """
        logger.info(f"Starting output relay for {instance_name}")

        try:
            while True:
                # Process output
                chunk = await self.handler.process_output(instance_name, pane_target)

                # If we got new output, format and display
                if chunk and self.on_output:
                    # Use summary format if available, otherwise raw
                    if chunk.summary:
                        output = self.formatter.format_summary(chunk)
                    else:
                        output = self.formatter.format_raw(chunk)

                    await self.on_output(output)

                # Wait before next poll
                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.info(f"Output relay cancelled for {instance_name}")
            raise
        except Exception as e:
            logger.error(f"Error in output relay for {instance_name}: {e}")
            if self.on_output:
                error_msg = self.formatter.format_error(instance_name, str(e))
                try:
                    await self.on_output(error_msg)
                except Exception:  # nosec B110
                    # Intentionally ignore errors in error reporting to avoid cascading failures
                    pass
            raise

    async def start_relay(
        self, instance_name: str, pane_target: str, poll_interval: float = 0.5
    ) -> None:
        """Start relaying output from an instance.

        Args:
            instance_name: Name of the instance.
            pane_target: Tmux pane target.
            poll_interval: Seconds between polls (default: 0.5).
        """
        # Stop existing relay if any
        if instance_name in self._monitoring:
            await self.stop_relay(instance_name)

        # Start monitoring task
        task = asyncio.create_task(
            self._monitor_output(instance_name, pane_target, poll_interval)
        )
        self._monitoring[instance_name] = task

        logger.info(f"Started output relay for {instance_name}")

    async def stop_relay(self, instance_name: str) -> None:
        """Stop relaying output from an instance.

        Args:
            instance_name: Name of the instance.
        """
        task = self._monitoring.pop(instance_name, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            logger.info(f"Stopped output relay for {instance_name}")

    async def stop_all(self) -> None:
        """Stop all output relays."""
        logger.info("Stopping all output relays")

        # Cancel all tasks
        tasks = list(self._monitoring.values())
        for task in tasks:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        self._monitoring.clear()

    async def get_latest_output(
        self, instance_name: str, pane_target: str, context: str | None = None
    ) -> str:
        """Get and format latest output from instance.

        Args:
            instance_name: Name of the instance.
            pane_target: Tmux pane target.
            context: Optional context for summarization.

        Returns:
            Formatted output string.
        """
        # Process output once
        chunk = await self.handler.process_output(
            instance_name, pane_target, context=context
        )

        if chunk is None:
            return self.formatter.format_status(instance_name, "No new output")

        # Format with summary if available
        if chunk.summary:
            return self.formatter.format_summary(chunk)

        return self.formatter.format_raw(chunk)
