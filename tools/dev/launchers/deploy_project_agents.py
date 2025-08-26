#!/usr/bin/env python3
"""
Deploy project agents from .claude-mpm/agents/ to .claude/agents/
Converts JSON format to Markdown with frontmatter for Claude Code compatibility.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict


def convert_json_to_markdown(agent_data: Dict[str, Any]) -> str:
    """Convert JSON agent to Markdown format with frontmatter."""

    # Extract metadata
    metadata = agent_data.get("metadata", {})
    capabilities = agent_data.get("capabilities", {})

    # Build frontmatter
    frontmatter = []
    frontmatter.append("---")
    frontmatter.append(f'name: {agent_data.get("agent_id", "unknown")}')
    frontmatter.append(f'description: {metadata.get("description", "No description")}')
    frontmatter.append(f'version: {agent_data.get("agent_version", "1.0.0")}')
    frontmatter.append(f'base_version: {agent_data.get("base_version", "0.3.0")}')
    frontmatter.append(f'author: {metadata.get("author", "claude-mpm-project")}')

    # Handle tools - no spaces after commas!
    tools = capabilities.get("tools", [])
    if tools:
        frontmatter.append(f'tools: {",".join(tools)}')

    # Handle model
    model = capabilities.get("model", "sonnet")
    frontmatter.append(f"model: {model}")

    frontmatter.append("---")

    # Get instructions
    instructions = agent_data.get("instructions", "")

    # Combine frontmatter and instructions
    return "\n".join(frontmatter) + "\n\n" + instructions


def deploy_project_agents():
    """Deploy all project agents from .claude-mpm/agents/ to .claude/agents/

    IMPORTANT: The PM (Project Manager) agent is NEVER deployed as a subagent.
    PM is the main Claude instance that orchestrates other agents, not a subagent itself.
    """

    # CRITICAL: PM agent must NEVER be deployed
    # PM is the main Claude instance, not a subagent
    EXCLUDED_AGENTS = {"pm", "project_manager"}  # Never deploy these

    # Find project root (where .claude-mpm exists)
    project_root = Path.cwd()
    while project_root != Path("/"):
        if (project_root / ".claude-mpm").exists():
            break
        project_root = project_root.parent
    else:
        print("❌ Could not find .claude-mpm directory in current project")
        return False

    source_dir = project_root / ".claude-mpm" / "agents"
    target_dir = project_root / ".claude" / "agents"

    if not source_dir.exists():
        print(f"❌ Source directory does not exist: {source_dir}")
        return False

    # Create target directory if needed
    target_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON agent files
    json_files = list(source_dir.glob("*.json"))

    if not json_files:
        print(f"❌ No JSON agent files found in {source_dir}")
        return False

    print(
        f"🚀 Deploying {len(json_files)} project agents from {source_dir} to {target_dir}"
    )

    deployed = []
    errors = []
    skipped = []

    for json_file in json_files:
        try:
            # Read JSON agent
            with open(json_file, encoding="utf-8") as f:
                agent_data = json.load(f)

            # Check if this agent should be excluded
            agent_id = agent_data.get("agent_id", json_file.stem)
            if agent_id.lower() in EXCLUDED_AGENTS:
                skipped.append(agent_id)
                print(
                    f"  ⚠️  Skipping {agent_id} (PM is the main Claude instance, not a subagent)"
                )
                continue

            # Convert to Markdown
            markdown_content = convert_json_to_markdown(agent_data)

            # Write to target
            target_file = target_dir / f"{agent_id}.md"

            with open(target_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            deployed.append(agent_id)
            print(f"  ✓ Deployed {agent_id}")

        except Exception as e:
            errors.append(f"{json_file.name}: {e}")
            print(f"  ❌ Failed to deploy {json_file.name}: {e}")

    # Summary
    print("\n📊 Deployment Summary:")
    print(f"  Successfully deployed: {len(deployed)} agents")
    if skipped:
        print(f"  Skipped (excluded): {len(skipped)} agents ({', '.join(skipped)})")
    if errors:
        print(f"  Failed: {len(errors)} agents")

    # Also clean up any accidentally deployed PM agent files
    for excluded in EXCLUDED_AGENTS:
        excluded_file = target_dir / f"{excluded}.md"
        if excluded_file.exists():
            excluded_file.unlink()
            print(f"  🧹 Cleaned up accidentally deployed {excluded}.md")

    return len(errors) == 0


if __name__ == "__main__":
    success = deploy_project_agents()
    sys.exit(0 if success else 1)
