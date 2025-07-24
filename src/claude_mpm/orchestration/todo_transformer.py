"""TODO Transformer - Converts Claude TODOs into PM delegations."""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger


class TodoTransformer:
    """
    Transforms Claude's TODO items into PM agent delegations.
    
    This class analyzes TODO content to:
    - Determine the appropriate agent type
    - Extract task description
    - Create proper delegation format
    - Map keywords to agent specializations
    """
    
    # Agent keyword mappings
    AGENT_KEYWORDS = {
        'engineer': {
            'keywords': ['code', 'implement', 'function', 'class', 'api', 'develop', 
                        'create', 'build', 'write', 'script', 'algorithm',
                        'refactor', 'optimize code', 'debug', 'fix bug'],
            'agent': 'Engineer',
            'priority': 8
        },
        'qa': {
            'keywords': ['unit test', 'unit tests', 'integration test', 'test', 'testing', 
                        'validate', 'verify', 'check', 'quality', 'qa', 'coverage', 
                        'pytest', 'assertion', 'mock', 'fixture'],
            'agent': 'QA',
            'priority': 9
        },
        'documentation': {
            'keywords': ['api documentation', 'document', 'docs', 'readme', 'changelog', 
                        'comment', 'docstring', 'documentation', 'guide', 'tutorial', 
                        'explain', 'description', 'wiki', 'manual'],
            'agent': 'Documentation',
            'priority': 9
        },
        'research': {
            'keywords': ['research', 'investigate', 'analyze', 'study', 'explore',
                        'find out', 'look into', 'understand', 'learn', 'compare',
                        'evaluate', 'assess', 'review'],
            'agent': 'Research',
            'priority': 5
        },
        'security': {
            'keywords': ['security', 'vulnerability', 'auth', 'authorization',
                        'authentication', 'encrypt', 'decrypt', 'permission',
                        'access control', 'token', 'password', 'secure'],
            'agent': 'Security',
            'priority': 9
        },
        'ops': {
            'keywords': ['deploy', 'deployment', 'ci/cd', 'pipeline', 'docker',
                        'kubernetes', 'container', 'infrastructure', 'devops',
                        'build', 'release', 'publish', 'package'],
            'agent': 'Ops',
            'priority': 4
        },
        'version_control': {
            'keywords': ['git branch', 'git', 'branch', 'merge', 'commit', 'version', 'tag',
                        'release', 'cherry-pick', 'rebase', 'pull request',
                        'github', 'gitlab'],
            'agent': 'Version Control',
            'priority': 7
        },
        'data_engineer': {
            'keywords': ['database', 'data', 'sql', 'query', 'migration', 'schema',
                        'table', 'index', 'api integration', 'openai', 'claude api',
                        'data pipeline', 'etl', 'analytics', 'redis', 'mongodb'],
            'agent': 'Data Engineer',
            'priority': 7
        }
    }
    
    def __init__(self):
        """Initialize the transformer."""
        self.logger = get_logger("todo_transformer")
    
    def transform_todo(self, todo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a TODO item into a delegation.
        
        Args:
            todo: TODO item from Claude
            
        Returns:
            Delegation dict with agent and task, or None if not transformable
        """
        # Skip completed TODOs
        if todo.get("status") == "completed" or todo.get("done", False):
            self.logger.debug("Skipping completed TODO")
            return None
            
        # Extract task content
        task_content = self._extract_task_content(todo)
        if not task_content:
            self.logger.debug("No task content found in TODO")
            return None
        
        # Determine agent and priority
        agent, confidence = self._determine_agent(task_content)
        
        # Skip low-confidence matches
        if confidence < 0.1:
            self.logger.debug(f"Low confidence ({confidence:.2f}) for task: {task_content[:50]}...")
            return None
        
        # Create delegation
        delegation = {
            'agent': agent,
            'task': task_content,
            'source': 'todo_hijacker',
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'todo_id': self._get_todo_id(todo)
        }
        
        # Add priority if available
        if 'priority' in todo:
            delegation['priority'] = todo['priority']
        
        # Add any labels or tags
        if 'labels' in todo:
            delegation['labels'] = todo['labels']
        elif 'tags' in todo:
            delegation['labels'] = todo['tags']
        
        return delegation
    
    def _extract_task_content(self, todo: Dict[str, Any]) -> Optional[str]:
        """
        Extract the task description from a TODO item.
        
        Args:
            todo: TODO item
            
        Returns:
            Task description string or None
        """
        # Try different content fields
        content = todo.get('content') or todo.get('task') or todo.get('description')
        
        if not content:
            # Try to build from title and body
            title = todo.get('title', '')
            body = todo.get('body', '')
            if title or body:
                content = f"{title}\n{body}".strip()
        
        return content if content else None
    
    def _determine_agent(self, task_content: str) -> Tuple[str, float]:
        """
        Determine the appropriate agent for a task.
        
        Args:
            task_content: Task description
            
        Returns:
            Tuple of (agent_name, confidence_score)
        """
        import re
        
        task_lower = task_content.lower()
        
        # Score each agent type
        agent_scores = []
        
        for agent_type, config in self.AGENT_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            # Check keywords (check longer ones first for better matching)
            sorted_keywords = sorted(config['keywords'], key=len, reverse=True)
            for keyword in sorted_keywords:
                # Use word boundary matching for single words
                if ' ' in keyword:
                    # Multi-word keywords - exact phrase match
                    if keyword in task_lower:
                        weight = len(keyword.split()) * 0.5 + 1.0
                        score += weight
                        matched_keywords.append(keyword)
                else:
                    # Single word - check word boundaries
                    if re.search(r'\b' + re.escape(keyword) + r'\b', task_lower):
                        weight = 1.0
                        score += weight
                        matched_keywords.append(keyword)
            
            # Only add if keywords were matched
            if score > 0 and matched_keywords:
                # Base score on number of matched keywords, not total keywords
                normalized_score = len(matched_keywords) / 3.0  # Expect ~3 keywords for high confidence
                # Apply priority boost
                normalized_score *= (config['priority'] / 10.0)
                
                agent_scores.append({
                    'agent': config['agent'],
                    'score': normalized_score,
                    'matched': matched_keywords
                })
        
        # Sort by score
        agent_scores.sort(key=lambda x: x['score'], reverse=True)
        
        if agent_scores:
            best_match = agent_scores[0]
            # Calculate confidence based on score and number of matches
            confidence = min(best_match['score'], 1.0)
            
            if len(best_match['matched']) > 0:
                self.logger.debug(f"Matched '{best_match['agent']}' with keywords: {best_match['matched']}")
            
            return best_match['agent'], confidence
        
        # Default to Engineer if no clear match
        return 'Engineer', 0.3
    
    def _get_todo_id(self, todo: Dict[str, Any]) -> str:
        """Generate a unique ID for tracking."""
        if 'id' in todo:
            return str(todo['id'])
        
        content = todo.get('content') or todo.get('task') or ''
        return str(hash(content))
    
    def transform_pm_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a PM ticket format into a delegation.
        
        This handles tickets extracted by the PM from responses.
        
        Args:
            ticket: PM ticket dict
            
        Returns:
            Delegation dict
        """
        # PM tickets typically have type and title
        task_content = ticket.get('title', '')
        if ticket.get('description'):
            task_content += f"\n{ticket['description']}"
        
        # Use ticket type to help determine agent
        ticket_type = ticket.get('type', '').lower()
        
        # Map ticket types to agents
        type_mapping = {
            'feature': 'Engineer',
            'bug': 'Engineer',
            'test': 'QA',
            'docs': 'Documentation',
            'research': 'Research',
            'security': 'Security',
            'deployment': 'Ops',
            'infrastructure': 'Ops',
            'data': 'Data Engineer'
        }
        
        # Try type mapping first
        agent = None
        for key, mapped_agent in type_mapping.items():
            if key in ticket_type:
                agent = mapped_agent
                break
        
        # Fall back to content analysis
        if not agent:
            agent, confidence = self._determine_agent(task_content)
        else:
            confidence = 0.8  # High confidence from explicit type
        
        return {
            'agent': agent,
            'task': task_content,
            'source': 'pm_ticket',
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'ticket_type': ticket.get('type'),
            'ticket_id': ticket.get('id')
        }
    
    def batch_transform(self, todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple TODOs into delegations.
        
        Args:
            todos: List of TODO items
            
        Returns:
            List of delegation dicts
        """
        delegations = []
        
        for todo in todos:
            delegation = self.transform_todo(todo)
            if delegation:
                delegations.append(delegation)
        
        # Sort by confidence and priority
        delegations.sort(
            key=lambda d: (d.get('priority', 5), d.get('confidence', 0)),
            reverse=True
        )
        
        return delegations