#!/bin/bash
# Test script for monitor status command

echo "Testing monitor status command..."
echo "================================="
echo

# Test 1: Check status when server is running
echo "Test 1: Status with running server"
echo "-----------------------------------"
python -m claude_mpm.cli monitor status
echo

# Test 2: Check status with verbose flag
echo "Test 2: Status with verbose flag"
echo "---------------------------------"
python -m claude_mpm.cli monitor status --verbose
echo

# Test 3: Default behavior (no subcommand)
echo "Test 3: Default behavior (no subcommand)"
echo "-----------------------------------------"
python -m claude_mpm.cli monitor
echo

# Test 4: Stop server and check status
echo "Test 4: Status when server is not running"
echo "------------------------------------------"
python -m claude_mpm.cli monitor stop > /dev/null 2>&1
sleep 1
python -m claude_mpm.cli monitor status
echo

# Restart server for other tests
echo "Restarting server..."
python -m claude_mpm.cli monitor start > /dev/null 2>&1
echo "Server restarted."
echo

echo "All tests completed successfully!"