from pathlib import Path

"""
Dynamic agent dependency loader for runtime dependency management.

This module handles loading and checking dependencies for deployed agents
at runtime, rather than requiring all possible agent dependencies to be
installed upfront.
"""

import hashlib
import json
import logging
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

from packaging.requirements import InvalidRequirement, Requirement

from ..core.logger import get_logger

logger = get_logger(__name__)


class AgentDependencyLoader:
    """
    Dynamically loads and manages dependencies for deployed agents.

    Only checks/installs dependencies for agents that are actually deployed
    and being used, rather than all possible agents.
    """

    def __init__(self, auto_install: bool = False):
        """
        Initialize the agent dependency loader.

        Args:
            auto_install: If True, automatically install missing dependencies.
                         If False, only check and report missing dependencies.
        """
        self.auto_install = auto_install
        self.deployed_agents: Dict[str, Path] = {}
        self.agent_dependencies: Dict[str, Dict] = {}
        self.missing_dependencies: Dict[str, List[str]] = {}
        self.checked_packages: Set[str] = set()
        self.deployment_state_file = (
            Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state"
        )

    def discover_deployed_agents(self) -> Dict[str, Path]:
        """
        Discover which agents are currently deployed in .claude/agents/

        Returns:
            Dictionary mapping agent IDs to their file paths
        """
        deployed_agents = {}
        claude_agents_dir = Path.cwd() / ".claude" / "agents"

        if not claude_agents_dir.exists():
            logger.debug("No .claude/agents directory found")
            return deployed_agents

        # Scan for deployed agent markdown files
        for agent_file in claude_agents_dir.glob("*.md"):
            agent_id = agent_file.stem
            deployed_agents[agent_id] = agent_file
            logger.debug(f"Found deployed agent: {agent_id}")

        logger.info(f"Discovered {len(deployed_agents)} deployed agents")
        self.deployed_agents = deployed_agents
        return deployed_agents

    def load_agent_dependencies(self) -> Dict[str, Dict]:
        """
        Load dependency information for deployed agents from their source configs.

        Returns:
            Dictionary mapping agent IDs to their dependency requirements
        """
        agent_dependencies = {}

        # Define paths to check for agent configs (in precedence order)
        config_paths = [
            Path.cwd() / ".claude-mpm" / "agents",  # PROJECT
            Path.home() / ".claude-mpm" / "agents",  # USER
            Path.cwd() / "src" / "claude_mpm" / "agents" / "templates",  # SYSTEM
        ]

        for agent_id in self.deployed_agents:
            # Try to find the agent's JSON config
            for config_dir in config_paths:
                config_file = config_dir / f"{agent_id}.json"
                if config_file.exists():
                    try:
                        with open(config_file) as f:
                            config = json.load(f)
                            if "dependencies" in config:
                                agent_dependencies[agent_id] = config["dependencies"]
                                logger.debug(f"Loaded dependencies for {agent_id}")
                                break
                    except Exception as e:
                        logger.warning(f"Failed to load config for {agent_id}: {e}")

        self.agent_dependencies = agent_dependencies
        logger.info(f"Loaded dependencies for {len(agent_dependencies)} agents")
        return agent_dependencies

    def check_python_dependency(self, package_spec: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a Python package dependency is satisfied.

        Args:
            package_spec: Package specification (e.g., "pandas>=2.0.0")

        Returns:
            Tuple of (is_satisfied, installed_version)
        """
        try:
            req = Requirement(package_spec)
            package_name = req.name

            # Skip if already checked
            if package_name in self.checked_packages:
                return True, None

            # Check if it's a built-in module first
            if self._is_builtin_module(package_name):
                self.checked_packages.add(package_name)
                return True, "built-in"

            # Try to import and check version
            try:
                import importlib.metadata

                try:
                    version = importlib.metadata.version(package_name)
                    self.checked_packages.add(package_name)

                    # Check if version satisfies requirement
                    if req.specifier.contains(version):
                        return True, version
                    logger.debug(
                        f"{package_name} {version} does not satisfy {req.specifier}"
                    )
                    return False, version

                except importlib.metadata.PackageNotFoundError:
                    return False, None

            except ImportError:
                # Fallback for older Python versions
                try:
                    import pkg_resources

                    version = pkg_resources.get_distribution(package_name).version
                    self.checked_packages.add(package_name)

                    if req.specifier.contains(version):
                        return True, version
                    return False, version

                except pkg_resources.DistributionNotFound:
                    return False, None

        except InvalidRequirement as e:
            logger.warning(f"Invalid requirement specification: {package_spec}: {e}")
            return False, None

    def _is_builtin_module(self, module_name: str) -> bool:
        """
        Check if a module is a built-in Python module.

        Args:
            module_name: Name of the module to check

        Returns:
            True if the module is built-in, False otherwise
        """
        # List of common built-in modules that don't have distribution metadata
        builtin_modules = {
            "json",
            "pathlib",
            "os",
            "sys",
            "datetime",
            "time",
            "math",
            "random",
            "collections",
            "itertools",
            "functools",
            "operator",
            "copy",
            "pickle",
            "sqlite3",
            "urllib",
            "http",
            "email",
            "html",
            "xml",
            "csv",
            "configparser",
            "logging",
            "unittest",
            "doctest",
            "pdb",
            "profile",
            "timeit",
            "trace",
            "gc",
            "weakref",
            "types",
            "inspect",
            "importlib",
            "pkgutil",
            "modulefinder",
            "runpy",
            "ast",
            "symtable",
            "keyword",
            "token",
            "tokenize",
            "tabnanny",
            "pyclbr",
            "py_compile",
            "compileall",
            "dis",
            "pickletools",
            "platform",
            "ctypes",
            "struct",
            "codecs",
            "unicodedata",
            "stringprep",
            "readline",
            "rlcompleter",
            "subprocess",
            "sched",
            "queue",
            "threading",
            "multiprocessing",
            "concurrent",
            "asyncio",
            "socket",
            "ssl",
            "select",
            "selectors",
            "signal",
            "mmap",
            "errno",
            "io",
            "tempfile",
            "glob",
            "fnmatch",
            "linecache",
            "shutil",
            "stat",
            "filecmp",
            "tarfile",
            "zipfile",
            "gzip",
            "bz2",
            "lzma",
            "zlib",
            "hashlib",
            "hmac",
            "secrets",
            "base64",
            "binascii",
            "quopri",
            "uu",
            "string",
            "re",
            "difflib",
            "textwrap",
            "calendar",
            "locale",
            "gettext",
            "argparse",
            "optparse",
            "getopt",
            "shlex",
            "cmd",
            "pprint",
            "reprlib",
            "enum",
            "numbers",
            "decimal",
            "fractions",
            "statistics",
            "array",
            "bisect",
            "heapq",
            "contextlib",
            "abc",
            "atexit",
            "traceback",
            "warnings",
            "dataclasses",
            "graphlib",
        }

        # Check if it's in our known built-in modules
        if module_name in builtin_modules:
            return True

        # Try to import it and check if it's a built-in module
        try:
            import importlib.util

            spec = importlib.util.find_spec(module_name)
            if spec is not None and spec.origin is None:
                # Built-in modules have spec.origin as None
                return True
        except (ImportError, ModuleNotFoundError, ValueError):
            pass

        return False

    def check_system_dependency(self, command: str) -> bool:
        """
        Check if a system command is available in PATH.

        Args:
            command: System command to check (e.g., "git")

        Returns:
            True if command is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    def analyze_dependencies(self) -> Dict[str, Dict]:
        """
        Analyze dependencies for all deployed agents.

        Returns:
            Analysis results including missing and satisfied dependencies
        """
        results = {
            "agents": {},
            "summary": {
                "total_agents": len(self.deployed_agents),
                "agents_with_deps": 0,
                "missing_python": [],
                "missing_system": [],
                "satisfied_python": [],
                "satisfied_system": [],
            },
        }

        for agent_id, deps in self.agent_dependencies.items():
            agent_result = {
                "python": {"satisfied": [], "missing": [], "outdated": []},
                "system": {"satisfied": [], "missing": []},
            }

            # Check Python dependencies
            if "python" in deps:
                for dep_spec in deps["python"]:
                    is_satisfied, version = self.check_python_dependency(dep_spec)
                    if is_satisfied:
                        agent_result["python"]["satisfied"].append(dep_spec)
                        if dep_spec not in results["summary"]["satisfied_python"]:
                            results["summary"]["satisfied_python"].append(dep_spec)
                    elif version:  # Installed but wrong version
                        agent_result["python"]["outdated"].append(
                            f"{dep_spec} (have {version})"
                        )
                    else:  # Not installed
                        agent_result["python"]["missing"].append(dep_spec)
                        if dep_spec not in results["summary"]["missing_python"]:
                            results["summary"]["missing_python"].append(dep_spec)

            # Check system dependencies
            if "system" in deps:
                for command in deps["system"]:
                    if self.check_system_dependency(command):
                        agent_result["system"]["satisfied"].append(command)
                        if command not in results["summary"]["satisfied_system"]:
                            results["summary"]["satisfied_system"].append(command)
                    else:
                        agent_result["system"]["missing"].append(command)
                        if command not in results["summary"]["missing_system"]:
                            results["summary"]["missing_system"].append(command)

            results["agents"][agent_id] = agent_result
            if "python" in deps or "system" in deps:
                results["summary"]["agents_with_deps"] += 1

        return results

    def check_python_compatibility(
        self, dependencies: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Check which dependencies are compatible with current Python version.

        Args:
            dependencies: List of package specifications to check

        Returns:
            Tuple of (compatible_deps, incompatible_deps)
        """
        import sys

        compatible = []
        incompatible = []

        for dep in dependencies:
            try:
                # For known problematic packages in Python 3.13
                req = Requirement(dep)
                package_name = req.name.lower()

                # Known Python 3.13 incompatibilities
                if sys.version_info >= (3, 13):
                    if (
                        package_name in ["ydata-profiling", "pandas-profiling"]
                        or package_name == "apache-airflow"
                    ):
                        incompatible.append(f"{dep} (requires Python <3.13)")
                        continue

                # Default to compatible if we don't know
                compatible.append(dep)

            except Exception as e:
                logger.warning(f"Could not check compatibility for {dep}: {e}")
                compatible.append(dep)  # Assume compatible if we can't check

        return compatible, incompatible

    def install_missing_dependencies(self, dependencies: List[str]) -> Tuple[bool, str]:
        """
        Install missing Python dependencies using robust retry logic.

        WHY: Network issues and temporary package unavailability can cause
        installation failures. Using the robust installer with retries
        significantly improves success rate.

        Args:
            dependencies: List of package specifications to install

        Returns:
            Tuple of (success, error_message)
        """
        if not dependencies:
            return True, ""

        # Check Python version compatibility first
        compatible, incompatible = self.check_python_compatibility(dependencies)

        if incompatible:
            logger.warning(f"Skipping {len(incompatible)} incompatible packages:")
            for dep in incompatible:
                logger.warning(f"  - {dep}")

        if not compatible:
            return True, "No compatible packages to install"

        # Use robust installer with retry logic
        try:
            from .robust_installer import RobustPackageInstaller

            logger.info(
                f"Installing {len(compatible)} compatible dependencies with retry logic..."
            )
            if incompatible:
                logger.info(
                    f"(Skipping {len(incompatible)} incompatible with Python {sys.version_info.major}.{sys.version_info.minor})"
                )

            # Create installer with sensible defaults
            installer = RobustPackageInstaller(
                max_retries=3, retry_delay=2.0, timeout=300
            )

            # Install packages
            successful, failed, errors = installer.install_packages(compatible)

            if failed:
                # Provide detailed error information
                error_details = []
                for pkg in failed:
                    error_details.append(f"{pkg}: {errors.get(pkg, 'Unknown error')}")

                error_msg = f"Failed to install {len(failed)} packages:\n" + "\n".join(
                    error_details
                )
                logger.error(error_msg)

                # Partial success handling
                if successful:
                    partial_msg = f"Partially successful: installed {len(successful)} of {len(compatible)} packages"
                    logger.info(partial_msg)
                    if incompatible:
                        return (
                            True,
                            f"{partial_msg}. Also skipped {len(incompatible)} incompatible",
                        )
                    return True, partial_msg

                return False, error_msg

            logger.info(
                f"Successfully installed all {len(successful)} compatible dependencies"
            )
            if incompatible:
                return (
                    True,
                    f"Installed {len(compatible)} packages, skipped {len(incompatible)} incompatible",
                )
            return True, ""

        except ImportError:
            # Fallback to simple installation if robust installer not available
            logger.warning(
                "Robust installer not available, falling back to simple installation"
            )
            try:
                cmd = [sys.executable, "-m", "pip", "install"]

                # Check for PEP 668 managed environment
                import sysconfig

                stdlib_path = sysconfig.get_path("stdlib")
                marker_file = Path(stdlib_path) / "EXTERNALLY-MANAGED"
                parent_marker = marker_file.parent.parent / "EXTERNALLY-MANAGED"

                if marker_file.exists() or parent_marker.exists():
                    logger.warning(
                        "PEP 668 managed environment detected. "
                        "Installing with --break-system-packages --user flags. "
                        "Consider using a virtual environment instead."
                    )
                    cmd.extend(["--break-system-packages", "--user"])

                cmd.extend(compatible)

                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300, check=False
                )

                if result.returncode == 0:
                    logger.info("Successfully installed compatible dependencies")
                    if incompatible:
                        return (
                            True,
                            f"Installed {len(compatible)} packages, skipped {len(incompatible)} incompatible",
                        )
                    return True, ""
                error_msg = f"Installation failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

            except Exception as e:
                error_msg = f"Failed to install dependencies: {e}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Failed to install dependencies: {e}"
            logger.error(error_msg)
            return False, error_msg

    def load_and_check(self) -> Dict[str, Dict]:
        """
        Complete workflow: discover agents, load dependencies, and check them.

        Returns:
            Complete analysis results
        """
        # Discover deployed agents
        self.discover_deployed_agents()

        if not self.deployed_agents:
            logger.info("No deployed agents found")
            return {"agents": {}, "summary": {"total_agents": 0}}

        # Load their dependencies
        self.load_agent_dependencies()

        # Analyze what's missing
        results = self.analyze_dependencies()

        # Optionally auto-install missing dependencies
        if self.auto_install and results["summary"]["missing_python"]:
            logger.info(
                f"Auto-installing {len(results['summary']['missing_python'])} missing dependencies..."
            )
            success, error = self.install_missing_dependencies(
                results["summary"]["missing_python"]
            )
            if success:
                # Re-analyze after installation
                self.checked_packages.clear()
                results = self.analyze_dependencies()

        return results

    def format_report(self, results: Dict[str, Dict]) -> str:
        """
        Format a human-readable dependency report.

        Args:
            results: Analysis results from analyze_dependencies()

        Returns:
            Formatted report string
        """
        import sys

        lines = []
        lines.append("=" * 80)
        lines.append("AGENT DEPENDENCY ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Python version info
        lines.append(
            f"Python Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        lines.append("")

        # Summary
        summary = results["summary"]
        lines.append(f"Deployed Agents: {summary['total_agents']}")
        lines.append(f"Agents with Dependencies: {summary['agents_with_deps']}")
        lines.append("")

        # Missing dependencies summary
        if summary["missing_python"] or summary["missing_system"]:
            lines.append("⚠️  MISSING DEPENDENCIES:")
            if summary["missing_python"]:
                lines.append(f"  Python packages: {len(summary['missing_python'])}")
                for dep in summary["missing_python"][:5]:  # Show first 5
                    lines.append(f"    - {dep}")
                if len(summary["missing_python"]) > 5:
                    lines.append(
                        f"    ... and {len(summary['missing_python']) - 5} more"
                    )

            if summary["missing_system"]:
                lines.append(f"  System commands: {len(summary['missing_system'])}")
                for cmd in summary["missing_system"]:
                    lines.append(f"    - {cmd}")
            lines.append("")

        # Per-agent details (only for agents with issues)
        agents_with_issues = {
            agent_id: info
            for agent_id, info in results["agents"].items()
            if info["python"]["missing"]
            or info["python"]["outdated"]
            or info["system"]["missing"]
        }

        if agents_with_issues:
            lines.append("AGENT-SPECIFIC ISSUES:")
            lines.append("-" * 40)
            for agent_id, info in agents_with_issues.items():
                lines.append(f"\n📦 {agent_id}:")

                if info["python"]["missing"]:
                    lines.append(
                        f"  Missing Python: {', '.join(info['python']['missing'])}"
                    )
                if info["python"]["outdated"]:
                    lines.append(
                        f"  Outdated Python: {', '.join(info['python']['outdated'])}"
                    )
                if info["system"]["missing"]:
                    lines.append(
                        f"  Missing System: {', '.join(info['system']['missing'])}"
                    )

        else:
            lines.append("✅ All agent dependencies are satisfied!")

        # Installation instructions
        if summary["missing_python"]:
            lines.append("")
            lines.append("TO INSTALL MISSING PYTHON DEPENDENCIES:")
            lines.append("-" * 40)

            # Check for Python 3.13 compatibility issues
            import sys

            if sys.version_info >= (3, 13):
                compatible, incompatible = self.check_python_compatibility(
                    summary["missing_python"]
                )
                if incompatible:
                    lines.append("⚠️  Python 3.13 Compatibility Warning:")
                    lines.append(
                        f"  {len(incompatible)} packages are not yet compatible with Python 3.13:"
                    )
                    for dep in incompatible[:3]:
                        lines.append(f"    - {dep}")
                    if len(incompatible) > 3:
                        lines.append(f"    ... and {len(incompatible) - 3} more")
                    lines.append("")
                    lines.append(
                        "  Consider using Python 3.12 or earlier for full compatibility."
                    )
                    lines.append("")

            lines.append("Option 1: Install all agent dependencies:")
            lines.append('  pip install "claude-mpm[agents]"')
            lines.append("")
            lines.append("Option 2: Install only what's needed:")
            deps_str = " ".join(f'"{dep}"' for dep in summary["missing_python"][:3])
            lines.append(f"  pip install {deps_str}")
            if len(summary["missing_python"]) > 3:
                lines.append(f"  # ... and {len(summary['missing_python']) - 3} more")

        if summary["missing_system"]:
            lines.append("")
            lines.append("TO INSTALL MISSING SYSTEM DEPENDENCIES:")
            lines.append("-" * 40)
            lines.append("Use your system package manager:")
            lines.append(
                "  # macOS: brew install " + " ".join(summary["missing_system"])
            )
            lines.append(
                "  # Ubuntu: apt-get install " + " ".join(summary["missing_system"])
            )

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def calculate_deployment_hash(self) -> str:
        """
        Calculate a hash of the current agent deployment state.

        WHY: We use SHA256 hash of agent files to detect when agents have changed.
        This allows us to skip dependency checks when nothing has changed,
        improving startup performance.

        Returns:
            SHA256 hash of all deployed agent files and their content.
        """
        hash_obj = hashlib.sha256()

        # Discover current agents if not already done
        if not self.deployed_agents:
            self.discover_deployed_agents()

        # Sort agent IDs for consistent hashing
        for agent_id in sorted(self.deployed_agents.keys()):
            agent_path = self.deployed_agents[agent_id]

            # Include agent ID in hash
            hash_obj.update(agent_id.encode("utf-8"))

            # Include file modification time and size for quick change detection
            try:
                stat = agent_path.stat()
                hash_obj.update(str(stat.st_mtime).encode("utf-8"))
                hash_obj.update(str(stat.st_size).encode("utf-8"))

                # Include file content for comprehensive change detection
                with open(agent_path, "rb") as f:
                    hash_obj.update(f.read())
            except Exception as e:
                logger.debug(f"Could not hash agent file {agent_path}: {e}")
                # Include error in hash to force recheck on next run
                hash_obj.update(f"error:{agent_id}:{e}".encode())

        return hash_obj.hexdigest()

    def load_deployment_state(self) -> Dict:
        """
        Load the saved deployment state.

        Returns:
            Dictionary with deployment state or empty dict if not found.
        """
        if not self.deployment_state_file.exists():
            return {}

        try:
            with open(self.deployment_state_file) as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load deployment state: {e}")
            return {}

    def save_deployment_state(self, state: Dict) -> None:
        """
        Save the deployment state to disk.

        Args:
            state: Deployment state dictionary to save.
        """
        try:
            # Ensure directory exists
            self.deployment_state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.deployment_state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save deployment state: {e}")

    def has_agents_changed(self) -> Tuple[bool, str]:
        """
        Check if agents have changed since last dependency check.

        WHY: This is the core of our smart checking system. We only want to
        check dependencies when agents have actually changed, not on every run.

        Returns:
            Tuple of (has_changed, current_hash)
        """
        current_hash = self.calculate_deployment_hash()
        state = self.load_deployment_state()

        last_hash = state.get("deployment_hash")
        last_check_time = state.get("last_check_time", 0)

        # Check if hash has changed
        if last_hash != current_hash:
            logger.info("Agent deployment has changed since last check")
            return True, current_hash

        # Also check if it's been more than 24 hours (optional staleness check)
        current_time = time.time()
        if current_time - last_check_time > 86400:  # 24 hours
            logger.debug("Over 24 hours since last dependency check")
            return True, current_hash

        logger.debug("No agent changes detected, skipping dependency check")
        return False, current_hash

    def mark_deployment_checked(
        self, deployment_hash: str, check_results: Dict
    ) -> None:
        """
        Mark the current deployment as checked.

        Args:
            deployment_hash: Hash of the current deployment
            check_results: Results of the dependency check
        """
        state = {
            "deployment_hash": deployment_hash,
            "last_check_time": time.time(),
            "last_check_results": check_results,
            "agent_count": len(self.deployed_agents),
        }
        self.save_deployment_state(state)

    def get_cached_check_results(self) -> Optional[Dict]:
        """
        Get cached dependency check results if still valid.

        Returns:
            Cached results or None if not available/valid.
        """
        has_changed, current_hash = self.has_agents_changed()

        if not has_changed:
            state = self.load_deployment_state()
            cached_results = state.get("last_check_results")
            if cached_results:
                logger.debug("Using cached dependency check results")
                return cached_results

        return None


def check_deployed_agent_dependencies(
    auto_install: bool = False, verbose: bool = False
) -> None:
    """
    Check dependencies for currently deployed agents.

    Args:
        auto_install: If True, automatically install missing Python dependencies
        verbose: If True, enable verbose logging
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    loader = AgentDependencyLoader(auto_install=auto_install)
    results = loader.load_and_check()

    # Print report
    report = loader.format_report(results)
    print(report)

    # Return status code based on missing dependencies
    if results["summary"]["missing_python"] or results["summary"]["missing_system"]:
        return 1  # Missing dependencies
    return 0  # All satisfied


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and manage dependencies for deployed agents"
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install missing Python dependencies",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    exit_code = check_deployed_agent_dependencies(
        auto_install=args.auto_install, verbose=args.verbose
    )
    sys.exit(exit_code)
