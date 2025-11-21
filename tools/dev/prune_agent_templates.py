#!/usr/bin/env python3
"""
Prune and optimize agent templates by removing redundant sections.
Maintains firmness and clarity while reducing file sizes.
"""

import json
import re
from pathlib import Path
from typing import Dict, Tuple

# Base sections to remove (will be inherited from BASE_AGENT_TEMPLATE.md)
REDUNDANT_SECTIONS = [
    # Memory warning headers
    r"<!-- MEMORY WARNING:.*?-->",
    r"<!-- CRITICAL:.*?-->",
    r"<!-- PATTERN:.*?-->",
    r"<!-- THRESHOLDS:.*?-->",
    # Full memory management sections
    r"## 🚨 MEMORY MANAGEMENT CRITICAL 🚨.*?(?=##)",
    r"## Memory Protection Protocol.*?(?=##)",
    r"### Content Threshold System.*?(?=###|\n##)",
    r"### Memory Management Rules.*?(?=###|\n##)",
    r"### Forbidden Memory Practices.*?(?=###|\n##)",
    # Content threshold code blocks
    r"### Threshold Constants\n```python.*?```",
    r"### Progressive Summarization Strategy.*?(?=##)",
    # Generic TodoWrite sections
    r"## TodoWrite Usage Guidelines.*?(?=##)",
    r"### Required Prefix Format.*?(?=###|\n##)",
    r"### Task Status Management.*?(?=###|\n##)",
    # Memory protocol sections
    r"## Memory Protocol\n\n.*?(?=##)",
    r"### Memory Usage Protocol.*?(?=###|\n##)",
    r"### Adding Memories During Tasks.*?(?=###|\n##)",
    # Response format sections (keep agent-specific examples)
    r"### Required JSON Block.*?```\n\n",
    r"## Response Structure\n\n.*?(?=##)",
]

# Sections to keep but simplify
SIMPLIFY_SECTIONS = {
    "memory_categories": "Keep only agent-specific memory categories",
    "todowrite_patterns": "Keep only agent-specific todo patterns",
    "response_examples": "Keep only unique response examples",
}


def count_lines(content: str) -> int:
    """Count non-empty lines in content."""
    return len([line for line in content.split("\n") if line.strip()])


def prune_template(content: str, agent_name: str) -> Tuple[str, int, int]:
    """
    Prune redundant sections from agent template.
    Returns: (pruned_content, original_lines, pruned_lines)
    """
    original_lines = count_lines(content)
    pruned = content

    # Remove redundant sections
    for pattern in REDUNDANT_SECTIONS:
        pruned = re.sub(pattern, "", pruned, flags=re.DOTALL | re.MULTILINE)

    # Add reference to base template at the beginning
    base_ref = f"""# {agent_name} Agent

**Inherits from**: BASE_AGENT_TEMPLATE.md
**Focus**: Agent-specific expertise and protocols only

"""

    # Clean up the pruned content
    pruned = base_ref + pruned
    pruned = re.sub(r"\n{3,}", "\n\n", pruned)  # Remove excessive newlines
    pruned = pruned.strip()

    pruned_lines = count_lines(pruned)
    return pruned, original_lines, pruned_lines


def update_agent_json(file_path: Path, reduction_stats: Dict) -> None:
    """Update agent JSON file with pruned instructions and new version."""
    with file_path.open() as f:
        agent_data = json.load(f)

    agent_name = agent_data["metadata"]["name"]
    original_instructions = agent_data.get("instructions", "")

    # Prune the instructions
    pruned_instructions, orig_lines, new_lines = prune_template(
        original_instructions, agent_name
    )

    # Update the agent data
    agent_data["instructions"] = pruned_instructions

    # Update version (increment patch)
    current_version = agent_data.get("agent_version", "1.0.0")
    parts = current_version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    agent_data["agent_version"] = ".".join(parts)

    # Add template version
    agent_data["template_version"] = "2.0.0"  # New optimized version

    # Add optimization note to metadata
    if "optimization_note" not in agent_data["metadata"]:
        agent_data["metadata"]["optimization_note"] = (
            f"Optimized template - reduced from {orig_lines} to {new_lines} lines"
        )

    # Save the updated agent
    with file_path.open("w") as f:
        json.dump(agent_data, f, indent=2)

    # Track statistics
    reduction_pct = (
        ((orig_lines - new_lines) / orig_lines * 100) if orig_lines > 0 else 0
    )
    reduction_stats[agent_name] = {
        "original": orig_lines,
        "optimized": new_lines,
        "reduction": f"{reduction_pct:.1f}%",
    }


def main():
    """Main function to prune agent templates."""
    templates_dir = Path(
        "/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates"
    )

    # Priority order based on redundancy analysis
    priority_agents = [
        "documentation.json",
        "qa.json",
        "research.json",
        "ops.json",
        "refactoring_engineer.json",
        "engineer.json",
        "security.json",
        "version_control.json",
    ]

    reduction_stats = {}

    print("🔧 Pruning Agent Templates\n")
    print("=" * 60)

    for agent_file in priority_agents:
        file_path = templates_dir / agent_file
        if not file_path.exists():
            print(f"⚠️  Skipping {agent_file} - file not found")
            continue

        print(f"\n📝 Processing {agent_file}...")

        try:
            update_agent_json(file_path, reduction_stats)
            stats = reduction_stats.get(agent_file.replace(".json", ""), {})
            print(
                f"   ✅ Reduced from {stats.get('original', '?')} to {stats.get('optimized', '?')} lines ({stats.get('reduction', '?')})"
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 OPTIMIZATION SUMMARY\n")

    total_original = sum(s["original"] for s in reduction_stats.values())
    total_optimized = sum(s["optimized"] for s in reduction_stats.values())
    total_reduction = (
        ((total_original - total_optimized) / total_original * 100)
        if total_original > 0
        else 0
    )

    for agent, stats in reduction_stats.items():
        print(
            f"{agent:25} {stats['original']:4} → {stats['optimized']:4} lines ({stats['reduction']})"
        )

    print(
        f"\n{'TOTAL':25} {total_original:4} → {total_optimized:4} lines ({total_reduction:.1f}% reduction)"
    )

    print("\n✅ Template optimization complete!")
    print("📌 All agents now reference BASE_AGENT_TEMPLATE.md for common patterns")


if __name__ == "__main__":
    main()
