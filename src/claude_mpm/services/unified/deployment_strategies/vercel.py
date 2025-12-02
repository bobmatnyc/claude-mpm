"""
Vercel Deployment Strategy
==========================

Handles deployment to Vercel platform for serverless applications.
Consolidates Vercel deployment patterns from multiple services.
"""

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.enums import HealthStatus, OperationResult
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.unified.strategies import StrategyMetadata, StrategyPriority

from .base import DeploymentContext, DeploymentResult, DeploymentStrategy


class VercelDeploymentStrategy(DeploymentStrategy):
    """
    Strategy for Vercel platform deployments.

    Handles deployment of serverless functions, static sites, and
    full-stack applications to Vercel.

    Features:
    - Serverless function deployment
    - Static site deployment
    - Environment variable management
    - Custom domain configuration
    - Deployment previews
    - Production deployments
    - Rollback to previous deployments
    """

    def __init__(self):
        """Initialize Vercel deployment strategy."""
        metadata = StrategyMetadata(
            name="VercelDeploymentStrategy",
            description="Deploy to Vercel serverless platform",
            supported_types=["application", "service", "agent", "*"],
            supported_operations=["deploy", "rollback", "verify", "promote"],
            priority=StrategyPriority.NORMAL,
            tags={"vercel", "serverless", "cloud", "edge"},
        )
        super().__init__(metadata)
        self._logger = get_logger(f"{__name__}.VercelDeploymentStrategy")
        self._deployment_urls: Dict[str, str] = {}

    def validate(self, context: DeploymentContext) -> List[str]:
        """
        Validate Vercel deployment configuration.

        Args:
            context: Deployment context

        Returns:
            List of validation errors
        """
        errors = []

        # Check Vercel CLI is available
        if not self._check_vercel_cli():
            errors.append("Vercel CLI not found. Install with: npm i -g vercel")

        # Check authentication
        if not self._check_vercel_auth():
            errors.append("Not authenticated with Vercel. Run: vercel login")

        # Validate source
        source_path = Path(context.source)
        if not source_path.exists():
            errors.append(f"Source does not exist: {source_path}")

        # Check for Vercel configuration
        vercel_json = source_path / "vercel.json"
        if not vercel_json.exists():
            self._logger.warning("No vercel.json found, using defaults")

        # Validate required config
        config = context.config

        # Check project name
        if not config.get("project_name") and not vercel_json.exists():
            errors.append("Project name required when vercel.json is missing")

        # Validate environment variables
        env_vars = config.get("env", {})
        for key, value in env_vars.items():
            if not isinstance(value, (str, int, bool)):
                errors.append(f"Invalid env var type for {key}: {type(value)}")

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """
        Prepare Vercel deployment artifacts.

        Args:
            context: Deployment context

        Returns:
            List of prepared artifact paths
        """
        artifacts = []
        source_path = Path(context.source)

        # Create deployment directory
        deploy_dir = Path(tempfile.mkdtemp(prefix="vercel_deploy_"))

        # Copy source to deployment directory
        if source_path.is_file():
            # Single file deployment (e.g., serverless function)
            deploy_file = deploy_dir / source_path.name
            import shutil

            shutil.copy2(source_path, deploy_file)
            artifacts.append(deploy_file)
        else:
            # Directory deployment
            import shutil

            shutil.copytree(source_path, deploy_dir / "app", dirs_exist_ok=True)
            artifacts.append(deploy_dir / "app")

        # Create/update vercel.json if needed
        vercel_config = self._prepare_vercel_config(context, deploy_dir)
        if vercel_config:
            artifacts.append(vercel_config)

        # Prepare environment file
        env_file = self._prepare_env_file(context, deploy_dir)
        if env_file:
            artifacts.append(env_file)

        return artifacts

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """
        Execute Vercel deployment.

        Args:
            context: Deployment context
            artifacts: Prepared artifacts

        Returns:
            Deployment information
        """
        deployment_id = self._generate_deployment_id()

        # Find deployment directory
        deploy_dir = artifacts[0].parent if artifacts else Path(tempfile.gettempdir())

        # Build Vercel command
        cmd = ["vercel"]

        # Add project name if specified
        if context.config.get("project_name"):
            cmd.extend(["--name", context.config["project_name"]])

        # Production deployment or preview
        if context.config.get("production", False):
            cmd.append("--prod")

        # Skip confirmation
        cmd.append("--yes")

        # Add token if provided
        if context.config.get("token"):
            cmd.extend(["--token", context.config["token"]])

        # Execute deployment
        self._logger.info(f"Deploying to Vercel: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=deploy_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse deployment URL from output
            deployment_url = self._parse_deployment_url(result.stdout)

            if deployment_url:
                self._deployment_urls[deployment_id] = deployment_url
                self._logger.info(f"Deployment successful: {deployment_url}")

                return {
                    "deployment_id": deployment_id,
                    "deployment_url": deployment_url,
                    "deployed_path": deploy_dir,
                    "production": context.config.get("production", False),
                    "stdout": result.stdout,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            raise Exception("Could not parse deployment URL from Vercel output")

        except subprocess.CalledProcessError as e:
            self._logger.error(f"Vercel deployment failed: {e.stderr}")
            raise Exception(f"Deployment failed: {e.stderr}") from e

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """
        Verify Vercel deployment success.

        Args:
            context: Deployment context
            deployment_info: Deployment information

        Returns:
            True if deployment verified
        """
        deployment_url = deployment_info.get("deployment_url")

        if not deployment_url:
            self._logger.error("No deployment URL to verify")
            return False

        # Check deployment status via API or HTTP
        try:
            import urllib.request

            # Try to access the deployment
            with urllib.request.urlopen(deployment_url) as response:
                if response.status == 200:
                    self._logger.info(f"Deployment verified: {deployment_url}")
                    return True
                self._logger.error(f"Deployment returned status: {response.status}")
                return False

        except Exception as e:
            self._logger.error(f"Failed to verify deployment: {e!s}")
            # May still be building, check via CLI
            return self._check_deployment_status(deployment_info.get("deployment_id"))

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """
        Rollback Vercel deployment.

        Args:
            context: Deployment context
            result: Current deployment result

        Returns:
            True if rollback successful
        """
        try:
            # Vercel doesn't support direct rollback via CLI
            # Instead, we can promote a previous deployment

            if context.config.get("previous_deployment_id"):
                # Promote previous deployment
                cmd = [
                    "vercel",
                    "promote",
                    context.config["previous_deployment_id"],
                    "--yes",
                ]

                if context.config.get("token"):
                    cmd.extend(["--token", context.config["token"]])

                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                self._logger.info("Rolled back to previous deployment")
                return True

            self._logger.warning(
                "No previous deployment ID available for rollback. "
                "Manual rollback required via Vercel dashboard."
            )
            return False

        except Exception as e:
            self._logger.error(f"Rollback failed: {e!s}")
            return False

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get health status of Vercel deployment.

        Args:
            deployment_info: Deployment information

        Returns:
            Health status information
        """
        deployment_url = deployment_info.get("deployment_url")

        health = {
            "status": OperationResult.UNKNOWN,
            "deployment_url": deployment_url,
            "checks": {},
        }

        if not deployment_url:
            health["status"] = HealthStatus.UNHEALTHY
            health["error"] = "No deployment URL"
            return health

        try:
            import urllib.request

            # Check main deployment URL
            with urllib.request.urlopen(deployment_url) as response:
                health["checks"]["main_url"] = response.status == 200
                health["response_time_ms"] = response.info().get(
                    "X-Vercel-Trace", "N/A"
                )

            # Check functions if configured
            if deployment_info.get("functions"):
                for func_name in deployment_info["functions"]:
                    func_url = f"{deployment_url}/api/{func_name}"
                    try:
                        with urllib.request.urlopen(func_url) as response:
                            health["checks"][f"function_{func_name}"] = (
                                response.status < 500
                            )
                    except (urllib.error.URLError, OSError, TimeoutError):
                        health["checks"][f"function_{func_name}"] = False

            # Determine overall status
            if all(health["checks"].values()):
                health["status"] = HealthStatus.HEALTHY
            elif any(health["checks"].values()):
                health["status"] = HealthStatus.DEGRADED
            else:
                health["status"] = HealthStatus.UNHEALTHY

        except Exception as e:
            health["status"] = HealthStatus.UNHEALTHY
            health["error"] = str(e)

        return health

    # Private helper methods

    def _check_vercel_cli(self) -> bool:
        """Check if Vercel CLI is installed."""
        try:
            subprocess.run(
                ["vercel", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_vercel_auth(self) -> bool:
        """Check if authenticated with Vercel."""
        try:
            subprocess.run(
                ["vercel", "whoami"],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _prepare_vercel_config(
        self, context: DeploymentContext, deploy_dir: Path
    ) -> Optional[Path]:
        """Prepare vercel.json configuration."""
        config = context.config
        vercel_config = {}

        # Add project settings
        if config.get("project_name"):
            vercel_config["name"] = config["project_name"]

        # Add build settings
        if config.get("build_command"):
            vercel_config["buildCommand"] = config["build_command"]

        if config.get("output_directory"):
            vercel_config["outputDirectory"] = config["output_directory"]

        # Add functions configuration
        if config.get("functions"):
            vercel_config["functions"] = config["functions"]

        # Add routes/rewrites
        if config.get("rewrites"):
            vercel_config["rewrites"] = config["rewrites"]

        if config.get("redirects"):
            vercel_config["redirects"] = config["redirects"]

        # Add environment configuration
        if config.get("env"):
            vercel_config["env"] = config["env"]

        if vercel_config:
            config_path = deploy_dir / "vercel.json"
            with config_path.open("w") as f:
                json.dump(vercel_config, f, indent=2)
            return config_path

        return None

    def _prepare_env_file(
        self, context: DeploymentContext, deploy_dir: Path
    ) -> Optional[Path]:
        """Prepare environment variables file."""
        env_vars = context.config.get("env", {})

        if env_vars:
            env_file = deploy_dir / ".env"
            with env_file.open("w") as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            return env_file

        return None

    def _parse_deployment_url(self, output: str) -> Optional[str]:
        """Parse deployment URL from Vercel output."""
        # Look for URL patterns in output
        lines = output.split("\n")
        for line in lines:
            if "https://" in line:
                # Extract URL
                import re

                url_match = re.search(r"https://[^\s]+", line)
                if url_match:
                    return url_match.group(0)

        return None

    def _check_deployment_status(self, deployment_id: str) -> bool:
        """Check deployment status via Vercel CLI."""
        try:
            cmd = ["vercel", "inspect", deployment_id]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Check for ready state in output
            return "State: READY" in result.stdout or "ready" in result.stdout.lower()

        except subprocess.CalledProcessError:
            return False

    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID."""
        return f"vercel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(self) % 10000:04d}"
