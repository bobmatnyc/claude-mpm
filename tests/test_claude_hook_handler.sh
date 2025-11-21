#!/bin/bash
"""
Shell script tests for claude-hook-handler.sh

This test script validates:
- Shell script argument parsing
- Python environment detection
- Error handling and exit codes
- Logging and output redirection
- Environment variable handling

These tests ensure the shell script wrapper correctly sets up
the Python environment and handles errors gracefully.
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results array
declare -a TEST_RESULTS

# Function to run a test
run_test() {
    local test_name="$1"
    local test_function="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    echo -n "Running: $test_name... "

    if $test_function; then
        echo -e "${GREEN}PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        TEST_RESULTS+=("✓ $test_name")
    else
        echo -e "${RED}FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TEST_RESULTS+=("✗ $test_name")
    fi
}

# Setup test environment
setup_test_env() {
    # Create temporary directory for testing
    export TEST_DIR=$(mktemp -d)
    export ORIG_DIR=$(pwd)

    # Create mock claude-mpm structure
    mkdir -p "$TEST_DIR/src/claude_mpm/scripts"
    mkdir -p "$TEST_DIR/src/claude_mpm/hooks/claude_hooks"
    mkdir -p "$TEST_DIR/venv/bin"

    # Copy the actual script to test location
    if [ -f "../src/claude_mpm/scripts/claude-hook-handler.sh" ]; then
        cp "../src/claude_mpm/scripts/claude-hook-handler.sh" "$TEST_DIR/src/claude_mpm/scripts/"
    else
        echo "Error: claude-hook-handler.sh not found"
        exit 1
    fi

    # Make it executable
    chmod +x "$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh"

    # Create mock Python scripts
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo "Mock Python executed"
echo "Args: $@"
exit 0
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    # Create mock hook handler module
    cat > "$TEST_DIR/src/claude_mpm/hooks/claude_hooks/hook_handler.py" << 'EOF'
#!/usr/bin/env python3
import json
import sys
print(json.dumps({"action": "continue"}))
sys.exit(0)
EOF
}

# Cleanup test environment
cleanup_test_env() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Test: Script finds Python in venv
test_find_python_venv() {
    cd "$TEST_DIR"

    # Create venv structure
    mkdir -p venv/bin
    echo '#!/bin/bash' > venv/bin/activate

    # Run script and check if it uses venv Python
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    if echo "$output" | grep -q "Mock Python executed"; then
        return 0
    else
        return 1
    fi
}

# Test: Script finds Python in .venv
test_find_python_dot_venv() {
    cd "$TEST_DIR"

    # Remove venv, create .venv
    rm -rf venv
    mkdir -p .venv/bin
    echo '#!/bin/bash' > .venv/bin/activate
    cp "$TEST_DIR/venv/bin/python" ".venv/bin/python"

    # Run script and check if it uses .venv Python
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    if echo "$output" | grep -q "Mock Python executed"; then
        return 0
    else
        return 1
    fi
}

# Test: Script handles missing Python gracefully
test_missing_python() {
    cd "$TEST_DIR"

    # Remove all Python executables
    rm -rf venv .venv

    # Create a script that simulates python3 not found
    cat > "$TEST_DIR/python3" << 'EOF'
#!/bin/bash
exit 127
EOF
    chmod +x "$TEST_DIR/python3"
    export PATH="$TEST_DIR:$PATH"

    # Run script and check if it returns continue
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    # Should still output continue action
    if echo "$output" | grep -q '{"action": "continue"}'; then
        return 0
    else
        return 1
    fi
}

# Test: PYTHONPATH is set correctly for development
test_pythonpath_development() {
    cd "$TEST_DIR"

    # Modify the mock Python to print PYTHONPATH
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo "PYTHONPATH=$PYTHONPATH"
exit 0
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    # Run script
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    # Check if src is in PYTHONPATH
    if echo "$output" | grep -q "$TEST_DIR/src"; then
        return 0
    else
        return 1
    fi
}

# Test: Debug mode logging
test_debug_logging() {
    cd "$TEST_DIR"

    # Enable debug mode
    export CLAUDE_MPM_HOOK_DEBUG="true"

    # Run script
    "$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1

    # Check if debug log was created
    if [ -f "/tmp/claude-mpm-hook.log" ]; then
        # Check log content
        if grep -q "Claude hook handler starting" /tmp/claude-mpm-hook.log; then
            rm -f /tmp/claude-mpm-hook.log
            return 0
        fi
    fi

    return 1
}

# Test: Socket.IO port configuration
test_socketio_port_config() {
    cd "$TEST_DIR"

    # Set custom port
    export CLAUDE_MPM_SOCKETIO_PORT="9999"

    # Modify mock Python to print environment
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo "SOCKETIO_PORT=$CLAUDE_MPM_SOCKETIO_PORT"
exit 0
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    # Run script
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    # Check if custom port is set
    if echo "$output" | grep -q "SOCKETIO_PORT=9999"; then
        return 0
    else
        return 1
    fi
}

# Test: Error handling - Python module fails
test_python_module_failure() {
    cd "$TEST_DIR"

    # Create failing Python script
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo "Error: Module not found" >&2
exit 1
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    # Run script
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    # Should still output continue action
    if echo "$output" | grep -q '{"action": "continue"}'; then
        # Check error log was created
        if [ -f "/tmp/claude-mpm-hook-error.log" ]; then
            rm -f /tmp/claude-mpm-hook-error.log
            return 0
        fi
    fi

    return 1
}

# Test: Script arguments are passed through
test_argument_passing() {
    cd "$TEST_DIR"

    # Modify mock Python to print arguments
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo "Arguments received: $@"
echo '{"action": "continue"}'
exit 0
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    # Run script with arguments
    output=$("$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" arg1 arg2 arg3 2>&1)

    # Check if arguments were passed
    if echo "$output" | grep -q "arg1 arg2 arg3"; then
        return 0
    else
        return 1
    fi
}

# Test: Script exit code propagation
test_exit_code() {
    cd "$TEST_DIR"

    # Test successful execution (exit 0)
    cat > "$TEST_DIR/venv/bin/python" << 'EOF'
#!/bin/bash
echo '{"action": "continue"}'
exit 0
EOF
    chmod +x "$TEST_DIR/venv/bin/python"

    "$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh"
    if [ $? -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Test: Script handles spaces in paths
test_spaces_in_paths() {
    # Create directory with spaces
    SPACE_DIR="$TEST_DIR/dir with spaces"
    mkdir -p "$SPACE_DIR/src/claude_mpm/scripts"
    cp "$TEST_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" "$SPACE_DIR/src/claude_mpm/scripts/"
    chmod +x "$SPACE_DIR/src/claude_mpm/scripts/claude-hook-handler.sh"

    cd "$SPACE_DIR"

    # Run script from directory with spaces
    output=$("$SPACE_DIR/src/claude_mpm/scripts/claude-hook-handler.sh" 2>&1)

    # Should handle spaces correctly
    if [ $? -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Main test execution
main() {
    echo "========================================="
    echo "Claude Hook Handler Shell Script Tests"
    echo "========================================="
    echo

    # Setup
    setup_test_env

    # Run tests
    run_test "Python detection in venv" test_find_python_venv
    run_test "Python detection in .venv" test_find_python_dot_venv
    run_test "Handle missing Python" test_missing_python
    run_test "PYTHONPATH for development" test_pythonpath_development
    run_test "Debug mode logging" test_debug_logging
    run_test "Socket.IO port configuration" test_socketio_port_config
    run_test "Python module failure handling" test_python_module_failure
    run_test "Argument passing" test_argument_passing
    run_test "Exit code propagation" test_exit_code
    run_test "Spaces in paths" test_spaces_in_paths

    # Cleanup
    cleanup_test_env

    # Summary
    echo
    echo "========================================="
    echo "Test Results Summary"
    echo "========================================="
    echo -e "Tests run: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo
    echo "Detailed Results:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "  $result"
    done
    echo

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

# Run main if executed directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi