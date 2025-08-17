#!/usr/bin/env python3
"""
Script to standardize imports across the claude-mpm codebase.
Converts relative imports to absolute imports from claude_mpm package.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Set


class ImportStandardizer:
    """Standardize imports across the codebase."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.issues_found = []
        self.files_modified = 0
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        return list(self.project_root.rglob("*.py"))
    
    def get_module_path(self, file_path: Path) -> str:
        """Get the module path for a given file."""
        # For files in src/claude_mpm/
        if str(file_path).startswith(str(self.src_path / "claude_mpm")):
            relative_to_package = file_path.relative_to(self.src_path / "claude_mpm")
            parts = list(relative_to_package.parts[:-1])  # Remove filename
            if file_path.stem != "__init__":
                parts.append(file_path.stem)
            return ".".join(parts)
        
        # For test files or scripts
        return None
    
    def resolve_relative_import(self, current_module: str, relative_import: str) -> str:
        """Resolve a relative import to an absolute import."""
        if not current_module:
            return None
            
        current_parts = current_module.split(".")
        import_parts = relative_import.split(".")
        
        # Count leading dots
        level = 0
        for part in import_parts:
            if part == "":
                level += 1
            else:
                break
        
        # Remove empty parts from leading dots
        import_parts = [p for p in import_parts if p]
        
        # Go up 'level' directories
        if level > len(current_parts):
            return None  # Invalid relative import
            
        base_parts = current_parts[:-level] if level > 0 else current_parts
        
        # Combine with the import parts
        if import_parts:
            full_parts = base_parts + import_parts
        else:
            full_parts = base_parts
            
        return "claude_mpm." + ".".join(full_parts)
    
    def process_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Process a single file and return whether it was modified and any issues."""
        try:
            content = file_path.read_text()
            original_content = content
            issues = []
            
            current_module = self.get_module_path(file_path)
            
            # Special handling for __init__.py files
            is_init_file = file_path.name == "__init__.py"
            if is_init_file and str(file_path).startswith(str(self.src_path / "claude_mpm")):
                # For __init__.py in claude_mpm package
                relative_to_package = file_path.relative_to(self.src_path / "claude_mpm")
                current_module = ".".join(relative_to_package.parts[:-1])
            
            # Pattern for relative imports
            relative_import_pattern = re.compile(
                r'^(\s*)(from\s+)(\.+)([.\w]*)?(\s+import\s+.+)$',
                re.MULTILINE
            )
            
            # Pattern for try/except imports
            try_except_pattern = re.compile(
                r'try:\s*\n(\s*)(from\s+[.\w]+\s+import\s+.+)\s*\nexcept\s+ImportError:\s*\n(\s*)(from\s+[.\w]+\s+import\s+.+)',
                re.MULTILINE
            )
            
            # Fix relative imports
            def replace_relative(match):
                indent = match.group(1)
                from_keyword = match.group(2)
                dots = match.group(3)
                module_path = match.group(4) or ""
                import_clause = match.group(5)
                
                relative_path = dots + module_path
                
                # Special case for top-level __init__.py
                if is_init_file and file_path.parent == self.src_path / "claude_mpm":
                    # For imports like "from ._version import __version__"
                    if dots == "." and module_path:
                        # Remove the leading dot for same-level imports
                        return f"{indent}{from_keyword}claude_mpm.{module_path}{import_clause}"
                
                absolute_path = self.resolve_relative_import(current_module, relative_path)
                
                if absolute_path:
                    return f"{indent}{from_keyword}{absolute_path}{import_clause}"
                else:
                    issues.append(f"Could not resolve relative import: {relative_path}")
                    return match.group(0)
            
            content = relative_import_pattern.sub(replace_relative, content)
            
            # Fix try/except imports - keep only the claude_mpm version
            def replace_try_except(match):
                indent1 = match.group(1)
                import1 = match.group(2)
                import2 = match.group(4)
                
                # Always prefer the import with dots (relative import that should be converted)
                if ".." in import1 or ".." in import2:
                    # Use the one with relative imports and convert it
                    if ".." in import1:
                        to_convert = import1
                    else:
                        to_convert = import2
                        
                    # Extract and convert the import
                    rel_match = re.match(r'from\s+(\.+)([.\w]*)?(\s+import\s+.+)', to_convert)
                    if rel_match:
                        dots = rel_match.group(1)
                        module_path = rel_match.group(2) or ""
                        import_clause = rel_match.group(3)
                        relative_path = dots + module_path
                        
                        # For imports from parent modules
                        if dots == ".." and current_module:
                            parts = current_module.split(".")
                            if len(parts) > 0:
                                parent = ".".join(parts[:-1])
                                if module_path:
                                    absolute_path = f"claude_mpm.{module_path}"
                                else:
                                    absolute_path = "claude_mpm"
                                return f"{indent1}from {absolute_path}{import_clause}"
                        
                        absolute_path = self.resolve_relative_import(current_module, relative_path)
                        if absolute_path:
                            return f"{indent1}from {absolute_path}{import_clause}"
                
                # Check which import uses claude_mpm
                if "claude_mpm" in import1:
                    return f"{indent1}{import1}"
                elif "claude_mpm" in import2:
                    return f"{indent1}{import2}"
                else:
                    # For simple module imports without claude_mpm, assume first is correct
                    # This handles cases like "from core.logger import" -> "from claude_mpm.core.logger import"
                    if "from " in import1 and not import1.startswith("from claude_mpm"):
                        parts = import1.split("from ", 1)[1].split(" import", 1)
                        if len(parts) == 2:
                            module = parts[0].strip()
                            import_clause = " import" + parts[1]
                            if module and not module.startswith((".", "claude_mpm")):
                                return f"{indent1}from claude_mpm.{module}{import_clause}"
                    
                    return f"{indent1}{import1}"
            
            content = try_except_pattern.sub(replace_try_except, content)
            
            # Check for any remaining relative imports
            if re.search(r'from\s+\.', content):
                issues.append("File still contains relative imports after conversion")
            
            # Check for any remaining try/except import blocks
            if re.search(r'try:\s*\n\s*(from|import)', content):
                issues.append("File still contains try/except import blocks")
            
            modified = content != original_content
            
            if modified:
                file_path.write_text(content)
                
            return modified, issues
            
        except Exception as e:
            return False, [f"Error processing file: {e}"]
    
    def run(self, dry_run: bool = True) -> None:
        """Run the import standardization process."""
        python_files = self.find_python_files()
        
        # Skip virtual environments and build directories
        python_files = [
            f for f in python_files 
            if not any(part in f.parts for part in [
                'venv', '.venv', 'env', '.env', 
                'build', 'dist', '.eggs', '__pycache__',
                'site-packages', '.tox', '.pytest_cache'
            ])
        ]
        
        print(f"Found {len(python_files)} Python files to process")
        
        if dry_run:
            print("\n=== DRY RUN MODE - No files will be modified ===\n")
        
        issues_by_file = {}
        modified_files = []
        
        for file_path in python_files:
            if dry_run:
                # Read file and check what would change
                try:
                    content = file_path.read_text()
                    temp_path = Path("/tmp") / file_path.name
                    temp_path.write_text(content)
                    modified, issues = self.process_file(temp_path)
                    temp_path.unlink()
                except Exception as e:
                    modified, issues = False, [f"Error in dry run: {e}"]
            else:
                modified, issues = self.process_file(file_path)
            
            if modified:
                modified_files.append(file_path)
                
            if issues:
                issues_by_file[file_path] = issues
        
        # Report results
        print(f"\n=== Import Standardization Report ===")
        print(f"Files that would be modified: {len(modified_files)}")
        print(f"Files with issues: {len(issues_by_file)}")
        
        if modified_files:
            print("\n=== Modified Files ===")
            for f in sorted(modified_files)[:20]:  # Show first 20
                print(f"  {f.relative_to(self.project_root)}")
            if len(modified_files) > 20:
                print(f"  ... and {len(modified_files) - 20} more")
        
        if issues_by_file:
            print("\n=== Issues Found ===")
            for file_path, issues in sorted(issues_by_file.items())[:10]:  # Show first 10
                print(f"\n{file_path.relative_to(self.project_root)}:")
                for issue in issues:
                    print(f"  - {issue}")
            if len(issues_by_file) > 10:
                print(f"\n... and issues in {len(issues_by_file) - 10} more files")
        
        if not dry_run:
            print(f"\n✓ Standardized imports in {len(modified_files)} files")
        else:
            print(f"\nRun with --no-dry-run to apply changes")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    standardizer = ImportStandardizer(project_root)
    
    dry_run = "--no-dry-run" not in sys.argv
    standardizer.run(dry_run=dry_run)


if __name__ == "__main__":
    main()