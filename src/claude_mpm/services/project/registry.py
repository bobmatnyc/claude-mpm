"""
Project Registry Service.

WHY: This service manages a persistent registry of claude-mpm projects to enable
project identification, tracking, and metadata management. The registry stores
comprehensive project information including git status, environment details,
runtime information, and project characteristics.

DESIGN DECISION: Uses YAML for human-readable registry files stored in the
user's home directory (~/.claude-mpm/registry/). Each project
gets a unique UUID-based registry file to avoid conflicts and enable easy project
identification. Registry is user-specific for better isolation and persistence.

The registry captures both static project information (paths, git info) and
dynamic runtime information (startup times, process IDs, command line args)
to provide complete project lifecycle tracking.
"""

import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.logger import get_logger


class ProjectRegistryError(Exception):
    """Base exception for project registry operations."""


class ProjectRegistry:
    """
    Manages the project registry for claude-mpm installations.

    WHY: The project registry provides persistent project tracking across sessions,
    enabling project identification, metadata collection, and usage analytics.
    This is crucial for multi-project environments where users switch between
    different codebases.

    DESIGN DECISION: Registry files are stored in ~/.claude-mpm/registry/
    with UUID-based filenames to ensure uniqueness and avoid conflicts. The registry
    uses YAML for human readability and ease of manual inspection/editing.
    Registry is stored in the user's home directory for persistence across projects.
    """

    def __init__(self):
        """
        Initialize the project registry.

        WHY: Sets up the registry directory and logger. The registry directory
        is created in the user's home directory to keep registry data user-specific
        and persistent across different projects and sessions.
        """
        self.logger = get_logger("project_registry")
        # Use user's home directory for registry to avoid project-specific contamination
        # This ensures registry persists across all projects for the user
        user_home = Path.home()
        self.registry_dir = user_home / ".claude-mpm" / "registry"
        self.current_project_path = Path.cwd().resolve()

        # Ensure registry directory exists
        try:
            self.registry_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create registry directory: {e}")
            raise ProjectRegistryError(f"Cannot create registry directory: {e}")

    def get_or_create_project_entry(self) -> Dict[str, Any]:
        """
        Get existing project registry entry or create a new one.

        WHY: This is the main entry point for project registration. It handles
        both new project registration and existing project updates, ensuring
        that every claude-mpm session is properly tracked.

        DESIGN DECISION: Matching is done by normalized absolute path to handle
        symbolic links and different path representations consistently.

        Returns:
            Dictionary containing the project registry data

        Raises:
            ProjectRegistryError: If registry operations fail
        """
        try:
            # Look for existing registry entry
            existing_entry = self._find_existing_entry()

            if existing_entry:
                self.logger.debug(
                    f"Found existing project entry: {existing_entry['project_id']}"
                )
                # Update existing entry with current session info
                return self._update_existing_entry(existing_entry)
            self.logger.debug("Creating new project registry entry")
            # Create new entry
            return self._create_new_entry()

        except Exception as e:
            self.logger.error(f"Failed to get or create project entry: {e}")
            raise ProjectRegistryError(f"Registry operation failed: {e}")

    def _find_existing_entry(self) -> Optional[Dict[str, Any]]:
        """
        Search for existing registry entry matching current project path.

        WHY: We need to match projects by their absolute path to avoid creating
        duplicate entries when the same project is accessed from different
        working directories or via different path representations.

        Returns:
            Existing registry data if found, None otherwise
        """
        try:
            # Normalize current path for consistent matching
            current_path_str = str(self.current_project_path)

            # Search all registry files
            for registry_file in self.registry_dir.glob("*.yaml"):
                try:
                    with open(registry_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}

                    # Check if project_path matches
                    if data.get("project_path") == current_path_str:
                        data["_registry_file"] = registry_file  # Add file reference
                        return data

                except Exception as e:
                    self.logger.warning(
                        f"Failed to read registry file {registry_file}: {e}"
                    )
                    continue

            return None

        except Exception as e:
            self.logger.error(f"Error searching for existing entry: {e}")
            return None

    def _create_new_entry(self) -> Dict[str, Any]:
        """
        Create a new project registry entry.

        WHY: New projects need to be registered with comprehensive metadata
        including project information, environment details, and initial runtime
        data. This creates a complete snapshot of the project at first access.

        Returns:
            Newly created registry data
        """
        project_id = str(uuid.uuid4())
        registry_file = self.registry_dir / f"{project_id}.yaml"

        # Build comprehensive project data
        project_data = {
            "project_id": project_id,
            "project_path": str(self.current_project_path),
            "project_name": self.current_project_path.name,
            "metadata": self._build_metadata(is_new=True),
            "runtime": self._build_runtime_info(),
            "environment": self._build_environment_info(),
            "git": self._build_git_info(),
            "session": self._build_session_info(),
            "project_info": self._build_project_info(),
        }

        # Save to registry file
        self._save_registry_data(registry_file, project_data)
        project_data["_registry_file"] = registry_file

        self.logger.info(f"Created new project registry entry: {project_id}")
        return project_data

    def _update_existing_entry(self, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing project registry entry with current session information.

        WHY: Existing projects need their metadata updated to reflect current
        access patterns, runtime information, and any changes in project state.
        This maintains accurate usage tracking and project state history.

        Args:
            existing_data: The existing registry data to update

        Returns:
            Updated registry data
        """
        registry_file = existing_data.get("_registry_file")
        if not registry_file:
            raise ProjectRegistryError(
                "Registry file reference missing from existing data"
            )

        # Update timestamps and counters
        metadata = existing_data.get("metadata", {})
        access_count = metadata.get("access_count", 0) + 1
        now = datetime.now(timezone.utc).isoformat()

        existing_data["metadata"].update(
            {"updated_at": now, "last_accessed": now, "access_count": access_count}
        )

        # Update runtime information
        existing_data["runtime"] = self._build_runtime_info()

        # Update session information
        existing_data["session"] = self._build_session_info()

        # Update git information (may have changed)
        existing_data["git"] = self._build_git_info()

        # Update project info (may have changed)
        existing_data["project_info"] = self._build_project_info()

        # Save updated data
        self._save_registry_data(registry_file, existing_data)

        self.logger.debug(f"Updated project registry entry (access #{access_count})")
        return existing_data

    def _build_metadata(self, is_new: bool = False) -> Dict[str, Any]:
        """
        Build metadata section for registry entry.

        WHY: Metadata tracks creation, modification, and access patterns for
        analytics and project lifecycle management.
        """
        now = datetime.now(timezone.utc).isoformat()

        metadata = {"updated_at": now, "last_accessed": now, "access_count": 1}

        if is_new:
            metadata["created_at"] = now

        return metadata

    def _build_runtime_info(self) -> Dict[str, Any]:
        """
        Build runtime information section.

        WHY: Runtime information helps track session lifecycle, process management,
        and system state. This is valuable for debugging session issues and
        understanding usage patterns.
        """
        # Get claude-mpm version
        try:
            from claude_mpm import __version__ as claude_mpm_version
        except ImportError:
            claude_mpm_version = "unknown"

        return {
            "startup_time": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "claude_mpm_version": claude_mpm_version,
            "command_line": " ".join(sys.argv),
            "launch_method": "subprocess",  # Default, could be detected based on parent process
        }

    def _build_environment_info(self) -> Dict[str, Any]:
        """
        Build environment information section.

        WHY: Environment information helps with debugging, platform-specific
        behavior analysis, and provides context for project usage patterns
        across different systems and user setups.
        """
        return {
            "user": os.getenv("USER") or os.getenv("USERNAME", "unknown"),
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.release(),
            "shell": os.getenv("SHELL", "unknown"),
            "terminal": os.getenv("TERM", "unknown"),
            "cwd": str(Path.cwd()),
        }

    def _build_git_info(self) -> Dict[str, Any]:
        """
        Build git repository information.

        WHY: Git information is crucial for project identification and tracking
        changes across different branches and commits. This helps understand
        project state and enables better project management features.
        """
        git_info = {
            "is_repo": False,
            "branch": None,
            "remote_url": None,
            "last_commit": None,
            "has_uncommitted": False,
        }

        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.current_project_path,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                git_info["is_repo"] = True

                # Get current branch
                try:
                    result = subprocess.run(
                        ["git", "branch", "--show-current"],
                        cwd=self.current_project_path,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        git_info["branch"] = result.stdout.strip()
                except Exception:
                    pass

                # Get remote URL
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=self.current_project_path,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        git_info["remote_url"] = result.stdout.strip()
                except Exception:
                    pass

                # Get last commit
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=self.current_project_path,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        git_info["last_commit"] = result.stdout.strip()
                except Exception:
                    pass

                # Check for uncommitted changes
                try:
                    result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=self.current_project_path,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        git_info["has_uncommitted"] = bool(result.stdout.strip())
                except Exception:
                    pass

        except Exception as e:
            self.logger.debug(f"Failed to get git info: {e}")

        return git_info

    def _build_session_info(self) -> Dict[str, Any]:
        """
        Build session information.

        WHY: Session information tracks the current claude-mpm session state,
        including active components and configuration. This helps with session
        management and debugging.
        """
        # These would be populated by the actual session manager
        # For now, we provide placeholders that can be updated by the caller
        return {
            "session_id": None,  # Could be set by session manager
            "ticket_count": 0,  # Could be updated by ticket manager
            "agent_count": 0,  # Could be updated by agent manager
            "hooks_enabled": False,  # Could be detected from configuration
            "monitor_enabled": False,  # Could be detected from process state
        }

    def _build_project_info(self) -> Dict[str, Any]:
        """
        Build project information section.

        WHY: Project information helps identify the type of project and its
        characteristics, enabling better tool selection and project-specific
        optimizations.
        """
        project_info = {
            "has_claude_config": False,
            "has_claude_md": False,
            "has_pyproject": False,
            "has_package_json": False,
            "project_type": "unknown",
        }

        # Check for various project files
        claude_files = [".claude", "claude.toml", ".claude.toml"]
        for claude_file in claude_files:
            if (self.current_project_path / claude_file).exists():
                project_info["has_claude_config"] = True
                break

        claude_md_files = ["CLAUDE.md", "claude.md", ".claude.md"]
        for claude_md in claude_md_files:
            if (self.current_project_path / claude_md).exists():
                project_info["has_claude_md"] = True
                break

        if (self.current_project_path / "pyproject.toml").exists():
            project_info["has_pyproject"] = True

        if (self.current_project_path / "package.json").exists():
            project_info["has_package_json"] = True

        # Determine project type
        if (
            project_info["has_pyproject"]
            or (self.current_project_path / "setup.py").exists()
        ):
            project_info["project_type"] = "python"
        elif project_info["has_package_json"]:
            project_info["project_type"] = "javascript"
        elif (self.current_project_path / "Cargo.toml").exists():
            project_info["project_type"] = "rust"
        elif (self.current_project_path / "go.mod").exists():
            project_info["project_type"] = "go"
        elif (self.current_project_path / "pom.xml").exists():
            project_info["project_type"] = "java"
        elif any(
            (self.current_project_path / ext).exists()
            for ext in ["*.c", "*.cpp", "*.h", "*.hpp"]
        ):
            project_info["project_type"] = "c/cpp"
        elif project_info["has_claude_config"] or project_info["has_claude_md"]:
            project_info["project_type"] = "claude"
        else:
            # Try to detect by file extensions
            common_files = list(self.current_project_path.iterdir())[
                :20
            ]  # Check first 20 files
            extensions = {f.suffix.lower() for f in common_files if f.is_file()}

            if ".py" in extensions:
                project_info["project_type"] = "python"
            elif any(ext in extensions for ext in [".js", ".ts", ".jsx", ".tsx"]):
                project_info["project_type"] = "javascript"
            elif any(ext in extensions for ext in [".rs"]):
                project_info["project_type"] = "rust"
            elif any(ext in extensions for ext in [".go"]):
                project_info["project_type"] = "go"
            elif any(ext in extensions for ext in [".java", ".scala", ".kt"]):
                project_info["project_type"] = "jvm"
            elif any(ext in extensions for ext in [".c", ".cpp", ".cc", ".h", ".hpp"]):
                project_info["project_type"] = "c/cpp"
            elif any(ext in extensions for ext in [".md", ".txt", ".rst"]):
                project_info["project_type"] = "documentation"

        return project_info

    def _save_registry_data(self, registry_file: Path, data: Dict[str, Any]) -> None:
        """
        Save registry data to YAML file.

        WHY: Centralized saving logic ensures consistent formatting and error
        handling across all registry operations. YAML format provides human
        readability for debugging and manual inspection.

        Args:
            registry_file: Path to the registry file
            data: Registry data to save
        """
        try:
            # Remove internal fields before saving
            save_data = {k: v for k, v in data.items() if not k.startswith("_")}

            with open(registry_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    save_data, f, default_flow_style=False, sort_keys=False, indent=2
                )

            self.logger.debug(f"Saved registry data to {registry_file}")

        except Exception as e:
            self.logger.error(f"Failed to save registry data: {e}")
            raise ProjectRegistryError(f"Failed to save registry: {e}")

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all registered projects.

        WHY: Provides visibility into all projects managed by claude-mpm,
        useful for project management and analytics.

        Returns:
            List of project registry data dictionaries
        """
        projects = []

        try:
            for registry_file in self.registry_dir.glob("*.yaml"):
                try:
                    with open(registry_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    projects.append(data)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to read registry file {registry_file}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Failed to list projects: {e}")

        return projects

    def cleanup_old_entries(self, max_age_days: int = 90) -> int:
        """
        Clean up old registry entries that haven't been accessed recently.

        WHY: Prevents registry directory from growing indefinitely with old
        project entries. Keeps the registry focused on active projects.

        Args:
            max_age_days: Maximum age in days for keeping entries

        Returns:
            Number of entries cleaned up
        """
        if max_age_days <= 0:
            return 0

        cleaned_count = 0
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        try:
            for registry_file in self.registry_dir.glob("*.yaml"):
                try:
                    with open(registry_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}

                    # Check last accessed time
                    last_accessed_str = data.get("metadata", {}).get("last_accessed")
                    if last_accessed_str:
                        last_accessed = datetime.fromisoformat(
                            last_accessed_str.replace("Z", "+00:00")
                        )
                        if last_accessed < cutoff_date:
                            registry_file.unlink()
                            cleaned_count += 1
                            self.logger.debug(
                                f"Cleaned up old registry entry: {registry_file}"
                            )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to process registry file {registry_file}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Failed to cleanup old entries: {e}")

        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old registry entries")

        return cleaned_count

    def update_session_info(self, session_updates: Dict[str, Any]) -> bool:
        """
        Update session information for the current project.

        WHY: Allows other components (session manager, ticket manager, etc.)
        to update the registry with current session state information.

        Args:
            session_updates: Dictionary of session updates to apply

        Returns:
            True if update was successful, False otherwise
        """
        try:
            existing_entry = self._find_existing_entry()
            if not existing_entry:
                self.logger.warning(
                    "No existing registry entry found for session update"
                )
                return False

            registry_file = existing_entry.get("_registry_file")
            if not registry_file:
                self.logger.error("Registry file reference missing")
                return False

            # Update session information
            if "session" not in existing_entry:
                existing_entry["session"] = {}

            existing_entry["session"].update(session_updates)

            # Update metadata timestamp
            now = datetime.now(timezone.utc).isoformat()
            existing_entry["metadata"]["updated_at"] = now

            # Save updated data
            self._save_registry_data(registry_file, existing_entry)

            self.logger.debug(f"Updated session info: {session_updates}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update session info: {e}")
            return False
