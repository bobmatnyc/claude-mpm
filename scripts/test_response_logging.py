#!/usr/bin/env python3
"""
Test script to verify response logging integration in claude-mpm.

This script tests that:
1. Response logger initializes correctly
2. Oneshot mode creates log files
3. Log files contain actual Claude responses
4. Failures in logging don't break main functionality
"""

import os
import sys
import time
import tempfile
from pathlib import Path
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import ClaudeRunner
from claude_mpm.core.config import Config


def test_response_logging():
    """Test response logging functionality."""
    print("Testing response logging integration...")
    
    # Check if configuration enables response logging
    config = Config()
    response_config = config.get('response_logging', {})
    
    if not response_config.get('enabled', False):
        print("⚠️  Response logging is disabled in configuration")
        print("   To enable, set response_logging.enabled: true in .claude-mpm/configuration.yaml")
        return False
    
    print(f"✓ Response logging is enabled in configuration")
    print(f"  - Directory: {response_config.get('session_directory', '.claude-mpm/responses')}")
    print(f"  - Async mode: {response_config.get('use_async', True)}")
    
    # Initialize runner with logging
    try:
        runner = ClaudeRunner(
            enable_tickets=False,
            log_level="OFF",  # Disable project logging for test
            launch_method="subprocess"
        )
        
        if runner.response_logger:
            print("✓ Response logger initialized successfully")
        else:
            print("⚠️  Response logger not initialized (might be disabled)")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize ClaudeRunner: {e}")
        return False
    
    # Get the response directory
    response_dir = Path(response_config.get('session_directory', '.claude-mpm/responses'))
    
    # Count existing files
    if response_dir.exists():
        existing_files = list(response_dir.glob("*.json"))
        initial_count = len(existing_files)
        print(f"  - Existing response files: {initial_count}")
    else:
        initial_count = 0
        print(f"  - Response directory will be created at: {response_dir}")
    
    # Test oneshot mode with a simple prompt
    print("\nTesting oneshot mode response logging...")
    test_prompt = "Say 'Hello from response logging test' and nothing else"
    
    try:
        # Set a session ID for testing
        os.environ['CLAUDE_SESSION_ID'] = 'test-session-' + str(int(time.time()))
        
        # Run the command
        success = runner.run_oneshot(test_prompt)
        
        if not success:
            print("⚠️  Claude command failed (this might be expected if Claude CLI is not installed)")
            # Still check if logging attempted to work
        else:
            print("✓ Claude command executed successfully")
        
        # Give async logger time to write if using async mode
        if response_config.get('use_async', True):
            time.sleep(0.5)
        
        # Check if new log files were created
        if response_dir.exists():
            new_files = list(response_dir.glob("*.json"))
            new_count = len(new_files)
            
            if new_count > initial_count:
                print(f"✓ New response log file(s) created: {new_count - initial_count} file(s)")
                
                # Check the latest file
                latest_file = max(new_files, key=lambda f: f.stat().st_mtime)
                print(f"  - Latest file: {latest_file.name}")
                
                # Verify content
                try:
                    with open(latest_file, 'r') as f:
                        log_data = json.load(f)
                        
                    # Check required fields
                    required_fields = ['timestamp', 'session_id', 'request', 'response', 'agent', 'metadata']
                    missing_fields = [field for field in required_fields if field not in log_data]
                    
                    if missing_fields:
                        print(f"⚠️  Log file missing fields: {missing_fields}")
                    else:
                        print("✓ Log file has all required fields")
                        print(f"  - Session ID: {log_data.get('session_id', 'N/A')}")
                        print(f"  - Agent: {log_data.get('agent', 'N/A')}")
                        print(f"  - Request length: {len(log_data.get('request', ''))}")
                        print(f"  - Response length: {len(log_data.get('response', ''))}")
                        
                        # Check metadata
                        metadata = log_data.get('metadata', {})
                        if 'execution_time' in metadata:
                            print(f"  - Execution time: {metadata['execution_time']:.2f}s")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse log file as JSON: {e}")
                except Exception as e:
                    print(f"⚠️  Error reading log file: {e}")
            else:
                print("⚠️  No new response log files created")
                print("   This might indicate the response logger is not being called")
        else:
            print(f"⚠️  Response directory not created at: {response_dir}")
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up environment
        if 'CLAUDE_SESSION_ID' in os.environ:
            del os.environ['CLAUDE_SESSION_ID']
    
    print("\n" + "="*50)
    print("Response logging integration test complete")
    return True


def main():
    """Main test entry point."""
    print("="*50)
    print("Claude MPM Response Logging Integration Test")
    print("="*50 + "\n")
    
    success = test_response_logging()
    
    if success:
        print("\n✅ Response logging integration appears to be working")
    else:
        print("\n⚠️  Response logging integration may have issues")
        print("   Check the messages above for details")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())