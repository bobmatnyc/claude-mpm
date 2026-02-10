"""Memory management abstraction layer for claude-mpm.

WHY: Enables switching between static file-based memory and graph-based
kuzu-memory backend without changing hook or PM code.

DESIGN:
- BaseMemoryBackend: Abstract interface for memory operations
- StaticMemoryBackend: Current file-based memory (default)
- KuzuMemoryBackend: Graph-based memory using kuzu-memory
- MemoryManager: Routes operations to configured backend
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseMemoryBackend(ABC):
    """Abstract interface for memory backends."""

    @abstractmethod
    async def store(
        self, agent_name: str, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Store memory for an agent.

        Args:
            agent_name: Agent identifier
            content: Memory content to store
            metadata: Optional metadata (tags, source, etc.)

        Returns:
            True if stored successfully
        """

    @abstractmethod
    async def recall(self, query: str, agent_name: str | None = None) -> str:
        """Recall memories matching query.

        Args:
            query: Search query
            agent_name: Optional filter by agent

        Returns:
            Retrieved memory content
        """

    @abstractmethod
    async def enhance_prompt(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Enhance a prompt with relevant memories.

        Args:
            prompt: Original prompt
            context: Optional context (agent, task, etc.)

        Returns:
            Enhanced prompt with memory context
        """

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            Statistics dict (count, size, etc.)
        """


class StaticMemoryBackend(BaseMemoryBackend):
    """File-based memory backend (current implementation)."""

    def __init__(self, memory_dir: Path | None = None, max_size: int = 81920):
        """Initialize static memory backend.

        Args:
            memory_dir: Directory for memory files (default: .claude-mpm/memories)
            max_size: Max file size in bytes (default: 80KB)
        """
        self.memory_dir = memory_dir or Path(".claude-mpm/memories")
        self.max_size = max_size
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    async def store(
        self, agent_name: str, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Store memory in markdown file."""
        try:
            memory_file = self.memory_dir / f"{agent_name}.md"

            # Read existing content
            existing = ""
            if memory_file.exists():
                existing = memory_file.read_text()

            # Append new content
            updated = existing + f"\n{content}\n"

            # Check size limit
            if len(updated.encode()) > self.max_size:
                logger.warning(
                    f"Memory file for {agent_name} exceeds {self.max_size} bytes. "
                    "Consider consolidation."
                )

            # Write back
            memory_file.write_text(updated)
            return True

        except Exception as e:
            logger.error(f"Error storing static memory for {agent_name}: {e}")
            return False

    async def recall(self, query: str, agent_name: str | None = None) -> str:
        """Recall memories from files (simple keyword search)."""
        try:
            results = []

            # Determine which files to search
            if agent_name:
                files = [self.memory_dir / f"{agent_name}.md"]
            else:
                files = list(self.memory_dir.glob("*.md"))

            # Search files for query keywords
            query_lower = query.lower()
            for file in files:
                if not file.exists():
                    continue

                content = file.read_text()
                # Simple line-by-line matching
                for line in content.split("\n"):
                    if query_lower in line.lower():
                        results.append(f"[{file.stem}] {line.strip()}")

            return "\n".join(results) if results else "No matching memories found."

        except Exception as e:
            logger.error(f"Error recalling static memory: {e}")
            return ""

    async def enhance_prompt(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Enhance prompt with relevant memories (basic implementation)."""
        agent_name = context.get("agent") if context else None

        # Recall memories related to prompt keywords
        memories = await self.recall(prompt, agent_name)

        if memories and memories != "No matching memories found.":
            return f"{prompt}\n\n## Relevant Memories:\n{memories}"

        return prompt

    def get_stats(self) -> dict[str, Any]:
        """Get static memory statistics."""
        try:
            files = list(self.memory_dir.glob("*.md"))
            total_size = sum(f.stat().st_size for f in files)

            return {
                "backend": "static",
                "agent_count": len(files),
                "total_size_bytes": total_size,
                "total_size_kb": round(total_size / 1024, 2),
                "directory": str(self.memory_dir),
            }
        except Exception as e:
            logger.error(f"Error getting static memory stats: {e}")
            return {"backend": "static", "error": str(e)}


class KuzuMemoryBackend(BaseMemoryBackend):
    """Graph-based memory backend using kuzu-memory."""

    def __init__(self, project_root: str | None = None, db_path: str | None = None):
        """Initialize kuzu memory backend.

        Args:
            project_root: Project root for kuzu
            db_path: Database path for kuzu
        """
        self.project_root = project_root or str(Path.cwd())
        self.db_path = db_path or str(Path(self.project_root) / "kuzu-memories")
        self._client = None

    def _get_client(self):
        """Lazy-load kuzu-memory client."""
        if self._client is None:
            try:
                # Import kuzu-memory client
                # This will be available if kuzu-memory is installed
                from kuzu_memory.client import KuzuMemoryClient  # type: ignore

                self._client = KuzuMemoryClient(
                    project_root=self.project_root,
                    db_path=self.db_path,
                )
            except ImportError:
                logger.error(
                    "kuzu-memory not installed. Run: claude-mpm setup kuzu-memory"
                )
                raise RuntimeError(
                    "kuzu-memory not available. "
                    "Install with: uv tool install kuzu-memory"
                ) from None

        return self._client

    async def store(
        self, agent_name: str, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Store memory in kuzu graph."""
        try:
            client = self._get_client()

            # Merge agent_name into metadata
            full_metadata = metadata or {}
            full_metadata["agent"] = agent_name

            # Call kuzu learn
            await client.learn(content, metadata=full_metadata)
            return True

        except Exception as e:
            logger.error(f"Error storing kuzu memory for {agent_name}: {e}")
            return False

    async def recall(self, query: str, agent_name: str | None = None) -> str:
        """Recall memories from kuzu graph."""
        try:
            client = self._get_client()

            # Build query with agent filter if provided
            if agent_name:
                # Add agent context to query
                full_query = f"agent:{agent_name} {query}"
            else:
                full_query = query

            # Call kuzu recall
            result = await client.recall(full_query)
            return result if result else "No matching memories found."

        except Exception as e:
            logger.error(f"Error recalling kuzu memory: {e}")
            return ""

    async def enhance_prompt(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Enhance prompt using kuzu's semantic search."""
        try:
            client = self._get_client()

            # Kuzu has built-in enhance functionality
            return await client.enhance(prompt, context=context)

        except Exception as e:
            logger.error(f"Error enhancing prompt with kuzu: {e}")
            return prompt

    def get_stats(self) -> dict[str, Any]:
        """Get kuzu memory statistics."""
        try:
            client = self._get_client()

            # Get stats from kuzu
            stats = client.get_stats()

            return {
                "backend": "kuzu",
                "project_root": self.project_root,
                "db_path": self.db_path,
                **stats,
            }

        except Exception as e:
            logger.error(f"Error getting kuzu memory stats: {e}")
            return {"backend": "kuzu", "error": str(e)}


class MemoryManager:
    """Main memory manager that routes to configured backend."""

    def __init__(self, backend: str = "static", config: dict[str, Any] | None = None):
        """Initialize memory manager.

        Args:
            backend: Backend type ("static" or "kuzu")
            config: Backend-specific configuration
        """
        self.backend_type = backend
        config = config or {}

        # Initialize appropriate backend
        if backend == "kuzu":
            self.backend: BaseMemoryBackend = KuzuMemoryBackend(
                project_root=config.get("project_root"),
                db_path=config.get("db_path"),
            )
        else:
            self.backend = StaticMemoryBackend(
                memory_dir=Path(config.get("directory", ".claude-mpm/memories")),
                max_size=config.get("max_size", 81920),
            )

        logger.info(f"Memory manager initialized with {backend} backend")

    async def store(
        self, agent_name: str, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Store memory using configured backend."""
        return await self.backend.store(agent_name, content, metadata)

    async def recall(self, query: str, agent_name: str | None = None) -> str:
        """Recall memories using configured backend."""
        return await self.backend.recall(query, agent_name)

    async def enhance_prompt(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Enhance prompt using configured backend."""
        return await self.backend.enhance_prompt(prompt, context)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return self.backend.get_stats()

    @classmethod
    def from_config_file(cls, config_path: Path | None = None) -> "MemoryManager":
        """Create memory manager from configuration file.

        Args:
            config_path: Path to config file (default: ~/.claude-mpm/config.yaml)

        Returns:
            Configured MemoryManager instance
        """
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config.yaml"

        # Load config
        try:
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            memory_config = config.get("memory", {})
            backend_type = memory_config.get("backend", "static")

            # Get backend-specific config
            if backend_type == "kuzu":
                backend_config = memory_config.get("kuzu", {})
            else:
                backend_config = memory_config.get("static", {})

            return cls(backend=backend_type, config=backend_config)

        except FileNotFoundError:
            logger.warning(
                f"Config file not found at {config_path}, using static backend"
            )
            return cls(backend="static")
        except Exception as e:
            logger.error(f"Error loading config: {e}, using static backend")
            return cls(backend="static")
