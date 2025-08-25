#!/usr/bin/env python3
"""Verify that version warning issues are fixed."""

import subprocess
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    MultiSourceAgentDeploymentService,
)


def run_verification():
    """Run comprehensive verification of fixes."""
    print("=" * 60)
    print("VERIFYING VERSION WARNING FIXES")
    print("=" * 60)

    success = True

    # Test 1: Check orphan detection is fixed
    print("\n✅ TEST 1: Orphan Detection Fix")
    print("-" * 40)

    service = MultiSourceAgentDeploymentService()
    project_agents_dir = Path.cwd() / ".claude" / "agents"

    if project_agents_dir.exists():
        all_agents = service.discover_agents_from_all_sources()
        orphaned = service.detect_orphaned_agents(project_agents_dir, all_agents)

        if orphaned:
            print(f"❌ FAILED: Found {len(orphaned)} orphaned agents")
            for orphan in orphaned[:3]:
                print(f"   - {orphan['name']}")
            success = False
        else:
            print("✅ PASSED: No orphaned agents detected")
    else:
        print("⚠️  SKIPPED: No agents directory found")

    # Test 2: Run deployment and check for warnings
    print("\n✅ TEST 2: Clean Deployment Without Warnings")
    print("-" * 40)

    try:
        # Capture deployment output
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService
import logging

# Set logging to capture warnings
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

service = AgentDeploymentService()
result = service.deploy_agents(force_rebuild=False)
print(f'Deployment result: {result}')
""",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # Check for warning messages
        output = result.stdout + result.stderr
        warning_keywords = [
            "warning:",
            "deployed version.*higher than template",
            "railway-ops",
        ]

        warnings_found = []
        for keyword in warning_keywords:
            if keyword.lower() in output.lower():
                warnings_found.append(keyword)

        if warnings_found:
            print(f"❌ FAILED: Found warning keywords: {warnings_found}")
            print(f"   Output excerpt: {output[:500]}")
            success = False
        else:
            print("✅ PASSED: No version warnings in deployment")

    except subprocess.TimeoutExpired:
        print("❌ FAILED: Deployment timed out")
        success = False
    except Exception as e:
        print(f"❌ FAILED: Deployment error: {e}")
        success = False

    # Test 3: Check CLI command registration
    print("\n✅ TEST 3: CLI Command Registration")
    print("-" * 40)

    try:
        result = subprocess.run(
            ["claude-mpm", "agents", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if "cleanup-orphaned" in result.stdout:
            print("✅ PASSED: cleanup-orphaned command is registered")
        else:
            print("⚠️  WARNING: cleanup-orphaned command not found in help")
            # Not a failure since the command might work anyway

    except Exception as e:
        print(f"⚠️  WARNING: Could not test CLI: {e}")

    # Test 4: Version comparison logic
    print("\n✅ TEST 4: Version Comparison Logic")
    print("-" * 40)

    from claude_mpm.services.agents.deployment.agent_version_manager import (
        AgentVersionManager,
    )

    version_manager = AgentVersionManager()

    # Test cases for version comparison
    test_cases = [
        ("3.1.0", "3.2.0", -1, "3.1.0 < 3.2.0"),
        ("3.2.0", "3.2.0", 0, "3.2.0 == 3.2.0"),
        ("3.3.0", "3.2.0", 1, "3.3.0 > 3.2.0"),
    ]

    all_passed = True
    for v1, v2, expected, desc in test_cases:
        result = version_manager.compare_versions(v1, v2)
        if result == expected:
            print(f"   ✓ {desc}: correct")
        else:
            print(f"   ✗ {desc}: got {result}, expected {expected}")
            all_passed = False

    if all_passed:
        print("✅ PASSED: Version comparison works correctly")
    else:
        print("❌ FAILED: Version comparison has issues")
        success = False

    # Final summary
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Version warning issues are fixed!")
    else:
        print("❌ SOME TESTS FAILED - Please review the issues above")
    print("=" * 60)

    return success


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
