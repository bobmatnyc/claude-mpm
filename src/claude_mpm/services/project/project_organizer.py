"""
ProjectOrganizer — thin coordinator for project-structure management.
=====================================================================

Implementation note
-------------------
All logic is delegated to focused collaborators:

  - StructurePolicy    (structure_policy.py)     — directory constants & rules
  - StructureVerifier  (structure_verifier.py)   — read-only scanning & grading
  - DirectoryCreator   (directory_creator.py)    — mkdir + README stubs
  - GitignoreManager   (gitignore_manager.py)    — .gitignore read/diff/update
  - FileOrganizer      (file_organizer.py)       — file classification & moves
  - StructureReporter  (structure_reporter.py)   — markdown & JSON reports

Public method signatures are identical to the original God Class so that
callers (core.py, modes.py) need zero changes.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.project.directory_creator import DirectoryCreator
from claude_mpm.services.project.file_organizer import FileOrganizer
from claude_mpm.services.project.gitignore_manager import GitignoreManager
from claude_mpm.services.project.structure_policy import StructurePolicy
from claude_mpm.services.project.structure_reporter import StructureReporter
from claude_mpm.services.project.structure_verifier import StructureVerifier

logger = get_logger(__name__)


class ProjectOrganizer:
    """Thin coordinator — delegates all logic to focused collaborators.

    Callers construct this class exactly as before:
        organizer = ProjectOrganizer(project_path)
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.gitignore_path = project_path / ".gitignore"

        # Collaborator instances (created once, reused across calls)
        self._policy = StructurePolicy()
        self._verifier = StructureVerifier(project_path, self._policy)
        self._creator = DirectoryCreator(project_path)
        self._gitignore = GitignoreManager(self.gitignore_path)
        self._organizer = FileOrganizer(project_path)
        self._reporter = StructureReporter(project_path, self._policy)

        # Cached verify report (matches original self.structure_report behaviour)
        self.structure_report: dict = {}

    # ------------------------------------------------------------------
    # Public API — identical signatures to the original God Class
    # ------------------------------------------------------------------

    def verify_structure(self, project_type: str | None = None) -> dict:
        """Verify project structure and identify missing components."""
        report = self._verifier.verify(project_type)
        self.structure_report = report
        return report

    def validate_structure(self) -> dict:
        """Validate the project structure and return a graded dict."""
        return self._verifier.validate(self.gitignore_path)

    def create_missing_directories(self, force: bool = False) -> dict:
        """Create missing standard directories."""
        report = self.verify_structure()
        return self._creator.create_missing(report, force=force)

    def update_gitignore(self, additional_patterns: list[str] | None = None) -> bool:
        """Update or create .gitignore with standard patterns."""
        return self._gitignore.update(additional_patterns)

    def organize_misplaced_files(
        self, dry_run: bool = True, auto_safe: bool = True
    ) -> dict:
        """Organize misplaced files into proper directories."""
        return self._organizer.organize(dry_run=dry_run, auto_safe=auto_safe)

    def generate_structure_documentation(self) -> str:
        """Generate markdown documentation of project structure."""
        validation = self.validate_structure()
        organize_result = self.organize_misplaced_files(dry_run=True, auto_safe=True)
        structure_report = self.structure_report or self.verify_structure()
        return self._reporter.to_markdown(
            validation, organize_result, structure_report, self.gitignore_path
        )

    def generate_structure_report_json(self) -> dict:
        """Generate a comprehensive JSON structure report."""
        validation = self.validate_structure()
        organize_result = self.organize_misplaced_files(dry_run=True, auto_safe=True)
        return self._reporter.to_json(validation, organize_result, self.gitignore_path)

    def ensure_project_ready(
        self, auto_organize: bool = False, safe_mode: bool = True
    ) -> tuple[bool, list[str]]:
        """Ensure project is ready for Claude MPM usage."""
        actions_taken: list[str] = []
        issues_found: list[str] = []

        # Verify structure (caches result in self.structure_report)
        self.verify_structure()

        # Create required directories
        result = self.create_missing_directories(force=False)
        if result["created"]:
            actions_taken.append(f"Created {len(result['created'])} directories")

        # Ensure tmp/ exists with a README
        tmp_dir = self.project_path / "tmp"
        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True, exist_ok=True)
            self._creator._add_readme(
                tmp_dir, "Temporary files, test outputs, and experiments"
            )
            actions_taken.append("Created tmp/ directory with README")

        # Update .gitignore
        if self.update_gitignore():
            actions_taken.append("Updated .gitignore with comprehensive patterns")

        # Check / perform file organisation
        organize_result = self.organize_misplaced_files(
            dry_run=True, auto_safe=safe_mode
        )
        if organize_result["proposed_moves"]:
            if auto_organize:
                actual = self.organize_misplaced_files(
                    dry_run=False, auto_safe=safe_mode
                )
                if actual["completed_moves"]:
                    actions_taken.append(
                        f"Organized {len(actual['completed_moves'])} files into proper directories"
                    )
                if actual["errors"]:
                    issues_found.append(f"Failed to move {len(actual['errors'])} files")
            else:
                actions_taken.append(
                    f"Identified {len(organize_result['proposed_moves'])} files to reorganize "
                    "(use --organize to move)"
                )
                if organize_result["skipped"]:
                    actions_taken.append(
                        f"Skipped {len(organize_result['skipped'])} low-confidence moves"
                    )

        # Surface non-file-placement issues
        for issue in self.structure_report.get("issues", []):
            if issue["type"] not in ("misplaced_scripts", "misplaced_tests"):
                issues_found.append(issue["description"])

        # Final validation
        validation = self.validate_structure()
        if not validation["is_valid"]:
            issues_found.extend(validation["errors"])

        return len(issues_found) == 0, actions_taken
