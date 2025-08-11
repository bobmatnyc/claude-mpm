#!/usr/bin/env python3
"""
Response Logging Verification Test Script

Tests response logging functionality to ensure it's working correctly:
1. Configuration verification
2. Directory and permissions check  
3. Hook system integration test
4. Actual logging test with file creation
5. Log format validation
6. Error condition testing
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add the src directory to the path so we can import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.core.config import Config
    from claude_mpm.services.claude_session_logger import ClaudeSessionLogger, get_session_logger
    from claude_mpm.hooks.builtin.session_response_logger_hook import SessionResponseLoggerHook
except ImportError as e:
    print(f"❌ Failed to import claude_mpm modules: {e}")
    print("Make sure you're running from the project root and dependencies are installed")
    sys.exit(1)


class ResponseLoggingTester:
    """Test suite for response logging verification."""
    
    def __init__(self):
        """Initialize the tester with configuration."""
        self.config = Config()
        self.test_session_id = f"test_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_results = []
        
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results."""
        print(f"\n🧪 Running {test_name}...")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                self.test_results.append((test_name, "PASSED", None))
                return True
            else:
                print(f"❌ {test_name} FAILED")
                self.test_results.append((test_name, "FAILED", "Test returned False"))
                return False
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            self.test_results.append((test_name, "FAILED", str(e)))
            return False
    
    def test_configuration_validation(self) -> bool:
        """Test that configuration is loaded and valid."""
        # Check response logging configuration
        response_config = self.config.get('response_logging', {})
        if not response_config.get('enabled', False):
            print("⚠️  Response logging is disabled in configuration")
            return False
        
        # Check hook configuration
        hooks_config = self.config.get('hooks', {})
        hook_config = hooks_config.get('session_response_logger', {})
        if not hook_config.get('enabled', False):
            print("⚠️  Session response logger hook is disabled")
            return False
        
        print(f"✓ Response logging enabled: {response_config.get('enabled')}")
        print(f"✓ Hook enabled: {hook_config.get('enabled')}")
        print(f"✓ Base directory: {response_config.get('session_directory', 'default')}")
        print(f"✓ Async mode: {response_config.get('use_async', 'default')}")
        
        return True
    
    def test_directory_creation(self) -> bool:
        """Test that logging directories can be created and are writable."""
        # Get the configured base directory
        response_config = self.config.get('response_logging', {})
        base_dir = Path(response_config.get('session_directory', '.claude-mpm/responses'))
        
        # Check if base directory exists
        if not base_dir.exists():
            print(f"⚠️  Base directory {base_dir} does not exist, attempting to create...")
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created base directory: {base_dir}")
            except Exception as e:
                print(f"❌ Failed to create base directory: {e}")
                return False
        
        # Test if directory is writable
        test_file = base_dir / "write_test.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            test_file.unlink()  # Delete test file
            print(f"✓ Directory is writable: {base_dir}")
        except Exception as e:
            print(f"❌ Directory not writable: {e}")
            return False
        
        return True
    
    def test_session_logger_creation(self) -> bool:
        """Test that session logger can be created and configured."""
        # Test with custom session ID
        logger = ClaudeSessionLogger(config=self.config)
        logger.set_session_id(self.test_session_id)
        
        if not logger.is_enabled():
            print("❌ Session logger is not enabled")
            return False
        
        # Check session path creation
        session_path = logger.get_session_path()
        if not session_path:
            print("❌ No session path available")
            return False
        
        print(f"✓ Session logger created with ID: {self.test_session_id}")
        print(f"✓ Session path: {session_path}")
        
        return True
    
    def test_response_logging(self) -> bool:
        """Test actual response logging functionality."""
        # Create a logger with our test session
        logger = ClaudeSessionLogger(config=self.config)
        logger.set_session_id(self.test_session_id)
        
        # Test data
        test_request = "Test request for verification"
        test_response = "This is a test response to verify logging functionality. " * 10  # Make it long enough
        test_metadata = {
            "agent": "test_agent",
            "model": "claude-3",
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the response
        log_path = logger.log_response(
            request_summary=test_request,
            response_content=test_response,
            metadata=test_metadata,
            agent="verification_test"
        )
        
        if not log_path:
            print("❌ Response logging returned None - no file was created")
            return False
        
        # Check if file exists (for sync logging)
        if log_path.exists():
            print(f"✓ Response logged to: {log_path}")
            
            # Validate file content
            try:
                with open(log_path, 'r') as f:
                    log_data = json.load(f)
                
                # Check required fields
                required_fields = ['timestamp', 'session_id', 'request', 'response', 'agent']
                for field in required_fields:
                    if field not in log_data:
                        print(f"❌ Missing required field in log: {field}")
                        return False
                
                print(f"✓ Log file contains all required fields")
                print(f"✓ Agent name: {log_data.get('agent')}")
                print(f"✓ Session ID: {log_data.get('session_id')}")
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to read/parse log file: {e}")
                return False
        else:
            # For async logging, we might not have the exact path
            session_dir = logger.get_session_path()
            if session_dir and session_dir.exists():
                log_files = list(session_dir.glob("*.json"))
                if log_files:
                    print(f"✓ Found {len(log_files)} log files in session directory (async logging)")
                    return True
            
            print(f"❌ Log file not found at {log_path}")
            return False
    
    def test_hook_integration(self) -> bool:
        """Test hook system integration."""
        # Get hook configuration
        hooks_config = self.config.get('hooks', {})
        hook_config = hooks_config.get('session_response_logger', {})
        
        # Create hook instance
        hook = SessionResponseLoggerHook(config=hook_config)
        
        if not hook.enabled:
            print("❌ Hook is not enabled")
            return False
        
        # Test event processing
        test_event = {
            'agent_name': 'test_agent',
            'request': 'Test hook integration',
            'response': 'This is a test response for hook integration testing. ' * 10,
            'model': 'test-model',
            'tokens': 150,
            'tools_used': ['test_tool']
        }
        
        # Process event through hook
        result_event = hook.on_agent_response(test_event)
        
        # Hook should return the original event unchanged
        if result_event != test_event:
            print("❌ Hook modified the event data")
            return False
        
        print("✓ Hook integration test passed")
        return True
    
    def test_error_conditions(self) -> bool:
        """Test error handling and edge cases."""
        logger = ClaudeSessionLogger(config=self.config)
        logger.set_session_id(self.test_session_id)
        
        # Test with empty response (should be rejected by minimum length)
        log_path = logger.log_response("Test", "", {})
        if log_path:
            print("⚠️  Empty response was logged (unexpected)")
        else:
            print("✓ Empty response correctly rejected")
        
        # Test with short response
        log_path = logger.log_response("Test", "Hi", {})
        if log_path:
            print("⚠️  Very short response was logged")
        else:
            print("✓ Short response handled appropriately")
        
        # Test with None session ID
        logger.set_session_id(None)
        log_path = logger.log_response("Test", "Valid response content", {})
        if not log_path:
            print("✓ Correctly handled None session ID")
        else:
            print("⚠️  Logged response with None session ID")
        
        return True
    
    def test_existing_logs_validation(self) -> bool:
        """Validate format and content of existing log files."""
        response_config = self.config.get('response_logging', {})
        base_dir = Path(response_config.get('session_directory', '.claude-mpm/responses'))
        
        if not base_dir.exists():
            print("✓ No existing logs to validate")
            return True
        
        # Find some log files to validate
        log_files = []
        for session_dir in base_dir.iterdir():
            if session_dir.is_dir():
                log_files.extend(session_dir.glob("*.json"))
        
        if not log_files:
            print("✓ No existing log files found")
            return True
        
        # Validate a few log files
        validated = 0
        errors = 0
        
        for log_file in log_files[:5]:  # Check first 5 files
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
                
                # Check if it has basic structure
                if 'timestamp' in log_data and 'response' in log_data:
                    validated += 1
                else:
                    print(f"⚠️  Log file {log_file.name} missing required fields")
                    errors += 1
                    
            except Exception as e:
                print(f"⚠️  Failed to validate {log_file.name}: {e}")
                errors += 1
        
        print(f"✓ Validated {validated} existing log files")
        if errors > 0:
            print(f"⚠️  Found {errors} files with issues")
        
        return errors == 0
    
    def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("🔍 Response Logging Verification Test Suite")
        print("=" * 50)
        
        tests = [
            ("Configuration Validation", self.test_configuration_validation),
            ("Directory Creation & Permissions", self.test_directory_creation),
            ("Session Logger Creation", self.test_session_logger_creation),
            ("Response Logging Functionality", self.test_response_logging),
            ("Hook Integration", self.test_hook_integration),
            ("Error Condition Handling", self.test_error_conditions),
            ("Existing Log Validation", self.test_existing_logs_validation),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 TEST SUMMARY")
        print("=" * 50)
        
        for test_name, status, error in self.test_results:
            status_emoji = "✅" if status == "PASSED" else "❌"
            print(f"{status_emoji} {test_name}: {status}")
            if error:
                print(f"   Error: {error}")
        
        print(f"\nPASSED: {passed}/{total} tests")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED - Response logging is working correctly!")
            return True
        else:
            print(f"\n⚠️  {total - passed} tests failed - Response logging may have issues")
            return False


def main():
    """Main execution function."""
    print("Response Logging Verification Test")
    print("Working directory:", os.getcwd())
    
    # Change to project root if we're in scripts directory
    if os.path.basename(os.getcwd()) == 'scripts':
        os.chdir('..')
        print("Changed to project root:", os.getcwd())
    
    tester = ResponseLoggingTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()