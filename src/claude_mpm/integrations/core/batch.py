"""Batch script execution framework (Phase 3).

Provides a framework for running batch operations across multiple integrations
or performing bulk operations with full client access.
"""

from __future__ import annotations

import asyncio
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .client import IntegrationClient
from .credentials import CredentialManager
from .manifest import IntegrationManifest  # noqa: TC001 - used in dataclass field


@dataclass
class BatchContext:
    """Context passed to batch scripts during execution.

    Provides access to integration clients, credentials, and results.
    """

    manifest: IntegrationManifest
    client: IntegrationClient
    credentials: CredentialManager
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def log_result(self, operation: str, data: Any) -> None:
        """Log a result from batch execution.

        Args:
            operation: Name of the operation executed.
            data: Result data to log.
        """
        self.results.append({"operation": operation, "data": data})

    def log_error(self, message: str) -> None:
        """Log an error during batch execution.

        Args:
            message: Error message to log.
        """
        self.errors.append(message)


@dataclass
class BatchResult:
    """Result of batch script execution."""

    success: bool
    results: list[dict[str, Any]]
    errors: list[str]
    script_path: Path | None = None
    integration: str | None = None


class BatchRunner:
    """Executes batch scripts with integration context.

    Batch scripts are Python modules that receive a BatchContext
    and can perform bulk operations using the integration client.
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize batch runner.

        Args:
            project_dir: Project root directory for credential resolution.
        """
        self.project_dir = project_dir or Path.cwd()

    async def run_script(
        self,
        script_path: Path,
        manifest: IntegrationManifest,
        manifest_path: Path,
    ) -> BatchResult:
        """Run a batch script with integration context.

        The script must define an async function `run(ctx: BatchContext)`.

        Args:
            script_path: Path to the Python batch script.
            manifest: Integration manifest.
            manifest_path: Path to the manifest file.

        Returns:
            BatchResult with execution results.
        """
        if not script_path.exists():
            return BatchResult(
                success=False,
                results=[],
                errors=[f"Script not found: {script_path}"],
                script_path=script_path,
                integration=manifest.name,
            )

        # Load the script module
        try:
            module = self._load_module(script_path)
        except Exception as e:
            return BatchResult(
                success=False,
                results=[],
                errors=[f"Failed to load script: {e}"],
                script_path=script_path,
                integration=manifest.name,
            )

        # Verify it has a run function
        if not hasattr(module, "run"):
            return BatchResult(
                success=False,
                results=[],
                errors=["Script must define 'async def run(ctx: BatchContext)'"],
                script_path=script_path,
                integration=manifest.name,
            )

        # Set up credentials
        cred_manager = CredentialManager(self.project_dir)
        credentials, missing = cred_manager.get_all_credentials(
            manifest.auth.credentials
        )

        if missing:
            return BatchResult(
                success=False,
                results=[],
                errors=[f"Missing required credentials: {', '.join(missing)}"],
                script_path=script_path,
                integration=manifest.name,
            )

        # Create context and run
        async with IntegrationClient(manifest, credentials) as client:
            ctx = BatchContext(
                manifest=manifest,
                client=client,
                credentials=cred_manager,
            )

            try:
                await module.run(ctx)
            except Exception as e:
                ctx.log_error(f"Script execution failed: {e}")

        return BatchResult(
            success=len(ctx.errors) == 0,
            results=ctx.results,
            errors=ctx.errors,
            script_path=script_path,
            integration=manifest.name,
        )

    def _load_module(self, script_path: Path) -> Any:
        """Dynamically load a Python module from path.

        Args:
            script_path: Path to the Python file.

        Returns:
            Loaded module object.
        """
        spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {script_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    async def run_inline(
        self,
        func: Callable[[BatchContext], Any],
        manifest: IntegrationManifest,
        manifest_path: Path,
    ) -> BatchResult:
        """Run an inline async function as a batch operation.

        Args:
            func: Async function that receives BatchContext.
            manifest: Integration manifest.
            manifest_path: Path to the manifest file.

        Returns:
            BatchResult with execution results.
        """
        cred_manager = CredentialManager(self.project_dir)
        credentials, _ = cred_manager.get_all_credentials(manifest.auth.credentials)

        async with IntegrationClient(manifest, credentials) as client:
            ctx = BatchContext(
                manifest=manifest,
                client=client,
                credentials=cred_manager,
            )

            try:
                result = func(ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                ctx.log_error(f"Inline batch execution failed: {e}")

        return BatchResult(
            success=len(ctx.errors) == 0,
            results=ctx.results,
            errors=ctx.errors,
            integration=manifest.name,
        )

    async def run_bulk(
        self,
        script_path: Path,
        manifests: list[tuple[IntegrationManifest, Path]],
    ) -> list[BatchResult]:
        """Run a batch script across multiple integrations.

        Args:
            script_path: Path to the Python batch script.
            manifests: List of (manifest, manifest_path) tuples.

        Returns:
            List of BatchResult for each integration.
        """
        results: list[BatchResult] = []

        for manifest, manifest_path in manifests:
            result = await self.run_script(script_path, manifest, manifest_path)
            results.append(result)

        return results


# Example batch script template
BATCH_SCRIPT_TEMPLATE = '''"""Batch script for {integration_name}.

This script runs bulk operations using the integration client.
"""

from claude_mpm.integrations.core.batch import BatchContext


async def run(ctx: BatchContext) -> None:
    """Main batch execution function.

    Args:
        ctx: Batch context with client and credentials.
    """
    # Example: Fetch multiple items
    # for item_id in [1, 2, 3]:
    #     result = await ctx.client.call_operation("get_item", {{"id": item_id}})
    #     ctx.log_result("get_item", result)

    # Your batch logic here
    pass
'''
