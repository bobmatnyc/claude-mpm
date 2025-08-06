#!/bin/bash
echo "=== Testing npm-installed claude-mpm ==="
echo ""
echo "1. Node version: $(node --version)"
echo "2. NPM version: $(npm --version)"
echo "3. Python version: $(python3 --version)"
echo "4. Claude version: $(claude --version 2>/dev/null || echo "Not found")"
echo ""
echo "5. Check npm global bin:"
ls -la /home/testuser/.npm-global/bin/ || echo "Directory not found"
echo ""
echo "6. PATH contents:"
echo $PATH
echo ""
echo "7. Try running claude-mpm wrapper (should install Python package):"
/home/testuser/.npm-global/bin/claude-mpm --version || echo "Failed to run"
echo ""
echo "8. Check if Python package was installed:"
pip3 show claude-mpm || echo "Not installed via pip"
pipx list 2>/dev/null | grep claude-mpm || echo "Not installed via pipx"
echo ""
echo "9. Find Python claude-mpm location:"
which claude-mpm || echo "Not in PATH"
ls -la /home/testuser/.local/bin/claude-mpm 2>/dev/null || echo "Not in .local/bin"
echo ""
echo "10. Check for hook files after installation:"
if [ -f "/home/testuser/.local/bin/claude-mpm" ]; then
    echo "Found claude-mpm, checking for hooks..."
    python3 -c "import sys; sys.path.insert(0, '/home/testuser/.local/lib/python3.11/site-packages'); import claude_mpm; import os; pkg_dir = os.path.dirname(claude_mpm.__file__); hook_dir = os.path.join(pkg_dir, 'hooks', 'claude_hooks'); print(f'Hook dir: {hook_dir}'); print(f'Exists: {os.path.exists(hook_dir)}'); print(f'Files: {os.listdir(hook_dir) if os.path.exists(hook_dir) else []}')"
else
    echo "claude-mpm not found, cannot check hooks"
fi
echo ""
echo "11. Test hook installation:"
if command -v claude-mpm &> /dev/null; then
    # Create a test Python script to run install_hooks
    cat > /tmp/test_hooks.py << "EOF"
import subprocess
import sys
try:
    # Try to import and find install_hooks.py
    result = subprocess.run([sys.executable, "-m", "claude_mpm.scripts.install_hooks"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Hook installation script ran successfully")
        print(result.stdout)
    else:
        print("✗ Hook installation script failed")
        print(result.stderr)
except Exception as e:
    print(f"✗ Could not run install_hooks: {e}")
EOF
    python3 /tmp/test_hooks.py
else
    echo "claude-mpm not available, cannot test hook installation"
fi