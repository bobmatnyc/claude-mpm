#!/usr/bin/env python3
"""Remove remaining ticketing sections from agent templates."""

import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Templates directory
templates_dir = (
    Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
)


def remove_ticketing_sections(content):
    """Remove entire ticketing-related sections."""

    # Remove "When to Create Subtask Tickets" sections
    content = re.sub(
        r"### When to Create Subtask Tickets\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Ticket Comment Patterns" sections
    content = re.sub(
        r"### Ticket Comment Patterns\n.*?(?=###|\n##|\Z)", "", content, flags=re.DOTALL
    )

    # Remove "Cross-Agent Ticket Coordination" sections
    content = re.sub(
        r"### Cross-Agent Ticket Coordination\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Ticket Reference Handling" sections
    content = re.sub(
        r"### Ticket Reference Handling\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Bug Ticket Creation Pattern" sections
    content = re.sub(
        r"### Bug Ticket Creation Pattern\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Deployment Ticket Pattern" sections
    content = re.sub(
        r"### Deployment Ticket Pattern\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Security Finding Pattern" sections
    content = re.sub(
        r"### Security Finding Pattern\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Compliance Ticket Pattern" sections
    content = re.sub(
        r"### Compliance Ticket Pattern\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Research Documentation Pattern" sections
    content = re.sub(
        r"### Research Documentation Pattern\n.*?(?=###|\n##|\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove "Data Migration Pattern" sections
    content = re.sub(
        r"### Data Migration Pattern\n.*?(?=###|\n##|\Z)", "", content, flags=re.DOTALL
    )

    # Remove "API Integration Pattern" sections
    content = re.sub(
        r"### API Integration Pattern\n.*?(?=###|\n##|\Z)", "", content, flags=re.DOTALL
    )

    # Remove "Code Review Pattern" sections
    content = re.sub(
        r"### Code Review Pattern\n.*?(?=###|\n##|\Z)", "", content, flags=re.DOTALL
    )

    # Remove "Bug Fix Pattern" sections
    content = re.sub(
        r"### Bug Fix Pattern\n.*?(?=###|\n##|\Z)", "", content, flags=re.DOTALL
    )

    # Remove any remaining lines with ticket references
    content = re.sub(r".*ticket.*\n", "", content, flags=re.IGNORECASE)
    content = re.sub(r".*ISS-\d+.*\n", "", content)
    content = re.sub(r".*TSK-\d+.*\n", "", content)
    content = re.sub(r".*EP-\d+.*\n", "", content)

    # Clean up excessive newlines
    content = re.sub(r"\n{4,}", "\n\n\n", content)
    return re.sub(r"\n{3,}$", "\n", content)


# Process each agent template
for agent_file in templates_dir.glob("*_agent.md"):
    content = agent_file.read_text()
    original_len = len(content)

    # Remove ticketing sections
    content = remove_ticketing_sections(content)

    # Write back
    agent_file.write_text(content)

    new_len = len(content)
    if new_len < original_len:
        print(f"✓ Cleaned {agent_file.name} (removed {original_len - new_len} chars)")
    else:
        print(f"  {agent_file.name} (no changes)")

print("\nDone!")
