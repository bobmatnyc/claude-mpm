#!/usr/bin/env python3
"""
Architecture Analyzer Service
=============================

WHY: Separates architectural pattern detection from the main analyzer to follow
single responsibility principle. Identifies project architecture, structure
patterns, and organization principles.

DECISION: Create a focused service for architecture analysis that can
identify patterns like MVC, microservices, layered architecture, etc.
"""

import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import ClassVar, Dict, List


@dataclass
class ArchitectureInfo:
    """Container for architecture analysis results."""

    architecture_type: str
    patterns_detected: List[str]
    main_modules: List[str]
    key_directories: List[str]
    entry_points: List[str]
    api_patterns: List[str]
    configuration_patterns: List[str]
    project_terminology: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class ArchitectureAnalyzerService:
    """Analyzes project architecture and structural patterns.

    WHY: Understanding project architecture helps agents work within
    established patterns and maintain architectural consistency.
    """

    # Common architectural directories
    ARCHITECTURE_INDICATORS: ClassVar[dict] = {
        "mvc": ["models", "views", "controllers"],
        "mvvm": ["models", "views", "viewmodels"],
        "layered": ["presentation", "business", "data", "domain"],
        "hexagonal": ["domain", "application", "infrastructure", "adapters"],
        "clean": ["entities", "usecases", "interfaces", "frameworks"],
        "microservices": ["services", "api-gateway", "service-discovery"],
        "modular": ["modules", "packages", "components"],
        "plugin": ["plugins", "extensions", "addons"],
        "event_driven": ["events", "handlers", "listeners", "publishers"],
        "serverless": ["functions", "lambdas", "handlers"],
    }

    # Entry point patterns by language/framework
    ENTRY_POINT_PATTERNS: ClassVar[dict] = {
        "python": [
            "main.py",
            "app.py",
            "server.py",
            "run.py",
            "__main__.py",
            "wsgi.py",
        ],
        "javascript": ["index.js", "main.js", "app.js", "server.js", "index.ts"],
        "java": ["Main.java", "Application.java", "App.java"],
        "go": ["main.go", "cmd/*/main.go"],
        "rust": ["main.rs", "lib.rs"],
        "ruby": ["app.rb", "application.rb", "config.ru"],
        "php": ["index.php", "app.php"],
        "csharp": ["Program.cs", "Startup.cs"],
    }

    # API pattern indicators
    API_INDICATORS: ClassVar[dict] = {
        "rest": ["routes", "endpoints", "resources", "api/v", "/api/"],
        "graphql": ["schema.graphql", "resolvers", "typeDefs", "graphql"],
        "grpc": [".proto", "grpc", "protobuf", "rpc"],
        "websocket": ["ws://", "wss://", "socket.io", "websocket"],
        "soap": [".wsdl", "soap", "xml-rpc"],
    }

    # Configuration file patterns
    CONFIG_PATTERNS: ClassVar[dict] = {
        "yaml": [".yaml", ".yml"],
        "json": [".json", "config.json", "settings.json"],
        "toml": [".toml", "pyproject.toml", "Cargo.toml"],
        "ini": [".ini", ".cfg", "setup.cfg"],
        "env": [".env", ".env.example", ".env.local"],
        "xml": [".xml", "pom.xml", "web.xml"],
    }

    def __init__(self, working_directory: Path):
        """Initialize the architecture analyzer service.

        Args:
            working_directory: Project root directory
        """
        self.working_directory = working_directory
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_architecture(self) -> ArchitectureInfo:
        """Analyze project architecture and structure.

        WHY: Understanding architecture helps maintain consistency
        and work within established patterns.

        Returns:
            ArchitectureInfo with analysis results
        """
        info = ArchitectureInfo(
            architecture_type="unknown",
            patterns_detected=[],
            main_modules=[],
            key_directories=[],
            entry_points=[],
            api_patterns=[],
            configuration_patterns=[],
            project_terminology=[],
        )

        # Analyze directory structure
        self._analyze_directory_patterns(info)

        # Detect entry points
        self._detect_entry_points(info)

        # Detect API patterns
        self._detect_api_patterns(info)

        # Detect configuration patterns
        self._detect_config_patterns(info)

        # Extract project terminology
        self._extract_terminology(info)

        # Infer architecture type
        self._infer_architecture_type(info)

        return info

    def detect_design_patterns(self) -> List[str]:
        """Detect design patterns used in the project.

        WHY: Understanding design patterns helps maintain
        consistent implementation approaches.

        Returns:
            List of detected design pattern names
        """
        patterns = []

        # Sample some source files
        source_files = self._get_sample_source_files()

        pattern_indicators = {
            "singleton": [r"getInstance\(\)", r"_instance\s*=", r"@singleton"],
            "factory": [r"Factory", r"create\w+\(\)", r"@factory"],
            "observer": [r"subscribe\(", r"notify\(", r"addEventListener"],
            "strategy": [r"Strategy", r"setStrategy\(", r"execute\("],
            "decorator": [r"@\w+", r"Decorator", r"wrapper"],
            "repository": [r"Repository", r"find\w+By", r"save\("],
            "dependency_injection": [r"@inject", r"@autowired", r"container\."],
            "mvc": [r"Controller", r"Model", r"View"],
            "middleware": [r"middleware", r"use\(", r"next\("],
        }

        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for pattern_name, indicators in pattern_indicators.items():
                    if any(re.search(ind, content) for ind in indicators):
                        if pattern_name not in patterns:
                            patterns.append(pattern_name)

            except Exception as e:
                self.logger.debug(f"Error detecting patterns in {file_path}: {e}")

        return patterns

    def analyze_module_structure(self) -> Dict[str, List[str]]:
        """Analyze module organization and dependencies.

        WHY: Module structure reveals how code is organized
        and helps understand component relationships.

        Returns:
            Dictionary mapping modules to their components
        """
        modules = {}

        # Look for common module directories
        module_dirs = ["src", "lib", "app", "modules", "packages", "components"]

        for module_dir in module_dirs:
            module_path = self.working_directory / module_dir
            if module_path.exists() and module_path.is_dir():
                # Get immediate subdirectories as modules
                for subdir in module_path.iterdir():
                    if subdir.is_dir() and not subdir.name.startswith("."):
                        module_name = subdir.name

                        # Get module components
                        components = []
                        for item in subdir.iterdir():
                            if item.is_file():
                                components.append(item.name)
                            elif item.is_dir() and not item.name.startswith("."):
                                components.append(f"{item.name}/")

                        if components:
                            modules[module_name] = components[:10]  # Limit to 10

        return modules

    def _analyze_directory_patterns(self, info: ArchitectureInfo) -> None:
        """Analyze directory structure for architectural patterns."""
        existing_dirs = set()

        # Collect all directory names
        for _dirpath, dirnames, _ in self.working_directory.walk():
            for dirname in dirnames:
                if not dirname.startswith("."):
                    existing_dirs.add(dirname.lower())

        # Check for architectural patterns
        for arch_type, indicators in self.ARCHITECTURE_INDICATORS.items():
            matches = sum(1 for ind in indicators if ind in existing_dirs)
            if matches >= len(indicators) * 0.6:  # 60% match threshold
                info.patterns_detected.append(arch_type)

        # Identify key directories
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
            "tests",
            "docs",
            "config",
            "utils",
            "helpers",
            "core",
            "modules",
            "packages",
        ]

        info.key_directories = [
            d for d in important_dirs if (self.working_directory / d).exists()
        ]

        # Identify main modules (top-level important directories)
        for key_dir in ["src", "lib", "app"]:
            key_path = self.working_directory / key_dir
            if key_path.exists() and key_path.is_dir():
                subdirs = [
                    d.name
                    for d in key_path.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                ]
                info.main_modules.extend(subdirs[:5])  # Top 5 modules

    def _detect_entry_points(self, info: ArchitectureInfo) -> None:
        """Detect project entry points."""
        entry_points = []

        for patterns in self.ENTRY_POINT_PATTERNS.values():
            for pattern in patterns:
                # Handle glob patterns
                if "*" in pattern:
                    for match in self.working_directory.glob(pattern):
                        if match.is_file():
                            rel_path = str(match.relative_to(self.working_directory))
                            entry_points.append(rel_path)
                else:
                    # Check direct path and in src/
                    for base in ["", "src/", "app/", "lib/"]:
                        entry_path = self.working_directory / base / pattern
                        if entry_path.exists() and entry_path.is_file():
                            rel_path = str(
                                entry_path.relative_to(self.working_directory)
                            )
                            entry_points.append(rel_path)

        info.entry_points = list(set(entry_points))[:10]  # Limit to 10

    def _detect_api_patterns(self, info: ArchitectureInfo) -> None:
        """Detect API patterns and styles."""
        api_patterns = []

        # Check directory structure
        for api_type, indicators in self.API_INDICATORS.items():
            for indicator in indicators:
                # Check for directories
                if "/" in indicator:
                    if any(
                        indicator in str(p)
                        for p in self.working_directory.rglob("*")
                        if p.is_dir()
                    ):
                        api_patterns.append(api_type.upper())
                        break

                # Check for files
                elif "." in indicator:
                    if list(self.working_directory.rglob(f"*{indicator}")):
                        api_patterns.append(api_type.upper())
                        break

        # Check source files for API patterns
        source_files = self._get_sample_source_files(limit=10)
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # REST API patterns
                if any(
                    p in content for p in ["@app.route", "@router.", "@Get(", "@Post("]
                ):
                    api_patterns.append("REST")

                # GraphQL patterns
                if any(p in content for p in ["graphql", "resolver", "typeDefs"]):
                    api_patterns.append("GraphQL")

            except Exception as e:
                self.logger.debug(f"Error detecting API patterns in {file_path}: {e}")

        info.api_patterns = list(set(api_patterns))

    def _detect_config_patterns(self, info: ArchitectureInfo) -> None:
        """Detect configuration file patterns."""
        config_patterns = []

        for config_type, extensions in self.CONFIG_PATTERNS.items():
            for ext in extensions:
                if list(self.working_directory.rglob(f"*{ext}")):
                    config_patterns.append(config_type)
                    break

        info.configuration_patterns = config_patterns

    def _extract_terminology(self, info: ArchitectureInfo) -> None:
        """Extract project-specific terminology."""
        terminology = set()

        # Extract from project name
        project_words = re.findall(r"[A-Z][a-z]+|[a-z]+", self.working_directory.name)
        terminology.update(project_words)

        # Extract from main modules
        for module in info.main_modules:
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", module)
            terminology.update(words)

        # Extract from key directories
        for directory in info.key_directories:
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", directory)
            terminology.update(words)

        # Filter out common words
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
            "vendor",
            "bin",
            "obj",
        }

        domain_terms = [
            term
            for term in terminology
            if len(term) > 3 and term.lower() not in common_words
        ]

        info.project_terminology = sorted(domain_terms)[:15]  # Top 15 terms

    def _infer_architecture_type(self, info: ArchitectureInfo) -> None:
        """Infer the overall architecture type."""
        # Check detected patterns
        if "microservices" in info.patterns_detected:
            info.architecture_type = "Microservices Architecture"
        elif "hexagonal" in info.patterns_detected:
            info.architecture_type = "Hexagonal Architecture"
        elif "clean" in info.patterns_detected:
            info.architecture_type = "Clean Architecture"
        elif "mvc" in info.patterns_detected:
            info.architecture_type = "MVC Architecture"
        elif "layered" in info.patterns_detected:
            info.architecture_type = "Layered Architecture"
        elif "event_driven" in info.patterns_detected:
            info.architecture_type = "Event-Driven Architecture"
        elif "serverless" in info.patterns_detected:
            info.architecture_type = "Serverless Architecture"
        elif "modular" in info.patterns_detected:
            info.architecture_type = "Modular Architecture"
        elif info.api_patterns:
            if "REST" in info.api_patterns:
                info.architecture_type = "REST API Service"
            elif "GraphQL" in info.api_patterns:
                info.architecture_type = "GraphQL Service"
            else:
                info.architecture_type = "API Service"
        elif "api" in info.key_directories:
            info.architecture_type = "API-First Architecture"
        elif any(fw in info.key_directories for fw in ["components", "views"]):
            info.architecture_type = "Component-Based Architecture"
        else:
            info.architecture_type = "Standard Application Architecture"

    def _get_sample_source_files(self, limit: int = 20) -> List[Path]:
        """Get a sample of source files for analysis."""
        extensions = [".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".php", ".cs"]
        source_files = []

        for ext in extensions:
            files = list(self.working_directory.rglob(f"*{ext}"))
            # Filter out vendor directories
            files = [
                f
                for f in files
                if not any(
                    part in [".git", "node_modules", "vendor", "__pycache__"]
                    for part in f.parts
                )
            ]
            source_files.extend(files[:3])  # Take up to 3 files per extension

        return source_files[:limit]
