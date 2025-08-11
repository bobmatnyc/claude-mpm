#!/usr/bin/env python3
"""
Test Script: Schema Compliance Verification

Verifies that all response logging uses standardized field names:
- agent (not agent_name)
- request (not request_summary)
- response (not response_content)
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

def test_async_logger_schema():
    """Test AsyncSessionLogger JSON output schema."""
    print("Testing AsyncSessionLogger schema compliance...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            enable_async=False,
            enable_compression=False
        )
        
        # Log multiple test entries
        test_cases = [
            ("Request 1", "Response 1", {"type": "test1"}, "agent1"),
            ("Request 2", "Response 2", {"type": "test2"}, "agent2"),
            ("Request 3", "Response 3", None, None),  # Test with no metadata/agent
        ]
        
        for req, resp, meta, agent in test_cases:
            success = logger.log_response(
                request_summary=req,
                response_content=resp,
                metadata=meta,
                agent=agent
            )
            if not success:
                print(f"  ❌ Failed to log: {req}")
                return False
        
        # Verify all JSON files
        session_dir = Path(tmpdir) / logger.session_id
        json_files = list(session_dir.glob("*.json"))
        
        if len(json_files) != len(test_cases):
            print(f"  ❌ Expected {len(test_cases)} files, found {len(json_files)}")
            return False
        
        for json_file in json_files:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check for standardized field names
            required_fields = ["timestamp", "session_id", "agent", "request", "response", "metadata"]
            for field in required_fields:
                if field not in data:
                    print(f"  ❌ Missing field '{field}' in {json_file.name}")
                    return False
            
            # Check that old field names are NOT present
            old_fields = ["agent_name", "request_summary", "response_content"]
            for field in old_fields:
                if field in data:
                    print(f"  ❌ Old field '{field}' found in {json_file.name}")
                    return False
            
            # Verify field content types
            if not isinstance(data["agent"], str):
                print(f"  ❌ 'agent' field is not a string in {json_file.name}")
                return False
            if not isinstance(data["request"], str):
                print(f"  ❌ 'request' field is not a string in {json_file.name}")
                return False
            if not isinstance(data["response"], str):
                print(f"  ❌ 'response' field is not a string in {json_file.name}")
                return False
            if not isinstance(data["metadata"], dict):
                print(f"  ❌ 'metadata' field is not a dict in {json_file.name}")
                return False
        
        print(f"  ✅ All {len(json_files)} JSON files have correct schema")
        return True

def test_claude_logger_schema():
    """Test ClaudeSessionLogger JSON output schema."""
    print("\nTesting ClaudeSessionLogger schema compliance...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ClaudeSessionLogger(
            base_dir=Path(tmpdir),
            use_async=False
        )
        
        # Log test entries
        test_cases = [
            ("Claude Request 1", "Claude Response 1", {"test": "claude1"}, "claude_agent1"),
            ("Claude Request 2", "Claude Response 2", None, "claude_agent2"),
        ]
        
        for req, resp, meta, agent in test_cases:
            path = logger.log_response(
                request_summary=req,
                response_content=resp,
                metadata=meta,
                agent=agent
            )
            if not path or not path.exists():
                print(f"  ❌ Failed to log: {req}")
                return False
        
        # Verify JSON files
        session_dir = Path(tmpdir) / logger.session_id
        json_files = sorted(session_dir.glob("*.json"))
        
        if len(json_files) != len(test_cases):
            print(f"  ❌ Expected {len(test_cases)} files, found {len(json_files)}")
            return False
        
        for i, json_file in enumerate(json_files):
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check standardized field names
            required_fields = ["timestamp", "session_id", "request", "response", "agent", "metadata"]
            for field in required_fields:
                if field not in data:
                    print(f"  ❌ Missing field '{field}' in {json_file.name}")
                    return False
            
            # Verify correct values
            req, resp, meta, agent = test_cases[i]
            if data["request"] != req:
                print(f"  ❌ Incorrect request value in {json_file.name}")
                return False
            if data["response"] != resp:
                print(f"  ❌ Incorrect response value in {json_file.name}")
                return False
            if data["agent"] != agent:
                print(f"  ❌ Incorrect agent value in {json_file.name}")
                return False
        
        print(f"  ✅ All {len(json_files)} JSON files have correct schema")
        return True

def test_schema_consistency():
    """Test that both loggers produce consistent schemas."""
    print("\nTesting schema consistency between loggers...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        async_logger = AsyncSessionLogger(
            base_dir=Path(tmpdir) / "async",
            enable_async=False
        )
        
        claude_logger = ClaudeSessionLogger(
            base_dir=Path(tmpdir) / "claude",
            use_async=False
        )
        
        # Log identical content with both
        test_request = "Consistency test request"
        test_response = "Consistency test response"
        test_metadata = {"consistency": "test", "version": 1}
        test_agent = "consistency_agent"
        
        async_logger.log_response(
            request_summary=test_request,
            response_content=test_response,
            metadata=test_metadata,
            agent=test_agent
        )
        
        claude_logger.log_response(
            request_summary=test_request,
            response_content=test_response,
            metadata=test_metadata,
            agent=test_agent
        )
        
        # Read both JSON files
        async_files = list((Path(tmpdir) / "async" / async_logger.session_id).glob("*.json"))
        claude_files = list((Path(tmpdir) / "claude" / claude_logger.session_id).glob("*.json"))
        
        if not async_files or not claude_files:
            print("  ❌ Failed to create log files")
            return False
        
        with open(async_files[0], 'r') as f:
            async_data = json.load(f)
        
        with open(claude_files[0], 'r') as f:
            claude_data = json.load(f)
        
        # Compare field names (not values since timestamps will differ)
        async_fields = set(async_data.keys())
        claude_fields = set(claude_data.keys())
        
        if async_fields != claude_fields:
            print(f"  ❌ Field mismatch: async={async_fields}, claude={claude_fields}")
            return False
        
        # Check that both have standardized fields
        standard_fields = {"timestamp", "session_id", "agent", "request", "response", "metadata"}
        if not standard_fields.issubset(async_fields):
            print(f"  ❌ AsyncLogger missing standard fields")
            return False
        
        if not standard_fields.issubset(claude_fields):
            print(f"  ❌ ClaudeLogger missing standard fields")
            return False
        
        # Verify content matches (except timestamp/session)
        if async_data["agent"] != claude_data["agent"]:
            print("  ❌ Agent field mismatch")
            return False
        
        if async_data["request"] != claude_data["request"]:
            print("  ❌ Request field mismatch")
            return False
        
        if async_data["response"] != claude_data["response"]:
            print("  ❌ Response field mismatch")
            return False
        
        print("  ✅ Both loggers produce consistent schemas")
        return True

def main():
    """Run all schema compliance tests."""
    print("=" * 60)
    print("SCHEMA COMPLIANCE TESTS")
    print("=" * 60)
    
    tests = [
        ("AsyncSessionLogger Schema", test_async_logger_schema),
        ("ClaudeSessionLogger Schema", test_claude_logger_schema),
        ("Schema Consistency", test_schema_consistency)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"  ❌ {name} ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if failed == 0:
        print("✅ ALL SCHEMA COMPLIANCE TESTS PASSED!")
        print("\nStandardized JSON Schema:")
        print("  - timestamp: ISO format timestamp")
        print("  - session_id: Session identifier")
        print("  - agent: Agent name (not 'agent_name')")
        print("  - request: Request content (not 'request_summary')")
        print("  - response: Response content (not 'response_content')")
        print("  - metadata: Additional metadata dict")
        return 0
    else:
        print(f"❌ {failed} SCHEMA TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())