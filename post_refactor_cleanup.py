#!/usr/bin/env python3
"""
Post-refactoring cleanup using Black, flake8, and isort.

This script:
1. Runs Black to fix formatting and indentation issues
2. Runs isort to organize imports properly
3. Runs flake8 to identify remaining structural issues
4. Attempts to fix common issues automatically
5. Reports remaining issues that need manual attention
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PostRefactorCleanup:
    """Clean up refactored code using automated tools."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"

    def run_black(self) -> Tuple[bool, str]:
        """Run Black to fix formatting issues."""
        print("🔧 Running Black to fix formatting...")

        try:
            result = subprocess.run(
                [
                    "black",
                    str(self.src_dir),
                    "--line-length",
                    "100",
                    "--target-version",
                    "py38",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                print("✅ Black formatting completed successfully")
                return True, result.stdout
            else:
                print(f"❌ Black failed: {result.stderr}")
                return False, result.stderr

        except Exception as e:
            print(f"❌ Error running Black: {e}")
            return False, str(e)

    def run_isort(self) -> Tuple[bool, str]:
        """Run isort to organize imports."""
        print("📦 Running isort to organize imports...")

        try:
            result = subprocess.run(
                [
                    "isort",
                    str(self.src_dir),
                    "--profile",
                    "black",
                    "--line-length",
                    "100",
                    "--multi-line",
                    "3",
                    "--trailing-comma",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                print("✅ isort completed successfully")
                return True, result.stdout
            else:
                print(f"❌ isort failed: {result.stderr}")
                return False, result.stderr

        except Exception as e:
            print(f"❌ Error running isort: {e}")
            return False, str(e)

    def run_flake8(self) -> Tuple[bool, List[str]]:
        """Run flake8 to identify issues."""
        print("🔍 Running flake8 to identify issues...")

        try:
            result = subprocess.run(
                [
                    "flake8",
                    str(self.src_dir),
                    "--max-line-length",
                    "100",
                    "--ignore",
                    "E203,W503,E501",  # Ignore some Black-compatible issues
                    "--exclude",
                    "__pycache__,*.pyc,.git,venv",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            issues = result.stdout.strip().split("\n") if result.stdout.strip() else []

            if result.returncode == 0:
                print("✅ flake8 found no issues")
                return True, []
            else:
                print(f"⚠️  flake8 found {len(issues)} issues")
                return False, issues

        except Exception as e:
            print(f"❌ Error running flake8: {e}")
            return False, [str(e)]

    def fix_common_issues(self):
        """Fix common issues that can be automated."""
        print("🔨 Fixing common refactoring issues...")

        # Find all Python files in refactored modules
        module_dirs = list(self.src_dir.rglob("*_modules"))

        for module_dir in module_dirs:
            if module_dir.is_dir():
                self._fix_module_directory(module_dir)

    def _fix_module_directory(self, module_dir: Path):
        """Fix issues in a specific module directory."""
        print(f"  Fixing {module_dir.name}...")

        # Fix import paths in module files
        for py_file in module_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self._fix_imports_in_file(py_file)
            self._fix_class_names(py_file)

    def _fix_imports_in_file(self, file_path: Path):
        """Fix import statements in a file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Fix relative imports that are broken
            lines = content.split("\n")
            fixed_lines = []

            for line in lines:
                # Fix imports that reference the wrong path
                if "from ." in line and "import" in line:
                    # Remove broken relative imports to extracted modules
                    if any(
                        x in line
                        for x in [
                            "agent_template_builder",
                            "agent_version_manager",
                            "agent_metrics_collector",
                            "agent_environment_manager",
                        ]
                    ):
                        # Convert to absolute import
                        line = line.replace(
                            "from .", "from claude_mpm.services.agents.deployment."
                        )

                fixed_lines.append(line)

            # Write back if changed
            new_content = "\n".join(fixed_lines)
            if new_content != content:
                with open(file_path, "w") as f:
                    f.write(new_content)
                print(f"    Fixed imports in {file_path.name}")

        except Exception as e:
            print(f"    Error fixing {file_path.name}: {e}")

    def _fix_class_names(self, file_path: Path):
        """Fix overly long or malformed class names."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Fix class names that are too long or malformed
            lines = content.split("\n")
            fixed_lines = []

            for line in lines:
                if line.strip().startswith("class ") and "Manager" in line:
                    # Simplify overly complex class names
                    if "managermanager" in line.lower():
                        line = line.replace("managermanager", "Manager")
                        line = line.replace("ManagerManager", "Manager")

                    # Fix specific naming issues
                    if "Metricsmanager" in line:
                        line = line.replace("Metricsmanager", "Metrics")
                    if "Validationmanager" in line:
                        line = line.replace("Validationmanager", "Validation")
                    if "Othermanager" in line:
                        line = line.replace("Othermanager", "Core")

                fixed_lines.append(line)

            # Write back if changed
            new_content = "\n".join(fixed_lines)
            if new_content != content:
                with open(file_path, "w") as f:
                    f.write(new_content)
                print(f"    Fixed class names in {file_path.name}")

        except Exception as e:
            print(f"    Error fixing class names in {file_path.name}: {e}")

    def analyze_issues(self, issues: List[str]) -> Dict[str, List[str]]:
        """Analyze flake8 issues by category."""
        categorized = {
            "import_errors": [],
            "syntax_errors": [],
            "undefined_names": [],
            "unused_imports": [],
            "other": [],
        }

        for issue in issues:
            if "import" in issue.lower():
                categorized["import_errors"].append(issue)
            elif "syntax" in issue.lower() or "invalid syntax" in issue.lower():
                categorized["syntax_errors"].append(issue)
            elif "undefined name" in issue.lower() or "not defined" in issue.lower():
                categorized["undefined_names"].append(issue)
            elif "unused import" in issue.lower():
                categorized["unused_imports"].append(issue)
            else:
                categorized["other"].append(issue)

        return categorized

    def cleanup_all(self):
        """Run complete cleanup process."""
        print("🚀 Starting post-refactoring cleanup...\n")

        # Step 1: Fix common issues first
        self.fix_common_issues()

        # Step 2: Run Black for formatting
        black_success, black_output = self.run_black()
        if black_output:
            print(f"Black output: {black_output}")

        # Step 3: Run isort for imports
        isort_success, isort_output = self.run_isort()
        if isort_output:
            print(f"isort output: {isort_output}")

        # Step 4: Run flake8 to check for remaining issues
        flake8_success, issues = self.run_flake8()

        if issues:
            print(f"\n📋 Remaining issues to address:")
            categorized = self.analyze_issues(issues)

            for category, category_issues in categorized.items():
                if category_issues:
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for issue in category_issues[:10]:  # Show first 10
                        print(f"  {issue}")
                    if len(category_issues) > 10:
                        print(f"  ... and {len(category_issues) - 10} more")

        # Step 5: Check final file sizes
        print(f"\n📊 Final file sizes:")
        self.show_file_sizes()

        print(f"\n✅ Cleanup complete!")
        return black_success and isort_success

    def show_file_sizes(self):
        """Show current file sizes for large files."""
        large_files = []

        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name.endswith(".backup"):
                continue

            with open(py_file, "r") as f:
                line_count = sum(1 for _ in f)

            if line_count > 500:  # Show files over 500 lines
                large_files.append((py_file, line_count))

        large_files.sort(key=lambda x: x[1], reverse=True)

        for file_path, line_count in large_files[:10]:
            rel_path = file_path.relative_to(self.project_root)
            status = "🎯" if line_count < 900 else "⚠️"
            print(f"  {status} {rel_path}: {line_count} lines")


def main():
    """Main cleanup function."""
    project_root = "/Users/masa/Projects/claude-mpm"

    cleanup = PostRefactorCleanup(project_root)
    success = cleanup.cleanup_all()

    if success:
        print("\n🎉 All cleanup tools ran successfully!")
    else:
        print("\n⚠️  Some issues remain - check output above")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
