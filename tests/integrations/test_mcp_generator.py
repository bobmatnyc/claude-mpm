"""Tests for MCP server generator."""

import json
from pathlib import Path

import pytest

from claude_mpm.integrations.core.manifest import (
    AuthConfig,
    CredentialDefinition,
    IntegrationManifest,
    MCPConfig,
    Operation,
    OperationParameter,
)
from claude_mpm.integrations.core.mcp_generator import MCPServerGenerator


class TestMCPServerGenerator:
    """Tests for MCPServerGenerator class."""

    @pytest.fixture
    def generator(self) -> MCPServerGenerator:
        """Create generator instance."""
        return MCPServerGenerator()

    @pytest.fixture
    def sample_manifest(self) -> IntegrationManifest:
        """Create sample manifest for testing."""
        return IntegrationManifest(
            name="github",
            version="1.0.0",
            description="GitHub API integration",
            api_type="rest",
            base_url="https://api.github.com",
            auth=AuthConfig(
                type="bearer",
                credentials=[
                    CredentialDefinition(
                        name="GITHUB_TOKEN",
                        prompt="Enter GitHub token",
                    )
                ],
            ),
            operations=[
                Operation(
                    name="list_repos",
                    description="List repositories",
                    type="rest_get",
                    endpoint="/users/{username}/repos",
                    parameters=[
                        OperationParameter(
                            name="username",
                            type="string",
                            required=True,
                        ),
                    ],
                ),
                Operation(
                    name="get_repo",
                    description="Get repository details",
                    type="rest_get",
                    endpoint="/repos/{owner}/{repo}",
                    parameters=[
                        OperationParameter(name="owner", type="string", required=True),
                        OperationParameter(name="repo", type="string", required=True),
                    ],
                ),
            ],
            mcp=MCPConfig(generate=True, tools=["list_repos"]),
        )

    @pytest.fixture
    def no_mcp_manifest(self) -> IntegrationManifest:
        """Create manifest with MCP disabled."""
        return IntegrationManifest(
            name="simple",
            version="1.0.0",
            description="Simple API",
            api_type="rest",
            base_url="https://api.simple.com",
            auth=AuthConfig(type="none"),
            operations=[
                Operation(
                    name="get_data",
                    description="Get data",
                    type="rest_get",
                    endpoint="/data",
                ),
            ],
            mcp=MCPConfig(generate=False),
        )

    def test_generate_server_contains_imports(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has required imports."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert "from mcp.server import Server" in code
        assert "from mcp.server.stdio import stdio_server" in code
        assert "from mcp.types import TextContent, Tool" in code

    def test_generate_server_contains_manifest_path(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has correct manifest path."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert str(manifest_path.resolve()) in code

    def test_generate_server_contains_server_name(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has correct server name."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert 'SERVER_NAME = "github-integration"' in code

    def test_generate_server_contains_list_tools(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has list_tools handler."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert "@server.list_tools()" in code
        assert "async def list_tools()" in code

    def test_generate_server_contains_call_tool(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has call_tool handler."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert "@server.call_tool()" in code
        assert "async def call_tool(" in code

    def test_generate_server_contains_main(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test generated server has main function."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        code = generator.generate_server(sample_manifest, manifest_path)

        assert "async def main()" in code
        assert 'if __name__ == "__main__":' in code
        assert "asyncio.run(main())" in code

    def test_write_server_creates_file(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test write_server creates server file."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        server_path = generator.write_server(sample_manifest, manifest_path, tmp_path)

        assert server_path.exists()
        assert server_path.name == "github_mcp_server.py"

    def test_write_server_is_executable(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test written server file is executable."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        server_path = generator.write_server(sample_manifest, manifest_path, tmp_path)

        # Check executable bit is set
        assert server_path.stat().st_mode & 0o100

    def test_write_server_content_matches_generate(
        self,
        generator: MCPServerGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path: Path,
    ) -> None:
        """Test written content matches generated content."""
        manifest_path = tmp_path / "integration.yaml"
        manifest_path.touch()

        server_path = generator.write_server(sample_manifest, manifest_path, tmp_path)
        expected = generator.generate_server(sample_manifest, manifest_path)

        assert server_path.read_text() == expected


class TestMCPJsonRegistration:
    """Tests for .mcp.json registration."""

    @pytest.fixture
    def generator(self) -> MCPServerGenerator:
        """Create generator instance."""
        return MCPServerGenerator()

    def test_register_creates_new_file(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test registration creates .mcp.json if missing."""
        mcp_json_path = tmp_path / ".mcp.json"
        server_path = tmp_path / "server.py"
        server_path.touch()

        result = generator.register_with_mcp_json("test", server_path, mcp_json_path)

        assert result is True
        assert mcp_json_path.exists()

    def test_register_adds_server_entry(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test registration adds server entry."""
        mcp_json_path = tmp_path / ".mcp.json"
        server_path = tmp_path / "server.py"
        server_path.touch()

        generator.register_with_mcp_json("github", server_path, mcp_json_path)

        with mcp_json_path.open() as f:
            config = json.load(f)

        assert "github-integration" in config["mcpServers"]
        server_config = config["mcpServers"]["github-integration"]
        assert server_config["type"] == "stdio"
        assert server_config["command"] == "python"
        assert str(server_path.resolve()) in server_config["args"]

    def test_register_preserves_existing_servers(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test registration preserves existing server entries."""
        mcp_json_path = tmp_path / ".mcp.json"
        server_path = tmp_path / "server.py"
        server_path.touch()

        # Create existing config
        existing = {
            "mcpServers": {
                "existing-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                }
            }
        }
        with mcp_json_path.open("w") as f:
            json.dump(existing, f)

        generator.register_with_mcp_json("new", server_path, mcp_json_path)

        with mcp_json_path.open() as f:
            config = json.load(f)

        assert "existing-server" in config["mcpServers"]
        assert "new-integration" in config["mcpServers"]

    def test_unregister_removes_server(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test unregistration removes server entry."""
        mcp_json_path = tmp_path / ".mcp.json"

        # Create config with server
        config = {
            "mcpServers": {
                "test-integration": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["server.py"],
                }
            }
        }
        with mcp_json_path.open("w") as f:
            json.dump(config, f)

        result = generator.unregister_from_mcp_json("test", mcp_json_path)

        assert result is True
        with mcp_json_path.open() as f:
            updated = json.load(f)
        assert "test-integration" not in updated["mcpServers"]

    def test_unregister_returns_false_for_missing_file(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test unregistration returns False for missing file."""
        mcp_json_path = tmp_path / ".mcp.json"

        result = generator.unregister_from_mcp_json("test", mcp_json_path)

        assert result is False

    def test_unregister_returns_false_for_missing_server(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test unregistration returns False for missing server."""
        mcp_json_path = tmp_path / ".mcp.json"

        config = {"mcpServers": {"other-server": {}}}
        with mcp_json_path.open("w") as f:
            json.dump(config, f)

        result = generator.unregister_from_mcp_json("test", mcp_json_path)

        assert result is False

    def test_unregister_preserves_other_servers(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test unregistration preserves other server entries."""
        mcp_json_path = tmp_path / ".mcp.json"

        config = {
            "mcpServers": {
                "test-integration": {"type": "stdio"},
                "other-server": {"type": "stdio"},
            }
        }
        with mcp_json_path.open("w") as f:
            json.dump(config, f)

        generator.unregister_from_mcp_json("test", mcp_json_path)

        with mcp_json_path.open() as f:
            updated = json.load(f)
        assert "other-server" in updated["mcpServers"]


class TestGetServerPath:
    """Tests for get_server_path method."""

    @pytest.fixture
    def generator(self) -> MCPServerGenerator:
        """Create generator instance."""
        return MCPServerGenerator()

    def test_get_server_path_returns_correct_path(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test get_server_path returns expected path."""
        path = generator.get_server_path("github", tmp_path)

        assert path == tmp_path / "github_mcp_server.py"

    def test_get_server_path_handles_hyphenated_names(
        self, generator: MCPServerGenerator, tmp_path: Path
    ) -> None:
        """Test get_server_path handles hyphenated names."""
        path = generator.get_server_path("my-api", tmp_path)

        assert path == tmp_path / "my-api_mcp_server.py"
