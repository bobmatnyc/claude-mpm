#!/usr/bin/env python3
"""Test using pexpect for terminal interaction."""

try:
    import pexpect
except ImportError:
    print("pexpect not installed. Install with: pip install pexpect")
    exit(1)

import sys

def test_pexpect_claude():
    """Test Claude with pexpect."""
    print("Testing Claude with pexpect...")
    
    # Start Claude
    child = pexpect.spawn('claude --model opus --dangerously-skip-permissions')
    child.logfile = sys.stdout.buffer
    
    try:
        # Wait for prompt
        child.expect('>', timeout=5)
        
        # Send a message
        child.sendline('Say "Hello from pexpect"')
        
        # Wait for response
        child.expect('>', timeout=30)
        
        # Send exit
        child.sendline('exit')
        child.expect(pexpect.EOF)
        
    except pexpect.TIMEOUT:
        print("\nTimeout waiting for Claude")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        child.close()

if __name__ == "__main__":
    test_pexpect_claude()