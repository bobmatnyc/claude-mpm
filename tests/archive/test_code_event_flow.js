// Test to verify code analysis event flow
// Run this in the browser console when the dashboard is open

console.log("=== Testing Code Analysis Event Flow ===");

// Check if socket is connected
if (!window.socket && !window.socketClient?.socket) {
    console.error("❌ Socket not connected!");
} else {
    const socket = window.socket || window.socketClient.socket;
    console.log("✅ Socket connected");

    // Track events
    const events = [];

    // Listen for all code-related events
    const codeEvents = [
        'code:discover:top_level',
        'code:discover:directory',
        'code:analyze:file',
        'code:directory:discovered',
        'code:file:discovered',
        'code:file:analyzed',
        'code:node:found',
        'code:analysis:start',
        'code:analysis:complete',
        'code:analysis:progress',
        'code:analysis:error'
    ];

    console.log("Setting up event listeners for:", codeEvents);

    codeEvents.forEach(eventName => {
        socket.on(eventName, (data) => {
            const timestamp = new Date().toISOString();
            console.log(`📨 [${timestamp}] ${eventName}:`, data);
            events.push({ eventName, data, timestamp });
        });
    });

    console.log("✅ Event listeners registered");

    // Test function to emit a discovery request
    window.testCodeAnalysis = function(path = '.') {
        console.log(`\n🚀 Emitting code:discover:top_level for path: ${path}`);
        socket.emit('code:discover:top_level', {
            path: path,
            depth: 'top_level'
        });
    };

    // Function to show collected events
    window.showCodeEvents = function() {
        console.log("\n=== Collected Events ===");
        if (events.length === 0) {
            console.log("No events collected yet");
        } else {
            events.forEach((e, i) => {
                console.log(`${i+1}. ${e.eventName} at ${e.timestamp}`);
                console.log("   Data:", e.data);
            });
        }
        return events;
    };

    // Clear events function
    window.clearCodeEvents = function() {
        events.length = 0;
        console.log("Events cleared");
    };

    console.log("\n📋 Available test functions:");
    console.log("- testCodeAnalysis(path) : Emit a discovery request");
    console.log("- showCodeEvents()       : Show collected events");
    console.log("- clearCodeEvents()      : Clear event history");
    console.log("\nYou can also click the Analyze button in the Code tab to test the actual flow.");
}
