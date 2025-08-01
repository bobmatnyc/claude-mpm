"""Memory integration hooks for automatic agent memory management.

WHY: Agents need to accumulate project-specific knowledge over time. These hooks
automatically inject agent memory before delegation and extract learnings after,
enabling agents to become more effective through experience.

DESIGN DECISION: We use explicit markers to extract structured learnings from
agent outputs because:
- It gives agents explicit control over what gets memorized
- The format is clear and unambiguous
- It's more reliable than pattern matching
- Agents can add multiple learnings in a single response
"""

import re
from typing import Dict, Any, List
from claude_mpm.hooks.base_hook import PreDelegationHook, PostDelegationHook, HookContext, HookResult
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.websocket_server import get_server_instance
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
                    
                    # Emit WebSocket event for memory injected
                    try:
                        ws_server = get_server_instance()
                        # Calculate size of injected content
                        injected_size = len(memory_section.encode('utf-8'))
                        ws_server.memory_injected(agent_id, injected_size)
                    except Exception as ws_error:
                        logger.debug(f"WebSocket notification failed: {ws_error}")
                    
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
    """Extract learnings from delegation results using explicit markers.
    
    WHY: Agents produce valuable insights during task execution. This hook
    extracts structured learnings from their outputs using explicit markers,
    building up project-specific knowledge over time.
    
    DESIGN DECISION: We use explicit markers (# Add To Memory: ... #) to give
    agents full control over what gets memorized. This is more reliable than
    pattern matching and allows multiple learnings per response.
    
    Format:
    # Add To Memory:
    Type: pattern
    Content: All services use dependency injection for flexibility
    #
    """
    
    def __init__(self, config: Config = None):
        """Initialize with optional config.
        
        Args:
            config: Optional Config object. If not provided, will create default Config.
        """
        super().__init__(name="memory_post_delegation", priority=80)
        self.config = config or Config()
        self.memory_manager = AgentMemoryManager(self.config)
        
        # Map of supported types to memory sections
        self.type_mapping = {
            'pattern': 'pattern',           # Coding Patterns Learned
            'architecture': 'architecture', # Project Architecture
            'guideline': 'guideline',      # Implementation Guidelines
            'mistake': 'mistake',          # Common Mistakes to Avoid
            'strategy': 'strategy',        # Effective Strategies
            'integration': 'integration',  # Integration Points
            'performance': 'performance',  # Performance Considerations
            'context': 'context'           # Current Technical Context
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
        """Extract structured learnings from text using explicit markers.
        
        WHY: We limit learnings to 100 characters to keep memory entries
        concise and actionable. Longer entries tend to be less useful as
        quick reference points.
        
        DESIGN DECISION: Using explicit markers (# Add To Memory: ... #) gives
        agents full control and makes extraction reliable. We support multiple
        memory additions in a single response.
        
        Args:
            text: The text to extract learnings from
            
        Returns:
            Dictionary mapping learning types to lists of extracted learnings
        """
        learnings = {learning_type: [] for learning_type in self.type_mapping.keys()}
        seen_learnings = set()  # Avoid duplicates
        
        # Pattern to find memory blocks
        # Matches: # Add To Memory:\n...\n#
        # The (?:(?!#\s*Add\s+To\s+Memory:).) ensures we don't match across blocks
        memory_pattern = r'#\s*Add\s+To\s+Memory:\s*\n((?:(?!#\s*Add\s+To\s+Memory:)(?!^\s*#\s*$).)*?)\n\s*#\s*$'
        matches = re.finditer(memory_pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            block_content = match.group(1).strip()
            logger.debug(f"Found memory block: {block_content[:50]}...")
            
            # Extract type and content from the block
            type_match = re.search(r'Type:\s*(\w+)', block_content, re.IGNORECASE)
            content_match = re.search(r'Content:\s*(.+)', block_content, re.IGNORECASE | re.DOTALL)
            
            if type_match and content_match:
                learning_type = type_match.group(1).lower().strip()
                content = content_match.group(1).strip()
                
                # Clean up multi-line content - take first line if multiple
                if '\n' in content:
                    content = content.split('\n')[0].strip()
                
                # Remove trailing punctuation
                content = content.rstrip('.!?,;')
                
                # Validate type is supported
                if learning_type in self.type_mapping:
                    # Check content length (between 5 and 100 characters)
                    if content and 5 < len(content) <= 100:
                        # Normalize for duplicate detection
                        normalized = content.lower()
                        if normalized not in seen_learnings:
                            learnings[learning_type].append(content)
                            seen_learnings.add(normalized)
                            logger.debug(f"Extracted learning - Type: {learning_type}, Content: {content}")
                        else:
                            logger.debug(f"Skipping duplicate learning: {content}")
                    else:
                        logger.debug(f"Skipping learning - invalid length ({len(content)}): {content}")
                else:
                    logger.warning(f"Unsupported learning type: {learning_type}. Supported types: {list(self.type_mapping.keys())}")
            else:
                logger.debug(f"Invalid memory block format - missing Type or Content")
        
        # Log summary of extracted learnings
        total_learnings = sum(len(items) for items in learnings.values())
        if total_learnings > 0:
            logger.info(f"Extracted {total_learnings} learnings from agent response")
            for learning_type, items in learnings.items():
                if items:
                    logger.debug(f"  {learning_type}: {len(items)} items")
        
        return learnings