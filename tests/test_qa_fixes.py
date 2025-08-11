#!/usr/bin/env python3
"""
Test script to verify the QA fixes are working correctly.

This script tests:
1. AsyncSessionLogger API parameter compatibility
2. Deployment directory creation
3. Discovery method availability
4. Schema field name standardization
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger
from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.services.agents.registry import DeployedAgentDiscovery


def test_async_logger_agent_parameter():
    """Test that AsyncSessionLogger accepts agent parameter."""
    print("\n1. Testing AsyncSessionLogger agent parameter...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            enable_async=False  # Sync mode for immediate testing
        )
        
        # Test with agent parameter
        success = logger.log_response(
            request_summary="Test request",
            response_content="Test response",
            metadata={"test": "data"},
            agent="test_agent"
        )
        
        assert success, "Failed to log with agent parameter"
        
        # Check the logged file
        session_dir = Path(tmpdir) / logger.session_id
        json_files = list(session_dir.glob("*.json"))
        
        if json_files:
            with open(json_files[0], 'r') as f:
                data = json.load(f)
                
                # Verify standardized field names
                assert 'request' in data, "Missing 'request' field"
                assert 'response' in data, "Missing 'response' field"
                assert 'agent' in data, "Missing 'agent' field"
                assert data['agent'] == 'test_agent', f"Agent name mismatch: {data['agent']}"
                
                print("✓ AsyncSessionLogger agent parameter works correctly")
                print(f"  - Agent field: {data['agent']}")
                print(f"  - Request field: {data['request'][:50]}...")
                print(f"  - Response field: {data['response'][:50]}...")
        else:
            print("✗ No JSON files created")
            return False
    
    return True


def test_claude_logger_agent_parameter():
    """Test that ClaudeSessionLogger accepts agent parameter."""
    print("\n2. Testing ClaudeSessionLogger agent parameter...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ClaudeSessionLogger(
            base_dir=Path(tmpdir),
            use_async=False  # Use sync mode
        )
        
        # Test with agent parameter
        file_path = logger.log_response(
            request_summary="Test request",
            response_content="Test response",
            metadata={"test": "data"},
            agent="qa_agent"
        )
        
        assert file_path, "Failed to log with agent parameter"
        
        # Check the logged file
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                # Verify standardized field names
                assert 'request' in data, "Missing 'request' field"
                assert 'response' in data, "Missing 'response' field"
                assert 'agent' in data, "Missing 'agent' field"
                assert data['agent'] == 'qa_agent', f"Agent name mismatch: {data['agent']}"
                
                print("✓ ClaudeSessionLogger agent parameter works correctly")
                print(f"  - Agent field: {data['agent']}")
                print(f"  - Request field: {data['request'][:50]}...")
                print(f"  - Response field: {data['response'][:50]}...")
        else:
            print("✗ File not created")
            return False
    
    return True


def test_deployment_directory_creation():
    """Test that deployment creates the .claude/agents directory."""
    print("\n3. Testing deployment directory creation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / ".claude" / "agents"
        
        # Ensure directory doesn't exist initially
        assert not target_dir.exists(), "Directory already exists"
        
        # Create deployment service
        service = AgentDeploymentService()
        
        # Deploy agents
        results = service.deploy_agents(target_dir=target_dir)
        
        # Check that directory was created
        assert target_dir.exists(), "Directory not created"
        assert target_dir.is_dir(), "Path is not a directory"
        
        print("✓ Deployment directory created successfully")
        print(f"  - Directory: {target_dir}")
        print(f"  - Deployed: {len(results['deployed'])} agents")
        print(f"  - Errors: {len(results['errors'])}")
    
    return True


def test_discovery_precedence_method():
    """Test that DeployedAgentDiscovery has get_precedence_order method."""
    print("\n4. Testing DeployedAgentDiscovery.get_precedence_order()...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        discovery = DeployedAgentDiscovery(project_root=Path(tmpdir))
        
        # Check method exists
        assert hasattr(discovery, 'get_precedence_order'), "Method not found"
        
        # Call the method
        precedence = discovery.get_precedence_order()
        
        # Verify result
        assert isinstance(precedence, list), "Method should return a list"
        assert precedence == ['project', 'user', 'system'], f"Unexpected precedence: {precedence}"
        
        print("✓ get_precedence_order() method works correctly")
        print(f"  - Precedence order: {precedence}")
    
    return True


def test_schema_standardization():
    """Test that all loggers use standardized field names."""
    print("\n5. Testing schema field name standardization...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test AsyncSessionLogger
        async_logger = AsyncSessionLogger(
            base_dir=Path(tmpdir) / "async",
            enable_async=False
        )
        
        async_logger.log_response(
            request_summary="Async test request",
            response_content="Async test response",
            metadata={"type": "async"},
            agent="async_agent"
        )
        
        # Check async logger output
        async_dir = Path(tmpdir) / "async" / async_logger.session_id
        async_files = list(async_dir.glob("*.json"))
        
        if async_files:
            with open(async_files[0], 'r') as f:
                async_data = json.load(f)
                assert 'request' in async_data, "Async: Missing 'request'"
                assert 'response' in async_data, "Async: Missing 'response'"
                assert 'agent' in async_data, "Async: Missing 'agent'"
                print("✓ AsyncSessionLogger uses standardized fields")
        
        # Test ClaudeSessionLogger
        claude_logger = ClaudeSessionLogger(
            base_dir=Path(tmpdir) / "claude",
            use_async=False
        )
        
        claude_path = claude_logger.log_response(
            request_summary="Claude test request",
            response_content="Claude test response",
            metadata={"type": "claude"},
            agent="claude_agent"
        )
        
        if claude_path and claude_path.exists():
            with open(claude_path, 'r') as f:
                claude_data = json.load(f)
                assert 'request' in claude_data, "Claude: Missing 'request'"
                assert 'response' in claude_data, "Claude: Missing 'response'"
                assert 'agent' in claude_data, "Claude: Missing 'agent'"
                print("✓ ClaudeSessionLogger uses standardized fields")
        
        # Compare field names
        if async_files and claude_path:
            async_fields = set(async_data.keys())
            claude_fields = set(claude_data.keys())
            
            common_fields = {'request', 'response', 'agent', 'timestamp', 'session_id', 'metadata'}
            
            for field in common_fields:
                if field in async_fields and field in claude_fields:
                    print(f"  ✓ Both have '{field}' field")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("QA FIX VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        ("AsyncSessionLogger agent parameter", test_async_logger_agent_parameter),
        ("ClaudeSessionLogger agent parameter", test_claude_logger_agent_parameter),
        ("Deployment directory creation", test_deployment_directory_creation),
        ("Discovery precedence method", test_discovery_precedence_method),
        ("Schema standardization", test_schema_standardization)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ {name} failed with error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL FIXES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n❌ SOME FIXES STILL NEED WORK")
        return 1


if __name__ == "__main__":
    sys.exit(main())