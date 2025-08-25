#!/usr/bin/env python3
"""Test script to verify framework loader loads all components correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_framework_loader():
    """Test that framework loader finds and loads all instruction components."""

    print("Testing Framework Loader Component Loading")
    print("=" * 60)

    # Initialize the loader
    loader = FrameworkLoader()

    # Check what was loaded
    content = loader.framework_content

    # Check each component
    components = {
        "INSTRUCTIONS.md": (
            "framework_instructions",
            content.get("framework_instructions", ""),
        ),
        "BASE_PM.md": ("base_pm_instructions", content.get("base_pm_instructions", "")),
        "WORKFLOW.md": (
            "workflow_instructions",
            content.get("workflow_instructions", ""),
        ),
        "MEMORY.md": ("memory_instructions", content.get("memory_instructions", "")),
        "PM.md memories": ("actual_memories", content.get("actual_memories", "")),
    }

    print("\nComponent Loading Status:")
    print("-" * 60)

    for name, (key, value) in components.items():
        if value:
            lines = value.strip().split("\n")
            preview = lines[0][:80] if lines else ""
            status = "✓ LOADED"
            size = len(value)
            print(f"{name:20} {status:12} ({size:,} bytes)")
            print(f"  Preview: {preview}...")

            # For WORKFLOW and MEMORY, check which version was loaded
            if name == "WORKFLOW.md":
                source = content.get("project_workflow", "unknown")
                print(f"  Source: {source}")
            elif name == "MEMORY.md":
                source = content.get("project_memory", "unknown")
                print(f"  Source: {source}")
        else:
            print(f"{name:20} {'✗ NOT FOUND':12}")

    # Check if agents were loaded
    print(f"\nAgents loaded: {len(content.get('agents', {}))}")
    if content.get("agents"):
        for agent_name in sorted(content["agents"].keys())[:5]:
            print(f"  - {agent_name}")
        if len(content["agents"]) > 5:
            print(f"  ... and {len(content['agents']) - 5} more")

    # Get the final instructions and check if everything is included
    print("\n" + "=" * 60)
    print("Final Instructions Assembly Check")
    print("=" * 60)

    final_instructions = loader.get_framework_instructions()

    # Check if key sections are present
    checks = [
        ("INSTRUCTIONS.md content", "Claude Multi-Agent Project Manager"),
        ("WORKFLOW.md content", "PM Workflow Configuration"),
        ("MEMORY.md content", "Static Memory Management"),
        ("PM memories", "Current PM Memories"),
        ("BASE_PM.md content", "Framework Requirements"),
        ("Agent capabilities", "Available Agent Capabilities"),
        ("Temporal context", "Today's Date"),
    ]

    print("\nPresence in final instructions:")
    for check_name, search_text in checks:
        present = search_text in final_instructions
        status = "✓" if present else "✗"
        print(f"  {status} {check_name}")

    # Show size of final instructions
    print(f"\nFinal instructions size: {len(final_instructions):,} bytes")
    print(f"Final instructions lines: {len(final_instructions.splitlines()):,}")

    # Check for any missing critical components
    print("\n" + "=" * 60)
    print("Issue Detection")
    print("=" * 60)

    issues = []

    if not content.get("workflow_instructions"):
        issues.append(
            "WORKFLOW.md not being loaded - check file existence and loader logic"
        )

    if not content.get("memory_instructions"):
        issues.append(
            "MEMORY.md not being loaded - check file existence and loader logic"
        )

    if not content.get("actual_memories"):
        pm_path = Path.cwd() / ".claude-mpm" / "memories" / "PM.md"
        if pm_path.exists():
            issues.append(f"PM.md exists at {pm_path} but not being loaded")
        else:
            issues.append(f"PM.md does not exist at {pm_path}")

    if not content.get("base_pm_instructions"):
        issues.append("BASE_PM.md not being loaded")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("✓ All components loaded successfully!")

    return len(issues) == 0


if __name__ == "__main__":
    success = test_framework_loader()
    sys.exit(0 if success else 1)
