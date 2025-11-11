"""Native Agent Converter Service

Converts MPM agent JSON definitions to Claude Code --agents flag format.

WHY: Claude Code 1.0.83+ supports native --agents flag for dynamic agent definition.
This allows agents to be passed directly via CLI instead of deployed to .claude/agents/.

DESIGN: Converts MPM agent schema → Claude native schema with field mappings:
- description → description (agent selection hint)
- system_instructions → prompt (agent behavior)
- allowed_tools → tools (tool limitations)
- model_tier → model (model selection)

USAGE:
    converter = NativeAgentConverter()
    agents_flag = converter.build_agents_flag(agent_configs)
    # Returns: --agents '{"agent-name": {...}, ...}'
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_config import get_logger


class NativeAgentConverter:
    """Converts MPM agent configurations to Claude Code --agents format."""

    # Map MPM model tiers to Claude model names
    MODEL_TIER_MAP = {
        "opus": "opus",
        "sonnet": "sonnet",
        "haiku": "haiku",
        "claude-3-opus": "opus",
        "claude-3-sonnet": "sonnet",
        "claude-3-haiku": "haiku",
        "claude-3.5-sonnet": "sonnet",
        "claude-4-sonnet": "sonnet",
        "claude-4-opus": "opus",
    }

    # Map MPM tool names to Claude tool names
    TOOL_NAME_MAP = {
        "Read": "Read",
        "Write": "Write",
        "Edit": "Edit",
        "MultiEdit": "MultiEdit",
        "Bash": "Bash",
        "Grep": "Grep",
        "Glob": "Glob",
        "LS": "LS",
        "WebSearch": "WebSearch",
        "WebFetch": "WebFetch",
        "TodoWrite": "TodoWrite",
        "NotebookEdit": "NotebookEdit",
        "BashOutput": "BashOutput",
        "KillShell": "KillShell",
        "AskUserQuestion": "AskUserQuestion",
    }

    def __init__(self):
        """Initialize the native agent converter."""
        self.logger = get_logger(__name__)

    def convert_mpm_agent_to_native(
        self, agent_config: Dict[str, Any], agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert a single MPM agent config to Claude native format.

        Args:
            agent_config: MPM agent JSON configuration
            agent_id: Optional agent ID (falls back to agent_config['agent_id'])

        Returns:
            Dict with Claude native agent format:
            {
                "description": "...",
                "prompt": "...",
                "tools": [...],
                "model": "sonnet"
            }
        """
        try:
            # Extract agent ID
            if not agent_id:
                agent_id = agent_config.get("agent_id") or agent_config.get("name", "")

            # Extract description (for agent selection)
            description = agent_config.get("description", "")
            if not description and "metadata" in agent_config:
                description = agent_config["metadata"].get("description", "")

            # Build prompt from instructions and BASE_*.md reference
            prompt = self._build_agent_prompt(agent_config)

            # Extract and map tools
            tools = self._extract_and_map_tools(agent_config)

            # Map model tier
            model = self._map_model_tier(agent_config)

            native_config = {
                "description": description,
                "prompt": prompt,
                "tools": tools,
                "model": model,
            }

            self.logger.debug(f"Converted agent '{agent_id}' to native format")
            return native_config

        except Exception as e:
            self.logger.error(f"Error converting agent {agent_id}: {e}")
            # Return minimal valid config as fallback
            return {
                "description": f"Agent {agent_id}",
                "prompt": agent_config.get("instructions", ""),
                "tools": [],
                "model": "sonnet",
            }

    def _build_agent_prompt(self, agent_config: Dict[str, Any]) -> str:
        """Build agent prompt from instructions and BASE_*.md reference.

        OPTIMIZATION: Keep prompts concise for CLI argument length limits.
        The BASE_*.md files contain full instructions, so we only need:
        1. Reference to BASE file
        2. Brief specialization note

        Args:
            agent_config: MPM agent configuration

        Returns:
            Concise prompt string
        """
        prompt_parts = []

        # Add base instructions reference if available (most important)
        if "knowledge" in agent_config:
            base_file = agent_config["knowledge"].get("base_instructions_file")
            if base_file:
                prompt_parts.append(f"Follow {base_file} for all protocols.")

        # Add main instructions (keep brief)
        instructions = agent_config.get("instructions", "")
        if instructions:
            # Limit instruction length to avoid bloat
            if len(instructions) > 300:
                instructions = instructions[:300] + "..."
            prompt_parts.append(instructions)

        # Skip domain expertise and best practices for CLI mode
        # These are already in BASE_*.md files referenced above
        # Adding them here just bloats the JSON unnecessarily

        return "\n".join(str(part) for part in prompt_parts if part)

    def _extract_and_map_tools(self, agent_config: Dict[str, Any]) -> List[str]:
        """Extract and map tools from MPM config to Claude tool names.

        Args:
            agent_config: MPM agent configuration

        Returns:
            List of Claude tool names
        """
        tools = []

        # Check capabilities.tools
        if "capabilities" in agent_config and "tools" in agent_config["capabilities"]:
            mpm_tools = agent_config["capabilities"]["tools"]
            for tool in mpm_tools:
                mapped_tool = self.TOOL_NAME_MAP.get(tool, tool)
                if mapped_tool not in tools:
                    tools.append(mapped_tool)

        # If no tools specified, provide reasonable defaults
        if not tools:
            tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]

        return tools

    def _map_model_tier(self, agent_config: Dict[str, Any]) -> str:
        """Map MPM model tier to Claude model name.

        Args:
            agent_config: MPM agent configuration

        Returns:
            Claude model name (opus, sonnet, haiku)
        """
        # Check capabilities.model
        if "capabilities" in agent_config and "model" in agent_config["capabilities"]:
            model_tier = agent_config["capabilities"]["model"]
            return self.MODEL_TIER_MAP.get(model_tier.lower(), "sonnet")

        # Check metadata.model_preference
        if (
            "metadata" in agent_config
            and "model_preference" in agent_config["metadata"]
        ):
            model_tier = agent_config["metadata"]["model_preference"]
            return self.MODEL_TIER_MAP.get(model_tier.lower(), "sonnet")

        # Default to sonnet
        return "sonnet"

    def generate_agents_json(self, agents: List[Dict[str, Any]]) -> str:
        """Generate complete --agents JSON string from list of agent configs.

        Args:
            agents: List of MPM agent configurations

        Returns:
            JSON string for --agents flag
        """
        native_agents = {}

        for agent_config in agents:
            agent_id = agent_config.get("agent_id") or agent_config.get("name", "")
            if not agent_id:
                self.logger.warning("Skipping agent without ID")
                continue

            # Skip PM agent (main Claude instance)
            if agent_id.lower() in ["pm", "project_manager"]:
                self.logger.debug(f"Skipping PM agent: {agent_id}")
                continue

            native_config = self.convert_mpm_agent_to_native(agent_config, agent_id)
            native_agents[agent_id] = native_config

        return json.dumps(native_agents, separators=(",", ":"))

    def build_agents_flag(
        self, agents: List[Dict[str, Any]], escape_for_shell: bool = True
    ) -> str:
        """Build complete --agents flag for CLI.

        Args:
            agents: List of MPM agent configurations
            escape_for_shell: Whether to escape JSON for shell

        Returns:
            Complete flag string: --agents '{"agent1": {...}, ...}'
        """
        agents_json = self.generate_agents_json(agents)

        # Check length (Claude CLI has argument length limits)
        if len(agents_json) > 50000:  # Conservative limit
            self.logger.warning(
                f"Agents JSON is very large ({len(agents_json)} chars). "
                "Consider using file-based deployment."
            )

        if escape_for_shell:
            # Escape for shell - wrap in single quotes
            return f"--agents '{agents_json}'"

        return f"--agents {agents_json}"

    def load_agents_from_templates(
        self, templates_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Load all agent configs from templates directory.

        Args:
            templates_dir: Path to templates directory (defaults to MPM agents)

        Returns:
            List of agent configurations
        """
        if not templates_dir:
            # Default to MPM agents directory
            mpm_package_dir = Path(__file__).parent.parent / "agents" / "templates"
            templates_dir = mpm_package_dir

        if not templates_dir.exists():
            self.logger.warning(f"Templates directory not found: {templates_dir}")
            return []

        agents = []
        json_files = list(templates_dir.glob("*.json"))

        self.logger.info(
            f"Loading {len(json_files)} agent templates from {templates_dir}"
        )

        for json_file in json_files:
            try:
                # Skip base_agent.json
                if json_file.stem == "base_agent":
                    continue

                agent_config = json.loads(json_file.read_text())
                agents.append(agent_config)
                self.logger.debug(f"Loaded agent: {json_file.stem}")

            except Exception as e:
                self.logger.error(f"Error loading agent {json_file.name}: {e}")
                continue

        return agents

    def estimate_json_size(self, agents: List[Dict[str, Any]]) -> int:
        """Estimate the size of --agents JSON output.

        Args:
            agents: List of agent configurations

        Returns:
            Estimated size in bytes
        """
        agents_json = self.generate_agents_json(agents)
        return len(agents_json.encode("utf-8"))

    def get_conversion_summary(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of agent conversion for reporting.

        Args:
            agents: List of agent configurations

        Returns:
            Summary dict with counts and size info
        """
        native_agents = {}
        model_counts = {"opus": 0, "sonnet": 0, "haiku": 0}
        tool_usage = {}

        for agent_config in agents:
            agent_id = agent_config.get("agent_id") or agent_config.get("name", "")
            if not agent_id or agent_id.lower() in ["pm", "project_manager"]:
                continue

            native_config = self.convert_mpm_agent_to_native(agent_config, agent_id)
            native_agents[agent_id] = native_config

            # Count models
            model = native_config.get("model", "sonnet")
            model_counts[model] = model_counts.get(model, 0) + 1

            # Count tools
            for tool in native_config.get("tools", []):
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        json_size = len(json.dumps(native_agents, separators=(",", ":")))

        return {
            "total_agents": len(native_agents),
            "json_size": json_size,
            "json_size_kb": round(json_size / 1024, 2),
            "model_distribution": model_counts,
            "tool_usage": tool_usage,
            "agents": list(native_agents.keys()),
        }
