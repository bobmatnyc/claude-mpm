#!/usr/bin/env python3
"""Show the actual system prompt that PM Claude receives."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import SimpleClaudeRunner


def show_system_prompt():
    """Display the complete system prompt that would be sent to Claude."""
    print("PM Claude System Prompt")
    print("=" * 80)

    # Create runner and get system prompt
    runner = SimpleClaudeRunner()
    system_prompt = runner._create_system_prompt()

    if not system_prompt:
        print("ERROR: Failed to load system prompt")
        return

    # Show stats
    print(f"Length: {len(system_prompt)} characters")
    print(f"Lines: {len(system_prompt.splitlines())}")
    print(
        f"Placeholder present: {'YES (ERROR!)' if '{{capabilities-list}}' in system_prompt else 'NO (Good!)'}"
    )

    print("\n" + "=" * 80)
    print("FULL SYSTEM PROMPT:")
    print("=" * 80)
    print(system_prompt)
    print("=" * 80)

    # Highlight the capabilities section
    if "## Agent Names & Capabilities" in system_prompt:
        print("\n✓ Dynamic agent capabilities successfully injected!")

        # Count agents mentioned
        agents = [
            "research",
            "engineer",
            "qa",
            "documentation",
            "security",
            "ops",
            "version_control",
            "data_engineer",
        ]
        found = sum(1 for agent in agents if agent in system_prompt)
        print(f"✓ Found {found}/{len(agents)} expected agents in capabilities")
    else:
        print("\n❌ WARNING: Agent capabilities section not found!")


if __name__ == "__main__":
    show_system_prompt()
