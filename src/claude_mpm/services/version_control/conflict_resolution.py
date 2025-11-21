from pathlib import Path

"""
Conflict Resolution Manager - Basic conflict resolution for Version Control Agent.

This module provides conflict resolution management including:
1. Conflict detection and analysis
2. Automatic resolution strategies
3. Manual resolution guidance
4. Conflict prevention
5. Resolution validation
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConflictType(Enum):
    """Types of merge conflicts."""

    CONTENT = "content"
    BINARY = "binary"
    DELETE_MODIFY = "delete_modify"
    ADD_ADD = "add_add"
    RENAME_RENAME = "rename_rename"
    SUBMODULE = "submodule"


class ResolutionStrategy(Enum):
    """Strategies for conflict resolution."""

    MANUAL = "manual"
    OURS = "ours"
    THEIRS = "theirs"
    AUTO_MERGE = "auto_merge"
    SMART_MERGE = "smart_merge"


@dataclass
class ConflictMarker:
    """Represents a conflict marker in a file."""

    start_line: int
    conflict_marker: int
    end_line: int
    ours_content: List[str]
    theirs_content: List[str]
    base_content: Optional[List[str]] = None


@dataclass
class FileConflict:
    """Represents a conflict in a single file."""

    file_path: str
    conflict_type: ConflictType
    markers: List[ConflictMarker] = field(default_factory=list)
    our_version: Optional[str] = None
    their_version: Optional[str] = None
    base_version: Optional[str] = None
    binary_conflict: bool = False
    resolution_suggestion: Optional[str] = None
    auto_resolvable: bool = False


@dataclass
class ConflictResolution:
    """Represents a conflict resolution."""

    file_path: str
    strategy: ResolutionStrategy
    resolved_content: Optional[str] = None
    success: bool = False
    message: str = ""
    manual_intervention_required: bool = False
    backup_created: bool = False


@dataclass
class ConflictAnalysis:
    """Analysis of merge conflicts."""

    total_conflicts: int
    conflicted_files: List[str]
    file_conflicts: List[FileConflict]
    auto_resolvable_count: int
    manual_resolution_count: int
    conflict_severity: str  # low, medium, high
    resolution_complexity: str  # simple, moderate, complex
    estimated_resolution_time: int  # minutes


class ConflictResolutionManager:
    """
    Manages conflict resolution for the Version Control Agent.

    Provides conflict detection, analysis, and resolution capabilities
    with both automatic and manual resolution strategies.
    """

    def __init__(self, project_root: str, logger: logging.Logger):
        """
        Initialize Conflict Resolution Manager.

        Args:
            project_root: Root directory of the project
            logger: Logger instance
        """
        self.project_root = Path(project_root)
        self.logger = logger

        # Conflict markers
        self.conflict_markers = {
            "start": r"^<{7} ",
            "separator": r"^={7}$",
            "end": r"^>{7} ",
        }

        # Auto-resolution patterns
        self.auto_resolution_patterns = {
            "whitespace_only": r"^\s*$",
            "comment_only": r"^\s*[#//]",
            "import_statement": r"^\s*(import|from|#include)",
            "log_statement": r"(console\.log|print\(|logger\.|log\.)",
        }

        # File types that can be auto-resolved
        self.auto_resolvable_extensions = {
            ".md",
            ".txt",
            ".json",
            ".yml",
            ".yaml",
            ".xml",
        }

        # Binary file extensions
        self.binary_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
        }

    def detect_conflicts(self) -> ConflictAnalysis:
        """
        Detect merge conflicts in the repository.

        Returns:
            ConflictAnalysis with detailed conflict information
        """
        try:
            # Get list of conflicted files from git status
            conflicted_files = self._get_conflicted_files()

            if not conflicted_files:
                return ConflictAnalysis(
                    total_conflicts=0,
                    conflicted_files=[],
                    file_conflicts=[],
                    auto_resolvable_count=0,
                    manual_resolution_count=0,
                    conflict_severity="none",
                    resolution_complexity="none",
                    estimated_resolution_time=0,
                )

            # Analyze each conflicted file
            file_conflicts = []
            auto_resolvable_count = 0

            for file_path in conflicted_files:
                conflict = self._analyze_file_conflict(file_path)
                file_conflicts.append(conflict)

                if conflict.auto_resolvable:
                    auto_resolvable_count += 1

            # Calculate analysis metrics
            total_conflicts = len(file_conflicts)
            manual_resolution_count = total_conflicts - auto_resolvable_count

            # Determine severity and complexity
            severity = self._calculate_severity(file_conflicts)
            complexity = self._calculate_complexity(file_conflicts)
            estimated_time = self._estimate_resolution_time(file_conflicts)

            return ConflictAnalysis(
                total_conflicts=total_conflicts,
                conflicted_files=conflicted_files,
                file_conflicts=file_conflicts,
                auto_resolvable_count=auto_resolvable_count,
                manual_resolution_count=manual_resolution_count,
                conflict_severity=severity,
                resolution_complexity=complexity,
                estimated_resolution_time=estimated_time,
            )

        except Exception as e:
            self.logger.error(f"Error detecting conflicts: {e}")
            return ConflictAnalysis(
                total_conflicts=0,
                conflicted_files=[],
                file_conflicts=[],
                auto_resolvable_count=0,
                manual_resolution_count=0,
                conflict_severity="unknown",
                resolution_complexity="unknown",
                estimated_resolution_time=0,
            )

    def _get_conflicted_files(self) -> List[str]:
        """Get list of files with merge conflicts."""
        import subprocess

        try:
            # Use git status to find conflicted files
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            conflicted_files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip() and (line.startswith(("UU", "AA", "DD"))):
                    # Extract filename
                    filename = line[3:].strip()
                    conflicted_files.append(filename)

            return conflicted_files

        except subprocess.CalledProcessError:
            return []
        except Exception as e:
            self.logger.error(f"Error getting conflicted files: {e}")
            return []

    def _analyze_file_conflict(self, file_path: str) -> FileConflict:
        """Analyze conflict in a single file."""
        full_path = self.project_root / file_path

        # Check if file is binary
        if self._is_binary_file(full_path):
            return FileConflict(
                file_path=file_path,
                conflict_type=ConflictType.BINARY,
                binary_conflict=True,
                auto_resolvable=False,
                resolution_suggestion="Manual resolution required for binary file",
            )

        try:
            with Path(full_path).open(
                encoding="utf-8",
            ) as f:
                content = f.read()

            # Parse conflict markers
            markers = self._parse_conflict_markers(content)

            if not markers:
                # No conflict markers, might be add/add or delete/modify conflict
                conflict_type = self._determine_conflict_type(file_path)
                return FileConflict(
                    file_path=file_path,
                    conflict_type=conflict_type,
                    auto_resolvable=False,
                    resolution_suggestion="Check git status for conflict details",
                )

            # Determine if auto-resolvable
            auto_resolvable = self._is_auto_resolvable(file_path, markers)

            # Generate resolution suggestion
            suggestion = self._generate_resolution_suggestion(file_path, markers)

            return FileConflict(
                file_path=file_path,
                conflict_type=ConflictType.CONTENT,
                markers=markers,
                auto_resolvable=auto_resolvable,
                resolution_suggestion=suggestion,
            )

        except Exception as e:
            self.logger.error(f"Error analyzing conflict in {file_path}: {e}")
            return FileConflict(
                file_path=file_path,
                conflict_type=ConflictType.CONTENT,
                auto_resolvable=False,
                resolution_suggestion=f"Error analyzing file: {e}",
            )

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        # Check extension
        if file_path.suffix.lower() in self.binary_extensions:
            return True

        # Check content (simple heuristic)
        try:
            with file_path.open("rb") as f:
                chunk = f.read(1024)
                if b"\0" in chunk:
                    return True
        except Exception:
            pass

        return False

    def _parse_conflict_markers(self, content: str) -> List[ConflictMarker]:
        """Parse conflict markers from file content."""
        lines = content.split("\n")
        markers = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Look for conflict start marker
            if re.match(self.conflict_markers["start"], line):
                start_line = i
                ours_content = []
                theirs_content = []
                conflict_marker = -1
                end_line = -1

                # Find separator and end markers
                i += 1
                while i < len(lines):
                    current_line = lines[i]

                    if re.match(self.conflict_markers["separator"], current_line):
                        conflict_marker = i
                    elif re.match(self.conflict_markers["end"], current_line):
                        end_line = i
                        break
                    elif conflict_marker == -1:
                        # We're in the "ours" section
                        ours_content.append(current_line)
                    else:
                        # We're in the "theirs" section
                        theirs_content.append(current_line)

                    i += 1

                if conflict_marker != -1 and end_line != -1:
                    markers.append(
                        ConflictMarker(
                            start_line=start_line,
                            conflict_marker=conflict_marker,
                            end_line=end_line,
                            ours_content=ours_content,
                            theirs_content=theirs_content,
                        )
                    )

            i += 1

        return markers

    def _determine_conflict_type(self, file_path: str) -> ConflictType:
        """Determine the type of conflict for a file."""
        # This would involve checking git status more carefully
        # For now, default to content conflict
        return ConflictType.CONTENT

    def _is_auto_resolvable(
        self, file_path: str, markers: List[ConflictMarker]
    ) -> bool:
        """Determine if conflict can be automatically resolved."""
        file_ext = Path(file_path).suffix.lower()

        # Check if file type is auto-resolvable
        if file_ext not in self.auto_resolvable_extensions:
            return False

        # Check if all conflicts are simple
        return all(self._is_simple_conflict(marker) for marker in markers)

    def _is_simple_conflict(self, marker: ConflictMarker) -> bool:
        """Check if a conflict marker represents a simple conflict."""
        ours_lines = marker.ours_content
        theirs_lines = marker.theirs_content

        # Check if one side is empty (addition vs no-change)
        if not ours_lines or not theirs_lines:
            return True

        # Check if differences are only whitespace
        if self._only_whitespace_differences(ours_lines, theirs_lines):
            return True

        # Check if differences are only comments
        if self._only_comment_differences(ours_lines, theirs_lines):
            return True

        # Check if differences are only imports
        return bool(self._only_import_differences(ours_lines, theirs_lines))

    def _only_whitespace_differences(self, ours: List[str], theirs: List[str]) -> bool:
        """Check if differences are only whitespace."""
        ours_stripped = [line.strip() for line in ours]
        theirs_stripped = [line.strip() for line in theirs]
        return ours_stripped == theirs_stripped

    def _only_comment_differences(self, ours: List[str], theirs: List[str]) -> bool:
        """Check if differences are only in comments."""
        # This is a simplified check
        for line in ours + theirs:
            stripped = line.strip()
            if stripped and not (stripped.startswith(("#", "//"))):
                return False
        return True

    def _only_import_differences(self, ours: List[str], theirs: List[str]) -> bool:
        """Check if differences are only in import statements."""
        import_pattern = re.compile(r"^\s*(import|from|#include)")

        for line in ours + theirs:
            stripped = line.strip()
            if stripped and not import_pattern.match(line):
                return False
        return True

    def _generate_resolution_suggestion(
        self, file_path: str, markers: List[ConflictMarker]
    ) -> str:
        """Generate resolution suggestion for a file."""
        if not markers:
            return "No conflict markers found"

        suggestions = []

        for i, marker in enumerate(markers):
            if not marker.ours_content and marker.theirs_content:
                suggestions.append(
                    f"Conflict {i + 1}: Accept incoming changes (theirs)"
                )
            elif marker.ours_content and not marker.theirs_content:
                suggestions.append(f"Conflict {i + 1}: Keep current changes (ours)")
            elif self._only_whitespace_differences(
                marker.ours_content, marker.theirs_content
            ):
                suggestions.append(
                    f"Conflict {i + 1}: Whitespace differences only - can auto-resolve"
                )
            else:
                suggestions.append(f"Conflict {i + 1}: Manual merge required")

        return "; ".join(suggestions)

    def _calculate_severity(self, file_conflicts: List[FileConflict]) -> str:
        """Calculate conflict severity."""
        if not file_conflicts:
            return "none"

        binary_conflicts = sum(1 for fc in file_conflicts if fc.binary_conflict)
        total_markers = sum(len(fc.markers) for fc in file_conflicts)
        auto_resolvable = sum(1 for fc in file_conflicts if fc.auto_resolvable)

        # High severity: binary conflicts or many complex conflicts
        if binary_conflicts > 0 or (
            total_markers > 10 and auto_resolvable < len(file_conflicts) * 0.5
        ):
            return "high"

        # Medium severity: some conflicts require manual resolution
        if total_markers > 5 or auto_resolvable < len(file_conflicts) * 0.8:
            return "medium"

        # Low severity: mostly auto-resolvable
        return "low"

    def _calculate_complexity(self, file_conflicts: List[FileConflict]) -> str:
        """Calculate resolution complexity."""
        if not file_conflicts:
            return "none"

        total_conflicts = len(file_conflicts)
        auto_resolvable = sum(1 for fc in file_conflicts if fc.auto_resolvable)
        auto_ratio = auto_resolvable / total_conflicts

        if auto_ratio > 0.8:
            return "simple"
        if auto_ratio > 0.5:
            return "moderate"
        return "complex"

    def _estimate_resolution_time(self, file_conflicts: List[FileConflict]) -> int:
        """Estimate resolution time in minutes."""
        if not file_conflicts:
            return 0

        total_time = 0

        for conflict in file_conflicts:
            if conflict.auto_resolvable:
                total_time += 1  # 1 minute for auto-resolution
            elif conflict.binary_conflict:
                total_time += 15  # 15 minutes for binary conflicts
            else:
                # Time based on number of conflict markers
                markers_count = len(conflict.markers)
                total_time += min(5 + markers_count * 2, 30)  # 5-30 minutes per file

        return total_time

    def resolve_conflicts_automatically(
        self,
        file_conflicts: List[FileConflict],
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO_MERGE,
    ) -> List[ConflictResolution]:
        """
        Automatically resolve conflicts where possible.

        Args:
            file_conflicts: List of file conflicts to resolve
            strategy: Resolution strategy to use

        Returns:
            List of resolution results
        """
        resolutions = []

        for conflict in file_conflicts:
            if not conflict.auto_resolvable:
                resolutions.append(
                    ConflictResolution(
                        file_path=conflict.file_path,
                        strategy=ResolutionStrategy.MANUAL,
                        success=False,
                        message="Requires manual resolution",
                        manual_intervention_required=True,
                    )
                )
                continue

            try:
                resolution = self._resolve_file_conflict(conflict, strategy)
                resolutions.append(resolution)

            except Exception as e:
                self.logger.error(
                    f"Error resolving conflict in {conflict.file_path}: {e}"
                )
                resolutions.append(
                    ConflictResolution(
                        file_path=conflict.file_path,
                        strategy=strategy,
                        success=False,
                        message=f"Auto-resolution failed: {e}",
                        manual_intervention_required=True,
                    )
                )

        return resolutions

    def _resolve_file_conflict(
        self, conflict: FileConflict, strategy: ResolutionStrategy
    ) -> ConflictResolution:
        """Resolve conflict in a single file."""
        file_path = self.project_root / conflict.file_path

        # Create backup
        backup_created = self._create_backup(file_path)

        try:
            # Read current content
            with Path(file_path).open(
                encoding="utf-8",
            ) as f:
                content = f.read()

            # Apply resolution strategy
            resolved_content = self._apply_resolution_strategy(
                content, conflict.markers, strategy
            )

            # Write resolved content
            with file_path.open("w", encoding="utf-8") as f:
                f.write(resolved_content)

            return ConflictResolution(
                file_path=conflict.file_path,
                strategy=strategy,
                resolved_content=resolved_content,
                success=True,
                message="Successfully auto-resolved",
                backup_created=backup_created,
            )

        except Exception as e:
            return ConflictResolution(
                file_path=conflict.file_path,
                strategy=strategy,
                success=False,
                message=f"Resolution failed: {e}",
                manual_intervention_required=True,
                backup_created=backup_created,
            )

    def _create_backup(self, file_path: Path) -> bool:
        """Create backup of file before resolution."""
        try:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.conflict_backup")
            backup_path.write_text(file_path.read_text())
            return True
        except Exception as e:
            self.logger.warning(f"Could not create backup for {file_path}: {e}")
            return False

    def _apply_resolution_strategy(
        self, content: str, markers: List[ConflictMarker], strategy: ResolutionStrategy
    ) -> str:
        """Apply resolution strategy to content."""
        lines = content.split("\n")

        # Process markers in reverse order to preserve line numbers
        for marker in reversed(markers):
            if strategy == ResolutionStrategy.OURS:
                # Keep our version
                replacement = marker.ours_content
            elif strategy == ResolutionStrategy.THEIRS:
                # Keep their version
                replacement = marker.theirs_content
            elif strategy == ResolutionStrategy.AUTO_MERGE:
                # Smart merge
                replacement = self._smart_merge(marker)
            else:
                # Default to ours
                replacement = marker.ours_content

            # Replace the conflict section
            lines[marker.start_line : marker.end_line + 1] = replacement

        return "\n".join(lines)

    def _smart_merge(self, marker: ConflictMarker) -> List[str]:
        """Perform smart merge of conflict marker."""
        ours = marker.ours_content
        theirs = marker.theirs_content

        # If one side is empty, use the other
        if not ours:
            return theirs
        if not theirs:
            return ours

        # If only whitespace differences, use ours but with their spacing
        if self._only_whitespace_differences(ours, theirs):
            return theirs  # Keep their formatting

        # If only comment differences, merge both
        if self._only_comment_differences(ours, theirs):
            return ours + theirs

        # If only import differences, merge and sort
        if self._only_import_differences(ours, theirs):
            combined = list(set(ours + theirs))
            return sorted(combined)

        # Default: keep ours
        return ours

    def generate_resolution_report(self, analysis: ConflictAnalysis) -> str:
        """Generate a human-readable conflict resolution report."""
        if analysis.total_conflicts == 0:
            return "No merge conflicts detected."

        report_lines = [
            "Merge Conflict Analysis Report",
            "=" * 40,
            "",
            f"Total conflicts: {analysis.total_conflicts}",
            f"Conflicted files: {len(analysis.conflicted_files)}",
            f"Auto-resolvable: {analysis.auto_resolvable_count}",
            f"Manual resolution required: {analysis.manual_resolution_count}",
            f"Severity: {analysis.conflict_severity}",
            f"Complexity: {analysis.resolution_complexity}",
            f"Estimated resolution time: {analysis.estimated_resolution_time} minutes",
            "",
            "Conflicted Files:",
            "-" * 20,
        ]

        for conflict in analysis.file_conflicts:
            report_lines.append(f"• {conflict.file_path}")
            report_lines.append(f"  Type: {conflict.conflict_type.value}")
            if conflict.auto_resolvable:
                report_lines.append("  Status: Auto-resolvable")
            else:
                report_lines.append("  Status: Manual resolution required")

            if conflict.resolution_suggestion:
                report_lines.append(f"  Suggestion: {conflict.resolution_suggestion}")

            report_lines.append("")

        return "\n".join(report_lines)

    def get_resolution_guidance(self, file_path: str) -> Dict[str, Any]:
        """Get detailed resolution guidance for a specific file."""
        full_path = self.project_root / file_path

        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            conflict = self._analyze_file_conflict(file_path)

            guidance = {
                "file_path": file_path,
                "conflict_type": conflict.conflict_type.value,
                "auto_resolvable": conflict.auto_resolvable,
                "resolution_suggestion": conflict.resolution_suggestion,
                "markers": [],
            }

            for i, marker in enumerate(conflict.markers):
                marker_info = {
                    "conflict_number": i + 1,
                    "lines": f"{marker.start_line + 1}-{marker.end_line + 1}",
                    "ours_lines": len(marker.ours_content),
                    "theirs_lines": len(marker.theirs_content),
                    "preview": {
                        "ours": marker.ours_content[:3],  # First 3 lines
                        "theirs": marker.theirs_content[:3],
                    },
                }
                guidance["markers"].append(marker_info)

            return guidance

        except Exception as e:
            return {"error": f"Error analyzing file: {e}"}
