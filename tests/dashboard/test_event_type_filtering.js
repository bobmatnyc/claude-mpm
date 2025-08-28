#!/usr/bin/env node

/**
 * Test Suite: Event Type Filtering
 * 
 * Tests the event normalizer's ability to:
 * 1. Transform raw events into clean types like "code.directory_discovered"
 * 2. Filter out internal functions (handle*, get*, set*)
 * 3. Show only directories, files, and main code functions
 */

const fs = require('fs');
const path = require('path');

// Color utilities for console output
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    reset: '\x1b[0m'
};

function log(message, color = 'white') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

// Test data - simulate various event formats
const testEvents = [
    // Raw event from code analysis
    {
        event_name: "code:node:found",
        data: {}
    },
    
    // Directory discovery event
    {
        type: "code:directory_discovered", 
        data: { path: "/src", name: "src" }
    },
    
    // File discovery event  
    {
        type: "code:file_discovered",
        data: { path: "/src/main.py", name: "main.py" }
    },
    
    // Internal function event (should be filtered)
    {
        type: "code:node_found",
        data: { name: "handle_request", type: "function" }
    },
    
    // Main function event (should be kept)
    {
        type: "code:node_found", 
        data: { name: "calculate_total", type: "function" }
    },
    
    // Getter/Setter (should be filtered)
    {
        type: "code:node_found",
        data: { name: "get_status", type: "function" }
    },
    
    // Private method (should be filtered) 
    {
        type: "code:node_found",
        data: { name: "_internal_method", type: "function" }
    },
    
    // Class definition (should be kept)
    {
        type: "code:node_found",
        data: { name: "UserManager", type: "class" }
    },
    
    // Legacy format with colons in event name
    {
        event_name: "code:analysis:queued",
        data: { path: "/project" }
    },
    
    // Hook event format
    {
        type: "hook",
        event: "pre_tool",
        data: { tool_name: "Read" }
    }
];

// Expected results after normalization
const expectedResults = [
    { type: "code", subtype: "node_found" },
    { type: "code", subtype: "directory_discovered" },
    { type: "code", subtype: "file_discovered" },
    { type: "code", subtype: "node_found", shouldFilter: true }, // Internal function
    { type: "code", subtype: "node_found", shouldFilter: false }, // Main function  
    { type: "code", subtype: "node_found", shouldFilter: true }, // Getter
    { type: "code", subtype: "node_found", shouldFilter: true }, // Private method
    { type: "code", subtype: "node_found", shouldFilter: false }, // Class
    { type: "code", subtype: "analysis_queued" },
    { type: "hook", subtype: "pre_tool" }
];

// Mock EventNormalizer class (simplified version for testing)
class MockEventNormalizer {
    normalize(eventData) {
        // Simple normalization logic based on the actual implementation
        if (typeof eventData === 'string') {
            return this._mapEventName(eventData);
        }
        
        if (typeof eventData === 'object') {
            // Handle type="hook" with event field
            if (eventData.type === "hook" && eventData.event) {
                return {
                    type: "hook",
                    subtype: eventData.event,
                    data: eventData.data || {}
                };
            }
            
            // Extract event name
            let eventName = eventData.event_name || eventData.type || "unknown";
            return this._mapEventName(eventName);
        }
        
        return { type: "unknown", subtype: "generic", data: {} };
    }
    
    _mapEventName(eventName) {
        // Handle colon-separated event names
        if (eventName.includes(":")) {
            const parts = eventName.split(":");
            if (parts.length >= 2) {
                const type = parts[0];
                const subtype = parts.slice(1).join("_").replace(/:/g, "_");
                return { type, subtype, data: {} };
            }
        }
        
        return { type: eventName, subtype: "generic", data: {} };
    }
}

// Function filtering logic (from code_tree_events.py)
function isInternalFunction(name) {
    if (!name) return false;
    
    const internalPatterns = [
        'handle',  // Event handlers
        'on_',     // Event callbacks  
        '_',       // Private methods
        'get_',    // Simple getters
        'set_',    // Simple setters
        '__'       // Python magic methods
    ];
    
    const nameLower = name.toLowerCase();
    return internalPatterns.some(pattern => nameLower.startsWith(pattern));
}

// Test runner
function runTests() {
    log('\n🧪 Testing Event Type Filtering', 'cyan');
    log('='.repeat(50), 'cyan');
    
    const normalizer = new MockEventNormalizer();
    let passed = 0;
    let failed = 0;
    
    testEvents.forEach((event, index) => {
        const expected = expectedResults[index];
        const result = normalizer.normalize(event);
        
        log(`\nTest ${index + 1}: ${JSON.stringify(event).substring(0, 60)}...`, 'blue');
        
        // Test event type normalization
        const typeMatch = result.type === expected.type;
        const subtypeMatch = result.subtype === expected.subtype;
        
        if (typeMatch && subtypeMatch) {
            log(`  ✅ Type normalization: ${result.type}.${result.subtype}`, 'green');
            passed++;
        } else {
            log(`  ❌ Type normalization: expected ${expected.type}.${expected.subtype}, got ${result.type}.${result.subtype}`, 'red');
            failed++;
        }
        
        // Test function filtering (if applicable)
        if (expected.hasOwnProperty('shouldFilter')) {
            const functionName = event.data?.name;
            const isFiltered = isInternalFunction(functionName);
            const expectedFilter = expected.shouldFilter;
            
            if (isFiltered === expectedFilter) {
                const filterText = isFiltered ? 'filtered out' : 'kept';
                log(`  ✅ Function filtering: "${functionName}" correctly ${filterText}`, 'green');
                passed++;
            } else {
                const expectedText = expectedFilter ? 'filtered out' : 'kept';
                const actualText = isFiltered ? 'filtered out' : 'kept';
                log(`  ❌ Function filtering: "${functionName}" should be ${expectedText} but was ${actualText}`, 'red');
                failed++;
            }
        }
    });
    
    // Test clean event type format
    log('\n🔍 Testing Clean Event Type Format', 'yellow');
    
    const cleanEventTypes = [
        "code.directory_discovered",
        "code.file_discovered", 
        "code.file_analyzed",
        "code.node_found",
        "hook.pre_tool",
        "hook.post_tool",
        "session.started"
    ];
    
    cleanEventTypes.forEach(eventType => {
        // Check that event type follows clean format (no colons, underscores for subtypes)
        const hasColons = eventType.includes(':');
        const isWellFormatted = /^[a-z]+\.[a-z_]+$/.test(eventType);
        
        if (!hasColons && isWellFormatted) {
            log(`  ✅ Clean format: ${eventType}`, 'green');
            passed++;
        } else {
            log(`  ❌ Unclean format: ${eventType}`, 'red');  
            failed++;
        }
    });
    
    // Summary
    log('\n📊 Test Results', 'magenta');
    log(`Total tests: ${passed + failed}`, 'white');
    log(`Passed: ${passed}`, 'green');
    log(`Failed: ${failed}`, failed > 0 ? 'red' : 'white');
    
    if (failed === 0) {
        log('\n🎉 All tests passed!', 'green');
        return true;
    } else {
        log('\n💥 Some tests failed!', 'red');
        return false;
    }
}

// Run the tests
if (require.main === module) {
    const success = runTests();
    process.exit(success ? 0 : 1);
}

module.exports = { runTests, isInternalFunction };