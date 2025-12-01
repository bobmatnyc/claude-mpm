#!/usr/bin/env python3
"""Deploy template files to ~/.claude-mpm/templates/ for easy access.

This script copies template documentation files from the package to a user-accessible
location. Templates are primarily for developer reference and documentation, not for
PM runtime execution.
"""

import shutil
import sys
from pathlib import Path
from typing import Optional

# Try to use importlib.resources for packaged installations
try:
    from importlib.resources import files
except ImportError:
    try:
        from importlib_resources import files
    except ImportError:
        files = None


def get_templates_source_dir():
    """Get the source directory for templates.

    Returns:
        Path: Source directory containing templates, or None if not found
    """
    # Try development installation first (running from source tree)
    current_file = Path(__file__).resolve()
    repo_root = current_file.parent.parent
    dev_templates = repo_root / "src" / "claude_mpm" / "agents" / "templates"

    if dev_templates.exists() and dev_templates.is_dir():
        return dev_templates

    # Try packaged installation using importlib.resources
    if files:
        try:
            agents_pkg = files("claude_mpm.agents")
            templates_path = agents_pkg / "templates"
            if templates_path.is_dir():
                return templates_path
        except Exception as e:
            print(f"Warning: Could not access packaged templates: {e}", file=sys.stderr)

    return None


def deploy_templates(target_dir: Optional[Path] = None, verbose: bool = True) -> bool:
    """Deploy template files to target directory.

    Args:
        target_dir: Target directory (default: ~/.claude-mpm/templates)
        verbose: Print progress messages

    Returns:
        bool: True if successful, False otherwise
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude-mpm" / "templates"

    # Get source directory
    source_dir = get_templates_source_dir()
    if not source_dir:
        print("Error: Could not locate templates source directory", file=sys.stderr)
        print("Templates should be in:", file=sys.stderr)
        print(
            "  - Development: <repo>/src/claude_mpm/agents/templates/", file=sys.stderr
        )
        print(
            "  - Packaged: python package claude_mpm.agents.templates", file=sys.stderr
        )
        return False

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Deploying templates from: {source_dir}")
        print(f"Deploying templates to:   {target_dir}")

    # Copy template files
    template_files = list(source_dir.glob("*.md"))
    copied_count = 0

    for template_file in template_files:
        # Skip __init__.py and non-template files
        if template_file.name.startswith("__"):
            continue

        target_file = target_dir / template_file.name

        try:
            # For packaged installations using importlib.resources
            if hasattr(template_file, "read_text"):
                content = template_file.read_text()
                target_file.write_text(content)
            # For file system paths
            else:
                shutil.copy2(template_file, target_file)

            copied_count += 1
            if verbose:
                print(f"  ✓ {template_file.name}")
        except Exception as e:
            print(f"  ✗ {template_file.name}: {e}", file=sys.stderr)

    if verbose:
        print(f"\nDeployed {copied_count} template files to {target_dir}")

    return copied_count > 0


def main():
    """Main entry point for template deployment script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy PM instruction templates to ~/.claude-mpm/templates/"
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Target directory (default: ~/.claude-mpm/templates)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress progress messages"
    )

    args = parser.parse_args()

    success = deploy_templates(target_dir=args.target, verbose=not args.quiet)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
