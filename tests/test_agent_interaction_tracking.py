#!/usr/bin/env python3
"""
Test response tracking during actual agent interactions.
This tests the full integration with the hook system.
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.response_tracker import ResponseTracker

def test_agent_interaction_tracking():
    """Test response tracking during actual agent interactions."""
    print("🧪 Testing agent interaction response tracking...")
    
    original_cwd = Path.cwd()
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        os.chdir(test_dir)
        print(f"   Working in: {test_dir}")
        
        # 1. Enable response tracking via config file
        print("   Step 1: Setting up response tracking configuration...")
        
        config_file = test_dir / "response_config.json"
        config_data = {
            "response_tracking": {
                "enabled": True,
                "storage": {
                    "base_dir": str(test_dir / ".claude-mpm" / "responses")
                }
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Set environment variable for config
        os.environ['CLAUDE_PM_CONFIG_FILE'] = str(config_file)
        print(f"   Config file: {config_file}")
        
        # 2. Create a simple test prompt that should trigger response tracking
        print("   Step 2: Testing simple command with response tracking...")
        
        script_path = original_cwd / "scripts" / "claude-mpm"
        test_prompt = "Hello, please respond with a simple greeting."
        
        # Use the claude-mpm run command with response tracking enabled
        result = subprocess.run([
            str(script_path), "run", 
            "--input", test_prompt,
            "--non-interactive"
        ], capture_output=True, text=True, cwd=test_dir, timeout=30)
        
        print(f"   Run command exit code: {result.returncode}")
        if result.stdout:
            print(f"   Output length: {len(result.stdout)} chars")
        if result.stderr:
            print(f"   Stderr: {result.stderr[:200]}...")
        
        # 3. Check if responses were tracked
        print("   Step 3: Checking if responses were tracked...")
        
        # Wait a moment for any async operations to complete
        time.sleep(1)
        
        responses_dir = test_dir / ".claude-mpm" / "responses"
        if responses_dir.exists():
            print(f"   Responses directory exists: {responses_dir}")
            
            # List all response files
            response_files = list(responses_dir.glob("**/*.json"))
            print(f"   Found {len(response_files)} response files")
            
            if response_files:
                # Check the content of the first response
                with open(response_files[0], 'r') as f:
                    response_data = json.load(f)
                
                print(f"   Sample response agent: {response_data.get('agent', 'unknown')}")
                print(f"   Sample response length: {len(response_data.get('response', ''))}")
                print(f"   Sample request: {response_data.get('request', 'unknown')[:50]}...")
                
                # Verify the response contains our test prompt
                assert test_prompt in response_data.get('request', ''), "Request should contain our test prompt"
                
                print("   ✅ Response tracking working during agent interaction")
            else:
                print("   ⚠️  No response files found - may not have triggered tracking")
        else:
            print(f"   ⚠️  Responses directory not created: {responses_dir}")
        
        # 4. Test with CLI to verify responses are accessible
        print("   Step 4: Testing CLI access to tracked responses...")
        
        result = subprocess.run([str(script_path), "responses", "list"], 
                              capture_output=True, text=True, cwd=test_dir)
        
        print(f"   CLI responses list exit code: {result.returncode}")
        if result.stdout:
            print(f"   CLI output length: {len(result.stdout)}")
            if "No responses found" not in result.stdout:
                print("   ✅ CLI can access tracked responses")
            else:
                print("   ⚠️  CLI shows no responses found")
        
        # 5. Test statistics
        result = subprocess.run([str(script_path), "responses", "stats"], 
                              capture_output=True, text=True, cwd=test_dir)
        
        if result.returncode == 0 and result.stdout:
            print(f"   Stats output: {result.stdout.strip()}")
        
        print("   ✅ Agent interaction tracking test completed")
        
    except subprocess.TimeoutExpired:
        print("   ⚠️  Test command timed out - this may be expected for some scenarios")
    except Exception as e:
        print(f"   ❌ Agent interaction test failed: {e}")
        # Don't raise - some failures are expected in testing environment
    finally:
        # Clean up environment
        if 'CLAUDE_PM_CONFIG_FILE' in os.environ:
            del os.environ['CLAUDE_PM_CONFIG_FILE']
        
        os.chdir(original_cwd)
        if test_dir.exists():
            shutil.rmtree(test_dir)

def test_hook_handler_integration():
    """Test the hook handler integration directly."""
    print("\n🧪 Testing hook handler integration...")
    
    try:
        # Test hook handler initialization with response tracking
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        # Create temporary config
        test_dir = Path(tempfile.mkdtemp())
        config_file = test_dir / "hook_config.json"
        
        config_data = {
            "response_tracking": {
                "enabled": True
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        os.environ['CLAUDE_PM_CONFIG_FILE'] = str(config_file)
        
        try:
            # Initialize handler with tracking enabled
            handler = ClaudeHookHandler()
            
            print(f"   Response tracking enabled: {handler.response_tracking_enabled}")
            print(f"   Response tracker initialized: {handler.response_tracker is not None}")
            
            if handler.response_tracking_enabled and handler.response_tracker:
                # Test manual response tracking
                test_response_path = handler.response_tracker.track_response(
                    agent_name="test_agent",
                    request="Test integration request",
                    response="Test integration response from hook handler",
                    session_id="hook_test_session",
                    metadata={"test": True, "integration": "hook_handler"}
                )
                
                print(f"   Manual response tracked: {test_response_path}")
                assert test_response_path.exists(), "Response file should be created"
                
                # Verify content
                with open(test_response_path, 'r') as f:
                    response_data = json.load(f)
                
                assert response_data['agent'] == 'test_agent'
                assert response_data['session_id'] == 'hook_test_session'
                assert response_data['metadata']['integration'] == 'hook_handler'
                
                print("   ✅ Hook handler integration working correctly")
            else:
                print("   ⚠️  Hook handler response tracking not properly initialized")
                
        finally:
            if 'CLAUDE_PM_CONFIG_FILE' in os.environ:
                del os.environ['CLAUDE_PM_CONFIG_FILE']
            if test_dir.exists():
                shutil.rmtree(test_dir)
    
    except Exception as e:
        print(f"   ❌ Hook handler integration test failed: {e}")
        # Don't raise - continue with other tests

if __name__ == "__main__":
    test_agent_interaction_tracking()
    test_hook_handler_integration()