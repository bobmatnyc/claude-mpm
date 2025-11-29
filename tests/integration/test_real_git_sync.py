#!/usr/bin/env python3
"""
Real network integration test for GitSourceSyncService.

This script tests actual GitHub synchronization against the production
bobmatnyc/claude-mpm-agents repository to verify:
- Agents download from real GitHub
- ETag caching works with real responses
- Cache directory structure is correct
- SQLite state tracking persists
"""

import sys
import tempfile
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)


def test_real_github_sync():
    """Test real GitHub synchronization (safe, read-only operation)."""
    print("=" * 80)
    print("REAL NETWORK INTEGRATION TEST")
    print("=" * 80)
    print()

    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "agent_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"Test cache directory: {cache_dir}")
        print()

        # Initialize service with default GitHub source
        service = GitSourceSyncService(cache_dir=str(cache_dir))

        print("Step 1: Sync all agents (auto-discovery)...")
        print()

        print("Step 2: Perform initial sync...")

        results = service.sync_agents()
        print(f"  Synced: {len(results['synced'])}")
        print(f"  Cached: {len(results['cached'])}")
        print(f"  Failed: {len(results['failed'])}")
        print(f"  Total downloaded: {results['total_downloaded']}")
        print(f"  Cache hits: {results['cache_hits']}")
        print()

        # Verify cache files exist
        print("Step 3: Verify cache files...")
        synced_agents = results['synced'][:3]  # Check first 3 synced agents
        for agent_name in synced_agents:
            cache_file = cache_dir / f"{agent_name}.md"
            if cache_file.exists():
                size = cache_file.stat().st_size
                print(f"  ✓ {agent_name}.md ({size:,} bytes)")
            else:
                print(f"  ✗ {agent_name}.md (MISSING)")
        print()

        # Test ETag caching (second sync should use cache)
        print("Step 4: Test ETag caching (re-sync)...")
        results2 = service.sync_agents()
        print(f"  Synced: {len(results2['synced'])}")
        print(f"  Cached: {len(results2['cached'])}")
        print(f"  Cache hits: {results2['cache_hits']}")

        if results2["cache_hits"] > 0:
            print("  ✓ ETag caching works!")
        else:
            print("  ⚠ Warning: Expected cache hits on second sync")
        print()

        # Check SQLite database
        print("Step 5: Verify SQLite state tracking...")
        db_path = cache_dir / "sync_state.db"
        if db_path.exists():
            print(f"  ✓ Database created: {db_path}")
            print(f"  Database size: {db_path.stat().st_size:,} bytes")

            # Check sources
            sources = service.sync_state.get_all_sources()
            print(f"  Registered sources: {len(sources)}")
            for source in sources:
                print(f"    - {source['source_id']}: {source['source_url']}")
        else:
            print("  ✗ Database not created")
        print()

        # Check for updates
        print("Step 6: Check for updates...")
        updates = service.check_for_updates()
        print(f"  Available updates: {len(updates.get('available_updates', []))}")
        print()

        print("=" * 80)
        print("INTEGRATION TEST COMPLETE")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Agents synced: {len(results['synced'])}")
        print(f"  - ETag caching: {'✓ Working' if results2['cache_hits'] > 0 else '✗ Not working'}")
        print(f"  - SQLite tracking: {'✓ Working' if db_path.exists() else '✗ Not working'}")
        print(f"  - Cache directory: {cache_dir}")
        print()


if __name__ == "__main__":
    try:
        test_real_github_sync()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
