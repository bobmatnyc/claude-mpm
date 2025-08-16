"""Tests for the run-guarded CLI command."""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from claude_mpm.cli.commands.run_guarded import (
    add_run_guarded_parser,
    execute_run_guarded,
    load_config_file
)
from claude_mpm.config.memory_guardian_config import (
    MemoryGuardianConfig,
    MemoryThresholds
)


class TestRunGuardedParser(unittest.TestCase):
    """Test run-guarded command parser."""
    
    def setUp(self):
        """Set up test parser."""
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(dest='command')
        add_run_guarded_parser(self.subparsers)
    
    def test_parser_creation(self):
        """Test that parser is created correctly."""
        args = self.parser.parse_args(['run-guarded'])
        self.assertEqual(args.command, 'run-guarded')
    
    def test_default_values(self):
        """Test default argument values."""
        args = self.parser.parse_args(['run-guarded'])
        self.assertEqual(args.memory_threshold, 18000)
        self.assertEqual(args.check_interval, 30)
        self.assertEqual(args.max_restarts, 3)
        self.assertTrue(args.state_preservation)
    
    def test_memory_threshold_argument(self):
        """Test memory threshold argument."""
        args = self.parser.parse_args(['run-guarded', '--memory-threshold', '16000'])
        self.assertEqual(args.memory_threshold, 16000)
    
    def test_check_interval_argument(self):
        """Test check interval argument."""
        args = self.parser.parse_args(['run-guarded', '--check-interval', '10'])
        self.assertEqual(args.check_interval, 10)
    
    def test_max_restarts_argument(self):
        """Test max restarts argument."""
        args = self.parser.parse_args(['run-guarded', '--max-restarts', '5'])
        self.assertEqual(args.max_restarts, 5)
    
    def test_state_preservation_flags(self):
        """Test state preservation enable/disable flags."""
        # Test disable flag
        args = self.parser.parse_args(['run-guarded', '--no-state-preservation'])
        self.assertFalse(args.state_preservation)
        
        # Test enable flag (should be default)
        args = self.parser.parse_args(['run-guarded', '--enable-state-preservation'])
        self.assertTrue(args.state_preservation)
    
    def test_config_file_argument(self):
        """Test configuration file argument."""
        args = self.parser.parse_args(['run-guarded', '--config', '/path/to/config.yaml'])
        self.assertEqual(args.config_file, Path('/path/to/config.yaml'))
    
    def test_verbosity_flags(self):
        """Test quiet and verbose flags."""
        args = self.parser.parse_args(['run-guarded', '--quiet'])
        self.assertTrue(args.quiet)
        
        args = self.parser.parse_args(['run-guarded', '--verbose'])
        self.assertTrue(args.verbose)
    
    def test_claude_args_remainder(self):
        """Test that remaining arguments are captured for Claude."""
        args = self.parser.parse_args(['run-guarded', '--', '--model', 'sonnet'])
        # argparse.REMAINDER includes the '--' separator
        self.assertEqual(args.claude_args, ['--', '--model', 'sonnet'])


class TestConfigLoading(unittest.TestCase):
    """Test configuration file loading."""
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent config file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=True) as f:
            # File is deleted immediately
            pass
        
        config = load_config_file(Path(f.name))
        self.assertIsNone(config)
    
    def test_load_config_file_invalid_yaml(self):
        """Test loading invalid YAML file."""
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = Path(f.name)
        
        try:
            with patch.object(yaml, 'safe_load', side_effect=Exception("Invalid YAML")):
                config = load_config_file(config_path)
                self.assertIsNone(config)
        finally:
            config_path.unlink()
    
    def test_load_valid_config_file(self):
        """Test loading valid configuration file."""
        config_content = """
enabled: true
thresholds:
  warning: 12000
  critical: 15000
  emergency: 18000
monitoring:
  normal_interval: 20
restart_policy:
  max_attempts: 5
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)
        
        try:
            config = load_config_file(config_path)
            self.assertIsNotNone(config)
            self.assertEqual(config.thresholds.critical, 15000)
            self.assertEqual(config.monitoring.normal_interval, 20)
            self.assertEqual(config.restart_policy.max_attempts, 5)
        finally:
            config_path.unlink()


class TestExecuteRunGuarded(unittest.TestCase):
    """Test execute_run_guarded function."""
    
    def setUp(self):
        """Set up test environment."""
        self.args = argparse.Namespace(
            memory_threshold=18000,
            check_interval=30,
            max_restarts=3,
            state_preservation=True,
            no_tickets=False,
            no_native_agents=False,
            claude_args=[],
            websocket_port=8765,
            logging='INFO',
            quiet=False,
            verbose=False,
            show_stats=False,
            non_interactive=False,
            config_file=None,
            input=None,
            state_dir=None
        )
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_with_defaults(self, mock_setup_logging, mock_runner_class):
        """Test execution with default arguments."""
        mock_runner = Mock()
        mock_runner.setup_agents.return_value = True
        mock_runner.run_interactive_with_monitoring = Mock()
        mock_runner_class.return_value = mock_runner
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 0)
        mock_setup_logging.assert_called_once()
        mock_runner.setup_agents.assert_called_once()
        mock_runner.run_interactive_with_monitoring.assert_called_once()
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_with_custom_threshold(self, mock_setup_logging, mock_runner_class):
        """Test execution with custom memory threshold."""
        self.args.memory_threshold = 16000
        
        mock_runner = Mock()
        mock_runner.setup_agents.return_value = True
        mock_runner.run_interactive_with_monitoring = Mock()
        mock_runner_class.return_value = mock_runner
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 0)
        
        # Check that config was created with custom threshold
        call_args = mock_runner_class.call_args
        self.assertIsNotNone(call_args)
        config = call_args.kwargs['memory_config']
        self.assertEqual(config.thresholds.critical, 16000)
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_no_agents(self, mock_setup_logging, mock_runner_class):
        """Test execution with agents disabled."""
        self.args.no_native_agents = True
        
        mock_runner = Mock()
        mock_runner.run_interactive_with_monitoring = Mock()
        mock_runner_class.return_value = mock_runner
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 0)
        mock_runner.setup_agents.assert_not_called()
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_with_input_file(self, mock_setup_logging, mock_runner_class):
        """Test execution with input file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Initial context from file")
            input_file = Path(f.name)
        
        try:
            self.args.input = str(input_file)
            
            mock_runner = Mock()
            mock_runner.setup_agents.return_value = True
            mock_runner.run_interactive_with_monitoring = Mock()
            mock_runner_class.return_value = mock_runner
            
            result = execute_run_guarded(self.args)
            
            self.assertEqual(result, 0)
            
            # Check that initial context was passed
            call_args = mock_runner.run_interactive_with_monitoring.call_args
            self.assertEqual(call_args.kwargs['initial_context'], "Initial context from file")
            
        finally:
            input_file.unlink()
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_non_interactive_not_supported(self, mock_setup_logging, mock_runner_class):
        """Test that non-interactive mode returns error."""
        self.args.non_interactive = True
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 1)
        mock_runner_class.assert_not_called()
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_keyboard_interrupt(self, mock_setup_logging, mock_runner_class):
        """Test handling of keyboard interrupt."""
        mock_runner = Mock()
        mock_runner.setup_agents.return_value = True
        mock_runner.run_interactive_with_monitoring.side_effect = KeyboardInterrupt()
        mock_runner_class.return_value = mock_runner
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 130)  # Standard exit code for SIGINT
    
    @patch('claude_mpm.cli.commands.run_guarded.MemoryAwareClaudeRunner')
    @patch('claude_mpm.cli.commands.run_guarded.setup_logging')
    def test_execute_general_exception(self, mock_setup_logging, mock_runner_class):
        """Test handling of general exceptions."""
        mock_runner = Mock()
        mock_runner.setup_agents.return_value = True
        mock_runner.run_interactive_with_monitoring.side_effect = Exception("Test error")
        mock_runner_class.return_value = mock_runner
        
        result = execute_run_guarded(self.args)
        
        self.assertEqual(result, 1)


class TestMemoryAwareRunner(unittest.TestCase):
    """Test MemoryAwareClaudeRunner integration."""
    
    @patch('claude_mpm.core.memory_aware_runner.StateManager')
    @patch('claude_mpm.core.memory_aware_runner.MemoryGuardian')
    def test_runner_initialization(self, mock_guardian_class, mock_state_class):
        """Test runner initialization with monitoring enabled."""
        from claude_mpm.core.memory_aware_runner import MemoryAwareClaudeRunner
        
        runner = MemoryAwareClaudeRunner(
            enable_monitoring=True,
            launch_method='exec'  # Should be forced to subprocess
        )
        
        self.assertTrue(runner.enable_monitoring)
        self.assertEqual(runner.launch_method, 'subprocess')
    
    @patch('claude_mpm.core.memory_aware_runner.StateManager')
    @patch('claude_mpm.core.memory_aware_runner.MemoryGuardian')
    def test_runner_fallback_without_monitoring(self, mock_guardian_class, mock_state_class):
        """Test that runner falls back to standard mode when monitoring disabled."""
        from claude_mpm.core.memory_aware_runner import MemoryAwareClaudeRunner
        
        runner = MemoryAwareClaudeRunner(enable_monitoring=False)
        
        # Mock the parent run_interactive method
        with patch.object(runner, 'run_interactive') as mock_run:
            runner.run_interactive_with_monitoring()
            mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()