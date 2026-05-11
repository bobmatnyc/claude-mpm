"""
Collection management handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages agent collection listing and deployment operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentCollectionsHandler:
    """Handles collection-based agent management commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def list_collections(self, args) -> CommandResult:
        """List all available agent collections.

        NEW: Shows all collections with agent counts and metadata.
        Enables discovery of available agent collections before deployment.
        """
        del args  # unused; method is dispatched uniformly via a table
        try:
            from pathlib import Path

            from ...services.agents.deployment.remote_agent_discovery_service import (
                RemoteAgentDiscoveryService,
            )

            # Get remote agents cache directory
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"

            if not cache_dir.exists():
                return CommandResult.error_result(
                    "No remote agent collections found. Run 'claude-mpm agents deploy' first."
                )

            # Use RemoteAgentDiscoveryService to list collections
            remote_service = RemoteAgentDiscoveryService(cache_dir)
            collections = remote_service.list_collections()

            if not collections:
                return CommandResult.success_result(
                    "No agent collections found in cache.", data={"collections": []}
                )

            # Format output
            output_lines = ["Available Agent Collections:\n"]
            for collection in collections:
                output_lines.append(
                    f"  • {collection['collection_id']} ({collection['agent_count']} agents)"
                )

            return CommandResult.success_result(
                "\n".join(output_lines), data={"collections": collections}
            )

        except Exception as e:
            self._logger.error(f"Error listing collections: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing collections: {e}")

    def deploy_collection(self, args) -> CommandResult:
        """Deploy all agents from a specific collection.

        NEW: Enables bulk deployment of all agents from a named collection.
        Useful for deploying entire agent sets at once.
        """
        try:
            from pathlib import Path

            from ...services.agents.deployment.multi_source_deployment_service import (
                MultiSourceAgentDeploymentService,
            )

            collection_id = args.collection_id

            # Get agents from collection
            service = MultiSourceAgentDeploymentService()
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            agents = service.get_agents_by_collection(collection_id, cache_dir)

            if not agents:
                return CommandResult.error_result(
                    f"No agents found in collection '{collection_id}'"
                )

            # Dry run mode
            if getattr(args, "dry_run", False):
                agent_names = [
                    agent.get("metadata", {}).get("name", "Unknown") for agent in agents
                ]
                output = f"Would deploy {len(agents)} agents from collection '{collection_id}':\n"
                for name in agent_names:
                    output += f"  • {name}\n"
                return CommandResult.success_result(
                    output,
                    data={"collection_id": collection_id, "agent_count": len(agents)},
                )

            # Deploy agents by copying their cached markdown files into the
            # project's .claude/agents/ directory. Remote/collection agents are
            # already authored as Claude Code-compatible markdown with YAML
            # frontmatter, so a direct copy is the correct deployment action
            # (the AgentDeploymentService template-build path applies only to
            # built-in JSON templates, not to markdown collection agents).
            import shutil

            from ...services.agents.deployment_utils import (
                normalize_deployment_filename,
            )

            force = bool(getattr(args, "force", False))
            target_dir = Path.cwd() / ".claude" / "agents"
            target_dir.mkdir(parents=True, exist_ok=True)

            deployed: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []

            print(
                f"\n📦 Deploying {len(agents)} agents from collection "
                f"'{collection_id}' to {target_dir}"
            )

            for agent in agents:
                metadata = agent.get("metadata", {}) or {}
                agent_name = agent.get("agent_id") or metadata.get("name") or "unknown"
                source_path_str = agent.get("path") or agent.get("file_path")

                if not source_path_str:
                    msg = "missing source file path"
                    failed.append({"agent": agent_name, "error": msg})
                    print(f"❌ {agent_name}: {msg}")
                    continue

                source_path = Path(source_path_str)
                if not source_path.exists():
                    msg = f"source file not found: {source_path}"
                    failed.append({"agent": agent_name, "error": msg})
                    print(f"❌ {agent_name}: {msg}")
                    continue

                target_filename = normalize_deployment_filename(f"{agent_name}.md")
                target_file = target_dir / target_filename

                if target_file.exists() and not force:
                    skipped.append(agent_name)
                    print(
                        f"⏭️  {agent_name}: already deployed (use --force to overwrite)"
                    )
                    continue

                try:
                    shutil.copy2(source_path, target_file)
                    deployed.append(agent_name)
                    print(f"✅ {agent_name} -> {target_file.name}")
                except Exception as copy_err:
                    failed.append({"agent": agent_name, "error": str(copy_err)})
                    self._logger.error(
                        f"Failed to deploy {agent_name}: {copy_err}",
                        exc_info=True,
                    )
                    print(f"❌ {agent_name}: {copy_err}")

            summary = (
                f"\n📊 Deployment summary for '{collection_id}':\n"
                f"  ✅ Deployed: {len(deployed)}\n"
                f"  ⏭️  Skipped: {len(skipped)}\n"
                f"  ❌ Failed:   {len(failed)}\n"
                f"  📁 Target:   {target_dir}"
            )
            print(summary)

            data = {
                "collection_id": collection_id,
                "target_dir": str(target_dir),
                "deployed": deployed,
                "skipped": skipped,
                "failed": failed,
                "agent_count": len(agents),
            }

            if failed and not deployed:
                return CommandResult.error_result(
                    f"Failed to deploy any agents from collection "
                    f"'{collection_id}' ({len(failed)} errors)",
                    data=data,
                )

            message = (
                f"Deployed {len(deployed)} of {len(agents)} agents from "
                f"collection '{collection_id}' to {target_dir}"
            )
            if failed:
                message += f" ({len(failed)} failed)"
            return CommandResult.success_result(message, data=data)

        except Exception as e:
            self._logger.error(f"Error deploying collection: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deploying collection: {e}")

    def list_by_collection(self, args) -> CommandResult:
        """List agents from a specific collection.

        NEW: Shows detailed information about agents in a collection.
        Supports multiple output formats (table, json, yaml).
        """
        try:
            import json as json_lib
            from pathlib import Path

            from ...services.agents.deployment.multi_source_deployment_service import (
                MultiSourceAgentDeploymentService,
            )

            collection_id = args.collection_id
            output_format = getattr(args, "format", "table")

            # Get agents from collection
            service = MultiSourceAgentDeploymentService()
            cache_dir = Path.home() / ".claude-mpm" / "cache" / "agents"
            agents = service.get_agents_by_collection(collection_id, cache_dir)

            if not agents:
                return CommandResult.error_result(
                    f"No agents found in collection '{collection_id}'"
                )

            # Format output based on requested format
            if output_format == "json":
                return CommandResult.success_result(
                    json_lib.dumps(agents, indent=2),
                    data={"collection_id": collection_id, "agents": agents},
                )
            if output_format == "yaml":
                try:
                    import yaml

                    return CommandResult.success_result(
                        yaml.dump(agents, default_flow_style=False),
                        data={"collection_id": collection_id, "agents": agents},
                    )
                except ImportError:
                    return CommandResult.error_result(
                        "YAML support not available (install PyYAML)"
                    )

            # Table format (default)
            output_lines = [f"Agents in collection '{collection_id}':\n"]
            for agent in agents:
                metadata = agent.get("metadata", {})
                name = metadata.get("name", "Unknown")
                description = metadata.get("description", "No description")
                version = agent.get("version", "unknown")
                output_lines.append(f"  • {name} (v{version})")
                output_lines.append(f"    {description}\n")

            return CommandResult.success_result(
                "\n".join(output_lines),
                data={"collection_id": collection_id, "agent_count": len(agents)},
            )

        except Exception as e:
            self._logger.error(f"Error listing collection agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error listing collection agents: {e}")
