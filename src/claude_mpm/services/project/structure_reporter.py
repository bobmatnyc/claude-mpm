"""
StructureReporter — markdown and JSON report generation.
=========================================================

Receives pre-computed validation and organize-result dicts from the thin
coordinator so it has zero dependency on filesystem scanning.

All public methods are pure transformations: dict/str inputs → str/dict output.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.project.structure_policy import StructurePolicy

logger = get_logger(__name__)

# Critical gitignore patterns checked in reports.
_CRITICAL_PATTERNS: tuple[str, ...] = (
    "tmp/",
    "__pycache__",
    ".env",
    "*.log",
    ".claude-mpm/cache/",
)


class StructureReporter:
    """Generate markdown and JSON structure reports.

    Accepts pre-computed dicts so tests can pass synthetic data directly.
    """

    def __init__(
        self, project_path: Path, policy: StructurePolicy | None = None
    ) -> None:
        self.project_path = project_path
        self.policy = policy or StructurePolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_markdown(
        self,
        validation: dict,
        organize_result: dict,
        structure_report: dict,
        gitignore_path: Path,
    ) -> str:
        """Render a human-readable markdown report.

        Args:
            validation:      Result from StructureVerifier.validate().
            organize_result: Result from FileOrganizer.organize(dry_run=True).
            structure_report: Result from StructureVerifier.verify().
            gitignore_path:  Path to the .gitignore file (may not exist).

        Returns:
            Markdown string.
        """
        doc = "# Project Structure Report\n\n## Structure Validation\n\n"

        doc += f"**Overall Grade:** {validation.get('grade', 'Not evaluated')}\n"
        doc += f"**Score:** {validation.get('score', 0)}/100\n\n"

        if validation.get("errors"):
            doc += "### Critical Issues\n"
            for error in validation["errors"]:
                doc += f"- {error}\n"
            doc += "\n"

        if validation.get("warnings"):
            doc += "### Warnings\n"
            for warning in validation["warnings"]:
                doc += f"- {warning}\n"
            doc += "\n"

        doc += "## Directory Organization\n\n"

        for dir_name, description in self.policy.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                doc += f"### `{dir_name}/`\n{description}\n\n"
                try:
                    contents = list(dir_path.iterdir())[:5]
                    if contents:
                        doc += "**Contents:**\n"
                        for item in contents:
                            suffix = "/ (directory)" if item.is_dir() else ""
                            doc += f"- {item.name}{suffix}\n"
                        all_items = list(dir_path.iterdir())
                        if len(all_items) > 5:
                            doc += f"- ... and {len(all_items) - 5} more items\n"
                        doc += "\n"
                except PermissionError:
                    doc += "*Permission denied to list contents*\n\n"
            else:
                doc += f"### `{dir_name}/` (Missing)\n{description}\n\n"

        proposed = organize_result.get("proposed_moves", [])
        if proposed:
            doc += "## Files to Reorganize\n\n"
            doc += "The following files could be better organized:\n\n"
            for move in proposed[:10]:
                doc += f"- `{move['source']}` -> `{move['target']}`\n"
                doc += f"  - Reason: {move['reason']}\n"
                doc += f"  - Confidence: {move['confidence']}\n"
            if len(proposed) > 10:
                doc += f"\n... and {len(proposed) - 10} more files\n"
            doc += "\n"

        doc += "## .gitignore Configuration\n\n"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            doc += "### Critical Patterns Status:\n"
            for pattern in _CRITICAL_PATTERNS:
                status = "OK" if pattern in gitignore_content else "MISSING"
                doc += f"- [{status}] `{pattern}`\n"
            doc += "\n"
        else:
            doc += "No .gitignore file found\n\n"

        recommendations = structure_report.get("recommendations", [])
        if recommendations:
            doc += "## Recommendations\n\n"
            for rec in recommendations:
                doc += f"- {rec}\n"
            doc += "\n"

        doc += "## Quick Fix Commands\n\n"
        doc += "```bash\n"
        doc += "# Run complete initialization\n"
        doc += "claude-mpm mpm-init --organize\n\n"
        doc += "# Review without changes\n"
        doc += "claude-mpm mpm-init --review\n\n"
        doc += "# Update existing documentation\n"
        doc += "claude-mpm mpm-init --update\n"
        doc += "```\n"

        return doc

    def to_json(
        self,
        validation: dict,
        organize_result: dict,
        gitignore_path: Path,
    ) -> dict:
        """Build a comprehensive JSON structure report dict.

        Args:
            validation:      Result from StructureVerifier.validate().
            organize_result: Result from FileOrganizer.organize(dry_run=True).
            gitignore_path:  Path to the .gitignore file (may not exist).

        Returns:
            Dict suitable for JSON serialisation.
        """
        report: dict = {
            "project_path": str(self.project_path),
            "validation": validation,
            "directories": {},
            "misplaced_files": organize_result,
            "gitignore": {
                "exists": gitignore_path.exists(),
                "patterns_status": {},
            },
            "statistics": {
                "total_directories": 0,
                "total_files": 0,
                "misplaced_files": len(organize_result.get("proposed_moves", [])),
                "structure_score": validation.get("score", 0),
            },
        }

        for dir_name, description in self.policy.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            exists = dir_path.exists()
            report["directories"][dir_name] = {
                "exists": exists,
                "description": description,
                "file_count": len(list(dir_path.glob("*"))) if exists else 0,
                "is_directory": dir_path.is_dir() if exists else None,
            }
            if exists:
                report["statistics"]["total_directories"] += 1

        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            for pattern in _CRITICAL_PATTERNS:
                report["gitignore"]["patterns_status"][pattern] = (
                    pattern in gitignore_content
                )

        for item in self.project_path.rglob("*"):
            if item.is_file():
                report["statistics"]["total_files"] += 1

        return report
