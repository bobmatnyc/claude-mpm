#!/usr/bin/env python3
"""
Documentation Audit Script for Claude MPM

This script validates documentation compliance with STRUCTURE.md requirements and
provides comprehensive analysis of documentation organization, consistency, and quality.

Purpose:
- Validates documentation structure against STRUCTURE.md requirements
- Checks for duplicate content in agent documentation files
- Verifies naming conventions (UPPER_CASE for major docs, lowercase with hyphens for subdirs)
- Identifies deprecated/legacy references that need updating
- Validates that numbered directories have README.md files
- Checks for broken internal links between documentation files
- Identifies files in wrong directories
- Reports redundant or overlapping documentation

Usage:
    python scripts/audit_documentation.py [options]

    Options:
    --fix         Auto-fix simple issues like naming conventions
    --verbose     Show detailed analysis
    --json        Output results in JSON format
    --strict      Fail on any issues (for CI/CD)
    --help        Show this help message

Examples:
    # Basic audit
    python scripts/audit_documentation.py

    # Detailed analysis with auto-fixes
    python scripts/audit_documentation.py --verbose --fix

    # CI/CD mode with JSON output
    python scripts/audit_documentation.py --json --strict

Author: Claude MPM Documentation Agent
Created: 2025-08-12
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class AuditIssue:
    """Represents a documentation audit issue"""

    category: str
    severity: str  # 'error', 'warning', 'info'
    file_path: str
    line_number: Optional[int]
    message: str
    suggestion: Optional[str] = None
    fixable: bool = False


@dataclass
class AuditSummary:
    """Summary of audit results"""

    total_files_scanned: int
    issues_found: int
    errors: int
    warnings: int
    info: int
    fixable_issues: int
    deployment_ready: bool
    duration_seconds: float


class DocumentationAuditor:
    """Main documentation auditor class"""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        self.verbose = verbose
        self.issues: List[AuditIssue] = []
        self.files_scanned = 0

        # Expected structure from STRUCTURE.md
        self.expected_structure = {
            "docs/": {
                "type": "directory",
                "required_files": [],
                "subdirs": {
                    "archive/": {
                        "type": "directory",
                        "description": "Historical documentation, QA reports",
                    },
                    "assets/": {
                        "type": "directory",
                        "description": "Documentation assets (images, diagrams)",
                    },
                    "dashboard/": {
                        "type": "directory",
                        "description": "Dashboard documentation",
                    },
                    "design/": {
                        "type": "directory",
                        "description": "Design documents and technical specifications",
                    },
                    "developer/": {
                        "type": "directory",
                        "description": "Developer documentation (API, internals, guides)",
                    },
                    "examples/": {
                        "type": "directory",
                        "description": "Usage examples and configurations",
                    },
                    "qa/": {
                        "type": "directory",
                        "description": "QA reports and test documentation",
                    },
                    "user/": {
                        "type": "directory",
                        "description": "User-facing documentation",
                    },
                },
            }
        }

        # Naming conventions
        self.major_doc_pattern = r"^[A-Z][A-Z_]*\.md$"  # UPPER_CASE.md
        self.subdir_pattern = (
            r"^[0-9]+-[a-z][a-z-]*$|^[a-z][a-z-]*$"  # lowercase with hyphens
        )

        # Legacy/deprecated patterns to detect
        self.deprecated_patterns = [
            r"claude-multiagent-pm",
            r"CLAUDE\.md",
            r"\.claude-mpm/agents/templates/",  # Old template location
            r"claude_mpm/agents/templates/",  # System templates referenced incorrectly
            r"legacy_",
            r"_old",
            r"deprecated",
        ]

        # Link patterns
        self.link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        self.internal_link_pattern = r"^\."  # Starts with . (relative)

    def audit(self) -> AuditSummary:
        """Perform comprehensive documentation audit"""
        import time

        start_time = time.time()

        if not self.docs_root.exists():
            self.add_issue(
                "structure",
                "error",
                str(self.docs_root),
                None,
                "Documentation directory does not exist",
                "Create docs/ directory structure",
            )
            return self._generate_summary(time.time() - start_time)

        # Run all audit checks
        self._audit_structure()
        self._audit_naming_conventions()
        self._audit_numbered_directories()
        self._audit_duplicate_content()
        self._audit_deprecated_references()
        self._audit_broken_links()
        self._audit_file_placement()
        self._audit_redundant_content()

        return self._generate_summary(time.time() - start_time)

    def add_issue(
        self,
        category: str,
        severity: str,
        file_path: str,
        line_number: Optional[int],
        message: str,
        suggestion: Optional[str] = None,
        fixable: bool = False,
    ):
        """Add an audit issue"""
        issue = AuditIssue(
            category=category,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            message=message,
            suggestion=suggestion,
            fixable=fixable,
        )
        self.issues.append(issue)

        if self.verbose:
            prefix = f"[{severity.upper()}]"
            location = f"{file_path}"
            if line_number:
                location += f":{line_number}"
            print(f"{prefix} {location}: {message}")
            if suggestion:
                print(f"  → Suggestion: {suggestion}")

    def _audit_structure(self):
        """Audit basic directory structure compliance"""
        if self.verbose:
            print("Auditing directory structure...")

        expected_subdirs = self.expected_structure["docs/"]["subdirs"].keys()
        actual_subdirs = {d.name + "/" for d in self.docs_root.iterdir() if d.is_dir()}

        # Check for missing expected directories
        missing_dirs = set(expected_subdirs) - actual_subdirs
        for missing_dir in missing_dirs:
            self.add_issue(
                "structure",
                "warning",
                f"docs/{missing_dir}",
                None,
                f"Expected directory missing: {missing_dir}",
                f"Create directory docs/{missing_dir}",
                fixable=True,
            )

        # Check for unexpected directories
        unexpected_dirs = actual_subdirs - set(expected_subdirs)
        for unexpected_dir in unexpected_dirs:
            # Skip if it matches numbered directory pattern
            if re.match(r"^[0-9]+-", unexpected_dir.rstrip("/")):
                continue
            self.add_issue(
                "structure",
                "info",
                f"docs/{unexpected_dir}",
                None,
                f"Unexpected directory found: {unexpected_dir}",
                "Review if this directory belongs here per STRUCTURE.md",
            )

    def _audit_naming_conventions(self):
        """Audit naming convention compliance"""
        if self.verbose:
            print("Auditing naming conventions...")

        # Check major documentation files in docs/
        for item in self.docs_root.iterdir():
            if item.is_file() and item.suffix == ".md":
                self.files_scanned += 1
                if not re.match(self.major_doc_pattern, item.name):
                    correct_name = item.name.upper().replace("-", "_")
                    self.add_issue(
                        "naming",
                        "warning",
                        str(item),
                        None,
                        f"File should follow UPPER_CASE naming: {item.name}",
                        f"Rename to {correct_name}",
                        fixable=True,
                    )

        # Check subdirectory naming
        for subdir in self.docs_root.iterdir():
            if subdir.is_dir():
                if not re.match(self.subdir_pattern, subdir.name):
                    self.add_issue(
                        "naming",
                        "warning",
                        str(subdir),
                        None,
                        f"Directory should follow lowercase-with-hyphens naming: {subdir.name}",
                        f"Consider renaming to follow convention",
                    )

    def _audit_numbered_directories(self):
        """Audit that numbered directories have README.md files"""
        if self.verbose:
            print("Auditing numbered directories...")

        def check_numbered_dirs(directory: Path):
            for item in directory.iterdir():
                if item.is_dir():
                    # Check if it's a numbered directory
                    if re.match(r"^[0-9]+-", item.name):
                        readme_path = item / "README.md"
                        if not readme_path.exists():
                            self.add_issue(
                                "structure",
                                "error",
                                str(item),
                                None,
                                f"Numbered directory missing README.md: {item.name}",
                                f"Create {readme_path}",
                                fixable=True,
                            )

                    # Recursively check subdirectories
                    check_numbered_dirs(item)

        check_numbered_dirs(self.docs_root)

    def _audit_duplicate_content(self):
        """Audit for duplicate content, especially in agent documentation"""
        if self.verbose:
            print("Auditing duplicate content...")

        content_hashes: Dict[str, List[str]] = defaultdict(list)
        agent_docs = []

        # Find all markdown files
        for md_file in self.docs_root.rglob("*.md"):
            self.files_scanned += 1
            try:
                content = md_file.read_text(encoding="utf-8")
                # Create hash of normalized content (ignore whitespace differences)
                normalized = re.sub(r"\s+", " ", content.lower().strip())
                content_hash = hashlib.md5(normalized.encode()).hexdigest()
                content_hashes[content_hash].append(str(md_file))

                # Track agent documentation specifically
                if "agent" in md_file.name.lower() or "/agents/" in str(md_file):
                    agent_docs.append(md_file)

            except Exception as e:
                self.add_issue(
                    "content",
                    "warning",
                    str(md_file),
                    None,
                    f"Could not read file for duplicate analysis: {e}",
                )

        # Report duplicates
        for content_hash, file_list in content_hashes.items():
            if len(file_list) > 1:
                self.add_issue(
                    "duplicates",
                    "warning",
                    file_list[0],
                    None,
                    f"Duplicate content found in {len(file_list)} files: {', '.join(file_list)}",
                    "Review and consolidate duplicate content",
                )

        # Check for similar agent documentation
        self._check_agent_doc_similarity(agent_docs)

    def _check_agent_doc_similarity(self, agent_docs: List[Path]):
        """Check for similar content in agent documentation"""
        if len(agent_docs) < 2:
            return

        # Simple similarity check based on common sections
        common_sections = defaultdict(list)

        for doc in agent_docs:
            try:
                content = doc.read_text(encoding="utf-8")
                # Extract headers
                headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
                for header in headers:
                    common_sections[header.lower().strip()].append(str(doc))
            except Exception:
                continue

        # Report sections that appear in many agent docs
        for section, docs in common_sections.items():
            if len(docs) > 3:  # If section appears in more than 3 agent docs
                self.add_issue(
                    "redundancy",
                    "info",
                    docs[0],
                    None,
                    f"Section '{section}' appears in {len(docs)} agent documents",
                    "Consider creating shared documentation for common content",
                )

    def _audit_deprecated_references(self):
        """Audit for deprecated/legacy references"""
        if self.verbose:
            print("Auditing deprecated references...")

        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for pattern in self.deprecated_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.add_issue(
                                "deprecated",
                                "warning",
                                str(md_file),
                                line_num,
                                f"Deprecated reference found: {pattern}",
                                "Update reference to current implementation",
                            )

            except Exception as e:
                self.add_issue(
                    "content",
                    "warning",
                    str(md_file),
                    None,
                    f"Could not read file for deprecated reference analysis: {e}",
                )

    def _audit_broken_links(self):
        """Audit for broken internal links"""
        if self.verbose:
            print("Auditing internal links...")

        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    links = re.findall(self.link_pattern, line)

                    for link_text, link_url in links:
                        # Skip external links
                        if link_url.startswith(("http://", "https://", "mailto:", "#")):
                            continue

                        # Check internal links
                        if (
                            link_url.startswith("./")
                            or link_url.startswith("../")
                            or not link_url.startswith("/")
                        ):
                            target_path = (md_file.parent / link_url).resolve()
                            if not target_path.exists():
                                self.add_issue(
                                    "links",
                                    "error",
                                    str(md_file),
                                    line_num,
                                    f"Broken internal link: {link_url}",
                                    "Fix or remove broken link",
                                )

            except Exception as e:
                self.add_issue(
                    "content",
                    "warning",
                    str(md_file),
                    None,
                    f"Could not read file for link analysis: {e}",
                )

    def _audit_file_placement(self):
        """Audit files for correct directory placement"""
        if self.verbose:
            print("Auditing file placement...")

        # Define placement rules
        placement_rules = {
            r".*qa.*report.*\.md$": ["docs/qa/", "docs/archive/qa-reports/"],
            r".*test.*result.*\.md$": ["docs/archive/test-results/"],
            r".*api.*ref.*\.md$": ["docs/developer/04-api-reference/"],
            r".*user.*guide.*\.md$": ["docs/user/"],
            r".*install.*\.md$": ["docs/user/"],
            r".*setup.*\.md$": ["docs/developer/03-development/"],
            r".*security.*\.md$": ["docs/developer/09-security/"],
            r".*schema.*\.md$": ["docs/developer/10-schemas/"],
        }

        for md_file in self.docs_root.rglob("*.md"):
            file_path = str(md_file.relative_to(self.project_root))

            for pattern, expected_locations in placement_rules.items():
                if re.search(pattern, md_file.name, re.IGNORECASE):
                    # Check if file is in one of the expected locations
                    in_correct_location = any(
                        expected_loc in file_path for expected_loc in expected_locations
                    )

                    if not in_correct_location:
                        self.add_issue(
                            "placement",
                            "warning",
                            file_path,
                            None,
                            f"File may be in wrong location: {md_file.name}",
                            f"Consider moving to: {', '.join(expected_locations)}",
                        )

    def _audit_redundant_content(self):
        """Audit for redundant or overlapping documentation"""
        if self.verbose:
            print("Auditing redundant content...")

        # Track topics by keywords in file names and content
        topics = defaultdict(list)

        for md_file in self.docs_root.rglob("*.md"):
            try:
                # Extract keywords from filename
                filename_keywords = re.findall(r"[a-zA-Z]+", md_file.stem.lower())

                # Extract keywords from content (headers)
                content = md_file.read_text(encoding="utf-8")
                header_keywords = re.findall(r"#+\s+([^\n]+)", content)
                header_keywords = [
                    word.lower()
                    for header in header_keywords
                    for word in re.findall(r"[a-zA-Z]+", header)
                ]

                all_keywords = filename_keywords + header_keywords

                # Group by common keywords
                for keyword in set(all_keywords):
                    if len(keyword) > 3:  # Skip short words
                        topics[keyword].append(str(md_file))

            except Exception:
                continue

        # Report potential redundancy
        for topic, files in topics.items():
            if len(files) > 4:  # If topic appears in more than 4 files
                self.add_issue(
                    "redundancy",
                    "info",
                    files[0],
                    None,
                    f"Topic '{topic}' appears in {len(files)} files",
                    "Review for potential consolidation",
                )

    def fix_issues(self) -> int:
        """Auto-fix fixable issues"""
        fixed_count = 0

        for issue in self.issues:
            if not issue.fixable:
                continue

            try:
                if (
                    issue.category == "structure"
                    and "Create directory" in issue.suggestion
                ):
                    # Create missing directories
                    dir_path = Path(issue.suggestion.split("Create directory ")[1])
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"Fixed: Created directory {dir_path}")
                    fixed_count += 1

                elif issue.category == "structure" and "README.md" in issue.suggestion:
                    # Create missing README.md files
                    readme_path = Path(issue.suggestion.split("Create ")[1])
                    if not readme_path.exists():
                        content = f"# {readme_path.parent.name.replace('-', ' ').title()}\n\nTODO: Add documentation for this section.\n"
                        readme_path.write_text(content, encoding="utf-8")
                        print(f"Fixed: Created {readme_path}")
                        fixed_count += 1

                elif issue.category == "naming" and "Rename to" in issue.suggestion:
                    # Auto-fix naming conventions (conservative approach)
                    old_path = Path(issue.file_path)
                    new_name = issue.suggestion.split("Rename to ")[1]
                    new_path = old_path.parent / new_name

                    if not new_path.exists():
                        old_path.rename(new_path)
                        print(f"Fixed: Renamed {old_path.name} to {new_name}")
                        fixed_count += 1

            except Exception as e:
                print(f"Failed to fix issue in {issue.file_path}: {e}")

        return fixed_count

    def _generate_summary(self, duration: float) -> AuditSummary:
        """Generate audit summary"""
        error_count = sum(1 for issue in self.issues if issue.severity == "error")
        warning_count = sum(1 for issue in self.issues if issue.severity == "warning")
        info_count = sum(1 for issue in self.issues if issue.severity == "info")
        fixable_count = sum(1 for issue in self.issues if issue.fixable)

        # Deployment ready if no errors
        deployment_ready = error_count == 0

        return AuditSummary(
            total_files_scanned=self.files_scanned,
            issues_found=len(self.issues),
            errors=error_count,
            warnings=warning_count,
            info=info_count,
            fixable_issues=fixable_count,
            deployment_ready=deployment_ready,
            duration_seconds=duration,
        )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Audit Claude MPM documentation compliance with STRUCTURE.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix simple issues like naming conventions",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed analysis")
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Fail on any issues (for CI/CD)"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Project root directory (default: auto-detect)",
    )

    args = parser.parse_args()

    # Validate project root
    project_root = args.project_root.resolve()
    if not (project_root / "docs" / "STRUCTURE.md").exists():
        print(f"Error: STRUCTURE.md not found in {project_root}/docs/", file=sys.stderr)
        print(
            "Please run from the project root or specify --project-root",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run audit
    auditor = DocumentationAuditor(project_root, verbose=args.verbose)
    summary = auditor.audit()

    # Auto-fix if requested
    fixed_count = 0
    if args.fix:
        fixed_count = auditor.fix_issues()
        if fixed_count > 0 and args.verbose:
            print(f"\nAuto-fixed {fixed_count} issues.")

    # Output results
    if args.json:
        # JSON output
        output = {
            "summary": asdict(summary),
            "issues": [asdict(issue) for issue in auditor.issues],
            "fixed_count": fixed_count if args.fix else 0,
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("\n" + "=" * 60)
        print("DOCUMENTATION AUDIT REPORT")
        print("=" * 60)

        print(f"Files Scanned: {summary.total_files_scanned}")
        print(f"Issues Found: {summary.issues_found}")
        print(f"  - Errors: {summary.errors}")
        print(f"  - Warnings: {summary.warnings}")
        print(f"  - Info: {summary.info}")
        print(f"Fixable Issues: {summary.fixable_issues}")

        if args.fix and fixed_count > 0:
            print(f"Issues Fixed: {fixed_count}")

        print(f"Duration: {summary.duration_seconds:.2f}s")
        print(f"Deployment Ready: {'✅ YES' if summary.deployment_ready else '❌ NO'}")

        # Show issues by category
        if auditor.issues:
            print("\nISSUES BY CATEGORY:")
            print("-" * 40)

            issues_by_category = defaultdict(list)
            for issue in auditor.issues:
                issues_by_category[issue.category].append(issue)

            for category, issues in sorted(issues_by_category.items()):
                print(f"\n{category.upper()} ({len(issues)} issues):")
                for issue in issues[:5]:  # Show first 5 issues per category
                    location = issue.file_path
                    if issue.line_number:
                        location += f":{issue.line_number}"
                    print(f"  [{issue.severity}] {location}")
                    print(f"    {issue.message}")
                    if issue.suggestion:
                        print(f"    → {issue.suggestion}")

                if len(issues) > 5:
                    print(f"    ... and {len(issues) - 5} more")

        if summary.fixable_issues > 0 and not args.fix:
            print(f"\nRun with --fix to auto-fix {summary.fixable_issues} issues")

    # Exit with appropriate code
    if args.strict and not summary.deployment_ready:
        sys.exit(1)
    elif summary.errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
