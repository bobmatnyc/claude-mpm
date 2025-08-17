#!/usr/bin/env python3
"""Interactive wrapper for Claude MPM that intercepts /mpm: commands."""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import SimpleClaudeRunner


def main():
    """Run interactive Claude session with command interception."""
    # Initialize runner
    runner = SimpleClaudeRunner()
    
    print("\033[32m╭───────────────────────────────────────────────────╮\033[0m")
    print("\033[32m│\033[0m ✻ Claude MPM - Interactive Wrapper                \033[32m│\033[0m")
    print("\033[32m│                                                   │\033[0m")
    print("\033[32m│\033[0m   Type '/mpm:test' to test MPM commands           \033[32m│\033[0m")
    print("\033[32m│\033[0m   Type '/agents' to see available agents          \033[32m│\033[0m")
    print("\033[32m│\033[0m   Type 'exit' to quit                             \033[32m│\033[0m")
    print("\033[32m╰───────────────────────────────────────────────────╯\033[0m")
    print("")
    
    # Setup agents
    runner.setup_agents()
    
    # Build base Claude command
    cmd_base = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
    
    # Add system prompt
    system_prompt = runner._create_system_prompt()
    if system_prompt:
        cmd_base.extend(["--append-system-prompt", system_prompt])
    
    # Interactive loop
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Check for /mpm: commands
            if user_input.startswith("/mpm:"):
                # Handle command directly
                success = runner._handle_mpm_command(user_input)
                if not success:
                    print("Command failed.")
                continue
            
            # Add to conversation history
            conversation_history.append(f"Human: {user_input}")
            
            # Build full prompt with conversation history
            full_prompt = "\n\n".join(conversation_history)
            
            # Send to Claude
            cmd = cmd_base + ["--print", full_prompt]
            
            # Run Claude and capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Extract just the assistant's response (after the last "Assistant:")
                if "Assistant:" in response:
                    response_parts = response.split("Assistant:")
                    assistant_response = response_parts[-1].strip()
                else:
                    assistant_response = response
                
                print(f"\nAssistant: {assistant_response}")
                
                # Add to conversation history
                conversation_history.append(f"Assistant: {assistant_response}")
                
                # Keep conversation history manageable (last 10 exchanges)
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]
                
                # Extract tickets if enabled
                if runner.enable_tickets and runner.ticket_manager:
                    runner._extract_tickets(assistant_response)
            else:
                print(f"\nError: {result.stderr.strip()}")
                
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()