"""Example post-delegation hook implementation."""

import json
import re
from typing import Dict, Any, List

from claude_mpm.hooks.base_hook import PostDelegationHook, HookContext, HookResult
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class ResultValidatorHook(PostDelegationHook):
    """Hook that validates agent results for quality and completeness."""
    
    def __init__(self):
        super().__init__(name="result_validator", priority=10)
        
    def execute(self, context: HookContext) -> HookResult:
        """Validate agent results."""
        try:
            result = context.data.get('result', {})
            agent = context.data.get('agent', 'unknown')
            
            # Validation checks
            issues = []
            
            # Check for empty results
            if not result:
                issues.append("Empty result returned")
                
            # Check for error indicators
            error_patterns = ['error', 'failed', 'exception', 'traceback']
            result_str = json.dumps(result).lower()
            for pattern in error_patterns:
                if pattern in result_str and 'success' not in result:
                    issues.append(f"Result contains '{pattern}' indicator")
                    
            # Agent-specific validation
            if agent.lower() == 'engineer' and 'code' in str(result):
                # Check for code quality indicators
                if 'todo' in result_str or 'fixme' in result_str:
                    issues.append("Code contains TODO/FIXME comments")
                    
            if issues:
                logger.warning(f"Validation issues found: {issues}")
                return HookResult(
                    success=True,
                    data={
                        'result': result,
                        'validation_issues': issues
                    },
                    modified=True,
                    metadata={'issues_count': len(issues)}
                )
            else:
                return HookResult(
                    success=True,
                    data=context.data,
                    modified=False,
                    metadata={'validated': True}
                )
                
        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )


class ResultMetricsHook(PostDelegationHook):
    """Hook that collects metrics from agent results."""
    
    def __init__(self):
        super().__init__(name="result_metrics", priority=50)
        
    def execute(self, context: HookContext) -> HookResult:
        """Collect metrics from agent results."""
        try:
            result = context.data.get('result', {})
            agent = context.data.get('agent', 'unknown')
            execution_time = context.metadata.get('execution_time_ms', 0)
            
            # Collect metrics
            metrics = {
                'agent': agent,
                'execution_time_ms': execution_time,
                'result_size_bytes': len(json.dumps(result).encode()),
                'timestamp': context.timestamp.isoformat()
            }
            
            # Agent-specific metrics
            if agent.lower() == 'engineer':
                # Count code-related metrics
                code_content = str(result)
                metrics['lines_of_code'] = code_content.count('\n')
                metrics['functions_created'] = len(re.findall(r'def\s+\w+', code_content))
                metrics['classes_created'] = len(re.findall(r'class\s+\w+', code_content))
                
            elif agent.lower() == 'qa':
                # Count test-related metrics
                test_content = str(result)
                metrics['tests_count'] = len(re.findall(r'test_\w+', test_content))
                metrics['assertions_count'] = len(re.findall(r'assert\s+', test_content))
                
            logger.info(f"Collected metrics: {metrics}")
            
            return HookResult(
                success=True,
                data={
                    'result': result,
                    'metrics': metrics
                },
                modified=True,
                metadata=metrics
            )
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )