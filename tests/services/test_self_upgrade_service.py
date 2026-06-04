"""
Tests for SelfUpgradeService._is_running_from_source_tree and
_detect_installation_method source-tree detection.

WHY: Regression guard for the bug where the upgrade-check notification fires
even when claude-mpm is run from the project's own source directory with a
globally-installed binary.  The fix adds an unconditional CWD walk that
returns EDITABLE when we are inside the source tree, regardless of how the
module was loaded.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> "SelfUpgradeService":  # type: ignore[name-defined]
    """Return a SelfUpgradeService with all expensive I/O stubbed out."""
    from claude_mpm.services.self_upgrade_service import SelfUpgradeService

    with (
        patch.object(
            SelfUpgradeService,
            "_get_current_version",
            return_value="6.5.17",
        ),
        patch.object(
            SelfUpgradeService,
            "_detect_installation_method",
            return_value="pip",
        ),
        patch.object(
            SelfUpgradeService,
            "_get_claude_code_version",
            return_value=None,
        ),
    ):
        svc = SelfUpgradeService()
    return svc


# ---------------------------------------------------------------------------
# _is_running_from_source_tree
# ---------------------------------------------------------------------------


class TestIsRunningFromSourceTree:
    """Unit tests for SelfUpgradeService._is_running_from_source_tree()."""

    def test_returns_true_when_cwd_is_source_root(self, tmp_path: Path) -> None:
        """Returns True when CWD is the project root with matching pyproject.toml."""
        # Create a minimal source-tree layout in tmp_path
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "claude-mpm"\nversion = "6.5.17"\n')
        (tmp_path / "src" / "claude_mpm").mkdir(parents=True)

        svc = _make_service()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = svc._is_running_from_source_tree()

        assert result is True

    def test_returns_true_when_cwd_is_subdirectory_of_source(
        self, tmp_path: Path
    ) -> None:
        """Returns True when CWD is nested inside the source tree (walk-up)."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.poetry]\nname = "claude-mpm"\n')
        (tmp_path / "src" / "claude_mpm").mkdir(parents=True)
        nested = tmp_path / "src" / "claude_mpm" / "services"
        nested.mkdir(parents=True)

        svc = _make_service()
        with patch("pathlib.Path.cwd", return_value=nested):
            result = svc._is_running_from_source_tree()

        assert result is True

    def test_returns_false_when_cwd_is_outside_source_tree(
        self, tmp_path: Path
    ) -> None:
        """Returns False when CWD contains no matching pyproject.toml."""
        svc = _make_service()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = svc._is_running_from_source_tree()

        assert result is False

    def test_returns_false_when_pyproject_exists_but_wrong_name(
        self, tmp_path: Path
    ) -> None:
        """Returns False when pyproject.toml exists but is for a different package."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "some-other-package"\nversion = "1.0.0"\n')
        (tmp_path / "src" / "claude_mpm").mkdir(parents=True)

        svc = _make_service()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = svc._is_running_from_source_tree()

        assert result is False

    def test_returns_false_when_src_claude_mpm_absent(self, tmp_path: Path) -> None:
        """Returns False when pyproject.toml matches but src/claude_mpm/ is missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "claude-mpm"\n')
        # Do NOT create src/claude_mpm

        svc = _make_service()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = svc._is_running_from_source_tree()

        assert result is False

    def test_walk_stops_at_filesystem_root(self) -> None:
        """Walk terminates gracefully when it reaches the filesystem root."""
        svc = _make_service()
        # Point CWD at filesystem root so the walk exits at parent == self
        with patch("pathlib.Path.cwd", return_value=Path("/")):
            result = svc._is_running_from_source_tree()

        assert result is False

    def test_non_fatal_on_oserror_reading_pyproject(self, tmp_path: Path) -> None:
        """OSError on pyproject.toml read is swallowed; returns False."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "claude-mpm"\n')
        (tmp_path / "src" / "claude_mpm").mkdir(parents=True)

        svc = _make_service()

        original_read_text = Path.read_text

        def _raise_oserror(self_path: Path, *args, **kwargs) -> str:  # type: ignore[override]
            if self_path == pyproject:
                raise OSError("permission denied")
            return original_read_text(self_path, *args, **kwargs)

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch.object(Path, "read_text", _raise_oserror),
        ):
            result = svc._is_running_from_source_tree()

        assert result is False

    def test_non_fatal_on_unexpected_exception(self) -> None:
        """Unexpected exceptions are caught and False is returned."""
        svc = _make_service()
        with patch("pathlib.Path.cwd", side_effect=RuntimeError("unexpected")):
            result = svc._is_running_from_source_tree()

        assert result is False


# ---------------------------------------------------------------------------
# _detect_installation_method — source-tree integration
# ---------------------------------------------------------------------------


class TestDetectInstallationMethodSourceTree:
    """Integration tests for _detect_installation_method with source-tree check."""

    def _service_with_real_detect(self) -> "SelfUpgradeService":  # type: ignore[name-defined]
        """Return a SelfUpgradeService where _detect_installation_method runs for real."""
        from claude_mpm.services.self_upgrade_service import SelfUpgradeService

        with (
            patch.object(
                SelfUpgradeService,
                "_get_current_version",
                return_value="6.5.17",
            ),
            patch.object(
                SelfUpgradeService,
                "_get_claude_code_version",
                return_value=None,
            ),
        ):
            svc = SelfUpgradeService()
        return svc

    def test_detect_editable_when_in_source_tree(self, tmp_path: Path) -> None:
        """Returns EDITABLE when CWD is the claude-mpm source tree.

        Simulates: globally-installed binary run from checkout directory.
        PathContext returns a non-dev context; the CWD walk must catch it.
        """
        from claude_mpm.services.self_upgrade_service import InstallationMethod

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "claude-mpm"\nversion = "6.5.17"\n')
        (tmp_path / "src" / "claude_mpm").mkdir(parents=True)

        mock_context = MagicMock()
        mock_context.name = "PIP_INSTALL"
        with (
            # Force PathContext to report a non-development context
            patch(
                "claude_mpm.services.self_upgrade_service.PathContext"
                ".detect_deployment_context",
                return_value=mock_context,
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            svc = self._service_with_real_detect()

        assert svc.installation_method == InstallationMethod.EDITABLE

    def test_no_editable_when_outside_source_tree(self, tmp_path: Path) -> None:
        """Does NOT return EDITABLE based on CWD when outside the source tree.

        Simulates: pip-installed binary run from an arbitrary project directory.
        """
        from claude_mpm.services.self_upgrade_service import InstallationMethod

        # tmp_path has no pyproject.toml / src/claude_mpm, so CWD walk returns False

        mock_context = MagicMock()
        mock_context.name = "PIP_INSTALL"
        with (
            patch(
                "claude_mpm.services.self_upgrade_service.PathContext"
                ".detect_deployment_context",
                return_value=mock_context,
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
            # Stub out slow subprocess checks
            patch(
                "claude_mpm.services.self_upgrade_service."
                "SelfUpgradeService._check_uv_tool_installation",
                return_value=False,
            ),
            patch(
                "claude_mpm.services.self_upgrade_service."
                "SelfUpgradeService._check_homebrew_installation",
                return_value=False,
            ),
            patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="")),
        ):
            svc = self._service_with_real_detect()

        assert svc.installation_method != InstallationMethod.EDITABLE
        assert svc.installation_method == InstallationMethod.PIP
