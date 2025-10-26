"""
Check filesystem permissions and disk space.

WHY: Verify that claude-mpm has proper filesystem access and sufficient
disk space for operation.
"""

import os
import shutil
from pathlib import Path

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class FilesystemCheck(BaseDiagnosticCheck):
    """Check filesystem health and permissions."""

    @property
    def name(self) -> str:
        return "filesystem_check"

    @property
    def category(self) -> str:
        return "File System"

    def run(self) -> DiagnosticResult:
        """Run filesystem diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check critical directory permissions
            perm_result = self._check_permissions()
            sub_results.append(perm_result)
            details["permissions"] = perm_result.details

            # Check disk space
            space_result = self._check_disk_space()
            sub_results.append(space_result)
            details["disk_space"] = space_result.details

            # Check .claude directory structure
            structure_result = self._check_directory_structure()
            sub_results.append(structure_result)
            details["structure"] = structure_result.details

            # Determine overall status
            if any(r.status == ValidationSeverity.ERROR for r in sub_results):
                status = ValidationSeverity.ERROR
                message = "File system has critical issues"
            elif any(r.status == ValidationSeverity.WARNING for r in sub_results):
                status = ValidationSeverity.WARNING
                message = "File system has minor issues"
            else:
                status = OperationResult.SUCCESS
                message = "File system healthy"

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
                message=f"Filesystem check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_permissions(self) -> DiagnosticResult:
        """Check permissions for critical directories."""
        # Focus on project-level directories as per v4.0.32+ architecture
        project_claude_dir = Path.cwd() / ".claude"
        critical_dirs = [
            project_claude_dir,
            project_claude_dir / "agents",
            project_claude_dir / "responses",
            project_claude_dir / "memory",
            project_claude_dir / "logs",
        ]

        issues = []
        checked = []

        for dir_path in critical_dirs:
            if dir_path.exists():
                checked.append(str(dir_path))

                # Check read permission
                if not os.access(dir_path, os.R_OK):
                    issues.append(f"{dir_path} not readable")

                # Check write permission
                if not os.access(dir_path, os.W_OK):
                    issues.append(f"{dir_path} not writable")

                # Check execute permission (needed to list directory)
                if not os.access(dir_path, os.X_OK):
                    issues.append(f"{dir_path} not accessible")

        if issues:
            return DiagnosticResult(
                category="Permissions",
                status=ValidationSeverity.ERROR,
                message=f"{len(issues)} permission issue(s)",
                details={"issues": issues, "checked": checked},
                fix_command="chmod -R 755 .claude",
                fix_description="Fix project .claude directory permissions",
            )

        if not checked:
            return DiagnosticResult(
                category="Permissions",
                status=ValidationSeverity.WARNING,
                message="No project .claude directories found",
                details={"checked": [], "missing": [str(d) for d in critical_dirs]},
            )

        return DiagnosticResult(
            category="Permissions",
            status=OperationResult.SUCCESS,
            message="All permissions valid",
            details={"checked": checked},
        )

    def _check_disk_space(self) -> DiagnosticResult:
        """Check available disk space."""
        try:
            # Check home directory disk usage
            home_path = Path.home()
            stat = shutil.disk_usage(home_path)

            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            used_percent = (stat.used / stat.total) * 100

            details = {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_percent": round(used_percent, 1),
                "path": str(home_path),
            }

            # Check for low disk space
            if free_gb < 0.1:  # Less than 100MB
                return DiagnosticResult(
                    category="Disk Space",
                    status=ValidationSeverity.ERROR,
                    message=f"Critical: Only {free_gb:.2f}GB free",
                    details=details,
                    fix_description="Free up disk space immediately",
                )
            if free_gb < 1:  # Less than 1GB
                return DiagnosticResult(
                    category="Disk Space",
                    status=ValidationSeverity.WARNING,
                    message=f"Low disk space: {free_gb:.2f}GB free",
                    details=details,
                    fix_description="Consider freeing up disk space",
                )

            return DiagnosticResult(
                category="Disk Space",
                status=OperationResult.SUCCESS,
                message=f"{free_gb:.1f}GB available",
                details=details,
            )

        except Exception as e:
            return DiagnosticResult(
                category="Disk Space",
                status=ValidationSeverity.WARNING,
                message=f"Could not check disk space: {e!s}",
                details={"error": str(e)},
            )

    def _check_directory_structure(self) -> DiagnosticResult:
        """Check project claude directory structure."""
        base_dir = Path.cwd() / ".claude"

        expected_dirs = {
            "agents": "Agent deployment directory",
            "responses": "Response logging directory",
            "memory": "Agent memory storage",
            "logs": "Application logs",
        }

        missing = []
        present = []

        if not base_dir.exists():
            return DiagnosticResult(
                category="Directory Structure",
                status=ValidationSeverity.WARNING,
                message="Project .claude directory missing",
                details={"base_dir": str(base_dir), "exists": False},
                fix_command="mkdir -p .claude/{agents,responses,memory,logs}",
                fix_description="Create project claude directory structure",
            )

        for dir_name, _description in expected_dirs.items():
            dir_path = base_dir / dir_name
            if dir_path.exists():
                present.append(dir_name)
            else:
                missing.append(dir_name)

        if missing:
            return DiagnosticResult(
                category="Directory Structure",
                status=ValidationSeverity.WARNING,
                message=f"Missing {len(missing)} subdirectory(s)",
                details={
                    "base_dir": str(base_dir),
                    "missing": missing,
                    "present": present,
                },
                fix_command=f"mkdir -p .claude/{{{','.join(missing)}}}",
                fix_description="Create missing project directories",
            )

        return DiagnosticResult(
            category="Directory Structure",
            status=OperationResult.SUCCESS,
            message="Directory structure complete",
            details={"base_dir": str(base_dir), "directories": present},
        )
