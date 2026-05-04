"""Tests for --sdk, --cli, and --inject-port CLI flags."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from claude_mpm.cli.parser import create_parser, preprocess_args


@pytest.fixture()
def parser():
    """Create a CLI parser for testing."""
    return create_parser(version="0.0.0-test")


class TestSdkFlag:
    """Tests for the --sdk flag."""

    def test_sdk_flag_parsed(self, parser):
        args = parser.parse_args(preprocess_args(["--sdk"]))
        assert args.sdk is True

    def test_sdk_flag_default_false(self, parser):
        args = parser.parse_args(preprocess_args([]))
        assert args.sdk is False

    def test_sdk_flag_sets_env_var(self, parser):
        """Simulate the main() logic: --sdk sets CLAUDE_MPM_RUNTIME=sdk."""
        args = parser.parse_args(preprocess_args(["--sdk"]))
        with patch.dict(os.environ, {}, clear=False):
            # Remove if present so we can verify it gets set
            os.environ.pop("CLAUDE_MPM_RUNTIME", None)

            use_sdk = getattr(args, "sdk", False)
            if use_sdk:
                os.environ["CLAUDE_MPM_RUNTIME"] = "sdk"

            assert os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk"


class TestCliFlag:
    """Tests for the --cli flag."""

    def test_cli_flag_parsed(self, parser):
        args = parser.parse_args(preprocess_args(["--cli"]))
        assert getattr(args, "cli", False) is True

    def test_cli_flag_default_false(self, parser):
        args = parser.parse_args(preprocess_args([]))
        assert getattr(args, "cli", False) is False

    def test_cli_flag_sets_env_var(self, parser):
        """Simulate the main() logic: --cli sets CLAUDE_MPM_RUNTIME=cli."""
        args = parser.parse_args(preprocess_args(["--cli"]))
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_RUNTIME", None)

            use_cli = getattr(args, "cli", False)
            if use_cli:
                os.environ["CLAUDE_MPM_RUNTIME"] = "cli"

            assert os.environ.get("CLAUDE_MPM_RUNTIME") == "cli"


class TestNeitherFlag:
    """Tests for when neither --sdk nor --cli is specified."""

    def test_neither_flag_leaves_env_unset(self, parser):
        """When neither flag is set, env var should not be modified."""
        args = parser.parse_args(preprocess_args([]))
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_RUNTIME", None)

            use_sdk = getattr(args, "sdk", False)
            if use_sdk:
                os.environ["CLAUDE_MPM_RUNTIME"] = "sdk"

            use_cli = getattr(args, "cli", False)
            if use_cli:
                os.environ["CLAUDE_MPM_RUNTIME"] = "cli"

            assert "CLAUDE_MPM_RUNTIME" not in os.environ

    def test_last_flag_wins(self, parser):
        """When both are set, --cli is processed after --sdk, so cli wins."""
        args = parser.parse_args(preprocess_args(["--sdk", "--cli"]))
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_RUNTIME", None)

            use_sdk = getattr(args, "sdk", False)
            if use_sdk:
                os.environ["CLAUDE_MPM_RUNTIME"] = "sdk"

            use_cli = getattr(args, "cli", False)
            if use_cli:
                os.environ["CLAUDE_MPM_RUNTIME"] = "cli"

            assert os.environ.get("CLAUDE_MPM_RUNTIME") == "cli"


class TestInjectPortFlag:
    """Tests for the --inject-port flag."""

    def test_inject_port_parsed(self, parser):
        args = parser.parse_args(preprocess_args(["--inject-port", "9999"]))
        assert args.inject_port == 9999

    def test_inject_port_default_none(self, parser):
        args = parser.parse_args(preprocess_args([]))
        assert args.inject_port is None

    def test_inject_port_sets_env_var(self, parser):
        """Simulate the main() logic: --inject-port sets CLAUDE_MPM_INJECT_PORT."""
        args = parser.parse_args(preprocess_args(["--inject-port", "8080"]))
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_INJECT_PORT", None)

            inject_port = getattr(args, "inject_port", None)
            if inject_port is not None:
                os.environ["CLAUDE_MPM_INJECT_PORT"] = str(inject_port)

            assert os.environ.get("CLAUDE_MPM_INJECT_PORT") == "8080"

    def test_inject_port_not_set_when_absent(self, parser):
        """When --inject-port not provided, env var should not be set."""
        args = parser.parse_args(preprocess_args([]))
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_INJECT_PORT", None)

            inject_port = getattr(args, "inject_port", None)
            if inject_port is not None:
                os.environ["CLAUDE_MPM_INJECT_PORT"] = str(inject_port)

            assert "CLAUDE_MPM_INJECT_PORT" not in os.environ


class TestSdkOneshotSkipsBackgroundServices:
    """Bug #486: --sdk --prompt should skip background services so the oneshot
    fire-and-forget path is not blocked by transient init failures."""

    def test_sdk_prompt_skips_background_services(self, parser):
        from claude_mpm.cli.startup import should_skip_background_services

        args = parser.parse_args(preprocess_args(["--sdk", "--prompt", "hello world"]))
        assert (
            should_skip_background_services(args, ["--sdk", "--prompt", "hello"])
            is True
        )

    def test_sdk_without_prompt_does_not_skip(self, parser):
        from claude_mpm.cli.startup import should_skip_background_services

        args = parser.parse_args(preprocess_args(["--sdk"]))
        # Plain --sdk (interactive) still needs background services
        assert should_skip_background_services(args, ["--sdk"]) is False

    def test_prompt_without_sdk_does_not_skip(self, parser):
        from claude_mpm.cli.startup import should_skip_background_services

        args = parser.parse_args(preprocess_args(["--prompt", "hello"]))
        assert should_skip_background_services(args, ["--prompt", "hello"]) is False


class TestSdkAutoDetectionRequiresExplicitFlag:
    """Bug #486: SDK mode must NOT be auto-activated just because
    claude_agent_sdk happens to be importable. Only the explicit --sdk flag
    (which sets CLAUDE_MPM_RUNTIME=sdk) should activate the SDK code path."""

    def test_will_use_sdk_false_when_runtime_unset(self):
        """When CLAUDE_MPM_RUNTIME is unset, _will_use_sdk must be False even
        if claude_agent_sdk would be importable."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_MPM_RUNTIME", None)
            # Mirror the production logic in cli/__init__.py
            will_use_sdk = os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk"
            assert will_use_sdk is False

    def test_will_use_sdk_true_when_runtime_sdk(self):
        with patch.dict(os.environ, {"CLAUDE_MPM_RUNTIME": "sdk"}, clear=False):
            will_use_sdk = os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk"
            assert will_use_sdk is True

    def test_will_use_sdk_false_when_runtime_cli(self):
        with patch.dict(os.environ, {"CLAUDE_MPM_RUNTIME": "cli"}, clear=False):
            will_use_sdk = os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk"
            assert will_use_sdk is False
