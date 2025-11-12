"""API Key Validation Module for Claude MPM.

This module validates API keys for various services on startup to ensure
proper configuration and prevent runtime failures. It follows the principle
of failing fast with clear error messages rather than degrading gracefully.
"""

import os
from typing import Dict, List, Optional, Tuple

import requests

from claude_mpm.core.logger import get_logger


class APIKeyValidator:
    """Validates API keys for various services on framework startup."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the API validator.

        Args:
            config: Optional configuration dictionary
        """
        self.logger = get_logger("api_validator")
        self.config = config or {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all_keys(
        self, strict: bool = True
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate all configured API keys.

        Args:
            strict: If True, validation failures raise exceptions.
                   If False, failures are logged as warnings.

        Returns:
            Tuple of (success, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Check if validation is enabled
        if not self.config.get("validate_api_keys", True):
            self.logger.info("API key validation disabled in config")
            return True, [], []

        # Validate OpenAI key if configured
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self._validate_openai_key(openai_key)

        # Validate Anthropic key if configured
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self._validate_anthropic_key(anthropic_key)

        # Validate GitHub token if configured
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            self._validate_github_token(github_token)

        # Validate custom API keys from config
        custom_apis = self.config.get("custom_api_validations", {})
        for api_name, validation_config in custom_apis.items():
            self._validate_custom_api(api_name, validation_config)

        # Report results
        if self.errors:
            error_msg = "API Key Validation Failed:\n" + "\n".join(self.errors)
            if strict:
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            self.logger.warning(error_msg)

        if self.warnings:
            for warning in self.warnings:
                self.logger.warning(warning)

        if not self.errors:
            self.logger.info("✅ All configured API keys validated successfully")

        return not bool(self.errors), self.errors, self.warnings

    def _validate_openai_key(self, api_key: str) -> bool:
        """Validate OpenAI API key.

        Args:
            api_key: The OpenAI API key to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Make a lightweight request to validate the key
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )

            if response.status_code == 401:
                self.errors.append("❌ OpenAI API key is invalid (401 Unauthorized)")
                return False
            if response.status_code == 403:
                self.errors.append(
                    "❌ OpenAI API key lacks required permissions (403 Forbidden)"
                )
                return False
            if response.status_code == 429:
                # Rate limited but key is valid
                self.warnings.append("⚠️ OpenAI API key is valid but rate limited")
                return True
            if response.status_code == 200:
                self.logger.debug("✅ OpenAI API key validated successfully")
                return True
            self.warnings.append(
                f"⚠️ OpenAI API returned unexpected status: {response.status_code}"
            )
            return True  # Assume valid for unexpected status codes

        except requests.exceptions.Timeout:
            self.warnings.append(
                "⚠️ OpenAI API validation timed out - assuming key is valid"
            )
            return True
        except requests.exceptions.ConnectionError as e:
            self.warnings.append(f"⚠️ Could not connect to OpenAI API: {e}")
            return True
        except Exception as e:
            self.errors.append(f"❌ OpenAI API validation failed with error: {e}")
            return False

    def _validate_anthropic_key(self, api_key: str) -> bool:
        """Validate Anthropic API key.

        Args:
            api_key: The Anthropic API key to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Make a minimal request to validate the key
            # Using a very small max_tokens to minimize cost
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Use cheapest model
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1,
                },
                timeout=10,
            )

            if response.status_code == 401:
                self.errors.append("❌ Anthropic API key is invalid (401 Unauthorized)")
                return False
            if response.status_code == 403:
                self.errors.append(
                    "❌ Anthropic API key lacks required permissions (403 Forbidden)"
                )
                return False
            if response.status_code == 400:
                # Bad request but key is valid (we sent minimal request on purpose)
                self.logger.debug("✅ Anthropic API key validated successfully")
                return True
            if response.status_code == 429:
                # Rate limited but key is valid
                self.warnings.append("⚠️ Anthropic API key is valid but rate limited")
                return True
            if response.status_code == 200:
                self.logger.debug("✅ Anthropic API key validated successfully")
                return True
            self.warnings.append(
                f"⚠️ Anthropic API returned unexpected status: {response.status_code}"
            )
            return True

        except requests.exceptions.Timeout:
            self.warnings.append(
                "⚠️ Anthropic API validation timed out - assuming key is valid"
            )
            return True
        except requests.exceptions.ConnectionError as e:
            self.warnings.append(f"⚠️ Could not connect to Anthropic API: {e}")
            return True
        except Exception as e:
            self.errors.append(f"❌ Anthropic API validation failed with error: {e}")
            return False

    def _validate_github_token(self, token: str) -> bool:
        """Validate GitHub personal access token.

        Args:
            token: The GitHub token to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check token validity with minimal request
            response = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10,
            )

            if response.status_code == 401:
                self.errors.append("❌ GitHub token is invalid (401 Unauthorized)")
                return False
            if response.status_code == 403:
                self.errors.append(
                    "❌ GitHub token lacks required permissions (403 Forbidden)"
                )
                return False
            if response.status_code == 200:
                self.logger.debug("✅ GitHub token validated successfully")
                return True
            self.warnings.append(
                f"⚠️ GitHub API returned unexpected status: {response.status_code}"
            )
            return True

        except requests.exceptions.Timeout:
            self.warnings.append(
                "⚠️ GitHub API validation timed out - assuming token is valid"
            )
            return True
        except requests.exceptions.ConnectionError as e:
            self.warnings.append(f"⚠️ Could not connect to GitHub API: {e}")
            return True
        except Exception as e:
            self.errors.append(f"❌ GitHub token validation failed with error: {e}")
            return False

    def _validate_custom_api(self, api_name: str, validation_config: Dict) -> bool:
        """Validate a custom API key based on configuration.

        Args:
            api_name: Name of the API
            validation_config: Configuration for validating this API

        Returns:
            True if valid, False otherwise
        """
        try:
            env_var = validation_config.get("env_var")
            if not env_var:
                return True

            api_key = os.getenv(env_var)
            if not api_key:
                return True  # Not configured, skip validation

            # Get validation endpoint and method
            endpoint = validation_config.get("endpoint")
            method = validation_config.get("method", "GET").upper()
            headers = validation_config.get("headers", {})

            # Replace {API_KEY} placeholder in headers
            for key, value in headers.items():
                if isinstance(value, str):
                    headers[key] = value.replace("{API_KEY}", api_key)

            # Make validation request
            if method == "GET":
                response = requests.get(endpoint, headers=headers, timeout=10)
            elif method == "POST":
                body = validation_config.get("body", {})
                response = requests.post(
                    endpoint, headers=headers, json=body, timeout=10
                )
            else:
                self.warnings.append(
                    f"⚠️ Unsupported validation method for {api_name}: {method}"
                )
                return True

            # Check expected status codes
            valid_status_codes = validation_config.get("valid_status_codes", [200])
            if response.status_code in valid_status_codes:
                self.logger.debug(f"✅ {api_name} API key validated successfully")
                return True
            if response.status_code == 401:
                self.errors.append(
                    f"❌ {api_name} API key is invalid (401 Unauthorized)"
                )
                return False
            if response.status_code == 403:
                self.errors.append(
                    f"❌ {api_name} API key lacks permissions (403 Forbidden)"
                )
                return False
            self.warnings.append(
                f"⚠️ {api_name} API returned status: {response.status_code}"
            )
            return True

        except Exception as e:
            self.warnings.append(f"⚠️ {api_name} API validation failed: {e}")
            return True


def validate_api_keys(config: Optional[Dict] = None, strict: bool = True) -> bool:
    """Convenience function to validate all API keys.

    Args:
        config: Optional configuration dictionary
        strict: If True, raise exception on validation failure

    Returns:
        True if all validations passed, False otherwise

    Raises:
        ValueError: If strict=True and any validation fails
    """
    validator = APIKeyValidator(config)
    success, _errors, _warnings = validator.validate_all_keys(strict=strict)
    return success
