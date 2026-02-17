"""Tests for integration agent/skill generator."""

import pytest

from claude_mpm.integrations.core.generator import IntegrationGenerator
from claude_mpm.integrations.core.manifest import (
    AuthConfig,
    CredentialDefinition,
    IntegrationManifest,
    MCPConfig,
    Operation,
    OperationParameter,
)


class TestIntegrationGenerator:
    """Tests for IntegrationGenerator class."""

    @pytest.fixture
    def generator(self) -> IntegrationGenerator:
        """Create generator instance."""
        return IntegrationGenerator()

    @pytest.fixture
    def sample_manifest(self) -> IntegrationManifest:
        """Create sample manifest for testing."""
        return IntegrationManifest(
            name="github",
            version="1.0.0",
            description="GitHub API integration for repository management",
            api_type="rest",
            base_url="https://api.github.com",
            auth=AuthConfig(
                type="bearer",
                credentials=[
                    CredentialDefinition(
                        name="GITHUB_TOKEN",
                        prompt="Enter GitHub token",
                        help="Create at github.com/settings/tokens",
                    )
                ],
            ),
            operations=[
                Operation(
                    name="list_repos",
                    description="List repositories for a user",
                    type="rest_get",
                    endpoint="/users/{username}/repos",
                    parameters=[
                        OperationParameter(
                            name="username",
                            type="string",
                            required=True,
                            description="GitHub username",
                        ),
                        OperationParameter(
                            name="per_page",
                            type="int",
                            required=False,
                            default=30,
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
                Operation(
                    name="create_issue",
                    description="Create a new issue",
                    type="rest_post",
                    endpoint="/repos/{owner}/{repo}/issues",
                    parameters=[
                        OperationParameter(name="owner", type="string", required=True),
                        OperationParameter(name="repo", type="string", required=True),
                        OperationParameter(name="title", type="string", required=True),
                        OperationParameter(name="body", type="string", required=False),
                    ],
                ),
            ],
            mcp=MCPConfig(generate=True, tools=["list_repos", "get_repo"]),
            author="Test Author",
        )

    @pytest.fixture
    def graphql_manifest(self) -> IntegrationManifest:
        """Create GraphQL manifest for testing."""
        return IntegrationManifest(
            name="linear",
            version="1.0.0",
            description="Linear issue tracking integration",
            api_type="graphql",
            base_url="https://api.linear.app",
            auth=AuthConfig(
                type="api_key",
                credentials=[
                    CredentialDefinition(name="LINEAR_API_KEY", prompt="Enter key")
                ],
                header_name="Authorization",
            ),
            operations=[
                Operation(
                    name="list_issues",
                    description="List issues",
                    type="query",
                    query="query { issues { nodes { id title } } }",
                ),
            ],
        )

    def test_generate_agent_contains_frontmatter(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent has valid frontmatter."""
        content = generator.generate_agent(sample_manifest)

        assert content.startswith("---")
        assert "agent_id: github-integration" in content
        assert "name: Github Integration Agent" in content
        assert "category: integration" in content

    def test_generate_agent_contains_description(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent contains description."""
        content = generator.generate_agent(sample_manifest)

        assert "GitHub API integration for repository management" in content

    def test_generate_agent_contains_operations(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent lists operations."""
        content = generator.generate_agent(sample_manifest)

        assert "### list_repos" in content
        assert "### get_repo" in content
        assert "### create_issue" in content
        assert "List repositories for a user" in content

    def test_generate_agent_contains_parameters(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent lists operation parameters."""
        content = generator.generate_agent(sample_manifest)

        assert "`username`" in content
        assert "(required)" in content
        assert "(optional)" in content
        assert "default:" in content

    def test_generate_agent_contains_auth_info(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent contains auth information."""
        content = generator.generate_agent(sample_manifest)

        assert "bearer" in content.lower()
        assert "GITHUB_TOKEN" in content
        assert "github.com/settings/tokens" in content

    def test_generate_agent_rest_best_practices(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test agent has REST-specific best practices."""
        content = generator.generate_agent(sample_manifest)

        assert "pagination" in content.lower()
        assert "HTTP method" in content

    def test_generate_agent_graphql_best_practices(
        self, generator: IntegrationGenerator, graphql_manifest: IntegrationManifest
    ) -> None:
        """Test agent has GraphQL-specific best practices."""
        content = generator.generate_agent(graphql_manifest)

        assert "variable" in content.lower()
        assert "field" in content.lower()

    def test_generate_skill_contains_frontmatter(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test skill has valid frontmatter."""
        content = generator.generate_skill(sample_manifest)

        assert content.startswith("---")
        assert "name: github" in content
        assert "category: integration" in content

    def test_generate_skill_contains_operations(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test skill lists operations."""
        content = generator.generate_skill(sample_manifest)

        assert "### list_repos" in content
        assert "### get_repo" in content
        assert "List repositories" in content

    def test_generate_skill_contains_quick_reference(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test skill has quick reference table."""
        content = generator.generate_skill(sample_manifest)

        assert "| Operation |" in content
        assert "| `list_repos` |" in content
        assert "rest_get" in content

    def test_generate_skill_contains_examples(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test skill contains usage examples."""
        content = generator.generate_skill(sample_manifest)

        assert "Example:" in content
        assert "call_operation" in content

    def test_generate_skill_contains_troubleshooting(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test skill has troubleshooting section."""
        content = generator.generate_skill(sample_manifest)

        assert "Troubleshooting" in content
        assert "Authentication errors" in content

    def test_deploy_creates_files(
        self,
        generator: IntegrationGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path,
    ) -> None:
        """Test deploy creates agent and skill files."""
        agent_path, skill_path = generator.deploy(
            sample_manifest, tmp_path, scope="project"
        )

        assert agent_path.exists()
        assert skill_path.exists()
        assert agent_path.name == "github-integration.md"
        assert skill_path.name == "github.md"

    def test_deploy_project_scope(
        self,
        generator: IntegrationGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path,
    ) -> None:
        """Test deploy to project scope."""
        agent_path, skill_path = generator.deploy(
            sample_manifest, tmp_path, scope="project"
        )

        assert tmp_path in agent_path.parents
        assert tmp_path in skill_path.parents

    def test_deploy_user_scope(
        self,
        generator: IntegrationGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Test deploy to user scope."""
        # Mock home directory
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        agent_path, skill_path = generator.deploy(
            sample_manifest, tmp_path / "project", scope="user"
        )

        assert ".claude-mpm" in str(agent_path)
        assert ".claude-mpm" in str(skill_path)

    def test_deploy_content_matches_generate(
        self,
        generator: IntegrationGenerator,
        sample_manifest: IntegrationManifest,
        tmp_path,
    ) -> None:
        """Test deployed content matches generated content."""
        agent_path, skill_path = generator.deploy(
            sample_manifest, tmp_path, scope="project"
        )

        expected_agent = generator.generate_agent(sample_manifest)
        expected_skill = generator.generate_skill(sample_manifest)

        assert agent_path.read_text() == expected_agent
        assert skill_path.read_text() == expected_skill

    def test_generate_mcp_tools_disabled(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test MCP tools not generated when disabled."""
        sample_manifest.mcp.generate = False

        content = generator.generate_mcp_tools(sample_manifest)
        assert content == ""

    def test_generate_mcp_tools_filtered(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test MCP tools filtered by config."""
        content = generator.generate_mcp_tools(sample_manifest)

        # Should only include specified tools
        assert "github_list_repos" in content
        assert "github_get_repo" in content
        # create_issue not in mcp.tools list
        assert "github_create_issue" not in content

    def test_generate_mcp_tools_all_operations(
        self, generator: IntegrationGenerator, sample_manifest: IntegrationManifest
    ) -> None:
        """Test all operations when tools is None."""
        sample_manifest.mcp.tools = None

        content = generator.generate_mcp_tools(sample_manifest)

        assert "github_list_repos" in content
        assert "github_get_repo" in content
        assert "github_create_issue" in content

    def test_python_type_conversion(self, generator: IntegrationGenerator) -> None:
        """Test parameter type to Python type conversion."""
        assert generator._python_type("string") == "str"
        assert generator._python_type("int") == "int"
        assert generator._python_type("float") == "float"
        assert generator._python_type("bool") == "bool"
        assert generator._python_type("file") == "str"
        assert generator._python_type("unknown") == "Any"


class TestGeneratorNameFormatting:
    """Tests for name formatting in generator."""

    @pytest.fixture
    def generator(self) -> IntegrationGenerator:
        """Create generator instance."""
        return IntegrationGenerator()

    def test_display_name_with_hyphens(self, generator: IntegrationGenerator) -> None:
        """Test display name with hyphens."""
        manifest = IntegrationManifest(
            name="my-custom-api",
            version="1.0.0",
            description="Test",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(type="none"),
            operations=[],
        )

        content = generator.generate_agent(manifest)
        assert "My Custom Api Integration Agent" in content

    def test_display_name_with_underscores(
        self, generator: IntegrationGenerator
    ) -> None:
        """Test display name with underscores."""
        manifest = IntegrationManifest(
            name="my_custom_api",
            version="1.0.0",
            description="Test",
            api_type="rest",
            base_url="https://api.test.com",
            auth=AuthConfig(type="none"),
            operations=[],
        )

        content = generator.generate_agent(manifest)
        assert "My Custom Api Integration Agent" in content
