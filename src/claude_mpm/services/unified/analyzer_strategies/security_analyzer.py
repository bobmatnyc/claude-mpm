"""
Security Analyzer Strategy Implementation
=========================================

Analyzes code for security vulnerabilities and compliance issues.
Consolidates security analysis functionality from multiple services.

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


class SecurityAnalyzerStrategy(AnalyzerStrategy):
    """
    Strategy for analyzing security vulnerabilities and compliance.

    Consolidates:
    - Vulnerability detection (SQL injection, XSS, etc.)
    - Hardcoded secrets detection
    - Insecure configuration detection
    - Dependency vulnerability scanning
    - Security best practices validation
    """

    # Common security vulnerability patterns
    VULNERABILITY_PATTERNS: ClassVar[dict] = {
        "sql_injection": {
            "patterns": [
                r'(execute|query)\s*\(\s*["\'].*%[s|d].*["\'].*%',
                r"(execute|query)\s*\(\s*.*\+.*\)",
                r'f["\'].*SELECT.*{.*}.*FROM',
            ],
            "severity": "critical",
            "description": "Potential SQL injection vulnerability",
        },
        "hardcoded_secret": {
            "patterns": [
                r'(password|passwd|pwd|secret|token|api_key)\s*=\s*["\'][^"\']{8,}["\']',
                r'(AWS|AZURE|GCP)_.*KEY\s*=\s*["\'][^"\']+["\']',
                r'(private_key|secret_key)\s*=\s*["\'][^"\']+["\']',
            ],
            "severity": "high",
            "description": "Hardcoded secret or credential detected",
        },
        "weak_crypto": {
            "patterns": [
                r"(MD5|SHA1)\s*\(",
                r"DES\s*\(",
                r"Random\(\)(?!\.SystemRandom)",
            ],
            "severity": "medium",
            "description": "Weak cryptographic algorithm usage",
        },
        "command_injection": {
            "patterns": [
                r"os\.(system|popen|spawn.*)\s*\([^)]*\+[^)]*\)",
                r"subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True",
                r"eval\s*\([^)]*input\s*\(",
            ],
            "severity": "critical",
            "description": "Potential command injection vulnerability",
        },
        "path_traversal": {
            "patterns": [
                r"open\s*\([^)]*\.\.[/\\]",
                r"(read_file|write_file)\s*\([^)]*user_input",
                r"Path\s*\([^)]*\+[^)]*\)",
            ],
            "severity": "high",
            "description": "Potential path traversal vulnerability",
        },
        "xss": {
            "patterns": [
                r"innerHTML\s*=\s*[^;]*user",
                r"document\.write\s*\([^)]*user",
                r'v-html\s*=\s*["\'][^"\']*user',
            ],
            "severity": "high",
            "description": "Potential cross-site scripting (XSS) vulnerability",
        },
    }

    # Insecure configuration patterns
    CONFIG_ISSUES: ClassVar[dict] = {
        "debug_enabled": {
            "patterns": [
                r"DEBUG\s*=\s*True",
                r"debug\s*:\s*true",
                r"app\.debug\s*=\s*True",
            ],
            "severity": "medium",
            "description": "Debug mode enabled in production configuration",
        },
        "insecure_cors": {
            "patterns": [
                r"Access-Control-Allow-Origin.*\*",
                r'cors\s*\(.*origin\s*:\s*["\'].*\*',
                r"CORS_ORIGIN_ALLOW_ALL\s*=\s*True",
            ],
            "severity": "medium",
            "description": "Insecure CORS configuration allowing all origins",
        },
        "missing_csrf": {
            "patterns": [
                r"csrf_enabled\s*=\s*False",
                r"CSRF_ENABLED\s*=\s*False",
                r"@csrf_exempt",
            ],
            "severity": "high",
            "description": "CSRF protection disabled",
        },
    }

    # Security headers to check
    SECURITY_HEADERS: ClassVar[list] = [
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Strict-Transport-Security",
        "X-XSS-Protection",
    ]

    def __init__(self):
        """Initialize security analyzer strategy."""
        metadata = StrategyMetadata(
            name="SecurityAnalyzer",
            description="Analyzes code for security vulnerabilities and compliance",
            supported_types=["file", "directory", "project"],
            supported_operations=["analyze", "scan", "audit", "compliance"],
            priority=StrategyPriority.CRITICAL,
            tags={"security", "vulnerabilities", "compliance", "audit"},
        )
        super().__init__(metadata)

        self._vulnerability_cache = {}

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
        else:
            errors.append(f"Invalid input type: {type(input_data).__name__}")

        return errors

    def analyze(
        self, target: Any, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute security analysis on target.

        Args:
            target: File, directory, or project to analyze
            options: Analysis options (scan_depth, check_dependencies, etc.)

        Returns:
            Analysis results with security findings
        """
        options = options or {}

        if isinstance(target, (str, Path)):
            target_path = Path(target)

            if target_path.is_file():
                return self._analyze_file(target_path, options)
            if target_path.is_dir():
                return self._analyze_directory(target_path, options)

        return {
            "status": OperationResult.ERROR,
            "message": f"Unsupported target type: {type(target).__name__}",
        }

    def _analyze_file(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file for security issues."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "file",
            "path": str(file_path),
            "vulnerabilities": [],
            "risk_score": 0,
        }

        try:
            content = file_path.read_text(encoding="utf-8")

            # Check for vulnerability patterns
            vulnerabilities = self._scan_for_vulnerabilities(content, file_path)
            results["vulnerabilities"].extend(vulnerabilities)

            # Check for configuration issues
            config_issues = self._scan_for_config_issues(content, file_path)
            results["vulnerabilities"].extend(config_issues)

            # Language-specific analysis
            if file_path.suffix == ".py":
                python_issues = self._analyze_python_security(content, file_path)
                results["vulnerabilities"].extend(python_issues)
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                js_issues = self._analyze_javascript_security(content, file_path)
                results["vulnerabilities"].extend(js_issues)

            # Calculate risk score
            results["risk_score"] = self._calculate_risk_score(
                results["vulnerabilities"]
            )

            # Add summary
            results["summary"] = self._generate_summary(results["vulnerabilities"])

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            results["status"] = OperationResult.ERROR
            results["error"] = str(e)

        return results

    def _analyze_directory(
        self, dir_path: Path, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze all files in a directory for security issues."""
        results = {
            "status": OperationResult.SUCCESS,
            "type": "directory",
            "path": str(dir_path),
            "files_analyzed": 0,
            "total_vulnerabilities": 0,
            "vulnerabilities_by_severity": {},
            "files": [],
            "risk_score": 0,
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
            ".php",
            ".rb",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
            ".yml",
            ".yaml",
            ".json",
            ".xml",
            ".conf",
            ".config",
            ".env",
            ".ini",
            ".properties",
        }

        # Analyze each file
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in analyzable_extensions:
                # Skip common ignore patterns
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                if "node_modules" in file_path.parts:
                    continue
                if "__pycache__" in file_path.parts:
                    continue

                file_result = self._analyze_file(file_path, options)
                if (
                    file_result["status"] == OperationResult.SUCCESS
                    and file_result["vulnerabilities"]
                ):
                    results["files"].append(file_result)
                    results["files_analyzed"] += 1
                    results["total_vulnerabilities"] += len(
                        file_result["vulnerabilities"]
                    )

                    # Count by severity
                    for vuln in file_result["vulnerabilities"]:
                        severity = vuln.get("severity", "unknown")
                        results["vulnerabilities_by_severity"][severity] = (
                            results["vulnerabilities_by_severity"].get(severity, 0) + 1
                        )

        # Calculate overall risk score
        results["risk_score"] = self._calculate_overall_risk(results)

        # Add recommendations
        results["recommendations"] = self._generate_recommendations(results)

        return results

    def _scan_for_vulnerabilities(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Scan content for known vulnerability patterns."""
        vulnerabilities = []

        for vuln_type, vuln_info in self.VULNERABILITY_PATTERNS.items():
            for pattern in vuln_info["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1

                    vulnerabilities.append(
                        {
                            "type": vuln_type,
                            "severity": vuln_info["severity"],
                            "description": vuln_info["description"],
                            "file": str(file_path),
                            "line": line_num,
                            "code": match.group(0)[:100],  # Truncate long matches
                            "pattern": pattern,
                        }
                    )

        return vulnerabilities

    def _scan_for_config_issues(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Scan for insecure configuration patterns."""
        issues = []

        # Only check configuration files
        config_extensions = {
            ".yml",
            ".yaml",
            ".json",
            ".conf",
            ".config",
            ".ini",
            ".env",
        }
        if file_path.suffix not in config_extensions and file_path.name not in [
            "settings.py",
            "config.py",
            "configuration.py",
        ]:
            return issues

        for issue_type, issue_info in self.CONFIG_ISSUES.items():
            for pattern in issue_info["patterns"]:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "type": f"config_{issue_type}",
                            "severity": issue_info["severity"],
                            "description": issue_info["description"],
                            "file": str(file_path),
                            "line": line_num,
                            "code": match.group(0),
                        }
                    )

        return issues

    def _analyze_python_security(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Perform Python-specific security analysis."""
        issues = []

        try:
            tree = ast.parse(content)

            # Check for dangerous functions
            dangerous_functions = {
                "eval": "critical",
                "exec": "critical",
                "compile": "high",
                "__import__": "medium",
                "pickle.loads": "high",
                "pickle.load": "high",
            }

            class SecurityVisitor(ast.NodeVisitor):
                def visit_Call(self, node):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in dangerous_functions:
                            issues.append(
                                {
                                    "type": "dangerous_function",
                                    "severity": dangerous_functions[func_name],
                                    "description": f"Use of dangerous function: {func_name}",
                                    "file": str(file_path),
                                    "line": node.lineno,
                                    "code": func_name,
                                }
                            )

                    # Check for subprocess with shell=True
                    elif isinstance(node.func, ast.Attribute):
                        if (
                            hasattr(node.func.value, "id")
                            and node.func.value.id == "subprocess"
                            and node.func.attr in ["run", "call", "Popen"]
                        ):
                            for keyword in node.keywords:
                                if (
                                    keyword.arg == "shell"
                                    and isinstance(keyword.value, ast.Constant)
                                    and keyword.value.value is True
                                ):
                                    issues.append(
                                        {
                                            "type": "shell_injection",
                                            "severity": "critical",
                                            "description": "subprocess with shell=True is vulnerable to injection",
                                            "file": str(file_path),
                                            "line": node.lineno,
                                            "code": "subprocess with shell=True",
                                        }
                                    )

                    self.generic_visit(node)

            visitor = SecurityVisitor()
            visitor.visit(tree)

        except SyntaxError:
            # Not valid Python, skip AST analysis
            pass

        return issues

    def _analyze_javascript_security(
        self, content: str, file_path: Path
    ) -> List[Dict[str, Any]]:
        """Perform JavaScript-specific security analysis."""
        issues = []

        # Check for dangerous JavaScript patterns
        js_patterns = {
            "eval_usage": {
                "pattern": r"\beval\s*\(",
                "severity": "critical",
                "description": "Use of eval() is dangerous and should be avoided",
            },
            "innerhtml": {
                "pattern": r"\.innerHTML\s*=",
                "severity": "high",
                "description": "Direct innerHTML assignment can lead to XSS",
            },
            "document_write": {
                "pattern": r"document\.write\s*\(",
                "severity": "medium",
                "description": "document.write() can be dangerous with user input",
            },
            "localstorage_sensitive": {
                "pattern": r'localStorage\.(setItem|getItem).*["\']*(password|token|secret)',
                "severity": "high",
                "description": "Sensitive data in localStorage is insecure",
            },
        }

        for issue_type, issue_info in js_patterns.items():
            matches = re.finditer(issue_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                issues.append(
                    {
                        "type": f"js_{issue_type}",
                        "severity": issue_info["severity"],
                        "description": issue_info["description"],
                        "file": str(file_path),
                        "line": line_num,
                        "code": match.group(0),
                    }
                )

        return issues

    def _calculate_risk_score(self, vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calculate risk score based on vulnerabilities."""
        if not vulnerabilities:
            return 0.0

        severity_scores = {
            "critical": 10,
            "high": 7,
            "medium": 4,
            "low": 1,
            "unknown": 0,
        }

        total_score = sum(
            severity_scores.get(v.get("severity", "unknown"), 0)
            for v in vulnerabilities
        )

        # Normalize to 0-100 scale
        # Maximum reasonable score would be ~50 critical issues = 500
        normalized = min(100, (total_score / 50) * 100)

        return round(normalized, 2)

    def _calculate_overall_risk(self, results: Dict[str, Any]) -> float:
        """Calculate overall risk score for directory analysis."""
        severity_weights = {
            "critical": 1.0,
            "high": 0.7,
            "medium": 0.4,
            "low": 0.1,
        }

        weighted_score = 0
        total_weight = 0

        for severity, count in results["vulnerabilities_by_severity"].items():
            weight = severity_weights.get(severity, 0)
            weighted_score += count * weight * 10
            total_weight += count

        if total_weight == 0:
            return 0.0

        # Normalize and cap at 100
        return min(100.0, round(weighted_score / max(results["files_analyzed"], 1), 2))

    def _generate_summary(
        self, vulnerabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary of security findings."""
        summary = {
            "total": len(vulnerabilities),
            "by_severity": {},
            "by_type": {},
            "most_critical": None,
        }

        for vuln in vulnerabilities:
            # Count by severity
            severity = vuln.get("severity", "unknown")
            summary["by_severity"][severity] = (
                summary["by_severity"].get(severity, 0) + 1
            )

            # Count by type
            vuln_type = vuln.get("type", "unknown")
            summary["by_type"][vuln_type] = summary["by_type"].get(vuln_type, 0) + 1

        # Find most critical issue
        critical_vulns = [v for v in vulnerabilities if v.get("severity") == "critical"]
        if critical_vulns:
            summary["most_critical"] = critical_vulns[0]

        return summary

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        vuln_by_severity = results.get("vulnerabilities_by_severity", {})

        if vuln_by_severity.get("critical", 0) > 0:
            recommendations.append(
                "URGENT: Address critical security vulnerabilities immediately"
            )

        if vuln_by_severity.get("high", 0) > 0:
            recommendations.append("Prioritize fixing high-severity vulnerabilities")

        # Type-specific recommendations
        if results["files"]:
            all_types = set()
            for file_result in results["files"]:
                for vuln in file_result.get("vulnerabilities", []):
                    all_types.add(vuln.get("type"))

            if "sql_injection" in all_types:
                recommendations.append(
                    "Use parameterized queries or prepared statements to prevent SQL injection"
                )

            if "hardcoded_secret" in all_types:
                recommendations.append(
                    "Move secrets to environment variables or secure vaults"
                )

            if "command_injection" in all_types or "shell_injection" in all_types:
                recommendations.append(
                    "Avoid shell=True in subprocess calls; use argument lists instead"
                )

            if "weak_crypto" in all_types:
                recommendations.append(
                    "Replace weak cryptographic algorithms with strong ones (e.g., SHA-256+)"
                )

            if any(t.startswith("config_") for t in all_types):
                recommendations.append(
                    "Review and harden configuration settings for production"
                )

        if not recommendations:
            recommendations.append(
                "No critical security issues found. Continue with regular security audits."
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
                    "vulnerabilities": len(analysis_result.get("vulnerabilities", [])),
                    "risk_score": analysis_result.get("risk_score", 0),
                }
            )

            # Count by severity
            for vuln in analysis_result.get("vulnerabilities", []):
                severity = vuln.get("severity", "unknown")
                key = f"severity_{severity}"
                metrics[key] = metrics.get(key, 0) + 1

        elif analysis_result.get("type") == "directory":
            metrics.update(
                {
                    "files_analyzed": analysis_result.get("files_analyzed", 0),
                    "total_vulnerabilities": analysis_result.get(
                        "total_vulnerabilities", 0
                    ),
                    "risk_score": analysis_result.get("risk_score", 0),
                }
            )

            # Add severity breakdown
            for severity, count in analysis_result.get(
                "vulnerabilities_by_severity", {}
            ).items():
                metrics[f"severity_{severity}"] = count

        return metrics

    def compare_results(
        self, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two security analysis results."""
        comparison = {
            "risk_change": 0,
            "vulnerability_changes": {},
            "new_vulnerabilities": [],
            "resolved_vulnerabilities": [],
            "improvements": [],
            "regressions": [],
        }

        # Compare risk scores
        baseline_risk = baseline.get("risk_score", 0)
        current_risk = current.get("risk_score", 0)
        comparison["risk_change"] = current_risk - baseline_risk

        # Compare vulnerability counts
        baseline_metrics = self.extract_metrics(baseline)
        current_metrics = self.extract_metrics(current)

        for key in [
            "severity_critical",
            "severity_high",
            "severity_medium",
            "severity_low",
        ]:
            baseline_count = baseline_metrics.get(key, 0)
            current_count = current_metrics.get(key, 0)

            if baseline_count != current_count:
                severity = key.replace("severity_", "")
                comparison["vulnerability_changes"][severity] = {
                    "baseline": baseline_count,
                    "current": current_count,
                    "change": current_count - baseline_count,
                }

        # Determine improvements vs regressions
        if comparison["risk_change"] < 0:
            comparison["improvements"].append(
                f"Risk score improved by {abs(comparison['risk_change']):.2f} points"
            )
        elif comparison["risk_change"] > 0:
            comparison["regressions"].append(
                f"Risk score increased by {comparison['risk_change']:.2f} points"
            )

        total_baseline = baseline_metrics.get("total_vulnerabilities", 0)
        total_current = current_metrics.get("total_vulnerabilities", 0)

        if total_current < total_baseline:
            comparison["improvements"].append(
                f"Reduced vulnerabilities from {total_baseline} to {total_current}"
            )
        elif total_current > total_baseline:
            comparison["regressions"].append(
                f"Vulnerabilities increased from {total_baseline} to {total_current}"
            )

        return comparison
