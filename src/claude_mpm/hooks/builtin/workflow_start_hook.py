"""Hook to log workflow information at the start of execution."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult, HookType
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)


class WorkflowStartHook(SubmitHook):
    """Hook that logs workflow information including steps list at workflow start."""
    
    def __init__(self):
        super().__init__(name="workflow_start_logger", priority=5)
    
    def execute(self, context: HookContext) -> HookResult:
        """Log workflow information when a workflow starts."""
        try:
            # Extract prompt and workflow data from context
            prompt = context.data.get('prompt', '')
            workflow_data = context.data.get('workflow', {})
            
            # Check if this is a workflow start (either by explicit workflow data or detected pattern)
            if workflow_data or self._is_workflow_prompt(prompt):
                # Extract workflow information
                workflow_name = workflow_data.get('name', 'Unnamed Workflow')
                workflow_steps = workflow_data.get('steps', [])
                
                # If no explicit steps provided, try to parse from prompt
                if not workflow_steps and prompt:
                    workflow_steps = self._extract_steps_from_prompt(prompt)
                
                # Log workflow start information
                logger.info("="*60)
                logger.info("WORKFLOW START")
                logger.info("="*60)
                logger.info(f"Workflow: {workflow_name}")
                logger.info(f"Started at: {context.timestamp.isoformat()}")
                logger.info(f"Session ID: {context.session_id or 'N/A'}")
                logger.info(f"User ID: {context.user_id or 'N/A'}")
                
                if workflow_steps:
                    logger.info(f"\nWorkflow Steps ({len(workflow_steps)} total):")
                    for i, step in enumerate(workflow_steps, 1):
                        if isinstance(step, dict):
                            step_name = step.get('name', step.get('description', 'Unnamed step'))
                            step_type = step.get('type', 'task')
                            logger.info(f"  {i}. [{step_type}] {step_name}")
                        else:
                            # Handle simple string steps
                            logger.info(f"  {i}. {step}")
                else:
                    logger.info("\nNo explicit workflow steps defined")
                
                # Log additional metadata if present
                metadata = workflow_data.get('metadata', {})
                if metadata:
                    logger.info(f"\nWorkflow Metadata:")
                    for key, value in metadata.items():
                        logger.info(f"  {key}: {value}")
                
                logger.info("="*60)
                
                # Add workflow info to result metadata for downstream hooks
                return HookResult(
                    success=True,
                    modified=False,
                    metadata={
                        'workflow_logged': True,
                        'workflow_name': workflow_name,
                        'step_count': len(workflow_steps),
                        'has_explicit_workflow': bool(workflow_data)
                    }
                )
            
            # Not a workflow start, pass through
            return HookResult(success=True, modified=False)
            
        except Exception as e:
            logger.error(f"Workflow start logging failed: {e}")
            # Don't block execution on logging errors
            return HookResult(
                success=True,
                modified=False,
                error=str(e)
            )
    
    def _is_workflow_prompt(self, prompt: str) -> bool:
        """Detect if a prompt indicates a workflow start."""
        if not prompt:
            return False
        
        prompt_lower = prompt.lower()
        workflow_indicators = [
            'workflow', 'steps:', 'step 1', 'first,', 'then,', 'finally,',
            'process:', 'procedure:', 'sequence:', 'plan:'
        ]
        
        return any(indicator in prompt_lower for indicator in workflow_indicators)
    
    def _extract_steps_from_prompt(self, prompt: str) -> List[str]:
        """Try to extract workflow steps from a prompt text."""
        steps = []
        
        # Look for numbered steps (1. 2. 3. or 1) 2) 3))
        import re
        numbered_pattern = re.compile(r'^\s*\d+[\)\.]\s*(.+)$', re.MULTILINE)
        matches = numbered_pattern.findall(prompt)
        if matches:
            steps.extend(matches)
            return steps
        
        # Look for bullet points
        bullet_pattern = re.compile(r'^\s*[-*•]\s*(.+)$', re.MULTILINE)
        matches = bullet_pattern.findall(prompt)
        if matches:
            steps.extend(matches)
            return steps
        
        # Look for sequential keywords
        sequential_pattern = re.compile(
            r'(?:first|then|next|after that|finally|lastly),?\s*(.+?)(?=(?:first|then|next|after that|finally|lastly|$))',
            re.IGNORECASE | re.DOTALL
        )
        matches = sequential_pattern.findall(prompt)
        if matches:
            steps.extend([m.strip() for m in matches if m.strip()])
        
        return steps
    
    def validate(self, context: HookContext) -> bool:
        """Validate if hook should run for given context."""
        if not super().validate(context):
            return False
        
        # This hook runs for all submit contexts to check for workflows
        return context.hook_type == HookType.SUBMIT


class WorkflowStepLogger(SubmitHook):
    """Alternative hook that logs individual workflow step execution."""
    
    def __init__(self):
        super().__init__(name="workflow_step_logger", priority=6)
    
    def execute(self, context: HookContext) -> HookResult:
        """Log individual workflow step execution."""
        try:
            # Check if this is a workflow step execution
            step_data = context.data.get('workflow_step', {})
            if not step_data:
                return HookResult(success=True, modified=False)
            
            # Extract step information
            step_number = step_data.get('number', 0)
            step_name = step_data.get('name', 'Unnamed step')
            step_type = step_data.get('type', 'task')
            workflow_name = step_data.get('workflow_name', 'Unknown workflow')
            
            # Log step execution
            logger.info(f"\n→ Executing Step {step_number}: {step_name}")
            logger.info(f"  Type: {step_type}")
            logger.info(f"  Workflow: {workflow_name}")
            logger.info(f"  Started: {context.timestamp.isoformat()}")
            
            return HookResult(
                success=True,
                modified=False,
                metadata={
                    'step_logged': True,
                    'step_number': step_number,
                    'step_name': step_name
                }
            )
            
        except Exception as e:
            logger.error(f"Workflow step logging failed: {e}")
            return HookResult(success=True, modified=False, error=str(e))