#!/usr/bin/env python3
"""
State Manager - Handles initialization, cleanup, and operation history
================================================================================

This module manages the initialization, cleanup, and operation tracking
for the parent directory manager service.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json

from ...core.logging_config import setup_logging, setup_streaming_logger, finalize_streaming_logs


class ParentDirectoryAction(Enum):
    """Actions for parent directory operations."""
    INSTALL = "install"
    UPDATE = "update"
    BACKUP = "backup"
    RESTORE = "restore"
    VALIDATE = "validate"
    REMOVE = "remove"


@dataclass
class ParentDirectoryStatus:
    """Status information for parent directory files."""
    file_path: Path
    exists: bool
    is_managed: bool
    current_version: Optional[str] = None
    last_modified: Optional[datetime] = None
    checksum: Optional[str] = None
    backup_available: bool = False
    template_source: Optional[str] = None
    deployment_context: Optional[str] = None


@dataclass
class ParentDirectoryOperation:
    """Result of a parent directory operation."""
    action: ParentDirectoryAction
    target_path: Path
    success: bool
    template_id: Optional[str] = None
    version: Optional[str] = None
    backup_path: Optional[Path] = None
    error_message: Optional[str] = None
    changes_made: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StateManager:
    """Manages state and lifecycle for parent directory operations."""

    def __init__(
        self,
        working_dir: Path,
        parent_directory_manager_dir: Path,
        framework_path: Path,
        quiet_mode: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the State Manager.

        Args:
            working_dir: Current working directory
            parent_directory_manager_dir: Parent directory manager directory
            framework_path: Path to framework
            quiet_mode: If True, suppress INFO level logging
            logger: Logger instance to use
        """
        self.working_dir = working_dir
        self.parent_directory_manager_dir = parent_directory_manager_dir
        self.framework_path = framework_path
        self.quiet_mode = quiet_mode
        self.logger = logger
        self._startup_phase = True
        
        # Operation history tracking
        self.operation_history: List[ParentDirectoryOperation] = []
        self.logs_dir = parent_directory_manager_dir / "logs"
        self.operation_history_file = self.logs_dir / "operation_history.json"
        
        # Subsystem version tracking
        self.subsystem_versions = {}
        
        # Deployment context
        self.deployment_context = None

    def log_info_if_not_quiet(self, message: str) -> None:
        """Log INFO message only if not in quiet mode."""
        if not self.quiet_mode and self.logger:
            self.logger.info(message)

    def log_protection_guidance(self, target_file: Path, skip_reason: str) -> None:
        """
        Log detailed guidance when permanent protection blocks deployment.
        
        Args:
            target_file: The file that's being protected
            skip_reason: The reason deployment was blocked
        """
        if not self.logger:
            return
            
        self.logger.error("")
        self.logger.error("🚫 DEPLOYMENT BLOCKED BY PERMANENT PROTECTION")
        self.logger.error("=" * 50)
        self.logger.error(f"Target file: {target_file}")
        self.logger.error(f"Protection reason: {skip_reason}")
        self.logger.error("")
        self.logger.error("📋 EXPLANATION:")
        self.logger.error("The file you're trying to deploy to is NOT a framework deployment template.")
        self.logger.error("This protection prevents overwriting project development files and custom CLAUDE.md files.")
        self.logger.error("")
        self.logger.error("✅ WHAT CAN BE REPLACED:")
        self.logger.error("• Framework deployment templates (identified by specific title and metadata)")
        self.logger.error("• Files with title: '# Claude PM Framework Configuration - Deployment'")
        self.logger.error("• Files containing framework deployment metadata blocks")
        self.logger.error("")
        self.logger.error("🛡️  WHAT IS PROTECTED:")
        self.logger.error("• Project development files")
        self.logger.error("• Custom CLAUDE.md files")
        self.logger.error("• Any file not matching framework deployment template pattern")
        self.logger.error("")
        self.logger.error("🔧 RESOLUTION OPTIONS:")
        self.logger.error("1. If this is a project development file, keep it as-is (protection working correctly)")
        self.logger.error("2. If you need framework deployment here, manually remove the file first")
        self.logger.error("3. If you need both, rename the existing file to preserve your work")
        self.logger.error("")
        self.logger.error("⚠️  IMPORTANT:")
        self.logger.error("The --force flag CANNOT override this protection by design.")
        self.logger.error("This ensures your project development files are never accidentally overwritten.")
        self.logger.error("=" * 50)
    
    def handle_protection_error(self, target_path: Path, error_message: str, simple: bool = False) -> None:
        """Handle protection error with appropriate logging.
        
        Args:
            target_path: The path that was protected
            error_message: The error message
            simple: If True, use simple guidance (just call log_protection_guidance)
        """
        if simple:
            self.log_protection_guidance(target_path, error_message)
        else:
            self.log_info_if_not_quiet(f"🚫 Force flag cannot override project development file protection")
            self.log_info_if_not_quiet(f"   • This protection prevents overwriting non-framework files")
            self.log_info_if_not_quiet(f"   • Only framework deployment templates can be replaced")
            self.log_protection_guidance(target_path, error_message)

    def create_directory_structure(self) -> None:
        """Create the parent directory manager directory structure."""
        directories = [
            self.parent_directory_manager_dir,
            self.parent_directory_manager_dir / "backups",
            self.parent_directory_manager_dir / "configs",
            self.parent_directory_manager_dir / "versions",
            self.logs_dir,
            self.working_dir / ".claude-pm" / "backups" / "framework",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def initialize_paths(self, parent_directory_manager_dir: Path, working_dir: Path) -> Dict[str, Path]:
        """Initialize and return parent directory manager paths.
        
        Args:
            parent_directory_manager_dir: Parent directory manager directory
            working_dir: Working directory
            
        Returns:
            Dictionary of initialized paths
        """
        return {
            'backups_dir': working_dir / ".claude-pm" / "backups" / "parent_directory_manager",
            'configs_dir': parent_directory_manager_dir / "configs",
            'versions_dir': parent_directory_manager_dir / "versions",
            'logs_dir': parent_directory_manager_dir / "logs",
            'managed_directories_file': parent_directory_manager_dir / "configs" / "managed_directories.json",
            'operation_history_file': parent_directory_manager_dir / "logs" / "operation_history.json"
        }

    async def cleanup_temporary_files(self, backups_dir: Path, retention_days: int) -> None:
        """
        Cleanup temporary files and old backups.
        
        Args:
            backups_dir: Directory containing backups
            retention_days: Number of days to retain backups
        """
        try:
            # Clean up old backups
            if backups_dir.exists():
                cutoff_date = datetime.now().timestamp() - (
                    retention_days * 24 * 60 * 60
                )

                for backup_file in backups_dir.rglob("*"):
                    if backup_file.is_file():
                        file_mtime = backup_file.stat().st_mtime
                        if file_mtime < cutoff_date:
                            backup_file.unlink()
                            if self.logger:
                                self.logger.debug(f"Removed old backup: {backup_file}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cleanup temporary files: {e}")

    def add_operation(self, operation: ParentDirectoryOperation) -> None:
        """
        Add an operation to the history.
        
        Args:
            operation: Operation to add
        """
        self.operation_history.append(operation)
    
    def create_operation_result(
        self,
        action: ParentDirectoryAction,
        target_path: Path,
        success: bool,
        template_id: Optional[str] = None,
        version: Optional[str] = None,
        backup_manager = None,
        changes_made: List[str] = None,
        warnings: List[str] = None,
        error_message: Optional[str] = None
    ) -> ParentDirectoryOperation:
        """Create a ParentDirectoryOperation result with common logic.
        
        Args:
            action: Action type
            target_path: Target path
            success: Success status
            template_id: Template ID
            version: Version
            backup_manager: Backup manager instance
            changes_made: List of changes made
            warnings: List of warnings
            error_message: Error message if failed
            
        Returns:
            ParentDirectoryOperation instance
        """
        backup_path = None
        if success and backup_manager and hasattr(backup_manager, 'last_backup_path'):
            backup_path = backup_manager.last_backup_path
            
        return ParentDirectoryOperation(
            action=action,
            target_path=target_path,
            success=success,
            template_id=template_id,
            version=version,
            backup_path=backup_path,
            changes_made=changes_made or [],
            warnings=warnings or [],
            error_message=error_message
        )

    async def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get operation history.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of operation history entries
        """
        try:
            history = []

            # Get most recent operations
            recent_operations = (
                self.operation_history[-limit:] if limit > 0 else self.operation_history
            )

            for operation in recent_operations:
                history_entry = {
                    "action": operation.action.value,
                    "target_path": str(operation.target_path),
                    "success": operation.success,
                    "template_id": operation.template_id,
                    "version": operation.version,
                    "backup_path": str(operation.backup_path) if operation.backup_path else None,
                    "error_message": operation.error_message,
                    "changes_made": operation.changes_made,
                    "warnings": operation.warnings,
                }

                history.append(history_entry)

            return history

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get operation history: {e}")
            return []

    def detect_framework_path(self) -> Path:
        """Detect framework path from environment or deployment structure."""
        # Try environment variable first (set by Node.js CLI)
        if framework_path := os.getenv('CLAUDE_PM_FRAMEWORK_PATH'):
            return Path(framework_path)
            
        # Try deployment directory
        if deployment_dir := os.getenv('CLAUDE_PM_DEPLOYMENT_DIR'):
            return Path(deployment_dir)
            
        # Check if we're running from a wheel/installed package
        current_path = Path(__file__).resolve()
        path_str = str(current_path)
        if 'site-packages' in path_str or 'dist-packages' in path_str:
            # For wheel installations, framework files are in the data directory
            package_dir = Path(__file__).parent.parent.parent.parent
            # Check in the package's data directory
            data_framework_path = package_dir / 'data' / 'framework' / 'CLAUDE.md'
            if data_framework_path.exists():
                return package_dir / 'data'
            # Also check for legacy location within the package
            legacy_framework_path = package_dir / 'framework' / 'CLAUDE.md'
            if legacy_framework_path.exists():
                return package_dir
            
        # Try relative to current module (source installations)
        current_dir = Path(__file__).parent.parent.parent.parent
        if (current_dir / 'framework' / 'CLAUDE.md').exists():
            return current_dir
            
        # Fallback to working directory
        return self.working_dir

    def finalize_startup(self) -> None:
        """Finalize startup phase and switch to normal logging."""
        if self.logger:
            finalize_streaming_logs(self.logger)
            self.logger = setup_logging(self.logger.name)
        self._startup_phase = False

    def is_startup_phase(self) -> bool:
        """Check if in startup phase."""
        return self._startup_phase
    
    def setup_deployment_logger(self, logger):
        """Setup streaming logger for deployment if in startup phase.
        
        Args:
            logger: Current logger instance
            
        Returns:
            Tuple of (original_logger, deployment_streaming)
        """
        if self.is_startup_phase():
            original_logger = logger
            return setup_streaming_logger(logger.name), original_logger, True
        return logger, None, False
    
    def finalize_deployment_logger(self, logger, original_logger, deployment_streaming):
        """Finalize streaming logs if we used streaming logger.
        
        Args:
            logger: Current logger (possibly streaming)
            original_logger: Original logger to restore
            deployment_streaming: Whether streaming was used
            
        Returns:
            Restored logger
        """
        if deployment_streaming and original_logger:
            finalize_streaming_logs(logger)
            return original_logger
        return logger

    async def get_parent_directory_status(
        self, 
        target_directory: Path,
        config_manager,
        backups_dir: Path
    ) -> ParentDirectoryStatus:
        """
        Get status of a parent directory.

        Args:
            target_directory: Directory to check
            config_manager: Configuration manager instance
            backups_dir: Directory containing backups

        Returns:
            ParentDirectoryStatus object
        """
        try:
            # Ensure target_directory is a Path object
            target_directory = Path(target_directory)
            target_file = target_directory / "CLAUDE.md"

            # Check if file exists
            if not target_file.exists():
                return ParentDirectoryStatus(
                    file_path=target_file,
                    exists=False,
                    is_managed=config_manager.is_directory_managed(str(target_directory)),
                )

            # Get file information
            stat = target_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)

            # Calculate checksum
            import hashlib
            content = target_file.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()

            # Check if managed
            directory_key = str(target_directory)
            is_managed = config_manager.is_directory_managed(directory_key)

            # Get template source if managed
            template_source = None
            current_version = None
            deployment_context = None

            if is_managed:
                config = config_manager.get_directory_config(directory_key)
                template_source = config.template_id

                # Get template version
                # template_manager removed - use Claude Code Task Tool instead
                current_version = "unknown"

                deployment_context = config.deployment_metadata.get("deployment_type")

            # Check for backups
            backup_available = False
            if backups_dir.exists():
                backup_pattern = f"*{target_file.name}*"
                backup_files = list(backups_dir.glob(backup_pattern))
                backup_available = len(backup_files) > 0

            return ParentDirectoryStatus(
                file_path=target_file,
                exists=True,
                is_managed=is_managed,
                current_version=current_version,
                last_modified=last_modified,
                checksum=checksum,
                backup_available=backup_available,
                template_source=template_source,
                deployment_context=deployment_context,
            )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get parent directory status for {target_directory}: {e}")
            return ParentDirectoryStatus(
                file_path=Path(target_directory) / "CLAUDE.md", exists=False, is_managed=False
            )

    async def list_managed_directories(
        self,
        config_manager,
        get_parent_directory_status_func
    ) -> List[Dict[str, Any]]:
        """
        List all managed directories.

        Args:
            config_manager: Configuration manager instance
            get_parent_directory_status_func: Function to get directory status

        Returns:
            List of managed directory information
        """
        try:
            directories = []

            for directory_key, config in config_manager.get_all_managed_directories().items():
                # Get current status
                status = await get_parent_directory_status_func(config.target_directory)

                directory_info = {
                    "directory": str(config.target_directory),
                    "context": config.context.value,
                    "template_id": config.template_id,
                    "exists": status.exists,
                    "is_managed": status.is_managed,
                    "current_version": status.current_version,
                    "last_modified": (
                        status.last_modified.isoformat() if status.last_modified else None
                    ),
                    "backup_available": status.backup_available,
                    "deployment_context": status.deployment_context,
                }

                directories.append(directory_info)

            return directories

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to list managed directories: {e}")
            return []

    async def initialize(
        self,
        create_directory_structure_func,
        config_manager,
        validation_manager,
        version_manager,
        deduplicate_claude_md_files_func,
        deployment_aware: bool,
        dependency_manager: Optional[Any]
    ) -> None:
        """
        Initialize the Parent Directory Manager service.
        
        Args:
            create_directory_structure_func: Function to create directories
            config_manager: Configuration manager instance
            validation_manager: Validation manager instance
            version_manager: Version manager instance
            deduplicate_claude_md_files_func: Deduplication function
            deployment_aware: Whether to check deployment context
            dependency_manager: Dependency manager instance
        """
        self.log_info_if_not_quiet("Initializing Parent Directory Manager...")

        try:
            # Create directory structure
            create_directory_structure_func()

            # Load existing configurations
            await config_manager.load_managed_directories()

            # Validate deployment context
            self.deployment_context = await validation_manager.validate_deployment_context(
                deployment_aware,
                dependency_manager
            )
            
            # Validate framework template integrity on startup
            if not validation_manager.validate_framework_template_integrity(self.framework_path):
                if self.logger:
                    self.logger.warning("Framework template integrity check failed during initialization")

            # Load subsystem versions
            await version_manager.load_subsystem_versions()
            
            # CRITICAL STARTUP TASK: Run deduplication to prevent duplicate context loading
            self.log_info_if_not_quiet("Running CLAUDE.md deduplication on startup...")
            try:
                dedup_actions = await deduplicate_claude_md_files_func()
                if dedup_actions:
                    backed_up_count = sum(1 for _, action in dedup_actions if "backed up" in action)
                    if backed_up_count > 0:
                        # Always log deduplication results, even in quiet mode
                        if self.logger:
                            self.logger.warning(f"🧹 Deduplication cleaned up {backed_up_count} redundant framework CLAUDE.md templates")
                            for path, action in dedup_actions:
                                if "backed up" in action:
                                    self.logger.warning(f"  - {path} → {action}")
            except Exception as e:
                # Always log deduplication errors
                if self.logger:
                    self.logger.error(f"Failed to run CLAUDE.md deduplication on startup: {e}")

            self.log_info_if_not_quiet("Parent Directory Manager initialized successfully")
            
            # Finalize streaming logs after initialization
            self.finalize_startup()

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Parent Directory Manager: {e}")
            raise

    async def cleanup(
        self,
        config_manager,
        backups_dir: Path,
        retention_days: int
    ) -> None:
        """
        Cleanup the Parent Directory Manager service.
        
        Args:
            config_manager: Configuration manager instance
            backups_dir: Directory containing backups
            retention_days: Number of days to retain backups
        """
        self.log_info_if_not_quiet("Cleaning up Parent Directory Manager...")

        try:
            # Save current state
            await config_manager.save_managed_directories()

            # Cleanup temporary files
            await self.cleanup_temporary_files(backups_dir, retention_days)

            self.log_info_if_not_quiet("Parent Directory Manager cleanup completed")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cleanup Parent Directory Manager: {e}")