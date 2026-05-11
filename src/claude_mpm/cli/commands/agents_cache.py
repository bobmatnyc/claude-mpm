"""
Cache git management handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages git operations on the agent cache repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...core.enums import OutputFormat
from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentCacheHandler:
    """Handles cache git management commands.

    Receives the parent AgentsCommand as a service/state container so we can
    reuse the logger, formatter, and helper methods without duplicating state.
    """

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    @property
    def _formatter(self):
        return self.cmd._formatter

    def cache_status(self, args) -> CommandResult:
        """Show git status of agent cache.

        Displays current branch, uncommitted changes, unpushed commits, and
        remote URL for the agent cache repository.
        """
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                print(f"\nCache location: {cache_dir}")
                print(
                    "\n💡 This is expected if you haven't cloned the agents repository."
                )
                print("   The cache will be managed via HTTP sync instead.")
                return CommandResult.error_result("Cache is not a git repository")

            status = manager.get_status()
            output_format = self.cmd._get_output_format(args)

            if self.cmd._is_structured_format(output_format):
                formatted = (
                    self._formatter.format_as_json(status)
                    if str(output_format).lower() == OutputFormat.JSON
                    else self._formatter.format_as_yaml(status)
                )
                print(formatted)
                return CommandResult.success_result(
                    "Cache status retrieved", data=status
                )

            # Text output
            print(f"\n📁 Cache: {manager.repo_path}")
            print(f"🌿 Branch: {status.get('branch', 'unknown')}")

            if status.get("remote_url"):
                print(f"🔗 Remote: {status['remote_url']}")

            # Show sync status
            ahead = status.get("ahead", 0)
            behind = status.get("behind", 0)

            if ahead > 0:
                print(f"📤 Ahead of remote: {ahead} commit(s)")
            if behind > 0:
                print(f"📥 Behind remote: {behind} commit(s)")

            if ahead == 0 and behind == 0:
                print("✅ In sync with remote")

            # Show uncommitted changes
            uncommitted = status.get("uncommitted", [])
            if uncommitted:
                print(f"\n⚠️  Uncommitted changes: {len(uncommitted)}")
                for file in uncommitted[:10]:  # Show max 10 files
                    print(f"   - {file}")
                if len(uncommitted) > 10:
                    print(f"   ... and {len(uncommitted) - 10} more")
            else:
                print("\n✅ No uncommitted changes")

            # Overall status
            if status.get("is_clean"):
                print("\n✨ Cache is clean and up-to-date")
            else:
                print("\n💡 Run 'claude-mpm agents cache-sync' to sync with remote")

            return CommandResult.success_result("Cache status displayed", data=status)

        except Exception as e:
            self._logger.error(f"Error getting cache status: {e}", exc_info=True)
            return CommandResult.error_result(f"Error getting cache status: {e}")

    def cache_pull(self, args) -> CommandResult:
        """Pull latest agents from remote repository."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            branch = getattr(args, "branch", "main")
            print(f"🔄 Pulling latest changes from {branch}...")

            success, msg = manager.pull_latest(branch)

            if success:
                print(f"✅ {msg}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self._logger.error(f"Error pulling cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error pulling cache: {e}")

    def cache_commit(self, args) -> CommandResult:
        """Commit changes to cache repository."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            # Get commit message from args
            message = getattr(args, "message", None)
            if not message:
                # Default message
                message = "feat: update agents from local development"

            print("💾 Committing changes...")
            success, msg = manager.commit_changes(message)

            if success:
                print(f"✅ {msg}")
                print(f"\n💡 Commit message: {message}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self._logger.error(f"Error committing cache changes: {e}", exc_info=True)
            return CommandResult.error_result(f"Error committing cache changes: {e}")

    def cache_push(self, args) -> CommandResult:
        """Push local agent changes to remote."""
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            # Check for uncommitted changes
            if manager.has_uncommitted_changes():
                print("⚠️  You have uncommitted changes.")
                print("\n💡 Commit changes first with:")
                print("   claude-mpm agents cache-commit --message 'your message'")

                # Ask if user wants to commit first
                auto_commit = getattr(args, "auto_commit", False)
                if auto_commit:
                    print("\n📝 Auto-committing changes...")
                    success, msg = manager.commit_changes("feat: update agents")
                    if not success:
                        print(f"❌ Commit failed: {msg}")
                        return CommandResult.error_result(f"Commit failed: {msg}")
                    print(f"✅ {msg}")
                else:
                    return CommandResult.error_result(
                        "Uncommitted changes detected. Commit first or use --auto-commit"
                    )

            # Push changes
            branch = getattr(args, "branch", "main")
            print(f"📤 Pushing changes to {branch}...")

            success, msg = manager.push_changes(branch)

            if success:
                print(f"✅ {msg}")
                return CommandResult.success_result(msg)
            print(f"❌ {msg}")
            return CommandResult.error_result(msg)

        except Exception as e:
            self._logger.error(f"Error pushing cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error pushing cache: {e}")

    def cache_sync(self, args) -> CommandResult:
        """Full cache sync: pull, commit (if needed), push."""
        del args  # unused; method is dispatched uniformly via a table
        try:
            from ...services.agents.cache_git_manager import CacheGitManager

            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            manager = CacheGitManager(cache_dir)

            if not manager.is_git_repo():
                print("❌ Cache is not a git repository")
                return CommandResult.error_result("Cache is not a git repository")

            print("🔄 Syncing cache with remote...\n")

            success, msg = manager.sync_with_remote()

            # Print detailed sync message
            print(msg)

            if success:
                print("\n✨ Cache sync complete!")
                return CommandResult.success_result("Cache synced successfully")

            print("\n❌ Cache sync failed. See details above.")
            return CommandResult.error_result("Cache sync failed")

        except Exception as e:
            self._logger.error(f"Error syncing cache: {e}", exc_info=True)
            return CommandResult.error_result(f"Error syncing cache: {e}")
