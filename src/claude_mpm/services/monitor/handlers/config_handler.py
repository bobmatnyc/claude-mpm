"""Socket.IO event handler for configuration changes.

Emits config_event events for:
- Source CRUD operations (add, update, remove)
- Sync progress and completion
- External config file changes (detected by mtime polling)

Event schema:
{
    "type": "config_event",
    "operation": str,        # "source_added", "source_removed", "sync_progress", etc.
    "entity_type": str,      # "agent_source", "skill_source", "config"
    "entity_id": str | None, # Source ID or None for global events
    "status": str,           # "started", "progress", "completed", "failed"
    "data": dict,            # Operation-specific payload
    "timestamp": str         # ISO 8601
}
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.config_file_lock import get_config_file_mtime
from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


class ConfigEventHandler:
    """Handles emission of config_event Socket.IO events."""

    def __init__(self, sio):
        """Initialize with Socket.IO server instance.

        Args:
            sio: socketio.AsyncServer instance from UnifiedMonitorServer.
        """
        self.sio = sio

    async def emit_config_event(
        self,
        operation: str,
        entity_type: str,
        status: str,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a config_event to all connected clients.

        Args:
            operation: What happened (e.g., "source_added", "sync_progress")
            entity_type: What was affected ("agent_source", "skill_source")
            status: Current state ("started", "progress", "completed", "failed")
            entity_id: Optional identifier of the specific entity
            data: Optional additional payload
        """
        event = {
            "type": "config_event",
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": status,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.sio.emit("config_event", event)
            logger.debug(f"Config event emitted: {operation}/{entity_type}/{status}")
        except Exception as e:
            logger.error(f"Failed to emit config event: {e}")


class ConfigFileWatcher:
    """Polls config files for external modification (mtime changes).

    Runs as an asyncio background task. When a config file's mtime changes
    (from CLI, editor, or another process), emits a config_event so the
    frontend can refresh.

    Watched files:
    - ~/.claude-mpm/config/agent_sources.yaml
    - ~/.claude-mpm/config/skill_sources.yaml
    - ~/.claude-mpm/configuration.yaml (or project-level equivalent)

    Poll interval: 5 seconds.
    """

    def __init__(self, config_event_handler: ConfigEventHandler):
        self.handler = config_event_handler
        self.poll_interval = 5.0
        self._mtimes: Dict[str, float] = {}
        self._task: Optional[asyncio.Task] = None
        self._watched_files = self._get_watched_files()

    def _get_watched_files(self) -> list:
        """Return list of config file paths to watch."""
        home = Path.home()
        return [
            home / ".claude-mpm" / "config" / "agent_sources.yaml",
            home / ".claude-mpm" / "config" / "skill_sources.yaml",
            home / ".claude-mpm" / "configuration.yaml",
        ]

    def start(self) -> None:
        """Start the mtime polling loop as a background task."""
        # Initialize mtimes
        for f in self._watched_files:
            self._mtimes[str(f)] = get_config_file_mtime(f)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Config file watcher started")

    async def stop(self) -> None:
        """Stop the polling loop."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Config file watcher stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop -- checks mtimes every poll_interval seconds."""
        while True:
            await asyncio.sleep(self.poll_interval)
            for file_path in self._watched_files:
                key = str(file_path)
                current_mtime = get_config_file_mtime(file_path)
                previous_mtime = self._mtimes.get(key, 0.0)

                if current_mtime > previous_mtime > 0.0:
                    # File was modified externally
                    entity_type = self._classify_file(file_path)
                    await self.handler.emit_config_event(
                        operation="external_change",
                        entity_type=entity_type,
                        status="completed",
                        data={
                            "file": str(file_path),
                            "previous_mtime": previous_mtime,
                            "current_mtime": current_mtime,
                        },
                    )
                    logger.info(f"External change detected: {file_path}")

                self._mtimes[key] = current_mtime

    def update_mtime(self, config_path: Path) -> None:
        """Update stored mtime after a known write (prevents false alerts).

        Call this after the API writes to a config file so the watcher
        doesn't treat our own write as an external change.

        Args:
            config_path: Path to the file that was just written.
        """
        key = str(config_path)
        self._mtimes[key] = get_config_file_mtime(config_path)

    @staticmethod
    def _classify_file(file_path: Path) -> str:
        """Classify a config file path into an entity_type string."""
        name = file_path.name
        if "agent_sources" in name:
            return "agent_source"
        if "skill_sources" in name:
            return "skill_source"
        return "config"
