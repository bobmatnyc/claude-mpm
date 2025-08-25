"""Tests for VersionService.

Tests the extracted version service to ensure it maintains
the same behavior as the original ClaudeRunner version methods.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.version_service import VersionService


class TestVersionService:
    """Test the VersionService class."""

    @pytest.fixture
    def service(self):
        """Create a VersionService instance for testing."""
        return VersionService()

    def test_get_version_with_package_import(service):
        """Test version retrieval via package import."""
        with patch("claude_mpm.__version__", "1.2.3"), patch.object(
            service, "_get_build_number", return_value=None
        ):
            version = service.get_version()
            assert version == "v1.2.3"

    def test_get_version_with_build_number(service):
        """Test version retrieval with build number."""
        with patch("claude_mpm.__version__", "1.2.3+build.123"):
            version = service.get_version()
            assert version == "v1.2.3-build.123"

    def test_get_version_with_importlib_metadata(service):
        """Test version retrieval via importlib.metadata."""
        # Mock the import to fail, then mock importlib.metadata to succeed
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args, **kwargs: (
                __import__(name, *args, **kwargs)
                if name != "claude_mpm"
                else (_ for _ in ()).throw(ImportError())
            ),
        ), patch("importlib.metadata.version", return_value="2.0.0"), patch.object(
            service, "_get_build_number", return_value=None
        ):
            version = service.get_version()
            assert version == "v2.0.0"

    def test_get_version_with_version_file(service):
        """Test version retrieval from VERSION file."""
        with patch("claude_mpm.__version__", side_effect=ImportError), patch(
            "importlib.metadata.version", side_effect=ImportError
        ), patch("claude_mpm.config.paths.paths") as mock_paths:
            # Mock version file
            mock_version_file = Mock()
            mock_version_file.exists.return_value = True
            mock_version_file.read_text.return_value = "3.0.0\n"
            mock_paths.version_file = mock_version_file

            with patch.object(service, "_get_build_number", return_value=None):
                version = service.get_version()
                assert version == "v3.0.0"

    def test_get_version_fallback(service):
        """Test version fallback when all methods fail."""
        with patch("claude_mpm.__version__", side_effect=ImportError), patch(
            "importlib.metadata.version", side_effect=ImportError
        ), patch("claude_mpm.config.paths.paths") as mock_paths:
            # Mock version file not existing
            mock_version_file = Mock()
            mock_version_file.exists.return_value = False
            mock_paths.version_file = mock_version_file

            with patch.object(service, "_get_build_number", return_value=None):
                version = service.get_version()
                assert version == "v0.0.0"

    def test_get_build_number_success(service):
        """Test build number retrieval."""
        with patch("claude_mpm.config.paths.paths") as mock_paths:
            # Mock build file
            mock_build_file = Mock()
            mock_build_file.exists.return_value = True
            mock_build_file.read_text.return_value = "456\n"
            mock_paths.project_root = Path("/mock")

            with patch.object(Path, "__truediv__", return_value=mock_build_file):
                build_number = service.get_build_number()
                assert build_number == 456

    def test_get_build_number_not_found(service):
        """Test build number when file doesn't exist."""
        with patch("claude_mpm.config.paths.paths") as mock_paths:
            # Mock build file not existing
            mock_build_file = Mock()
            mock_build_file.exists.return_value = False
            mock_paths.project_root = Path("/mock")

            with patch.object(Path, "__truediv__", return_value=mock_build_file):
                build_number = service.get_build_number()
                assert build_number is None

    def test_get_base_version(service):
        """Test base version retrieval."""
        with patch("claude_mpm.__version__", "1.2.3+build.123"):
            base_version = service.get_base_version()
            assert base_version == "1.2.3"

    def test_get_pep440_version_with_build(service):
        """Test PEP 440 version format with build number."""
        with patch("claude_mpm.__version__", "1.2.3"), patch.object(
            service, "get_build_number", return_value=456
        ):
            pep440_version = service.get_pep440_version()
            assert pep440_version == "1.2.3+build.456"

    def test_get_pep440_version_without_build(service):
        """Test PEP 440 version format without build number."""
        with patch("claude_mpm.__version__", "1.2.3"), patch.object(
            service, "get_build_number", return_value=None
        ):
            pep440_version = service.get_pep440_version()
            assert pep440_version == "1.2.3"

    def test_format_version_with_build(service):
        """Test version formatting with build number."""
        formatted = service._format_version("1.2.3", 456)
        assert formatted == "v1.2.3-build.456"

    def test_format_version_without_build(service):
        """Test version formatting without build number."""
        formatted = service._format_version("1.2.3", None)
        assert formatted == "v1.2.3"

    def test_version_with_build_file(service):
        """Test complete version flow with build file."""
        with patch("claude_mpm.__version__", "1.2.3"), patch(
            "claude_mpm.config.paths.paths"
        ) as mock_paths:
            # Mock build file
            mock_build_file = Mock()
            mock_build_file.exists.return_value = True
            mock_build_file.read_text.return_value = "789"
            mock_paths.project_root = Path("/mock")

            with patch.object(Path, "__truediv__", return_value=mock_build_file):
                version = service.get_version()
                assert version == "v1.2.3-build.789"

    def test_error_handling_in_version_detection(service):
        """Test error handling during version detection."""
        with patch(
            "claude_mpm.__version__", side_effect=Exception("Test error")
        ), patch(
            "importlib.metadata.version", side_effect=Exception("Metadata error")
        ), patch(
            "claude_mpm.config.paths.paths"
        ) as mock_paths:
            # Mock version file with error
            mock_version_file = Mock()
            mock_version_file.exists.return_value = True
            mock_version_file.read_text.side_effect = Exception("File error")
            mock_paths.version_file = mock_version_file

            version = service.get_version()
            assert version == "v0.0.0"  # Should fallback gracefully

    def test_error_handling_in_build_number(service):
        """Test error handling during build number detection."""
        with patch("claude_mpm.config.paths.paths") as mock_paths:
            # Mock build file with error
            mock_build_file = Mock()
            mock_build_file.exists.return_value = True
            mock_build_file.read_text.side_effect = Exception("Build file error")
            mock_paths.project_root = Path("/mock")

            with patch.object(Path, "__truediv__", return_value=mock_build_file):
                build_number = service.get_build_number()
                assert build_number is None  # Should handle error gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
