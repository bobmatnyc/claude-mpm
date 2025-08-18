/**
 * Browser Debug Script for Hook Events
 * 
 * Run this in the browser console while the dashboard is open to:
 * 1. Monitor all incoming socket.io events
 * 2. Send test hook events
 * 3. Check event transformation
 * 4. Identify where hook events are being lost
 * 
 * Usage:
 * 1. Open http://localhost:8765/ in browser
 * 2. Open DevTools (F12) -> Console
 * 3. Paste this entire script and press Enter
 * 4. Watch the console output for debug information
 */

console.log("🔍 Starting Hook Event Debug Session");
console.log("=====================================");

// Store original functions for debugging
const originalConsoleLog = console.log;
const originalConsoleWarn = console.warn;
const originalConsoleError = console.error;

// Enhanced logging
function debugLog(message, data = null) {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, -1);
    if (data) {
        originalConsoleLog(`[${timestamp}] 🔍 ${message}`, data);
    } else {
        originalConsoleLog(`[${timestamp}] 🔍 ${message}`);
    }
}

// Check if required objects exist
if (typeof window.socketClient === 'undefined') {
    console.error("❌ socketClient not found! Make sure dashboard is fully loaded.");
} else {
    debugLog("✅ socketClient found");
}

if (typeof window.eventViewer === 'undefined') {
    console.warn("⚠️ eventViewer not found - may be using new modular system");
} else {
    debugLog("✅ eventViewer found");
}

// Monitor socket.io events
if (window.socketClient && window.socketClient.socket) {
    const socket = window.socketClient.socket;
    
    // Track original event handlers
    const originalHandlers = {};
    
    // Intercept claude_event handler
    const originalClaudeEventHandler = socket._callbacks['$claude_event'] || [];
    debugLog("Original claude_event handlers:", originalClaudeEventHandler.length);
    
    // Add our debug handler
    socket.on('claude_event', function(data) {
        debugLog("📨 Intercepted claude_event:", data);
        
        // Check if it's a hook event
        if (data && (
            (data.type && data.type.startsWith('hook.')) ||
            (data.type === 'hook') ||
            (data.event && data.event.toLowerCase().includes('hook'))
        )) {
            debugLog("🎣 HOOK EVENT DETECTED:", {
                type: data.type,
                subtype: data.subtype,
                event: data.event,
                data: data.data
            });
        }
        
        // Check event transformation
        try {
            const transformedEvent = window.socketClient.transformEvent(data);
            debugLog("🔄 Event after transformation:", transformedEvent);
            
            if (transformedEvent.type === 'hook') {
                debugLog("🎣 TRANSFORMED HOOK EVENT:", {
                    type: transformedEvent.type,
                    subtype: transformedEvent.subtype,
                    originalEventName: transformedEvent.originalEventName
                });
            }
        } catch (error) {
            debugLog("❌ Error in event transformation:", error);
        }
    });
    
    // Monitor other hook-related events
    ['hook.pre', 'hook.post', 'hook.user_prompt', 'hook.pre_tool', 'hook.post_tool'].forEach(eventType => {
        socket.on(eventType, function(data) {
            debugLog(`📨 Received ${eventType}:`, data);
        });
    });
    
    debugLog("✅ Event monitoring set up");
} else {
    console.error("❌ Socket not available for monitoring");
}

// Function to send test hook events
function sendTestHookEvents() {
    if (!window.socketClient || !window.socketClient.socket || !window.socketClient.socket.connected) {
        console.error("❌ Not connected to socket.io server");
        return;
    }
    
    const socket = window.socketClient.socket;
    
    debugLog("🧪 Sending test hook events...");
    
    // Test 1: Standard hook event
    const testHook1 = {
        type: 'hook.user_prompt',
        timestamp: new Date().toISOString(),
        data: {
            prompt: 'Browser debug test 1',
            session_id: 'browser-debug-1'
        }
    };
    
    debugLog("🔬 Sending test 1:", testHook1);
    socket.emit('claude_event', testHook1);
    
    setTimeout(() => {
        // Test 2: Pre-tool hook
        const testHook2 = {
            type: 'hook.pre_tool',
            timestamp: new Date().toISOString(),
            data: {
                tool_name: 'browser_debug_tool',
                session_id: 'browser-debug-2'
            }
        };
        
        debugLog("🔬 Sending test 2:", testHook2);
        socket.emit('claude_event', testHook2);
    }, 1000);
    
    setTimeout(() => {
        // Test 3: Legacy format
        const testHook3 = {
            event: 'UserPrompt',
            timestamp: new Date().toISOString(),
            prompt: 'Browser debug test 3 - legacy',
            session_id: 'browser-debug-3'
        };
        
        debugLog("🔬 Sending test 3:", testHook3);
        socket.emit('claude_event', testHook3);
    }, 2000);
}

// Function to check current events in dashboard
function checkCurrentEvents() {
    let events = [];
    
    // Try to get events from socketClient
    if (window.socketClient && window.socketClient.events) {
        events = window.socketClient.events;
        debugLog(`📊 Total events in socketClient: ${events.length}`);
    }
    
    // Try to get events from eventViewer
    if (window.eventViewer && window.eventViewer.events) {
        events = window.eventViewer.events;
        debugLog(`📊 Total events in eventViewer: ${events.length}`);
    }
    
    // Count hook events
    const hookEvents = events.filter(event => 
        event.type === 'hook' || 
        (event.type && event.type.startsWith('hook.')) ||
        (event.originalEventName && event.originalEventName.includes('hook'))
    );
    
    debugLog(`🎣 Hook events found: ${hookEvents.length}`);
    
    if (hookEvents.length > 0) {
        debugLog("🎣 Hook events details:", hookEvents);
    }
    
    // Check recent events (last 10)
    const recentEvents = events.slice(-10);
    debugLog("📅 Recent events (last 10):", recentEvents.map(e => ({
        type: e.type,
        subtype: e.subtype,
        timestamp: e.timestamp
    })));
    
    return {
        totalEvents: events.length,
        hookEvents: hookEvents.length,
        recentEvents: recentEvents.length
    };
}

// Function to check event filters
function checkEventFilters() {
    if (window.eventViewer) {
        debugLog("🔍 Current filters:", {
            searchFilter: window.eventViewer.searchFilter,
            typeFilter: window.eventViewer.typeFilter,
            sessionFilter: window.eventViewer.sessionFilter
        });
        
        // Check available event types
        const dropdown = document.getElementById('events-type-filter');
        if (dropdown) {
            const options = Array.from(dropdown.options).map(opt => opt.value);
            debugLog("📋 Available event types in dropdown:", options);
            
            const hasHookTypes = options.some(opt => opt.includes('hook'));
            debugLog(`🎣 Hook types in dropdown: ${hasHookTypes}`);
        }
    }
}

// Function to check DOM elements
function checkEventDOMElements() {
    const eventsList = document.getElementById('events-list');
    if (eventsList) {
        const eventElements = eventsList.querySelectorAll('.event-item');
        debugLog(`📋 Event items in DOM: ${eventElements.length}`);
        
        const hookEventElements = Array.from(eventElements).filter(el => {
            const text = el.textContent.toLowerCase();
            return text.includes('hook');
        });
        
        debugLog(`🎣 Hook event items in DOM: ${hookEventElements.length}`);
        
        if (hookEventElements.length > 0) {
            debugLog("🎣 Hook event DOM elements:", hookEventElements);
        }
    }
}

// Run initial checks
debugLog("🔍 Running initial checks...");
checkCurrentEvents();
checkEventFilters();
checkEventDOMElements();

// Set up periodic monitoring
let monitoringInterval = setInterval(() => {
    debugLog("⏰ Periodic check...");
    const stats = checkCurrentEvents();
    
    if (stats.hookEvents > 0) {
        debugLog("✅ Hook events detected! Stopping monitoring.");
        clearInterval(monitoringInterval);
    }
}, 5000);

// Provide functions for manual testing
window.debugHookEvents = {
    sendTest: sendTestHookEvents,
    checkEvents: checkCurrentEvents,
    checkFilters: checkEventFilters,
    checkDOM: checkEventDOMElements,
    stopMonitoring: () => {
        clearInterval(monitoringInterval);
        debugLog("⏹️ Monitoring stopped");
    }
};

// Instructions
debugLog("📋 Debug functions available:");
debugLog("   debugHookEvents.sendTest() - Send test hook events");
debugLog("   debugHookEvents.checkEvents() - Check current events");
debugLog("   debugHookEvents.checkFilters() - Check active filters");
debugLog("   debugHookEvents.checkDOM() - Check DOM elements");
debugLog("   debugHookEvents.stopMonitoring() - Stop periodic monitoring");

debugLog("🚀 Debug setup complete! Monitoring for hook events...");