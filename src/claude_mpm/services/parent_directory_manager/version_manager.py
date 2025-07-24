#!/usr/bin/env python3
"""
Version Manager - Handles subsystem version tracking and management
================================================================================

This module manages subsystem version tracking, loading, updating, and reporting
for the parent directory manager service.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging


class VersionManager:
    """Manages subsystem version tracking and operations."""

    def __init__(
        self,
        framework_path: Path,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Version Manager.

        Args:
            framework_path: Path to framework
            logger: Logger instance to use
        """
        self.framework_path = framework_path
        self.logger = logger or logging.getLogger(__name__)
        self.subsystem_versions: Dict[str, Dict[str, Any]] = {}
        
        # Define subsystem version files
        self.subsystem_files = {
            "health": "HEALTH_VERSION"
        }

    async def load_subsystem_versions(self) -> None:
        """Load subsystem versions from version files."""
        try:
            for subsystem, filename in self.subsystem_files.items():
                version_file = self.framework_path / filename
                if version_file.exists():
                    try:
                        version = version_file.read_text().strip()
                        self.subsystem_versions[subsystem] = {
                            "version": version,
                            "file_path": str(version_file),
                            "last_checked": datetime.now().isoformat()
                        }
                        self.logger.debug(f"Loaded {subsystem} version: {version}")
                    except Exception as e:
                        self.logger.error(f"Failed to read {subsystem} version from {version_file}: {e}")
                        self.subsystem_versions[subsystem] = {
                            "version": "unknown",
                            "file_path": str(version_file),
                            "error": str(e),
                            "last_checked": datetime.now().isoformat()
                        }
                else:
                    self.logger.warning(f"Subsystem version file not found: {version_file}")
                    self.subsystem_versions[subsystem] = {
                        "version": "not_found",
                        "file_path": str(version_file),
                        "last_checked": datetime.now().isoformat()
                    }

            self.logger.info(f"Loading subsystem versions...")

        except Exception as e:
            self.logger.error(f"Failed to load subsystem versions: {e}")

    def get_subsystem_versions(self) -> Dict[str, Any]:
        """
        Get all detected subsystem versions.

        Returns:
            Dictionary with subsystem version information
        """
        return {
            "framework_path": str(self.framework_path),
            "subsystems": self.subsystem_versions.copy(),
            "detection_timestamp": datetime.now().isoformat()
        }

    def get_subsystem_version(self, subsystem: str) -> Optional[str]:
        """
        Get version for a specific subsystem.

        Args:
            subsystem: Name of the subsystem

        Returns:
            Version string or None if not found
        """
        version_info = self.subsystem_versions.get(subsystem, {})
        version = version_info.get("version")
        
        # Return None for error states
        if version in ["unknown", "not_found"]:
            return None
            
        return version

    async def update_subsystem_version(
        self,
        subsystem: str,
        new_version: str,
        create_backup_func
    ) -> bool:
        """
        Update a subsystem version file.

        Args:
            subsystem: Name of the subsystem
            new_version: New version string
            create_backup_func: Function to create backup of version file

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            filename = self.subsystem_files.get(subsystem)
            if not filename:
                self.logger.error(f"Unknown subsystem: {subsystem}")
                return False

            version_file = self.framework_path / filename
            
            # Backup existing version file if it exists
            if version_file.exists():
                backup_path = await create_backup_func(version_file)
                if backup_path:
                    self.logger.info(f"Created backup of {filename}: {backup_path}")

            # Write new version
            version_file.write_text(new_version.strip())
            
            # Update in-memory tracking
            self.subsystem_versions[subsystem] = {
                "version": new_version,
                "file_path": str(version_file),
                "last_updated": datetime.now().isoformat()
            }

            self.logger.info(f"Updated {subsystem} version to: {new_version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update {subsystem} version to {new_version}: {e}")
            return False

    def get_subsystem_version_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive subsystem version report.

        Returns:
            Dictionary with detailed version information
        """
        try:
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "framework_path": str(self.framework_path),
                "subsystem_count": len(self.subsystem_versions),
                "subsystems": {},
                "summary": {
                    "total": 0,
                    "found": 0,
                    "missing": 0,
                    "errors": 0
                }
            }

            for subsystem, info in self.subsystem_versions.items():
                version = info.get("version", "unknown")
                status = "found"
                
                if version == "not_found":
                    status = "missing"
                    report["summary"]["missing"] += 1
                elif version == "unknown" or "error" in info:
                    status = "error"
                    report["summary"]["errors"] += 1
                else:
                    report["summary"]["found"] += 1
                
                report["summary"]["total"] += 1
                
                report["subsystems"][subsystem] = {
                    "version": version,
                    "status": status,
                    "file_path": info.get("file_path"),
                    "last_checked": info.get("last_checked"),
                    "error": info.get("error")
                }

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate subsystem version report: {e}")
            return {
                "error": str(e),
                "report_timestamp": datetime.now().isoformat()
            }

    def get_version_report(self) -> Dict[str, Any]:
        """
        Get a simple version report (for compatibility with VersionControlHelper).
        
        Returns:
            Dictionary with subsystem versions
        """
        return {
            "subsystems": {
                subsystem: info.get("version", "unknown")
                for subsystem, info in self.subsystem_versions.items()
            }
        }