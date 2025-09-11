// Test script to verify Browser Logs tab isolation
// Run this in the dashboard console after it loads

function testBrowserLogsIsolation() {
    console.log("========================================");
    console.log("BROWSER LOGS TAB ISOLATION TEST");
    console.log("========================================");
    
    // Step 1: Check initial state
    console.log("\n1. INITIAL STATE CHECK:");
    console.log("- BrowserLogViewer defined:", typeof BrowserLogViewer !== 'undefined');
    console.log("- browserLogViewer instance:", !!window.browserLogViewer);
    
    // Step 2: Switch to Browser Logs tab
    console.log("\n2. SWITCHING TO BROWSER LOGS TAB...");
    const browserLogsBtn = Array.from(document.querySelectorAll('.tab-button'))
        .find(btn => btn.getAttribute('data-tab') === 'browser-logs');
    
    if (browserLogsBtn) {
        browserLogsBtn.click();
        
        setTimeout(() => {
            // Step 3: Check Browser Logs tab content
            console.log("\n3. BROWSER LOGS TAB CONTENT:");
            const container = document.getElementById('browser-logs-container');
            
            if (container) {
                // Check for contamination
                const eventItems = container.querySelectorAll('.event-item');
                const hookEvents = container.innerHTML.includes('[hook]');
                const logEntries = container.querySelectorAll('.log-entry');
                const emptyState = container.querySelector('.empty-state');
                
                console.log("- Container exists:", true);
                console.log("- Container owner:", container.getAttribute('data-owner'));
                console.log("- Event items found:", eventItems.length, eventItems.length > 0 ? "❌ FAIL" : "✅ PASS");
                console.log("- '[hook]' text found:", hookEvents, hookEvents ? "❌ FAIL" : "✅ PASS");
                console.log("- Log entries found:", logEntries.length);
                console.log("- Empty state shown:", !!emptyState, !emptyState || emptyState.textContent.includes('No browser console logs') ? "✅ PASS" : "❌ FAIL");
                
                // Step 4: Trigger a hook event to test isolation
                console.log("\n4. TRIGGERING TEST HOOK EVENT...");
                if (window.socket) {
                    // Emit a test claude_event that looks like a hook
                    const testHookEvent = {
                        type: 'hook',
                        event_type: 'hook',
                        hook_type: 'subagent_start',
                        message: '[hook] Test hook event - should NOT appear in Browser Logs',
                        timestamp: new Date().toISOString()
                    };
                    
                    // Simulate receiving the event
                    if (window.dashboard && window.dashboard.socketClient) {
                        window.dashboard.socketClient.addEvent(testHookEvent);
                    }
                    
                    setTimeout(() => {
                        // Check if hook event contaminated Browser Logs
                        console.log("\n5. POST-EVENT CONTAMINATION CHECK:");
                        const newEventItems = container.querySelectorAll('.event-item');
                        const newHookText = container.innerHTML.includes('Test hook event');
                        
                        console.log("- Event items after test:", newEventItems.length, newEventItems.length > 0 ? "❌ FAIL - Hook leaked!" : "✅ PASS");
                        console.log("- Test hook text found:", newHookText, newHookText ? "❌ FAIL - Hook leaked!" : "✅ PASS");
                        
                        // Step 5: Switch to Events tab to verify hook appears there
                        console.log("\n6. CHECKING EVENTS TAB...");
                        const eventsBtn = Array.from(document.querySelectorAll('.tab-button'))
                            .find(btn => btn.getAttribute('data-tab') === 'events');
                        
                        if (eventsBtn) {
                            eventsBtn.click();
                            
                            setTimeout(() => {
                                const eventsList = document.getElementById('events-list');
                                if (eventsList) {
                                    const hasTestEvent = eventsList.innerHTML.includes('Test hook event');
                                    console.log("- Test event in Events tab:", hasTestEvent, hasTestEvent ? "✅ PASS" : "❌ FAIL");
                                }
                                
                                // Final results
                                console.log("\n========================================");
                                console.log("TEST COMPLETE");
                                console.log("Browser Logs tab should show ONLY browser console logs");
                                console.log("Hook events should appear ONLY in Events tab");
                                console.log("========================================");
                            }, 500);
                        }
                    }, 1000);
                }
            } else {
                console.error("Browser logs container not found!");
            }
        }, 500);
    } else {
        console.error("Browser Logs tab button not found!");
    }
}

// Auto-run test after a delay
setTimeout(testBrowserLogsIsolation, 2000);
console.log("Browser Logs Isolation Test will run in 2 seconds...");