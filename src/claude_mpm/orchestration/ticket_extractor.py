"""Ticket extraction from Claude output."""

import re
from typing import List, Dict, Any, Pattern, Tuple
from datetime import datetime

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger


class TicketExtractor:
    """
    Extract ticket-worthy patterns from Claude's output.
    
    Patterns detected:
    - TODO: items
    - BUG: reports
    - FEATURE: requests
    - FIXME: issues
    - ISSUE: problems
    - TASK: work items
    """
    
    # Ticket patterns with (pattern, ticket_type, label)
    PATTERNS: List[Tuple[Pattern, str, str]] = [
        (re.compile(r'TODO:\s*(.+)', re.IGNORECASE), 'task', 'todo'),
        (re.compile(r'TASK:\s*(.+)', re.IGNORECASE), 'task', 'task'),
        (re.compile(r'BUG:\s*(.+)', re.IGNORECASE), 'bug', 'bug'),
        (re.compile(r'FIXME:\s*(.+)', re.IGNORECASE), 'bug', 'fixme'),
        (re.compile(r'FEATURE:\s*(.+)', re.IGNORECASE), 'feature', 'feature'),
        (re.compile(r'ISSUE:\s*(.+)', re.IGNORECASE), 'issue', 'issue'),
        (re.compile(r'ENHANCEMENT:\s*(.+)', re.IGNORECASE), 'enhancement', 'enhancement'),
    ]
    
    def __init__(self):
        """Initialize the ticket extractor."""
        self.logger = get_logger("ticket_extractor")
        self.extracted_tickets: List[Dict[str, Any]] = []
        
    def extract_from_line(self, line: str) -> List[Dict[str, Any]]:
        """
        Extract tickets from a single line of output.
        
        Args:
            line: Line of text to process
            
        Returns:
            List of extracted tickets
        """
        tickets = []
        
        for pattern, ticket_type, label in self.PATTERNS:
            match = pattern.search(line)
            if match:
                title = match.group(1).strip()
                
                # Clean up the title
                title = self._clean_title(title)
                
                if title:  # Only create ticket if title is non-empty
                    ticket = {
                        'type': ticket_type,
                        'title': title,
                        'label': label,
                        'raw_line': line,
                        'extracted_at': datetime.now().isoformat(),
                    }
                    
                    tickets.append(ticket)
                    self.extracted_tickets.append(ticket)
                    
                    self.logger.debug(f"Extracted {ticket_type}: {title}")
        
        return tickets
    
    def extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract tickets from multi-line text.
        
        Args:
            text: Text to process
            
        Returns:
            List of extracted tickets
        """
        tickets = []
        
        for line in text.splitlines():
            line_tickets = self.extract_from_line(line)
            tickets.extend(line_tickets)
        
        return tickets
    
    def _clean_title(self, title: str) -> str:
        """
        Clean up ticket title.
        
        Args:
            title: Raw title text
            
        Returns:
            Cleaned title
        """
        # Remove trailing punctuation
        title = title.rstrip('.,;:')
        
        # Remove quotes if they wrap the entire title
        if len(title) >= 2 and title[0] == title[-1] and title[0] in '"\'':
            title = title[1:-1]
        
        # Collapse multiple spaces
        title = ' '.join(title.split())
        
        return title
    
    def get_all_tickets(self) -> List[Dict[str, Any]]:
        """Get all extracted tickets."""
        return self.extracted_tickets.copy()
    
    def clear(self):
        """Clear extracted tickets."""
        self.extracted_tickets.clear()
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get summary of extracted tickets by type.
        
        Returns:
            Dictionary with ticket type counts
        """
        summary = {}
        for ticket in self.extracted_tickets:
            ticket_type = ticket['type']
            summary[ticket_type] = summary.get(ticket_type, 0) + 1
        
        return summary
    
    def add_ticket(self, ticket: Dict[str, Any]):
        """
        Add a ticket manually (e.g., from hook response).
        
        Args:
            ticket: Ticket dictionary with at least 'type' and 'title'
        """
        # Ensure required fields
        if 'type' not in ticket or 'title' not in ticket:
            self.logger.warning(f"Skipping invalid ticket: {ticket}")
            return
        
        # Add metadata if not present
        if 'extracted_at' not in ticket:
            ticket['extracted_at'] = datetime.now().isoformat()
        if 'label' not in ticket:
            ticket['label'] = ticket['type']
        
        self.extracted_tickets.append(ticket)
        self.logger.debug(f"Added ticket from hook: {ticket['type']} - {ticket['title']}")