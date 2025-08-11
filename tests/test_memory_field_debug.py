#!/usr/bin/env python3
"""
Debug test to capture full agent response and analyze remember field.
"""

import subprocess
import os
from pathlib import Path

def debug_agent_response():
    """Capture and analyze full agent response."""
    project_root = Path(__file__).parent.parent
    
    # Create a simple test prompt
    prompt = "Please delegate this to the QA agent: List any Python files in the current directory. This is a simple directory listing task."
    
    print("Debug test for agent remember field...")
    print(f"Prompt: {prompt}")
    
    try:
        claude_mpm_script = project_root / "claude-mpm"
        cmd = [
            str(claude_mpm_script),
            "run", "-i", prompt, "--non-interactive", 
            "--logging", "OFF"  # Reduce noise
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")
        
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120,
            env=env,
            cwd=project_root
        )
        
        print(f"Return code: {process.returncode}")
        
        if process.returncode != 0:
            print(f"STDERR:\n{process.stderr}")
        
        response = process.stdout
        print(f"Response length: {len(response)} chars")
        
        # Save full response to file for analysis
        response_file = project_root / "debug_agent_response.txt"
        with open(response_file, 'w') as f:
            f.write("=== STDOUT ===\n")
            f.write(response)
            f.write("\n\n=== STDERR ===\n")
            f.write(process.stderr)
        
        print(f"Full response saved to: {response_file}")
        
        # Look for various remember patterns
        remember_patterns = [
            "Remember:",
            "**Remember**:",
            '"Remember":',
            "'Remember':",
            "remember field",
            "universal",
            "memory"
        ]
        
        found_patterns = []
        for pattern in remember_patterns:
            if pattern.lower() in response.lower():
                found_patterns.append(pattern)
        
        if found_patterns:
            print(f"✅ Found patterns: {found_patterns}")
        else:
            print("❌ No remember-related patterns found")
        
        # Look for the actual agent response (skip the framework output)
        lines = response.split('\n')
        agent_response_start = -1
        
        for i, line in enumerate(lines):
            if "Task:" in line or "Agent:" in line or "Context:" in line:
                agent_response_start = i
                break
        
        if agent_response_start >= 0:
            agent_response = '\n'.join(lines[agent_response_start:])
            print("\n=== AGENT RESPONSE SECTION ===")
            print(agent_response[-1000:])  # Last 1000 chars
        else:
            print("\n=== FULL RESPONSE (last 1000 chars) ===")
            print(response[-1000:])
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_agent_response()