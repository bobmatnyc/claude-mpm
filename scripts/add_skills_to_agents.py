#!/usr/bin/env python3
"""
Script to add skills field to agent templates without aggressive pruning.
Only prunes instructions if they explicitly reference inherited base templates.
"""
import json
from pathlib import Path
from typing import Dict, List

# Skill mappings by agent type
SKILL_MAPPINGS = {
    # Engineer agents - all language-specific
    "engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "python_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "typescript_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "react_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "nextjs_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
        "docker-containerization",
    ],
    "golang_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "rust_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "java_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "php-engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "ruby-engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "dart_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "data_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "performance-profiling",
        "database-migration",
        "code-review",
        "git-workflow",
    ],
    "web_ui": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "code-review",
        "refactoring-patterns",
        "git-workflow",
    ],
    "refactoring_engineer": [
        "systematic-debugging",
        "refactoring-patterns",
        "code-review",
        "performance-profiling",
        "git-workflow",
    ],
    # QA agents
    "qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
    ],
    "web_qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
    ],
    "api_qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "api-documentation",
    ],
    # Ops agents
    "ops": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging",
    ],
    "local_ops_agent": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging",
    ],
    "gcp_ops_agent": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging",
    ],
    "vercel_ops_agent": [
        "docker-containerization",
        "git-workflow",
        "systematic-debugging",
    ],
    "clerk-ops": ["security-scanning", "git-workflow", "systematic-debugging"],
    "agentic-coder-optimizer": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging",
    ],
    "project_organizer": ["git-workflow", "systematic-debugging"],
    # Documentation agent
    "documentation": ["api-documentation", "code-review", "git-workflow"],
    "ticketing": ["git-workflow"],
    # Security agent
    "security": ["security-scanning", "code-review", "systematic-debugging"],
    # Other specialized agents
    "code_analyzer": ["code-review", "refactoring-patterns", "systematic-debugging"],
    "version_control": ["git-workflow"],
    "refactoring": [
        "refactoring-patterns",
        "code-review",
        "systematic-debugging",
        "performance-profiling",
        "test-driven-development",
    ],
    "content": [
        # Content agents typically don't use code skills
    ],
    "imagemagick": [
        # Specialized image processing, no general coding skills
    ],
    "research": ["systematic-debugging"],  # For analytical problem-solving
    "analysis": ["systematic-debugging", "code-review"],
    "product": [
        # Product owners focus on requirements, not implementation
    ],
    "system": [
        # System agents manage other agents, different skillset
    ],
    "memory_manager": [
        # Memory management is specialized, no general coding skills
    ],
}


def get_agent_type(filename: str, data: Dict) -> str:
    """Extract agent type from filename or data."""
    if "agent_type" in data:
        return data["agent_type"]
    # Derive from filename
    return filename.replace(".json", "").replace("-", "_")


def process_agent_file(filepath: Path) -> Dict:
    """Process a single agent file to add skills field."""
    with open(filepath) as f:
        data = json.load(f)

    agent_type = get_agent_type(filepath.stem, data)

    # Check if already has skills
    has_skills = "skills" in data and isinstance(data["skills"], list)

    # Get suggested skills
    suggested_skills = SKILL_MAPPINGS.get(agent_type, [])

    result = {
        "filename": filepath.name,
        "agent_type": agent_type,
        "had_skills": has_skills,
        "skills_added": False,
        "skills_count": 0,
    }

    # Add skills if not present and we have suggestions
    if not has_skills and suggested_skills:
        data["skills"] = suggested_skills
        result["skills_added"] = True
        result["skills_count"] = len(suggested_skills)

        # Write back to file
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")  # Add trailing newline
    elif has_skills:
        result["skills_count"] = len(data.get("skills", []))

    return result


def main():
    """Main execution function."""
    templates_dir = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates"
    )

    # Find all agent templates
    agent_files = sorted(templates_dir.glob("*.json"))

    print(f"Found {len(agent_files)} agent templates\n")

    # Process all agents
    results = []
    for filepath in agent_files:
        try:
            result = process_agent_file(filepath)
            results.append(result)

            if result["skills_added"]:
                print(
                    f"✓ Added {result['skills_count']} skills to {result['filename']}"
                )
        except Exception as e:
            print(f"✗ Error processing {filepath.name}: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal agents processed: {len(results)}")
    print(f"Agents with skills added: {sum(1 for r in results if r['skills_added'])}")
    print(f"Agents already had skills: {sum(1 for r in results if r['had_skills'])}")
    print(
        f"Agents with no skill mapping: {sum(1 for r in results if r['skills_count'] == 0)}"
    )

    # List agents that got skills added
    added = [r for r in results if r["skills_added"]]
    if added:
        print("\nAgents updated with skills:")
        for r in added:
            print(f"  - {r['filename']}: {r['skills_count']} skills")


if __name__ == "__main__":
    main()
