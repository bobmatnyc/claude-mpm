"""Tests for ticket extraction functionality."""

import pytest
from orchestration.ticket_extractor import TicketExtractor


class TestTicketExtractor:
    """Test the TicketExtractor class."""
    
    def setup_method(self):
        """Set up test instance."""
        self.extractor = TicketExtractor()
    
    def test_extract_todo(self):
        """Test TODO extraction."""
        line = "TODO: Implement user authentication system"
        tickets = self.extractor.extract_from_line(line)
        
        assert len(tickets) == 1
        assert tickets[0]['type'] == 'task'
        assert tickets[0]['title'] == 'Implement user authentication system'
        assert tickets[0]['label'] == 'todo'
    
    def test_extract_bug(self):
        """Test BUG extraction."""
        line = "BUG: Memory leak in session handler"
        tickets = self.extractor.extract_from_line(line)
        
        assert len(tickets) == 1
        assert tickets[0]['type'] == 'bug'
        assert tickets[0]['title'] == 'Memory leak in session handler'
        assert tickets[0]['label'] == 'bug'
    
    def test_extract_feature(self):
        """Test FEATURE extraction."""
        line = "FEATURE: Add dark mode support"
        tickets = self.extractor.extract_from_line(line)
        
        assert len(tickets) == 1
        assert tickets[0]['type'] == 'feature'
        assert tickets[0]['title'] == 'Add dark mode support'
        assert tickets[0]['label'] == 'feature'
    
    def test_case_insensitive(self):
        """Test case insensitive matching."""
        lines = [
            "todo: lowercase todo",
            "Todo: Titlecase todo",
            "TODO: UPPERCASE TODO"
        ]
        
        for line in lines:
            tickets = self.extractor.extract_from_line(line)
            assert len(tickets) == 1
            assert tickets[0]['type'] == 'task'
    
    def test_extract_multiline_text(self):
        """Test extraction from multi-line text."""
        text = """
        Here's what needs to be done:
        TODO: Refactor database connection
        BUG: Fix login timeout issue
        FEATURE: Add export functionality
        Some other text here
        """
        
        tickets = self.extractor.extract_from_text(text)
        assert len(tickets) == 3
        
        # Check ticket types
        types = [t['type'] for t in tickets]
        assert 'task' in types
        assert 'bug' in types
        assert 'feature' in types
    
    def test_clean_title(self):
        """Test title cleaning."""
        test_cases = [
            ("TODO: 'Quoted title'", "Quoted title"),
            ('TODO: "Double quoted"', "Double quoted"),
            ("TODO: Title with trailing dots...", "Title with trailing dots"),
            ("TODO: Title   with   spaces", "Title with spaces"),
            ("TODO: Title with comma,", "Title with comma"),
        ]
        
        for line, expected_title in test_cases:
            tickets = self.extractor.extract_from_line(line)
            assert len(tickets) == 1
            assert tickets[0]['title'] == expected_title
    
    def test_no_extraction(self):
        """Test lines that shouldn't extract tickets."""
        lines = [
            "This is just regular text",
            "Not a TODO item",
            "TODO without colon",
            "Empty TODO:",
            "TODO: ",  # Just whitespace
        ]
        
        for line in lines:
            tickets = self.extractor.extract_from_line(line)
            assert len(tickets) == 0
    
    def test_get_all_tickets(self):
        """Test getting all extracted tickets."""
        self.extractor.extract_from_line("TODO: First task")
        self.extractor.extract_from_line("BUG: First bug")
        
        all_tickets = self.extractor.get_all_tickets()
        assert len(all_tickets) == 2
        assert all_tickets[0]['title'] == 'First task'
        assert all_tickets[1]['title'] == 'First bug'
    
    def test_clear_tickets(self):
        """Test clearing extracted tickets."""
        self.extractor.extract_from_line("TODO: Task to clear")
        assert len(self.extractor.get_all_tickets()) == 1
        
        self.extractor.clear()
        assert len(self.extractor.get_all_tickets()) == 0
    
    def test_get_summary(self):
        """Test getting summary of tickets."""
        self.extractor.extract_from_line("TODO: Task 1")
        self.extractor.extract_from_line("TODO: Task 2")
        self.extractor.extract_from_line("BUG: Bug 1")
        self.extractor.extract_from_line("FEATURE: Feature 1")
        
        summary = self.extractor.get_summary()
        assert summary['task'] == 2
        assert summary['bug'] == 1
        assert summary['feature'] == 1
    
    def test_all_patterns(self):
        """Test all supported patterns."""
        patterns = [
            ("TODO: todo task", 'task', 'todo'),
            ("TASK: explicit task", 'task', 'task'),
            ("BUG: bug report", 'bug', 'bug'),
            ("FIXME: fix this", 'bug', 'fixme'),
            ("FEATURE: new feature", 'feature', 'feature'),
            ("ISSUE: general issue", 'issue', 'issue'),
            ("ENHANCEMENT: enhancement request", 'enhancement', 'enhancement'),
        ]
        
        for line, expected_type, expected_label in patterns:
            self.extractor.clear()
            tickets = self.extractor.extract_from_line(line)
            assert len(tickets) == 1
            assert tickets[0]['type'] == expected_type
            assert tickets[0]['label'] == expected_label