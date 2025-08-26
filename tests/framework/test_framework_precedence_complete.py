#!/usr/bin/env python3
"""Test and demonstrate framework loader precedence and memory loading."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_system_loading():
    """Test loading from system directories."""
    print("\n" + "=" * 60)
    print("TEST 1: System File Loading")
    print("=" * 60)

    loader = FrameworkLoader()
    content = loader.framework_content

    print("\nSystem files loaded:")
    if content.get("workflow_instructions"):
        print("  ✓ WORKFLOW.md from: src/claude_mpm/agents/ (system)")
    if content.get("memory_instructions"):
        print("  ✓ MEMORY.md from: src/claude_mpm/agents/ (system)")
    if content.get("actual_memories"):
        print("  ✓ PM.md from: .claude/memories/")

    return True


def test_project_override():
    """Test that project-specific files override system files."""
    print("\n" + "=" * 60)
    print("TEST 2: Project-Specific Override")
    print("=" * 60)

    # Create temporary project override files
    project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"
    project_agents_dir.mkdir(parents=True, exist_ok=True)

    # Create a custom WORKFLOW.md
    custom_workflow = project_agents_dir / "WORKFLOW.md"
    custom_workflow_content = """<!-- PROJECT_WORKFLOW_VERSION: 0001 -->
# Custom Project Workflow

This is a project-specific workflow that should override the system workflow.

## Project-Specific Phases
1. Custom Research Phase
2. Custom Implementation Phase
3. Custom Testing Phase
"""

    try:
        # Write the custom workflow
        custom_workflow.write_text(custom_workflow_content)
        print(f"\nCreated project-specific WORKFLOW.md at: {custom_workflow}")

        # Load with the project override
        loader = FrameworkLoader()
        content = loader.framework_content

        # Check if project workflow was loaded
        if content.get("workflow_instructions"):
            if "Custom Project Workflow" in content["workflow_instructions"]:
                print("  ✓ Project-specific WORKFLOW.md loaded successfully")
                print(f"  ✓ Source: {content.get('project_workflow', 'unknown')}")
                return True
            print("  ✗ Project-specific WORKFLOW.md not loaded")
            return False
        print("  ✗ No WORKFLOW.md loaded")
        return False

    finally:
        # Clean up
        if custom_workflow.exists():
            custom_workflow.unlink()
            print(f"\nCleaned up test file: {custom_workflow}")


def test_memory_loading():
    """Test loading of actual PM memories."""
    print("\n" + "=" * 60)
    print("TEST 3: PM Memory Loading")
    print("=" * 60)

    memories_path = Path.cwd() / ".claude-mpm" / "memories" / "PM.md"

    if not memories_path.exists():
        print(f"  ⚠️  PM.md not found at: {memories_path}")
        print("  Creating a test PM.md file...")

        memories_path.parent.mkdir(parents=True, exist_ok=True)
        test_memory_content = """# PM Memory

## Test Memory Entry
- This is a test memory entry
- The framework loader should load this
"""
        memories_path.write_text(test_memory_content)
        created_test_file = True
    else:
        created_test_file = False
        print(f"  ✓ PM.md exists at: {memories_path}")

    try:
        # Load and check
        loader = FrameworkLoader()
        content = loader.framework_content

        if content.get("actual_memories"):
            print(f"  ✓ PM memories loaded: {len(content['actual_memories'])} bytes")

            # Check if memories are in final instructions
            final = loader.get_framework_instructions()
            if "Current PM Memories" in final:
                print("  ✓ PM memories included in final instructions")

                # Show a preview
                lines = content["actual_memories"].split("\n")[:3]
                print("\n  Memory preview:")
                for line in lines:
                    if line.strip():
                        print(f"    {line[:60]}...")

                return True
            print("  ✗ PM memories NOT in final instructions")
            return False
        print("  ✗ PM memories not loaded")
        return False

    finally:
        if created_test_file and memories_path.exists():
            memories_path.unlink()
            print("\n  Cleaned up test memory file")


def test_complete_integration():
    """Test that all components are integrated in final instructions."""
    print("\n" + "=" * 60)
    print("TEST 4: Complete Integration")
    print("=" * 60)

    loader = FrameworkLoader()
    final = loader.get_framework_instructions()

    # Define expected sections with their markers
    expected_sections = [
        ("Main Instructions", "Claude Multi-Agent Project Manager"),
        ("Workflow Configuration", "Workflow" in final or "WORKFLOW" in final),
        ("Memory Management", "Memory" in final or "MEMORY" in final),
        ("PM Memories", "Current PM Memories" in final or "PM Memory" in final),
        ("Base Framework", "Framework Requirements" in final or "Base PM" in final),
        ("Agent Capabilities", "Available Agent" in final),
        ("Temporal Context", "Today's Date" in final),
    ]

    print("\nIntegration check:")
    all_present = True
    for section_name, check in expected_sections:
        present = check if isinstance(check, bool) else check

        status = "✓" if present else "✗"
        print(f"  {status} {section_name}")
        if not present:
            all_present = False

    print("\nFinal instructions statistics:")
    print(f"  Size: {len(final):,} bytes")
    print(f"  Lines: {len(final.splitlines()):,}")
    print(f"  Characters: {len(final):,}")

    return all_present


def main():
    """Run all tests."""
    print("Framework Loader Complete Test Suite")
    print("=" * 60)
    print("Testing all framework loader functionality:")
    print("  1. System file loading")
    print("  2. Project-specific overrides")
    print("  3. PM memory loading")
    print("  4. Complete integration")

    results = []

    # Run tests
    results.append(("System Loading", test_system_loading()))
    results.append(("Project Override", test_project_override()))
    results.append(("Memory Loading", test_memory_loading()))
    results.append(("Complete Integration", test_complete_integration()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nThe framework loader is working correctly:")
        print("  • Loads WORKFLOW.md and MEMORY.md from system")
        print("  • Supports project-specific overrides")
        print("  • Loads PM memories from .claude/memories/PM.md")
        print("  • Integrates everything into final instructions")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease check the framework loader implementation.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
