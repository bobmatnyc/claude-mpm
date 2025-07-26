"""Comprehensive tests for agent name normalization across TodoWrite and Task tools."""

import unittest
from unittest.mock import Mock, patch
import logging
from datetime import datetime

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer, agent_name_normalizer
from claude_mpm.hooks.builtin.todo_agent_prefix_hook import (
    TodoAgentPrefixHook, 
    TodoAgentPrefixValidatorHook
)
from claude_mpm.hooks.base_hook import HookContext, HookType

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestAgentNameNormalizer(unittest.TestCase):
    """Test the AgentNameNormalizer class functionality."""
    
    def test_normalize_basic_names(self):
        """Test normalization of basic agent names."""
        test_cases = [
            # Input -> Expected output
            ("research", "Research"),
            ("Research", "Research"),
            ("RESEARCH", "Research"),
            ("engineer", "Engineer"),
            ("Engineer", "Engineer"),
            ("qa", "QA"),
            ("QA", "QA"),
            ("Qa", "QA"),
            ("security", "Security"),
            ("documentation", "Documentation"),
            ("ops", "Ops"),
            ("version_control", "Version Control"),
            ("version control", "Version Control"),
            ("Version Control", "Version Control"),
            ("data_engineer", "Data Engineer"),
            ("data engineer", "Data Engineer"),
            ("Data Engineer", "Data Engineer"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.normalize(input_name)
                self.assertEqual(result, expected, 
                    f"Failed to normalize '{input_name}' to '{expected}', got '{result}'")
    
    def test_normalize_aliases(self):
        """Test normalization of agent aliases."""
        test_cases = [
            # Aliases -> Expected canonical name
            ("researcher", "Research"),
            ("dev", "Engineer"),
            ("developer", "Engineer"),
            ("engineering", "Engineer"),
            ("quality", "QA"),
            ("testing", "QA"),
            ("test", "QA"),
            ("sec", "Security"),
            ("docs", "Documentation"),
            ("doc", "Documentation"),
            ("operations", "Ops"),
            ("devops", "Ops"),
            ("git", "Version Control"),
            ("vcs", "Version Control"),
            ("data", "Data Engineer"),
            ("architect", "Architect"),
            ("architecture", "Architect"),
            ("arch", "Architect"),
            ("pm", "PM"),
            ("PM", "PM"),
            ("project_manager", "PM"),
            ("project manager", "PM"),
        ]
        
        for alias, expected in test_cases:
            with self.subTest(alias=alias):
                result = AgentNameNormalizer.normalize(alias)
                self.assertEqual(result, expected,
                    f"Failed to normalize alias '{alias}' to '{expected}', got '{result}'")
    
    def test_normalize_edge_cases(self):
        """Test edge cases in normalization."""
        # Empty string
        self.assertEqual(AgentNameNormalizer.normalize(""), "Engineer")
        
        # Unknown agent
        self.assertEqual(AgentNameNormalizer.normalize("unknown_agent"), "Engineer")
        
        # With extra spaces
        self.assertEqual(AgentNameNormalizer.normalize("  research  "), "Research")
        
        # With hyphens
        self.assertEqual(AgentNameNormalizer.normalize("version-control"), "Version Control")
        self.assertEqual(AgentNameNormalizer.normalize("data-engineer"), "Data Engineer")
    
    def test_to_key_format(self):
        """Test conversion to key format."""
        test_cases = [
            ("Research", "research"),
            ("Version Control", "version_control"),
            ("Data Engineer", "data_engineer"),
            ("QA", "qa"),
            ("version-control", "version_control"),  # Hyphen to underscore
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.to_key(input_name)
                self.assertEqual(result, expected)
    
    def test_to_todo_prefix(self):
        """Test TODO prefix generation."""
        test_cases = [
            ("research", "[Research]"),
            ("engineer", "[Engineer]"),
            ("version_control", "[Version Control]"),
            ("data-engineer", "[Data Engineer]"),
            ("qa", "[QA]"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input=input_name):
                result = AgentNameNormalizer.to_todo_prefix(input_name)
                self.assertEqual(result, expected)
    
    def test_extract_from_todo(self):
        """Test extracting agent names from TODO text."""
        test_cases = [
            ("[Research] Analyze patterns", "Research"),
            ("[Engineer] Implement feature", "Engineer"),
            ("[Version Control] Create release", "Version Control"),
            ("[Data Engineer] Build pipeline", "Data Engineer"),
            ("[QA] Run tests", "QA"),
            # With extra spaces
            ("  [Research]  Analyze patterns", "Research"),
            # Without prefix
            ("Implement feature", None),
            # Invalid prefix
            ("[Unknown] Do something", "Engineer"),  # Falls back to default
        ]
        
        for todo_text, expected in test_cases:
            with self.subTest(todo=todo_text):
                result = AgentNameNormalizer.extract_from_todo(todo_text)
                self.assertEqual(result, expected)
    
    def test_validate_todo_format(self):
        """Test TODO format validation."""
        # Valid formats
        valid_todos = [
            "[Research] Analyze patterns",
            "[Engineer] Implement feature",
            "[Version Control] Create release",
            "[Data Engineer] Build pipeline",
            "[QA] Run tests",
            "[Security] Audit code",
            "[Documentation] Update README",
            "[Ops] Deploy service",
        ]
        
        for todo in valid_todos:
            with self.subTest(todo=todo):
                is_valid, error = AgentNameNormalizer.validate_todo_format(todo)
                self.assertTrue(is_valid, f"Todo '{todo}' should be valid")
                self.assertIsNone(error)
        
        # Invalid formats - Note: Unknown agents get normalized to Engineer, so they're technically valid
        invalid_todos = [
            "Implement feature",  # No prefix
            "[] Empty prefix",  # Empty prefix
        ]
        
        for todo in invalid_todos:
            with self.subTest(todo=todo):
                is_valid, error = AgentNameNormalizer.validate_todo_format(todo)
                self.assertFalse(is_valid, f"Todo '{todo}' should be invalid")
                self.assertIsNotNone(error)
        
        # Test that unknown agents get normalized but are still valid
        unknown_agent_todo = "[Unknown] Do something"
        is_valid, error = AgentNameNormalizer.validate_todo_format(unknown_agent_todo)
        self.assertTrue(is_valid, "Unknown agents should be normalized to Engineer and be valid")
    
    def test_to_task_format(self):
        """Test conversion to Task tool format."""
        test_cases = [
            # TodoWrite format -> Task format
            ("Research", "research"),
            ("Engineer", "engineer"),
            ("QA", "qa"),
            ("Security", "security"),
            ("Documentation", "documentation"),
            ("Ops", "ops"),
            ("Version Control", "version-control"),
            ("Data Engineer", "data-engineer"),
            ("Architect", "architect"),
            ("PM", "pm"),
            # Already in lowercase
            ("research", "research"),
            ("version control", "version-control"),
        ]
        
        for todo_format, expected_task_format in test_cases:
            with self.subTest(input=todo_format):
                result = AgentNameNormalizer.to_task_format(todo_format)
                self.assertEqual(result, expected_task_format,
                    f"Failed to convert '{todo_format}' to task format '{expected_task_format}', got '{result}'")
    
    def test_from_task_format(self):
        """Test conversion from Task tool format to TodoWrite format."""
        test_cases = [
            # Task format -> TodoWrite format
            ("research", "Research"),
            ("engineer", "Engineer"),
            ("qa", "QA"),
            ("security", "Security"),
            ("documentation", "Documentation"),
            ("ops", "Ops"),
            ("version-control", "Version Control"),
            ("data-engineer", "Data Engineer"),
            ("architect", "Architect"),
            ("pm", "PM"),
            # Already in canonical format
            ("Research", "Research"),
            ("Version Control", "Version Control"),
        ]
        
        for task_format, expected_todo_format in test_cases:
            with self.subTest(input=task_format):
                result = AgentNameNormalizer.from_task_format(task_format)
                self.assertEqual(result, expected_todo_format,
                    f"Failed to convert '{task_format}' from task format to '{expected_todo_format}', got '{result}'")
    
    def test_colorize(self):
        """Test agent name colorization."""
        # Just test that it adds color codes
        result = AgentNameNormalizer.colorize("research")
        self.assertIn("\033[", result)  # Contains color code
        self.assertIn("Research", result)  # Contains normalized name
        self.assertIn("\033[0m", result)  # Contains reset code
        
        # Test with custom text
        result = AgentNameNormalizer.colorize("research", "Custom Text")
        self.assertIn("Custom Text", result)
        self.assertNotIn("Research", result)


class TestTodoAgentPrefixHook(unittest.TestCase):
    """Test the TodoAgentPrefixHook functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hook = TodoAgentPrefixHook()
        self.validator_hook = TodoAgentPrefixValidatorHook()
    
    def create_hook_context(self, tool_name, parameters):
        """Create a HookContext for testing."""
        return HookContext(
            hook_type=HookType.CUSTOM,
            data={
                'tool_name': tool_name,
                'parameters': parameters
            },
            metadata={},
            timestamp=datetime.now()
        )
    
    def test_hook_adds_prefix_automatically(self):
        """Test that hook automatically adds appropriate prefixes."""
        test_cases = [
            # Todo content -> Expected keywords to match agent
            ("Research best practices for testing", "research"),
            ("Implement new feature", "implement"),
            ("Run test suite and validate", "test"),
            ("Document the API endpoints", "document"),
            ("Audit security vulnerabilities", "security"),
            ("Deploy application to production", "deploy"),
            ("Build data pipeline for analytics", "data.*pipeline"),
            ("Create git branch for release", "git"),
        ]
        
        for content, pattern_hint in test_cases:
            with self.subTest(content=content):
                context = self.create_hook_context('TodoWrite', {
                    'todos': [{'content': content}]
                })
                
                result = self.hook.execute(context)
                
                self.assertTrue(result.success)
                self.assertTrue(result.modified)
                
                # Check that a prefix was added
                updated_todos = result.data['parameters']['todos']
                updated_content = updated_todos[0]['content']
                
                # Verify it has a bracketed prefix
                import re
                self.assertTrue(re.match(r'^\[[^\]]+\]', updated_content),
                    f"Content '{updated_content}' should start with a bracketed agent prefix")
    
    def test_hook_preserves_existing_prefix(self):
        """Test that hook doesn't modify todos with existing prefixes."""
        todos_with_prefixes = [
            "[Research] Analyze patterns",
            "[Engineer] Implement feature",
            "[Version Control] Create release",
            "[Data Engineer] Build pipeline",
        ]
        
        for todo_content in todos_with_prefixes:
            with self.subTest(todo=todo_content):
                context = self.create_hook_context('TodoWrite', {
                    'todos': [{'content': todo_content}]
                })
                
                result = self.hook.execute(context)
                
                self.assertTrue(result.success)
                self.assertFalse(result.modified)  # Should not modify
    
    def test_hook_blocks_ambiguous_todos(self):
        """Test that hook blocks todos it can't classify."""
        ambiguous_todos = [
            "Do something",
            "Complete the task",
            "Work on the project",
        ]
        
        for todo_content in ambiguous_todos:
            with self.subTest(todo=todo_content):
                context = self.create_hook_context('TodoWrite', {
                    'todos': [{'content': todo_content}]
                })
                
                result = self.hook.execute(context)
                
                self.assertFalse(result.success)
                self.assertIn("missing required [Agent] prefix", result.error)
    
    def test_validator_hook(self):
        """Test the validator hook (no auto-fixing)."""
        # Valid todo
        context = self.create_hook_context('TodoWrite', {
            'todos': [{'content': '[Research] Analyze patterns'}]
        })
        result = self.validator_hook.execute(context)
        self.assertTrue(result.success)
        
        # Invalid todo
        context = self.create_hook_context('TodoWrite', {
            'todos': [{'content': 'Analyze patterns'}]
        })
        result = self.validator_hook.execute(context)
        self.assertFalse(result.success)
        self.assertIn("missing required agent prefix", result.error)


class TestIntegrationScenarios(unittest.TestCase):
    """Test end-to-end integration scenarios."""
    
    def test_todo_to_task_flow(self):
        """Test the flow from TodoWrite format to Task format."""
        # Simulate TodoWrite creating todos
        todos = [
            "[Research] Investigate best practices",
            "[Version Control] Create release v2.0",
            "[Data Engineer] Build ETL pipeline",
            "[QA] Run integration tests",
        ]
        
        # Extract agents and convert to Task format
        for todo in todos:
            agent = AgentNameNormalizer.extract_from_todo(todo)
            self.assertIsNotNone(agent)
            
            # Convert to Task format
            task_format = AgentNameNormalizer.to_task_format(agent)
            
            # Verify Task format
            self.assertIsInstance(task_format, str)
            self.assertEqual(task_format, task_format.lower())
            self.assertNotIn(" ", task_format)  # No spaces, uses hyphens
            
            # Verify round-trip conversion
            back_to_todo = AgentNameNormalizer.from_task_format(task_format)
            self.assertEqual(back_to_todo, agent)
    
    def test_all_agents_coverage(self):
        """Ensure all agent types are properly handled."""
        all_agents = [
            "Research", "Engineer", "QA", "Security", 
            "Documentation", "Ops", "Version Control", 
            "Data Engineer", "Architect", "PM"
        ]
        
        for agent in all_agents:
            with self.subTest(agent=agent):
                # Test TODO prefix
                prefix = AgentNameNormalizer.to_todo_prefix(agent)
                self.assertEqual(prefix, f"[{agent}]")
                
                # Test Task format
                task_format = AgentNameNormalizer.to_task_format(agent)
                self.assertTrue(task_format.islower() or "-" in task_format)
                
                # Test extraction
                todo = f"{prefix} Some task"
                extracted = AgentNameNormalizer.extract_from_todo(todo)
                self.assertEqual(extracted, agent)
                
                # Test round-trip
                back = AgentNameNormalizer.from_task_format(task_format)
                self.assertEqual(back, agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)