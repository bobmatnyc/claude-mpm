"""
Kuzu-Memory MCP Service Integration
====================================

Provides MCP tool wrappers for kuzu-memory knowledge graph operations,
enabling the PM agent to store and retrieve memories programmatically.

WHY: The PM agent needs structured tools to manage conversation memories,
allowing it to build up project knowledge over time.

DESIGN DECISIONS:
- Extends ExternalMCPService for consistent integration patterns
- Provides high-level tools that abstract kuzu-memory complexity
- Includes context enrichment for better memory retrieval
- Supports tagging for organized knowledge management
- kuzu-memory>=1.1.5 is now a REQUIRED dependency (moved from optional in v4.8.6)
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class KuzuMemoryService(BaseToolAdapter):
    """
    MCP service wrapper for kuzu-memory knowledge graph.

    Provides tools for:
    - Storing memories with tags
    - Retrieving relevant memories
    - Searching memories by query
    - Getting enriched context for topics
    """

    def __init__(self):
        """Initialize kuzu-memory MCP service."""
        # Define the tool
        definition = MCPToolDefinition(
            name="kuzu_memory",
            description="Knowledge graph memory system for persistent context",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["store", "recall", "search", "context"],
                        "description": "The memory operation to perform",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content for store operation",
                    },
                    "query": {
                        "type": "string",
                        "description": "Query for recall/search/context operations",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for filtering or categorization",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of results",
                    },
                },
                "required": ["action"],
            },
        )
        super().__init__(definition)

        self.service_name = "kuzu-memory"
        self.package_name = "kuzu-memory"
        # Use the current project directory as kuzu-memory works with project-specific databases
        self.project_path = Path.cwd()
        self._is_installed = False
        self.kuzu_cmd = None

    async def _check_installation(self) -> bool:
        """Check if kuzu-memory is installed via pipx."""
        # Check pipx installation first
        pipx_path = (
            Path.home()
            / ".local"
            / "pipx"
            / "venvs"
            / "kuzu-memory"
            / "bin"
            / "kuzu-memory"
        )
        if pipx_path.exists():
            self.kuzu_cmd = str(pipx_path)
            return True

        # Check system PATH
        import shutil

        kuzu_cmd = shutil.which("kuzu-memory")
        if kuzu_cmd:
            self.kuzu_cmd = kuzu_cmd
            return True

        return False

    async def _install_package(self) -> bool:
        """
        Install kuzu-memory using pipx (preferred over pip).

        NOTE: As of v4.8.6, kuzu-memory is a required dependency and should be
        installed via pip along with claude-mpm. This method is kept for backward
        compatibility and edge cases where the package may be missing.
        """
        try:
            # Check if pipx is available
            import shutil

            if not shutil.which("pipx"):
                self.log_warning(
                    "pipx not found. Install it first: python -m pip install --user pipx"
                )
                self.log_info(
                    "Alternatively, kuzu-memory should be installed via pip with claude-mpm dependencies"
                )
                return False

            self.log_info("Installing kuzu-memory via pipx...")
            result = subprocess.run(
                ["pipx", "install", "kuzu-memory"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode == 0:
                self.log_info("Successfully installed kuzu-memory via pipx")
                return await self._check_installation()

            self.log_error(f"Failed to install kuzu-memory: {result.stderr}")
            return False

        except Exception as e:
            self.log_error(f"Error installing kuzu-memory: {e}")
            return False

    async def initialize(self) -> bool:
        """
        Initialize the kuzu-memory service.

        NOTE: As of v4.8.6, kuzu-memory is a required dependency. This method
        checks for installation and provides helpful messages if missing.
        """
        try:
            # Check if package is installed
            self._is_installed = await self._check_installation()

            if not self._is_installed:
                self.log_warning(
                    f"{self.package_name} not found in PATH. "
                    f"Since v4.8.6, it's a required dependency."
                )
                self.log_info("Attempting installation via pipx as fallback...")
                await self._install_package()
                self._is_installed = await self._check_installation()

            if not self._is_installed:
                self.log_error(
                    f"Failed to initialize {self.package_name}. "
                    f"Please install manually: pip install kuzu-memory>=1.1.5"
                )
                return False

            self.log_info(f"{self.package_name} is available and ready")
            self._initialized = True
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize {self.service_name}: {e}")
            return False

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke kuzu-memory tool based on the invocation request.

        Routes to appropriate method based on action parameter.
        """
        params = invocation.parameters
        action = params.get("action")

        try:
            if action == "store":
                result = await self.store_memory(
                    params.get("content"), params.get("tags"), {}  # metadata
                )
            elif action == "recall":
                result = await self.recall_memories(
                    params.get("query"), params.get("limit", 5), params.get("tags")
                )
            elif action == "search":
                result = await self.search_memories(
                    params.get("query", ""),
                    "both",  # search_type
                    params.get("limit", 10),
                )
            elif action == "context":
                result = await self.get_context(
                    params.get("query", ""), 2, True  # depth  # include_related
                )
            else:
                return MCPToolResult(success=False, error=f"Unknown action: {action}")

            return MCPToolResult(
                success=result.get("success", False),
                data=result,
                error=result.get("error"),
            )

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters - basic implementation."""
        return True  # Validation is handled in individual methods

    async def shutdown(self) -> None:
        """Shutdown the service."""
        # No resources to clean up

    async def store_memory(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store a memory in the knowledge graph.

        Args:
            content: Memory content to store
            tags: Optional tags for categorization
            metadata: Optional metadata

        Returns:
            Result of the storage operation
        """
        if not self._is_installed:
            return {
                "success": False,
                "error": "kuzu-memory not installed",
            }

        try:
            # Use remember command for storing memories
            # kuzu-memory works with project-specific databases in the current working directory
            cmd = [self.kuzu_cmd, "remember", content]

            # Execute command in project directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Memory stored successfully",
                    "content": content[:100],
                    "tags": tags or [],
                }

            return {
                "success": False,
                "error": result.stderr or "Failed to store memory",
            }

        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def recall_memories(
        self,
        query: str,
        limit: int = 5,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Recall memories relevant to a query.

        Args:
            query: Query to find relevant memories
            limit: Maximum number of memories
            tags: Optional tag filter

        Returns:
            Retrieved memories
        """
        if not self._is_installed:
            return {
                "success": False,
                "error": "kuzu-memory not installed",
                "memories": [],
            }

        try:
            # Use recall command for retrieving memories
            # kuzu-memory works with project-specific databases in the current working directory
            cmd = [
                self.kuzu_cmd,
                "recall",
                query,
                "--format",
                "json",
                "--max-memories",
                str(limit),
            ]

            # Execute command in project directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                memories = json.loads(result.stdout)
                return {
                    "success": True,
                    "query": query,
                    "count": len(memories),
                    "memories": memories,
                }

            return {
                "success": True,
                "query": query,
                "count": 0,
                "memories": [],
            }

        except Exception as e:
            self.logger.error(f"Error recalling memories: {e}")
            return {
                "success": False,
                "error": str(e),
                "memories": [],
            }

    async def search_memories(
        self,
        search_term: str,
        search_type: str = "both",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search memories by using recall with the search term.

        Args:
            search_term: Term to search for
            search_type: Type of search (not used, kept for compatibility)
            limit: Maximum number of results

        Returns:
            Search results
        """
        if not self._is_installed:
            return {
                "success": False,
                "error": "kuzu-memory not installed",
                "results": [],
            }

        try:
            # Use recall for searching (kuzu-memory doesn't have a separate search command)
            cmd = [
                self.kuzu_cmd,
                "recall",
                search_term,
                "--format",
                "json",
                "--max-memories",
                str(limit),
            ]

            # Execute command in project directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                # Parse the output
                results = []
                if "No relevant memories found" not in result.stdout:
                    # Try to extract memories from output
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if line.strip() and not line.startswith("🔍"):
                            results.append({"content": line.strip()})

                return {
                    "success": True,
                    "search_term": search_term,
                    "count": len(results),
                    "results": results[:limit],
                }

            return {
                "success": True,
                "search_term": search_term,
                "count": 0,
                "results": [],
            }

        except Exception as e:
            self.log_error(f"Error searching memories: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    async def get_context(
        self,
        topic: str,
        depth: int = 2,
        include_related: bool = True,
    ) -> Dict[str, Any]:
        """
        Get enriched context for a topic using the enhance command.

        Args:
            topic: Topic to get context for
            depth: Maximum memories to include
            include_related: Not used, kept for compatibility

        Returns:
            Enriched context for the topic
        """
        if not self._is_installed:
            return {
                "success": False,
                "error": "kuzu-memory not installed",
                "context": {},
            }

        try:
            # Use enhance command for context enrichment
            cmd = [
                self.kuzu_cmd,
                "enhance",
                topic,
                "--max-memories",
                str(depth * 3),
                "--format",
                "plain",  # Get just the context
            ]

            # Execute command in project directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(self.project_path),
                check=False,
            )

            if result.returncode == 0 and result.stdout:
                return {
                    "success": True,
                    "topic": topic,
                    "context": result.stdout.strip(),
                    "memories": [],  # Enhanced context is already processed
                }

            # Fallback to recall if enhance fails
            self.log_debug("Enhance command failed, falling back to recall")
            return await self.recall_memories(topic, limit=depth * 3)

        except Exception as e:
            self.log_error(f"Error getting context: {e}")
            # Fallback to basic recall
            return await self.recall_memories(topic, limit=depth * 3)


# Tool function wrappers for MCP Gateway
async def store_memory(
    content: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Store a memory using the kuzu-memory service."""
    service = KuzuMemoryService()
    await service.initialize()
    return await service.store_memory(content, tags, metadata)


async def recall_memories(
    query: str,
    limit: int = 5,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Recall memories relevant to a query."""
    service = KuzuMemoryService()
    await service.initialize()
    return await service.recall_memories(query, limit, tags)


async def search_memories(
    search_term: str,
    search_type: str = "both",
    limit: int = 10,
) -> Dict[str, Any]:
    """Search memories by content or tags."""
    service = KuzuMemoryService()
    await service.initialize()
    return await service.search_memories(search_term, search_type, limit)


async def get_context(
    topic: str,
    depth: int = 2,
    include_related: bool = True,
) -> Dict[str, Any]:
    """Get enriched context for a topic."""
    service = KuzuMemoryService()
    await service.initialize()
    return await service.get_context(topic, depth, include_related)
