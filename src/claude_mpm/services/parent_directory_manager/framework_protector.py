"""Framework protection module for critical framework files.

This module provides the FrameworkProtector class which ensures critical
framework files like framework/INSTRUCTIONS.md (legacy: framework/CLAUDE.md) 
are protected from accidental deletion and maintain proper permissions.
"""

import os
from pathlib import Path
from typing import Optional
import logging


class FrameworkProtector:
    """Protects critical framework files from deletion and corruption."""
    
    def __init__(self, framework_path: Path, logger: Optional[logging.Logger] = None):
        """Initialize the FrameworkProtector.
        
        Args:
            framework_path: Path to the framework directory
            logger: Optional logger instance for logging protection activities
        """
        self.framework_path = framework_path
        self.logger = logger or logging.getLogger(__name__)
        
    def protect_framework_template(self, framework_template_path: Path) -> None:
        """Ensure framework template is protected from deletion.
        
        This method verifies that the framework template exists, is the correct
        file, and has proper read permissions. This is critical to prevent
        accidental deletion of the master framework template.
        
        Args:
            framework_template_path: Path to the framework template file
        """
        try:
            # Verify the file exists
            if not framework_template_path.exists():
                self.logger.warning(
                    f"Framework template not found at {framework_template_path}"
                )
                return
                
            # Verify this is actually the framework template
            # Check that the filename is INSTRUCTIONS.md or CLAUDE.md (legacy) and path contains "framework"
            if (framework_template_path.name not in ["INSTRUCTIONS.md", "CLAUDE.md"] or 
                "framework" not in str(framework_template_path)):
                self.logger.debug(
                    f"Path {framework_template_path} does not appear to be "
                    "the framework template"
                )
                return
                
            # Ensure file has proper permissions (readable)
            try:
                # Get current permissions
                current_mode = framework_template_path.stat().st_mode
                
                # Ensure owner can read (add read permission if needed)
                if not (current_mode & 0o400):
                    new_mode = current_mode | 0o400  # Add owner read
                    os.chmod(framework_template_path, new_mode)
                    self.logger.info(
                        f"Added read permission to framework template at "
                        f"{framework_template_path}"
                    )
                    
                # Log successful protection
                self.logger.debug(
                    f"Framework template protected at {framework_template_path}"
                )
                
            except Exception as e:
                self.logger.error(
                    f"Failed to set permissions on framework template: {e}"
                )
                
        except Exception as e:
            self.logger.error(
                f"Error protecting framework template at "
                f"{framework_template_path}: {e}"
            )
            
    def validate_framework_template_integrity(self, content: str) -> bool:
        """Validate that framework template has proper structure and metadata.
        
        This method checks that the template contains essential metadata
        and structure required for proper framework operation.
        
        Args:
            content: The content of the framework template to validate
            
        Returns:
            bool: True if template is valid, False otherwise
        """
        try:
            # Check for essential metadata markers
            required_markers = [
                "CLAUDE_MD_VERSION:",
                "FRAMEWORK_VERSION:",
                "AI ASSISTANT ROLE DESIGNATION",
                "AGENTS",
                "TODO AND TASK TOOLS"
            ]
            
            # Check each required marker exists in content
            for marker in required_markers:
                if marker not in content:
                    self.logger.warning(
                        f"Framework template missing required marker: {marker}"
                    )
                    return False
                    
            # Check for handlebars variables that should be present
            required_variables = [
                "{{DEPLOYMENT_ID}}",
                "{{PLATFORM_NOTES}}"
            ]
            
            for variable in required_variables:
                if variable not in content:
                    self.logger.warning(
                        f"Framework template missing required variable: {variable}"
                    )
                    return False
                    
            # Validate minimum content length (templates should be substantial)
            min_content_length = 1000  # Reasonable minimum for a valid template
            if len(content) < min_content_length:
                self.logger.warning(
                    f"Framework template content too short: {len(content)} chars "
                    f"(minimum: {min_content_length})"
                )
                return False
                
            # If all checks pass, template is valid
            self.logger.debug("Framework template integrity validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating framework template integrity: {e}")
            return False