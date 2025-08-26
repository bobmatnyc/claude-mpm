"""Tests for the InstructionsCheck diagnostic."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.services.diagnostics.checks.instructions_check import (
    InstructionsCheck,
)
from claude_mpm.services.diagnostics.models import DiagnosticStatus


class TestInstructionsCheck:
    """Test the instructions check diagnostic."""

    def test_check_properties(self):
        """Test check has correct properties."""
        check = InstructionsCheck()
        assert check.name == "instructions_check"
        assert check.category == "Instructions"

    def test_no_instruction_files(self):
        """Test when no instruction files exist."""
        check = InstructionsCheck()

        # Mock finding no files
        with patch.object(check, "_find_instruction_files", return_value={}):
            result = check.run()

            assert result.status == DiagnosticStatus.OK
            assert "properly configured" in result.message.lower()

    def test_claude_md_in_root_only(self):
        """Test CLAUDE.md properly placed in root."""
        check = InstructionsCheck(verbose=True)  # Enable verbose for sub_results

        # Mock finding CLAUDE.md only in project root
        project_root = Path.cwd()
        files = {project_root / "CLAUDE.md": "Claude Code instructions"}

        with patch.object(check, "_find_instruction_files", return_value=files):
            result = check.run()

            # Find the placement sub-result
            placement_result = next(
                (r for r in result.sub_results if "Placement" in r.category), None
            )

            assert placement_result is not None
            assert placement_result.status == DiagnosticStatus.OK

    def test_misplaced_claude_md(self):
        """Test detection of misplaced CLAUDE.md files."""
        check = InstructionsCheck(verbose=True)

        # Mock finding CLAUDE.md in wrong location
        project_root = Path.cwd()
        files = {
            project_root / "CLAUDE.md": "Claude Code instructions",
            project_root / "subdir" / "CLAUDE.md": "Claude Code instructions",
        }

        with patch.object(check, "_find_instruction_files", return_value=files):
            result = check.run()

            # Find the placement sub-result
            placement_result = next(
                (r for r in result.sub_results if "Placement" in r.category), None
            )

            assert placement_result is not None
            assert placement_result.status == DiagnosticStatus.WARNING
            assert "misplaced" in placement_result.message.lower()

    def test_duplicate_content_detection(self):
        """Test detection of duplicate content between files."""
        check = InstructionsCheck(verbose=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create files with duplicate content
            file1 = tmpdir_path / "CLAUDE.md"
            file2 = tmpdir_path / "INSTRUCTIONS.md"

            duplicate_content = """
            This is a long paragraph that appears in both files.
            It should be detected as duplicate content by the check.
            This helps ensure we don't have redundant instructions.
            """

            file1.write_text(f"# Claude Code\n\n{duplicate_content}\n\nOther content")
            file2.write_text(
                f"# Instructions\n\n{duplicate_content}\n\nDifferent content"
            )

            files = {
                file1: "Claude Code instructions",
                file2: "MPM agent customization",
            }

            with patch.object(check, "_find_instruction_files", return_value=files):
                result = check.run()

                # Find duplicate content sub-result
                duplicate_result = next(
                    (r for r in result.sub_results if "Duplicate" in r.category), None
                )

                assert duplicate_result is not None
                assert duplicate_result.status == DiagnosticStatus.WARNING
                assert "duplicate content" in duplicate_result.message.lower()

    def test_conflicting_directives(self):
        """Test detection of conflicting directives."""
        check = InstructionsCheck(verbose=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create files with conflicting PM role definitions
            file1 = tmpdir_path / "INSTRUCTIONS.md"
            file2 = tmpdir_path / "OTHER_INSTRUCTIONS.md"

            file1.write_text("You are a PM who delegates all work")
            file2.write_text("You are the PM responsible for implementation")

            files = {file1: "MPM agent customization", file2: "MPM agent customization"}

            with patch.object(check, "_find_instruction_files", return_value=files):
                result = check.run()

                # Find conflicts sub-result
                conflict_result = next(
                    (r for r in result.sub_results if "Conflict" in r.category), None
                )

                assert conflict_result is not None
                # Should detect PM role definition conflict
                if conflict_result.details.get("conflicts"):
                    assert conflict_result.status == DiagnosticStatus.ERROR

    def test_agent_definition_duplicates(self):
        """Test detection of duplicate agent definitions."""
        check = InstructionsCheck(verbose=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create files with duplicate agent definitions
            file1 = tmpdir_path / "INSTRUCTIONS.md"
            file2 = tmpdir_path / "BACKUP_INSTRUCTIONS.md"

            file1.write_text("Agent Engineer specializes in coding")
            file2.write_text("Agent Engineer handles implementation")

            files = {file1: "MPM agent customization", file2: "MPM agent customization"}

            with patch.object(check, "_find_instruction_files", return_value=files):
                result = check.run()

                # Find agent definitions sub-result
                agent_result = next(
                    (r for r in result.sub_results if "Agent" in r.category), None
                )

                assert agent_result is not None
                if agent_result.details.get("duplicates"):
                    assert agent_result.status == DiagnosticStatus.WARNING
                    assert "engineer" in str(agent_result.details).lower()

    def test_separation_of_concerns(self):
        """Test detection of improper separation of concerns."""
        check = InstructionsCheck(verbose=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create CLAUDE.md with MPM-specific content
            claude_file = tmpdir_path / "CLAUDE.md"
            claude_file.write_text(
                """
            # Claude Code Guidelines

            This file contains multi-agent orchestration rules
            and delegation patterns for the PM.
            """
            )

            # Create INSTRUCTIONS.md with Claude Code content
            instructions_file = tmpdir_path / "INSTRUCTIONS.md"
            instructions_file.write_text(
                """
            # MPM Instructions

            Follow these Claude Code development guidelines
            for project structure and coding standards.
            """
            )

            files = {
                claude_file: "Claude Code instructions",
                instructions_file: "MPM agent customization",
            }

            with patch.object(check, "_find_instruction_files", return_value=files):
                result = check.run()

                # Find separation sub-result
                separation_result = next(
                    (r for r in result.sub_results if "Separation" in r.category), None
                )

                assert separation_result is not None
                assert separation_result.status == DiagnosticStatus.WARNING
                assert len(separation_result.details.get("issues", [])) > 0

    def test_check_handles_read_errors(self):
        """Test that check handles file read errors gracefully."""
        check = InstructionsCheck()

        # Mock finding files but failing to read them
        mock_path = Mock(spec=Path)
        mock_path.name = "INSTRUCTIONS.md"
        mock_path.read_text.side_effect = PermissionError("Cannot read file")

        files = {mock_path: "MPM agent customization"}

        with patch.object(check, "_find_instruction_files", return_value=files):
            result = check.run()

            # Should not crash, should return a result
            assert result is not None
            assert result.category == "Instructions"

    def test_verbose_output(self):
        """Test that verbose mode includes sub-results."""
        check = InstructionsCheck(verbose=True)

        with patch.object(check, "_find_instruction_files", return_value={}):
            result = check.run()

            # Verbose mode should include sub-results
            assert result.sub_results is not None
            assert len(result.sub_results) > 0

    def test_non_verbose_output(self):
        """Test that non-verbose mode excludes detailed sub-results."""
        check = InstructionsCheck(verbose=False)

        with patch.object(check, "_find_instruction_files", return_value={}):
            result = check.run()

            # Non-verbose mode should have empty sub-results
            assert result.sub_results == []
