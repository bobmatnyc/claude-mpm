"""Example of how to integrate hooks into orchestrator methods."""

from typing import Optional
from ..hooks.hook_client import HookServiceClient


class HookIntegrationExample:
    """Example methods showing how to integrate hooks into orchestrators."""
    
    def __init__(self, hook_client: Optional[HookServiceClient] = None):
        """Initialize with optional hook client."""
        self.hook_client = hook_client
    
    def process_user_input_with_hooks(self, user_input: str) -> str:
        """Process user input through submit hooks before sending to Claude.
        
        This method shows how to:
        1. Send user input to hook service
        2. Get modified input back
        3. Use the modified input for Claude
        """
        if not self.hook_client:
            # No hooks available, return original input
            return user_input
        
        try:
            # Execute submit hooks
            results = self.hook_client.execute_submit_hook(
                prompt=user_input,
                session_id="current_session"
            )
            
            # Get modified data from hooks
            modified_data = self.hook_client.get_modified_data(results)
            
            # Use modified prompt if available
            if modified_data.get('prompt'):
                return modified_data['prompt']
            
            # Check for priority changes
            if modified_data.get('priority'):
                # Could adjust Claude model or other settings based on priority
                print(f"Priority set by hooks: {modified_data['priority']}")
            
            return user_input
            
        except Exception as e:
            print(f"Hook processing failed: {e}")
            # Fallback to original input
            return user_input
    
    def process_agent_delegation_with_hooks(self, agent_name: str, task: str) -> tuple[str, str]:
        """Process agent delegation through pre-delegation hooks.
        
        Returns:
            Tuple of (agent_name, task) potentially modified by hooks
        """
        if not self.hook_client:
            return agent_name, task
        
        try:
            # Execute pre-delegation hooks
            context = {
                'agent': agent_name,
                'task': task
            }
            
            results = self.hook_client.execute_pre_delegation_hook(
                agent=agent_name,
                context=context
            )
            
            # Get modified data
            modified_data = self.hook_client.get_modified_data(results)
            
            # Update agent or task if modified
            new_agent = modified_data.get('agent', agent_name)
            new_context = modified_data.get('context', {})
            new_task = new_context.get('task', task)
            
            return new_agent, new_task
            
        except Exception as e:
            print(f"Pre-delegation hook failed: {e}")
            return agent_name, task
    
    def process_agent_response_with_hooks(self, agent_name: str, response: str) -> str:
        """Process agent response through post-delegation hooks.
        
        Returns:
            Potentially modified response
        """
        if not self.hook_client:
            return response
        
        try:
            # Execute post-delegation hooks
            result = {
                'response': response,
                'success': True
            }
            
            results = self.hook_client.execute_post_delegation_hook(
                agent=agent_name,
                result=result
            )
            
            # Get modified data
            modified_data = self.hook_client.get_modified_data(results)
            
            # Use modified response if available
            if modified_data.get('result', {}).get('response'):
                return modified_data['result']['response']
            
            return response
            
        except Exception as e:
            print(f"Post-delegation hook failed: {e}")
            return response
    
    def extract_tickets_with_hooks(self, conversation: str) -> list:
        """Extract tickets from conversation using ticket extraction hooks.
        
        Returns:
            List of extracted tickets
        """
        if not self.hook_client:
            return []
        
        try:
            # Execute ticket extraction hooks
            results = self.hook_client.execute_ticket_extraction_hook(
                content={'conversation': conversation}
            )
            
            # Get extracted tickets
            tickets = self.hook_client.get_extracted_tickets(results)
            
            return tickets
            
        except Exception as e:
            print(f"Ticket extraction hook failed: {e}")
            return []


# Example of integrating into an existing orchestrator method
def example_orchestrator_run_method(self, user_input: str):
    """Example of how to modify an existing orchestrator run method."""
    
    # Process input through hooks if available
    if self.hook_client:
        user_input = self.process_user_input_with_hooks(user_input)
    
    # Continue with normal orchestration
    # ... existing orchestrator code ...
    
    # When delegating to agents
    if needs_delegation:
        agent_name = "Engineer"
        task = "Implement the feature"
        
        # Process through pre-delegation hooks
        if self.hook_client:
            agent_name, task = self.process_agent_delegation_with_hooks(agent_name, task)
        
        # Perform delegation
        response = self.delegate_to_agent(agent_name, task)
        
        # Process response through post-delegation hooks
        if self.hook_client:
            response = self.process_agent_response_with_hooks(agent_name, response)
    
    # Extract tickets from the conversation
    if self.hook_client:
        conversation = f"User: {user_input}\nAssistant: {response}"
        tickets = self.extract_tickets_with_hooks(conversation)
        for ticket in tickets:
            print(f"Extracted ticket: {ticket['title']}")