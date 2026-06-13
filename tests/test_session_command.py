"""Tests for the ``claude-mpm session`` command group.

Covers:
- Parser registration and argument parsing for ``session pause`` and
  ``session resume``
- Handler dispatch to the shared pause/resume logic
- ``--select``, exact-id, and default-resume paths route correctly
- Back-compat: ``mpm-init pause`` still dispatches to the same shared logic
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestSessionParser:
    """Verify that session subparsers are registered and parse correctly."""

    def _make_parser(self) -> argparse.ArgumentParser:
        """Build a minimal parser with only the session subparser registered."""
        from claude_mpm.cli.parsers.session_parser import add_session_subparser

        parser = argparse.ArgumentParser(prog="claude-mpm-test")
        subparsers = parser.add_subparsers(dest="command")
        add_session_subparser(subparsers)
        return parser

    def test_session_pause_sets_command(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause"])
        assert args.command == "session"
        assert args.session_command == "pause"

    def test_session_resume_sets_command(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume"])
        assert args.command == "session"
        assert args.session_command == "resume"

    def test_pause_message_short_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause", "-m", "End of day"])
        assert args.message == "End of day"

    def test_pause_message_long_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause", "--message", "Some context"])
        assert args.message == "Some context"

    def test_pause_no_commit_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause", "--no-commit"])
        assert args.no_commit is True

    def test_pause_export_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause", "--export", "/tmp/out.json"])
        assert args.export == "/tmp/out.json"

    def test_pause_project_path_positional(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause", "/some/project"])
        assert args.project_path == "/some/project"

    def test_pause_project_path_default(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "pause"])
        assert args.project_path == "."

    def test_resume_select_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume", "--select", "2"])
        assert args.select == "2"

    def test_resume_select_partial_id(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume", "--select", "20240101"])
        assert args.select == "20240101"

    def test_resume_exact_session_id(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume", "session-20240101-120000"])
        assert args.session_id == "session-20240101-120000"

    def test_resume_defaults_no_select_no_id(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume"])
        assert args.select is None
        assert args.session_id is None
        assert args.project_path == "."

    def test_resume_project_path_flag(self) -> None:
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume", "--project-path", "/my/project"])
        assert args.project_path == "/my/project"

    def test_resume_project_path_does_not_collide_with_session_id(self) -> None:
        """Passing a path-like string must not be swallowed into session_id."""
        parser = self._make_parser()
        args = parser.parse_args(["session", "resume", "--project-path", "/my/project"])
        assert args.session_id is None
        assert args.project_path == "/my/project"

    def test_session_registered_in_full_parser(self) -> None:
        """Verify the session subparser is visible in the full CLI parser."""
        from claude_mpm.cli.parsers.base_parser import create_parser

        parser = create_parser()
        args = parser.parse_args(["session", "pause"])
        assert args.command == "session"
        assert args.session_command == "pause"


# ---------------------------------------------------------------------------
# Handler dispatch tests
# ---------------------------------------------------------------------------


class TestSessionHandler:
    """Verify manage_session dispatches to the correct shared functions."""

    def _make_args(self, session_command: str, **kwargs) -> argparse.Namespace:
        defaults = {
            "session_command": session_command,
            "project_path": ".",
            "message": None,
            "no_commit": False,
            "export": None,
            "select": None,
            "session_id": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_dispatch_pause_calls_handle_pause(self) -> None:
        from claude_mpm.cli.commands.session import manage_session

        args = self._make_args("pause")
        with patch(
            "claude_mpm.cli.commands.session.handle_pause", return_value=0
        ) as mock_pause:
            result = manage_session(args)
        mock_pause.assert_called_once_with(args)
        assert result == 0

    def test_dispatch_resume_calls_handle_resume(self) -> None:
        from claude_mpm.cli.commands.session import manage_session

        args = self._make_args("resume")
        with patch(
            "claude_mpm.cli.commands.session.handle_resume", return_value=0
        ) as mock_resume:
            result = manage_session(args)
        mock_resume.assert_called_once_with(args)
        assert result == 0

    def test_no_subcommand_returns_nonzero(self) -> None:
        from claude_mpm.cli.commands.session import manage_session

        args = argparse.Namespace(session_command=None)
        result = manage_session(args)
        assert result != 0


# ---------------------------------------------------------------------------
# handle_pause logic tests
# ---------------------------------------------------------------------------


class TestHandlePause:
    """Verify handle_pause drives SessionPauseManager correctly."""

    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "project_path": ".",
            "message": None,
            "no_commit": False,
            "export": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_pause_creates_session(self, tmp_path: Path) -> None:
        from claude_mpm.cli.commands.session_shared import handle_pause

        args = self._make_args(project_path=str(tmp_path))

        mock_manager = MagicMock()
        mock_manager.create_pause_session.return_value = "session-20250101-120000"
        mock_manager._is_git_repo.return_value = False

        # SessionPauseManager is imported lazily inside handle_pause via
        # ``from claude_mpm.services.cli.session_pause_manager import ...``,
        # so we patch it at its source module.
        with patch(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager",
            return_value=mock_manager,
        ):
            result = handle_pause(args)

        assert result == 0
        mock_manager.create_pause_session.assert_called_once_with(
            message=None,
            skip_commit=False,
            export_path=None,
        )

    def test_pause_passes_message(self, tmp_path: Path) -> None:
        from claude_mpm.cli.commands.session_shared import handle_pause

        args = self._make_args(project_path=str(tmp_path), message="Test message")

        mock_manager = MagicMock()
        mock_manager.create_pause_session.return_value = "session-20250101-120000"
        mock_manager._is_git_repo.return_value = False

        with patch(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager",
            return_value=mock_manager,
        ):
            handle_pause(args)

        mock_manager.create_pause_session.assert_called_once_with(
            message="Test message",
            skip_commit=False,
            export_path=None,
        )

    def test_pause_passes_no_commit(self, tmp_path: Path) -> None:
        from claude_mpm.cli.commands.session_shared import handle_pause

        args = self._make_args(project_path=str(tmp_path), no_commit=True)

        mock_manager = MagicMock()
        mock_manager.create_pause_session.return_value = "session-20250101-120000"
        mock_manager._is_git_repo.return_value = False

        with patch(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager",
            return_value=mock_manager,
        ):
            handle_pause(args)

        mock_manager.create_pause_session.assert_called_once_with(
            message=None,
            skip_commit=True,
            export_path=None,
        )

    def test_pause_passes_export(self, tmp_path: Path) -> None:
        from claude_mpm.cli.commands.session_shared import handle_pause

        args = self._make_args(project_path=str(tmp_path), export="/tmp/backup.json")

        mock_manager = MagicMock()
        mock_manager.create_pause_session.return_value = "session-20250101-120000"
        mock_manager._is_git_repo.return_value = False

        with patch(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager",
            return_value=mock_manager,
        ):
            handle_pause(args)

        mock_manager.create_pause_session.assert_called_once_with(
            message=None,
            skip_commit=False,
            export_path="/tmp/backup.json",
        )

    def test_pause_returns_1_on_exception(self, tmp_path: Path) -> None:
        from claude_mpm.cli.commands.session_shared import handle_pause

        args = self._make_args(project_path=str(tmp_path))

        mock_manager = MagicMock()
        mock_manager.create_pause_session.side_effect = RuntimeError("disk full")
        mock_manager._is_git_repo.return_value = False

        with patch(
            "claude_mpm.services.cli.session_pause_manager.SessionPauseManager",
            return_value=mock_manager,
        ):
            result = handle_pause(args)

        assert result == 1


# ---------------------------------------------------------------------------
# handle_resume logic tests
# ---------------------------------------------------------------------------


class TestHandleResume:
    """Verify handle_resume routes --select, exact-id, and default correctly."""

    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "project_path": ".",
            "select": None,
            "session_id": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def _mock_helper(self, **kwargs) -> MagicMock:
        helper = MagicMock()
        helper.get_session_count.return_value = kwargs.get("session_count", 0)
        helper.list_all_sessions.return_value = kwargs.get("sessions", [])
        helper.check_and_display_resume_prompt.return_value = kwargs.get("session_data")
        helper.format_session_list.return_value = "Session list output"
        helper.format_resume_prompt.return_value = "Resume prompt"
        helper.resolve_session_by_selection.return_value = kwargs.get(
            "resolve_result", (None, "Not found")
        )
        return helper

    def test_no_sessions_returns_0(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        args = self._make_args()
        mock_helper = self._mock_helper(session_count=0)

        # SessionResumeHelper is imported lazily inside handle_resume via
        # ``from claude_mpm.services.cli.session_resume_helper import ...``,
        # so we patch at its source module.
        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 0

    def test_single_session_resumes_directly(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        session = {"session_id": "session-20250101-120000", "file_path": None}
        args = self._make_args()
        mock_helper = self._mock_helper(session_count=1, session_data=session)

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 0
        mock_helper.check_and_display_resume_prompt.assert_called_once()

    def test_multiple_sessions_shows_list_and_resumes_most_recent(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        session = {"session_id": "session-20250101-120000", "file_path": None}
        args = self._make_args()
        mock_helper = self._mock_helper(session_count=3, session_data=session)

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 0
        mock_helper.format_session_list.assert_called_once()
        mock_helper.check_and_display_resume_prompt.assert_called_once()

    def test_select_flag_uses_resolve_session(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        session = {"session_id": "session-20250101-120000", "file_path": None}
        args = self._make_args(select="2")
        mock_helper = self._mock_helper(resolve_result=(session, ""))

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 0
        mock_helper.resolve_session_by_selection.assert_called_once_with("2")

    def test_select_flag_not_found_returns_1(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        args = self._make_args(select="99")
        mock_helper = self._mock_helper(
            resolve_result=(None, "Index 99 is out of range")
        )

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 1

    def test_exact_session_id_match(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        session = {
            "session_id": "session-20250101-120000",
            "file_path": None,
        }
        args = self._make_args(session_id="session-20250101-120000")
        mock_helper = self._mock_helper(sessions=[session])

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 0
        mock_helper.list_all_sessions.assert_called_once()
        mock_helper.format_resume_prompt.assert_called_once_with(session)

    def test_exact_session_id_no_match_returns_1(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        args = self._make_args(session_id="session-does-not-exist")
        mock_helper = self._mock_helper(sessions=[])

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 1

    def test_exception_in_helper_returns_1(self) -> None:
        from claude_mpm.cli.commands.session_shared import handle_resume

        args = self._make_args()
        mock_helper = self._mock_helper(session_count=1)
        mock_helper.check_and_display_resume_prompt.side_effect = RuntimeError(
            "disk error"
        )

        with patch(
            "claude_mpm.services.cli.session_resume_helper.SessionResumeHelper",
            return_value=mock_helper,
        ):
            result = handle_resume(args)

        assert result == 1


# ---------------------------------------------------------------------------
# Back-compat: mpm-init pause still routes to shared logic
# ---------------------------------------------------------------------------


class TestMpmInitPauseBackCompat:
    """Ensure mpm-init pause still calls the shared handle_pause function."""

    def test_mpm_init_pause_delegates_to_handle_pause(self) -> None:
        from claude_mpm.cli.commands.mpm_init_handler import manage_mpm_init

        args = argparse.Namespace(
            subcommand="pause",
            project_path=".",
            message=None,
            no_commit=False,
            export=None,
            verbose=False,
        )

        # handle_pause is imported from .session_shared inside manage_mpm_init;
        # patch it at its canonical location so the lazy import picks up the mock.
        with patch(
            "claude_mpm.cli.commands.session_shared.handle_pause", return_value=0
        ) as mock_pause:
            result = manage_mpm_init(args)

        mock_pause.assert_called_once_with(args)
        assert result == 0
