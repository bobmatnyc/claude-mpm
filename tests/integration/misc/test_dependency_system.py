#!/usr/bin/env python3
"""
Test script for the agent dependency management system.

This script verifies that:
1. Agent dependencies are correctly parsed from JSON files
2. Dependencies are aggregated properly
3. pyproject.toml is updated correctly
4. Optional dependencies can be installed
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_dependency_parsing():
    """Test that dependencies are correctly parsed from agent files."""
    print("Testing dependency parsing...")

    # Create a test agent file
    test_agent = {
        "schema_version": "1.2.0",
        "agent_id": "test_agent",
        "agent_version": "1.0.0",
        "agent_type": "engineer",
        "metadata": {
            "name": "Test Agent",
            "description": "Test agent for dependency management",
            "tags": ["test"],
        },
        "capabilities": {
            "model": "sonnet",
            "tools": ["Read", "Write"],
            "resource_tier": "standard",
        },
        "dependencies": {
            "python": ["pytest>=7.0", "requests>=2.25.0"],
            "system": ["git"],
            "optional": False,
        },
        "instructions": "Test agent instructions.",
    }

    # Write test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_agent, f, indent=2)
        test_file = Path(f.name)

    try:
        # Add the scripts directory to path for import
        sys.path.insert(0, str(Path(__file__).parent))
        # Test loading and parsing
        from aggregate_agent_dependencies import DependencyAggregator

        aggregator = DependencyAggregator(Path.cwd(), dry_run=True)
        config = aggregator.load_agent_config(test_file)

        assert config is not None, "Failed to load test agent config"
        assert "dependencies" in config, "Dependencies section not found"

        deps = aggregator.extract_dependencies(config)
        assert len(deps) == 2, f"Expected 2 dependencies, got {len(deps)}"
        assert "pytest>=7.0" in deps, "pytest dependency not found"
        assert "requests>=2.25.0" in deps, "requests dependency not found"

        print("✅ Dependency parsing test passed")
        return True

    finally:
        test_file.unlink()


def test_version_conflict_resolution():
    """Test that version conflicts are resolved correctly."""
    print("Testing version conflict resolution...")

    # Add the scripts directory to path for import
    sys.path.insert(0, str(Path(__file__).parent))
    from aggregate_agent_dependencies import DependencyAggregator

    aggregator = DependencyAggregator(Path.cwd(), dry_run=True)

    # Test version conflict resolution
    dependencies = {
        "pytest": [">=6.0", ">=7.0", ">=6.5"],
        "requests": [">=2.25.0", ">=2.20.0"],
        "simple": [""],
    }

    resolved = aggregator.resolve_version_conflicts(dependencies)

    assert "pytest" in resolved, "pytest not in resolved dependencies"
    assert "requests" in resolved, "requests not in resolved dependencies"
    assert "simple" in resolved, "simple not in resolved dependencies"

    # Check that highest version is preferred
    assert "7.0" in resolved["pytest"], f"Expected version 7.0 in {resolved['pytest']}"
    assert (
        "2.25.0" in resolved["requests"]
    ), f"Expected version 2.25.0 in {resolved['requests']}"

    print("✅ Version conflict resolution test passed")
    return True


def test_aggregation_script():
    """Test the full aggregation script."""
    print("Testing aggregation script...")

    script_path = Path(__file__).parent / "aggregate_agent_dependencies.py"
    assert script_path.exists(), "Aggregation script not found"

    # Run the script in dry-run mode
    result = subprocess.run(
        [sys.executable, str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"Aggregation script failed: {result.stderr}"
    assert (
        "Agent dependency aggregation completed successfully" in result.stdout
        or "Agent dependency aggregation completed successfully" in result.stderr
    ), f"Success message not found in output: {result.stdout} {result.stderr}"

    print("✅ Aggregation script test passed")
    return True


def test_pyproject_update():
    """Test that pyproject.toml is updated correctly."""
    print("Testing pyproject.toml update...")

    # Add the scripts directory to path for import
    sys.path.insert(0, str(Path(__file__).parent))
    from aggregate_agent_dependencies import DependencyAggregator

    # Create a temporary directory with test files
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)

        # Create minimal pyproject.toml
        pyproject_content = """[project]
name = "test-project"

[project.optional-dependencies]
dev = ["pytest"]
"""
        (temp_path / "pyproject.toml").write_text(pyproject_content)

        # Create test agent
        (temp_path / ".claude-mpm").mkdir(parents=True)
        (temp_path / ".claude-mpm" / "agents").mkdir()

        test_agent = {
            "schema_version": "1.2.0",
            "agent_id": "test",
            "agent_version": "1.0.0",
            "agent_type": "engineer",
            "metadata": {"name": "Test", "description": "Test", "tags": ["test"]},
            "capabilities": {
                "model": "sonnet",
                "tools": [],
                "resource_tier": "standard",
            },
            "dependencies": {"python": ["numpy>=1.0"]},
            "instructions": "Test",
        }

        with open(temp_path / ".claude-mpm" / "agents" / "test.json", "w") as f:
            json.dump(test_agent, f)

        # Run aggregation
        aggregator = DependencyAggregator(temp_path, dry_run=False)
        success = aggregator.run()

        assert success, "Aggregation failed"

        # Check that pyproject.toml was updated
        import toml

        with open(temp_path / "pyproject.toml") as f:
            updated_config = toml.load(f)

        assert "project" in updated_config
        assert "optional-dependencies" in updated_config["project"]
        assert "agents" in updated_config["project"]["optional-dependencies"]
        assert (
            "numpy>=1.0" in updated_config["project"]["optional-dependencies"]["agents"]
        )

        # Check that existing optional-dependencies are preserved
        assert "dev" in updated_config["project"]["optional-dependencies"]
        assert updated_config["project"]["optional-dependencies"]["dev"] == ["pytest"]

    print("✅ pyproject.toml update test passed")
    return True


def main():
    """Run all tests."""
    print("🧪 Testing Agent Dependency Management System\n")

    tests = [
        test_dependency_parsing,
        test_version_conflict_resolution,
        test_aggregation_script,
        test_pyproject_update,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} failed with exception: {e}")

    print(f"\n📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print(
            "🎉 All tests passed! Agent dependency management system is working correctly."
        )
        return 0
    print("❌ Some tests failed. Please check the implementation.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
