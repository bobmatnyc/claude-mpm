"""System instructions deployment for agent deployment service.

This module handles deployment of system instructions and framework files.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import logging
import shutil
from pathlib import Path
from typing import Any


class SystemInstructionsDeployer:
    """Handles deployment of system instructions and framework files."""

    def __init__(self, logger: logging.Logger, working_directory: Path):
        """Initialize the deployer with logger and working directory."""
        self.logger = logger
        self.working_directory = working_directory

    def _resolve_block(self, block_name: str, agents_path: Path) -> str:
        """Resolve a block file with additive project+user override semantics.

        Priority: user_override + project_override (additive, together replace system)
        Fallback: system default from agents_path

        Args:
            block_name: Filename of the block (e.g. "PM_INSTRUCTIONS.md")
            agents_path: Path to the system agents directory

        Returns:
            Resolved content string (may be empty if no sources found)
        """
        system_path = agents_path / block_name
        user_path = Path.home() / ".claude-mpm" / block_name
        project_path = self.working_directory / ".claude-mpm" / block_name

        parts = []
        if user_path.exists():
            parts.append(user_path.read_text(encoding="utf-8"))
        if project_path.exists():
            parts.append(project_path.read_text(encoding="utf-8"))
        if not parts and system_path.exists():
            parts.append(system_path.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    def deploy_system_instructions(
        self,
        target_dir: Path,
        force_rebuild: bool,
        results: dict[str, Any],
    ) -> None:
        """
        Deploy system instructions and framework files for PM framework.

        Deploys to project .claude-mpm directory as merged PM_INSTRUCTIONS_DEPLOYED.md
        containing PM_INSTRUCTIONS.md + AGENT_DELEGATION.md + WORKFLOW.md + MEMORY.md.

        Each block is resolved with additive override semantics:
          - user override (~/.claude-mpm/<BLOCK>.md) + project override
            (.claude-mpm/<BLOCK>.md) concatenated together replace the system default.
          - If neither override exists, the system default is used.

        Args:
            target_dir: Target directory for deployment (not used - always uses project .claude-mpm)
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        # Initialize before try so it's always bound for deploy_templates below
        claude_mpm_dir = self.working_directory / ".claude-mpm"

        try:
            # Ensure .claude-mpm directory exists
            claude_mpm_dir.mkdir(parents=True, exist_ok=True)

            # Find the agents directory with framework files
            # Use centralized paths for consistency
            from claude_mpm.config.paths import paths

            agents_path = paths.agents_dir

            # Blocks that compose PM_INSTRUCTIONS_DEPLOYED.md (in order)
            BLOCKS = [
                "PM_INSTRUCTIONS.md",
                "AGENT_DELEGATION.md",
                "WORKFLOW.md",
                "MEMORY.md",
            ]

            # Resolve each block with additive override semantics
            merged_content = [self._resolve_block(b, agents_path) for b in BLOCKS]
            merged_content = [c for c in merged_content if c]  # drop empty blocks

            if not merged_content:
                self.logger.error("No framework files found to merge")
                results["errors"].append("No framework files found to merge")
                return

            # Collect all paths that should trigger a rebuild when modified
            watched_paths: list[Path] = []
            for block in BLOCKS:
                for base in [
                    agents_path,
                    Path.home() / ".claude-mpm",
                    self.working_directory / ".claude-mpm",
                ]:
                    p = base / block
                    if p.exists():
                        watched_paths.append(p)

            latest_mtime = (
                max(p.stat().st_mtime for p in watched_paths) if watched_paths else 0
            )

            # Write merged content to PM_INSTRUCTIONS_DEPLOYED.md
            target_file = claude_mpm_dir / "PM_INSTRUCTIONS_DEPLOYED.md"

            # Check if update needed
            if (
                not force_rebuild
                and target_file.exists()
                and target_file.stat().st_mtime >= latest_mtime
            ):
                # File is up to date based on modification time
                results["skipped"].append("PM_INSTRUCTIONS_DEPLOYED.md")
                self.logger.debug("PM_INSTRUCTIONS_DEPLOYED.md up to date")
            else:
                # Check if file exists before writing (for proper tracking)
                file_existed = target_file.exists()

                # Write merged content
                target_file.write_text("\n\n".join(merged_content))

                # Track deployment
                source_desc = ", ".join(str(p) for p in watched_paths if p.exists())
                deployment_info = {
                    "name": "PM_INSTRUCTIONS_DEPLOYED.md",
                    "template": source_desc,
                    "target": str(target_file),
                }

                if file_existed:
                    results["updated"].append(deployment_info)
                    self.logger.info("Updated merged PM_INSTRUCTIONS_DEPLOYED.md")
                else:
                    results["deployed"].append(deployment_info)
                    self.logger.info("Deployed merged PM_INSTRUCTIONS_DEPLOYED.md")

        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising AgentDeploymentError as this is non-critical

        # Also deploy templates directory
        self.deploy_templates(claude_mpm_dir, force_rebuild, results)

    def deploy_templates(
        self,
        claude_mpm_dir: Path,
        force_rebuild: bool,
        results: dict[str, Any],
    ) -> None:
        """
        Deploy PM instruction template files to project .claude-mpm/templates directory.

        Only deploys PM instruction templates (not agent definition templates).
        Templates are documentation files referenced in PM_INSTRUCTIONS.md that provide
        detailed protocols, examples, and matrices.

        Args:
            claude_mpm_dir: Project .claude-mpm directory
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Find templates source directory
            from claude_mpm.config.paths import paths

            templates_source = paths.agents_dir / "templates"

            if not templates_source.exists():
                self.logger.warning(
                    f"Templates source directory not found: {templates_source}"
                )
                return

            # Create templates target directory
            templates_target = claude_mpm_dir / "templates"
            templates_target.mkdir(parents=True, exist_ok=True)

            # Only deploy PM instruction templates (not agent definitions)
            pm_templates = [
                "circuit-breakers.md",
                "context-management-examples.md",
                "git-file-tracking.md",
                "pm-examples.md",
                "pm-red-flags.md",
                "pr-workflow-examples.md",
                "research-gate-examples.md",
                "response-format.md",
                "structured-questions-examples.md",
                "ticketing-examples.md",
                "validation-templates.md",
            ]

            # Get template files that exist
            template_files = [
                templates_source / name
                for name in pm_templates
                if (templates_source / name).exists()
            ]

            deployed_count = 0
            skipped_count = 0
            missing_count = 0

            # Track missing templates
            for name in pm_templates:
                if not (templates_source / name).exists():
                    self.logger.warning(f"PM template not found: {name}")
                    missing_count += 1

            for template_file in template_files:
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

                self.logger.debug(f"Deployed PM template: {template_file.name}")

            # Track results
            if deployed_count > 0:
                template_info = {
                    "name": "templates/",
                    "count": deployed_count,
                    "target": str(templates_target),
                }
                results["deployed"].append(template_info)
                self.logger.info(
                    f"Deployed {deployed_count} PM template files to {templates_target}"
                )

            if skipped_count > 0:
                self.logger.debug(
                    f"Skipped {skipped_count} up-to-date PM template files"
                )

            if missing_count > 0:
                self.logger.warning(f"{missing_count} PM templates not found in source")

        except Exception as e:
            error_msg = f"Failed to deploy templates: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising exception as template deployment is non-critical
