"""Tests for the StartupCheckerService.

Tests configuration validation, memory checking, environment validation,
and warning aggregation functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.services.cli.startup_checker import (
    IStartupChecker,
    StartupCheckerService,
    StartupWarning,
)


class MockConfigService:
    """Mock configuration service for testing."""
    
    def __init__(self, config_data=None):
        self.config_data = config_data or {}
        self.config_file = None
    
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        """Set configuration value."""
        self.config_data[key] = value


class TestStartupCheckerService:
    """Test suite for StartupCheckerService."""
    
    def test_interface_compliance(self):
        """Test that service implements IStartupChecker interface."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        assert isinstance(service, IStartupChecker)
    
    def test_check_configuration_with_response_logging(self):
        """Test configuration check with response logging enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {
                "response_logging": {
                    "enabled": True,
                    "directory": temp_dir
                }
            }
            config_service = MockConfigService(config_data)
            service = StartupCheckerService(config_service)
            
            warnings = service.check_configuration()
            assert len(warnings) == 0  # No warnings for valid directory
    
    def test_check_configuration_missing_log_directory(self):
        """Test configuration check with missing log directory."""
        config_data = {
            "response_logging": {
                "enabled": True,
                "directory": "/nonexistent/directory"
            }
        }
        config_service = MockConfigService(config_data)
        service = StartupCheckerService(config_service)
        
        warnings = service.check_configuration()
        assert len(warnings) > 0
        assert any(w.category == 'config' and 'does not exist' in w.message for w in warnings)
    
    def test_check_configuration_low_memory_threshold(self):
        """Test configuration check with low memory cleanup threshold."""
        config_data = {
            "memory_management": {
                "auto_cleanup": True,
                "cleanup_threshold_mb": 25
            }
        }
        config_service = MockConfigService(config_data)
        service = StartupCheckerService(config_service)
        
        warnings = service.check_configuration()
        assert len(warnings) > 0
        assert any(w.category == 'config' and 'threshold very low' in w.message for w in warnings)
    
    def test_check_configuration_deprecated_keys(self):
        """Test detection of deprecated configuration keys."""
        config_data = {
            "legacy_mode": True,
            "old_agent_format": "v1"
        }
        config_service = MockConfigService(config_data)
        service = StartupCheckerService(config_service)
        
        warnings = service.check_configuration()
        assert len(warnings) >= 2
        deprecated_warnings = [w for w in warnings if 'Deprecated' in w.message]
        assert len(deprecated_warnings) == 2
    
    def test_check_memory_no_resume(self):
        """Test memory check when resume is not enabled."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        warning = service.check_memory(resume_enabled=False)
        assert warning is None
    
    def test_check_memory_with_large_file(self):
        """Test memory check with large .claude.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a large fake .claude.json file
            claude_json = Path(temp_dir) / ".claude.json"
            claude_json.write_text("x" * (600 * 1024))  # 600KB
            
            config_service = MockConfigService()
            service = StartupCheckerService(config_service)
            
            # Mock cwd to return our temp directory
            with patch('claude_mpm.services.cli.startup_checker.Path.cwd', return_value=Path(temp_dir)):
                warning = service.check_memory(resume_enabled=True)
                assert warning is not None
                assert warning.category == 'memory'
                assert 'Large .claude.json' in warning.message
                assert 'cleanup-memory' in warning.suggestion
    
    def test_check_memory_with_small_file(self):
        """Test memory check with small .claude.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a small .claude.json file
            claude_json = Path(temp_dir) / ".claude.json"
            claude_json.write_text("small content")
            
            config_service = MockConfigService()
            service = StartupCheckerService(config_service)
            
            with patch('claude_mpm.services.cli.startup_checker.Path.cwd', return_value=Path(temp_dir)):
                warning = service.check_memory(resume_enabled=True)
                assert warning is None
    
    def test_check_memory_no_file(self):
        """Test memory check when .claude.json doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_service = MockConfigService()
            service = StartupCheckerService(config_service)
            
            with patch('claude_mpm.services.cli.startup_checker.Path.cwd', return_value=Path(temp_dir)):
                warning = service.check_memory(resume_enabled=True)
                assert warning is None
    
    def test_check_environment_python_version(self):
        """Test environment check for Python version."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        # Create a mock version_info object that has the needed attributes
        mock_version = Mock()
        mock_version.major = 3
        mock_version.minor = 7
        # Make it comparable with tuples
        mock_version.__lt__ = lambda self, other: (3, 7) < other if isinstance(other, tuple) else False
        
        with patch('sys.version_info', mock_version):
            warnings = service.check_environment()
            assert any(w.category == 'environment' and 'Python 3.7' in w.message for w in warnings)
    
    def test_check_environment_claude_directory(self):
        """Test environment check for .claude directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file where .claude directory should be
            claude_path = Path(temp_dir) / ".claude"
            claude_path.write_text("not a directory")
            
            config_service = MockConfigService()
            service = StartupCheckerService(config_service)
            
            with patch('claude_mpm.services.cli.startup_checker.Path.cwd', return_value=Path(temp_dir)):
                warnings = service.check_environment()
                assert any(w.category == 'environment' and 'not a directory' in w.message for w in warnings)
    
    def test_get_startup_warnings_aggregation(self):
        """Test that get_startup_warnings aggregates all warning types."""
        config_data = {
            "response_logging": {
                "enabled": True,
                "directory": "/nonexistent"
            },
            "legacy_mode": True
        }
        config_service = MockConfigService(config_data)
        service = StartupCheckerService(config_service)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create large .claude.json
            claude_json = Path(temp_dir) / ".claude.json"
            claude_json.write_text("x" * (600 * 1024))
            
            with patch('claude_mpm.services.cli.startup_checker.Path.cwd', return_value=Path(temp_dir)):
                warnings = service.get_startup_warnings(resume_enabled=True)
                
                # Should have warnings from all categories
                categories = {w.category for w in warnings}
                assert 'config' in categories
                assert 'memory' in categories
    
    def test_display_warnings_formatting(self, capsys):
        """Test warning display formatting."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        warnings = [
            StartupWarning('config', 'Error message', 'Fix this', 'error'),
            StartupWarning('memory', 'Warning message', 'Consider this', 'warning'),
            StartupWarning('environment', 'Info message', None, 'info'),
        ]
        
        service.display_warnings(warnings)
        captured = capsys.readouterr()
        
        assert '❌ Error message' in captured.out
        assert '⚠️  Warning message' in captured.out
        assert 'ℹ️  Info message' in captured.out
        assert '💡 Consider this' in captured.out
    
    def test_display_warnings_empty_list(self, capsys):
        """Test display_warnings with empty list."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        service.display_warnings([])
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_format_file_size(self):
        """Test file size formatting."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        assert service._format_file_size(500) == "500 B"
        assert service._format_file_size(1536) == "1.5 KB"
        assert service._format_file_size(1024 * 1024 * 2.5) == "2.5 MB"
    
    def test_check_configuration_handles_exceptions(self):
        """Test that configuration check handles exceptions gracefully."""
        config_service = Mock()
        config_service.get.side_effect = Exception("Config error")
        
        service = StartupCheckerService(config_service)
        warnings = service.check_configuration()
        
        # Should return a warning about the failure, not raise
        assert len(warnings) > 0
        assert any('Configuration check failed' in w.message for w in warnings)
    
    def test_check_memory_handles_exceptions(self):
        """Test that memory check handles exceptions gracefully."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        with patch('claude_mpm.services.cli.startup_checker.Path.cwd', side_effect=Exception("Path error")):
            warning = service.check_memory(resume_enabled=True)
            assert warning is None  # Should return None on error
    
    def test_check_environment_handles_exceptions(self):
        """Test that environment check handles exceptions gracefully."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        with patch('sys.version_info', side_effect=Exception("Version error")):
            warnings = service.check_environment()
            # Should handle the error and return some warnings
            assert any('Environment check failed' in w.message for w in warnings)
    
    def test_check_config_file_access(self):
        """Test configuration file access check."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            config_path = tmp_file.name
            tmp_file.write(b"test config")
        
        try:
            # Make file unreadable
            os.chmod(config_path, 0o000)
            
            config_service = MockConfigService()
            config_service.config_file = config_path
            service = StartupCheckerService(config_service)
            
            warnings = service._check_config_file_access()
            assert any('not readable' in w.message for w in warnings)
        finally:
            # Cleanup
            os.chmod(config_path, 0o644)
            os.unlink(config_path)
    
    def test_warning_severity_ordering(self):
        """Test that warnings are displayed in correct severity order."""
        config_service = MockConfigService()
        service = StartupCheckerService(config_service)
        
        warnings = [
            StartupWarning('env', 'Info 1', None, 'info'),
            StartupWarning('config', 'Error 1', None, 'error'),
            StartupWarning('mem', 'Warning 1', None, 'warning'),
            StartupWarning('env', 'Info 2', None, 'info'),
            StartupWarning('config', 'Error 2', None, 'error'),
        ]
        
        # Test display order by capturing output
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            service.display_warnings(warnings)
            output = captured_output.getvalue()
            
            # Find positions of each severity marker
            error_pos = output.find('❌')
            warning_pos = output.find('⚠️')
            info_pos = output.find('ℹ️')
            
            # Errors should come first, then warnings, then info
            assert error_pos < warning_pos < info_pos
        finally:
            sys.stdout = sys.__stdout__