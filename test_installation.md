# Claude MPM v4.2.34 Installation Test Suite

## Quick Installation Verification

### 1. Basic Installation Check
```bash
# Check if claude-mpm is installed and get version
claude-mpm --version

# Expected output: Should show version 4.2.34
```

### 2. Help Command Test
```bash
# Verify help is accessible
claude-mpm --help

# Expected: Should display all available commands
```

## Core Functionality Tests

### 3. Agent Discovery Test
```bash
# List all available agents
claude-mpm agents list

# Expected: Should show 22+ agents including:
# - engineer
# - qa
# - research
# - documentation
# - security
# - ops
```

### 4. Simple Agent Execution Test
Create a test file `/tmp/test_simple.txt`:
```
What is 2 + 2?
```

Run with Research agent:
```bash
claude-mpm run -i /tmp/test_simple.txt research --non-interactive

# Expected: Should execute and provide answer
```

### 5. PM (Project Manager) Test
```bash
# Test the PM orchestration
echo "Help me understand what claude-mpm is" | claude-mpm run

# Expected: PM should delegate to appropriate agents
```

## Monitor/Dashboard Tests

### 6. Monitor Status Check
```bash
# Check monitor status
claude-mpm monitor status

# Expected: Should show monitor status (running/stopped)
```

### 7. Dashboard Start Test (if port 8765 is free)
```bash
# Try starting dashboard
claude-mpm dashboard start

# Expected: Either starts successfully or reports port conflict
# If successful, visit http://localhost:8765
```

### 8. Monitor with Agent Execution
```bash
# Run agent with monitoring enabled
echo "What is Python?" | claude-mpm run --monitor research

# Expected: Should execute with monitoring (may fail if port busy)
```

## Configuration Tests

### 9. Configuration Check
```bash
# Show current configuration
claude-mpm config show

# Expected: Should display configuration settings
```

### 10. Doctor Diagnostic Test
```bash
# Run diagnostic checks
claude-mpm doctor

# Expected: Should show system health status
```

## Advanced Tests

### 11. Interactive Mode Test
```bash
# Start interactive session
claude-mpm run

# Type: "exit" to quit
# Expected: Should start interactive prompt
```

### 12. Memory System Test
```bash
# Check memory system
claude-mpm memory list

# Expected: Should show available memory files
```

### 13. Multiple Agent Test
Create `/tmp/test_complex.txt`:
```
Research Python best practices, then create a simple hello world script
```

```bash
claude-mpm run -i /tmp/test_complex.txt

# Expected: PM should coordinate multiple agents
```

## Troubleshooting Common Issues

### Issue 1: Port 8765 Already in Use
If you see: "ERROR: Port 8765 is already in use"

Solution:
```bash
# Check what's using the port
lsof -i :8765

# Kill monitor processes if needed
pkill -f "claude-mpm.*monitor"
pkill -f "socketio_daemon"

# Or run without monitor
claude-mpm run -i /tmp/test.txt research --non-interactive
```

### Issue 2: Module Import Errors
If you see import errors:

```bash
# Reinstall the package
pip uninstall claude-mpm
pip install claude-mpm==4.2.34

# Or with pipx
pipx uninstall claude-mpm
pipx install claude-mpm==4.2.34
```

### Issue 3: Claude Code Not Detected
If output styles aren't working:

```bash
# Check Claude Code version
claude-mpm doctor

# Should show Claude Code version >= 1.0.83
```

## Expected Success Indicators

✅ **Successful Installation:**
- Version shows 4.2.34
- Agents list shows 22+ agents
- Help command displays all options
- Doctor command shows no critical issues

✅ **Successful Execution:**
- Agents respond to queries
- PM delegates work appropriately  
- Non-interactive mode completes without hanging
- Output is formatted and readable

✅ **Optional Features (may fail due to port conflicts):**
- Monitor starts if port 8765 is free
- Dashboard accessible at http://localhost:8765
- Real-time event streaming works

## Quick Validation Script

Save this as `validate_install.sh`:

```bash
#!/bin/bash

echo "=== Claude MPM Installation Validation ==="
echo

echo "1. Version Check:"
claude-mpm --version
echo

echo "2. Agent Count:"
claude-mpm agents list | grep -c "^  •" || echo "0 agents found"
echo

echo "3. Simple Test:"
echo "What is 2+2?" | claude-mpm run research --non-interactive | head -20
echo

echo "4. Configuration:"
claude-mpm config show | head -5
echo

echo "5. Doctor Check:"
claude-mpm doctor | grep -E "(✅|❌|⚠️)" | head -10
echo

echo "=== Validation Complete ==="
```

Run with:
```bash
chmod +x validate_install.sh
./validate_install.sh
```

## Notes for Testing

1. **Port Conflicts**: The monitor feature uses port 8765. If Chrome or another process is using it, the monitor will fail but core functionality should still work.

2. **First Run**: The first run may take longer as it loads agents and deploys output styles.

3. **Pipx vs Pip**: If installed with pipx, the package runs in an isolated environment. If installed with pip, it uses the system Python environment.

4. **Output Styles**: These only work with Claude Code >= 1.0.83. Check with `claude-mpm doctor`.

5. **Background Processes**: Some tests may leave background processes running. Use `pkill -f claude-mpm` to clean up if needed.

## Report Issues

If any tests fail unexpectedly, report the issue with:
- The test that failed
- The error message
- Output of `claude-mpm doctor`
- Installation method (pip/pipx)
- Python version (`python --version`)