"""
StructureVerifier — read-only filesystem scanning and grading.
==============================================================

Receives an injected StructurePolicy so callers can substitute alternative
policies (e.g. in tests) without patching globals.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.project.structure_policy import StructurePolicy

logger = get_logger(__name__)


class StructureVerifier:
    """Scan a project directory tree and produce verification/validation dicts.

    Read-only: never modifies the filesystem.
    """

    def __init__(
        self, project_path: Path, policy: StructurePolicy | None = None
    ) -> None:
        self.project_path = project_path
        self.policy = policy or StructurePolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(self, project_type: str | None = None) -> dict:
        """Verify project structure and identify missing components.

        Returns a report dict with keys: project_path, exists, missing,
        issues, recommendations.
        """
        report: dict = {
            "project_path": str(self.project_path),
            "exists": [],
            "missing": [],
            "issues": [],
            "recommendations": [],
        }

        # Check standard directories
        for dir_name, description in self.policy.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                report["exists"].append(
                    {
                        "path": dir_name,
                        "description": description,
                        "is_directory": dir_path.is_dir(),
                    }
                )
            else:
                report["missing"].append(
                    {
                        "path": dir_name,
                        "description": description,
                        "required": self.policy.is_required_directory(
                            dir_name, project_type
                        ),
                    }
                )

        # Check project-type specific directories
        if project_type and project_type in self.policy.PROJECT_STRUCTURES:
            for dir_name in self.policy.PROJECT_STRUCTURES[project_type]:
                dir_path = self.project_path / dir_name
                if not dir_path.exists():
                    report["missing"].append(
                        {
                            "path": dir_name,
                            "description": f"{project_type} specific directory",
                            "required": False,
                        }
                    )

        report["issues"] = self._check_common_issues()
        report["recommendations"] = self._generate_recommendations(report)
        return report

    def validate(self, gitignore_path: Path) -> dict:
        """Validate the project structure and return a graded dict.

        Returned keys: is_valid, errors, warnings, score, grade.
        """
        validation: dict = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "score": 100,
        }

        # Check critical directories exist
        for dir_name in ("tmp", "scripts", "docs"):
            if not (self.project_path / dir_name).exists():
                validation["is_valid"] = False
                validation["errors"].append(f"Missing critical directory: {dir_name}/")
                validation["score"] -= 10

        # Check .gitignore completeness
        if not gitignore_path.exists():
            validation["is_valid"] = False
            validation["errors"].append("No .gitignore file found")
            validation["score"] -= 15
        else:
            gitignore_content = gitignore_path.read_text()
            for pattern in ("tmp/", "__pycache__", ".env", "*.log"):
                if pattern not in gitignore_content:
                    validation["warnings"].append(
                        f"Missing gitignore pattern: {pattern}"
                    )
                    validation["score"] -= 2

        # Check for files in wrong locations
        misplaced_count = sum(
            1
            for f in self.project_path.glob("*")
            if f.is_file()
            and (
                ("test" in f.name.lower() and f.suffix == ".py")
                or (f.suffix in (".sh", ".bash") and f.name not in ("Makefile",))
                or f.suffix in (".log", ".tmp", ".cache")
            )
        )
        if misplaced_count > 0:
            validation["warnings"].append(
                f"{misplaced_count} files potentially misplaced in root"
            )
            validation["score"] -= min(misplaced_count * 2, 20)

        # Grade
        score = validation["score"]
        if score >= 90:
            validation["grade"] = "A - Excellent structure"
        elif score >= 80:
            validation["grade"] = "B - Good structure"
        elif score >= 70:
            validation["grade"] = "C - Acceptable structure"
        elif score >= 60:
            validation["grade"] = "D - Needs improvement"
        else:
            validation["grade"] = "F - Poor structure"

        return validation

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_common_issues(self) -> list[dict]:
        """Check for common project organisation issues (read-only)."""
        issues: list[dict] = []
        gitignore_path = self.project_path / ".gitignore"

        root_py = list(self.project_path.glob("*.py"))

        test_files_in_root = [f for f in root_py if "test" in f.name.lower()]
        if test_files_in_root:
            issues.append(
                {
                    "type": "misplaced_tests",
                    "description": "Test files found in project root",
                    "files": [f.name for f in test_files_in_root],
                    "recommendation": "Move test files to tests/ directory",
                }
            )

        script_files = [
            f
            for f in root_py
            if not f.name.startswith(".")
            and f.name not in ("setup.py", "pyproject.toml")
        ]
        if script_files:
            issues.append(
                {
                    "type": "misplaced_scripts",
                    "description": "Script files found in project root",
                    "files": [f.name for f in script_files[:5]],
                    "recommendation": "Move scripts to scripts/ directory",
                }
            )

        if not gitignore_path.exists():
            issues.append(
                {
                    "type": "missing_gitignore",
                    "description": "No .gitignore file found",
                    "recommendation": "Create .gitignore with standard patterns",
                }
            )
        else:
            content = gitignore_path.read_text()
            missing_patterns = [
                p for p in ("tmp/", "__pycache__", ".env", "*.log") if p not in content
            ]
            if missing_patterns:
                issues.append(
                    {
                        "type": "incomplete_gitignore",
                        "description": "Common patterns missing from .gitignore",
                        "patterns": missing_patterns,
                        "recommendation": "Update .gitignore with missing patterns",
                    }
                )

        # Large files outside tmp/
        large_files: list[dict] = []
        for f in self.project_path.rglob("*"):
            if f.is_file() and not any(part.startswith(".") for part in f.parts):
                try:
                    size_mb = f.stat().st_size / (1024 * 1024)
                    if (
                        size_mb > 10
                        and "tmp" not in str(f)
                        and "node_modules" not in str(f)
                    ):
                        large_files.append(
                            {
                                "path": str(f.relative_to(self.project_path)),
                                "size_mb": round(size_mb, 2),
                            }
                        )
                except (OSError, PermissionError):
                    continue

        if large_files:
            issues.append(
                {
                    "type": "large_files",
                    "description": "Large files outside tmp/ directory",
                    "files": large_files[:5],
                    "recommendation": "Consider moving large files to tmp/ or adding to .gitignore",
                }
            )

        return issues

    def _generate_recommendations(self, report: dict) -> list[str]:
        """Generate recommendations based on a verify() *report*."""
        recommendations: list[str] = []

        required_missing = [d for d in report["missing"] if d.get("required")]
        if required_missing:
            recommendations.append(
                f"Create {len(required_missing)} required directories: "
                + ", ".join(d["path"] for d in required_missing)
            )

        for issue in report.get("issues", []):
            recommendations.append(issue["recommendation"])

        existing_paths = {d["path"] for d in report.get("exists", [])}
        if "docs" not in existing_paths:
            recommendations.append("Create docs/ directory for project documentation")

        return recommendations
