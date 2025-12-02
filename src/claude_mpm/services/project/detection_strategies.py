"""
Toolchain Detection Strategies for Claude MPM Framework
=======================================================

WHY: This module implements pluggable detection strategies for different
programming languages and frameworks. Using the Strategy pattern allows
easy addition of new language detectors without modifying existing code.

DESIGN DECISION: Each strategy is independent and responsible for detecting
a specific language/ecosystem. Strategies calculate confidence scores based
on multiple indicators, providing transparency in detection results.

Part of TSK-0054: Auto-Configuration Feature - Phase 2
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.models.toolchain import (
    ConfidenceLevel,
    Framework,
    LanguageDetection,
    ToolchainComponent,
)


@dataclass
class DetectionEvidence:
    """Evidence gathered during detection process.

    WHY: Transparency in detection helps users understand why certain
    technologies were detected and builds trust in recommendations.
    """

    indicators_found: List[str] = field(default_factory=list)
    confidence_contributors: Dict[str, float] = field(default_factory=dict)
    version_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_indicator(self, indicator: str, confidence_boost: float = 0.15) -> None:
        """Add an indicator and its confidence contribution."""
        self.indicators_found.append(indicator)
        self.confidence_contributors[indicator] = confidence_boost

    def total_confidence(self) -> float:
        """Calculate total confidence score."""
        base = 0.5
        total = base + sum(self.confidence_contributors.values())
        return min(total, 0.95)  # Cap at 0.95


class IToolchainDetectionStrategy(ABC):
    """Base interface for toolchain detection strategies.

    WHY: Defines contract for all detection strategies, ensuring consistency
    and enabling polymorphic usage in the analyzer service.
    """

    @abstractmethod
    def can_detect(self, project_path: Path) -> bool:
        """Check if this strategy can detect anything in the project.

        Args:
            project_path: Path to project root

        Returns:
            True if strategy found relevant indicators
        """

    @abstractmethod
    def detect_language(self, project_path: Path) -> Optional[LanguageDetection]:
        """Detect language with confidence and evidence.

        Args:
            project_path: Path to project root

        Returns:
            LanguageDetection if detected, None otherwise
        """

    @abstractmethod
    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect frameworks used in the project.

        Args:
            project_path: Path to project root

        Returns:
            List of detected frameworks
        """

    @abstractmethod
    def get_language_name(self) -> str:
        """Get the language this strategy detects."""


class BaseDetectionStrategy(IToolchainDetectionStrategy):
    """Base implementation with common detection utilities.

    WHY: Provides shared utilities for file checking, version extraction,
    and confidence calculation to reduce code duplication.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _file_exists(self, project_path: Path, *relative_paths: str) -> bool:
        """Check if file exists in project."""
        return any((project_path / rel_path).exists() for rel_path in relative_paths)

    def _read_file(self, file_path: Path) -> Optional[str]:
        """Safely read file contents."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            self.logger.debug(f"Could not read {file_path}: {e}")
            return None

    def _extract_version_from_file(
        self, file_path: Path, patterns: List[str]
    ) -> Optional[str]:
        """Extract version using regex patterns."""
        content = self._read_file(file_path)
        if not content:
            return None

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return None

    def _calculate_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 0.80:
            return ConfidenceLevel.HIGH
        if score >= 0.50:
            return ConfidenceLevel.MEDIUM
        if score >= 0.20:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _count_source_files(
        self, project_path: Path, extensions: Set[str], max_depth: int = 5
    ) -> int:
        """Count source files with given extensions."""
        count = 0
        try:
            for ext in extensions:
                # Limit search depth to avoid performance issues
                pattern = f"**/*{ext}"
                files = list(project_path.glob(pattern))
                # Filter out common excluded directories
                files = [
                    f
                    for f in files
                    if not any(
                        part.startswith(".")
                        or part in {"node_modules", "venv", "target", "build", "dist"}
                        for part in f.parts
                    )
                ]
                count += len(files[:1000])  # Cap at 1000 per extension
        except Exception as e:
            self.logger.debug(f"Error counting files: {e}")
        return count


class NodeJSDetectionStrategy(BaseDetectionStrategy):
    """Detection strategy for Node.js projects.

    WHY: Node.js projects have distinct markers (package.json, node_modules)
    and well-defined dependency management that enables high-confidence detection.
    """

    MARKER_FILES = ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"]
    VERSION_PATTERNS = [
        r'"node":\s*"([^"]+)"',  # engines.node in package.json
        r'"version":\s*"([^"]+)"',  # package version
    ]

    FRAMEWORK_INDICATORS = {
        "next": {
            "type": "web",
            "patterns": ["next"],
            "config_files": ["next.config.js", "next.config.ts"],
        },
        "react": {"type": "web", "patterns": ["react", "react-dom"]},
        "vue": {"type": "web", "patterns": ["vue"]},
        "angular": {"type": "web", "patterns": ["@angular/core"]},
        "express": {"type": "web", "patterns": ["express"]},
        "nestjs": {"type": "web", "patterns": ["@nestjs/core"]},
        "nuxt": {"type": "web", "patterns": ["nuxt"]},
    }

    def get_language_name(self) -> str:
        return "Node.js"

    def can_detect(self, project_path: Path) -> bool:
        """Check for Node.js indicators."""
        return self._file_exists(project_path, *self.MARKER_FILES)

    def detect_language(self, project_path: Path) -> Optional[LanguageDetection]:
        """Detect Node.js with confidence scoring."""
        if not self.can_detect(project_path):
            return None

        evidence = DetectionEvidence()

        # Check for package.json (strongest indicator)
        package_json_path = project_path / "package.json"
        if package_json_path.exists():
            evidence.add_indicator("package.json found", 0.20)

            # Extract version information
            version = self._extract_version_from_file(
                package_json_path, self.VERSION_PATTERNS
            )
            if version:
                evidence.version_sources.append("package.json engines.node")

        # Check for lock files
        if (project_path / "package-lock.json").exists():
            evidence.add_indicator("package-lock.json found", 0.10)
        if (project_path / "yarn.lock").exists():
            evidence.add_indicator("yarn.lock found", 0.10)
        if (project_path / "pnpm-lock.yaml").exists():
            evidence.add_indicator("pnpm-lock.yaml found", 0.10)

        # Check for node_modules
        if (project_path / "node_modules").exists():
            evidence.add_indicator("node_modules directory found", 0.05)

        # Count JavaScript/TypeScript files
        js_count = self._count_source_files(
            project_path, {".js", ".jsx", ".ts", ".tsx"}
        )
        if js_count > 0:
            evidence.add_indicator(f"{js_count} JavaScript/TypeScript files", 0.10)

        # Determine confidence
        confidence_score = evidence.total_confidence()
        confidence = self._calculate_confidence_level(confidence_score)

        # Detect secondary languages (TypeScript)
        secondary_languages = []
        ts_count = self._count_source_files(project_path, {".ts", ".tsx"})
        if ts_count > 0:
            ts_percentage = (ts_count / max(js_count, 1)) * 100
            if ts_percentage > 10:  # More than 10% TypeScript
                secondary_languages.append(
                    ToolchainComponent(
                        name="TypeScript",
                        confidence=(
                            ConfidenceLevel.HIGH
                            if ts_percentage > 50
                            else ConfidenceLevel.MEDIUM
                        ),
                    )
                )

        # Calculate language percentages
        total_files = js_count
        language_percentages = {"JavaScript": 100.0}
        if secondary_languages:
            js_only = js_count - ts_count
            language_percentages = {
                "JavaScript": (js_only / total_files * 100) if total_files > 0 else 0,
                "TypeScript": (ts_count / total_files * 100) if total_files > 0 else 0,
            }

        return LanguageDetection(
            primary_language="Node.js",
            primary_version=version,
            primary_confidence=confidence,
            secondary_languages=secondary_languages,
            language_percentages=language_percentages,
        )

    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect Node.js frameworks from package.json."""
        frameworks = []

        package_json_path = project_path / "package.json"
        if not package_json_path.exists():
            return frameworks

        try:
            content = self._read_file(package_json_path)
            if not content:
                return frameworks

            package_data = json.loads(content)
            all_deps = {}
            all_deps.update(package_data.get("dependencies", {}))
            all_deps.update(package_data.get("devDependencies", {}))

            # Check for known frameworks
            for fw_name, fw_info in self.FRAMEWORK_INDICATORS.items():
                # Check dependency names
                for dep_name, dep_version in all_deps.items():
                    if any(pattern in dep_name for pattern in fw_info["patterns"]):
                        # Check if framework-specific config exists (for higher confidence)
                        config_files = fw_info.get("config_files", [])
                        has_config = (
                            any(
                                (project_path / config_file).exists()
                                for config_file in config_files
                            )
                            if config_files
                            else False
                        )

                        confidence = (
                            ConfidenceLevel.HIGH
                            if has_config
                            else ConfidenceLevel.MEDIUM
                        )

                        frameworks.append(
                            Framework(
                                name=fw_name,
                                version=(
                                    dep_version.strip("^~>=<")
                                    if isinstance(dep_version, str)
                                    else None
                                ),
                                framework_type=fw_info["type"],
                                confidence=confidence,
                                is_dev_dependency=dep_name
                                in package_data.get("devDependencies", {}),
                            )
                        )
                        break  # Found this framework, move to next

        except Exception as e:
            self.logger.warning(f"Error parsing package.json: {e}")

        return frameworks


class PythonDetectionStrategy(BaseDetectionStrategy):
    """Detection strategy for Python projects.

    WHY: Python has multiple dependency management approaches (pip, poetry, pipenv)
    requiring flexible detection logic.
    """

    MARKER_FILES = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]
    VERSION_PATTERNS = [
        r'python_requires\s*=\s*["\']([^"\']+)["\']',  # setup.py
        r'python\s*=\s*["\']([^"\']+)["\']',  # pyproject.toml
    ]

    FRAMEWORK_INDICATORS = {
        "Django": {"type": "web", "patterns": ["django", "Django"]},
        "Flask": {"type": "web", "patterns": ["flask", "Flask"]},
        "FastAPI": {"type": "web", "patterns": ["fastapi", "FastAPI"]},
        "Tornado": {"type": "web", "patterns": ["tornado"]},
        "pytest": {"type": "testing", "patterns": ["pytest"]},
        "SQLAlchemy": {"type": "orm", "patterns": ["sqlalchemy", "SQLAlchemy"]},
    }

    def get_language_name(self) -> str:
        return "Python"

    def can_detect(self, project_path: Path) -> bool:
        """Check for Python indicators."""
        return self._file_exists(project_path, *self.MARKER_FILES)

    def detect_language(self, project_path: Path) -> Optional[LanguageDetection]:
        """Detect Python with confidence scoring."""
        if not self.can_detect(project_path):
            return None

        evidence = DetectionEvidence()
        version = None

        # Check for requirements.txt
        if (project_path / "requirements.txt").exists():
            evidence.add_indicator("requirements.txt found", 0.15)

        # Check for pyproject.toml (modern Python)
        pyproject_path = project_path / "pyproject.toml"
        if pyproject_path.exists():
            evidence.add_indicator("pyproject.toml found", 0.20)
            version = self._extract_version_from_file(
                pyproject_path, self.VERSION_PATTERNS
            )
            if version:
                evidence.version_sources.append("pyproject.toml")

        # Check for setup.py
        setup_path = project_path / "setup.py"
        if setup_path.exists():
            evidence.add_indicator("setup.py found", 0.15)
            if not version:
                version = self._extract_version_from_file(
                    setup_path, self.VERSION_PATTERNS
                )
                if version:
                    evidence.version_sources.append("setup.py")

        # Check for Pipfile
        if (project_path / "Pipfile").exists():
            evidence.add_indicator("Pipfile found", 0.10)

        # Check for virtual environment
        if self._file_exists(project_path, "venv", ".venv", "env"):
            evidence.add_indicator("Virtual environment found", 0.05)

        # Count Python files
        py_count = self._count_source_files(project_path, {".py"})
        if py_count > 0:
            evidence.add_indicator(f"{py_count} Python files", 0.10)

        # Determine confidence
        confidence_score = evidence.total_confidence()
        confidence = self._calculate_confidence_level(confidence_score)

        return LanguageDetection(
            primary_language="Python",
            primary_version=version,
            primary_confidence=confidence,
            secondary_languages=[],
            language_percentages={"Python": 100.0},
        )

    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect Python frameworks from dependency files."""
        frameworks = []
        dependencies = self._extract_dependencies(project_path)

        for fw_name, fw_info in self.FRAMEWORK_INDICATORS.items():
            for dep_name, dep_version in dependencies.items():
                if any(
                    pattern.lower() in dep_name.lower()
                    for pattern in fw_info["patterns"]
                ):
                    frameworks.append(
                        Framework(
                            name=fw_name,
                            version=dep_version,
                            framework_type=fw_info["type"],
                            confidence=ConfidenceLevel.HIGH,
                            is_dev_dependency=False,  # Hard to determine from requirements.txt
                        )
                    )
                    break

        return frameworks

    def _extract_dependencies(self, project_path: Path) -> Dict[str, Optional[str]]:
        """Extract dependencies from various Python dependency files."""
        dependencies = {}

        # Parse requirements.txt
        req_path = project_path / "requirements.txt"
        if req_path.exists():
            content = self._read_file(req_path)
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse package==version or package>=version
                        match = re.match(
                            r"([a-zA-Z0-9_-]+)\s*([>=<~!]+)\s*([0-9.]+)", line
                        )
                        if match:
                            dependencies[match.group(1)] = match.group(3)
                        else:
                            # Just package name
                            pkg_name = re.match(r"([a-zA-Z0-9_-]+)", line)
                            if pkg_name:
                                dependencies[pkg_name.group(1)] = None

        # Parse pyproject.toml (basic parsing without tomllib for now)
        pyproject_path = project_path / "pyproject.toml"
        if pyproject_path.exists():
            content = self._read_file(pyproject_path)
            if content:
                # Simple regex-based parsing
                dep_matches = re.findall(
                    r'([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', content
                )
                for dep_name, dep_version in dep_matches:
                    if dep_name not in dependencies:
                        dependencies[dep_name] = dep_version.strip("^~>=<")

        return dependencies


class RustDetectionStrategy(BaseDetectionStrategy):
    """Detection strategy for Rust projects.

    WHY: Rust has a standardized toolchain (Cargo) making detection reliable.
    """

    MARKER_FILES = ["Cargo.toml", "Cargo.lock"]
    VERSION_PATTERNS = [
        r'rust-version\s*=\s*"([^"]+)"',  # Cargo.toml
        r'edition\s*=\s*"([^"]+)"',  # Rust edition
    ]

    FRAMEWORK_INDICATORS = {
        "actix-web": {"type": "web", "patterns": ["actix-web"]},
        "rocket": {"type": "web", "patterns": ["rocket"]},
        "warp": {"type": "web", "patterns": ["warp"]},
        "tokio": {"type": "async", "patterns": ["tokio"]},
        "async-std": {"type": "async", "patterns": ["async-std"]},
    }

    def get_language_name(self) -> str:
        return "Rust"

    def can_detect(self, project_path: Path) -> bool:
        """Check for Rust indicators."""
        return self._file_exists(project_path, *self.MARKER_FILES)

    def detect_language(self, project_path: Path) -> Optional[LanguageDetection]:
        """Detect Rust with confidence scoring."""
        if not self.can_detect(project_path):
            return None

        evidence = DetectionEvidence()
        version = None

        # Check for Cargo.toml (strongest indicator)
        cargo_path = project_path / "Cargo.toml"
        if cargo_path.exists():
            evidence.add_indicator("Cargo.toml found", 0.25)
            version = self._extract_version_from_file(cargo_path, self.VERSION_PATTERNS)
            if version:
                evidence.version_sources.append("Cargo.toml")

        # Check for Cargo.lock
        if (project_path / "Cargo.lock").exists():
            evidence.add_indicator("Cargo.lock found", 0.10)

        # Check for src/ directory with main.rs or lib.rs
        if (project_path / "src" / "main.rs").exists():
            evidence.add_indicator("src/main.rs found", 0.10)
        if (project_path / "src" / "lib.rs").exists():
            evidence.add_indicator("src/lib.rs found", 0.10)

        # Count Rust files
        rs_count = self._count_source_files(project_path, {".rs"})
        if rs_count > 0:
            evidence.add_indicator(f"{rs_count} Rust files", 0.10)

        # Determine confidence
        confidence_score = evidence.total_confidence()
        confidence = self._calculate_confidence_level(confidence_score)

        return LanguageDetection(
            primary_language="Rust",
            primary_version=version,
            primary_confidence=confidence,
            secondary_languages=[],
            language_percentages={"Rust": 100.0},
        )

    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect Rust frameworks from Cargo.toml."""
        frameworks = []

        cargo_path = project_path / "Cargo.toml"
        if not cargo_path.exists():
            return frameworks

        content = self._read_file(cargo_path)
        if not content:
            return frameworks

        # Parse dependencies section (simple approach)
        in_dependencies = False
        for line in content.splitlines():
            line = line.strip()

            if line.startswith("[dependencies]"):
                in_dependencies = True
                continue
            if line.startswith("["):
                in_dependencies = False
                continue

            if in_dependencies and "=" in line:
                dep_match = re.match(r"([a-zA-Z0-9_-]+)\s*=", line)
                if dep_match:
                    dep_name = dep_match.group(1)

                    # Check against known frameworks
                    for fw_name, fw_info in self.FRAMEWORK_INDICATORS.items():
                        if any(pattern in dep_name for pattern in fw_info["patterns"]):
                            # Extract version if present
                            version_match = re.search(r'"([0-9.]+)"', line)
                            version = version_match.group(1) if version_match else None

                            frameworks.append(
                                Framework(
                                    name=fw_name,
                                    version=version,
                                    framework_type=fw_info["type"],
                                    confidence=ConfidenceLevel.HIGH,
                                    is_dev_dependency=False,
                                )
                            )
                            break

        return frameworks


class GoDetectionStrategy(BaseDetectionStrategy):
    """Detection strategy for Go projects.

    WHY: Go has standardized module system (go.mod) since Go 1.11.
    """

    MARKER_FILES = ["go.mod", "go.sum"]
    VERSION_PATTERNS = [
        r"go\s+([0-9.]+)",  # go.mod
    ]

    FRAMEWORK_INDICATORS = {
        "gin": {"type": "web", "patterns": ["gin-gonic/gin"]},
        "echo": {"type": "web", "patterns": ["labstack/echo"]},
        "fiber": {"type": "web", "patterns": ["gofiber/fiber"]},
        "beego": {"type": "web", "patterns": ["beego/beego"]},
    }

    def get_language_name(self) -> str:
        return "Go"

    def can_detect(self, project_path: Path) -> bool:
        """Check for Go indicators."""
        return self._file_exists(project_path, *self.MARKER_FILES)

    def detect_language(self, project_path: Path) -> Optional[LanguageDetection]:
        """Detect Go with confidence scoring."""
        if not self.can_detect(project_path):
            return None

        evidence = DetectionEvidence()
        version = None

        # Check for go.mod
        gomod_path = project_path / "go.mod"
        if gomod_path.exists():
            evidence.add_indicator("go.mod found", 0.25)
            version = self._extract_version_from_file(gomod_path, self.VERSION_PATTERNS)
            if version:
                evidence.version_sources.append("go.mod")

        # Check for go.sum
        if (project_path / "go.sum").exists():
            evidence.add_indicator("go.sum found", 0.10)

        # Count Go files
        go_count = self._count_source_files(project_path, {".go"})
        if go_count > 0:
            evidence.add_indicator(f"{go_count} Go files", 0.10)

        # Check for main.go
        if (project_path / "main.go").exists():
            evidence.add_indicator("main.go found", 0.05)

        # Determine confidence
        confidence_score = evidence.total_confidence()
        confidence = self._calculate_confidence_level(confidence_score)

        return LanguageDetection(
            primary_language="Go",
            primary_version=version,
            primary_confidence=confidence,
            secondary_languages=[],
            language_percentages={"Go": 100.0},
        )

    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect Go frameworks from go.mod."""
        frameworks = []

        gomod_path = project_path / "go.mod"
        if not gomod_path.exists():
            return frameworks

        content = self._read_file(gomod_path)
        if not content:
            return frameworks

        # Parse require section
        for line in content.splitlines():
            line = line.strip()

            # Match require lines
            if "require" in line or line.startswith("github.com"):
                for fw_name, fw_info in self.FRAMEWORK_INDICATORS.items():
                    if any(pattern in line for pattern in fw_info["patterns"]):
                        # Extract version
                        version_match = re.search(r"v([0-9.]+)", line)
                        version = version_match.group(1) if version_match else None

                        frameworks.append(
                            Framework(
                                name=fw_name,
                                version=version,
                                framework_type=fw_info["type"],
                                confidence=ConfidenceLevel.HIGH,
                                is_dev_dependency=False,
                            )
                        )
                        break

        return frameworks
