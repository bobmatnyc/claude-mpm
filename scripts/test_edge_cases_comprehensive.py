#!/usr/bin/env python3
"""
Test Edge Cases and Error Handling

Comprehensive tests for edge cases, error conditions, and robustness
of the session logging system.
"""

import os
import sys
import json
import tempfile
import shutil
import stat
from pathlib import Path
from datetime import datetime
import threading
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def clear_session_env_vars():
    """Clear all session-related environment variables."""
    env_vars = ['CLAUDE_SESSION_ID', 'ANTHROPIC_SESSION_ID', 'SESSION_ID']
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]


def reset_logger_singleton():
    """Reset the logger singleton."""
    import claude_mpm.services.claude_session_logger
    claude_mpm.services.claude_session_logger._logger_instance = None


def test_very_long_response():
    """Test logging of very long responses."""
    print("Testing Very Long Responses")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"long_response_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Create a very long response (1MB+)
    long_response = "This is a very long response. " * 35000  # ~1MB
    
    print(f"Response length: {len(long_response):,} characters")
    
    start_time = time.time()
    response_path = logger.log_response(
        "Test very long response logging",
        long_response,
        {"test": "long_response", "size": len(long_response)}
    )
    end_time = time.time()
    
    if response_path:
        print(f"✓ Long response logged successfully")
        print(f"  File: {response_path.name}")
        print(f"  Time: {end_time - start_time:.3f} seconds")
        
        # Verify file size and content
        file_size = response_path.stat().st_size
        print(f"  File size: {file_size:,} bytes")
        
        # Read and verify a portion of the file
        with open(response_path, 'r') as f:
            data = json.load(f)
            actual_response = data['response']
            print(f"  Verified response length: {len(actual_response):,} characters")
            print(f"  Content matches: {'✓' if actual_response == long_response else '✗'}")
    else:
        print("✗ Failed to log long response")
    
    clear_session_env_vars()
    print()


def test_special_characters_unicode():
    """Test logging with special characters and Unicode."""
    print("Testing Special Characters and Unicode")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"unicode_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Test various special characters
    special_response = """
    Unicode test: 你好世界 🌍 🚀
    Emoji: 😀 😃 😄 😁 😆 🤣 😂
    Special chars: ñáéíóú àèìòù äëïöü
    Symbols: ™ © ® § ¶ † ‡ • … ‰ ‱ ′ ″ ‴ ‵ ‶ ‷
    Math: ∀ ∂ ∃ ∅ ∇ ∈ ∉ ∋ ∌ ∏ ∑ √ ∝ ∞ ∟ ∠ ∡
    Arrows: ← ↑ → ↓ ↔ ↕ ↖ ↗ ↘ ↙
    Currency: $ € £ ¥ ¢ ₩ ₪ ₫ ₹ ₽
    Quotes: "smart quotes" 'apostrophes' „German quotes" «French quotes»
    Code: `backticks` ```code blocks```
    JSON: {"key": "value", "nested": {"array": [1, 2, 3]}}
    XML: <tag attribute="value">content</tag>
    Control chars: \\n\\t\\r\\0
    """
    
    response_path = logger.log_response(
        "Testing special characters and Unicode 测试",
        special_response,
        {"test": "unicode", "emojis": "🎯", "special": "ñáéíóú"}
    )
    
    if response_path:
        print("✓ Unicode response logged successfully")
        
        # Verify the content was preserved
        with open(response_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            preserved_response = data['response']
            preserved_metadata = data['metadata']
            
            print(f"  Response preserved: {'✓' if preserved_response == special_response else '✗'}")
            print(f"  Metadata preserved: {'✓' if preserved_metadata['emojis'] == '🎯' else '✗'}")
            print(f"  Unicode in request: {'✓' if '测试' in data['request_summary'] else '✗'}")
    else:
        print("✗ Failed to log Unicode response")
    
    clear_session_env_vars()
    print()


def test_concurrent_logging():
    """Test concurrent logging from multiple threads."""
    print("Testing Concurrent Logging")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"concurrent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    results = []
    errors = []
    
    def log_response(thread_id):
        """Log a response from a thread."""
        try:
            response_path = logger.log_response(
                f"Concurrent test from thread {thread_id}",
                f"This is response {thread_id} from concurrent logging test. " * 10,
                {"thread_id": thread_id, "test": "concurrent"}
            )
            results.append((thread_id, response_path))
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    # Start multiple threads
    threads = []
    num_threads = 10
    
    print(f"Starting {num_threads} concurrent threads...")
    
    start_time = time.time()
    for i in range(num_threads):
        thread = threading.Thread(target=log_response, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    print(f"All threads completed in {end_time - start_time:.3f} seconds")
    print(f"Successful logs: {len(results)}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("Errors encountered:")
        for thread_id, error in errors:
            print(f"  Thread {thread_id}: {error}")
    
    # Verify all responses were logged
    session_dir = Path.cwd() / "docs" / "responses" / test_session_id
    if session_dir.exists():
        files = list(session_dir.glob("response_*.json"))
        print(f"Files created: {len(files)}")
        print(f"Expected files: {num_threads}")
        print(f"All responses logged: {'✓' if len(files) == num_threads else '✗'}")
        
        # Verify response numbering is sequential and unique
        response_numbers = []
        for file in files:
            # Extract number from filename like "response_001.json"
            try:
                num = int(file.stem.split('_')[1])
                response_numbers.append(num)
            except:
                pass
        
        response_numbers.sort()
        expected_numbers = list(range(1, num_threads + 1))
        print(f"Sequential numbering: {'✓' if response_numbers == expected_numbers else '✗'}")
    else:
        print("✗ No session directory created")
    
    clear_session_env_vars()
    print()


def test_permission_errors():
    """Test handling of permission errors."""
    print("Testing Permission Errors")
    print("-" * 50)
    
    clear_session_env_vars()
    
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create logger with custom base directory
        from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
        
        test_session_id = f"permission_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.environ['CLAUDE_SESSION_ID'] = test_session_id
        
        logger = ClaudeSessionLogger(base_dir=temp_path / "responses")
        
        # First, test normal operation
        response_path = logger.log_response(
            "Permission test - normal",
            "This should work normally.",
            {"test": "permission_normal"}
        )
        
        if response_path:
            print("✓ Normal operation works")
        else:
            print("✗ Normal operation failed")
            clear_session_env_vars()
            return
        
        # Now make the session directory read-only
        session_dir = logger.get_session_path()
        if session_dir and session_dir.exists():
            # Change permissions to read-only
            os.chmod(session_dir, stat.S_IREAD)
            
            try:
                # This should fail
                response_path = logger.log_response(
                    "Permission test - read-only",
                    "This should fail due to permissions.",
                    {"test": "permission_readonly"}
                )
                
                if response_path:
                    print("✗ Write to read-only directory unexpectedly succeeded")
                else:
                    print("✓ Write to read-only directory properly failed")
            
            except Exception as e:
                print(f"✓ Permission error properly caught: {type(e).__name__}")
            
            finally:
                # Restore permissions for cleanup
                os.chmod(session_dir, stat.S_IWRITE | stat.S_IREAD)
    
    clear_session_env_vars()
    print()


def test_disk_space_simulation():
    """Test behavior when disk space is limited (simulated)."""
    print("Testing Large File Handling (Disk Space Simulation)")
    print("-" * 60)
    
    clear_session_env_vars()
    test_session_id = f"diskspace_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Create an extremely large response (simulating potential disk space issues)
    # Note: This is a simulation - we won't actually fill up the disk
    very_large_response = "Large response content. " * 100000  # ~2.5MB
    
    print(f"Testing response size: {len(very_large_response):,} characters")
    
    try:
        start_time = time.time()
        response_path = logger.log_response(
            "Disk space test - large response",
            very_large_response,
            {"test": "disk_space", "size": len(very_large_response)}
        )
        end_time = time.time()
        
        if response_path:
            print(f"✓ Large response logged successfully")
            print(f"  Time taken: {end_time - start_time:.3f} seconds")
            
            # Verify file was created and has correct size
            file_size = response_path.stat().st_size
            print(f"  File size: {file_size:,} bytes")
        else:
            print("✗ Large response logging failed")
    
    except Exception as e:
        print(f"Exception during large response logging: {type(e).__name__}: {e}")
    
    clear_session_env_vars()
    print()


def test_invalid_json_metadata():
    """Test handling of metadata that might cause JSON serialization issues."""
    print("Testing Invalid JSON Metadata Handling")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"json_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    # Test various problematic metadata values
    problematic_metadata = {
        "circular_ref": None,  # We'll add a circular reference
        "nan_value": float('nan'),
        "inf_value": float('inf'),
        "bytes_value": b"binary data",
        "function": lambda x: x,  # Function object
        "complex_number": 3+4j,
        "set_value": {1, 2, 3},
        "normal_value": "this should work"
    }
    
    # Create circular reference
    problematic_metadata["circular_ref"] = problematic_metadata
    
    try:
        response_path = logger.log_response(
            "JSON metadata test",
            "Testing metadata that might cause JSON serialization issues",
            problematic_metadata
        )
        
        if response_path:
            print("✓ Response logged despite problematic metadata")
            
            # Check what actually got saved
            with open(response_path, 'r') as f:
                data = json.load(f)
                saved_metadata = data['metadata']
                
                print("Saved metadata keys:")
                for key in saved_metadata:
                    print(f"  {key}: {type(saved_metadata[key]).__name__}")
                
                # Check if normal values were preserved
                if "normal_value" in saved_metadata:
                    print("✓ Normal values preserved")
        else:
            print("✗ Response logging failed with problematic metadata")
    
    except Exception as e:
        print(f"Exception with problematic metadata: {type(e).__name__}: {e}")
        
        # Try again with clean metadata
        clean_metadata = {"test": "json_recovery", "clean": True}
        response_path = logger.log_response(
            "JSON metadata recovery test",
            "Testing recovery with clean metadata",
            clean_metadata
        )
        
        if response_path:
            print("✓ Recovery with clean metadata successful")
        else:
            print("✗ Recovery failed")
    
    clear_session_env_vars()
    print()


def test_empty_and_null_values():
    """Test handling of empty and null values."""
    print("Testing Empty and Null Values")
    print("-" * 50)
    
    clear_session_env_vars()
    test_session_id = f"empty_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.environ['CLAUDE_SESSION_ID'] = test_session_id
    
    reset_logger_singleton()
    
    from claude_mpm.services.claude_session_logger import get_session_logger
    
    logger = get_session_logger()
    
    test_cases = [
        ("Empty request", "", "Normal response", {"test": "empty_request"}),
        ("Normal request", "Normal request", "", {"test": "empty_response"}),
        ("None request", None, "Normal response", {"test": "none_request"}),
        ("Normal request", "Normal request", None, {"test": "none_response"}),
        ("Empty metadata", "Normal request", "Normal response", {}),
        ("None metadata", "Normal request", "Normal response", None),
        ("All empty", "", "", {}),
    ]
    
    successful_logs = 0
    
    for test_name, request, response, metadata in test_cases:
        print(f"Testing: {test_name}")
        
        try:
            response_path = logger.log_response(request, response, metadata)
            
            if response_path:
                print(f"  ✓ Logged successfully")
                successful_logs += 1
                
                # Verify content
                with open(response_path, 'r') as f:
                    data = json.load(f)
                    print(f"  Request: '{data['request_summary']}'")
                    print(f"  Response: '{data['response'][:20]}{'...' if len(data['response']) > 20 else ''}'")
            else:
                print(f"  ✗ Failed to log")
        
        except Exception as e:
            print(f"  Exception: {type(e).__name__}: {e}")
    
    print(f"\nSuccessful logs: {successful_logs}/{len(test_cases)}")
    
    clear_session_env_vars()
    print()


def test_session_directory_creation_failure():
    """Test handling when session directory cannot be created."""
    print("Testing Session Directory Creation Failure")
    print("-" * 50)
    
    clear_session_env_vars()
    
    # Try to create logger with invalid base directory
    from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
    
    # Use a path that should cause permission issues
    invalid_paths = [
        "/root/responses",  # Requires root permissions
        "/invalid/path/that/does/not/exist/responses",  # Invalid path
        "/dev/null/responses",  # /dev/null is a file, not a directory
    ]
    
    for invalid_path in invalid_paths:
        print(f"Testing invalid path: {invalid_path}")
        
        try:
            test_session_id = f"invalid_path_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.environ['CLAUDE_SESSION_ID'] = test_session_id
            
            logger = ClaudeSessionLogger(base_dir=Path(invalid_path))
            
            # Try to log something
            response_path = logger.log_response(
                "Invalid path test",
                "This should handle the invalid path gracefully",
                {"test": "invalid_path"}
            )
            
            if response_path:
                print(f"  Unexpectedly succeeded: {response_path}")
            else:
                print(f"  ✓ Properly failed for invalid path")
        
        except Exception as e:
            print(f"  ✓ Exception handled: {type(e).__name__}: {e}")
        
        finally:
            clear_session_env_vars()
    
    print()


if __name__ == "__main__":
    print("Edge Cases and Error Handling Comprehensive Test")
    print("=" * 70)
    
    test_very_long_response()
    test_special_characters_unicode()
    test_concurrent_logging()
    test_permission_errors()
    test_disk_space_simulation()
    test_invalid_json_metadata()
    test_empty_and_null_values()
    test_session_directory_creation_failure()
    
    print("=" * 70)
    print("Edge cases and error handling tests complete!")
    print("The system should handle these edge cases gracefully.")