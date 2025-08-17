"""
Header section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class HeaderGenerator(BaseSectionGenerator):
    """Generates the header section with version metadata."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the header section."""
        version = data.get("version", f"{self.framework_version}-001")
        timestamp = self.get_timestamp()
        content_hash = data.get("content_hash", "pending")

        return f"""# Claude PM Framework Configuration - Deployment

<!--
CLAUDE_MD_VERSION: {version}
FRAMEWORK_VERSION: {self.framework_version}
DEPLOYMENT_DATE: {timestamp}
LAST_UPDATED: {timestamp}
CONTENT_HASH: {content_hash}
-->"""
