"""Project Inspector Service for Technology Stack Detection.

This service analyzes a project directory to detect:
- Programming languages (Python, JavaScript, TypeScript, Rust, Go, etc.)
- Frameworks (FastAPI, Django, React, Next.js, etc.)
- Tools and databases (Docker, Kubernetes, PostgreSQL, etc.)

Used by the skills optimization command to recommend relevant skills.

Author: Claude MPM Team
Created: 2026-02-12
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TechnologyStack:
    """Detected technology stack with confidence scores."""

    languages: Dict[str, float] = field(default_factory=dict)
    frameworks: Dict[str, float] = field(default_factory=dict)
    tools: Dict[str, float] = field(default_factory=dict)
    databases: Dict[str, float] = field(default_factory=dict)

    def all_technologies(self) -> Set[str]:
        """Get all detected technologies as a flat set."""
        return (
            set(self.languages.keys())
            | set(self.frameworks.keys())
            | set(self.tools.keys())
            | set(self.databases.keys())
        )


class ProjectInspector:
    """Inspects project to detect technology stack."""

    # File patterns for language detection
    LANGUAGE_FILES = {
        "python": ["*.py", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
        "javascript": ["*.js", "*.jsx", "package.json", ".babelrc"],
        "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
        "rust": ["*.rs", "Cargo.toml"],
        "go": ["*.go", "go.mod", "go.sum"],
        "java": ["*.java", "pom.xml", "build.gradle"],
        "ruby": ["*.rb", "Gemfile", "*.gemspec"],
        "php": ["*.php", "composer.json"],
        "csharp": ["*.cs", "*.csproj"],
        "cpp": ["*.cpp", "*.hpp", "CMakeLists.txt"],
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        # Python frameworks
        "fastapi": {
            "files": ["pyproject.toml", "requirements.txt"],
            "packages": ["fastapi"],
        },
        "django": {
            "files": ["pyproject.toml", "requirements.txt"],
            "packages": ["django"],
        },
        "flask": {
            "files": ["pyproject.toml", "requirements.txt"],
            "packages": ["flask"],
        },
        "pytest": {
            "files": ["pyproject.toml", "requirements.txt"],
            "packages": ["pytest"],
        },
        "sqlalchemy": {
            "files": ["pyproject.toml", "requirements.txt"],
            "packages": ["sqlalchemy"],
        },
        # JavaScript/TypeScript frameworks
        "react": {"files": ["package.json"], "packages": ["react"]},
        "nextjs": {"files": ["package.json"], "packages": ["next"]},
        "vue": {"files": ["package.json"], "packages": ["vue"]},
        "angular": {"files": ["package.json"], "packages": ["@angular/core"]},
        "express": {"files": ["package.json"], "packages": ["express"]},
        "jest": {"files": ["package.json"], "packages": ["jest"]},
        "vitest": {"files": ["package.json"], "packages": ["vitest"]},
        # Rust frameworks
        "actix-web": {"files": ["Cargo.toml"], "packages": ["actix-web"]},
        "rocket": {"files": ["Cargo.toml"], "packages": ["rocket"]},
        # Go frameworks
        "gin": {"files": ["go.mod"], "packages": ["github.com/gin-gonic/gin"]},
        "echo": {"files": ["go.mod"], "packages": ["github.com/labstack/echo"]},
    }

    # Tool detection patterns
    TOOL_PATTERNS = {
        "docker": {
            "files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
        },
        "kubernetes": {
            "files": ["*.yaml", "k8s/*.yaml"],
            "dirs": ["k8s", "kubernetes"],
        },
        "terraform": {"files": ["*.tf", "terraform.tfvars"]},
        "ansible": {"files": ["*.yml", "playbook.yml"], "dirs": ["ansible"]},
        "makefile": {"files": ["Makefile", "makefile"]},
        "github-actions": {"dirs": [".github/workflows"]},
        "gitlab-ci": {"files": [".gitlab-ci.yml"]},
        "circleci": {"dirs": [".circleci"]},
    }

    # Database detection patterns
    DATABASE_PATTERNS = {
        "postgresql": {
            "packages": ["psycopg2", "asyncpg", "pg"],
            "env_vars": ["POSTGRES_", "DATABASE_URL=postgres"],
        },
        "mysql": {
            "packages": ["mysql", "mysqlclient", "pymysql"],
            "env_vars": ["MYSQL_"],
        },
        "mongodb": {
            "packages": ["pymongo", "motor", "mongoose"],
            "env_vars": ["MONGO_", "MONGODB_"],
        },
        "redis": {
            "packages": ["redis", "aioredis"],
            "env_vars": ["REDIS_"],
        },
        "sqlite": {
            "packages": ["sqlite3"],
            "files": ["*.db", "*.sqlite", "*.sqlite3"],
        },
    }

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize inspector with project path."""
        self.project_path = project_path or Path.cwd()
        if not self.project_path.is_absolute():
            self.project_path = self.project_path.resolve()

    def inspect(self) -> TechnologyStack:
        """Inspect project and return detected technology stack."""
        stack = TechnologyStack()

        # Detect languages
        logger.debug(f"Inspecting project at: {self.project_path}")
        stack.languages = self._detect_languages()

        # Detect frameworks (requires language context)
        stack.frameworks = self._detect_frameworks(stack.languages)

        # Detect tools
        stack.tools = self._detect_tools()

        # Detect databases
        stack.databases = self._detect_databases(stack.languages)

        logger.debug(
            f"Detected stack: {len(stack.languages)} languages, "
            f"{len(stack.frameworks)} frameworks, {len(stack.tools)} tools, "
            f"{len(stack.databases)} databases"
        )

        return stack

    def _detect_languages(self) -> Dict[str, float]:
        """Detect programming languages with confidence scores."""
        detected = {}

        for lang, patterns in self.LANGUAGE_FILES.items():
            confidence = 0.0
            indicators = []

            for pattern in patterns:
                if "*" in pattern:
                    # Glob pattern - check for file extensions
                    ext = pattern.replace("*", "")
                    matching_files = list(self.project_path.rglob(f"*{ext}"))
                    # Exclude test/vendor directories
                    matching_files = [
                        f
                        for f in matching_files
                        if not any(
                            part in f.parts
                            for part in [
                                "test",
                                "tests",
                                "__pycache__",
                                "node_modules",
                                "vendor",
                                ".git",
                            ]
                        )
                    ]
                    if matching_files:
                        confidence += 0.7
                        indicators.append(f"{len(matching_files)} {ext} files")
                # Specific file
                elif (self.project_path / pattern).exists():
                    confidence += 0.3
                    indicators.append(pattern)

            if confidence > 0:
                # Normalize confidence (max 1.0)
                confidence = min(confidence, 1.0)
                detected[lang] = confidence
                logger.debug(
                    f"Detected {lang}: {confidence:.2f} ({', '.join(indicators)})"
                )

        return detected

    def _detect_frameworks(self, languages: Dict[str, float]) -> Dict[str, float]:
        """Detect frameworks based on dependency files."""
        detected = {}

        for framework, config in self.FRAMEWORK_PATTERNS.items():
            confidence = 0.0

            # Check relevant config files exist
            config_files = config.get("files", [])
            available_configs = [
                f for f in config_files if (self.project_path / f).exists()
            ]

            if not available_configs:
                continue

            # Parse dependencies from config files
            for config_file in available_configs:
                file_path = self.project_path / config_file

                if config_file == "package.json":
                    confidence += self._check_npm_dependencies(
                        file_path, config.get("packages", [])
                    )
                elif config_file in ["pyproject.toml", "requirements.txt"]:
                    confidence += self._check_python_dependencies(
                        file_path, config.get("packages", [])
                    )
                elif config_file == "Cargo.toml":
                    confidence += self._check_rust_dependencies(
                        file_path, config.get("packages", [])
                    )
                elif config_file == "go.mod":
                    confidence += self._check_go_dependencies(
                        file_path, config.get("packages", [])
                    )

            if confidence > 0:
                confidence = min(confidence, 1.0)
                detected[framework] = confidence
                logger.debug(f"Detected {framework}: {confidence:.2f}")

        return detected

    def _check_npm_dependencies(self, package_json: Path, packages: List[str]) -> float:
        """Check if packages are in package.json dependencies."""
        try:
            with open(package_json) as f:
                data = json.load(f)

            all_deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            for pkg in packages:
                if pkg in all_deps:
                    return 0.95  # High confidence - direct dependency

            return 0.0

        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Error reading {package_json}: {e}")
            return 0.0

    def _check_python_dependencies(self, dep_file: Path, packages: List[str]) -> float:
        """Check if packages are in Python dependency files."""
        try:
            content = dep_file.read_text().lower()

            for pkg in packages:
                pkg_lower = pkg.lower()
                # Check for package name (handle extras like package[extra])
                if re.search(rf"\b{re.escape(pkg_lower)}\b", content):
                    return 0.95

            return 0.0

        except OSError as e:
            logger.debug(f"Error reading {dep_file}: {e}")
            return 0.0

    def _check_rust_dependencies(self, cargo_toml: Path, packages: List[str]) -> float:
        """Check if packages are in Cargo.toml dependencies."""
        try:
            content = cargo_toml.read_text()

            for pkg in packages:
                if re.search(rf"^{re.escape(pkg)}\s*=", content, re.MULTILINE):
                    return 0.95

            return 0.0

        except OSError as e:
            logger.debug(f"Error reading {cargo_toml}: {e}")
            return 0.0

    def _check_go_dependencies(self, go_mod: Path, packages: List[str]) -> float:
        """Check if packages are in go.mod require statements."""
        try:
            content = go_mod.read_text()

            for pkg in packages:
                if pkg in content:
                    return 0.95

            return 0.0

        except OSError as e:
            logger.debug(f"Error reading {go_mod}: {e}")
            return 0.0

    def _detect_tools(self) -> Dict[str, float]:
        """Detect development tools and infrastructure."""
        detected = {}

        for tool, config in self.TOOL_PATTERNS.items():
            confidence = 0.0

            # Check for specific files
            for file_pattern in config.get("files", []):
                if "*" in file_pattern:
                    matching = list(self.project_path.rglob(file_pattern))
                    if matching:
                        confidence += 0.8
                elif (self.project_path / file_pattern).exists():
                    confidence += 0.9

            # Check for directories
            for dir_pattern in config.get("dirs", []):
                if (self.project_path / dir_pattern).exists():
                    confidence += 0.9

            if confidence > 0:
                confidence = min(confidence, 1.0)
                detected[tool] = confidence
                logger.debug(f"Detected {tool}: {confidence:.2f}")

        return detected

    def _detect_databases(self, languages: Dict[str, float]) -> Dict[str, float]:
        """Detect database usage from dependencies and env files."""
        detected = {}

        for db, config in self.DATABASE_PATTERNS.items():
            confidence = 0.0

            # Check package dependencies
            if "python" in languages:
                for pkg in config.get("packages", []):
                    if self._check_python_package_installed(pkg):
                        confidence += 0.7

            # Check environment variables
            env_file = self.project_path / ".env"
            if env_file.exists():
                try:
                    env_content = env_file.read_text()
                    for env_pattern in config.get("env_vars", []):
                        if env_pattern in env_content:
                            confidence += 0.6
                except OSError:
                    pass

            # Check for database files
            for file_pattern in config.get("files", []):
                if "*" in file_pattern:
                    if list(self.project_path.rglob(file_pattern)):
                        confidence += 0.5

            if confidence > 0:
                confidence = min(confidence, 1.0)
                detected[db] = confidence
                logger.debug(f"Detected {db}: {confidence:.2f}")

        return detected

    def _check_python_package_installed(self, package: str) -> bool:
        """Check if Python package is in project dependencies."""
        # Check requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text().lower()
            if package.lower() in content:
                return True

        # Check pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text().lower()
            if package.lower() in content:
                return True

        return False
