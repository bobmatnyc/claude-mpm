"""Framework content formatter for generating instructions."""

import re
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger


class ContentFormatter:
    """Formats framework content for injection into prompts."""

    def __init__(self):
        """Initialize the content formatter."""
        self.logger = get_logger("content_formatter")

    def strip_metadata_comments(self, content: str) -> str:
        """Strip metadata HTML comments from content.

        Removes comments like:
        <!-- FRAMEWORK_VERSION: 0010 -->
        <!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->

        Args:
            content: Content to clean

        Returns:
            Cleaned content without metadata comments
        """
        # Remove HTML comments that contain metadata
        cleaned = re.sub(
            r"<!--\s*(FRAMEWORK_VERSION|LAST_MODIFIED|WORKFLOW_VERSION|PROJECT_WORKFLOW_VERSION|CUSTOM_PROJECT_WORKFLOW)[^>]*-->\n?",
            "",
            content,
        )
        # Also remove any leading blank lines that might result
        return cleaned.lstrip("\n")

    def format_full_framework(
        self,
        framework_content: Dict[str, Any],
        capabilities_section: str,
        context_section: str,
        inject_output_style: bool = False,
        output_style_content: Optional[str] = None,
    ) -> str:
        """Format complete framework instructions.

        Args:
            framework_content: Dictionary containing framework content
            capabilities_section: Generated agent capabilities section
            context_section: Generated temporal/user context section
            inject_output_style: Whether to inject output style content
            output_style_content: Output style content to inject (if needed)

        Returns:
            Formatted framework instructions
        """
        # If we have the full framework INSTRUCTIONS.md, use it
        if framework_content.get("framework_instructions"):
            instructions = self.strip_metadata_comments(
                framework_content["framework_instructions"]
            )

            # Add custom INSTRUCTIONS.md if present (overrides or extends framework instructions)
            if framework_content.get("custom_instructions"):
                level = framework_content.get("custom_instructions_level", "unknown")
                instructions += f"\n\n## Custom PM Instructions ({level} level)\n\n"
                instructions += "**The following custom instructions override or extend the framework defaults:**\n\n"
                instructions += self.strip_metadata_comments(
                    framework_content["custom_instructions"]
                )
                instructions += "\n"

            # Add WORKFLOW.md after instructions
            if framework_content.get("workflow_instructions"):
                workflow_content = self.strip_metadata_comments(
                    framework_content["workflow_instructions"]
                )
                level = framework_content.get("workflow_instructions_level", "system")
                if level != "system":
                    instructions += f"\n\n## Workflow Instructions ({level} level)\n\n"
                    instructions += "**The following workflow instructions override system defaults:**\n\n"
                instructions += f"{workflow_content}\n"

            # Add MEMORY.md after workflow instructions
            if framework_content.get("memory_instructions"):
                memory_content = self.strip_metadata_comments(
                    framework_content["memory_instructions"]
                )
                level = framework_content.get("memory_instructions_level", "system")
                if level != "system":
                    instructions += f"\n\n## Memory Instructions ({level} level)\n\n"
                    instructions += "**The following memory instructions override system defaults:**\n\n"
                instructions += f"{memory_content}\n"

            # Add actual PM memories after memory instructions
            if framework_content.get("actual_memories"):
                instructions += "\n\n## Current PM Memories\n\n"
                instructions += "**The following are your accumulated memories and knowledge from this project:**\n\n"
                instructions += framework_content["actual_memories"]
                instructions += "\n"

            # NOTE: Agent memories are now injected at agent deployment time
            # in agent_template_builder.py, not in PM instructions.
            # This ensures each agent gets its own memory, not all memories embedded in PM.

            # Add dynamic agent capabilities section
            instructions += capabilities_section

            # Add enhanced temporal and user context for better awareness
            instructions += context_section

            # Add BASE_PM.md framework requirements AFTER INSTRUCTIONS.md
            if framework_content.get("base_pm_instructions"):
                base_pm = self.strip_metadata_comments(
                    framework_content["base_pm_instructions"]
                )
                instructions += f"\n\n{base_pm}"

            # Inject output style content if needed (for Claude < 1.0.83)
            if inject_output_style and output_style_content:
                instructions += "\n\n## Output Style Configuration\n"
                instructions += "**Note: The following output style is injected for Claude < 1.0.83**\n\n"
                instructions += output_style_content
                instructions += "\n"

            # Clean up any trailing whitespace
            return instructions.rstrip() + "\n"

        # Otherwise generate minimal framework
        return self.format_minimal_framework(framework_content)

    def format_minimal_framework(self, framework_content: Dict[str, Any]) -> str:
        """Format minimal framework instructions when full framework not available.

        Args:
            framework_content: Dictionary containing framework content

        Returns:
            Minimal framework instructions
        """
        instructions = """# Claude MPM Framework Instructions

You are operating within the Claude Multi-Agent Project Manager (MPM) framework.

## Core Role
You are a multi-agent orchestrator. Your primary responsibilities are:
- Delegate all implementation work to specialized agents via Task Tool
- Coordinate multi-agent workflows and cross-agent collaboration
- Extract and track TODO/BUG/FEATURE items for ticket creation
- Maintain project visibility and strategic oversight
- NEVER perform direct implementation work yourself

"""

        # Add agent definitions if available
        if framework_content.get("agents"):
            instructions += "## Available Agents\n\n"
            instructions += "You have the following specialized agents available for delegation:\n\n"

            # List agents with brief descriptions and correct IDs
            agent_list = []
            for agent_name in sorted(framework_content["agents"].keys()):
                # Use the actual agent_name as the ID (it's the filename stem)
                agent_id = agent_name
                clean_name = agent_name.replace("-", " ").replace("_", " ").title()
                if (
                    "engineer" in agent_name.lower()
                    and "data" not in agent_name.lower()
                ):
                    agent_list.append(
                        f"- **Engineer Agent** (`{agent_id}`): Code implementation and development"
                    )
                elif "qa" in agent_name.lower():
                    agent_list.append(
                        f"- **QA Agent** (`{agent_id}`): Testing and quality assurance"
                    )
                elif "documentation" in agent_name.lower():
                    agent_list.append(
                        f"- **Documentation Agent** (`{agent_id}`): Documentation creation and maintenance"
                    )
                elif "research" in agent_name.lower():
                    agent_list.append(
                        f"- **Research Agent** (`{agent_id}`): Investigation and analysis"
                    )
                elif "security" in agent_name.lower():
                    agent_list.append(
                        f"- **Security Agent** (`{agent_id}`): Security analysis and protection"
                    )
                elif "version" in agent_name.lower():
                    agent_list.append(
                        f"- **Version Control Agent** (`{agent_id}`): Git operations and version management"
                    )
                elif "ops" in agent_name.lower():
                    agent_list.append(
                        f"- **Ops Agent** (`{agent_id}`): Deployment and operations"
                    )
                elif "data" in agent_name.lower():
                    agent_list.append(
                        f"- **Data Engineer Agent** (`{agent_id}`): Data management and AI API integration"
                    )
                else:
                    agent_list.append(
                        f"- **{clean_name}** (`{agent_id}`): Available for specialized tasks"
                    )

            instructions += "\n".join(agent_list) + "\n\n"

            # Add full agent details
            instructions += "### Agent Details\n\n"
            for agent_name, agent_content in sorted(
                framework_content["agents"].items()
            ):
                instructions += f"#### {agent_name.replace('-', ' ').title()}\n"
                instructions += agent_content + "\n\n"

        # Add orchestration principles
        instructions += """
## Orchestration Principles
1. **Always Delegate**: Never perform direct work - use Task Tool for all implementation
2. **Comprehensive Context**: Provide rich, filtered context to each agent
3. **Track Everything**: Extract all TODO/BUG/FEATURE items systematically
4. **Cross-Agent Coordination**: Orchestrate workflows spanning multiple agents
5. **Results Integration**: Actively receive and integrate agent results

## Task Tool Format
```
**[Agent Name]**: [Clear task description with deliverables]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to [specific considerations].

**Task**: [Detailed task breakdown]
1. [Specific action item 1]
2. [Specific action item 2]
3. [Specific action item 3]

**Context**: [Comprehensive filtered context for this agent]
**Authority**: [Agent's decision-making scope]
**Expected Results**: [Specific deliverables needed]
**Integration**: [How results integrate with other work]
```

## Ticket Extraction Patterns
Extract tickets from these patterns:
- TODO: [description] → TODO ticket
- BUG: [description] → BUG ticket
- FEATURE: [description] → FEATURE ticket
- ISSUE: [description] → ISSUE ticket
- FIXME: [description] → BUG ticket

---
"""

        return instructions

    def get_fallback_capabilities(self) -> str:
        """Return fallback capabilities when dynamic discovery fails.

        Returns:
            Fallback agent capabilities section
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
