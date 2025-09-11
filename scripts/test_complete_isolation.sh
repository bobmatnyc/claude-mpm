#!/bin/bash

echo "🧪 Complete Browser Log Isolation Test"
echo "======================================"
echo ""

# Function to trigger hook events
trigger_hook_events() {
    echo "📤 Triggering hook events by running tools..."
    
    # Use claude-mpm to trigger some hook events
    echo "Test hook isolation" > /tmp/test_hook_file.txt
    ls -la /tmp/test_hook_file.txt > /dev/null
    rm -f /tmp/test_hook_file.txt
    
    echo "✅ Hook events triggered"
}

# Function to check dashboard
check_dashboard() {
    echo ""
    echo "📊 Checking dashboard state..."
    
    # Check if browser-log-viewer.js has our fix
    echo -n "  Checking browser-log-viewer.js has fix... "
    if curl -s http://localhost:8765/static/js/components/browser-log-viewer.js | grep -q "CRITICAL: Only accept entries with browser_id"; then
        echo "✅"
    else
        echo "❌"
        echo "  ERROR: Fix not found in browser-log-viewer.js!"
        exit 1
    fi
    
    # Check if server is responding
    echo -n "  Checking server is responding... "
    if curl -s http://localhost:8765/ | grep -q "Claude MPM"; then
        echo "✅"
    else
        echo "❌"
        echo "  ERROR: Server not responding!"
        exit 1
    fi
}

# Main test flow
main() {
    # Check monitor is running
    echo -n "Checking monitor server... "
    if pgrep -f "claude-mpm.*monitor" > /dev/null; then
        echo "✅ Running"
    else
        echo "❌ Not running"
        echo "Starting monitor..."
        ./scripts/claude-mpm --use-venv monitor start &
        sleep 3
    fi
    
    # Trigger events
    trigger_hook_events
    
    # Check dashboard
    check_dashboard
    
    echo ""
    echo "✅ Test complete!"
    echo ""
    echo "MANUAL VERIFICATION STEPS:"
    echo "1. Open http://localhost:8765 in your browser"
    echo "2. Click on 'Browser Logs' tab"
    echo "3. Verify: Should show 'No browser console logs yet'"
    echo "4. Click on 'Events/Hooks' tab"
    echo "5. Verify: Should show hook events from our test"
    echo ""
    echo "Expected result:"
    echo "  ✅ Browser Logs tab: Empty (no hook events)"
    echo "  ✅ Events tab: Contains hook.pre_tool and hook.post_tool events"
}

# Run the test
main