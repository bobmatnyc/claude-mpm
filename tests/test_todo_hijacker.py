"""Test the TODO hijacking system."""

import json
import time
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

import pytest

from src.orchestration.todo_hijacker import TodoHijacker
from src.orchestration.todo_transformer import TodoTransformer


class TestTodoTransformer:
    """Test the TODO transformer."""
    
    def test_transform_basic_todo(self):
        """Test basic TODO transformation."""
        transformer = TodoTransformer()
        
        # Test engineer task
        todo = {
            "id": "1",
            "content": "Implement a function to calculate factorial",
            "status": "pending"
        }
        
        delegation = transformer.transform_todo(todo)
        assert delegation is not None
        assert delegation['agent'] == "Engineer"
        assert "factorial" in delegation['task']
        assert delegation['source'] == 'todo_hijacker'
        
    def test_agent_detection(self):
        """Test agent detection from task content."""
        transformer = TodoTransformer()
        
        test_cases = [
            ("Write unit tests for the authentication module", "QA"),
            ("Update the README documentation", "Documentation"),
            ("Research best practices for async programming", "Research"),
            ("Fix security vulnerability in login endpoint", "Security"),
            ("Deploy the application to production", "Ops"),
            ("Create a git branch for the new feature", "Version Control"),
            ("Set up database migration scripts", "Data Engineer")
        ]
        
        for task_content, expected_agent in test_cases:
            todo = {"content": task_content}
            delegation = transformer.transform_todo(todo)
            assert delegation['agent'] == expected_agent, f"Expected {expected_agent} for '{task_content}'"
    
    def test_skip_completed_todos(self):
        """Test that completed TODOs are skipped."""
        transformer = TodoTransformer()
        
        # Completed TODO
        todo = {
            "content": "Implement feature",
            "status": "completed"
        }
        
        delegation = transformer.transform_todo(todo)
        assert delegation is None  # Should be skipped


class TestTodoHijacker:
    """Test the TODO hijacker."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create a temporary directory for TODOs
        self.temp_dir = tempfile.mkdtemp()
        self.todo_dir = Path(self.temp_dir) / "todos"
        self.todo_dir.mkdir()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_todo_file_detection(self):
        """Test that TODO files are detected and processed."""
        delegations_received = []
        
        def on_delegation(delegation):
            delegations_received.append(delegation)
        
        hijacker = TodoHijacker(
            todo_dir=self.todo_dir,
            on_delegation=on_delegation
        )
        
        # Start monitoring
        hijacker.start_monitoring()
        
        try:
            # Create a TODO file
            todo_data = {
                "todos": [
                    {
                        "id": "test-1",
                        "content": "Write unit tests for the new feature",
                        "status": "pending"
                    }
                ]
            }
            
            todo_file = self.todo_dir / "test_todos.json"
            with open(todo_file, 'w') as f:
                json.dump(todo_data, f)
            
            # Give the watcher time to detect the file
            time.sleep(0.2)
            
            # Check that delegation was created
            assert len(delegations_received) == 1
            delegation = delegations_received[0]
            assert delegation['agent'] == "QA"
            assert "unit tests" in delegation['task']
            
        finally:
            hijacker.stop_monitoring()
    
    def test_multiple_todos(self):
        """Test processing multiple TODOs from one file."""
        hijacker = TodoHijacker(todo_dir=self.todo_dir)
        
        # Create a file with multiple TODOs
        todo_data = {
            "todos": [
                {"content": "Implement user authentication", "status": "pending"},
                {"content": "Write API documentation", "status": "pending"},
                {"content": "Deploy to staging server", "status": "pending"}
            ]
        }
        
        todo_file = self.todo_dir / "multi_todos.json"
        with open(todo_file, 'w') as f:
            json.dump(todo_data, f)
        
        # Get pending delegations
        delegations = hijacker.get_pending_delegations()
        
        assert len(delegations) == 3
        agents = [d['agent'] for d in delegations]
        assert "Security" in agents  # "Implement user authentication" -> Security
        assert "Documentation" in agents
        assert "Ops" in agents
    
    def test_skip_already_processed(self):
        """Test that processed TODOs are not reprocessed."""
        delegations_received = []
        
        def on_delegation(delegation):
            delegations_received.append(delegation)
        
        hijacker = TodoHijacker(
            todo_dir=self.todo_dir,
            on_delegation=on_delegation
        )
        
        # Create initial TODO
        todo_data = {"todos": [{"id": "1", "content": "Test task"}]}
        todo_file = self.todo_dir / "test.json"
        
        with hijacker:
            # Write file
            with open(todo_file, 'w') as f:
                json.dump(todo_data, f)
            
            time.sleep(0.2)
            assert len(delegations_received) == 1
            
            # Modify the file (but same TODO)
            with open(todo_file, 'w') as f:
                json.dump(todo_data, f)
            
            time.sleep(0.2)
            # Should still be 1 - not reprocessed
            assert len(delegations_received) == 1
    
    def test_context_manager(self):
        """Test context manager functionality."""
        delegations = []
        
        def on_delegation(d):
            delegations.append(d)
        
        with TodoHijacker(todo_dir=self.todo_dir, on_delegation=on_delegation) as hijacker:
            # Create TODO while monitoring
            todo_data = {"todos": [{"content": "Context manager test"}]}
            with open(self.todo_dir / "context.json", 'w') as f:
                json.dump(todo_data, f)
            
            time.sleep(0.2)
            assert len(delegations) == 1
        
        # After exiting context, monitoring should be stopped
        assert not hijacker._active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])