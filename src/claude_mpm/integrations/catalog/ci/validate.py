"""CI validation script for integration catalog (Phase 3).

Validates all integrations in the catalog and checks index consistency.
Can be run from CI/CD pipelines.

Usage:
    python -m claude_mpm.integrations.catalog.ci.validate

Exit codes:
    0 - All validations passed
    1 - One or more validations failed
"""

from __future__ import annotations

import sys
from pathlib import Path  # noqa: TC003 - used at runtime
from typing import NamedTuple

from claude_mpm.integrations.catalog import CATALOG_DIR
from claude_mpm.integrations.core.index_generator import CatalogIndexGenerator
from claude_mpm.integrations.core.manifest import IntegrationManifest


class ValidationResult(NamedTuple):
    """Result of a validation check."""

    name: str
    passed: bool
    errors: list[str]


def validate_manifest(manifest_path: Path) -> ValidationResult:
    """Validate a single integration manifest.

    Args:
        manifest_path: Path to integration.yaml file.

    Returns:
        ValidationResult with pass/fail and errors.
    """
    name = manifest_path.parent.name
    errors: list[str] = []

    try:
        manifest = IntegrationManifest.from_yaml(manifest_path)
        manifest_errors = manifest.validate()
        errors.extend(manifest_errors)
    except Exception as e:
        errors.append(f"Failed to parse manifest: {e}")

    return ValidationResult(
        name=name,
        passed=len(errors) == 0,
        errors=errors,
    )


def validate_catalog(catalog_dir: Path | None = None) -> list[ValidationResult]:
    """Validate all integrations in the catalog.

    Args:
        catalog_dir: Path to catalog directory. Defaults to package catalog.

    Returns:
        List of ValidationResult for each integration.
    """
    if catalog_dir is None:
        catalog_dir = CATALOG_DIR

    results: list[ValidationResult] = []

    for item in sorted(catalog_dir.iterdir()):
        # Skip non-directories and special files
        if not item.is_dir():
            continue
        if item.name.startswith(("_", ".", "ci")):
            continue

        manifest_path = item / "integration.yaml"
        if not manifest_path.exists():
            results.append(
                ValidationResult(
                    name=item.name,
                    passed=False,
                    errors=["Missing integration.yaml"],
                )
            )
            continue

        results.append(validate_manifest(manifest_path))

    return results


def validate_index(catalog_dir: Path | None = None) -> ValidationResult:
    """Validate _index.yaml is up to date.

    Args:
        catalog_dir: Path to catalog directory. Defaults to package catalog.

    Returns:
        ValidationResult for index validation.
    """
    if catalog_dir is None:
        catalog_dir = CATALOG_DIR

    generator = CatalogIndexGenerator()
    is_valid, discrepancies = generator.verify_index(catalog_dir)

    return ValidationResult(
        name="_index.yaml",
        passed=is_valid,
        errors=discrepancies,
    )


def run_all_validations(
    catalog_dir: Path | None = None,
    check_index: bool = True,
) -> tuple[bool, list[ValidationResult]]:
    """Run all catalog validations.

    Args:
        catalog_dir: Path to catalog directory. Defaults to package catalog.
        check_index: Whether to validate _index.yaml.

    Returns:
        Tuple of (all_passed, list of results).
    """
    results: list[ValidationResult] = []

    # Validate all manifests
    results.extend(validate_catalog(catalog_dir))

    # Validate index
    if check_index:
        results.append(validate_index(catalog_dir))

    all_passed = all(r.passed for r in results)
    return all_passed, results


def print_results(results: list[ValidationResult]) -> None:
    """Print validation results to stdout.

    Args:
        results: List of validation results.
    """
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(f"\n{'=' * 60}")
    print("CATALOG VALIDATION RESULTS")
    print(f"{'=' * 60}\n")

    if passed:
        print(f"PASSED ({len(passed)}):")
        for r in passed:
            print(f"  [OK] {r.name}")

    if failed:
        print(f"\nFAILED ({len(failed)}):")
        for r in failed:
            print(f"  [FAIL] {r.name}")
            for error in r.errors:
                print(f"         - {error}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(passed)} passed, {len(failed)} failed")
    print(f"{'=' * 60}\n")


def main() -> int:
    """Main entry point for CI validation.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    print("Running catalog validation...")

    all_passed, results = run_all_validations()
    print_results(results)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
