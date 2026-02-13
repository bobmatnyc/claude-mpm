"""Operation journal for crash-recovery safety.

Records intent before execution so that incomplete operations can be
detected and rolled back on restart. Uses a JSON file as a minimal
write-ahead log.

Minimal version per Devil's Advocate Note 5: rollback_info is accepted
but not required.
"""

import json
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)

# Valid status transitions
VALID_STATUSES = {"pending", "in_progress", "completed", "failed", "rolled_back"}


@dataclass
class JournalEntry:
    """A single operation record in the journal."""

    id: str
    operation: str
    entity_type: str
    entity_id: str
    started_at: str
    status: str
    backup_id: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    rollback_info: Optional[Dict] = None


class OperationJournal:
    """Write-ahead journal for tracking in-flight operations.

    Journal file schema:
        {
            "version": "1.0",
            "entries": [...]
        }

    Status transitions:
        pending -> in_progress -> completed | failed | rolled_back
    """

    JOURNAL_PATH = Path.home() / ".claude-mpm" / ".operation-journal.json"

    def __init__(self, journal_path: Optional[Path] = None) -> None:
        """Initialize OperationJournal.

        Args:
            journal_path: Path to the journal file. Defaults to JOURNAL_PATH.
        """
        self.journal_path = journal_path or self.JOURNAL_PATH

    def begin_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: str,
        backup_id: str,
        rollback_info: Optional[Dict] = None,
    ) -> str:
        """Write intent before execution begins.

        Args:
            operation: Operation name (e.g. "deploy_agent", "undeploy_skill").
            entity_type: Entity type ("agent", "skill", "config").
            entity_id: Entity identifier.
            backup_id: Associated backup ID for rollback.
            rollback_info: Optional rollback hints (not required in minimal version).

        Returns:
            Operation ID like "op-{timestamp}-{random}".
        """
        op_id = f"op-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()

        entry = JournalEntry(
            id=op_id,
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            started_at=now,
            status="in_progress",
            backup_id=backup_id,
            rollback_info=rollback_info,
        )

        journal = self._load_journal()
        journal["entries"].append(asdict(entry))
        self._save_journal(journal)

        logger.info(
            "Journal: began operation %s (%s %s/%s)",
            op_id,
            operation,
            entity_type,
            entity_id,
        )
        return op_id

    def complete_operation(self, operation_id: str) -> None:
        """Mark an operation as successfully completed.

        Args:
            operation_id: The operation ID returned by begin_operation.
        """
        self._update_status(
            operation_id,
            "completed",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Journal: completed operation %s", operation_id)

    def fail_operation(self, operation_id: str, error: str) -> None:
        """Mark an operation as failed.

        Args:
            operation_id: The operation ID returned by begin_operation.
            error: Error message describing the failure.
        """
        self._update_status(
            operation_id,
            "failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=error,
        )
        logger.warning("Journal: failed operation %s: %s", operation_id, error)

    def check_incomplete_operations(self) -> List[JournalEntry]:
        """Find operations still in_progress (indicates a crash during execution).

        Returns:
            List of JournalEntry objects with status="in_progress".
        """
        journal = self._load_journal()
        incomplete: List[JournalEntry] = []

        for raw in journal["entries"]:
            if raw.get("status") == "in_progress":
                incomplete.append(
                    JournalEntry(
                        **{
                            k: v
                            for k, v in raw.items()
                            if k in JournalEntry.__dataclass_fields__
                        }
                    )
                )

        if incomplete:
            logger.warning("Journal: found %d incomplete operations", len(incomplete))

        return incomplete

    def mark_rolled_back(self, operation_id: str) -> None:
        """Mark an incomplete operation as rolled back.

        Args:
            operation_id: The operation ID to mark as rolled back.
        """
        self._update_status(
            operation_id,
            "rolled_back",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Journal: marked operation %s as rolled_back", operation_id)

    def _update_status(
        self,
        operation_id: str,
        status: str,
        completed_at: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update the status of a journal entry.

        Args:
            operation_id: Operation to update.
            status: New status value.
            completed_at: Optional completion timestamp.
            error: Optional error message.

        Raises:
            ValueError: If operation_id is not found.
        """
        journal = self._load_journal()
        found = False

        for entry in journal["entries"]:
            if entry.get("id") == operation_id:
                entry["status"] = status
                if completed_at is not None:
                    entry["completed_at"] = completed_at
                if error is not None:
                    entry["error"] = error
                found = True
                break

        if not found:
            raise ValueError(f"Operation '{operation_id}' not found in journal")

        self._save_journal(journal)

    def _load_journal(self) -> Dict:
        """Load journal from disk, creating empty journal if missing or corrupt.

        Returns:
            Journal dict with "version" and "entries" keys.
        """
        if not self.journal_path.exists():
            return {"version": "1.0", "entries": []}

        try:
            data = json.loads(self.journal_path.read_text())
            if not isinstance(data, dict) or "entries" not in data:
                logger.warning("Journal file has unexpected format, resetting")
                return {"version": "1.0", "entries": []}
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load journal, starting fresh: %s", e)
            return {"version": "1.0", "entries": []}

    def _save_journal(self, journal: Dict) -> None:
        """Atomically save journal to disk (write to temp, then rename).

        Args:
            journal: Journal dict to persist.
        """
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory for atomic rename
        fd, tmp_path = tempfile.mkstemp(
            prefix=".journal-",
            suffix=".tmp",
            dir=str(self.journal_path.parent),
        )
        try:
            with open(fd, "w") as f:
                json.dump(journal, f, indent=2)

            # Atomic rename
            Path(tmp_path).replace(self.journal_path)
        except Exception:
            # Clean up temp file on failure
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise
