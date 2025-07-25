#!/usr/bin/env python3
"""
Validation Manager - Handles validation and compatibility checks
================================================================================

This module manages validation of parent directories, subsystem compatibility,
and version comparisons.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging

from .state_manager import ParentDirectoryOperation, ParentDirectoryAction
from ...utils.path_operations import path_ops


class ValidationManager:
    """Manages validation and compatibility checks."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Validation Manager.

        Args:
            logger: Logger instance to use
        """
        self.logger = logger or logging.getLogger(__name__)

    async def validate_parent_directory(
        self,
        target_directory: Path,
        managed_directories: Dict[str, Any],
        template_manager: Optional[Any] = None
    ) -> ParentDirectoryOperation:
        """
        Validate a parent directory's template.

        Args:
            target_directory: Directory to validate
            managed_directories: Dictionary of managed directories
            template_manager: Template manager instance (optional)

        Returns:
            ParentDirectoryOperation result
        """
        try:
            # Check for INSTRUCTIONS.md first, then CLAUDE.md
            target_file = target_directory / "INSTRUCTIONS.md"
            if not path_ops.validate_exists(target_file):
                target_file = target_directory / "CLAUDE.md"
            
            if not path_ops.validate_exists(target_file):
                return ParentDirectoryOperation(
                    action=ParentDirectoryAction.VALIDATE,
                    target_path=target_file,
                    success=False,
                    error_message="INSTRUCTIONS.md/CLAUDE.md file not found",
                )

            # Check if managed
            directory_key = str(target_directory)
            if directory_key not in managed_directories:
                return ParentDirectoryOperation(
                    action=ParentDirectoryAction.VALIDATE,
                    target_path=target_file,
                    success=True,
                    warnings=["Directory not managed by Parent Directory Manager"],
                )

            config = managed_directories[directory_key]

            # Validate template if template manager available
            validation_errors = []
            validation_warnings = []

            # template_manager removed - use Claude Code Task Tool instead
            rendered_content = None

            if rendered_content:
                # Compare with actual content
                actual_content = path_ops.safe_read(target_file)
                if not actual_content:
                    return ParentDirectoryOperation(
                        action=ParentDirectoryAction.VALIDATE,
                        target_path=target_file,
                        success=False,
                        error_message="Failed to read file content",
                    )

                if actual_content != rendered_content:
                    validation_warnings.append("Content differs from expected template output")
            else:
                validation_errors.append("Failed to render template for validation")

            # Check file permissions
            if not os.access(target_file, os.R_OK):
                validation_errors.append("File is not readable")

            if not os.access(target_file, os.W_OK):
                validation_warnings.append("File is not writable")

            # Create operation result
            operation = ParentDirectoryOperation(
                action=ParentDirectoryAction.VALIDATE,
                target_path=target_file,
                success=len(validation_errors) == 0,
                template_id=config.template_id,
                error_message="; ".join(validation_errors) if validation_errors else None,
                warnings=validation_warnings,
            )

            return operation

        except Exception as e:
            self.logger.error(f"Failed to validate parent directory {target_directory}: {e}")
            return ParentDirectoryOperation(
                action=ParentDirectoryAction.VALIDATE,
                # Try to determine which file would be used
                target_file = target_directory / "INSTRUCTIONS.md"
                if not path_ops.validate_exists(target_file):
                    target_file = target_directory / "CLAUDE.md"
                return ParentDirectoryOperation(
                    action=ParentDirectoryAction.VALIDATE,
                    target_path=target_file,
                success=False,
                    success=False,
                    error_message=str(e),
                )

    async def validate_subsystem_compatibility(
        self,
        required_versions: Dict[str, str],
        get_subsystem_version_func
    ) -> Dict[str, Any]:
        """
        Validate subsystem version compatibility against requirements.

        Args:
            required_versions: Dictionary of subsystem -> required version
            get_subsystem_version_func: Function to get current subsystem version

        Returns:
            Validation results with compatibility status
        """
        try:
            results = {
                "compatible": True,
                "validation_timestamp": datetime.now().isoformat(),
                "subsystem_checks": {}
            }

            for subsystem, required_version in required_versions.items():
                current_version = get_subsystem_version_func(subsystem)
                
                check_result = {
                    "subsystem": subsystem,
                    "required_version": required_version,
                    "current_version": current_version,
                    "compatible": False,
                    "status": "unknown"
                }

                if current_version is None or current_version in ["unknown", "not_found"]:
                    check_result["status"] = "missing"
                    results["compatible"] = False
                elif current_version == required_version:
                    check_result["compatible"] = True
                    check_result["status"] = "exact_match"
                else:
                    # Try version comparison for compatibility
                    try:
                        comparison = self.compare_subsystem_versions(current_version, required_version)
                        if comparison >= 0:
                            check_result["compatible"] = True
                            check_result["status"] = "compatible" if comparison > 0 else "exact_match"
                        else:
                            check_result["status"] = "outdated"
                            results["compatible"] = False
                    except Exception as comp_error:
                        check_result["status"] = "comparison_failed"
                        check_result["error"] = str(comp_error)
                        results["compatible"] = False

                results["subsystem_checks"][subsystem] = check_result

            return results

        except Exception as e:
            self.logger.error(f"Failed to validate subsystem compatibility: {e}")
            return {
                "compatible": False,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat()
            }

    def compare_subsystem_versions(self, version1: str, version2: str) -> int:
        """
        Compare two subsystem version strings.
        Supports serial number format (001, 002, etc.).

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        try:
            # Handle serial number format (001, 002, etc.)
            if version1.isdigit() and version2.isdigit():
                v1_num = int(version1)
                v2_num = int(version2)
                if v1_num < v2_num:
                    return -1
                elif v1_num > v2_num:
                    return 1
                else:
                    return 0
            
            # Handle semantic versioning (x.y.z)
            if "." in version1 and "." in version2:
                v1_parts = [int(x) for x in version1.split(".")]
                v2_parts = [int(x) for x in version2.split(".")]
                
                # Pad shorter version with zeros
                max_len = max(len(v1_parts), len(v2_parts))
                v1_parts.extend([0] * (max_len - len(v1_parts)))
                v2_parts.extend([0] * (max_len - len(v2_parts)))
                
                for i in range(max_len):
                    if v1_parts[i] < v2_parts[i]:
                        return -1
                    elif v1_parts[i] > v2_parts[i]:
                        return 1
                
                return 0
            
            # String comparison fallback
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Failed to compare subsystem versions {version1} vs {version2}: {e}")
            # If comparison fails, assume versions are different
            return -1 if version1 != version2 else 0

    def validate_framework_template_integrity(self, framework_path: Path) -> bool:
        """
        Validate that the framework template exists and has expected content.
        
        Args:
            framework_path: Path to framework

        Returns:
            True if framework template is valid, False otherwise
        """
        try:
            # Try INSTRUCTIONS.md first, then fall back to CLAUDE.md
            framework_template_path = framework_path / "agents" / "INSTRUCTIONS.md"
            if not path_ops.validate_exists(framework_template_path):
                framework_template_path = framework_path / "agents" / "CLAUDE.md"
            
            if not path_ops.validate_exists(framework_template_path):
                self.logger.error(f"Framework template does not exist: {framework_template_path}")
                return False
            
            if not path_ops.validate_is_file(framework_template_path):
                self.logger.error(f"Framework template path is not a file: {framework_template_path}")
                return False
            
            # Read and validate content
            content = path_ops.safe_read(framework_template_path)
            if not content:
                self.logger.error(f"Failed to read framework template at {framework_template_path}")
                return False
            
            if len(content.strip()) == 0:
                self.logger.error(f"Framework template is empty: {framework_template_path}")
                return False
            
            # Check for critical content markers
            critical_markers = [
                "AI ASSISTANT ROLE DESIGNATION",
                "CLAUDE_MD_VERSION:",
                "Framework Context"
            ]
            
            missing_critical = [marker for marker in critical_markers if marker not in content]
            
            if missing_critical:
                self.logger.error(f"Framework template missing critical content: {missing_critical}")
                return False
            
            self.logger.debug(f"Framework template integrity verified: {framework_template_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate framework template integrity: {e}")
            return False

    async def validate_deployment_context(
        self,
        deployment_aware: bool,
        dependency_manager: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate deployment context using CMPM-101.
        
        Args:
            deployment_aware: Whether to check deployment context
            dependency_manager: Dependency manager instance

        Returns:
            Deployment context or None
        """
        try:
            if not deployment_aware:
                return None

            # Use dependency manager to get deployment context
            # dependency_manager removed - use Claude Code Task Tool instead
            deployment_config = None
            if deployment_config:
                self.logger.info(
                    f"Deployment context validated: {deployment_config.get('strategy', 'unknown')}"
                )
                return deployment_config
            else:
                self.logger.warning("No deployment context available - dependency manager removed")
                return None

        except Exception as e:
            self.logger.error(f"Failed to validate deployment context: {e}")
            return None

    def should_skip_deployment(
        self, 
        target_file: Path, 
        template_content: str, 
        force: bool,
        template_deployer
    ) -> Tuple[bool, Optional[str], bool]:
        """
        Check if deployment should be skipped based on file type and version comparison.
        
        Args:
            target_file: Target file path
            template_content: Template content to deploy
            force: Force deployment flag
            template_deployer: Template deployer instance
            
        Returns:
            Tuple of (should_skip, reason, is_permanent_protection)
        """
        should_skip, reason = template_deployer.should_skip_deployment(
            target_file, template_content, force
        )
        
        # Check for permanent protection
        is_permanent_protection = False
        if path_ops.validate_exists(target_file) and should_skip:
            existing_content = path_ops.safe_read(target_file)
            if not existing_content:
                return False, "Failed to read existing file content"
            if not template_deployer.is_framework_deployment_template(existing_content):
                is_permanent_protection = True
                reason = "Existing file is not a framework deployment template"
        
        return should_skip, reason, is_permanent_protection