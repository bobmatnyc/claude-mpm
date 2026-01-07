#!/usr/bin/env python3
"""
Comprehensive script to fix all imports in the claude-mpm codebase.
This handles all the edge cases we've identified.
"""

import re
import sys
from pathlib import Path
from typing import List, Optional


class ComprehensiveImportFixer:
    """Fix all import issues in the codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.fixed_count = 0
        self.error_count = 0

    def fix_file(self, file_path: Path) -> bool:
        """Fix imports in a single file."""
        try:
            content = file_path.read_text()
            original = content

            # 1. Fix try/except imports
            content = self.fix_try_except_imports(content, file_path)

            # 2. Fix relative imports in regular code
            content = self.fix_relative_imports(content, file_path)

            # 3. Fix relative imports within the same package
            content = self.fix_same_package_imports(content, file_path)

            # 4. Clean up any double claude_mpm.claude_mpm patterns
            content = content.replace("claude_mpm.claude_mpm.", "claude_mpm.")

            if content != original:
                file_path.write_text(content)
                self.fixed_count += 1
                return True
            return False

        except Exception as e:
            print(f"Error fixing {file_path}: {e}")
            self.error_count += 1
            return False

    def fix_try_except_imports(self, content: str, file_path: Path) -> str:
        """Fix all try/except import blocks."""
        # Pattern for try/except with imports
        pattern = re.compile(
            r"try:\s*\n(\s*)(from\s+[^\n]+)\s*\nexcept\s+ImportError:\s*\n(\s*)(from\s+[^\n]+)",
            re.MULTILINE,
        )

        def replace_try_except(match):
            indent = match.group(1)
            import1 = match.group(2).strip()
            import2 = match.group(4).strip()

            # Determine which import to use
            if "claude_mpm" in import1:
                return f"{indent}{import1}"
            if "claude_mpm" in import2:
                return f"{indent}{import2}"
            # Convert relative imports
            if ".." in import1:
                # Convert relative import to absolute
                converted = self.convert_relative_to_absolute(import1, file_path)
                if converted:
                    return f"{indent}{converted}"
            elif "from " in import1:
                # Add claude_mpm prefix
                parts = import1.split("from ", 1)[1].split(" import", 1)
                if len(parts) == 2:
                    module = parts[0].strip()
                    import_clause = parts[1]
                    if not module.startswith(("claude_mpm", ".", "ai_trackdown")):
                        return f"{indent}from claude_mpm.{module} import{import_clause}"

            return f"{indent}{import1}"

        return pattern.sub(replace_try_except, content)

    def fix_relative_imports(self, content: str, file_path: Path) -> str:
        """Fix relative imports like 'from ..module import'."""
        pattern = re.compile(
            r"^(\s*from\s+)(\.+)([.\w]*)?(\s+import\s+.+)$", re.MULTILINE
        )

        def replace_relative(match):
            indent_from = match.group(1)
            dots = match.group(2)
            module_path = match.group(3) or ""
            import_clause = match.group(4)

            # Calculate absolute path
            current_parts = self.get_module_parts(file_path)
            if not current_parts:
                return match.group(0)

            # Go up directories based on dots
            level = len(dots)
            if level > len(current_parts):
                return match.group(0)

            base_parts = current_parts[:-level] if level > 0 else current_parts

            # Build absolute import
            if module_path:
                if base_parts:
                    absolute_module = (
                        "claude_mpm." + ".".join(base_parts) + "." + module_path
                    )
                else:
                    absolute_module = "claude_mpm." + module_path
            elif base_parts:
                absolute_module = "claude_mpm." + ".".join(base_parts)
            else:
                absolute_module = "claude_mpm"

            return f"{indent_from}{absolute_module}{import_clause}"

        return pattern.sub(replace_relative, content)

    def fix_same_package_imports(self, content: str, file_path: Path) -> str:
        """Fix imports within the same package (e.g., in __init__.py)."""
        # Special handling for __init__.py files
        if file_path.name == "__init__.py":
            # For top-level __init__.py
            if file_path.parent == self.src_path / "claude_mpm":
                # Fix imports like "from ._version import"
                content = re.sub(
                    r"from\s+\.([.\w]+)\s+import", r"from claude_mpm.\1 import", content
                )
            else:
                # For other __init__.py files, convert relative to absolute
                module_parts = self.get_module_parts(file_path)
                if module_parts:
                    base_module = "claude_mpm." + ".".join(module_parts)
                    content = re.sub(
                        r"from\s+\.([.\w]+)\s+import",
                        rf"from {base_module}.\1 import",
                        content,
                    )

        return content

    def get_module_parts(self, file_path: Path) -> List[str]:
        """Get module parts for a file."""
        if str(file_path).startswith(str(self.src_path / "claude_mpm")):
            relative = file_path.relative_to(self.src_path / "claude_mpm")
            parts = list(relative.parts[:-1])  # Remove filename

            # Don't include __init__ in module path
            if file_path.stem != "__init__":
                parts.append(file_path.stem)

            return parts
        return []

    def convert_relative_to_absolute(
        self, import_stmt: str, file_path: Path
    ) -> Optional[str]:
        """Convert a relative import statement to absolute."""
        match = re.match(r"from\s+(\.+)([.\w]*)?(\s+import\s+.+)", import_stmt)
        if not match:
            return None

        dots = match.group(1)
        module_path = match.group(2) or ""
        import_clause = match.group(3)

        current_parts = self.get_module_parts(file_path)
        if not current_parts:
            return None

        level = len(dots)
        if level > len(current_parts):
            return None

        base_parts = current_parts[:-level] if level > 0 else current_parts

        if module_path:
            if base_parts:
                absolute_module = (
                    "claude_mpm." + ".".join(base_parts) + "." + module_path
                )
            else:
                absolute_module = "claude_mpm." + module_path
        elif base_parts:
            absolute_module = "claude_mpm." + ".".join(base_parts)
        else:
            absolute_module = "claude_mpm"

        return f"from {absolute_module}{import_clause}"

    def run(self, dry_run: bool = False) -> None:
        """Run the import fixing process."""
        # Find all Python files
        python_files = list(self.src_path.rglob("*.py"))

        # Filter out unwanted directories
        python_files = [
            f
            for f in python_files
            if not any(
                part in f.parts
                for part in ["__pycache__", ".pytest_cache", "build", "dist"]
            )
        ]

        print(f"Processing {len(python_files)} Python files...")

        if dry_run:
            print("DRY RUN - No files will be modified\n")

        for file_path in python_files:
            if dry_run:
                print(f"Would process: {file_path.relative_to(self.project_root)}")
            elif self.fix_file(file_path):
                print(f"Fixed: {file_path.relative_to(self.project_root)}")

        print("\nSummary:")
        print(f"  Files fixed: {self.fixed_count}")
        print(f"  Errors: {self.error_count}")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    fixer = ComprehensiveImportFixer(project_root)

    dry_run = "--dry-run" in sys.argv
    fixer.run(dry_run=dry_run)

    if dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
