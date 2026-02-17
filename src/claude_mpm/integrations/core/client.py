"""REST and GraphQL HTTP client for integrations (ISS-0010).

This module provides an async HTTP client for making API requests
to integrated services. Supports both REST and GraphQL APIs with
automatic authentication handling.

Example:
    async with IntegrationClient(manifest, credentials) as client:
        # REST request
        users = await client.rest_request("GET", "/users")

        # GraphQL request
        result = await client.graphql_request(
            "query { user(id: 1) { name } }"
        )

        # Call operation by name
        repos = await client.call_operation("list_repos", username="octocat")
"""

import base64
from typing import Any

import aiohttp

from .manifest import IntegrationManifest, Operation


class IntegrationClientError(Exception):
    """Base exception for integration client errors."""


class AuthenticationError(IntegrationClientError):
    """Authentication failed."""


class APIError(IntegrationClientError):
    """API returned an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class IntegrationClient:
    """HTTP client for REST and GraphQL APIs.

    Provides methods for making authenticated API requests based on
    an integration manifest. Supports REST (GET, POST, PUT, DELETE)
    and GraphQL (query, mutation) operations.

    Attributes:
        manifest: Integration manifest defining the API.
        credentials: Dictionary of credential name -> value.
    """

    def __init__(
        self,
        manifest: IntegrationManifest,
        credentials: dict[str, str],
    ) -> None:
        """Initialize the integration client.

        Args:
            manifest: Integration manifest defining the API.
            credentials: Dictionary of credential name -> value.
        """
        self.manifest = manifest
        self.credentials = credentials
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "IntegrationClient":
        """Enter async context manager."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_auth_headers(self) -> dict[str, str]:
        """Build authentication headers based on auth type.

        Returns:
            Dictionary of authentication headers.

        Raises:
            AuthenticationError: If required credentials are missing.
        """
        headers: dict[str, str] = {}
        auth = self.manifest.auth

        if auth.type == "none":
            return headers

        if auth.type == "bearer":
            # Find bearer token credential
            for cred in auth.credentials:
                if cred.name in self.credentials:
                    headers["Authorization"] = f"Bearer {self.credentials[cred.name]}"
                    break
            else:
                raise AuthenticationError("Bearer token credential not found")

        elif auth.type == "api_key":
            # Find API key credential
            for cred in auth.credentials:
                if cred.name in self.credentials:
                    header_name = auth.header_name or "X-API-Key"
                    headers[header_name] = self.credentials[cred.name]
                    break
            else:
                raise AuthenticationError("API key credential not found")

        elif auth.type == "basic":
            # Find username and password credentials
            username = None
            password = None
            for cred in auth.credentials:
                value = self.credentials.get(cred.name)
                if value:
                    name_lower = cred.name.lower()
                    if "user" in name_lower or "name" in name_lower:
                        username = value
                    elif "pass" in name_lower or "secret" in name_lower:
                        password = value

            if not username or not password:
                raise AuthenticationError("Basic auth credentials incomplete")

            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    async def rest_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a REST API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            params: Query parameters.
            json: JSON request body.
            headers: Additional headers.

        Returns:
            Parsed JSON response.

        Raises:
            IntegrationClientError: If no session is active.
            APIError: If the API returns an error response.
        """
        if not self._session:
            raise IntegrationClientError(
                "Client not initialized. Use 'async with' context manager."
            )

        url = f"{self.manifest.base_url.rstrip('/')}{endpoint}"

        # Build headers
        request_headers = self._get_auth_headers()
        request_headers["Content-Type"] = "application/json"
        request_headers["Accept"] = "application/json"
        if headers:
            request_headers.update(headers)

        async with self._session.request(
            method,
            url,
            params=params,
            json=json,
            headers=request_headers,
        ) as response:
            # Handle error responses
            if response.status >= 400:
                try:
                    error_body = await response.json()
                except (aiohttp.ContentTypeError, ValueError):
                    error_body = await response.text()

                raise APIError(
                    f"API request failed: {response.status}",
                    status_code=response.status,
                    response_body=error_body,
                )

            # Parse successful response
            try:
                result: dict[str, Any] = await response.json()
                return result
            except (aiohttp.ContentTypeError, ValueError):
                # Return text wrapped in dict if not JSON
                text = await response.text()
                return {"response": text}

    async def graphql_request(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL request.

        Args:
            query: GraphQL query or mutation string.
            variables: Query variables.
            operation_name: Optional operation name.

        Returns:
            GraphQL response data.

        Raises:
            IntegrationClientError: If no session is active.
            APIError: If the API returns an error response.
        """
        if not self._session:
            raise IntegrationClientError(
                "Client not initialized. Use 'async with' context manager."
            )

        url = f"{self.manifest.base_url.rstrip('/')}/graphql"

        # Build request body
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        if operation_name:
            body["operationName"] = operation_name

        # Build headers
        request_headers = self._get_auth_headers()
        request_headers["Content-Type"] = "application/json"
        request_headers["Accept"] = "application/json"

        async with self._session.post(
            url,
            json=body,
            headers=request_headers,
        ) as response:
            result: dict[str, Any] = await response.json()

            # Check for GraphQL errors
            if result.get("errors"):
                error_messages = [e.get("message", str(e)) for e in result["errors"]]
                raise APIError(
                    f"GraphQL errors: {'; '.join(error_messages)}",
                    status_code=response.status,
                    response_body=result,
                )

            data: dict[str, Any] = result.get("data", result)
            return data

    async def call_operation(
        self,
        operation_name: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Call an operation by name with parameters.

        Args:
            operation_name: Name of the operation to call.
            **params: Operation parameters.

        Returns:
            Operation response data.

        Raises:
            IntegrationClientError: If operation not found.
            APIError: If the API returns an error response.
        """
        operation = self.manifest.get_operation(operation_name)
        if not operation:
            raise IntegrationClientError(f"Operation not found: {operation_name}")

        # Build parameters from operation definition
        operation_params = self._build_operation_params(operation, params)

        # Call appropriate method based on operation type
        if operation.type == "rest_get":
            endpoint = self._interpolate_endpoint(operation.endpoint or "", params)
            return await self.rest_request("GET", endpoint, params=operation_params)

        if operation.type == "rest_post":
            endpoint = self._interpolate_endpoint(operation.endpoint or "", params)
            return await self.rest_request("POST", endpoint, json=operation_params)

        if operation.type == "rest_put":
            endpoint = self._interpolate_endpoint(operation.endpoint or "", params)
            return await self.rest_request("PUT", endpoint, json=operation_params)

        if operation.type == "rest_delete":
            endpoint = self._interpolate_endpoint(operation.endpoint or "", params)
            return await self.rest_request("DELETE", endpoint, params=operation_params)

        if operation.type in ("query", "mutation"):
            return await self.graphql_request(
                operation.query or "",
                variables=operation_params,
            )

        if operation.type == "script":
            raise IntegrationClientError("Script operations not yet supported")

        raise IntegrationClientError(f"Unknown operation type: {operation.type}")

    async def health_check(self) -> tuple[bool, str]:
        """Run health check and return status.

        Returns:
            Tuple of (success, message).
        """
        health = self.manifest.health
        if not health:
            return True, "No health check defined"

        try:
            result = await self.call_operation(
                health.operation,
                **health.params,
            )

            # Check expected values
            if health.expect:
                for key, expected in health.expect.items():
                    actual = self._get_nested_value(result, key)
                    if actual != expected:
                        return (
                            False,
                            f"Health check failed: {key}={actual}, expected {expected}",
                        )

            return True, "Health check passed"

        except IntegrationClientError as e:
            return False, f"Health check failed: {e}"
        except Exception as e:
            return False, f"Health check error: {e}"

    def _build_operation_params(
        self,
        operation: Operation,
        provided: dict[str, Any],
    ) -> dict[str, Any]:
        """Build operation parameters with defaults and validation.

        Args:
            operation: Operation definition.
            provided: User-provided parameters.

        Returns:
            Complete parameter dictionary.

        Raises:
            IntegrationClientError: If required parameter is missing.
        """
        result: dict[str, Any] = {}

        for param in operation.parameters:
            if param.name in provided:
                result[param.name] = self._coerce_param_type(
                    provided[param.name],
                    param.type,
                )
            elif param.default is not None:
                result[param.name] = param.default
            elif param.required:
                raise IntegrationClientError(
                    f"Missing required parameter: {param.name}"
                )

        # Include any extra parameters not in definition
        for key, value in provided.items():
            if key not in result:
                result[key] = value

        return result

    def _coerce_param_type(self, value: Any, param_type: str) -> Any:
        """Coerce parameter value to expected type.

        Args:
            value: Parameter value.
            param_type: Expected type name.

        Returns:
            Coerced value.
        """
        if param_type == "int":
            return int(value)
        if param_type == "float":
            return float(value)
        if param_type == "bool":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        if param_type == "string":
            return str(value)
        return value

    def _interpolate_endpoint(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> str:
        """Interpolate path parameters in endpoint.

        Args:
            endpoint: Endpoint template with {param} placeholders.
            params: Parameters for interpolation.

        Returns:
            Interpolated endpoint path.
        """
        result = endpoint
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def _get_nested_value(self, data: dict[str, Any], key: str) -> Any:
        """Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search.
            key: Dot-separated key path (e.g., "data.user.name").

        Returns:
            Value at key path, or None if not found.
        """
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
