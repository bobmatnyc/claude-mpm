"""Tests for agent delegator functionality."""

import pytest
from unittest.mock import Mock, MagicMock
from orchestration.agent_delegator import AgentDelegator
from core.agent_registry import AgentRegistryAdapter


class TestAgentDelegator:
    """Test the AgentDelegator class."""
    
    def setup_method(self):
        """Set up test instance."""
        self.delegator = AgentDelegator()
    
    def test_extract_explicit_delegation(self):
        """Test extracting explicit delegation pattern."""
        text = "Delegate to Engineer: Implement user authentication system"
        delegations = self.delegator.extract_delegations(text)
        
        assert len(delegations) == 1
        assert delegations[0]['agent'] == 'engineer'
        assert delegations[0]['task'] == 'Implement user authentication system'
        assert delegations[0]['pattern_type'] == 'explicit'
    
    def test_extract_arrow_delegation(self):
        """Test extracting arrow delegation pattern."""
        text = "→ QA Agent: Write comprehensive test suite"
        delegations = self.delegator.extract_delegations(text)
        
        assert len(delegations) == 1
        assert delegations[0]['agent'] == 'qa'
        assert delegations[0]['task'] == 'Write comprehensive test suite'
        assert delegations[0]['pattern_type'] == 'arrow'
    
    def test_extract_task_for_pattern(self):
        """Test extracting 'task for' pattern."""
        text = "Task for Documentation: Update API documentation"
        delegations = self.delegator.extract_delegations(text)
        
        assert len(delegations) == 1
        assert delegations[0]['agent'] == 'documentation'
        assert delegations[0]['task'] == 'Update API documentation'
    
    def test_extract_should_pattern(self):
        """Test extracting 'should' pattern."""
        text = "Research Agent should: Investigate performance optimization options"
        delegations = self.delegator.extract_delegations(text)
        
        assert len(delegations) == 1
        assert delegations[0]['agent'] == 'research'
        assert delegations[0]['task'] == 'Investigate performance optimization options'
    
    def test_extract_ask_pattern(self):
        """Test extracting 'ask' pattern."""
        text = "Ask Security to: Review authentication implementation"
        delegations = self.delegator.extract_delegations(text)
        
        assert len(delegations) == 1
        assert delegations[0]['agent'] == 'security'
        assert delegations[0]['task'] == 'Review authentication implementation'
    
    def test_agent_name_normalization(self):
        """Test agent name normalization."""
        test_cases = [
            ("Delegate to Doc: Task", "documentation"),
            ("Delegate to Eng: Task", "engineer"),
            ("Delegate to Dev: Task", "engineer"),
            ("Delegate to Test: Task", "qa"),
            ("Delegate to DevOps: Task", "ops"),
            ("Delegate to Sec: Task", "security"),
            ("Delegate to Git: Task", "version-control"),
            ("Delegate to Versioner: Task", "version-control"),
            ("Delegate to Data: Task", "data-engineer"),
            ("Delegate to Database: Task", "data-engineer"),
        ]
        
        for text, expected_agent in test_cases:
            delegations = self.delegator.extract_delegations(text)
            assert len(delegations) == 1
            assert delegations[0]['agent'] == expected_agent
    
    def test_multiline_extraction(self):
        """Test extraction from multiline text."""
        text = """
        Here's the plan:
        Delegate to Engineer: Implement the core functionality
        → QA Agent: Create test cases
        Task for Documentation: Write user guide
        Regular text here
        Ask Ops to: Set up CI/CD pipeline
        """
        
        delegations = self.delegator.extract_delegations(text)
        assert len(delegations) == 4
        
        agents = [d['agent'] for d in delegations]
        assert 'engineer' in agents
        assert 'qa' in agents
        assert 'documentation' in agents
        assert 'ops' in agents
    
    def test_format_task_tool_delegation_with_registry(self):
        """Test formatting with agent registry."""
        mock_registry = Mock(spec=AgentRegistryAdapter)
        mock_registry.format_agent_for_task_tool.return_value = "**Formatted Task**"
        
        delegator = AgentDelegator(agent_registry=mock_registry)
        result = delegator.format_task_tool_delegation('engineer', 'Task', 'Context')
        
        assert result == "**Formatted Task**"
        mock_registry.format_agent_for_task_tool.assert_called_once_with('engineer', 'Task', 'Context')
    
    def test_format_task_tool_delegation_fallback(self):
        """Test formatting without agent registry."""
        result = self.delegator.format_task_tool_delegation('engineer', 'Implement feature', 'Use patterns')
        
        assert "**Engineer Agent**:" in result
        assert "Implement feature" in result
        assert "Use patterns" in result
        assert "TEMPORAL CONTEXT" in result
    
    def test_suggest_agent_for_task_keywords(self):
        """Test agent suggestion based on keywords."""
        test_cases = [
            ("Update the README file", "documentation"),
            ("Implement new user model", "engineer"),
            ("Write unit tests for auth", "qa"),
            ("Research best practices for caching", "research"),
            ("Deploy to production server", "ops"),
            ("Review security vulnerabilities", "security"),
            ("Create a new git branch", "version-control"),
            ("Set up database migrations", "data-engineer"),
        ]
        
        for task, expected_agent in test_cases:
            suggested = self.delegator.suggest_agent_for_task(task)
            assert suggested == expected_agent
    
    def test_suggest_agent_with_registry(self):
        """Test agent suggestion with registry."""
        mock_registry = Mock(spec=AgentRegistryAdapter)
        mock_registry.select_agent_for_task.return_value = {
            'metadata': {'type': 'specialized-agent'}
        }
        
        delegator = AgentDelegator(agent_registry=mock_registry)
        result = delegator.suggest_agent_for_task("Complex task")
        
        assert result == 'specialized-agent'
    
    def test_get_delegation_summary(self):
        """Test getting delegation summary."""
        # Add some delegations
        self.delegator.extract_delegations("Delegate to Engineer: Task 1")
        self.delegator.extract_delegations("Delegate to Engineer: Task 2")
        self.delegator.extract_delegations("Delegate to QA: Task 3")
        self.delegator.extract_delegations("Delegate to Documentation: Task 4")
        
        summary = self.delegator.get_delegation_summary()
        assert summary['engineer'] == 2
        assert summary['qa'] == 1
        assert summary['documentation'] == 1
    
    def test_clear_delegations(self):
        """Test clearing delegations."""
        self.delegator.extract_delegations("Delegate to Engineer: Task")
        assert len(self.delegator.delegated_tasks) == 1
        
        self.delegator.clear()
        assert len(self.delegator.delegated_tasks) == 0
    
    def test_no_delegation_extraction(self):
        """Test lines that shouldn't extract delegations."""
        lines = [
            "This is regular text",
            "The engineer is working on it",
            "Documentation is important",
            "No delegation here",
        ]
        
        for line in lines:
            delegations = self.delegator.extract_delegations(line)
            assert len(delegations) == 0