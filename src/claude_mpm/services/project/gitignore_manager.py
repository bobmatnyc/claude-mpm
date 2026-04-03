"""
GitignoreManager — .gitignore read/diff/update logic.
======================================================

Owns exactly one file: the .gitignore at the path supplied at construction.
All pattern constants are exposed at module level so callers can import them
without instantiating the class.
"""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level constant (previously GITIGNORE_DIRS on ProjectOrganizer)
# ---------------------------------------------------------------------------

STANDARD_GITIGNORE_PATTERNS: frozenset[str] = frozenset(
    {
        # Temporary and cache directories
        "tmp/",
        "temp/",
        "*.tmp",
        "*.temp",
        "*.cache",
        ".claude-mpm/cache/",
        ".claude-mpm/logs/",
        ".claude/cache/",
        # MCP service directories for local data
        ".mcp-vector-search/",
        ".kuzu-memory/",
        "kuzu-memories/",
        # User-specific config files (should NOT be committed)
        ".mcp.json",
        ".claude.json",
        ".claude/",
        # Python artifacts
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        "*.egg-info/",
        "*.egg",
        "dist/",
        "build/",
        "develop-eggs/",
        ".eggs/",
        "wheels/",
        "pip-wheel-metadata/",
        "*.manifest",
        "*.spec",
        # Testing and coverage
        ".pytest_cache/",
        ".coverage",
        ".coverage.*",
        "htmlcov/",
        ".tox/",
        ".nox/",
        "*.cover",
        ".hypothesis/",
        ".pytype/",
        "coverage.xml",
        "*.pytest_cache",
        # Virtual environments
        ".env",
        ".venv",
        "env/",
        "venv/",
        "ENV/",
        "env.bak/",
        "venv.bak/",
        "virtualenv/",
        ".conda/",
        "conda-env/",
        # IDE and editor files
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*~",
        ".project",
        ".pydevproject",
        ".settings/",
        "*.sublime-workspace",
        "*.sublime-project",
        # OS-specific files
        ".DS_Store",
        "Thumbs.db",
        "ehthumbs.db",
        "Desktop.ini",
        "$RECYCLE.BIN/",
        "*.cab",
        "*.msi",
        "*.msm",
        "*.msp",
        "*.lnk",
        # Logs and databases
        "*.log",
        "*.sql",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
        "logs/",
        # Node/JavaScript
        "node_modules/",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
        ".npm",
        ".yarn/",
        # Documentation builds
        "_build/",
        "site/",
        "docs/_build/",
        # Security and credentials
        ".env.*",
        "*.pem",
        "*.key",
        "*.cert",
        "*.crt",
        ".secrets/",
        "credentials/",
        # Claude MPM specific
        ".claude-mpm/*.log",
        ".claude-mpm/sessions/",
        ".claude-mpm/tmp/",
        ".claude/sessions/",
        "*.mpm.tmp",
        # Backup files
        "*.bak",
        "*.backup",
        "*.old",
        "backup/",
        "backups/",
    }
)


class GitignoreManager:
    """Read, diff, and update a single .gitignore file."""

    def __init__(self, gitignore_path: Path) -> None:
        self.gitignore_path = gitignore_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, additional_patterns: list[str] | None = None) -> bool:
        """Add any missing standard patterns (plus *additional_patterns*).

        Returns True when the file was modified, False when no change was
        needed or an error occurred.
        """
        try:
            existing = self._read_existing()

            all_patterns: frozenset[str] = STANDARD_GITIGNORE_PATTERNS
            if additional_patterns:
                all_patterns = all_patterns | frozenset(additional_patterns)

            missing = all_patterns - existing

            if not missing:
                logger.info(".gitignore already contains all standard patterns")
                return False

            # Build the new section and append
            current_text = (
                self.gitignore_path.read_text() if self.gitignore_path.exists() else ""
            )
            new_section = "\n# Added by Claude MPM /mpm-init\n"
            for pattern in sorted(missing):
                new_section += f"{pattern}\n"

            if current_text and not current_text.endswith("\n"):
                current_text += "\n"
            self.gitignore_path.write_text(current_text + new_section)

            logger.info(f"Updated .gitignore with {len(missing)} patterns")
            return True

        except Exception as exc:
            logger.error(f"Failed to update .gitignore: {exc}")
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_existing(self) -> set[str]:
        """Return the set of non-comment, non-empty lines currently in the file."""
        if not self.gitignore_path.exists():
            return set()
        lines = self.gitignore_path.read_text().splitlines()
        return {
            line.strip() for line in lines if line.strip() and not line.startswith("#")
        }
