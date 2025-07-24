"""Backup management functionality for Claude PM framework."""

from pathlib import Path
from typing import Optional, Dict, Any
import datetime
import shutil
import logging

# Import needed for restore operation
from .state_manager import ParentDirectoryOperation, ParentDirectoryAction
from ...utils.path_operations import path_ops


class BackupManager:
    """Manages backup operations for files and framework templates."""
    
    def __init__(self, base_dir: Path, retention_days: int = 30, logger: Optional[logging.Logger] = None):
        """Initialize BackupManager.
        
        Args:
            base_dir: Base directory for the service (typically .claude-pm)
            retention_days: Number of days to retain backups (default: 30)
            logger: Logger instance for logging operations
        """
        self.base_dir = base_dir
        self.retention_days = retention_days
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure framework backup directory exists
        self.framework_backups_dir = self.base_dir / "backups" / "framework"
        path_ops.ensure_dir(self.framework_backups_dir)
    
    def create_backup(self, file_path: Path, backups_dir: Path) -> Optional[Path]:
        """Create a timestamped backup of a file.
        
        Args:
            file_path: Path to the file to backup
            backups_dir: Directory to store the backup
            
        Returns:
            Path to the created backup file, or None if backup failed
        """
        if not path_ops.validate_exists(file_path):
            self.logger.warning(f"Cannot backup non-existent file: {file_path}")
            return None
            
        try:
            # Create backups directory if it doesn't exist
            path_ops.ensure_dir(backups_dir)
            
            # Generate timestamp for backup filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            backup_filename = f"{file_path.stem}_{timestamp}.backup"
            backup_path = backups_dir / backup_filename
            
            # Copy file to backup location
            path_ops.safe_copy(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup of {file_path}: {e}")
            return None
    
    async def backup_parent_directory(self, target_directory: Path, backups_dir: Path) -> Optional[Path]:
        """
        Create a backup of a parent directory's INSTRUCTIONS.md/CLAUDE.md file.

        Args:
            target_directory: Directory containing file to backup
            backups_dir: Directory to store backups

        Returns:
            Path to backup file or None if failed
        """
        try:
            # Check for INSTRUCTIONS.md first, then CLAUDE.md
            target_file = target_directory / "INSTRUCTIONS.md"
            if not path_ops.validate_exists(target_file):
                target_file = target_directory / "CLAUDE.md"
            
            if not path_ops.validate_exists(target_file):
                self.logger.warning(f"No INSTRUCTIONS.md or CLAUDE.md file to backup in {target_directory}")
                return None

            # Delegate to create_backup
            return self.create_backup(target_file, backups_dir)

        except Exception as e:
            self.logger.error(f"Failed to backup parent directory {target_directory}: {e}")
            return None
    
    def backup_framework_template(self, framework_template_path: Path) -> Optional[Path]:
        """Create a backup of the framework template with rotation.
        
        Only keeps the 2 most recent backups to prevent accumulation.
        
        Args:
            framework_template_path: Path to the framework template file
            
        Returns:
            Path to the created backup, or None if backup failed
        """
        if not path_ops.validate_exists(framework_template_path):
            self.logger.warning(f"Framework template not found: {framework_template_path}")
            return None
            
        try:
            # Create backup
            backup_path = self.create_backup(framework_template_path, self.framework_backups_dir)
            
            if backup_path:
                # Rotate backups to keep only 2 most recent
                self._rotate_framework_backups()
                
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to backup framework template: {e}")
            return None
    
    def get_framework_backup_status(self) -> Dict[str, Any]:
        """Get status information about framework backups.
        
        Returns:
            Dictionary containing backup status information
        """
        try:
            backup_files = list(self.framework_backups_dir.glob("framework_CLAUDE_md_*.backup"))
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            status = {
                "backup_dir": str(self.framework_backups_dir),
                "backup_count": len(backup_files),
                "backups": []
            }
            
            for backup_file in backup_files:
                try:
                    stat = backup_file.stat()
                    backup_info = {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "age_days": (datetime.datetime.now() - datetime.datetime.fromtimestamp(stat.st_mtime)).days
                    }
                    status["backups"].append(backup_info)
                except Exception as e:
                    self.logger.warning(f"Could not get info for backup {backup_file}: {e}")
                    
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get framework backup status: {e}")
            return {
                "backup_dir": str(self.framework_backups_dir),
                "backup_count": 0,
                "backups": [],
                "error": str(e)
            }
    
    def _rotate_framework_backups(self) -> None:
        """Rotate framework backups to keep only the 2 most recent."""
        try:
            # Get all framework backup files
            backup_files = list(self.framework_backups_dir.glob("framework_CLAUDE_md_*.backup"))
            
            if len(backup_files) <= 2:
                return
                
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove all but the 2 most recent
            for old_backup in backup_files[2:]:
                try:
                    old_backup.unlink()
                    self.logger.info(f"Removed old framework backup: {old_backup.name}")
                except Exception as e:
                    self.logger.warning(f"Could not remove old backup {old_backup}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to rotate framework backups: {e}")
    
    async def restore_from_backup(
        self, 
        target_directory: Path, 
        backups_dir: Path,
        backup_timestamp: Optional[str] = None
    ) -> ParentDirectoryOperation:
        """
        Restore a parent directory from backup.

        Args:
            target_directory: Directory to restore
            backups_dir: Directory containing backups
            backup_timestamp: Specific backup to restore (latest if None)

        Returns:
            ParentDirectoryOperation result
        """
        try:
            # Check for INSTRUCTIONS.md first, then CLAUDE.md
            target_file = target_directory / "INSTRUCTIONS.md"
            if not target_file.exists():
                target_file = target_directory / "CLAUDE.md"

            # Find backup files
            backup_pattern = f"*{target_file.name}*"
            backup_files = list(backups_dir.glob(backup_pattern))

            if not backup_files:
                raise ValueError(f"No backup files found for {target_file}")

            # Select backup file
            if backup_timestamp:
                backup_file = None
                for bf in backup_files:
                    if backup_timestamp in bf.name:
                        backup_file = bf
                        break

                if not backup_file:
                    raise ValueError(f"No backup found for timestamp: {backup_timestamp}")
            else:
                # Use most recent backup
                backup_file = max(backup_files, key=lambda f: f.stat().st_mtime)

            # Create backup of current file if it exists
            current_backup = None
            if target_file.exists():
                current_backup = self.create_backup(target_file, backups_dir)

            # Restore from backup
            shutil.copy2(backup_file, target_file)

            # Create operation result
            operation = ParentDirectoryOperation(
                action=ParentDirectoryAction.RESTORE,
                target_path=target_file,
                success=True,
                backup_path=current_backup,
                changes_made=[f"Restored {target_file} from backup {backup_file}"],
            )

            self.logger.info(f"Successfully restored {target_file} from backup")
            return operation

        except Exception as e:
            self.logger.error(f"Failed to restore parent directory {target_directory}: {e}")
            return ParentDirectoryOperation(
                action=ParentDirectoryAction.RESTORE,
                target_path=target_file,
                success=False,
                error_message=str(e),
            )