#!/usr/bin/env python3
"""
Metrics Collector Service
=========================

WHY: Separates code metrics collection from the main analyzer to follow
single responsibility principle. Collects quantitative metrics about
the codebase for analysis and reporting.

DECISION: Create a focused service for metrics that can provide insights
about code complexity, size, and quality indicators.
"""

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class ProjectMetrics:
    """Container for project metrics."""

    # Size metrics
    total_files: int = 0
    total_lines: int = 0
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0

    # File type distribution
    file_types: Dict[str, int] = None
    largest_files: List[Tuple[str, int]] = None

    # Directory metrics
    total_directories: int = 0
    max_depth: int = 0
    average_files_per_directory: float = 0.0

    # Code complexity indicators
    average_file_size: float = 0.0
    files_over_500_lines: int = 0
    files_over_1000_lines: int = 0

    # Testing metrics
    test_files: int = 0
    test_coverage_files: int = 0
    test_to_code_ratio: float = 0.0

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.file_types is None:
            self.file_types = {}
        if self.largest_files is None:
            self.largest_files = []

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollectorService:
    """Collects quantitative metrics about a project.

    WHY: Metrics provide objective insights about code health, complexity,
    and structure that help agents understand the project scale and quality.
    """

    # File extensions to analyze
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".r",
        ".lua",
    }

    # Test file patterns
    TEST_PATTERNS = [
        "test_",
        "_test.",
        ".test.",
        ".spec.",
        "_spec.",
        "tests/",
        "test/",
        "__tests__/",
        "spec/",
    ]

    # Directories to exclude from analysis
    EXCLUDE_DIRS = {
        ".git",
        "node_modules",
        "vendor",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        "target",
        ".venv",
        "venv",
        "env",
        ".tox",
        "coverage",
        ".coverage",
        "htmlcov",
        ".mypy_cache",
    }

    def __init__(self, working_directory: Path):
        """Initialize the metrics collector service.

        Args:
            working_directory: Project root directory
        """
        self.working_directory = working_directory
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def collect_metrics(self) -> ProjectMetrics:
        """Collect comprehensive project metrics.

        WHY: Comprehensive metrics help understand project scale,
        complexity, and quality indicators.

        Returns:
            ProjectMetrics object with collected data
        """
        metrics = ProjectMetrics()

        # Collect file and directory metrics
        self._collect_file_metrics(metrics)

        # Calculate derived metrics
        self._calculate_derived_metrics(metrics)

        # Collect test metrics
        self._collect_test_metrics(metrics)

        return metrics

    def analyze_file_sizes(self) -> Dict[str, List[Tuple[str, int]]]:
        """Analyze file sizes and identify outliers.

        WHY: Large files often indicate code that needs refactoring
        and can be harder to maintain.

        Returns:
            Dictionary with file size analysis
        """
        file_sizes = []

        for file_path in self._iter_code_files():
            try:
                file_path.stat().st_size
                lines = len(
                    file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                )
                file_sizes.append(
                    (str(file_path.relative_to(self.working_directory)), lines)
                )
            except Exception as e:
                self.logger.debug(f"Error analyzing {file_path}: {e}")

        # Sort by size
        file_sizes.sort(key=lambda x: x[1], reverse=True)

        return {
            "largest_files": file_sizes[:10],
            "files_over_500_lines": [f for f in file_sizes if f[1] > 500],
            "files_over_1000_lines": [f for f in file_sizes if f[1] > 1000],
        }

    def analyze_directory_structure(self) -> Dict[str, any]:
        """Analyze project directory structure.

        WHY: Directory structure reveals architectural decisions
        and organizational patterns.

        Returns:
            Dictionary with directory structure analysis
        """
        dir_info = {
            "total_directories": 0,
            "max_depth": 0,
            "directories_by_depth": {},
            "files_per_directory": {},
        }

        for dirpath, dirnames, filenames in self.working_directory.walk():
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDE_DIRS]

            # Calculate depth
            depth = len(Path(dirpath).relative_to(self.working_directory).parts)
            dir_info["max_depth"] = max(dir_info["max_depth"], depth)

            # Count directories
            dir_info["total_directories"] += 1

            # Track directories by depth
            if depth not in dir_info["directories_by_depth"]:
                dir_info["directories_by_depth"][depth] = 0
            dir_info["directories_by_depth"][depth] += 1

            # Track files per directory
            rel_path = str(Path(dirpath).relative_to(self.working_directory))
            dir_info["files_per_directory"][rel_path] = len(filenames)

        return dir_info

    def calculate_code_to_comment_ratio(self) -> Dict[str, float]:
        """Calculate code to comment ratio for different file types.

        WHY: Comment ratio indicates documentation quality and
        code self-documentation level.

        Returns:
            Dictionary with ratios by file type
        """
        ratios = {}

        # Language-specific comment patterns
        comment_patterns = {
            ".py": (r"#", r'"""', r"'''"),
            ".js": (r"//", r"/*", r"*/"),
            ".java": (r"//", r"/*", r"*/"),
            ".cpp": (r"//", r"/*", r"*/"),
            ".c": (r"//", r"/*", r"*/"),
            ".go": (r"//", r"/*", r"*/"),
            ".rs": (r"//", r"/*", r"*/"),
            ".rb": (r"#", r"=begin", r"=end"),
        }

        for ext, patterns in comment_patterns.items():
            files = list(self.working_directory.rglob(f"*{ext}"))
            files = [f for f in files if self._should_analyze_file(f)]

            if not files:
                continue

            total_lines = 0
            comment_lines = 0

            for file_path in files[:20]:  # Sample files
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    total_lines += len(lines)

                    for line in lines:
                        stripped = line.strip()
                        if any(
                            stripped.startswith(p)
                            for p in patterns
                            if isinstance(p, str)
                        ):
                            comment_lines += 1

                except Exception as e:
                    self.logger.debug(f"Error analyzing {file_path}: {e}")

            if total_lines > 0:
                ratios[ext] = comment_lines / total_lines

        return ratios

    def _collect_file_metrics(self, metrics: ProjectMetrics) -> None:
        """Collect basic file metrics."""
        file_counter = Counter()
        total_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        file_sizes = []

        for file_path in self._iter_code_files():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                metrics.total_files += 1
                file_ext = file_path.suffix
                file_counter[file_ext] += 1

                file_line_count = len(lines)
                total_lines += file_line_count
                file_sizes.append(
                    (
                        str(file_path.relative_to(self.working_directory)),
                        file_line_count,
                    )
                )

                # Count line types
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        blank_lines += 1
                    elif stripped.startswith(("#", "//", "/*", "*")):
                        comment_lines += 1
                    else:
                        code_lines += 1

                # Track large files
                if file_line_count > 500:
                    metrics.files_over_500_lines += 1
                if file_line_count > 1000:
                    metrics.files_over_1000_lines += 1

            except Exception as e:
                self.logger.debug(f"Error collecting metrics for {file_path}: {e}")

        metrics.total_lines = total_lines
        metrics.lines_of_code = code_lines
        metrics.comment_lines = comment_lines
        metrics.blank_lines = blank_lines
        metrics.file_types = dict(file_counter)

        # Get largest files
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        metrics.largest_files = file_sizes[:10]

    def _collect_test_metrics(self, metrics: ProjectMetrics) -> None:
        """Collect testing-related metrics."""
        test_files = 0
        test_lines = 0

        for file_path in self._iter_code_files():
            try:
                rel_path = str(file_path.relative_to(self.working_directory))

                # Check if it's a test file
                is_test = any(
                    pattern in rel_path.lower() for pattern in self.TEST_PATTERNS
                )

                if is_test:
                    test_files += 1
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    test_lines += len(content.splitlines())

            except Exception as e:
                self.logger.debug(f"Error collecting test metrics for {file_path}: {e}")

        metrics.test_files = test_files

        # Calculate test to code ratio
        if metrics.lines_of_code > 0:
            metrics.test_to_code_ratio = test_lines / metrics.lines_of_code

        # Check for coverage files
        coverage_indicators = [".coverage", "coverage.xml", "coverage.json", "htmlcov"]
        for indicator in coverage_indicators:
            if (self.working_directory / indicator).exists():
                metrics.test_coverage_files += 1

    def _calculate_derived_metrics(self, metrics: ProjectMetrics) -> None:
        """Calculate derived metrics from collected data."""
        # Calculate average file size
        if metrics.total_files > 0:
            metrics.average_file_size = metrics.total_lines / metrics.total_files

        # Count directories
        dir_count = 0
        for _dirpath, dirnames, _ in self.working_directory.walk():
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDE_DIRS]
            dir_count += len(dirnames)

        metrics.total_directories = dir_count

        # Calculate average files per directory
        if dir_count > 0:
            metrics.average_files_per_directory = metrics.total_files / dir_count

        # Calculate max depth
        max_depth = 0
        for file_path in self._iter_code_files():
            depth = len(file_path.relative_to(self.working_directory).parts)
            max_depth = max(max_depth, depth)
        metrics.max_depth = max_depth

    def _iter_code_files(self):
        """Iterate over code files in the project."""
        for ext in self.CODE_EXTENSIONS:
            for file_path in self.working_directory.rglob(f"*{ext}"):
                if self._should_analyze_file(file_path):
                    yield file_path

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Check if a file should be analyzed."""
        # Skip files in excluded directories
        return all(part not in self.EXCLUDE_DIRS for part in file_path.parts)
