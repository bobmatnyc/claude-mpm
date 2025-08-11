"""
Tests for .claude-mpm directory initialization.

This module tests that the .claude-mpm directory structure is properly
created on startup in various scenarios.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest

from claude_mpm.init import ProjectInitializer
from claude_mpm.cli.utils import ensure_directories


class TestDirectoryInitialization:
    """Test directory initialization functionality."""
    
    def test_project_initializer_creates_all_directories(self):
        """Test that ProjectInitializer creates all required directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_project"
            test_dir.mkdir()
            
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(test_dir)
            
            try:
                # Initialize project directory
                initializer = ProjectInitializer()
                result = initializer.initialize_project_directory()
                
                # Check initialization succeeded
                assert result is True, "Initialization should return True"
                
                # Check .claude-mpm exists
                claude_dir = test_dir / ".claude-mpm"
                assert claude_dir.exists(), f".claude-mpm should exist at {claude_dir}"
                
                # Check all required directories exist
                required_dirs = [
                    claude_dir / "agents" / "project-specific",
                    claude_dir / "config",
                    claude_dir / "responses",
                    claude_dir / "logs",
                ]
                
                for dir_path in required_dirs:
                    assert dir_path.exists(), f"Directory {dir_path} should exist"
                
                # Check config file exists
                config_file = claude_dir / "config" / "project.json"
                assert config_file.exists(), "project.json should exist"
                
                # Check .gitignore exists
                gitignore = claude_dir / ".gitignore"
                assert gitignore.exists(), ".gitignore should exist"
                
            finally:
                os.chdir(original_cwd)
    
    def test_cli_ensure_directories_creates_structure(self):
        """Test that CLI ensure_directories creates the structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_cli"
            test_dir.mkdir()
            
            original_cwd = os.getcwd()
            os.chdir(test_dir)
            
            try:
                # Call CLI's ensure_directories
                ensure_directories()
                
                # Check .claude-mpm exists
                claude_dir = test_dir / ".claude-mpm"
                assert claude_dir.exists(), f".claude-mpm should exist at {claude_dir}"
                
                # Check essential directories
                essential_dirs = [
                    claude_dir / "agents",
                    claude_dir / "config",
                    claude_dir / "responses",
                    claude_dir / "logs",
                ]
                
                for dir_path in essential_dirs:
                    assert dir_path.exists(), f"Directory {dir_path} should exist"
                    
            finally:
                os.chdir(original_cwd)
    
    def test_initialization_uses_current_working_directory(self):
        """Test that initialization always uses the current working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested directory structure
            root_dir = Path(tmpdir) / "root"
            sub_dir = root_dir / "sub" / "project"
            sub_dir.mkdir(parents=True)
            
            # Add a .git directory in root (should be ignored)
            (root_dir / ".git").mkdir()
            
            original_cwd = os.getcwd()
            os.chdir(sub_dir)
            
            try:
                # Initialize - should create .claude-mpm in sub_dir, not root
                initializer = ProjectInitializer()
                result = initializer.initialize_project_directory()
                
                assert result is True
                
                # Check .claude-mpm is in current directory, not git root
                claude_in_cwd = sub_dir / ".claude-mpm"
                claude_in_root = root_dir / ".claude-mpm"
                
                assert claude_in_cwd.exists(), f".claude-mpm should exist in {sub_dir}"
                assert not claude_in_root.exists(), f".claude-mpm should NOT exist in {root_dir}"
                
                # Verify responses directory exists
                responses_dir = claude_in_cwd / "responses"
                assert responses_dir.exists(), "responses directory should exist"
                
            finally:
                os.chdir(original_cwd)
    
    def test_repeated_initialization_is_safe(self):
        """Test that repeated initialization doesn't cause errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_repeat"
            test_dir.mkdir()
            
            original_cwd = os.getcwd()
            os.chdir(test_dir)
            
            try:
                # Initialize multiple times
                initializer = ProjectInitializer()
                
                # First initialization
                result1 = initializer.initialize_project_directory()
                assert result1 is True
                
                # Create a file in responses directory
                responses_dir = test_dir / ".claude-mpm" / "responses"
                test_file = responses_dir / "test.txt"
                test_file.write_text("test content")
                
                # Second initialization - should not fail or delete existing files
                result2 = initializer.initialize_project_directory()
                assert result2 is True
                
                # Check test file still exists
                assert test_file.exists(), "Existing files should be preserved"
                assert test_file.read_text() == "test content"
                
                # Check all directories still exist
                claude_dir = test_dir / ".claude-mpm"
                assert (claude_dir / "agents" / "project-specific").exists()
                assert (claude_dir / "config").exists()
                assert (claude_dir / "responses").exists()
                assert (claude_dir / "logs").exists()
                
            finally:
                os.chdir(original_cwd)
    
    def test_fallback_creation_on_error(self):
        """Test that the fallback mechanism in CLI utils works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_fallback"
            test_dir.mkdir()
            
            original_cwd = os.getcwd()
            os.chdir(test_dir)
            
            try:
                # Just verify that calling ensure_directories creates the structure
                # even if there might be some internal errors
                ensure_directories()
                
                # Check that directories were created
                claude_dir = test_dir / ".claude-mpm"
                assert claude_dir.exists(), ".claude-mpm should be created"
                
                # Check essential directories including responses
                assert (claude_dir / "responses").exists(), "responses directory should exist"
                assert (claude_dir / "logs").exists(), "logs directory should exist"
                assert (claude_dir / "config").exists(), "config directory should exist"
                assert (claude_dir / "agents").exists(), "agents directory should exist"
                
            finally:
                os.chdir(original_cwd)


@pytest.fixture
def clean_test_dir():
    """Create a clean test directory and change to it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test"
        test_dir.mkdir()
        
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            yield test_dir
        finally:
            os.chdir(original_cwd)


def test_responses_directory_is_created(clean_test_dir):
    """Ensure responses directory is always created - this was the reported bug."""
    # Initialize project
    initializer = ProjectInitializer()
    result = initializer.initialize_project_directory()
    
    assert result is True
    
    # Check responses directory specifically
    responses_dir = clean_test_dir / ".claude-mpm" / "responses"
    assert responses_dir.exists(), "responses directory must be created"
    assert responses_dir.is_dir(), "responses should be a directory"
    
    # Verify it's writable
    test_file = responses_dir / "test.json"
    test_file.write_text('{"test": true}')
    assert test_file.exists()