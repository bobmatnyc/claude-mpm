"""
Local Deployment Strategy
=========================

Handles deployment to local filesystem and project directories.
Consolidates functionality from:
- agent_deployment.py
- local_template_deployment.py
- agent_filesystem_manager.py
- system_instructions_deployer.py
"""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.enums import HealthStatus, OperationResult
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.unified.strategies import StrategyMetadata, StrategyPriority

from .base import (
    DeploymentContext,
    DeploymentResult,
    DeploymentStrategy,
    DeploymentType,
)


class LocalDeploymentStrategy(DeploymentStrategy):
    """
    Strategy for local filesystem deployments.

    Handles deployment of agents, configs, templates, and resources to
    local project directories. Consolidates multiple local deployment
    patterns from various services.

    Features:
    - Agent deployment to .claude/agents
    - Configuration file deployment
    - Template instantiation and deployment
    - Resource copying and linking
    - Version management and rollback
    - Backup and restore capabilities
    """

    def __init__(self):
        """Initialize local deployment strategy."""
        metadata = StrategyMetadata(
            name="LocalDeploymentStrategy",
            description="Deploy to local filesystem and project directories",
            supported_types=["agent", "config", "template", "resource", "*"],
            supported_operations=["deploy", "rollback", "verify", "backup"],
            priority=StrategyPriority.HIGH,
            tags={"local", "filesystem", "project"},
        )
        super().__init__(metadata)
        self._logger = get_logger(f"{__name__}.LocalDeploymentStrategy")
        self._backups: Dict[str, Path] = {}

    def validate(self, context: DeploymentContext) -> List[str]:
        """
        Validate local deployment configuration.

        Args:
            context: Deployment context

        Returns:
            List of validation errors
        """
        errors = []

        # Check source exists
        source_path = Path(context.source)
        if not source_path.exists():
            errors.append(f"Source does not exist: {source_path}")

        # Check target directory permissions
        target_path = Path(context.target)
        target_parent = target_path.parent if target_path.suffix else target_path

        if not target_parent.exists():
            # Check if we can create it
            try:
                target_parent.mkdir(parents=True, exist_ok=True)
                target_parent.rmdir()  # Clean up test directory
            except PermissionError:
                errors.append(
                    f"No permission to create target directory: {target_parent}"
                )
        # Check write permissions
        elif not target_parent.is_dir():
            errors.append(f"Target parent is not a directory: {target_parent}")
        elif not self._check_write_permission(target_parent):
            errors.append(f"No write permission for target: {target_parent}")

        # Validate deployment type specific requirements
        if context.deployment_type == DeploymentType.AGENT:
            errors.extend(self._validate_agent_deployment(context))
        elif context.deployment_type == DeploymentType.CONFIG:
            errors.extend(self._validate_config_deployment(context))
        elif context.deployment_type == DeploymentType.TEMPLATE:
            errors.extend(self._validate_template_deployment(context))

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """
        Prepare deployment artifacts.

        Args:
            context: Deployment context

        Returns:
            List of prepared artifact paths
        """
        artifacts = []
        source_path = Path(context.source)

        # Create backup if enabled
        if context.backup_enabled:
            backup_path = self._create_backup(context)
            if backup_path:
                self._backups[str(context.target)] = backup_path
                artifacts.append(backup_path)

        # Prepare based on deployment type
        if context.deployment_type == DeploymentType.AGENT:
            artifacts.extend(self._prepare_agent_artifacts(context))
        elif context.deployment_type == DeploymentType.CONFIG:
            artifacts.extend(self._prepare_config_artifacts(context))
        elif context.deployment_type == DeploymentType.TEMPLATE:
            artifacts.extend(self._prepare_template_artifacts(context))
        else:
            # Default: prepare source as-is
            artifacts.append(source_path)

        return artifacts

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """
        Execute local deployment.

        Args:
            context: Deployment context
            artifacts: Prepared artifacts

        Returns:
            Deployment information
        """
        target_path = Path(context.target)
        deployment_id = self._generate_deployment_id()

        # Ensure target directory exists
        if not target_path.suffix:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)

        deployed_files = []

        # Deploy artifacts based on type
        if context.deployment_type == DeploymentType.AGENT:
            deployed_files = self._deploy_agent(context, artifacts, target_path)
        elif context.deployment_type == DeploymentType.CONFIG:
            deployed_files = self._deploy_config(context, artifacts, target_path)
        elif context.deployment_type == DeploymentType.TEMPLATE:
            deployed_files = self._deploy_template(context, artifacts, target_path)
        else:
            deployed_files = self._deploy_resources(context, artifacts, target_path)

        # Update version file if versioned
        if context.version:
            self._write_version_file(target_path, context.version)

        return {
            "deployment_id": deployment_id,
            "deployed_path": target_path,
            "deployed_files": deployed_files,
            "artifacts": [str(a) for a in artifacts],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """
        Verify local deployment success.

        Args:
            context: Deployment context
            deployment_info: Deployment information

        Returns:
            True if deployment verified
        """
        deployed_path = Path(deployment_info["deployed_path"])

        # Check deployed path exists
        if not deployed_path.exists():
            self._logger.error(f"Deployed path does not exist: {deployed_path}")
            return False

        # Check all deployed files exist
        for file_path in deployment_info.get("deployed_files", []):
            if not Path(file_path).exists():
                self._logger.error(f"Deployed file missing: {file_path}")
                return False

        # Type-specific verification
        if context.deployment_type == DeploymentType.AGENT:
            return self._verify_agent_deployment(deployed_path, context)
        if context.deployment_type == DeploymentType.CONFIG:
            return self._verify_config_deployment(deployed_path, context)
        if context.deployment_type == DeploymentType.TEMPLATE:
            return self._verify_template_deployment(deployed_path, context)

        return True

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """
        Rollback local deployment.

        Args:
            context: Deployment context
            result: Current deployment result

        Returns:
            True if rollback successful
        """
        target_path = Path(context.target)

        try:
            # Remove deployed files
            if result.deployed_path and result.deployed_path.exists():
                if result.deployed_path.is_file():
                    result.deployed_path.unlink()
                elif result.deployed_path.is_dir():
                    shutil.rmtree(result.deployed_path)

            # Restore from backup if available
            backup_path = self._backups.get(str(target_path))
            if backup_path and backup_path.exists():
                if backup_path.is_file():
                    shutil.copy2(backup_path, target_path)
                else:
                    shutil.copytree(backup_path, target_path, dirs_exist_ok=True)

                self._logger.info(f"Restored from backup: {backup_path}")

            return True

        except Exception as e:
            self._logger.error(f"Rollback failed: {e!s}")
            return False

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get health status of local deployment.

        Args:
            deployment_info: Deployment information

        Returns:
            Health status information
        """
        deployed_path = Path(deployment_info.get("deployed_path", ""))

        health = {
            "status": OperationResult.UNKNOWN,
            "deployed_path": str(deployed_path),
            "exists": deployed_path.exists() if deployed_path else False,
            "checks": {},
        }

        if deployed_path and deployed_path.exists():
            health["status"] = OperationResult.SUCCESS

            # Check file integrity
            for file_path in deployment_info.get("deployed_files", []):
                path = Path(file_path)
                health["checks"][str(path)] = path.exists()

            # Check if any file is missing
            if any(not check for check in health["checks"].values()):
                health["status"] = HealthStatus.DEGRADED

        else:
            health["status"] = HealthStatus.UNHEALTHY

        return health

    # Private helper methods

    def _check_write_permission(self, path: Path) -> bool:
        """Check if we have write permission to path."""
        try:
            test_file = path / f".write_test_{datetime.now(timezone.utc).timestamp()}"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID."""
        return f"local_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(self) % 10000:04d}"

    def _create_backup(self, context: DeploymentContext) -> Optional[Path]:
        """Create backup of target before deployment."""
        target_path = Path(context.target)

        if not target_path.exists():
            return None

        try:
            backup_dir = Path(tempfile.gettempdir()) / "claude_mpm_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"{target_path.name}.backup_{timestamp}"
            backup_path = backup_dir / backup_name

            if target_path.is_file():
                shutil.copy2(target_path, backup_path)
            else:
                shutil.copytree(target_path, backup_path)

            self._logger.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self._logger.warning(f"Failed to create backup: {e!s}")
            return None

    def _write_version_file(self, target_path: Path, version: str) -> None:
        """Write version file to deployment."""
        version_file = target_path / ".version"
        version_file.write_text(
            f"{version}\n{datetime.now(timezone.utc).isoformat()}\n"
        )

    # Agent deployment methods (consolidating agent_deployment.py patterns)

    def _validate_agent_deployment(self, context: DeploymentContext) -> List[str]:
        """Validate agent deployment specifics."""
        errors = []
        source_path = Path(context.source)

        # Check for required agent files
        if source_path.is_file():
            if source_path.suffix not in [".json", ".yaml", ".yml"]:
                errors.append(f"Invalid agent file format: {source_path.suffix}")
        elif source_path.is_dir():
            # Check for agent definition files
            agent_files = (
                list(source_path.glob("*.json"))
                + list(source_path.glob("*.yaml"))
                + list(source_path.glob("*.yml"))
            )
            if not agent_files:
                errors.append(f"No agent definition files found in: {source_path}")

        return errors

    def _prepare_agent_artifacts(self, context: DeploymentContext) -> List[Path]:
        """Prepare agent deployment artifacts."""
        source_path = Path(context.source)
        artifacts = []

        # Convert JSON to YAML if needed
        if source_path.suffix == ".json":
            yaml_path = self._convert_json_to_yaml(source_path)
            artifacts.append(yaml_path)
        else:
            artifacts.append(source_path)

        return artifacts

    def _deploy_agent(
        self, context: DeploymentContext, artifacts: List[Path], target_path: Path
    ) -> List[Path]:
        """Deploy agent files."""
        deployed = []

        for artifact in artifacts:
            if artifact.suffix in [".yaml", ".yml"]:
                dest = target_path / artifact.name
                shutil.copy2(artifact, dest)
                deployed.append(dest)

                self._logger.debug(f"Deployed agent: {dest}")

        return deployed

    def _verify_agent_deployment(
        self, deployed_path: Path, context: DeploymentContext
    ) -> bool:
        """Verify agent deployment."""
        # Check for valid YAML structure
        yaml_files = list(deployed_path.glob("*.yaml")) + list(
            deployed_path.glob("*.yml")
        )

        for yaml_file in yaml_files:
            try:
                with yaml_file.open() as f:
                    data = yaml.safe_load(f)
                    # Basic agent structure validation
                    if not isinstance(data, dict):
                        return False
                    if "name" not in data:
                        self._logger.error(f"Agent missing 'name' field: {yaml_file}")
                        return False
            except Exception as e:
                self._logger.error(f"Invalid agent YAML: {yaml_file}: {e!s}")
                return False

        return True

    def _convert_json_to_yaml(self, json_path: Path) -> Path:
        """Convert JSON agent to YAML format."""
        with json_path.open() as f:
            data = json.load(f)

        yaml_path = Path(tempfile.gettempdir()) / f"{json_path.stem}.yaml"
        with yaml_path.open("w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return yaml_path

    # Config deployment methods

    def _validate_config_deployment(self, context: DeploymentContext) -> List[str]:
        """Validate config deployment."""
        errors = []
        source_path = Path(context.source)

        if source_path.is_file():
            # Validate config file format
            if source_path.suffix not in [
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                ".env",
            ]:
                errors.append(f"Unsupported config format: {source_path.suffix}")

        return errors

    def _prepare_config_artifacts(self, context: DeploymentContext) -> List[Path]:
        """Prepare config artifacts."""
        return [Path(context.source)]

    def _deploy_config(
        self, context: DeploymentContext, artifacts: List[Path], target_path: Path
    ) -> List[Path]:
        """Deploy configuration files."""
        deployed = []

        for artifact in artifacts:
            dest = target_path / artifact.name if target_path.is_dir() else target_path

            shutil.copy2(artifact, dest)
            deployed.append(dest)

            self._logger.info(f"Deployed config: {dest}")

        return deployed

    def _verify_config_deployment(
        self, deployed_path: Path, context: DeploymentContext
    ) -> bool:
        """Verify config deployment."""
        # Basic validation - file exists and is readable
        if deployed_path.is_file():
            try:
                deployed_path.read_text()
                return True
            except Exception:
                return False
        return deployed_path.exists()

    # Template deployment methods

    def _validate_template_deployment(self, context: DeploymentContext) -> List[str]:
        """Validate template deployment."""
        errors = []

        # Check for template variables in config
        if "variables" not in context.config:
            self._logger.warning("No template variables provided")

        return errors

    def _prepare_template_artifacts(self, context: DeploymentContext) -> List[Path]:
        """Prepare template artifacts."""
        source_path = Path(context.source)
        artifacts = []

        # Process template with variables
        if source_path.is_file():
            processed = self._process_template(
                source_path, context.config.get("variables", {})
            )
            artifacts.append(processed)
        else:
            # Process all template files in directory
            for template_file in source_path.rglob("*"):
                if template_file.is_file():
                    processed = self._process_template(
                        template_file, context.config.get("variables", {})
                    )
                    artifacts.append(processed)

        return artifacts

    def _deploy_template(
        self, context: DeploymentContext, artifacts: List[Path], target_path: Path
    ) -> List[Path]:
        """Deploy template files."""
        deployed = []

        for artifact in artifacts:
            if target_path.is_dir():
                # Maintain relative structure
                source_base = Path(context.source)
                if source_base.is_dir():
                    rel_path = artifact.relative_to(Path(tempfile.gettempdir()))
                    dest = target_path / rel_path
                else:
                    dest = target_path / artifact.name
            else:
                dest = target_path

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact, dest)
            deployed.append(dest)

            self._logger.info(f"Deployed template: {dest}")

        return deployed

    def _verify_template_deployment(
        self, deployed_path: Path, context: DeploymentContext
    ) -> bool:
        """Verify template deployment."""
        # Check that template variables were replaced
        context.config.get("variables", {})

        if deployed_path.is_file():
            content = deployed_path.read_text()
            # Check no template markers remain
            if "{{" in content or "{%" in content:
                self._logger.warning("Template markers still present in deployed file")
                return False

        return True

    def _process_template(self, template_path: Path, variables: Dict[str, Any]) -> Path:
        """Process template file with variables."""
        content = template_path.read_text()

        # Simple variable replacement (can be enhanced with Jinja2)
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

        # Write to temp file
        processed_path = Path(tempfile.gettempdir()) / template_path.name
        processed_path.write_text(content)

        return processed_path

    # Resource deployment methods

    def _deploy_resources(
        self, context: DeploymentContext, artifacts: List[Path], target_path: Path
    ) -> List[Path]:
        """Deploy generic resources."""
        deployed = []

        for artifact in artifacts:
            if artifact.is_file():
                dest = (
                    target_path / artifact.name if target_path.is_dir() else target_path
                )
                shutil.copy2(artifact, dest)
                deployed.append(dest)
            elif artifact.is_dir():
                if target_path.is_dir():
                    dest = target_path / artifact.name
                else:
                    dest = target_path
                shutil.copytree(artifact, dest, dirs_exist_ok=True)
                deployed.append(dest)

            self._logger.info(f"Deployed resource: {deployed[-1]}")

        return deployed
