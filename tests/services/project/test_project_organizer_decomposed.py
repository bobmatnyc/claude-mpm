"""
Tests for the decomposed ProjectOrganizer collaborators (Phase 4).

Covers:
- TestStructurePolicy   — pure data / requirement rules
- TestGitignoreManager  — .gitignore read / diff / write
- TestFileOrganizer     — classification and move proposals
- TestStructureVerifier — verify() and validate() scanning
- TestStructureReporter — markdown and JSON report generation
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# TestStructurePolicy
# ---------------------------------------------------------------------------


class TestStructurePolicy:
    def setup_method(self) -> None:
        from claude_mpm.services.project.structure_policy import StructurePolicy

        self.policy = StructurePolicy()

    def test_standard_directories_contains_expected_keys(self) -> None:
        assert "tmp" in self.policy.STANDARD_DIRECTORIES
        assert "scripts" in self.policy.STANDARD_DIRECTORIES
        assert "docs" in self.policy.STANDARD_DIRECTORIES

    def test_always_required_directories(self) -> None:
        for name in ("tmp", "scripts", "docs"):
            assert self.policy.is_required_directory(name, None) is True

    def test_src_required_for_library(self) -> None:
        assert self.policy.is_required_directory("src", "library") is True
        assert self.policy.is_required_directory("src", "package") is True

    def test_src_not_required_without_project_type(self) -> None:
        assert self.policy.is_required_directory("src", None) is False

    def test_tests_required_for_web(self) -> None:
        for ptype in ("web", "api", "fullstack"):
            assert self.policy.is_required_directory("tests", ptype) is True

    def test_tests_not_required_for_cli(self) -> None:
        assert self.policy.is_required_directory("tests", "cli") is False

    def test_project_structures_keys(self) -> None:
        assert "web" in self.policy.PROJECT_STRUCTURES
        assert "api" in self.policy.PROJECT_STRUCTURES
        assert "library" in self.policy.PROJECT_STRUCTURES

    def test_unknown_directory_not_required(self) -> None:
        assert self.policy.is_required_directory("unknown_dir", "web") is False


# ---------------------------------------------------------------------------
# TestGitignoreManager
# ---------------------------------------------------------------------------


class TestGitignoreManager:
    def setup_method(self, tmp_path_fixture=None) -> None:
        # NOTE: tmp_path injected via fixture — see individual tests below.
        pass

    def test_update_creates_file_when_missing(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.gitignore_manager import GitignoreManager

        path = tmp_path / ".gitignore"
        mgr = GitignoreManager(path)
        result = mgr.update()
        assert result is True
        assert path.exists()
        content = path.read_text()
        assert "tmp/" in content
        assert "__pycache__/" in content

    def test_update_returns_false_when_nothing_missing(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.gitignore_manager import (
            STANDARD_GITIGNORE_PATTERNS,
            GitignoreManager,
        )

        path = tmp_path / ".gitignore"
        path.write_text("\n".join(sorted(STANDARD_GITIGNORE_PATTERNS)) + "\n")
        mgr = GitignoreManager(path)
        assert mgr.update() is False

    def test_update_appends_only_missing_patterns(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.gitignore_manager import GitignoreManager

        path = tmp_path / ".gitignore"
        path.write_text("*.log\n")
        mgr = GitignoreManager(path)
        mgr.update()
        content = path.read_text()
        # Original pattern preserved
        assert "*.log" in content
        # Additional patterns added
        assert "tmp/" in content

    def test_update_with_additional_patterns(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.gitignore_manager import GitignoreManager

        path = tmp_path / ".gitignore"
        mgr = GitignoreManager(path)
        mgr.update(additional_patterns=["my_custom_pattern/"])
        content = path.read_text()
        assert "my_custom_pattern/" in content

    def test_read_existing_ignores_comments(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.gitignore_manager import GitignoreManager

        path = tmp_path / ".gitignore"
        path.write_text("# comment\n*.log\n\n")
        mgr = GitignoreManager(path)
        existing = mgr._read_existing()
        assert "*.log" in existing
        assert "# comment" not in existing

    def test_read_existing_returns_empty_set_for_missing_file(
        self, tmp_path: Path
    ) -> None:
        from claude_mpm.services.project.gitignore_manager import GitignoreManager

        path = tmp_path / "no_such_file"
        mgr = GitignoreManager(path)
        assert mgr._read_existing() == set()


# ---------------------------------------------------------------------------
# TestFileOrganizer
# ---------------------------------------------------------------------------


class TestFileOrganizer:
    def test_classify_test_file_high_confidence(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        fo = FileOrganizer(tmp_path)
        f = tmp_path / "test_something.py"
        f.touch()
        target, confidence, _ = fo.classify(f)
        assert target == "tests"
        assert confidence == "high"

    def test_classify_shell_script_high_confidence(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        fo = FileOrganizer(tmp_path)
        f = tmp_path / "deploy.sh"
        f.touch()
        target, confidence, _ = fo.classify(f)
        assert target == "scripts"
        assert confidence == "high"

    def test_classify_log_file_high_confidence(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        fo = FileOrganizer(tmp_path)
        f = tmp_path / "app.log"
        f.touch()
        target, confidence, _ = fo.classify(f)
        assert target == "tmp"
        assert confidence == "high"

    def test_classify_python_script_medium_confidence(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        fo = FileOrganizer(tmp_path)
        f = tmp_path / "run_script.py"
        f.touch()
        target, confidence, _ = fo.classify(f)
        assert target == "scripts"
        assert confidence == "medium"

    def test_classify_returns_none_for_unrecognised_file(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        fo = FileOrganizer(tmp_path)
        f = tmp_path / "ordinary_module.py"
        f.touch()
        target, _, _ = fo.classify(f)
        assert target is None

    def test_propose_moves_auto_safe_only_high_confidence(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        (tmp_path / "test_foo.py").touch()
        (tmp_path / "run_cli.py").touch()  # medium confidence
        fo = FileOrganizer(tmp_path)
        moves = fo.propose_moves(auto_safe=True)
        sources = [m["source"] for m in moves]
        assert "test_foo.py" in sources
        # medium-confidence file should NOT appear in auto_safe mode
        assert "run_cli.py" not in sources

    def test_propose_moves_non_safe_includes_medium(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        (tmp_path / "run_cli.py").touch()
        fo = FileOrganizer(tmp_path)
        moves = fo.propose_moves(auto_safe=False)
        sources = [m["source"] for m in moves]
        assert "run_cli.py" in sources

    def test_execute_moves_creates_target_directory(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        src = tmp_path / "test_foo.py"
        src.write_text("# test")
        fo = FileOrganizer(tmp_path)
        result = fo.execute_moves(
            [{"source": "test_foo.py", "target": "tests/test_foo.py"}]
        )
        assert len(result["completed"]) == 1
        assert len(result["errors"]) == 0
        assert (tmp_path / "tests" / "test_foo.py").exists()

    def test_organize_dry_run_does_not_move_files(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import FileOrganizer

        src = tmp_path / "test_foo.py"
        src.write_text("# test")
        fo = FileOrganizer(tmp_path)
        result = fo.organize(dry_run=True)
        assert result["dry_run"] is True
        assert src.exists()  # file was NOT moved

    def test_protected_root_files_never_moved(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.file_organizer import (
            PROTECTED_ROOT_FILES,
            FileOrganizer,
        )

        for name in list(PROTECTED_ROOT_FILES)[:3]:
            (tmp_path / name).touch()
        fo = FileOrganizer(tmp_path)
        moves = fo.propose_moves(auto_safe=False)
        moved_sources = {m["source"] for m in moves}
        for name in list(PROTECTED_ROOT_FILES)[:3]:
            assert name not in moved_sources


# ---------------------------------------------------------------------------
# TestStructureVerifier
# ---------------------------------------------------------------------------


class TestStructureVerifier:
    def test_verify_detects_missing_directories(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        report = sv.verify()
        missing_paths = {d["path"] for d in report["missing"]}
        assert "tmp" in missing_paths
        assert "docs" in missing_paths

    def test_verify_detects_existing_directories(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        (tmp_path / "tmp").mkdir()
        sv = StructureVerifier(tmp_path)
        report = sv.verify()
        existing_paths = {d["path"] for d in report["exists"]}
        assert "tmp" in existing_paths

    def test_verify_project_path_in_report(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        report = sv.verify()
        assert report["project_path"] == str(tmp_path)

    def test_verify_with_project_type_adds_type_dirs(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        report = sv.verify(project_type="web")
        missing_paths = {d["path"] for d in report["missing"]}
        # web project structure includes "public"
        assert "public" in missing_paths

    def test_validate_returns_grade(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("tmp/\n__pycache__\n.env\n*.log\n")
        for d in ("tmp", "scripts", "docs"):
            (tmp_path / d).mkdir()
        result = sv.validate(gitignore)
        assert "grade" in result
        assert result["score"] == 100

    def test_validate_penalises_missing_critical_dirs(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("tmp/\n__pycache__\n.env\n*.log\n")
        result = sv.validate(gitignore)
        assert result["score"] < 100
        assert not result["is_valid"]

    def test_validate_penalises_missing_gitignore(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        result = sv.validate(tmp_path / ".gitignore")
        assert result["score"] < 100
        assert not result["is_valid"]

    def test_check_common_issues_detects_misplaced_tests(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        (tmp_path / "test_something.py").write_text("# test")
        sv = StructureVerifier(tmp_path)
        issues = sv._check_common_issues()
        types = [i["type"] for i in issues]
        assert "misplaced_tests" in types

    def test_check_common_issues_detects_missing_gitignore(
        self, tmp_path: Path
    ) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        issues = sv._check_common_issues()
        types = [i["type"] for i in issues]
        assert "missing_gitignore" in types

    def test_generate_recommendations_lists_required_missing(
        self, tmp_path: Path
    ) -> None:
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        sv = StructureVerifier(tmp_path)
        report = sv.verify()
        assert len(report["recommendations"]) > 0

    def test_injected_policy_used(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_policy import StructurePolicy
        from claude_mpm.services.project.structure_verifier import StructureVerifier

        class MinimalPolicy(StructurePolicy):
            STANDARD_DIRECTORIES = {"minimal_dir": "A minimal directory"}

        sv = StructureVerifier(tmp_path, policy=MinimalPolicy())
        report = sv.verify()
        # Only the custom directory should appear in missing
        all_paths = {d["path"] for d in report["missing"]}
        assert "minimal_dir" in all_paths
        assert "tmp" not in all_paths


# ---------------------------------------------------------------------------
# TestStructureReporter
# ---------------------------------------------------------------------------


class TestStructureReporter:
    def _make_validation(self, score: int = 90) -> dict:
        grade = "A - Excellent structure" if score >= 90 else "B - Good structure"
        return {
            "is_valid": score >= 70,
            "errors": [],
            "warnings": [],
            "score": score,
            "grade": grade,
        }

    def _make_organize_result(self) -> dict:
        return {
            "dry_run": True,
            "proposed_moves": [],
            "completed_moves": [],
            "skipped": [],
            "errors": [],
            "total": 0,
            "total_skipped": 0,
            "total_errors": 0,
        }

    def test_to_markdown_contains_grade(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        md = reporter.to_markdown(
            self._make_validation(),
            self._make_organize_result(),
            {"recommendations": []},
            tmp_path / ".gitignore",
        )
        assert "A - Excellent structure" in md

    def test_to_markdown_lists_missing_gitignore(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        md = reporter.to_markdown(
            self._make_validation(),
            self._make_organize_result(),
            {"recommendations": []},
            tmp_path / ".gitignore",
        )
        assert "No .gitignore file found" in md

    def test_to_markdown_shows_gitignore_pattern_status(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("tmp/\n__pycache__\n.env\n*.log\n.claude-mpm/cache/\n")
        reporter = StructureReporter(tmp_path)
        md = reporter.to_markdown(
            self._make_validation(),
            self._make_organize_result(),
            {"recommendations": []},
            gitignore,
        )
        assert "[OK]" in md

    def test_to_markdown_shows_proposed_moves(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        organize = self._make_organize_result()
        organize["proposed_moves"] = [
            {
                "source": "test_foo.py",
                "target": "tests/test_foo.py",
                "reason": "Test file pattern",
                "confidence": "high",
            }
        ]
        reporter = StructureReporter(tmp_path)
        md = reporter.to_markdown(
            self._make_validation(),
            organize,
            {"recommendations": []},
            tmp_path / ".gitignore",
        )
        assert "test_foo.py" in md
        assert "Files to Reorganize" in md

    def test_to_markdown_includes_recommendations(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        md = reporter.to_markdown(
            self._make_validation(),
            self._make_organize_result(),
            {"recommendations": ["Create docs/ directory"]},
            tmp_path / ".gitignore",
        )
        assert "Create docs/ directory" in md

    def test_to_json_returns_required_keys(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        result = reporter.to_json(
            self._make_validation(),
            self._make_organize_result(),
            tmp_path / ".gitignore",
        )
        for key in (
            "project_path",
            "validation",
            "directories",
            "misplaced_files",
            "gitignore",
            "statistics",
        ):
            assert key in result

    def test_to_json_statistics_structure_score(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        result = reporter.to_json(
            self._make_validation(score=85),
            self._make_organize_result(),
            tmp_path / ".gitignore",
        )
        assert result["statistics"]["structure_score"] == 85

    def test_to_json_gitignore_exists_false_when_missing(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        reporter = StructureReporter(tmp_path)
        result = reporter.to_json(
            self._make_validation(),
            self._make_organize_result(),
            tmp_path / ".gitignore",
        )
        assert result["gitignore"]["exists"] is False

    def test_to_json_gitignore_patterns_status_populated(self, tmp_path: Path) -> None:
        from claude_mpm.services.project.structure_reporter import StructureReporter

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("tmp/\n__pycache__\n.env\n*.log\n.claude-mpm/cache/\n")
        reporter = StructureReporter(tmp_path)
        result = reporter.to_json(
            self._make_validation(),
            self._make_organize_result(),
            gitignore,
        )
        assert result["gitignore"]["exists"] is True
        assert result["gitignore"]["patterns_status"].get("tmp/") is True
