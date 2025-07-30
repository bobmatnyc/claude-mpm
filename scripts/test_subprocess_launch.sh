#!/bin/bash
# Test subprocess launch method

echo "Testing subprocess launch method..."
echo "exit" | ./claude-mpm run --launch-method subprocess --no-native-agents