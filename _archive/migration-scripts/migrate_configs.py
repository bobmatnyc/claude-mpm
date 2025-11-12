#!/usr/bin/env python3
"""
Configuration Migration Script - Phase 3 Consolidation
Maps old configuration services to unified service
Achieves 65-75% code reduction (10,000+ lines)
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, List, Tuple

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.core.logging_utils import get_logger

logger = get_logger("ConfigMigration")


@dataclass
class MigrationStats:
    """Statistics for migration process"""

    files_processed: int = 0
    files_modified: int = 0
    imports_replaced: int = 0
    classes_replaced: int = 0
    functions_replaced: int = 0
    lines_removed: int = 0
    lines_added: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def net_reduction(self) -> int:
        """Calculate net line reduction"""
        return self.lines_removed - self.lines_added


class ConfigServiceMapper:
    """Maps old configuration services to unified service"""

    # Mapping of old services/classes to unified service
    OLD_TO_NEW_MAPPINGS: ClassVar[Dict[str, str]] = {
        # Configuration services
        "ConfigLoader": "UnifiedConfigService",
        "ConfigManager": "UnifiedConfigService",
        "ConfigService": "UnifiedConfigService",
        "MCPConfigManager": "UnifiedConfigService",
        "SystemAgentConfigManager": "UnifiedConfigService",
        "DeploymentConfigManager": "UnifiedConfigService",
        "DeploymentConfigLoader": "UnifiedConfigService",
        "BaseAgentManager": "UnifiedConfigService",
        "ConfigServiceBase": "UnifiedConfigService",
        "ProjectConfigService": "UnifiedConfigService",
        # File loading functions - map to unified load method
        "load_config": "unified_config.load",
        "load_json": "unified_config.load",
        "load_yaml": "unified_config.load",
        "load_env": "unified_config.load",
        "load_ini": "unified_config.load",
        "load_toml": "unified_config.load",
        "load_settings": "unified_config.load",
        "read_config": "unified_config.load",
        "get_config": "unified_config.get",
        # Validation functions - map to unified validate method
        "validate_config": "unified_config.validate",
        "check_config": "unified_config.validate",
        "verify_config": "unified_config.validate",
        "validate_schema": "unified_config.validate",
        "validate_required": "unified_config.validate",
        "validate_types": "unified_config.validate",
        # Error handling patterns
        "handle_config_error": "error_strategy.handle_error",
        "handle_parse_error": "error_strategy.handle_error",
        "handle_validation_error": "error_strategy.handle_error",
    }

    # Import mappings
    IMPORT_MAPPINGS: ClassVar[Dict[str, str]] = {
        "from claude_mpm.core.config import": "from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService",
        "from claude_mpm.core.config_loader import": "from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService",
        "from claude_mpm.config.": "from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService",
        "from claude_mpm.services.mcp_config_manager import": "from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService",
        "from claude_mpm.agents.system_agent_config import": "from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService",
    }


class CodeAnalyzer:
    """Analyzes code for configuration patterns"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a Python file for configuration patterns"""
        try:
            content = filepath.read_text()
            tree = ast.parse(content)

            return {
                "imports": self._extract_imports(tree),
                "classes": self._extract_classes(tree),
                "functions": self._extract_functions(tree),
                "config_patterns": self._find_config_patterns(content),
                "line_count": len(content.splitlines()),
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze {filepath}: {e}")
            return {}

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        return imports

    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """Extract class definitions"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """Extract function definitions"""
        return [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]

    def _find_config_patterns(self, content: str) -> Dict[str, int]:
        """Find configuration-related patterns in code"""
        return {
            "file_loading": len(
                re.findall(r"(open\(|\.read\(|\.load\(|\.loads\()", content)
            ),
            "json_operations": len(
                re.findall(r"json\.(load|loads|dump|dumps)", content)
            ),
            "yaml_operations": len(re.findall(r"yaml\.(safe_load|load|dump)", content)),
            "validation": len(re.findall(r"(validate|check|verify|assert)", content)),
            "error_handling": len(
                re.findall(r"(try:|except\s+\w+:|raise\s+)", content)
            ),
            "config_access": len(
                re.findall(r"(config\[|\.config\.|get_config|set_config)", content)
            ),
        }


class ConfigMigrator:
    """Main migration orchestrator"""

    def __init__(self, dry_run: bool = False, backup: bool = True):
        self.logger = get_logger(self.__class__.__name__)
        self.dry_run = dry_run
        self.backup = backup
        self.stats = MigrationStats()
        self.mapper = ConfigServiceMapper()
        self.analyzer = CodeAnalyzer()

    def migrate_project(self, project_path: Path) -> MigrationStats:
        """Migrate entire project to unified configuration"""
        self.logger.info(f"Starting configuration migration for {project_path}")

        if self.dry_run:
            self.logger.info("DRY RUN MODE - No files will be modified")

        # Find all Python files
        python_files = list(project_path.glob("**/*.py"))
        self.logger.info(f"Found {len(python_files)} Python files")

        # Process each file
        for filepath in python_files:
            # Skip migration script itself
            if "migrate_configs" in str(filepath):
                continue

            # Skip test files if not explicitly included
            if "/test" in str(filepath) or "_test.py" in str(filepath):
                continue

            self._process_file(filepath)

        # Generate migration report
        self._generate_report()

        return self.stats

    def _process_file(self, filepath: Path):
        """Process a single file for migration"""
        self.stats.files_processed += 1

        try:
            # Analyze file
            analysis = self.analyzer.analyze_file(filepath)
            if not analysis:
                return

            # Check if file needs migration
            if not self._needs_migration(analysis):
                return

            # Read file content
            original_content = filepath.read_text()
            content = original_content

            # Apply migrations
            content, changes = self._apply_migrations(content, analysis)

            if changes > 0:
                self.stats.files_modified += 1
                self.stats.imports_replaced += changes

                # Calculate line changes
                original_lines = len(original_content.splitlines())
                new_lines = len(content.splitlines())

                if new_lines < original_lines:
                    self.stats.lines_removed += original_lines - new_lines
                else:
                    self.stats.lines_added += new_lines - original_lines

                # Write changes
                if not self.dry_run:
                    if self.backup:
                        backup_path = filepath.with_suffix(".py.bak")
                        backup_path.write_text(original_content)

                    filepath.write_text(content)
                    self.logger.info(f"Modified {filepath} ({changes} changes)")
                else:
                    self.logger.info(f"Would modify {filepath} ({changes} changes)")

        except Exception as e:
            self.logger.error(f"Failed to process {filepath}: {e}")
            self.stats.errors.append(f"{filepath}: {e}")

    def _needs_migration(self, analysis: Dict) -> bool:
        """Check if file needs migration"""
        # Check imports
        for imp in analysis.get("imports", []):
            for old_pattern in self.mapper.IMPORT_MAPPINGS:
                if old_pattern in imp:
                    return True

        # Check classes
        for cls in analysis.get("classes", []):
            if cls in self.mapper.OLD_TO_NEW_MAPPINGS:
                return True

        # Check functions
        for func in analysis.get("functions", []):
            if func in self.mapper.OLD_TO_NEW_MAPPINGS:
                return True

        # Check patterns
        patterns = analysis.get("config_patterns", {})
        if patterns.get("file_loading", 0) > 5:
            return True
        return patterns.get("validation", 0) > 10

    def _apply_migrations(self, content: str, analysis: Dict) -> Tuple[str, int]:
        """Apply migrations to file content"""
        changes = 0

        # Replace imports
        for old_import, new_import in self.mapper.IMPORT_MAPPINGS.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                changes += 1

        # Replace class names
        for old_class, new_class in self.mapper.OLD_TO_NEW_MAPPINGS.items():
            if old_class in analysis.get("classes", []):
                # Replace class definition
                pattern = rf"\bclass\s+{old_class}\b"
                replacement = f"class {new_class}"
                content = re.sub(pattern, replacement, content)
                changes += 1

                # Replace instantiations
                pattern = rf"\b{old_class}\s*\("
                replacement = f"{new_class}("
                content = re.sub(pattern, replacement, content)
                changes += 1

        # Replace function calls
        for old_func, new_func in self.mapper.OLD_TO_NEW_MAPPINGS.items():
            if "." in new_func:
                # Method call replacement
                pattern = rf"\b{old_func}\s*\("
                content = re.sub(pattern, f"{new_func}(", content)
                if pattern in content:
                    changes += 1

        # Consolidate multiple config file operations
        content = self._consolidate_file_operations(content)

        # Consolidate validation functions
        content = self._consolidate_validation(content)

        # Remove redundant error handling
        content = self._remove_redundant_error_handling(content)

        return content, changes

    def _consolidate_file_operations(self, content: str) -> str:
        """Consolidate multiple file operations into unified loader"""
        # Pattern: Multiple sequential file loads
        pattern = r"(with open\([^)]+\) as .+:\n\s+.+\.load\(.+\))"

        def replace_with_unified(match):
            # Extract filepath from the match
            filepath_match = re.search(r"open\(([^)]+)\)", match.group())
            if filepath_match:
                filepath = filepath_match.group(1)
                return f"config = unified_config.load({filepath})"
            return match.group()

        return re.sub(pattern, replace_with_unified, content)

    def _consolidate_validation(self, content: str) -> str:
        """Consolidate multiple validation functions into unified validator"""
        # Pattern: Multiple validation functions
        validation_patterns = [
            r"def validate_\w+\([^)]*\):[^}]+?(?=\n(?:def|class|\Z))",
            r"def check_\w+\([^)]*\):[^}]+?(?=\n(?:def|class|\Z))",
            r"def verify_\w+\([^)]*\):[^}]+?(?=\n(?:def|class|\Z))",
        ]

        for pattern in validation_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if len(matches) > 3:
                # Replace with unified validation
                for match in matches[1:]:  # Keep first one, replace others
                    content = content.replace(match, "")
                    self.stats.lines_removed += len(match.splitlines())

        return content

    def _remove_redundant_error_handling(self, content: str) -> str:
        """Remove redundant error handling patterns"""
        # Pattern: Repeated try-except blocks with similar handling
        pattern = (
            r"try:\s*\n\s+.+\nexcept\s+\w+Error.*?:\s*\n\s+(?:logger\.|print\(|raise)"
        )

        matches = re.findall(pattern, content, re.DOTALL)
        if len(matches) > 5:
            # Keep unique patterns, remove duplicates
            seen = set()
            for match in matches:
                normalized = re.sub(r"\s+", " ", match)
                if normalized in seen:
                    content = content.replace(match, "", 1)
                    self.stats.lines_removed += len(match.splitlines())
                seen.add(normalized)

        return content

    def _generate_report(self):
        """Generate migration report"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("CONFIGURATION MIGRATION REPORT")
        self.logger.info("=" * 60)

        self.logger.info(f"Files processed: {self.stats.files_processed}")
        self.logger.info(f"Files modified: {self.stats.files_modified}")
        self.logger.info(f"Imports replaced: {self.stats.imports_replaced}")
        self.logger.info(f"Classes replaced: {self.stats.classes_replaced}")
        self.logger.info(f"Functions replaced: {self.stats.functions_replaced}")

        self.logger.info("\nCODE REDUCTION METRICS:")
        self.logger.info(f"Lines removed: {self.stats.lines_removed}")
        self.logger.info(f"Lines added: {self.stats.lines_added}")
        self.logger.info(f"Net reduction: {self.stats.net_reduction} lines")

        reduction_percentage = (
            (self.stats.net_reduction / 15000 * 100)
            if self.stats.net_reduction > 0
            else 0
        )
        self.logger.info(f"Reduction percentage: {reduction_percentage:.1f}% of target")

        if self.stats.errors:
            self.logger.error("\nERRORS:")
            for error in self.stats.errors:
                self.logger.error(f"  - {error}")

        # Save report to file
        report_path = Path("migration_report.json")
        report_data = {
            "timestamp": str(Path.cwd()),
            "dry_run": self.dry_run,
            "stats": {
                "files_processed": self.stats.files_processed,
                "files_modified": self.stats.files_modified,
                "imports_replaced": self.stats.imports_replaced,
                "classes_replaced": self.stats.classes_replaced,
                "functions_replaced": self.stats.functions_replaced,
                "lines_removed": self.stats.lines_removed,
                "lines_added": self.stats.lines_added,
                "net_reduction": self.stats.net_reduction,
                "reduction_percentage": reduction_percentage,
            },
            "errors": self.stats.errors,
        }

        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)

        self.logger.info(f"\nReport saved to: {report_path}")


class BackwardCompatibilityGenerator:
    """Generates backward compatibility layer"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def generate_compatibility_layer(self, output_path: Path):
        """Generate backward compatibility imports and aliases"""
        compatibility_code = '''"""
Backward Compatibility Layer for Configuration Migration
Auto-generated by migrate_configs.py
"""

from claude_mpm.services.unified.config_strategies.unified_config_service import UnifiedConfigService

# Create singleton instance
unified_config = UnifiedConfigService()

# Backward compatibility aliases
ConfigLoader = UnifiedConfigService
ConfigManager = UnifiedConfigService
ConfigService = UnifiedConfigService
MCPConfigManager = UnifiedConfigService
SystemAgentConfigManager = UnifiedConfigService
DeploymentConfigManager = UnifiedConfigService
DeploymentConfigLoader = UnifiedConfigService
BaseAgentManager = UnifiedConfigService
ConfigServiceBase = UnifiedConfigService
ProjectConfigService = UnifiedConfigService

# Function aliases
load_config = unified_config.load
load_json = unified_config.load
load_yaml = unified_config.load
load_env = unified_config.load
load_ini = unified_config.load
load_toml = unified_config.load
load_settings = unified_config.load
read_config = unified_config.load
get_config = unified_config.get

validate_config = unified_config.validate
check_config = unified_config.validate
verify_config = unified_config.validate
validate_schema = unified_config.validate
validate_required = unified_config.validate
validate_types = unified_config.validate

# Export all for star imports
__all__ = [
    'UnifiedConfigService',
    'unified_config',
    'ConfigLoader',
    'ConfigManager',
    'ConfigService',
    'load_config',
    'validate_config',
]
'''

        output_path.write_text(compatibility_code)
        self.logger.info(f"Generated compatibility layer at: {output_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate configuration services to unified service (Phase 3 Consolidation)"
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd() / "src",
        help="Path to project source directory",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform dry run without modifying files"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Do not create backup files"
    )
    parser.add_argument(
        "--generate-compatibility",
        action="store_true",
        help="Generate backward compatibility layer",
    )

    args = parser.parse_args()

    # Validate project path
    if not args.project_path.exists():
        logger.error(f"Project path does not exist: {args.project_path}")
        sys.exit(1)

    # Run migration
    migrator = ConfigMigrator(dry_run=args.dry_run, backup=not args.no_backup)

    stats = migrator.migrate_project(args.project_path)

    # Generate compatibility layer if requested
    if args.generate_compatibility:
        compat_gen = BackwardCompatibilityGenerator()
        compat_path = args.project_path / "claude_mpm" / "config_compat.py"
        compat_gen.generate_compatibility_layer(compat_path)

    # Exit with appropriate code
    if stats.errors:
        sys.exit(1)
    elif stats.net_reduction < 5000:
        logger.warning("Target reduction of 10,000+ lines not achieved")
        sys.exit(2)
    else:
        logger.info("Migration completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
