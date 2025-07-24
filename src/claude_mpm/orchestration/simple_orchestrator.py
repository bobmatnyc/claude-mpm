"""Simple orchestrator using Claude's print mode."""

import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

class SimpleOrchestrator:
    """Orchestrator that uses Claude's print mode for each interaction."""
    
    def __init__(self, framework_loader, log_level="OFF"):
        self.framework_loader = framework_loader
        self.log_level = log_level
        self.conversation_id = None
        self.framework_injected = False
        
    def send_message(self, message: str) -> str:
        """Send a message to Claude and get response."""
        
        # Prepare the full message
        if not self.framework_injected:
            # First message includes framework
            framework = self.framework_loader.get_framework_instructions()
            full_message = framework + "\n\nUser: " + message
            self.framework_injected = True
        else:
            full_message = message
        
        # Build command
        cmd = [
            "claude",
            "--model", "opus",
            "--dangerously-skip-permissions",
            "--print",  # Print mode
            full_message
        ]
        
        # If we have a conversation ID, continue it
        if self.conversation_id:
            cmd.extend(["--conversation", self.conversation_id])
        
        # Run Claude
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Claude failed: {result.stderr}")
        
        # Extract conversation ID from output if needed
        # (Claude might output this in stderr or in a specific format)
        
        return result.stdout
    
    def run_interactive(self):
        """Run interactive session using multiple print calls."""
        print("Claude MPM Session (Print Mode)")
        print("Type 'exit' to quit")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                if user_input:
                    print("\nClaude: ", end='', flush=True)
                    response = self.send_message(user_input)
                    print(response)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {e}")
                break
        
        print("\nSession ended")