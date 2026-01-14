"""Work item persistence for MPM Commander.

This module handles persistence and recovery of work queues,
including all work items across all projects.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from ..models.work import WorkItem

logger = logging.getLogger(__name__)


class WorkStore:
    """Persists and recovers work items.

    Provides efficient work item persistence with:
    - Batch save of all work items across all projects
    - Atomic writes to prevent corruption
    - Schema validation on load

    Attributes:
        state_dir: Directory for state files
        work_path: Path to work.json

    Example:
        >>> store = WorkStore(Path("~/.claude-mpm/commander"))
        >>> await store.save_work(work_queues)
        >>> work_items = await store.load_work()
    """

    VERSION = "1.0"

    def __init__(self, state_dir: Path):
        """Initialize work store.

        Args:
            state_dir: Directory for state files (created if needed)
        """
        self.state_dir = state_dir.expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.work_path = self.state_dir / "work.json"

        logger.info(f"Initialized WorkStore at {self.state_dir}")

    async def save_work(self, work_queues: Dict[str, "WorkQueue"]) -> None:  # noqa: F821
        """Save work items from all queues to disk.

        Args:
            work_queues: Dict of project_id -> WorkQueue

        Raises:
            IOError: If write fails
        """
        # Collect all work items from all queues
        all_items: List[WorkItem] = []
        for queue in work_queues.values():
            all_items.extend(queue.list())

        data = {
            "version": self.VERSION,
            "saved_at": self._get_timestamp(),
            "work_items": [item.to_dict() for item in all_items],
        }

        # Run sync I/O in executor
        await asyncio.get_event_loop().run_in_executor(
            None, self._atomic_write, self.work_path, data
        )

        logger.info(
            f"Saved {len(all_items)} work items from {len(work_queues)} "
            f"queues to {self.work_path}"
        )

    async def load_work(self) -> List[WorkItem]:
        """Load work items from disk.

        Returns:
            List of WorkItem instances (empty if file missing or corrupt)
        """
        if not self.work_path.exists():
            logger.info("No work file found, returning empty list")
            return []

        try:
            # Run sync I/O in executor
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._read_json, self.work_path
            )

            if data.get("version") != self.VERSION:
                logger.warning(
                    f"Version mismatch: expected {self.VERSION}, "
                    f"got {data.get('version')}"
                )

            # Deserialize work items
            items = []
            for item_data in data.get("work_items", []):
                try:
                    item = WorkItem.from_dict(item_data)
                    items.append(item)
                except Exception as e:
                    logger.error(f"Failed to deserialize work item: {e}")
                    logger.debug(f"Item data: {item_data}")

            logger.info(f"Loaded {len(items)} work items from {self.work_path}")
            return items

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse work file: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load work items: {e}")
            return []

    def _atomic_write(self, path: Path, data: Dict[str, Any]) -> None:
        """Write data to file atomically.

        Uses temp file + rename to ensure atomic write.

        Args:
            path: Target file path
            data: Dictionary to write as JSON
        """
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=".work-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            json.dump(data, tmp, indent=2, default=str)
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(path)
        logger.debug(f"Wrote work file atomically: {path}")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """Read JSON file.

        Args:
            path: File path

        Returns:
            Parsed JSON data
        """
        with open(path) as f:
            return json.load(f)

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
