#!/usr/bin/env python3
"""
Dependency Analyzer Service
===========================

WHY: Separates dependency analysis from the main analyzer to follow
single responsibility principle. Handles parsing and analysis of
project dependencies across different package managers.

DECISION: Create a focused service for dependency analysis that can
handle multiple package managers and provide detailed dependency insights.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


class DependencyAnalyzerService:
    """Analyzes project dependencies and package management.

    WHY: Dependency analysis is complex and varies by ecosystem. This service
    provides a unified interface for analyzing dependencies across different
    package managers and languages.
    """

    # Configuration file to package manager mapping
    PACKAGE_MANAGERS = {
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
    DATABASE_PACKAGES = {
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
    TESTING_PACKAGES = {
        "python": ["pytest", "unittest", "nose", "nose2", "tox"],
        "javascript": ["jest", "mocha", "chai", "jasmine", "cypress", "playwright"],
        "java": ["junit", "testng", "mockito"],
        "ruby": ["rspec", "minitest"],
        "go": ["testify", "ginkgo"],
        "rust": ["test", "quickcheck", "proptest"],
    }

    def __init__(self, working_directory: Path):
        """Initialize the dependency analyzer service.

        Args:
            working_directory: Project root directory
        """
        self.working_directory = working_directory
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def detect_package_manager(self) -> Optional[str]:
        """Detect the primary package manager used in the project.

        WHY: Knowing the package manager helps understand the project's
        ecosystem and how to install/manage dependencies.

        Returns:
            Package manager name or None
        """
        # Check for lock files first (more specific)
        lock_files = [
            "yarn.lock",
            "pnpm-lock.yaml",
            "package-lock.json",
            "poetry.lock",
            "Pipfile.lock",
            "Cargo.lock",
        ]

        for lock_file in lock_files:
            if (self.working_directory / lock_file).exists():
                if lock_file in self.PACKAGE_MANAGERS:
                    return self.PACKAGE_MANAGERS[lock_file]

        # Then check for config files
        for config_file, manager in self.PACKAGE_MANAGERS.items():
            if (self.working_directory / config_file).exists():
                return manager

        return None

    def analyze_dependencies(self) -> Dict[str, List[str]]:
        """Analyze all project dependencies.

        WHY: Understanding dependencies helps identify the project's
        technology stack and integration points.

        Returns:
            Dictionary with categories of dependencies
        """
        dependencies = {
            "production": [],
            "development": [],
            "databases": [],
            "testing": [],
            "build_tools": [],
        }

        # Analyze package.json
        package_json_path = self.working_directory / "package.json"
        if package_json_path.exists():
            self._analyze_package_json(package_json_path, dependencies)

        # Analyze Python dependencies
        for py_file in ["requirements.txt", "pyproject.toml", "Pipfile"]:
            py_path = self.working_directory / py_file
            if py_path.exists():
                self._analyze_python_deps(py_path, dependencies)

        # Analyze Cargo.toml
        cargo_path = self.working_directory / "Cargo.toml"
        if cargo_path.exists():
            self._analyze_cargo_toml(cargo_path, dependencies)

        # Analyze go.mod
        go_mod_path = self.working_directory / "go.mod"
        if go_mod_path.exists():
            self._analyze_go_mod(go_mod_path, dependencies)

        return dependencies

    def detect_databases(self, dependencies: Optional[List[str]] = None) -> List[str]:
        """Detect database systems from dependencies.

        WHY: Database detection helps understand data persistence patterns
        and integration requirements.

        Args:
            dependencies: Optional list of dependencies to analyze

        Returns:
            List of detected database names
        """
        if dependencies is None:
            all_deps = self.analyze_dependencies()
            dependencies = all_deps["production"] + all_deps["development"]

        databases = set()

        for dep in dependencies:
            dep_lower = dep.lower()
            for db_name, db_packages in self.DATABASE_PACKAGES.items():
                if any(pkg in dep_lower for pkg in db_packages):
                    databases.add(db_name)

        return sorted(databases)

    def detect_testing_frameworks(
        self, dependencies: Optional[List[str]] = None
    ) -> List[str]:
        """Detect testing frameworks from dependencies.

        WHY: Understanding testing tools helps maintain and extend
        the project's test suite appropriately.

        Args:
            dependencies: Optional list of dependencies to analyze

        Returns:
            List of detected testing framework names
        """
        if dependencies is None:
            all_deps = self.analyze_dependencies()
            dependencies = all_deps["development"] + all_deps["testing"]

        testing_frameworks = set()

        for dep in dependencies:
            dep_lower = dep.lower()
            for test_packages in self.TESTING_PACKAGES.values():
                for test_pkg in test_packages:
                    if test_pkg in dep_lower:
                        testing_frameworks.add(dep)
                        break

        return sorted(testing_frameworks)

    def detect_web_frameworks(self, dependencies: List[str]) -> List[str]:
        """Detect web frameworks from dependencies.

        WHY: Web frameworks indicate the project type and determine
        specific patterns agents should understand.

        Args:
            dependencies: List of project dependencies

        Returns:
            List of detected web framework names
        """
        web_frameworks = []
        web_framework_names = [
            "flask",
            "django",
            "fastapi",
            "tornado",
            "bottle",
            "pyramid",  # Python
            "express",
            "koa",
            "hapi",
            "fastify",
            "nestjs",  # JavaScript
            "rails",
            "sinatra",
            "hanami",  # Ruby
            "laravel",
            "symfony",
            "slim",
            "lumen",  # PHP
            "spring",
            "springboot",
            "struts",
            "play",  # Java
            "actix-web",
            "warp",
            "rocket",  # Rust
            "gin",
            "echo",
            "fiber",  # Go
            "aspnet",
            "aspnetcore",  # C#
        ]

        for dep in dependencies:
            dep_lower = dep.lower()
            for framework in web_framework_names:
                if framework in dep_lower:
                    web_frameworks.append(dep)
                    break

        return list(set(web_frameworks))

    def get_build_tools(
        self, package_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Extract build tools from package configuration.

        WHY: Build tools determine how the project is compiled, bundled,
        and prepared for deployment.

        Args:
            package_data: Optional package.json data

        Returns:
            List of build tool names
        """
        build_tools = []

        # Check package.json scripts
        if package_data is None:
            package_json_path = self.working_directory / "package.json"
            if package_json_path.exists():
                try:
                    with package_json_path.open() as f:
                        package_data = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error reading package.json: {e}")
                    return []

        if package_data and "scripts" in package_data:
            scripts = package_data["scripts"]

            # Common build tools
            build_tool_names = [
                "webpack",
                "rollup",
                "vite",
                "parcel",
                "esbuild",
                "browserify",
                "gulp",
                "grunt",
                "make",
                "cmake",
            ]

            for script_cmd in scripts.values():
                for tool in build_tool_names:
                    if tool in script_cmd.lower():
                        build_tools.append(tool)

        # Check for Makefile
        if (self.working_directory / "Makefile").exists():
            build_tools.append("make")

        # Check for gradle/maven
        if (self.working_directory / "build.gradle").exists():
            build_tools.append("gradle")
        if (self.working_directory / "pom.xml").exists():
            build_tools.append("maven")

        return list(set(build_tools))

    def _analyze_package_json(
        self, path: Path, dependencies: Dict[str, List[str]]
    ) -> None:
        """Parse package.json for dependencies."""
        try:
            with path.open() as f:
                data = json.load(f)

            # Production dependencies
            if "dependencies" in data:
                dependencies["production"].extend(data["dependencies"].keys())

            # Development dependencies
            if "devDependencies" in data:
                dependencies["development"].extend(data["devDependencies"].keys())

            # Detect databases
            all_deps = list(data.get("dependencies", {}).keys()) + list(
                data.get("devDependencies", {}).keys()
            )

            for dep in all_deps:
                dep_lower = dep.lower()
                # Check for database packages
                for _db_name, db_packages in self.DATABASE_PACKAGES.items():
                    if any(pkg in dep_lower for pkg in db_packages):
                        dependencies["databases"].append(dep)

                # Check for testing packages
                for test_packages in self.TESTING_PACKAGES.values():
                    if any(pkg in dep_lower for pkg in test_packages):
                        dependencies["testing"].append(dep)

            # Extract build tools
            build_tools = self.get_build_tools(data)
            dependencies["build_tools"].extend(build_tools)

        except Exception as e:
            self.logger.warning(f"Error parsing package.json: {e}")

    def _analyze_python_deps(
        self, path: Path, dependencies: Dict[str, List[str]]
    ) -> None:
        """Parse Python dependency files."""
        try:
            if path.name == "requirements.txt":
                content = path.read_text()
                deps = [
                    line.strip().split("=")[0].split(">")[0].split("<")[0].split("[")[0]
                    for line in content.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                dependencies["production"].extend(deps)

            elif path.name == "pyproject.toml":
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        return

                with path.open("rb") as f:
                    data = tomllib.load(f)

                # PEP 621 dependencies
                project_deps = data.get("project", {}).get("dependencies", [])
                dependencies["production"].extend(project_deps)

                # Poetry dependencies
                poetry_deps = (
                    data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                )
                dependencies["production"].extend(poetry_deps.keys())

                # Development dependencies
                dev_deps = (
                    data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
                )
                dependencies["development"].extend(dev_deps.keys())

            # Categorize Python dependencies
            for dep_list in [dependencies["production"], dependencies["development"]]:
                for dep in dep_list:
                    dep_lower = dep.lower()

                    # Check databases
                    for _db_name, db_packages in self.DATABASE_PACKAGES.items():
                        if any(pkg in dep_lower for pkg in db_packages):
                            dependencies["databases"].append(dep)

                    # Check testing
                    if any(
                        test in dep_lower for test in self.TESTING_PACKAGES["python"]
                    ):
                        dependencies["testing"].append(dep)

        except Exception as e:
            self.logger.warning(f"Error parsing Python dependencies: {e}")

    def _analyze_cargo_toml(
        self, path: Path, dependencies: Dict[str, List[str]]
    ) -> None:
        """Parse Cargo.toml for Rust dependencies."""
        try:
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    return

            with path.open("rb") as f:
                data = tomllib.load(f)

            # Production dependencies
            deps = data.get("dependencies", {})
            dependencies["production"].extend(deps.keys())

            # Dev dependencies
            dev_deps = data.get("dev-dependencies", {})
            dependencies["development"].extend(dev_deps.keys())

        except Exception as e:
            self.logger.warning(f"Error parsing Cargo.toml: {e}")

    def _analyze_go_mod(self, path: Path, dependencies: Dict[str, List[str]]) -> None:
        """Parse go.mod for Go dependencies."""
        try:
            content = path.read_text()

            # Extract require blocks
            import re

            requires = re.findall(r"require\s+([^\s]+)\s+v", content)
            dependencies["production"].extend(requires)

        except Exception as e:
            self.logger.warning(f"Error parsing go.mod: {e}")
