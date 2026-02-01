"""
Unit tests for CLI adapters.
Tests the CLIAdapter base class and all concrete adapter implementations.
"""

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from claude_mpm.adapters.cli_adapters import (
    ADAPTERS,
    AuggieAdapter,
    ClaudeAdapter,
    CLIAdapter,
    CodexAdapter,
    GeminiAdapter,
    get_adapter,
    get_available_adapters,
)


class TestCLIAdapterBaseClass(unittest.TestCase):
    """Test CLIAdapter abstract base class."""

    def test_adapter_has_required_attributes(self):
        """All adapters must define name and command class attributes."""
        for name, cls in ADAPTERS.items():
            adapter = cls()
            self.assertTrue(hasattr(adapter, "name"), f"{name} missing name attribute")
            self.assertTrue(
                hasattr(adapter, "command"), f"{name} missing command attribute"
            )
            self.assertIsInstance(adapter.name, str)
            self.assertIsInstance(adapter.command, str)

    def test_adapter_has_required_methods(self):
        """All adapters must implement invoke and invoke_json methods."""
        for name, cls in ADAPTERS.items():
            adapter = cls()
            self.assertTrue(
                callable(getattr(adapter, "invoke", None)),
                f"{name} missing invoke method",
            )
            self.assertTrue(
                callable(getattr(adapter, "invoke_json", None)),
                f"{name} missing invoke_json method",
            )
            self.assertTrue(
                callable(getattr(adapter, "is_available", None)),
                f"{name} missing is_available method",
            )


class TestIsAvailable(unittest.TestCase):
    """Test is_available() method for each adapter."""

    @patch("shutil.which")
    def test_is_available_when_command_exists(self, mock_which):
        """is_available returns True when CLI command is found."""
        mock_which.return_value = "/usr/local/bin/claude"
        adapter = ClaudeAdapter()
        self.assertTrue(adapter.is_available())
        mock_which.assert_called_once_with("claude")

    @patch("shutil.which")
    def test_is_available_when_command_missing(self, mock_which):
        """is_available returns False when CLI command is not found."""
        mock_which.return_value = None
        adapter = ClaudeAdapter()
        self.assertFalse(adapter.is_available())

    @patch("shutil.which")
    def test_all_adapters_check_correct_command(self, mock_which):
        """Each adapter checks for its specific command."""
        expected_commands = {
            "claude": "claude",
            "codex": "codex",
            "auggie": "auggie",
            "gemini": "gemini",
        }

        for name, cls in ADAPTERS.items():
            mock_which.reset_mock()
            mock_which.return_value = None
            adapter = cls()
            adapter.is_available()
            mock_which.assert_called_once_with(expected_commands[name])


class TestGetAdapter(unittest.TestCase):
    """Test get_adapter() function."""

    def test_get_adapter_returns_correct_type(self):
        """get_adapter returns correct adapter instance for each name."""
        self.assertIsInstance(get_adapter("claude"), ClaudeAdapter)
        self.assertIsInstance(get_adapter("codex"), CodexAdapter)
        self.assertIsInstance(get_adapter("auggie"), AuggieAdapter)
        self.assertIsInstance(get_adapter("gemini"), GeminiAdapter)

    def test_get_adapter_default_is_claude(self):
        """get_adapter defaults to ClaudeAdapter when no name specified."""
        adapter = get_adapter()
        self.assertIsInstance(adapter, ClaudeAdapter)

    def test_get_adapter_invalid_name_raises_value_error(self):
        """get_adapter raises ValueError for unknown adapter names."""
        with self.assertRaises(ValueError) as context:
            get_adapter("nonexistent")

        self.assertIn("Unknown adapter", str(context.exception))
        self.assertIn("nonexistent", str(context.exception))
        self.assertIn("Available:", str(context.exception))

    def test_get_adapter_error_message_lists_available_adapters(self):
        """ValueError message includes list of available adapters."""
        with self.assertRaises(ValueError) as context:
            get_adapter("invalid")

        error_msg = str(context.exception)
        for name in ADAPTERS:
            self.assertIn(name, error_msg)


class TestGetAvailableAdapters(unittest.TestCase):
    """Test get_available_adapters() function."""

    @patch("shutil.which")
    def test_returns_empty_list_when_none_available(self, mock_which):
        """get_available_adapters returns empty list when no CLIs installed."""
        mock_which.return_value = None
        result = get_available_adapters()
        self.assertEqual(result, [])

    @patch("shutil.which")
    def test_returns_only_available_adapters(self, mock_which):
        """get_available_adapters returns only installed CLIs."""

        def which_side_effect(cmd):
            return "/usr/bin/claude" if cmd == "claude" else None

        mock_which.side_effect = which_side_effect
        result = get_available_adapters()
        self.assertEqual(result, ["claude"])

    @patch("shutil.which")
    def test_returns_all_when_all_available(self, mock_which):
        """get_available_adapters returns all when all CLIs installed."""
        mock_which.return_value = "/usr/bin/command"
        result = get_available_adapters()
        self.assertEqual(sorted(result), sorted(ADAPTERS.keys()))


class TestClaudeAdapter(unittest.TestCase):
    """Test ClaudeAdapter implementation."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = ClaudeAdapter()

    def test_name_and_command(self):
        """ClaudeAdapter has correct name and command."""
        self.assertEqual(self.adapter.name, "claude")
        self.assertEqual(self.adapter.command, "claude")

    @patch("subprocess.run")
    def test_invoke_calls_claude_with_prompt(self, mock_run):
        """invoke calls claude CLI with correct arguments."""
        mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
        result = self.adapter.invoke("test prompt")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["claude", "-p", "test prompt"])
        self.assertEqual(result, "response")

    @patch("subprocess.run")
    def test_invoke_json_calls_claude_with_json_format(self, mock_run):
        """invoke_json calls claude CLI with JSON output format."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"result": "test"}', stderr=""
        )
        result = self.adapter.invoke_json("test prompt")

        args = mock_run.call_args[0][0]
        self.assertIn("--output-format", args)
        self.assertIn("json", args)
        self.assertEqual(result, {"result": "test"})


class TestCodexAdapter(unittest.TestCase):
    """Test CodexAdapter implementation."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = CodexAdapter()

    def test_name_and_command(self):
        """CodexAdapter has correct name and command."""
        self.assertEqual(self.adapter.name, "codex")
        self.assertEqual(self.adapter.command, "codex")

    @patch("subprocess.run")
    def test_invoke_calls_codex_exec(self, mock_run):
        """invoke calls codex exec with prompt."""
        mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
        result = self.adapter.invoke("test prompt")

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["codex", "exec", "test prompt"])
        self.assertEqual(result, "response")

    @patch("subprocess.run")
    def test_invoke_json_parses_jsonl_format(self, mock_run):
        """invoke_json parses JSONL format from codex."""
        jsonl_output = '{"line": 1}\n{"line": 2}'
        mock_run.return_value = MagicMock(returncode=0, stdout=jsonl_output, stderr="")
        result = self.adapter.invoke_json("test prompt")

        self.assertIn("responses", result)
        self.assertIn("final", result)
        self.assertEqual(len(result["responses"]), 2)
        self.assertEqual(result["final"], {"line": 2})


class TestAuggieAdapter(unittest.TestCase):
    """Test AuggieAdapter implementation."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = AuggieAdapter()

    def test_name_and_command(self):
        """AuggieAdapter has correct name and command."""
        self.assertEqual(self.adapter.name, "auggie")
        self.assertEqual(self.adapter.command, "auggie")

    @patch("subprocess.run")
    def test_invoke_calls_auggie_with_print_quiet(self, mock_run):
        """invoke calls auggie with --print and --quiet flags."""
        mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
        result = self.adapter.invoke("test prompt")

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["auggie", "--print", "--quiet", "test prompt"])
        self.assertEqual(result, "response")

    @patch("subprocess.run")
    def test_invoke_json_wraps_text_response(self, mock_run):
        """invoke_json wraps text response since auggie has no native JSON."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="text response", stderr=""
        )
        result = self.adapter.invoke_json("test prompt")

        self.assertEqual(result["response"], "text response")
        self.assertEqual(result["format"], "text")


class TestGeminiAdapter(unittest.TestCase):
    """Test GeminiAdapter implementation."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = GeminiAdapter()

    def test_name_and_command(self):
        """GeminiAdapter has correct name and command."""
        self.assertEqual(self.adapter.name, "gemini")
        self.assertEqual(self.adapter.command, "gemini")

    @patch("subprocess.run")
    def test_invoke_calls_gemini_with_default_model(self, mock_run):
        """invoke calls gemini with default flash model."""
        mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
        result = self.adapter.invoke("test prompt")

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["gemini", "-m", "flash", "-p", "test prompt"])
        self.assertEqual(result, "response")

    @patch("subprocess.run")
    def test_invoke_with_custom_model(self, mock_run):
        """invoke uses specified model when provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
        self.adapter.invoke("test prompt", model="pro")

        args = mock_run.call_args[0][0]
        self.assertIn("-m", args)
        self.assertIn("pro", args)

    @patch("subprocess.run")
    def test_invoke_json_parses_json_output(self, mock_run):
        """invoke_json parses JSON output from gemini."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"result": "test"}', stderr=""
        )
        result = self.adapter.invoke_json("test prompt")

        args = mock_run.call_args[0][0]
        self.assertIn("-o", args)
        self.assertIn("json", args)
        self.assertEqual(result, {"result": "test"})


class TestRunMethod(unittest.TestCase):
    """Test the _run method error handling."""

    def setUp(self):
        """Set up test adapter."""
        self.adapter = ClaudeAdapter()

    @patch("subprocess.run")
    def test_run_raises_on_nonzero_exit(self, mock_run):
        """_run raises RuntimeError when CLI returns non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: something went wrong"
        )

        with self.assertRaises(RuntimeError) as context:
            self.adapter.invoke("test prompt")

        self.assertIn("claude error", str(context.exception))
        self.assertIn("something went wrong", str(context.exception))

    @patch("subprocess.run")
    def test_run_has_timeout(self, mock_run):
        """_run passes timeout to subprocess."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        self.adapter.invoke("test")

        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("timeout"), 300)

    @patch("subprocess.run")
    def test_run_captures_output(self, mock_run):
        """_run captures both stdout and stderr."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        self.adapter.invoke("test")

        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))


class TestADAPTERSRegistry(unittest.TestCase):
    """Test the ADAPTERS registry dictionary."""

    def test_registry_contains_all_adapters(self):
        """ADAPTERS registry contains all expected adapter types."""
        expected = {"claude", "codex", "auggie", "gemini"}
        self.assertEqual(set(ADAPTERS.keys()), expected)

    def test_registry_values_are_adapter_classes(self):
        """All registry values are CLIAdapter subclasses."""
        for name, cls in ADAPTERS.items():
            self.assertTrue(
                issubclass(cls, CLIAdapter),
                f"{name} is not a CLIAdapter subclass",
            )


if __name__ == "__main__":
    unittest.main()
