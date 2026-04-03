"""
DirectoryCreator — mkdir and README-stub operations.
=====================================================

Write-only module: only creates directories and writes README stubs.
Takes a pre-built verify report from StructureVerifier so it has zero
dependency on scanning/policy logic.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# Directories that receive a README stub when first created.
_README_DIRS: frozenset[str] = frozenset(
    {"tmp", "scripts", "docs/_archive", ".claude-mpm/memories"}
)

# Per-directory usage text appended after the common header.
_README_USAGE: dict[str, str] = {
    "tmp": (
        "- Place all temporary files and test outputs here\n"
        "- This directory is gitignored - contents will not be committed\n"
        "- Clean up old files periodically to save disk space\n"
        "- Use subdirectories to organize different types of temporary files\n"
    ),
    "scripts": (
        "- All project scripts should be placed here\n"
        "- Use descriptive names for scripts\n"
        "- Include comments and usage instructions in scripts\n"
        "- Make scripts executable with `chmod +x script_name.sh`\n"
    ),
    "docs/_archive": (
        "- Archived documentation versions are stored here\n"
        "- Files are timestamped when archived\n"
        "- Preserve important historical documentation\n"
        "- Review and clean up old archives periodically\n"
    ),
    ".claude-mpm/memories": (
        "- Agent memory files are stored here\n"
        "- Each agent can have its own memory file\n"
        "- Memories persist between sessions\n"
        "- Update memories when project knowledge changes\n"
    ),
}


class DirectoryCreator:
    """Create missing directories and optional README stubs.

    Write-only: never reads the filesystem for scanning purposes.
    Accepts a pre-built report dict (from StructureVerifier.verify()) so the
    two concerns stay separate.
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_missing(self, report: dict, force: bool = False) -> dict:
        """Create directories listed in *report["missing"]*.

        Args:
            report: Result dict from StructureVerifier.verify().
            force:  When True, create even non-required directories.

        Returns:
            ``{"created": [...], "skipped": [...], "errors": [...]}``.
        """
        created: list[str] = []
        skipped: list[str] = []
        errors: list[dict] = []

        for dir_info in report.get("missing", []):
            dir_name: str = dir_info["path"]
            dir_path = self.project_path / dir_name

            if not dir_info.get("required") and not force:
                skipped.append(dir_name)
                continue

            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(dir_name)
                logger.info("Created directory: %s", dir_path)
                self._add_readme(dir_path, dir_info.get("description", ""))
            except Exception as exc:
                errors.append({"path": dir_name, "error": str(exc)})
                logger.error("Failed to create %s: %s", dir_path, exc)

        return {"created": created, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_readme(self, dir_path: Path, description: str) -> None:
        """Write a README.md stub into *dir_path* for well-known directories."""
        # Determine which key to look up (use relative suffix matching)
        matched_key: str | None = None
        for key in _README_DIRS:
            if str(dir_path).endswith(key):
                matched_key = key
                break

        if matched_key is None:
            return

        readme_path = dir_path / "README.md"
        if readme_path.exists():
            return

        usage = _README_USAGE.get(matched_key, "")
        content = (
            f"# {dir_path.name}\n\n"
            f"{description}\n\n"
            "## Purpose\n\n"
            f"This directory is used for {description.lower()}.\n\n"
            "## Usage Guidelines\n\n"
            f"{usage}"
        )
        readme_path.write_text(content)
        logger.debug("Created README in %s", dir_path)
