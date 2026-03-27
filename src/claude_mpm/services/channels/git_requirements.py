"""Git state validation before allowing session creation.

Checks branch patterns and working tree cleanliness as specified in
bot-permissions.yaml git requirements.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitRequirementsChecker:
    """Validates git state before allowing session creation."""

    async def check(
        self,
        project_root: str,
        branch_pattern: str = ".*",
        require_clean: str = "ignore",
    ) -> tuple[bool, str]:
        """Check git requirements for a project root.

        Args:
            project_root: Path to the git repository.
            branch_pattern: Regex pattern that the current branch must match.
            require_clean: "ignore" | "warn" | "block"
                - ignore: don't check working tree state
                - warn: log a warning if dirty, but allow
                - block: reject if working tree has uncommitted changes

        Returns:
            (allowed: bool, reason: str)
            allowed=True means the session can proceed.
            reason is empty on success, or describes the failure.
        """
        root = Path(project_root)
        if not (root / ".git").exists():
            return True, ""  # Not a git repo, no requirements apply

        # Check branch pattern
        current_branch = self._get_current_branch(root)
        if current_branch and not re.match(branch_pattern, current_branch):
            return (
                False,
                f"Branch '{current_branch}' does not match pattern '{branch_pattern}'",
            )

        # Check clean state
        if require_clean != "ignore":
            is_clean = self._is_clean(root)
            if not is_clean:
                if require_clean == "block":
                    return (
                        False,
                        "Working tree has uncommitted changes (require_clean=block)",
                    )
                if require_clean == "warn":
                    logger.warning(
                        "Working tree at %s has uncommitted changes "
                        "(require_clean=warn)",
                        root,
                    )

        return True, ""

    @staticmethod
    def _get_current_branch(root: Path) -> str | None:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                check=False,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    @staticmethod
    def _is_clean(root: Path) -> bool:
        """Check if the working tree is clean (no uncommitted changes)."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=False,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return len(result.stdout.strip()) == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return True  # Fail-open: if we can't check, allow
