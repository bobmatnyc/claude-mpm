#!/usr/bin/env python3
"""Test if pexpect is available and working."""

import sys

print("Testing pexpect availability...")

try:
    import pexpect
    print("✓ pexpect is installed")
    print(f"  Version: {pexpect.__version__}")
    print(f"  Location: {pexpect.__file__}")
    
    # Test basic functionality
    print("\nTesting basic pexpect functionality...")
    child = pexpect.spawn('echo "Hello from pexpect"')
    child.expect(pexpect.EOF)
    output = child.before
    print(f"✓ Basic test passed: {output.strip()}")
    
except ImportError as e:
    print("✗ pexpect is NOT installed")
    print(f"  Error: {e}")
    print("\nTo install pexpect:")
    print("  1. Using pipx: brew install pipx && pipx install pexpect")
    print("  2. Using venv: python3 -m venv venv && source venv/bin/activate && pip install pexpect")
    print("  3. Force install: pip install --break-system-packages --user pexpect")
    sys.exit(1)
    
print("\n✓ pexpect is ready to use!")