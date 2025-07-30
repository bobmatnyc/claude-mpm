"""Memory integration hooks for automatic agent memory management.

WHY: Agents need to accumulate project-specific knowledge over time. These hooks
automatically inject agent memory before delegation and extract learnings after,
enabling agents to become more effective through experience.

DESIGN DECISION: We use regex patterns to extract structured learnings from
agent outputs because:
- It's non-invasive - agents don't need special formatting
- Natural language patterns are intuitive
- We can evolve patterns based on actual agent outputs
"""

import re
from typing import Dict, Any, List
from claude_mpm.hooks.base_hook import PreDelegationHook, PostDelegationHook, HookContext, HookResult
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.config import Config
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class MemoryPreDelegationHook(PreDelegationHook):
    """Inject agent memory into delegation context.
    
    WHY: Agents perform better when they have access to accumulated project knowledge.
    This hook loads agent-specific memory and adds it to the delegation context,
    allowing agents to apply learned patterns and avoid known mistakes.
    
    DESIGN DECISION: Memory is injected as a clearly formatted section in the context
    to ensure agents understand it's their accumulated knowledge, not current task info.
    """
    
    def __init__(self, config: Config = None):
        """Initialize with optional config.
        
        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__(name="memory_pre_delegation", priority=20)
        self.config = config or Config()
        self.memory_manager = AgentMemoryManager(self.config)
    
    def execute(self, context: HookContext) -> HookResult:
        """Add agent memory to delegation context.
        
        WHY: By loading memory before delegation, agents can reference their
        accumulated knowledge when performing tasks, leading to better outcomes.
        """
        try:
            # Extract and normalize agent ID from context
            agent_name = context.data.get('agent', '')
            if not agent_name:
                return HookResult(success=True, data=context.data, modified=False)
            
            # Normalize agent ID (e.g., "Engineer Agent" -> "engineer")
            agent_id = agent_name.lower().replace(' ', '_').replace('_agent', '').replace('agent', '').strip('_')
            
            if agent_id:
                # Load agent memory
                memory_content = self.memory_manager.load_agent_memory(agent_id)
                
                if memory_content and memory_content.strip():
                    # Get existing context data
                    delegation_context = context.data.get('context', {})
                    if isinstance(delegation_context, str):
                        # If context is a string, convert to dict
                        delegation_context = {'prompt': delegation_context}
                    
                    # Add memory with clear formatting
                    memory_section = f"""
AGENT MEMORY - PROJECT-SPECIFIC KNOWLEDGE:
{memory_content}

INSTRUCTIONS: Review your memory above before proceeding. Apply learned patterns and avoid known mistakes.
"""
                    
                    # Add to context
                    delegation_context['agent_memory'] = memory_section
                    
                    # Update the context data
                    updated_data = context.data.copy()
                    updated_data['context'] = delegation_context
                    
                    logger.info(f"Injected memory for agent '{agent_id}'")
                    
                    return HookResult(
                        success=True,
                        data=updated_data,
                        modified=True,
                        metadata={'memory_injected': True, 'agent_id': agent_id}
                    )
            
            return HookResult(success=True, data=context.data, modified=False)
                
        except Exception as e:
            logger.error(f"Memory injection failed: {e}")
            # Don't fail the delegation if memory injection fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Memory injection failed: {str(e)}"
            )


class MemoryPostDelegationHook(PostDelegationHook):
    """Extract learnings from delegation results.
    
    WHY: Agents produce valuable insights during task execution. This hook
    extracts structured learnings from their outputs, building up project-specific
    knowledge over time.
    
    DESIGN DECISION: We use multiple regex patterns to catch various ways agents
    might express learnings. Patterns are case-insensitive and flexible to maximize
    learning extraction while keeping entries concise (<100 chars).
    """
    
    def __init__(self, config: Config = None):
        """Initialize with optional config.
        
        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__(name="memory_post_delegation", priority=80)
        self.config = config or Config()
        self.memory_manager = AgentMemoryManager(self.config)
        
        # Learning extraction patterns
        # These patterns capture various ways agents express learnings
        self.learning_patterns = {
            'pattern': [
                r'discovered pattern:?\s*(.+)',
                r'learned that\s+(.+)',
                r'pattern found:?\s*(.+)',
                r'observed pattern:?\s*(.+)',
                r'noticed that\s+(.+)'
            ],
            'mistake': [
                r'mistake:?\s*(.+)',
                r'error was:?\s*(.+)', 
                r'should not\s+(.+)',
                r'avoid\s+(.+)',
                r'don\'t\s+(.+)',
                r'problem was:?\s*(.+)'
            ],
            'guideline': [
                r'guideline:?\s*(.+)',
                r'best practice:?\s*(.+)',
                r'should always\s+(.+)',
                r'recommendation:?\s*(.+)',
                r'always\s+(.+)',
                r'important to\s+(.+)'
            ],
            'architecture': [
                r'architecture:?\s*(.+)',
                r'structure:?\s*(.+)',
                r'component:?\s*(.+)',
                r'design pattern:?\s*(.+)',
                r'system uses\s+(.+)'
            ]
        }
    
    def execute(self, context: HookContext) -> HookResult:
        """Extract and store learnings from delegation result.
        
        WHY: Capturing learnings immediately after task completion ensures we
        don't lose valuable insights that agents discover during execution.
        """
        try:
            # Check if auto-learning is enabled
            if not self.config.get('memory.auto_learning', False):
                return HookResult(success=True, data=context.data, modified=False)
            
            # Extract agent ID
            agent_name = context.data.get('agent', '')
            if not agent_name:
                return HookResult(success=True, data=context.data, modified=False)
            
            # Normalize agent ID
            agent_id = agent_name.lower().replace(' ', '_').replace('_agent', '').replace('agent', '').strip('_')
            
            # Check if auto-learning is enabled for this specific agent
            agent_overrides = self.config.get('memory.agent_overrides', {})
            agent_config = agent_overrides.get(agent_id, {})
            if 'auto_learning' in agent_config and not agent_config['auto_learning']:
                return HookResult(success=True, data=context.data, modified=False)
            
            # Extract result content
            result = context.data.get('result', {})
            if isinstance(result, dict):
                result_text = result.get('content', '') or str(result)
            else:
                result_text = str(result)
            
            if agent_id and result_text:
                # Extract learnings using patterns
                learnings = self._extract_learnings(result_text)
                
                # Store each learning
                learnings_stored = 0
                for learning_type, items in learnings.items():
                    for item in items:
                        try:
                            self.memory_manager.add_learning(agent_id, learning_type, item)
                            learnings_stored += 1
                        except Exception as e:
                            logger.warning(f"Failed to store learning: {e}")
                
                if learnings_stored > 0:
                    logger.info(f"Extracted {learnings_stored} learnings for agent '{agent_id}'")
                    
                    return HookResult(
                        success=True,
                        data=context.data,
                        modified=False,
                        metadata={
                            'learnings_extracted': learnings_stored,
                            'agent_id': agent_id
                        }
                    )
            
            return HookResult(success=True, data=context.data, modified=False)
                
        except Exception as e:
            logger.error(f"Learning extraction failed: {e}")
            # Don't fail the delegation result if learning extraction fails
            return HookResult(
                success=True,
                data=context.data,
                modified=False,
                error=f"Learning extraction failed: {str(e)}"
            )
    
    def _extract_learnings(self, text: str) -> Dict[str, List[str]]:
        """Extract structured learnings from text.
        
        WHY: We limit learnings to 100 characters to keep memory entries
        concise and actionable. Longer entries tend to be less useful as
        quick reference points.
        
        Args:
            text: The text to extract learnings from
            
        Returns:
            Dictionary mapping learning types to lists of extracted learnings
        """
        learnings = {}
        
        for learning_type, patterns in self.learning_patterns.items():
            learnings[learning_type] = []
            seen_learnings = set()  # Avoid duplicates
            
            for pattern in patterns:
                # Use MULTILINE and IGNORECASE for flexible matching
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    learning = match.group(1).strip()
                    
                    # Clean up the learning
                    # Remove trailing punctuation
                    learning = learning.rstrip('.!?,;')
                    
                    # Skip if too long or too short
                    if learning and 5 < len(learning) < 100:
                        # Normalize for duplicate detection
                        normalized = learning.lower()
                        if normalized not in seen_learnings:
                            learnings[learning_type].append(learning)
                            seen_learnings.add(normalized)
        
        return learnings