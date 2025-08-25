#!/usr/bin/env python3
"""
Post-installation setup script for claude-mpm.

This script handles the setup tasks that were previously done in setup.py:
- Create necessary directories
- Build dashboard assets
- Install ticket command wrapper

Usage:
    python scripts/post_install.py
"""

import subprocess
import sys
from pathlib import Path


def create_directories():
    """Create necessary directories for claude-mpm."""
    print("Creating claude-mpm directories...")

    # Create user .claude-mpm directory
    user_dir = Path.home() / ".claude-mpm"
    user_dir.mkdir(exist_ok=True)
    print(f"Created: {user_dir}")

    # Create subdirectories
    subdirs = [
        user_dir / "agents" / "user-defined",
        user_dir / "logs",
        user_dir / "config",
    ]

    for subdir in subdirs:
        subdir.mkdir(parents=True, exist_ok=True)
        print(f"Created: {subdir}")


def build_dashboard_assets():
    """Build dashboard assets using Vite if Node.js is available."""
    print("Building dashboard assets...")

    try:
        build_script = Path(__file__).parent / "build-dashboard.sh"
        if build_script.exists():
            print("Running dashboard build script...")
            result = subprocess.run(
                ["bash", str(build_script)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                check=False,
            )
            if result.returncode != 0:
                print(f"Warning: Dashboard build failed: {result.stderr}")
                print(
                    "Dashboard will use individual script files instead of optimized bundles."
                )
            else:
                print("Dashboard assets built successfully")
        else:
            print("Dashboard build script not found, skipping...")
    except Exception as e:
        print(f"Warning: Failed to build dashboard assets: {e}")


def install_ticket_command():
    """Install ticket command wrapper."""
    print("Installing ticket command wrapper...")

    try:
        import site

        # Get the scripts directory
        if hasattr(site, "USER_BASE"):
            scripts_dir = Path(site.USER_BASE) / "bin"
        else:
            scripts_dir = Path(sys.prefix) / "bin"

        scripts_dir.mkdir(exist_ok=True)

        # Create ticket wrapper script
        ticket_script = scripts_dir / "ticket"
        ticket_content = '''#!/usr/bin/env python3
"""Ticket command wrapper for claude-mpm."""
import sys
from claude_mpm.ticket_wrapper import main

if __name__ == "__main__":
    sys.exit(main())
'''
        ticket_script.write_text(ticket_content)
        ticket_script.chmod(0o755)
        print(f"Installed ticket command: {ticket_script}")

    except Exception as e:
        print(f"Warning: Failed to install ticket command: {e}")


def aggregate_agent_dependencies():
    """Run agent dependency aggregation script."""
    print("Aggregating agent dependencies...")

    try:
        script_path = Path(__file__).parent / "aggregate_agent_dependencies.py"
        if script_path.exists():
            print("Running agent dependency aggregation...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                check=False,
            )
            if result.returncode != 0:
                print(f"Warning: Agent dependency aggregation failed: {result.stderr}")
            else:
                print("Agent dependencies aggregated successfully")
        else:
            print("Agent dependency aggregation script not found, skipping...")
    except Exception as e:
        print(f"Warning: Failed to aggregate agent dependencies: {e}")


def main():
    """Run all post-installation tasks."""
    print("🚀 Running claude-mpm post-installation setup...")
    print("=" * 50)

    try:
        create_directories()
        print()

        build_dashboard_assets()
        print()

        install_ticket_command()
        print()

        aggregate_agent_dependencies()
        print()

        print("✅ Post-installation setup completed successfully!")

    except Exception as e:
        print(f"❌ Post-installation setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
