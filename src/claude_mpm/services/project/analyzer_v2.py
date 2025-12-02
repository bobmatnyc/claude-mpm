#!/usr/bin/env python3
"""
Project Analyzer Service V2 (Refactored with SOLID Principles)
===============================================================

This is the refactored version that replaces the original god class.
It maintains 100% backward compatibility while delegating to specialized services.

WHY: The original analyzer.py (1,012 lines) violated the Single Responsibility
Principle. This refactored version delegates work to focused services:
- LanguageAnalyzerService: Language and framework detection
- DependencyAnalyzerService: Dependency and package management
- ArchitectureAnalyzerService: Architecture and structure analysis
- MetricsCollectorService: Code metrics collection

MIGRATION: To use this refactored version, simply replace imports:
  FROM: from claude_mpm.services.project.analyzer import ProjectAnalyzer
  TO:   from claude_mpm.services.project.analyzer_v2 import ProjectAnalyzer
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.config import Config
from claude_mpm.core.interfaces import ProjectAnalyzerInterface
from claude_mpm.core.unified_paths import get_path_manager

# Import the data class from original
from .analyzer import ProjectCharacteristics

# Import refactored services
from .architecture_analyzer import ArchitectureAnalyzerService
from .dependency_analyzer import DependencyAnalyzerService
from .language_analyzer import LanguageAnalyzerService
from .metrics_collector import MetricsCollectorService


class ProjectAnalyzer(ProjectAnalyzerInterface):
    """Refactored ProjectAnalyzer using service composition.

    WHY: This version maintains full backward compatibility while following
    SOLID principles through delegation to specialized services.

    BENEFITS:
    - Reduced complexity: Each service has a single responsibility
    - Better testability: Services can be mocked independently
    - Easier maintenance: Changes are localized to specific services
    - Improved performance: Services can be optimized independently

    COMPATIBILITY: This class provides the exact same interface as the
    original ProjectAnalyzer, ensuring zero breaking changes.
    """

    # Keep original constants for compatibility
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

    DATABASE_PATTERNS = {
        "postgresql": ["psycopg2", "postgresql:", "postgres:", "pg_"],
        "mysql": ["mysql-connector", "mysql:", "MySQLdb"],
        "sqlite": ["sqlite3", "sqlite:", ".db", ".sqlite"],
        "mongodb": ["pymongo", "mongodb:", "mongoose"],
        "redis": ["redis:", "redis-py", "RedisClient"],
        "elasticsearch": ["elasticsearch:", "elastic"],
    }

    def __init__(
        self,
        config: Optional[Config] = None,
        working_directory: Optional[Path] = None,
        # Dependency injection for services (optional)
        language_analyzer: Optional[LanguageAnalyzerService] = None,
        dependency_analyzer: Optional[DependencyAnalyzerService] = None,
        architecture_analyzer: Optional[ArchitectureAnalyzerService] = None,
        metrics_collector: Optional[MetricsCollectorService] = None,
    ):
        """Initialize the refactored project analyzer.

        Args:
            config: Optional Config object
            working_directory: Optional working directory path
            language_analyzer: Optional injected language analyzer service
            dependency_analyzer: Optional injected dependency analyzer service
            architecture_analyzer: Optional injected architecture analyzer service
            metrics_collector: Optional injected metrics collector service
        """
        self.config = config or Config()
        self.working_directory = (
            working_directory or get_path_manager().get_project_root()
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize services (use injected or create new)
        self.language_analyzer = language_analyzer or LanguageAnalyzerService(
            self.working_directory
        )
        self.dependency_analyzer = dependency_analyzer or DependencyAnalyzerService(
            self.working_directory
        )
        self.architecture_analyzer = (
            architecture_analyzer or ArchitectureAnalyzerService(self.working_directory)
        )
        self.metrics_collector = metrics_collector or MetricsCollectorService(
            self.working_directory
        )

        # Cache for analysis results
        self._analysis_cache: Optional[ProjectCharacteristics] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # 5 minutes

    def analyze_project(self, force_refresh: bool = False) -> ProjectCharacteristics:
        """Analyze the current project and return characteristics.

        WHY: Orchestrates multiple specialized services to provide comprehensive
        project analysis while maintaining the original interface.

        Args:
            force_refresh: If True, ignores cache and performs fresh analysis

        Returns:
            ProjectCharacteristics: Structured project analysis results
        """
        try:
            # Check cache first
            if not force_refresh and self._is_cache_valid():
                self.logger.debug("Using cached project analysis")
                return self._analysis_cache

            self.logger.info(f"Analyzing project at: {self.working_directory}")

            # Initialize characteristics
            characteristics = self._create_empty_characteristics()

            # Delegate to specialized services
            self._analyze_with_language_service(characteristics)
            self._analyze_with_dependency_service(characteristics)
            self._analyze_with_architecture_service(characteristics)
            self._enrich_with_metrics(characteristics)

            # Apply any compatibility adjustments
            self._ensure_backward_compatibility(characteristics)

            # Cache the results
            self._update_cache(characteristics)

            self.logger.info(
                f"Project analysis complete: {characteristics.primary_language} project "
                f"with {len(characteristics.frameworks)} frameworks"
            )
            return characteristics

        except Exception as e:
            self.logger.error(f"Error analyzing project: {e}")
            return self._create_empty_characteristics()

    # ================================================================================
    # Service Delegation Methods
    # ================================================================================

    def _analyze_with_language_service(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Delegate language analysis to specialized service."""
        try:
            characteristics.languages = self.language_analyzer.detect_languages()
            characteristics.primary_language = (
                self.language_analyzer.detect_primary_language()
            )
            characteristics.frameworks = self.language_analyzer.detect_frameworks()
            characteristics.code_conventions = (
                self.language_analyzer.analyze_code_style()
            )
        except Exception as e:
            self.logger.warning(f"Error in language analysis: {e}")

    def _analyze_with_dependency_service(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Delegate dependency analysis to specialized service."""
        try:
            characteristics.package_manager = (
                self.dependency_analyzer.detect_package_manager()
            )

            deps = self.dependency_analyzer.analyze_dependencies()
            characteristics.key_dependencies = deps["production"][:20]
            characteristics.databases = self.dependency_analyzer.detect_databases(
                deps["production"] + deps["development"]
            )
            characteristics.web_frameworks = (
                self.dependency_analyzer.detect_web_frameworks(deps["production"])
            )

            testing_frameworks = self.dependency_analyzer.detect_testing_frameworks(
                deps["development"] + deps["testing"]
            )
            if testing_frameworks:
                characteristics.testing_framework = testing_frameworks[0]

            characteristics.build_tools = self.dependency_analyzer.get_build_tools()
        except Exception as e:
            self.logger.warning(f"Error in dependency analysis: {e}")

    def _analyze_with_architecture_service(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Delegate architecture analysis to specialized service."""
        try:
            arch_info = self.architecture_analyzer.analyze_architecture()

            characteristics.architecture_type = arch_info.architecture_type
            characteristics.main_modules = arch_info.main_modules
            characteristics.key_directories = arch_info.key_directories
            characteristics.entry_points = arch_info.entry_points
            characteristics.api_patterns = arch_info.api_patterns
            characteristics.configuration_patterns = arch_info.configuration_patterns
            characteristics.project_terminology = arch_info.project_terminology

            design_patterns = self.architecture_analyzer.detect_design_patterns()
            for pattern in design_patterns[:3]:
                pattern_name = pattern.replace("_", " ").title() + " Pattern"
                if pattern_name not in characteristics.code_conventions:
                    characteristics.code_conventions.append(pattern_name)
        except Exception as e:
            self.logger.warning(f"Error in architecture analysis: {e}")

    def _enrich_with_metrics(self, characteristics: ProjectCharacteristics) -> None:
        """Enrich characteristics with metrics data."""
        try:
            metrics = self.metrics_collector.collect_metrics()

            if metrics.test_files > 0:
                characteristics.test_patterns.append(f"{metrics.test_files} test files")
            if metrics.test_to_code_ratio > 0:
                ratio_pct = int(metrics.test_to_code_ratio * 100)
                characteristics.test_patterns.append(
                    f"{ratio_pct}% test coverage ratio"
                )
            if metrics.test_coverage_files > 0:
                characteristics.test_patterns.append("Test coverage tracking")

            # Find documentation files
            doc_patterns = ["README*", "CONTRIBUTING*", "CHANGELOG*", "docs/*"]
            doc_files = []
            for pattern in doc_patterns:
                matches = list(self.working_directory.glob(pattern))
                doc_files.extend(
                    [
                        str(f.relative_to(self.working_directory))
                        for f in matches
                        if f.is_file()
                    ]
                )
            characteristics.documentation_files = doc_files[:10]

            # Find important configs
            config_patterns = ["*.json", "*.yaml", "*.yml", "*.toml", "*.ini", ".env*"]
            config_files = []
            for pattern in config_patterns:
                matches = list(self.working_directory.glob(pattern))
                config_files.extend(
                    [
                        str(f.relative_to(self.working_directory))
                        for f in matches
                        if f.is_file()
                    ]
                )
            characteristics.important_configs = config_files[:10]
        except Exception as e:
            self.logger.warning(f"Error collecting metrics: {e}")

    def _ensure_backward_compatibility(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Ensure compatibility with original analyzer behavior."""
        # Ensure test patterns always has "Tests in /tests/ directory" if tests exist
        if (self.working_directory / "tests").exists():
            pattern = "Tests in /tests/ directory"
            if pattern not in characteristics.test_patterns:
                characteristics.test_patterns.insert(0, pattern)
        elif (self.working_directory / "test").exists():
            pattern = "Tests in /test/ directory"
            if pattern not in characteristics.test_patterns:
                characteristics.test_patterns.insert(0, pattern)

    # ================================================================================
    # Backward Compatibility Methods (Delegate to services)
    # ================================================================================

    def _analyze_config_files(self, characteristics: ProjectCharacteristics) -> None:
        """Backward compatibility method - delegates to dependency service."""
        self._analyze_with_dependency_service(characteristics)

    def _analyze_directory_structure(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method - delegates to architecture service."""
        arch_info = self.architecture_analyzer.analyze_architecture()
        characteristics.key_directories = arch_info.key_directories
        characteristics.main_modules = arch_info.main_modules
        characteristics.entry_points = arch_info.entry_points

    def _analyze_source_code(self, characteristics: ProjectCharacteristics) -> None:
        """Backward compatibility method - delegates to language service."""
        self._analyze_with_language_service(characteristics)

    def _analyze_dependencies(self, characteristics: ProjectCharacteristics) -> None:
        """Backward compatibility method - delegates to dependency service."""
        deps = self.dependency_analyzer.analyze_dependencies()
        characteristics.key_dependencies = deps["production"][:20]

    def _analyze_testing_patterns(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method - analyzes testing patterns."""
        self._ensure_backward_compatibility(characteristics)

    def _analyze_documentation(self, characteristics: ProjectCharacteristics) -> None:
        """Backward compatibility method - finds documentation files."""
        doc_patterns = ["README*", "CONTRIBUTING*", "CHANGELOG*", "docs/*"]
        doc_files = []
        for pattern in doc_patterns:
            matches = list(self.working_directory.glob(pattern))
            doc_files.extend(
                [
                    str(f.relative_to(self.working_directory))
                    for f in matches
                    if f.is_file()
                ]
            )
        characteristics.documentation_files = doc_files[:10]

    def _infer_architecture_type(self, characteristics: ProjectCharacteristics) -> None:
        """Backward compatibility method - already handled by architecture service."""
        # Architecture type is set by architecture service

    def _extract_project_terminology(
        self, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method - already handled by architecture service."""
        # Terminology is extracted by architecture service

    def _parse_package_json(
        self, package_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method for package.json parsing."""
        deps = self.dependency_analyzer.analyze_dependencies()
        characteristics.key_dependencies.extend(deps["production"][:10])
        characteristics.web_frameworks = self.dependency_analyzer.detect_web_frameworks(
            deps["production"]
        )
        characteristics.build_tools = self.dependency_analyzer.get_build_tools()

    def _parse_python_dependencies(
        self, deps_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method for Python dependency parsing."""
        deps = self.dependency_analyzer.analyze_dependencies()
        characteristics.key_dependencies.extend(deps["production"][:10])
        characteristics.web_frameworks = self.dependency_analyzer.detect_web_frameworks(
            deps["production"]
        )

    def _parse_cargo_toml(
        self, cargo_path: Path, characteristics: ProjectCharacteristics
    ) -> None:
        """Backward compatibility method for Cargo.toml parsing."""
        deps = self.dependency_analyzer.analyze_dependencies()
        characteristics.key_dependencies.extend(deps["production"][:10])

    def _get_subdirectories(self, path: Path, max_depth: int = 2) -> List[str]:
        """Backward compatibility method - get subdirectory names."""
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
        return subdirs[:10]

    # ================================================================================
    # Interface Methods
    # ================================================================================

    def detect_technology_stack(self) -> List[str]:
        """Detect technologies used in the project."""
        characteristics = self.analyze_project()

        technologies = []
        technologies.extend(characteristics.languages)
        technologies.extend(characteristics.frameworks)
        technologies.extend(characteristics.web_frameworks)
        technologies.extend(characteristics.databases)

        if characteristics.package_manager:
            technologies.append(characteristics.package_manager)
        technologies.extend(characteristics.build_tools)

        return list(set(technologies))

    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and conventions."""
        characteristics = self.analyze_project()

        return {
            "code_conventions": characteristics.code_conventions,
            "test_patterns": characteristics.test_patterns,
            "api_patterns": characteristics.api_patterns,
            "configuration_patterns": characteristics.configuration_patterns,
            "architecture_type": characteristics.architecture_type,
        }

    def get_project_structure(self) -> Dict[str, Any]:
        """Get project directory structure analysis."""
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
        """Identify project entry points."""
        characteristics = self.analyze_project()

        entry_paths = []
        for entry_point in characteristics.entry_points:
            entry_path = self.working_directory / entry_point
            if entry_path.exists():
                entry_paths.append(entry_path)
        return entry_paths

    def get_project_context_summary(self) -> str:
        """Get a concise summary of project context for memory templates."""
        characteristics = self.analyze_project()

        summary_parts = []

        lang_info = characteristics.primary_language or "mixed"
        if characteristics.languages and len(characteristics.languages) > 1:
            lang_info = (
                f"{lang_info} (with {', '.join(characteristics.languages[1:3])})"
            )

        summary_parts.append(
            f"{characteristics.project_name}: {lang_info} {characteristics.architecture_type.lower()}"
        )

        if characteristics.main_modules:
            modules_str = ", ".join(characteristics.main_modules[:4])
            summary_parts.append(f"- Main modules: {modules_str}")

        if characteristics.frameworks or characteristics.web_frameworks:
            all_frameworks = characteristics.frameworks + characteristics.web_frameworks
            frameworks_str = ", ".join(all_frameworks[:3])
            summary_parts.append(f"- Uses: {frameworks_str}")

        if characteristics.testing_framework:
            summary_parts.append(f"- Testing: {characteristics.testing_framework}")
        elif characteristics.test_patterns:
            summary_parts.append(f"- Testing: {characteristics.test_patterns[0]}")

        if characteristics.code_conventions:
            patterns_str = ", ".join(characteristics.code_conventions[:2])
            summary_parts.append(f"- Key patterns: {patterns_str}")

        return "\n".join(summary_parts)

    def get_important_files_for_context(self) -> List[str]:
        """Get list of important files for memory context."""
        characteristics = self.analyze_project()
        important_files = []

        standard_docs = ["README.md", "CONTRIBUTING.md", "CHANGELOG.md"]
        for doc in standard_docs:
            if (self.working_directory / doc).exists():
                important_files.append(doc)

        important_files.extend(characteristics.important_configs)
        important_files.extend(characteristics.documentation_files[:5])
        important_files.extend(characteristics.entry_points)

        arch_patterns = ["ARCHITECTURE.md", "docs/architecture.md", "docs/STRUCTURE.md"]
        for pattern in arch_patterns:
            if (self.working_directory / pattern).exists():
                important_files.append(pattern)

        return list(set(important_files))

    # ================================================================================
    # Helper Methods
    # ================================================================================

    def _create_empty_characteristics(self) -> ProjectCharacteristics:
        """Create empty ProjectCharacteristics with defaults."""
        return ProjectCharacteristics(
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

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._analysis_cache is None or self._cache_timestamp is None:
            return False
        return time.time() - self._cache_timestamp < self._cache_ttl

    def _update_cache(self, characteristics: ProjectCharacteristics) -> None:
        """Update the cache with new results."""
        self._analysis_cache = characteristics
        self._cache_timestamp = time.time()
