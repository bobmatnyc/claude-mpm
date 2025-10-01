from pathlib import Path

"""
Validation hooks for claude-mpm operations.

Inspired by awesome-claude-code's pre-push validation approach.
"""

from typing import Any, Callable, Dict, List, Optional

import yaml

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.validation import AgentValidator, ValidationResult

logger = get_logger(__name__)


class ValidationHooks:
    """Manages validation hooks for various operations."""

    def __init__(self):
        """Initialize validation hooks."""
        self.pre_load_hooks: List[Callable] = []
        self.post_load_hooks: List[Callable] = []
        self.pre_execute_hooks: List[Callable] = []
        self.validator = AgentValidator()

    def register_pre_load_hook(self, hook: Callable) -> None:
        """Register a hook to run before loading an agent."""
        self.pre_load_hooks.append(hook)

    def register_post_load_hook(self, hook: Callable) -> None:
        """Register a hook to run after loading an agent."""
        self.post_load_hooks.append(hook)

    def register_pre_execute_hook(self, hook: Callable) -> None:
        """Register a hook to run before executing an agent."""
        self.pre_execute_hooks.append(hook)

    async def run_pre_load_validation(self, profile_path: Path) -> ValidationResult:
        """Run validation before loading an agent profile."""
        logger.info(f"Running pre-load validation for {profile_path}")

        # Run basic file validation
        if not profile_path.exists():
            result = ValidationResult(is_valid=False)
            result.errors.append(f"Profile file not found: {profile_path}")
            return result

        # Validate profile structure
        result = self.validator.validate_profile(profile_path)

        # Run custom pre-load hooks
        for hook in self.pre_load_hooks:
            try:
                hook_result = await hook(profile_path)
                if hasattr(hook_result, "errors"):
                    result.errors.extend(hook_result.errors)
                    if hook_result.errors:
                        result.is_valid = False
            except Exception as e:
                logger.error(f"Pre-load hook failed: {e}")
                result.warnings.append(f"Pre-load hook failed: {e!s}")

        return result

    async def run_post_load_validation(
        self, agent_config: Dict[str, Any]
    ) -> ValidationResult:
        """Run validation after loading an agent."""
        result = ValidationResult(is_valid=True)

        # Run custom post-load hooks
        for hook in self.post_load_hooks:
            try:
                hook_result = await hook(agent_config)
                if hasattr(hook_result, "warnings"):
                    result.warnings.extend(hook_result.warnings)
            except Exception as e:
                logger.error(f"Post-load hook failed: {e}")
                result.warnings.append(f"Post-load hook failed: {e!s}")

        return result

    async def run_pre_execute_validation(
        self, agent_name: str, task: str
    ) -> ValidationResult:
        """Run validation before executing an agent task."""
        result = ValidationResult(is_valid=True)

        # Validate task format
        if not task or not task.strip():
            result.errors.append("Task cannot be empty")
            result.is_valid = False

        # Check task length
        if len(task) > 10000:
            result.warnings.append("Task is very long, consider breaking it down")

        # Run custom pre-execute hooks
        for hook in self.pre_execute_hooks:
            try:
                hook_result = await hook(agent_name, task)
                if hasattr(hook_result, "errors") and hook_result.errors:
                    result.errors.extend(hook_result.errors)
                    result.is_valid = False
            except Exception as e:
                logger.error(f"Pre-execute hook failed: {e}")
                result.warnings.append(f"Pre-execute hook failed: {e!s}")

        return result


# Built-in validation hooks
async def validate_agent_dependencies(profile_path: Path) -> ValidationResult:
    """Validate that agent dependencies are available."""
    result = ValidationResult(is_valid=True)

    try:
        with profile_path.open() as f:
            profile_data = yaml.safe_load(f)

        # Check for circular dependencies
        agents = profile_data.get("agents", [])
        for agent in agents:
            dependencies = agent.get("dependencies", [])
            # Simple check - in real implementation would need graph analysis
            if agent["name"] in dependencies:
                result.errors.append(f"Agent '{agent['name']}' has circular dependency")
                result.is_valid = False

    except Exception as e:
        result.warnings.append(f"Could not check dependencies: {e}")

    return result


async def validate_security_constraints(agent_name: str, task: str) -> ValidationResult:
    """Validate security constraints before execution."""
    result = ValidationResult(is_valid=True)

    # Check for potential security issues in task
    dangerous_patterns = [
        "rm -rf /",
        "sudo rm",
        "format c:",
        "__import__",
        "eval(",
        "exec(",
    ]

    task_lower = task.lower()
    for pattern in dangerous_patterns:
        if pattern in task_lower:
            result.errors.append(f"Potentially dangerous pattern detected: {pattern}")
            result.is_valid = False

    return result


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(
        self, message: str, validation_result: Optional[ValidationResult] = None
    ):
        """Initialize validation error."""
        super().__init__(message)
        self.validation_result = validation_result

    def get_detailed_message(self) -> str:
        """Get detailed error message including validation results."""
        if not self.validation_result:
            return str(self)

        lines = [str(self)]

        if self.validation_result.errors:
            lines.append("\nErrors:")
            for error in self.validation_result.errors:
                lines.append(f"  - {error}")

        if self.validation_result.warnings:
            lines.append("\nWarnings:")
            for warning in self.validation_result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)
