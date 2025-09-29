"""Loader for packaged installations using importlib.resources."""

import re
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger

# Import resource handling for packaged installations
try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.8 fallback
    try:
        from importlib_resources import files
    except ImportError:
        # Final fallback for development environments
        files = None


class PackagedLoader:
    """Handles loading resources from packaged installations."""

    def __init__(self):
        """Initialize the packaged loader."""
        self.logger = get_logger("packaged_loader")
        self.framework_version: Optional[str] = None
        self.framework_last_modified: Optional[str] = None

    def load_packaged_file(self, filename: str) -> Optional[str]:
        """Load a file from the packaged installation."""
        if not files:
            self.logger.warning("importlib.resources not available")
            return None

        try:
            # Use importlib.resources to load file from package
            agents_package = files("claude_mpm.agents")
            file_path = agents_package / filename

            if file_path.is_file():
                content = file_path.read_text()
                self.logger.info(f"Loaded {filename} from package")
                return content
            self.logger.warning(f"File {filename} not found in package")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load {filename} from package: {e}")
            return None

    def load_packaged_file_fallback(self, filename: str, resources) -> Optional[str]:
        """Load a file from the packaged installation using importlib.resources fallback."""
        try:
            # Try different resource loading methods
            try:
                # Method 1: resources.read_text (Python 3.9+)
                content = resources.read_text("claude_mpm.agents", filename)
                self.logger.info(f"Loaded {filename} from package using read_text")
                return content
            except AttributeError:
                # Method 2: resources.files (Python 3.9+)
                agents_files = resources.files("claude_mpm.agents")
                file_path = agents_files / filename
                if file_path.is_file():
                    content = file_path.read_text()
                    self.logger.info(f"Loaded {filename} from package using files")
                    return content
                self.logger.warning(f"File {filename} not found in package")
                return None
        except Exception as e:
            self.logger.error(
                f"Failed to load {filename} from package with fallback: {e}"
            )
            return None

    def extract_metadata_from_content(self, content: str, filename: str) -> None:
        """Extract metadata from content string.

        Args:
            content: Content to extract metadata from
            filename: Filename for context
        """
        # Extract version
        version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
        if version_match and "INSTRUCTIONS.md" in filename:
            self.framework_version = version_match.group(1)
            self.logger.info(f"Framework version: {self.framework_version}")

        # Extract timestamp
        timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)
        if timestamp_match and "INSTRUCTIONS.md" in filename:
            self.framework_last_modified = timestamp_match.group(1).strip()
            self.logger.info(f"Last modified: {self.framework_last_modified}")

    def load_framework_content(self, content: Dict[str, Any]) -> None:
        """Load framework content from packaged installation.

        Args:
            content: Dictionary to update with loaded content
        """
        if not files:
            self.logger.warning(
                "importlib.resources not available, cannot load packaged framework"
            )
            self.logger.debug(f"files variable is: {files}")
            # Try alternative import methods
            try:
                from importlib import resources

                self.logger.info("Using importlib.resources as fallback")
                self.load_framework_content_fallback(content, resources)
                return
            except ImportError:
                self.logger.error(
                    "No importlib.resources available, using minimal framework"
                )
                return

        try:
            # Try new consolidated PM_INSTRUCTIONS.md first
            pm_instructions_content = self.load_packaged_file("PM_INSTRUCTIONS.md")
            if pm_instructions_content:
                content["framework_instructions"] = pm_instructions_content
                content["loaded"] = True
                self.logger.info("Loaded consolidated PM_INSTRUCTIONS.md from package")
                # Extract and store version/timestamp metadata
                self.extract_metadata_from_content(
                    pm_instructions_content, "PM_INSTRUCTIONS.md"
                )
            else:
                # Fall back to legacy INSTRUCTIONS.md
                instructions_content = self.load_packaged_file("INSTRUCTIONS.md")
                if instructions_content:
                    content["framework_instructions"] = instructions_content
                    content["loaded"] = True
                    self.logger.warning("Using legacy INSTRUCTIONS.md from package")
                    # Extract and store version/timestamp metadata
                    self.extract_metadata_from_content(
                        instructions_content, "INSTRUCTIONS.md"
                    )

            if self.framework_version:
                content["instructions_version"] = self.framework_version
                content["version"] = self.framework_version
            if self.framework_last_modified:
                content["instructions_last_modified"] = self.framework_last_modified

            # Load BASE_PM.md
            base_pm_content = self.load_packaged_file("BASE_PM.md")
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

            # Load WORKFLOW.md
            workflow_content = self.load_packaged_file("WORKFLOW.md")
            if workflow_content:
                content["workflow_instructions"] = workflow_content
                content["workflow_instructions_level"] = "system"

            # Load MEMORY.md
            memory_content = self.load_packaged_file("MEMORY.md")
            if memory_content:
                content["memory_instructions"] = memory_content
                content["memory_instructions_level"] = "system"

        except Exception as e:
            self.logger.error(f"Failed to load packaged framework content: {e}")

    def load_framework_content_fallback(
        self, content: Dict[str, Any], resources
    ) -> None:
        """Load framework content using importlib.resources fallback.

        Args:
            content: Dictionary to update with loaded content
            resources: The importlib.resources module
        """
        try:
            # Try new consolidated PM_INSTRUCTIONS.md first
            pm_instructions_content = self.load_packaged_file_fallback(
                "PM_INSTRUCTIONS.md", resources
            )
            if pm_instructions_content:
                content["framework_instructions"] = pm_instructions_content
                content["loaded"] = True
                self.logger.info("Loaded consolidated PM_INSTRUCTIONS.md via fallback")
                # Extract and store version/timestamp metadata
                self.extract_metadata_from_content(
                    pm_instructions_content, "PM_INSTRUCTIONS.md"
                )
            else:
                # Fall back to legacy INSTRUCTIONS.md
                instructions_content = self.load_packaged_file_fallback(
                    "INSTRUCTIONS.md", resources
                )
                if instructions_content:
                    content["framework_instructions"] = instructions_content
                    content["loaded"] = True
                    self.logger.warning("Using legacy INSTRUCTIONS.md via fallback")
                    # Extract and store version/timestamp metadata
                    self.extract_metadata_from_content(
                        instructions_content, "INSTRUCTIONS.md"
                    )

            if self.framework_version:
                content["instructions_version"] = self.framework_version
                content["version"] = self.framework_version
            if self.framework_last_modified:
                content["instructions_last_modified"] = self.framework_last_modified

            # Load BASE_PM.md
            base_pm_content = self.load_packaged_file_fallback("BASE_PM.md", resources)
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

            # Load WORKFLOW.md
            workflow_content = self.load_packaged_file_fallback(
                "WORKFLOW.md", resources
            )
            if workflow_content:
                content["workflow_instructions"] = workflow_content
                content["workflow_instructions_level"] = "system"

            # Load MEMORY.md
            memory_content = self.load_packaged_file_fallback("MEMORY.md", resources)
            if memory_content:
                content["memory_instructions"] = memory_content
                content["memory_instructions_level"] = "system"

        except Exception as e:
            self.logger.error(
                f"Failed to load packaged framework content with fallback: {e}"
            )
