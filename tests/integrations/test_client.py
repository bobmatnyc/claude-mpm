"""Tests for integration HTTP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.integrations.core.client import (
    APIError,
    AuthenticationError,
    IntegrationClient,
    IntegrationClientError,
)
from claude_mpm.integrations.core.manifest import (
    AuthConfig,
    CredentialDefinition,
    HealthCheck,
    IntegrationManifest,
    Operation,
    OperationParameter,
)


class TestIntegrationClient:
    """Tests for IntegrationClient class."""

    @pytest.fixture
    def rest_manifest(self) -> IntegrationManifest:
        """Create a REST API manifest for testing."""
        return IntegrationManifest(
            name="test-api",
            version="1.0.0",
            description="Test API",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(
                type="bearer",
                credentials=[CredentialDefinition(name="TOKEN", prompt="Enter token")],
            ),
            operations=[
                Operation(
                    name="list_items",
                    description="List items",
                    type="rest_get",
                    endpoint="/items",
                    parameters=[
                        OperationParameter(
                            name="limit",
                            type="int",
                            required=False,
                            default=10,
                        )
                    ],
                ),
                Operation(
                    name="get_item",
                    description="Get item by ID",
                    type="rest_get",
                    endpoint="/items/{item_id}",
                    parameters=[
                        OperationParameter(
                            name="item_id",
                            type="string",
                            required=True,
                        )
                    ],
                ),
                Operation(
                    name="create_item",
                    description="Create item",
                    type="rest_post",
                    endpoint="/items",
                    parameters=[
                        OperationParameter(name="name", type="string", required=True),
                        OperationParameter(name="value", type="int", required=True),
                    ],
                ),
            ],
            health=HealthCheck(
                operation="list_items",
                expect={"status": "ok"},
            ),
        )

    @pytest.fixture
    def graphql_manifest(self) -> IntegrationManifest:
        """Create a GraphQL API manifest for testing."""
        return IntegrationManifest(
            name="graphql-api",
            version="1.0.0",
            description="GraphQL API",
            api_type="graphql",
            base_url="https://api.graphql.com",
            auth=AuthConfig(
                type="api_key",
                credentials=[CredentialDefinition(name="API_KEY", prompt="Enter key")],
                header_name="X-API-Key",
            ),
            operations=[
                Operation(
                    name="get_user",
                    description="Get user by ID",
                    type="query",
                    query="query GetUser($id: ID!) { user(id: $id) { id name } }",
                    parameters=[
                        OperationParameter(name="id", type="string", required=True)
                    ],
                ),
            ],
        )

    @pytest.fixture
    def credentials(self) -> dict[str, str]:
        """Sample credentials."""
        return {
            "TOKEN": "test_token_123",  # pragma: allowlist secret
            "API_KEY": "api_key_456",  # pragma: allowlist secret
        }

    def test_get_auth_headers_bearer(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test bearer auth header generation."""
        client = IntegrationClient(rest_manifest, credentials)
        headers = client._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"

    def test_get_auth_headers_api_key(
        self, graphql_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test API key header generation."""
        client = IntegrationClient(graphql_manifest, credentials)
        headers = client._get_auth_headers()

        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "api_key_456"

    def test_get_auth_headers_basic(self) -> None:
        """Test basic auth header generation."""
        manifest = IntegrationManifest(
            name="test",
            version="1.0.0",
            description="Test",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(
                type="basic",
                credentials=[
                    CredentialDefinition(name="USERNAME", prompt="Enter user"),
                    CredentialDefinition(name="PASSWORD", prompt="Enter pass"),
                ],
            ),
            operations=[],
        )
        credentials = {
            "USERNAME": "user",
            "PASSWORD": "pass",  # pragma: allowlist secret
        }

        client = IntegrationClient(manifest, credentials)
        headers = client._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_get_auth_headers_none(self) -> None:
        """Test no auth headers."""
        manifest = IntegrationManifest(
            name="test",
            version="1.0.0",
            description="Test",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(type="none"),
            operations=[],
        )

        client = IntegrationClient(manifest, {})
        headers = client._get_auth_headers()

        assert headers == {}

    def test_get_auth_headers_missing_credential(
        self, rest_manifest: IntegrationManifest
    ) -> None:
        """Test error when credential is missing."""
        client = IntegrationClient(rest_manifest, {})

        with pytest.raises(AuthenticationError, match="credential not found"):
            client._get_auth_headers()

    def test_interpolate_endpoint(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test endpoint interpolation."""
        client = IntegrationClient(rest_manifest, credentials)

        result = client._interpolate_endpoint(
            "/items/{item_id}/details/{detail_id}",
            {"item_id": "123", "detail_id": "456"},
        )

        assert result == "/items/123/details/456"

    def test_build_operation_params_with_defaults(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test building operation params with defaults."""
        client = IntegrationClient(rest_manifest, credentials)
        operation = rest_manifest.get_operation("list_items")

        params = client._build_operation_params(operation, {})

        assert params == {"limit": 10}

    def test_build_operation_params_override_default(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test building operation params with override."""
        client = IntegrationClient(rest_manifest, credentials)
        operation = rest_manifest.get_operation("list_items")

        params = client._build_operation_params(operation, {"limit": 20})

        assert params == {"limit": 20}

    def test_build_operation_params_missing_required(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test error for missing required param."""
        client = IntegrationClient(rest_manifest, credentials)
        operation = rest_manifest.get_operation("get_item")

        with pytest.raises(IntegrationClientError, match="Missing required parameter"):
            client._build_operation_params(operation, {})

    def test_coerce_param_type_int(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test parameter type coercion for int."""
        client = IntegrationClient(rest_manifest, credentials)

        assert client._coerce_param_type("42", "int") == 42
        assert client._coerce_param_type(42, "int") == 42

    def test_coerce_param_type_bool(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test parameter type coercion for bool."""
        client = IntegrationClient(rest_manifest, credentials)

        assert client._coerce_param_type("true", "bool") is True
        assert client._coerce_param_type("false", "bool") is False
        assert client._coerce_param_type("1", "bool") is True
        assert client._coerce_param_type(True, "bool") is True

    def test_get_nested_value(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test getting nested values from dict."""
        client = IntegrationClient(rest_manifest, credentials)

        data = {"level1": {"level2": {"value": 42}}}

        assert client._get_nested_value(data, "level1.level2.value") == 42
        assert client._get_nested_value(data, "level1.level2") == {"value": 42}
        assert client._get_nested_value(data, "nonexistent") is None


@pytest.mark.asyncio
class TestIntegrationClientAsync:
    """Async tests for IntegrationClient."""

    @pytest.fixture
    def rest_manifest(self) -> IntegrationManifest:
        """Create REST manifest."""
        return IntegrationManifest(
            name="test-api",
            version="1.0.0",
            description="Test API",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(
                type="bearer",
                credentials=[CredentialDefinition(name="TOKEN", prompt="Enter token")],
            ),
            operations=[
                Operation(
                    name="list_items",
                    description="List items",
                    type="rest_get",
                    endpoint="/items",
                ),
            ],
            health=HealthCheck(
                operation="list_items",
                expect={"status": "ok"},
            ),
        )

    @pytest.fixture
    def credentials(self) -> dict[str, str]:
        """Sample credentials."""
        return {"TOKEN": "test_token"}

    async def test_context_manager(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test async context manager."""
        async with IntegrationClient(rest_manifest, credentials) as client:
            assert client._session is not None

        # Session should be closed after context exit
        assert client._session is None

    async def test_rest_request_without_session(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test error when calling without context manager."""
        client = IntegrationClient(rest_manifest, credentials)

        with pytest.raises(IntegrationClientError, match="not initialized"):
            await client.rest_request("GET", "/items")

    @patch("aiohttp.ClientSession")
    async def test_rest_request_success(
        self,
        mock_session_class,
        rest_manifest: IntegrationManifest,
        credentials: dict[str, str],
    ) -> None:
        """Test successful REST request."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"items": [1, 2, 3]})

        # Setup mock context manager
        mock_request = MagicMock()
        mock_request.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        async with IntegrationClient(rest_manifest, credentials) as client:
            result = await client.rest_request("GET", "/items")

        assert result == {"items": [1, 2, 3]}

    @patch("aiohttp.ClientSession")
    async def test_rest_request_error(
        self,
        mock_session_class,
        rest_manifest: IntegrationManifest,
        credentials: dict[str, str],
    ) -> None:
        """Test REST request error handling."""
        # Setup mock error response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": "Not found"})

        mock_request = MagicMock()
        mock_request.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        async with IntegrationClient(rest_manifest, credentials) as client:
            with pytest.raises(APIError) as exc_info:
                await client.rest_request("GET", "/items/999")

        assert exc_info.value.status_code == 404

    async def test_call_operation_not_found(
        self, rest_manifest: IntegrationManifest, credentials: dict[str, str]
    ) -> None:
        """Test calling nonexistent operation."""
        async with IntegrationClient(rest_manifest, credentials) as client:
            with pytest.raises(IntegrationClientError, match="Operation not found"):
                await client.call_operation("nonexistent_operation")
