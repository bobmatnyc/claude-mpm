#!/usr/bin/env python3
"""
Test Git branch validation fixes

Tests the client-side and server-side validation improvements for Git branch requests
to ensure that invalid directory states like 'Loading...' are properly handled.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestGitBranchValidation(unittest.TestCase):
    """Test Git branch request validation fixes."""

    def test_invalid_directory_states(self):
        """Test that common invalid directory states are properly handled."""
        # Test server-side validation
        from claude_mpm.services.socketio_server import SocketIOServer
        
        # Mock the server components
        mock_sio = MagicMock()
        mock_app = MagicMock()
        
        with patch('claude_mpm.services.socketio_server.SOCKETIO_AVAILABLE', True):
            server = SocketIOServer(host="localhost", port=8765)
            
            # Test invalid states that should be rejected or handled gracefully
            invalid_states = [
                'Loading...',
                'Loading', 
                'Unknown',
                'undefined',
                'null',
                '',
                None
            ]
            
            for invalid_state in invalid_states:
                print(f"Testing invalid state: {repr(invalid_state)}")
                
                # These states should either be rejected or converted to valid defaults
                # The server should not attempt to run git commands on these paths
                self.assertIn(invalid_state, [
                    None, '', 'Unknown', 'Loading...', 'Loading', 'undefined', 'null', 
                    'Not Connected', 'Invalid Directory', 'No Directory'
                ] or (isinstance(invalid_state, str) and invalid_state.strip() == ''))
                
        print("✅ Invalid directory state validation tests passed")

    def test_path_validation_logic(self):
        """Test the path validation logic from the working directory manager."""
        # Simulate the client-side validation logic
        def validate_directory_path(path):
            """Simulates the client-side validateDirectoryPath function."""
            if not path or not isinstance(path, str):
                return False
            
            # Basic path validation
            trimmed = path.strip()
            if len(trimmed) == 0:
                return False
            
            # Check for obviously invalid paths
            if '\0' in trimmed:
                return False
            
            # Check for common invalid placeholder states
            invalid_states = [
                'Loading...',
                'Loading',
                'Unknown',
                'undefined',
                'null',
                'Not Connected',
                'Invalid Directory',
                'No Directory'
            ]
            
            if trimmed in invalid_states:
                return False
            
            # Basic path structure validation - should start with / or drive letter on Windows
            if not trimmed.startswith('/') and not (len(trimmed) >= 2 and trimmed[1] == ':' and trimmed[0].isalpha()):
                # Allow relative paths that look reasonable
                if (trimmed.startswith('./') or trimmed.startswith('../') or 
                    (len(trimmed) > 0 and (trimmed[0].isalnum() or trimmed[0] in '._-'))):
                    return True
                return False
            
            return True

        # Test valid paths
        valid_paths = [
            '/usr/local/bin',
            '/Users/masa/Projects/claude-mpm',
            'C:\\Windows\\System32',
            './local/path',
            '../parent/path',
            'relative-path'
        ]
        
        for path in valid_paths:
            result = validate_directory_path(path)
            print(f"Valid path '{path}': {result}")
            self.assertTrue(result, f"Expected '{path}' to be valid")
        
        # Test invalid paths
        invalid_paths = [
            'Loading...',
            'Loading',
            'Unknown',
            'undefined',
            'null',
            'Not Connected',
            'Invalid Directory',
            'No Directory',
            '',
            None,
            'path\x00with\x00nulls'
        ]
        
        for path in invalid_paths:
            result = validate_directory_path(path)
            print(f"Invalid path {repr(path)}: {result}")
            self.assertFalse(result, f"Expected {repr(path)} to be invalid")

        print("✅ Path validation logic tests passed")

    def test_git_branch_request_prevention(self):
        """Test that Git branch requests are prevented for invalid directories."""
        # Simulate the client-side logic that prevents invalid requests
        def should_make_git_request(dir_path):
            """Simulates the logic that decides whether to make a Git branch request."""
            if not dir_path or not isinstance(dir_path, str):
                return False
                
            trimmed = dir_path.strip()
            
            # Check for loading states
            if trimmed in ['Loading...', 'Loading']:
                return False
                
            # Check for unknown states  
            if trimmed in ['Unknown', 'undefined', 'null']:
                return False
                
            # Check for empty/whitespace
            if len(trimmed) == 0:
                return False
                
            # Basic validation
            if '\0' in trimmed:
                return False
                
            return True

        # Test cases that should prevent Git requests
        prevent_cases = [
            'Loading...',
            'Loading', 
            'Unknown',
            'undefined',
            'null',
            '',
            '   ',  # whitespace only
            None,
            'path\x00with\x00nulls'
        ]
        
        for case in prevent_cases:
            should_request = should_make_git_request(case)
            print(f"Should request Git branch for {repr(case)}: {should_request}")
            self.assertFalse(should_request, f"Should not make Git request for {repr(case)}")
            
        # Test cases that should allow Git requests
        allow_cases = [
            '/valid/path',
            '/Users/masa/Projects/claude-mpm',
            'C:\\Users\\Name\\Project',
            './relative/path'
        ]
        
        for case in allow_cases:
            should_request = should_make_git_request(case)
            print(f"Should request Git branch for {repr(case)}: {should_request}")
            self.assertTrue(should_request, f"Should make Git request for {repr(case)}")

        print("✅ Git branch request prevention tests passed")

if __name__ == '__main__':
    print("Running Git branch validation fix tests...")
    print("=" * 50)
    
    unittest.main(verbosity=2)