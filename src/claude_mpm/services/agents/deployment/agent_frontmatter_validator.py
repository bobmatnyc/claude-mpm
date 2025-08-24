"""Agent frontmatter validation for deployment service.

This module provides validation and repair functionality for agent frontmatter.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

import contextlib
import logging
from pathlib import Path
from typing import Any, Dict


class AgentFrontmatterValidator:
    """Validates and repairs agent frontmatter."""

    def __init__(self, logger: logging.Logger):
        """Initialize the validator with a logger."""
        self.logger = logger

    def validate_and_repair_existing_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """
        Validate and repair broken frontmatter in existing agent files.

        This method scans existing .claude/agents/*.md files and validates their
        frontmatter. If the frontmatter is broken or missing, it attempts to repair
        it or marks the agent for replacement during deployment.

        WHY: Ensures all existing agents have valid YAML frontmatter before deployment,
        preventing runtime errors in Claude Code when loading agents.

        Args:
            agents_dir: Directory containing agent .md files

        Returns:
            Dictionary with validation results:
            - repaired: List of agent names that were repaired
            - replaced: List of agent names marked for replacement
            - errors: List of validation errors
        """
        results = {"repaired": [], "replaced": [], "errors": []}

        try:
            # Import frontmatter validator
            from claude_mpm.agents.frontmatter_validator import FrontmatterValidator

            validator = FrontmatterValidator()

            # Find existing agent files
            agent_files = list(agents_dir.glob("*.md"))

            if not agent_files:
                self.logger.debug("No existing agent files to validate")
                return results

            self.logger.debug(
                f"Validating frontmatter in {len(agent_files)} existing agents"
            )

            for agent_file in agent_files:
                try:
                    agent_name = agent_file.stem

                    # Read agent file content
                    content = agent_file.read_text()

                    # Check if this is a system agent (authored by claude-mpm)
                    # Only repair system agents, leave user agents alone
                    if (
                        "author: claude-mpm" not in content
                        and "author: 'claude-mpm'" not in content
                    ):
                        self.logger.debug(
                            f"Skipping validation for user agent: {agent_name}"
                        )
                        continue

                    # Extract and validate frontmatter
                    if not content.startswith("---"):
                        # No frontmatter at all - mark for replacement
                        self.logger.warning(
                            f"Agent {agent_name} has no frontmatter, marking for replacement"
                        )
                        results["replaced"].append(agent_name)
                        # Delete the file so it will be recreated
                        agent_file.unlink()
                        continue

                    # Try to extract frontmatter
                    try:
                        end_marker = content.find("\n---\n", 4)
                        if end_marker == -1:
                            end_marker = content.find("\n---\r\n", 4)

                        if end_marker == -1:
                            # Broken frontmatter - mark for replacement
                            self.logger.warning(
                                f"Agent {agent_name} has broken frontmatter, marking for replacement"
                            )
                            results["replaced"].append(agent_name)
                            # Delete the file so it will be recreated
                            agent_file.unlink()
                            continue

                        # Validate frontmatter with the validator
                        validation_result = validator.validate_file(agent_file)

                        if not validation_result.is_valid:
                            # Check if it can be corrected
                            if validation_result.corrected_frontmatter:
                                # Apply corrections
                                correction_result = validator.correct_file(
                                    agent_file, dry_run=False
                                )
                                if correction_result.corrections:
                                    results["repaired"].append(agent_name)
                                    self.logger.info(
                                        f"Repaired frontmatter for agent {agent_name}"
                                    )
                                    for correction in correction_result.corrections:
                                        self.logger.debug(f"  - {correction}")
                            else:
                                # Cannot be corrected - mark for replacement
                                self.logger.warning(
                                    f"Agent {agent_name} has invalid frontmatter that cannot be repaired, marking for replacement"
                                )
                                results["replaced"].append(agent_name)
                                # Delete the file so it will be recreated
                                agent_file.unlink()
                        elif validation_result.warnings:
                            # Has warnings but is valid
                            for warning in validation_result.warnings:
                                self.logger.debug(
                                    f"Agent {agent_name} warning: {warning}"
                                )

                    except Exception as e:
                        # Any error in parsing - mark for replacement
                        self.logger.warning(
                            f"Failed to parse frontmatter for {agent_name}: {e}, marking for replacement"
                        )
                        results["replaced"].append(agent_name)
                        # Delete the file so it will be recreated
                        with contextlib.suppress(Exception):
                            agent_file.unlink()

                except Exception as e:
                    error_msg = f"Failed to validate agent {agent_file.name}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)

        except ImportError:
            self.logger.warning(
                "FrontmatterValidator not available, skipping validation"
            )
        except Exception as e:
            error_msg = f"Agent validation failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results
