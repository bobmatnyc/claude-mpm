#!/usr/bin/env python3
"""
Quick verification script to test that all critical fixes are working correctly.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.async_session_logger import AsyncSessionLogger

def test_json_schema():
    """Test that JSON output uses standardized field names."""
    print("Testing JSON schema compliance...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            enable_async=False
        )
        
        # Log a test response
        success = logger.log_response(
            request_summary="Test request",
            response_content="Test response",
            metadata={"test": True},
            agent="test_agent"
        )
        
        if not success:
            print("❌ Failed to log response")
            return False
        
        # Check the JSON file
        session_dir = Path(tmpdir) / logger.session_id
        json_files = list(session_dir.glob("*.json"))
        
        if not json_files:
            print("❌ No JSON files created")
            return False
        
        # Read and verify the JSON structure
        with open(json_files[0], 'r') as f:
            data = json.load(f)
        
        # Check standardized field names
        expected_fields = ["timestamp", "session_id", "agent", "request", "response", "metadata"]
        for field in expected_fields:
            if field not in data:
                print(f"❌ Missing field: {field}")
                return False
        
        # Verify correct field names (not old names)
        if "agent_name" in data or "request_summary" in data or "response_content" in data:
            print("❌ Old field names still present in JSON")
            return False
        
        print("✅ JSON schema is correct with standardized field names")
        return True

def test_deployment_directory():
    """Test that deployment creates .claude/agents directory correctly."""
    print("\nTesting deployment directory creation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test template
        templates_dir = Path(tmpdir) / "templates"
        templates_dir.mkdir()
        
        test_template = templates_dir / "test_agent.json"
        test_template.write_text(json.dumps({
            "agent_version": "1.0.0",
            "metadata": {"description": "Test agent"},
            "capabilities": {"tools": ["Read", "Write"]},
            "instructions": "Test instructions"
        }))
        
        # Deploy to a target directory
        deployment_service = AgentDeploymentService(templates_dir=templates_dir)
        deployment_dir = Path(tmpdir) / "deployment"
        
        results = deployment_service.deploy_agents(target_dir=deployment_dir)
        
        # Check that .claude/agents was created
        expected_agents_dir = deployment_dir / ".claude" / "agents"
        if not expected_agents_dir.exists():
            print(f"❌ Expected directory not created: {expected_agents_dir}")
            return False
        
        # Check that agent file was deployed
        agent_file = expected_agents_dir / "test_agent.md"
        if not agent_file.exists():
            print(f"❌ Agent file not deployed: {agent_file}")
            return False
        
        print(f"✅ Deployment directory created correctly at {expected_agents_dir}")
        return True

def test_logger_parameters():
    """Test that logger accepts correct parameters."""
    print("\nTesting logger parameter signatures...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            enable_async=False
        )
        
        try:
            # Test correct parameter names
            success = logger.log_response(
                request_summary="Test request",
                response_content="Test response",
                metadata={"test": True},
                agent="test_agent"
            )
            
            if not success:
                print("❌ log_response returned False")
                return False
            
            print("✅ Logger accepts correct parameter names")
            return True
            
        except TypeError as e:
            print(f"❌ Parameter error: {e}")
            return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("CRITICAL FIXES VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_json_schema,
        test_deployment_directory,
        test_logger_parameters
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL CRITICAL FIXES VERIFIED!")
        return 0
    else:
        print("❌ Some fixes still need work")
        return 1

if __name__ == "__main__":
    sys.exit(main())