#!/usr/bin/env python3
"""Test that analyze-code command works via subprocess.

This test verifies that:
1. The analyze-code command can be invoked via subprocess
2. It produces valid JSON output when --output json is specified
3. The JSON contains expected fields (nodes, stats)
4. The analysis produces meaningful results (files processed, code elements found)

This is particularly important for dashboard integration where the command
is called via subprocess to analyze codebases.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_analyze_code_subprocess():
    """Test running analyze-code via subprocess."""

    # Test with a small directory
    test_path = Path(__file__).parent  # tests directory

    # Build command similar to what dashboard uses
    cmd = [
        sys.executable,
        "-m",
        "claude_mpm",
        "analyze-code",
        str(test_path),
        "--output",
        "json",
        "--max-depth",
        "2",  # Limit depth for faster test
    ]

    print(f"Running command: {' '.join(cmd)}")

    # Run subprocess
    result = subprocess.run(
        cmd, check=False, capture_output=True, text=True, timeout=30
    )

    print(f"Return code: {result.returncode}")

    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        return False

    # The command outputs progress messages before JSON, so we need to extract just the JSON
    stdout_lines = result.stdout.split("\n")

    # Look for JSON starting with '{'
    json_start = -1
    for i, line in enumerate(stdout_lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    if json_start == -1:
        print("No JSON found in output")
        print(f"Full output:\n{result.stdout}")
        return False

    # Extract JSON part
    json_lines = stdout_lines[json_start:]
    json_text = "\n".join(json_lines).strip()

    # Try to parse JSON output
    try:
        data = json.loads(json_text)

        # Validate JSON structure
        assert "nodes" in data, "JSON missing 'nodes' field"
        assert "stats" in data, "JSON missing 'stats' field"

        nodes = data["nodes"]
        stats = data["stats"]

        print(f"✓ Got valid JSON with {len(nodes)} nodes")
        print(
            f"✓ Analysis stats: files_processed={stats.get('files_processed', 0)}, "
            f"classes={stats.get('classes', 0)}, functions={stats.get('functions', 0)}"
        )

        # Basic sanity checks
        assert len(nodes) > 0, "No nodes found in analysis"
        assert stats.get("files_processed", 0) > 0, "No files processed"

        print("✓ All validation checks passed")
        return True

    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON: {e}")
        print(f"JSON text was: {json_text[:500]}...")
        return False
    except AssertionError as e:
        print(f"✗ JSON validation failed: {e}")
        return False


def test_analyze_code_subprocess_pytest():
    """Pytest version of the subprocess test."""
    success = test_analyze_code_subprocess()
    assert success, "Subprocess analyze-code command failed"


if __name__ == "__main__":
    success = test_analyze_code_subprocess()
    sys.exit(0 if success else 1)
