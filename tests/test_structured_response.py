#!/usr/bin/env python3
"""
Test agent structured response format including remember field.
"""

import subprocess
import os
import tempfile
from pathlib import Path

def test_structured_agent_response():
    """Test if agents return structured responses with remember field."""
    project_root = Path(__file__).parent.parent
    
    # Create a complex task that should generate a structured response
    prompt = """Please delegate this to the QA agent: 

Analyze the testing approach in this project and provide a comprehensive QA assessment. 
Look at the test files, identify testing patterns, and recommend universal quality standards 
that should apply to all future testing in this codebase.

This task should generate both analysis and universal memory items about testing standards."""
    
    print("Testing structured agent response...")
    print(f"Task involves analysis that should generate universal testing patterns")
    
    try:
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
            timeout=180,  # Longer timeout for complex task
            env=env,
            cwd=project_root
        )
        
        print(f"Return code: {process.returncode}")
        
        if process.returncode != 0:
            print(f"Command failed: {process.stderr}")
            return False
        
        response = process.stdout
        print(f"Response length: {len(response)} chars")
        
        # Save response for analysis
        response_file = project_root / "structured_response_test.txt"
        with open(response_file, 'w') as f:
            f.write("=== FULL RESPONSE ===\n")
            f.write(response)
            f.write("\n\n=== STDERR ===\n")
            f.write(process.stderr)
        
        print(f"Full response saved to: {response_file}")
        
        # Check for structured response elements
        structure_indicators = [
            "## Summary",
            "**Task Completed**",
            "**Approach**",
            "**Test Results**",
            "**Remember**:",
            "Remember:",
            "**QA Sign-off**",
            "QA Complete:"
        ]
        
        found_structure = []
        for indicator in structure_indicators:
            if indicator in response:
                found_structure.append(indicator)
        
        print(f"Found structure indicators: {found_structure}")
        
        # Look specifically for remember field
        remember_found = any(
            indicator in response 
            for indicator in ["**Remember**:", "Remember:"]
        )
        
        if remember_found:
            print("✅ Remember field found in structured response!")
            
            # Extract remember field content
            import re
            patterns = [
                r"\*\*Remember\*\*:\s*(.+?)(?=\n\*\*|\n\n|$)",
                r"Remember:\s*(.+?)(?=\n\*\*|\n\n|$)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.MULTILINE | re.DOTALL)
                if match:
                    remember_content = match.group(1).strip()
                    print(f"Remember content: {remember_content}")
                    
                    # Check if it's properly formatted
                    if remember_content.lower() in ["null", "none", "[]"] or remember_content.startswith("-") or remember_content.startswith("["):
                        print("✅ Remember field properly formatted")
                        return True
                    else:
                        print(f"⚠️ Remember field may be improperly formatted: {remember_content}")
                        return True  # Still found, just format issue
                    
        else:
            print("❌ Remember field not found")
            
            # Show the actual response structure
            print("\n=== RESPONSE STRUCTURE ANALYSIS ===")
            lines = response.split('\n')
            for i, line in enumerate(lines[-50:], max(0, len(lines)-50)):
                if line.strip():
                    print(f"{i:3d}: {line[:100]}")
            
            return False
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_structured_agent_response()
    exit(0 if success else 1)