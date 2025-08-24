#!/usr/bin/env python3
"""
Agent Loader Integration
========================

Integrates the new agent management service with the existing agent loader.
Provides backward compatibility while enabling advanced features.
"""

import logging
from typing import Any, Dict, Optional

from ..models.agent_definition import AgentDefinition
from ..services import AgentManager
from .agent_loader import get_agent_prompt

logger = logging.getLogger(__name__)


class EnhancedAgentLoader:
    """Enhanced agent loader with management capabilities."""

    def __init__(self):
        """Initialize enhanced loader."""
        self.manager = AgentManager()

    def get_agent_definition(self, agent_name: str) -> Optional[AgentDefinition]:
        """
        Get full agent definition with structured data.

        Args:
            agent_name: Agent name (e.g., 'documentation', 'ticketing')

        Returns:
            AgentDefinition or None
        """
        # Map from old naming to new naming if needed
        # Since AGENT_MAPPINGS no longer exists, use direct naming
        agent_file_name = agent_name

        return self.manager.read_agent(agent_file_name)

    def get_agent_metadata(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent metadata only.

        Args:
            agent_name: Agent name

        Returns:
            Metadata dict or None
        """
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            return None

        return {
            "name": agent_def.name,
            "title": agent_def.title,
            "version": agent_def.metadata.version,
            "type": agent_def.metadata.type.value,
            "model_preference": agent_def.metadata.model_preference,
            "specializations": agent_def.metadata.specializations,
            "last_updated": (
                agent_def.metadata.last_updated.isoformat()
                if agent_def.metadata.last_updated
                else None
            ),
        }

    def get_agent_capabilities(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent capabilities and permissions.

        Args:
            agent_name: Agent name

        Returns:
            Capabilities dict or None
        """
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            return None

        return {
            "capabilities": agent_def.capabilities,
            "authority": {
                "write_access": agent_def.authority.exclusive_write_access,
                "forbidden": agent_def.authority.forbidden_operations,
                "read_access": agent_def.authority.read_access,
            },
            "workflows": [w.name for w in agent_def.workflows],
            "tools_available": bool(agent_def.tools_commands),
        }

    def get_agent_selection_criteria(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent selection criteria for routing.

        Args:
            agent_name: Agent name

        Returns:
            Selection criteria dict or None
        """
        agent_def = self.get_agent_definition(agent_name)
        if not agent_def:
            return None

        return {
            "when_to_select": agent_def.when_to_use.get("select", []),
            "when_not_to_select": agent_def.when_to_use.get("do_not_select", []),
            "specializations": agent_def.metadata.specializations,
            "dependencies": agent_def.dependencies,
            "escalation_triggers": agent_def.escalation_triggers,
        }

    def update_agent_version(self, agent_name: str) -> bool:
        """
        Increment agent version (serial).

        Args:
            agent_name: Agent name

        Returns:
            True if updated, False otherwise
        """
        # Map name - since AGENT_MAPPINGS no longer exists, use direct naming
        agent_file_name = agent_name

        result = self.manager.update_agent(agent_file_name, {}, increment_version=True)
        return result is not None

    def refresh_agent_prompt(self, agent_name: str) -> str:
        """
        Force refresh agent prompt from file.

        Args:
            agent_name: Agent name

        Returns:
            Agent prompt with base instructions
        """
        # Use existing loader for backward compatibility
        return get_agent_prompt(agent_name, force_reload=True)


# Global instance for convenience
_enhanced_loader = None


def get_enhanced_loader() -> EnhancedAgentLoader:
    """Get global enhanced loader instance."""
    global _enhanced_loader
    if _enhanced_loader is None:
        _enhanced_loader = EnhancedAgentLoader()
    return _enhanced_loader


# Convenience functions
def get_agent_full_definition(agent_name: str) -> Optional[AgentDefinition]:
    """Get complete agent definition."""
    return get_enhanced_loader().get_agent_definition(agent_name)


def get_agent_version(agent_name: str) -> Optional[str]:
    """Get agent version."""
    metadata = get_enhanced_loader().get_agent_metadata(agent_name)
    return metadata["version"] if metadata else None


def check_agent_capability(agent_name: str, capability_keyword: str) -> bool:
    """Check if agent has a specific capability."""
    caps = get_enhanced_loader().get_agent_capabilities(agent_name)
    if not caps:
        return False

    # Check in capabilities list
    for cap in caps["capabilities"]:
        if capability_keyword.lower() in cap.lower():
            return True
    return False


def should_select_agent(agent_name: str, task_description: str) -> Dict[str, Any]:
    """
    Determine if an agent should be selected for a task.

    Args:
        agent_name: Agent name
        task_description: Task description

    Returns:
        Dict with selection recommendation and reasons
    """
    criteria = get_enhanced_loader().get_agent_selection_criteria(agent_name)
    if not criteria:
        return {"should_select": False, "reason": "Agent not found"}

    task_lower = task_description.lower()

    # Check positive matches
    positive_matches = []
    for criterion in criteria["when_to_select"]:
        # Extract keywords from criterion
        if "Keywords:" in criterion:
            keywords = criterion.split("Keywords:")[1].strip()
            for keyword in keywords.split(","):
                keyword = keyword.strip().strip('"').strip("'")
                if keyword.lower() in task_lower:
                    positive_matches.append(f"Keyword match: {keyword}")
        elif any(word in task_lower for word in criterion.lower().split()):
            positive_matches.append(f"Criterion match: {criterion[:50]}...")

    # Check negative matches
    negative_matches = []
    for criterion in criteria["when_not_to_select"]:
        if any(word in task_lower for word in criterion.lower().split()[:5]):
            negative_matches.append(f"Exclusion: {criterion[:50]}...")

    return {
        "should_select": len(positive_matches) > 0 and len(negative_matches) == 0,
        "positive_matches": positive_matches,
        "negative_matches": negative_matches,
        "specializations": criteria["specializations"],
    }
