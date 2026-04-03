"""Manifest Fetcher — reads and parses agent version metadata from .md and .json files.

Single responsibility: given a template file path, return the version string (or None).
"""

import json
from pathlib import Path

import yaml

from claude_mpm.core.logging_config import get_logger


class ManifestFetcher:
    """Reads version information from agent template files.

    Supports two formats:
    - Markdown (.md) with YAML frontmatter  (``version: 1.2.3`` inside ``---`` fences)
    - JSON (.json) with ``agent_version`` / ``version`` / ``metadata.version`` fields
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def read_template_version(self, template_path: Path) -> str | None:
        """Read version from a template file (supports both .md and .json formats).

        For .md files: Extract version from YAML frontmatter
        For .json files: Extract version from JSON structure

        Args:
            template_path: Path to template file

        Returns:
            Version string or None if version cannot be extracted
        """
        try:
            if template_path.suffix == ".md":
                # Parse markdown with YAML frontmatter
                content = template_path.read_text()

                # Extract YAML frontmatter (between --- markers)
                if not content.strip().startswith("---"):
                    return None

                parts = content.split("---", 2)
                if len(parts) < 3:
                    return None

                # Parse YAML frontmatter
                frontmatter = yaml.safe_load(parts[1])
                if not frontmatter:
                    return None

                # Extract version from frontmatter
                version = frontmatter.get("version")
                return version if version else None

            if template_path.suffix == ".json":
                # Parse JSON template
                template_data = json.loads(template_path.read_text())
                metadata = template_data.get("metadata", {})
                version = (
                    template_data.get("agent_version")
                    or template_data.get("version")
                    or metadata.get("version")
                )
                return version if version else None

            self.logger.warning(
                f"Unknown template format: {template_path.suffix} for {template_path.name}"
            )
            return None

        except yaml.YAMLError as e:
            self.logger.warning(
                f"Invalid YAML frontmatter in {template_path.name}: {e}"
            )
            return None
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON in {template_path.name}: {e}")
            return None
        except Exception as e:
            self.logger.warning(
                f"Error reading template version from {template_path.name}: {e}"
            )
            return None
