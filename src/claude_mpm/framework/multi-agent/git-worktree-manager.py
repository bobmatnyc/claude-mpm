"""
Claude PM Framework - Git Worktree Manager
Manages isolated git worktrees for parallel agent execution.
"""

import os
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
import uuid
from datetime import datetime


class WorktreeStatus(str, Enum):
    """Worktree status enumeration."""
    CREATING = "creating"
    ACTIVE = "active"
    BUSY = "busy"
    CLEANING = "cleaning"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class WorktreeInfo:
    """Information about a git worktree."""
    worktree_id: str
    agent_id: str
    path: Path
    branch: str
    status: WorktreeStatus
    created_at: datetime
    last_used: Optional[datetime] = None
    process_id: Optional[str] = None
    lock_reason: Optional[str] = None


class GitWorktreeManager:
    """
    Manages git worktrees for parallel agent execution.
    Provides isolation between agents working on the same repository.
    """
    
    def __init__(self, base_repo_path: str, worktree_base_path: str = None):
        """
        Initialize the worktree manager.
        
        Args:
            base_repo_path: Path to the main git repository
            worktree_base_path: Base path for creating worktrees (defaults to base_repo/.worktrees)
        """
        self.base_repo_path = Path(base_repo_path).resolve()
        self.worktree_base_path = Path(worktree_base_path or self.base_repo_path / ".worktrees")
        self.active_worktrees: Dict[str, WorktreeInfo] = {}
        self.max_worktrees = 10  # Maximum number of concurrent worktrees
        
        # Ensure base paths exist and are valid
        self._validate_base_repository()
        self._ensure_worktree_directory()
        
        # Load existing worktrees
        self._discover_existing_worktrees()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _validate_base_repository(self):
        """Validate that the base path is a git repository."""
        if not self.base_repo_path.exists():
            raise ValueError(f"Base repository path does not exist: {self.base_repo_path}")
        
        git_dir = self.base_repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.base_repo_path}")
    
    def _ensure_worktree_directory(self):
        """Ensure the worktree base directory exists."""
        self.worktree_base_path.mkdir(parents=True, exist_ok=True)
        
        # Add .gitignore to exclude worktrees from main repo
        gitignore_path = self.base_repo_path / ".gitignore"
        gitignore_entry = ".worktrees/"
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
            if gitignore_entry not in content:
                with open(gitignore_path, 'a') as f:
                    f.write(f"\n# Agent worktrees\n{gitignore_entry}\n")
        else:
            with open(gitignore_path, 'w') as f:
                f.write(f"# Agent worktrees\n{gitignore_entry}\n")
    
    def _discover_existing_worktrees(self):
        """Discover existing worktrees from git worktree list."""
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.base_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            worktrees = self._parse_worktree_list(result.stdout)
            for worktree_path, branch in worktrees:
                worktree_path = Path(worktree_path)
                if worktree_path.parent == self.worktree_base_path:
                    # This is one of our managed worktrees
                    worktree_id = worktree_path.name
                    self.active_worktrees[worktree_id] = WorktreeInfo(
                        worktree_id=worktree_id,
                        agent_id="unknown",  # Will be determined on first use
                        path=worktree_path,
                        branch=branch,
                        status=WorktreeStatus.ACTIVE,
                        created_at=datetime.now()
                    )
                    
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to discover existing worktrees: {e}")
    
    def _parse_worktree_list(self, output: str) -> List[Tuple[str, str]]:
        """Parse git worktree list output."""
        worktrees = []
        lines = output.strip().split('\n')
        current_path = None
        current_branch = None
        
        for line in lines:
            if line.startswith('worktree '):
                current_path = line.split(' ', 1)[1]
            elif line.startswith('branch '):
                current_branch = line.split(' ', 1)[1].replace('refs/heads/', '')
            elif line == '' and current_path and current_branch:
                worktrees.append((current_path, current_branch))
                current_path = None
                current_branch = None
        
        # Handle last worktree if no trailing newline
        if current_path and current_branch:
            worktrees.append((current_path, current_branch))
        
        return worktrees
    
    def create_worktree(self, agent_id: str, branch: str = None) -> str:
        """
        Create a new worktree for an agent.
        
        Args:
            agent_id: ID of the agent requesting the worktree
            branch: Branch to checkout (defaults to current branch)
            
        Returns:
            worktree_id: Unique identifier for the created worktree
            
        Raises:
            RuntimeError: If worktree creation fails or limits exceeded
        """
        if len(self.active_worktrees) >= self.max_worktrees:
            raise RuntimeError(f"Maximum number of worktrees ({self.max_worktrees}) exceeded")
        
        # Generate unique worktree ID
        worktree_id = f"agent-{agent_id}-{uuid.uuid4().hex[:8]}"
        worktree_path = self.worktree_base_path / worktree_id
        
        # Determine branch to use
        if not branch:
            branch = self._get_current_branch()
        
        try:
            # Create the worktree
            self.logger.info(f"Creating worktree {worktree_id} for agent {agent_id} on branch {branch}")
            
            cmd = ["git", "worktree", "add", str(worktree_path), branch]
            result = subprocess.run(
                cmd,
                cwd=self.base_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Create worktree info
            worktree_info = WorktreeInfo(
                worktree_id=worktree_id,
                agent_id=agent_id,
                path=worktree_path,
                branch=branch,
                status=WorktreeStatus.ACTIVE,
                created_at=datetime.now()
            )
            
            self.active_worktrees[worktree_id] = worktree_info
            
            self.logger.info(f"Successfully created worktree {worktree_id} at {worktree_path}")
            return worktree_id
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create worktree {worktree_id}: {e.stderr}")
            raise RuntimeError(f"Git worktree creation failed: {e.stderr}")
    
    def get_worktree_path(self, worktree_id: str) -> Path:
        """Get the filesystem path for a worktree."""
        if worktree_id not in self.active_worktrees:
            raise ValueError(f"Worktree {worktree_id} not found")
        
        return self.active_worktrees[worktree_id].path
    
    def lock_worktree(self, worktree_id: str, process_id: str, reason: str = None) -> bool:
        """
        Lock a worktree for exclusive use by a process.
        
        Args:
            worktree_id: ID of the worktree to lock
            process_id: ID of the process locking the worktree
            reason: Optional reason for the lock
            
        Returns:
            True if lock acquired, False if already locked
        """
        if worktree_id not in self.active_worktrees:
            raise ValueError(f"Worktree {worktree_id} not found")
        
        worktree = self.active_worktrees[worktree_id]
        
        if worktree.status == WorktreeStatus.BUSY and worktree.process_id != process_id:
            return False  # Already locked by another process
        
        worktree.status = WorktreeStatus.BUSY
        worktree.process_id = process_id
        worktree.lock_reason = reason
        worktree.last_used = datetime.now()
        
        self.logger.info(f"Locked worktree {worktree_id} for process {process_id}")
        return True
    
    def unlock_worktree(self, worktree_id: str, process_id: str) -> bool:
        """
        Unlock a worktree.
        
        Args:
            worktree_id: ID of the worktree to unlock
            process_id: ID of the process that locked the worktree
            
        Returns:
            True if unlocked successfully, False if not locked by this process
        """
        if worktree_id not in self.active_worktrees:
            raise ValueError(f"Worktree {worktree_id} not found")
        
        worktree = self.active_worktrees[worktree_id]
        
        if worktree.process_id != process_id:
            return False  # Not locked by this process
        
        worktree.status = WorktreeStatus.ACTIVE
        worktree.process_id = None
        worktree.lock_reason = None
        
        self.logger.info(f"Unlocked worktree {worktree_id} from process {process_id}")
        return True
    
    def destroy_worktree(self, worktree_id: str) -> bool:
        """
        Destroy a worktree and clean up resources.
        
        Args:
            worktree_id: ID of the worktree to destroy
            
        Returns:
            True if destroyed successfully, False if worktree was busy
        """
        if worktree_id not in self.active_worktrees:
            raise ValueError(f"Worktree {worktree_id} not found")
        
        worktree = self.active_worktrees[worktree_id]
        
        # Don't destroy busy worktrees
        if worktree.status == WorktreeStatus.BUSY:
            self.logger.warning(f"Cannot destroy busy worktree {worktree_id}")
            return False
        
        try:
            self.logger.info(f"Destroying worktree {worktree_id}")
            worktree.status = WorktreeStatus.CLEANING
            
            # Remove the worktree from git
            subprocess.run(
                ["git", "worktree", "remove", str(worktree.path), "--force"],
                cwd=self.base_repo_path,
                check=True
            )
            
            # Clean up any remaining files
            if worktree.path.exists():
                shutil.rmtree(worktree.path)
            
            # Remove from tracking
            worktree.status = WorktreeStatus.DESTROYED
            del self.active_worktrees[worktree_id]
            
            self.logger.info(f"Successfully destroyed worktree {worktree_id}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to destroy worktree {worktree_id}: {e}")
            worktree.status = WorktreeStatus.ERROR
            return False
    
    def list_worktrees(self) -> List[WorktreeInfo]:
        """List all active worktrees."""
        return list(self.active_worktrees.values())
    
    def get_worktree_info(self, worktree_id: str) -> WorktreeInfo:
        """Get information about a specific worktree."""
        if worktree_id not in self.active_worktrees:
            raise ValueError(f"Worktree {worktree_id} not found")
        
        return self.active_worktrees[worktree_id]
    
    def cleanup_unused_worktrees(self, max_age_hours: int = 24) -> int:
        """
        Clean up worktrees that haven't been used recently.
        
        Args:
            max_age_hours: Maximum age in hours before a worktree is considered unused
            
        Returns:
            Number of worktrees cleaned up
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        # Find unused worktrees
        to_cleanup = []
        for worktree_id, worktree in self.active_worktrees.items():
            if worktree.status == WorktreeStatus.ACTIVE:
                last_used = worktree.last_used or worktree.created_at
                if last_used < cutoff_time:
                    to_cleanup.append(worktree_id)
        
        # Clean them up
        for worktree_id in to_cleanup:
            if self.destroy_worktree(worktree_id):
                cleaned_count += 1
        
        self.logger.info(f"Cleaned up {cleaned_count} unused worktrees")
        return cleaned_count
    
    def _get_current_branch(self) -> str:
        """Get the current branch of the base repository."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.base_repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to main/master
            return "main"
    
    def get_stats(self) -> Dict[str, int]:
        """Get worktree manager statistics."""
        stats = {
            "total_worktrees": len(self.active_worktrees),
            "active_worktrees": sum(1 for w in self.active_worktrees.values() if w.status == WorktreeStatus.ACTIVE),
            "busy_worktrees": sum(1 for w in self.active_worktrees.values() if w.status == WorktreeStatus.BUSY),
            "error_worktrees": sum(1 for w in self.active_worktrees.values() if w.status == WorktreeStatus.ERROR),
            "max_worktrees": self.max_worktrees
        }
        return stats


# Context manager for automatic worktree lifecycle management
class WorktreeContext:
    """Context manager for automatic worktree creation and cleanup."""
    
    def __init__(self, manager: GitWorktreeManager, agent_id: str, branch: str = None):
        self.manager = manager
        self.agent_id = agent_id
        self.branch = branch
        self.worktree_id = None
        self.process_id = str(uuid.uuid4())
    
    def __enter__(self) -> Tuple[str, Path]:
        """Create and lock a worktree."""
        self.worktree_id = self.manager.create_worktree(self.agent_id, self.branch)
        self.manager.lock_worktree(self.worktree_id, self.process_id, "Context manager")
        path = self.manager.get_worktree_path(self.worktree_id)
        return self.worktree_id, path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Unlock and optionally destroy the worktree."""
        if self.worktree_id:
            self.manager.unlock_worktree(self.worktree_id, self.process_id)
            # Note: Not auto-destroying to allow for inspection/reuse
            # Cleanup will happen via cleanup_unused_worktrees()


# Factory function
def create_worktree_manager(base_repo_path: str, worktree_base_path: str = None) -> GitWorktreeManager:
    """Create and initialize a git worktree manager."""
    return GitWorktreeManager(base_repo_path, worktree_base_path)