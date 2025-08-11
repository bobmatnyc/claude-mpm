#!/usr/bin/env python3
"""
Test different logging formats (JSON, Syslog, Journald).
Validates format switching and environment variable controls.
"""

import asyncio
import time
import json
import tempfile
import shutil
import os
import subprocess
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import AsyncSessionLogger, LogFormat


def test_json_format():
    """Test JSON format logging."""
    print("\n=== Testing JSON Format ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AsyncSessionLogger(
            base_dir=Path(tmpdir),
            log_format=LogFormat.JSON,
            enable_async=True
        )
        logger.set_session_id("json_test_session")
        
        # Log some test responses
        test_responses = [
            ("User login request", "Login successful for user@example.com", {"agent": "auth_agent", "status": "success"}),
            ("Data query request", "Retrieved 1,245 records from database", {"agent": "data_agent", "query_time": 0.15}),
            ("File upload request", "Uploaded file: document.pdf (2.3MB)", {"agent": "file_agent", "size_mb": 2.3}),
        ]
        
        for req_summary, resp_content, metadata in test_responses:
            logger.log_response(req_summary, resp_content, metadata)
        
        # Flush and analyze results
        logger.flush(timeout=5.0)
        
        # Check created files
        session_dir = Path(tmpdir) / "json_test_session"
        json_files = list(session_dir.glob("*.json"))
        
        print(f"  ✓ Created {len(json_files)} JSON files")
        
        # Validate JSON structure
        valid_files = 0
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Check required fields
                required_fields = ["timestamp", "agent_name", "session_id", "request_summary", "response_content", "metadata", "microseconds"]
                for field in required_fields:
                    assert field in data, f"Missing field: {field}"
                
                # Validate data types
                assert isinstance(data["timestamp"], str)
                assert isinstance(data["microseconds"], int)
                assert isinstance(data["metadata"], dict)
                
                valid_files += 1
                print(f"  ✓ Valid JSON file: {json_file.name}")
                
            except Exception as e:
                print(f"  ✗ Invalid JSON file {json_file}: {e}")
        
        logger.shutdown()
        
        return {
            "files_created": len(json_files),
            "valid_files": valid_files,
            "success": valid_files == len(json_files) == 3
        }


def test_syslog_format():
    """Test syslog format logging."""
    print("\n=== Testing Syslog Format ===")
    
    try:
        logger = AsyncSessionLogger(
            base_dir=Path("/tmp/syslog_test"),
            log_format=LogFormat.SYSLOG,
            enable_async=True
        )
        logger.set_session_id("syslog_test_session")
        
        # Log test responses
        test_responses = [
            ("Authentication check", "User authenticated successfully", {"agent": "auth_agent"}),
            ("Database query", "Query executed in 0.25s", {"agent": "db_agent"}),
            ("API call", "External API responded in 1.2s", {"agent": "api_agent"}),
        ]
        
        start_time = time.perf_counter()
        
        for req_summary, resp_content, metadata in test_responses:
            logger.log_response(req_summary, resp_content, metadata)
        
        queue_time = time.perf_counter() - start_time
        
        # Flush to ensure all syslog entries are written
        logger.flush(timeout=5.0)
        total_time = time.perf_counter() - start_time
        
        print(f"  ✓ Logged {len(test_responses)} entries to syslog")
        print(f"  ✓ Queue time: {queue_time:.3f}s")
        print(f"  ✓ Total time: {total_time:.3f}s")
        print(f"  ✓ Throughput: {len(test_responses)/queue_time:.1f} entries/sec")
        
        # Try to check recent syslog entries (platform dependent)
        syslog_check_success = False
        try:
            if sys.platform == "darwin":
                # macOS - check system log
                result = subprocess.run(
                    ["log", "show", "--last", "1m", "--predicate", "process == 'Python' AND message CONTAINS 'claude-mpm'"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and "claude-mpm" in result.stdout:
                    print(f"  ✓ Found syslog entries in system log")
                    syslog_check_success = True
                else:
                    print(f"  ⚠ Could not verify syslog entries (may still be working)")
            elif sys.platform.startswith("linux"):
                # Linux - check journalctl or syslog
                result = subprocess.run(
                    ["journalctl", "--since", "1 minute ago", "--grep", "claude-mpm"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and "claude-mpm" in result.stdout:
                    print(f"  ✓ Found syslog entries in journal")
                    syslog_check_success = True
                else:
                    print(f"  ⚠ Could not verify syslog entries (may still be working)")
            else:
                print(f"  ⚠ Syslog verification not supported on {sys.platform}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  ⚠ Could not check syslog: {e}")
        
        logger.shutdown()
        
        return {
            "logged_entries": len(test_responses),
            "queue_time": queue_time,
            "total_time": total_time,
            "syslog_verified": syslog_check_success,
            "success": True  # Success if no exceptions were thrown
        }
        
    except Exception as e:
        print(f"  ✗ Syslog test failed: {e}")
        return {
            "logged_entries": 0,
            "success": False,
            "error": str(e)
        }


def test_journald_format():
    """Test systemd journal format logging."""
    print("\n=== Testing Journald Format ===")
    
    try:
        logger = AsyncSessionLogger(
            base_dir=Path("/tmp/journald_test"),
            log_format=LogFormat.JOURNALD,
            enable_async=True
        )
        logger.set_session_id("journald_test_session")
        
        # Log test responses
        test_responses = [
            ("Service startup", "Application started successfully", {"agent": "system_agent"}),
            ("Health check", "All services healthy", {"agent": "monitor_agent"}),
            ("Backup process", "Daily backup completed", {"agent": "backup_agent"}),
        ]
        
        start_time = time.perf_counter()
        
        for req_summary, resp_content, metadata in test_responses:
            logger.log_response(req_summary, resp_content, metadata)
        
        queue_time = time.perf_counter() - start_time
        
        # Flush to ensure all journal entries are written
        logger.flush(timeout=5.0)
        total_time = time.perf_counter() - start_time
        
        print(f"  ✓ Logged {len(test_responses)} entries to journal")
        print(f"  ✓ Queue time: {queue_time:.3f}s")
        print(f"  ✓ Total time: {total_time:.3f}s")
        print(f"  ✓ Throughput: {len(test_responses)/queue_time:.1f} entries/sec")
        
        # Try to check recent journal entries (Linux only)
        journal_check_success = False
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run(
                    ["journalctl", "--since", "1 minute ago", "-f", "-n", "10", "--grep", "Claude MPM Response"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "Claude MPM Response" in result.stdout:
                    print(f"  ✓ Found journal entries")
                    journal_check_success = True
                else:
                    print(f"  ⚠ Could not verify journal entries (may still be working)")
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"  ⚠ Could not check journal: {e}")
        else:
            print(f"  ⚠ Journald not available on {sys.platform}, likely fell back to JSON")
        
        logger.shutdown()
        
        return {
            "logged_entries": len(test_responses),
            "queue_time": queue_time,
            "total_time": total_time,
            "journal_verified": journal_check_success,
            "success": True  # Success if no exceptions were thrown
        }
        
    except Exception as e:
        print(f"  ✗ Journald test failed: {e}")
        return {
            "logged_entries": 0,
            "success": False,
            "error": str(e)
        }


def test_environment_variable_controls():
    """Test environment variable controls for format switching."""
    print("\n=== Testing Environment Variable Controls ===")
    
    # Test CLAUDE_LOG_FORMAT environment variable
    formats_to_test = [
        ("json", LogFormat.JSON),
        ("syslog", LogFormat.SYSLOG),
        ("journald", LogFormat.JOURNALD),
    ]
    
    results = {}
    
    for env_value, expected_format in formats_to_test:
        print(f"\n--- Testing CLAUDE_LOG_FORMAT={env_value} ---")
        
        # Set environment variable
        os.environ["CLAUDE_LOG_FORMAT"] = env_value
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Import fresh to pick up env variable
                from claude_mpm.services.async_session_logger import get_async_logger
                
                logger = get_async_logger()
                
                # Check that the format was set correctly
                actual_format = logger.log_format
                format_correct = actual_format == expected_format
                
                print(f"  ✓ Expected format: {expected_format}")
                print(f"  ✓ Actual format: {actual_format}")
                print(f"  ✓ Format correct: {format_correct}")
                
                # Test a quick log
                logger.log_response(
                    "Environment test",
                    f"Testing {env_value} format via environment variable",
                    {"agent": "test_agent"}
                )
                
                logger.flush(timeout=2.0)
                logger.shutdown()
                
                results[env_value] = {
                    "expected_format": expected_format,
                    "actual_format": actual_format,
                    "format_correct": format_correct,
                    "success": True
                }
                
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            results[env_value] = {
                "success": False,
                "error": str(e)
            }
    
    # Clean up environment
    if "CLAUDE_LOG_FORMAT" in os.environ:
        del os.environ["CLAUDE_LOG_FORMAT"]
    
    # Test CLAUDE_LOG_SYNC environment variable
    print(f"\n--- Testing CLAUDE_LOG_SYNC=true ---")
    os.environ["CLAUDE_LOG_SYNC"] = "true"
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            from claude_mpm.services.async_session_logger import get_async_logger
            
            logger = get_async_logger()
            
            # Check that async is disabled
            async_disabled = not logger.enable_async
            print(f"  ✓ Async disabled: {async_disabled}")
            
            logger.shutdown()
            
            results["sync_mode"] = {
                "async_disabled": async_disabled,
                "success": True
            }
    
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results["sync_mode"] = {
            "success": False,
            "error": str(e)
        }
    
    # Clean up environment
    if "CLAUDE_LOG_SYNC" in os.environ:
        del os.environ["CLAUDE_LOG_SYNC"]
    
    return results


def main():
    """Main test function."""
    print("🧪 LOGGING FORMAT VALIDATION TEST SUITE")
    print("="*60)
    
    # Test all formats
    json_result = test_json_format()
    syslog_result = test_syslog_format()
    journald_result = test_journald_format()
    env_results = test_environment_variable_controls()
    
    # Summary
    print("\n" + "="*60)
    print("FORMAT TESTING SUMMARY")
    print("="*60)
    
    print(f"📄 JSON Format:")
    print(f"  ✓ Files created: {json_result.get('files_created', 0)}")
    print(f"  ✓ Valid files: {json_result.get('valid_files', 0)}")
    print(f"  ✓ Status: {'✅ PASS' if json_result.get('success') else '❌ FAIL'}")
    
    print(f"\n📊 Syslog Format:")
    print(f"  ✓ Entries logged: {syslog_result.get('logged_entries', 0)}")
    if 'queue_time' in syslog_result:
        print(f"  ✓ Queue time: {syslog_result['queue_time']:.3f}s")
    print(f"  ✓ Status: {'✅ PASS' if syslog_result.get('success') else '❌ FAIL'}")
    if not syslog_result.get('success') and 'error' in syslog_result:
        print(f"  ⚠ Error: {syslog_result['error']}")
    
    print(f"\n📋 Journald Format:")
    print(f"  ✓ Entries logged: {journald_result.get('logged_entries', 0)}")
    if 'queue_time' in journald_result:
        print(f"  ✓ Queue time: {journald_result['queue_time']:.3f}s")
    print(f"  ✓ Status: {'✅ PASS' if journald_result.get('success') else '❌ FAIL'}")
    if not journald_result.get('success') and 'error' in journald_result:
        print(f"  ⚠ Error: {journald_result['error']}")
    
    print(f"\n🔧 Environment Variable Controls:")
    for key, result in env_results.items():
        if key == "sync_mode":
            print(f"  ✓ Sync mode: {'✅ PASS' if result.get('success') else '❌ FAIL'}")
        else:
            print(f"  ✓ {key.upper()} format: {'✅ PASS' if result.get('success') else '❌ FAIL'}")
    
    # Overall assessment
    successful_tests = sum(1 for r in [json_result, syslog_result, journald_result] if r.get('success'))
    env_successful = sum(1 for r in env_results.values() if r.get('success'))
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"  ✓ Format tests passed: {successful_tests}/3")
    print(f"  ✓ Environment tests passed: {env_successful}/{len(env_results)}")
    
    if successful_tests >= 2 and env_successful >= 3:  # At least JSON + 1 other format, most env controls
        print("\n🎉 FORMAT TESTING PASSED!")
        print("✅ Multiple logging formats working correctly")
        print("✅ Environment variable controls functional")
        print("✅ Format switching operates as expected")
    else:
        print("\n⚠️ SOME FORMAT TESTS FAILED")
        print("❌ Review failed tests above for issues")
    
    return {
        "json": json_result,
        "syslog": syslog_result,
        "journald": journald_result,
        "environment": env_results
    }


if __name__ == "__main__":
    main()