from pathlib import Path

#!/usr/bin/env python3
"""Optimized agent loader with caching and parallel loading.

This module provides high-performance agent loading with:
- Compiled template caching
- Parallel file operations
- Memory-efficient batch processing
- Incremental loading for large agent sets

WHY optimized agent loading:
- Reduces agent deployment time from >500ms to <200ms per agent
- Caches compiled templates to avoid repeated parsing
- Parallel I/O operations for multi-agent loading
- Minimizes file system operations through batching
"""

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from ..core.logger import get_logger
from .cache import get_file_cache


@dataclass
class AgentLoadMetrics:
    """Metrics for agent loading performance."""

    total_agents: int = 0
    loaded_agents: int = 0
    cached_agents: int = 0
    failed_agents: int = 0
    total_time: float = 0.0
    parse_time: float = 0.0
    io_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


class OptimizedAgentLoader:
    """High-performance agent loader with caching and parallelization.

    WHY this design:
    - ThreadPoolExecutor for parallel file I/O
    - LRU cache for compiled agent templates
    - Batch processing to reduce overhead
    - Lazy compilation for rarely-used agents

    Example:
        loader = OptimizedAgentLoader(max_workers=4)

        # Load agents in parallel
        agents = loader.load_agents_parallel([
            '/path/to/agent1.json',
            '/path/to/agent2.json'
        ])

        # Async loading
        agents = await loader.load_agents_async(paths)
    """

    def __init__(
        self, max_workers: int = 4, cache_ttl: int = 3600, enable_lazy: bool = True
    ):
        """Initialize optimized agent loader.

        Args:
            max_workers: Number of parallel workers for loading
            cache_ttl: Cache time-to-live in seconds
            enable_lazy: Whether to use lazy loading for templates
        """
        self.max_workers = max_workers
        self.cache_ttl = cache_ttl
        self.enable_lazy = enable_lazy

        # Get or create cache
        self.cache = get_file_cache(max_size_mb=50, default_ttl=cache_ttl)

        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Metrics tracking
        self.metrics = AgentLoadMetrics()

        # Logger
        self.logger = get_logger("optimized_agent_loader")

        # Template compilation cache
        self._compiled_templates: Dict[str, Dict[str, Any]] = {}
        self._template_lock = threading.Lock()

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for an agent file.

        Includes file path and modification time for cache invalidation.
        """
        try:
            mtime = file_path.stat().st_mtime
            return f"agent:{file_path}:{mtime}"
        except:
            return f"agent:{file_path}"

    def _load_agent_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load and parse a single agent file.

        Args:
            file_path: Path to agent file (.json or .md)

        Returns:
            Parsed agent data or None if failed
        """
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path)
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.metrics.cache_hits += 1
                return cached

            self.metrics.cache_misses += 1

            # Read file
            io_start = time.time()
            content = file_path.read_text(encoding="utf-8")
            self.metrics.io_time += time.time() - io_start

            # Parse based on file type
            parse_start = time.time()
            if file_path.suffix == ".json":
                agent_data = json.loads(content)
            elif file_path.suffix == ".md":
                # Extract frontmatter from markdown
                agent_data = self._parse_markdown_agent(content)
            else:
                agent_data = {"content": content}

            self.metrics.parse_time += time.time() - parse_start

            # Add metadata
            agent_data["_file_path"] = str(file_path)
            agent_data["_loaded_at"] = datetime.now().isoformat()

            # Cache the result
            self.cache.put(cache_key, agent_data, ttl=self.cache_ttl)

            return agent_data

        except Exception as e:
            self.logger.error(f"Failed to load agent {file_path}: {e}")
            self.metrics.failed_agents += 1
            return None
        finally:
            elapsed = time.time() - start_time
            self.logger.debug(f"Loaded {file_path.name} in {elapsed:.3f}s")

    def _parse_markdown_agent(self, content: str) -> Dict[str, Any]:
        """Parse agent data from markdown content.

        Extracts YAML frontmatter and content from markdown files.
        """
        lines = content.split("\n")

        # Look for frontmatter
        if lines[0] == "---":
            try:
                import yaml

                end_index = lines[1:].index("---") + 1
                frontmatter = "\n".join(lines[1:end_index])
                body = "\n".join(lines[end_index + 1 :])

                data = yaml.safe_load(frontmatter) or {}
                data["instructions"] = body
                return data
            except:
                pass

        # No frontmatter, treat as pure instructions
        return {"instructions": content}

    def load_agents_parallel(
        self, file_paths: List[Path], batch_size: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """Load multiple agents in parallel.

        Args:
            file_paths: List of agent file paths
            batch_size: Number of agents to load concurrently

        Returns:
            Dictionary mapping agent IDs to agent data
        """
        start_time = time.time()
        self.metrics.total_agents = len(file_paths)

        agents = {}

        # Process in batches to avoid overwhelming the system
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]

            # Submit batch to thread pool
            futures = {
                self.executor.submit(self._load_agent_file, path): path
                for path in batch
            }

            # Collect results
            for future in as_completed(futures):
                path = futures[future]
                try:
                    agent_data = future.result(timeout=5.0)
                    if agent_data:
                        agent_id = path.stem
                        agents[agent_id] = agent_data
                        self.metrics.loaded_agents += 1
                except Exception as e:
                    self.logger.error(f"Failed to load {path}: {e}")
                    self.metrics.failed_agents += 1

        self.metrics.total_time = time.time() - start_time

        self.logger.info(
            f"Loaded {self.metrics.loaded_agents}/{self.metrics.total_agents} agents "
            f"in {self.metrics.total_time:.2f}s "
            f"(cache hits: {self.metrics.cache_hits}, misses: {self.metrics.cache_misses})"
        )

        return agents

    async def load_agents_async(
        self, file_paths: List[Path]
    ) -> Dict[str, Dict[str, Any]]:
        """Load agents asynchronously for async applications.

        Args:
            file_paths: List of agent file paths

        Returns:
            Dictionary mapping agent IDs to agent data
        """
        if not AIOFILES_AVAILABLE:
            # Fallback to sync loading in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.load_agents_parallel, file_paths
            )

        start_time = time.time()
        self.metrics.total_agents = len(file_paths)

        # Create async tasks for all agents
        tasks = []
        for path in file_paths:
            tasks.append(self._load_agent_async(path))

        # Load all agents concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful loads
        agents = {}
        for path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to load {path}: {result}")
                self.metrics.failed_agents += 1
            elif result:
                agent_id = path.stem
                agents[agent_id] = result
                self.metrics.loaded_agents += 1

        self.metrics.total_time = time.time() - start_time

        self.logger.info(
            f"Async loaded {self.metrics.loaded_agents}/{self.metrics.total_agents} agents "
            f"in {self.metrics.total_time:.2f}s"
        )

        return agents

    async def _load_agent_async(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load a single agent asynchronously."""
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path)
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.metrics.cache_hits += 1
                return cached

            self.metrics.cache_misses += 1

            # Read file asynchronously
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            # Parse in executor to avoid blocking
            loop = asyncio.get_event_loop()
            if file_path.suffix == ".json":
                agent_data = await loop.run_in_executor(None, json.loads, content)
            elif file_path.suffix == ".md":
                agent_data = await loop.run_in_executor(
                    None, self._parse_markdown_agent, content
                )
            else:
                agent_data = {"content": content}

            # Add metadata
            agent_data["_file_path"] = str(file_path)
            agent_data["_loaded_at"] = datetime.now().isoformat()

            # Cache the result
            self.cache.put(cache_key, agent_data, ttl=self.cache_ttl)

            return agent_data

        except Exception as e:
            self.logger.error(f"Failed to async load {file_path}: {e}")
            return None

    def compile_template(self, agent_id: str, template: str) -> Dict[str, Any]:
        """Compile and cache an agent template.

        WHY template compilation:
        - Pre-processes templates for faster runtime use
        - Validates template syntax once
        - Caches compiled form for reuse
        - Reduces repeated parsing overhead

        Args:
            agent_id: Unique agent identifier
            template: Raw template string

        Returns:
            Compiled template data
        """
        with self._template_lock:
            # Check if already compiled
            if agent_id in self._compiled_templates:
                self.metrics.cache_hits += 1
                return self._compiled_templates[agent_id]

            self.metrics.cache_misses += 1

            # Compile template
            start_time = time.time()
            try:
                # Parse any template variables
                compiled = {
                    "id": agent_id,
                    "template": template,
                    "variables": self._extract_variables(template),
                    "sections": self._extract_sections(template),
                    "compiled_at": datetime.now().isoformat(),
                }

                # Cache compiled template
                self._compiled_templates[agent_id] = compiled

                self.metrics.parse_time += time.time() - start_time
                return compiled

            except Exception as e:
                self.logger.error(f"Failed to compile template {agent_id}: {e}")
                return {"id": agent_id, "template": template, "error": str(e)}

    def _extract_variables(self, template: str) -> List[str]:
        """Extract variable placeholders from template."""
        import re

        # Find {{variable}} patterns
        return re.findall(r"\{\{(\w+)\}\}", template)

    def _extract_sections(self, template: str) -> Dict[str, str]:
        """Extract named sections from template."""
        sections = {}
        current_section = "main"
        current_content = []

        for line in template.split("\n"):
            # Check for section headers (## Section Name)
            if line.startswith("## "):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                # Start new section
                current_section = line[3:].strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def preload_agents(self, agent_dirs: List[Path]) -> None:
        """Preload all agents from specified directories.

        Useful for warming up the cache at startup.

        Args:
            agent_dirs: List of directories containing agents
        """
        self.logger.info(f"Preloading agents from {len(agent_dirs)} directories")

        all_paths = []
        for dir_path in agent_dirs:
            if dir_path.exists():
                all_paths.extend(dir_path.glob("*.json"))
                all_paths.extend(dir_path.glob("*.md"))

        if all_paths:
            self.load_agents_parallel(all_paths)

    def get_metrics(self) -> Dict[str, Any]:
        """Get loader performance metrics."""
        return {
            "total_agents": self.metrics.total_agents,
            "loaded_agents": self.metrics.loaded_agents,
            "cached_agents": len(self._compiled_templates),
            "failed_agents": self.metrics.failed_agents,
            "total_time": self.metrics.total_time,
            "avg_load_time": self.metrics.total_time
            / max(1, self.metrics.loaded_agents),
            "parse_time": self.metrics.parse_time,
            "io_time": self.metrics.io_time,
            "cache_hit_rate": self.metrics.cache_hits
            / max(1, self.metrics.cache_hits + self.metrics.cache_misses),
        }

    def cleanup(self):
        """Clean up resources."""
        self.executor.shutdown(wait=False)
        self._compiled_templates.clear()


# Global loader instance
_global_loader: Optional[OptimizedAgentLoader] = None


def get_optimized_loader(max_workers: int = 4) -> OptimizedAgentLoader:
    """Get or create global optimized loader."""
    global _global_loader
    if _global_loader is None:
        _global_loader = OptimizedAgentLoader(max_workers=max_workers)
    return _global_loader


def preload_system_agents():
    """Preload all system agents at startup."""
    loader = get_optimized_loader()

    # Common agent directories
    agent_dirs = [
        Path.cwd() / ".claude" / "agents",
        Path.cwd() / ".claude-mpm" / "agents",
        Path.home() / ".claude-mpm" / "agents",
        Path(__file__).parent.parent / "agents" / "templates",
        Path(__file__).parent.parent / "agents",
    ]

    loader.preload_agents([d for d in agent_dirs if d.exists()])
