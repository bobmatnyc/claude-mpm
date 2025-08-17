#!/usr/bin/env python3
"""Debug the deployment logic in detail"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json
import re
from pathlib import Path


def check_research_agent():
    """Check research agent in detail"""
    # Paths
    agent_file = Path.home() / ".claude" / "agents" / "research.md"
    template_file = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
        / "research.json"
    )

    print("=== Research Agent Analysis ===")
    print(f"Agent file exists: {agent_file.exists()}")
    print(f"Template file exists: {template_file.exists()}")

    if agent_file.exists():
        content = agent_file.read_text()
        version_match = re.search(
            r'^version:\s*["\']?([^"\'\n]+)["\']?', content, re.MULTILINE
        )
        if version_match:
            print(f"Deployed version: {version_match.group(1)}")

    if template_file.exists():
        template_data = json.loads(template_file.read_text())
        print(f"Template agent_version: {template_data.get('agent_version')}")
        print(f"Template version: {template_data.get('version')}")

    # Now trace through the deployment logic
    print("\n=== Deployment Logic Trace ===")

    # Simulate what happens in deploy_agents
    target_dir = Path.home() / ".claude" / "agents"
    template_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    )

    # List templates matching actual file pattern
    print(f"\nLooking for templates in: {template_dir}")
    templates = list(template_dir.glob("*.json"))
    print(f"Found {len(templates)} templates")

    # Check if research.json is in the list
    research_template = template_dir / "research.json"
    print(f"\nresearch.json in templates: {research_template in templates}")
    print(f"research.json path: {research_template}")
    print(f"research.json exists: {research_template.exists()}")


if __name__ == "__main__":
    check_research_agent()
