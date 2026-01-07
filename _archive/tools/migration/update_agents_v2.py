#!/usr/bin/env python3
"""
Update all agent templates to version 2.0.0 with enhanced dependencies and code hints.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Agent update configurations
AGENT_UPDATES = {
    "research.json": {
        "version": "3.0.0",
        "description": "Advanced codebase analysis with semantic search, complexity metrics, and architecture visualization",
        "dependencies": {
            "python": [
                "pygments>=2.17.0",
                "radon>=6.0.0",
                "semgrep>=1.45.0",
                "lizard>=1.17.0",
                "pydriller>=2.5.0",
                "tree-sitter>=0.21.0",
                "tree-sitter-languages>=1.8.0",
            ]
        },
    },
    "qa.json": {
        "version": "3.0.0",
        "description": "Advanced testing with mutation testing, property-based testing, and coverage analysis",
        "dependencies": {
            "python": [
                "pytest>=7.4.0",
                "pytest-cov>=4.1.0",
                "hypothesis>=6.92.0",
                "mutmut>=2.4.0",
                "pytest-benchmark>=4.0.0",
                "allure-pytest>=2.13.0",
                "faker>=20.0.0",
            ]
        },
    },
    "security.json": {
        "version": "2.0.0",
        "description": "Advanced security scanning with SAST, dependency auditing, and secret detection",
        "dependencies": {
            "python": ["bandit>=1.7.5", "detect-secrets>=1.4.0", "sqlparse>=0.4.4"]
        },
    },
    "data_engineer.json": {
        "version": "2.0.0",
        "description": "Data engineering with quality validation, ETL patterns, and profiling",
        "dependencies": {
            "python": ["pandas>=2.1.0", "dask>=2023.12.0", "sqlalchemy>=2.0.0"]
        },
    },
    "documentation.json": {
        "version": "2.0.0",
        "description": "Documentation generation with API docs, diagrams, and docstring validation",
        "dependencies": {
            "python": [
                "sphinx>=7.2.0",
                "mkdocs>=1.5.0",
                "pydoc-markdown>=4.8.0",
                "diagrams>=0.23.0",
                "mermaid-py>=0.2.0",
                "docstring-parser>=0.15.0",
            ]
        },
    },
    "ops.json": {
        "version": "2.0.0",
        "description": "Infrastructure automation with IaC validation and container security",
        "dependencies": {"python": ["prometheus-client>=0.19.0"]},
    },
    "version_control.json": {
        "version": "2.0.0",
        "description": "Git operations with commit validation and branch strategy enforcement",
        "dependencies": {
            "python": [
                "gitpython>=3.1.40",
                "pre-commit>=3.5.0",
                "commitizen>=3.13.0",
                "gitlint>=0.19.0",
            ]
        },
    },
}


def update_agent(file_path: Path, config: dict):
    """Update a single agent file with new configuration."""

    # Read current agent
    with open(file_path) as f:
        agent = json.load(f)

    # Update version
    agent["agent_version"] = config["version"]

    # Update description
    agent["metadata"]["description"] = config["description"]

    # Update timestamp
    agent["metadata"]["updated_at"] = datetime.now().isoformat() + "Z"

    # Add dependencies if not present
    if "dependencies" not in agent and "dependencies" in config:
        agent["dependencies"] = {
            "python": config["dependencies"]["python"],
            "system": ["python3", "git"],
            "optional": False,
        }
    elif "dependencies" in config:
        # Update existing dependencies
        agent["dependencies"]["python"] = config["dependencies"]["python"]

    # Write back
    with open(file_path, "w") as f:
        json.dump(agent, f, indent=2)

    print(f"✅ Updated {file_path.name} to version {config['version']}")


def main():
    """Update all agent templates."""

    templates_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    )

    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        return 1

    print(f"📁 Updating agents in: {templates_dir}")
    print()

    for agent_file, config in AGENT_UPDATES.items():
        file_path = templates_dir / agent_file

        if not file_path.exists():
            print(f"⚠️  Agent file not found: {agent_file}")
            continue

        try:
            update_agent(file_path, config)
        except Exception as e:
            print(f"❌ Failed to update {agent_file}: {e}")

    print("\n✨ Agent updates complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
