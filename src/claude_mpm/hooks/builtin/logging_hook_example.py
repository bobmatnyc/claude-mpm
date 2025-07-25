#!/usr/bin/env python3
"""
Example logging hook for Claude MPM.

This hook demonstrates how to capture and log all prompts and responses
through the hook system, providing an alternative to built-in logging.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configure your logging directory
LOG_DIR = Path.home() / ".claude-mpm-hook-logs"
LOG_DIR.mkdir(exist_ok=True)


def execute_pre_delegation_hook(agent: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log task details before delegation.
    
    Args:
        agent: The agent being invoked
        context: Contains 'task' and other context data
    
    Returns:
        Empty dict (no modifications)
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event": "pre_delegation",
        "agent": agent,
        "task": context.get("task", ""),
        "context": context
    }
    
    # Write to daily log file
    log_file = LOG_DIR / f"delegations_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    return {}


def execute_post_delegation_hook(agent: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log complete prompt and response after delegation.
    
    Args:
        agent: The agent that was invoked
        result: Contains task, response, execution_time, tokens
    
    Returns:
        Empty dict (no modifications)
    """
    timestamp = datetime.now().isoformat()
    
    # Extract data
    task = result.get("task", "")
    response = result.get("response", "")
    execution_time = result.get("execution_time", 0)
    tokens = result.get("tokens", 0)
    
    # Create detailed log entry
    log_entry = {
        "timestamp": timestamp,
        "event": "post_delegation",
        "agent": agent,
        "task": task,
        "response_length": len(response),
        "execution_time": execution_time,
        "tokens": tokens,
        "success": not response.startswith("Error:"),
        "response_preview": response[:500] + "..." if len(response) > 500 else response
    }
    
    # Write to agent-specific log
    agent_log_dir = LOG_DIR / "agents" / agent.lower()
    agent_log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = agent_log_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Save full prompt/response if needed
    if os.environ.get("CLAUDE_MPM_HOOK_LOG_FULL", "").lower() == "true":
        # Create unique filename
        task_hash = str(hash(task))[-8:]
        prompt_file = agent_log_dir / f"prompt_{timestamp}_{task_hash}.txt"
        response_file = agent_log_dir / f"response_{timestamp}_{task_hash}.txt"
        
        # Note: We don't have access to the original prompt in post-delegation
        # To capture prompts, you'd need to store them in pre-delegation
        # and match them up using task hash or similar
        
        response_file.write_text(response)
        
        log_entry["response_file"] = str(response_file)
    
    return {}


def execute_submit_hook(prompt: str, session_type: str) -> Dict[str, Any]:
    """
    Log user prompts at session start.
    
    Args:
        prompt: The user's input prompt
        session_type: Type of session (e.g., "subprocess")
    
    Returns:
        Empty dict (no modifications)
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event": "user_submit",
        "session_type": session_type,
        "prompt": prompt,
        "prompt_length": len(prompt)
    }
    
    # Write to session log
    log_file = LOG_DIR / f"sessions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    print(f"[Logging Hook] Logged user prompt to {log_file}")
    
    return {}


# Optional: Hook metadata for registration
HOOK_METADATA = {
    "name": "logging_hook",
    "description": "Comprehensive logging of all prompts and responses",
    "version": "1.0.0",
    "author": "claude-mpm",
    "events": ["pre_delegation", "post_delegation", "submit"],
    "config": {
        "log_dir": str(LOG_DIR),
        "full_logging": os.environ.get("CLAUDE_MPM_HOOK_LOG_FULL", "false")
    }
}


if __name__ == "__main__":
    # Test the hook
    print(f"Logging hook configured to write to: {LOG_DIR}")
    print("Set CLAUDE_MPM_HOOK_LOG_FULL=true to save complete responses")
    
    # Example usage
    execute_submit_hook("Test prompt", "test")
    execute_pre_delegation_hook("Engineer", {"task": "Test task"})
    execute_post_delegation_hook("Engineer", {
        "task": "Test task",
        "response": "Test response",
        "execution_time": 1.5,
        "tokens": 100
    })
    
    print(f"\nCheck logs in: {LOG_DIR}")