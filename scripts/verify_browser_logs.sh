#!/bin/bash

echo "====================================="
echo "BROWSER LOGS TAB VERIFICATION"
echo "====================================="
echo ""
echo "This script will help verify that the Browser Logs tab is properly isolated."
echo ""
echo "STEPS TO VERIFY:"
echo "1. Open dashboard: http://localhost:8765"
echo "2. Click on the 'Browser Logs' tab"
echo "3. Verify you see: 'No browser console logs yet'"
echo "4. Switch to 'Events' tab"
echo "5. Verify hook events appear there"
echo ""
echo "EXPECTED BEHAVIOR:"
echo "✅ Browser Logs tab: Shows 'No browser console logs yet' (empty state)"
echo "✅ Events tab: Shows hook events like '[hook] hook.subagent_start'"
echo "❌ Browser Logs tab should NEVER show hook events"
echo ""
echo "To run automated test, paste this in the dashboard console:"
echo ""
cat << 'EOF'
// Quick check
(() => {
    const btn = Array.from(document.querySelectorAll('.tab-button'))
        .find(b => b.getAttribute('data-tab') === 'browser-logs');
    if (btn) {
        btn.click();
        setTimeout(() => {
            const container = document.getElementById('browser-logs-container');
            const hasHooks = container.innerHTML.includes('[hook]');
            const hasEmpty = container.innerHTML.includes('No browser console logs');
            console.log('Browser Logs Tab Status:');
            console.log('- Contains hook events:', hasHooks ? '❌ FAIL' : '✅ PASS');
            console.log('- Shows empty state:', hasEmpty ? '✅ PASS' : '❌ FAIL');
        }, 500);
    }
})();
EOF
echo ""
echo "====================================="