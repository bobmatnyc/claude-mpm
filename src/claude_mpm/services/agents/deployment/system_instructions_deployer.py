"""System instructions deployment for agent deployment service.

This module handles deployment of system instructions and framework files.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import logging
from pathlib import Path
from typing import Any, Dict


class SystemInstructionsDeployer:
    """Handles deployment of system instructions and framework files."""

    def __init__(self, logger: logging.Logger, working_directory: Path):
        """Initialize the deployer with logger and working directory."""
        self.logger = logger
        self.working_directory = working_directory

    def deploy_system_instructions(
        self,
        target_dir: Path,
        force_rebuild: bool,
        results: Dict[str, Any],
    ) -> None:
        """
        Deploy system instructions and framework files for PM framework.

        Always deploys to project .claude directory regardless of agent source
        (system, user, or project). This ensures consistent project-level
        deployment while maintaining discovery from both user (~/.claude-mpm)
        and project (.claude-mpm) directories.

        Args:
            target_dir: Target directory for deployment (not used - always uses project .claude)
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Always use project's .claude directory
            # This is the key change - all system instructions go to project .claude
            claude_dir = self.working_directory / ".claude"

            # Ensure .claude directory exists
            claude_dir.mkdir(parents=True, exist_ok=True)

            # Framework files to deploy
            framework_files = [
                (
                    "INSTRUCTIONS.md",
                    "INSTRUCTIONS.md",
                ),  # Keep INSTRUCTIONS.md as is - NEVER rename to CLAUDE.md
                ("WORKFLOW.md", "WORKFLOW.md"),
                ("MEMORY.md", "MEMORY.md"),
            ]

            # Find the agents directory with framework files
            # Use centralized paths for consistency
            from claude_mpm.config.paths import paths

            agents_path = paths.agents_dir

            for source_name, target_name in framework_files:
                source_path = agents_path / source_name

                if not source_path.exists():
                    self.logger.warning(f"Framework file not found: {source_path}")
                    continue

                target_file = claude_dir / target_name

                # Check if update needed
                if not force_rebuild and target_file.exists():
                    # Compare modification times
                    if target_file.stat().st_mtime >= source_path.stat().st_mtime:
                        results["skipped"].append(target_name)
                        self.logger.debug(f"Framework file {target_name} up to date")
                        continue

                # Read and deploy framework file
                file_content = source_path.read_text()
                target_file.write_text(file_content)

                # Track deployment
                file_existed = target_file.exists()
                deployment_info = {
                    "name": target_name,
                    "template": str(source_path),
                    "target": str(target_file),
                }

                if file_existed:
                    results["updated"].append(deployment_info)
                    self.logger.info(f"Updated framework file: {target_name}")
                else:
                    results["deployed"].append(deployment_info)
                    self.logger.info(f"Deployed framework file: {target_name}")

        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising AgentDeploymentError as this is non-critical
