#!/bin/bash
# Test script to verify agent response logging

echo "================================================"
echo "AGENT RESPONSE LOGGING TEST"
echo "================================================"

# Enable debug mode for hooks
export CLAUDE_MPM_HOOK_DEBUG=true

# Create a test prompt that will delegate to an agent
TEST_PROMPT="Please delegate this to the research agent: analyze the current project structure and list the main components"

echo ""
echo "1. Running test delegation..."
echo "   Prompt: $TEST_PROMPT"
echo ""

# Run the command with claude-mpm
./claude-mpm run -i "$TEST_PROMPT" --non-interactive 2>&1 | tee /tmp/agent_test_output.log

echo ""
echo "2. Checking for response files..."
echo ""

# Wait a moment for files to be written
sleep 2

# Check for recent response files
RESPONSE_DIR=".claude-mpm/responses"
if [ -d "$RESPONSE_DIR" ]; then
    echo "   Recent response files (last 5):"
    ls -lt "$RESPONSE_DIR"/*.json 2>/dev/null | head -5 | while read line; do
        echo "   $line"
    done

    # Check for files created in the last minute
    echo ""
    echo "   Files created in last 60 seconds:"
    find "$RESPONSE_DIR" -name "*.json" -mtime -1m -type f 2>/dev/null | while read file; do
        basename=$(basename "$file")
        # Check if it contains agent-related content
        if grep -q "research\|engineer\|documentation\|subagent" "$file" 2>/dev/null; then
            echo "   ✅ $basename (contains agent data)"
            echo "      Agent: $(jq -r '.agent' "$file" 2>/dev/null)"
            echo "      Has request: $(jq -r 'has("request")' "$file" 2>/dev/null)"
            echo "      Has response: $(jq -r 'has("response")' "$file" 2>/dev/null)"
        else
            echo "   - $basename"
        fi
    done
else
    echo "   ❌ Response directory not found"
fi

echo ""
echo "3. Checking hook handler debug output..."
echo ""

# Check if debug output shows response tracking
if grep -q "Tracked.*agent response\|Tracked.*Claude response" /tmp/agent_test_output.log 2>/dev/null; then
    echo "   ✅ Hook handler tracked responses:"
    grep "Tracked.*response" /tmp/agent_test_output.log | head -5
else
    echo "   ⚠️ No response tracking messages found in output"
    echo "   (This could mean debug mode is off or tracking failed)"
fi

echo ""
echo "================================================"
echo "TEST COMPLETE"
echo "================================================"
echo ""
echo "To manually verify:"
echo "1. Check .claude-mpm/responses/ for new JSON files"
echo "2. Look for files with 'research', 'engineer', etc. in agent field"
echo "3. Enable debug with: export CLAUDE_MPM_HOOK_DEBUG=true"
echo "4. Run claude-mpm interactively and delegate to agents"
echo ""
