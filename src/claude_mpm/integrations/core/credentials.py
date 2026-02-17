"""Credential management for integrations (ISS-0009).

This module provides secure credential management with support for:
- Environment variables
- Project-level .env and .env.local files
- User-level ~/.claude-mpm/.env file
- Interactive credential prompting wizard

Credential priority (highest to lowest):
1. Environment variables
2. Project .env.local
3. Project .env
4. User .env (~/.claude-mpm/.env)
"""

import os
import re
from pathlib import Path
from typing import Literal

from .manifest import CredentialDefinition


class CredentialManager:
    """Manages credentials for integrations.

    Provides secure credential storage and retrieval with support for
    multiple scopes (project and user) and an interactive wizard for
    prompting missing credentials.

    Attributes:
        project_dir: Project directory for project-scoped credentials.
        user_env: Path to user-level .env file.
        project_env: Path to project-level .env file.
        project_env_local: Path to project-level .env.local file.
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize credential manager.

        Args:
            project_dir: Project directory. Defaults to current working directory.
        """
        self.project_dir = project_dir or Path.cwd()
        self.user_env = Path.home() / ".claude-mpm" / ".env"
        self.project_env = self.project_dir / ".env"
        self.project_env_local = self.project_dir / ".env.local"

    def get(self, name: str) -> str | None:
        """Get credential value.

        Priority: env > .env.local > .env > user .env

        Args:
            name: Credential/environment variable name.

        Returns:
            Credential value if found, None otherwise.
        """
        # 1. Check environment variable first
        value = os.environ.get(name)
        if value:
            return value

        # 2. Check project .env.local
        value = self._read_from_env_file(self.project_env_local, name)
        if value:
            return value

        # 3. Check project .env
        value = self._read_from_env_file(self.project_env, name)
        if value:
            return value

        # 4. Check user .env
        value = self._read_from_env_file(self.user_env, name)
        if value:
            return value

        return None

    def set(
        self,
        name: str,
        value: str,
        scope: Literal["project", "user"] = "project",
    ) -> None:
        """Save credential to appropriate .env file.

        Args:
            name: Credential/environment variable name.
            value: Credential value to store.
            scope: Storage scope - 'project' uses .env.local, 'user' uses ~/.claude-mpm/.env.
        """
        if scope == "user":
            env_file = self.user_env
        else:
            # Use .env.local for project scope (gitignored by convention)
            env_file = self.project_env_local

        self._write_to_env_file(env_file, name, value)

    def prompt_missing(
        self,
        credentials: list[CredentialDefinition],
    ) -> dict[str, str]:
        """Interactive wizard to prompt for missing credentials.

        Args:
            credentials: List of credential definitions to check/prompt.

        Returns:
            Dictionary of credential name -> value pairs.
        """
        result: dict[str, str] = {}

        for cred in credentials:
            # Check if already available
            existing = self.get(cred.name)
            if existing:
                result[cred.name] = existing
                continue

            # Skip non-required credentials
            if not cred.required:
                continue

            # Prompt user
            print(f"\n{cred.prompt}")
            if cred.help:
                print(f"  Help: {cred.help}")

            value = self._prompt_credential(cred.name)
            if value:
                result[cred.name] = value

                # Ask where to store
                store_scope = self._prompt_storage_scope(cred.name)
                if store_scope:
                    self.set(cred.name, value, store_scope)

        return result

    def mask(self, value: str) -> str:
        """Mask credential for safe display.

        Shows first 4 and last 4 characters, masks middle with asterisks.

        Args:
            value: Credential value to mask.

        Returns:
            Masked credential string.
        """
        if not value:
            return ""

        if len(value) <= 8:
            return "*" * len(value)

        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

    def has_credential(self, name: str) -> bool:
        """Check if a credential is available.

        Args:
            name: Credential name to check.

        Returns:
            True if credential exists and has a value.
        """
        return self.get(name) is not None

    def get_all_credentials(
        self,
        credentials: list[CredentialDefinition],
    ) -> tuple[dict[str, str], list[str]]:
        """Get all credentials, returning found values and missing names.

        Args:
            credentials: List of credential definitions to retrieve.

        Returns:
            Tuple of (found credentials dict, list of missing credential names).
        """
        found: dict[str, str] = {}
        missing: list[str] = []

        for cred in credentials:
            value = self.get(cred.name)
            if value:
                found[cred.name] = value
            elif cred.required:
                missing.append(cred.name)

        return found, missing

    def _read_from_env_file(self, env_file: Path, name: str) -> str | None:
        """Read a specific variable from an .env file.

        Args:
            env_file: Path to .env file.
            name: Variable name to look up.

        Returns:
            Variable value if found, None otherwise.
        """
        if not env_file.exists():
            return None

        try:
            content = env_file.read_text(encoding="utf-8")
            # Parse .env format: NAME=value or NAME="value" or NAME='value'
            pattern = rf"^{re.escape(name)}=(.*)$"
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue

                match = re.match(pattern, line)
                if match:
                    value = match.group(1).strip()
                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    return value
        except OSError:
            pass

        return None

    def _write_to_env_file(self, env_file: Path, name: str, value: str) -> None:
        """Write or update a variable in an .env file.

        Args:
            env_file: Path to .env file.
            name: Variable name.
            value: Variable value.
        """
        # Ensure parent directory exists
        env_file.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        found = False

        # Read existing content
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.strip().startswith(f"{name}="):
                        # Update existing line
                        lines.append(f'{name}="{value}"')
                        found = True
                    else:
                        lines.append(line)
            except OSError:
                pass

        # Add new variable if not found
        if not found:
            lines.append(f'{name}="{value}"')

        # Write back
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _prompt_credential(self, name: str) -> str:
        """Prompt user for a credential value.

        Args:
            name: Credential name for display.

        Returns:
            User-provided value or empty string.
        """
        try:
            import getpass

            return getpass.getpass(f"  Enter {name}: ")
        except (ImportError, EOFError):
            # Fallback for non-interactive environments
            return ""

    def _prompt_storage_scope(self, name: str) -> Literal["project", "user"] | None:
        """Prompt user for credential storage scope.

        Args:
            name: Credential name for display.

        Returns:
            Selected scope or None if user declines storage.
        """
        try:
            print(f"\n  Where should {name} be stored?")
            print("    [1] Project (.env.local) - for this project only")
            print("    [2] User (~/.claude-mpm/.env) - for all projects")
            print("    [3] Don't save - keep in memory only")

            choice = input("  Choice [1]: ").strip()

            if choice == "2":
                return "user"
            if choice == "3":
                return None
            return "project"
        except (EOFError, KeyboardInterrupt):
            return "project"

    def delete(
        self,
        name: str,
        scope: Literal["project", "user", "all"] = "all",
    ) -> bool:
        """Delete a credential from .env files.

        Args:
            name: Credential name to delete.
            scope: Which scope(s) to delete from.

        Returns:
            True if credential was found and deleted.
        """
        deleted = False

        files_to_check = []
        if scope in ("project", "all"):
            files_to_check.extend([self.project_env, self.project_env_local])
        if scope in ("user", "all"):
            files_to_check.append(self.user_env)

        for env_file in files_to_check:
            if self._delete_from_env_file(env_file, name):
                deleted = True

        return deleted

    def _delete_from_env_file(self, env_file: Path, name: str) -> bool:
        """Delete a variable from an .env file.

        Args:
            env_file: Path to .env file.
            name: Variable name to delete.

        Returns:
            True if variable was found and deleted.
        """
        if not env_file.exists():
            return False

        try:
            content = env_file.read_text(encoding="utf-8")
            lines = []
            found = False

            for line in content.splitlines():
                if line.strip().startswith(f"{name}="):
                    found = True
                else:
                    lines.append(line)

            if found:
                env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

            return found
        except OSError:
            return False
