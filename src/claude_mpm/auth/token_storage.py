"""Secure OAuth token storage with Fernet encryption and keyring.

This module provides encrypted persistence for OAuth tokens, using
the system keyring for encryption key storage and Fernet symmetric
encryption for the actual token data.

Security Features:
    - Encryption keys stored in system keyring (not on disk)
    - Fernet symmetric encryption for token data
    - File permissions restricted to owner only (600)
    - Credentials stored in user-specific directory
"""

import json
import stat
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import keyring
from cryptography.fernet import Fernet, InvalidToken

from claude_mpm.auth.models import OAuthToken, StoredToken, TokenMetadata, TokenStatus

# Keyring service identifier for encryption keys
KEYRING_SERVICE = "claude-mpm-oauth"

# Timeout for keyring operations (seconds)
KEYRING_TIMEOUT = 10.0

# TypeVar for generic return types in timeout wrapper
T = TypeVar("T")

# Default credentials directory
CREDENTIALS_DIR = Path.home() / ".claude-mpm" / "credentials"


class KeyringTimeoutError(Exception):
    """Raised when a keyring operation times out.

    This typically indicates the system keychain is locked or requires
    user authentication that isn't being provided.
    """

    def __init__(self, operation: str, timeout: float) -> None:
        """Initialize the timeout error.

        Args:
            operation: Description of the keyring operation that timed out.
            timeout: The timeout value in seconds.
        """
        message = (
            f"Keyring operation '{operation}' timed out after {timeout} seconds.\n"
            "This may indicate:\n"
            "  - The system keychain is locked\n"
            "  - Keychain authentication is required but not provided\n"
            "  - The keychain service is unresponsive\n\n"
            "To unlock your keychain, try running:\n"
            "  security unlock-keychain ~/Library/Keychains/login.keychain-db"
        )
        super().__init__(message)
        self.operation = operation
        self.timeout = timeout


def _keyring_with_timeout(
    func: Callable[..., T],
    args: tuple[Any, ...],
    operation: str,
    timeout: float = KEYRING_TIMEOUT,
) -> T:
    """Execute a keyring operation with a timeout.

    Keyring operations can hang indefinitely on macOS when the Keychain
    requires authentication or is unresponsive. This wrapper ensures
    operations either complete or fail within the specified timeout.

    Args:
        func: The keyring function to call.
        args: Arguments to pass to the function.
        operation: Description of the operation for error messages.
        timeout: Maximum time to wait in seconds.

    Returns:
        The result of the keyring function.

    Raises:
        KeyringTimeoutError: If the operation doesn't complete within timeout.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as err:
            raise KeyringTimeoutError(operation, timeout) from err


class TokenStorage:
    """Secure storage for OAuth tokens using Fernet encryption.

    Tokens are encrypted using Fernet symmetric encryption with keys
    stored securely in the system keyring. Token files are stored
    with restricted permissions (600) in the credentials directory.

    Attributes:
        credentials_dir: Directory where encrypted tokens are stored.

    Example:
        ```python
        storage = TokenStorage()

        # Store a token
        token = OAuthToken(
            access_token="abc123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["read", "write"]
        )
        metadata = TokenMetadata(service_name="github-mcp", provider="github")
        storage.store("github-mcp", token, metadata)

        # Retrieve the token
        stored = storage.retrieve("github-mcp")
        if stored:
            print(f"Token expires at: {stored.token.expires_at}")
        ```
    """

    def __init__(self, credentials_dir: Optional[Path] = None) -> None:
        """Initialize token storage.

        Args:
            credentials_dir: Custom directory for storing encrypted tokens.
                Defaults to ~/.claude-mpm/credentials/
        """
        self.credentials_dir = credentials_dir or CREDENTIALS_DIR
        self._ensure_credentials_dir()

    def _ensure_credentials_dir(self) -> None:
        """Create credentials directory with secure permissions if needed."""
        if not self.credentials_dir.exists():
            self.credentials_dir.mkdir(parents=True, mode=0o700)
        else:
            # Ensure directory has correct permissions
            self.credentials_dir.chmod(0o700)

    def _get_encryption_key(self, service_name: str) -> bytes:
        """Get or create the Fernet encryption key for a service.

        Keys are stored in the system keyring, not on disk.

        Args:
            service_name: Name of the service to get/create key for.

        Returns:
            Fernet encryption key as bytes.

        Raises:
            KeyringTimeoutError: If keyring operations time out.
        """
        key_name = f"{service_name}-key"
        existing_key = _keyring_with_timeout(
            keyring.get_password,
            (KEYRING_SERVICE, key_name),
            f"get_password for {service_name}",
        )

        if existing_key:
            return existing_key.encode()

        # Generate new key and store in keyring
        new_key = Fernet.generate_key()
        _keyring_with_timeout(
            keyring.set_password,
            (KEYRING_SERVICE, key_name, new_key.decode()),
            f"set_password for {service_name}",
        )
        return new_key

    def _delete_encryption_key(self, service_name: str) -> None:
        """Delete the encryption key for a service from keyring.

        Args:
            service_name: Name of the service to delete key for.

        Raises:
            KeyringTimeoutError: If the keyring operation times out.
        """
        key_name = f"{service_name}-key"
        try:
            _keyring_with_timeout(
                keyring.delete_password,
                (KEYRING_SERVICE, key_name),
                f"delete_password for {service_name}",
            )
        except keyring.errors.PasswordDeleteError:
            pass  # Key doesn't exist, nothing to delete

    def _get_token_path(self, service_name: str) -> Path:
        """Get the file path for a service's encrypted token.

        Args:
            service_name: Name of the service.

        Returns:
            Path to the encrypted token file.
        """
        # Sanitize service name for filesystem
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in service_name
        )
        return self.credentials_dir / f"{safe_name}.enc"

    def store(
        self,
        service_name: str,
        token: OAuthToken,
        metadata: TokenMetadata,
    ) -> None:
        """Store an OAuth token securely.

        The token is encrypted using Fernet symmetric encryption with
        a key stored in the system keyring. The encrypted data is
        written to a file with 600 permissions.

        Args:
            service_name: Unique identifier for the service.
            token: OAuth token data to store.
            metadata: Token metadata including provider info.
        """
        stored_token = StoredToken(
            version=1,
            metadata=metadata,
            token=token,
        )

        # Serialize to JSON
        token_json = stored_token.model_dump_json()

        # Encrypt the token data
        key = self._get_encryption_key(service_name)
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(token_json.encode())

        # Write encrypted data with secure permissions
        token_path = self._get_token_path(service_name)
        token_path.write_bytes(encrypted_data)

        # Set file permissions to owner read/write only (600)
        token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def retrieve(self, service_name: str) -> Optional[StoredToken]:
        """Retrieve a stored OAuth token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            StoredToken if found and valid, None otherwise.
        """
        token_path = self._get_token_path(service_name)

        if not token_path.exists():
            return None

        try:
            # Read encrypted data
            encrypted_data = token_path.read_bytes()

            # Decrypt
            key = self._get_encryption_key(service_name)
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)

            # Deserialize
            return StoredToken.model_validate_json(decrypted_data)

        except (InvalidToken, json.JSONDecodeError, ValueError):
            # Token is corrupted or invalid
            return None

    def delete(self, service_name: str) -> bool:
        """Delete a stored token and its encryption key.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            True if token was deleted, False if it didn't exist.
        """
        token_path = self._get_token_path(service_name)

        if not token_path.exists():
            return False

        # Delete the token file
        token_path.unlink()

        # Delete the encryption key from keyring
        self._delete_encryption_key(service_name)

        return True

    def list_services(self) -> list[str]:
        """List all services with stored tokens.

        Returns:
            List of service names that have stored tokens.
        """
        services = []
        for path in self.credentials_dir.glob("*.enc"):
            # Extract service name from filename
            service_name = path.stem
            services.append(service_name)
        return sorted(services)

    def get_status(self, service_name: str) -> TokenStatus:
        """Get the status of a stored token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            TokenStatus indicating the token's current state.
        """
        stored = self.retrieve(service_name)

        if stored is None:
            token_path = self._get_token_path(service_name)
            if token_path.exists():
                # File exists but couldn't be decrypted
                return TokenStatus.INVALID
            return TokenStatus.MISSING

        if stored.token.is_expired():
            return TokenStatus.EXPIRED

        return TokenStatus.VALID
