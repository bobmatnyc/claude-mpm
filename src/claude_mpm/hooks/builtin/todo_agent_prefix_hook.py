"""Hook to enforce [Agent] prefix requirement for TodoWrite tool calls."""

import re
from typing import Dict, Any, List, Optional

from claude_mpm.hooks.base_hook import BaseHook, HookContext, HookResult, HookType
from claude_mpm.core.logger import get_logger
from claude_mpm.core.agent_name_normalizer import agent_name_normalizer

logger = get_logger(__name__)


class TodoAgentPrefixHook(BaseHook):
    """Hook that enforces agent name prefixes in TodoWrite tool calls."""
    
    def __init__(self):
        super().__init__(name="todo_agent_prefix_enforcer", priority=20)
        
        # Mapping of task content patterns to appropriate agent prefixes
        self.agent_patterns = {
            'engineer': [
                r'implement', r'code', r'fix', r'refactor', r'debug', r'develop',
                r'create.*function', r'write.*class', r'add.*feature', r'optimize.*code'
            ],
            'research': [
                r'research', r'investigate', r'analyze', r'explore', r'find.*best',
                r'compare', r'evaluate', r'study', r'discover', r'understand'
            ],
            'documentation': [
                r'document', r'write.*doc', r'update.*readme', r'changelog',
                r'create.*guide', r'explain', r'describe', r'write.*tutorial'
            ],
            'qa': [
                r'test', r'validate', r'verify', r'check', r'ensure.*quality',
                r'run.*tests', r'coverage', r'lint', r'audit'
            ],
            'security': [
                r'security', r'vulnerability', r'protect', r'secure', r'audit.*security',
                r'penetration', r'encrypt', r'authenticate', r'authorize'
            ],
            'ops': [
                r'deploy', r'configure', r'setup', r'install', r'provision',
                r'infrastructure', r'ci/cd', r'pipeline', r'monitor'
            ],
            'data_engineer': [
                r'data.*pipeline', r'etl', r'database', r'schema', r'migrate',
                r'transform.*data', r'api.*integration', r'data.*flow'
            ],
            'version_control': [
                r'version', r'release', r'tag', r'branch', r'merge',
                r'git', r'commit', r'push', r'pull'
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for agent, patterns in self.agent_patterns.items():
            self.compiled_patterns[agent] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def execute(self, context: HookContext) -> HookResult:
        """Check and enforce agent prefix in TodoWrite calls."""
        try:
            # This hook is designed to work with tool interception
            # Check if this is a TodoWrite tool call
            if context.hook_type != HookType.CUSTOM:
                return HookResult(success=True, modified=False)
            
            tool_name = context.data.get('tool_name', '')
            if tool_name != 'TodoWrite':
                return HookResult(success=True, modified=False)
            
            # Extract todos from the tool parameters
            tool_params = context.data.get('parameters', {})
            todos = tool_params.get('todos', [])
            
            if not todos:
                return HookResult(success=True, modified=False)
            
            # Check and fix each todo item
            modified = False
            validation_errors = []
            updated_todos = []
            
            for todo in todos:
                content = todo.get('content', '')
                
                # Check if content already has an agent prefix
                if self._has_agent_prefix(content):
                    updated_todos.append(todo)
                    continue
                
                # Try to determine appropriate agent
                suggested_agent = self._suggest_agent(content)
                
                if suggested_agent:
                    # Automatically add the prefix using normalized format
                    prefix = agent_name_normalizer.to_todo_prefix(suggested_agent)
                    todo['content'] = f"{prefix} {content}"
                    updated_todos.append(todo)
                    modified = True
                    logger.info(f"Added '{prefix}' prefix to todo: {content[:50]}...")
                else:
                    # If we can't determine the agent, block the call
                    validation_errors.append(
                        f"Todo item missing required [Agent] prefix: '{content[:50]}...'. "
                        f"Please prefix with one of: [Research], [Engineer], [QA], "
                        f"[Security], [Documentation], [Ops], [Data Engineer], or [Version Control]."
                    )
            
            # If there are validation errors, block the call
            if validation_errors:
                return HookResult(
                    success=False,
                    error="\n".join(validation_errors),
                    metadata={'validation_failed': True}
                )
            
            # If we modified any todos, update the parameters
            if modified:
                tool_params['todos'] = updated_todos
                return HookResult(
                    success=True,
                    data={
                        'tool_name': tool_name,
                        'parameters': tool_params
                    },
                    modified=True,
                    metadata={'prefixes_added': True}
                )
            
            return HookResult(success=True, modified=False)
            
        except Exception as e:
            logger.error(f"Todo agent prefix enforcement failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def _has_agent_prefix(self, content: str) -> bool:
        """Check if content already has an agent prefix."""
        import re
        content = content.strip()
        # Only check for [Agent] prefix at the beginning, not agent mentions in content
        match = re.match(r'^\[([^\]]+)\]', content)
        return match is not None
    
    def _suggest_agent(self, content: str) -> Optional[str]:
        """Suggest an appropriate agent based on content analysis."""
        content_lower = content.lower()
        
        # Check each agent's patterns
        for agent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(content_lower):
                    return agent_name_normalizer.normalize(agent)
        
        # Default suggestions based on common keywords
        if any(word in content_lower for word in ['code', 'implement', 'fix', 'bug']):
            return agent_name_normalizer.normalize('engineer')
        elif any(word in content_lower for word in ['test', 'validate', 'check']):
            return agent_name_normalizer.normalize('qa')
        elif any(word in content_lower for word in ['doc', 'readme', 'guide']):
            return agent_name_normalizer.normalize('documentation')
        elif any(word in content_lower for word in ['research', 'investigate']):
            return agent_name_normalizer.normalize('research')
        
        return None
    
    def validate(self, context: HookContext) -> bool:
        """Validate if hook should run for given context."""
        if not super().validate(context):
            return False
        
        # This hook only runs for CUSTOM type with tool_name = TodoWrite
        return (context.hook_type == HookType.CUSTOM and 
                context.data.get('tool_name') == 'TodoWrite')


class TodoAgentPrefixValidatorHook(BaseHook):
    """Alternative hook that only validates without auto-fixing."""
    
    def __init__(self):
        super().__init__(name="todo_agent_prefix_validator", priority=15)
        # Get valid agents from normalizer
        self.valid_agents = list(agent_name_normalizer.CANONICAL_NAMES.values())
    
    def execute(self, context: HookContext) -> HookResult:
        """Validate agent prefix in TodoWrite calls without auto-fixing."""
        try:
            # Check if this is a TodoWrite tool call
            if context.data.get('tool_name') != 'TodoWrite':
                return HookResult(success=True, modified=False)
            
            # Extract todos
            tool_params = context.data.get('parameters', {})
            todos = tool_params.get('todos', [])
            
            validation_errors = []
            
            for i, todo in enumerate(todos):
                content = todo.get('content', '')
                
                # Check for agent prefix using normalizer
                if not agent_name_normalizer.extract_from_todo(content):
                    validation_errors.append(
                        f"Todo #{i+1} missing required agent prefix. "
                        f"Content: '{content[:50]}...'\n"
                        f"Please use format: '[Agent] Task description' where [Agent] is one of: "
                        f"{', '.join('[' + agent + ']' for agent in self.valid_agents)}"
                    )
            
            if validation_errors:
                return HookResult(
                    success=False,
                    error="\n\n".join(validation_errors),
                    metadata={
                        'validation_type': 'agent_prefix',
                        'valid_agents': self.valid_agents
                    }
                )
            
            return HookResult(success=True, modified=False)
            
        except Exception as e:
            logger.error(f"Todo validation failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def validate(self, context: HookContext) -> bool:
        """Validate if hook should run for given context."""
        if not super().validate(context):
            return False
        
        return (context.hook_type == HookType.CUSTOM and 
                context.data.get('tool_name') == 'TodoWrite')