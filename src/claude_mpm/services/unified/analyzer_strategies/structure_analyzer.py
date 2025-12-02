"""
Structure Analyzer Strategy Implementation
==========================================

Analyzes project structure, organization, and architectural patterns.
Consolidates structure analysis functionality from multiple services.

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import fnmatch
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logging_utils import get_logger

from ..strategies import (
    AnalyzerStrategy,
    StrategyContext,
    StrategyMetadata,
    StrategyPriority,
)

logger = get_logger(__name__)


class StructureAnalyzerStrategy(AnalyzerStrategy):
    """
    Strategy for analyzing project structure and organization.

    Consolidates:
    - Directory structure analysis
    - File organization patterns
    - Module/package detection
    - Architecture pattern recognition
    - Naming convention analysis
    """

    # Common project patterns
    PROJECT_PATTERNS: ClassVar[dict] = {
        "mvc": {
            "dirs": ["models", "views", "controllers"],
            "confidence": 0.8,
        },
        "layered": {
            "dirs": ["presentation", "business", "data", "domain"],
            "confidence": 0.7,
        },
        "hexagonal": {
            "dirs": ["domain", "application", "infrastructure", "adapters"],
            "confidence": 0.8,
        },
        "clean": {
            "dirs": ["entities", "usecases", "interfaces", "frameworks"],
            "confidence": 0.8,
        },
        "microservice": {
            "dirs": ["services", "api-gateway", "common", "shared"],
            "confidence": 0.7,
        },
    }

    # Language-specific structure patterns
    LANGUAGE_STRUCTURES: ClassVar[dict] = {
        "python": {
            "src_patterns": ["src", "lib", "app"],
            "test_patterns": ["tests", "test", "spec"],
            "config_files": ["setup.py", "setup.cfg", "pyproject.toml"],
            "module_indicator": "__init__.py",
        },
        "javascript": {
            "src_patterns": ["src", "lib", "app", "client", "server"],
            "test_patterns": ["tests", "test", "__tests__", "spec"],
            "config_files": ["package.json", "tsconfig.json", "webpack.config.js"],
            "module_indicator": "index.js",
        },
        "java": {
            "src_patterns": ["src/main/java", "src"],
            "test_patterns": ["src/test/java", "test"],
            "config_files": ["pom.xml", "build.gradle"],
            "module_indicator": None,
        },
        "go": {
            "src_patterns": ["cmd", "internal", "pkg"],
            "test_patterns": ["test"],
            "config_files": ["go.mod"],
            "module_indicator": "go.mod",
        },
    }

    # Common ignore patterns
    IGNORE_PATTERNS: ClassVar[list] = [
        "*.pyc",
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        "*.egg-info",
        ".pytest_cache",
        ".coverage",
        ".tox",
    ]

    def __init__(self):
        """Initialize structure analyzer strategy."""
        metadata = StrategyMetadata(
            name="StructureAnalyzer",
            description="Analyzes project structure and organization patterns",
            supported_types=["project", "directory", "module"],
            supported_operations=["analyze", "structure", "patterns", "metrics"],
            priority=StrategyPriority.HIGH,
            tags={"structure", "organization", "architecture", "patterns"},
        )
        super().__init__(metadata)

        self._file_cache = {}
        self._dir_cache = {}

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
            elif not path.is_dir():
                errors.append(f"Path is not a directory: {path}")
        else:
            errors.append(f"Invalid input type: {type(input_data).__name__}")

        return errors

    def analyze(
        self, target: Any, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute structure analysis on target.

        Args:
            target: Project directory to analyze
            options: Analysis options (max_depth, ignore_patterns, etc.)

        Returns:
            Analysis results with structure information
        """
        options = options or {}

        if isinstance(target, (str, Path)):
            target_path = Path(target)

            if not target_path.is_dir():
                return {
                    "status": OperationResult.ERROR,
                    "message": "Target must be a directory",
                }

            return self._analyze_structure(target_path, options)

        return {
            "status": OperationResult.ERROR,
            "message": f"Unsupported target type: {type(target).__name__}",
        }

    def _analyze_structure(
        self, root_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the structure of a project directory."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "structure",
            "path": str(root_path),
            "tree": {},
            "statistics": {},
            "patterns": {},
            "organization": {},
        }

        # Build directory tree
        max_depth = options.get("max_depth", 5)
        ignore_patterns = options.get("ignore_patterns", self.IGNORE_PATTERNS)

        tree, stats = self._build_tree(root_path, max_depth, ignore_patterns)
        results["tree"] = tree
        results["statistics"] = stats

        # Detect project patterns
        results["patterns"] = self._detect_patterns(root_path, tree)

        # Analyze organization
        results["organization"] = self._analyze_organization(root_path, tree, stats)

        # Detect architecture style
        results["architecture"] = self._detect_architecture(tree)

        # Calculate complexity metrics
        results["complexity"] = self._calculate_structure_complexity(tree, stats)

        # Detect language and framework
        results["language"] = self._detect_language(root_path)
        results["framework"] = self._detect_framework(root_path, results["language"])

        return results

    def _build_tree(
        self, root_path: Path, max_depth: int, ignore_patterns: List[str]
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Build directory tree structure."""
        tree = {
            "name": root_path.name,
            "type": "directory",
            "path": str(root_path),
            "children": [],
        }

        statistics = {
            "total_files": 0,
            "total_dirs": 0,
            "max_depth": 0,
            "file_types": {},
        }

        def should_ignore(path: Path) -> bool:
            """Check if path should be ignored."""
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path.name, pattern):
                    return True
            return False

        def walk_directory(
            current_path: Path, current_node: Dict[str, Any], depth: int
        ) -> None:
            """Recursively walk directory tree."""
            if depth > max_depth:
                return

            statistics["max_depth"] = max(statistics["max_depth"], depth)

            try:
                items = sorted(current_path.iterdir())
            except PermissionError:
                return

            for item in items:
                if should_ignore(item):
                    continue

                if item.is_dir():
                    statistics["total_dirs"] += 1
                    child_node = {
                        "name": item.name,
                        "type": "directory",
                        "path": str(item),
                        "children": [],
                    }
                    current_node["children"].append(child_node)
                    walk_directory(item, child_node, depth + 1)

                elif item.is_file():
                    statistics["total_files"] += 1

                    # Track file types
                    ext = item.suffix.lower()
                    if ext:
                        statistics["file_types"][ext] = (
                            statistics["file_types"].get(ext, 0) + 1
                        )

                    # Get file info
                    try:
                        size = item.stat().st_size
                    except (OSError, PermissionError):
                        size = 0

                    child_node = {
                        "name": item.name,
                        "type": "file",
                        "path": str(item),
                        "size": size,
                        "extension": ext,
                    }
                    current_node["children"].append(child_node)

        walk_directory(root_path, tree, 0)

        return tree, statistics

    def _detect_patterns(self, root_path: Path, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Detect common project patterns."""
        patterns = {
            "has_src": False,
            "has_tests": False,
            "has_docs": False,
            "has_ci": False,
            "has_config": False,
            "has_examples": False,
            "naming_convention": None,
        }

        # Get top-level directories
        top_level_dirs = {
            child["name"].lower()
            for child in tree.get("children", [])
            if child["type"] == "directory"
        }

        # Check for common directories
        src_dirs = {"src", "lib", "app", "source", "main"}
        test_dirs = {"tests", "test", "spec", "__tests__"}
        doc_dirs = {"docs", "doc", "documentation"}
        ci_dirs = {".github", ".gitlab", ".circleci"}
        example_dirs = {"examples", "example", "samples", "demo"}

        patterns["has_src"] = bool(src_dirs & top_level_dirs)
        patterns["has_tests"] = bool(test_dirs & top_level_dirs)
        patterns["has_docs"] = bool(doc_dirs & top_level_dirs)
        patterns["has_ci"] = bool(ci_dirs & top_level_dirs)
        patterns["has_examples"] = bool(example_dirs & top_level_dirs)

        # Check for config files
        config_files = {
            child["name"].lower()
            for child in tree.get("children", [])
            if (child["type"] == "file" and child["name"].startswith("."))
            or child["name"].endswith(".config.js")
        }
        patterns["has_config"] = len(config_files) > 0

        # Detect naming convention
        patterns["naming_convention"] = self._detect_naming_convention(tree)

        return patterns

    def _detect_naming_convention(self, tree: Dict[str, Any]) -> str:
        """Detect naming convention used in the project."""
        file_names = []

        def collect_names(node: Dict[str, Any]) -> None:
            """Collect all file and directory names."""
            if node["type"] == "file":
                name = (
                    node["name"].rsplit(".", 1)[0]
                    if "." in node["name"]
                    else node["name"]
                )
                file_names.append(name)
            elif node["type"] == "directory":
                file_names.append(node["name"])
                for child in node.get("children", []):
                    collect_names(child)

        collect_names(tree)

        if not file_names:
            return "unknown"

        # Count naming patterns
        snake_case = sum(1 for n in file_names if "_" in n and n.islower())
        kebab_case = sum(1 for n in file_names if "-" in n)
        camel_case = sum(
            1 for n in file_names if n[0].islower() and any(c.isupper() for c in n)
        )
        pascal_case = sum(
            1 for n in file_names if n[0].isupper() and any(c.islower() for c in n)
        )

        # Determine dominant pattern
        patterns = {
            "snake_case": snake_case,
            "kebab-case": kebab_case,
            "camelCase": camel_case,
            "PascalCase": pascal_case,
        }

        if max(patterns.values()) == 0:
            return "mixed"

        return max(patterns, key=patterns.get)

    def _analyze_organization(
        self, root_path: Path, tree: Dict[str, Any], stats: Dict[str, int]
    ) -> Dict[str, Any]:
        """Analyze project organization quality."""
        organization = {
            "structure_score": 0,
            "file_organization": {},
            "depth_analysis": {},
            "recommendations": [],
        }

        # Calculate structure score (0-100)
        score = 100

        # Check for proper separation
        patterns = self._detect_patterns(root_path, tree)
        if not patterns["has_src"]:
            score -= 10
            organization["recommendations"].append(
                "Consider organizing source code in a dedicated directory (src, lib, or app)"
            )

        if not patterns["has_tests"]:
            score -= 15
            organization["recommendations"].append(
                "Add a dedicated test directory for better organization"
            )

        # Check depth balance
        max_depth = stats.get("max_depth", 0)
        if max_depth > 7:
            score -= 10
            organization["recommendations"].append(
                f"Directory structure is too deep ({max_depth} levels). Consider flattening"
            )
        elif max_depth < 2:
            score -= 5
            organization["recommendations"].append(
                "Directory structure is too flat. Consider better organization"
            )

        # Check file distribution
        avg_files_per_dir = stats["total_files"] / max(stats["total_dirs"], 1)
        if avg_files_per_dir > 20:
            score -= 10
            organization["recommendations"].append(
                "Too many files per directory. Consider better organization"
            )

        organization["structure_score"] = max(0, score)

        # Analyze file organization by type
        file_types = stats.get("file_types", {})
        total_files = stats.get("total_files", 0)

        if total_files > 0:
            organization["file_organization"] = {
                ext: {"count": count, "percentage": (count / total_files) * 100}
                for ext, count in sorted(
                    file_types.items(), key=lambda x: x[1], reverse=True
                )[:10]
            }

        # Depth analysis
        organization["depth_analysis"] = {
            "max_depth": max_depth,
            "average_files_per_directory": avg_files_per_dir,
            "total_directories": stats["total_dirs"],
            "total_files": stats["total_files"],
        }

        return organization

    def _detect_architecture(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Detect architectural patterns in the project structure."""
        architecture = {
            "pattern": "unknown",
            "confidence": 0.0,
            "detected_patterns": [],
        }

        # Get all directory names at various levels
        dir_names = set()

        def collect_dir_names(node: Dict[str, Any], depth: int = 0) -> None:
            """Collect directory names up to depth 3."""
            if depth > 3 or node["type"] != "directory":
                return

            dir_names.add(node["name"].lower())
            for child in node.get("children", []):
                collect_dir_names(child, depth + 1)

        collect_dir_names(tree)

        # Check for architectural patterns
        for pattern_name, pattern_info in self.PROJECT_PATTERNS.items():
            required_dirs = set(pattern_info["dirs"])
            found_dirs = required_dirs & dir_names

            if len(found_dirs) >= len(required_dirs) * pattern_info["confidence"]:
                architecture["detected_patterns"].append(
                    {
                        "name": pattern_name,
                        "confidence": len(found_dirs) / len(required_dirs),
                        "matched_dirs": list(found_dirs),
                    }
                )

        # Select the pattern with highest confidence
        if architecture["detected_patterns"]:
            best_pattern = max(
                architecture["detected_patterns"], key=lambda x: x["confidence"]
            )
            architecture["pattern"] = best_pattern["name"]
            architecture["confidence"] = best_pattern["confidence"]

        return architecture

    def _calculate_structure_complexity(
        self, tree: Dict[str, Any], stats: Dict[str, int]
    ) -> Dict[str, Any]:
        """Calculate structural complexity metrics."""
        complexity = {
            "structural_complexity": 0,
            "nesting_complexity": 0,
            "file_dispersion": 0,
            "coupling_indicator": 0,
        }

        # Structural complexity based on file and directory count
        total_nodes = stats["total_files"] + stats["total_dirs"]
        complexity["structural_complexity"] = (total_nodes / 100) * (
            stats["max_depth"] / 3
        )

        # Nesting complexity
        complexity["nesting_complexity"] = min(100, (stats["max_depth"] / 7) * 100)

        # File dispersion (how spread out files are)
        if stats["total_dirs"] > 0:
            avg_files = stats["total_files"] / stats["total_dirs"]
            # Ideal is around 5-10 files per directory
            if avg_files < 5:
                complexity["file_dispersion"] = (5 - avg_files) * 10
            elif avg_files > 10:
                complexity["file_dispersion"] = (avg_files - 10) * 5
            else:
                complexity["file_dispersion"] = 0

        # Coupling indicator (based on common cross-cutting directories)
        cross_cutting_dirs = {"common", "shared", "utils", "helpers", "core"}
        dir_names = set()

        def collect_dir_names(node: Dict[str, Any]) -> None:
            if node["type"] == "directory":
                dir_names.add(node["name"].lower())
                for child in node.get("children", []):
                    collect_dir_names(child)

        collect_dir_names(tree)
        coupling_count = len(cross_cutting_dirs & dir_names)
        complexity["coupling_indicator"] = min(100, coupling_count * 20)

        return complexity

    def _detect_language(self, root_path: Path) -> str:
        """Detect primary programming language."""
        # Check for language-specific config files
        for language, structure in self.LANGUAGE_STRUCTURES.items():
            for config_file in structure["config_files"]:
                if (root_path / config_file).exists():
                    return language

        # Check for common file extensions
        language_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".hpp", ".cc"],
            "csharp": [".cs"],
            "ruby": [".rb"],
            "php": [".php"],
        }

        file_counts = {}
        for language, extensions in language_extensions.items():
            count = sum(len(list(root_path.rglob(f"*{ext}"))) for ext in extensions)
            if count > 0:
                file_counts[language] = count

        if file_counts:
            return max(file_counts, key=file_counts.get)

        return "unknown"

    def _detect_framework(self, root_path: Path, language: str) -> Optional[str]:
        """Detect framework based on language and files."""
        framework_indicators = {
            "python": {
                "django": ["manage.py", "settings.py"],
                "flask": ["app.py", "flask"],
                "fastapi": ["main.py", "fastapi"],
            },
            "javascript": {
                "react": ["package.json", "react"],
                "angular": ["angular.json"],
                "vue": ["vue.config.js"],
                "express": ["app.js", "express"],
                "next": ["next.config.js"],
            },
            "java": {
                "spring": ["pom.xml", "spring"],
                "springboot": ["application.properties", "application.yml"],
            },
        }

        if language in framework_indicators:
            for framework, indicators in framework_indicators[language].items():
                for indicator in indicators:
                    if (root_path / indicator).exists():
                        return framework

                    # Check in package files
                    if language == "javascript" and indicator != "package.json":
                        package_json = root_path / "package.json"
                        if package_json.exists():
                            content = package_json.read_text()
                            if indicator in content:
                                return framework

        return None

    def extract_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from analysis results."""
        metrics = {}

        if analysis_result.get("status") != OperationResult.SUCCESS:
            return metrics

        # Extract structure statistics
        if "statistics" in analysis_result:
            stats = analysis_result["statistics"]
            metrics.update(
                {
                    "total_files": stats.get("total_files", 0),
                    "total_directories": stats.get("total_dirs", 0),
                    "max_depth": stats.get("max_depth", 0),
                    "unique_file_types": len(stats.get("file_types", {})),
                }
            )

        # Extract organization metrics
        if "organization" in analysis_result:
            org = analysis_result["organization"]
            metrics["structure_score"] = org.get("structure_score", 0)

        # Extract complexity metrics
        if "complexity" in analysis_result:
            complexity = analysis_result["complexity"]
            metrics.update(
                {
                    "structural_complexity": complexity.get("structural_complexity", 0),
                    "nesting_complexity": complexity.get("nesting_complexity", 0),
                    "file_dispersion": complexity.get("file_dispersion", 0),
                    "coupling_indicator": complexity.get("coupling_indicator", 0),
                }
            )

        return metrics

    def compare_results(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two structure analysis results."""
        comparison = {
            "structure_changes": {},
            "metric_changes": {},
            "pattern_changes": {},
        }

        # Compare metrics
        baseline_metrics = self.extract_metrics(baseline)
        current_metrics = self.extract_metrics(current)

        for key in baseline_metrics:
            if key in current_metrics:
                diff = current_metrics[key] - baseline_metrics[key]
                comparison["metric_changes"][key] = {
                    "baseline": baseline_metrics[key],
                    "current": current_metrics[key],
                    "change": diff,
                    "percent_change": (
                        (diff / baseline_metrics[key] * 100)
                        if baseline_metrics[key]
                        else 0
                    ),
                }

        # Compare patterns
        if "patterns" in baseline and "patterns" in current:
            baseline_patterns = baseline["patterns"]
            current_patterns = current["patterns"]

            for key in baseline_patterns:
                if key in current_patterns:
                    if baseline_patterns[key] != current_patterns[key]:
                        comparison["pattern_changes"][key] = {
                            "baseline": baseline_patterns[key],
                            "current": current_patterns[key],
                        }

        # Compare architecture
        if (
            "architecture" in baseline
            and "architecture" in current
            and (
                baseline["architecture"]["pattern"]
                != current["architecture"]["pattern"]
            )
        ):
            comparison["architecture_change"] = {
                "baseline": baseline["architecture"]["pattern"],
                "current": current["architecture"]["pattern"],
            }

        return comparison
