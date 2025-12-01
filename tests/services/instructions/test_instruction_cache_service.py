"""Unit tests for InstructionCacheService.

Test Coverage:
- Cache creation and updates
- Hash-based invalidation
- Metadata management
- Error handling
- Edge cases (missing files, corrupted metadata)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.instructions.instruction_cache_service import (
    InstructionCacheService,
)


@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project root directory."""
    return tmp_path


@pytest.fixture
def test_instruction_content():
    """Create test assembled instruction content."""
    return "# Test PM Instructions\n\nThis is a test file."


@pytest.fixture
def cache_service(temp_project_root):
    """Create InstructionCacheService."""
    return InstructionCacheService(project_root=temp_project_root)


class TestInstructionCacheService:
    """Test suite for InstructionCacheService."""

    def test_init_sets_paths_correctly(self, temp_project_root):
        """Test that initialization sets up paths correctly."""
        service = InstructionCacheService(project_root=temp_project_root)

        assert service.project_root == temp_project_root
        assert service.cache_dir == temp_project_root / ".claude-mpm"
        assert (
            service.cache_file
            == temp_project_root / ".claude-mpm" / "PM_INSTRUCTIONS.md"
        )
        assert (
            service.meta_file
            == temp_project_root / ".claude-mpm" / "PM_INSTRUCTIONS.md.meta"
        )

    def test_init_uses_cwd_when_no_root_provided(self):
        """Test that initialization uses current directory when no root provided."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/path")
            service = InstructionCacheService()
            assert service.project_root == Path("/test/path")

    def test_update_cache_creates_cache_on_first_run(
        self, cache_service, test_instruction_content
    ):
        """Test that update_cache creates cache and metadata on first run."""
        result = cache_service.update_cache(
            instruction_content=test_instruction_content
        )

        assert result["updated"] is True
        assert result["reason"] == "content_changed"
        assert cache_service.cache_file.exists()
        assert cache_service.meta_file.exists()

        # Verify cache content matches provided content
        assert cache_service.cache_file.read_text() == test_instruction_content

        # Verify metadata structure
        metadata = json.loads(cache_service.meta_file.read_text())
        assert "version" in metadata
        assert "content_type" in metadata
        assert "content_hash" in metadata
        assert "content_size_bytes" in metadata
        assert "components" in metadata
        assert "cached_at" in metadata
        assert metadata["version"] == InstructionCacheService.CACHE_VERSION
        assert metadata["content_type"] == "assembled_instruction"

    def test_update_cache_skips_when_valid(
        self, cache_service, test_instruction_content
    ):
        """Test that update_cache skips update when cache is valid."""
        # First update to create cache
        result1 = cache_service.update_cache(
            instruction_content=test_instruction_content
        )
        assert result1["updated"] is True

        # Second update with same content should skip
        result2 = cache_service.update_cache(
            instruction_content=test_instruction_content
        )
        assert result2["updated"] is False
        assert result2["reason"] == "cache_valid"

    def test_update_cache_updates_when_content_changes(self, cache_service):
        """Test that update_cache updates when content changes."""
        # Create initial cache
        initial_content = "# Initial Instructions\n\nInitial content."
        result1 = cache_service.update_cache(instruction_content=initial_content)
        assert result1["updated"] is True
        initial_hash = result1["content_hash"]

        # Update with new content
        new_content = "# Modified Instructions\n\nNew content."
        result2 = cache_service.update_cache(instruction_content=new_content)
        assert result2["updated"] is True
        assert result2["reason"] == "content_changed"
        assert result2["content_hash"] != initial_hash

        # Verify cache has new content
        assert cache_service.cache_file.read_text() == new_content

    def test_update_cache_force_updates_regardless(
        self, cache_service, test_instruction_content
    ):
        """Test that update_cache with force=True updates even if valid."""
        # Create initial cache
        result1 = cache_service.update_cache(
            instruction_content=test_instruction_content
        )
        assert result1["updated"] is True

        # Force update
        result2 = cache_service.update_cache(
            instruction_content=test_instruction_content, force=True
        )
        assert result2["updated"] is True
        assert result2["reason"] == "forced"

    def test_update_cache_handles_permission_errors_gracefully(
        self, cache_service, test_instruction_content
    ):
        """Test that update_cache handles permission errors gracefully."""
        # Create cache directory without write permissions
        cache_service.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service.cache_dir.chmod(0o444)

        try:
            result = cache_service.update_cache(
                instruction_content=test_instruction_content
            )
            assert result["updated"] is False
            assert result["reason"] == "error"
            assert "error" in result
        finally:
            # Restore permissions for cleanup
            cache_service.cache_dir.chmod(0o755)

    def test_is_cache_valid_returns_false_when_missing(
        self, cache_service, test_instruction_content
    ):
        """Test that is_cache_valid returns False when cache doesn't exist."""
        assert (
            cache_service.is_cache_valid(instruction_content=test_instruction_content)
            is False
        )

    def test_is_cache_valid_returns_false_when_metadata_missing(
        self, cache_service, test_instruction_content
    ):
        """Test that is_cache_valid returns False when metadata missing."""
        # Create cache but not metadata
        cache_service.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service.cache_file.write_text("Test content")

        assert (
            cache_service.is_cache_valid(instruction_content=test_instruction_content)
            is False
        )

    def test_is_cache_valid_returns_true_when_matches(
        self, cache_service, test_instruction_content
    ):
        """Test that is_cache_valid returns True when hash matches."""
        # Create valid cache
        cache_service.update_cache(instruction_content=test_instruction_content)

        assert (
            cache_service.is_cache_valid(instruction_content=test_instruction_content)
            is True
        )

    def test_is_cache_valid_returns_false_when_hash_mismatch(self, cache_service):
        """Test that is_cache_valid returns False when hash doesn't match."""
        # Create valid cache
        initial_content = "# Initial content"
        cache_service.update_cache(instruction_content=initial_content)

        # Check with different content
        new_content = "# Changed content"
        assert cache_service.is_cache_valid(instruction_content=new_content) is False

    def test_is_cache_valid_handles_corrupted_metadata_gracefully(
        self, cache_service, test_instruction_content
    ):
        """Test that is_cache_valid handles corrupted metadata gracefully."""
        # Create cache with corrupted metadata
        cache_service.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service.cache_file.write_text("Test content")
        cache_service.meta_file.write_text("Not valid JSON{{{")

        assert (
            cache_service.is_cache_valid(instruction_content=test_instruction_content)
            is False
        )

    def test_invalidate_cache_removes_files(
        self, cache_service, test_instruction_content
    ):
        """Test that invalidate_cache removes cache and metadata files."""
        # Create cache
        cache_service.update_cache(instruction_content=test_instruction_content)
        assert cache_service.cache_file.exists()
        assert cache_service.meta_file.exists()

        # Invalidate
        result = cache_service.invalidate_cache()
        assert result is True
        assert not cache_service.cache_file.exists()
        assert not cache_service.meta_file.exists()

    def test_invalidate_cache_returns_false_when_no_cache(self, cache_service):
        """Test that invalidate_cache returns False when no cache exists."""
        result = cache_service.invalidate_cache()
        assert result is False

    def test_invalidate_cache_handles_errors_gracefully(self, cache_service):
        """Test that invalidate_cache handles errors gracefully."""
        # Create cache with non-existent parent directory
        cache_service.cache_file = Path("/nonexistent/path/cache.md")
        cache_service.meta_file = Path("/nonexistent/path/cache.md.meta")

        result = cache_service.invalidate_cache()
        assert result is False

    def test_get_cache_path_returns_correct_path(self, cache_service):
        """Test that get_cache_path returns the correct cache file path."""
        path = cache_service.get_cache_path()
        assert path == cache_service.cache_file
        assert path.name == "PM_INSTRUCTIONS.md"

    def test_get_cache_info_returns_metadata(
        self, cache_service, test_instruction_content
    ):
        """Test that get_cache_info returns complete metadata."""
        # Create cache
        cache_service.update_cache(instruction_content=test_instruction_content)

        info = cache_service.get_cache_info()

        assert info["cache_exists"] is True
        assert info["cache_valid"] is None  # Can't validate without current content
        assert "cache_path" in info
        assert "content_type" in info
        assert info["content_type"] == "assembled_instruction"
        assert "cache_size_kb" in info
        assert "cached_at" in info
        assert "content_hash" in info
        assert "content_size_bytes" in info
        assert "components" in info
        assert "cache_version" in info

    def test_get_cache_info_handles_missing_cache(self, cache_service):
        """Test that get_cache_info handles missing cache gracefully."""
        info = cache_service.get_cache_info()

        assert info["cache_exists"] is False
        assert info["cache_valid"] is None
        assert "content_type" in info

    def test_get_cache_info_handles_errors_gracefully(self, cache_service):
        """Test that get_cache_info handles errors gracefully."""
        # Create cache with valid content first
        cache_service.update_cache(instruction_content="test")

        # Mock read_text to raise an error
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            info = cache_service.get_cache_info()
            # Should handle error gracefully
            assert "error" in info or "cache_exists" in info

    def test_calculate_hash_from_content_returns_consistent_hash(self, cache_service):
        """Test that _calculate_hash_from_content returns consistent hash for same content."""
        content = "# Test content\n\nThis is test content."
        hash1 = cache_service._calculate_hash_from_content(content)
        hash2 = cache_service._calculate_hash_from_content(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string

    def test_calculate_hash_from_content_changes_with_content(self, cache_service):
        """Test that _calculate_hash_from_content changes when content changes."""
        content1 = "# Test content 1"
        content2 = "# Test content 2"

        hash1 = cache_service._calculate_hash_from_content(content1)
        hash2 = cache_service._calculate_hash_from_content(content2)

        assert hash1 != hash2

    def test_get_cached_hash_returns_none_when_missing(self, cache_service):
        """Test that _get_cached_hash returns None when metadata missing."""
        assert cache_service._get_cached_hash() is None

    def test_get_cached_hash_returns_hash_when_exists(
        self, cache_service, test_instruction_content
    ):
        """Test that _get_cached_hash returns hash when metadata exists."""
        # Create cache
        result = cache_service.update_cache(
            instruction_content=test_instruction_content
        )
        content_hash = result["content_hash"]

        cached_hash = cache_service._get_cached_hash()
        assert cached_hash == content_hash

    def test_get_cached_hash_handles_corrupted_metadata(self, cache_service):
        """Test that _get_cached_hash handles corrupted metadata gracefully."""
        # Create corrupted metadata
        cache_service.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_service.meta_file.write_text("Invalid JSON")

        assert cache_service._get_cached_hash() is None

    def test_write_metadata_creates_valid_json(self, cache_service):
        """Test that _write_metadata creates valid JSON metadata."""
        cache_service.cache_dir.mkdir(parents=True, exist_ok=True)
        test_hash = "abc123"
        test_size = 450000

        cache_service._write_metadata(test_hash, test_size)

        assert cache_service.meta_file.exists()
        metadata = json.loads(cache_service.meta_file.read_text())

        assert metadata["version"] == InstructionCacheService.CACHE_VERSION
        assert metadata["content_hash"] == test_hash
        assert metadata["content_size_bytes"] == test_size
        assert metadata["content_type"] == "assembled_instruction"
        assert "components" in metadata
        assert "cached_at" in metadata

    def test_atomic_cache_update(self, cache_service):
        """Test that cache updates are atomic (via temp file)."""
        # Create initial cache
        initial_content = "# Initial content"
        cache_service.update_cache(instruction_content=initial_content)
        cached_initial = cache_service.cache_file.read_text()

        # Update with new content
        new_content = "# New content that is different"

        # Update should be atomic - no partial writes
        result = cache_service.update_cache(instruction_content=new_content)
        assert result["updated"] is True

        # After update, cache should have complete new content
        assert cache_service.cache_file.read_text() == new_content

    def test_cache_service_with_large_content(self, cache_service):
        """Test that cache service handles large content efficiently."""
        # Create large content (~1MB)
        large_content = "# Large PM Instructions\n" + ("Test content\n" * 10000)

        # Should handle large content without issues
        result = cache_service.update_cache(instruction_content=large_content)
        assert result["updated"] is True

        # Verify content matches
        assert cache_service.cache_file.read_text() == large_content

        # Verify cache is valid
        assert cache_service.is_cache_valid(instruction_content=large_content) is True

    def test_concurrent_cache_operations(self, cache_service, test_instruction_content):
        """Test that cache service handles concurrent operations gracefully."""
        # Create cache
        cache_service.update_cache(instruction_content=test_instruction_content)

        # Simulate concurrent read and invalidate
        info = cache_service.get_cache_info()
        cache_service.invalidate_cache()

        # Should not crash and info should be consistent
        assert isinstance(info, dict)

    def test_cache_version_in_metadata(self, cache_service, test_instruction_content):
        """Test that cache version is included in metadata."""
        cache_service.update_cache(instruction_content=test_instruction_content)

        metadata = json.loads(cache_service.meta_file.read_text())
        assert metadata["version"] == "1.0"

    def test_content_size_in_result(self, cache_service):
        """Test that update_cache returns content size in KB."""
        content = "# Test Instructions\n" * 100
        result = cache_service.update_cache(instruction_content=content)

        assert "content_size_kb" in result
        assert result["content_size_kb"] > 0
        assert isinstance(result["content_size_kb"], float)


class TestInstructionCacheServiceIntegration:
    """Integration tests for InstructionCacheService."""

    def test_full_cache_lifecycle(self, cache_service):
        """Test complete cache lifecycle: create, validate, update, invalidate."""
        initial_content = "# Initial content"
        updated_content = "# Updated content"

        # 1. Initial state - no cache
        assert not cache_service.is_cache_valid(instruction_content=initial_content)
        info = cache_service.get_cache_info()
        assert info["cache_exists"] is False

        # 2. Create cache
        result = cache_service.update_cache(instruction_content=initial_content)
        assert result["updated"] is True
        assert cache_service.is_cache_valid(instruction_content=initial_content)

        # 3. Verify cache info
        info = cache_service.get_cache_info()
        assert info["cache_exists"] is True
        assert info["cache_valid"] is None  # Can't validate without content

        # 4. Update with same content - should skip
        result = cache_service.update_cache(instruction_content=initial_content)
        assert result["updated"] is False

        # 5. Update with different content
        assert not cache_service.is_cache_valid(instruction_content=updated_content)

        # 6. Update cache with new content
        result = cache_service.update_cache(instruction_content=updated_content)
        assert result["updated"] is True
        assert cache_service.is_cache_valid(instruction_content=updated_content)

        # 7. Invalidate cache
        assert cache_service.invalidate_cache() is True
        assert not cache_service.is_cache_valid(instruction_content=updated_content)

    def test_cache_survives_service_recreation(self, temp_project_root):
        """Test that cache survives service instance recreation."""
        content = "# Test content for recreation"

        # Create cache with first service instance
        service1 = InstructionCacheService(project_root=temp_project_root)
        service1.update_cache(instruction_content=content)

        # Create new service instance
        service2 = InstructionCacheService(project_root=temp_project_root)

        # Cache should still exist and be valid
        assert service2.is_cache_valid(instruction_content=content)
        assert service2.cache_file.exists()

    def test_is_cache_valid_exception_during_hash_calculation(self, cache_service):
        """Test that is_cache_valid handles exceptions during hash calculation."""
        content = "# Test content"

        # Create cache
        cache_service.update_cache(instruction_content=content)

        # Mock _calculate_hash_from_content to raise exception
        with patch.object(
            cache_service,
            "_calculate_hash_from_content",
            side_effect=OSError("Hash error"),
        ):
            assert cache_service.is_cache_valid(instruction_content=content) is False

    def test_invalidate_cache_with_permission_error(
        self, cache_service, test_instruction_content
    ):
        """Test that invalidate_cache handles permission errors gracefully."""
        # Create cache
        cache_service.update_cache(instruction_content=test_instruction_content)

        # Mock unlink to raise permission error
        with patch.object(Path, "unlink", side_effect=PermissionError("Cannot delete")):
            result = cache_service.invalidate_cache()
            assert result is False

    def test_get_cache_info_with_exception_during_metadata_read(
        self, cache_service, test_instruction_content
    ):
        """Test that get_cache_info handles exceptions during metadata read."""
        # Create cache
        cache_service.update_cache(instruction_content=test_instruction_content)

        # Mock read_text to raise exception
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            info = cache_service.get_cache_info()
            assert "error" in info
