"""
Check claude-mpm configuration files.

WHY: Verify that user and project configurations are valid, accessible,
and properly structured.
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from ..models import DiagnosticResult, DiagnosticStatus
from .base_check import BaseDiagnosticCheck


class ConfigurationCheck(BaseDiagnosticCheck):
    """Check configuration files and settings."""

    @property
    def name(self) -> str:
        return "configuration_check"

    @property
    def category(self) -> str:
        return "Configuration"

    def run(self) -> DiagnosticResult:
        """Run configuration diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check user configuration
            user_result = self._check_user_config()
            sub_results.append(user_result)
            details["user_config"] = user_result.details

            # Check project configuration
            project_result = self._check_project_config()
            sub_results.append(project_result)
            details["project_config"] = project_result.details

            # Check environment variables
            env_result = self._check_environment_variables()
            sub_results.append(env_result)
            details["environment"] = env_result.details

            # Check configuration permissions
            perm_result = self._check_config_permissions()
            sub_results.append(perm_result)

            # Determine overall status
            if any(r.status == DiagnosticStatus.ERROR for r in sub_results):
                status = DiagnosticStatus.ERROR
                message = "Configuration has critical issues"
            elif any(r.status == DiagnosticStatus.WARNING for r in sub_results):
                status = DiagnosticStatus.WARNING
                message = "Configuration has minor issues"
            else:
                status = DiagnosticStatus.OK
                message = "Configuration is valid"

            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                sub_results=sub_results if self.verbose else [],
            )

        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=DiagnosticStatus.ERROR,
                message=f"Configuration check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_user_config(self) -> DiagnosticResult:
        """Check user-level configuration."""
        config_path = Path.home() / ".claude" / "claude-mpm.yaml"

        if not config_path.exists():
            return DiagnosticResult(
                category="User Config",
                status=DiagnosticStatus.OK,
                message="No user configuration (using defaults)",
                details={"path": str(config_path), "exists": False},
            )

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            issues = self._validate_config_structure(config)
            if issues:
                return DiagnosticResult(
                    category="User Config",
                    status=DiagnosticStatus.WARNING,
                    message=f"User config has issues: {', '.join(issues)}",
                    details={"path": str(config_path), "issues": issues},
                )

            return DiagnosticResult(
                category="User Config",
                status=DiagnosticStatus.OK,
                message="User configuration valid",
                details={
                    "path": str(config_path),
                    "size": config_path.stat().st_size,
                    "exists": True,
                },
            )

        except yaml.YAMLError as e:
            return DiagnosticResult(
                category="User Config",
                status=DiagnosticStatus.ERROR,
                message="User config has invalid YAML",
                details={"path": str(config_path), "error": str(e)},
                fix_description="Fix YAML syntax errors in the configuration file",
            )
        except Exception as e:
            return DiagnosticResult(
                category="User Config",
                status=DiagnosticStatus.WARNING,
                message=f"Could not read user config: {e!s}",
                details={"path": str(config_path), "error": str(e)},
            )

    def _check_project_config(self) -> DiagnosticResult:
        """Check project-level configuration."""
        config_path = Path.cwd() / ".claude" / "claude-mpm.yaml"

        if not config_path.exists():
            return DiagnosticResult(
                category="Project Config",
                status=DiagnosticStatus.OK,
                message="No project configuration (using defaults)",
                details={"path": str(config_path), "exists": False},
            )

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            issues = self._validate_config_structure(config)
            if issues:
                return DiagnosticResult(
                    category="Project Config",
                    status=DiagnosticStatus.WARNING,
                    message=f"Project config has issues: {', '.join(issues)}",
                    details={"path": str(config_path), "issues": issues},
                )

            # Check for deprecated keys
            deprecated = self._check_deprecated_keys(config)
            if deprecated:
                return DiagnosticResult(
                    category="Project Config",
                    status=DiagnosticStatus.WARNING,
                    message=f"Using deprecated config keys: {', '.join(deprecated)}",
                    details={"path": str(config_path), "deprecated_keys": deprecated},
                    fix_description="Remove deprecated configuration keys",
                )

            return DiagnosticResult(
                category="Project Config",
                status=DiagnosticStatus.OK,
                message="Project configuration valid",
                details={
                    "path": str(config_path),
                    "size": config_path.stat().st_size,
                    "exists": True,
                },
            )

        except yaml.YAMLError as e:
            return DiagnosticResult(
                category="Project Config",
                status=DiagnosticStatus.ERROR,
                message="Project config has invalid YAML",
                details={"path": str(config_path), "error": str(e)},
                fix_description="Fix YAML syntax errors in the configuration file",
            )
        except Exception as e:
            return DiagnosticResult(
                category="Project Config",
                status=DiagnosticStatus.WARNING,
                message=f"Could not read project config: {e!s}",
                details={"path": str(config_path), "error": str(e)},
            )

    def _check_environment_variables(self) -> DiagnosticResult:
        """Check relevant environment variables."""
        env_vars = {
            "CLAUDE_MPM_CONFIG": os.environ.get("CLAUDE_MPM_CONFIG"),
            "CLAUDE_MPM_LOG_LEVEL": os.environ.get("CLAUDE_MPM_LOG_LEVEL"),
            "CLAUDE_MPM_PROJECT_DIR": os.environ.get("CLAUDE_MPM_PROJECT_DIR"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
        }

        set_vars = {k: v for k, v in env_vars.items() if v is not None}

        if not set_vars:
            return DiagnosticResult(
                category="Environment Variables",
                status=DiagnosticStatus.OK,
                message="No claude-mpm environment variables set",
                details={"variables": {}},
            )

        return DiagnosticResult(
            category="Environment Variables",
            status=DiagnosticStatus.OK,
            message=f"{len(set_vars)} environment variable(s) configured",
            details={"variables": set_vars},
        )

    def _check_config_permissions(self) -> DiagnosticResult:
        """Check configuration file permissions."""
        issues = []
        paths_checked = []

        for config_path in [
            Path.home() / ".claude" / "claude-mpm.yaml",
            Path.cwd() / ".claude" / "claude-mpm.yaml",
        ]:
            if config_path.exists():
                paths_checked.append(str(config_path))

                # Check readability
                if not os.access(config_path, os.R_OK):
                    issues.append(f"{config_path.name} is not readable")

                # Check if world-writable (security concern)
                stat_info = config_path.stat()
                if stat_info.st_mode & 0o002:
                    issues.append(
                        f"{config_path.name} is world-writable (security risk)"
                    )

        if not paths_checked:
            return DiagnosticResult(
                category="Config Permissions",
                status=DiagnosticStatus.OK,
                message="No configuration files to check",
                details={"paths_checked": []},
            )

        if issues:
            return DiagnosticResult(
                category="Config Permissions",
                status=DiagnosticStatus.WARNING,
                message=f"Permission issues: {', '.join(issues)}",
                details={"issues": issues, "paths_checked": paths_checked},
                fix_command="chmod 644 ~/.claude/claude-mpm.yaml",
                fix_description="Fix file permissions for configuration files",
            )

        return DiagnosticResult(
            category="Config Permissions",
            status=DiagnosticStatus.OK,
            message="Configuration file permissions are correct",
            details={"paths_checked": paths_checked},
        )

    def _validate_config_structure(self, config: Dict[str, Any]) -> list:
        """Validate configuration structure and return issues."""
        issues = []

        if not isinstance(config, dict):
            issues.append("Configuration is not a dictionary")
            return issues

        # Check for invalid top-level keys
        valid_keys = {
            "response_logging",
            "agent_deployment",
            "memory_management",
            "monitoring",
            "mcp",
            "hooks",
            "paths",
            "debug",
        }

        invalid_keys = set(config.keys()) - valid_keys
        if invalid_keys:
            issues.append(f"Unknown keys: {', '.join(invalid_keys)}")

        return issues

    def _check_deprecated_keys(self, config: Dict[str, Any]) -> list:
        """Check for deprecated configuration keys."""
        deprecated_keys = ["legacy_mode", "old_agent_format", "deprecated_logging"]
        found_deprecated = []

        for key in deprecated_keys:
            if key in config:
                found_deprecated.append(key)

        return found_deprecated
