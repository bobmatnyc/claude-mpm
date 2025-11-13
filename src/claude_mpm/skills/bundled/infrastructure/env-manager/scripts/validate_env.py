#!/usr/bin/env python3
"""
Environment variable validation script.

This script validates .env files for:
- Structure (valid key-value format, no duplicates, proper quoting)
- Completeness (compare with .env.example)
- Naming conventions (UPPERCASE_WITH_UNDERSCORES)
- Framework-specific rules (Next.js, Express, Flask, etc.)

Security: NEVER logs actual secret values.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


class ValidationError:
    """Represents a validation error."""

    def __init__(
        self, line: Optional[int], key: str, message: str, severity: str = "error"
    ):
        self.line = line
        self.key = key
        self.message = message
        self.severity = severity  # "error" or "warning"

    def to_dict(self) -> Dict:
        return {
            "line": self.line,
            "key": self.key,
            "message": self.message,
            "severity": self.severity,
        }

    def __str__(self) -> str:
        prefix = "❌" if self.severity == "error" else "⚠️ "
        line_info = f"Line {self.line}: " if self.line else ""
        return f"{prefix} {line_info}{self.key}: {self.message}"


class EnvValidator:
    """Validates environment variable files."""

    # Valid variable name pattern: UPPERCASE_WITH_UNDERSCORES
    VALID_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

    # Framework-specific prefixes
    FRAMEWORK_PREFIXES = {
        "nextjs": ["NEXT_PUBLIC_", "NEXT_"],
        "vite": ["VITE_"],
        "react": ["REACT_APP_"],
    }

    # Secret indicators (variables that should never be in NEXT_PUBLIC_, etc.)
    SECRET_INDICATORS = ["secret", "key", "password", "token", "private", "api_key"]

    def __init__(self, framework: Optional[str] = None, strict: bool = False):
        self.framework = framework
        self.strict = strict
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """Parse .env file safely. Returns dict of key-value pairs."""
        vars_dict = {}

        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Check for valid format
                if "=" not in line:
                    self.errors.append(
                        ValidationError(
                            line_num,
                            "",
                            f"Invalid format (missing =): {line[:50]}",
                            "error",
                        )
                    )
                    continue

                # Split on first = only
                key, value = line.split("=", 1)
                key = key.strip()

                # Remove quotes from value
                value = value.strip()
                if value and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]

                vars_dict[key] = value

        return vars_dict

    def validate_structure(self, env_file: Path) -> List[ValidationError]:
        """Validate basic file structure."""
        errors = []

        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Check for inline comments (warning)
                if "#" in line and not line.startswith("#"):
                    key_value = line.split("#", 1)[0]
                    if "=" in key_value:
                        key, value = key_value.split("=", 1)
                        # Check if # is inside quotes
                        value = value.strip()
                        if not (value.startswith('"') or value.startswith("'")):
                            errors.append(
                                ValidationError(
                                    line_num,
                                    key.strip(),
                                    "Possible inline comment (not all parsers support this)",
                                    "warning",
                                )
                            )

                # Check format
                if "=" not in line:
                    errors.append(
                        ValidationError(
                            line_num,
                            "",
                            f"Invalid format (missing =): {line[:50]}",
                            "error",
                        )
                    )
                    continue

                key, value = line.split("=", 1)
                key = key.strip()

                # Validate key name
                if not self.VALID_NAME_PATTERN.match(key):
                    errors.append(
                        ValidationError(
                            line_num,
                            key,
                            "Invalid naming (use UPPERCASE_WITH_UNDERSCORES)",
                            "error",
                        )
                    )

                # Check for spaces without quotes
                value = value.strip()
                if value and " " in value:
                    if not (value.startswith('"') or value.startswith("'")):
                        errors.append(
                            ValidationError(
                                line_num,
                                key,
                                "Value with spaces should be quoted",
                                "warning",
                            )
                        )

        return errors

    def check_duplicates(self, env_file: Path) -> Dict[str, List[int]]:
        """Find duplicate keys and their line numbers."""
        keys: Dict[str, List[int]] = {}

        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key in keys:
                        keys[key].append(line_num)
                    else:
                        keys[key] = [line_num]

        # Return only duplicates
        duplicates = {k: v for k, v in keys.items() if len(v) > 1}

        # Add errors for duplicates
        for key, lines in duplicates.items():
            self.errors.append(
                ValidationError(
                    None,
                    key,
                    f"Duplicate key found on lines: {', '.join(map(str, lines))}",
                    "error",
                )
            )

        return duplicates

    def compare_env_files(self, env_file: Path, example_file: Path) -> Dict:
        """Compare .env against .env.example."""
        if not example_file.exists():
            self.warnings.append(
                ValidationError(
                    None, "", f".env.example not found: {example_file}", "warning"
                )
            )
            return {"missing": set(), "extra": set(), "common": set()}

        env_vars = set(self.parse_env_file(env_file).keys())
        example_vars = set(self.parse_env_file(example_file).keys())

        missing = example_vars - env_vars
        extra = env_vars - example_vars
        common = env_vars & example_vars

        # Add errors for missing required variables
        for var in missing:
            self.errors.append(
                ValidationError(
                    None,
                    var,
                    "Required variable missing (defined in .env.example)",
                    "error",
                )
            )

        # Add warnings for undocumented variables
        for var in extra:
            self.warnings.append(
                ValidationError(
                    None, var, "Variable not documented in .env.example", "warning"
                )
            )

        return {"missing": missing, "extra": extra, "common": common}

    def validate_framework_specific(self, env_file: Path) -> List[ValidationError]:
        """Validate framework-specific rules."""
        errors = []
        vars_dict = self.parse_env_file(env_file)

        if self.framework == "nextjs":
            errors.extend(self._validate_nextjs(vars_dict))
        elif self.framework == "vite":
            errors.extend(self._validate_vite(vars_dict))
        elif self.framework == "react":
            errors.extend(self._validate_react(vars_dict))
        elif self.framework == "nodejs":
            errors.extend(self._validate_nodejs(vars_dict))
        elif self.framework == "flask":
            errors.extend(self._validate_flask(vars_dict))

        return errors

    def _validate_nextjs(self, vars_dict: Dict[str, str]) -> List[ValidationError]:
        """Validate Next.js environment variables."""
        errors = []

        for key, value in vars_dict.items():
            # Check for secrets in NEXT_PUBLIC_ vars
            if key.startswith("NEXT_PUBLIC_"):
                if any(
                    indicator in key.lower() for indicator in self.SECRET_INDICATORS
                ):
                    errors.append(
                        ValidationError(
                            None,
                            key,
                            "SECURITY: Secret in NEXT_PUBLIC_ variable (exposed to browser)",
                            "error",
                        )
                    )

            # Check for API URLs without NEXT_PUBLIC_ prefix
            if "api" in key.lower() and "url" in key.lower():
                if not key.startswith("NEXT_PUBLIC_") and not key.endswith("_SECRET"):
                    errors.append(
                        ValidationError(
                            None,
                            key,
                            "API URL without NEXT_PUBLIC_ prefix (not accessible client-side)",
                            "warning",
                        )
                    )

        return errors

    def _validate_vite(self, vars_dict: Dict[str, str]) -> List[ValidationError]:
        """Validate Vite environment variables."""
        errors = []

        for key in vars_dict:
            # Check for secrets in VITE_ vars
            if key.startswith("VITE_"):
                if any(
                    indicator in key.lower() for indicator in self.SECRET_INDICATORS
                ):
                    errors.append(
                        ValidationError(
                            None,
                            key,
                            "SECURITY: Secret in VITE_ variable (exposed to browser)",
                            "error",
                        )
                    )

            # Warn about non-VITE_ vars
            elif key not in ["NODE_ENV", "PORT"]:
                errors.append(
                    ValidationError(
                        None,
                        key,
                        "Variable not prefixed with VITE_ (not accessible in client code)",
                        "warning",
                    )
                )

        return errors

    def _validate_react(self, vars_dict: Dict[str, str]) -> List[ValidationError]:
        """Validate Create React App environment variables."""
        errors = []

        for key in vars_dict:
            # Check for secrets in REACT_APP_ vars
            if key.startswith("REACT_APP_"):
                if any(
                    indicator in key.lower() for indicator in self.SECRET_INDICATORS
                ):
                    errors.append(
                        ValidationError(
                            None,
                            key,
                            "SECURITY: Secret in REACT_APP_ variable (exposed to browser)",
                            "error",
                        )
                    )

        return errors

    def _validate_nodejs(self, vars_dict: Dict[str, str]) -> List[ValidationError]:
        """Validate Node.js environment variables."""
        errors = []

        # Check NODE_ENV value
        if "NODE_ENV" in vars_dict:
            valid_values = ["development", "production", "test"]
            if vars_dict["NODE_ENV"] not in valid_values:
                # SECURITY: Never expose actual variable values in error messages
                # to prevent accidental secret leakage in logs/CI output
                errors.append(
                    ValidationError(
                        None,
                        "NODE_ENV",
                        f"Invalid value for NODE_ENV, expected one of {valid_values}",
                        "error",
                    )
                )

        # Check PORT is numeric
        if "PORT" in vars_dict:
            try:
                port = int(vars_dict["PORT"])
                if not (1 <= port <= 65535):
                    errors.append(
                        ValidationError(
                            None, "PORT", "PORT must be between 1 and 65535", "error"
                        )
                    )
            except ValueError:
                errors.append(
                    ValidationError(None, "PORT", "PORT must be numeric", "error")
                )

        return errors

    def _validate_flask(self, vars_dict: Dict[str, str]) -> List[ValidationError]:
        """Validate Flask environment variables."""
        errors = []

        # Check required vars
        required = ["FLASK_APP", "SECRET_KEY"]
        for var in required:
            if var not in vars_dict:
                errors.append(
                    ValidationError(
                        None, var, "Required Flask variable missing", "error"
                    )
                )

        # Check FLASK_APP ends with .py
        if "FLASK_APP" in vars_dict:
            if not vars_dict["FLASK_APP"].endswith(".py"):
                errors.append(
                    ValidationError(
                        None,
                        "FLASK_APP",
                        "FLASK_APP should point to a .py file",
                        "warning",
                    )
                )

        # Check FLASK_ENV value
        if "FLASK_ENV" in vars_dict:
            valid_values = ["development", "production"]
            if vars_dict["FLASK_ENV"] not in valid_values:
                errors.append(
                    ValidationError(
                        None,
                        "FLASK_ENV",
                        f"Invalid value, expected one of {valid_values}",
                        "error",
                    )
                )

        return errors

    def validate(self, env_file: Path, example_file: Optional[Path] = None) -> Dict:
        """Run all validations. Returns summary dict."""
        self.errors = []
        self.warnings = []

        # 1. Structure validation
        structure_errors = self.validate_structure(env_file)
        self.errors.extend([e for e in structure_errors if e.severity == "error"])
        self.warnings.extend([e for e in structure_errors if e.severity == "warning"])

        # 2. Check duplicates
        self.check_duplicates(env_file)

        # 3. Compare with .env.example
        if example_file:
            self.compare_env_files(env_file, example_file)

        # 4. Framework-specific validation
        if self.framework:
            framework_errors = self.validate_framework_specific(env_file)
            self.errors.extend([e for e in framework_errors if e.severity == "error"])
            self.warnings.extend(
                [e for e in framework_errors if e.severity == "warning"]
            )

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


def generate_example(env_file: Path, output_file: Path) -> None:
    """Generate .env.example from .env file (with values removed)."""
    with open(env_file) as f:
        lines = f.readlines()

    with open(output_file, "w") as f:
        for line in lines:
            line = line.strip()

            # Keep comments and empty lines
            if not line or line.startswith("#"):
                f.write(line + "\n")
                continue

            # Replace values with placeholders
            if "=" in line:
                key, _ = line.split("=", 1)
                f.write(f"{key}=your-{key.lower().replace('_', '-')}-here\n")

    print(f"✅ Generated {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Validate environment variable files")
    parser.add_argument("file", type=Path, help="Path to .env file to validate")
    parser.add_argument(
        "--compare-with",
        type=Path,
        help="Compare with .env.example file",
        metavar="FILE",
    )
    parser.add_argument(
        "--framework",
        choices=["nextjs", "vite", "react", "nodejs", "flask", "generic"],
        help="Framework-specific validation",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--quiet", action="store_true", help="Only show errors, not warnings"
    )
    parser.add_argument(
        "--generate-example",
        type=Path,
        help="Generate .env.example file",
        metavar="OUTPUT",
    )

    args = parser.parse_args()

    # Check input file exists
    if not args.file.exists():
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(2)

    # Generate example if requested
    if args.generate_example:
        generate_example(args.file, args.generate_example)
        return

    # Run validation
    validator = EnvValidator(framework=args.framework, strict=args.strict)
    result = validator.validate(args.file, example_file=args.compare_with)

    # Output results
    if args.json:
        output = {
            "valid": result["valid"],
            "file": str(args.file),
            "errors": [e.to_dict() for e in result["errors"]],
            "warnings": [w.to_dict() for w in result["warnings"]],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n🔍 Validating: {args.file}")
        if args.framework:
            print(f"📦 Framework: {args.framework}")
        print()

        # Show errors
        if result["errors"]:
            print("❌ Errors:")
            for error in result["errors"]:
                print(f"  {error}")
            print()

        # Show warnings (unless quiet)
        if result["warnings"] and not args.quiet:
            print("⚠️  Warnings:")
            for warning in result["warnings"]:
                print(f"  {warning}")
            print()

        # Summary
        if result["valid"]:
            print("✅ Validation passed!")
        else:
            print(f"❌ Validation failed: {result['error_count']} error(s)")

        if not args.quiet:
            print(
                f"📊 Summary: {result['error_count']} errors, {result['warning_count']} warnings"
            )

    # Exit code
    if result["errors"] or (args.strict and result["warnings"]):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
