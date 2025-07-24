#!/usr/bin/env python3
"""
Parent Directory Operations - Handles directory context detection and registration
================================================================================

This module manages parent directory context detection, auto-registration,
and template variable generation.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging


class ParentDirectoryContext(Enum):
    """Context types for parent directory management."""
    DEPLOYMENT_ROOT = "deployment_root"
    PROJECT_COLLECTION = "project_collection"
    WORKSPACE_ROOT = "workspace_root"
    USER_HOME = "user_home"
    CUSTOM = "custom"


class ParentDirectoryOperations:
    """Manages parent directory detection and operations."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Parent Directory Operations.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)

    async def detect_parent_directory_context(
        self, target_directory: Path
    ) -> ParentDirectoryContext:
        """
        Detect the context of a parent directory.

        Args:
            target_directory: Directory to analyze

        Returns:
            ParentDirectoryContext enum value
        """
        try:
            # Check if it's the user home directory
            if target_directory == Path.home():
                return ParentDirectoryContext.USER_HOME

            # Check if it contains a deployment (has claude-multiagent-pm subdirectory)
            if (target_directory / "claude-multiagent-pm").exists():
                return ParentDirectoryContext.DEPLOYMENT_ROOT

            # Check if it contains multiple projects
            subdirs = [d for d in target_directory.iterdir() if d.is_dir()]
            project_indicators = [".git", "package.json", "pyproject.toml", "Cargo.toml"]

            project_count = 0
            for subdir in subdirs:
                if any((subdir / indicator).exists() for indicator in project_indicators):
                    project_count += 1

            if project_count > 1:
                return ParentDirectoryContext.PROJECT_COLLECTION

            # Check if it's a workspace root
            workspace_indicators = [".vscode", ".idea", "workspace.json"]
            if any((target_directory / indicator).exists() for indicator in workspace_indicators):
                return ParentDirectoryContext.WORKSPACE_ROOT

            # Default to custom
            return ParentDirectoryContext.CUSTOM

        except Exception as e:
            self.logger.error(
                f"Failed to detect parent directory context for {target_directory}: {e}"
            )
            return ParentDirectoryContext.CUSTOM

    async def auto_register_parent_directories(
        self,
        search_paths: List[Path],
        template_id: str,
        register_func,
        get_default_variables_func
    ) -> List[Path]:
        """
        Automatically register parent directories that should be managed.

        Args:
            search_paths: Paths to search for parent directories
            template_id: Template to use for auto-registration
            register_func: Function to register directory
            get_default_variables_func: Function to get default template variables

        Returns:
            List of registered directories
        """
        try:
            registered_directories = []

            for search_path in search_paths:
                if not search_path.exists() or not search_path.is_dir():
                    continue

                # Check if this directory should be managed
                context = await self.detect_parent_directory_context(search_path)

                # Skip user home directory unless explicitly configured
                if context == ParentDirectoryContext.USER_HOME:
                    continue

                # Auto-register if it looks like a deployment root or project collection
                if context in [
                    ParentDirectoryContext.DEPLOYMENT_ROOT,
                    ParentDirectoryContext.PROJECT_COLLECTION,
                ]:
                    success = await register_func(
                        search_path,
                        context,
                        template_id,
                        get_default_variables_func(search_path, context),
                    )

                    if success:
                        registered_directories.append(search_path)
                        self.logger.info(f"Auto-registered parent directory: {search_path}")

            return registered_directories

        except Exception as e:
            self.logger.error(f"Failed to auto-register parent directories: {e}")
            return []

    def get_default_template_variables(
        self,
        target_directory: Path,
        context: ParentDirectoryContext,
        deployment_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get default template variables for a directory."""
        variables = {
            "DIRECTORY_PATH": str(target_directory),
            "DIRECTORY_NAME": target_directory.name,
            "CONTEXT": context.value,
            "TIMESTAMP": datetime.now().isoformat(),
            "PLATFORM": os.name,
        }

        # Add deployment-specific variables if available
        if deployment_context:
            variables.update(
                {
                    "DEPLOYMENT_TYPE": deployment_context.get("strategy", "unknown"),
                    "DEPLOYMENT_PLATFORM": deployment_context.get("config", {}).get(
                        "platform", "unknown"
                    ),
                }
            )

        return variables

    def get_platform_notes(self) -> str:
        """
        Get platform-specific notes for the framework template.
        
        Returns:
            Platform-specific notes string
        """
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            return "Windows users may need to use 'python' instead of 'python3' depending on installation."
        elif system == 'darwin':
            return "macOS users should ensure python3 is installed via Homebrew or official Python installer."
        elif system == 'linux':
            return "Linux users may need to install python3 via their package manager if not present."
        else:
            return f"Platform-specific configuration may be required for {system}."