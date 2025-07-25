"""Agent delegation for Claude MPM."""

import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

try:
    from ..core.logger import get_logger
    from ..core.agent_registry import AgentRegistryAdapter
except ImportError:
    from core.logger import get_logger
    from core.agent_registry import AgentRegistryAdapter


class AgentDelegator:
    """
    Handle agent delegation patterns in Claude output.
    
    This component:
    1. Detects delegation patterns (e.g., "Delegate to Engineer: ...")
    2. Formats proper Task Tool delegations
    3. Tracks delegated tasks
    """
    
    # Delegation patterns
    DELEGATION_PATTERNS = [
        # Explicit delegation
        (re.compile(r'Delegate to (\w+):\s*(.+)', re.IGNORECASE), 'explicit'),
        (re.compile(r'→\s*(\w+) Agent:\s*(.+)', re.IGNORECASE), 'arrow'),
        (re.compile(r'Task for (\w+):\s*(.+)', re.IGNORECASE), 'task_for'),
        # Implicit patterns that suggest delegation
        (re.compile(r'(\w+) Agent should:\s*(.+)', re.IGNORECASE), 'should'),
        (re.compile(r'Ask (\w+) to:\s*(.+)', re.IGNORECASE), 'ask'),
    ]
    
    def __init__(self, agent_registry: Optional[AgentRegistryAdapter] = None):
        """
        Initialize the agent delegator.
        
        Args:
            agent_registry: Agent registry adapter
        """
        self.logger = get_logger("agent_delegator")
        self.agent_registry = agent_registry
        self.delegated_tasks: List[Dict[str, Any]] = []
    
    def extract_delegations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract agent delegations from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of delegation dictionaries
        """
        delegations = []
        
        for line in text.splitlines():
            delegation = self._extract_from_line(line)
            if delegation:
                delegations.append(delegation)
                self.delegated_tasks.append(delegation)
        
        return delegations
    
    def _extract_from_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Extract delegation from a single line.
        
        Args:
            line: Line to analyze
            
        Returns:
            Delegation dictionary or None
        """
        for pattern, pattern_type in self.DELEGATION_PATTERNS:
            match = pattern.search(line)
            if match:
                agent_name = match.group(1).lower()
                task = match.group(2).strip()
                
                # Normalize agent names
                agent_name = self._normalize_agent_name(agent_name)
                
                return {
                    'agent': agent_name,
                    'task': task,
                    'pattern_type': pattern_type,
                    'raw_line': line,
                    'timestamp': datetime.now().isoformat(),
                }
        
        return None
    
    def _normalize_agent_name(self, name: str) -> str:
        """
        Normalize agent name to standard form.
        
        Args:
            name: Raw agent name
            
        Returns:
            Normalized name
        """
        # Common aliases
        aliases = {
            'doc': 'documentation',
            'docs': 'documentation',
            'documenter': 'documentation',
            'eng': 'engineer',
            'dev': 'engineer',
            'developer': 'engineer',
            'test': 'qa',
            'testing': 'qa',
            'quality': 'qa',
            'researcher': 'research',
            'investigate': 'research',
            'devops': 'ops',
            'operations': 'ops',
            'sec': 'security',
            'git': 'version-control',
            'vcs': 'version-control',
            'versioner': 'version-control',
            'data': 'data-engineer',
            'database': 'data-engineer',
        }
        
        name_lower = name.lower().strip()
        return aliases.get(name_lower, name_lower)
    
    def format_task_tool_delegation(self, agent: str, task: str, context: str = "") -> str:
        """
        Format a proper Task Tool delegation.
        
        Args:
            agent: Agent name
            task: Task description
            context: Additional context
            
        Returns:
            Formatted Task Tool prompt
        """
        if self.agent_registry:
            return self.agent_registry.format_agent_for_task_tool(agent, task, context)
        
        # Fallback formatting
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""**{agent.title()} Agent**: {task}

TEMPORAL CONTEXT: Today is {today}.

**Task**: {task}

**Context**: {context}

**Expected Results**: Completed task with deliverables"""
    
    def suggest_agent_for_task(self, task: str) -> Optional[str]:
        """
        Suggest an appropriate agent for a task.
        
        Args:
            task: Task description
            
        Returns:
            Suggested agent name or None
        """
        task_lower = task.lower()
        
        # Keywords to agent mapping
        keyword_mapping = {
            'documentation': ['document', 'docs', 'readme', 'changelog', 'docstring'],
            'engineer': ['implement', 'code', 'develop', 'create', 'build', 'fix bug'],
            'qa': ['test', 'validate', 'verify', 'quality', 'coverage'],
            'research': ['investigate', 'research', 'analyze', 'explore', 'find out'],
            'ops': ['deploy', 'install', 'setup', 'configure', 'infrastructure'],
            'security': ['security', 'vulnerability', 'auth', 'permission', 'encrypt'],
            'version-control': ['git', 'branch', 'merge', 'commit', 'tag', 'version'],
            'data-engineer': ['database', 'data', 'migration', 'schema', 'api integration'],
        }
        
        # Check keywords
        for agent, keywords in keyword_mapping.items():
            if any(keyword in task_lower for keyword in keywords):
                self.logger.debug(f"Suggested {agent} for task: {task}")
                return agent
        
        # Use agent registry if available
        if self.agent_registry:
            selected = self.agent_registry.select_agent_for_task(task)
            if selected:
                return selected['metadata'].get('type', 'engineer')
        
        # Default to engineer
        return 'engineer'
    
    def get_delegation_summary(self) -> Dict[str, int]:
        """
        Get summary of delegated tasks by agent.
        
        Returns:
            Dictionary with agent task counts
        """
        summary = {}
        for task in self.delegated_tasks:
            agent = task['agent']
            summary[agent] = summary.get(agent, 0) + 1
        
        return summary
    
    def clear(self):
        """Clear delegated tasks."""
        self.delegated_tasks.clear()