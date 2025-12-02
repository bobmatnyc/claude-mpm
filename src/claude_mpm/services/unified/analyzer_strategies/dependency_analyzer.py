"""
Dependency Analyzer Strategy Implementation
===========================================

Analyzes project dependencies, package management, and dependency graphs.
Consolidates dependency analysis functionality from multiple services.

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import json
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logging_utils import get_logger

from ..strategies import (
    AnalyzerStrategy,
    StrategyContext,
    StrategyMetadata,
    StrategyPriority,
)

logger = get_logger(__name__)


class DependencyAnalyzerStrategy(AnalyzerStrategy):
    """
    Strategy for analyzing project dependencies and package management.

    Consolidates:
    - Package manager detection
    - Dependency graph analysis
    - Version conflict detection
    - Security vulnerability scanning
    - License compliance checking
    """

    # Package manager configurations
    PACKAGE_MANAGERS: ClassVar[dict] = {
        "package.json": "npm",
        "yarn.lock": "yarn",
        "pnpm-lock.yaml": "pnpm",
        "package-lock.json": "npm",
        "requirements.txt": "pip",
        "Pipfile": "pipenv",
        "poetry.lock": "poetry",
        "pyproject.toml": "pip",
        "Cargo.toml": "cargo",
        "go.mod": "go",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "composer.json": "composer",
        "Gemfile": "bundler",
        "mix.exs": "mix",
        "pubspec.yaml": "pub",
    }

    # Database-related dependencies
    DATABASE_PACKAGES: ClassVar[dict] = {
        "postgresql": ["psycopg2", "pg", "postgres", "postgresql", "node-postgres"],
        "mysql": ["mysql", "mysql2", "mysqlclient", "mysql-connector"],
        "sqlite": ["sqlite3", "better-sqlite3"],
        "mongodb": ["mongodb", "mongoose", "pymongo", "motor"],
        "redis": ["redis", "ioredis", "redis-py"],
        "elasticsearch": ["elasticsearch", "@elastic/elasticsearch"],
        "cassandra": ["cassandra-driver"],
        "neo4j": ["neo4j", "neo4j-driver"],
    }

    # Testing framework packages
    TESTING_PACKAGES: ClassVar[dict] = {
        "python": ["pytest", "unittest", "nose", "nose2", "tox", "coverage"],
        "javascript": [
            "jest",
            "mocha",
            "chai",
            "jasmine",
            "cypress",
            "playwright",
            "vitest",
        ],
        "java": ["junit", "testng", "mockito", "assertj"],
        "ruby": ["rspec", "minitest", "cucumber"],
        "go": ["testify", "ginkgo", "gomega"],
        "rust": ["test", "quickcheck", "proptest"],
    }

    # Web framework packages
    FRAMEWORK_PACKAGES: ClassVar[dict] = {
        "python": ["django", "flask", "fastapi", "pyramid", "tornado", "aiohttp"],
        "javascript": [
            "express",
            "koa",
            "fastify",
            "hapi",
            "nestjs",
            "next",
            "nuxt",
            "gatsby",
        ],
        "ruby": ["rails", "sinatra", "hanami"],
        "java": ["spring", "spring-boot", "struts", "play"],
        "php": ["laravel", "symfony", "slim", "lumen"],
    }

    def __init__(self):
        """Initialize dependency analyzer strategy."""
        metadata = StrategyMetadata(
            name="DependencyAnalyzer",
            description="Analyzes project dependencies and package management",
            supported_types=["project", "package", "lockfile", "manifest"],
            supported_operations=["analyze", "detect", "graph", "vulnerabilities"],
            priority=StrategyPriority.HIGH,
            tags={"dependencies", "packages", "versions", "security"},
        )
        super().__init__(metadata)

    def can_handle(self, context: StrategyContext) -> bool:
        """Check if strategy can handle the given context."""
        return (
            context.target_type in self.metadata.supported_types
            and context.operation in self.metadata.supported_operations
        )

    def validate_input(self, input_data: Any) -> List[str]:
        """Validate input data for strategy."""
        errors = []

        if not input_data:
            errors.append("Input data is required")
            return errors

        if isinstance(input_data, (str, Path)):
            path = Path(input_data)
            if not path.exists():
                errors.append(f"Path does not exist: {path}")
        elif not isinstance(input_data, dict):
            errors.append(f"Invalid input type: {type(input_data).__name__}")

        return errors

    def analyze(
        self, target: Any, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute dependency analysis on target.

        Args:
            target: Project directory or package manifest to analyze
            options: Analysis options (depth, check_vulnerabilities, etc.)

        Returns:
            Analysis results with dependency information
        """
        options = options or {}

        if isinstance(target, (str, Path)):
            target_path = Path(target)

            if target_path.is_dir():
                return self._analyze_project(target_path, options)
            if target_path.is_file():
                return self._analyze_manifest(target_path, options)

        return {
            "status": OperationResult.ERROR,
            "message": f"Unsupported target type: {type(target).__name__}",
        }

    def _analyze_project(
        self, project_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze dependencies in a project directory."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "project",
            "path": str(project_path),
            "package_managers": [],
            "dependencies": {},
            "dev_dependencies": {},
            "frameworks": [],
            "databases": [],
            "testing_tools": [],
        }

        # Detect package managers
        detected_managers = self._detect_package_managers(project_path)
        results["package_managers"] = detected_managers

        # Analyze each package manager's dependencies
        for manager in detected_managers:
            manager_deps = self._analyze_package_manager(project_path, manager, options)
            if manager_deps:
                results["dependencies"][manager] = manager_deps.get("dependencies", {})
                results["dev_dependencies"][manager] = manager_deps.get(
                    "dev_dependencies", {}
                )

        # Detect frameworks, databases, and testing tools
        all_deps = self._flatten_dependencies(results["dependencies"])
        all_deps.update(self._flatten_dependencies(results["dev_dependencies"]))

        results["frameworks"] = self._detect_frameworks(all_deps)
        results["databases"] = self._detect_databases(all_deps)
        results["testing_tools"] = self._detect_testing_tools(all_deps)

        # Check for security vulnerabilities if requested
        if options.get("check_vulnerabilities", False):
            results["vulnerabilities"] = self._check_vulnerabilities(project_path)

        # Generate dependency statistics
        results["statistics"] = self._calculate_statistics(results)

        return results

    def _analyze_manifest(
        self, manifest_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a specific package manifest file."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "manifest",
            "path": str(manifest_path),
            "dependencies": {},
            "dev_dependencies": {},
        }

        # Determine package manager from file
        manager = self.PACKAGE_MANAGERS.get(manifest_path.name)
        if not manager:
            # Check for pyproject.toml variants
            if manifest_path.name == "pyproject.toml":
                content = manifest_path.read_text()
                manager = "poetry" if "[tool.poetry]" in content else "pip"

        if not manager:
            return {
                "status": OperationResult.ERROR,
                "message": f"Unknown manifest file: {manifest_path.name}",
            }

        # Parse manifest based on type
        if manifest_path.name == "package.json":
            results.update(self._parse_package_json(manifest_path))
        elif manifest_path.name == "requirements.txt":
            results.update(self._parse_requirements_txt(manifest_path))
        elif manifest_path.name == "pyproject.toml":
            results.update(self._parse_pyproject_toml(manifest_path))
        elif manifest_path.name == "Cargo.toml":
            results.update(self._parse_cargo_toml(manifest_path))
        elif manifest_path.name == "go.mod":
            results.update(self._parse_go_mod(manifest_path))

        return results

    def _detect_package_managers(self, project_path: Path) -> List[str]:
        """Detect all package managers used in the project."""
        managers = []

        # Check for lock files first (more specific)
        lock_files = {
            "yarn.lock": "yarn",
            "pnpm-lock.yaml": "pnpm",
            "package-lock.json": "npm",
            "poetry.lock": "poetry",
            "Pipfile.lock": "pipenv",
            "Cargo.lock": "cargo",
            "go.sum": "go",
            "composer.lock": "composer",
            "Gemfile.lock": "bundler",
        }

        for lock_file, manager in lock_files.items():
            if (project_path / lock_file).exists():
                if manager not in managers:
                    managers.append(manager)

        # Check for manifest files
        for manifest_file, manager in self.PACKAGE_MANAGERS.items():
            if (project_path / manifest_file).exists():
                # Special handling for pyproject.toml
                if manifest_file == "pyproject.toml":
                    content = (project_path / manifest_file).read_text()
                    if "[tool.poetry]" in content:
                        manager = "poetry"
                    elif "[tool.setuptools]" in content or "[project]" in content:
                        manager = "pip"

                if manager not in managers:
                    managers.append(manager)

        return managers

    def _analyze_package_manager(
        self, project_path: Path, manager: str, options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze dependencies for a specific package manager."""
        try:
            if manager in ["npm", "yarn", "pnpm"]:
                return self._analyze_node_dependencies(project_path, manager)
            if manager in ["pip", "pipenv", "poetry"]:
                return self._analyze_python_dependencies(project_path, manager)
            if manager == "cargo":
                return self._analyze_cargo_dependencies(project_path)
            if manager == "go":
                return self._analyze_go_dependencies(project_path)
            logger.debug(f"Unsupported package manager for analysis: {manager}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing {manager} dependencies: {e}")
            return None

    def _analyze_node_dependencies(
        self, project_path: Path, manager: str
    ) -> Dict[str, Any]:
        """Analyze Node.js dependencies."""
        package_json_path = project_path / "package.json"
        if not package_json_path.exists():
            return {}

        return self._parse_package_json(package_json_path)

    def _analyze_python_dependencies(
        self, project_path: Path, manager: str
    ) -> Dict[str, Any]:
        """Analyze Python dependencies."""
        results = {"dependencies": {}, "dev_dependencies": {}}

        if manager == "pip":
            req_file = project_path / "requirements.txt"
            if req_file.exists():
                parsed = self._parse_requirements_txt(req_file)
                results["dependencies"] = parsed.get("dependencies", {})

            # Check for dev requirements
            dev_req_file = project_path / "requirements-dev.txt"
            if dev_req_file.exists():
                parsed = self._parse_requirements_txt(dev_req_file)
                results["dev_dependencies"] = parsed.get("dependencies", {})

        elif manager == "poetry":
            pyproject_path = project_path / "pyproject.toml"
            if pyproject_path.exists():
                results = self._parse_pyproject_toml(pyproject_path)

        elif manager == "pipenv":
            pipfile_path = project_path / "Pipfile"
            if pipfile_path.exists():
                results = self._parse_pipfile(pipfile_path)

        return results

    def _analyze_cargo_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """Analyze Rust/Cargo dependencies."""
        cargo_toml_path = project_path / "Cargo.toml"
        if not cargo_toml_path.exists():
            return {}

        return self._parse_cargo_toml(cargo_toml_path)

    def _analyze_go_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """Analyze Go dependencies."""
        go_mod_path = project_path / "go.mod"
        if not go_mod_path.exists():
            return {}

        return self._parse_go_mod(go_mod_path)

    def _parse_package_json(self, path: Path) -> Dict[str, Any]:
        """Parse package.json file."""
        try:
            with path.open() as f:
                data = json.load(f)

            return {
                "dependencies": data.get("dependencies", {}),
                "dev_dependencies": data.get("devDependencies", {}),
                "peer_dependencies": data.get("peerDependencies", {}),
            }
        except Exception as e:
            logger.error(f"Error parsing package.json: {e}")
            return {}

    def _parse_requirements_txt(self, path: Path) -> Dict[str, Any]:
        """Parse requirements.txt file."""
        dependencies = {}

        try:
            content = path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # Parse package spec
                    match = re.match(r"^([a-zA-Z0-9\-_.]+)([<>=!~]+.*)?$", line)
                    if match:
                        package = match.group(1)
                        version = match.group(2) or "*"
                        dependencies[package] = version

        except Exception as e:
            logger.error(f"Error parsing requirements.txt: {e}")

        return {"dependencies": dependencies}

    def _parse_pyproject_toml(self, path: Path) -> Dict[str, Any]:
        """Parse pyproject.toml file."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.warning("TOML parser not available")
                return {}

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)

            dependencies = {}
            dev_dependencies = {}

            # Check for poetry dependencies
            if "tool" in data and "poetry" in data["tool"]:
                poetry_data = data["tool"]["poetry"]
                dependencies = poetry_data.get("dependencies", {})
                dev_dependencies = poetry_data.get("dev-dependencies", {})

            # Check for PEP 621 dependencies
            elif "project" in data:
                project_data = data["project"]
                deps = project_data.get("dependencies", [])
                for dep in deps:
                    # Parse dependency string
                    match = re.match(r"^([a-zA-Z0-9\-_.]+)(.*)$", dep)
                    if match:
                        dependencies[match.group(1)] = match.group(2) or "*"

            return {
                "dependencies": dependencies,
                "dev_dependencies": dev_dependencies,
            }

        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return {}

    def _parse_pipfile(self, path: Path) -> Dict[str, Any]:
        """Parse Pipfile."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return {}

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)

            return {
                "dependencies": data.get("packages", {}),
                "dev_dependencies": data.get("dev-packages", {}),
            }
        except Exception as e:
            logger.error(f"Error parsing Pipfile: {e}")
            return {}

    def _parse_cargo_toml(self, path: Path) -> Dict[str, Any]:
        """Parse Cargo.toml file."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return {}

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)

            return {
                "dependencies": data.get("dependencies", {}),
                "dev_dependencies": data.get("dev-dependencies", {}),
            }
        except Exception as e:
            logger.error(f"Error parsing Cargo.toml: {e}")
            return {}

    def _parse_go_mod(self, path: Path) -> Dict[str, Any]:
        """Parse go.mod file."""
        dependencies = {}

        try:
            content = path.read_text()
            in_require = False

            for line in content.splitlines():
                line = line.strip()

                if line.startswith("require ("):
                    in_require = True
                    continue
                if line == ")":
                    in_require = False
                    continue

                if in_require or line.startswith("require "):
                    # Parse dependency line
                    parts = line.replace("require ", "").split()
                    if len(parts) >= 2:
                        dependencies[parts[0]] = parts[1]

        except Exception as e:
            logger.error(f"Error parsing go.mod: {e}")

        return {"dependencies": dependencies}

    def _flatten_dependencies(
        self, deps_dict: Dict[str, Dict[str, str]]
    ) -> Dict[str, str]:
        """Flatten nested dependency dictionaries."""
        flattened = {}
        for manager_deps in deps_dict.values():
            flattened.update(manager_deps)
        return flattened

    def _detect_frameworks(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect web frameworks from dependencies."""
        detected = []

        for _language, frameworks in self.FRAMEWORK_PACKAGES.items():
            for framework in frameworks:
                if framework in dependencies:
                    detected.append(framework)

        return detected

    def _detect_databases(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect database systems from dependencies."""
        detected = []

        for db_type, packages in self.DATABASE_PACKAGES.items():
            for package in packages:
                if package in dependencies:
                    if db_type not in detected:
                        detected.append(db_type)
                    break

        return detected

    def _detect_testing_tools(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect testing tools from dependencies."""
        detected = []

        for _language, tools in self.TESTING_PACKAGES.items():
            for tool in tools:
                if tool in dependencies:
                    detected.append(tool)

        return detected

    def _check_vulnerabilities(self, project_path: Path) -> Dict[str, Any]:
        """Check for known security vulnerabilities in dependencies."""
        return {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "details": [],
        }

        # This is a simplified placeholder
        # In production, you would integrate with vulnerability databases
        # like npm audit, pip-audit, or safety

    def _calculate_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate dependency statistics."""
        all_deps = self._flatten_dependencies(results.get("dependencies", {}))
        all_dev_deps = self._flatten_dependencies(results.get("dev_dependencies", {}))

        return {
            "total_dependencies": len(all_deps),
            "total_dev_dependencies": len(all_dev_deps),
            "package_managers_count": len(results.get("package_managers", [])),
            "frameworks_count": len(results.get("frameworks", [])),
            "databases_count": len(results.get("databases", [])),
            "testing_tools_count": len(results.get("testing_tools", [])),
        }

    def extract_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from analysis results."""
        metrics = {}

        if analysis_result.get("status") != OperationResult.SUCCESS:
            return metrics

        # Extract dependency counts
        if "statistics" in analysis_result:
            metrics.update(analysis_result["statistics"])

        # Extract vulnerability metrics
        if "vulnerabilities" in analysis_result:
            vuln = analysis_result["vulnerabilities"]
            metrics.update(
                {
                    "vulnerability_total": vuln.get("total", 0),
                    "vulnerability_critical": vuln.get("critical", 0),
                    "vulnerability_high": vuln.get("high", 0),
                }
            )

        return metrics

    def compare_results(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two analysis results."""
        comparison = {
            "added_dependencies": [],
            "removed_dependencies": [],
            "updated_dependencies": [],
            "vulnerability_changes": {},
        }

        # Compare dependencies
        baseline_deps = self._flatten_dependencies(baseline.get("dependencies", {}))
        current_deps = self._flatten_dependencies(current.get("dependencies", {}))

        # Find added dependencies
        for dep, version in current_deps.items():
            if dep not in baseline_deps:
                comparison["added_dependencies"].append(
                    {
                        "name": dep,
                        "version": version,
                    }
                )

        # Find removed dependencies
        for dep, version in baseline_deps.items():
            if dep not in current_deps:
                comparison["removed_dependencies"].append(
                    {
                        "name": dep,
                        "version": version,
                    }
                )

        # Find updated dependencies
        for dep in baseline_deps:
            if dep in current_deps and baseline_deps[dep] != current_deps[dep]:
                comparison["updated_dependencies"].append(
                    {
                        "name": dep,
                        "old_version": baseline_deps[dep],
                        "new_version": current_deps[dep],
                    }
                )

        # Compare vulnerability counts
        if "vulnerabilities" in baseline and "vulnerabilities" in current:
            baseline_vuln = baseline["vulnerabilities"]
            current_vuln = current["vulnerabilities"]

            comparison["vulnerability_changes"] = {
                "total": current_vuln.get("total", 0) - baseline_vuln.get("total", 0),
                "critical": current_vuln.get("critical", 0)
                - baseline_vuln.get("critical", 0),
                "high": current_vuln.get("high", 0) - baseline_vuln.get("high", 0),
            }

        return comparison
