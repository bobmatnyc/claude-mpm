"""Rclone integration manager for Google Drive operations.

This module provides a manager class for executing rclone operations
using OAuth tokens from the claude-mpm TokenStorage system.

The RcloneManager generates temporary rclone configuration files
using the existing OAuth tokens, enabling seamless integration
between the MCP server's authentication and rclone's file operations.

Example:
    >>> from claude_mpm.auth import TokenStorage
    >>> storage = TokenStorage()
    >>> manager = RcloneManager(storage, "google-workspace-mcp")
    >>> items = manager.list_json("Documents")
    >>> manager.cleanup()
"""

from __future__ import annotations

import json
import logging
import os
import subprocess  # nosec B404 - subprocess is required to execute rclone CLI
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claude_mpm.auth import TokenStorage

logger = logging.getLogger(__name__)

# Default remote name for Google Drive in rclone config
DEFAULT_REMOTE_NAME = "gdrive"


@dataclass
class RcloneConfig:
    """Configuration for rclone Google Drive remote.

    Holds the OAuth credentials and configuration needed to
    generate an rclone configuration file for Google Drive access.

    Attributes:
        remote_name: Name of the rclone remote (default: "gdrive").
        access_token: OAuth access token for API calls.
        refresh_token: OAuth refresh token for token renewal.
        token_expiry: Token expiration time in ISO format.
        client_id: Optional OAuth client ID.
        client_secret: Optional OAuth client secret.
    """

    remote_name: str = DEFAULT_REMOTE_NAME
    access_token: str = ""
    refresh_token: str = ""
    token_expiry: str = ""
    client_id: str = ""
    client_secret: str = ""
    extra_options: dict[str, str] = field(default_factory=dict)


class RcloneNotInstalledError(Exception):
    """Raised when rclone binary is not found on the system."""


class RcloneOperationError(Exception):
    """Raised when an rclone operation fails."""

    def __init__(self, message: str, returncode: int = 1, stderr: str = "") -> None:
        """Initialize with error details.

        Args:
            message: Error description.
            returncode: Process return code.
            stderr: Standard error output from rclone.
        """
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class RcloneManager:
    """Manager for rclone operations using MCP OAuth tokens.

    Generates temporary rclone configuration files from the OAuth tokens
    stored in TokenStorage, enabling Google Drive file operations without
    requiring a separate rclone authentication flow.

    Attributes:
        storage: TokenStorage instance for retrieving OAuth tokens.
        service_name: Name of the service in TokenStorage.
        remote_name: Name of the rclone remote (default: "gdrive").
    """

    def __init__(
        self,
        storage: TokenStorage,
        service_name: str,
        remote_name: str = DEFAULT_REMOTE_NAME,
    ) -> None:
        """Initialize the RcloneManager.

        Args:
            storage: TokenStorage instance for retrieving OAuth tokens.
            service_name: Service name used to retrieve tokens.
            remote_name: Name for the rclone remote (default: "gdrive").

        Raises:
            RcloneNotInstalledError: If rclone is not installed.
        """
        self.storage = storage
        self.service_name = service_name
        self.remote_name = remote_name
        self._config_file: str | None = None

        # Verify rclone is installed
        installed, version = self.check_rclone_installed()
        if not installed:
            raise RcloneNotInstalledError(
                "rclone is not installed. Install it from https://rclone.org/downloads/"
            )
        logger.info("Using rclone %s", version)

    @staticmethod
    def check_rclone_installed() -> tuple[bool, str]:
        """Check if rclone is installed and get its version.

        Returns:
            Tuple of (is_installed, version_string).
            If not installed, version_string will be empty.
        """
        try:
            result = subprocess.run(
                ["rclone", "version"],  # nosec B603 B607
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            # Parse version from first line: "rclone v1.65.0"
            version_line = result.stdout.split("\n")[0]
            version = version_line.split()[-1] if version_line else "unknown"
            return True, version
        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return False, ""

    def _generate_config_content(self, config: RcloneConfig) -> str:
        """Generate rclone configuration file content.

        Args:
            config: RcloneConfig with OAuth credentials.

        Returns:
            Configuration file content as string.
        """
        token_json = json.dumps(
            {
                "access_token": config.access_token,
                "token_type": "Bearer",
                "refresh_token": config.refresh_token,
                "expiry": config.token_expiry,
            }
        )

        lines = [
            f"[{config.remote_name}]",
            "type = drive",
            f"token = {token_json}",
        ]

        if config.client_id:
            lines.append(f"client_id = {config.client_id}")
        if config.client_secret:
            lines.append(f"client_secret = {config.client_secret}")

        # Add any extra options
        for key, value in config.extra_options.items():
            lines.append(f"{key} = {value}")

        return "\n".join(lines) + "\n"

    def _get_config_file(self) -> str:
        """Get or create a temporary rclone config file.

        Retrieves OAuth tokens from TokenStorage and generates
        a temporary configuration file for rclone.

        Returns:
            Path to the temporary config file.

        Raises:
            RuntimeError: If no OAuth tokens are available.
        """
        if self._config_file and Path(self._config_file).exists():
            return self._config_file

        stored = self.storage.retrieve(self.service_name)
        if not stored:
            raise RuntimeError(
                f"No OAuth tokens available for service '{self.service_name}'. "
                "Run 'google-workspace-mcp --setup' first."
            )

        token = stored.token

        # Build expiry string in RFC3339 format
        expiry_str = ""
        if token.expires_at:
            expiry_str = token.expires_at.isoformat()
            if not expiry_str.endswith("Z") and "+" not in expiry_str:
                expiry_str += "Z"

        config = RcloneConfig(
            remote_name=self.remote_name,
            access_token=token.access_token,
            refresh_token=token.refresh_token or "",
            token_expiry=expiry_str,
        )

        config_content = self._generate_config_content(config)

        # Create temp config file with restricted permissions
        fd, path = tempfile.mkstemp(suffix=".conf", prefix="rclone_mcp_")
        try:
            os.chmod(path, 0o600)  # Owner read/write only
            with os.fdopen(fd, "w") as f:
                f.write(config_content)
        except Exception:
            os.close(fd)
            if Path(path).exists():
                os.unlink(path)
            raise

        self._config_file = path
        logger.debug("Created temporary rclone config at %s", path)
        return path

    def _run_rclone(
        self,
        args: list[str],
        capture_output: bool = True,
        timeout: int | None = 300,
    ) -> subprocess.CompletedProcess[str]:
        """Run an rclone command with the managed config file.

        Args:
            args: Command arguments (without 'rclone' prefix).
            capture_output: Whether to capture stdout/stderr.
            timeout: Command timeout in seconds (default: 5 minutes).

        Returns:
            CompletedProcess with command results.

        Raises:
            RcloneOperationError: If the command fails.
        """
        config_path = self._get_config_file()
        cmd = ["rclone", "--config", config_path, *args]

        logger.debug("Running: %s", " ".join(cmd[:4]) + " ...")

        try:
            result = subprocess.run(  # nosec B603 - cmd is built internally, not from user input
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,  # We handle return code ourselves
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise RcloneOperationError(
                    f"rclone command failed: {error_msg}",
                    returncode=result.returncode,
                    stderr=result.stderr or "",
                )

            return result

        except subprocess.TimeoutExpired as e:
            raise RcloneOperationError(
                f"rclone command timed out after {timeout} seconds",
                returncode=-1,
            ) from e

    def list_json(
        self,
        path: str = "",
        recursive: bool = False,
        files_only: bool = False,
        include_hash: bool = False,
        max_depth: int = -1,
    ) -> list[dict[str, Any]]:
        """List directory contents as JSON.

        Uses rclone's lsjson command to get a structured listing
        of files and folders in Google Drive.

        Args:
            path: Drive path to list (default: root).
            recursive: Recursively list subdirectories.
            files_only: Only show files, not directories.
            include_hash: Include MD5 hash for each file.
            max_depth: Maximum recursion depth (-1 for unlimited).

        Returns:
            List of file/folder dictionaries with keys:
            - Path: Relative path
            - Name: File/folder name
            - Size: Size in bytes (-1 for directories)
            - MimeType: MIME type
            - ModTime: Modification time (ISO format)
            - IsDir: Whether this is a directory
            - ID: Google Drive file ID
        """
        remote_path = f"{self.remote_name}:{path}"
        args = ["lsjson", remote_path]

        if recursive:
            args.append("--recursive")
        if files_only:
            args.append("--files-only")
        if include_hash:
            args.append("--hash")
        if max_depth >= 0:
            args.extend(["--max-depth", str(max_depth)])

        result = self._run_rclone(args)
        return json.loads(result.stdout) if result.stdout.strip() else []

    def download(
        self,
        drive_path: str,
        local_path: str,
        google_docs_format: str = "docx",
        exclude: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Download files from Google Drive to local filesystem.

        Uses rclone copy (not sync) so it doesn't delete local files.

        Args:
            drive_path: Path in Google Drive to download.
            local_path: Local destination directory.
            google_docs_format: Export format for Google Docs.
            exclude: Patterns to exclude from download.
            dry_run: Preview changes without downloading.

        Returns:
            Operation result with status and details.
        """
        remote_path = f"{self.remote_name}:{drive_path}"
        args = ["copy", remote_path, local_path, "--progress"]

        # Set export format for Google Docs
        args.extend(["--drive-export-formats", google_docs_format])

        if exclude:
            for pattern in exclude:
                args.extend(["--exclude", pattern])

        if dry_run:
            args.append("--dry-run")

        result = self._run_rclone(
            args, timeout=3600
        )  # 1 hour timeout for large downloads

        return {
            "status": "success" if result.returncode == 0 else "error",
            "operation": "download",
            "source": drive_path,
            "destination": local_path,
            "dry_run": dry_run,
            "output": result.stderr,  # rclone progress goes to stderr
        }

    def upload(
        self,
        local_path: str,
        drive_path: str,
        convert_to_google_docs: bool = False,
        exclude: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Upload files from local filesystem to Google Drive.

        Uses rclone copy (not sync) so it doesn't delete Drive files.

        Args:
            local_path: Local path to upload.
            drive_path: Destination path in Google Drive.
            convert_to_google_docs: Convert Office files to Google Docs format.
            exclude: Patterns to exclude from upload.
            dry_run: Preview changes without uploading.

        Returns:
            Operation result with status and details.
        """
        remote_path = f"{self.remote_name}:{drive_path}"
        args = ["copy", local_path, remote_path, "--progress"]

        if convert_to_google_docs:
            args.extend(
                ["--drive-import-formats", "docx,doc,odt,xlsx,xls,ods,pptx,ppt,odp"]
            )

        if exclude:
            for pattern in exclude:
                args.extend(["--exclude", pattern])

        if dry_run:
            args.append("--dry-run")

        result = self._run_rclone(
            args, timeout=3600
        )  # 1 hour timeout for large uploads

        return {
            "status": "success" if result.returncode == 0 else "error",
            "operation": "upload",
            "source": local_path,
            "destination": drive_path,
            "dry_run": dry_run,
            "output": result.stderr,
        }

    def sync(
        self,
        source: str,
        destination: str,
        delete_extra: bool = False,
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        dry_run: bool = True,  # Safe default
    ) -> dict[str, Any]:
        """Synchronize files between source and destination.

        Can sync in either direction:
        - Drive to local: source="drive:path", destination="/local/path"
        - Local to Drive: source="/local/path", destination="drive:path"

        Args:
            source: Source path (prefix with remote name for Drive).
            destination: Destination path (prefix with remote name for Drive).
            delete_extra: Delete files at destination not in source.
            exclude: Patterns to exclude.
            include: Patterns to include (if set, only matching files).
            dry_run: Preview changes without syncing (default: True).

        Returns:
            Operation result with status and details.
        """
        # Handle path prefixing for Drive paths
        if not source.startswith("/") and ":" not in source:
            source = f"{self.remote_name}:{source}"
        if not destination.startswith("/") and ":" not in destination:
            destination = f"{self.remote_name}:{destination}"

        # Use copy by default (safer), sync only if delete_extra is True
        operation = "sync" if delete_extra else "copy"
        args = [operation, source, destination, "--progress"]

        if exclude:
            for pattern in exclude:
                args.extend(["--exclude", pattern])

        if include:
            for pattern in include:
                args.extend(["--include", pattern])

        if dry_run:
            args.append("--dry-run")

        result = self._run_rclone(args, timeout=3600)

        return {
            "status": "success" if result.returncode == 0 else "error",
            "operation": operation,
            "source": source,
            "destination": destination,
            "delete_extra": delete_extra,
            "dry_run": dry_run,
            "output": result.stderr,
        }

    def cleanup(self) -> None:
        """Remove the temporary config file.

        Should be called when done with rclone operations
        to clean up sensitive credential data.
        """
        if self._config_file and Path(self._config_file).exists():
            try:
                # Overwrite before deleting for security
                with open(self._config_file, "w") as f:
                    f.write("# cleaned\n")
                os.unlink(self._config_file)
                logger.debug("Cleaned up temporary config at %s", self._config_file)
            except OSError as e:
                logger.warning("Failed to cleanup config file: %s", e)
            finally:
                self._config_file = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.cleanup()


def check_rclone_available() -> tuple[bool, str]:
    """Check if rclone is available on the system.

    Convenience function for checking rclone installation
    without creating an RcloneManager instance.

    Returns:
        Tuple of (is_installed, version_string).
    """
    return RcloneManager.check_rclone_installed()
