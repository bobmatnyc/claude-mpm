#!/bin/bash
# Test npm installation locally

echo "=== Testing npm installation flow ==="
echo ""

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
echo "Working in: $TEMP_DIR"
echo ""

# Copy npm package files
cp -r "$OLDPWD/package.json" .
cp -r "$OLDPWD/npm-bin" .
cp -r "$OLDPWD/scripts/postinstall.js" scripts/
cp -r "$OLDPWD/README.npm.md" .

# Mock claude command
mkdir -p bin
echo '#!/bin/bash' > bin/claude
echo 'echo "1.0.60"' >> bin/claude
chmod +x bin/claude
export PATH="$PWD/bin:$PATH"

# Set npm prefix to local directory
export NPM_CONFIG_PREFIX="$TEMP_DIR/npm-global"
mkdir -p "$NPM_CONFIG_PREFIX"

# Install npm package
echo "Installing npm package..."
npm install -g . || echo "npm install failed"
echo ""

# Check installation
echo "Checking npm installation..."
ls -la "$NPM_CONFIG_PREFIX/bin/" || echo "No bin directory"
echo ""

# Try running the wrapper (should trigger Python install)
export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
echo "Testing claude-mpm wrapper..."
claude-mpm --version || echo "Failed to run claude-mpm"
echo ""

# Check if Python package was installed
echo "Checking Python installation..."
pip3 show claude-mpm || echo "Not installed via pip"
echo ""

# Check for hooks
echo "Checking for hook files..."
python3 -c "
try:
    import claude_mpm
    import os
    pkg_dir = os.path.dirname(claude_mpm.__file__)
    hook_dir = os.path.join(pkg_dir, 'hooks', 'claude_hooks')
    print(f'Package location: {pkg_dir}')
    print(f'Hook directory: {hook_dir}')
    if os.path.exists(hook_dir):
        files = os.listdir(hook_dir)
        print(f'Hook files: {files}')
        wrapper = os.path.join(hook_dir, 'hook_wrapper.sh')
        if os.path.exists(wrapper):
            print(f'Hook wrapper exists: {wrapper}')
            print(f'Hook wrapper executable: {os.access(wrapper, os.X_OK)}')
    else:
        print('Hook directory not found')
except ImportError:
    print('claude_mpm not installed')
except Exception as e:
    print(f'Error: {e}')
"

# Cleanup
echo ""
echo "Cleaning up..."
cd /
rm -rf "$TEMP_DIR"

echo "Test complete."