#!/usr/bin/env python3
"""Simple test to check if Claude recognizes subagent Markdown files."""

import os
import shutil
from datetime import datetime
from pathlib import Path

import yaml


def create_simple_agent(agent_dir: Path):
    """Create a simple test agent."""

    agent_content = """---
name: test-agent
description: "Simple test agent for POC validation"
---

You are a test agent created to validate Claude's subagent loading.

When called, always respond with: "Test Agent Active - Loaded from {}"
""".format(
        agent_dir
    )

    agent_file = agent_dir / "test-agent.md"
    agent_file.write_text(agent_content)
    print(f"✓ Created: {agent_file}")

    # Also create yaml version
    agent_yaml = agent_dir / "test-agent.yaml"
    agent_yaml.write_text(agent_content)
    print(f"✓ Created: {agent_yaml}")


def main():
    print("🧪 Claude Subagent Location Test")
    print("=" * 60)

    # Test different locations
    locations = [
        Path.cwd() / ".claude" / "agents",
        Path.cwd() / ".claude-mpm" / "agents",
        Path.home() / ".claude" / "agents",
    ]

    for location in locations:
        print(f"\n📁 Testing: {location}")

        # Create directory
        location.mkdir(parents=True, exist_ok=True)

        # Create test agent
        create_simple_agent(location)

        # List contents
        files = list(location.glob("*"))
        print(f"  Files: {[f.name for f in files]}")

    print("\n📋 Summary:")
    print("Test agents created in multiple locations.")
    print("Now run Claude manually to test which location is recognized:")
    print("\n1. In project root: claude")
    print("2. Ask: 'Can you list available subagents?'")
    print("3. Try: 'Delegate to test-agent: Say hello'")

    print("\n🔧 Environment variables to try:")
    print(f"export CLAUDE_CONFIG_DIR={Path.cwd() / '.claude'}")
    print(f"export CLAUDE_AGENT_DIR={Path.cwd() / '.claude' / 'agents'}")


if __name__ == "__main__":
    main()