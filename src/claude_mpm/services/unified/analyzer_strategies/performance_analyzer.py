"""
Performance Analyzer Strategy Implementation
============================================

Analyzes code for performance bottlenecks and optimization opportunities.
Consolidates performance analysis functionality from multiple services.

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import ast
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


class PerformanceAnalyzerStrategy(AnalyzerStrategy):
    """
    Strategy for analyzing performance bottlenecks and optimization opportunities.

    Consolidates:
    - Algorithm complexity analysis
    - Database query optimization
    - Memory usage patterns
    - I/O operation efficiency
    - Caching opportunities
    """

    # Performance anti-patterns
    PERFORMANCE_PATTERNS: ClassVar[dict] = {
        "n_plus_one_query": {
            "patterns": [
                r"for .* in .*:\s*\n.*\.(get|filter|select|find)",
                r"\.map\s*\([^)]*=>\s*[^)]*fetch",
            ],
            "severity": "high",
            "description": "Potential N+1 query problem",
            "category": "database",
        },
        "unnecessary_loop": {
            "patterns": [
                r"for .* in .*:\s*\n\s*for .* in .*:\s*\n\s*for .* in .*:",
                r"\.forEach\s*\([^)]*\)\s*{\s*[^}]*\.forEach",
            ],
            "severity": "medium",
            "description": "Triple nested loop detected",
            "category": "algorithm",
        },
        "string_concatenation_loop": {
            "patterns": [
                r'for .* in .*:\s*\n.*\+=\s*["\']',
                r"\.forEach\s*\([^)]*\)\s*{\s*[^}]*\+=",
            ],
            "severity": "medium",
            "description": "String concatenation in loop",
            "category": "memory",
        },
        "synchronous_io": {
            "patterns": [
                r"open\s*\([^)]*\)\.read\s*\(",
                r"fs\.readFileSync\s*\(",
                r"requests\.get\s*\([^)]*\)\.text",
            ],
            "severity": "medium",
            "description": "Synchronous I/O operation",
            "category": "io",
        },
        "missing_index": {
            "patterns": [
                r"SELECT .* FROM .* WHERE .* LIKE .*%",
                r"\.find\s*\(\s*{\s*[^}]*:\s*{\s*\$regex",
            ],
            "severity": "high",
            "description": "Potentially unindexed database query",
            "category": "database",
        },
    }

    # Algorithm complexity indicators
    COMPLEXITY_INDICATORS: ClassVar[dict] = {
        "quadratic": ["nested_loops", "bubble_sort", "selection_sort"],
        "exponential": ["recursive_fibonacci", "recursive_factorial"],
        "linear": ["single_loop", "map", "filter"],
        "logarithmic": ["binary_search", "divide_conquer"],
        "constant": ["direct_access", "hash_lookup"],
    }

    # Memory usage patterns
    MEMORY_PATTERNS: ClassVar[dict] = {
        "memory_leak": {
            "patterns": [
                r"global\s+\w+\s*=",
                r"window\.\w+\s*=",
                r"self\.\w+\s*=\s*\[\]",
            ],
            "description": "Potential memory leak from global variable",
        },
        "large_data_structure": {
            "patterns": [
                r"\[\s*\*\s*range\s*\(\s*\d{6,}",
                r"Array\s*\(\s*\d{6,}\s*\)",
            ],
            "description": "Large data structure allocation",
        },
        "inefficient_copy": {
            "patterns": [
                r"deepcopy\s*\(",
                r"JSON\.parse\s*\(\s*JSON\.stringify",
                r"\.slice\s*\(\s*\)\.map",
            ],
            "description": "Inefficient data copying",
        },
    }

    def __init__(self):
        """Initialize performance analyzer strategy."""
        metadata = StrategyMetadata(
            name="PerformanceAnalyzer",
            description="Analyzes performance bottlenecks and optimization opportunities",
            supported_types=["file", "directory", "function", "query"],
            supported_operations=["analyze", "profile", "optimize", "benchmark"],
            priority=StrategyPriority.HIGH,
            tags={"performance", "optimization", "bottlenecks", "profiling"},
        )
        super().__init__(metadata)

        self._optimization_cache = {}

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
        elif not isinstance(input_data, (dict, ast.AST)):
            errors.append(f"Invalid input type: {type(input_data).__name__}")

        return errors

    def analyze(
        self, target: Any, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute performance analysis on target.

        Args:
            target: File, directory, or code to analyze
            options: Analysis options (profile_depth, check_queries, etc.)

        Returns:
            Analysis results with performance findings
        """
        options = options or {}

        if isinstance(target, (str, Path)):
            target_path = Path(target)

            if target_path.is_file():
                return self._analyze_file(target_path, options)
            if target_path.is_dir():
                return self._analyze_directory(target_path, options)
        elif isinstance(target, ast.AST):
            return self._analyze_ast_performance(target, options)

        return {
            "status": OperationResult.ERROR,
            "message": f"Unsupported target type: {type(target).__name__}",
        }

    def _analyze_file(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file for performance issues."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "file",
            "path": str(file_path),
            "issues": [],
            "optimizations": [],
            "complexity": {},
            "performance_score": 100,
        }

        try:
            content = file_path.read_text(encoding="utf-8")

            # Scan for performance patterns
            issues = self._scan_performance_patterns(content, file_path)
            results["issues"].extend(issues)

            # Check memory usage patterns
            memory_issues = self._scan_memory_patterns(content, file_path)
            results["issues"].extend(memory_issues)

            # Language-specific analysis
            if file_path.suffix == ".py":
                python_analysis = self._analyze_python_performance(content, file_path)
                results["complexity"] = python_analysis.get("complexity", {})
                results["issues"].extend(python_analysis.get("issues", []))
                results["optimizations"].extend(
                    python_analysis.get("optimizations", [])
                )

            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                js_analysis = self._analyze_javascript_performance(content, file_path)
                results["issues"].extend(js_analysis.get("issues", []))
                results["optimizations"].extend(js_analysis.get("optimizations", []))

            # Calculate performance score
            results["performance_score"] = self._calculate_performance_score(results)

            # Generate optimization recommendations
            if not results["optimizations"]:
                results["optimizations"] = self._generate_optimizations(
                    results["issues"]
                )

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            results["status"] = OperationResult.ERROR
            results["error"] = str(e)

        return results

    def _analyze_directory(
        self, dir_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze all files in a directory for performance issues."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "directory",
            "path": str(dir_path),
            "files_analyzed": 0,
            "total_issues": 0,
            "issues_by_category": {},
            "files": [],
            "performance_score": 100,
        }

        # Define file extensions to analyze
        analyzable_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".cs",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".sql",
        }

        total_score = 0

        # Analyze each file
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in analyzable_extensions:
                # Skip common ignore patterns
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                if any(
                    ignore in file_path.parts
                    for ignore in ["node_modules", "__pycache__", "dist", "build"]
                ):
                    continue

                file_result = self._analyze_file(file_path, options)
                if file_result["status"] == OperationResult.SUCCESS:
                    results["files_analyzed"] += 1
                    total_score += file_result["performance_score"]

                    if file_result["issues"]:
                        results["files"].append(file_result)
                        results["total_issues"] += len(file_result["issues"])

                        # Categorize issues
                        for issue in file_result["issues"]:
                            category = issue.get("category", "unknown")
                            results["issues_by_category"][category] = (
                                results["issues_by_category"].get(category, 0) + 1
                            )

        # Calculate average performance score
        if results["files_analyzed"] > 0:
            results["performance_score"] = total_score / results["files_analyzed"]

        # Add summary and recommendations
        results["summary"] = self._generate_performance_summary(results)
        results["recommendations"] = self._generate_directory_recommendations(results)

        return results

    def _scan_performance_patterns(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Scan for performance anti-patterns."""
        issues = []

        for pattern_name, pattern_info in self.PERFORMANCE_PATTERNS.items():
            for pattern in pattern_info["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "type": pattern_name,
                            "severity": pattern_info["severity"],
                            "category": pattern_info["category"],
                            "description": pattern_info["description"],
                            "file": str(file_path),
                            "line": line_num,
                            "code": match.group(0)[:100],
                        }
                    )

        return issues

    def _scan_memory_patterns(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Scan for memory usage issues."""
        issues = []

        for pattern_name, pattern_info in self.MEMORY_PATTERNS.items():
            for pattern in pattern_info["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "type": f"memory_{pattern_name}",
                            "severity": "medium",
                            "category": "memory",
                            "description": pattern_info["description"],
                            "file": str(file_path),
                            "line": line_num,
                            "code": match.group(0),
                        }
                    )

        return issues

    def _analyze_python_performance(
        self, content: str, file_path: Path
    ) -> Dict[str, Any]:
        """Perform Python-specific performance analysis."""
        results = {
            "complexity": {},
            "issues": [],
            "optimizations": [],
        }

        try:
            tree = ast.parse(content)

            # Analyze function complexities
            class PerformanceVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.current_function = None
                    self.loop_depth = 0
                    self.complexities = {}

                def visit_FunctionDef(self, node):
                    old_function = self.current_function
                    self.current_function = node.name
                    old_depth = self.loop_depth
                    self.loop_depth = 0

                    # Calculate complexity
                    complexity = self._calculate_complexity(node)
                    self.complexities[node.name] = complexity

                    # Check for performance issues
                    if complexity["time_complexity"] in ["O(n^2)", "O(n^3)", "O(2^n)"]:
                        results["issues"].append(
                            {
                                "type": "high_complexity",
                                "severity": "high",
                                "category": "algorithm",
                                "description": f"Function '{node.name}' has {complexity['time_complexity']} complexity",
                                "file": str(file_path),
                                "line": node.lineno,
                                "code": node.name,
                            }
                        )

                    self.generic_visit(node)
                    self.current_function = old_function
                    self.loop_depth = old_depth

                def visit_For(self, node):
                    self.loop_depth += 1
                    if self.loop_depth > 2:
                        results["issues"].append(
                            {
                                "type": "deep_nesting",
                                "severity": "medium",
                                "category": "algorithm",
                                "description": f"Deep loop nesting (level {self.loop_depth})",
                                "file": str(file_path),
                                "line": node.lineno,
                                "code": f"Loop depth: {self.loop_depth}",
                            }
                        )
                    self.generic_visit(node)
                    self.loop_depth -= 1

                def visit_While(self, node):
                    self.visit_For(node)  # Treat while loops similarly

                def visit_ListComp(self, node):
                    # Check for nested list comprehensions
                    nested_comps = (
                        sum(
                            1
                            for child in ast.walk(node)
                            if isinstance(
                                child, (ast.ListComp, ast.SetComp, ast.DictComp)
                            )
                        )
                        - 1
                    )

                    if nested_comps > 1:
                        results["optimizations"].append(
                            {
                                "type": "nested_comprehension",
                                "description": "Consider breaking down nested comprehensions for clarity",
                                "file": str(file_path),
                                "line": node.lineno,
                            }
                        )

                def _calculate_complexity(self, node):
                    """Calculate time and space complexity of a function."""
                    loop_count = sum(
                        1 for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))
                    )

                    # Detect nested loops
                    max_nesting = 0
                    for child in ast.walk(node):
                        if isinstance(child, (ast.For, ast.While)):
                            nesting = self._get_loop_nesting(child, node)
                            max_nesting = max(max_nesting, nesting)

                    # Estimate complexity
                    if max_nesting >= 3:
                        time_complexity = f"O(n^{max_nesting})"
                    elif max_nesting == 2:
                        time_complexity = "O(n^2)"
                    elif max_nesting == 1:
                        time_complexity = "O(n)"
                    else:
                        time_complexity = "O(1)"

                    return {
                        "time_complexity": time_complexity,
                        "loop_count": loop_count,
                        "max_nesting": max_nesting,
                    }

                def _get_loop_nesting(self, loop_node, function_node):
                    """Get the nesting level of a loop."""
                    nesting = 1
                    for parent in ast.walk(function_node):
                        for child in ast.iter_child_nodes(parent):
                            if child is loop_node:
                                return nesting
                            if isinstance(child, (ast.For, ast.While)):
                                if loop_node in ast.walk(child):
                                    nesting += 1
                    return nesting

            visitor = PerformanceVisitor()
            visitor.visit(tree)
            results["complexity"] = visitor.complexities

            # Check for list operations that could be optimized
            self._check_python_optimizations(tree, results, file_path)

        except SyntaxError:
            pass

        return results

    def _check_python_optimizations(
        self, tree: ast.AST, results: Dict, file_path: Path
    ):
        """Check for Python-specific optimization opportunities."""

        class OptimizationVisitor(ast.NodeVisitor):
            def visit_For(self, node):
                # Check for range(len()) anti-pattern
                if isinstance(node.iter, ast.Call):
                    if (
                        isinstance(node.iter.func, ast.Name)
                        and node.iter.func.id == "range"
                        and len(node.iter.args) == 1
                    ):
                        if isinstance(node.iter.args[0], ast.Call):
                            if (
                                isinstance(node.iter.args[0].func, ast.Name)
                                and node.iter.args[0].func.id == "len"
                            ):
                                results["optimizations"].append(
                                    {
                                        "type": "range_len_pattern",
                                        "description": "Use enumerate() instead of range(len())",
                                        "file": str(file_path),
                                        "line": node.lineno,
                                    }
                                )

                self.generic_visit(node)

            def visit_ListComp(self, node):
                # Check if list comprehension could be a generator
                parent = None
                for p in ast.walk(tree):
                    for child in ast.iter_child_nodes(p):
                        if child is node:
                            parent = p
                            break

                if parent and isinstance(parent, ast.Call):
                    if isinstance(parent.func, ast.Name) and parent.func.id in [
                        "sum",
                        "any",
                        "all",
                        "min",
                        "max",
                    ]:
                        results["optimizations"].append(
                            {
                                "type": "generator_opportunity",
                                "description": "Consider using generator expression instead of list comprehension",
                                "file": str(file_path),
                                "line": node.lineno,
                            }
                        )

                self.generic_visit(node)

        visitor = OptimizationVisitor()
        visitor.visit(tree)

    def _analyze_javascript_performance(
        self, content: str, file_path: Path
    ) -> Dict[str, Any]:
        """Perform JavaScript-specific performance analysis."""
        results = {
            "issues": [],
            "optimizations": [],
        }

        # Check for common JS performance issues
        js_patterns = {
            "dom_in_loop": {
                "pattern": r"for\s*\([^)]*\)\s*{\s*[^}]*document\.(getElementById|querySelector)",
                "description": "DOM access inside loop - consider caching",
                "severity": "high",
            },
            "missing_debounce": {
                "pattern": r'addEventListener\s*\(\s*["\']scroll["\']',
                "description": "Scroll event without debouncing",
                "severity": "medium",
            },
            "sync_ajax": {
                "pattern": r"async\s*:\s*false",
                "description": "Synchronous AJAX request",
                "severity": "high",
            },
            "inefficient_array": {
                "pattern": r"\.shift\s*\(\s*\)",
                "description": "Array.shift() is O(n) - consider using different data structure",
                "severity": "medium",
            },
        }

        for issue_name, issue_info in js_patterns.items():
            matches = re.finditer(
                issue_info["pattern"], content, re.IGNORECASE | re.MULTILINE
            )
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                results["issues"].append(
                    {
                        "type": f"js_{issue_name}",
                        "severity": issue_info["severity"],
                        "category": "performance",
                        "description": issue_info["description"],
                        "file": str(file_path),
                        "line": line_num,
                        "code": match.group(0)[:100],
                    }
                )

        # Check for optimization opportunities
        if "forEach" in content and "return" not in content:
            results["optimizations"].append(
                {
                    "type": "use_for_of",
                    "description": "Consider using for...of instead of forEach for better performance",
                    "file": str(file_path),
                }
            )

        if ".map(" in content and ".filter(" in content:
            results["optimizations"].append(
                {
                    "type": "combine_array_methods",
                    "description": "Consider combining map and filter operations for better performance",
                    "file": str(file_path),
                }
            )

        return results

    def _analyze_ast_performance(
        self, node: ast.AST, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance of an AST node."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "ast",
            "complexity": {},
            "issues": [],
        }

        # Calculate complexity for the node
        if isinstance(node, ast.FunctionDef):
            loop_count = sum(
                1 for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))
            )

            results["complexity"] = {
                "name": node.name,
                "loop_count": loop_count,
                "line_count": (
                    node.end_lineno - node.lineno + 1
                    if hasattr(node, "end_lineno")
                    else 0
                ),
            }

            if loop_count > 3:
                results["issues"].append(
                    {
                        "type": "excessive_loops",
                        "severity": "medium",
                        "description": f"Function has {loop_count} loops",
                    }
                )

        return results

    def _calculate_performance_score(self, results: Dict[str, Any]) -> float:
        """Calculate performance score based on issues found."""
        score = 100.0

        severity_penalties = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2,
        }

        for issue in results.get("issues", []):
            severity = issue.get("severity", "low")
            penalty = severity_penalties.get(severity, 1)
            score -= penalty

        return max(0, score)

    def _generate_optimizations(
        self, issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on issues."""
        optimizations = []
        categories = set()

        for issue in issues:
            category = issue.get("category", "unknown")
            categories.add(category)

        if "database" in categories:
            optimizations.append(
                {
                    "type": "database_optimization",
                    "description": "Consider adding database indexes and optimizing queries",
                    "priority": "high",
                }
            )

        if "algorithm" in categories:
            optimizations.append(
                {
                    "type": "algorithm_optimization",
                    "description": "Review algorithm complexity and consider more efficient approaches",
                    "priority": "high",
                }
            )

        if "memory" in categories:
            optimizations.append(
                {
                    "type": "memory_optimization",
                    "description": "Optimize memory usage by using generators and avoiding large allocations",
                    "priority": "medium",
                }
            )

        if "io" in categories:
            optimizations.append(
                {
                    "type": "io_optimization",
                    "description": "Use asynchronous I/O operations to improve responsiveness",
                    "priority": "medium",
                }
            )

        return optimizations

    def _generate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of performance analysis."""
        return {
            "files_analyzed": results["files_analyzed"],
            "total_issues": results["total_issues"],
            "average_score": results["performance_score"],
            "top_categories": sorted(
                results["issues_by_category"].items(), key=lambda x: x[1], reverse=True
            )[:3],
        }

    def _generate_directory_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations for directory-level performance."""
        recommendations = []

        issues_by_category = results.get("issues_by_category", {})

        if issues_by_category.get("database", 0) > 5:
            recommendations.append(
                "Multiple database performance issues detected. Consider implementing query optimization and caching strategies."
            )

        if issues_by_category.get("algorithm", 0) > 10:
            recommendations.append(
                "High number of algorithmic complexity issues. Review and optimize critical code paths."
            )

        if issues_by_category.get("memory", 0) > 5:
            recommendations.append(
                "Memory usage issues detected. Implement memory profiling and optimize data structures."
            )

        if results["performance_score"] < 50:
            recommendations.append(
                "Overall performance score is low. Consider conducting a comprehensive performance audit."
            )

        if not recommendations:
            recommendations.append(
                "Performance is generally good. Continue monitoring for regressions."
            )

        return recommendations

    def extract_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from analysis results."""
        metrics = {}

        if analysis_result.get("status") != OperationResult.SUCCESS:
            return metrics

        if analysis_result.get("type") == "file":
            metrics.update(
                {
                    "performance_score": analysis_result.get("performance_score", 0),
                    "issue_count": len(analysis_result.get("issues", [])),
                    "optimization_count": len(analysis_result.get("optimizations", [])),
                }
            )

            # Add complexity metrics if available
            if "complexity" in analysis_result:
                for func_name, complexity in analysis_result["complexity"].items():
                    metrics[f"complexity_{func_name}"] = complexity.get(
                        "time_complexity", "O(1)"
                    )

        elif analysis_result.get("type") == "directory":
            metrics.update(
                {
                    "files_analyzed": analysis_result.get("files_analyzed", 0),
                    "total_issues": analysis_result.get("total_issues", 0),
                    "average_score": analysis_result.get("performance_score", 0),
                }
            )

            # Add category breakdown
            for category, count in analysis_result.get(
                "issues_by_category", {}
            ).items():
                metrics[f"category_{category}"] = count

        return metrics

    def compare_results(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two performance analysis results."""
        comparison = {
            "score_change": 0,
            "issue_changes": {},
            "improvements": [],
            "regressions": [],
        }

        # Compare performance scores
        baseline_score = baseline.get("performance_score", 100)
        current_score = current.get("performance_score", 100)
        comparison["score_change"] = current_score - baseline_score

        # Compare issue counts
        baseline_metrics = self.extract_metrics(baseline)
        current_metrics = self.extract_metrics(current)

        baseline_issues = baseline_metrics.get(
            "total_issues", baseline_metrics.get("issue_count", 0)
        )
        current_issues = current_metrics.get(
            "total_issues", current_metrics.get("issue_count", 0)
        )

        if current_issues < baseline_issues:
            comparison["improvements"].append(
                f"Reduced performance issues from {baseline_issues} to {current_issues}"
            )
        elif current_issues > baseline_issues:
            comparison["regressions"].append(
                f"Performance issues increased from {baseline_issues} to {current_issues}"
            )

        # Compare by category if available
        for key in baseline_metrics:
            if key.startswith("category_"):
                category = key.replace("category_", "")
                if key in current_metrics:
                    baseline_count = baseline_metrics[key]
                    current_count = current_metrics[key]

                    if baseline_count != current_count:
                        comparison["issue_changes"][category] = {
                            "baseline": baseline_count,
                            "current": current_count,
                            "change": current_count - baseline_count,
                        }

        # Performance score interpretation
        if comparison["score_change"] > 10:
            comparison["improvements"].append(
                f"Significant performance improvement: +{comparison['score_change']:.1f} points"
            )
        elif comparison["score_change"] < -10:
            comparison["regressions"].append(
                f"Significant performance regression: {comparison['score_change']:.1f} points"
            )

        return comparison
