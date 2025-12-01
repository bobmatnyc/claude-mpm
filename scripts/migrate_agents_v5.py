#!/usr/bin/env python3
"""One-time migration script for v5.0 agent upgrade.

Archives old JSON-template agents and replaces with Git-sourced agents.

This script safely migrates from the old JSON-template based agents to the
new Git-sourced agent system introduced in v5.0.

Usage:
    python scripts/migrate_agents_v5.py [--dry-run] [--force]

Options:
    --dry-run    Preview migration without making changes
    --force      Skip confirmation prompts
"""

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class AgentMigrator:
    """Handles migration from JSON-template agents to Git-sourced agents."""

    def __init__(self, dry_run: bool = False, force: bool = False):
        """Initialize migrator.

        Args:
            dry_run: If True, only preview changes without executing
            force: If True, skip confirmation prompts
        """
        self.dry_run = dry_run
        self.force = force
        self.agents_dir = Path.home() / ".claude" / "agents"
        self.archive_path = Path.home() / ".claude" / "agents-old-archive.zip"

    def find_old_agents(self) -> List[Path]:
        """Find old JSON-template based agents.

        Returns:
            List of paths to old agent files
        """
        if not self.agents_dir.exists():
            return []

        # Old agents typically have _agent.md suffix or end with agent.md
        patterns = ["*_agent.md", "*agent.md"]
        old_agents = []

        for pattern in patterns:
            old_agents.extend(self.agents_dir.glob(pattern))

        # Remove duplicates and sort
        return sorted(set(old_agents))

    def is_git_sourced_agent(self, agent_path: Path) -> bool:
        """Check if agent is Git-sourced (has metadata).

        Args:
            agent_path: Path to agent file

        Returns:
            True if agent appears to be Git-sourced
        """
        try:
            content = agent_path.read_text()
            # Git-sourced agents typically have source metadata
            # This is a heuristic - adjust based on actual Git agent format
            return "git_source:" in content or "source: git" in content
        except Exception:
            return False

    def create_archive_readme(self, old_agents: List[Path]) -> str:
        """Create README content for archive.

        Args:
            old_agents: List of agents being archived

        Returns:
            README content as string
        """
        timestamp = datetime.now().isoformat()
        agent_list = "\n".join(f"  - {agent.name}" for agent in old_agents)

        return f"""Claude MPM v5.0 Agent Migration Archive
{"=" * 50}

This archive contains old JSON-template based agents that were
replaced with Git-sourced agents during the v5.0 migration.

Migration Date: {timestamp}
Agents Archived: {len(old_agents)}

Archived Agents:
{agent_list}

What Changed in v5.0:
---------------------
- Old: Agents deployed from JSON templates in src/claude_mpm/agents/templates/
- New: Agents synced from Git repository (bobmatnyc/claude-mpm-agents)

Why This Archive Exists:
------------------------
This is a safety backup created before removing old agents. If you need
to reference old agent configurations or restore them, they are preserved
here.

Restoration (if needed):
------------------------
To restore old agents:
1. Extract this archive
2. Copy desired agent files to ~/.claude/agents/
3. Note: Old agents won't receive updates from Git source

Git-Sourced Agents:
-------------------
The new agents are automatically synced from:
https://github.com/bobmatnyc/claude-mpm-agents

To update agents:
  claude-mpm agent-source sync

To list available agents:
  claude-mpm agents list

For More Information:
---------------------
See: docs/migration/agent-sources-git-default-v4.5.0.md
"""

    def create_archive(self, old_agents: List[Path]) -> bool:
        """Create ZIP archive of old agents.

        Args:
            old_agents: List of agents to archive

        Returns:
            True if archive created successfully
        """
        if self.dry_run:
            print(f"[DRY RUN] Would create archive: {self.archive_path}")
            return True

        try:
            with zipfile.ZipFile(self.archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add README
                readme = self.create_archive_readme(old_agents)
                zf.writestr("README.txt", readme)

                # Add agent files
                for agent in old_agents:
                    arcname = f"agents/{agent.name}"
                    zf.write(agent, arcname)

            # Verify archive
            if not self.verify_archive(old_agents):
                print("❌ Archive verification failed!")
                return False

            # Get archive size
            size_mb = self.archive_path.stat().st_size / (1024 * 1024)
            print(f"✅ Archive created successfully ({size_mb:.2f} MB)")

            return True

        except Exception as e:
            print(f"❌ Failed to create archive: {e}")
            return False

    def verify_archive(self, old_agents: List[Path]) -> bool:
        """Verify archive integrity.

        Args:
            old_agents: List of agents that should be in archive

        Returns:
            True if archive is valid
        """
        try:
            with zipfile.ZipFile(self.archive_path, "r") as zf:
                # Check for README
                if "README.txt" not in zf.namelist():
                    return False

                # Check all agents present
                archived = {f"agents/{agent.name}" for agent in old_agents}
                present = set(zf.namelist()) - {"README.txt"}

                if archived != present:
                    missing = archived - present
                    if missing:
                        print(f"❌ Missing from archive: {missing}")
                    return False

                # Test archive integrity
                if zf.testzip() is not None:
                    return False

            return True

        except Exception as e:
            print(f"❌ Archive verification error: {e}")
            return False

    def remove_old_agents(self, old_agents: List[Path]) -> int:
        """Remove old agent files.

        Args:
            old_agents: List of agents to remove

        Returns:
            Number of agents successfully removed
        """
        if self.dry_run:
            print(f"[DRY RUN] Would remove {len(old_agents)} old agents")
            return len(old_agents)

        removed = 0
        for agent in old_agents:
            try:
                agent.unlink()
                removed += 1
            except Exception as e:
                print(f"⚠️  Failed to remove {agent.name}: {e}")

        return removed

    def deploy_git_agents(self) -> Tuple[bool, int]:
        """Deploy fresh Git-sourced agents.

        Returns:
            Tuple of (success, agent_count)
        """
        if self.dry_run:
            print("[DRY RUN] Would deploy Git-sourced agents")
            return True, 0

        try:
            # Use agent-source sync to deploy from Git
            result = subprocess.run(
                ["claude-mpm", "agent-source", "sync"],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output to count deployed agents
                # This is a heuristic - adjust based on actual output
                output = result.stdout

                # Try to extract agent count from output
                import re

                match = re.search(r"(\d+)\s+agents?", output, re.IGNORECASE)
                agent_count = int(match.group(1)) if match else 0

                return True, agent_count
            print(f"❌ Deployment failed: {result.stderr}")
            return False, 0

        except subprocess.TimeoutExpired:
            print("❌ Deployment timed out after 5 minutes")
            return False, 0
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return False, 0

    def confirm_migration(self, old_agents: List[Path]) -> bool:
        """Ask user to confirm migration.

        Args:
            old_agents: List of agents to be migrated

        Returns:
            True if user confirms
        """
        if self.force:
            return True

        print("\n⚠️  This will:")
        print(f"   1. Archive {len(old_agents)} old agents to {self.archive_path}")
        print(f"   2. Remove old agent files from {self.agents_dir}")
        print("   3. Deploy fresh Git-sourced agents")
        print()

        response = input("Continue? [y/N]: ").strip().lower()
        return response in ("y", "yes")

    def run(self) -> int:
        """Execute migration.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print("🔄 Starting v5.0 agent migration...\n")

        # 1. Find old agents
        old_agents = self.find_old_agents()

        # Filter out Git-sourced agents
        old_agents = [a for a in old_agents if not self.is_git_sourced_agent(a)]

        if not old_agents:
            print("✅ No old JSON-template agents found!")
            print(f"   Agents directory: {self.agents_dir}")
            print()
            print("🔍 Checking Git-sourced agents...")

            # Still try to sync Git agents
            if not self.dry_run:
                success, count = self.deploy_git_agents()
                if success:
                    print("✅ Git agents synced successfully")
                    if count > 0:
                        print(f"   {count} agents available")
                else:
                    print("⚠️  Git agent sync had issues")

            return 0

        print(f"📦 Found {len(old_agents)} old JSON-template agents")
        for agent in old_agents[:10]:  # Show first 10
            print(f"   - {agent.name}")
        if len(old_agents) > 10:
            print(f"   ... and {len(old_agents) - 10} more")
        print()

        # Confirm migration
        if not self.confirm_migration(old_agents):
            print("❌ Migration cancelled by user")
            return 1

        # 2. Create archive
        print(f"📦 Creating archive: {self.archive_path}")
        if not self.create_archive(old_agents):
            print("❌ Migration aborted - archive creation failed")
            return 1
        print(f"   Verified: All {len(old_agents)} agents backed up\n")

        # 3. Remove old agents
        print("🗑️  Removing old agents...")
        removed = self.remove_old_agents(old_agents)
        print(f"   ✅ Removed {removed} old agents\n")

        if removed != len(old_agents):
            print(f"⚠️  Warning: Only removed {removed}/{len(old_agents)} agents")

        # 4. Deploy Git agents
        print("🚀 Deploying fresh Git-sourced agents...")
        print("   Syncing from: https://github.com/bobmatnyc/claude-mpm-agents")

        success, new_count = self.deploy_git_agents()
        if success:
            print("   ✅ Deployed successfully")
            if new_count > 0:
                print(f"   ✅ {new_count} agents available")
        else:
            print("   ⚠️  Deployment had issues (check logs)")
        print()

        # 5. Summary
        print("📊 Migration Summary:")
        print(f"   - Archived: {len(old_agents)} old agents")
        print(f"   - Removed: {removed} old agents")
        if new_count > 0:
            print(f"   - Deployed: {new_count} new Git agents")
        print(f"   - Archive: {self.archive_path}")
        print()

        if success:
            print("✅ Migration complete! v5.0 agents ready.")
        else:
            print("⚠️  Migration completed with warnings.")
            print("   Old agents archived, but Git deployment had issues.")
            print("   Run: claude-mpm agent-source sync")

        return 0 if success else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate from JSON-template agents to Git-sourced agents (v5.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    migrator = AgentMigrator(dry_run=args.dry_run, force=args.force)
    return migrator.run()


if __name__ == "__main__":
    sys.exit(main())
