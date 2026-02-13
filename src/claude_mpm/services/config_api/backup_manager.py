"""Backup manager for pre-deployment safety.

Creates timestamped backups of agents, skills, and configuration files
before any destructive operation. Supports restore and automatic pruning.
"""

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BackupResult:
    """Result of a backup creation operation."""

    backup_id: str
    backup_path: Path
    files_backed_up: int
    size_bytes: int
    created_at: str
    operation: str
    entity_type: str
    entity_id: str


@dataclass
class RestoreResult:
    """Result of a backup restore operation."""

    success: bool
    backup_id: str
    files_restored: int
    errors: List[str] = field(default_factory=list)


@dataclass
class BackupMetadata:
    """Metadata for a stored backup."""

    backup_id: str
    backup_path: str
    created_at: str
    operation: str
    entity_type: str
    entity_id: str
    files_backed_up: int
    size_bytes: int


class BackupManager:
    """Manages timestamped backups before destructive operations.

    Backup directory structure:
        ~/.claude-mpm/backups/{backup_id}/
            agents/          # Copy of .claude/agents/
            skills/          # Copy of ~/.claude/skills/
            config/          # Copy of configuration files
            metadata.json    # Backup metadata
    """

    BACKUP_ROOT = Path.home() / ".claude-mpm" / "backups"
    MAX_BACKUPS = 5

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        config_dir: Optional[Path] = None,
    ) -> None:
        """Initialize BackupManager with configurable paths.

        Args:
            backup_root: Root directory for backups. Defaults to ~/.claude-mpm/backups.
            agents_dir: Project agents directory. Defaults to .claude/agents.
            skills_dir: User skills directory. Defaults to ~/.claude/skills.
            config_dir: MPM config directory. Defaults to ~/.claude-mpm/config.
        """
        self.backup_root = backup_root or self.BACKUP_ROOT
        self.agents_dir = agents_dir or (Path.cwd() / ".claude" / "agents")
        self.skills_dir = skills_dir or (Path.home() / ".claude" / "skills")
        self.config_dir = config_dir or (Path.home() / ".claude-mpm" / "config")

    def create_backup(
        self, operation: str, entity_type: str, entity_id: str
    ) -> BackupResult:
        """Create a timestamped backup before a destructive operation.

        Backs up agents directory, skills directory, and config files
        into a single timestamped backup folder.

        Args:
            operation: The operation about to be performed (e.g. "deploy_agent").
            entity_type: Type of entity being modified ("agent", "skill", "config").
            entity_id: Name/identifier of the entity being modified.

        Returns:
            BackupResult with backup details.

        Raises:
            OSError: If backup directory cannot be created or files cannot be copied.
        """
        now = datetime.now(timezone.utc)
        backup_id = now.strftime("%Y-%m-%dT%H-%M-%S")
        backup_dir = self.backup_root / backup_id

        logger.info(
            "Creating backup %s for %s %s/%s",
            backup_id,
            operation,
            entity_type,
            entity_id,
        )

        # Create backup in a temp directory first, then rename for atomicity
        temp_dir = Path(
            tempfile.mkdtemp(prefix="mpm-backup-", dir=self.backup_root.parent)
        )

        try:
            self.backup_root.mkdir(parents=True, exist_ok=True)

            total_files = 0
            total_size = 0

            # Back up agents directory
            if self.agents_dir.exists():
                dest = temp_dir / "agents"
                shutil.copytree(self.agents_dir, dest, dirs_exist_ok=True)
                files, size = self._count_dir(dest)
                total_files += files
                total_size += size
                logger.debug("Backed up %d agent files (%d bytes)", files, size)

            # Back up skills directory
            if self.skills_dir.exists():
                dest = temp_dir / "skills"
                shutil.copytree(self.skills_dir, dest, dirs_exist_ok=True)
                files, size = self._count_dir(dest)
                total_files += files
                total_size += size
                logger.debug("Backed up %d skill files (%d bytes)", files, size)

            # Back up config directory
            if self.config_dir.exists():
                dest = temp_dir / "config"
                shutil.copytree(self.config_dir, dest, dirs_exist_ok=True)
                files, size = self._count_dir(dest)
                total_files += files
                total_size += size
                logger.debug("Backed up %d config files (%d bytes)", files, size)

            # Write metadata
            metadata = {
                "backup_id": backup_id,
                "created_at": now.isoformat(),
                "operation": operation,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "files_backed_up": total_files,
                "size_bytes": total_size,
            }
            metadata_path = temp_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))

            # Atomic rename into final location
            if backup_dir.exists():
                # Edge case: two backups in the same second
                backup_id = now.strftime("%Y-%m-%dT%H-%M-%S") + "-1"
                backup_dir = self.backup_root / backup_id
                metadata["backup_id"] = backup_id
                metadata_path.write_text(json.dumps(metadata, indent=2))

            shutil.move(str(temp_dir), str(backup_dir))

            logger.info(
                "Backup %s created: %d files, %d bytes",
                backup_id,
                total_files,
                total_size,
            )

            # Auto-prune old backups
            self.prune_old_backups()

            return BackupResult(
                backup_id=backup_id,
                backup_path=backup_dir,
                files_backed_up=total_files,
                size_bytes=total_size,
                created_at=now.isoformat(),
                operation=operation,
                entity_type=entity_type,
                entity_id=entity_id,
            )

        except Exception:
            # Clean up temp directory on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def restore_from_backup(self, backup_id: str) -> RestoreResult:
        """Restore agents, skills, and config from a named backup.

        Args:
            backup_id: The backup ID (timestamp-based directory name).

        Returns:
            RestoreResult with restore details.
        """
        backup_dir = self.backup_root / backup_id
        errors: List[str] = []
        total_restored = 0

        if not backup_dir.exists():
            return RestoreResult(
                success=False,
                backup_id=backup_id,
                files_restored=0,
                errors=[f"Backup '{backup_id}' not found at {backup_dir}"],
            )

        logger.info("Restoring from backup %s", backup_id)

        # Restore agents
        agents_backup = backup_dir / "agents"
        if agents_backup.exists():
            try:
                if self.agents_dir.exists():
                    shutil.rmtree(self.agents_dir)
                shutil.copytree(agents_backup, self.agents_dir)
                files, _ = self._count_dir(self.agents_dir)
                total_restored += files
                logger.info("Restored %d agent files", files)
            except Exception as e:
                errors.append(f"Failed to restore agents: {e}")
                logger.error("Failed to restore agents: %s", e)

        # Restore skills
        skills_backup = backup_dir / "skills"
        if skills_backup.exists():
            try:
                if self.skills_dir.exists():
                    shutil.rmtree(self.skills_dir)
                shutil.copytree(skills_backup, self.skills_dir)
                files, _ = self._count_dir(self.skills_dir)
                total_restored += files
                logger.info("Restored %d skill files", files)
            except Exception as e:
                errors.append(f"Failed to restore skills: {e}")
                logger.error("Failed to restore skills: %s", e)

        # Restore config
        config_backup = backup_dir / "config"
        if config_backup.exists():
            try:
                if self.config_dir.exists():
                    shutil.rmtree(self.config_dir)
                shutil.copytree(config_backup, self.config_dir)
                files, _ = self._count_dir(self.config_dir)
                total_restored += files
                logger.info("Restored %d config files", files)
            except Exception as e:
                errors.append(f"Failed to restore config: {e}")
                logger.error("Failed to restore config: %s", e)

        success = len(errors) == 0
        logger.info(
            "Restore %s: %d files restored, %d errors",
            "succeeded" if success else "completed with errors",
            total_restored,
            len(errors),
        )

        return RestoreResult(
            success=success,
            backup_id=backup_id,
            files_restored=total_restored,
            errors=errors,
        )

    def list_backups(self) -> List[BackupMetadata]:
        """List available backups sorted by date (newest first).

        Returns:
            List of BackupMetadata for each valid backup directory.
        """
        if not self.backup_root.exists():
            return []

        backups: List[BackupMetadata] = []

        for entry in self.backup_root.iterdir():
            if not entry.is_dir():
                continue

            metadata_file = entry / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                data = json.loads(metadata_file.read_text())
                backups.append(
                    BackupMetadata(
                        backup_id=data.get("backup_id", entry.name),
                        backup_path=str(entry),
                        created_at=data.get("created_at", ""),
                        operation=data.get("operation", ""),
                        entity_type=data.get("entity_type", ""),
                        entity_id=data.get("entity_id", ""),
                        files_backed_up=data.get("files_backed_up", 0),
                        size_bytes=data.get("size_bytes", 0),
                    )
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping corrupt backup metadata in %s: %s", entry, e)

        # Sort newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def prune_old_backups(self) -> int:
        """Remove backups beyond MAX_BACKUPS (keeps newest).

        Returns:
            Number of backups removed.
        """
        backups = self.list_backups()

        if len(backups) <= self.MAX_BACKUPS:
            return 0

        to_remove = backups[self.MAX_BACKUPS :]
        removed = 0

        for backup in to_remove:
            backup_path = Path(backup.backup_path)
            try:
                shutil.rmtree(backup_path)
                removed += 1
                logger.info("Pruned old backup: %s", backup.backup_id)
            except Exception as e:
                logger.warning("Failed to prune backup %s: %s", backup.backup_id, e)

        return removed

    @staticmethod
    def _count_dir(directory: Path) -> tuple[int, int]:
        """Count files and total size in a directory.

        Returns:
            Tuple of (file_count, total_size_bytes).
        """
        file_count = 0
        total_size = 0
        for f in directory.rglob("*"):
            if f.is_file():
                file_count += 1
                total_size += f.stat().st_size
        return file_count, total_size
