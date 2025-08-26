#!/usr/bin/env python3
"""
Configuration Validation Script for Claude MPM

WHY: Configuration errors, especially YAML syntax errors, can cause silent failures
in the response logging system. This script proactively validates configuration
files and provides clear, actionable error messages to help users fix issues.

DESIGN DECISIONS:
- Exit codes for CI/CD integration (0=success, 1=error, 2=warning)
- Detailed error messages with line numbers and suggestions
- Checks both syntax and semantic validity
- Validates required fields and data types
- Provides fix suggestions for common mistakes

USAGE:
    python scripts/validate_configuration.py
    python scripts/validate_configuration.py --config .claude-mpm/configuration.yaml
    python scripts/validate_configuration.py --strict  # Fail on warnings
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try to import YAML - provide helpful error if missing
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("ERROR: PyYAML is required for configuration validation", file=sys.stderr)
    print("Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from claude_mpm.core.config import Config


class ConfigurationValidator:
    """Validates Claude MPM configuration files with detailed error reporting.

    WHY: Users need clear, actionable feedback when their configuration is invalid.
    This validator checks both syntax and semantic validity, providing specific
    guidance on how to fix issues.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the configuration validator.

        Args:
            verbose: Enable verbose output for debugging
        """
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []

    def validate_yaml_syntax(
        self, file_path: Path
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate YAML syntax and return parsed content.

        WHY: YAML syntax errors are the most common configuration problem.
        We need to catch these early and provide helpful error messages.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Tuple of (is_valid, parsed_config)
        """
        if not file_path.exists():
            self.errors.append(f"Configuration file not found: {file_path}")
            self.suggestions.append(
                f"Create a configuration file with: "
                f"mkdir -p {file_path.parent} && touch {file_path}"
            )
            return False, None

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for common YAML mistakes before parsing
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Check for tabs (YAML requires spaces)
                if "\t" in line:
                    self.errors.append(
                        f"Line {i}: YAML files must use spaces, not tabs"
                    )
                    self.suggestions.append(
                        f"Replace tabs with spaces on line {i}: {line.strip()}"
                    )

                # Check for invalid boolean values
                if re.search(r":\s*(True|False|YES|NO|Yes|No)\s*($|#)", line):
                    self.warnings.append(
                        f"Line {i}: Use lowercase 'true/false' for booleans in YAML"
                    )
                    self.suggestions.append(
                        f"Change '{line.strip()}' to use lowercase boolean values"
                    )

            # Try to parse the YAML
            config = yaml.safe_load(content)

            if config is None:
                config = {}  # Empty file is valid but empty

            if self.verbose:
                print(f"✓ YAML syntax is valid for {file_path}")

            return True, config

        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error: {e}")

            # Extract line number from error if available
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                self.errors.append(
                    f"Error at line {mark.line + 1}, column {mark.column + 1}"
                )

                # Try to provide context
                try:
                    with open(file_path) as f:
                        lines = f.readlines()
                        if mark.line < len(lines):
                            self.errors.append(
                                f"Problem line: {lines[mark.line].rstrip()}"
                            )
                except:
                    pass

            # Common YAML error patterns and suggestions
            error_str = str(e).lower()
            if "found character" in error_str and "tab" in error_str:
                self.suggestions.append(
                    "Replace all tabs with spaces. You can use: "
                    "sed -i '' 's/\\t/    /g' " + str(file_path)
                )
            elif "mapping values" in error_str:
                self.suggestions.append(
                    "Check indentation - YAML requires consistent spacing. "
                    "Make sure all nested items are properly indented."
                )
            elif "duplicate key" in error_str:
                self.suggestions.append(
                    "Remove duplicate keys - each key should appear only once "
                    "at the same level in the configuration."
                )

            return False, None

        except Exception as e:
            self.errors.append(f"Failed to read configuration file: {e}")
            return False, None

    def validate_structure(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and required fields.

        WHY: Even valid YAML might have incorrect structure or missing required
        fields. We validate the semantic correctness of the configuration.

        Args:
            config: Parsed configuration dictionary

        Returns:
            True if structure is valid
        """
        is_valid = True

        # Check response_logging configuration
        if "response_logging" in config:
            rl_config = config["response_logging"]

            # Validate boolean fields
            bool_fields = ["enabled", "use_async", "debug_sync", "enable_compression"]
            for field in bool_fields:
                if field in rl_config and not isinstance(rl_config[field], bool):
                    self.errors.append(
                        f"response_logging.{field} must be a boolean (true/false), "
                        f"got {type(rl_config[field]).__name__}: {rl_config[field]}"
                    )
                    self.suggestions.append(
                        f"Change 'response_logging.{field}' to either 'true' or 'false'"
                    )
                    is_valid = False

            # Validate format field
            if "format" in rl_config:
                valid_formats = ["json", "syslog", "journald"]
                if rl_config["format"] not in valid_formats:
                    self.errors.append(
                        f"response_logging.format must be one of {valid_formats}, "
                        f"got '{rl_config['format']}'"
                    )
                    self.suggestions.append(
                        f"Change 'response_logging.format' to one of: {', '.join(valid_formats)}"
                    )
                    is_valid = False

            # Validate session_directory
            if "session_directory" in rl_config:
                session_dir = rl_config["session_directory"]
                if not isinstance(session_dir, str):
                    self.errors.append(
                        f"response_logging.session_directory must be a string path, "
                        f"got {type(session_dir).__name__}"
                    )
                    is_valid = False
                else:
                    # Check if parent directory exists
                    session_path = Path(session_dir)
                    if session_path.is_absolute() and not session_path.parent.exists():
                        self.warnings.append(
                            f"Parent directory for session_directory does not exist: "
                            f"{session_path.parent}"
                        )
                        self.suggestions.append(
                            f"Create directory with: mkdir -p {session_path.parent}"
                        )

            # Validate max_queue_size
            if "max_queue_size" in rl_config:
                queue_size = rl_config["max_queue_size"]
                if not isinstance(queue_size, int) or queue_size <= 0:
                    self.errors.append(
                        f"response_logging.max_queue_size must be a positive integer, "
                        f"got {queue_size}"
                    )
                    self.suggestions.append(
                        "Set max_queue_size to a positive number like 10000"
                    )
                    is_valid = False

        # Check memory configuration
        if "memory" in config:
            mem_config = config["memory"]

            if "enabled" in mem_config and not isinstance(mem_config["enabled"], bool):
                self.errors.append(
                    f"memory.enabled must be a boolean, got {type(mem_config['enabled']).__name__}"
                )
                is_valid = False

            # Check limits
            if "limits" in mem_config:
                limits = mem_config["limits"]
                int_fields = [
                    "default_size_kb",
                    "max_sections",
                    "max_items_per_section",
                    "max_line_length",
                ]
                for field in int_fields:
                    if field in limits:
                        value = limits[field]
                        if not isinstance(value, int) or value <= 0:
                            self.errors.append(
                                f"memory.limits.{field} must be a positive integer, got {value}"
                            )
                            is_valid = False

        # Check health monitoring configuration
        if "health_thresholds" in config:
            thresholds = config["health_thresholds"]

            # CPU percentage should be 0-100
            if "cpu_percent" in thresholds:
                cpu = thresholds["cpu_percent"]
                if not isinstance(cpu, (int, float)) or cpu < 0 or cpu > 100:
                    self.errors.append(
                        f"health_thresholds.cpu_percent must be between 0-100, got {cpu}"
                    )
                    self.suggestions.append(
                        "Set cpu_percent to a value between 0 and 100 (e.g., 80.0)"
                    )
                    is_valid = False

            # Memory should be positive
            if "memory_mb" in thresholds:
                mem = thresholds["memory_mb"]
                if not isinstance(mem, (int, float)) or mem <= 0:
                    self.errors.append(
                        f"health_thresholds.memory_mb must be positive, got {mem}"
                    )
                    is_valid = False

        return is_valid

    def validate_config_loading(self, file_path: Path) -> bool:
        """Validate that configuration can be loaded by the actual Config class.

        WHY: Even if YAML is valid and structure looks good, the actual Config
        class might fail to load it. This tests the real loading process.

        Args:
            file_path: Path to configuration file

        Returns:
            True if configuration loads successfully
        """
        try:
            # Try to load with the actual Config class
            config = Config(config_file=file_path)

            # Test getting some key values
            test_keys = [
                "response_logging.enabled",
                "memory.enabled",
                "health_thresholds.cpu_percent",
            ]

            for key in test_keys:
                value = config.get(key)
                if self.verbose and value is not None:
                    print(f"  {key}: {value}")

            if self.verbose:
                print("✓ Configuration loads successfully with Config class")

            return True

        except Exception as e:
            self.errors.append(f"Failed to load configuration with Config class: {e}")
            self.suggestions.append(
                "Check that all configuration values have the correct types "
                "and that there are no circular references"
            )
            return False

    def validate_file(self, file_path: Path) -> bool:
        """Validate a configuration file completely.

        Args:
            file_path: Path to configuration file

        Returns:
            True if valid, False if there are errors
        """
        print(f"\n{'='*60}")
        print(f"Validating configuration: {file_path}")
        print(f"{'='*60}")

        # Clear previous validation state
        self.errors.clear()
        self.warnings.clear()
        self.suggestions.clear()

        # Step 1: Validate YAML syntax
        syntax_valid, config = self.validate_yaml_syntax(file_path)
        if not syntax_valid:
            return False

        # Step 2: Validate structure
        if config:
            structure_valid = self.validate_structure(config)
            if not structure_valid and self.verbose:
                print("✗ Configuration structure validation failed")

        # Step 3: Validate loading with Config class
        self.validate_config_loading(file_path)

        # Return True only if no errors
        return len(self.errors) == 0

    def print_results(self, strict: bool = False) -> int:
        """Print validation results with helpful formatting.

        Args:
            strict: If True, treat warnings as errors

        Returns:
            Exit code (0=success, 1=errors, 2=warnings)
        """
        # Print errors
        if self.errors:
            print(f"\n🔴 ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")

        # Print warnings
        if self.warnings:
            print(f"\n🟡 WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        # Print suggestions
        if self.suggestions:
            print("\n💡 SUGGESTIONS:")
            for suggestion in self.suggestions:
                print(f"  → {suggestion}")

        # Determine exit code
        if self.errors:
            print(
                f"\n❌ Configuration validation FAILED with {len(self.errors)} error(s)"
            )
            return 1
        if self.warnings and strict:
            print(
                f"\n⚠️  Configuration has {len(self.warnings)} warning(s) (strict mode)"
            )
            return 2
        if self.warnings:
            print(f"\n✅ Configuration is valid with {len(self.warnings)} warning(s)")
            return 0
        print("\n✅ Configuration is VALID")
        return 0


def main():
    """Main entry point for configuration validation."""
    parser = argparse.ArgumentParser(
        description="Validate Claude MPM configuration files"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".claude-mpm/configuration.yaml"),
        help="Path to configuration file (default: .claude-mpm/configuration.yaml)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors (exit code 2)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Check all standard configuration locations",
    )

    args = parser.parse_args()

    validator = ConfigurationValidator(verbose=args.verbose)

    if args.check_all:
        # Check multiple standard locations
        locations = [
            Path(".claude-mpm/configuration.yaml"),
            Path(".claude-mpm/configuration.yml"),
            Path(".claude-mpm/config.yaml"),
            Path(".claude-mpm/config.yml"),
        ]

        found_any = False
        all_valid = True

        for location in locations:
            if location.exists():
                found_any = True
                valid = validator.validate_file(location)
                if not valid:
                    all_valid = False
                exit_code = validator.print_results(args.strict)
                if exit_code != 0:
                    all_valid = False

        if not found_any:
            print("No configuration files found in standard locations")
            print("Standard locations checked:")
            for location in locations:
                print(f"  - {location}")
            return 1

        return 0 if all_valid else 1
    # Validate single file
    valid = validator.validate_file(args.config)
    return validator.print_results(args.strict)


if __name__ == "__main__":
    sys.exit(main())
