#!/usr/bin/env python3
"""
Script to prune redundant instructions from agent templates and add skills field.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

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
        "git-workflow"
    ],
    "python_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "typescript_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "react_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
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
        "docker-containerization"
    ],
    "golang_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "rust_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "java_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "php-engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "ruby-engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "dart_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "security-scanning",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "data_engineer": [
        "test-driven-development",
        "systematic-debugging",
        "performance-profiling",
        "database-migration",
        "code-review",
        "git-workflow"
    ],
    "web_ui": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "code-review",
        "refactoring-patterns",
        "git-workflow"
    ],
    "refactoring_engineer": [
        "systematic-debugging",
        "refactoring-patterns",
        "code-review",
        "performance-profiling",
        "git-workflow"
    ],
    # QA agents
    "qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling"
    ],
    "web_qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling"
    ],
    "api_qa": [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
        "api-documentation"
    ],
    # Ops agents
    "ops": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging"
    ],
    "local_ops_agent": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging"
    ],
    "gcp_ops_agent": [
        "docker-containerization",
        "database-migration",
        "security-scanning",
        "git-workflow",
        "systematic-debugging"
    ],
    "vercel_ops_agent": [
        "docker-containerization",
        "git-workflow",
        "systematic-debugging"
    ],
    "clerk-ops": [
        "security-scanning",
        "git-workflow",
        "systematic-debugging"
    ],
    # Documentation agent
    "documentation": [
        "api-documentation",
        "code-review",
        "git-workflow"
    ],
    # Security agent
    "security": [
        "security-scanning",
        "code-review",
        "systematic-debugging"
    ],
    # Other specialized agents
    "code_analyzer": [
        "code-review",
        "refactoring-patterns",
        "systematic-debugging"
    ],
    "version_control": [
        "git-workflow"
    ]
}

def count_lines(text: str) -> int:
    """Count non-empty lines in text."""
    return len([line for line in text.split('\n') if line.strip()])

def has_skills_field(data: Dict) -> bool:
    """Check if agent template already has skills field."""
    return "skills" in data and isinstance(data["skills"], list)

def get_agent_type(filename: str, data: Dict) -> str:
    """Extract agent type from filename or data."""
    if "agent_type" in data:
        return data["agent_type"]
    # Derive from filename
    return filename.replace(".json", "").replace("-", "_")

def analyze_agent(filepath: Path) -> Dict:
    """Analyze an agent template file."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    instructions = data.get("instructions", "")
    lines_before = count_lines(instructions)

    agent_type = get_agent_type(filepath.stem, data)
    has_skills = has_skills_field(data)
    suggested_skills = SKILL_MAPPINGS.get(agent_type, [])

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "agent_type": agent_type,
        "lines_before": lines_before,
        "has_skills": has_skills,
        "current_skills": data.get("skills", []),
        "suggested_skills": suggested_skills,
        "data": data
    }

def should_prune_instructions(agent_type: str, instructions: str) -> bool:
    """Determine if instructions should be pruned based on content."""
    # Keywords that indicate redundant content covered by skills
    redundant_keywords = [
        "test-driven development",
        "tdd",
        "red-green-refactor",
        "write tests first",
        "debug first protocol",
        "isolate the problem",
        "root cause",
        "async testing",
        "performance profiling",
        "security scanning",
        "code review",
        "refactoring",
        "git workflow",
        "docker",
        "containerization",
        "database migration"
    ]

    instructions_lower = instructions.lower()
    matches = sum(1 for keyword in redundant_keywords if keyword in instructions_lower)

    # If instructions contain 3+ redundant keywords, they should be pruned
    return matches >= 3

def prune_instructions(instructions: str, agent_type: str) -> str:
    """Prune redundant instructions while keeping agent-specific content."""

    # Don't prune if instructions already reference BASE_ENGINEER.md or base instructions
    if "BASE_ENGINEER.md" in instructions or "BASE_AGENT" in instructions:
        return instructions

    # Don't prune if instructions are already concise (<200 chars)
    if len(instructions) < 200:
        return instructions

    # For agents with extensive redundant content (>500 lines), use special handling
    line_count = count_lines(instructions)

    if line_count > 500:
        # Extract just the identity/focus from very long instructions
        lines = instructions.split('\n')

        # Look for identity markers in first 50 lines
        identity_lines = []
        for line in lines[:50]:
            line_stripped = line.strip()
            if line_stripped.startswith('#') and len(line_stripped) < 100:
                # Keep headers
                identity_lines.append(line_stripped)
            elif any(keyword in line.lower() for keyword in ['you are', 'identity', 'focus', 'speciali']):
                if len(line_stripped) > 0 and len(line_stripped) < 300:
                    identity_lines.append(line_stripped)

            if len(identity_lines) >= 5:  # Got enough context
                break

        if identity_lines:
            return '\n'.join(identity_lines[:5])

        # Fallback to first paragraph
        paragraphs = [p.strip() for p in instructions.split('\n\n') if p.strip()]
        if paragraphs:
            return paragraphs[0][:500]  # First paragraph, max 500 chars

    # For moderately redundant content, just return as-is
    # Skills will provide the detailed guidance
    return instructions

def update_agent(analysis: Dict, dry_run: bool = True) -> Dict:
    """Update an agent template with pruned instructions and skills."""
    data = analysis["data"]
    agent_type = analysis["agent_type"]

    # Get current instructions
    old_instructions = data.get("instructions", "")
    old_lines = count_lines(old_instructions)

    # Prune instructions if needed
    new_instructions = prune_instructions(old_instructions, agent_type)
    new_lines = count_lines(new_instructions)

    # Add or update skills field
    if not analysis["has_skills"] and analysis["suggested_skills"]:
        data["skills"] = analysis["suggested_skills"]
        skills_added = True
    else:
        skills_added = False

    # Update instructions if pruned
    instructions_changed = new_instructions != old_instructions
    if instructions_changed:
        data["instructions"] = new_instructions

    # Calculate metrics
    lines_removed = old_lines - new_lines
    reduction_pct = (lines_removed / old_lines * 100) if old_lines > 0 else 0

    result = {
        "filename": analysis["filename"],
        "agent_type": agent_type,
        "lines_before": old_lines,
        "lines_after": new_lines,
        "lines_removed": lines_removed,
        "reduction_pct": reduction_pct,
        "skills_added": skills_added,
        "skills_count": len(data.get("skills", [])),
        "instructions_changed": instructions_changed,
        "data": data
    }

    # Write updated file if not dry run
    if not dry_run and (instructions_changed or skills_added):
        filepath = Path(analysis["filepath"])
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')  # Add trailing newline

    return result

def main():
    """Main execution function."""
    templates_dir = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates")

    # Find all agent templates
    agent_files = sorted(templates_dir.glob("*.json"))

    print(f"Found {len(agent_files)} agent templates\n")

    # Analyze all agents
    analyses = []
    for filepath in agent_files:
        try:
            analysis = analyze_agent(filepath)
            analyses.append(analysis)
        except Exception as e:
            print(f"Error analyzing {filepath.name}: {e}")

    # Print analysis summary
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"\nTotal agents: {len(analyses)}")
    print(f"Agents with skills field: {sum(1 for a in analyses if a['has_skills'])}")
    print(f"Agents needing skills: {sum(1 for a in analyses if not a['has_skills'])}")
    print(f"Total instruction lines: {sum(a['lines_before'] for a in analyses)}")

    # Agents needing updates
    needs_skills = [a for a in analyses if not a["has_skills"] and a["suggested_skills"]]
    needs_pruning = [a for a in analyses if should_prune_instructions(a["agent_type"], a["data"].get("instructions", ""))]

    print(f"\nAgents needing skills field: {len(needs_skills)}")
    print(f"Agents with redundant instructions: {len(needs_pruning)}")

    # Perform updates (dry run first)
    print("\n" + "=" * 80)
    print("PERFORMING UPDATES (DRY RUN)")
    print("=" * 80 + "\n")

    results = []
    for analysis in analyses:
        result = update_agent(analysis, dry_run=True)
        results.append(result)

        if result["instructions_changed"] or result["skills_added"]:
            print(f"\n{result['filename']}:")
            print(f"  Agent Type: {result['agent_type']}")
            print(f"  Lines: {result['lines_before']} → {result['lines_after']} ({result['lines_removed']} removed, {result['reduction_pct']:.1f}% reduction)")
            if result["skills_added"]:
                print(f"  Skills Added: {result['skills_count']} skills")
            if result["instructions_changed"]:
                print(f"  Instructions: Pruned")

    # Summary statistics
    total_lines_before = sum(r["lines_before"] for r in results)
    total_lines_after = sum(r["lines_after"] for r in results)
    total_removed = total_lines_before - total_lines_after
    total_reduction_pct = (total_removed / total_lines_before * 100) if total_lines_before > 0 else 0

    skills_added_count = sum(1 for r in results if r["skills_added"])
    instructions_changed_count = sum(1 for r in results if r["instructions_changed"])

    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal agents processed: {len(results)}")
    print(f"Agents with skills added: {skills_added_count}")
    print(f"Agents with instructions pruned: {instructions_changed_count}")
    print(f"\nTotal lines before: {total_lines_before}")
    print(f"Total lines after: {total_lines_after}")
    print(f"Total lines removed: {total_removed}")
    print(f"Overall reduction: {total_reduction_pct:.1f}%")

    # Ask for confirmation to proceed
    print("\n" + "=" * 80)
    import sys
    if sys.stdin.isatty():
        response = input("\nProceed with actual updates? (yes/no): ")
        proceed = response.lower() == 'yes'
    else:
        print("\nNon-interactive mode: skipping updates. Use --execute flag to apply changes.")
        proceed = '--execute' in sys.argv

    if proceed:
        print("\nPerforming actual updates...")
        for analysis in analyses:
            result = update_agent(analysis, dry_run=False)
            if result["instructions_changed"] or result["skills_added"]:
                print(f"✓ Updated {result['filename']}")
        print("\n✓ All updates completed!")
    else:
        print("\nUpdate cancelled. Run with --execute to apply changes.")

    # Return results for further processing
    return results

if __name__ == "__main__":
    main()
