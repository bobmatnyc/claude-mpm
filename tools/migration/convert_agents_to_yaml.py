#!/usr/bin/env python3
"""Convert Claude MPM agents to Claude Code native YAML format."""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def convert_agent_to_yaml(agent_path: Path, output_dir: Path):
    """Convert a markdown agent to Claude Code YAML format."""

    agent_name = agent_path.stem.replace("_agent", "").replace("_", "-")

    # Read the original agent content
    with open(agent_path) as f:
        content = f.read()

    # Extract the agent description from the content
    lines = content.split("\n")
    description = ""
    for line in lines:
        if line.strip().startswith("You are the") and "Agent" in line:
            # Extract a cleaner description
            desc_parts = line.replace("You are the", "").replace("Agent", "").strip()
            description = f"{desc_parts} specialist"
            break

    if not description:
        description = (
            f"{agent_name.replace('-', ' ').title()} agent for specialized tasks"
        )

    # Define tools based on agent type
    tools_map = {
        "engineer": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        "qa": ["Read", "Bash", "Grep", "Write", "Edit"],
        "documentation": ["Read", "Write", "Edit", "Grep"],
        "research": ["Read", "Grep", "WebSearch", "WebFetch"],
        "security": ["Read", "Grep", "Bash"],
        "ops": ["Read", "Bash", "Write", "Edit"],
        "data-engineer": ["Read", "Write", "Edit", "Bash", "Grep"],
        "version-control": ["Bash", "Read", "Write"],
    }

    # Get tools for this agent
    tools = tools_map.get(agent_name, ["Read", "Write", "Edit"])

    # Create YAML frontmatter
    yaml_config = {
        "name": agent_name,
        "description": description.strip(),
        "version": "1.0.0",
        "author": "claude-mpm",
        "tags": [agent_name.split("-")[0], "mpm", "system"],
        "tools": tools,
        "priority": "high" if agent_name in ["engineer", "qa"] else "medium",
        "timeout": 600,
        "max_tokens": 8192,
        "temperature": 0.3 if agent_name in ["qa", "security"] else 0.5,
        # Claude MPM specific metadata
        "source": "claude-mpm-system",
        "template": f"{agent_name}-base",
        "created": datetime.now().isoformat(),
        # Context management
        "context_isolation": "moderate",
        "preserve_context": True,
        # Resource limits
        "memory_limit": 1024,
        "cpu_limit": 50,
        # Access control
        "file_access": "project",
        "network_access": agent_name == "research",
    }

    # Create the output file
    output_file = output_dir / f"{agent_name}.md"

    with open(output_file, "w") as f:
        # Write YAML frontmatter
        f.write("---\n")
        yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
        f.write("---\n\n")

        # Write the agent prompt with enhancements
        f.write("# System Prompt\n\n")
        f.write(content)
        f.write("\n\n")

        # Add Claude Code specific instructions
        f.write("## Subagent Guidelines\n\n")
        f.write("When executing tasks as a subagent:\n")
        f.write("1. Focus exclusively on the delegated task\n")
        f.write("2. Use only the tools provided in your configuration\n")
        f.write("3. Report results in a structured format\n")
        f.write("4. Indicate completion status clearly\n")
        f.write("5. Preserve context between related tasks when requested\n")

    print(f"✓ Converted: {agent_name} -> {output_file}")
    return output_file


def main():
    print("🔄 Converting Claude MPM Agents to Native YAML Format")
    print("=" * 60)

    # Source and destination directories
    src_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    )

    # Create two output directories
    system_agents_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "system"
    )
    local_agents_dir = Path.cwd() / ".claude" / "agents"

    # Create directories
    system_agents_dir.mkdir(parents=True, exist_ok=True)
    local_agents_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Source: {src_dir}")
    print(f"📁 System Storage: {system_agents_dir}")
    print(f"📁 Local Deployment: {local_agents_dir}")

    # Convert all agents
    print("\n🔧 Converting agents...")

    agent_files = list(src_dir.glob("*_agent.md"))
    converted_count = 0

    for agent_file in agent_files:
        try:
            # Convert to system storage
            system_output = convert_agent_to_yaml(agent_file, system_agents_dir)

            # Also copy to local deployment for testing
            local_output = local_agents_dir / system_output.name
            shutil.copy2(system_output, local_output)
            print(f"  ↳ Deployed to: {local_output}")

            converted_count += 1
        except Exception as e:
            print(f"❌ Error converting {agent_file.name}: {e}")

    # Create a manifest file
    manifest = {
        "version": "1.0.0",
        "generated": datetime.now().isoformat(),
        "agents": [],
    }

    for agent_file in system_agents_dir.glob("*.md"):
        with open(agent_file) as f:
            content = f.read()
            # Extract YAML frontmatter
            if content.startswith("---"):
                yaml_end = content.find("---", 3)
                if yaml_end > 0:
                    yaml_content = content[3:yaml_end]
                    agent_data = yaml.safe_load(yaml_content)
                    manifest["agents"].append(
                        {
                            "name": agent_data["name"],
                            "description": agent_data["description"],
                            "version": agent_data["version"],
                            "file": agent_file.name,
                        }
                    )

    # Save manifest
    manifest_file = system_agents_dir / "manifest.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False)

    print("\n✅ Conversion Complete!")
    print(f"  - Converted: {converted_count} agents")
    print(f"  - System agents: {system_agents_dir}")
    print(f"  - Local deployment: {local_agents_dir}")
    print(f"  - Manifest: {manifest_file}")

    print("\n📋 Next Steps:")
    print("1. Test agent loading: claude (in project root)")
    print("2. List agents: Task list agents")
    print("3. Test delegation: Task('engineer: Create a hello world function')")


if __name__ == "__main__":
    main()
