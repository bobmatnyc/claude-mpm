#!/usr/bin/env python3
"""
Project Analyzer Service (Refactored)
=====================================

Analyzes project characteristics to enable project-specific memory creation.

WHY: Instead of creating generic memories, agents need to understand the specific
project they're working on - its tech stack, architecture patterns, coding conventions,
and key components. This service extracts these characteristics automatically.

REFACTORING NOTE: This module has been refactored to follow SOLID principles.
The original god class has been split into focused services:
- LanguageAnalyzerService: Language and framework detection
- DependencyAnalyzerService: Dependency and package management
- ArchitectureAnalyzerService: Architecture and structure analysis
- MetricsCollectorService: Code metrics collection

The main ProjectAnalyzer class now orchestrates these services while maintaining
full backward compatibility with the original interface.

This service analyzes:
- Technology stack from config files (package.json, requirements.txt, etc.)
- Code patterns from source files
- Architecture patterns from directory structure
- Testing frameworks and approaches
- API patterns and endpoints
- Database integrations
- Project-specific terminology and conventions
"""

import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import ProjectAnalyzerInterface
from claude_mpm.core.unified_paths import get_path_manager

# Import refactored services


@dataclass
class ProjectCharacteristics:
    """Structured representation of project characteristics."""

    # Core project info
    project_name: str
    primary_language: Optional[str]
    languages: List[str]
    frameworks: List[str]

    # Architecture and structure
    architecture_type: str
    main_modules: List[str]
    key_directories: List[str]
    entry_points: List[str]

    # Development practices
    testing_framework: Optional[str]
    test_patterns: List[str]
    package_manager: Optional[str]
    build_tools: List[str]

    # Integrations and dependencies
    databases: List[str]
    web_frameworks: List[str]
    api_patterns: List[str]
    key_dependencies: List[str]

    # Project-specific patterns
    code_conventions: List[str]
    configuration_patterns: List[str]
    project_terminology: List[str]

    # Documentation and structure
    documentation_files: List[str]
    important_configs: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ProjectAnalyzer(ProjectAnalyzerInterface):
    """Analyzes project characteristics for context-aware memory creation.

    WHY: Generic agent memories aren't helpful for specific projects. This analyzer
    extracts project-specific characteristics that enable agents to create relevant,
    actionable memories with proper context.

    DESIGN DECISION: Uses a combination of file pattern analysis, content parsing,
    and directory structure analysis to build comprehensive project understanding
    without requiring external tools or API calls.
    """

    # Common configuration files and their indicators
    CONFIG_FILE_PATTERNS = {
        "package.json": "node_js",
        "requirements.txt": "python",
        "pyproject.toml": "python",
        "setup.py": "python",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "build.gradle": "java",
        "composer.json": "php",
        "Gemfile": "ruby",
        "go.mod": "go",
        "CMakeLists.txt": "cpp",
        "Makefile": "c_cpp",
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "flask": ["from flask", "Flask(", "app.route"],
        "django": ["from django", "DJANGO_SETTINGS", "django.contrib"],
        "fastapi": ["from fastapi", "FastAPI(", "@app."],
        "express": ["express()", "app.get(", "app.post("],
        "react": ["import React", "from react", "ReactDOM"],
        "vue": ["Vue.createApp", "new Vue(", "vue-"],
        "angular": ["@Component", "@Injectable", "Angular"],
        "spring": ["@SpringBootApplication", "@RestController", "Spring"],
        "rails": ["Rails.application", "ApplicationController"],
    }

    # Database detection patterns
    DATABASE_PATTERNS = {
        "postgresql": ["psycopg2", "postgresql:", "postgres:", "pg_"],
        "mysql": ["mysql-connector", "mysql:", "MySQLdb"],
        "sqlite": ["sqlite3", "sqlite:", ".db", ".sqlite"],
        "mongodb": ["pymongo", "mongodb:", "mongoose"],
        "redis": ["redis:", "redis-py", "RedisClient"],
        "elasticsearch": ["elasticsearch:", "elastic"],
    }

    def __init__(
        self, config: Optional[Config] = None, working_directory: Optional[Path] = None
    ):
        """Initialize the project analyzer.

        Args:
            config: Optional Config object
            working_directory: Optional working directory path. If not provided, uses current.
        """
        self.config = config or Config()
        self.working_directory = (
            working_directory or get_path_manager().get_project_root()
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Cache for analysis results
        self._analysis_cache: Optional[ProjectCharacteristics] = None
        self._cache_timestamp: Optional[float] = None

    def analyze_project(self, force_refresh: bool = False) -> ProjectCharacteristics:
        """Analyze the current project and return characteristics.

        WHY: Comprehensive project analysis enables agents to create memories
        that are specific to the actual project context, tech stack, and patterns.

        Args:
            force_refresh: If True, ignores cache and performs fresh analysis

        Returns:
            ProjectCharacteristics: Structured project analysis results
        """
        try:
            # Check cache first (unless force refresh)
            if not force_refresh and self._analysis_cache and self._cache_timestamp:
                # Cache is valid for 5 minutes
                import time

                if time.time() - self._cache_timestamp < 300:
                    self.logger.debug("Using cached project analysis")
                    return self._analysis_cache

            self.logger.info(f"Analyzing project at: {self.working_directory}")

            # Initialize characteristics with basic info
            characteristics = ProjectCharacteristics(
                project_name=self.working_directory.name,
                primary_language=None,
                languages=[],
                frameworks=[],
                architecture_type="unknown",
                main_modules=[],
                key_directories=[],
                entry_points=[],
                testing_framework=None,
                test_patterns=[],
                package_manager=None,
                build_tools=[],
                databases=[],
                web_frameworks=[],
                api_patterns=[],
                key_dependencies=[],
                code_conventions=[],
                configuration_patterns=[],
                project_terminology=[],
                documentation_files=[],
                important_configs=[],
            )

            # Perform various analyses
            self._analyze_config_files(characteristics)
            self._analyze_directory_structure(characteristics)
            self._analyze_source_code(characteristics)
            self._analyze_dependencies(characteristics)
            self._analyze_testing_patterns(characteristics)
            self._analyze_documentation(characteristics)
            self._infer_architecture_type(characteristics)
            self._extract_project_terminology(characteristics)

            # Cache the results
            self._analysis_cache = characteristics
            import time

            self._cache_timestamp = time.time()

            self.logger.info(
                f"Project analysis complete: {characteristics.primary_language} project with {len(characteristics.frameworks)} frameworks"
            )
            return characteristics

        except Exception as e:
            self.logger.error(f"Error analyzing project: {e}")
            # Return minimal characteristics on error
            return ProjectCharacteristics(
                project_name=self.working_directory.name,
                primary_language="unknown",
                languages=[],
                frameworks=[],
                architecture_type="unknown",
                main_modules=[],
                key_directories=[],
                entry_points=[],
                testing_framework=None,
                test_patterns=[],
                package_manager=None,
                build_tools=[],
                databases=[],
                web_frameworks=[],
                api_patterns=[],
                key_dependencies=[],
                code_conventions=[],
                configuration_patterns=[],
                project_terminology=[],
                documentation_files=[],
                important_configs=[],
            )

    def _analyze_config_files(self, characteristics: ProjectCharacteristics) -> None:
        """Analyze configuration files to determine tech stack.

        WHY: Configuration files are the most reliable indicators of project
        technology stack and dependencies. They provide definitive information
        about what technologies are actually used.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        config_files = []
        languages_found = set()

        for config_file, language in self.CONFIG_FILE_PATTERNS.items():
            config_path = self.working_directory / config_file
            if config_path.exists():
                config_files.append(config_file)
                languages_found.add(language)
                characteristics.important_configs.append(
                    str(config_path.relative_to(self.working_directory))
                )

                # Parse specific config files for more details
                try:
                    if config_file == "package.json":
                        self._parse_package_json(config_path, characteristics)
                    elif config_file in ["requirements.txt", "pyproject.toml"]:
                        self._parse_python_dependencies(config_path, characteristics)
                    elif config_file == "Cargo.toml":
                        self._parse_cargo_toml(config_path, characteristics)
                except Exception as e:
                    self.logger.warning(f"Error parsing {config_file}: {e}")

        # Set primary language (prefer more specific indicators)
        language_priority = ["python", "node_js", "rust", "java", "go", "php", "ruby"]
        for lang in language_priority:
            if lang in languages_found:
                characteristics.primary_language = lang
                break

        characteristics.languages = list(languages_found)

        # Determine package manager
        if "package.json" in config_files:
            if (self.working_directory / "yarn.lock").exists():
                characteristics.package_manager = "yarn"
            elif (self.working_directory / "pnpm-lock.yaml").exists():
                characteristics.package_manager = "pnpm"
            else:
                characteristics.package_manager = "npm"
        elif "requirements.txt" in config_files or "pyproject.toml" in config_files:
            characteristics.package_manager = "pip"
        elif "Cargo.toml" in config_files:
            characteristics.package_manager = "cargo"

    def _parse_package_json(
        self, package_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Parse package.json for Node.js project details."""
        try:
            with open(package_path) as f:
                package_data = json.load(f)

            # Extract dependencies
            all_deps = {}
            all_deps.update(package_data.get("dependencies", {}))
            all_deps.update(package_data.get("devDependencies", {}))

            # Identify frameworks and tools
            for dep_name in all_deps:
                dep_lower = dep_name.lower()

                # Web frameworks
                if any(fw in dep_lower for fw in ["express", "koa", "hapi"]):
                    characteristics.web_frameworks.append(dep_name)
                elif any(
                    fw in dep_lower for fw in ["react", "vue", "angular", "svelte"]
                ):
                    characteristics.frameworks.append(dep_name)
                elif any(
                    db in dep_lower for db in ["mysql", "postgres", "mongodb", "redis"]
                ):
                    characteristics.databases.append(dep_name)
                elif (
                    any(
                        test in dep_lower
                        for test in ["jest", "mocha", "cypress", "playwright"]
                    )
                    and not characteristics.testing_framework
                ):
                    characteristics.testing_framework = dep_name

                characteristics.key_dependencies.append(dep_name)

            # Check scripts for build tools
            scripts = package_data.get("scripts", {})
            for script_name, script_cmd in scripts.items():
                if any(
                    tool in script_cmd
                    for tool in ["webpack", "rollup", "vite", "parcel"]
                ):
                    characteristics.build_tools.append(script_name)

        except Exception as e:
            self.logger.warning(f"Error parsing package.json: {e}")

    def _parse_python_dependencies(
        self, deps_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Parse Python dependency files."""
        try:
            if deps_path.name == "requirements.txt":
                content = deps_path.read_text()
                deps = [
                    line.strip().split("=")[0].split(">")[0].split("<")[0]
                    for line in content.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
            elif deps_path.name == "pyproject.toml":
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        self.logger.warning(
                            f"TOML parsing not available for {deps_path}"
                        )
                        return
                with open(deps_path, "rb") as f:
                    data = tomllib.load(f)
                deps = list(data.get("project", {}).get("dependencies", []))
                deps.extend(
                    list(
                        data.get("tool", {})
                        .get("poetry", {})
                        .get("dependencies", {})
                        .keys()
                    )
                )
            else:
                return

            # Identify frameworks and tools
            for dep in deps:
                dep_lower = dep.lower()

                # Web frameworks
                if dep_lower in ["flask", "django", "fastapi", "tornado"]:
                    characteristics.web_frameworks.append(dep)
                elif dep_lower in ["pytest", "unittest2", "nose"]:
                    if not characteristics.testing_framework:
                        characteristics.testing_framework = dep
                elif any(
                    db in dep_lower
                    for db in ["psycopg2", "mysql", "sqlite", "redis", "mongo"]
                ):
                    characteristics.databases.append(dep)

                characteristics.key_dependencies.append(dep)

        except Exception as e:
            self.logger.warning(f"Error parsing Python dependencies: {e}")

    def _parse_cargo_toml(
        self, cargo_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Parse Cargo.toml for Rust project details."""
        try:
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    self.logger.warning(f"TOML parsing not available for {cargo_path}")
                    return
            with open(cargo_path, "rb") as f:
                cargo_data = tomllib.load(f)

            deps = cargo_data.get("dependencies", {})
            for dep_name in deps:
                characteristics.key_dependencies.append(dep_name)

                # Identify common Rust frameworks
                if dep_name in ["actix-web", "warp", "rocket"]:
                    characteristics.web_frameworks.append(dep_name)
                elif dep_name in ["tokio", "async-std"]:
                    characteristics.frameworks.append(dep_name)

        except Exception as e:
            self.logger.warning(f"Error parsing Cargo.toml: {e}")

    def _analyze_directory_structure(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Analyze directory structure for architecture patterns.

        WHY: Directory structure reveals architectural decisions and project
        organization patterns that agents should understand and follow.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        # Common important directories to look for
        important_dirs = [
            "src",
            "lib",
            "app",
            "components",
            "services",
            "models",
            "views",
            "controllers",
            "routes",
            "api",
            "web",
            "static",
            "templates",
            "tests",
            "test",
            "__tests__",
            "spec",
            "docs",
            "documentation",
            "config",
            "configs",
            "settings",
            "utils",
            "helpers",
            "core",
            "modules",
            "packages",
            "plugins",
            "extensions",
        ]

        # Check which directories exist
        existing_dirs = []
        for dir_name in important_dirs:
            dir_path = self.working_directory / dir_name
            if dir_path.exists() and dir_path.is_dir():
                existing_dirs.append(dir_name)

                # Special handling for certain directories
                if dir_name in ["src", "lib", "app"]:
                    # These are likely main module directories
                    characteristics.main_modules.extend(
                        self._get_subdirectories(dir_path)
                    )

        characteristics.key_directories = existing_dirs

        # Look for entry points
        entry_point_patterns = [
            "main.py",
            "app.py",
            "server.py",
            "index.js",
            "main.js",
            "app.js",
            "server.js",
            "main.rs",
            "lib.rs",
            "Main.java",
            "main.go",
            "index.php",
            "application.rb",
        ]

        for pattern in entry_point_patterns:
            entry_path = self.working_directory / pattern
            if entry_path.exists():
                characteristics.entry_points.append(pattern)

            # Also check in src/ directory
            src_entry_path = self.working_directory / "src" / pattern
            if src_entry_path.exists():
                characteristics.entry_points.append(f"src/{pattern}")

    def _get_subdirectories(self, path: Path, max_depth: int = 2) -> List[str]:
        """Get subdirectory names up to a certain depth."""
        subdirs = []
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    subdirs.append(item.name)
                    if max_depth > 1:
                        for subitem in item.iterdir():
                            if subitem.is_dir() and not subitem.name.startswith("."):
                                subdirs.append(f"{item.name}/{subitem.name}")
        except PermissionError:
            pass
        return subdirs[:10]  # Limit to prevent overwhelming output

    def _analyze_source_code(self, characteristics: ProjectCharacteristics) -> None:
        """Analyze source code files for patterns and conventions.

        WHY: Source code contains the actual implementation patterns that agents
        should understand and follow. This analysis extracts coding conventions
        and architectural patterns from the codebase.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        source_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".rs": "rust",
            ".java": "java",
            ".go": "go",
            ".php": "php",
            ".rb": "ruby",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".c": "c",
        }

        # Find source files
        source_files = []
        languages_found = set()

        for ext, lang in source_extensions.items():
            files = list(self.working_directory.rglob(f"*{ext}"))
            # Filter out node_modules, .git, etc.
            files = [
                f
                for f in files
                if not any(
                    part.startswith(".") or part == "node_modules" for part in f.parts
                )
            ]
            source_files.extend(files)
            if files:
                languages_found.add(lang)

        # Update languages found
        characteristics.languages.extend(
            [lang for lang in languages_found if lang not in characteristics.languages]
        )

        # Analyze a sample of source files for patterns
        sample_files = source_files[:20]  # Don't analyze too many files

        framework_mentions = Counter()
        pattern_mentions = Counter()

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Look for framework patterns
                for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                    if any(pattern in content for pattern in patterns):
                        framework_mentions[framework] += 1

                # Look for database patterns
                for db, patterns in self.DATABASE_PATTERNS.items():
                    if any(pattern in content for pattern in patterns):
                        if db not in characteristics.databases:
                            characteristics.databases.append(db)

                # Look for common patterns
                if "class " in content and "def __init__" in content:
                    pattern_mentions["object_oriented"] += 1
                if "@app.route" in content or "app.get(" in content:
                    pattern_mentions["web_routes"] += 1
                if "async def" in content or "async function" in content:
                    pattern_mentions["async_programming"] += 1
                if "import pytest" in content or "describe(" in content:
                    pattern_mentions["unit_testing"] += 1

            except Exception as e:
                self.logger.debug(f"Error analyzing {file_path}: {e}")
                continue

        # Add discovered frameworks
        for framework, count in framework_mentions.most_common(5):
            if framework not in characteristics.frameworks:
                characteristics.frameworks.append(framework)

        # Add coding conventions based on patterns found
        for pattern, count in pattern_mentions.most_common():
            if count >= 2:  # Pattern appears in multiple files
                characteristics.code_conventions.append(
                    pattern.replace("_", " ").title()
                )

    def _analyze_dependencies(self, characteristics: ProjectCharacteristics) -> None:
        """Analyze dependencies for integration patterns.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        # This is partially covered by config file analysis
        # Here we can add more sophisticated dependency analysis

        # Look for common integration patterns in dependencies
        api_indicators = [
            "requests",
            "axios",
            "fetch",
            "http",
            "urllib",
            "rest",
            "graphql",
            "grpc",
            "soap",
        ]

        for dep in characteristics.key_dependencies:
            dep_lower = dep.lower()
            for indicator in api_indicators:
                if indicator in dep_lower:
                    if "REST API" not in characteristics.api_patterns:
                        characteristics.api_patterns.append("REST API")
                    break

    def _analyze_testing_patterns(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Analyze testing patterns and frameworks.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        test_dirs = ["tests", "test", "__tests__", "spec"]
        test_patterns = []

        for test_dir in test_dirs:
            test_path = self.working_directory / test_dir
            if test_path.exists() and test_path.is_dir():
                test_patterns.append(f"Tests in /{test_dir}/ directory")

                # Look for test files to understand patterns
                test_files = (
                    list(test_path.rglob("*.py"))
                    + list(test_path.rglob("*.js"))
                    + list(test_path.rglob("*.ts"))
                )

                for test_file in test_files[:5]:  # Sample a few test files
                    try:
                        content = test_file.read_text(encoding="utf-8", errors="ignore")

                        if "def test_" in content:
                            test_patterns.append("Python unittest pattern")
                        if "describe(" in content and "it(" in content:
                            test_patterns.append("BDD test pattern")
                        if "@pytest.fixture" in content:
                            test_patterns.append("pytest fixtures")
                        if "beforeEach(" in content or "beforeAll(" in content:
                            test_patterns.append("Setup/teardown patterns")

                    except Exception:
                        continue

        characteristics.test_patterns = list(set(test_patterns))

    def _analyze_documentation(self, characteristics: ProjectCharacteristics) -> None:
        """Analyze documentation files.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        doc_patterns = [
            "README.md",
            "README.rst",
            "README.txt",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "HISTORY.md",
            "docs/",
            "documentation/",
            "wiki/",
        ]

        doc_files = []
        for pattern in doc_patterns:
            doc_path = self.working_directory / pattern
            if doc_path.exists():
                if doc_path.is_file():
                    doc_files.append(pattern)
                elif doc_path.is_dir():
                    # Find markdown files in doc directories
                    md_files = list(doc_path.rglob("*.md"))[:10]
                    doc_files.extend(
                        [str(f.relative_to(self.working_directory)) for f in md_files]
                    )

        characteristics.documentation_files = doc_files

    def _infer_architecture_type(self, characteristics: ProjectCharacteristics) -> None:
        """Infer architecture type based on discovered patterns.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        # Simple architecture inference based on patterns
        if any(
            fw in characteristics.web_frameworks
            for fw in ["flask", "django", "express", "fastapi"]
        ):
            if "api" in characteristics.key_directories:
                characteristics.architecture_type = "REST API Service"
            else:
                characteristics.architecture_type = "Web Application"
        elif "services" in characteristics.key_directories:
            characteristics.architecture_type = "Service-Oriented Architecture"
        elif (
            "modules" in characteristics.key_directories
            or "packages" in characteristics.key_directories
        ):
            characteristics.architecture_type = "Modular Architecture"
        elif (
            characteristics.primary_language == "python"
            and "cli" in characteristics.main_modules
        ):
            characteristics.architecture_type = "CLI Application"
        elif any("react" in fw.lower() for fw in characteristics.frameworks):
            characteristics.architecture_type = "Single Page Application"
        else:
            characteristics.architecture_type = "Standard Application"

    def _extract_project_terminology(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Extract project-specific terminology from various sources.

        WHY: Projects often have domain-specific terminology that agents should
        understand and use consistently.

        Args:
            characteristics: ProjectCharacteristics object to update
        """
        terminology = set()

        # Extract from project name
        project_words = re.findall(r"[A-Z][a-z]+|[a-z]+", characteristics.project_name)
        terminology.update(project_words)

        # Extract from directory names
        for dir_name in characteristics.key_directories:
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", dir_name)
            terminology.update(words)

        # Extract from main modules
        for module in characteristics.main_modules:
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", module)
            terminology.update(words)

        # Filter out common words and keep domain-specific terms
        common_words = {
            "src",
            "lib",
            "app",
            "main",
            "test",
            "tests",
            "docs",
            "config",
            "utils",
            "helpers",
            "core",
            "base",
            "common",
            "shared",
            "public",
            "private",
            "static",
            "assets",
            "build",
            "dist",
            "node",
            "modules",
        }

        domain_terms = [
            term
            for term in terminology
            if len(term) > 3 and term.lower() not in common_words
        ]

        characteristics.project_terminology = list(set(domain_terms))[
            :10
        ]  # Limit to most relevant

    def get_project_context_summary(self) -> str:
        """Get a concise summary of project context for memory templates.

        WHY: Provides a formatted summary specifically designed for inclusion
        in agent memory templates, focusing on the most relevant characteristics.

        Returns:
            str: Formatted project context summary
        """
        characteristics = self.analyze_project()

        summary_parts = []

        # Basic project info
        lang_info = characteristics.primary_language or "mixed"
        if characteristics.languages and len(characteristics.languages) > 1:
            lang_info = (
                f"{lang_info} (with {', '.join(characteristics.languages[1:3])})"
            )

        summary_parts.append(
            f"{characteristics.project_name}: {lang_info} {characteristics.architecture_type.lower()}"
        )

        # Key directories and modules
        if characteristics.main_modules:
            modules_str = ", ".join(characteristics.main_modules[:4])
            summary_parts.append(f"- Main modules: {modules_str}")

        # Frameworks and tools
        if characteristics.frameworks or characteristics.web_frameworks:
            all_frameworks = characteristics.frameworks + characteristics.web_frameworks
            frameworks_str = ", ".join(all_frameworks[:3])
            summary_parts.append(f"- Uses: {frameworks_str}")

        # Testing
        if characteristics.testing_framework:
            summary_parts.append(f"- Testing: {characteristics.testing_framework}")
        elif characteristics.test_patterns:
            summary_parts.append(f"- Testing: {characteristics.test_patterns[0]}")

        # Key patterns
        if characteristics.code_conventions:
            patterns_str = ", ".join(characteristics.code_conventions[:2])
            summary_parts.append(f"- Key patterns: {patterns_str}")

        return "\n".join(summary_parts)

    def get_important_files_for_context(self) -> List[str]:
        """Get list of important files that should be considered for memory context.

        WHY: Instead of hardcoding which files to analyze for memory creation,
        this method dynamically determines the most relevant files based on
        the actual project structure.

        Returns:
            List[str]: List of file paths relative to project root
        """
        characteristics = self.analyze_project()
        important_files = []

        # Always include standard documentation
        standard_docs = ["README.md", "CONTRIBUTING.md", "CHANGELOG.md"]
        for doc in standard_docs:
            if (self.working_directory / doc).exists():
                important_files.append(doc)

        # Include configuration files
        important_files.extend(characteristics.important_configs)

        # Include project-specific documentation
        important_files.extend(characteristics.documentation_files[:5])

        # Include entry points
        important_files.extend(characteristics.entry_points)

        # Look for architecture documentation
        arch_patterns = ["ARCHITECTURE.md", "docs/architecture.md", "docs/STRUCTURE.md"]
        for pattern in arch_patterns:
            if (self.working_directory / pattern).exists():
                important_files.append(pattern)

        # Remove duplicates and return
        return list(set(important_files))

    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods adapt the existing implementation to comply with ProjectAnalyzerInterface

    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in the project.

        WHY: This adapter method provides interface compliance by extracting
        technology information from the analyzed project characteristics.

        Returns:
            List of detected technologies
        """
        characteristics = self.analyze_project()

        technologies = []
        technologies.extend(characteristics.languages)
        technologies.extend(characteristics.frameworks)
        technologies.extend(characteristics.web_frameworks)
        technologies.extend(characteristics.databases)

        # Add package manager as technology
        if characteristics.package_manager:
            technologies.append(characteristics.package_manager)

        # Add build tools
        technologies.extend(characteristics.build_tools)

        # Remove duplicates
        return list(set(technologies))

    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions.

        WHY: This adapter method provides interface compliance by extracting
        pattern information from the project characteristics.

        Returns:
            Dictionary of pattern analysis results
        """
        characteristics = self.analyze_project()

        return {
            "code_conventions": characteristics.code_conventions,
            "test_patterns": characteristics.test_patterns,
            "api_patterns": characteristics.api_patterns,
            "configuration_patterns": characteristics.configuration_patterns,
            "architecture_type": characteristics.architecture_type,
        }

    def get_project_structure(self) -> Dict[str, Any]:
        """Get project directory structure analysis.

        WHY: This adapter method provides interface compliance by organizing
        structural information from the project characteristics.

        Returns:
            Dictionary representing project structure
        """
        characteristics = self.analyze_project()

        return {
            "project_name": characteristics.project_name,
            "main_modules": characteristics.main_modules,
            "key_directories": characteristics.key_directories,
            "entry_points": characteristics.entry_points,
            "documentation_files": characteristics.documentation_files,
            "important_configs": characteristics.important_configs,
            "architecture_type": characteristics.architecture_type,
        }

    def identify_entry_points(self) -> List[Path]:
        """Identify project entry points.

        WHY: This adapter method provides interface compliance by converting
        string entry points to Path objects as expected by the interface.

        Returns:
            List of entry point paths
        """
        characteristics = self.analyze_project()

        # Convert string paths to Path objects
        entry_paths = []
        for entry_point in characteristics.entry_points:
            entry_path = self.working_directory / entry_point
            if entry_path.exists():
                entry_paths.append(entry_path)

        return entry_paths
