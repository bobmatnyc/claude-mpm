"""Integration manifest parser and validator (ISS-0008).

This module provides dataclasses for parsing integration.yaml manifest files
that define API integrations for the mpm-integrate feature.

Example manifest:
    name: github
    version: 1.0.0
    description: GitHub API integration
    api_type: rest
    base_url: https://api.github.com
    auth:
      type: bearer
      credentials:
        - name: GITHUB_TOKEN
          prompt: "Enter your GitHub personal access token"
    operations:
      - name: list_repos
        description: List repositories for a user
        type: rest_get
        endpoint: /users/{username}/repos
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class CredentialDefinition:
    """Definition of a credential required by the integration.

    Attributes:
        name: Environment variable name for the credential.
        prompt: User-facing prompt when requesting the credential.
        help: Optional help text explaining how to obtain the credential.
        required: Whether the credential is required (default True).
    """

    name: str
    prompt: str
    help: str | None = None
    required: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CredentialDefinition":
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            prompt=data["prompt"],
            help=data.get("help"),
            required=data.get("required", True),
        )


@dataclass
class AuthConfig:
    """Authentication configuration for the integration.

    Attributes:
        type: Authentication type (bearer, api_key, basic, none).
        credentials: List of credential definitions.
        header_name: Custom header name for api_key type (default X-API-Key).
    """

    type: Literal["bearer", "api_key", "basic", "none"]
    credentials: list[CredentialDefinition] = field(default_factory=list)
    header_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthConfig":
        """Create from dictionary representation."""
        credentials = [
            CredentialDefinition.from_dict(c) for c in data.get("credentials", [])
        ]
        return cls(
            type=data["type"],
            credentials=credentials,
            header_name=data.get("header_name"),
        )


@dataclass
class OperationParameter:
    """Parameter definition for an API operation.

    Attributes:
        name: Parameter name.
        type: Parameter data type.
        required: Whether the parameter is required.
        default: Default value if not provided.
        description: Human-readable description.
    """

    name: str
    type: Literal["string", "int", "float", "bool", "file"]
    required: bool = True
    default: Any = None
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OperationParameter":
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            type=data.get("type", "string"),
            required=data.get("required", True),
            default=data.get("default"),
            description=data.get("description"),
        )


@dataclass
class Operation:
    """API operation definition.

    Attributes:
        name: Unique operation identifier.
        description: Human-readable description.
        type: Operation type (rest_get, rest_post, query, mutation, etc).
        endpoint: REST endpoint path (for REST operations).
        query: GraphQL query string (for GraphQL operations).
        script: Batch script content (for script operations).
        parameters: List of operation parameters.
    """

    name: str
    description: str
    type: Literal[
        "rest_get",
        "rest_post",
        "rest_put",
        "rest_delete",
        "query",
        "mutation",
        "script",
    ]
    endpoint: str | None = None
    query: str | None = None
    script: str | None = None
    parameters: list[OperationParameter] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Operation":
        """Create from dictionary representation."""
        parameters = [
            OperationParameter.from_dict(p) for p in data.get("parameters", [])
        ]
        return cls(
            name=data["name"],
            description=data["description"],
            type=data["type"],
            endpoint=data.get("endpoint"),
            query=data.get("query"),
            script=data.get("script"),
            parameters=parameters,
        )


@dataclass
class HealthCheck:
    """Health check configuration for the integration.

    Attributes:
        operation: Name of the operation to use for health check.
        params: Parameters to pass to the health check operation.
        expect: Expected response values for a healthy check.
    """

    operation: str
    params: dict[str, Any] = field(default_factory=dict)
    expect: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthCheck":
        """Create from dictionary representation."""
        return cls(
            operation=data["operation"],
            params=data.get("params", {}),
            expect=data.get("expect", {}),
        )


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) configuration.

    Attributes:
        generate: Whether to generate MCP server tools.
        tools: List of operation names to expose as tools (None = all).
    """

    generate: bool = True
    tools: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPConfig":
        """Create from dictionary representation."""
        return cls(
            generate=data.get("generate", True),
            tools=data.get("tools"),
        )


@dataclass
class IntegrationManifest:
    """Complete integration manifest definition.

    Attributes:
        name: Integration identifier (e.g., 'github', 'linear').
        version: Semantic version of the integration.
        description: Human-readable description.
        api_type: Type of API (rest, graphql, hybrid).
        base_url: Base URL for API requests.
        auth: Authentication configuration.
        operations: List of available operations.
        health: Optional health check configuration.
        mcp: MCP tool generation configuration.
        author: Optional author information.
        repository: Optional repository URL.
    """

    name: str
    version: str
    description: str
    api_type: Literal["rest", "graphql", "hybrid"]
    base_url: str
    auth: AuthConfig
    operations: list[Operation]
    health: HealthCheck | None = None
    mcp: MCPConfig = field(default_factory=MCPConfig)
    author: str | None = None
    repository: str | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "IntegrationManifest":
        """Parse integration.yaml file into manifest.

        Args:
            path: Path to the integration.yaml file.

        Returns:
            Parsed IntegrationManifest instance.

        Raises:
            FileNotFoundError: If the manifest file doesn't exist.
            ValueError: If the manifest is invalid.
            yaml.YAMLError: If the YAML is malformed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntegrationManifest":
        """Create from dictionary representation.

        Args:
            data: Dictionary containing manifest data.

        Returns:
            Parsed IntegrationManifest instance.
        """
        auth = AuthConfig.from_dict(data["auth"])
        operations = [Operation.from_dict(op) for op in data.get("operations", [])]
        health = HealthCheck.from_dict(data["health"]) if data.get("health") else None
        mcp = MCPConfig.from_dict(data["mcp"]) if data.get("mcp") else MCPConfig()

        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            api_type=data["api_type"],
            base_url=data["base_url"],
            auth=auth,
            operations=operations,
            health=health,
            mcp=mcp,
            author=data.get("author"),
            repository=data.get("repository"),
        )

    def validate(self) -> list[str]:
        """Validate manifest and return list of errors.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors: list[str] = []

        # Required fields
        if not self.name:
            errors.append("name is required")
        if not self.version:
            errors.append("version is required")
        if not self.description:
            errors.append("description is required")
        if not self.base_url:
            errors.append("base_url is required")

        # Validate API type
        if self.api_type not in ("rest", "graphql", "hybrid"):
            errors.append(f"Invalid api_type: {self.api_type}")

        # Validate auth type
        if self.auth.type not in ("bearer", "api_key", "basic", "none"):
            errors.append(f"Invalid auth type: {self.auth.type}")

        # Validate operations
        if not self.operations:
            errors.append("At least one operation is required")

        operation_names = set()
        for op in self.operations:
            if op.name in operation_names:
                errors.append(f"Duplicate operation name: {op.name}")
            operation_names.add(op.name)

            # Validate operation type matches API type
            if self.api_type == "rest" and op.type in ("query", "mutation"):
                errors.append(
                    f"Operation {op.name}: GraphQL operation type not allowed for REST API"
                )
            if self.api_type == "graphql" and op.type.startswith("rest_"):
                errors.append(
                    f"Operation {op.name}: REST operation type not allowed for GraphQL API"
                )

            # Validate required fields for operation type
            if op.type.startswith("rest_") and not op.endpoint:
                errors.append(
                    f"Operation {op.name}: endpoint required for REST operations"
                )
            if op.type in ("query", "mutation") and not op.query:
                errors.append(
                    f"Operation {op.name}: query required for GraphQL operations"
                )

        # Validate health check references valid operation
        if self.health and self.health.operation not in operation_names:
            errors.append(
                f"Health check references unknown operation: {self.health.operation}"
            )

        # Validate MCP tools reference valid operations
        if self.mcp.tools:
            for tool in self.mcp.tools:
                if tool not in operation_names:
                    errors.append(f"MCP config references unknown operation: {tool}")

        return errors

    def get_operation(self, name: str) -> Operation | None:
        """Get operation by name.

        Args:
            name: Operation name to look up.

        Returns:
            Operation if found, None otherwise.
        """
        for op in self.operations:
            if op.name == name:
                return op
        return None

    def get_required_credentials(self) -> list[CredentialDefinition]:
        """Get list of required credentials.

        Returns:
            List of required credential definitions.
        """
        return [c for c in self.auth.credentials if c.required]

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary representation.

        Returns:
            Dictionary representation of the manifest.
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "api_type": self.api_type,
            "base_url": self.base_url,
            "auth": {
                "type": self.auth.type,
                "credentials": [
                    {
                        "name": c.name,
                        "prompt": c.prompt,
                        "help": c.help,
                        "required": c.required,
                    }
                    for c in self.auth.credentials
                ],
                "header_name": self.auth.header_name,
            },
            "operations": [
                {
                    "name": op.name,
                    "description": op.description,
                    "type": op.type,
                    "endpoint": op.endpoint,
                    "query": op.query,
                    "script": op.script,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required,
                            "default": p.default,
                            "description": p.description,
                        }
                        for p in op.parameters
                    ],
                }
                for op in self.operations
            ],
            "health": (
                {
                    "operation": self.health.operation,
                    "params": self.health.params,
                    "expect": self.health.expect,
                }
                if self.health
                else None
            ),
            "mcp": {
                "generate": self.mcp.generate,
                "tools": self.mcp.tools,
            },
            "author": self.author,
            "repository": self.repository,
        }
