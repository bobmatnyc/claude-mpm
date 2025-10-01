#!/usr/bin/env python3
"""Test script to verify .claude-mpm/ directory loading."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.core.logger import get_logger

logger = get_logger("test_claude_mpm")


def test_claude_mpm_loading():
    """Test that framework loader correctly loads from .claude-mpm/ directories."""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create .claude-mpm directory structure
        claude_mpm_dir = test_dir / ".claude-mpm"
        claude_mpm_dir.mkdir()

        # Create test INSTRUCTIONS.md
        instructions_content = """# Test Project Instructions

These are custom project-level PM instructions from .claude-mpm/INSTRUCTIONS.md

## Custom Rules
- Always test first
- Document everything
"""
        (claude_mpm_dir / "INSTRUCTIONS.md").write_text(instructions_content)

        # Create test WORKFLOW.md
        workflow_content = """# Test Workflow

Custom workflow from .claude-mpm/WORKFLOW.md

## Phases
1. Research
2. Implement
3. Test
"""
        (claude_mpm_dir / "WORKFLOW.md").write_text(workflow_content)

        # Create test MEMORY.md
        memory_content = """# Test Memory Instructions

Custom memory instructions from .claude-mpm/MEMORY.md

## Memory Rules
- Remember everything
- Forget nothing
"""
        (claude_mpm_dir / "MEMORY.md").write_text(memory_content)

        # Create memories directory with PM_memories.md
        memories_dir = claude_mpm_dir / "memories"
        memories_dir.mkdir()
        (memories_dir / "PM_memories.md").write_text(
            """# PM Memories

## Project Knowledge
- This project uses Python 3.11
- Testing is critical
"""
        )

        # Also create a .claude directory to ensure it's NOT read
        claude_dir = test_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "INSTRUCTIONS.md").write_text("SHOULD NOT BE LOADED")
        (claude_dir / "WORKFLOW.md").write_text("SHOULD NOT BE LOADED")
        (claude_dir / "MEMORY.md").write_text("SHOULD NOT BE LOADED")

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(test_dir)

            # Initialize framework loader
            loader = FrameworkLoader()

            # Check that custom instructions were loaded
            content = loader.framework_content

            print("\n=== Test Results ===\n")

            # Test INSTRUCTIONS.md loading
            if content.get("custom_instructions"):
                print("✅ INSTRUCTIONS.md loaded from .claude-mpm/")
                print(
                    f"   Level: {content.get('custom_instructions_level', 'unknown')}"
                )
                if "Test Project Instructions" in content["custom_instructions"]:
                    print("   ✅ Correct content loaded")
                else:
                    print("   ❌ Wrong content loaded")
            else:
                print("❌ INSTRUCTIONS.md NOT loaded")

            # Test WORKFLOW.md loading
            if content.get("workflow_instructions"):
                print("✅ WORKFLOW.md loaded")
                print(
                    f"   Level: {content.get('workflow_instructions_level', 'unknown')}"
                )
                if "Test Workflow" in content["workflow_instructions"]:
                    print("   ✅ Correct content loaded from .claude-mpm/")
                elif "SHOULD NOT BE LOADED" in content["workflow_instructions"]:
                    print("   ❌ WRONG! Loaded from .claude/ directory")
                else:
                    print("   ℹ️  Loaded from system defaults")  # noqa: RUF001
            else:
                print("❌ WORKFLOW.md NOT loaded")

            # Test MEMORY.md loading
            if content.get("memory_instructions"):
                print("✅ MEMORY.md loaded")
                print(
                    f"   Level: {content.get('memory_instructions_level', 'unknown')}"
                )
                if "Test Memory Instructions" in content["memory_instructions"]:
                    print("   ✅ Correct content loaded from .claude-mpm/")
                elif "SHOULD NOT BE LOADED" in content["memory_instructions"]:
                    print("   ❌ WRONG! Loaded from .claude/ directory")
                else:
                    print("   ℹ️  Loaded from system defaults")  # noqa: RUF001
            else:
                print("❌ MEMORY.md NOT loaded")

            # Test actual memories loading
            if content.get("actual_memories"):
                print("✅ PM_memories.md loaded")
                if "This project uses Python 3.11" in content["actual_memories"]:
                    print("   ✅ Correct memory content loaded")
                else:
                    print("   ❌ Wrong memory content")
            else:
                print("ℹ️  No PM memories loaded (expected if no deployed agents)")  # noqa: RUF001

            # Verify .claude/ directory was NOT read
            instructions_text = loader.get_framework_instructions()
            if "SHOULD NOT BE LOADED" in instructions_text:
                print("\n❌ ERROR: Content from .claude/ directory was loaded!")
                print(
                    "   This is a critical bug - framework should NEVER read from .claude/"
                )
            else:
                print("\n✅ Correctly ignored .claude/ directory")

            print("\n=== User Home Directory Test ===\n")

            # Now test user-level loading
            user_claude_mpm = Path.home() / ".claude-mpm"
            if user_claude_mpm.exists():
                print(f"Found user .claude-mpm at: {user_claude_mpm}")

                # Check what files exist
                for file in ["INSTRUCTIONS.md", "WORKFLOW.md", "MEMORY.md"]:
                    file_path = user_claude_mpm / file
                    if file_path.exists():
                        print(f"   ✅ {file} exists")
                    else:
                        print(f"   ℹ️  {file} not found")  # noqa: RUF001

                # Check memories directory
                memories_dir = user_claude_mpm / "memories"
                if memories_dir.exists():
                    print("   ✅ memories/ directory exists")
                    pm_memories = memories_dir / "PM_memories.md"
                    if pm_memories.exists():
                        print("      ✅ PM_memories.md exists")
            else:
                print(f"ℹ️  No user .claude-mpm directory at: {user_claude_mpm}")  # noqa: RUF001

        finally:
            os.chdir(original_cwd)

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    test_claude_mpm_loading()
