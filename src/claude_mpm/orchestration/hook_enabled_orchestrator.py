"""Example orchestrator that integrates with the hook service."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.hooks.hook_client import get_hook_client, HookServiceClient
from src.hooks.base_hook import HookType
from src.orchestration.orchestrator import Orchestrator
from src.services.ticket_manager import TicketManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HookEnabledOrchestrator(Orchestrator):
    """Orchestrator that integrates with the centralized hook service."""
    
    def __init__(self, *args, **kwargs):
        """Initialize hook-enabled orchestrator."""
        super().__init__(*args, **kwargs)
        
        # Initialize hook client
        self.hook_client = get_hook_client()
        
        # Check hook service health
        health = self.hook_client.health_check()
        if health.get('status') == 'healthy':
            logger.info(f"Hook service is healthy with {health.get('hooks_count', 0)} hooks")
        else:
            logger.warning(f"Hook service is not available: {health.get('error')}")
            
    async def process_prompt(self, prompt: str) -> str:
        """Process user prompt with hook integration.
        
        Args:
            prompt: User prompt to process
            
        Returns:
            Response from orchestration
        """
        try:
            # Execute submit hooks
            logger.debug("Executing submit hooks...")
            submit_results = self.hook_client.execute_submit_hook(
                prompt=prompt,
                session_id=getattr(self, 'session_id', None)
            )
            
            # Get modified prompt data
            modified_data = self.hook_client.get_modified_data(submit_results)
            if modified_data.get('prompt'):
                prompt = modified_data['prompt']
                
            # Check for priority override
            if modified_data.get('priority'):
                logger.info(f"Priority detected: {modified_data['priority']}")
                
            # Process prompt through normal orchestration
            response = await super().process_prompt(prompt)
            
            # Execute ticket extraction hooks on the conversation
            logger.debug("Executing ticket extraction hooks...")
            extraction_results = self.hook_client.execute_ticket_extraction_hook(
                content={
                    'prompt': prompt,
                    'response': response
                }
            )
            
            # Extract and create tickets
            tickets = self.hook_client.get_extracted_tickets(extraction_results)
            if tickets:
                logger.info(f"Extracted {len(tickets)} tickets from conversation")
                await self._create_tickets(tickets)
                
            return response
            
        except Exception as e:
            logger.error(f"Error in hook-enabled orchestration: {e}")
            # Fallback to normal orchestration if hooks fail
            return await super().process_prompt(prompt)
            
    async def delegate_to_agent(self, agent_name: str, context: Dict[str, Any]) -> Any:
        """Delegate to agent with hook integration.
        
        Args:
            agent_name: Name of agent to delegate to
            context: Context to pass to agent
            
        Returns:
            Result from agent
        """
        try:
            # Execute pre-delegation hooks
            logger.debug(f"Executing pre-delegation hooks for {agent_name}...")
            pre_results = self.hook_client.execute_pre_delegation_hook(
                agent=agent_name,
                context=context
            )
            
            # Get modified context
            modified_data = self.hook_client.get_modified_data(pre_results)
            if 'context' in modified_data:
                context = modified_data['context']
                logger.debug("Context modified by pre-delegation hooks")
                
            # Delegate to agent
            result = await super().delegate_to_agent(agent_name, context)
            
            # Execute post-delegation hooks
            logger.debug(f"Executing post-delegation hooks for {agent_name}...")
            post_results = self.hook_client.execute_post_delegation_hook(
                agent=agent_name,
                result=result,
                execution_time_ms=context.get('execution_time_ms')
            )
            
            # Get modified result
            modified_data = self.hook_client.get_modified_data(post_results)
            if 'result' in modified_data:
                result = modified_data['result']
                logger.debug("Result modified by post-delegation hooks")
                
            # Check for validation issues
            for post_result in post_results:
                if 'validation_issues' in post_result.get('data', {}):
                    issues = post_result['data']['validation_issues']
                    logger.warning(f"Validation issues: {issues}")
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in hook-enabled delegation: {e}")
            # Fallback to normal delegation if hooks fail
            return await super().delegate_to_agent(agent_name, context)
            
    async def _create_tickets(self, tickets: List[Dict[str, Any]]):
        """Create tickets in the ticket system.
        
        Args:
            tickets: List of ticket dictionaries
        """
        try:
            # Initialize ticket manager if needed
            if not hasattr(self, 'ticket_manager'):
                self.ticket_manager = TicketManager()
                
            for ticket in tickets:
                try:
                    # Create ticket
                    ticket_id = await self.ticket_manager.create_ticket(
                        title=ticket.get('title', 'Untitled'),
                        description=ticket.get('description', ''),
                        priority=ticket.get('priority', 'normal'),
                        ticket_type=ticket.get('type', 'task'),
                        metadata=ticket.get('metadata', {})
                    )
                    logger.info(f"Created ticket {ticket_id}: {ticket['title']}")
                except Exception as e:
                    logger.error(f"Failed to create ticket: {e}")
                    
        except Exception as e:
            logger.error(f"Error creating tickets: {e}")


# Example usage
async def main():
    """Example usage of hook-enabled orchestrator."""
    # Create orchestrator
    orchestrator = HookEnabledOrchestrator()
    
    # Process some prompts
    prompts = [
        "URGENT: Fix the bug in the login system",
        "TODO: Add unit tests for the new API endpoints",
        "Can you create ticket: Implement user dashboard feature",
        "Research the best practices for React performance optimization"
    ]
    
    for prompt in prompts:
        print(f"\nProcessing: {prompt}")
        response = await orchestrator.process_prompt(prompt)
        print(f"Response: {response[:100]}...")
        
        
if __name__ == "__main__":
    asyncio.run(main())