"""Test that framework loader correctly uses .claude-mpm/ and ignores .claude/ directories."""

import os
import sys
from pathlib import Path

# Add src to path for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


class TestClaudeMpmDirectoryLoading:
    """Test suite for .claude-mpm/ directory loading."""

    def test_project_instructions_loading(self, tmp_path):
        """Test that project-level INSTRUCTIONS.md is loaded from .claude-mpm/."""
        # Create .claude-mpm directory
        claude_mpm_dir = tmp_path / ".claude-mpm"
        claude_mpm_dir.mkdir()

        # Create test INSTRUCTIONS.md
        instructions_content = "# Project Instructions\nTest content"
        (claude_mpm_dir / "INSTRUCTIONS.md").write_text(instructions_content)

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Verify instructions were loaded
            assert loader.framework_content.get("custom_instructions") is not None
            assert (
                "Project Instructions"
                in loader.framework_content["custom_instructions"]
            )
            assert (
                loader.framework_content.get("custom_instructions_level") == "project"
            )
        finally:
            os.chdir(original_cwd)

    def test_project_workflow_loading(self, tmp_path):
        """Test that project-level WORKFLOW.md is loaded from .claude-mpm/."""
        # Create .claude-mpm directory
        claude_mpm_dir = tmp_path / ".claude-mpm"
        claude_mpm_dir.mkdir()

        # Create test WORKFLOW.md
        workflow_content = "# Project Workflow\nCustom workflow"
        (claude_mpm_dir / "WORKFLOW.md").write_text(workflow_content)

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Verify workflow was loaded
            assert loader.framework_content.get("workflow_instructions") is not None
            assert (
                "Project Workflow" in loader.framework_content["workflow_instructions"]
            )
            assert (
                loader.framework_content.get("workflow_instructions_level") == "project"
            )
        finally:
            os.chdir(original_cwd)

    def test_project_memory_loading(self, tmp_path):
        """Test that project-level MEMORY.md is loaded from .claude-mpm/."""
        # Create .claude-mpm directory
        claude_mpm_dir = tmp_path / ".claude-mpm"
        claude_mpm_dir.mkdir()

        # Create test MEMORY.md
        memory_content = "# Project Memory\nCustom memory instructions"
        (claude_mpm_dir / "MEMORY.md").write_text(memory_content)

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Verify memory was loaded
            assert loader.framework_content.get("memory_instructions") is not None
            assert "Project Memory" in loader.framework_content["memory_instructions"]
            assert (
                loader.framework_content.get("memory_instructions_level") == "project"
            )
        finally:
            os.chdir(original_cwd)

    def test_claude_directory_ignored(self, tmp_path):
        """Test that .claude/ directory is completely ignored."""
        # Create both .claude-mpm and .claude directories
        claude_mpm_dir = tmp_path / ".claude-mpm"
        claude_mpm_dir.mkdir()
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Put correct content in .claude-mpm
        (claude_mpm_dir / "INSTRUCTIONS.md").write_text("CORRECT INSTRUCTIONS")
        (claude_mpm_dir / "WORKFLOW.md").write_text("CORRECT WORKFLOW")
        (claude_mpm_dir / "MEMORY.md").write_text("CORRECT MEMORY")

        # Put wrong content in .claude (should be ignored)
        (claude_dir / "INSTRUCTIONS.md").write_text(
            "CLAUDE_DIR_INSTRUCTIONS - SHOULD NOT LOAD"
        )
        (claude_dir / "WORKFLOW.md").write_text("CLAUDE_DIR_WORKFLOW - SHOULD NOT LOAD")
        (claude_dir / "MEMORY.md").write_text("CLAUDE_DIR_MEMORY - SHOULD NOT LOAD")

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Get all instructions
            full_instructions = loader.get_framework_instructions()

            # Verify correct content was loaded
            assert "CORRECT INSTRUCTIONS" in loader.framework_content.get(
                "custom_instructions", ""
            )
            assert "CORRECT WORKFLOW" in loader.framework_content.get(
                "workflow_instructions", ""
            )
            assert "CORRECT MEMORY" in loader.framework_content.get(
                "memory_instructions", ""
            )

            # Verify wrong content was NOT loaded (from .claude/ directory)
            assert "CLAUDE_DIR_INSTRUCTIONS" not in full_instructions
            assert "CLAUDE_DIR_WORKFLOW" not in full_instructions
            assert "CLAUDE_DIR_MEMORY" not in full_instructions

            # Verify no .claude/ references in instructions
            assert ".claude/" not in full_instructions
        finally:
            os.chdir(original_cwd)

    def test_precedence_order(self, tmp_path, monkeypatch):
        """Test that precedence order is: project > user > system."""
        # Create project .claude-mpm
        project_dir = tmp_path / ".claude-mpm"
        project_dir.mkdir()
        (project_dir / "INSTRUCTIONS.md").write_text("PROJECT INSTRUCTIONS")

        # Create fake user .claude-mpm in temp location
        user_dir = tmp_path / "fake_home" / ".claude-mpm"
        user_dir.mkdir(parents=True)
        (user_dir / "INSTRUCTIONS.md").write_text("USER INSTRUCTIONS")

        # Mock Path.home() to return our fake home
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake_home")

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Project should override user
            assert "PROJECT INSTRUCTIONS" in loader.framework_content.get(
                "custom_instructions", ""
            )
            assert "USER INSTRUCTIONS" not in loader.framework_content.get(
                "custom_instructions", ""
            )
            assert (
                loader.framework_content.get("custom_instructions_level") == "project"
            )

            # Now remove project file and test user level
            (project_dir / "INSTRUCTIONS.md").unlink()  # Remove the file first
            project_dir.rmdir()  # Then remove the directory
            loader = FrameworkLoader()

            # User level should be loaded
            assert "USER INSTRUCTIONS" in loader.framework_content.get(
                "custom_instructions", ""
            )
            assert loader.framework_content.get("custom_instructions_level") == "user"
        finally:
            os.chdir(original_cwd)

    def test_memory_files_loading(self, tmp_path):
        """Test that PM_memories.md is loaded from .claude-mpm/memories/."""
        # Create directory structure
        memories_dir = tmp_path / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)

        # Create PM memories
        pm_content = "# PM Memories\n- Project uses Python\n- Testing is important"
        (memories_dir / "PM_memories.md").write_text(pm_content)

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Verify PM memories were loaded
            assert loader.framework_content.get("actual_memories") is not None
            assert "Project uses Python" in loader.framework_content["actual_memories"]
            assert "Testing is important" in loader.framework_content["actual_memories"]
        finally:
            os.chdir(original_cwd)

    def test_instructions_in_final_output(self, tmp_path):
        """Test that custom instructions appear in final formatted output."""
        # Create .claude-mpm directory with all files
        claude_mpm_dir = tmp_path / ".claude-mpm"
        claude_mpm_dir.mkdir()

        (claude_mpm_dir / "INSTRUCTIONS.md").write_text(
            "# Custom PM Instructions\nAlways delegate"
        )
        (claude_mpm_dir / "WORKFLOW.md").write_text(
            "# Custom Workflow\nPhase 1: Research"
        )
        (claude_mpm_dir / "MEMORY.md").write_text(
            "# Custom Memory\nRemember everything"
        )

        # Change to test directory
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loader = FrameworkLoader()

            # Get final formatted instructions
            final = loader.get_framework_instructions()

            # Verify custom content appears with proper labels
            assert "Custom PM Instructions" in final
            assert "Custom Workflow" in final
            assert "Custom Memory" in final

            # Verify level indicators appear
            assert "(project level)" in final or "project-specific" in final.lower()
        finally:
            os.chdir(original_cwd)
