"""
Cloud Deployment Strategies
===========================

Consolidated cloud deployment strategies for Railway, AWS, Docker, and Git.
Reduces duplication by sharing common cloud deployment patterns.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.enums import OperationResult, ServiceState
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.unified.strategies import StrategyMetadata, StrategyPriority

from .base import DeploymentContext, DeploymentResult, DeploymentStrategy
from .utils import (
    check_docker_container,
    prepare_deployment_artifact,
    rollback_docker_deployment,
    verify_deployment_health,
)


class RailwayDeploymentStrategy(DeploymentStrategy):
    """Deploy to Railway platform."""

    def __init__(self):
        """Initialize Railway strategy."""
        super().__init__(
            StrategyMetadata(
                name="RailwayDeploymentStrategy",
                description="Deploy to Railway cloud platform",
                supported_types=["application", "service", "*"],
                supported_operations=["deploy", "rollback", "verify"],
                priority=StrategyPriority.NORMAL,
                tags={"railway", "cloud", "paas"},
            )
        )
        self._logger = get_logger(f"{__name__}.RailwayDeploymentStrategy")

    def validate(self, context: DeploymentContext) -> List[str]:
        """Validate Railway deployment."""
        errors = []

        # Check Railway CLI
        try:
            subprocess.run(["railway", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append(
                "Railway CLI not installed. Install with: npm i -g @railway/cli"
            )

        # Check authentication
        try:
            subprocess.run(["railway", "whoami"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append("Not authenticated with Railway. Run: railway login")

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """Prepare Railway artifacts."""
        artifact_path, _metadata = prepare_deployment_artifact(
            context.source, "directory", context.config
        )
        return [artifact_path]

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """Execute Railway deployment."""
        deploy_dir = artifacts[0] if artifacts else Path(context.source)

        cmd = ["railway", "up"]
        if context.config.get("service"):
            cmd.extend(["--service", context.config["service"]])
        if context.config.get("environment"):
            cmd.extend(["--environment", context.config["environment"]])

        try:
            result = subprocess.run(
                cmd, cwd=deploy_dir, capture_output=True, text=True, check=True
            )

            # Parse deployment URL from output
            deployment_url = None
            for line in result.stdout.split("\n"):
                if "https://" in line:
                    import re

                    match = re.search(r"https://[^\s]+", line)
                    if match:
                        deployment_url = match.group(0)
                        break

            return {
                "deployment_id": f"railway_{datetime.now(timezone.utc).timestamp()}",
                "deployment_url": deployment_url,
                "deployed_path": deploy_dir,
                "stdout": result.stdout,
            }
        except subprocess.CalledProcessError as e:
            raise Exception(f"Railway deployment failed: {e.stderr}") from e

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """Verify Railway deployment."""
        return (
            verify_deployment_health("railway", deployment_info, ["accessibility"])[
                "status"
            ]
            == "healthy"
        )

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """Railway doesn't support CLI rollback."""
        self._logger.warning("Railway rollback must be done via dashboard")
        return False

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get Railway deployment health."""
        return verify_deployment_health("railway", deployment_info)


class AWSDeploymentStrategy(DeploymentStrategy):
    """Deploy to AWS (Lambda, EC2, ECS)."""

    def __init__(self):
        """Initialize AWS strategy."""
        super().__init__(
            StrategyMetadata(
                name="AWSDeploymentStrategy",
                description="Deploy to AWS services",
                supported_types=["lambda", "ec2", "ecs", "application", "*"],
                supported_operations=["deploy", "rollback", "verify"],
                priority=StrategyPriority.NORMAL,
                tags={"aws", "cloud", "serverless"},
            )
        )
        self._logger = get_logger(f"{__name__}.AWSDeploymentStrategy")

    def validate(self, context: DeploymentContext) -> List[str]:
        """Validate AWS deployment."""
        errors = []

        # Check AWS CLI
        try:
            subprocess.run(["aws", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append("AWS CLI not installed")

        # Check credentials
        try:
            subprocess.run(
                ["aws", "sts", "get-caller-identity"], capture_output=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append("AWS credentials not configured")

        # Validate service type
        service = context.config.get("service", "lambda")
        if service not in ["lambda", "ec2", "ecs", "s3"]:
            errors.append(f"Unsupported AWS service: {service}")

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """Prepare AWS deployment artifacts."""
        service = context.config.get("service", "lambda")

        if service == "lambda":
            # Create ZIP for Lambda
            artifact_path, _ = prepare_deployment_artifact(
                context.source, "zip", context.config
            )
            return [artifact_path]
        artifact_path, _ = prepare_deployment_artifact(
            context.source, "directory", context.config
        )
        return [artifact_path]

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """Execute AWS deployment."""
        service = context.config.get("service", "lambda")

        if service == "lambda":
            return self._deploy_lambda(context, artifacts[0])
        if service == "s3":
            return self._deploy_s3(context, artifacts[0])
        raise NotImplementedError(f"AWS {service} deployment not implemented")

    def _deploy_lambda(
        self, context: DeploymentContext, artifact: Path
    ) -> Dict[str, Any]:
        """Deploy AWS Lambda function."""
        function_name = context.config.get("function_name", artifact.stem)

        # Check if function exists
        try:
            subprocess.run(
                ["aws", "lambda", "get-function", "--function-name", function_name],
                capture_output=True,
                check=True,
            )
            # Update existing function
            cmd = [
                "aws",
                "lambda",
                "update-function-code",
                "--function-name",
                function_name,
                "--zip-file",
                f"fileb://{artifact}",
            ]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            # Create new function
            cmd = [
                "aws",
                "lambda",
                "create-function",
                "--function-name",
                function_name,
                "--runtime",
                context.config.get("runtime", "python3.9"),
                "--role",
                context.config.get("role"),
                "--handler",
                context.config.get("handler", "index.handler"),
                "--zip-file",
                f"fileb://{artifact}",
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)

        return {
            "deployment_id": response.get("FunctionArn"),
            "deployment_url": response.get("FunctionUrl"),
            "deployed_path": artifact,
            "function_arn": response.get("FunctionArn"),
        }

    def _deploy_s3(self, context: DeploymentContext, artifact: Path) -> Dict[str, Any]:
        """Deploy to S3 bucket."""
        bucket = context.config.get("bucket")
        prefix = context.config.get("prefix", "")

        cmd = ["aws", "s3", "sync", str(artifact), f"s3://{bucket}/{prefix}"]
        subprocess.run(cmd, check=True)

        return {
            "deployment_id": f"s3://{bucket}/{prefix}",
            "deployment_url": f"https://{bucket}.s3.amazonaws.com/{prefix}",
            "deployed_path": artifact,
        }

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """Verify AWS deployment."""
        service = context.config.get("service", "lambda")

        if service == "lambda" and "function_arn" in deployment_info:
            try:
                cmd = [
                    "aws",
                    "lambda",
                    "get-function",
                    "--function-name",
                    deployment_info["function_arn"],
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                return False

        return True

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """Rollback AWS deployment."""
        # AWS Lambda supports versioning for rollback
        if context.config.get("service") == "lambda" and result.previous_version:
            function_name = context.config.get("function_name")
            cmd = [
                "aws",
                "lambda",
                "update-alias",
                "--function-name",
                function_name,
                "--name",
                "PROD",
                "--function-version",
                result.previous_version,
            ]
            try:
                subprocess.run(cmd, check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                pass
        return False

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get AWS deployment health."""
        return verify_deployment_health("aws", deployment_info)


class DockerDeploymentStrategy(DeploymentStrategy):
    """Deploy using Docker containers."""

    def __init__(self):
        """Initialize Docker strategy."""
        super().__init__(
            StrategyMetadata(
                name="DockerDeploymentStrategy",
                description="Deploy using Docker containers",
                supported_types=["container", "application", "service", "*"],
                supported_operations=["deploy", "rollback", "verify", "stop"],
                priority=StrategyPriority.HIGH,
                tags={"docker", "container", "microservice"},
            )
        )
        self._logger = get_logger(f"{__name__}.DockerDeploymentStrategy")

    def validate(self, context: DeploymentContext) -> List[str]:
        """Validate Docker deployment."""
        errors = []

        # Check Docker
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append("Docker not installed or not running")

        # Check Dockerfile exists
        source_path = Path(context.source)
        if source_path.is_dir():
            dockerfile = source_path / "Dockerfile"
            if not dockerfile.exists():
                errors.append(f"No Dockerfile found in {source_path}")

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """Prepare Docker artifacts."""
        return [Path(context.source)]

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """Execute Docker deployment."""
        source_dir = artifacts[0] if artifacts[0].is_dir() else artifacts[0].parent
        image_name = context.config.get(
            "image_name", f"app_{datetime.now(timezone.utc).timestamp()}"
        )
        container_name = context.config.get("container_name", image_name)

        # Build image
        build_cmd = ["docker", "build", "-t", image_name, str(source_dir)]
        subprocess.run(build_cmd, check=True)

        # Stop existing container if exists
        subprocess.run(
            ["docker", "stop", container_name], capture_output=True, check=False
        )
        subprocess.run(
            ["docker", "rm", container_name], capture_output=True, check=False
        )

        # Run container
        run_cmd = ["docker", "run", "-d", "--name", container_name]

        # Add port mapping
        if "ports" in context.config:
            for port_map in context.config["ports"]:
                run_cmd.extend(["-p", port_map])

        # Add environment variables
        if "env" in context.config:
            for key, value in context.config["env"].items():
                run_cmd.extend(["-e", f"{key}={value}"])

        run_cmd.append(image_name)

        result = subprocess.run(run_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()

        return {
            "deployment_id": container_id[:12],
            "container_id": container_id,
            "image_name": image_name,
            "container_name": container_name,
            "deployed_path": source_dir,
        }

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """Verify Docker deployment."""
        return check_docker_container(deployment_info.get("container_id"))

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """Rollback Docker deployment."""
        return rollback_docker_deployment(result.to_dict())

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get Docker container health."""
        container_id = deployment_info.get("container_id")
        health = {"status": OperationResult.UNKNOWN, "container_id": container_id}

        if container_id:
            health["running"] = check_docker_container(container_id)
            health["status"] = (
                ServiceState.RUNNING if health["running"] else ServiceState.ERROR
            )

        return health


class GitDeploymentStrategy(DeploymentStrategy):
    """Deploy using Git (GitHub, GitLab)."""

    def __init__(self):
        """Initialize Git strategy."""
        super().__init__(
            StrategyMetadata(
                name="GitDeploymentStrategy",
                description="Deploy using Git repositories",
                supported_types=["repository", "code", "*"],
                supported_operations=["deploy", "rollback", "verify"],
                priority=StrategyPriority.NORMAL,
                tags={"git", "github", "gitlab", "version-control"},
            )
        )
        self._logger = get_logger(f"{__name__}.GitDeploymentStrategy")

    def validate(self, context: DeploymentContext) -> List[str]:
        """Validate Git deployment."""
        errors = []

        # Check Git
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            errors.append("Git not installed")

        # Check remote URL
        if not context.config.get("remote_url"):
            errors.append("Git remote URL required")

        return errors

    def prepare(self, context: DeploymentContext) -> List[Path]:
        """Prepare Git artifacts."""
        return [Path(context.source)]

    def execute(
        self, context: DeploymentContext, artifacts: List[Path]
    ) -> Dict[str, Any]:
        """Execute Git deployment."""
        source_dir = artifacts[0] if artifacts[0].is_dir() else artifacts[0].parent
        remote_url = context.config.get("remote_url")
        branch = context.config.get("branch", "main")

        # Initialize git if needed
        if not (source_dir / ".git").exists():
            subprocess.run(["git", "init"], cwd=source_dir, check=True)

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "deploy", remote_url],
            cwd=source_dir,
            capture_output=True,
            check=False,
        )

        # Add all files
        subprocess.run(["git", "add", "."], cwd=source_dir, check=True)

        # Commit
        commit_msg = context.config.get("commit_message", "Deploy via Claude MPM")
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=source_dir,
            capture_output=True,
            check=False,
        )

        # Push
        subprocess.run(
            ["git", "push", "-u", "deploy", branch], cwd=source_dir, check=True
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        return {
            "deployment_id": commit_hash[:8],
            "commit_hash": commit_hash,
            "remote_url": remote_url,
            "branch": branch,
            "deployed_path": source_dir,
        }

    def verify(
        self, context: DeploymentContext, deployment_info: Dict[str, Any]
    ) -> bool:
        """Verify Git deployment."""
        # Check if commit exists on remote
        try:
            subprocess.run(
                [
                    "git",
                    "ls-remote",
                    deployment_info.get("remote_url"),
                    deployment_info.get("commit_hash"),
                ],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False

    def rollback(self, context: DeploymentContext, result: DeploymentResult) -> bool:
        """Rollback Git deployment."""
        if result.previous_version:
            try:
                subprocess.run(
                    ["git", "checkout", result.previous_version],
                    cwd=result.deployed_path,
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        "push",
                        "--force",
                        "deploy",
                        f"{result.previous_version}:{context.config.get('branch', 'main')}",
                    ],
                    cwd=result.deployed_path,
                    check=True,
                )
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                pass
        return False

    def get_health_status(self, deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get Git deployment health."""
        return {
            "status": (
                ServiceState.RUNNING
                if deployment_info.get("commit_hash")
                else ServiceState.ERROR
            ),
            "commit": deployment_info.get("commit_hash", "unknown"),
            "branch": deployment_info.get("branch", "unknown"),
        }
