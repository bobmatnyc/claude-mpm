#!/usr/bin/env python3
"""Manual test script for private repository token support.

This script demonstrates how to add and sync a private skill repository
using per-source token authentication.

Usage:
    # Set up environment variable
    export PRIVATE_SKILLS_TOKEN=ghp_your_token_here

    # Run the test
    python tests/manual/test_private_repo_token.py
"""

import os
import tempfile
from pathlib import Path

from claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration
from claude_mpm.services.skills.git_skill_source_manager import (
    GitSkillSourceManager,
    _get_github_token,
)


def test_token_resolution():
    """Test token resolution logic."""
    print("=" * 60)
    print("Test 1: Token Resolution")
    print("=" * 60)

    # Test 1: Env var reference
    print("\n1. Environment variable reference ($PRIVATE_SKILLS_TOKEN):")
    source_env = SkillSource(
        id="private-env",
        type="git",
        url="https://github.com/myorg/private-skills",
        token="$PRIVATE_SKILLS_TOKEN",
    )

    os.environ["PRIVATE_SKILLS_TOKEN"] = "test_token_from_env"
    token = _get_github_token(source_env)
    print(f"   Resolved token: {token}")
    assert token == "test_token_from_env", "Env var resolution failed"
    print("   ✅ Passed")

    # Test 2: Direct token
    print("\n2. Direct token (not recommended):")
    source_direct = SkillSource(
        id="private-direct",
        type="git",
        url="https://github.com/myorg/private-skills",
        token="ghp_direct_token_123",
    )

    token = _get_github_token(source_direct)
    print(f"   Resolved token: {token}")
    assert token == "ghp_direct_token_123", "Direct token failed"
    print("   ✅ Passed")

    # Test 3: Fallback to GITHUB_TOKEN
    print("\n3. Fallback to GITHUB_TOKEN:")
    source_no_token = SkillSource(
        id="fallback",
        type="git",
        url="https://github.com/myorg/repo",
    )

    os.environ["GITHUB_TOKEN"] = "global_github_token"
    token = _get_github_token(source_no_token)
    print(f"   Resolved token: {token}")
    assert token == "global_github_token", "Fallback failed"
    print("   ✅ Passed")

    # Clean up
    del os.environ["PRIVATE_SKILLS_TOKEN"]
    del os.environ["GITHUB_TOKEN"]

    print("\n✅ All token resolution tests passed!")


def test_yaml_persistence():
    """Test token persistence to YAML."""
    print("\n" + "=" * 60)
    print("Test 2: YAML Persistence")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "skill_sources.yaml"
        config = SkillSourceConfiguration(config_path=config_path)

        # Create source with env var token
        source = SkillSource(
            id="private",
            type="git",
            url="https://github.com/myorg/private-skills",
            branch="main",
            priority=100,
            enabled=True,
            token="$PRIVATE_SKILLS_TOKEN",
        )

        # Save
        print("\n1. Saving source with token to YAML...")
        config.save([source])
        print(f"   Config saved to: {config_path}")

        # Check YAML content
        yaml_content = config_path.read_text()
        print("\n2. YAML content:")
        print("   " + yaml_content.replace("\n", "\n   "))

        assert "token: $PRIVATE_SKILLS_TOKEN" in yaml_content, "Token not in YAML"
        print("\n   ✅ Token persisted to YAML")

        # Load
        print("\n3. Loading source from YAML...")
        loaded_sources = config.load()

        assert len(loaded_sources) == 1, "Wrong number of sources loaded"
        assert loaded_sources[0].token == "$PRIVATE_SKILLS_TOKEN", "Token not loaded"
        print(f"   Loaded source: {loaded_sources[0].id}")
        print(f"   Token: {loaded_sources[0].token}")
        print("\n   ✅ Token loaded from YAML")

    print("\n✅ All YAML persistence tests passed!")


def test_backward_compatibility():
    """Test backward compatibility with sources without tokens."""
    print("\n" + "=" * 60)
    print("Test 3: Backward Compatibility")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "skill_sources.yaml"

        # Create legacy YAML without token field
        print("\n1. Creating legacy YAML (no token field)...")
        config_path.write_text(
            """sources:
  - id: public-repo
    type: git
    url: https://github.com/owner/public-repo
    branch: main
    priority: 100
    enabled: true
"""
        )

        config = SkillSourceConfiguration(config_path=config_path)
        sources = config.load()

        assert len(sources) == 1, "Failed to load legacy YAML"
        assert sources[0].token is None, "Token should be None for legacy sources"
        print(f"   Loaded legacy source: {sources[0].id}")
        print(f"   Token: {sources[0].token}")
        print("\n   ✅ Legacy YAML loaded successfully")

        # Add new source with token
        print("\n2. Adding new source with token to existing config...")
        new_source = SkillSource(
            id="private",
            type="git",
            url="https://github.com/myorg/private",
            token="$MY_TOKEN",
        )

        config.add_source(new_source)

        # Verify both sources
        all_sources = config.load()
        assert len(all_sources) == 2, "Wrong number of sources"
        assert all_sources[0].token is None, "Legacy source token changed"
        assert all_sources[1].token == "$MY_TOKEN", "New source token incorrect"
        print(
            f"   Source 1 (legacy): {all_sources[0].id}, token={all_sources[0].token}"
        )
        print(f"   Source 2 (new): {all_sources[1].id}, token={all_sources[1].token}")
        print("\n   ✅ Mixed legacy + token sources work together")

    print("\n✅ All backward compatibility tests passed!")


def main():
    """Run all manual tests."""
    print("\n🚀 Testing Private Repository Token Support")
    print("=" * 60)

    test_token_resolution()
    test_yaml_persistence()
    test_backward_compatibility()

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

    print("\n📖 Usage Example:")
    print("   # Add private repo with env var token:")
    print("   claude-mpm skill-source add \\")
    print("       https://github.com/myorg/private-skills \\")
    print("       --token $PRIVATE_SKILLS_TOKEN")
    print()
    print("   # Set environment variable:")
    print("   export PRIVATE_SKILLS_TOKEN=ghp_your_token_here")
    print()
    print("   # Sync will use the token:")
    print("   claude-mpm skill-source update")
    print()


if __name__ == "__main__":
    main()
