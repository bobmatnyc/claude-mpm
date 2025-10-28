#!/usr/bin/env python3
"""Bump agent versions for skills integration."""

import json
from pathlib import Path

AGENTS_DIR = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates")

# All agents that received skills field (using actual file names)
AGENTS_WITH_SKILLS = [
    "agent-manager",
    "agentic-coder-optimizer",
    "api_qa",
    "clerk-ops",
    "code_analyzer",
    "content-agent",
    "dart_engineer",
    "data_engineer",
    "documentation",
    "engineer",
    "gcp_ops_agent",
    "golang_engineer",
    "imagemagick",
    "java_engineer",
    "local_ops_agent",
    "nextjs_engineer",
    "ops",
    "php-engineer",
    "project_organizer",
    "python_engineer",
    "qa",
    "react_engineer",
    "refactoring_engineer",
    "ruby-engineer",
    "rust_engineer",
    "security",
    "ticketing",
    "typescript_engineer",
    "vercel_ops_agent",
    "version_control",
    "web_ui",
]


def bump_patch_version(version_str):
    """Bump patch version (3.0.0 → 3.0.1)."""
    parts = version_str.split(".")
    if len(parts) == 3:
        major, minor, patch = parts
        new_patch = str(int(patch) + 1)
        return f"{major}.{minor}.{new_patch}"
    return version_str


def bump_agent_version(agent_file):
    """Bump version in agent JSON file."""
    with open(agent_file) as f:
        data = json.load(f)

    old_version = data.get("version", "1.0.0")
    new_version = bump_patch_version(old_version)
    data["version"] = new_version

    with open(agent_file, "w") as f:
        json.dump(data, f, indent=2)

    return old_version, new_version


def main():
    """Main execution function."""
    print("Bumping agent versions for skills integration...")
    print("=" * 60)

    bumped = []
    failed = []

    for agent_name in AGENTS_WITH_SKILLS:
        agent_file = AGENTS_DIR / f"{agent_name}.json"
        if agent_file.exists():
            try:
                old, new = bump_agent_version(agent_file)
                bumped.append((agent_name, old, new))
                print(f"✓ {agent_name}: {old} → {new}")
            except Exception as e:
                failed.append((agent_name, str(e)))
                print(f"✗ {agent_name}: ERROR - {e}")
        else:
            failed.append((agent_name, "file not found"))
            print(f"✗ {agent_name}: file not found")

    print("\n" + "=" * 60)
    print(f"Summary: {len(bumped)} bumped, {len(failed)} failed")

    if failed:
        print("\nFailed agents:")
        for agent, reason in failed:
            print(f"  - {agent}: {reason}")

    return bumped, failed


if __name__ == "__main__":
    bumped, failed = main()
