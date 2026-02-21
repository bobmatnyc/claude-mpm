#!/usr/bin/env python3
"""
Migration script to convert file-based messages to SQLite database.

This script migrates existing markdown message files to the new SQLite database format.
It preserves all message data and can be run safely multiple times.
"""

import argparse
import sys
from pathlib import Path

import yaml

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.communication.messaging_db import MessagingDatabase

logger = get_logger(__name__)


def parse_markdown_message(content: str) -> dict:
    """Parse a markdown message file."""
    # Split frontmatter and body
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("Invalid message format: missing frontmatter")

    frontmatter_text = parts[1]
    body_text = parts[2].strip()

    # Parse frontmatter
    frontmatter = yaml.safe_load(frontmatter_text)

    # Extract subject from first heading if present
    subject = ""
    if body_text.startswith("# "):
        lines = body_text.split("\n", 1)
        subject = lines[0][2:].strip()
        body_text = lines[1].strip() if len(lines) > 1 else ""

    # Extract attachments section if present
    attachments = []
    if "\n## Attachments\n" in body_text:
        parts = body_text.split("\n## Attachments\n", 1)
        body_text = parts[0].strip()
        attachment_lines = parts[1].strip().split("\n")
        attachments = [
            line.strip("- `").rstrip("`")
            for line in attachment_lines
            if line.strip().startswith("- `")
        ]

    return {
        "id": frontmatter["id"],
        "from_project": frontmatter["from_project"],
        "from_agent": frontmatter.get("from_agent", "pm"),
        "to_project": frontmatter["to_project"],
        "to_agent": frontmatter.get("to_agent", "pm"),
        "type": frontmatter.get("type", "notification"),
        "priority": frontmatter.get("priority", "normal"),
        "subject": subject,
        "body": body_text,
        "status": frontmatter.get("status", "unread"),
        "created_at": frontmatter["created_at"],
        "reply_to": frontmatter.get("reply_to"),
        "metadata": frontmatter.get("metadata", {}),
        "attachments": attachments,
    }


def migrate_project(project_path: Path, force: bool = False) -> tuple[int, int]:
    """
    Migrate messages for a single project.

    Args:
        project_path: Path to project root
        force: Force migration even if database exists

    Returns:
        Tuple of (messages_migrated, messages_skipped)
    """
    inbox_dir = project_path / ".claude-mpm" / "inbox"
    outbox_dir = project_path / ".claude-mpm" / "outbox"
    archive_dir = project_path / ".claude-mpm" / "inbox" / ".archive"
    db_path = project_path / ".claude-mpm" / "messaging.db"

    # Check if database already exists
    if db_path.exists() and not force:
        logger.warning(
            f"Database already exists at {db_path}. Use --force to re-migrate."
        )
        return 0, 0

    # Initialize database
    db = MessagingDatabase(db_path)
    logger.info(f"Initialized database at {db_path}")

    messages_migrated = 0
    messages_skipped = 0

    # Migrate inbox messages
    if inbox_dir.exists():
        for msg_file in inbox_dir.glob("*.md"):
            try:
                content = msg_file.read_text()
                message_data = parse_markdown_message(content)

                # Check if message already exists
                existing = db.get_message(message_data["id"])
                if existing:
                    logger.debug(
                        f"Message {message_data['id']} already exists, skipping"
                    )
                    messages_skipped += 1
                    continue

                # Insert message
                db.insert_message(message_data)
                messages_migrated += 1
                logger.debug(f"Migrated inbox message: {message_data['id']}")

            except Exception as e:
                logger.error(f"Failed to migrate message {msg_file}: {e}")
                messages_skipped += 1

    # Migrate archived messages
    if archive_dir.exists():
        for msg_file in archive_dir.glob("*.md"):
            try:
                content = msg_file.read_text()
                message_data = parse_markdown_message(content)
                message_data["status"] = "archived"  # Override status

                # Check if message already exists
                existing = db.get_message(message_data["id"])
                if existing:
                    logger.debug(
                        f"Message {message_data['id']} already exists, skipping"
                    )
                    messages_skipped += 1
                    continue

                # Insert message
                db.insert_message(message_data)
                messages_migrated += 1
                logger.debug(f"Migrated archived message: {message_data['id']}")

            except Exception as e:
                logger.error(f"Failed to migrate message {msg_file}: {e}")
                messages_skipped += 1

    # Migrate outbox messages (sent messages)
    if outbox_dir.exists():
        for msg_file in outbox_dir.glob("*.md"):
            try:
                content = msg_file.read_text()
                message_data = parse_markdown_message(content)
                message_data["status"] = "sent"  # Outbox messages are sent

                # Check if message already exists
                existing = db.get_message(message_data["id"])
                if existing:
                    logger.debug(
                        f"Message {message_data['id']} already exists, skipping"
                    )
                    messages_skipped += 1
                    continue

                # Insert message
                db.insert_message(message_data)
                messages_migrated += 1
                logger.debug(f"Migrated outbox message: {message_data['id']}")

            except Exception as e:
                logger.error(f"Failed to migrate message {msg_file}: {e}")
                messages_skipped += 1

    return messages_migrated, messages_skipped


def find_projects(search_path: Path) -> list[Path]:
    """
    Find all projects with Claude MPM messaging directories.

    Args:
        search_path: Path to search for projects

    Returns:
        List of project paths
    """
    projects = []

    # Look for .claude-mpm directories
    for claude_dir in search_path.rglob(".claude-mpm"):
        if claude_dir.is_dir():
            project_path = claude_dir.parent
            inbox_dir = claude_dir / "inbox"
            outbox_dir = claude_dir / "outbox"

            # Check if it has messaging directories
            if inbox_dir.exists() or outbox_dir.exists():
                projects.append(project_path)
                logger.debug(f"Found project: {project_path}")

    return projects


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate Claude MPM messages from files to SQLite database"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to project or directory containing projects (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if database already exists",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search for projects to migrate",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    search_path = Path(args.path).resolve()

    if not search_path.exists():
        logger.error(f"Path does not exist: {search_path}")
        return 1

    # Find projects to migrate
    if args.recursive:
        logger.info(f"Recursively searching for projects in: {search_path}")
        projects = find_projects(search_path)
    # Check if path is a project
    elif (search_path / ".claude-mpm").exists():
        projects = [search_path]
    else:
        logger.error(f"No .claude-mpm directory found in: {search_path}")
        logger.info("Use --recursive to search for projects recursively")
        return 1

    if not projects:
        logger.info("No projects found with messaging directories")
        return 0

    logger.info(f"Found {len(projects)} project(s) to migrate")

    total_migrated = 0
    total_skipped = 0
    successful_projects = 0

    for project_path in projects:
        logger.info(f"Migrating project: {project_path}")
        try:
            migrated, skipped = migrate_project(project_path, force=args.force)
            total_migrated += migrated
            total_skipped += skipped
            successful_projects += 1
            logger.info(f"  Migrated: {migrated} messages, Skipped: {skipped}")

        except Exception as e:
            logger.error(f"Failed to migrate project {project_path}: {e}")

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("Migration Summary:")
    logger.info(f"  Projects migrated: {successful_projects}/{len(projects)}")
    logger.info(f"  Messages migrated: {total_migrated}")
    logger.info(f"  Messages skipped: {total_skipped}")

    if total_migrated > 0:
        logger.info("\nMigration completed successfully!")
        logger.info("The new SQLite database is backward compatible.")
        logger.info("Old markdown files can be safely deleted if desired.")
    elif total_skipped > 0:
        logger.info("\nNo new messages to migrate (all already in database)")
    else:
        logger.info("\nNo messages found to migrate")

    return 0


if __name__ == "__main__":
    sys.exit(main())
