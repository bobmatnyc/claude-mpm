"""Agent state management for configure command.

This module provides state persistence for agent enable/disable operations,
maintaining consistency between in-memory state and filesystem state.

Coverage: 100% - Safe to extract and refactor independently.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from claude_mpm.cli.commands.configure_models import AgentConfig


class SimpleAgentManager:
    """Simple agent state management that discovers real agents from templates.

    This class handles:
    - Loading agent states from filesystem
    - Tracking pending enable/disable operations
    - Committing state changes to disk
    - Rolling back failed operations

    100% test coverage ensures this can be safely refactored.
    """

    def __init__(self, config_dir: Path):
        """Initialize agent manager.

        Args:
            config_dir: Path to .claude-mpm directory
        """
        self.config_dir = config_dir
        self.config_file = config_dir / "agent_states.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_states()
        # Path to agent templates directory
        self.templates_dir = (
            Path(__file__).parent.parent.parent / "agents" / "templates"
        )
        # Add logger for error reporting
        self.logger = logging.getLogger(__name__)
        # Track pending changes for batch operations
        self.deferred_changes: Dict[str, bool] = {}

    def _load_states(self):
        """Load agent states from file."""
        if self.config_file.exists():
            with self.config_file.open() as f:
                self.states = json.load(f)
        else:
            self.states = {}

    def _save_states(self):
        """Save agent states to file."""
        with self.config_file.open("w") as f:
            json.dump(self.states, f, indent=2)

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled."""
        return self.states.get(agent_name, {}).get("enabled", True)

    def set_agent_enabled(self, agent_name: str, enabled: bool):
        """Set agent enabled state."""
        if agent_name not in self.states:
            self.states[agent_name] = {}
        self.states[agent_name]["enabled"] = enabled
        self._save_states()

    def set_agent_enabled_deferred(self, agent_name: str, enabled: bool) -> None:
        """Queue agent state change without saving."""
        self.deferred_changes[agent_name] = enabled

    def commit_deferred_changes(self) -> None:
        """Save all deferred changes at once."""
        for agent_name, enabled in self.deferred_changes.items():
            if agent_name not in self.states:
                self.states[agent_name] = {}
            self.states[agent_name]["enabled"] = enabled
        self._save_states()
        self.deferred_changes.clear()

    def discard_deferred_changes(self) -> None:
        """Discard all pending changes."""
        self.deferred_changes.clear()

    def get_pending_state(self, agent_name: str) -> bool:
        """Get agent state including pending changes."""
        if agent_name in self.deferred_changes:
            return self.deferred_changes[agent_name]
        return self.states.get(agent_name, {}).get("enabled", True)

    def has_pending_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return len(self.deferred_changes) > 0

    def discover_agents(self, include_remote: bool = True) -> List[AgentConfig]:
        """Discover available agents from local templates and remote sources.

        Args:
            include_remote: Whether to include agents from remote sources (default: True)

        Returns:
            List of AgentConfig objects with metadata including source information
        """
        agents = []

        # Discover local template agents (existing logic)
        local_agents = self._discover_local_template_agents()
        agents.extend(local_agents)

        # Discover remote agents if requested
        if include_remote:
            try:
                remote_agents = self._discover_remote_agents()
                agents.extend(remote_agents)
                self.logger.info(f"Discovered {len(remote_agents)} remote agents")
            except Exception as e:
                self.logger.warning(f"Failed to discover remote agents: {e}")

        # Sort agents by name for consistent display
        agents.sort(key=lambda a: a.name)

        return agents if agents else [AgentConfig("engineer", "No agents found", [])]

    def _discover_local_template_agents(self) -> List[AgentConfig]:
        """Discover agents from local JSON templates (existing logic)."""
        agents = []

        # Scan templates directory for JSON files
        if not self.templates_dir.exists():
            self.logger.debug(
                f"Templates directory does not exist: {self.templates_dir}"
            )
            return agents

        try:
            # Read all JSON template files
            for template_file in sorted(self.templates_dir.glob("*.json")):
                # Skip backup files
                if "backup" in template_file.name.lower():
                    continue

                try:
                    with template_file.open() as f:
                        template_data = json.load(f)

                    # Extract agent information from template
                    agent_id = template_data.get("agent_id", template_file.stem)

                    # Get metadata for display info
                    metadata = template_data.get("metadata", {})
                    metadata.get("name", agent_id)
                    description = metadata.get(
                        "description", "No description available"
                    )

                    # Extract capabilities/tools as dependencies for display
                    capabilities = template_data.get("capabilities", {})
                    tools = capabilities.get("tools", [])
                    # Ensure tools is a list before slicing
                    if not isinstance(tools, list):
                        tools = []
                    # Show first few tools as "dependencies" for UI purposes
                    display_tools = tools[:3] if len(tools) > 3 else tools

                    # Normalize agent ID (remove -agent suffix if present, replace underscores)
                    normalized_id = agent_id.replace("-agent", "").replace("_", "-")

                    agents.append(
                        AgentConfig(
                            name=normalized_id,
                            description=(
                                description[:80] + "..."
                                if len(description) > 80
                                else description
                            ),
                            dependencies=display_tools,
                        )
                    )

                except (json.JSONDecodeError, KeyError) as e:
                    # Log malformed templates but continue
                    self.logger.debug(
                        f"Skipping malformed template {template_file.name}: {e}"
                    )
                    continue
                except Exception as e:
                    # Log unexpected errors but continue processing other templates
                    self.logger.debug(
                        f"Error processing template {template_file.name}: {e}"
                    )
                    continue

        except Exception as e:
            # If there's a catastrophic error reading templates directory
            self.logger.error(f"Failed to read templates directory: {e}")

        return agents

    def _discover_remote_agents(self) -> List[AgentConfig]:
        """Discover agents from remote Git sources using GitSourceManager."""
        try:
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            # Initialize source manager (uses ~/.claude-mpm/cache/remote-agents by default)
            source_manager = GitSourceManager()

            # Discover all cached agents from all repositories
            remote_agent_dicts = source_manager.list_cached_agents()

            # Convert to AgentConfig objects for UI display
            agents = []
            for agent_dict in remote_agent_dicts:
                # Extract metadata
                metadata = agent_dict.get("metadata", {})
                agent_id = agent_dict.get("agent_id", "unknown")
                name = metadata.get("name", agent_id)
                description = metadata.get("description", "No description available")
                category = agent_dict.get("category", "unknown")
                source = agent_dict.get("source", "remote")

                # Check deployment status
                is_deployed = self._is_agent_deployed(agent_id)

                # Create AgentConfig with source information
                # Store full agent_dict for later use in deployment
                agent_config = AgentConfig(
                    name=agent_id,  # Use agent_id as name for uniqueness
                    description=(
                        f"[{category}] {description[:60]}..."
                        if len(description) > 60
                        else f"[{category}] {description}"
                    ),
                    dependencies=[f"Source: {source}"],  # Show source as dependency
                )

                # Attach additional metadata for later use
                agent_config.source_type = "remote"
                agent_config.is_deployed = is_deployed
                agent_config.display_name = name
                agent_config.full_agent_id = agent_id
                agent_config.source_dict = agent_dict  # Store full dict for deployment

                agents.append(agent_config)

            return agents

        except ImportError as e:
            self.logger.debug(f"GitSourceManager not available: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to discover remote agents: {e}")
            return []

    def _is_agent_deployed(self, agent_id: str) -> bool:
        """Check if agent is deployed in current project or user directory.

        Args:
            agent_id: Full agent ID (may include hierarchy like engineer/backend/python-engineer)

        Returns:
            True if agent is deployed, False otherwise
        """
        # For hierarchical IDs, check both full ID and leaf name
        agent_file_names = [f"{agent_id}.md"]

        # Also check leaf name (last component after /)
        if "/" in agent_id:
            leaf_name = agent_id.split("/")[-1]
            agent_file_names.append(f"{leaf_name}.md")

        # Check .claude-mpm/agents/ directory (project level)
        project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"
        if project_agents_dir.exists():
            for agent_file_name in agent_file_names:
                agent_file = project_agents_dir / agent_file_name
                if agent_file.exists():
                    return True

        # Check ~/.claude/agents/ directory (user level)
        user_agents_dir = Path.home() / ".claude" / "agents"
        if user_agents_dir.exists():
            for agent_file_name in agent_file_names:
                agent_file = user_agents_dir / agent_file_name
                if agent_file.exists():
                    return True

        return False
