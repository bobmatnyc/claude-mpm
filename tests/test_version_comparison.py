#!/usr/bin/env python3
"""Simple test to verify version comparison works correctly."""

import json
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


def main():
    """Test that highest version wins across sources."""

    # Create a temporary project directory
    temp_dir = Path(tempfile.mkdtemp(prefix="version_test_"))
    project_agents = temp_dir / ".claude-mpm" / "agents"
    project_agents.mkdir(parents=True)

    print("Testing Version Comparison Across Sources")
    print("=" * 50)

    # Create a project-specific QA agent with LOWER version than system
    qa_agent = {
        "agent_version": "1.0.0",  # System has 3.2.0
        "metadata": {"name": "Qa Agent", "description": "Project-specific QA agent"},
        "capabilities": {"tools": ["Read"], "model": "sonnet"},
        "instructions": "# Project QA Agent v1.0.0\n\nThis is a project-specific QA agent.",
    }

    # Create a project-specific Engineer agent with HIGHER version than system
    engineer_agent = {
        "agent_version": "5.0.0",  # System might have lower version
        "metadata": {
            "name": "Engineer Agent",
            "description": "Project-specific Engineer agent",
        },
        "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
        "instructions": "# Project Engineer Agent v5.0.0\n\nThis is a project-specific engineer.",
    }

    # Write the agents
    (project_agents / "qa.json").write_text(json.dumps(qa_agent, indent=2))
    (project_agents / "engineer.json").write_text(json.dumps(engineer_agent, indent=2))

    print(f"Created project agents in: {project_agents}")
    print("  - qa.json (v1.0.0) - LOWER than system")
    print("  - engineer.json (v5.0.0) - HIGHER than system")
    print()

    # Deploy agents
    target_dir = temp_dir / ".claude"
    service = AgentDeploymentService(working_directory=temp_dir)

    print("Deploying agents with version comparison...")
    results = service.deploy_agents(
        target_dir=target_dir,
        deployment_mode="update",  # This should use multi-source
        force_rebuild=True,
    )

    print()
    print("Deployment Results:")
    print("-" * 30)

    if results.get("multi_source"):
        print("✓ Multi-source deployment was used")
    else:
        print("✗ Multi-source deployment was NOT used")

    # Check deployed agents
    deployed_dir = target_dir / "agents"
    if deployed_dir.exists():
        deployed_files = list(deployed_dir.glob("*.md"))
        print(f"\nDeployed {len(deployed_files)} agents:")

        for agent_file in sorted(deployed_files):
            content = agent_file.read_text()

            # Extract version and source
            version = None
            source = None
            for line in content.split("\n"):
                stripped_line = line.strip()
                if stripped_line.startswith("version:"):
                    version = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("source:"):
                    source = stripped_line.split(":", 1)[1].strip()

            print(f"  {agent_file.stem:15} v{version:10} from {source}")

            # Verify expectations
            if agent_file.stem == "qa":
                if version == "3.2.0" and source == "system":
                    print("    ✓ Correctly using system version (project had v1.0.0)")
                else:
                    print(
                        f"    ✗ ERROR: Expected system v3.2.0, got {source} v{version}"
                    )

            elif agent_file.stem == "engineer":
                if version == "5.0.0" and source == "project":
                    print("    ✓ Correctly using project version (higher than system)")
                else:
                    print(f"    ✗ Should use project v5.0.0, got {source} v{version}")

    print()
    print("=" * 50)
    print("Test Complete!")

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
