"""Integration creation wizard (Phase 3).

Interactive wizard for creating new integration manifests with sensible defaults
and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()


@dataclass
class WizardState:
    """State collected during wizard execution."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    base_url: str = ""
    api_type: str = "rest"
    auth_type: str = "none"
    auth_header: str = "Authorization"
    credentials: list[dict[str, Any]] = field(default_factory=list)
    operations: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    health_check_path: str = ""
    author: str = ""
    repository: str = ""


class IntegrationWizard:
    """Interactive wizard for creating new integration manifests.

    Guides users through creating a complete integration.yaml file
    with validation and sensible defaults.
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize wizard.

        Args:
            output_dir: Directory to create integration in.
                       If None, uses current directory.
        """
        self.output_dir = output_dir or Path.cwd()
        self.state = WizardState()

    def run(self) -> Path | None:
        """Run the interactive wizard.

        Returns:
            Path to created integration.yaml, or None if cancelled.
        """
        console.print(
            Panel(
                "[bold blue]Integration Creation Wizard[/bold blue]\n"
                "Create a new API integration manifest",
                expand=False,
            )
        )

        try:
            # Step 1: Basic info
            if not self._collect_basic_info():
                return None

            # Step 2: API configuration
            if not self._collect_api_config():
                return None

            # Step 3: Authentication
            if not self._collect_auth_config():
                return None

            # Step 4: Operations
            if not self._collect_operations():
                return None

            # Step 5: Optional metadata
            self._collect_metadata()

            # Generate and write
            return self._write_manifest()

        except KeyboardInterrupt:
            console.print("\n[yellow]Wizard cancelled[/yellow]")
            return None

    def _collect_basic_info(self) -> bool:
        """Collect basic integration information.

        Returns:
            True if successful, False to cancel.
        """
        console.print("\n[bold]Step 1: Basic Information[/bold]")

        self.state.name = (
            Prompt.ask(
                "Integration name (lowercase, no spaces)",
                default="my-api",
            )
            .lower()
            .replace(" ", "-")
        )

        self.state.version = Prompt.ask(
            "Version",
            default="1.0.0",
        )

        self.state.description = Prompt.ask(
            "Description",
            default=f"{self.state.name} API integration",
        )

        return True

    def _collect_api_config(self) -> bool:
        """Collect API configuration.

        Returns:
            True if successful, False to cancel.
        """
        console.print("\n[bold]Step 2: API Configuration[/bold]")

        self.state.base_url = Prompt.ask(
            "Base URL (e.g., https://api.example.com/v1)",
        )

        if not self.state.base_url.startswith(("http://", "https://")):
            self.state.base_url = "https://" + self.state.base_url

        self.state.api_type = Prompt.ask(
            "API type",
            choices=["rest", "graphql", "hybrid"],
            default="rest",
        )

        return True

    def _collect_auth_config(self) -> bool:
        """Collect authentication configuration.

        Returns:
            True if successful, False to cancel.
        """
        console.print("\n[bold]Step 3: Authentication[/bold]")

        self.state.auth_type = Prompt.ask(
            "Authentication type",
            choices=["none", "api_key", "bearer", "basic"],
            default="api_key",
        )

        if self.state.auth_type == "none":
            return True

        if self.state.auth_type == "api_key":
            self.state.auth_header = Prompt.ask(
                "API key header name",
                default="X-API-Key",
            )

        # Collect credentials
        while True:
            console.print("\n[dim]Add credentials (API keys, tokens, etc.)[/dim]")

            cred_name = Prompt.ask(
                "Credential environment variable name (or 'done' to finish)",
                default="done" if self.state.credentials else "API_KEY",
            )

            if cred_name.lower() == "done":
                break

            cred_desc = Prompt.ask(
                f"Description for {cred_name}",
                default=f"Your {cred_name.replace('_', ' ').lower()}",
            )

            cred_required = Confirm.ask(
                f"Is {cred_name} required?",
                default=True,
            )

            self.state.credentials.append(
                {
                    "name": cred_name.upper(),
                    "description": cred_desc,
                    "required": cred_required,
                }
            )

        return True

    def _collect_operations(self) -> bool:
        """Collect API operations.

        Returns:
            True if successful, False to cancel.
        """
        console.print("\n[bold]Step 4: API Operations[/bold]")
        console.print("[dim]Define at least one API operation[/dim]")

        while True:
            op = self._collect_single_operation()
            if op:
                self.state.operations.append(op)
                console.print(f"[green]Added operation: {op['name']}[/green]")

            if not Confirm.ask(
                "Add another operation?", default=bool(not self.state.operations)
            ):
                break

        if not self.state.operations:
            console.print("[red]At least one operation is required[/red]")
            return False

        return True

    def _collect_single_operation(self) -> dict[str, Any] | None:
        """Collect a single operation definition.

        Returns:
            Operation dictionary or None.
        """
        name = Prompt.ask("Operation name (e.g., list_items, get_user)")
        if not name:
            return None

        description = Prompt.ask(
            "Description",
            default=f"Perform {name.replace('_', ' ')}",
        )

        if self.state.api_type in ("rest", "hybrid"):
            method = Prompt.ask(
                "HTTP method",
                choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
                default="GET",
            )

            path = Prompt.ask(
                "Path (e.g., /items, /users/{id})",
                default=f"/{name.split('_')[-1]}s",
            )

            op: dict[str, Any] = {
                "name": name,
                "description": description,
                "method": method,
                "path": path,
            }

            # Collect parameters
            if Confirm.ask("Add parameters?", default=False):
                op["parameters"] = self._collect_parameters(path)

            return op

        # GraphQL
        query_type = Prompt.ask(
            "Query type",
            choices=["query", "mutation"],
            default="query",
        )

        query = Prompt.ask(
            f"GraphQL {query_type}",
            default=f"{query_type} {{ {name} }}",
        )

        return {
            "name": name,
            "description": description,
            "type": query_type,
            "query": query,
        }

    def _collect_parameters(self, path: str) -> list[dict[str, Any]]:
        """Collect parameters for an operation.

        Args:
            path: Operation path to detect path parameters.

        Returns:
            List of parameter definitions.
        """
        parameters: list[dict[str, Any]] = []

        # Auto-detect path parameters
        import re

        path_params = re.findall(r"\{(\w+)\}", path)
        for param in path_params:
            parameters.append(
                {
                    "name": param,
                    "type": "string",
                    "required": True,
                    "in": "path",
                    "description": f"The {param}",
                }
            )

        # Collect additional parameters
        while Confirm.ask("Add a query/body parameter?", default=False):
            param_name = Prompt.ask("Parameter name")
            if not param_name:
                continue

            param_type = Prompt.ask(
                "Type",
                choices=["string", "integer", "boolean", "object", "array"],
                default="string",
            )

            param_in = Prompt.ask(
                "Location",
                choices=["query", "body", "header"],
                default="query",
            )

            param_required = Confirm.ask("Required?", default=False)

            param_desc = Prompt.ask(
                "Description",
                default=f"The {param_name.replace('_', ' ')}",
            )

            parameters.append(
                {
                    "name": param_name,
                    "type": param_type,
                    "required": param_required,
                    "in": param_in,
                    "description": param_desc,
                }
            )

        return parameters

    def _collect_metadata(self) -> None:
        """Collect optional metadata."""
        console.print("\n[bold]Step 5: Optional Metadata[/bold]")

        if Confirm.ask("Add health check endpoint?", default=True):
            self.state.health_check_path = Prompt.ask(
                "Health check path",
                default="/health",
            )

        if Confirm.ask("Add tags?", default=False):
            tags_str = Prompt.ask(
                "Tags (comma-separated)",
                default="api, rest",
            )
            self.state.tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        if Confirm.ask("Add author info?", default=False):
            self.state.author = Prompt.ask("Author name/email")
            self.state.repository = Prompt.ask(
                "Repository URL",
                default="",
            )

    def _write_manifest(self) -> Path:
        """Generate and write the manifest file.

        Returns:
            Path to the created manifest.
        """
        # Build manifest dictionary
        manifest: dict[str, Any] = {
            "name": self.state.name,
            "version": self.state.version,
            "description": self.state.description,
            "base_url": self.state.base_url,
        }

        # Auth section
        auth: dict[str, Any] = {"type": self.state.auth_type}
        if self.state.auth_type == "api_key":
            auth["header"] = self.state.auth_header

        manifest["auth"] = auth

        # Credentials
        if self.state.credentials:
            manifest["credentials"] = self.state.credentials

        # Operations
        manifest["operations"] = self.state.operations

        # Health check
        if self.state.health_check_path:
            manifest["health_check"] = {
                "path": self.state.health_check_path,
                "method": "GET",
                "expected_status": 200,
            }

        # Tags
        if self.state.tags:
            manifest["tags"] = self.state.tags

        # Author info
        if self.state.author:
            manifest["author"] = self.state.author
        if self.state.repository:
            manifest["repository"] = self.state.repository

        # Create output directory
        integration_dir = self.output_dir / self.state.name
        integration_dir.mkdir(parents=True, exist_ok=True)

        # Write manifest
        manifest_path = integration_dir / "integration.yaml"
        with manifest_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                manifest,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        console.print(f"\n[green]Created integration at: {manifest_path}[/green]")
        console.print("\n[dim]Next steps:[/dim]")
        console.print(f"  1. Review and edit: {manifest_path}")
        console.print(f"  2. Validate: mpm integrate validate {integration_dir}")
        console.print(f"  3. Install: mpm integrate add {self.state.name}")

        return manifest_path

    def from_template(self, template: dict[str, Any]) -> WizardState:
        """Initialize wizard state from a template dictionary.

        Args:
            template: Dictionary with pre-filled values.

        Returns:
            WizardState with template values.
        """
        state = WizardState()
        state.name = template.get("name", "")
        state.version = template.get("version", "1.0.0")
        state.description = template.get("description", "")
        state.base_url = template.get("base_url", "")
        state.api_type = template.get("api_type", "rest")

        auth = template.get("auth", {})
        state.auth_type = auth.get("type", "none")
        state.auth_header = auth.get("header", "Authorization")

        state.credentials = template.get("credentials", [])
        state.operations = template.get("operations", [])
        state.tags = template.get("tags", [])

        health = template.get("health_check", {})
        state.health_check_path = health.get("path", "")

        state.author = template.get("author", "")
        state.repository = template.get("repository", "")

        self.state = state
        return state

    def generate_from_state(self) -> Path:
        """Generate manifest from current state without interaction.

        Useful for programmatic creation.

        Returns:
            Path to created manifest.
        """
        return self._write_manifest()
