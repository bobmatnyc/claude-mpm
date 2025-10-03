#!/usr/bin/env python3
"""
Memory Template Generator
========================

Generates project-specific memory templates for agents based on project analysis.

This module provides:
- Project-specific memory template creation
- Section generation based on project characteristics
- Domain-specific knowledge starters
- Fallback templates when project analysis fails
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from claude_mpm.core.config import Config


class MemoryTemplateGenerator:
    """Generates project-specific memory templates for agents.

    WHY: Instead of generic templates, agents need project-specific knowledge
    from the start. This class creates simple memory templates that agents
    can populate as they learn about the project.
    """

    REQUIRED_SECTIONS = [
        "Project Architecture",
        "Implementation Guidelines",
        "Common Mistakes to Avoid",
        "Current Technical Context",
    ]

    def __init__(self, config: Config, working_directory: Path):
        """Initialize the template generator.

        Args:
            config: Configuration object
            working_directory: Working directory path
        """
        self.config = config
        self.working_directory = working_directory
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create_default_memory(self, agent_id: str, limits: Dict[str, Any]) -> str:
        """Create basic memory template for agent.

        Args:
            agent_id: The agent identifier
            limits: Memory limits for this agent

        Returns:
            str: The basic memory template content
        """
        # Convert agent_id to proper name, handling cases like "test_agent" -> "Test"
        agent_id.replace("_agent", "").replace("_", " ").title()
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Create a simple template that agents will populate through learning
        return self._create_basic_memory_template(agent_id, limits)

    def _create_basic_memory_template(
        self, agent_id: str, limits: Dict[str, Any]
    ) -> str:
        """Create basic memory template as a simple list.

        Args:
            agent_id: The agent identifier
            limits: Memory limits for this agent

        Returns:
            str: Basic memory template
        """
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        return f"""# Agent Memory: {agent_id}
<!-- Last Updated: {timestamp} -->

"""
