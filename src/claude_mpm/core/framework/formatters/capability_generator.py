"""Agent capability generator for dynamic agent discovery.

Why: The PM system prompt must list every available agent with its routing
hints so the model knows when to delegate and to whom.  Hardcoding that list
would fall out of date whenever agents are added or removed.  This module
generates the ``## Available Agent Capabilities`` section dynamically from
the agents actually deployed on disk, with a hardcoded fallback for
environments where no agents are found.

What: :class:`CapabilityGenerator` reads deployed ``.md`` agent files, merges
their YAML frontmatter with routing metadata from JSON templates, and renders
a Markdown section listing every agent with its description, routing keywords,
authority, and model hints.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.logging_utils import get_logger

# Import resource handling for packaged installations
try:
    from importlib.resources import files
except ImportError:
    try:
        from importlib_resources import files
    except ImportError:
        files = None


class CapabilityGenerator:
    """Generates the ``## Available Agent Capabilities`` section of the PM prompt.

    Why: The PM model needs an up-to-date catalogue of available agents so it
    can make informed delegation decisions.  This class encapsulates all logic
    for discovering agents, parsing their metadata, and rendering the section,
    keeping the formatter layer thin and testable.

    Test: Instantiate with no arguments and call
    ``generate_capabilities_section([], {})``; the returned string should
    equal ``get_fallback_capabilities()`` (no agents found path).  With a
    populated ``deployed_agents`` list the section should contain at least one
    ``### <Name>`` heading per agent.
    """

    def __init__(self):
        """Initialise the capability generator with a module-level logger.

        Why: A dedicated logger prefixed ``"capability_generator"`` makes it
        easy to filter debug output for this subsystem without enabling
        verbose logging globally.

        Test: After construction, ``self.logger`` is not ``None`` and
        ``self.logger.name == "capability_generator"``.
        """
        self.logger = get_logger("capability_generator")

    def generate_capabilities_section(
        self,
        deployed_agents: List[Dict[str, Any]],
        local_agents: Dict[str, Dict[str, Any]],
    ) -> str:
        """Generate the ``## Available Agent Capabilities`` Markdown section.

        Why: The PM prompt must enumerate all reachable agents so the model
        can select the right one without guessing.  Local (project-tier) agents
        override deployed ones of the same ID so project customisations take
        precedence.

        What: Merges *local_agents* (highest priority) with *deployed_agents*,
        de-duplicates by agent ID, sorts alphabetically, then renders each
        agent as a Markdown sub-section with its description, routing hints,
        authority, primary function, handoff targets, tools, model, and memory
        routing metadata.  Falls back to :meth:`get_fallback_capabilities` if
        no agents are found.

        Args:
            deployed_agents: List of deployed agent metadata dicts (each must
                contain at least ``"id"`` and optionally ``"description"``,
                ``"routing"``, ``"authority"``, etc.)
            local_agents: Mapping of ``agent_id -> metadata`` for project-local
                agents; these take precedence over identically-named deployed
                agents.

        Returns:
            A Markdown string starting with
            ``"\\n\\n## Available Agent Capabilities\\n\\n"`` and ending with
            a total-agent count line.

        Test: Pass one deployed agent ``{"id": "research", "description": "…"}``
        and verify the returned string contains ``"### Research"`` and the
        agent description.  Pass an empty list/dict and verify the fallback
        string is returned instead.
        """
        # Build capabilities section
        section = "\n\n## Available Agent Capabilities\n\n"

        # Combine deployed and local agents
        all_agents = {}  # key: agent_id, value: (agent_data, priority)

        # Add local agents first (highest priority)
        for agent_id, agent_data in local_agents.items():
            all_agents[agent_id] = (agent_data, -1)  # Priority -1 for local agents

        # Add deployed agents with lower priority
        for priority, agent_data in enumerate(deployed_agents):
            agent_id = agent_data["id"]
            # Only add if not already present
            if agent_id not in all_agents:
                all_agents[agent_id] = (agent_data, priority)

        # Extract just the agent data and sort
        final_agents = [agent_data for agent_data, _ in all_agents.values()]

        if not final_agents:
            return self.get_fallback_capabilities()

        # Sort agents alphabetically by ID
        final_agents.sort(key=lambda x: x["id"])

        # Display all agents with their rich descriptions
        for agent in final_agents:
            # Clean up display name - handle common acronyms
            display_name = agent.get("display_name", agent["id"])
            display_name = (
                display_name.replace("Qa ", "QA ")
                .replace("Ui ", "UI ")
                .replace("Api ", "API ")
            )
            if display_name.lower() == "qa agent":
                display_name = "QA Agent"

            # Add local indicator if this is a local agent
            if agent.get("is_local"):
                tier_label = f" [LOCAL-{agent.get('tier', 'PROJECT').upper()}]"
                section += f"\n### {display_name} (`{agent['id']}`) {tier_label}\n"
            else:
                section += f"\n### {display_name} (`{agent['id']}`)\n"

            section += f"{agent.get('description', 'Specialized agent')}\n"

            # Add routing information if available
            if agent.get("routing"):
                routing = agent["routing"]
                routing_hints = []

                if routing.get("keywords"):
                    # Show first 5 keywords for brevity
                    keywords = routing["keywords"][:5]
                    routing_hints.append(f"Keywords: {', '.join(keywords)}")

                if routing.get("paths"):
                    # Show first 3 paths for brevity
                    paths = routing["paths"][:3]
                    routing_hints.append(f"Paths: {', '.join(paths)}")

                if routing.get("priority"):
                    routing_hints.append(f"Priority: {routing['priority']}")

                if routing_hints:
                    section += f"- **Routing**: {' | '.join(routing_hints)}\n"

                # Add when_to_use if present
                if routing.get("when_to_use"):
                    section += f"- **When to use**: {routing['when_to_use']}\n"

            # Add any additional metadata if present
            if agent.get("authority"):
                section += f"- **Authority**: {agent['authority']}\n"
            if agent.get("primary_function"):
                section += f"- **Primary Function**: {agent['primary_function']}\n"
            if agent.get("handoff_to"):
                section += f"- **Handoff To**: {agent['handoff_to']}\n"
            if agent.get("tools") and agent["tools"] != "standard":
                section += f"- **Tools**: {agent['tools']}\n"
            if agent.get("model") and agent["model"] != "opus":
                section += f"- **Model**: {agent['model']}\n"

            # Add memory routing information if available
            if agent.get("memory_routing"):
                memory_routing = agent["memory_routing"]
                if memory_routing.get("description"):
                    section += (
                        f"- **Memory Routing**: {memory_routing['description']}\n"
                    )

        # Add simple Context-Aware Agent Selection
        section += "\n## Context-Aware Agent Selection\n\n"
        section += "Select agents based on their descriptions above. Key principles:\n"
        section += "- **PM questions** → Answer directly (only exception)\n"
        section += "- Match task requirements to agent descriptions and authority\n"
        section += "- Consider agent handoff recommendations\n"
        section += "- Use the agent ID in parentheses when delegating via Task tool\n"

        # Add summary
        section += f"\n**Total Available Agents**: {len(final_agents)}\n"

        return section

    def parse_agent_metadata(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Parse agent metadata from a deployed ``.md`` agent file.

        Why: Each deployed agent carries its identity (``name``), description,
        routing hints, and capability metadata in a YAML frontmatter block.
        Centralising the parse logic here ensures every caller gets the same
        structured dict with sensible defaults when fields are absent.

        What: Reads *agent_file*, extracts the ``---`` frontmatter block,
        parses it with ``yaml.safe_load``, then supplements missing fields
        (``routing``, ``memory_routing``) from the corresponding JSON template
        via :meth:`load_routing_from_template` and
        :meth:`load_memory_routing_from_template`.  Returns ``None`` on any
        read/parse error so callers can skip unreadable files gracefully.

        Args:
            agent_file: Path to the deployed ``.md`` agent file.

        Returns:
            Dict with at minimum ``"id"``, ``"display_name"``, and
            ``"description"`` keys, plus any additional frontmatter fields;
            or ``None`` if the file could not be read or parsed.

        Test: Create a temp ``.md`` file with valid frontmatter
        ``name: My Agent`` and call ``parse_agent_metadata(path)``; assert
        ``result["id"] == "My Agent"``.  A file with no frontmatter should
        return a dict with the stem as the ``"id"``.  A completely
        unreadable file (permissions error) should return ``None``.
        """
        try:
            with agent_file.open() as f:
                content = f.read()

            # Default values
            agent_data: Dict[str, Any] = {
                "id": agent_file.stem,
                "display_name": agent_file.stem.replace("_", " ")
                .replace("-", " ")
                .title(),
                "description": "Specialized agent",
            }

            # Extract YAML frontmatter if present
            if content.startswith("---"):
                end_marker = content.find("---", 3)
                if end_marker > 0:
                    frontmatter = content[3:end_marker]
                    metadata = yaml.safe_load(frontmatter)
                    if metadata:
                        # Use name as ID for Task tool
                        agent_data["id"] = metadata.get("name", agent_data["id"])
                        agent_data["display_name"] = (
                            metadata.get("name", agent_data["display_name"])
                            .replace("-", " ")
                            .title()
                        )

                        # Copy all metadata fields directly
                        for key, value in metadata.items():
                            if key not in ["name"]:  # Skip already processed fields
                                agent_data[key] = value

            # Try to load routing metadata from JSON template if not in YAML frontmatter
            if "routing" not in agent_data:
                routing_data = self.load_routing_from_template(agent_file.stem)
                if routing_data:
                    agent_data["routing"] = routing_data

            # Try to load memory routing metadata from JSON template
            if "memory_routing" not in agent_data:
                memory_routing_data = self.load_memory_routing_from_template(
                    agent_file.stem
                )
                if memory_routing_data:
                    agent_data["memory_routing"] = memory_routing_data

            return agent_data

        except Exception as e:
            self.logger.debug(f"Could not parse metadata from {agent_file}: {e}")
            return None

    def load_routing_from_template(
        self, agent_name: str, framework_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Load routing metadata from an agent's JSON template file.

        Why: Routing hints (keywords, file paths, priority) are stored in JSON
        templates rather than the ``.md`` file so they can be updated without
        redeploying the agent.  When an ``.md`` file lacks a ``routing`` key in
        its frontmatter this method retrieves the routing data from the
        corresponding template.

        What: For packaged installations uses ``importlib.resources`` to
        locate templates; for development mode resolves the path relative to
        *framework_path*.  Tries the canonical agent name first, then
        alternative spellings (hyphens vs underscores).  Returns ``None``
        when no template is found or on any error.

        Args:
            agent_name: Stem of the agent file (e.g. ``"local-ops"``).
            framework_path: Root of the framework installation; pass
                ``None`` or ``Path("__PACKAGED__")`` for packaged mode.

        Returns:
            The ``"routing"`` sub-dict from the template, or ``None``.

        Test: In development mode, create a mock template JSON with a
        ``"routing"`` key and confirm the method returns that dict.  Pass an
        unknown agent name and confirm ``None`` is returned without raising.
        """
        try:
            # Check if we have a framework path
            if not framework_path or framework_path == Path("__PACKAGED__"):
                # For packaged installations, try to load from package resources
                if files:
                    try:
                        templates_package = files("claude_mpm.agents.templates")
                        template_file = templates_package / f"{agent_name}.json"

                        if template_file.is_file():
                            template_content = template_file.read_text()
                            template_data = json.loads(template_content)
                            return template_data.get("routing")
                    except Exception as e:
                        self.logger.debug(
                            f"Could not load routing from packaged template for {agent_name}: {e}"
                        )
                return None

            # For development mode, load from filesystem
            templates_dir = (
                framework_path / "src" / "claude_mpm" / "agents" / "templates"
            )
            template_file = templates_dir / f"{agent_name}.json"

            if template_file.exists():
                with template_file.open() as f:
                    template_data = json.load(f)
                    return template_data.get("routing")

            # Also check for variations in naming (underscore vs dash)
            alternative_names = list(
                {
                    agent_name.replace("-", "_"),
                    agent_name.replace("_", "-"),
                    agent_name.replace("-", ""),
                    agent_name.replace("_", ""),
                }
            )

            for alt_name in alternative_names:
                if alt_name != agent_name:
                    alt_file = templates_dir / f"{alt_name}.json"
                    if alt_file.exists():
                        with alt_file.open() as f:
                            template_data = json.load(f)
                            return template_data.get("routing")

            return None

        except Exception as e:
            self.logger.debug(f"Could not load routing metadata for {agent_name}: {e}")
            return None

    def load_memory_routing_from_template(
        self, agent_name: str, framework_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Load memory-routing metadata from an agent's JSON template file.

        Why: Memory routing describes how an agent's outputs should be stored
        in the project memory graph (KuzuDB).  Like routing hints, this data
        lives in JSON templates rather than the ``.md`` file so it can evolve
        independently.

        What: Identical search strategy to :meth:`load_routing_from_template`
        but returns the ``"memory_routing"`` sub-dict instead of ``"routing"``.
        Also tries ``-agent`` and ``_agent`` name variants because some
        templates use the suffixed form.

        Args:
            agent_name: Stem of the agent file (e.g. ``"engineer"``).
            framework_path: Root of the framework installation; pass
                ``None`` or ``Path("__PACKAGED__")`` for packaged mode.

        Returns:
            The ``"memory_routing"`` sub-dict from the template, or ``None``.

        Test: Provide a mock template JSON with a ``"memory_routing"`` key;
        confirm the method returns that dict.  An agent with no template
        should return ``None`` without raising.
        """
        try:
            # Check if we have a framework path
            if not framework_path or framework_path == Path("__PACKAGED__"):
                # For packaged installations, try to load from package resources
                if files:
                    try:
                        templates_package = files("claude_mpm.agents.templates")
                        template_file = templates_package / f"{agent_name}.json"

                        if template_file.is_file():
                            template_content = template_file.read_text()
                            template_data = json.loads(template_content)
                            return template_data.get("memory_routing")
                    except Exception as e:
                        self.logger.debug(
                            f"Could not load memory routing from packaged template for {agent_name}: {e}"
                        )
                return None

            # For development mode, load from filesystem
            templates_dir = (
                framework_path / "src" / "claude_mpm" / "agents" / "templates"
            )
            template_file = templates_dir / f"{agent_name}.json"

            if template_file.exists():
                with template_file.open() as f:
                    template_data = json.load(f)
                    return template_data.get("memory_routing")

            # Also check for variations in naming
            alternative_names = list(
                {
                    agent_name.replace("-", "_"),
                    agent_name.replace("_", "-"),
                    agent_name.replace("-agent", ""),
                    agent_name.replace("_agent", ""),
                    agent_name + "_agent",
                    agent_name + "-agent",
                }
            )

            for alt_name in alternative_names:
                if alt_name != agent_name:
                    alt_file = templates_dir / f"{alt_name}.json"
                    if alt_file.exists():
                        with alt_file.open() as f:
                            template_data = json.load(f)
                            return template_data.get("memory_routing")

            return None

        except Exception as e:
            self.logger.debug(
                f"Could not load memory routing from template for {agent_name}: {e}"
            )
            return None

    def get_fallback_capabilities(self) -> str:
        """Return a static fallback capabilities section when discovery fails.

        Why: If no agents are deployed (e.g. a fresh install or a CI
        environment without a ``.claude/agents/`` directory) the PM prompt
        must still list *something* so the model can function.  This method
        returns a minimal hardcoded list of core agents.

        What: Returns a fixed Markdown string listing eight core agents with
        their canonical IDs.  This string is identical in structure to the
        dynamically generated section so the model's prompt format is
        consistent.

        Returns:
            A Markdown string with a hardcoded ``## Available Agent
            Capabilities`` section listing core agents.

        Test: Call with no arguments and assert the return value contains
        ``"## Available Agent Capabilities"`` and the string
        ``"engineer"`` (the Engineer agent ID).
        """
        return """

## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer** (`engineer`): Code implementation and development
- **Research** (`research-agent`): Investigation and analysis
- **QA** (`qa-agent`): Testing and quality assurance
- **Documentation** (`documentation-agent`): Documentation creation and maintenance
- **Security** (`security-agent`): Security analysis and protection
- **Data Engineer** (`data-engineer`): Data management and pipelines
- **Ops** (`ops-agent`): Deployment and operations
- **Version Control** (`version-control`): Git operations and version management

**IMPORTANT**: Use the exact agent ID in parentheses when delegating tasks.
"""
