"""Agent File System Manager Service

This service handles file system operations for agent deployment including
cleanup, file management, and directory operations.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logging_config import get_logger


class AgentFileSystemManager:
    """Service for managing agent file system operations.

    This service handles:
    - Agent file cleanup and removal
    - Directory management
    - File format conversion (YAML to MD)
    - Backup and restore operations
    """

    def __init__(self):
        """Initialize the file system manager."""
        self.logger = get_logger(__name__)

    def clean_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Clean up deployed agents while preserving user-created agents.

        This method removes system-deployed agents (authored by claude-mpm)
        while preserving any user-created agents in the directory.

        Args:
            config_dir: Claude configuration directory (default: .claude/)

        Returns:
            Dictionary with cleanup results
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"

        results = {"removed": [], "preserved": [], "errors": [], "total_processed": 0}

        agents_dir = config_dir / "agents"

        if not agents_dir.exists():
            self.logger.info(f"Agents directory does not exist: {agents_dir}")
            return results

        # Find all agent files
        agent_files = list(agents_dir.glob("*.md")) + list(agents_dir.glob("*.yaml"))
        results["total_processed"] = len(agent_files)

        for agent_file in agent_files:
            try:
                # Read file content to check if it's system-managed
                content = agent_file.read_text()

                # Check if it's a system agent (authored by claude-mpm)
                if self._is_system_agent(content):
                    # Remove system agent
                    agent_file.unlink()
                    results["removed"].append(agent_file.name)
                    self.logger.info(f"Removed system agent: {agent_file.name}")
                else:
                    # Preserve user-created agent
                    results["preserved"].append(agent_file.name)
                    self.logger.debug(f"Preserved user agent: {agent_file.name}")

            except Exception as e:
                error_msg = f"Error processing {agent_file.name}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)

        self.logger.info(
            f"Cleanup complete: {len(results['removed'])} removed, {len(results['preserved'])} preserved"
        )
        return results

    def convert_yaml_to_md(self, agents_dir: Path) -> Dict[str, Any]:
        """
        Convert existing YAML agent files to Markdown format.

        This handles the migration from old YAML format to the new Markdown
        format with YAML frontmatter that Claude Code prefers.

        Args:
            agents_dir: Directory containing agent files

        Returns:
            Dictionary with conversion results
        """
        results = {"converted": [], "errors": [], "skipped": []}

        if not agents_dir.exists():
            self.logger.debug(f"Agents directory does not exist: {agents_dir}")
            return results

        try:
            # Find YAML files that need conversion
            yaml_files = list(agents_dir.glob("*.yaml"))

            for yaml_file in yaml_files:
                try:
                    # Check if corresponding MD file already exists
                    md_file = yaml_file.with_suffix(".md")

                    if md_file.exists():
                        # Check modification times
                        yaml_mtime = yaml_file.stat().st_mtime
                        md_mtime = md_file.stat().st_mtime

                        if md_mtime >= yaml_mtime:
                            # MD file is newer or same age, skip conversion
                            results["skipped"].append(yaml_file.name)
                            continue
                        # MD file is older, proceed with conversion
                        self.logger.info(
                            f"MD file {md_file.name} is older than YAML, converting..."
                        )

                    # Read YAML content
                    yaml_content = yaml_file.read_text()

                    # Convert to Markdown format
                    md_content = self._convert_yaml_to_markdown(
                        yaml_content, yaml_file.stem
                    )

                    # Write MD file
                    md_file.write_text(md_content)

                    # Remove original YAML file
                    yaml_file.unlink()

                    results["converted"].append(
                        {"from": yaml_file.name, "to": md_file.name}
                    )

                    self.logger.info(f"Converted {yaml_file.name} to {md_file.name}")

                except Exception as e:
                    error_msg = f"Failed to convert {yaml_file.name}: {e}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

        except Exception as e:
            error_msg = f"YAML to MD conversion failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def backup_agents_directory(
        self, agents_dir: Path, backup_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Create a backup of the agents directory.

        Args:
            agents_dir: Directory to backup
            backup_dir: Backup destination (default: agents_backup_TIMESTAMP)

        Returns:
            Dictionary with backup results
        """
        results = {
            "success": False,
            "backup_path": None,
            "files_backed_up": 0,
            "errors": [],
        }

        if not agents_dir.exists():
            results["errors"].append(f"Source directory does not exist: {agents_dir}")
            return results

        try:
            # Generate backup directory name if not provided
            if not backup_dir:
                from datetime import datetime, timezone

                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_dir = agents_dir.parent / f"agents_backup_{timestamp}"

            # Create backup
            shutil.copytree(agents_dir, backup_dir, dirs_exist_ok=True)

            # Count backed up files
            backup_files = list(backup_dir.rglob("*"))
            file_count = len([f for f in backup_files if f.is_file()])

            results.update(
                {
                    "success": True,
                    "backup_path": str(backup_dir),
                    "files_backed_up": file_count,
                }
            )

            self.logger.info(
                f"Successfully backed up {file_count} files to {backup_dir}"
            )

        except Exception as e:
            error_msg = f"Backup failed: {e}"
            results["errors"].append(error_msg)
            self.logger.error(error_msg)

        return results

    def restore_agents_from_backup(
        self, backup_dir: Path, agents_dir: Path
    ) -> Dict[str, Any]:
        """
        Restore agents from a backup directory.

        Args:
            backup_dir: Backup directory to restore from
            agents_dir: Target agents directory

        Returns:
            Dictionary with restore results
        """
        results = {"success": False, "files_restored": 0, "errors": []}

        if not backup_dir.exists():
            results["errors"].append(f"Backup directory does not exist: {backup_dir}")
            return results

        try:
            # Remove existing agents directory if it exists
            if agents_dir.exists():
                shutil.rmtree(agents_dir)

            # Restore from backup
            shutil.copytree(backup_dir, agents_dir)

            # Count restored files
            restored_files = list(agents_dir.rglob("*"))
            file_count = len([f for f in restored_files if f.is_file()])

            results.update({"success": True, "files_restored": file_count})

            self.logger.info(
                f"Successfully restored {file_count} files from {backup_dir}"
            )

        except Exception as e:
            error_msg = f"Restore failed: {e}"
            results["errors"].append(error_msg)
            self.logger.error(error_msg)

        return results

    def get_directory_info(self, directory: Path) -> Dict[str, Any]:
        """
        Get information about a directory and its contents.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary with directory information
        """
        info = {
            "exists": False,
            "total_files": 0,
            "agent_files": 0,
            "total_size_bytes": 0,
            "file_types": {},
            "largest_files": [],
        }

        if not directory.exists():
            return info

        info["exists"] = True

        try:
            all_files = list(directory.rglob("*"))
            files_only = [f for f in all_files if f.is_file()]

            info["total_files"] = len(files_only)

            # Count agent files
            agent_files = [f for f in files_only if f.suffix in [".md", ".yaml"]]
            info["agent_files"] = len(agent_files)

            # Calculate total size and file type distribution
            file_sizes = []
            for file_path in files_only:
                try:
                    size = file_path.stat().st_size
                    info["total_size_bytes"] += size
                    file_sizes.append((file_path, size))

                    # Track file types
                    ext = file_path.suffix.lower()
                    info["file_types"][ext] = info["file_types"].get(ext, 0) + 1

                except Exception:
                    continue

            # Find largest files
            file_sizes.sort(key=lambda x: x[1], reverse=True)
            info["largest_files"] = [
                {"name": f.name, "size_bytes": size} for f, size in file_sizes[:5]
            ]

        except Exception as e:
            self.logger.error(f"Error analyzing directory {directory}: {e}")

        return info

    def _is_system_agent(self, content: str) -> bool:
        """Check if an agent file is system-managed."""
        return "claude-mpm" in content or "author: claude-mpm" in content

    def _convert_yaml_to_markdown(self, yaml_content: str, agent_name: str) -> str:
        """Convert YAML agent content to Markdown format with frontmatter."""
        from datetime import datetime, timezone

        # Extract YAML fields (simplified parsing)
        name = self._extract_yaml_field(yaml_content, "name") or agent_name
        description = (
            self._extract_yaml_field(yaml_content, "description")
            or f"{agent_name.title()} agent for specialized tasks"
        )
        version = self._extract_yaml_field(yaml_content, "version") or "1.0.0"
        tools_line = (
            self._extract_yaml_field(yaml_content, "tools")
            or "Read, Write, Edit, Grep, Glob, LS"
        )

        # Convert tools string to list format
        if isinstance(tools_line, str):
            if tools_line.startswith("[") and tools_line.endswith("]"):
                # Already in list format
                tools_list = tools_line
            else:
                # Convert comma-separated to list
                tools = [tool.strip() for tool in tools_line.split(",")]
                tools_list = str(tools).replace("'", '"')
        else:
            tools_list = '["Read", "Write", "Edit"]'

        # Build Markdown with YAML frontmatter
        return f"""---
name: {name}
description: "{description}"
version: "{version}"
author: "claude-mpm@anthropic.com"
created: "{datetime.now(timezone.utc).isoformat()}Z"
updated: "{datetime.now(timezone.utc).isoformat()}Z"
tags: ["{agent_name}", "mpm-framework"]
tools: {tools_list}
model: "sonnet"
---

# {name.title()} Agent

{description}

## Instructions

This agent provides specialized functionality for your tasks.
"""

    def _extract_yaml_field(self, yaml_content: str, field_name: str) -> Optional[str]:
        """Extract a field value from YAML content."""
        import re

        pattern = rf"^{field_name}:\s*(.+)$"
        match = re.search(pattern, yaml_content, re.MULTILINE)
        if match:
            return match.group(1).strip().strip("\"'")
        return None
