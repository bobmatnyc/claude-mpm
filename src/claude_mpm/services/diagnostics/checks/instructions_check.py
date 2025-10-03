"""
Check for duplicate or conflicting CLAUDE.md and instruction files.

WHY: Detect duplicate content, conflicting directives, and improperly placed
instruction files that could cause confusion in agent behavior.
"""

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict

from ..models import DiagnosticResult, DiagnosticStatus
from .base_check import BaseDiagnosticCheck


class InstructionsCheck(BaseDiagnosticCheck):
    """Check for duplicate, conflicting, or misplaced instruction files."""

    # Known instruction file patterns
    INSTRUCTION_FILES = {
        "CLAUDE.md": "Claude Code instructions (should be in project root only)",
        "INSTRUCTIONS.md": "MPM agent customization",
        "BASE_PM.md": "Base PM framework requirements",
    }

    # Patterns that indicate potential conflicts
    CONFLICT_PATTERNS = [
        (r"(?i)you\s+are\s+.*pm", "PM role definition"),
        (r"(?i)delegation\s+rules?", "Delegation rules"),
        (r"(?i)agent\s+selection", "Agent selection logic"),
        (r"(?i)framework\s+behavior", "Framework behavior"),
        (r"(?i)command\s+interception", "Command interception"),
        (r"(?i)memory\s+system", "Memory system configuration"),
        (r"(?i)response\s+format", "Response formatting"),
    ]

    @property
    def name(self) -> str:
        return "instructions_check"

    @property
    def category(self) -> str:
        return "Instructions"

    def run(self) -> DiagnosticResult:
        """Run instructions file diagnostics."""
        try:
            sub_results = []
            details = {}

            # Find all instruction files
            instruction_files = self._find_instruction_files()
            details["found_files"] = {
                str(path): file_type for path, file_type in instruction_files.items()
            }

            # Check for misplaced CLAUDE.md files
            claude_result = self._check_claude_md_placement(instruction_files)
            sub_results.append(claude_result)

            # Check for duplicate content
            duplicate_result = self._check_duplicates(instruction_files)
            sub_results.append(duplicate_result)

            # Check for conflicting directives
            conflict_result = self._check_conflicts(instruction_files)
            sub_results.append(conflict_result)

            # Check for overlapping agent definitions
            agent_result = self._check_agent_definitions(instruction_files)
            sub_results.append(agent_result)

            # Check proper separation of concerns
            separation_result = self._check_separation_of_concerns(instruction_files)
            sub_results.append(separation_result)

            # Determine overall status
            if any(r.status == DiagnosticStatus.ERROR for r in sub_results):
                status = DiagnosticStatus.ERROR
                message = "Found critical issues with instruction files"
            elif any(r.status == DiagnosticStatus.WARNING for r in sub_results):
                status = DiagnosticStatus.WARNING
                message = "Found minor issues with instruction files"
            else:
                status = DiagnosticStatus.OK
                message = "Instruction files are properly configured"

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
                status=DiagnosticStatus.ERROR,
                message=f"Instructions check failed: {e!s}",
                details={"error": str(e)},
            )

    def _find_instruction_files(self) -> Dict[Path, str]:
        """Find all instruction files in the project and user directories."""
        found_files = {}

        # Search locations
        search_paths = [
            Path.cwd(),  # Current project
            Path.home() / ".claude-mpm",  # User directory
            Path.home() / ".claude",  # Alternative user directory
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            for pattern, file_type in self.INSTRUCTION_FILES.items():
                # Use rglob for recursive search
                for file_path in base_path.rglob(pattern):
                    # Skip node_modules and virtual environments
                    if any(
                        part in file_path.parts
                        for part in [
                            "node_modules",
                            "venv",
                            ".venv",
                            "__pycache__",
                            ".git",
                        ]
                    ):
                        continue
                    found_files[file_path] = file_type

        return found_files

    def _check_claude_md_placement(self, files: Dict[Path, str]) -> DiagnosticResult:
        """Check that CLAUDE.md files are properly placed."""
        claude_files = [
            path for path, file_type in files.items() if path.name == "CLAUDE.md"
        ]

        if not claude_files:
            return DiagnosticResult(
                category="CLAUDE.md Placement",
                status=DiagnosticStatus.OK,
                message="No CLAUDE.md files found",
                details={},
            )

        issues = []
        project_root = Path.cwd()

        for path in claude_files:
            # CLAUDE.md should only be in project root
            if path.parent != project_root:
                rel_path = (
                    path.relative_to(project_root)
                    if project_root in path.parents or path.parent == project_root
                    else path
                )
                issues.append(
                    f"CLAUDE.md found in non-root location: {rel_path}\n"
                    f"  → Should be in project root only for Claude Code"
                )

        if issues:
            return DiagnosticResult(
                category="CLAUDE.md Placement",
                status=DiagnosticStatus.WARNING,
                message=f"Found {len(issues)} misplaced CLAUDE.md file(s)",
                details={"issues": issues},
                fix_description=(
                    "CLAUDE.md should only exist in the project root directory. "
                    "Move or remove misplaced files."
                ),
            )

        return DiagnosticResult(
            category="CLAUDE.md Placement",
            status=DiagnosticStatus.OK,
            message="CLAUDE.md properly placed in project root",
            details={"count": len(claude_files)},
        )

    def _check_duplicates(self, files: Dict[Path, str]) -> DiagnosticResult:
        """Check for duplicate content between instruction files."""
        if len(files) < 2:
            return DiagnosticResult(
                category="Duplicate Content",
                status=DiagnosticStatus.OK,
                message="No duplicate content detected",
                details={},
            )

        # Calculate content hashes
        content_snippets = defaultdict(list)

        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
                # Hash significant blocks (paragraphs)
                paragraphs = re.split(r"\n\s*\n", content)
                for para in paragraphs:
                    para = para.strip()
                    if len(para) > 50:  # Skip short snippets
                        hash_val = hashlib.md5(para.encode()).hexdigest()
                        content_snippets[hash_val].append((path, para[:100]))
            except Exception:
                continue

        # Find duplicates
        duplicates = []
        for hash_val, occurrences in content_snippets.items():
            if len(occurrences) > 1:
                files_str = ", ".join(str(path) for path, _ in occurrences)
                snippet = occurrences[0][1]
                duplicates.append(
                    f"Duplicate content found in: {files_str}\n"
                    f"  Snippet: {snippet}..."
                )

        if duplicates:
            return DiagnosticResult(
                category="Duplicate Content",
                status=DiagnosticStatus.WARNING,
                message=f"Found {len(duplicates)} duplicate content block(s)",
                details={"duplicates": duplicates[:5]},  # Limit to first 5
                fix_description=(
                    "Remove duplicate content between files. "
                    "CLAUDE.md should contain Claude Code instructions, "
                    "INSTRUCTIONS.md should contain MPM-specific customization."
                ),
            )

        return DiagnosticResult(
            category="Duplicate Content",
            status=DiagnosticStatus.OK,
            message="No significant duplicate content found",
            details={},
        )

    def _check_conflicts(self, files: Dict[Path, str]) -> DiagnosticResult:
        """Check for conflicting directives between instruction files."""
        conflicts = []
        pattern_occurrences = defaultdict(list)

        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
                for pattern, description in self.CONFLICT_PATTERNS:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    if matches:
                        pattern_occurrences[description].append(
                            (path, len(matches), matches[0][:100])
                        )
            except Exception:
                continue

        # Find patterns that appear in multiple files
        for description, occurrences in pattern_occurrences.items():
            if len(occurrences) > 1:
                files_info = []
                for path, count, _snippet in occurrences:
                    rel_path = (
                        path.relative_to(Path.cwd())
                        if Path.cwd() in path.parents or path.parent == Path.cwd()
                        else path
                    )
                    files_info.append(f"{rel_path} ({count} occurrence(s))")

                conflicts.append(
                    f"Potential conflict for '{description}':\n"
                    f"  Found in: {', '.join(files_info)}"
                )

        if conflicts:
            return DiagnosticResult(
                category="Conflicting Directives",
                status=DiagnosticStatus.ERROR,
                message=f"Found {len(conflicts)} potential conflict(s)",
                details={"conflicts": conflicts},
                fix_description=(
                    "Review and consolidate conflicting directives. "
                    "PM role and behavior should be in INSTRUCTIONS.md, "
                    "Claude Code directives should be in CLAUDE.md."
                ),
            )

        return DiagnosticResult(
            category="Conflicting Directives",
            status=DiagnosticStatus.OK,
            message="No conflicting directives detected",
            details={},
        )

    def _check_agent_definitions(self, files: Dict[Path, str]) -> DiagnosticResult:
        """Check for overlapping or duplicate agent definitions."""
        agent_definitions = defaultdict(list)
        agent_pattern = r"(?:agent|Agent)\s+(\w+).*?(?:specializes?|expert|handles?)"

        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
                matches = re.findall(agent_pattern, content, re.IGNORECASE)
                for agent_name in matches:
                    agent_definitions[agent_name.lower()].append(path)
            except Exception:
                continue

        # Find agents defined in multiple places
        duplicates = []
        for agent_name, paths in agent_definitions.items():
            if len(paths) > 1:
                files_str = ", ".join(
                    str(
                        path.relative_to(Path.cwd())
                        if Path.cwd() in path.parents or path.parent == Path.cwd()
                        else path
                    )
                    for path in paths
                )
                duplicates.append(
                    f"Agent '{agent_name}' defined in multiple files: {files_str}"
                )

        if duplicates:
            return DiagnosticResult(
                category="Agent Definitions",
                status=DiagnosticStatus.WARNING,
                message=f"Found {len(duplicates)} duplicate agent definition(s)",
                details={"duplicates": duplicates},
                fix_description=(
                    "Consolidate agent definitions in INSTRUCTIONS.md. "
                    "Each agent should be defined only once."
                ),
            )

        return DiagnosticResult(
            category="Agent Definitions",
            status=DiagnosticStatus.OK,
            message="Agent definitions are unique",
            details={"total_agents": len(agent_definitions)},
        )

    def _check_separation_of_concerns(self, files: Dict[Path, str]) -> DiagnosticResult:
        """Check that instruction files follow proper separation of concerns."""
        issues = []

        # Check for MPM-specific content in CLAUDE.md
        claude_files = [path for path in files if path.name == "CLAUDE.md"]
        for path in claude_files:
            try:
                content = path.read_text(encoding="utf-8")
                # Check for MPM-specific patterns
                mpm_patterns = [
                    r"(?i)multi-agent",
                    r"(?i)delegation",
                    r"(?i)agent\s+selection",
                    r"(?i)PM\s+role",
                ]
                for pattern in mpm_patterns:
                    if re.search(pattern, content):
                        issues.append(
                            f"CLAUDE.md contains MPM-specific content (pattern: {pattern})\n"
                            f"  → Move to INSTRUCTIONS.md"
                        )
                        break
            except Exception:
                continue

        # Check for Claude Code specific content in INSTRUCTIONS.md
        instructions_files = [path for path in files if path.name == "INSTRUCTIONS.md"]
        for path in instructions_files:
            try:
                content = path.read_text(encoding="utf-8")
                # Check for Claude Code specific patterns
                claude_patterns = [
                    r"(?i)claude\s+code",
                    r"(?i)development\s+guidelines",
                    r"(?i)project\s+structure",
                ]
                for pattern in claude_patterns:
                    if re.search(pattern, content):
                        issues.append(
                            f"INSTRUCTIONS.md contains Claude Code content (pattern: {pattern})\n"
                            f"  → Should focus on MPM customization only"
                        )
                        break
            except Exception:
                continue

        if issues:
            return DiagnosticResult(
                category="Separation of Concerns",
                status=DiagnosticStatus.WARNING,
                message=f"Found {len(issues)} separation of concerns issue(s)",
                details={"issues": issues},
                fix_description=(
                    "Maintain clear separation:\n"
                    "• CLAUDE.md: Claude Code development guidelines\n"
                    "• INSTRUCTIONS.md: MPM agent behavior and customization\n"
                    "• BASE_PM.md: Framework requirements (do not modify)"
                ),
            )

        return DiagnosticResult(
            category="Separation of Concerns",
            status=DiagnosticStatus.OK,
            message="Instruction files properly separated",
            details={},
        )
