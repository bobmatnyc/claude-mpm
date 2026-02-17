#!/usr/bin/env python3
"""Test script for Mermaid rendering functionality.

This script tests the render_mermaid_to_doc implementation by:
1. Verifying npx is available
2. Testing mermaid-cli rendering locally
3. Checking the implementation's syntax and imports
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_npx_available():
    """Verify npx is installed."""
    print("Testing npx availability...")
    try:
        result = subprocess.run(  # nosec B603 B607
            ["npx", "--version"],
            capture_output=True,
            check=True,
            text=True,
        )
        print(f"✓ npx is available: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("✗ npx is not installed")
        return False


def test_mermaid_cli():
    """Test mermaid-cli can render a diagram."""
    print("\nTesting mermaid-cli rendering...")

    test_diagram = """graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Option 1]
    B -->|No| D[Option 2]
    C --> E[End]
    D --> E
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test.mmd"
        output_path = Path(tmpdir) / "test.svg"

        # Write test diagram
        input_path.write_text(test_diagram, encoding="utf-8")

        # Render with mermaid-cli
        try:
            _ = subprocess.run(  # nosec B603 B607
                [
                    "npx",
                    "-y",
                    "@mermaid-js/mermaid-cli@11.12.0",
                    "-i",
                    str(input_path),
                    "-o",
                    str(output_path),
                ],
                capture_output=True,
                check=True,
                text=True,
                timeout=30,
            )
            print("✓ Mermaid-cli rendered successfully")
            print(f"  Output: {output_path}")

            # Check output exists
            if output_path.exists():
                size = output_path.stat().st_size
                print(f"  File size: {size} bytes")
                print("✓ Output file created successfully")
                return True
            print("✗ Output file not created")
            return False

        except subprocess.CalledProcessError as e:
            print(f"✗ Mermaid rendering failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            print("✗ Mermaid rendering timed out")
            return False


def test_import_implementation():
    """Test that the implementation can be imported."""
    print("\nTesting implementation imports...")
    try:
        from src.claude_mpm.mcp.google_workspace_server import GoogleWorkspaceServer

        print("✓ GoogleWorkspaceServer imported successfully")

        # Check that the method exists
        if hasattr(GoogleWorkspaceServer, "_render_mermaid_to_doc"):
            print("✓ _render_mermaid_to_doc method exists")
            return True
        print("✗ _render_mermaid_to_doc method not found")
        return False

    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Mermaid Rendering Implementation Tests")
    print("=" * 60)

    results = []
    results.append(("NPX Available", test_npx_available()))
    results.append(("Mermaid-CLI Rendering", test_mermaid_cli()))
    results.append(("Implementation Import", test_import_implementation()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✓ All tests passed!")
        return 0
    print("✗ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
