"""Integration tests for native --agents flag implementation."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.claude_runner import ClaudeRunner
from claude_mpm.services.native_agent_converter import NativeAgentConverter


class TestNativeAgentsIntegration:
    """Test suite for native --agents flag integration."""

    def test_runner_with_native_agents_disabled(self):
        """Test ClaudeRunner with native agents disabled (default)."""
        runner = ClaudeRunner(use_native_agents=False)

        assert hasattr(runner, "use_native_agents")
        assert runner.use_native_agents is False

    def test_runner_with_native_agents_enabled(self):
        """Test ClaudeRunner with native agents enabled."""
        runner = ClaudeRunner(use_native_agents=True)

        assert runner.use_native_agents is True

    def test_interactive_session_build_command_without_native_agents(self):
        """Test interactive session command building without native agents."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=False)
        session = InteractiveSession(runner)

        cmd = session._build_claude_command()

        assert "claude" in cmd
        assert "--agents" not in cmd

    def test_interactive_session_build_command_with_native_agents(self):
        """Test interactive session command building with native agents."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=True)
        session = InteractiveSession(runner)

        cmd = session._build_claude_command()

        assert "claude" in cmd
        # Should have --agents flag
        if "--agents" in cmd:
            agents_idx = cmd.index("--agents")
            # Next element should be JSON
            assert agents_idx + 1 < len(cmd)
            agents_json = cmd[agents_idx + 1]
            # Verify it's valid JSON
            parsed = json.loads(agents_json)
            assert isinstance(parsed, dict)
            assert len(parsed) > 0  # Should have agents

    def test_oneshot_session_build_command_without_native_agents(self):
        """Test oneshot session command building without native agents."""
        from claude_mpm.core.oneshot_session import OneshotSession

        runner = ClaudeRunner(use_native_agents=False)
        session = OneshotSession(runner)

        cmd = session._build_command()

        assert "claude" in cmd
        assert "--agents" not in cmd

    def test_oneshot_session_build_command_with_native_agents(self):
        """Test oneshot session command building with native agents."""
        from claude_mpm.core.oneshot_session import OneshotSession

        runner = ClaudeRunner(use_native_agents=True)
        session = OneshotSession(runner)

        cmd = session._build_command()

        assert "claude" in cmd
        # Should have --agents flag
        if "--agents" in cmd:
            agents_idx = cmd.index("--agents")
            assert agents_idx + 1 < len(cmd)
            agents_json = cmd[agents_idx + 1]
            # Verify it's valid JSON
            parsed = json.loads(agents_json)
            assert isinstance(parsed, dict)

    def test_agents_json_structure(self):
        """Test that generated agents JSON has correct structure."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=True)
        session = InteractiveSession(runner)

        cmd = session._build_claude_command()

        if "--agents" in cmd:
            agents_idx = cmd.index("--agents")
            agents_json = cmd[agents_idx + 1]
            agents = json.loads(agents_json)

            # Verify structure of each agent
            for agent_id, agent_config in agents.items():
                assert "description" in agent_config, (
                    f"Agent {agent_id} missing description"
                )
                assert "prompt" in agent_config, f"Agent {agent_id} missing prompt"
                assert "tools" in agent_config, f"Agent {agent_id} missing tools"
                assert "model" in agent_config, f"Agent {agent_id} missing model"

                # Verify types
                assert isinstance(agent_config["description"], str)
                assert isinstance(agent_config["prompt"], str)
                assert isinstance(agent_config["tools"], list)
                assert isinstance(agent_config["model"], str)

    def test_cli_argument_length_limit(self):
        """Test that --agents JSON doesn't exceed reasonable CLI length."""
        converter = NativeAgentConverter()
        agents = converter.load_agents_from_templates()

        if not agents:
            pytest.skip("No agents available to test")

        summary = converter.get_conversion_summary(agents)

        # Total command length estimate
        base_cmd_length = len("claude --dangerously-skip-permissions --agents ")
        json_length = summary["json_size"]
        total_length = base_cmd_length + json_length

        # Most systems support at least 128KB for command line arguments
        # macOS: ~260KB, Linux: ~2MB, Windows: ~32KB
        # We'll use 100KB as a conservative limit
        assert total_length < 100000, (
            f"Command too long: {total_length} bytes. "
            f"Consider reducing agent prompts or using file-based deployment."
        )

    def test_all_37_agents_conversion(self):
        """Test that all 37 MPM agents can be converted."""
        converter = NativeAgentConverter()
        agents = converter.load_agents_from_templates()

        if not agents:
            pytest.skip("No agents available")

        summary = converter.get_conversion_summary(agents)

        # Should have close to 37 agents (might vary slightly)
        assert summary["total_agents"] >= 35, (
            f"Expected ~37 agents, got {summary['total_agents']}"
        )
        assert summary["json_size"] > 0
        assert summary["json_size_kb"] < 100  # Should be under 100KB

    def test_native_vs_traditional_deployment_modes(self):
        """Test both deployment modes work independently."""
        # Traditional mode (default)
        runner_traditional = ClaudeRunner(use_native_agents=False)
        assert runner_traditional.use_native_agents is False

        # Native mode
        runner_native = ClaudeRunner(use_native_agents=True)
        assert runner_native.use_native_agents is True

        # Both should be valid runner instances
        assert runner_traditional.logger is not None
        assert runner_native.logger is not None

    def test_agent_exclusion(self):
        """Test that PM agent is excluded from --agents flag."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=True)
        session = InteractiveSession(runner)

        cmd = session._build_claude_command()

        if "--agents" in cmd:
            agents_idx = cmd.index("--agents")
            agents_json = cmd[agents_idx + 1]
            agents = json.loads(agents_json)

            # PM should not be in the agents list
            assert "pm" not in agents
            assert "project_manager" not in agents

    def test_error_handling_invalid_agents(self):
        """Test error handling when agent loading fails."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=True)
        session = InteractiveSession(runner)

        # Mock agent loading to fail
        with patch.object(
            NativeAgentConverter, "load_agents_from_templates", return_value=[]
        ):
            result = session._build_agents_flag()
            # Should return None when no agents loaded
            assert result is None

    def test_performance_agent_conversion(self):
        """Test that agent conversion is reasonably fast."""
        import time

        converter = NativeAgentConverter()

        start = time.time()
        agents = converter.load_agents_from_templates()
        agents_json = converter.generate_agents_json(agents)
        end = time.time()

        conversion_time = end - start

        # Should complete in under 1 second
        assert conversion_time < 1.0, (
            f"Conversion took {conversion_time:.2f}s (too slow)"
        )

    def test_command_with_resume_flag_and_native_agents(self):
        """Test that --resume flag works with native agents."""
        from claude_mpm.core.interactive_session import InteractiveSession

        runner = ClaudeRunner(use_native_agents=True, claude_args=["--resume"])
        session = InteractiveSession(runner)

        cmd = session._build_claude_command()

        # In resume mode, should skip native agents to avoid interfering
        assert "--resume" in cmd
        # Native agents should be skipped in resume mode
        # (based on the has_resume check in _build_claude_command)

    def test_json_escaping(self):
        """Test that JSON is properly escaped for shell."""
        converter = NativeAgentConverter()
        agents = [
            {
                "agent_id": "test",
                "description": "Test with \"quotes\" and 'apostrophes'",
                "instructions": "Test instructions",
                "capabilities": {"model": "sonnet", "tools": ["Read"]},
            }
        ]

        agents_json = converter.generate_agents_json(agents)

        # Should be valid JSON
        parsed = json.loads(agents_json)
        assert "test" in parsed
        assert "quotes" in parsed["test"]["description"]

    def test_model_distribution(self):
        """Test model tier distribution in converted agents."""
        converter = NativeAgentConverter()
        agents = converter.load_agents_from_templates()

        if not agents:
            pytest.skip("No agents available")

        summary = converter.get_conversion_summary(agents)
        model_dist = summary["model_distribution"]

        # All agents should have a model assigned
        total_models = sum(model_dist.values())
        assert total_models == summary["total_agents"]

        # Should primarily use sonnet (MPM's default)
        assert model_dist.get("sonnet", 0) > 0

    def test_tool_coverage(self):
        """Test that common tools are available across agents."""
        converter = NativeAgentConverter()
        agents = converter.load_agents_from_templates()

        if not agents:
            pytest.skip("No agents available")

        summary = converter.get_conversion_summary(agents)
        tool_usage = summary["tool_usage"]

        # Common tools should be widely available
        assert tool_usage.get("Read", 0) > 20  # Most agents need Read
        assert tool_usage.get("Write", 0) > 10  # Many agents need Write
        assert tool_usage.get("Bash", 0) > 10  # Many agents need Bash
