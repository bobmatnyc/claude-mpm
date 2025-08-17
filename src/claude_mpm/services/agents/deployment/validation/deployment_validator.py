"""Main deployment validator service."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger

from .agent_validator import AgentValidator
from .template_validator import TemplateValidator
from .validation_result import ValidationResult


class DeploymentValidator:
    """Main validator for deployment operations.

    This service orchestrates validation of templates, agents,
    and deployment environments.
    """

    def __init__(self):
        """Initialize the deployment validator."""
        self.logger = get_logger(__name__)
        self.template_validator = TemplateValidator()
        self.agent_validator = AgentValidator()

    def validate_template_files(
        self, template_files: List[Path]
    ) -> Dict[str, ValidationResult]:
        """Validate multiple template files.

        Args:
            template_files: List of template file paths

        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}

        for template_file in template_files:
            self.logger.debug(f"Validating template: {template_file}")
            result = self.template_validator.validate_template_file(template_file)
            results[str(template_file)] = result

            if not result.is_valid:
                self.logger.warning(
                    f"Template validation failed for {template_file}: {result}"
                )
            elif result.has_warnings:
                self.logger.info(
                    f"Template validation warnings for {template_file}: {result.warning_count} warnings"
                )

        return results

    def validate_agent_files(
        self, agent_files: List[Path]
    ) -> Dict[str, ValidationResult]:
        """Validate multiple agent files.

        Args:
            agent_files: List of agent file paths

        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}

        for agent_file in agent_files:
            self.logger.debug(f"Validating agent: {agent_file}")
            result = self.agent_validator.validate_agent_file(agent_file)
            results[str(agent_file)] = result

            if not result.is_valid:
                self.logger.warning(
                    f"Agent validation failed for {agent_file}: {result}"
                )
            elif result.has_warnings:
                self.logger.info(
                    f"Agent validation warnings for {agent_file}: {result.warning_count} warnings"
                )

        return results

    def validate_deployment_environment(
        self, target_dir: Path, templates_dir: Optional[Path] = None
    ) -> ValidationResult:
        """Validate deployment environment.

        Args:
            target_dir: Target deployment directory
            templates_dir: Optional templates directory

        Returns:
            ValidationResult for environment validation
        """
        result = ValidationResult(is_valid=True)

        # Validate target directory
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                result.add_info(f"Created target directory: {target_dir}")
            except Exception as e:
                result.add_error(f"Cannot create target directory {target_dir}: {e}")
                return result

        if not target_dir.is_dir():
            result.add_error(f"Target path is not a directory: {target_dir}")
            return result

        # Check if target directory is writable
        test_file = target_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            result.add_info("Target directory is writable")
        except Exception as e:
            result.add_error(f"Target directory is not writable: {target_dir} - {e}")

        # Validate templates directory if provided
        if templates_dir:
            if not templates_dir.exists():
                result.add_error(f"Templates directory does not exist: {templates_dir}")
            elif not templates_dir.is_dir():
                result.add_error(f"Templates path is not a directory: {templates_dir}")
            else:
                # Check for template files
                template_files = list(templates_dir.glob("*.json"))
                if not template_files:
                    result.add_warning(f"No template files found in: {templates_dir}")
                else:
                    result.add_info(f"Found {len(template_files)} template files")

        return result

    def validate_deployment_context(self, context) -> ValidationResult:
        """Validate deployment context.

        Args:
            context: Deployment context (pipeline or deployment context)

        Returns:
            ValidationResult for context validation
        """
        result = ValidationResult(is_valid=True)

        # Validate target directory
        target_dir = getattr(context, "actual_target_dir", None) or getattr(
            context, "target_dir", None
        )
        if target_dir:
            env_result = self.validate_deployment_environment(target_dir)
            result = result.merge(env_result)
        else:
            result.add_error("No target directory specified in context")

        # Validate template files
        template_files = getattr(context, "template_files", [])
        if template_files:
            template_results = self.validate_template_files(template_files)

            # Aggregate template validation results
            total_templates = len(template_results)
            valid_templates = sum(1 for r in template_results.values() if r.is_valid)

            if valid_templates == total_templates:
                result.add_info(f"All {total_templates} templates are valid")
            else:
                invalid_count = total_templates - valid_templates
                result.add_error(
                    f"{invalid_count} of {total_templates} templates are invalid"
                )

            # Add template validation details to metadata
            result.metadata["template_validation"] = {
                "total": total_templates,
                "valid": valid_templates,
                "invalid": total_templates - valid_templates,
                "details": {path: r.to_dict() for path, r in template_results.items()},
            }
        else:
            result.add_warning("No template files to validate")

        return result

    def repair_agent_files(
        self, agent_files: List[Path], dry_run: bool = True
    ) -> Dict[str, ValidationResult]:
        """Repair multiple agent files.

        Args:
            agent_files: List of agent file paths
            dry_run: If True, don't actually modify files

        Returns:
            Dictionary mapping file paths to repair results
        """
        results = {}

        for agent_file in agent_files:
            self.logger.debug(f"Repairing agent: {agent_file}")
            result = self.agent_validator.repair_agent_file(agent_file, dry_run=dry_run)
            results[str(agent_file)] = result

            if not result.is_valid:
                self.logger.error(f"Agent repair failed for {agent_file}: {result}")
            else:
                self.logger.info(f"Agent repair completed for {agent_file}")

        return results

    def get_validation_summary(
        self, results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """Get summary of validation results.

        Args:
            results: Dictionary of validation results

        Returns:
            Summary dictionary
        """
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        invalid = total - valid

        total_errors = sum(r.error_count for r in results.values())
        total_warnings = sum(r.warning_count for r in results.values())

        return {
            "total_files": total,
            "valid_files": valid,
            "invalid_files": invalid,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "success_rate": (valid / total * 100) if total > 0 else 0,
            "details": {path: r.to_dict() for path, r in results.items()},
        }
