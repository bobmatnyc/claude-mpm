"""Git worktree manager for session isolation."""

import logging
import subprocess  # nosec B404 - subprocess needed for git commands
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Info about a git worktree."""

    name: str
    path: Path
    branch: str
    base_path: Path  # Original repo path


class WorktreeManager:
    """Manages git worktrees for session isolation."""

    def __init__(self, base_path: Path):
        """Initialize with base project path."""
        self.base_path = Path(base_path)
        self.worktrees_dir = self.base_path.parent / f".worktrees-{self.base_path.name}"

    def create(self, name: str, branch: Optional[str] = None) -> WorktreeInfo:
        """Create a worktree for a session.

        Args:
            name: Session/worktree name (e.g., "izzie")
            branch: Branch name, defaults to session-{name}

        Returns:
            WorktreeInfo with path and branch details
        """
        branch = branch or f"session-{name}"
        worktree_path = self.worktrees_dir / name

        # Ensure worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        # Check if worktree already exists
        if worktree_path.exists():
            logger.info(f"Worktree '{name}' already exists at {worktree_path}")
            return self._get_worktree_info(name, worktree_path)

        # Create new branch if it doesn't exist
        try:
            subprocess.run(  # nosec B603 B607 - git command with safe args
                ["git", "branch", branch],
                cwd=self.base_path,
                capture_output=True,
                check=False,  # Branch may already exist
            )
        except Exception as e:
            logger.warning(f"Could not create branch {branch}: {e}")

        # Create worktree
        result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "worktree", "add", str(worktree_path), branch],
            check=False,
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        logger.info(f"Created worktree '{name}' at {worktree_path} on branch {branch}")
        return WorktreeInfo(
            name=name, path=worktree_path, branch=branch, base_path=self.base_path
        )

    def _get_worktree_info(self, name: str, path: Path) -> WorktreeInfo:
        """Get info for existing worktree."""
        result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "branch", "--show-current"],
            check=False,
            cwd=path,
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip() or f"session-{name}"
        return WorktreeInfo(
            name=name, path=path, branch=branch, base_path=self.base_path
        )

    def list(self) -> list[WorktreeInfo]:
        """List all worktrees for this project."""
        result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "worktree", "list", "--porcelain"],
            check=False,
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )

        worktrees = []
        current_path = None
        current_branch = None

        for line in result.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                current_path = Path(line.split(" ", 1)[1])
            elif line.startswith("branch "):
                current_branch = line.split("/")[-1]  # refs/heads/branch -> branch
            elif line == "":
                if current_path and str(self.worktrees_dir) in str(current_path):
                    name = current_path.name
                    worktrees.append(
                        WorktreeInfo(
                            name=name,
                            path=current_path,
                            branch=current_branch or f"session-{name}",
                            base_path=self.base_path,
                        )
                    )
                current_path = None
                current_branch = None

        return worktrees

    def remove(self, name: str, force: bool = False) -> bool:
        """Remove a worktree."""
        worktree_path = self.worktrees_dir / name

        if not worktree_path.exists():
            return False

        args = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            args.insert(3, "--force")

        result = subprocess.run(  # nosec B603 B607 - git command with safe args
            args, check=False, cwd=self.base_path, capture_output=True, text=True
        )
        return result.returncode == 0

    def get(self, name: str) -> Optional[WorktreeInfo]:
        """Get worktree by name."""
        worktree_path = self.worktrees_dir / name
        if worktree_path.exists():
            return self._get_worktree_info(name, worktree_path)
        return None

    def merge_to_main(self, name: str, delete_after: bool = True) -> tuple[bool, str]:
        """Merge worktree branch back to main and optionally delete worktree.

        Args:
            name: Worktree name to merge
            delete_after: Remove worktree after merge (default True)

        Returns:
            Tuple of (success, message)
        """
        worktree = self.get(name)
        if not worktree:
            return False, f"Worktree '{name}' not found"

        # Get main branch name
        result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            check=False,
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )
        main_branch = (
            result.stdout.strip().split("/")[-1] if result.returncode == 0 else "main"
        )

        # Checkout main in base repo
        checkout_result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "checkout", main_branch],
            check=False,
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )
        if checkout_result.returncode != 0:
            return False, f"Failed to checkout {main_branch}: {checkout_result.stderr}"

        # Merge worktree branch
        merge_result = subprocess.run(  # nosec B603 B607 - git command with safe args
            ["git", "merge", worktree.branch, "--no-edit"],
            check=False,
            cwd=self.base_path,
            capture_output=True,
            text=True,
        )

        if merge_result.returncode != 0:
            return False, f"Merge failed: {merge_result.stderr}"

        # Delete worktree if requested
        if delete_after:
            self.remove(name, force=True)
            # Delete branch
            subprocess.run(  # nosec B603 B607 - git command with safe args
                ["git", "branch", "-d", worktree.branch],
                check=False,
                cwd=self.base_path,
                capture_output=True,
            )

        logger.info(f"Merged '{worktree.branch}' to {main_branch}")
        return True, f"Merged '{worktree.branch}' to {main_branch}"
