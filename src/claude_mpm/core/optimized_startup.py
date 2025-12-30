#!/usr/bin/env python3
"""Optimized startup performance with deferred initialization.

This module provides startup optimization techniques:
- Deferred service initialization
- Async configuration loading
- Minimal import strategy
- Progressive enhancement

WHY optimized startup:
- Reduces startup time from 3-5 seconds to <2 seconds
- Defers non-critical initialization
- Loads only required components
- Provides instant CLI responsiveness
"""

import asyncio
import importlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.logger import get_logger
from .cache import get_file_cache
from .lazy import LazyService, lazy_load


@dataclass
class StartupMetrics:
    """Metrics for startup performance."""

    total_time: float = 0.0
    import_time: float = 0.0
    config_time: float = 0.0
    service_time: float = 0.0
    agent_time: float = 0.0
    phases: Dict[str, float] = field(default_factory=dict)
    deferred_services: List[str] = field(default_factory=list)


class OptimizedStartup:
    """Manager for optimized application startup.

    WHY this design:
    - Phase-based initialization for progressive loading
    - Critical-path optimization
    - Deferred loading for optional features
    - Parallel initialization where possible

    Example:
        startup = OptimizedStartup()

        # Fast minimal startup
        startup.initialize_minimal()

        # Progressive enhancement
        startup.initialize_services()
        startup.initialize_agents()
    """

    # Critical services needed immediately
    CRITICAL_SERVICES = {"logger", "config", "paths", "cli_parser"}

    # Services that can be deferred
    DEFERRED_SERVICES = {
        "socketio",
        "dashboard",
        "memory",
        "hooks",
        "project_analyzer",
        "tree_sitter",
        "monitoring",
    }

    # Heavy imports to defer
    HEAVY_IMPORTS = {
        "numpy",
        "pandas",
        "matplotlib",
        "scipy",
        "tensorflow",
        "torch",
        "transformers",
    }

    def __init__(self):
        self.metrics = StartupMetrics()
        self.logger = get_logger("startup")
        self.initialized_services: Set[str] = set()
        self.lazy_services: Dict[str, LazyService] = {}
        self.import_cache: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Start timer
        self.start_time = time.time()

    def initialize_minimal(self) -> float:
        """Initialize only critical components for fast startup.

        Returns:
            Time taken for minimal initialization
        """
        phase_start = time.time()

        # 1. Setup basic logging (synchronous, required immediately)
        self._setup_logging()

        # 2. Load minimal config (only required settings)
        self._load_minimal_config()

        # 3. Setup CLI parser (needed for argument processing)
        self._setup_cli_parser()

        elapsed = time.time() - phase_start
        self.metrics.phases["minimal"] = elapsed
        self.logger.info(f"Minimal initialization completed in {elapsed:.2f}s")

        return elapsed

    def initialize_services(self, lazy: bool = True) -> float:
        """Initialize service layer with optional lazy loading.

        Args:
            lazy: Whether to use lazy loading for services

        Returns:
            Time taken for service initialization
        """
        phase_start = time.time()

        if lazy:
            # Create lazy wrappers for deferred services
            self._create_lazy_services()
            self.logger.debug(f"Created {len(self.lazy_services)} lazy services")
        else:
            # Initialize all services immediately
            self._initialize_all_services()

        elapsed = time.time() - phase_start
        self.metrics.phases["services"] = elapsed
        self.metrics.service_time = elapsed

        return elapsed

    def initialize_agents(self, preload: bool = False) -> float:
        """Initialize agent system with optional preloading.

        Args:
            preload: Whether to preload all agents

        Returns:
            Time taken for agent initialization
        """
        phase_start = time.time()

        if preload:
            # Load all agents immediately
            from .optimized_agent_loader import preload_system_agents

            preload_system_agents()
        else:
            # Just setup agent registry, load on demand
            self._setup_agent_registry()

        # Verify PM skills after agent setup (non-blocking)
        self._verify_pm_skills()

        elapsed = time.time() - phase_start
        self.metrics.phases["agents"] = elapsed
        self.metrics.agent_time = elapsed

        return elapsed

    async def initialize_async(self) -> StartupMetrics:
        """Fully async initialization for maximum performance.

        Returns:
            Complete startup metrics
        """
        start = time.time()

        # Run initialization phases concurrently where possible
        tasks = [
            self._async_load_config(),
            self._async_setup_services(),
            self._async_load_agents(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Async initialization error in task {i}: {result}")

        self.metrics.total_time = time.time() - start
        self.logger.info(f"Async startup completed in {self.metrics.total_time:.2f}s")

        return self.metrics

    def _verify_pm_skills(self) -> None:
        """Verify PM skills are deployed. Non-blocking with warnings."""
        try:
            from claude_mpm.services.pm_skills_deployer import PMSkillsDeployerService

            deployer = PMSkillsDeployerService()
            project_dir = Path.cwd()

            result = deployer.verify_pm_skills(project_dir)

            if not result.verified:
                for warning in result.warnings:
                    self.logger.warning(warning)

                # Check if auto-deploy is enabled
                if self._should_auto_deploy_pm_skills():
                    self.logger.info("Auto-deploying PM skills...")
                    deploy_result = deployer.deploy_pm_skills(project_dir)
                    if deploy_result.success:
                        self.logger.info(
                            f"PM skills deployed: {len(deploy_result.deployed)} deployed, "
                            f"{len(deploy_result.skipped)} skipped"
                        )
                    else:
                        self.logger.warning(
                            f"PM skills deployment had errors: {len(deploy_result.errors)}"
                        )
            else:
                # Count skills from registry
                registry = deployer._load_registry(project_dir)
                skill_count = len(registry.get("skills", []))
                self.logger.debug(f"PM skills verified: {skill_count} skills")

        except ImportError:
            self.logger.debug("PM skills deployer not available")
        except Exception as e:
            self.logger.warning(f"PM skills verification failed: {e}")

    def _should_auto_deploy_pm_skills(self) -> bool:
        """Check if auto-deploy is enabled via config.

        Returns:
            True if auto-deploy should be performed (default: True for convenience)
        """
        # Default to True for convenience - PM skills are essential for PM agents
        # Users can disable by setting environment variable or config
        import os

        # Check environment variable override
        env_disable = os.environ.get(
            "CLAUDE_MPM_DISABLE_AUTO_DEPLOY_PM_SKILLS", ""
        ).lower()
        if env_disable in ("1", "true", "yes"):
            return False

        # Default to enabled
        return True

    def _setup_logging(self):
        """Setup basic logging (critical path)."""
        # Minimal logging setup - already handled by logger module
        self.initialized_services.add("logger")

    def _load_minimal_config(self):
        """Load only essential configuration."""
        try:
            # Use cache for config if available
            cache = get_file_cache()
            config_path = Path.home() / ".claude-mpm" / "config.yaml"

            if config_path.exists():
                config = cache.get_or_compute(
                    f"config:{config_path}",
                    lambda: self._parse_config(config_path),
                    ttl=60,
                )
                # Store in a lightweight way
                self._store_config(config)

            self.initialized_services.add("config")
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}")

    def _parse_config(self, path: Path) -> Dict[str, Any]:
        """Parse configuration file."""
        import yaml

        with path.open() as f:
            return yaml.safe_load(f) or {}

    def _store_config(self, config: Dict[str, Any]):
        """Store configuration for later use."""
        # Simple storage without heavy Config class
        sys.modules["__claude_mpm_config__"] = type("Config", (), config)()

    def _setup_cli_parser(self):
        """Setup CLI argument parser."""
        # Defer actual parser creation until needed
        self.lazy_services["cli_parser"] = LazyService(
            service_class=self._create_cli_parser, name="cli_parser"
        )
        self.initialized_services.add("cli_parser")

    def _create_cli_parser(self):
        """Actually create the CLI parser when needed."""
        from ..cli.parser import create_parser

        return create_parser()

    def _create_lazy_services(self):
        """Create lazy wrappers for deferred services."""
        # SocketIO service (heavy, often not needed)
        self.lazy_services["socketio"] = lazy_load(
            self._create_socketio_service, name="socketio"
        )

        # Dashboard service
        self.lazy_services["dashboard"] = lazy_load(
            self._create_dashboard_service, name="dashboard"
        )

        # Memory service
        self.lazy_services["memory"] = lazy_load(
            self._create_memory_service, name="memory"
        )

        # Hook service
        self.lazy_services["hooks"] = lazy_load(self._create_hook_service, name="hooks")

        # Project analyzer (very heavy)
        self.lazy_services["project_analyzer"] = lazy_load(
            self._create_project_analyzer, name="project_analyzer"
        )

        # Track deferred services
        self.metrics.deferred_services = list(self.lazy_services.keys())

    def _create_socketio_service(self):
        """Create SocketIO service when needed."""
        from ..core.socketio_pool import get_connection_pool

        return get_connection_pool()

    def _create_dashboard_service(self):
        """Create dashboard service when needed."""
        # Import only when needed
        from ..services.dashboard import DashboardService

        return DashboardService()

    def _create_memory_service(self):
        """Create memory service when needed."""
        from ..services.memory.indexed_memory import get_indexed_memory

        return get_indexed_memory()

    def _create_hook_service(self):
        """Create hook service when needed."""
        from ..services.hook_service import HookService

        return HookService()

    def _create_project_analyzer(self):
        """Create project analyzer when needed."""
        # This is typically very heavy
        from ..services.project.analyzer import ProjectAnalyzer

        return ProjectAnalyzer()

    def _initialize_all_services(self):
        """Initialize all services immediately (non-lazy mode)."""
        services = ["socketio", "dashboard", "memory", "hooks", "project_analyzer"]

        for service_name in services:
            try:
                creator = getattr(self, f"_create_{service_name}_service", None)
                if creator:
                    creator()
                    self.initialized_services.add(service_name)
            except Exception as e:
                self.logger.warning(f"Failed to initialize {service_name}: {e}")

    def _setup_agent_registry(self):
        """Setup agent registry for on-demand loading."""
        self.lazy_services["agent_registry"] = lazy_load(
            self._create_agent_registry, name="agent_registry"
        )
        self.initialized_services.add("agent_registry")

    def _create_agent_registry(self):
        """Create agent registry when needed."""
        from pathlib import Path

        from ..core.agent_registry import SimpleAgentRegistry

        return SimpleAgentRegistry(Path.cwd())

    async def _async_load_config(self):
        """Load configuration asynchronously."""
        loop = asyncio.get_event_loop()
        config_path = Path.home() / ".claude-mpm" / "config.yaml"

        if config_path.exists():
            config = await loop.run_in_executor(None, self._parse_config, config_path)
            self._store_config(config)

    async def _async_setup_services(self):
        """Setup services asynchronously."""
        # Create all lazy services concurrently
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_lazy_services)

    async def _async_load_agents(self):
        """Load agents asynchronously."""
        from .optimized_agent_loader import get_optimized_loader

        loader = get_optimized_loader()
        agent_paths = self._discover_agent_paths()

        if agent_paths:
            await loader.load_agents_async(agent_paths)

    def _discover_agent_paths(self) -> List[Path]:
        """Discover agent file paths."""
        paths = []
        agent_dirs = [
            Path.cwd() / ".claude" / "agents",
            Path.cwd() / ".claude-mpm" / "agents",
            Path.home() / ".claude-mpm" / "agents",
        ]

        for dir_path in agent_dirs:
            if dir_path.exists():
                paths.extend(dir_path.glob("*.json"))
                paths.extend(dir_path.glob("*.md"))

        return paths

    def defer_import(self, module_name: str) -> Optional[Any]:
        """Defer heavy imports until actually needed.

        Args:
            module_name: Name of module to import

        Returns:
            Imported module or None if not needed yet
        """
        if module_name in self.HEAVY_IMPORTS:
            # Don't import heavy modules during startup
            self.logger.debug(f"Deferring import of {module_name}")
            return None

        # Check cache
        if module_name in self.import_cache:
            return self.import_cache[module_name]

        # Import and cache
        try:
            module = importlib.import_module(module_name)
            self.import_cache[module_name] = module
            return module
        except ImportError as e:
            self.logger.warning(f"Failed to import {module_name}: {e}")
            return None

    def get_service(self, name: str) -> Any:
        """Get a service, initializing if needed.

        Args:
            name: Service name

        Returns:
            Service instance
        """
        if name in self.lazy_services:
            # Lazy service will initialize on first access
            return self.lazy_services[name]

        # Try to create service
        creator = getattr(self, f"_create_{name}_service", None)
        if creator:
            service = creator()
            self.initialized_services.add(name)
            return service

        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get startup performance metrics."""
        self.metrics.total_time = time.time() - self.start_time

        return {
            "total_time": self.metrics.total_time,
            "phases": self.metrics.phases,
            "service_time": self.metrics.service_time,
            "agent_time": self.metrics.agent_time,
            "initialized_services": list(self.initialized_services),
            "deferred_services": self.metrics.deferred_services,
            "lazy_services_initialized": sum(
                1 for s in self.lazy_services.values() if s.is_initialized
            ),
        }


def optimize_startup(mode: str = "lazy") -> OptimizedStartup:
    """Optimize application startup.

    Args:
        mode: Startup mode ('lazy', 'eager', 'async')

    Returns:
        Configured startup manager

    Example:
        # Fast lazy startup
        startup = optimize_startup('lazy')
        startup.initialize_minimal()
        startup.initialize_services(lazy=True)

        # Access services as needed (they initialize on first use)
        memory = startup.get_service('memory')
    """
    startup = OptimizedStartup()

    if mode == "lazy":
        # Minimal startup with lazy loading
        startup.initialize_minimal()
        startup.initialize_services(lazy=True)
        startup.initialize_agents(preload=False)
    elif mode == "eager":
        # Full initialization upfront
        startup.initialize_minimal()
        startup.initialize_services(lazy=False)
        startup.initialize_agents(preload=True)
    elif mode == "async":
        # Async initialization
        asyncio.run(startup.initialize_async())

    return startup


# Global startup manager
_startup_manager: Optional[OptimizedStartup] = None


def get_startup_manager() -> OptimizedStartup:
    """Get or create global startup manager."""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = OptimizedStartup()
    return _startup_manager
