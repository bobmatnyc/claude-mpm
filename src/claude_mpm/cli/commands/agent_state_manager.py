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

        # Discover Git-sourced agents if requested
        if include_remote:
            try:
                git_agents = self._discover_git_agents()
                agents.extend(git_agents)
                self.logger.info(f"Discovered {len(git_agents)} Git-sourced agents")
            except Exception as e:
                self.logger.warning(f"Failed to discover Git-sourced agents: {e}")

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
                    display_name = metadata.get("name", agent_id)
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

                    # Check if this agent is deployed
                    is_deployed = self._is_agent_deployed(normalized_id)

                    agent_config = AgentConfig(
                        name=normalized_id,
                        description=(
                            description[:80] + "..."
                            if len(description) > 80
                            else description
                        ),
                        dependencies=display_tools,
                    )

                    # Set deployment status and display name
                    agent_config.is_deployed = is_deployed
                    agent_config.source_type = "local"
                    agent_config.display_name = display_name

                    agents.append(agent_config)

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

    def _discover_git_agents(self) -> List[AgentConfig]:
        """Discover agents from Git sources using GitSourceManager."""
        try:
            from claude_mpm.services.agents.git_source_manager import GitSourceManager

            # Initialize source manager (uses ~/.claude-mpm/cache/agents by default)
            source_manager = GitSourceManager()

            # Discover all cached agents from all repositories
            git_agent_dicts = source_manager.list_cached_agents()

            # Convert to AgentConfig objects for UI display
            agents = []
            for agent_dict in git_agent_dicts:
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
                    name=name,  # Use display name for UI
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
                agent_config.agent_id = agent_id  # Store technical ID for reference
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
        """Check if agent is deployed (virtual deployment or physical files).

        Args:
            agent_id: Full agent ID (may include hierarchy like engineer/backend/python-engineer)

        Returns:
            True if agent is deployed, False otherwise
        """
        # Check virtual deployment state (primary method)
        # Only checking project-level deployment in simplified architecture
        deployment_state_paths = [
            Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
        ]

        for state_path in deployment_state_paths:
            if state_path.exists():
                try:
                    with state_path.open() as f:
                        state = json.load(f)

                    # Check if agent is in deployment state
                    agents = state.get("last_check_results", {}).get("agents", {})

                    # Check full agent_id
                    if agent_id in agents:
                        self.logger.debug(
                            f"Agent {agent_id} found in virtual deployment state"
                        )
                        return True

                    # Check leaf name for hierarchical IDs
                    if "/" in agent_id:
                        leaf_name = agent_id.split("/")[-1]
                        if leaf_name in agents:
                            self.logger.debug(
                                f"Agent {agent_id} (leaf: {leaf_name}) found in virtual deployment state"
                            )
                            return True
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.debug(
                        f"Failed to read deployment state from {state_path}: {e}"
                    )
                    continue
                except Exception as e:
                    self.logger.debug(f"Unexpected error reading deployment state: {e}")
                    continue

        # Fallback to physical file checks (legacy support)
        # For hierarchical IDs, check both full ID and leaf name
        agent_file_names = [f"{agent_id}.md"]

        # Also check leaf name (last component after /)
        if "/" in agent_id:
            leaf_name = agent_id.split("/")[-1]
            agent_file_names.append(f"{leaf_name}.md")

        # Check .claude/agents/ directory (project deployment)
        project_agents_dir = Path.cwd() / ".claude" / "agents"
        if project_agents_dir.exists():
            for agent_file_name in agent_file_names:
                agent_file = project_agents_dir / agent_file_name
                if agent_file.exists():
                    self.logger.debug(
                        f"Agent {agent_id} found as physical file: {agent_file}"
                    )
                    return True

        return False
