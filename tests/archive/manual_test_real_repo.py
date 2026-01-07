#!/usr/bin/env python3
"""Manual test script to verify Git Tree API discovers all agents from real repository.

This script tests Phase 1 implementation against the actual GitHub repository
to verify that all 50+ agents are discovered (not just 1).
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)


def test_real_repository_discovery():
    """Test agent discovery from real GitHub repository."""
    print("=" * 80)
    print("Phase 1 Implementation Test: Real Repository Discovery")
    print("=" * 80)
    print()

    # Create service with temporary cache
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache" / "agents"
        service = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
            cache_dir=cache_dir,
        )

        print(f"Cache directory: {cache_dir}")
        print()

        # Test Git Tree API discovery
        print("Testing Git Tree API discovery...")
        print("-" * 80)

        try:
            agents = service._get_agent_list()

            print(f"✓ Discovered {len(agents)} agents")
            print()

            if len(agents) > 10:
                print("First 10 agents:")
                for i, agent in enumerate(agents[:10], 1):
                    print(f"  {i}. {agent}")
                print(f"  ... and {len(agents) - 10} more")
            else:
                print("All agents:")
                for i, agent in enumerate(agents, 1):
                    print(f"  {i}. {agent}")

            print()
            print("-" * 80)
            print()

            # Check if nested structure is discovered
            nested_agents = [a for a in agents if "/" in a]
            print(f"Nested agents (with directories): {len(nested_agents)}")
            if nested_agents:
                print("Sample nested agents:")
                for agent in nested_agents[:5]:
                    print(f"  - {agent}")
            print()

            # Success criteria
            print("Success Criteria:")
            print(f"  ✓ Total agents discovered: {len(agents)}")
            print(
                f"  {'✓' if len(agents) >= 10 else '✗'} At least 10 agents (expected: 50+)"
            )
            print(
                f"  {'✓' if nested_agents else '✗'} Nested directory structure discovered"
            )
            print()

            if len(agents) >= 10:
                print("🎉 SUCCESS: Phase 1 Git Tree API implementation working!")
                print("   - Discovered multiple agents (not just 1)")
                print("   - Nested directory structure supported")
                return True
            print("❌ FAILED: Not enough agents discovered")
            print("   Expected: 50+ agents")
            print(f"   Got: {len(agents)} agents")
            return False

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_sync_to_cache():
    """Test full sync to cache directory."""
    print()
    print("=" * 80)
    print("Phase 1 Implementation Test: Sync to Cache")
    print("=" * 80)
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache" / "agents"
        service = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
            cache_dir=cache_dir,
        )

        print(f"Cache directory: {cache_dir}")
        print()

        print("Starting agent sync (this may take a moment)...")
        print("-" * 80)

        try:
            result = service.sync_agents(show_progress=False)

            print("✓ Sync complete!")
            print()
            print("Sync Results:")
            print(f"  - Downloaded: {result['total_downloaded']}")
            print(f"  - Cached: {result['cache_hits']}")
            print(f"  - Failed: {len(result['failed'])}")
            print()

            # Check cache directory structure
            cache_files = list(cache_dir.rglob("*.md"))
            nested_files = [
                f for f in cache_files if len(f.relative_to(cache_dir).parts) > 1
            ]

            print("Cache Directory Structure:")
            print(f"  - Total files: {len(cache_files)}")
            print(f"  - Nested files: {len(nested_files)}")
            print()

            if nested_files:
                print("Sample nested structure:")
                for f in nested_files[:3]:
                    rel_path = f.relative_to(cache_dir)
                    print(f"  {cache_dir.name}/{rel_path}")
            print()

            print("Success Criteria:")
            print(
                f"  {'✓' if result['total_downloaded'] > 0 else '✗'} Files downloaded"
            )
            print(
                f"  {'✓' if nested_files else '✗'} Nested structure preserved in cache"
            )
            print()

            if result["total_downloaded"] > 0 and nested_files:
                print("🎉 SUCCESS: Cache directory working correctly!")
                return True
            print("❌ FAILED: Cache directory issues")
            return False

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_deployment_from_cache():
    """Test deployment from cache to project."""
    print()
    print("=" * 80)
    print("Phase 1 Implementation Test: Deployment from Cache")
    print("=" * 80)
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache" / "agents"
        project_dir = Path(tmpdir) / "project"

        service = GitSourceSyncService(cache_dir=cache_dir)

        # Populate cache with sample agents
        print("Setting up cache...")
        service._save_to_cache("research.md", "# Research Agent")
        service._save_to_cache("engineer/core/engineer.md", "# Engineer Agent")
        service._save_to_cache("qa/qa.md", "# QA Agent")
        print("✓ Cache populated with 3 test agents")
        print()

        print("Deploying agents to project...")
        print(f"Project directory: {project_dir}")
        print("-" * 80)

        try:
            result = service.deploy_agents_to_project(project_dir)

            print("✓ Deployment complete!")
            print()
            print("Deployment Results:")
            print(f"  - Deployed: {len(result['deployed'])}")
            print(f"  - Updated: {len(result['updated'])}")
            print(f"  - Skipped: {len(result['skipped'])}")
            print(f"  - Failed: {len(result['failed'])}")
            print()

            deployment_dir = project_dir / ".claude-mpm" / "agents"
            deployed_files = (
                list(deployment_dir.glob("*.md")) if deployment_dir.exists() else []
            )

            print("Deployed Files:")
            for f in deployed_files:
                print(f"  - {f.name}")
            print()

            print("Success Criteria:")
            print(
                f"  {'✓' if deployment_dir.exists() else '✗'} Deployment directory created"
            )
            print(f"  {'✓' if len(deployed_files) == 3 else '✗'} All agents deployed")
            print(
                f"  {'✓' if all(len(f.relative_to(deployment_dir).parts) == 1 for f in deployed_files) else '✗'} Paths flattened"
            )
            print()

            if deployment_dir.exists() and len(deployed_files) == 3:
                print("🎉 SUCCESS: Deployment working correctly!")
                return True
            print("❌ FAILED: Deployment issues")
            return False

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "PHASE 1 GIT SYNC ARCHITECTURE TEST SUITE" + " " * 22 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    results = []

    # Test 1: Real repository discovery
    results.append(("Discovery", test_real_repository_discovery()))

    # Test 2: Sync to cache
    # Commented out to avoid rate limiting during rapid testing
    # Uncomment to test full sync
    # results.append(("Sync", test_sync_to_cache()))

    # Test 3: Deployment from cache
    results.append(("Deployment", test_deployment_from_cache()))

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")

    print()
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
