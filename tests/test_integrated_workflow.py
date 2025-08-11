#!/usr/bin/env python3
"""
Test integrated workflow for response logging including CLI commands.
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.response_tracker import ResponseTracker

def test_integrated_workflow():
    """Test the complete integrated workflow for response logging."""
    print("🧪 Testing integrated response logging workflow...")
    
    # Set up temporary working directory
    original_cwd = Path.cwd()
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        os.chdir(test_dir)
        print(f"   Working in: {test_dir}")
        
        # 1. Create some test responses using the ResponseTracker directly
        print("   Step 1: Creating test response data...")
        responses_dir = test_dir / ".claude-mpm" / "responses"
        tracker = ResponseTracker(base_dir=responses_dir)
        
        # Create varied test data
        test_scenarios = [
            ("session_2024_1", "engineer", "Fix the authentication bug", 
             "Fixed authentication timeout issue in login.py by increasing session timeout from 30 to 300 seconds."),
            ("session_2024_1", "qa", "Test the auth fix", 
             "Tested authentication fix:\n- ✅ Login works correctly\n- ✅ Session persistence improved\n- ✅ No regression in logout\nReady for deployment."),
            ("session_2024_2", "engineer", "Implement user dashboard", 
             "Created new user dashboard with:\n- User profile section\n- Recent activity feed\n- Settings panel\n- Responsive design for mobile"),
            ("session_2024_2", "security", "Security review of dashboard", 
             "Security review completed:\n- ✅ XSS protection implemented\n- ✅ CSRF tokens in place\n- ✅ Input sanitization working\n- ⚠️  Consider rate limiting for API calls"),
            ("session_2024_3", "research", "Analyze user feedback", 
             "User feedback analysis:\n- 85% satisfaction rate\n- Top request: Dark mode (45 votes)\n- Performance concerns in mobile (23 reports)\n- Feature request: Export functionality (31 votes)")
        ]
        
        for session_id, agent, request, response in test_scenarios:
            tracker.track_response(
                agent_name=agent,
                request=request,
                response=response,
                session_id=session_id,
                metadata={
                    "tokens": len(response) // 4,  # Rough token estimate
                    "duration": 2.5 + len(response) * 0.01,  # Simulate processing time
                    "model": "claude-sonnet-4",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        print(f"   Created {len(test_scenarios)} responses across 3 sessions")
        
        # 2. Test CLI commands using the actual claude-mpm script
        script_path = original_cwd / "scripts" / "claude-mpm"
        print(f"   Step 2: Testing CLI commands with {script_path}")
        
        # Test listing all responses
        print("   Testing: claude-mpm responses list")
        result = subprocess.run([str(script_path), "responses", "list"], 
                              capture_output=True, text=True, cwd=test_dir)
        print(f"   Exit code: {result.returncode}")
        if result.stdout:
            lines = result.stdout.split('\n')
            print(f"   Output lines: {len([l for l in lines if l.strip()])}")
            # Check for key indicators
            assert any("engineer" in line.lower() for line in lines), "Should contain engineer responses"
            assert any("session_2024" in line for line in lines), "Should contain session info"
        
        # Test filtering by agent
        print("   Testing: claude-mpm responses list --agent engineer")
        result = subprocess.run([str(script_path), "responses", "list", "--agent", "engineer"], 
                              capture_output=True, text=True, cwd=test_dir)
        print(f"   Engineer filter exit code: {result.returncode}")
        
        # Test filtering by session
        print("   Testing: claude-mpm responses list --session session_2024_1")
        result = subprocess.run([str(script_path), "responses", "list", "--session", "session_2024_1"], 
                              capture_output=True, text=True, cwd=test_dir)
        print(f"   Session filter exit code: {result.returncode}")
        
        # Test statistics
        print("   Testing: claude-mpm responses stats")
        result = subprocess.run([str(script_path), "responses", "stats"], 
                              capture_output=True, text=True, cwd=test_dir)
        print(f"   Stats exit code: {result.returncode}")
        if result.stdout:
            assert "Total Sessions: 3" in result.stdout, f"Expected 3 sessions, got: {result.stdout}"
            assert "Total Responses: 5" in result.stdout, f"Expected 5 responses, got: {result.stdout}"
        
        # 3. Verify response tracking configuration
        print("   Step 3: Testing configuration scenarios...")
        
        # Test with tracking disabled (default)
        print("   Testing with default config (tracking disabled)")
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        handler = ClaudeHookHandler()
        assert not handler.response_tracking_enabled, "Should be disabled by default"
        
        # Test with tracking enabled via config file
        print("   Testing with config file (tracking enabled)")
        config_file = test_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"response_tracking": {"enabled": True}}, f)
        
        os.environ['CLAUDE_PM_CONFIG_FILE'] = str(config_file)
        try:
            handler_enabled = ClaudeHookHandler()
            assert handler_enabled.response_tracking_enabled, "Should be enabled via config"
            assert handler_enabled.response_tracker is not None, "Tracker should be initialized"
        finally:
            if 'CLAUDE_PM_CONFIG_FILE' in os.environ:
                del os.environ['CLAUDE_PM_CONFIG_FILE']
        
        # 4. Test edge cases
        print("   Step 4: Testing edge cases...")
        
        # Test with no responses directory
        empty_dir = test_dir / "empty_test"
        empty_dir.mkdir()
        os.chdir(empty_dir)
        
        result = subprocess.run([str(script_path), "responses", "list"], 
                              capture_output=True, text=True, cwd=empty_dir)
        print(f"   Empty directory test exit code: {result.returncode}")
        assert "No responses found" in result.stdout, "Should handle empty directory gracefully"
        
        # Return to test directory
        os.chdir(test_dir)
        
        # Test clearing responses (but don't actually clear for final verification)
        print("   Testing: claude-mpm responses clear --session session_2024_3 --confirm")
        result = subprocess.run([str(script_path), "responses", "clear", "--session", "session_2024_3", "--confirm"], 
                              capture_output=True, text=True, cwd=test_dir)
        print(f"   Clear session exit code: {result.returncode}")
        
        # Verify session was cleared
        result = subprocess.run([str(script_path), "responses", "list", "--session", "session_2024_3"], 
                              capture_output=True, text=True, cwd=test_dir)
        assert "No responses found" in result.stdout, "Session 3 should be cleared"
        
        # 5. Final verification
        print("   Step 5: Final verification...")
        result = subprocess.run([str(script_path), "responses", "stats"], 
                              capture_output=True, text=True, cwd=test_dir)
        if result.stdout:
            # Should now have 2 sessions and 4 responses
            assert "Total Sessions: 2" in result.stdout, f"Expected 2 sessions after clear, got: {result.stdout}"
            assert "Total Responses: 4" in result.stdout, f"Expected 4 responses after clear, got: {result.stdout}"
        
        print("   ✅ Integrated workflow test completed successfully!")
        
    except Exception as e:
        print(f"   ❌ Integrated workflow test failed: {e}")
        raise
    finally:
        os.chdir(original_cwd)
        if test_dir.exists():
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_integrated_workflow()