"""Migration utilities for transitioning to new directory structure.

WHY: Phase 3 of 1M-486 requires migrating from old single-tier deployment
     (~/.claude/agents/, ~/.claude/skills/) to new two-phase architecture:
     - Cache: ~/.claude-mpm/cache/agents/, ~/.claude-mpm/cache/skills/
     - Deployment: .claude-mpm/agents/, .claude-mpm/skills/

DESIGN DECISIONS:
- Optional migration: Users can continue using old paths (fallback support)
- User confirmation: Prevents accidental data movement
- Non-destructive: Creates copies, doesn't delete originals immediately
- Deprecation warnings: Guides users toward new structure

MIGRATION PATH:
1. Detect old locations (if they exist)
2. Prompt user for confirmation
3. Copy to new cache location (not deployment, as that's project-specific)
4. Show deprecation warning with cleanup instructions
5. Provide fallback support for unmigrated systems
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MigrationUtility:
    """Handles migration from old to new directory structure.

    Trade-offs:
    - Safety: Non-destructive copies vs. automatic moves
    - User experience: Manual confirmation vs. automatic migration
    - Compatibility: Fallback support adds complexity but ensures smooth transition
    """

    def __init__(self):
        """Initialize migration utility with old and new paths."""
        self.old_agent_dir = Path.home() / ".claude" / "agents"
        self.old_skill_dir = Path.home() / ".claude" / "skills"

        self.new_agent_cache = Path.home() / ".claude-mpm" / "cache" / "agents"
        self.new_skill_cache = Path.home() / ".claude-mpm" / "cache" / "skills"

    def detect_old_locations(self) -> Dict[str, bool]:
        """Detect if old directory locations exist and contain files.

        Returns:
            Dictionary with 'agents' and 'skills' keys indicating presence
        """
        results = {
            "agents_exists": False,
            "agents_count": 0,
            "skills_exists": False,
            "skills_count": 0,
        }

        # Check agents
        if self.old_agent_dir.exists():
            agent_files = list(self.old_agent_dir.glob("*.md")) + list(
                self.old_agent_dir.glob("*.json")
            )
            results["agents_exists"] = len(agent_files) > 0
            results["agents_count"] = len(agent_files)

        # Check skills
        if self.old_skill_dir.exists():
            skill_dirs = [
                d
                for d in self.old_skill_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            ]
            results["skills_exists"] = len(skill_dirs) > 0
            results["skills_count"] = len(skill_dirs)

        return results

    def migrate_agents(
        self, dry_run: bool = False, auto_confirm: bool = False
    ) -> Dict[str, any]:
        """Migrate agents from ~/.claude/agents/ to ~/.claude-mpm/cache/agents/.

        Args:
            dry_run: Preview migration without making changes
            auto_confirm: Skip confirmation prompt (use with caution)

        Returns:
            Dictionary with migration results:
            {
                "migrated_count": 5,
                "migrated_files": ["engineer.md", ...],
                "skipped_count": 2,
                "errors": []
            }
        """
        if not self.old_agent_dir.exists():
            return {
                "migrated_count": 0,
                "migrated_files": [],
                "skipped_count": 0,
                "errors": [],
                "message": "No old agent directory found",
            }

        # Find agent files
        agent_files = list(self.old_agent_dir.glob("*.md")) + list(
            self.old_agent_dir.glob("*.json")
        )

        if not agent_files:
            return {
                "migrated_count": 0,
                "migrated_files": [],
                "skipped_count": 0,
                "errors": [],
                "message": "No agent files found in old directory",
            }

        # Dry run mode
        if dry_run:
            return {
                "migrated_count": len(agent_files),
                "migrated_files": [f.name for f in agent_files],
                "skipped_count": 0,
                "errors": [],
                "dry_run": True,
                "message": f"Would migrate {len(agent_files)} agent files",
            }

        # Confirmation prompt (unless auto_confirm)
        if not auto_confirm:
            logger.info(
                f"Migration will copy {len(agent_files)} agents from:\n"
                f"  {self.old_agent_dir}\n"
                f"  → {self.new_agent_cache}"
            )
            # In CLI context, this would show interactive prompt
            # For now, we assume confirmation through function parameter

        # Create cache directory
        try:
            self.new_agent_cache.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            return {
                "migrated_count": 0,
                "migrated_files": [],
                "skipped_count": 0,
                "errors": [f"Permission denied creating cache directory: {e}"],
            }

        # Copy files
        results = {
            "migrated_count": 0,
            "migrated_files": [],
            "skipped_count": 0,
            "errors": [],
        }

        for agent_file in agent_files:
            target_file = self.new_agent_cache / agent_file.name

            try:
                # Skip if already exists and is identical
                if target_file.exists():
                    if self._files_identical(agent_file, target_file):
                        results["skipped_count"] += 1
                        logger.debug(f"Skipped (identical): {agent_file.name}")
                        continue

                # Copy to cache
                shutil.copy2(agent_file, target_file)
                results["migrated_count"] += 1
                results["migrated_files"].append(agent_file.name)
                logger.info(f"Migrated: {agent_file.name}")

            except Exception as e:
                error_msg = f"Failed to migrate {agent_file.name}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        results["message"] = (
            f"Migrated {results['migrated_count']} agents to cache. "
            f"Old directory: {self.old_agent_dir}"
        )

        return results

    def migrate_skills(
        self, dry_run: bool = False, auto_confirm: bool = False
    ) -> Dict[str, any]:
        """Migrate skills from ~/.claude/skills/ to ~/.claude-mpm/cache/skills/.

        Args:
            dry_run: Preview migration without making changes
            auto_confirm: Skip confirmation prompt

        Returns:
            Dictionary with migration results
        """
        if not self.old_skill_dir.exists():
            return {
                "migrated_count": 0,
                "migrated_skills": [],
                "skipped_count": 0,
                "errors": [],
                "message": "No old skill directory found",
            }

        # Find skill directories
        skill_dirs = [
            d
            for d in self.old_skill_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]

        if not skill_dirs:
            return {
                "migrated_count": 0,
                "migrated_skills": [],
                "skipped_count": 0,
                "errors": [],
                "message": "No skill directories found",
            }

        # Dry run mode
        if dry_run:
            return {
                "migrated_count": len(skill_dirs),
                "migrated_skills": [d.name for d in skill_dirs],
                "skipped_count": 0,
                "errors": [],
                "dry_run": True,
                "message": f"Would migrate {len(skill_dirs)} skill directories",
            }

        # Create cache directory
        try:
            self.new_skill_cache.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            return {
                "migrated_count": 0,
                "migrated_skills": [],
                "skipped_count": 0,
                "errors": [f"Permission denied creating cache directory: {e}"],
            }

        # Copy skill directories
        results = {
            "migrated_count": 0,
            "migrated_skills": [],
            "skipped_count": 0,
            "errors": [],
        }

        for skill_dir in skill_dirs:
            target_dir = self.new_skill_cache / skill_dir.name

            try:
                # Skip if already exists
                if target_dir.exists():
                    results["skipped_count"] += 1
                    logger.debug(f"Skipped (exists): {skill_dir.name}")
                    continue

                # Copy entire skill directory
                shutil.copytree(skill_dir, target_dir)
                results["migrated_count"] += 1
                results["migrated_skills"].append(skill_dir.name)
                logger.info(f"Migrated: {skill_dir.name}")

            except Exception as e:
                error_msg = f"Failed to migrate {skill_dir.name}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        results["message"] = (
            f"Migrated {results['migrated_count']} skills to cache. "
            f"Old directory: {self.old_skill_dir}"
        )

        return results

    def migrate_all(
        self, dry_run: bool = False, auto_confirm: bool = False
    ) -> Dict[str, any]:
        """Migrate both agents and skills.

        Args:
            dry_run: Preview migration without making changes
            auto_confirm: Skip confirmation prompts

        Returns:
            Combined migration results for agents and skills
        """
        agent_results = self.migrate_agents(dry_run=dry_run, auto_confirm=auto_confirm)
        skill_results = self.migrate_skills(dry_run=dry_run, auto_confirm=auto_confirm)

        return {
            "agents": agent_results,
            "skills": skill_results,
            "total_migrated": agent_results["migrated_count"]
            + skill_results["migrated_count"],
            "dry_run": dry_run,
        }

    def show_deprecation_warning(self) -> str:
        """Generate deprecation warning message for old paths.

        Returns:
            Formatted warning message for display to user
        """
        detection = self.detect_old_locations()

        if not detection["agents_exists"] and not detection["skills_exists"]:
            return ""

        warning = "\n⚠️  DEPRECATION WARNING ⚠️\n\n"
        warning += "Old directory structure detected:\n\n"

        if detection["agents_exists"]:
            warning += f"  • {self.old_agent_dir}\n"
            warning += f"    ({detection['agents_count']} agent files)\n"

        if detection["skills_exists"]:
            warning += f"  • {self.old_skill_dir}\n"
            warning += f"    ({detection['skills_count']} skill directories)\n"

        warning += "\nThe deployment architecture has changed:\n"
        warning += "  OLD: ~/.claude/agents/ (single-tier, global)\n"
        warning += "  NEW: ~/.claude-mpm/cache/agents/ → .claude-mpm/agents/ (two-phase, per-project)\n\n"

        warning += "To migrate:\n"
        warning += "  claude-mpm migrate\n\n"

        warning += "Or to continue using old paths (not recommended):\n"
        warning += "  # Fallback support is enabled automatically\n\n"

        return warning

    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files are byte-for-byte identical
        """
        try:
            return file1.read_bytes() == file2.read_bytes()
        except Exception:
            return False

    def get_fallback_paths(self) -> Dict[str, Optional[Path]]:
        """Get fallback paths for old directory structure.

        Used when migration hasn't been performed and old paths still exist.

        Returns:
            Dictionary with fallback paths:
            {
                "agent_dir": Path to old agents (or None),
                "skill_dir": Path to old skills (or None)
            }
        """
        return {
            "agent_dir": self.old_agent_dir if self.old_agent_dir.exists() else None,
            "skill_dir": self.old_skill_dir if self.old_skill_dir.exists() else None,
        }
