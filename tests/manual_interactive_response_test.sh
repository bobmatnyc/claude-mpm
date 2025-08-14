#!/bin/bash

# Manual test for interactive response logging
# This script sets up a configuration with response logging enabled
# and verifies that responses are logged during interactive sessions.

set -e

# Create temporary directory for test
TEST_DIR=$(mktemp -d)
echo "Test directory: $TEST_DIR"

# Create config file with response logging enabled
cat > "$TEST_DIR/config.json" <<EOF
{
  "response_logging": {
    "enabled": true,
    "session_directory": "$TEST_DIR/responses",
    "format": "json",
    "track_all_interactions": true
  }
}
EOF

echo "Created config with response logging enabled"

# Export config path
export CLAUDE_MPM_CONFIG="$TEST_DIR/config.json"

echo ""
echo "Configuration set up. To test interactive response logging:"
echo "1. Run: claude-mpm run"
echo "2. Enter some prompts in the interactive session"
echo "3. Exit the session (Ctrl+D or exit command)"
echo "4. Check for response files in: $TEST_DIR/responses/"
echo ""
echo "To clean up after testing:"
echo "rm -rf $TEST_DIR"
echo ""
echo "Starting interactive session with response logging..."
echo ""

# Start interactive session
claude-mpm run