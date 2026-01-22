"""Tests for tmux error handling in Commander API."""

import subprocess
import uuid
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.commander.api.errors import TmuxNoSpaceError
from claude_mpm.commander.models import Project


class TestTmuxNoSpaceError:
    """Tests for TmuxNoSpaceError."""

    def test_default_message(self):
        """Test default error message contains helpful guidance."""
        error = TmuxNoSpaceError()
        assert "no space for new pane" in error.detail["error"]["message"].lower()
        assert "tmux new-window" in error.detail["error"]["message"]
        assert error.status_code == 409

    def test_custom_message(self):
        """Test custom error message is used when provided."""
        error = TmuxNoSpaceError("Custom error message")
        assert error.detail["error"]["message"] == "Custom error message"
        assert error.status_code == 409

    def test_error_code(self):
        """Test error code is set correctly."""
        error = TmuxNoSpaceError()
        assert error.detail["error"]["code"] == "TMUX_NO_SPACE"


class TestSessionCreatePaneErrorHandling:
    """Tests for pane creation error handling in session creation."""

    @pytest.fixture
    def mock_registry(self):
        """Mock registry with a test project."""
        registry = MagicMock()
        project = Project(
            id="test-proj-123",
            name="test-project",
            path="/fake/path",
            sessions={},
        )
        registry.get.return_value = project
        registry.add_session = MagicMock()
        return registry

    @pytest.fixture
    def mock_tmux(self):
        """Mock tmux orchestrator."""
        tmux = MagicMock()
        return tmux

    def test_no_space_error_raises_tmux_no_space_error(self, mock_registry, mock_tmux):
        """Test that subprocess error with 'no space' raises TmuxNoSpaceError."""
        from claude_mpm.commander.api.routes.sessions import create_session
        from claude_mpm.commander.api.schemas import CreateSessionRequest

        # Mock subprocess error with "no space for new pane" in stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["tmux", "new-window"],
            stderr=b"tmux: no space for new pane",
        )
        mock_tmux.create_pane.side_effect = error

        # Patch app globals
        with patch(
            "claude_mpm.commander.api.routes.sessions._get_registry",
            return_value=mock_registry,
        ):
            with patch(
                "claude_mpm.commander.api.routes.sessions._get_tmux",
                return_value=mock_tmux,
            ):
                # Create session request
                request = CreateSessionRequest(runtime="claude-code")

                # Should raise TmuxNoSpaceError
                with pytest.raises(TmuxNoSpaceError) as exc_info:
                    import asyncio
                    from unittest.mock import Mock

                    mock_request = Mock()
                    asyncio.run(create_session(mock_request, "test-proj-123", request))

                # Verify error details
                assert exc_info.value.status_code == 409
                assert (
                    "no space for new pane"
                    in exc_info.value.detail["error"]["message"].lower()
                )

    def test_other_subprocess_errors_are_reraised(self, mock_registry, mock_tmux):
        """Test that other subprocess errors are re-raised unchanged."""
        from claude_mpm.commander.api.routes.sessions import create_session
        from claude_mpm.commander.api.schemas import CreateSessionRequest

        # Mock subprocess error without "no space" message
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["tmux", "new-window"],
            stderr=b"tmux: session not found",
        )
        mock_tmux.create_pane.side_effect = error

        # Patch app globals
        with patch(
            "claude_mpm.commander.api.routes.sessions._get_registry",
            return_value=mock_registry,
        ):
            with patch(
                "claude_mpm.commander.api.routes.sessions._get_tmux",
                return_value=mock_tmux,
            ):
                # Create session request
                request = CreateSessionRequest(runtime="claude-code")

                # Should re-raise original CalledProcessError
                with pytest.raises(subprocess.CalledProcessError) as exc_info:
                    import asyncio
                    from unittest.mock import Mock

                    mock_request = Mock()
                    asyncio.run(create_session(mock_request, "test-proj-123", request))

                # Verify it's the original error
                assert exc_info.value.returncode == 1
                assert b"session not found" in exc_info.value.stderr

    def test_successful_pane_creation(self, mock_registry, mock_tmux):
        """Test successful pane creation without errors."""
        from claude_mpm.commander.api.routes.sessions import create_session
        from claude_mpm.commander.api.schemas import CreateSessionRequest

        # Mock successful pane creation
        mock_tmux.create_pane.return_value = "%1"

        # Patch app globals
        with patch(
            "claude_mpm.commander.api.routes.sessions._get_registry",
            return_value=mock_registry,
        ):
            with patch(
                "claude_mpm.commander.api.routes.sessions._get_tmux",
                return_value=mock_tmux,
            ):
                # Create session request
                request = CreateSessionRequest(runtime="claude-code")

                # Should succeed
                import asyncio
                from unittest.mock import Mock

                mock_request = Mock()
                response = asyncio.run(
                    create_session(mock_request, "test-proj-123", request)
                )

                # Verify response
                assert response.project_id == "test-proj-123"
                assert response.runtime == "claude-code"
                assert response.tmux_target == "%1"
                assert response.status == "initializing"

                # Verify session was added to registry
                mock_registry.add_session.assert_called_once()

    def test_no_space_error_case_insensitive(self, mock_registry, mock_tmux):
        """Test that 'no space' detection is case-insensitive."""
        from claude_mpm.commander.api.routes.sessions import create_session
        from claude_mpm.commander.api.schemas import CreateSessionRequest

        # Mock subprocess error with mixed-case message
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["tmux", "new-window"],
            stderr=b"tmux: No Space For New Pane",
        )
        mock_tmux.create_pane.side_effect = error

        # Patch app globals
        with patch(
            "claude_mpm.commander.api.routes.sessions._get_registry",
            return_value=mock_registry,
        ):
            with patch(
                "claude_mpm.commander.api.routes.sessions._get_tmux",
                return_value=mock_tmux,
            ):
                # Create session request
                request = CreateSessionRequest(runtime="claude-code")

                # Should raise TmuxNoSpaceError
                with pytest.raises(TmuxNoSpaceError):
                    import asyncio
                    from unittest.mock import Mock

                    mock_request = Mock()
                    asyncio.run(create_session(mock_request, "test-proj-123", request))
