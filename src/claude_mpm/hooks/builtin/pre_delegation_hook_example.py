"""Example pre-delegation hook implementation."""

import json
from typing import Dict, Any, List

from claude_mpm.hooks.base_hook import PreDelegationHook, HookContext, HookResult
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class ContextFilterHook(PreDelegationHook):
    """Hook that filters sensitive information from context before delegation."""
    
    def __init__(self):
        super().__init__(name="context_filter", priority=10)
        self.sensitive_keys = {
            'api_key', 'secret', 'password', 'token',
            'private_key', 'credentials', 'auth'
        }
        
    def execute(self, context: HookContext) -> HookResult:
        """Filter sensitive information from delegation context."""
        try:
            agent_context = context.data.get('context', {})
            filtered_context = self._filter_sensitive(agent_context)
            
            if filtered_context != agent_context:
                logger.info("Filtered sensitive information from context")
                return HookResult(
                    success=True,
                    data={
                        'agent': context.data.get('agent'),
                        'context': filtered_context
                    },
                    modified=True,
                    metadata={'filtered_keys': True}
                )
            else:
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False
                )
                
        except Exception as e:
            logger.error(f"Context filtering failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
            
    def _filter_sensitive(self, data: Any) -> Any:
        """Recursively filter sensitive keys from data."""
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_keys):
                    filtered[key] = "[REDACTED]"
                else:
                    filtered[key] = self._filter_sensitive(value)
            return filtered
        elif isinstance(data, list):
            return [self._filter_sensitive(item) for item in data]
        else:
            return data


class AgentCapabilityEnhancerHook(PreDelegationHook):
    """Hook that enhances agent context with additional capabilities."""
    
    def __init__(self):
        super().__init__(name="capability_enhancer", priority=30)
        self.agent_enhancements = {
            'engineer': {
                'tools': ['code_analysis', 'refactoring', 'testing'],
                'context': 'You have access to advanced code analysis tools.'
            },
            'researcher': {
                'tools': ['web_search', 'document_analysis'],
                'context': 'You can search the web and analyze documents.'
            },
            'qa': {
                'tools': ['test_runner', 'coverage_analyzer'],
                'context': 'You have access to comprehensive testing tools.'
            }
        }
        
    def execute(self, context: HookContext) -> HookResult:
        """Enhance agent capabilities based on agent type."""
        try:
            agent_type = context.data.get('agent', '').lower()
            
            if agent_type in self.agent_enhancements:
                enhancement = self.agent_enhancements[agent_type]
                
                # Add enhancements to context
                enhanced_context = context.data.get('context', {}).copy()
                enhanced_context['additional_tools'] = enhancement['tools']
                enhanced_context['enhanced_context'] = enhancement['context']
                
                logger.info(f"Enhanced {agent_type} agent with additional capabilities")
                
                return HookResult(
                    success=True,
                    data={
                        'agent': context.data.get('agent'),
                        'context': enhanced_context
                    },
                    modified=True,
                    metadata={'enhancements_applied': True}
                )
            else:
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False
                )
                
        except Exception as e:
            logger.error(f"Capability enhancement failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )