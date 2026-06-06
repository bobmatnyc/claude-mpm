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
import re
from pathlib import Path
from typing import Any

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
        deployed_agents: list[dict[str, Any]],
        local_agents: dict[str, dict[str, Any]],
    ) -> str:
        """Generate the ``## Available Agent Capabilities`` Markdown section.

        WHAT: Produces a terse one-liner-per-agent bullet list for the PM
        system prompt, keeping every agent name, subagent_type/routing
        identifier, and a 1-line description.  Verbose per-agent sub-fields
        (Memory Routing, Authority, Routing keywords, etc.) are omitted; that
        detail is not needed for PM routing decisions and was the largest single
        source of token bloat (~860 tokens / session for 27 Memory-Routing
        entries alone).

        WHY: Issue #678 — reduce the assembled PM system prompt from ~12 K
        tokens.  Conservative trim: routing must not break, so ALL agent
        names and IDs stay INLINE.  Only per-agent verbose blurbs are dropped.

        Format per agent::

            - **Display Name** (`subagent_type`) — one-line description [model]

        Local-tier agents get a ``[LOCAL]`` suffix instead of the model hint.

        Local (project-tier) agents override deployed ones of the same ID so
        project customisations take precedence.

        Falls back to :meth:`get_fallback_capabilities` if no agents are found.

        Args:
            deployed_agents: List of deployed agent metadata dicts (each must
                contain at least ``"id"`` and optionally ``"description"``,
                ``"model"``, etc.)
            local_agents: Mapping of ``agent_id -> metadata`` for project-local
                agents; these take precedence over identically-named deployed
                agents.

        Returns:
            A Markdown string starting with
            ``"\\n\\n## Available Agent Capabilities\\n\\n"`` and ending with
            a total-agent count line.

        Test: Pass one deployed agent ``{"id": "research", "description": "…"}``
        and verify the returned string contains ``"(`research`)"`` and the
        agent description.  Pass an empty list/dict and verify the fallback
        string is returned instead.
        """
        # Build capabilities section
        section = "\n\n## Available Agent Capabilities\n\n"

        # Combine deployed and local agents
        all_agents: dict[str, tuple[dict[str, Any], int]] = {}

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

        # Secondary de-dup by normalized display name.
        # ID-based de-dup above does not catch the case where the same agent is
        # discovered twice under different IDs but resolves to the same display
        # name (e.g. local ``.claude/agents/research.md`` -> id ``research`` and
        # deployed ``~/.claude-mpm/agents/research.md`` -> id ``Research``, both
        # rendering as "Research").  Those duplicate entries waste PM-prompt
        # tokens, so keep only the first occurrence of each display name with
        # local agents winning over deployed ones.
        final_agents = self._dedup_by_display_name(final_agents)

        if not final_agents:
            return self.get_fallback_capabilities()

        # Sort agents alphabetically by ID
        final_agents.sort(key=lambda x: x["id"])

        # Emit a terse one-liner per agent.
        # Format: - **Display Name** (`id`) — description [model]
        # Rationale: The verbose ### heading + multi-line bullet format used
        # ~257 bytes per agent on average; the one-liner uses ~130 bytes.
        # Memory Routing, Authority, Routing-keywords, and other per-agent
        # sub-fields are intentionally dropped here — they are not needed for
        # PM routing decisions and cost ~860 tokens for 27 agents (issue #678).
        for agent in final_agents:
            # Strip <example>...</example> blocks from description before rendering.
            # These blocks help Claude Code route tasks during agent-file parsing, but
            # they are redundant here because the PM already uses the routing tables in
            # AGENT_DELEGATION.md.  Removing them from the rendered capabilities section
            # saves ~4,800 tokens per session without losing any routing information.
            desc_raw = agent.get("description", "Specialized agent")
            desc = re.sub(
                r"\s*<example>.*?</example>", "", desc_raw, flags=re.DOTALL
            ).strip()
            if not desc:
                desc = "Specialized agent"

            # Clean up display name - handle common acronyms
            display_name = agent.get("display_name", agent["id"])
            display_name = (
                display_name.replace("Qa ", "QA ")
                .replace("Ui ", "UI ")
                .replace("Api ", "API ")
            )
            if display_name.lower() == "qa agent":
                display_name = "QA Agent"

            # Inline model hint or LOCAL marker — keeps routing context without
            # a separate bullet line per agent.
            if agent.get("is_local"):
                tier = agent.get("tier", "PROJECT").upper()
                suffix = f" [LOCAL-{tier}]"
            elif agent.get("model") and agent["model"] != "opus":
                suffix = f" [{agent['model']}]"
            else:
                suffix = ""

            section += f"- **{display_name}** (`{agent['id']}`) — {desc}{suffix}\n"

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

    def _dedup_by_display_name(
        self, agents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Drop agents that share a normalized display name, local-first.

        Why: Agents can be discovered twice under different IDs (e.g. local
        ``research`` vs deployed ``Research``) yet render the same display
        name.  Both then appear in the PM capabilities block, wasting tokens
        with redundant entries.  De-duplicating by display name removes that
        waste while preserving the local-over-deployed precedence the rest of
        this class relies on.

        What: Walks *agents* in order, computing a case-insensitive,
        whitespace-collapsed display name for each.  Keeps the first agent seen
        for each normalized name; if a later agent has the same name but the
        already-kept one is *not* local while the new one *is* local, the local
        agent replaces it.  Logs a debug line for every dropped duplicate.

        Args:
            agents: Agent metadata dicts (already ID-de-duplicated), each
                optionally carrying ``display_name``, ``id`` and ``is_local``.

        Returns:
            A new list with display-name duplicates removed, order preserved.

        Test: Pass ``[{"id": "research", "is_local": True}, {"id": "Research"}]``
        and assert the result has length 1 and keeps the local ``research``
        entry.  Pass two distinct names and assert both survive unchanged.
        """
        kept: dict[str, dict[str, Any]] = {}
        for agent in agents:
            key = self._normalize_display_name(
                agent.get("display_name", agent.get("id", ""))
            )
            existing = kept.get(key)
            if existing is None:
                kept[key] = agent
                continue

            # Duplicate display name: prefer the local agent.
            if agent.get("is_local") and not existing.get("is_local"):
                self.logger.debug(
                    "Dropping duplicate display name %r: deployed %r superseded "
                    "by local %r",
                    key,
                    existing.get("id"),
                    agent.get("id"),
                )
                kept[key] = agent
            else:
                self.logger.debug(
                    "Dropping duplicate display name %r: %r superseded by kept %r",
                    key,
                    agent.get("id"),
                    existing.get("id"),
                )
        return list(kept.values())

    @staticmethod
    def _normalize_display_name(name: str) -> str:
        """Return a case-insensitive, whitespace-collapsed display-name key.

        Why: Display-name de-duplication must treat ``"QA  Agent"`` and
        ``"qa agent"`` as the same agent; a normalized key makes the comparison
        robust to casing and incidental whitespace differences.

        What: Lower-cases *name* and collapses any run of whitespace into a
        single space, then strips leading/trailing whitespace.

        Test: Assert ``_normalize_display_name("  QA   Agent ") ==
        "qa agent"`` and that two strings differing only in case/whitespace map
        to the same value.
        """
        return re.sub(r"\s+", " ", name).strip().lower()

    def parse_agent_metadata(self, agent_file: Path) -> dict[str, Any] | None:
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
            agent_data: dict[str, Any] = {
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
        self, agent_name: str, framework_path: Path | None = None
    ) -> dict[str, Any] | None:
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
        self, agent_name: str, framework_path: Path | None = None
    ) -> dict[str, Any] | None:
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
