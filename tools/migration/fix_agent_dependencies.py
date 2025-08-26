#!/usr/bin/env python3
"""
Script to fix agent dependency issues with robust retry logic.

WHY: This script provides a user-friendly way to resolve dependency issues
for claude-mpm agents, especially when network issues or package availability
problems occur.

USAGE:
    python scripts/fix_agent_dependencies.py [--check-only] [--verbose]
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logger import get_logger, setup_logging
from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader
from claude_mpm.utils.robust_installer import RobustPackageInstaller


def main():
    parser = argparse.ArgumentParser(
        description="Fix agent dependency issues with robust retry logic"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check dependencies, don't install",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per package (default: 3)",
    )
    parser.add_argument(
        "--specific-agent", help="Only check/fix dependencies for a specific agent"
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        setup_logging(level="DEBUG")
    else:
        setup_logging(level="INFO")

    get_logger(__name__)

    print("=" * 70)
    print("AGENT DEPENDENCY FIXER")
    print("=" * 70)
    print()

    # Create dependency loader
    loader = AgentDependencyLoader(auto_install=False)

    # Discover deployed agents
    print("Discovering deployed agents...")
    loader.discover_deployed_agents()

    if not loader.deployed_agents:
        print("No deployed agents found in .claude/agents/")
        return 0

    print(f"Found {len(loader.deployed_agents)} deployed agents")

    # Filter to specific agent if requested
    if args.specific_agent:
        if args.specific_agent in loader.deployed_agents:
            loader.deployed_agents = {
                args.specific_agent: loader.deployed_agents[args.specific_agent]
            }
            print(f"Focusing on agent: {args.specific_agent}")
        else:
            print(f"Error: Agent '{args.specific_agent}' not found")
            print(f"Available agents: {', '.join(loader.deployed_agents.keys())}")
            return 1

    # Load dependencies
    print("Loading agent dependencies...")
    loader.load_agent_dependencies()

    # Analyze current state
    print("Analyzing dependency status...")
    results = loader.analyze_dependencies()

    # Show current status
    print()
    print("CURRENT STATUS:")
    print("-" * 40)

    missing_python = results["summary"]["missing_python"]
    missing_system = results["summary"]["missing_system"]

    if not missing_python and not missing_system:
        print("✅ All dependencies are satisfied!")
        return 0

    if missing_python:
        print(f"❌ Missing Python packages: {len(missing_python)}")
        for pkg in missing_python[:10]:  # Show first 10
            print(f"   - {pkg}")
        if len(missing_python) > 10:
            print(f"   ... and {len(missing_python) - 10} more")

    if missing_system:
        print(f"❌ Missing system commands: {len(missing_system)}")
        for cmd in missing_system:
            print(f"   - {cmd}")

    print()

    # Check-only mode
    if args.check_only:
        print("Check-only mode: Not installing packages")
        print()
        print("To fix missing dependencies, run without --check-only")
        return 1 if missing_python or missing_system else 0

    # Handle system dependencies
    if missing_system:
        print("⚠️  System dependencies must be installed manually:")
        print()
        print("For macOS:")
        print(f"  brew install {' '.join(missing_system)}")
        print()
        print("For Ubuntu/Debian:")
        print(f"  sudo apt-get install {' '.join(missing_system)}")
        print()

    # Handle Python dependencies
    if missing_python:
        print("FIXING PYTHON DEPENDENCIES:")
        print("-" * 40)

        # Check Python version compatibility
        compatible, incompatible = loader.check_python_compatibility(missing_python)

        if incompatible:
            print(f"⚠️  Skipping {len(incompatible)} incompatible packages:")
            for pkg in incompatible[:5]:
                print(f"   - {pkg}")
            if len(incompatible) > 5:
                print(f"   ... and {len(incompatible) - 5} more")
            print()

        if compatible:
            print(
                f"Installing {len(compatible)} compatible packages with retry logic..."
            )
            print()

            # Use robust installer
            installer = RobustPackageInstaller(
                max_retries=args.max_retries, retry_delay=2.0, timeout=300
            )

            successful, failed, errors = installer.install_packages(compatible)

            print()
            print("INSTALLATION RESULTS:")
            print("-" * 40)

            if successful:
                print(f"✅ Successfully installed: {len(successful)} packages")
                if args.verbose:
                    for pkg in successful:
                        print(f"   - {pkg}")

            if failed:
                print(f"❌ Failed to install: {len(failed)} packages")
                for pkg in failed:
                    print(f"   - {pkg}: {errors.get(pkg, 'Unknown error')}")

            if args.verbose:
                print()
                print("DETAILED REPORT:")
                print(installer.get_report())

            # Re-check after installation
            print()
            print("Re-checking dependencies after installation...")
            loader.checked_packages.clear()
            final_results = loader.analyze_dependencies()

            final_missing = final_results["summary"]["missing_python"]
            if not final_missing:
                print("✅ All Python dependencies are now satisfied!")
            else:
                print(
                    f"⚠️  Still missing {len(final_missing)} packages after installation"
                )
                if args.verbose:
                    for pkg in final_missing:
                        print(f"   - {pkg}")
        else:
            print("No compatible packages to install")

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)

    # Return appropriate exit code
    final_results = loader.analyze_dependencies()
    if (
        final_results["summary"]["missing_python"]
        or final_results["summary"]["missing_system"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
