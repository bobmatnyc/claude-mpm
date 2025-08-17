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
from typing import Dict, List, Optional, Set, Tuple

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
                 forbidden_locations: List[str] = None, description: str = ""):
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
            if parent_dir == Path("."):
                return False, f"Python script '{file_path.name}' should not be in project root"
            return True, ""  # Files in subdirectories are fine

        if self.name == "shell_scripts_in_root":
            # Only check files directly in root
            if parent_dir == Path("."):
                return False, f"Shell script '{file_path.name}' should not be in project root"
            return True, ""  # Files in subdirectories are fine

        if self.name == "test_files_misplaced":
            # Test files should be in tests directory
            if not str(relative_path).startswith("tests/"):
                return False, f"Test file '{file_path.name}' should be in /tests/ directory"
            return True, ""  # Files in tests directory are fine

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
        
        # Report results
        if self.violations:
            self._report_violations()
            return False
        else:
            if self.verbose:
                print("✅ No structure violations found")
            return True
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored during linting."""
        ignore_patterns = [
            r"\.git/.*",
            r"\.venv/.*", 
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
        return violation['rule'] in ['python_scripts_in_root', 'shell_scripts_in_root', 'test_files_misplaced']

    def _auto_fix_violation(self, violation: Dict) -> bool:
        """Attempt to automatically fix a violation."""
        try:
            source_path = PROJECT_ROOT / violation['file']

            # Determine target location
            if violation['rule'] == 'python_scripts_in_root':
                target_dir = PROJECT_ROOT / "scripts"
            elif violation['rule'] == 'shell_scripts_in_root':
                target_dir = PROJECT_ROOT / "scripts"
            elif violation['rule'] == 'test_files_misplaced':
                target_dir = PROJECT_ROOT / "tests"
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
