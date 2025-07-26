"""Example submit hook implementation."""

import re
from typing import Dict, Any

from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class TicketDetectionSubmitHook(SubmitHook):
    """Hook that detects ticket references in user prompts."""
    
    def __init__(self):
        super().__init__(name="ticket_detection", priority=10)
        self.ticket_pattern = re.compile(r'\b(?:TSK|BUG|FEAT)-\d+\b', re.IGNORECASE)
        
    def execute(self, context: HookContext) -> HookResult:
        """Detect and extract ticket references from prompt."""
        try:
            prompt = context.data.get('prompt', '')
            
            # Find all ticket references
            tickets = self.ticket_pattern.findall(prompt)
            
            if tickets:
                logger.info(f"Found {len(tickets)} ticket references: {tickets}")
                
                # Add ticket references to metadata
                return HookResult(
                    success=True,
                    data={
                        'tickets': list(set(tickets)),  # Unique tickets
                        'prompt': prompt
                    },
                    modified=True,
                    metadata={'ticket_count': len(set(tickets))}
                )
            else:
                return HookResult(
                    success=True,
                    data={'prompt': prompt},
                    modified=False
                )
                
        except Exception as e:
            logger.error(f"Ticket detection failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )


class PriorityDetectionSubmitHook(SubmitHook):
    """Hook that detects priority indicators in prompts."""
    
    def __init__(self):
        super().__init__(name="priority_detection", priority=20)
        self.priority_keywords = {
            'urgent': 'high',
            'asap': 'high',
            'critical': 'high',
            'important': 'high',
            'when you can': 'low',
            'whenever': 'low',
            'low priority': 'low'
        }
        
    def execute(self, context: HookContext) -> HookResult:
        """Detect priority level from prompt."""
        try:
            prompt = context.data.get('prompt', '').lower()
            
            # Check for priority keywords
            detected_priority = 'normal'
            for keyword, priority in self.priority_keywords.items():
                if keyword in prompt:
                    detected_priority = priority
                    break
                    
            if detected_priority != 'normal':
                logger.info(f"Detected priority: {detected_priority}")
                
            return HookResult(
                success=True,
                data={
                    'prompt': context.data.get('prompt', ''),
                    'priority': detected_priority
                },
                modified=detected_priority != 'normal',
                metadata={'priority_detected': detected_priority != 'normal'}
            )
            
        except Exception as e:
            logger.error(f"Priority detection failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )