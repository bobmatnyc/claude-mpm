#!/usr/bin/env python3
"""
Agent Dependency Aggregation Script for Claude MPM

This script scans all agent JSON files across the system to collect Python
dependencies and updates pyproject.toml with agent-specific optional dependencies.

Features:
- Scans system, user, and project agent directories
- Handles version conflict resolution (takes highest version)
- Preserves existing optional-dependencies sections
- Supports both JSON and YAML agent formats
- Comprehensive error handling and logging
- Validates dependency format and versions

Usage:
    python scripts/aggregate_agent_dependencies.py [--dry-run] [--verbose]

Arguments:
    --dry-run: Show what would be changed without modifying files
    --verbose: Enable detailed logging output
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from packaging import version
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

# Handle TOML imports for different Python versions
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python < 3.11
    except ImportError:
        tomllib = None

import toml  # For writing TOML files

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DependencyAggregator:
    """
    Aggregates dependencies from agent configuration files.

    This class handles the complex task of collecting dependencies from multiple
    agent sources, resolving version conflicts, and updating the project configuration.
    """

    def __init__(
        self, project_root: Path, dry_run: bool = False, verbose: bool = False
    ):
        """
        Initialize the dependency aggregator.

        Args:
            project_root: Path to the project root directory
            dry_run: If True, show changes without applying them
            verbose: Enable detailed logging
        """
        self.project_root = project_root
        self.dry_run = dry_run
        self.verbose = verbose

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Define agent directory paths in precedence order
        self.agent_paths = [
            project_root / ".claude-mpm" / "agents",  # PROJECT level
            Path.home() / ".claude-mpm" / "agents",  # USER level
            project_root
            / "src"
            / "claude_mpm"
            / "agents"
            / "templates",  # SYSTEM level
        ]

        self.pyproject_path = project_root / "pyproject.toml"

    def scan_agent_files(self) -> List[Path]:
        """
        Scan all agent directories for configuration files.

        Returns:
            List of paths to agent configuration files
        """
        agent_files = []

        for agent_dir in self.agent_paths:
            if not agent_dir.exists():
                logger.debug(f"Agent directory not found: {agent_dir}")
                continue

            logger.debug(f"Scanning agent directory: {agent_dir}")

            # Find JSON and YAML files
            for pattern in ["*.json", "*.yaml", "*.yml"]:
                files = list(agent_dir.glob(pattern))
                agent_files.extend(files)
                logger.debug(f"Found {len(files)} {pattern} files in {agent_dir}")

        logger.info(f"Total agent files found: {len(agent_files)}")
        return agent_files

    def load_agent_config(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load and parse an agent configuration file.

        Args:
            file_path: Path to the agent configuration file

        Returns:
            Parsed agent configuration or None if loading fails
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                if file_path.suffix == ".json":
                    return json.load(f)
                # YAML
                return yaml.safe_load(f)

        except Exception as e:
            logger.warning(f"Failed to load agent config {file_path}: {e}")
            return None

    def extract_dependencies(
        self, config: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """
        Extract Python dependencies from an agent configuration.

        Args:
            config: Agent configuration dictionary

        Returns:
            Tuple of (required_dependencies, optional_dependencies) with version specifiers
        """
        required_dependencies = []
        optional_dependencies = []

        # Check for dependencies section
        deps_section = config.get("dependencies", {})
        if isinstance(deps_section, dict):
            # Required Python dependencies
            python_deps = deps_section.get("python", [])
            if isinstance(python_deps, list):
                required_dependencies.extend(python_deps)

            # Optional Python dependencies
            python_optional_deps = deps_section.get("python_optional", [])
            if isinstance(python_optional_deps, list):
                optional_dependencies.extend(python_optional_deps)

        return required_dependencies, optional_dependencies

    def normalize_dependency(self, dep_string: str) -> Optional[Tuple[str, str]]:
        """
        Normalize a dependency string to (package_name, version_spec) tuple.

        Args:
            dep_string: Dependency string like "package>=1.0.0"

        Returns:
            Tuple of (package_name, version_specifier) or None if invalid
        """
        try:
            req = Requirement(dep_string)
            return (req.name.lower(), str(req.specifier) if req.specifier else "")
        except Exception as e:
            logger.warning(f"Invalid dependency format '{dep_string}': {e}")
            return None

    def resolve_version_conflicts(
        self, dependencies: Dict[str, List[str]]
    ) -> Dict[str, str]:
        """
        Resolve version conflicts between dependencies by taking the highest version.

        Args:
            dependencies: Dict mapping package names to lists of version specs

        Returns:
            Dict mapping package names to resolved version specs
        """
        resolved = {}

        for package, version_specs in dependencies.items():
            if not version_specs:
                resolved[package] = ""
                continue

            if len(version_specs) == 1:
                resolved[package] = version_specs[0]
                continue

            # Multiple version specs - need to resolve conflicts
            logger.debug(f"Resolving version conflict for {package}: {version_specs}")

            try:
                # Parse all specifiers and find the most restrictive one
                specifier_sets = [SpecifierSet(spec) for spec in version_specs if spec]

                if not specifier_sets:
                    resolved[package] = ""
                    continue

                # For now, take the highest minimum version requirement
                # This is a simplified approach - real resolution is complex
                highest_min = ""
                for spec_set in specifier_sets:
                    for spec in spec_set:
                        if spec.operator in (">=", "==", ">"):
                            if not highest_min or version.parse(
                                spec.version
                            ) > version.parse(highest_min.split(">=")[-1]):
                                highest_min = f">={spec.version}"

                resolved[package] = highest_min or version_specs[0]
                logger.debug(f"Resolved {package} to: {resolved[package]}")

            except Exception as e:
                logger.warning(f"Failed to resolve version conflict for {package}: {e}")
                resolved[package] = version_specs[0]  # Use first as fallback

        return resolved

    def aggregate_dependencies(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Aggregate all dependencies from agent files.

        Returns:
            Tuple of (required_dependencies, optional_dependencies) mapping package names to version specifiers
        """
        logger.info("Starting dependency aggregation...")

        agent_files = self.scan_agent_files()
        all_required_deps = {}  # package_name -> [version_specs]
        all_optional_deps = {}  # package_name -> [version_specs]

        for file_path in agent_files:
            logger.debug(f"Processing agent file: {file_path}")

            config = self.load_agent_config(file_path)
            if not config:
                continue

            required_deps, optional_deps = self.extract_dependencies(config)

            total_deps = len(required_deps) + len(optional_deps)
            if total_deps > 0:
                logger.debug(
                    f"Found {len(required_deps)} required and {len(optional_deps)} optional dependencies in {file_path.name}"
                )

            # Process required dependencies
            for dep in required_deps:
                normalized = self.normalize_dependency(dep)
                if not normalized:
                    continue

                package_name, version_spec = normalized
                if package_name not in all_required_deps:
                    all_required_deps[package_name] = []

                if version_spec and version_spec not in all_required_deps[package_name]:
                    all_required_deps[package_name].append(version_spec)

            # Process optional dependencies
            for dep in optional_deps:
                normalized = self.normalize_dependency(dep)
                if not normalized:
                    continue

                package_name, version_spec = normalized
                if package_name not in all_optional_deps:
                    all_optional_deps[package_name] = []

                if version_spec and version_spec not in all_optional_deps[package_name]:
                    all_optional_deps[package_name].append(version_spec)

        # Resolve version conflicts
        resolved_required = self.resolve_version_conflicts(all_required_deps)
        resolved_optional = self.resolve_version_conflicts(all_optional_deps)

        logger.info(
            f"Aggregated {len(resolved_required)} required and {len(resolved_optional)} optional dependencies"
        )
        return resolved_required, resolved_optional

    def load_pyproject_toml(self) -> Dict[str, Any]:
        """
        Load and parse the pyproject.toml file.

        Returns:
            Parsed pyproject.toml content
        """
        try:
            if self.pyproject_path.exists():
                if tomllib is not None:
                    with open(self.pyproject_path, "rb") as f:
                        return tomllib.load(f)
                else:
                    # Fallback to toml library for writing
                    with open(self.pyproject_path, encoding="utf-8") as f:
                        return toml.load(f)
            else:
                logger.warning("pyproject.toml not found, creating minimal structure")
                return {"project": {}}

        except Exception as e:
            logger.error(f"Failed to load pyproject.toml: {e}")
            raise

    def update_pyproject_toml(
        self, required_dependencies: Dict[str, str], optional_dependencies: Dict[str, str]
    ) -> None:
        """
        Update pyproject.toml with agent dependencies.

        Args:
            required_dependencies: Dict of required package names to version specifiers
            optional_dependencies: Dict of optional package names to version specifiers
        """
        logger.info("Updating pyproject.toml with agent dependencies...")

        # Load current content
        content = self.load_pyproject_toml()

        # Ensure project section exists
        if "project" not in content:
            content["project"] = {}

        # Ensure optional-dependencies section exists
        if "optional-dependencies" not in content["project"]:
            content["project"]["optional-dependencies"] = {}

        # Format required dependencies for TOML
        formatted_required = []
        for package, version_spec in sorted(required_dependencies.items()):
            if version_spec:
                formatted_required.append(f"{package}{version_spec}")
            else:
                formatted_required.append(package)

        # Format optional dependencies for TOML
        formatted_optional = []
        for package, version_spec in sorted(optional_dependencies.items()):
            if version_spec:
                formatted_optional.append(f"{package}{version_spec}")
            else:
                formatted_optional.append(package)

        # Update agents section (required dependencies)
        content["project"]["optional-dependencies"]["agents"] = formatted_required

        # Update agents-load-testing section (optional dependencies for performance/load testing)
        if formatted_optional:
            content["project"]["optional-dependencies"]["agents-load-testing"] = (
                formatted_optional
            )

        if self.dry_run:
            logger.info("DRY RUN: Would update pyproject.toml with:")
            logger.info("  [project.optional-dependencies]")
            logger.info(f"  agents = {formatted_required}")
            if formatted_optional:
                logger.info(f"  agents-load-testing = {formatted_optional}")
            return

        # Write back to file
        try:
            with open(self.pyproject_path, "w", encoding="utf-8") as f:
                toml.dump(content, f)
            logger.info(f"Successfully updated {self.pyproject_path}")
            logger.info(
                f"  - agents: {len(formatted_required)} required dependencies"
            )
            if formatted_optional:
                logger.info(
                    f"  - agents-load-testing: {len(formatted_optional)} optional dependencies"
                )

        except Exception as e:
            logger.error(f"Failed to write pyproject.toml: {e}")
            raise

    def validate_dependencies(self, dependencies: Dict[str, str]) -> bool:
        """
        Validate that all dependencies are properly formatted.

        Args:
            dependencies: Dict of dependencies to validate

        Returns:
            True if all dependencies are valid
        """
        valid = True

        for package, version_spec in dependencies.items():
            try:
                if version_spec:
                    # Validate full requirement string
                    Requirement(f"{package}{version_spec}")
                else:
                    # Just validate package name
                    Requirement(package)
            except Exception as e:
                logger.error(f"Invalid dependency: {package}{version_spec} - {e}")
                valid = False

        return valid

    def run(self) -> bool:
        """
        Run the complete dependency aggregation process.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting agent dependency aggregation...")

            # Aggregate dependencies
            required_deps, optional_deps = self.aggregate_dependencies()

            if not required_deps and not optional_deps:
                logger.info("No agent dependencies found")
                return True

            # Validate dependencies
            if required_deps and not self.validate_dependencies(required_deps):
                logger.error("Required dependency validation failed")
                return False

            if optional_deps and not self.validate_dependencies(optional_deps):
                logger.error("Optional dependency validation failed")
                return False

            # Update pyproject.toml
            self.update_pyproject_toml(required_deps, optional_deps)

            logger.info("Agent dependency aggregation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Dependency aggregation failed: {e}")
            return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Aggregate agent dependencies for Claude MPM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable detailed logging output"
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to project root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Validate project root
    if not args.project_root.is_dir():
        logger.error(f"Project root is not a directory: {args.project_root}")
        return 1

    # Run aggregation
    aggregator = DependencyAggregator(
        project_root=args.project_root, dry_run=args.dry_run, verbose=args.verbose
    )

    success = aggregator.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
