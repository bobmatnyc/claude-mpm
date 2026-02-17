"""Tests for integration manifest parsing and validation."""

import pytest
import yaml

from claude_mpm.integrations.core.manifest import (
    AuthConfig,
    CredentialDefinition,
    HealthCheck,
    IntegrationManifest,
    MCPConfig,
    Operation,
    OperationParameter,
)


class TestCredentialDefinition:
    """Tests for CredentialDefinition dataclass."""

    def test_from_dict_minimal(self) -> None:
        """Test creating credential from minimal dict."""
        data = {"name": "API_KEY", "prompt": "Enter API key"}
        cred = CredentialDefinition.from_dict(data)

        assert cred.name == "API_KEY"
        assert cred.prompt == "Enter API key"
        assert cred.help is None
        assert cred.required is True

    def test_from_dict_full(self) -> None:
        """Test creating credential from full dict."""
        data = {
            "name": "TOKEN",
            "prompt": "Enter token",
            "help": "Get from settings page",
            "required": False,
        }
        cred = CredentialDefinition.from_dict(data)

        assert cred.name == "TOKEN"
        assert cred.prompt == "Enter token"
        assert cred.help == "Get from settings page"
        assert cred.required is False


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_from_dict_bearer(self) -> None:
        """Test bearer auth config."""
        data = {
            "type": "bearer",
            "credentials": [{"name": "TOKEN", "prompt": "Enter token"}],
        }
        auth = AuthConfig.from_dict(data)

        assert auth.type == "bearer"
        assert len(auth.credentials) == 1
        assert auth.credentials[0].name == "TOKEN"
        assert auth.header_name is None

    def test_from_dict_api_key(self) -> None:
        """Test API key auth config with custom header."""
        data = {
            "type": "api_key",
            "credentials": [{"name": "API_KEY", "prompt": "Enter key"}],
            "header_name": "X-Custom-Key",
        }
        auth = AuthConfig.from_dict(data)

        assert auth.type == "api_key"
        assert auth.header_name == "X-Custom-Key"

    def test_from_dict_none(self) -> None:
        """Test no auth config."""
        data = {"type": "none"}
        auth = AuthConfig.from_dict(data)

        assert auth.type == "none"
        assert len(auth.credentials) == 0


class TestOperationParameter:
    """Tests for OperationParameter dataclass."""

    def test_from_dict_minimal(self) -> None:
        """Test parameter from minimal dict."""
        data = {"name": "user_id"}
        param = OperationParameter.from_dict(data)

        assert param.name == "user_id"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None
        assert param.description is None

    def test_from_dict_full(self) -> None:
        """Test parameter from full dict."""
        data = {
            "name": "limit",
            "type": "int",
            "required": False,
            "default": 10,
            "description": "Maximum results",
        }
        param = OperationParameter.from_dict(data)

        assert param.name == "limit"
        assert param.type == "int"
        assert param.required is False
        assert param.default == 10
        assert param.description == "Maximum results"


class TestOperation:
    """Tests for Operation dataclass."""

    def test_from_dict_rest_get(self) -> None:
        """Test REST GET operation."""
        data = {
            "name": "list_users",
            "description": "List all users",
            "type": "rest_get",
            "endpoint": "/users",
            "parameters": [{"name": "limit", "type": "int"}],
        }
        op = Operation.from_dict(data)

        assert op.name == "list_users"
        assert op.description == "List all users"
        assert op.type == "rest_get"
        assert op.endpoint == "/users"
        assert len(op.parameters) == 1

    def test_from_dict_graphql(self) -> None:
        """Test GraphQL query operation."""
        data = {
            "name": "get_user",
            "description": "Get user by ID",
            "type": "query",
            "query": "query GetUser($id: ID!) { user(id: $id) { name } }",
        }
        op = Operation.from_dict(data)

        assert op.name == "get_user"
        assert op.type == "query"
        assert op.query is not None
        assert "user(id: $id)" in op.query


class TestHealthCheck:
    """Tests for HealthCheck dataclass."""

    def test_from_dict(self) -> None:
        """Test health check config."""
        data = {
            "operation": "get_status",
            "params": {"verbose": True},
            "expect": {"status": "ok"},
        }
        health = HealthCheck.from_dict(data)

        assert health.operation == "get_status"
        assert health.params == {"verbose": True}
        assert health.expect == {"status": "ok"}


class TestMCPConfig:
    """Tests for MCPConfig dataclass."""

    def test_from_dict_defaults(self) -> None:
        """Test MCP config with defaults."""
        data = {}
        mcp = MCPConfig.from_dict(data)

        assert mcp.generate is True
        assert mcp.tools is None

    def test_from_dict_custom(self) -> None:
        """Test MCP config with custom values."""
        data = {"generate": False, "tools": ["list_users", "get_user"]}
        mcp = MCPConfig.from_dict(data)

        assert mcp.generate is False
        assert mcp.tools == ["list_users", "get_user"]


class TestIntegrationManifest:
    """Tests for IntegrationManifest dataclass."""

    @pytest.fixture
    def sample_manifest_dict(self) -> dict:
        """Sample manifest dictionary."""
        return {
            "name": "github",
            "version": "1.0.0",
            "description": "GitHub API integration",
            "api_type": "rest",
            "base_url": "https://api.github.com",
            "auth": {
                "type": "bearer",
                "credentials": [
                    {
                        "name": "GITHUB_TOKEN",
                        "prompt": "Enter GitHub token",
                        "help": "Create at github.com/settings/tokens",
                    }
                ],
            },
            "operations": [
                {
                    "name": "list_repos",
                    "description": "List repositories",
                    "type": "rest_get",
                    "endpoint": "/users/{username}/repos",
                    "parameters": [
                        {"name": "username", "type": "string", "required": True}
                    ],
                },
                {
                    "name": "get_repo",
                    "description": "Get repository details",
                    "type": "rest_get",
                    "endpoint": "/repos/{owner}/{repo}",
                },
            ],
            "health": {"operation": "list_repos", "params": {"username": "octocat"}},
            "mcp": {"generate": True, "tools": ["list_repos"]},
            "author": "Test Author",
            "repository": "https://github.com/test/repo",
        }

    def test_from_dict(self, sample_manifest_dict: dict) -> None:
        """Test creating manifest from dict."""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)

        assert manifest.name == "github"
        assert manifest.version == "1.0.0"
        assert manifest.description == "GitHub API integration"
        assert manifest.api_type == "rest"
        assert manifest.base_url == "https://api.github.com"
        assert manifest.auth.type == "bearer"
        assert len(manifest.operations) == 2
        assert manifest.health is not None
        assert manifest.health.operation == "list_repos"
        assert manifest.mcp.generate is True
        assert manifest.author == "Test Author"

    def test_from_yaml(self, tmp_path, sample_manifest_dict: dict) -> None:
        """Test creating manifest from YAML file."""
        yaml_path = tmp_path / "integration.yaml"
        yaml_path.write_text(yaml.dump(sample_manifest_dict))

        manifest = IntegrationManifest.from_yaml(yaml_path)

        assert manifest.name == "github"
        assert len(manifest.operations) == 2

    def test_from_yaml_file_not_found(self, tmp_path) -> None:
        """Test error when YAML file not found."""
        with pytest.raises(FileNotFoundError):
            IntegrationManifest.from_yaml(tmp_path / "nonexistent.yaml")

    def test_validate_valid_manifest(self, sample_manifest_dict: dict) -> None:
        """Test validation passes for valid manifest."""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert len(errors) == 0

    def test_validate_missing_name(self, sample_manifest_dict: dict) -> None:
        """Test validation fails for missing name."""
        sample_manifest_dict["name"] = ""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("name is required" in e for e in errors)

    def test_validate_no_operations(self, sample_manifest_dict: dict) -> None:
        """Test validation fails for no operations."""
        sample_manifest_dict["operations"] = []
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("operation is required" in e for e in errors)

    def test_validate_duplicate_operation_names(
        self, sample_manifest_dict: dict
    ) -> None:
        """Test validation fails for duplicate operation names."""
        sample_manifest_dict["operations"].append(sample_manifest_dict["operations"][0])
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("Duplicate operation name" in e for e in errors)

    def test_validate_rest_operation_missing_endpoint(
        self, sample_manifest_dict: dict
    ) -> None:
        """Test validation fails for REST operation without endpoint."""
        sample_manifest_dict["operations"][0]["endpoint"] = None
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("endpoint required" in e for e in errors)

    def test_validate_health_check_unknown_operation(
        self, sample_manifest_dict: dict
    ) -> None:
        """Test validation fails for health check referencing unknown operation."""
        sample_manifest_dict["health"]["operation"] = "nonexistent"
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("unknown operation" in e for e in errors)

    def test_validate_mcp_unknown_tool(self, sample_manifest_dict: dict) -> None:
        """Test validation fails for MCP config referencing unknown operation."""
        sample_manifest_dict["mcp"]["tools"] = ["nonexistent"]
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        errors = manifest.validate()

        assert any("unknown operation" in e for e in errors)

    def test_get_operation(self, sample_manifest_dict: dict) -> None:
        """Test getting operation by name."""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)

        op = manifest.get_operation("list_repos")
        assert op is not None
        assert op.name == "list_repos"

        op = manifest.get_operation("nonexistent")
        assert op is None

    def test_get_required_credentials(self, sample_manifest_dict: dict) -> None:
        """Test getting required credentials."""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        creds = manifest.get_required_credentials()

        assert len(creds) == 1
        assert creds[0].name == "GITHUB_TOKEN"

    def test_to_dict(self, sample_manifest_dict: dict) -> None:
        """Test converting manifest back to dict."""
        manifest = IntegrationManifest.from_dict(sample_manifest_dict)
        result = manifest.to_dict()

        assert result["name"] == "github"
        assert result["version"] == "1.0.0"
        assert len(result["operations"]) == 2


class TestManifestValidationAPITypes:
    """Tests for API type validation in manifests."""

    def test_validate_graphql_operation_on_rest_api(self) -> None:
        """Test validation fails for GraphQL op on REST API."""
        manifest = IntegrationManifest(
            name="test",
            version="1.0.0",
            description="Test",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(type="none"),
            operations=[
                Operation(
                    name="query_data",
                    description="Query data",
                    type="query",
                    query="{ data }",
                )
            ],
        )
        errors = manifest.validate()

        assert any("GraphQL operation type not allowed" in e for e in errors)

    def test_validate_rest_operation_on_graphql_api(self) -> None:
        """Test validation fails for REST op on GraphQL API."""
        manifest = IntegrationManifest(
            name="test",
            version="1.0.0",
            description="Test",
            api_type="graphql",
            base_url="https://api.test.com",
            auth=AuthConfig(type="none"),
            operations=[
                Operation(
                    name="get_data",
                    description="Get data",
                    type="rest_get",
                    endpoint="/data",
                )
            ],
        )
        errors = manifest.validate()

        assert any("REST operation type not allowed" in e for e in errors)
