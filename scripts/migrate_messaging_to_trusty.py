#!/usr/bin/env python3
"""Export claude-mpm messaging.db rows to trusty-memory palace format.

BACKGROUND
----------
The ``/mpm-message`` skill and its ``MessageService`` backend are
soft-deprecated in favour of trusty-memory palace messaging.  This script
reads every row from ``~/.claude-mpm/messaging.db`` and emits them as
structured JSON entries suitable for import into a trusty-memory palace.

Because trusty-memory is an MCP server (``mcp__memory__*``), this script
cannot call its tools directly.  Instead it writes JSONL (one JSON object per
line) to stdout (or to ``--output <file>``).  Each line represents one message
that should be saved via::

    mcp__memory__palace_save(
        palace="messaging",
        key=entry["key"],
        value=entry["value"],
        type="message",
    )

USAGE
-----
    # Dry run — show what would be exported, no files written
    python scripts/migrate_messaging_to_trusty.py --dry-run

    # Export to stdout (JSONL)
    python scripts/migrate_messaging_to_trusty.py

    # Export to a file
    python scripts/migrate_messaging_to_trusty.py --output /tmp/messages.jsonl

    # Point at a non-default DB path
    python scripts/migrate_messaging_to_trusty.py --db /path/to/messaging.db

SAFETY
------
This script is **read-only** — it never modifies ``messaging.db``.  Running
it multiple times is safe (idempotent from the source DB's perspective).

SEE ALSO
---------
- ``src/claude_mpm/services/communication/message_service.py`` (source)
- ``bobmatnyc/trusty-tools#99`` for full migration guidance
"""

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".claude-mpm" / "messaging.db"

# Schema columns present in the ``messages`` table (see messaging_db.py).
_MESSAGE_COLUMNS = (
    "id",
    "from_project",
    "from_agent",
    "to_project",
    "to_agent",
    "message_type",
    "priority",
    "subject",
    "body",
    "status",
    "created_at",
    "read_at",
    "replied_to",
    "task_injected",
    "metadata",
    "attachments",
)


def _read_messages(db_path: Path) -> list[dict]:
    """Return all rows from ``messages`` table as plain dicts.

    Args:
        db_path: Path to ``messaging.db``.

    Returns:
        List of message dicts.  Empty list if table does not exist.

    Raises:
        sqlite3.OperationalError: If the DB exists but cannot be opened.
    """
    conn = sqlite3.connect(str(db_path), timeout=1.0)
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL-mode reads (matches MessagingDatabase)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.execute("SELECT * FROM messages ORDER BY created_at")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            logger.info("No 'messages' table found in %s — nothing to export.", db_path)
            return []
        raise
    finally:
        conn.close()


def _row_to_palace_entry(row: dict) -> dict:
    """Convert a DB row to a trusty-memory palace entry dict.

    The trusty-memory ``palace_save`` tool expects:
    - ``palace``: string name of the palace drawer (we use ``"messaging"``)
    - ``key``: unique identifier for the entry
    - ``value``: the content to store (we embed the full message as JSON)
    - ``type``: entry type tag (we use ``"message"``)

    Args:
        row: Raw DB row as a dict.

    Returns:
        Dict with ``palace``, ``key``, ``value``, ``type`` fields.
    """
    # Deserialize JSON-encoded columns (metadata, attachments)
    metadata_raw = row.get("metadata") or "{}"
    attachments_raw = row.get("attachments") or "[]"
    try:
        metadata = (
            json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
        )
    except (json.JSONDecodeError, TypeError):
        metadata = {}
    try:
        attachments = (
            json.loads(attachments_raw)
            if isinstance(attachments_raw, str)
            else attachments_raw
        )
    except (json.JSONDecodeError, TypeError):
        attachments = []

    message_payload = {
        "id": row.get("id", ""),
        "from_project": row.get("from_project", ""),
        "from_agent": row.get("from_agent", "pm"),
        "to_project": row.get("to_project", ""),
        "to_agent": row.get("to_agent", "pm"),
        "message_type": row.get("message_type", "notification"),
        "priority": row.get("priority", "normal"),
        "subject": row.get("subject", ""),
        "body": row.get("body", ""),
        "status": row.get("status", "unread"),
        "created_at": row.get("created_at", ""),
        "read_at": row.get("read_at"),
        "replied_to": row.get("replied_to"),
        "task_injected": bool(row.get("task_injected", 0)),
        "metadata": metadata,
        "attachments": attachments,
        # Source tracking — helps detect duplicate imports
        "migrated_from": "messaging.db",
    }

    return {
        "palace": "messaging",
        "key": f"message/{row.get('id', 'unknown')}",
        "value": message_payload,
        "type": "message",
    }


def migrate(
    db_path: Path,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Read messaging.db and emit palace entries.

    Args:
        db_path: Path to the source SQLite database.
        output_path: Write JSONL here; ``None`` means stdout.
        dry_run: If ``True``, only log what would be exported without writing.

    Returns:
        Number of messages processed (0 if none found or DB missing).
    """
    if not db_path.exists():
        logger.info(
            "messaging.db not found at %s — nothing to migrate.  "
            "This is normal if the /mpm-message skill was never used.",
            db_path,
        )
        return 0

    logger.info("Reading messages from %s …", db_path)
    rows = _read_messages(db_path)

    if not rows:
        logger.info("No messages found in %s.", db_path)
        return 0

    logger.info("Found %d message(s) to export.", len(rows))

    entries = [_row_to_palace_entry(row) for row in rows]

    if dry_run:
        logger.info("[DRY RUN] Would export %d entries:", len(entries))
        for entry in entries:
            logger.info(
                "  key=%s  from=%s  to=%s  subject=%r  status=%s",
                entry["key"],
                entry["value"].get("from_project", "?"),
                entry["value"].get("to_project", "?"),
                entry["value"].get("subject", ""),
                entry["value"].get("status", "?"),
            )
        logger.info("[DRY RUN] No files written.")
        return len(entries)

    jsonl = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n"

    if output_path is None:
        sys.stdout.write(jsonl)
        logger.info("Exported %d entries to stdout (JSONL).", len(entries))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(jsonl, encoding="utf-8")
        logger.info("Exported %d entries to %s.", len(entries), output_path)

    logger.info(
        "Next step: import each JSONL line via mcp__memory__palace_save "
        "(palace='messaging', type='message').  "
        "See bobmatnyc/trusty-tools#99 for detailed import instructions."
    )
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Export claude-mpm messaging.db to trusty-memory palace format (JSONL). "
            "Read-only — never modifies the source database."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        metavar="PATH",
        help=f"Path to messaging.db (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write JSONL output to this file (default: stdout)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be exported without writing any output",
    )
    args = parser.parse_args(argv)

    try:
        count = migrate(
            db_path=args.db,
            output_path=args.output,
            dry_run=args.dry_run,
        )
        if count == 0:
            print(
                "No messages to export.  Nothing to do.",
                file=sys.stderr,
            )
        return 0
    except Exception as exc:
        logger.error("Migration failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
