#!/usr/bin/env python3
"""
Backup and restore operations for agent files.

This module handles creating backups of agent files before modifications
and provides restore functionality.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AgentModification, ModificationType


class BackupManager:
    """Manager for agent file backup and restore operations."""
    
    def __init__(self, backup_root: Path):
        self.logger = logging.getLogger(__name__)
        self.backup_root = backup_root
        self._ensure_backup_directory()
    
    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        self.backup_root.mkdir(parents=True, exist_ok=True)
    
    async def create_backup(self, file_path: str, modification_id: str) -> Optional[str]:
        """Create backup of agent file before modification."""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return None
            
            # Create timestamped backup path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{source_path.stem}_{timestamp}_{modification_id[:8]}{source_path.suffix}"
            backup_path = self.backup_root / backup_filename
            
            # Copy file to backup location
            shutil.copy2(source_path, backup_path)
            
            self.logger.debug(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    async def restore_from_backup(self, modification: AgentModification) -> bool:
        """Restore agent file from backup."""
        try:
            if not modification.backup_path:
                self.logger.warning(f"No backup path for modification {modification.modification_id}")
                return False
            
            backup_path = Path(modification.backup_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Restore file
            original_path = Path(modification.file_path)
            shutil.copy2(backup_path, original_path)
            
            self.logger.info(f"Restored agent '{modification.agent_name}' from backup")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore agent backup: {e}")
            return False
    
    async def cleanup_old_backups(self, max_age_days: int) -> int:
        """Clean up backups older than specified days."""
        try:
            import time
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            cleaned_count = 0
            
            if self.backup_root.exists():
                for backup_file in self.backup_root.iterdir():
                    if backup_file.is_file():
                        file_time = backup_file.stat().st_mtime
                        if file_time < cutoff_time:
                            backup_file.unlink()
                            cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old backup files")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    def get_backup_stats(self) -> dict:
        """Get statistics about backup storage."""
        stats = {
            'total_backups': 0,
            'total_size_bytes': 0,
            'oldest_backup': None,
            'newest_backup': None
        }
        
        try:
            if self.backup_root.exists():
                backup_files = list(self.backup_root.iterdir())
                stats['total_backups'] = len(backup_files)
                
                if backup_files:
                    # Calculate total size
                    stats['total_size_bytes'] = sum(f.stat().st_size for f in backup_files if f.is_file())
                    
                    # Find oldest and newest
                    backup_times = [(f, f.stat().st_mtime) for f in backup_files if f.is_file()]
                    if backup_times:
                        backup_times.sort(key=lambda x: x[1])
                        stats['oldest_backup'] = backup_times[0][0].name
                        stats['newest_backup'] = backup_times[-1][0].name
        
        except Exception as e:
            self.logger.error(f"Failed to get backup stats: {e}")
        
        return stats