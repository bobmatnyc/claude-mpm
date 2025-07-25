"""Example ticket extraction hook implementation."""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from claude_mpm.hooks.base_hook import TicketExtractionHook, HookContext, HookResult
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class AutoTicketExtractionHook(TicketExtractionHook):
    """Hook that automatically extracts tickets from conversations."""
    
    def __init__(self):
        super().__init__(name="auto_ticket_extraction", priority=10)
        
        # Patterns for detecting ticket-worthy content
        self.ticket_patterns = [
            # Action items: "TODO:", "FIXME:", "ACTION:"
            (r'(?:TODO|FIXME|ACTION):\s*(.+?)(?:\n|$)', 'action'),
            # Bug reports: "bug:", "issue:", "problem:"
            (r'(?:bug|issue|problem):\s*(.+?)(?:\n|$)', 'bug'),
            # Feature requests: "feature:", "enhancement:", "request:"
            (r'(?:feature|enhancement|request):\s*(.+?)(?:\n|$)', 'feature'),
            # Questions that need follow-up
            (r'(?:question|Q):\s*(.+?)(?:\n|$)', 'question'),
            # Explicit ticket creation: "create ticket:", "new ticket:"
            (r'(?:create ticket|new ticket):\s*(.+?)(?:\n|$)', 'ticket')
        ]
        
    def execute(self, context: HookContext) -> HookResult:
        """Extract potential tickets from conversation."""
        try:
            # Get conversation content
            content = context.data.get('content', '')
            if isinstance(content, dict):
                # Handle structured content
                content = self._extract_text_content(content)
                
            # Find all potential tickets
            tickets = []
            
            for pattern, ticket_type in self.ticket_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    description = match.group(1).strip()
                    if description:
                        ticket = self._create_ticket(
                            description=description,
                            ticket_type=ticket_type,
                            context=context
                        )
                        tickets.append(ticket)
                        
            # Also check for numbered lists that might be tasks
            numbered_tasks = re.findall(r'^\d+\.\s*(.+?)$', content, re.MULTILINE)
            for task in numbered_tasks:
                if self._is_actionable(task):
                    ticket = self._create_ticket(
                        description=task.strip(),
                        ticket_type='task',
                        context=context
                    )
                    tickets.append(ticket)
                    
            if tickets:
                logger.info(f"Extracted {len(tickets)} potential tickets")
                return HookResult(
                    success=True,
                    data={
                        'tickets': tickets,
                        'original_content': content
                    },
                    modified=True,
                    metadata={'ticket_count': len(tickets)}
                )
            else:
                return HookResult(
                    success=True,
                    data={'original_content': content},
                    modified=False
                )
                
        except Exception as e:
            logger.error(f"Ticket extraction failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
            
    def _extract_text_content(self, data: Any) -> str:
        """Extract text content from structured data."""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            # Try common keys
            for key in ['content', 'text', 'message', 'result']:
                if key in data:
                    return self._extract_text_content(data[key])
            # Fallback to string representation
            return str(data)
        elif isinstance(data, list):
            return '\n'.join(self._extract_text_content(item) for item in data)
        else:
            return str(data)
            
    def _is_actionable(self, text: str) -> bool:
        """Determine if text represents an actionable item."""
        actionable_verbs = [
            'implement', 'create', 'add', 'fix', 'update', 'remove',
            'test', 'verify', 'check', 'investigate', 'research',
            'document', 'write', 'review', 'refactor', 'optimize'
        ]
        
        text_lower = text.lower()
        return any(verb in text_lower for verb in actionable_verbs)
        
    def _create_ticket(self, description: str, ticket_type: str, 
                      context: HookContext) -> Dict[str, Any]:
        """Create a ticket structure."""
        return {
            'id': None,  # To be assigned by ticket system
            'title': self._generate_title(description),
            'description': description,
            'type': ticket_type,
            'priority': context.data.get('priority', 'normal'),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'source': 'auto_extraction',
            'metadata': {
                'session_id': context.session_id,
                'user_id': context.user_id,
                'extraction_timestamp': context.timestamp.isoformat()
            }
        }
        
    def _generate_title(self, description: str) -> str:
        """Generate a concise title from description."""
        # Take first 50 chars or up to first period/newline
        title = description[:50]
        
        # Try to cut at sentence boundary
        for delimiter in ['.', '\n', '!', '?']:
            if delimiter in title:
                title = title.split(delimiter)[0]
                break
                
        # Clean up and ensure not too long
        title = title.strip()
        if len(title) > 50:
            title = title[:47] + '...'
            
        return title


class TicketPriorityAnalyzerHook(TicketExtractionHook):
    """Hook that analyzes and assigns priority to extracted tickets."""
    
    def __init__(self):
        super().__init__(name="ticket_priority_analyzer", priority=50)
        
        self.priority_indicators = {
            'critical': ['critical', 'urgent', 'blocker', 'emergency', 'asap'],
            'high': ['important', 'high priority', 'needed', 'required'],
            'low': ['minor', 'nice to have', 'someday', 'optional']
        }
        
    def execute(self, context: HookContext) -> HookResult:
        """Analyze and update ticket priorities."""
        try:
            tickets = context.data.get('tickets', [])
            
            if not tickets:
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False
                )
                
            # Analyze each ticket
            updated_tickets = []
            priorities_updated = 0
            
            for ticket in tickets:
                original_priority = ticket.get('priority', 'normal')
                analyzed_priority = self._analyze_priority(ticket)
                
                if analyzed_priority != original_priority:
                    ticket['priority'] = analyzed_priority
                    ticket['metadata']['priority_analyzed'] = True
                    priorities_updated += 1
                    
                updated_tickets.append(ticket)
                
            if priorities_updated > 0:
                logger.info(f"Updated priority for {priorities_updated} tickets")
                return HookResult(
                    success=True,
                    data={
                        'tickets': updated_tickets
                    },
                    modified=True,
                    metadata={'priorities_updated': priorities_updated}
                )
            else:
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False
                )
                
        except Exception as e:
            logger.error(f"Priority analysis failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
            
    def _analyze_priority(self, ticket: Dict[str, Any]) -> str:
        """Analyze ticket content to determine priority."""
        content = f"{ticket.get('title', '')} {ticket.get('description', '')}".lower()
        
        # Check for priority indicators
        for priority, indicators in self.priority_indicators.items():
            if any(indicator in content for indicator in indicators):
                return priority
                
        # Check ticket type
        ticket_type = ticket.get('type', '')
        if ticket_type == 'bug':
            return 'high'
        elif ticket_type == 'question':
            return 'normal'
            
        return 'normal'