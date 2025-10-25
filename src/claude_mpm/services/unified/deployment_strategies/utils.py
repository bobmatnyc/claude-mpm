"""
Deployment Utilities
====================

Common utilities for deployment strategies, consolidating shared patterns
from 45+ deployment services to eliminate duplication.

This module reduces ~5000 LOC of duplicated utility functions across:
- Validation routines
- Artifact preparation
- Health checks
- Rollback operations
- Environment management
- Version control
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from claude_mpm.core.enums import HealthStatus, OperationResult
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


# Validation Utilities
# ====================


def validate_deployment_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate deployment configuration.

    Consolidates validation logic from multiple deployment services.

    Args:
        config: Deployment configuration

    Returns:
        List of validation errors
    """
    errors = []

    # Required fields
    required_fields = ["type", "source", "target"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Required field missing: {field}")

    # Type validation
    if "type" in config:
        valid_types = [
            "local",
            "vercel",
            "railway",
            "aws",
            "docker",
            "git",
            "agent",
            "config",
            "template",
            "resource",
        ]
        if config["type"] not in valid_types:
            errors.append(f"Invalid deployment type: {config['type']}")

    # Source/target validation
    if "source" in config:
        source_path = Path(config["source"])
        if not source_path.exists():
            errors.append(f"Source does not exist: {source_path}")

    # Version format validation
    if "version" in config and not validate_version_format(config["version"]):
        errors.append(f"Invalid version format: {config['version']}")

    # Environment variables validation
    if "env" in config:
        if not isinstance(config["env"], dict):
            errors.append("Environment variables must be a dictionary")
        else:
            for key, value in config["env"].items():
                if not isinstance(key, str):
                    errors.append(f"Environment variable key must be string: {key}")
                if not isinstance(value, (str, int, float, bool)):
                    errors.append(f"Invalid environment variable type for {key}")

    return errors


def validate_version_format(version: str) -> bool:
    """
    Validate version string format.

    Supports semantic versioning and date-based versions.

    Args:
        version: Version string

    Returns:
        True if valid format
    """
    import re

    # Semantic version pattern
    semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"

    # Date-based version pattern
    date_pattern = r"^\d{4}\.\d{2}\.\d{2}(\.\d+)?$"

    return bool(re.match(semver_pattern, version) or re.match(date_pattern, version))


def validate_path_security(path: Path, base_path: Path) -> bool:
    """
    Validate path doesn't escape base directory (path traversal prevention).

    Args:
        path: Path to validate
        base_path: Base directory path

    Returns:
        True if path is safe
    """
    try:
        resolved_path = path.resolve()
        resolved_base = base_path.resolve()
        return resolved_path.is_relative_to(resolved_base)
    except (ValueError, OSError):
        return False


# Artifact Preparation
# ====================


def prepare_deployment_artifact(
    source: Union[str, Path],
    artifact_type: str = "auto",
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Prepare deployment artifact from source.

    Consolidates artifact preparation from multiple services.

    Args:
        source: Source path
        artifact_type: Type of artifact (auto, zip, tar, directory)
        config: Additional configuration

    Returns:
        Tuple of (artifact_path, metadata)
    """
    source_path = Path(source)
    config = config or {}
    metadata = {
        "source": str(source_path),
        "type": artifact_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Auto-detect type
    if artifact_type == "auto":
        if source_path.is_file():
            artifact_type = "file"
        elif source_path.is_dir():
            artifact_type = "directory"
        else:
            raise ValueError(f"Source does not exist: {source_path}")

    # Prepare based on type
    artifact_dir = Path(tempfile.mkdtemp(prefix="deploy_artifact_"))

    if artifact_type == "zip":
        artifact_path = create_zip_artifact(source_path, artifact_dir)
        metadata["format"] = "zip"
    elif artifact_type == "tar":
        artifact_path = create_tar_artifact(source_path, artifact_dir)
        metadata["format"] = "tar.gz"
    elif artifact_type == "directory":
        artifact_path = artifact_dir / "content"
        if source_path.is_dir():
            shutil.copytree(source_path, artifact_path)
        else:
            artifact_path.mkdir(parents=True)
            shutil.copy2(source_path, artifact_path / source_path.name)
        metadata["format"] = "directory"
    else:  # file
        artifact_path = artifact_dir / source_path.name
        shutil.copy2(source_path, artifact_path)
        metadata["format"] = "file"

    # Add checksums
    metadata["checksum"] = calculate_checksum(artifact_path)
    metadata["size_bytes"] = get_size(artifact_path)

    return artifact_path, metadata


def create_zip_artifact(source: Path, output_dir: Path) -> Path:
    """Create ZIP artifact from source."""
    import zipfile

    zip_path = output_dir / f"{source.name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if source.is_file():
            zipf.write(source, source.name)
        else:
            for file_path in source.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source.parent)
                    zipf.write(file_path, arcname)

    return zip_path


def create_tar_artifact(source: Path, output_dir: Path) -> Path:
    """Create TAR.GZ artifact from source."""
    import tarfile

    tar_path = output_dir / f"{source.name}.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(source, arcname=source.name)

    return tar_path


# Health Check Utilities
# ======================


def verify_deployment_health(
    deployment_type: str,
    deployment_info: Dict[str, Any],
    checks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Perform health checks on deployment.

    Consolidates health check patterns from multiple services.

    Args:
        deployment_type: Type of deployment
        deployment_info: Deployment information
        checks: Specific checks to perform

    Returns:
        Health status dictionary
    """
    health = {
        "status": OperationResult.UNKNOWN,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "errors": [],
    }

    checks = checks or ["existence", "accessibility", "integrity"]

    try:
        # Existence check
        if "existence" in checks and "deployed_path" in deployment_info:
            path = Path(deployment_info["deployed_path"])
            health["checks"]["exists"] = path.exists()

        # Accessibility check
        if "accessibility" in checks and "deployment_url" in deployment_info:
            health["checks"]["accessible"] = check_url_accessibility(
                deployment_info["deployment_url"]
            )

        # Integrity check
        if "integrity" in checks and "checksum" in deployment_info:
            health["checks"]["integrity"] = verify_checksum(
                deployment_info.get("deployed_path"), deployment_info["checksum"]
            )

        # Service-specific checks
        if deployment_type == "docker":
            health["checks"]["container_running"] = check_docker_container(
                deployment_info.get("container_id")
            )
        elif deployment_type == "aws":
            health["checks"]["aws_status"] = check_aws_deployment(deployment_info)

        # Determine overall status
        if all(health["checks"].values()):
            health["status"] = HealthStatus.HEALTHY
        elif any(health["checks"].values()):
            health["status"] = HealthStatus.DEGRADED
        else:
            health["status"] = HealthStatus.UNHEALTHY

    except Exception as e:
        health["status"] = HealthStatus.UNKNOWN
        health["errors"].append(str(e))

    return health


def check_url_accessibility(url: str, timeout: int = 10) -> bool:
    """Check if URL is accessible."""
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status < 400
    except Exception:
        return False


def check_docker_container(container_id: Optional[str]) -> bool:
    """Check if Docker container is running."""
    if not container_id:
        return False

    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().lower() == "true"
    except Exception:
        return False


def check_aws_deployment(deployment_info: Dict[str, Any]) -> bool:
    """Check AWS deployment status."""
    # Simplified check - would use boto3 in production
    return deployment_info.get("aws_status") == "deployed"


# Rollback Utilities
# ==================


def rollback_deployment(
    deployment_type: str,
    deployment_info: Dict[str, Any],
    backup_info: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Rollback deployment to previous state.

    Consolidates rollback patterns from multiple services.

    Args:
        deployment_type: Type of deployment
        deployment_info: Current deployment information
        backup_info: Backup information for restoration

    Returns:
        True if rollback successful
    """
    try:
        if deployment_type == "local":
            return rollback_local_deployment(deployment_info, backup_info)
        if deployment_type == "docker":
            return rollback_docker_deployment(deployment_info)
        if deployment_type == "git":
            return rollback_git_deployment(deployment_info)
        logger.warning(f"No rollback strategy for type: {deployment_type}")
        return False

    except Exception as e:
        logger.error(f"Rollback failed: {e!s}")
        return False


def rollback_local_deployment(
    deployment_info: Dict[str, Any], backup_info: Optional[Dict[str, Any]] = None
) -> bool:
    """Rollback local filesystem deployment."""
    deployed_path = Path(deployment_info.get("deployed_path", ""))

    if deployed_path.exists():
        # Remove current deployment
        if deployed_path.is_file():
            deployed_path.unlink()
        else:
            shutil.rmtree(deployed_path)

    # Restore from backup if available
    if backup_info and "backup_path" in backup_info:
        backup_path = Path(backup_info["backup_path"])
        if backup_path.exists():
            if backup_path.is_file():
                shutil.copy2(backup_path, deployed_path)
            else:
                shutil.copytree(backup_path, deployed_path)
            return True

    return True


def rollback_docker_deployment(deployment_info: Dict[str, Any]) -> bool:
    """Rollback Docker deployment."""
    container_id = deployment_info.get("container_id")

    if container_id:
        # Stop and remove container
        subprocess.run(["docker", "stop", container_id], check=False)
        subprocess.run(["docker", "rm", container_id], check=False)

    # Restore previous container if specified
    if "previous_container" in deployment_info:
        subprocess.run(
            ["docker", "start", deployment_info["previous_container"]], check=True
        )

    return True


def rollback_git_deployment(deployment_info: Dict[str, Any]) -> bool:
    """Rollback Git-based deployment."""
    repo_path = Path(deployment_info.get("repo_path", ""))
    previous_commit = deployment_info.get("previous_commit")

    if repo_path.exists() and previous_commit:
        subprocess.run(["git", "checkout", previous_commit], cwd=repo_path, check=True)
        return True

    return False


# Version Management
# ==================


def get_version_info(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract version information from deployment.

    Args:
        path: Deployment path

    Returns:
        Version information dictionary
    """
    path = Path(path)
    version_info = {}

    # Check for version files
    version_files = [
        "VERSION",
        ".version",
        "version.txt",
        "package.json",
        "setup.py",
        "pyproject.toml",
    ]

    for version_file in version_files:
        file_path = path / version_file if path.is_dir() else path.parent / version_file

        if file_path.exists():
            if version_file == "package.json":
                with file_path.open() as f:
                    data = json.load(f)
                    version_info["version"] = data.get("version")
                    version_info["source"] = "package.json"
            elif version_file in ["setup.py", "pyproject.toml"]:
                # Simple regex extraction
                import re

                content = file_path.read_text()
                match = re.search(r'version\s*=\s*["\'](.*?)["\']', content)
                if match:
                    version_info["version"] = match.group(1)
                    version_info["source"] = version_file
            else:
                # Plain text version file
                version_info["version"] = file_path.read_text().strip()
                version_info["source"] = version_file

            if "version" in version_info:
                break

    return version_info


def update_version(
    path: Union[str, Path], new_version: str, create_backup: bool = True
) -> bool:
    """
    Update version in deployment.

    Args:
        path: Deployment path
        new_version: New version string
        create_backup: Whether to backup current version

    Returns:
        True if update successful
    """
    path = Path(path)
    version_file = path / ".version" if path.is_dir() else path.with_suffix(".version")

    try:
        # Backup current version
        if create_backup and version_file.exists():
            backup_file = version_file.with_suffix(".backup")
            shutil.copy2(version_file, backup_file)

        # Write new version
        version_file.write_text(
            f"{new_version}\n{datetime.now(timezone.utc).isoformat()}\n"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to update version: {e!s}")
        return False


# Checksum and Integrity
# ======================


def calculate_checksum(path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate checksum of file or directory.

    Args:
        path: Path to calculate checksum for
        algorithm: Hash algorithm to use

    Returns:
        Hex digest of checksum
    """
    path = Path(path)
    hasher = hashlib.new(algorithm)

    if path.is_file():
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
    elif path.is_dir():
        # Hash all files in directory
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                hasher.update(str(file_path.relative_to(path)).encode())
                with file_path.open("rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)

    return hasher.hexdigest()


def verify_checksum(
    path: Union[str, Path], expected_checksum: str, algorithm: str = "sha256"
) -> bool:
    """
    Verify checksum of file or directory.

    Args:
        path: Path to verify
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm to use

    Returns:
        True if checksum matches
    """
    try:
        actual_checksum = calculate_checksum(path, algorithm)
        return actual_checksum == expected_checksum
    except Exception:
        return False


def get_size(path: Union[str, Path]) -> int:
    """
    Get size of file or directory in bytes.

    Args:
        path: Path to measure

    Returns:
        Size in bytes
    """
    path = Path(path)

    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    return 0


# Environment Management
# =====================


def load_env_file(env_file: Union[str, Path]) -> Dict[str, str]:
    """
    Load environment variables from file.

    Args:
        env_file: Path to environment file

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file)

    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def merge_environments(*env_dicts: Dict[str, str]) -> Dict[str, str]:
    """
    Merge multiple environment dictionaries.

    Later dictionaries override earlier ones.

    Args:
        *env_dicts: Environment dictionaries to merge

    Returns:
        Merged environment dictionary
    """
    merged = {}
    for env_dict in env_dicts:
        if env_dict:
            merged.update(env_dict)
    return merged


def export_env_to_file(env_vars: Dict[str, str], output_file: Union[str, Path]) -> None:
    """
    Export environment variables to file.

    Args:
        env_vars: Environment variables
        output_file: Output file path
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        for key, value in env_vars.items():
            # Escape special characters in value
            if " " in value or '"' in value:
                value = f'"{value}"'
            f.write(f"{key}={value}\n")
