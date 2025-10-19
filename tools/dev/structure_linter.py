#!/usr/bin/env python3
"""
Project Structure Linter for Claude MPM

This tool enforces the project structure rules defined in docs/STRUCTURE.md
and prevents violations of documented file placement guidelines.

Usage:
    python tools/dev/structure_linter.py [--fix] [--verbose] [path]

Features:
- Validates file placement according to STRUCTURE.md
- Checks naming conventions
- Identifies misplaced files
- Provides fix suggestions
- Can automatically fix some violations
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Project root detection
def find_project_root() -> Path:
    """Find the project root by looking for key files."""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() and (current / "src" / "claude_mpm").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = find_project_root()

class StructureRule:
    """Represents a structure validation rule."""

    def __init__(self, name: str, pattern: str, allowed_locations: List[str],
                 forbidden_locations: Optional[List[str]] = None, description: str = ""):
        self.name = name
        self.pattern = re.compile(pattern)
        self.allowed_locations = [Path(loc) for loc in allowed_locations]
        self.forbidden_locations = [Path(loc) for loc in (forbidden_locations or [])]
        self.description = description

    def check_file(self, file_path: Path) -> Tuple[bool, str]:
        """Check if file matches this rule and is in correct location."""
        if not self.pattern.match(file_path.name):
            return True, ""  # Rule doesn't apply

        relative_path = file_path.relative_to(PROJECT_ROOT)
        parent_dir = relative_path.parent

        # Special exceptions
        if self.name == "python_scripts_in_root":
            if file_path.name == "setup.py":
                return True, ""  # setup.py is allowed in root
            # Only check files directly in root
            if parent_dir == Path():
                return False, f"Python script '{file_path.name}' should not be in project root"
            return True, ""  # Files in subdirectories are fine

        if self.name == "shell_scripts_in_root":
            # Only check files directly in root
            if parent_dir == Path():
                return False, f"Shell script '{file_path.name}' should not be in project root"
            return True, ""  # Files in subdirectories are fine

        if self.name == "test_files_misplaced":
            # Test files should be in tests directory
            if not str(relative_path).startswith("tests/"):
                return False, f"Test file '{file_path.name}' should be in /tests/ directory"
            return True, ""  # Files in tests directory are fine

        if self.name == "old_release_notes_in_root":
            # Release notes files should be in docs/release-notes directory
            if parent_dir == Path():
                return False, f"Historical release notes file '{file_path.name}' should be in docs/release-notes/ directory"
            return True, ""  # Files in subdirectories are fine

        return True, ""  # Default: no violation

    def _path_matches(self, file_path: Path, location: Path) -> bool:
        """Check if file path is within the specified location."""
        try:
            file_path.relative_to(location)
            return True
        except ValueError:
            return False

class StructureLinter:
    """Main structure linting class."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.violations: List[Dict] = []
        self.rules = self._load_rules()
        self.changelog_sections = ['Added', 'Changed', 'Fixed', 'Removed', 'Deprecated', 'Security']

    def _load_rules(self) -> List[StructureRule]:
        """Load structure validation rules based on STRUCTURE.md."""
        return [
            # Python scripts should not be in project root (except setup.py)
            StructureRule(
                name="python_scripts_in_root",
                pattern=r".*\.py$",
                allowed_locations=[],  # Not used for this rule
                forbidden_locations=["."],  # Project root only
                description="Python scripts must not be in project root (except setup.py)"
            ),

            # Shell scripts should not be in project root
            StructureRule(
                name="shell_scripts_in_root",
                pattern=r".*\.(sh|bash)$",
                allowed_locations=[],  # Not used for this rule
                forbidden_locations=["."],  # Project root only
                description="Shell scripts must not be in project root"
            ),

            # Test files should be in /tests/ directory
            StructureRule(
                name="test_files_misplaced",
                pattern=r"test_.*\.py$|.*_test\.py$",
                allowed_locations=["tests"],
                forbidden_locations=[".", "scripts", "tools", "examples"],
                description="Test files must be in /tests/ directory"
            ),

            # Release notes files should be in docs/release-notes (except current)
            StructureRule(
                name="old_release_notes_in_root",
                pattern=r"RELEASE_NOTES_.*\.md$",
                allowed_locations=["docs/release-notes"],
                forbidden_locations=["."],
                description="Historical release notes must be in docs/release-notes directory"
            ),
        ]

    def lint_project(self, target_path: Optional[Path] = None) -> bool:
        """Lint the entire project or specific path."""
        if target_path is None:
            target_path = PROJECT_ROOT

        self.violations = []

        if self.verbose:
            print(f"Linting project structure from: {target_path}")

        # Check all files
        for file_path in target_path.rglob("*"):
            if file_path.is_file() and not self._should_ignore(file_path):
                self._check_file(file_path)

        # Check changelog
        self._check_changelog()

        # Check version consistency
        self._check_version_consistency()

        # Report results
        if self.violations:
            self._report_violations()
            return False
        if self.verbose:
            print("✅ No structure violations found")
        return True

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored during linting."""
        ignore_patterns = [
            r"\.git/.*",
            r"\.venv/.*",
            r"\.venv-.*/.*",  # Additional venv patterns
            r"venv/.*",
            r"__pycache__/.*",
            r"\.pytest_cache/.*",
            r"node_modules/.*",
            r"dist/.*",
            r"build/.*",
            r"\.egg-info/.*",
            r"logs/.*",
            r"\.DS_Store",
            r"\.pyc$",
        ]

        relative_path = str(file_path.relative_to(PROJECT_ROOT))
        return any(re.match(pattern, relative_path) for pattern in ignore_patterns)

    def _check_file(self, file_path: Path):
        """Check a single file against all rules."""
        for rule in self.rules:
            is_valid, message = rule.check_file(file_path)
            if not is_valid:
                violation = {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "rule": rule.name,
                    "message": message,
                    "description": rule.description,
                    "suggested_locations": [str(loc) for loc in rule.allowed_locations]
                }
                self.violations.append(violation)

                if self.verbose:
                    print(f"❌ {violation['file']}: {violation['message']}")

    def _report_violations(self):
        """Report all violations found."""
        print(f"\n🚨 Found {len(self.violations)} structure violations:\n")

        # Group by rule type
        by_rule = {}
        for violation in self.violations:
            rule = violation['rule']
            if rule not in by_rule:
                by_rule[rule] = []
            by_rule[rule].append(violation)

        for rule_name, violations in by_rule.items():
            print(f"📋 {rule_name.replace('_', ' ').title()} ({len(violations)} violations):")
            for v in violations:
                print(f"  ❌ {v['file']}")
                print(f"     {v['message']}")
                if v['suggested_locations']:
                    print(f"     💡 Suggested: {', '.join(v['suggested_locations'])}")
            print()

    def fix_violations(self) -> bool:
        """Attempt to automatically fix violations."""
        if not self.violations:
            print("No violations to fix")
            return True

        print(f"Attempting to fix {len(self.violations)} violations...")
        fixed = 0

        for violation in self.violations:
            if self._can_auto_fix(violation):
                if self._auto_fix_violation(violation):
                    fixed += 1
                    print(f"✅ Fixed: {violation['file']}")
                else:
                    print(f"❌ Failed to fix: {violation['file']}")
            else:
                print(f"⚠️  Manual fix required: {violation['file']}")

        print(f"\nFixed {fixed}/{len(self.violations)} violations")
        return fixed == len(self.violations)

    def _can_auto_fix(self, violation: Dict) -> bool:
        """Check if violation can be automatically fixed."""
        # Only auto-fix simple file moves for now
        return violation['rule'] in ['python_scripts_in_root', 'shell_scripts_in_root', 'test_files_misplaced', 'old_release_notes_in_root']

    def _auto_fix_violation(self, violation: Dict) -> bool:
        """Attempt to automatically fix a violation."""
        try:
            source_path = PROJECT_ROOT / violation['file']

            # Determine target location
            if violation['rule'] == 'python_scripts_in_root' or violation['rule'] == 'shell_scripts_in_root':
                target_dir = PROJECT_ROOT / "scripts"
            elif violation['rule'] == 'test_files_misplaced':
                target_dir = PROJECT_ROOT / "tests"
            elif violation['rule'] == 'old_release_notes_in_root':
                target_dir = PROJECT_ROOT / "docs" / "release-notes"
            else:
                return False

            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / source_path.name

            # Check if target already exists
            if target_path.exists():
                if self.verbose:
                    print(f"Target already exists: {target_path}")
                return False

            # Move file
            source_path.rename(target_path)
            return True

        except Exception as e:
            if self.verbose:
                print(f"Error fixing {violation['file']}: {e}")
            return False

    def _check_changelog(self):
        """Check CHANGELOG.md format and requirements."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"

        if not changelog_path.exists():
            self.violations.append({
                "file": "CHANGELOG.md",
                "rule": "missing_changelog",
                "message": "CHANGELOG.md file is missing",
                "description": "Project must have a CHANGELOG.md file",
                "suggested_locations": ["."]
            })
            return

        content = changelog_path.read_text()
        lines = content.split('\n')

        # Check for [Unreleased] section
        has_unreleased = False
        unreleased_line = -1
        for i, line in enumerate(lines):
            if re.match(r'^##\s+\[Unreleased\]', line):
                has_unreleased = True
                unreleased_line = i
                break

        if not has_unreleased:
            self.violations.append({
                "file": "CHANGELOG.md",
                "rule": "missing_unreleased_section",
                "message": "CHANGELOG.md missing [Unreleased] section",
                "description": "CHANGELOG.md must have an [Unreleased] section for upcoming changes",
                "suggested_locations": []
            })
        else:
            # Check that [Unreleased] section has proper subsections
            found_sections = set()
            for i in range(unreleased_line + 1, min(unreleased_line + 50, len(lines))):
                line = lines[i]
                if re.match(r'^##\s+\[', line):  # Next version section
                    break
                for section in self.changelog_sections:
                    if re.match(rf'^###\s+{section}', line):
                        found_sections.add(section)

            # At least some of the standard sections should be present
            if len(found_sections) < 3:
                self.violations.append({
                    "file": "CHANGELOG.md",
                    "rule": "incomplete_unreleased_section",
                    "message": f"[Unreleased] section missing standard subsections (found: {', '.join(found_sections) if found_sections else 'none'})",
                    "description": f"[Unreleased] section should have subsections: {', '.join(self.changelog_sections[:4])}",
                    "suggested_locations": []
                })

        # Check for Keep a Changelog format
        if "Keep a Changelog" not in content:
            self.violations.append({
                "file": "CHANGELOG.md",
                "rule": "invalid_changelog_format",
                "message": "CHANGELOG.md not following Keep a Changelog format",
                "description": "CHANGELOG.md should follow https://keepachangelog.com format",
                "suggested_locations": []
            })

        # Check for comparison links
        if not re.search(r'\[Unreleased\]:\s+https?://', content):
            self.violations.append({
                "file": "CHANGELOG.md",
                "rule": "missing_comparison_links",
                "message": "CHANGELOG.md missing comparison links for versions",
                "description": "CHANGELOG.md should have comparison links at the bottom",
                "suggested_locations": []
            })

    def _check_version_consistency(self):
        """Check version consistency across files."""
        version_file = PROJECT_ROOT / "VERSION"
        package_json = PROJECT_ROOT / "package.json"
        pyproject_toml = PROJECT_ROOT / "pyproject.toml"

        versions = {}

        # Read VERSION file
        if version_file.exists():
            versions['VERSION'] = version_file.read_text().strip()
        else:
            self.violations.append({
                "file": "VERSION",
                "rule": "missing_version_file",
                "message": "VERSION file is missing",
                "description": "Project must have a VERSION file",
                "suggested_locations": ["."]
            })

        # Read package.json version
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    pkg_data = json.load(f)
                    versions['package.json'] = pkg_data.get('version', '')
            except Exception as e:
                if self.verbose:
                    print(f"Error reading package.json: {e}")

        # Read pyproject.toml commitizen version
        if pyproject_toml.exists():
            content = pyproject_toml.read_text()
            match = re.search(r'\[tool\.commitizen\].*?version\s*=\s*"([^"]+)"', content, re.DOTALL)
            if match:
                versions['pyproject.toml'] = match.group(1)

        # Check consistency
        if len(set(versions.values())) > 1:
            self.violations.append({
                "file": "version_files",
                "rule": "version_mismatch",
                "message": f"Version mismatch across files: {versions}",
                "description": "All version files must have the same version number",
                "suggested_locations": []
            })

        # Check that version is in CHANGELOG
        if versions.get('VERSION'):
            changelog_path = PROJECT_ROOT / "CHANGELOG.md"
            if changelog_path.exists():
                content = changelog_path.read_text()
                version_pattern = rf'##\s+\[{re.escape(versions["VERSION"])}\]'
                if not re.search(version_pattern, content):
                    # Only warn if this is not a development version
                    if not versions['VERSION'].endswith('-dev'):
                        self.violations.append({
                            "file": "CHANGELOG.md",
                            "rule": "version_not_in_changelog",
                            "message": f"Version {versions['VERSION']} not found in CHANGELOG.md",
                            "description": "Current version must have an entry in CHANGELOG.md",
                            "suggested_locations": []
                        })

def main():
    parser = argparse.ArgumentParser(description="Claude MPM Project Structure Linter")
    parser.add_argument("path", nargs="?", help="Path to lint (default: project root)")
    parser.add_argument("--fix", action="store_true", help="Attempt to automatically fix violations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Determine target path
    if args.path:
        target_path = Path(args.path).resolve()
        if not target_path.exists():
            print(f"Error: Path does not exist: {target_path}")
            sys.exit(1)
    else:
        target_path = None

    # Run linter
    linter = StructureLinter(verbose=args.verbose)
    is_valid = linter.lint_project(target_path)

    # Output results
    if args.json:
        result = {
            "valid": is_valid,
            "violations": linter.violations,
            "total_violations": len(linter.violations)
        }
        print(json.dumps(result, indent=2))

    # Attempt fixes if requested
    if args.fix and linter.violations:
        linter.fix_violations()

    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
