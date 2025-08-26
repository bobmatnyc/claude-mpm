#!/usr/bin/env python3
"""
Example demonstrating how to use custom instructions with .claude-mpm/ directories.

This example shows how the framework loader properly loads custom instructions
from .claude-mpm/ directories while completely ignoring .claude/ directories.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def demonstrate_custom_instructions():
    """Demonstrate loading custom instructions from .claude-mpm/ directories."""

    print("=" * 60)
    print("Claude MPM Custom Instructions Demo")
    print("=" * 60)

    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        print(f"\nCreating demo project at: {project_dir}")

        # Create .claude-mpm directory structure
        claude_mpm_dir = project_dir / ".claude-mpm"
        claude_mpm_dir.mkdir()
        print("✓ Created .claude-mpm/ directory")

        # Create custom INSTRUCTIONS.md
        instructions_path = claude_mpm_dir / "INSTRUCTIONS.md"
        instructions_path.write_text("""# Custom Project PM Instructions

## Project-Specific Rules
- Always prioritize security in this project
- Use TypeScript for all new code
- Follow strict TDD practices
- Delegate all database work to the Data Engineer agent

## Custom Delegation Patterns
- Security reviews must go through Security agent first
- All API changes require Documentation agent updates
- Performance issues should involve both Engineer and Ops agents
""")
        print("✓ Created custom INSTRUCTIONS.md")

        # Create custom WORKFLOW.md
        workflow_path = claude_mpm_dir / "WORKFLOW.md"
        workflow_path.write_text("""# Custom Project Workflow

## Phase 1: Security Analysis
- Security agent reviews requirements
- Identifies potential vulnerabilities

## Phase 2: Test-Driven Development
- QA agent writes test specifications
- Engineer implements with TDD

## Phase 3: Performance Validation
- Ops agent runs performance tests
- Engineer optimizes if needed
""")
        print("✓ Created custom WORKFLOW.md")

        # Create custom MEMORY.md
        memory_path = claude_mpm_dir / "MEMORY.md"
        memory_path.write_text("""# Custom Memory Instructions

## Memory Management Rules
- Track all security decisions
- Remember performance benchmarks
- Keep API version history
- Document breaking changes

## Memory Retention Priority
1. Security vulnerabilities found
2. Performance bottlenecks identified
3. API breaking changes
4. Customer-reported issues
""")
        print("✓ Created custom MEMORY.md")

        # Create memories directory with PM memories
        memories_dir = claude_mpm_dir / "memories"
        memories_dir.mkdir()
        pm_memories_path = memories_dir / "PM_memories.md"
        pm_memories_path.write_text("""# Project Manager Memories

## Project Context
- This is a financial services application
- Security is the top priority
- Must comply with SOC2 requirements
- Performance SLA: <100ms response time

## Technical Decisions
- Using PostgreSQL for main database
- Redis for caching layer
- TypeScript for all new development
- Jest for testing framework

## Known Issues
- Legacy code in /src/old needs refactoring
- API v1 will be deprecated in Q2
- Performance issues with large datasets
""")
        print("✓ Created PM memories")

        # Also create a .claude directory to demonstrate it's ignored
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "INSTRUCTIONS.md").write_text("THIS SHOULD BE IGNORED")
        print("✓ Created .claude/ directory (will be ignored)")

        # Change to project directory and load framework
        original_cwd = Path.cwd()
        try:
            os.chdir(project_dir)
            print(f"\n{'='*40}")
            print("Loading framework...")
            print(f"{'='*40}\n")

            # Initialize framework loader
            loader = FrameworkLoader()

            # Display what was loaded
            content = loader.framework_content

            print("Loaded Custom Instructions:")
            print("-" * 30)
            if content.get("custom_instructions"):
                print(f"✓ INSTRUCTIONS.md loaded from {content.get('custom_instructions_level', 'unknown')} level")
                print(f"  First line: {content['custom_instructions'].split(chr(10))[0]}")
            else:
                print("✗ No custom instructions loaded")

            if content.get("workflow_instructions_level") == "project":
                print("✓ WORKFLOW.md loaded from project level")
                print(f"  First line: {content['workflow_instructions'].split(chr(10))[0]}")
            else:
                print(f"ℹ WORKFLOW.md using {content.get('workflow_instructions_level', 'system')} defaults")

            if content.get("memory_instructions_level") == "project":
                print("✓ MEMORY.md loaded from project level")
                print(f"  First line: {content['memory_instructions'].split(chr(10))[0]}")
            else:
                print(f"ℹ MEMORY.md using {content.get('memory_instructions_level', 'system')} defaults")

            if content.get("actual_memories"):
                print("✓ PM memories loaded")
                # Count memory items
                memory_lines = [l for l in content['actual_memories'].split('\n') if l.strip().startswith('-')]
                print(f"  Found {len(memory_lines)} memory items")

            # Verify .claude/ directory was ignored
            print("\nSecurity Check:")
            print("-" * 30)
            full_instructions = loader.get_framework_instructions()
            if "THIS SHOULD BE IGNORED" in full_instructions:
                print("✗ ERROR: .claude/ directory was read (security issue!)")
            else:
                print("✓ .claude/ directory correctly ignored")

            # Show how custom instructions appear in final output
            print(f"\n{'='*40}")
            print("Custom Instructions in Final Output:")
            print(f"{'='*40}\n")

            if "Custom Project PM Instructions" in full_instructions:
                print("✓ Custom PM instructions integrated")
            if "Custom Project Workflow" in full_instructions:
                print("✓ Custom workflow integrated")
            if "Custom Memory Instructions" in full_instructions:
                print("✓ Custom memory instructions integrated")
            if "financial services application" in full_instructions:
                print("✓ PM memories integrated")

            # Display file structure for clarity
            print(f"\n{'='*40}")
            print("Project Structure:")
            print(f"{'='*40}")
            print(f"""
{project_dir}/
├── .claude-mpm/              ✓ LOADED
│   ├── INSTRUCTIONS.md       ✓ Custom PM instructions
│   ├── WORKFLOW.md           ✓ Custom workflow
│   ├── MEMORY.md             ✓ Custom memory rules
│   └── memories/
│       └── PM_memories.md    ✓ PM memories
└── .claude/                   ✗ IGNORED
    └── INSTRUCTIONS.md        ✗ Not loaded (correct!)
""")

        finally:
            os.chdir(original_cwd)

    print(f"\n{'='*60}")
    print("Demo Complete!")
    print(f"{'='*60}")
    print("\nKey Takeaways:")
    print("1. Place custom instructions in .claude-mpm/ directory")
    print("2. Files in .claude/ are completely ignored")
    print("3. Project-level overrides user-level overrides system defaults")
    print("4. Custom instructions are clearly labeled in the output")


if __name__ == "__main__":
    demonstrate_custom_instructions()
