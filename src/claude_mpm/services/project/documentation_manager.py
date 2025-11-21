"""
Documentation Manager Service for Claude MPM Project Initialization
===================================================================

This service manages CLAUDE.md documentation updates, merging, and intelligent
content organization for the mpm-init command.

Key Features:
- Smart merging of existing CLAUDE.md content with new sections
- Priority-based content organization (🔴🟡🟢⚪)
- Content deduplication and conflict resolution
- Template-based documentation generation
- Version comparison and change tracking

Author: Claude MPM Development Team
Created: 2025-01-26
"""

import difflib
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)
console = Console()


class DocumentationManager:
    """Manages CLAUDE.md documentation updates and organization."""

    # Priority markers
    PRIORITY_MARKERS = {
        "critical": "🔴",
        "important": "🟡",
        "standard": "🟢",
        "optional": "⚪",
    }

    # Section priority order (higher index = higher priority)
    SECTION_PRIORITY = {
        "priority_index": 100,
        "critical_security": 95,
        "critical_business": 90,
        "important_architecture": 80,
        "important_workflow": 75,
        "project_overview": 70,
        "standard_coding": 60,
        "standard_tasks": 55,
        "documentation_links": 40,
        "optional_future": 20,
        "meta_maintenance": 10,
    }

    def __init__(self, project_path: Path):
        """Initialize the documentation manager."""
        self.project_path = project_path
        self.claude_md_path = project_path / "CLAUDE.md"
        self.existing_content = None
        self.content_hash = None
        self._load_existing_content()

    def _load_existing_content(self) -> None:
        """Load existing CLAUDE.md content if it exists."""
        if self.claude_md_path.exists():
            self.existing_content = self.claude_md_path.read_text(encoding="utf-8")
            self.content_hash = hashlib.md5(self.existing_content.encode()).hexdigest()
            logger.info(
                f"Loaded existing CLAUDE.md ({len(self.existing_content)} chars)"
            )

    def has_existing_documentation(self) -> bool:
        """Check if project has existing CLAUDE.md."""
        return self.claude_md_path.exists()

    def analyze_existing_content(self) -> Dict:
        """Analyze existing CLAUDE.md structure and content."""
        if not self.existing_content:
            return {"exists": False}

        analysis = {
            "exists": True,
            "size": len(self.existing_content),
            "lines": self.existing_content.count("\n"),
            "sections": self._extract_sections(self.existing_content),
            "has_priority_index": "🎯 Priority Index" in self.existing_content,
            "has_priority_markers": any(
                marker in self.existing_content
                for marker in self.PRIORITY_MARKERS.values()
            ),
            "last_modified": datetime.fromtimestamp(
                self.claude_md_path.stat().st_mtime
            ).isoformat(),
            "content_hash": self.content_hash,
        }

        # Check for outdated patterns
        analysis["outdated_patterns"] = self._check_outdated_patterns()

        # Extract custom sections
        analysis["custom_sections"] = self._find_custom_sections(analysis["sections"])

        return analysis

    def _extract_sections(self, content: str) -> List[Dict]:
        """Extract section headers and their content from markdown."""
        sections = []
        lines = content.split("\n")

        current_section = None
        current_level = 0
        section_start = 0

        for i, line in enumerate(lines):
            if line.startswith("#"):
                # Save previous section if exists
                if current_section:
                    sections.append(
                        {
                            "title": current_section,
                            "level": current_level,
                            "start_line": section_start,
                            "end_line": i - 1,
                            "content_preview": self._get_content_preview(
                                lines[section_start:i]
                            ),
                        }
                    )

                # Parse new section
                level = len(line.split()[0])
                title = line.lstrip("#").strip()
                current_section = title
                current_level = level
                section_start = i

        # Add last section
        if current_section:
            sections.append(
                {
                    "title": current_section,
                    "level": current_level,
                    "start_line": section_start,
                    "end_line": len(lines) - 1,
                    "content_preview": self._get_content_preview(lines[section_start:]),
                }
            )

        return sections

    def _get_content_preview(self, lines: List[str], max_length: int = 100) -> str:
        """Get a preview of section content."""
        content = " ".join(line.strip() for line in lines[1:6] if line.strip())
        if len(content) > max_length:
            content = content[:max_length] + "..."
        return content

    def _check_outdated_patterns(self) -> List[str]:
        """Check for outdated documentation patterns."""
        patterns = []

        if self.existing_content:
            # Check for old patterns
            if (
                "## Installation" in self.existing_content
                and "pip install" not in self.existing_content
            ):
                patterns.append("Missing installation instructions")

            if "TODO" in self.existing_content or "FIXME" in self.existing_content:
                patterns.append("Contains TODO/FIXME items")

            if not re.search(
                r"Last Updated:|Last Modified:", self.existing_content, re.IGNORECASE
            ):
                patterns.append("Missing update timestamp")

            if "```" not in self.existing_content:
                patterns.append("No code examples")

        return patterns

    def _find_custom_sections(self, sections: List[Dict]) -> List[str]:
        """Find sections that don't match standard template."""
        standard_patterns = [
            r"priority.?index",
            r"project.?overview",
            r"critical",
            r"important",
            r"standard",
            r"optional",
            r"architecture",
            r"workflow",
            r"development",
            r"documentation",
            r"meta",
        ]

        custom = []
        for section in sections:
            title_lower = section["title"].lower()
            if not any(
                re.search(pattern, title_lower) for pattern in standard_patterns
            ):
                custom.append(section["title"])

        return custom

    def merge_with_template(
        self, new_content: str, preserve_custom: bool = True
    ) -> str:
        """Merge existing content with new template content."""
        if not self.existing_content:
            return new_content

        logger.info("Merging existing CLAUDE.md with new content...")

        # Parse both contents into sections
        existing_sections = self._parse_into_sections(self.existing_content)
        new_sections = self._parse_into_sections(new_content)

        # Merge sections intelligently
        merged = self._merge_sections(existing_sections, new_sections, preserve_custom)

        # Reorganize by priority
        merged = self._reorganize_by_priority(merged)

        # Add metadata
        return self._add_metadata(merged)

    def _parse_into_sections(self, content: str) -> Dict[str, str]:
        """Parse markdown content into a dictionary of sections."""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            if line.startswith("#"):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content)

                # Start new section
                current_section = line
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _merge_sections(
        self, existing: Dict[str, str], new: Dict[str, str], preserve_custom: bool
    ) -> Dict[str, str]:
        """Merge existing and new sections intelligently."""
        merged = {}

        # Start with new sections as base
        merged.update(new)

        # Preserve custom sections from existing
        if preserve_custom:
            for section_header, content in existing.items():
                section_key = self._get_section_key(section_header)

                # If it's a custom section, preserve it
                if section_key not in self.SECTION_PRIORITY:
                    merged[section_header] = content
                    logger.info(f"Preserving custom section: {section_header}")

                # If section exists in both, merge content
                elif section_header in new:
                    merged_content = self._merge_section_content(
                        content, new[section_header], section_header
                    )
                    merged[section_header] = merged_content

        return merged

    def _get_section_key(self, header: str) -> str:
        """Extract section key from header for priority mapping."""
        title = header.lstrip("#").strip().lower()

        # Map to known section types
        if "priority" in title and "index" in title:
            return "priority_index"
        if "critical" in title and "security" in title:
            return "critical_security"
        if "critical" in title and "business" in title:
            return "critical_business"
        if "important" in title and "architecture" in title:
            return "important_architecture"
        if "important" in title and "workflow" in title:
            return "important_workflow"
        if "project" in title and "overview" in title:
            return "project_overview"
        if "standard" in title and "coding" in title:
            return "standard_coding"
        if "standard" in title and "tasks" in title:
            return "standard_tasks"
        if "documentation" in title:
            return "documentation_links"
        if "optional" in title or "future" in title:
            return "optional_future"
        if "meta" in title or "maintain" in title:
            return "meta_maintenance"
        return "unknown"

    def _merge_section_content(
        self, existing: str, new: str, section_header: str
    ) -> str:
        """Merge content from existing and new sections."""
        # For critical sections, prefer new content but append unique existing items
        if (
            "critical" in section_header.lower()
            or "important" in section_header.lower()
        ):
            # Extract bullet points from both
            existing_items = self._extract_bullet_points(existing)
            new_items = self._extract_bullet_points(new)

            # Combine unique items
            all_items = new_items.copy()
            for item in existing_items:
                if not self._is_duplicate_item(item, new_items):
                    all_items.append(f"{item} [preserved]")

            # Reconstruct section
            if all_items:
                return "\n".join(["", *all_items, ""])
            return new
        # For other sections, use new as base and append existing
        if existing.strip() and existing.strip() != new.strip():
            return f"{new}\n\n<!-- Preserved from previous version -->\n{existing}"
        return new

    def _extract_bullet_points(self, content: str) -> List[str]:
        """Extract bullet points from content."""
        points = []
        for line in content.split("\n"):
            if line.strip().startswith(("-", "*", "•", "+")):
                points.append(line.strip())
        return points

    def _is_duplicate_item(self, item: str, items: List[str]) -> bool:
        """Check if item is duplicate of any in list."""
        item_clean = re.sub(r"[^a-zA-Z0-9\s]", "", item.lower())
        for existing in items:
            existing_clean = re.sub(r"[^a-zA-Z0-9\s]", "", existing.lower())
            # Use fuzzy matching for similarity
            similarity = difflib.SequenceMatcher(
                None, item_clean, existing_clean
            ).ratio()
            if similarity > 0.8:  # 80% similarity threshold
                return True
        return False

    def _reorganize_by_priority(self, sections: Dict[str, str]) -> str:
        """Reorganize sections by priority order."""
        # Sort sections by priority
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: self.SECTION_PRIORITY.get(
                self._get_section_key(x[0]),
                50,  # Default priority
            ),
            reverse=True,  # Higher priority first
        )

        # Reconstruct document
        result = []
        for header, content in sorted_sections:
            result.append(header)
            result.append(content)

        return "\n".join(result)

    def _add_metadata(self, content: str) -> str:
        """Add metadata to the document."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Check if meta section exists
        if "## 📝 Meta:" not in content and "## Meta:" not in content:
            meta_section = f"""

## 📝 Meta: Maintaining This Document

- **Last Updated**: {timestamp}
- **Update Method**: Claude MPM /mpm-init (intelligent merge)
- **Version Control**: Previous versions archived in `docs/_archive/`
- **Update Frequency**: Update when project requirements change significantly
- **Priority Guidelines**:
  - 🔴 CRITICAL: Security, data handling, breaking changes
  - 🟡 IMPORTANT: Key workflows, architecture decisions
  - 🟢 STANDARD: Common operations, best practices
  - ⚪ OPTIONAL: Nice-to-have features, future ideas
"""
            content += meta_section
        else:
            # Update timestamp in existing meta section
            content = re.sub(
                r"Last Updated[:\s]*[\d\-T:\.]+",
                f"Last Updated: {timestamp}",
                content,
                flags=re.IGNORECASE,
            )

        return content

    def generate_update_report(self, old_content: str, new_content: str) -> Dict:
        """Generate a report of changes between old and new content."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": [],
            "additions": [],
            "deletions": [],
            "statistics": {},
        }

        # Get diff
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="")

        # Analyze changes
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                report["additions"].append(line[1:].strip())
            elif line.startswith("-") and not line.startswith("---"):
                report["deletions"].append(line[1:].strip())

        # Statistics
        report["statistics"] = {
            "old_lines": len(old_lines),
            "new_lines": len(new_lines),
            "lines_added": len(report["additions"]),
            "lines_removed": len(report["deletions"]),
            "net_change": len(new_lines) - len(old_lines),
        }

        # Identify major changes
        old_sections = set(self._extract_section_titles(old_content))
        new_sections = set(self._extract_section_titles(new_content))

        report["sections_added"] = list(new_sections - old_sections)
        report["sections_removed"] = list(old_sections - new_sections)

        return report

    def _extract_section_titles(self, content: str) -> List[str]:
        """Extract section titles from content."""
        titles = []
        for line in content.splitlines():
            if line.startswith("#"):
                titles.append(line.lstrip("#").strip())
        return titles

    def validate_content(self, content: str) -> Tuple[bool, List[str]]:
        """Validate CLAUDE.md content for completeness and correctness."""
        issues = []

        # Check for required sections
        required_sections = [
            "Priority Index",
            "Project Overview",
            "CRITICAL",
            "IMPORTANT",
        ]

        for section in required_sections:
            if section not in content:
                issues.append(f"Missing required section: {section}")

        # Check for priority markers
        has_markers = any(
            marker in content for marker in self.PRIORITY_MARKERS.values()
        )
        if not has_markers:
            issues.append("No priority markers found (🔴🟡🟢⚪)")

        # Check for single-path documentation
        if "one way" not in content.lower() and "single path" not in content.lower():
            issues.append("Missing single-path workflow documentation")

        # Check for examples
        if "```" not in content:
            issues.append("No code examples found")

        # Check length
        if len(content) < 1000:
            issues.append("Documentation seems too brief (< 1000 characters)")

        return len(issues) == 0, issues

    def create_minimal_template(self) -> str:
        """Create a minimal CLAUDE.md template."""
        project_name = self.project_path.name
        return f"""# {project_name} - CLAUDE.md

## 🎯 Priority Index

### 🔴 CRITICAL Instructions
- [Add critical security and data handling rules here]

### 🟡 IMPORTANT Instructions
- [Add key architectural decisions and workflows here]

## 📋 Project Overview

[Brief description of the project's purpose and goals]

## 🔴 CRITICAL: Security & Data Handling

[Critical security requirements and data handling rules]

## 🟡 IMPORTANT: Development Workflow

### ONE Way to Build
```bash
# Add build command
```

### ONE Way to Test
```bash
# Add test command
```

### ONE Way to Deploy
```bash
# Add deploy command
```

## 🟢 STANDARD: Coding Guidelines

[Standard development practices and conventions]

## 📚 Documentation Links

- [Link to additional documentation]

## 📝 Meta: Maintaining This Document

- **Last Updated**: {datetime.now(timezone.utc).isoformat()}
- **Created By**: Claude MPM /mpm-init
- **Update Frequency**: As needed when requirements change
"""
