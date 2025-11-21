"""
Debug command for claude-mpm CLI.

This module provides comprehensive debugging tools for developers, including:
- Service debugging (status, dependencies, health)
- Agent debugging (deployed, memory, trace)
- Hook system debugging (list, trace, performance)
- Cache inspection and management
- Performance profiling and analysis
- SocketIO event monitoring
"""

import contextlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ...core.logger import get_logger


def manage_debug(args):
    """
    Main entry point for debug commands.

    Args:
        args: Parsed command-line arguments

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Get logger (it will use the logging level set by main CLI)
    logger = get_logger("debug")

    # Dispatch to appropriate subcommand
    if args.debug_command == "socketio":
        return debug_socketio(args, logger)
    if args.debug_command == "events":
        # Alias for socketio
        return debug_socketio(args, logger)
    if args.debug_command == "connections":
        return debug_connections(args, logger)
    if args.debug_command == "services":
        return debug_services(args, logger)
    if args.debug_command == "agents":
        return debug_agents(args, logger)
    if args.debug_command == "hooks":
        return debug_hooks(args, logger)
    if args.debug_command == "cache":
        return debug_cache(args, logger)
    if args.debug_command == "performance":
        return debug_performance(args, logger)
    logger.error(f"Unknown debug command: {args.debug_command}")
    return 1


def debug_socketio(args, logger):
    """
    Debug SocketIO events using the professional debugging tool.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        from ...tools.socketio_debug import DisplayMode, SocketIODebugger

        logger.info("Starting SocketIO debugger...")

        # Map display mode from args
        mode = DisplayMode.LIVE  # Default
        if args.summary:
            mode = DisplayMode.SUMMARY
        elif args.raw:
            mode = DisplayMode.RAW
        elif args.pretty:
            mode = DisplayMode.PRETTY
        elif args.filter_types:
            mode = DisplayMode.FILTERED

        # Create debugger instance
        debugger = SocketIODebugger(
            host=args.host,
            port=args.port,
            mode=mode,
            filter_types=args.filter_types,
            output_file=Path(args.output) if args.output else None,
            quiet=args.quiet,
            show_raw=args.raw,
            max_reconnect_attempts=getattr(args, "max_reconnect", 10),
            reconnect_delay=getattr(args, "reconnect_delay", 1.0),
        )

        # Run the debugger
        success = debugger.run()

        if success:
            logger.info("SocketIO debugger stopped successfully")
            return 0
        logger.error("SocketIO debugger encountered an error")
        return 1

    except ImportError as e:
        logger.error(f"Failed to import debugging tool: {e}")
        print(
            "❌ Debugging tool not available. Please ensure all dependencies are installed."
        )
        return 1
    except KeyboardInterrupt:
        logger.info("SocketIO debugger interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in SocketIO debugger: {e}", exc_info=True)
        return 1


def debug_connections(args, logger):
    """
    Debug active SocketIO connections and server status.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        import json

        from ...services.port_manager import PortManager

        logger.info("Checking SocketIO connections...")

        # Get port manager
        port_manager = PortManager()

        # Clean up dead instances
        port_manager.cleanup_dead_instances()

        # Get active instances
        active_instances = port_manager.list_active_instances()

        if not active_instances:
            print("No active SocketIO servers found")
            return 0

        print(f"\n📡 Active SocketIO Servers ({len(active_instances)}):")
        print("-" * 60)

        for instance in active_instances:
            port = instance.get("port", "unknown")
            pid = instance.get("pid", "unknown")
            start_time = instance.get("start_time", "unknown")

            print(f"\n🔌 Server on port {port}")
            print(f"   PID: {pid}")
            print(f"   Started: {start_time}")

            # Try to check if it's actually responding
            import socket

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    result = s.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        print("   Status: ✅ Responding")
                    else:
                        print("   Status: ⚠️ Not responding (may be stale)")
            except Exception as e:
                print(f"   Status: ❌ Error checking: {e}")

        print("\n" + "-" * 60)
        print(f"Total: {len(active_instances)} server(s)")

        # If verbose, show full JSON
        if getattr(args, "verbose", False):
            print("\nFull instance data:")
            print(json.dumps(active_instances, indent=2, default=str))

        return 0

    except Exception as e:
        logger.error(f"Failed to check connections: {e}", exc_info=True)
        return 1


def debug_services(args, logger):
    """
    Debug services: list, status, dependencies, and health.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        # Import service-related modules
        from ...core.container import DIContainer

        logger.info("Debugging services...")

        # Get the global container if available
        container = None
        try:
            # Try to get a container instance if it has the method
            if hasattr(DIContainer, "get_instance"):
                container = DIContainer.get_instance()
            else:
                container = DIContainer()
        except Exception:
            # Create a new container if none exists
            container = DIContainer()
            logger.warning("No active container found, created new instance")

        if args.list:
            # List all registered services
            print("\n📦 Registered Services:")
            print("=" * 60)

            services = container._services if hasattr(container, "_services") else {}
            if not services:
                print("No services registered")
            else:
                for service_type, registration in services.items():
                    service_name = (
                        service_type.__name__
                        if hasattr(service_type, "__name__")
                        else str(service_type)
                    )
                    impl_name = (
                        registration.implementation.__name__
                        if hasattr(registration.implementation, "__name__")
                        else str(registration.implementation)
                    )
                    print(f"\n🔧 {service_name}")
                    print(f"   Implementation: {impl_name}")
                    print(f"   Lifetime: {registration.lifetime.value}")
                    if registration.instance:
                        print("   Status: ✅ Instantiated")
                    else:
                        print("   Status: ⏸️ Not instantiated")

        elif args.status:
            # Show service status and health
            print("\n🏥 Service Health Status:")
            print("=" * 60)

            # Try to get monitoring service
            try:
                from ...services.infrastructure.monitoring import MonitoringService

                monitor = MonitoringService()

                # Collect health metrics
                metrics = monitor.collect_metrics()

                print("\n📊 System Metrics:")
                print(f"   CPU Usage: {metrics.get('cpu_percent', 'N/A')}%")
                print(f"   Memory Usage: {metrics.get('memory_percent', 'N/A')}%")
                print(f"   Disk Usage: {metrics.get('disk_percent', 'N/A')}%")

                if "network" in metrics:
                    net = metrics["network"]
                    print("\n🌐 Network:")
                    print(f"   Bytes Sent: {net.get('bytes_sent', 0):,}")
                    print(f"   Bytes Received: {net.get('bytes_recv', 0):,}")

            except Exception as e:
                logger.warning(f"Could not get monitoring metrics: {e}")
                print("⚠️ Monitoring service not available")

        elif args.dependencies:
            # Show service dependency graph
            print("\n🕸️ Service Dependencies:")
            print("=" * 60)

            services = container._services if hasattr(container, "_services") else {}
            if not services:
                print("No services registered")
            else:
                # Build dependency graph
                for service_type, registration in services.items():
                    service_name = (
                        service_type.__name__
                        if hasattr(service_type, "__name__")
                        else str(service_type)
                    )
                    print(f"\n📌 {service_name}")

                    if registration.dependencies:
                        for dep_name, dep_type in registration.dependencies.items():
                            dep_type_name = (
                                dep_type.__name__
                                if hasattr(dep_type, "__name__")
                                else str(dep_type)
                            )
                            print(f"   └─> {dep_name}: {dep_type_name}")
                    else:
                        print("   └─> No dependencies")

        elif args.trace:
            # Trace service resolution
            service_name = args.trace
            print(f"\n🔍 Tracing service resolution for: {service_name}")
            print("=" * 60)

            # Try to find and resolve the service
            services = container._services if hasattr(container, "_services") else {}
            found = False

            for service_type, registration in services.items():
                type_name = (
                    service_type.__name__
                    if hasattr(service_type, "__name__")
                    else str(service_type)
                )
                if service_name in type_name:
                    found = True
                    print(f"\n✅ Found service: {type_name}")
                    print(f"   Implementation: {registration.implementation}")
                    print(f"   Lifetime: {registration.lifetime.value}")

                    # Try to resolve
                    try:
                        instance = container.resolve(service_type)
                        print("   Resolution: ✅ Success")
                        print(f"   Instance Type: {type(instance).__name__}")
                    except Exception as e:
                        print("   Resolution: ❌ Failed")
                        print(f"   Error: {e}")
                    break

            if not found:
                print(f"❌ Service '{service_name}' not found")

        else:
            # Default: show summary
            print("\n📊 Services Summary:")
            print("=" * 60)
            services = container._services if hasattr(container, "_services") else {}
            print(f"Total Registered: {len(services)}")

            # Count by lifetime
            lifetime_counts = defaultdict(int)
            instantiated = 0

            for registration in services.values():
                lifetime_counts[registration.lifetime.value] += 1
                if registration.instance:
                    instantiated += 1

            print("\nLifetime Distribution:")
            for lifetime, count in lifetime_counts.items():
                print(f"   {lifetime}: {count}")

            print(f"\nInstantiated: {instantiated}/{len(services)}")

        return 0

    except Exception as e:
        logger.error(f"Failed to debug services: {e}", exc_info=True)
        return 1


def debug_agents(args, logger):
    """
    Debug agents: deployed agents, memory, and tracing.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        logger.info("Debugging agents...")

        if args.deployed:
            # List deployed agents
            from pathlib import Path

            print("\n🤖 Deployed Agents:")
            print("=" * 60)

            # Check different deployment locations
            locations = [
                Path.home() / ".claude" / "agents",
                Path.cwd() / ".claude" / "agents",
            ]

            total_agents = 0
            for location in locations:
                if location.exists():
                    print(f"\n📁 Location: {location}")
                    agent_files = list(location.glob("*.md"))
                    if agent_files:
                        for agent_file in agent_files:
                            agent_name = agent_file.stem
                            size = agent_file.stat().st_size
                            modified = datetime.fromtimestamp(
                                agent_file.stat().st_mtime, tz=timezone.utc
                            )
                            print(f"   • {agent_name}")
                            print(f"     Size: {size:,} bytes")
                            print(
                                f"     Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            total_agents += 1
                    else:
                        print("   No agents found")

            print(f"\nTotal Agents: {total_agents}")

        elif args.memory:
            # Show agent memory status
            from ...services.agents.memory import get_memory_manager

            print("\n🧠 Agent Memory Status:")
            print("=" * 60)

            try:
                get_memory_manager()

                # List all memory files
                memory_dir = Path.home() / ".claude" / "memory"
                if not memory_dir.exists():
                    memory_dir = Path.cwd() / ".claude" / "memory"

                if memory_dir.exists():
                    memory_files = list(memory_dir.glob("*.json"))

                    total_size = 0
                    for mem_file in memory_files:
                        agent_name = mem_file.stem
                        size = mem_file.stat().st_size

                        # Try to load and analyze memory
                        try:
                            with mem_file.open() as f:
                                memory_data = json.load(f)

                            entry_count = (
                                len(memory_data) if isinstance(memory_data, list) else 1
                            )
                            print(f"\n📝 Agent: {agent_name}")
                            print(f"   File: {mem_file}")
                            print(f"   Size: {size:,} bytes")
                            print(f"   Entries: {entry_count}")
                            total_size += size

                            # Show recent entries if requested
                            if (
                                args.verbose
                                and isinstance(memory_data, list)
                                and memory_data
                            ):
                                print("   Recent entries:")
                                for entry in memory_data[-3:]:
                                    timestamp = entry.get("timestamp", "N/A")
                                    category = entry.get("category", "N/A")
                                    print(f"     - [{timestamp}] {category}")

                        except Exception as e:
                            print(f"\n📝 Agent: {agent_name}")
                            print(f"   ⚠️ Could not parse memory: {e}")

                    print("\n📊 Summary:")
                    print(f"   Total Memory Files: {len(memory_files)}")
                    print(f"   Total Size: {total_size:,} bytes")
                else:
                    print("No memory directory found")

            except Exception as e:
                logger.warning(f"Could not access memory manager: {e}")
                print("⚠️ Memory manager not available")

        elif args.trace:
            # Trace agent execution
            agent_name = args.trace
            print(f"\n🔍 Tracing agent: {agent_name}")
            print("=" * 60)

            # Look for the agent
            from pathlib import Path

            # Check different locations
            locations = [
                Path.home() / ".claude" / "agents",
                Path.cwd() / ".claude" / "agents",
            ]

            found = False
            for location in locations:
                agent_file = location / f"{agent_name}.md"
                if agent_file.exists():
                    found = True
                    print(f"✅ Agent found: {agent_name}")
                    print(f"   Location: {agent_file}")
                    print(f"   Size: {agent_file.stat().st_size:,} bytes")

                    # Read first few lines for type detection
                    with agent_file.open() as f:
                        lines = f.readlines()[:10]
                        for line in lines:
                            if "role:" in line.lower():
                                print(f"   Role: {line.split(':')[1].strip()}")
                            elif "type:" in line.lower():
                                print(f"   Type: {line.split(':')[1].strip()}")
                    break

            if not found:
                print(f"❌ Agent '{agent_name}' not found")

        else:
            # Default: show summary
            print("\n📊 Agents Summary:")
            print("=" * 60)

            # Count agents in different locations
            locations = [
                (Path.home() / ".claude" / "agents", "User"),
                (Path.cwd() / ".claude" / "agents", "Project"),
            ]

            total = 0
            for location, label in locations:
                if location.exists():
                    count = len(list(location.glob("*.md")))
                    print(f"{label} Agents: {count}")
                    total += count

            print(f"\nTotal Agents: {total}")

        return 0

    except Exception as e:
        logger.error(f"Failed to debug agents: {e}", exc_info=True)
        return 1


def debug_hooks(args, logger):
    """
    Debug hook system: list hooks, trace execution, analyze performance.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        from ...services.hook_service import HookService

        logger.info("Debugging hooks...")

        # Try to get the hook service
        hook_service = HookService()

        if args.list:
            # List all registered hooks
            print("\n🪝 Registered Hooks:")
            print("=" * 60)

            print("\n📥 Pre-Delegation Hooks:")
            if hook_service.pre_delegation_hooks:
                for hook in hook_service.pre_delegation_hooks:
                    print(f"   • {hook.name}")
                    print(f"     Priority: {hook.priority}")
                    print(f"     Enabled: {hook.enabled}")
                    if hasattr(hook, "description"):
                        print(f"     Description: {hook.description}")
            else:
                print("   No pre-delegation hooks registered")

            print("\n📤 Post-Delegation Hooks:")
            if hook_service.post_delegation_hooks:
                for hook in hook_service.post_delegation_hooks:
                    print(f"   • {hook.name}")
                    print(f"     Priority: {hook.priority}")
                    print(f"     Enabled: {hook.enabled}")
                    if hasattr(hook, "description"):
                        print(f"     Description: {hook.description}")
            else:
                print("   No post-delegation hooks registered")

            # Show statistics
            print("\n📊 Hook Statistics:")
            print(
                f"   Pre-delegation executed: {hook_service.stats.get('pre_delegation_executed', 0)}"
            )
            print(
                f"   Post-delegation executed: {hook_service.stats.get('post_delegation_executed', 0)}"
            )
            print(f"   Errors: {hook_service.stats.get('errors', 0)}")

        elif args.trace:
            # Trace hook execution
            hook_name = args.trace
            print(f"\n🔍 Tracing hook: {hook_name}")
            print("=" * 60)

            found = False

            # Search in pre-delegation hooks
            for hook in hook_service.pre_delegation_hooks:
                if hook_name.lower() in hook.name.lower():
                    found = True
                    print(f"\n✅ Found pre-delegation hook: {hook.name}")
                    print(f"   Priority: {hook.priority}")
                    print(f"   Enabled: {hook.enabled}")
                    print(f"   Type: {type(hook).__name__}")

                    # Test execution
                    if args.test:
                        print("\n🧪 Test Execution:")
                        from ...hooks.base_hook import HookContext

                        test_context = HookContext(
                            agent_name="test_agent",
                            task="test_task",
                            metadata={"test": True},
                        )

                        try:
                            start_time = time.time()
                            result = hook.execute(test_context)
                            elapsed = time.time() - start_time

                            print("   Status: ✅ Success")
                            print(f"   Execution Time: {elapsed:.3f}s")
                            print(f"   Modified: {result.context_modified}")
                            if result.error:
                                print(f"   Error: {result.error}")
                        except Exception as e:
                            print("   Status: ❌ Failed")
                            print(f"   Error: {e}")
                    break

            # Search in post-delegation hooks
            for hook in hook_service.post_delegation_hooks:
                if hook_name.lower() in hook.name.lower():
                    found = True
                    print(f"\n✅ Found post-delegation hook: {hook.name}")
                    print(f"   Priority: {hook.priority}")
                    print(f"   Enabled: {hook.enabled}")
                    print(f"   Type: {type(hook).__name__}")
                    break

            if not found:
                print(f"❌ Hook '{hook_name}' not found")

        elif args.performance:
            # Analyze hook performance
            print("\n⚡ Hook Performance Analysis:")
            print("=" * 60)

            # Performance test each hook
            print("\n📥 Pre-Delegation Hooks Performance:")
            for hook in hook_service.pre_delegation_hooks:
                from ...hooks.base_hook import HookContext

                test_context = HookContext(
                    agent_name="perf_test", task="performance test", metadata={}
                )

                # Run multiple iterations
                iterations = 10
                times = []

                for _ in range(iterations):
                    try:
                        start = time.time()
                        hook.execute(test_context)
                        elapsed = time.time() - start
                        times.append(elapsed)
                    except Exception:
                        pass

                if times:
                    avg_time = sum(times) / len(times)
                    min_time = min(times)
                    max_time = max(times)

                    print(f"\n   {hook.name}:")
                    print(f"     Average: {avg_time * 1000:.2f}ms")
                    print(f"     Min: {min_time * 1000:.2f}ms")
                    print(f"     Max: {max_time * 1000:.2f}ms")

        else:
            # Default: show summary
            print("\n📊 Hooks Summary:")
            print("=" * 60)
            print(f"Pre-delegation hooks: {len(hook_service.pre_delegation_hooks)}")
            print(f"Post-delegation hooks: {len(hook_service.post_delegation_hooks)}")
            print("\nExecution Statistics:")
            print(
                f"   Pre-delegation executed: {hook_service.stats.get('pre_delegation_executed', 0)}"
            )
            print(
                f"   Post-delegation executed: {hook_service.stats.get('post_delegation_executed', 0)}"
            )
            print(f"   Total errors: {hook_service.stats.get('errors', 0)}")

        return 0

    except Exception as e:
        logger.error(f"Failed to debug hooks: {e}", exc_info=True)
        return 1


def debug_cache(args, logger):
    """
    Debug cache: inspect, clear, and analyze cache performance.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        from ...services.core.cache_manager import CacheManager

        logger.info("Debugging cache...")

        if args.inspect:
            # Inspect cache contents
            print("\n🗄️ Cache Inspection:")
            print("=" * 60)

            # Get cache directory
            cache_dir = Path.home() / ".cache" / "claude-mpm"
            if not cache_dir.exists():
                print("No cache directory found")
                return 0

            # Analyze cache files
            cache_files = list(cache_dir.rglob("*"))
            total_size = 0
            file_count = 0

            categories = defaultdict(list)

            for file_path in cache_files:
                if file_path.is_file():
                    file_count += 1
                    size = file_path.stat().st_size
                    total_size += size

                    # Categorize by parent directory
                    category = file_path.parent.name
                    categories[category].append((file_path.name, size))

            print("\n📊 Cache Statistics:")
            print(f"   Location: {cache_dir}")
            print(f"   Total Files: {file_count}")
            print(
                f"   Total Size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)"
            )

            print("\n📁 Categories:")
            for category, files in categories.items():
                cat_size = sum(size for _, size in files)
                print(f"\n   {category}:")
                print(f"     Files: {len(files)}")
                print(f"     Size: {cat_size:,} bytes")

                if args.verbose:
                    # Show individual files
                    for name, size in sorted(files, key=lambda x: x[1], reverse=True)[
                        :5
                    ]:
                        print(f"       • {name}: {size:,} bytes")

        elif args.clear:
            # Clear cache
            print("\n🧹 Clearing cache...")
            print("=" * 60)

            cache_dir = Path.home() / ".cache" / "claude-mpm"

            if not cache_dir.exists():
                print("No cache to clear")
                return 0

            # Count files before clearing
            files_before = list(cache_dir.rglob("*"))
            file_count = len([f for f in files_before if f.is_file()])

            if (
                args.confirm
                or input(f"Clear {file_count} cache files? (y/N): ").lower() == "y"
            ):
                # Clear cache
                import shutil

                try:
                    shutil.rmtree(cache_dir)
                    print(f"✅ Cleared {file_count} cache files")
                except Exception as e:
                    print(f"❌ Failed to clear cache: {e}")
                    return 1
            else:
                print("Cache clear cancelled")

        elif args.stats:
            # Show cache performance statistics
            print("\n📈 Cache Performance Statistics:")
            print("=" * 60)

            # Try to get cache manager
            cache_manager = CacheManager()

            # Simulate cache operations to gather stats
            print("\n🔄 Cache TTL Configuration:")
            print(f"   Capabilities TTL: {cache_manager.capabilities_ttl}s")
            print(f"   Deployed Agents TTL: {cache_manager.deployed_agents_ttl}s")
            print(f"   Metadata TTL: {cache_manager.metadata_ttl}s")
            print(f"   Memories TTL: {cache_manager.memories_ttl}s")

            # Check cache status
            current_time = time.time()

            print("\n⏱️ Cache Status:")

            # Check capabilities cache
            if cache_manager._capabilities_cache:
                age = current_time - cache_manager._capabilities_cache_time
                status = (
                    "✅ Valid" if age < cache_manager.capabilities_ttl else "❌ Expired"
                )
                print(f"   Capabilities: {status} (age: {age:.1f}s)")
            else:
                print("   Capabilities: ⚫ Empty")

            # Check deployed agents cache
            if cache_manager._deployed_agents_cache:
                age = current_time - cache_manager._deployed_agents_cache_time
                status = (
                    "✅ Valid"
                    if age < cache_manager.deployed_agents_ttl
                    else "❌ Expired"
                )
                print(f"   Deployed Agents: {status} (age: {age:.1f}s)")
            else:
                print("   Deployed Agents: ⚫ Empty")

        else:
            # Default: show summary
            print("\n📊 Cache Summary:")
            print("=" * 60)

            cache_dir = Path.home() / ".cache" / "claude-mpm"

            if cache_dir.exists():
                cache_files = list(cache_dir.rglob("*"))
                file_count = len([f for f in cache_files if f.is_file()])
                total_size = sum(f.stat().st_size for f in cache_files if f.is_file())

                print(f"Location: {cache_dir}")
                print(f"Files: {file_count}")
                print(f"Size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
            else:
                print("No cache found")

        return 0

    except Exception as e:
        logger.error(f"Failed to debug cache: {e}", exc_info=True)
        return 1


def debug_performance(args, logger):
    """
    Debug performance: profile operations, analyze bottlenecks.

    Args:
        args: Parsed command-line arguments
        logger: Logger instance

    Returns:
        int: Exit code
    """
    try:
        logger.info("Running performance analysis...")

        print("\n⚡ Performance Analysis:")
        print("=" * 60)

        if args.profile:
            # Profile specific operation
            operation = args.profile
            print(f"\n🔍 Profiling operation: {operation}")

            import cProfile
            import pstats
            from io import StringIO

            profiler = cProfile.Profile()

            # Map operation to actual function
            operations = {
                "agent_load": lambda: _profile_agent_load(),
                "service_init": lambda: _profile_service_init(),
                "cache_ops": lambda: _profile_cache_operations(),
                "memory_ops": lambda: _profile_memory_operations(),
            }

            if operation in operations:
                print("Starting profile...")

                profiler.enable()
                start_time = time.time()

                try:
                    operations[operation]()
                except Exception as e:
                    print(f"⚠️ Operation failed: {e}")

                elapsed = time.time() - start_time
                profiler.disable()

                # Print statistics
                print(f"\n✅ Profile complete (elapsed: {elapsed:.3f}s)")

                s = StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
                ps.print_stats(20)  # Top 20 functions

                print("\n📊 Top Functions by Cumulative Time:")
                print(s.getvalue())
            else:
                print(f"❌ Unknown operation: {operation}")
                print("   Available: agent_load, service_init, cache_ops, memory_ops")

        elif args.benchmark:
            # Run benchmarks
            print("\n🏃 Running benchmarks...")

            benchmarks = [
                ("Service Container Resolution", _benchmark_service_resolution),
                ("Cache Operations", _benchmark_cache_operations),
                ("Agent Loading", _benchmark_agent_loading),
                ("Hook Execution", _benchmark_hook_execution),
            ]

            results = []

            for name, benchmark_func in benchmarks:
                print(f"\n▶️ {name}...")
                try:
                    result = benchmark_func()
                    results.append((name, result))
                    print(f"   Time: {result['time']:.3f}s")
                    print(f"   Ops/sec: {result.get('ops_per_sec', 'N/A')}")
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    results.append((name, {"error": str(e)}))

            # Summary
            print("\n📊 Benchmark Summary:")
            print("=" * 60)
            for name, result in results:
                if "error" in result:
                    print(f"{name}: ❌ Failed")
                else:
                    print(f"{name}: {result['time']:.3f}s")

        else:
            # Default: show system performance
            print("\n📊 System Performance:")

            try:
                import psutil
            except ImportError:
                print("⚠️ psutil not installed. Install with: pip install psutil")
                return 0

            # CPU info
            print("\n🖥️ CPU:")
            print(f"   Usage: {psutil.cpu_percent(interval=1)}%")
            print(
                f"   Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical"
            )

            # Memory info
            mem = psutil.virtual_memory()
            print("\n💾 Memory:")
            print(f"   Total: {mem.total / 1024 / 1024 / 1024:.2f} GB")
            print(f"   Used: {mem.used / 1024 / 1024 / 1024:.2f} GB ({mem.percent}%)")
            print(f"   Available: {mem.available / 1024 / 1024 / 1024:.2f} GB")

            # Disk info
            disk = psutil.disk_usage("/")
            print("\n💿 Disk:")
            print(f"   Total: {disk.total / 1024 / 1024 / 1024:.2f} GB")
            print(f"   Used: {disk.used / 1024 / 1024 / 1024:.2f} GB ({disk.percent}%)")
            print(f"   Free: {disk.free / 1024 / 1024 / 1024:.2f} GB")

            # Process info
            process = psutil.Process()
            print("\n📦 Current Process:")
            print(f"   PID: {process.pid}")
            print(f"   Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            print(f"   CPU: {process.cpu_percent()}%")
            print(f"   Threads: {process.num_threads()}")

        return 0

    except Exception as e:
        logger.error(f"Failed to run performance analysis: {e}", exc_info=True)
        return 1


# Helper functions for profiling
def _profile_agent_load():
    """Profile agent loading operation."""
    from ...services.agents.deployment import AgentDeploymentService

    service = AgentDeploymentService()
    # Simulate loading agents
    for _ in range(10):
        with contextlib.suppress(Exception):
            service.list_agents()


def _profile_service_init():
    """Profile service initialization."""
    from ...core.container import DIContainer

    container = DIContainer()
    # Register and resolve services

    class TestService:
        pass

    for i in range(20):
        container.register(f"TestService{i}", TestService)
        container.resolve(f"TestService{i}")


def _profile_cache_operations():
    """Profile cache operations."""
    from ...services.core.cache_manager import CacheManager

    cache = CacheManager()

    # Simulate cache operations
    for i in range(100):
        cache.set_capabilities(f"test_cap_{i}")
        cache.get_capabilities()
        cache.invalidate_capabilities()


def _profile_memory_operations():
    """Profile memory operations."""
    from ...services.agents.memory import AgentMemoryManager

    memory = AgentMemoryManager("test_agent")

    # Simulate memory operations
    for i in range(50):
        try:
            memory.add_memory(f"category_{i}", {"data": f"test_{i}"})
            memory.get_memories()
        except Exception:
            pass


# Helper functions for benchmarking
def _benchmark_service_resolution() -> Dict[str, Any]:
    """Benchmark service container resolution."""
    from ...core.container import DIContainer

    container = DIContainer()

    class TestService:
        pass

    container.register(TestService, TestService)

    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        container.resolve(TestService)

    elapsed = time.time() - start

    return {
        "time": elapsed,
        "iterations": iterations,
        "ops_per_sec": iterations / elapsed,
    }


def _benchmark_cache_operations() -> Dict[str, Any]:
    """Benchmark cache operations."""
    from ...services.core.cache_manager import CacheManager

    cache = CacheManager()
    iterations = 1000

    start = time.time()

    for i in range(iterations):
        cache.set_capabilities(f"test_{i}")
        cache.get_capabilities()

    elapsed = time.time() - start

    return {
        "time": elapsed,
        "iterations": iterations * 2,  # set + get
        "ops_per_sec": (iterations * 2) / elapsed,
    }


def _benchmark_agent_loading() -> Dict[str, Any]:
    """Benchmark agent loading."""
    from pathlib import Path

    iterations = 100
    start = time.time()

    for _ in range(iterations):
        # Simulate agent discovery
        agent_dir = Path.home() / ".claude" / "agents"
        if agent_dir.exists():
            list(agent_dir.glob("*.md"))

    elapsed = time.time() - start

    return {
        "time": elapsed,
        "iterations": iterations,
        "ops_per_sec": iterations / elapsed,
    }


def _benchmark_hook_execution() -> Dict[str, Any]:
    """Benchmark hook execution."""
    from ...hooks.base_hook import HookContext, HookResult, PreDelegationHook

    class TestHook(PreDelegationHook):
        def execute(self, context: HookContext) -> HookResult:
            return HookResult(context=context)

    hook = TestHook(name="test", priority=0)
    context = HookContext(agent_name="test", task="test", metadata={})

    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        hook.execute(context)

    elapsed = time.time() - start

    return {
        "time": elapsed,
        "iterations": iterations,
        "ops_per_sec": iterations / elapsed,
    }


def add_debug_parser(subparsers):
    """
    Add the debug subparser with debugging commands.

    This function is called by the main parser to add debug commands.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured debug subparser
    """

    # Main debug parser
    debug_parser = subparsers.add_parser(
        "debug",
        help="Development debugging tools",
        description="Tools for debugging and monitoring claude-mpm components",
    )

    # Add debug subcommands
    debug_subparsers = debug_parser.add_subparsers(
        dest="debug_command", help="Debug commands", metavar="SUBCOMMAND"
    )

    # SocketIO debugging
    socketio_parser = debug_subparsers.add_parser(
        "socketio",
        help="Debug SocketIO events in real-time",
        aliases=["events"],
        description="Professional SocketIO event monitoring and analysis tool",
    )

    # Connection options
    socketio_parser.add_argument(
        "--host", default="localhost", help="SocketIO server host (default: localhost)"
    )
    socketio_parser.add_argument(
        "--port", type=int, default=8765, help="SocketIO server port (default: 8765)"
    )

    # Display options
    display_group = socketio_parser.add_mutually_exclusive_group()
    display_group.add_argument(
        "--live",
        action="store_true",
        default=True,
        help="Live event monitoring (default)",
    )
    display_group.add_argument(
        "--summary", action="store_true", help="Show aggregated statistics and summary"
    )
    display_group.add_argument(
        "--raw", action="store_true", help="Display raw JSON output"
    )
    display_group.add_argument(
        "--pretty", action="store_true", help="Enhanced formatted output with colors"
    )

    # Filtering
    socketio_parser.add_argument(
        "--filter",
        nargs="+",
        dest="filter_types",
        help="Filter specific event types (e.g., PreToolUse PostToolUse)",
    )

    # Output options
    socketio_parser.add_argument(
        "--output", "-o", help="Save events to file (JSONL format)"
    )
    socketio_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output except errors (useful with --output)",
    )

    # Connection resilience
    socketio_parser.add_argument(
        "--max-reconnect",
        type=int,
        default=10,
        help="Maximum reconnection attempts (default: 10)",
    )
    socketio_parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=1.0,
        help="Reconnection delay in seconds (default: 1.0)",
    )

    # Connection debugging
    connections_parser = debug_subparsers.add_parser(
        "connections",
        help="Show active SocketIO server connections",
        description="Display information about active SocketIO servers and their status",
    )
    connections_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed connection information",
    )

    # Services debugging
    services_parser = debug_subparsers.add_parser(
        "services",
        help="Debug service container and dependencies",
        description="Inspect services, dependencies, and health status",
    )
    services_group = services_parser.add_mutually_exclusive_group()
    services_group.add_argument(
        "--list", action="store_true", help="List all registered services"
    )
    services_group.add_argument(
        "--status", action="store_true", help="Show service health status"
    )
    services_group.add_argument(
        "--dependencies", action="store_true", help="Show service dependency graph"
    )
    services_group.add_argument(
        "--trace",
        metavar="SERVICE",
        help="Trace service resolution for specific service",
    )

    # Agents debugging
    agents_parser = debug_subparsers.add_parser(
        "agents",
        help="Debug deployed agents and memory",
        description="Inspect deployed agents, memory, and traces",
    )
    agents_group = agents_parser.add_mutually_exclusive_group()
    agents_group.add_argument(
        "--deployed", action="store_true", help="List all deployed agents"
    )
    agents_group.add_argument(
        "--memory", action="store_true", help="Show agent memory status"
    )
    agents_group.add_argument(
        "--trace", metavar="AGENT", help="Trace specific agent execution"
    )
    agents_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )

    # Hooks debugging
    hooks_parser = debug_subparsers.add_parser(
        "hooks",
        help="Debug hook system",
        description="List hooks, trace execution, analyze performance",
    )
    hooks_group = hooks_parser.add_mutually_exclusive_group()
    hooks_group.add_argument(
        "--list", action="store_true", help="List all registered hooks"
    )
    hooks_group.add_argument(
        "--trace", metavar="HOOK", help="Trace specific hook execution"
    )
    hooks_group.add_argument(
        "--performance", action="store_true", help="Analyze hook performance"
    )
    hooks_parser.add_argument(
        "--test", action="store_true", help="Run test execution when tracing"
    )

    # Cache debugging
    cache_parser = debug_subparsers.add_parser(
        "cache",
        help="Debug cache system",
        description="Inspect, clear, and analyze cache",
    )
    cache_group = cache_parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--inspect", action="store_true", help="Inspect cache contents"
    )
    cache_group.add_argument("--clear", action="store_true", help="Clear all cache")
    cache_group.add_argument(
        "--stats", action="store_true", help="Show cache performance statistics"
    )
    cache_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed cache information"
    )
    cache_parser.add_argument(
        "--confirm",
        "-y",
        action="store_true",
        help="Skip confirmation for clear operation",
    )

    # Performance debugging
    performance_parser = debug_subparsers.add_parser(
        "performance",
        help="Performance profiling and analysis",
        description="Profile operations and analyze bottlenecks",
    )
    perf_group = performance_parser.add_mutually_exclusive_group()
    perf_group.add_argument(
        "--profile",
        metavar="OPERATION",
        help="Profile specific operation (agent_load, service_init, cache_ops, memory_ops)",
    )
    perf_group.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmarks"
    )

    return debug_parser
