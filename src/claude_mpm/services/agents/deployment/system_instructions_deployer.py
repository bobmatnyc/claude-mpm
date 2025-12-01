"""System instructions deployment for agent deployment service.

This module handles deployment of system instructions and framework files.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import logging
import shutil
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
                    "PM_INSTRUCTIONS.md",
                    "PM_INSTRUCTIONS.md",
                ),  # Keep PM_INSTRUCTIONS.md as is - NEVER rename to CLAUDE.md
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
                if (
                    not force_rebuild
                    and target_file.exists()
                    and target_file.stat().st_mtime >= source_path.stat().st_mtime
                ):
                    # File is up to date based on modification time
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

        # Also deploy templates directory
        self.deploy_templates(claude_dir, force_rebuild, results)

    def deploy_templates(
        self,
        claude_dir: Path,
        force_rebuild: bool,
        results: Dict[str, Any],
    ) -> None:
        """
        Deploy template reference files to project .claude/templates directory.

        Templates are documentation files referenced in PM_INSTRUCTIONS.md that provide
        detailed protocols, examples, and matrices. They are deployed alongside the
        main instruction files for easy access.

        Args:
            claude_dir: Project .claude directory
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Find templates source directory
            from claude_mpm.config.paths import paths

            templates_source = paths.agents_dir / "templates"

            if not templates_source.exists():
                self.logger.warning(f"Templates source directory not found: {templates_source}")
                return

            # Create templates target directory
            templates_target = claude_dir / "templates"
            templates_target.mkdir(parents=True, exist_ok=True)

            # Deploy template markdown files
            template_files = list(templates_source.glob("*.md"))
            deployed_count = 0
            skipped_count = 0

            for template_file in template_files:
                # Skip special files
                if template_file.name.startswith("__"):
                    continue

                target_file = templates_target / template_file.name

                # Check if update needed
                if (
                    not force_rebuild
                    and target_file.exists()
                    and target_file.stat().st_mtime >= template_file.stat().st_mtime
                ):
                    skipped_count += 1
                    continue

                # Copy template file
                shutil.copy2(template_file, target_file)
                deployed_count += 1

                self.logger.debug(f"Deployed template: {template_file.name}")

            # Track results
            if deployed_count > 0:
                template_info = {
                    "name": "templates/",
                    "count": deployed_count,
                    "target": str(templates_target),
                }
                results["deployed"].append(template_info)
                self.logger.info(f"Deployed {deployed_count} template files to {templates_target}")

            if skipped_count > 0:
                self.logger.debug(f"Skipped {skipped_count} up-to-date template files")

        except Exception as e:
            error_msg = f"Failed to deploy templates: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising exception as template deployment is non-critical
