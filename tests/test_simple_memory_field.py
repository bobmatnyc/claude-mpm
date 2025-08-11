#!/usr/bin/env python3
"""
Simple test to check if a single agent returns the remember field.
"""

import subprocess
import tempfile
import os
from pathlib import Path

def test_single_agent_remember_field():
    """Test a single agent for remember field presence."""
    project_root = Path(__file__).parent.parent
    
    # Create a simple test prompt that should not generate memories
    prompt = "Please delegate this to the QA agent: Check if there are any Python files in the current directory"
    
    print("Testing QA agent for remember field...")
    print(f"Prompt: {prompt}")
    
    try:
        # Run claude-mpm with the test prompt
        claude_mpm_script = project_root / "claude-mpm"
        cmd = [
            str(claude_mpm_script),
            "run", "-i", prompt, "--non-interactive"
        ]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")
        
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=60,
            env=env,
            cwd=project_root
        )
        
        if process.returncode != 0:
            print(f"❌ Command failed: {process.stderr}")
            return False
            
        response = process.stdout
        print(f"✅ Command succeeded. Response length: {len(response)} chars")
        
        # Look for Remember field
        if "Remember:" in response or "**Remember**:" in response:
            print("✅ Remember field found!")
            
            # Extract the remember field content
            import re
            patterns = [
                r"\*\*Remember\*\*:\s*(.+?)(?=\n\*\*|\n\n|\n$|$)",
                r"Remember:\s*(.+?)(?=\n\*\*|\n\n|\n$|$)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.MULTILINE | re.DOTALL)
                if match:
                    remember_content = match.group(1).strip()
                    print(f"Remember content: {remember_content}")
                    break
            
            return True
        else:
            print("❌ Remember field not found in response")
            print("Response preview:")
            print("-" * 50)
            print(response[:1000] + ("..." if len(response) > 1000 else ""))
            print("-" * 50)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_single_agent_remember_field()
    exit(0 if success else 1)