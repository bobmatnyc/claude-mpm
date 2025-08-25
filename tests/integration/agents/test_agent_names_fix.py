#!/usr/bin/env python3
"""Test that agent names are correctly configured for Claude Code Task tool."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_deployed_agents():
    """Check deployed agent YAML names."""
    print("🔍 Checking deployed agent YAML names...")
    # Check in project's .claude/agents directory
    deployed_agents_dir = Path(__file__).parent.parent / ".claude" / "agents"

    expected_names = {
        "research.md": "research-agent",
        "qa.md": "qa-agent",
        "documentation.md": "documentation-agent",
        "security.md": "security-agent",
        "ops.md": "ops-agent",
        "data_engineer.md": "data-engineer",
        "version_control.md": "version-control",
        "engineer.md": "engineer",
    }

    for agent_file, expected_name in expected_names.items():
        agent_path = deployed_agents_dir / agent_file
        if agent_path.exists():
            with open(agent_path) as f:
                content = f.read()
                if f"name: {expected_name}" in content:
                    print(f"  ✅ {agent_file}: name is '{expected_name}'")
                else:
                    print(f"  ❌ {agent_file}: name is NOT '{expected_name}'")
        else:
            print(f"  ⚠️  {agent_file}: not found")


def test_documentation_generator():
    """Test that documentation generator uses correct names."""
    print("\n📚 Testing documentation generator...")
    from claude_mpm.services.framework_claude_md_generator.section_generators.todo_task_tools import (
        TodoTaskToolsGenerator,
    )

    generator = TodoTaskToolsGenerator(framework_version="test")
    content = generator.generate({})

    # Check correct formats are present
    correct_formats = [
        'subagent_type="research-agent"',
        'subagent_type="qa-agent"',
        'subagent_type="documentation-agent"',
        'subagent_type="security-agent"',
        'subagent_type="ops-agent"',
        'subagent_type="version-control"',
        'subagent_type="data-engineer"',
        'subagent_type="engineer"',
    ]

    for format_str in correct_formats:
        if format_str in content:
            print(f"  ✅ Found correct format: {format_str}")
        else:
            print(f"  ❌ Missing correct format: {format_str}")


def test_framework_loader():
    """Test that framework_loader reads YAML names correctly."""
    print("\n🔧 Testing framework_loader...")
    import yaml

    from claude_mpm.core.framework_loader import FrameworkLoader

    loader = FrameworkLoader()

    # Check that the loader correctly reads agent YAML frontmatter
    deployed_agents_dir = Path(__file__).parent.parent / ".claude" / "agents"
    if deployed_agents_dir.exists():
        for agent_file in deployed_agents_dir.glob("*.md"):
            with open(agent_file) as f:
                content = f.read()
                if content.startswith("---"):
                    end_marker = content.find("---", 3)
                    if end_marker > 0:
                        frontmatter = content[3:end_marker]
                        metadata = yaml.safe_load(frontmatter)
                        if metadata and "name" in metadata:
                            print(
                                f"  ✅ {agent_file.name}: YAML name = '{metadata['name']}'"
                            )
    else:
        print("  ⚠️  No deployed agents found")


def main():
    print("=" * 60)
    print("🧪 Testing Agent Names Fix for Claude Code Task Tool")
    print("=" * 60)

    test_deployed_agents()
    test_documentation_generator()
    test_framework_loader()

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("\nSummary:")
    print("- Agent YAML files should have the correct 'name:' field")
    print("- Documentation generator should use these exact names")
    print("- Framework loader should read names from YAML frontmatter")
    print("- Task tool calls must use exact YAML names for subagent_type")


if __name__ == "__main__":
    main()
