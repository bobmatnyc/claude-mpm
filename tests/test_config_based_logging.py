#!/usr/bin/env python3
"""
Test script to verify configuration-based response logging.

This script tests:
1. Loading configuration from .claude-mpm/configuration.yaml
2. Using configuration settings instead of environment variables
3. Backward compatibility with environment variables
4. Async and sync logging modes
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Use centralized path management
from claude_mpm.config.paths import paths
paths.ensure_in_path()

from claude_mpm.core.config import Config
from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat, get_async_logger
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger, get_session_logger


def test_config_loading():
    """Test that configuration is loaded from YAML file."""
    print("\n=== Testing Configuration Loading ===")
    
    # Load configuration
    config = Config()
    
    # Check response_logging section
    response_config = config.get('response_logging', {})
    print(f"Response logging enabled: {response_config.get('enabled', False)}")
    print(f"Use async: {response_config.get('use_async', False)}")
    print(f"Format: {response_config.get('format', 'json')}")
    print(f"Session directory: {response_config.get('session_directory', '.claude-mpm/responses')}")
    print(f"Debug sync: {response_config.get('debug_sync', False)}")
    
    assert response_config.get('enabled') == True, "Response logging should be enabled"
    assert response_config.get('use_async') == True, "Async logging should be enabled"
    assert response_config.get('format') == 'json', "Format should be json"
    
    print("✓ Configuration loaded successfully")


def test_async_logger_with_config():
    """Test AsyncSessionLogger with configuration."""
    print("\n=== Testing AsyncSessionLogger with Config ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom configuration
        config = Config()
        config.set('response_logging.session_directory', tmpdir)
        config.set('response_logging.use_async', True)
        config.set('response_logging.format', 'json')
        
        # Create logger with configuration
        logger = AsyncSessionLogger(config=config)
        
        # Verify settings
        assert str(logger.base_dir) == tmpdir, f"Base dir should be {tmpdir}"
        assert logger.log_format == LogFormat.JSON, "Format should be JSON"
        assert logger.enable_async == True, "Async should be enabled"
        
        # Test logging
        success = logger.log_response(
            request_summary="Test request",
            response_content="Test response content",
            metadata={"agent": "test", "model": "claude-3"}
        )
        
        assert success, "Logging should succeed"
        
        # Flush and shutdown
        logger.flush(timeout=2.0)
        logger.shutdown(timeout=2.0)
        
        # Check stats
        stats = logger.get_stats()
        print(f"Logger stats: {stats}")
        assert stats['logged'] > 0 or stats['queued'] > 0, "Should have logged entries"
        
        print("✓ AsyncSessionLogger works with configuration")


def test_session_logger_with_config():
    """Test ClaudeSessionLogger with configuration."""
    print("\n=== Testing ClaudeSessionLogger with Config ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom configuration
        config = Config()
        config.set('response_logging.enabled', True)
        config.set('response_logging.use_async', False)  # Use sync for testing
        
        # Create logger with configuration - explicitly pass base_dir
        logger = ClaudeSessionLogger(base_dir=tmpdir, config=config)
        
        # Verify settings - note that Path might add trailing slash or resolve symlinks
        assert Path(logger.base_dir).resolve() == Path(tmpdir).resolve(), f"Base dir should be {tmpdir}, got {logger.base_dir}"
        assert logger.use_async == False, "Async should be disabled for this test"
        
        # Test logging
        file_path = logger.log_response(
            request_summary="Test request",
            response_content="Test response content",
            metadata={"agent": "test", "model": "claude-3"}
        )
        
        if file_path:
            assert file_path.exists(), "Log file should exist"
            print(f"✓ Created log file: {file_path}")
        
        print("✓ ClaudeSessionLogger works with configuration")


def test_backward_compatibility():
    """Test backward compatibility with environment variables."""
    print("\n=== Testing Backward Compatibility ===")
    
    # Save original environment
    original_env = os.environ.copy()
    
    try:
        # Set deprecated environment variables
        os.environ['CLAUDE_USE_ASYNC_LOG'] = 'false'
        os.environ['CLAUDE_LOG_FORMAT'] = 'syslog'
        
        # Create logger (should use environment variables)
        logger = get_async_logger()
        
        # Check that environment variables are respected
        assert logger.enable_async == False, "Should respect CLAUDE_USE_ASYNC_LOG"
        assert logger.log_format == LogFormat.SYSLOG, "Should respect CLAUDE_LOG_FORMAT"
        
        print("✓ Backward compatibility with environment variables works")
        
        # Clean up singleton
        import claude_mpm.services.async_session_logger as async_module
        async_module._logger_instance = None
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_config_override():
    """Test that configuration can override defaults."""
    print("\n=== Testing Configuration Override ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test configuration file
        test_config_path = Path(tmpdir) / "test_config.yaml"
        
        config_content = """
response_logging:
  enabled: true
  use_async: false
  format: journald
  session_directory: /tmp/test_responses
  debug_sync: true
  max_queue_size: 5000
  enable_compression: true
"""
        
        test_config_path.write_text(config_content)
        
        # Load configuration from test file
        config = Config(config_file=test_config_path)
        
        # Verify overrides
        response_config = config.get('response_logging', {})
        assert response_config.get('use_async') == False, "Should override use_async"
        assert response_config.get('format') == 'journald', "Should override format"
        assert response_config.get('debug_sync') == True, "Should override debug_sync"
        assert response_config.get('max_queue_size') == 5000, "Should override max_queue_size"
        assert response_config.get('enable_compression') == True, "Should override compression"
        
        print("✓ Configuration overrides work correctly")


def test_default_configuration():
    """Test that default configuration is applied when no config file exists."""
    print("\n=== Testing Default Configuration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory to avoid loading project config
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create config without file (should use defaults)
            config = Config()
            
            # Check that defaults are applied
            response_config = config.get('response_logging', {})
            
            # The defaults from Config class don't include response_logging by default
            # So it should be an empty dict
            if not response_config:
                print("✓ No response_logging config found (expected for defaults)")
            else:
                print(f"Response logging config: {response_config}")
            
            # The logger should still work with defaults
            logger = AsyncSessionLogger(config=config)
            assert logger.base_dir.name == "responses", "Should use default directory"
            assert logger.log_format == LogFormat.JSON, "Should use default format"
            
            print("✓ Default configuration works correctly")
            
        finally:
            os.chdir(original_cwd)


def main():
    """Run all tests."""
    print("Testing Configuration-based Response Logging")
    print("=" * 50)
    
    try:
        test_config_loading()
        test_async_logger_with_config()
        test_session_logger_with_config()
        test_backward_compatibility()
        test_config_override()
        test_default_configuration()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()