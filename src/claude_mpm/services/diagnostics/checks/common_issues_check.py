"""
Check for common known issues.

WHY: Proactively detect and report common problems that users encounter,
providing specific fixes for each issue.
"""

import json
from pathlib import Path

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class CommonIssuesCheck(BaseDiagnosticCheck):
    """Check for common known issues."""

    @property
    def name(self) -> str:
        return "common_issues_check"

    @property
    def category(self) -> str:
        return "Common Issues"

    def run(self) -> DiagnosticResult:
        """Run common issues diagnostics."""
        try:
            issues_found = []
            warnings_found = []
            details = {}

            # Check for large .claude.json file
            claude_json_result = self._check_claude_json_size()
            if claude_json_result.has_issues:
                if claude_json_result.status == ValidationSeverity.ERROR:
                    issues_found.append(claude_json_result)
                else:
                    warnings_found.append(claude_json_result)

            # Check for memory leaks
            memory_result = self._check_memory_issues()
            if memory_result.has_issues:
                warnings_found.append(memory_result)

            # Check for stale lock files
            lock_result = self._check_lock_files()
            if lock_result.has_issues:
                warnings_found.append(lock_result)

            # Check for conflicting configurations
            conflict_result = self._check_config_conflicts()
            if conflict_result.has_issues:
                warnings_found.append(conflict_result)

            # Check for outdated cache
            cache_result = self._check_cache_issues()
            if cache_result.has_issues:
                warnings_found.append(cache_result)

            # Aggregate results
            total_issues = len(issues_found) + len(warnings_found)

            if issues_found:
                status = ValidationSeverity.ERROR
                message = f"{len(issues_found)} critical issue(s), {len(warnings_found)} warning(s)"
            elif warnings_found:
                status = ValidationSeverity.WARNING
                message = f"{len(warnings_found)} known issue(s) detected"
            else:
                status = OperationResult.SUCCESS
                message = "No known issues detected"

            details = {
                "total_issues": total_issues,
                "critical": len(issues_found),
                "warnings": len(warnings_found),
            }

            sub_results = issues_found + warnings_found

            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                sub_results=sub_results if self.verbose else [],
            )

        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.ERROR,
                message=f"Common issues check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_claude_json_size(self) -> DiagnosticResult:
        """Check for large .claude.json file causing memory issues."""
        claude_json_path = Path.cwd() / ".claude.json"

        if not claude_json_path.exists():
            return DiagnosticResult(
                category="Large .claude.json",
                status=OperationResult.SUCCESS,
                message="No .claude.json file",
                details={"exists": False},
            )

        try:
            size_bytes = claude_json_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            # Try to count conversations
            conversation_count = 0
            try:
                with claude_json_path.open() as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "conversations" in data:
                        conversation_count = len(data["conversations"])
            except Exception:
                pass

            details = {
                "path": str(claude_json_path),
                "size_mb": round(size_mb, 2),
                "size_bytes": size_bytes,
                "conversations": conversation_count,
            }

            if size_mb > 10:  # Critical: >10MB
                return DiagnosticResult(
                    category="Large .claude.json",
                    status=ValidationSeverity.ERROR,
                    message=f"Critical: .claude.json is {size_mb:.1f}MB (causes memory issues)",
                    details=details,
                    fix_command="claude-mpm cleanup-memory",
                    fix_description="Clean up conversation history to prevent memory issues",
                )
            if size_mb > 1:  # Warning: >1MB
                return DiagnosticResult(
                    category="Large .claude.json",
                    status=ValidationSeverity.WARNING,
                    message=f".claude.json is {size_mb:.1f}MB (may cause memory issues)",
                    details=details,
                    fix_command="claude-mpm cleanup-memory",
                    fix_description="Consider cleaning up old conversations",
                )

            return DiagnosticResult(
                category="Large .claude.json",
                status=OperationResult.SUCCESS,
                message=f".claude.json size acceptable ({size_mb:.2f}MB)",
                details=details,
            )

        except Exception as e:
            return DiagnosticResult(
                category="Large .claude.json",
                status=ValidationSeverity.WARNING,
                message=f"Could not check .claude.json: {e!s}",
                details={"error": str(e)},
            )

    def _check_memory_issues(self) -> DiagnosticResult:
        """Check for potential memory leaks."""
        # Check project-level memory directory first (v4.0.32+ architecture)
        memory_dir = Path.cwd() / ".claude" / "memory"

        if not memory_dir.exists():
            return DiagnosticResult(
                category="Memory Usage",
                status=OperationResult.SUCCESS,
                message="No project memory directory",
                details={"exists": False, "path": str(memory_dir)},
            )

        try:
            # Count and size memory files
            memory_files = list(memory_dir.glob("**/*.json"))
            total_size = sum(f.stat().st_size for f in memory_files)
            size_mb = total_size / (1024 * 1024)

            # Check for old memory files
            import time

            current_time = time.time()
            old_files = []
            for f in memory_files:
                age_days = (current_time - f.stat().st_mtime) / (24 * 3600)
                if age_days > 30:
                    old_files.append(f.name)

            details = {
                "file_count": len(memory_files),
                "total_size_mb": round(size_mb, 2),
                "old_files": len(old_files),
            }

            if size_mb > 100:  # >100MB of memory files
                return DiagnosticResult(
                    category="Memory Usage",
                    status=ValidationSeverity.WARNING,
                    message=f"High memory usage: {size_mb:.1f}MB in {len(memory_files)} files",
                    details=details,
                    fix_command="claude-mpm memory clean --days 30",
                    fix_description="Clean up old project memory files",
                )
            if old_files:
                return DiagnosticResult(
                    category="Memory Usage",
                    status=ValidationSeverity.WARNING,
                    message=f"{len(old_files)} memory file(s) older than 30 days",
                    details=details,
                    fix_command="claude-mpm memory clean --days 30",
                    fix_description="Clean up old project memory files",
                )

            return DiagnosticResult(
                category="Memory Usage",
                status=OperationResult.SUCCESS,
                message=f"Memory usage normal ({size_mb:.1f}MB)",
                details=details,
            )

        except Exception as e:
            return DiagnosticResult(
                category="Memory Usage",
                status=ValidationSeverity.WARNING,
                message=f"Could not check memory: {e!s}",
                details={"error": str(e)},
            )

    def _check_lock_files(self) -> DiagnosticResult:
        """Check for stale lock files."""
        # Prioritize project-level lock files
        lock_locations = [
            Path.cwd() / ".claude" / "*.lock",
            Path.home() / ".claude" / "*.lock",
            Path("/tmp") / "claude-mpm-*.lock",
        ]

        stale_locks = []

        for pattern in lock_locations:
            try:
                for lock_file in pattern.parent.glob(pattern.name):
                    # Check if lock is stale (older than 1 hour)
                    import time

                    age_hours = (time.time() - lock_file.stat().st_mtime) / 3600
                    if age_hours > 1:
                        stale_locks.append(str(lock_file))
            except Exception:
                pass

        if stale_locks:
            return DiagnosticResult(
                category="Lock Files",
                status=ValidationSeverity.WARNING,
                message=f"{len(stale_locks)} stale lock file(s) found",
                details={"stale_locks": stale_locks},
                fix_command=f"rm {' '.join(stale_locks)}",
                fix_description="Remove stale lock files",
            )

        return DiagnosticResult(
            category="Lock Files",
            status=OperationResult.SUCCESS,
            message="No stale lock files",
            details={"stale_locks": []},
        )

    def _check_config_conflicts(self) -> DiagnosticResult:
        """Check for conflicting configurations."""
        conflicts = []

        # Check for both user and project configs with same settings
        project_config = Path.cwd() / ".claude" / "claude-mpm.yaml"
        user_config = Path.home() / ".claude" / "claude-mpm.yaml"

        if user_config.exists() and project_config.exists():
            try:
                import yaml

                with user_config.open() as f:
                    user_data = yaml.safe_load(f) or {}

                with project_config.open() as f:
                    project_data = yaml.safe_load(f) or {}

                # Check for conflicting keys
                for key in user_data:
                    if key in project_data and user_data[key] != project_data[key]:
                        conflicts.append(
                            f"'{key}' defined in both user and project config"
                        )

            except Exception:
                pass

        if conflicts:
            return DiagnosticResult(
                category="Config Conflicts",
                status=ValidationSeverity.WARNING,
                message=f"{len(conflicts)} configuration conflict(s)",
                details={"conflicts": conflicts},
                fix_description="Resolve conflicting configurations",
            )

        return DiagnosticResult(
            category="Config Conflicts",
            status=OperationResult.SUCCESS,
            message="No configuration conflicts",
            details={"conflicts": []},
        )

    def _check_cache_issues(self) -> DiagnosticResult:
        """Check for cache-related issues."""
        cache_dir = Path.home() / ".cache" / "claude-mpm"

        if not cache_dir.exists():
            return DiagnosticResult(
                category="Cache",
                status=OperationResult.SUCCESS,
                message="No cache directory",
                details={"exists": False},
            )

        try:
            # Check cache size
            cache_files = list(cache_dir.glob("**/*"))
            total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
            size_mb = total_size / (1024 * 1024)

            if size_mb > 500:  # >500MB cache
                return DiagnosticResult(
                    category="Cache",
                    status=ValidationSeverity.WARNING,
                    message=f"Large cache: {size_mb:.1f}MB",
                    details={
                        "size_mb": round(size_mb, 2),
                        "file_count": len(cache_files),
                    },
                    fix_command=f"rm -rf {cache_dir}",
                    fix_description="Clear cache to free up space",
                )

            return DiagnosticResult(
                category="Cache",
                status=OperationResult.SUCCESS,
                message=f"Cache size normal ({size_mb:.1f}MB)",
                details={"size_mb": round(size_mb, 2), "file_count": len(cache_files)},
            )

        except Exception as e:
            return DiagnosticResult(
                category="Cache",
                status=ValidationSeverity.WARNING,
                message=f"Could not check cache: {e!s}",
                details={"error": str(e)},
            )
