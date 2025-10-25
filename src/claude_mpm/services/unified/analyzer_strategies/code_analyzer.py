"""
Code Analyzer Strategy Implementation
=====================================

Analyzes code structure, complexity, quality metrics, and patterns.
Consolidates functionality from multiple analyzer services.

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logging_utils import get_logger

from ..strategies import (
    AnalyzerStrategy,
    StrategyContext,
    StrategyMetadata,
    StrategyPriority,
)

logger = get_logger(__name__)


class CodeAnalyzerStrategy(AnalyzerStrategy):
    """
    Strategy for analyzing code structure, complexity, and quality metrics.

    Consolidates:
    - Code complexity analysis (cyclomatic, cognitive)
    - Code quality metrics (maintainability index, technical debt)
    - Pattern detection (anti-patterns, code smells)
    - Function/class analysis (size, complexity, coupling)
    """

    def __init__(self):
        """Initialize code analyzer strategy."""
        metadata = StrategyMetadata(
            name="CodeAnalyzer",
            description="Analyzes code structure, complexity, and quality metrics",
            supported_types=["file", "directory", "module", "class", "function"],
            supported_operations=["analyze", "metrics", "complexity", "quality"],
            priority=StrategyPriority.HIGH,
            tags={"code", "complexity", "quality", "metrics", "ast"},
        )
        super().__init__(metadata)

        # Language-specific file extensions
        self.language_extensions = {
            "python": {".py", ".pyi"},
            "javascript": {".js", ".jsx", ".mjs"},
            "typescript": {".ts", ".tsx"},
            "java": {".java"},
            "go": {".go"},
            "rust": {".rs"},
            "c": {".c", ".h"},
            "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".h"},
        }

        # Code smell patterns
        self.code_smell_patterns = {
            "long_method": {"threshold": 50, "metric": "lines"},
            "large_class": {"threshold": 500, "metric": "lines"},
            "long_parameter_list": {"threshold": 5, "metric": "count"},
            "duplicate_code": {"threshold": 0.7, "metric": "similarity"},
            "god_class": {"threshold": 10, "metric": "responsibilities"},
        }

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
        Execute code analysis on target.

        Args:
            target: Code file, directory, or AST node to analyze
            options: Analysis options (language, metrics, depth, etc.)

        Returns:
            Analysis results with metrics and findings
        """
        options = options or {}

        # Determine target type and language
        if isinstance(target, (str, Path)):
            target_path = Path(target)
            if target_path.is_file():
                return self._analyze_file(target_path, options)
            if target_path.is_dir():
                return self._analyze_directory(target_path, options)
        elif isinstance(target, ast.AST):
            return self._analyze_ast(target, options)

        return {
            "status": OperationResult.ERROR,
            "message": f"Unsupported target type: {type(target).__name__}",
        }

    def _analyze_file(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single code file."""
        try:
            # Detect language from extension
            language = self._detect_language(file_path)

            # Read file content
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            # Base metrics
            metrics = {
                "file": str(file_path),
                "language": language,
                "lines_of_code": len(lines),
                "blank_lines": sum(1 for line in lines if not line.strip()),
                "comment_lines": self._count_comment_lines(content, language),
            }

            # Language-specific analysis
            if language == "python":
                metrics.update(self._analyze_python_code(content, file_path))

            # Calculate complexity metrics
            metrics["complexity"] = self._calculate_complexity_metrics(
                content, language
            )

            # Detect code smells
            metrics["code_smells"] = self._detect_code_smells(content, metrics)

            # Calculate maintainability index
            metrics["maintainability_index"] = self._calculate_maintainability(metrics)

            return {
                "status": OperationResult.SUCCESS,
                "type": "file",
                "path": str(file_path),
                "metrics": metrics,
            }

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                "status": OperationResult.ERROR,
                "path": str(file_path),
                "error": str(e),
            }

    def _analyze_directory(
        self, dir_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze all code files in a directory."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "directory",
            "path": str(dir_path),
            "files": [],
            "summary": {},
        }

        # Collect all code files
        code_files = []
        for ext_set in self.language_extensions.values():
            for ext in ext_set:
                code_files.extend(dir_path.rglob(f"*{ext}"))

        # Analyze each file
        total_metrics = {}
        for file_path in code_files:
            file_result = self._analyze_file(file_path, options)
            if file_result["status"] == OperationResult.SUCCESS:
                results["files"].append(file_result)

                # Aggregate metrics
                for key, value in file_result.get("metrics", {}).items():
                    if isinstance(value, (int, float)):
                        total_metrics[key] = total_metrics.get(key, 0) + value

        # Calculate summary statistics
        results["summary"] = {
            "total_files": len(results["files"]),
            "total_lines": total_metrics.get("lines_of_code", 0),
            "average_complexity": total_metrics.get("complexity", {}).get(
                "cyclomatic", 0
            )
            / max(len(results["files"]), 1),
            "code_smells_count": sum(
                len(f.get("metrics", {}).get("code_smells", []))
                for f in results["files"]
            ),
        }

        return results

    def _analyze_python_code(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Perform Python-specific code analysis."""
        try:
            tree = ast.parse(content)

            # Count functions, classes, methods
            functions = []
            classes = []
            methods = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if any(
                        isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)
                    ):
                        methods.append(node.name)
                    else:
                        functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)

            return {
                "functions": functions,
                "classes": classes,
                "methods": methods,
                "function_count": len(functions),
                "class_count": len(classes),
                "method_count": len(methods),
            }

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return {}

    def _analyze_ast(self, node: ast.AST, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an AST node directly."""
        metrics = {
            "node_type": node.__class__.__name__,
            "complexity": self._calculate_ast_complexity(node),
        }

        # Analyze specific node types
        if isinstance(node, ast.FunctionDef):
            metrics.update(
                {
                    "name": node.name,
                    "parameters": len(node.args.args),
                    "lines": (
                        node.end_lineno - node.lineno + 1
                        if hasattr(node, "end_lineno")
                        else 0
                    ),
                }
            )
        elif isinstance(node, ast.ClassDef):
            metrics.update(
                {
                    "name": node.name,
                    "methods": sum(
                        1 for n in node.body if isinstance(n, ast.FunctionDef)
                    ),
                    "bases": len(node.bases),
                }
            )

        return {
            "status": OperationResult.SUCCESS,
            "type": "ast",
            "metrics": metrics,
        }

    def _calculate_complexity_metrics(
        self, content: str, language: str
    ) -> Dict[str, Any]:
        """Calculate various complexity metrics."""
        complexity = {
            "cyclomatic": 1,  # Base complexity
            "cognitive": 0,
            "halstead": {},
        }

        if language == "python":
            try:
                tree = ast.parse(content)
                complexity["cyclomatic"] = self._calculate_cyclomatic_complexity(tree)
                complexity["cognitive"] = self._calculate_cognitive_complexity(tree)
            except (SyntaxError, ValueError):
                pass

        return complexity

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity for Python AST."""
        complexity = 1

        for node in ast.walk(tree):
            # Decision points increase complexity
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity (simplified version)."""
        complexity = 0
        nesting_level = 0

        # Simplified cognitive complexity calculation
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1 + nesting_level
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_ast_complexity(self, node: ast.AST) -> int:
        """Calculate complexity for a single AST node."""
        return self._calculate_cyclomatic_complexity(node)

    def _detect_code_smells(
        self, content: str, metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect common code smells."""
        smells = []

        # Long method/function
        if (
            metrics.get("lines_of_code", 0)
            > self.code_smell_patterns["long_method"]["threshold"]
        ):
            smells.append(
                {
                    "type": "long_method",
                    "severity": "medium",
                    "message": f"Method/function has {metrics['lines_of_code']} lines (threshold: {self.code_smell_patterns['long_method']['threshold']})",
                }
            )

        # High complexity
        complexity = metrics.get("complexity", {}).get("cyclomatic", 0)
        if complexity > 10:
            smells.append(
                {
                    "type": "high_complexity",
                    "severity": "high",
                    "message": f"High cyclomatic complexity: {complexity}",
                }
            )

        return smells

    def _calculate_maintainability(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate maintainability index (0-100 scale).
        Simplified version of the standard formula.
        """
        loc = metrics.get("lines_of_code", 0)
        complexity = metrics.get("complexity", {}).get("cyclomatic", 1)

        # Simplified maintainability index
        if loc == 0:
            return 100.0

        # Basic formula (simplified)
        mi = 171 - 5.2 * (loc / 100) - 0.23 * complexity

        # Normalize to 0-100 scale
        return max(0, min(100, mi))

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()

        for language, extensions in self.language_extensions.items():
            if ext in extensions:
                return language

        return "unknown"

    def _count_comment_lines(self, content: str, language: str) -> int:
        """Count comment lines based on language."""
        comment_patterns = {
            "python": r"^\s*#",
            "javascript": r"^\s*(//|/\*|\*)",
            "java": r"^\s*(//|/\*|\*)",
            "c": r"^\s*(//|/\*|\*)",
            "cpp": r"^\s*(//|/\*|\*)",
        }

        pattern = comment_patterns.get(language)
        if not pattern:
            return 0

        count = 0
        for line in content.splitlines():
            if re.match(pattern, line):
                count += 1

        return count

    def extract_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from analysis results."""
        metrics = {}

        if analysis_result.get("status") != OperationResult.SUCCESS:
            return metrics

        # Extract relevant metrics
        if "metrics" in analysis_result:
            raw_metrics = analysis_result["metrics"]

            metrics.update(
                {
                    "lines_of_code": raw_metrics.get("lines_of_code", 0),
                    "cyclomatic_complexity": raw_metrics.get("complexity", {}).get(
                        "cyclomatic", 0
                    ),
                    "cognitive_complexity": raw_metrics.get("complexity", {}).get(
                        "cognitive", 0
                    ),
                    "maintainability_index": raw_metrics.get(
                        "maintainability_index", 0
                    ),
                    "code_smells": len(raw_metrics.get("code_smells", [])),
                    "function_count": raw_metrics.get("function_count", 0),
                    "class_count": raw_metrics.get("class_count", 0),
                }
            )

        # Extract summary metrics for directory analysis
        if "summary" in analysis_result:
            summary = analysis_result["summary"]
            metrics.update(
                {
                    "total_files": summary.get("total_files", 0),
                    "total_lines": summary.get("total_lines", 0),
                    "average_complexity": summary.get("average_complexity", 0),
                    "total_code_smells": summary.get("code_smells_count", 0),
                }
            )

        return metrics

    def compare_results(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two analysis results."""
        comparison = {
            "improved": [],
            "degraded": [],
            "unchanged": [],
        }

        baseline_metrics = self.extract_metrics(baseline)
        current_metrics = self.extract_metrics(current)

        for key in baseline_metrics:
            if key not in current_metrics:
                continue

            baseline_val = baseline_metrics[key]
            current_val = current_metrics[key]

            if isinstance(baseline_val, (int, float)):
                diff = current_val - baseline_val
                pct_change = (diff / baseline_val * 100) if baseline_val else 0

                result = {
                    "metric": key,
                    "baseline": baseline_val,
                    "current": current_val,
                    "change": diff,
                    "percent_change": pct_change,
                }

                # Determine if improvement or degradation
                if key in ["maintainability_index"]:
                    # Higher is better
                    if diff > 0:
                        comparison["improved"].append(result)
                    elif diff < 0:
                        comparison["degraded"].append(result)
                    else:
                        comparison["unchanged"].append(result)
                # Lower is better (complexity, code smells, etc.)
                elif diff < 0:
                    comparison["improved"].append(result)
                elif diff > 0:
                    comparison["degraded"].append(result)
                else:
                    comparison["unchanged"].append(result)

        return comparison
