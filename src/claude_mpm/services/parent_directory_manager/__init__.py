#!/usr/bin/env python3
"""
Parent Directory Manager Service - CMPM-104: Parent Directory Template Installation
================================================================================

This service provides comprehensive parent directory template management with
deployment awareness, building on CMPM-101, CMPM-102, and CMPM-103.

Key Features:
- Parent directory CLAUDE.md management with deployment awareness
- Template installation workflow with conflict resolution
- Existing file detection and backup system
- Version control integration
- Cross-platform compatibility
- Integration with all previous CMPM implementations

Dependencies:
- CMPM-101 (Deployment Detection System)
- CMPM-102 (Versioned Template Management)
- CMPM-103 (Dependency Management)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ...core.base_service import BaseService
from ...core.logging_config import setup_logging

# Import extracted modules for delegation
from .backup_manager import BackupManager
from .template_deployer import TemplateDeployer, DeploymentContext
from .framework_protector import FrameworkProtector
from .version_control_helper import VersionControlHelper
from .deduplication_manager import DeduplicationManager
from .operations import ParentDirectoryOperations, ParentDirectoryContext
from .config_manager import ConfigManager, ParentDirectoryConfig
from .state_manager import StateManager, ParentDirectoryStatus, ParentDirectoryOperation, ParentDirectoryAction
from .validation_manager import ValidationManager
from .version_manager import VersionManager


class ParentDirectoryManager(BaseService):
    """
    Parent Directory Template Management Service for Claude PM Framework.

    This service provides:
    - Parent directory CLAUDE.md management with deployment awareness
    - Template installation workflow with conflict resolution
    - Existing file detection and backup system
    - Version control integration
    - Integration with CMPM-101, CMPM-102, and CMPM-103
    
    This is now a facade that delegates to specialized modules for:
    - Backup management
    - Template deployment
    - Framework protection
    - Version control
    - Deduplication
    - Directory operations
    - Configuration management
    - State management
    - Validation
    - Version tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, quiet_mode: bool = False):
        """
        Initialize the Parent Directory Manager.

        Args:
            config: Optional configuration dictionary
            quiet_mode: If True, suppress INFO level logging
        """
        super().__init__(name="parent_directory_manager", config=config)
        
        # Setup logger based on quiet mode
        level = "WARNING" if quiet_mode or os.getenv('CLAUDE_PM_QUIET_MODE') == 'true' else "INFO"
        self.logger = setup_logging(__name__, level=level)
        
        self._quiet_mode = quiet_mode  # Store quiet mode setting

        # Configuration
        self.backup_retention_days = self.get_config("backup_retention_days", 30)
        self.deployment_aware = self.get_config("deployment_aware", True)

        # Working paths
        self.working_dir = Path.cwd()
        # Temporarily set framework_path - will be properly set after state manager init
        self.framework_path = Path(__file__).resolve().parent.parent.parent.parent
        self.parent_directory_manager_dir = (
            self.working_dir / ".claude-pm" / "parent_directory_manager"
        )
        
        
        # Initialize extracted service modules for delegation
        self._backup_manager = BackupManager(
            base_dir=self.working_dir,
            retention_days=self.backup_retention_days,
            logger=self.logger
        )
        
        self._template_deployer = TemplateDeployer(
            framework_path=self.framework_path,
            logger=self.logger
        )
        
        self._deduplication_manager = DeduplicationManager(
            logger=self.logger
        )
        
        self._directory_ops = ParentDirectoryOperations(
            logger=self.logger
        )
        
        self._config_manager = ConfigManager(
            configs_dir=self.parent_directory_manager_dir / "configs",
            logger=self.logger
        )
        
        # Initialize version manager early
        self._version_manager = VersionManager(
            framework_path=self.framework_path,
            logger=self.logger
        )
        
        self._state_manager = StateManager(
            working_dir=self.working_dir,
            parent_directory_manager_dir=self.parent_directory_manager_dir,
            framework_path=self.framework_path,
            quiet_mode=quiet_mode,
            logger=self.logger
        )
        
        # Now properly detect framework path using state manager
        self.framework_path = self._detect_framework_path()
        # Update all managers' framework paths
        self._state_manager.framework_path = self.framework_path
        self._template_deployer.framework_path = self.framework_path
        self._version_manager.framework_path = self.framework_path
        
        # Initialize paths
        paths = self._state_manager.initialize_paths(self.parent_directory_manager_dir, self.working_dir)
        self.backups_dir = paths['backups_dir']
        self.configs_dir = paths['configs_dir']
        self.versions_dir = paths['versions_dir']
        self.logs_dir = paths['logs_dir']
        self.managed_directories_file = paths['managed_directories_file']
        self.operation_history_file = paths['operation_history_file']
        
        self._validation_manager = ValidationManager(
            logger=self.logger
        )

        # Integration with other CMPM services removed - use Claude Code Task Tool instead
        self.template_manager = None
        self.dependency_manager = None
        self.deployment_context = None  # Loaded during initialization

    @property
    def quiet(self) -> bool:
        """Get quiet mode setting."""
        return self._quiet_mode
    
    @property
    def version_manager(self):
        """Get version manager for direct access to version operations."""
        return self._version_manager
    
    @property
    def validation_manager(self):
        """Get validation manager for direct access to validation operations."""
        return self._validation_manager

    # Delegation methods for public API
    def _log_info_if_not_quiet(self, message: str) -> None:
        self._state_manager.log_info_if_not_quiet(message)

    def _detect_framework_path(self) -> Path:
        return self._state_manager.detect_framework_path()



    # Main lifecycle methods
    async def _initialize(self) -> None:
        """Initialize the Parent Directory Manager service."""
        # Delegate initialization to StateManager
        await self._state_manager.initialize(
            self._state_manager.create_directory_structure,
            self._config_manager,
            self._validation_manager,
            self._version_manager,
            self._deduplicate_claude_md_files,
            self.deployment_aware,
            self.dependency_manager
        )
        
        # Update local references
        self.managed_directories = self._config_manager.managed_directories
        self.operation_history = self._state_manager.operation_history
        self.deployment_context = self._state_manager.deployment_context
        self.subsystem_versions = self._version_manager.subsystem_versions

    async def _cleanup(self) -> None:
        """Cleanup the Parent Directory Manager service."""
        # Delegate cleanup to StateManager
        await self._state_manager.cleanup(
            self._config_manager,
            self.backups_dir,
            self.backup_retention_days
        )

    # Public API Methods - all delegating to specialized modules

    async def register_parent_directory(
        self,
        target_directory: Path,
        context: ParentDirectoryContext,
        template_id: str,
        template_variables: Dict[str, Any] = None,
        **kwargs,
    ) -> bool:
        """
        Register a parent directory for management.

        Args:
            target_directory: Directory to manage
            context: Context type for the directory
            template_id: Template to use for management
            template_variables: Variables for template rendering
            **kwargs: Additional configuration options

        Returns:
            True if registration successful, False otherwise
        """
        result = await self._config_manager.register_parent_directory(
            target_directory, context, template_id, template_variables, **kwargs
        )
        if result:
            self.managed_directories = self._config_manager.managed_directories
        return result

    async def deploy_framework_template(
        self,
        target_directory: Path,
        force: bool = False,
    ) -> ParentDirectoryOperation:
        """
        Deploy framework template using the new generator with integrated deployment.

        Args:
            target_directory: Directory to deploy template to
            force: Force deployment even if version is current

        Returns:
            ParentDirectoryOperation result
        """
        # Delegate to TemplateDeployer
        success, target_path, error_message, changes_made = await self._template_deployer.deploy_framework_template(
            target_directory=target_directory,
            force=force,
            deduplication_handler=self._deduplicate_claude_md_files,
            backup_manager=self._backup_manager,
            state_manager=self._state_manager,
            quiet=self.quiet
        )
        
        # Handle protection guidance if error
        if not success and "Permanent protection" in error_message:
            self._state_manager.handle_protection_error(target_path, error_message, simple=True)
        
        # Create operation result
        operation = self._state_manager.create_operation_result(
            action=ParentDirectoryAction.INSTALL,
            target_path=target_path,
            success=success,
            template_id="framework_claude_md",
            backup_manager=self._backup_manager,
            changes_made=changes_made if success else [],
            error_message=error_message if not success else None
        )
        
        if success:
            self._state_manager.add_operation(operation)
        
        return operation

    async def install_template_to_parent_directory(
        self,
        target_directory: Path,
        template_id: str,
        template_variables: Dict[str, Any] = None,
        force: bool = False,
    ) -> ParentDirectoryOperation:
        """
        Install a template to a parent directory with version checking.

        Args:
            target_directory: Directory to install template to
            template_id: Template to install
            template_variables: Variables for template rendering
            force: Force installation even if version is current (overrides version checking)

        Returns:
            ParentDirectoryOperation result
        """
        # Handle streaming logging setup
        self.logger, original_logger, deployment_streaming = self._state_manager.setup_deployment_logger(self.logger)
        
        try:
            target_file = target_directory / "CLAUDE.md"
            self._current_target_file = target_file
            
            # Delegate to TemplateDeployer
            success, target_path, version, error_message, changes_made = await self._template_deployer.install_template(
                target_directory=target_directory,
                template_id=template_id,
                template_variables=template_variables,
                force=force,
                deduplication_handler=self._deduplicate_claude_md_files,
                backup_manager=self._backup_manager,
                state_manager=self._state_manager,
                quiet=self.quiet,
                current_target_file=target_file
            )
            
            # Handle protection guidance if error
            if not success and "Permanent protection" in error_message:
                self._state_manager.handle_protection_error(target_path, error_message)
            
            # Handle warnings for skipped deployments
            warnings = []
            if success and "Deployment skipped" in str(changes_made):
                warnings = changes_made
                changes_made = []
            
            # Create and return operation result
            operation = self._state_manager.create_operation_result(
                action=ParentDirectoryAction.INSTALL,
                target_path=target_path,
                success=success,
                template_id=template_id,
                version=version,
                backup_manager=self._backup_manager,
                changes_made=changes_made if success else [],
                warnings=warnings,
                error_message=error_message if not success else None
            )
            
            if success:
                self._state_manager.add_operation(operation)
            
            if hasattr(self, '_current_target_file'):
                del self._current_target_file
            
            self.logger = self._state_manager.finalize_deployment_logger(self.logger, original_logger, deployment_streaming)
            return operation
            
        except Exception as e:
            self.logger.error(f"Failed to install template {template_id} to {target_directory}: {e}")
            
            # Clean up temporary attribute
            if hasattr(self, '_current_target_file'):
                del self._current_target_file
            
            # Finalize streaming logs if we used streaming logger
            self.logger = self._state_manager.finalize_deployment_logger(self.logger, original_logger, deployment_streaming)
            
            return self._state_manager.create_operation_result(
                action=ParentDirectoryAction.INSTALL,
                target_path=target_directory / "CLAUDE.md",
                success=False,
                template_id=template_id,
                error_message=str(e)
            )

    async def update_parent_directory_template(
        self, target_directory: Path, template_variables: Dict[str, Any] = None, force: bool = False
    ) -> ParentDirectoryOperation:
        """
        Update a template in a parent directory.

        Args:
            target_directory: Directory containing template to update
            template_variables: New variables for template rendering
            force: Force update even if no changes detected

        Returns:
            ParentDirectoryOperation result
        """
        try:
            # Check if directory is managed
            directory_key = str(target_directory)
            if not self._config_manager.is_directory_managed(directory_key):
                raise ValueError(f"Directory not managed: {target_directory}")

            config = self._config_manager.get_directory_config(directory_key)

            # Get current status
            status = await self.get_parent_directory_status(target_directory)

            if not status.exists:
                # File doesn't exist, perform installation
                return await self.install_template_to_parent_directory(
                    target_directory, config.template_id, template_variables, force
                )

            # Update template variables if provided
            if template_variables:
                config.template_variables.update(template_variables)

            # For updates, delegate to install with force flag to ensure update happens
            result = await self.install_template_to_parent_directory(
                target_directory, config.template_id, config.template_variables, force=True
            )
            
            # Change the action to UPDATE in the result
            result.action = ParentDirectoryAction.UPDATE
            
            return result

        except Exception as e:
            self.logger.error(f"Failed to update template in {target_directory}: {e}")
            return self._state_manager.create_operation_result(
                action=ParentDirectoryAction.UPDATE,
                target_path=target_directory / "CLAUDE.md",
                success=False,
                error_message=str(e)
            )

    async def get_parent_directory_status(self, target_directory: Path) -> ParentDirectoryStatus:
        """Get status of a parent directory."""
        return await self._state_manager.get_parent_directory_status(
            target_directory, self._config_manager, self.backups_dir
        )

    async def backup_parent_directory(self, target_directory: Path) -> Optional[Path]:
        """
        Create a backup of a parent directory's CLAUDE.md file.

        Args:
            target_directory: Directory containing file to backup

        Returns:
            Path to backup file or None if failed
        """
        return await self._backup_manager.backup_parent_directory(target_directory, self.backups_dir)

    async def restore_parent_directory(
        self, target_directory: Path, backup_timestamp: Optional[str] = None
    ) -> ParentDirectoryOperation:
        """
        Restore a parent directory from backup.

        Args:
            target_directory: Directory to restore
            backup_timestamp: Specific backup to restore (latest if None)

        Returns:
            ParentDirectoryOperation result
        """
        # Delegate to BackupManager
        operation = await self._backup_manager.restore_from_backup(
            target_directory,
            self.backups_dir,
            backup_timestamp
        )
        
        # Store operation in history if successful
        if operation.success:
            self._state_manager.add_operation(operation)
        
        return operation

    async def validate_parent_directory(self, target_directory: Path) -> ParentDirectoryOperation:
        """Validate a parent directory's template."""
        return await self._validation_manager.validate_parent_directory(
            target_directory, self.managed_directories
        )

    async def list_managed_directories(self) -> List[Dict[str, Any]]:
        """List all managed directories."""
        return await self._state_manager.list_managed_directories(
            self._config_manager, self.get_parent_directory_status
        )

    async def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get operation history."""
        return await self._state_manager.get_operation_history(limit)

    # Subsystem Version Management Methods - delegating to version manager
    # Subsystem Version Management - direct delegation to version manager
    def get_subsystem_versions(self) -> Dict[str, Any]:
        return self._version_manager.get_subsystem_versions()

    def get_subsystem_version(self, subsystem: str) -> Optional[str]:
        return self._version_manager.get_subsystem_version(subsystem)

    async def validate_subsystem_compatibility(self, required_versions: Dict[str, str]) -> Dict[str, Any]:
        return await self._validation_manager.validate_subsystem_compatibility(
            required_versions, self._version_manager.get_subsystem_version
        )

    async def update_subsystem_version(self, subsystem: str, new_version: str) -> bool:
        return await self._version_manager.update_subsystem_version(
            subsystem, new_version,
            lambda file_path: self._backup_manager.create_backup(file_path, self.backups_dir)
        )

    def get_subsystem_version_report(self) -> Dict[str, Any]:
        return self._version_manager.get_subsystem_version_report()

    # Directory operations - delegating to directory operations module
    async def detect_parent_directory_context(self, target_directory: Path) -> ParentDirectoryContext:
        return await self._directory_ops.detect_parent_directory_context(target_directory)

    async def auto_register_parent_directories(
        self, search_paths: List[Path], template_id: str = "parent_directory_claude_md"
    ) -> List[Path]:
        """Automatically register parent directories that should be managed."""
        return await self._directory_ops.auto_register_parent_directories(
            search_paths,
            template_id,
            self.register_parent_directory,
            lambda path, ctx: self._directory_ops.get_default_template_variables(
                path, ctx, self.deployment_context
            )
        )

    # Deduplication - delegating to deduplication manager
    async def _deduplicate_claude_md_files(self) -> List[Tuple[Path, str]]:
        """Deduplicate CLAUDE.md files in parent directory hierarchy."""
        return await self._deduplication_manager.deduplicate_claude_md_files(
            self._template_deployer.is_framework_deployment_template,
            self._template_deployer.extract_claude_md_version,
            self._template_deployer.compare_versions,
            lambda file_path: self._backup_manager.create_backup(file_path, self.backups_dir)
        )

    async def deduplicate_parent_claude_md(self) -> Dict[str, Any]:
        """Public method to manually trigger CLAUDE.md deduplication in parent hierarchy."""
        return await self._deduplication_manager.deduplicate_parent_claude_md(
            self._template_deployer.is_framework_deployment_template,
            self._template_deployer.extract_claude_md_version,
            self._template_deployer.compare_versions,
            lambda file_path: self._backup_manager.create_backup(file_path, self.backups_dir)
        )

    # Helper Methods


    async def _get_framework_template(
        self, template_id: str
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Get template from deployment framework path using the new generator."""
        current_target_file = getattr(self, '_current_target_file', None)
        return await self._template_deployer.get_framework_template(
            template_id, 
            current_target_file,
            self._backup_manager,
            self._log_info_if_not_quiet
        )

    def get_framework_backup_status(self) -> Dict[str, Any]:
        return self._backup_manager.get_framework_backup_status()


# Export all public symbols
__all__ = [
    'ParentDirectoryManager',
    'ParentDirectoryContext',
    'ParentDirectoryStatus',
    'ParentDirectoryOperation',
    'ParentDirectoryAction',
    'ParentDirectoryConfig',
    'DeploymentContext'
]