"""Agent Configuration Manager Service

This service handles agent configuration management including base agent loading,
tool configuration, and agent-specific settings.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.logging_config import get_logger


class AgentConfigurationManager:
    """Service for managing agent configuration and settings.

    This service handles:
    - Base agent loading and parsing
    - Tool configuration for different agent types
    - Agent-specific configuration management
    - Source tier determination and configuration
    """

    def __init__(self, base_agent_path: Optional[Path] = None):
        """Initialize the agent configuration manager.

        Args:
            base_agent_path: Path to the base agent file
        """
        self.logger = get_logger(__name__)
        self.base_agent_path = base_agent_path
        self._base_agent_cache = None  # Cache for base agent data

    def load_base_agent(self) -> Tuple[dict, tuple]:
        """
        Load base agent configuration and version.

        Returns:
            Tuple of (base_agent_data, base_agent_version)
        """
        # Return cached data if available
        if self._base_agent_cache is not None:
            return self._base_agent_cache

        if not self.base_agent_path or not self.base_agent_path.exists():
            self.logger.warning(f"Base agent file not found: {self.base_agent_path}")
            # Return minimal default base agent
            default_base_agent = {
                "name": "base-agent",
                "description": "Base agent configuration",
                "version": "1.0.0",
                "instructions": "You are a helpful AI assistant.",
                "tools": ["Read", "Write", "Edit"],
            }
            self._base_agent_cache = (default_base_agent, (1, 0, 0))
            return self._base_agent_cache

        try:
            # Read base agent file
            base_agent_content = self.base_agent_path.read_text()

            # Parse base agent data
            base_agent_data = self._parse_base_agent_content(base_agent_content)

            # Extract version information
            base_agent_version = self._extract_base_agent_version(base_agent_data)

            # Cache the result
            self._base_agent_cache = (base_agent_data, base_agent_version)

            self.logger.info(f"Loaded base agent from {self.base_agent_path}")
            return self._base_agent_cache

        except Exception as e:
            self.logger.error(f"Failed to load base agent: {e}")
            # Return minimal default on error
            default_base_agent = {
                "name": "base-agent",
                "description": "Base agent configuration (fallback)",
                "version": "1.0.0",
                "instructions": "You are a helpful AI assistant.",
                "tools": ["Read", "Write", "Edit"],
            }
            self._base_agent_cache = (default_base_agent, (1, 0, 0))
            return self._base_agent_cache

    def get_agent_tools(self, agent_name: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Get appropriate tools for an agent based on its type and metadata.

        Args:
            agent_name: Name of the agent
            metadata: Agent metadata

        Returns:
            List of tool names
        """
        # Base tools all agents should have
        base_tools = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Grep",
            "Glob",
            "LS",
            "TodoWrite",
        ]

        # Agent-specific tools based on name patterns
        agent_tools = {
            # Security agents
            "security": [*base_tools, "SecurityScan", "VulnerabilityCheck"],
            "sec": [*base_tools, "SecurityScan", "VulnerabilityCheck"],
            # QA and testing agents
            "qa": [*base_tools, "TestRunner", "CodeAnalysis"],
            "test": [*base_tools, "TestRunner", "CodeAnalysis"],
            "testing": [*base_tools, "TestRunner", "CodeAnalysis"],
            # Documentation agents
            "doc": [*base_tools, "DocumentGenerator", "MarkdownProcessor"],
            "docs": [*base_tools, "DocumentGenerator", "MarkdownProcessor"],
            "documentation": [*base_tools, "DocumentGenerator", "MarkdownProcessor"],
            # Data processing agents
            "data": [*base_tools, "DataProcessor", "CSVHandler"],
            "analytics": [*base_tools, "DataProcessor", "CSVHandler"],
            # Operations agents
            "ops": [*base_tools, "SystemMonitor", "LogAnalyzer"],
            "operations": [*base_tools, "SystemMonitor", "LogAnalyzer"],
            "monitor": [*base_tools, "SystemMonitor", "LogAnalyzer"],
            # Research agents
            "research": [*base_tools, "WebSearch", "DataCollector"],
            "analysis": [*base_tools, "WebSearch", "DataCollector"],
        }

        # Check agent name for tool assignment
        agent_name_lower = agent_name.lower()
        for pattern, tools in agent_tools.items():
            if pattern in agent_name_lower:
                return tools

        # Check metadata for specializations
        specializations = metadata.get("specializations", [])
        for spec in specializations:
            spec_lower = spec.lower()
            if spec_lower in agent_tools:
                return agent_tools[spec_lower]

        # Return default tools with web search and bash
        return [*base_tools, "Bash", "WebSearch"]

    def get_agent_specific_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get agent-specific configuration based on agent type.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with agent-specific configuration
        """
        agent_name_lower = agent_name.lower()

        # Default configuration
        config = {
            "timeout": 300,  # 5 minutes
            "max_iterations": 10,
            "memory_limit": "1GB",
            "parallel_execution": False,
        }

        # Agent-specific configurations
        if "security" in agent_name_lower or "sec" in agent_name_lower:
            config.update(
                {
                    "timeout": 600,  # Security scans may take longer
                    "max_iterations": 20,
                    "security_mode": True,
                    "audit_logging": True,
                }
            )

        elif "qa" in agent_name_lower or "test" in agent_name_lower:
            config.update(
                {
                    "timeout": 900,  # Tests may take longer
                    "max_iterations": 15,
                    "test_mode": True,
                    "coverage_reporting": True,
                }
            )

        elif "data" in agent_name_lower or "analytics" in agent_name_lower:
            config.update(
                {
                    "timeout": 1200,  # Data processing may take longer
                    "memory_limit": "2GB",
                    "parallel_execution": True,
                    "data_processing_mode": True,
                }
            )

        elif "ops" in agent_name_lower or "monitor" in agent_name_lower:
            config.update(
                {
                    "timeout": 180,  # Operations should be quick
                    "max_iterations": 5,
                    "monitoring_mode": True,
                    "alert_threshold": "warning",
                }
            )

        elif "research" in agent_name_lower:
            config.update(
                {
                    "timeout": 1800,  # Research may take very long
                    "max_iterations": 25,
                    "research_mode": True,
                    "web_search_enabled": True,
                }
            )

        return config

    def determine_source_tier(self) -> str:
        """
        Determine the source tier for agent deployment.

        Returns:
            Source tier string ("system", "user", or "project")
        """
        # For now, this is a simple implementation
        # In the future, this could be enhanced with more sophisticated logic

        # Check if we're in a project context
        current_dir = Path.cwd()

        # Look for project indicators
        project_indicators = [
            ".git",
            "package.json",
            "requirements.txt",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
        ]

        for indicator in project_indicators:
            if (current_dir / indicator).exists():
                return "project"

        # Check for user-specific configuration
        user_config_dir = Path.home() / ".claude"
        if user_config_dir.exists():
            return "user"

        # Default to system tier
        return "system"

    def _parse_base_agent_content(self, content: str) -> dict:
        """
        Parse base agent content from various formats.

        Args:
            content: Base agent file content

        Returns:
            Parsed base agent data
        """
        # Try to parse as JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to parse as Markdown with YAML frontmatter
        if content.strip().startswith("---"):
            try:
                import yaml

                # Split frontmatter and content
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    markdown_content = parts[2].strip()

                    # Parse YAML frontmatter
                    data = yaml.safe_load(frontmatter)

                    # Add markdown content as instructions
                    if markdown_content:
                        data["instructions"] = markdown_content

                    return data
            except Exception:
                pass

        # Fallback: treat as plain text instructions
        return {
            "name": "base-agent",
            "description": "Base agent configuration",
            "version": "1.0.0",
            "instructions": content.strip(),
            "tools": ["Read", "Write", "Edit"],
        }

    def _extract_base_agent_version(self, base_agent_data: dict) -> tuple:
        """
        Extract version from base agent data.

        Args:
            base_agent_data: Base agent data dictionary

        Returns:
            Version tuple (major, minor, patch)
        """
        version_str = base_agent_data.get("version", "1.0.0")

        # Parse semantic version
        try:
            import re

            match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(version_str))
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except Exception:
            pass

        # Fallback to default version
        return (1, 0, 0)

    def clear_cache(self):
        """Clear the base agent cache."""
        self._base_agent_cache = None
        self.logger.debug("Base agent cache cleared")

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.

        Returns:
            Dictionary with configuration summary
        """
        base_agent_data, base_agent_version = self.load_base_agent()

        return {
            "base_agent_path": (
                str(self.base_agent_path) if self.base_agent_path else None
            ),
            "base_agent_loaded": self._base_agent_cache is not None,
            "base_agent_version": base_agent_version,
            "base_agent_name": base_agent_data.get("name", "unknown"),
            "source_tier": self.determine_source_tier(),
            "cache_status": "loaded" if self._base_agent_cache else "empty",
        }
