#!/usr/bin/env python3
"""Test /mpm agents command when no agents are deployed.

WHY: This verifies that the command handles the case gracefully when
no agents have been deployed yet, providing helpful guidance to users.
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def test_no_agents():
    """Test the command when no agents are deployed."""
    print("Testing /mpm agents with no deployed agents")
    print("=" * 60)
    
    # Create a temporary directory to simulate empty deployment
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily set CLAUDE_CONFIG_DIR to the temp directory
        import os
        original_config = os.environ.get('CLAUDE_CONFIG_DIR')
        os.environ['CLAUDE_CONFIG_DIR'] = tmpdir
        
        # Create empty .claude/agents directory
        agents_dir = Path(tmpdir) / '.claude' / 'agents'
        agents_dir.mkdir(parents=True)
        
        try:
            # Test CLI command
            result = subprocess.run(
                [sys.executable, "-m", "claude_mpm.cli", "agents"],
                capture_output=True,
                text=True,
                env=os.environ
            )
            
            print("STDOUT:")
            print(result.stdout)
            print(f"\nReturn code: {result.returncode}")
            
            # Check for expected message
            if "No deployed agents found" in result.stdout:
                print("\n✓ Correctly detected no deployed agents")
            else:
                print("\n✗ Did not show expected 'No deployed agents found' message")
                
            if "claude-mpm --mpm:agents deploy" in result.stdout or "claude-mpm agents deploy" in result.stdout:
                print("✓ Shows helpful deployment instructions")
            else:
                print("✗ Missing deployment instructions")
                
        finally:
            # Restore original environment
            if original_config:
                os.environ['CLAUDE_CONFIG_DIR'] = original_config
            elif 'CLAUDE_CONFIG_DIR' in os.environ:
                del os.environ['CLAUDE_CONFIG_DIR']

if __name__ == "__main__":
    test_no_agents()