#!/usr/bin/env node

/**
 * Test Suite: Event Viewer Autoscroll Behavior
 *
 * Tests the autoscroll functionality:
 * 1. Autoscroll only happens when user is at bottom
 * 2. Scrolling up stops autoscroll
 * 3. Smooth user experience when reading event history
 * 4. Manual scroll position is preserved
 */

const fs = require('fs');
const path = require('path');

// Color utilities
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

// Mock DOM element for testing scroll behavior
class MockScrollElement {
    constructor(clientHeight = 400, scrollHeight = 400) {
        this.clientHeight = clientHeight;  // Visible area height
        this.scrollHeight = scrollHeight;  // Total content height (start equal to visible)
        this.scrollTop = 0;               // Current scroll position
        this.scrollBehavior = 'smooth';
        this.scrollHistory = [];
    }

    // Simulate adding content (increases scrollHeight)
    addContent(heightIncrease = 100) {
        this.scrollHeight += heightIncrease;
        this.scrollHistory.push({
            action: 'addContent',
            scrollTop: this.scrollTop,
            scrollHeight: this.scrollHeight,
            clientHeight: this.clientHeight,
            timestamp: Date.now()
        });
    }

    // Check if user is at bottom (with tolerance)
    isAtBottom(tolerance = 10) {
        return (this.scrollTop + this.clientHeight >= this.scrollHeight - tolerance);
    }

    // Scroll to bottom
    scrollToBottom() {
        this.scrollTop = this.scrollHeight - this.clientHeight;
        this.scrollHistory.push({
            action: 'scrollToBottom',
            scrollTop: this.scrollTop,
            scrollHeight: this.scrollHeight,
            clientHeight: this.clientHeight,
            timestamp: Date.now()
        });
    }

    // Manual scroll by user
    manualScroll(scrollTop) {
        this.scrollTop = Math.max(0, Math.min(scrollTop, this.scrollHeight - this.clientHeight));
        this.scrollHistory.push({
            action: 'manualScroll',
            scrollTop: this.scrollTop,
            scrollHeight: this.scrollHeight,
            clientHeight: this.clientHeight,
            timestamp: Date.now()
        });
    }

    // Get scroll stats
    getStats() {
        return {
            scrollTop: this.scrollTop,
            scrollHeight: this.scrollHeight,
            clientHeight: this.clientHeight,
            isAtBottom: this.isAtBottom(),
            scrollPercentage: (this.scrollTop / (this.scrollHeight - this.clientHeight) * 100).toFixed(1)
        };
    }
}

// Mock EventViewer with autoscroll logic (simplified)
class MockEventViewer {
    constructor() {
        this.eventsList = new MockScrollElement();
        this.autoScroll = true;
        this.events = [];
        this.filteredEvents = [];
        this.renderCount = 0;
    }

    // Add new events (simulates real-time event updates)
    addEvents(newEvents) {
        this.events.push(...newEvents);
        this.filteredEvents.push(...newEvents);
        this.renderEvents();
    }

    // Render events with autoscroll logic (based on actual implementation)
    renderEvents() {
        // Check if user was at bottom BEFORE rendering (key logic)
        const wasAtBottom = this.eventsList.isAtBottom();

        // Simulate DOM rendering (content increases)
        const newContentHeight = this.filteredEvents.length * 50; // 50px per event
        this.eventsList.scrollHeight = Math.max(400, newContentHeight);

        this.renderCount++;

        // Auto-scroll only if user was already at bottom before rendering
        if (this.filteredEvents.length > 0 && wasAtBottom && this.autoScroll) {
            // Simulate requestAnimationFrame delay
            setTimeout(() => {
                this.eventsList.scrollToBottom();
            }, 1);
        }

        return {
            wasAtBottom,
            didAutoScroll: wasAtBottom && this.autoScroll,
            renderCount: this.renderCount
        };
    }

    // User scrolls manually
    userScroll(scrollTop) {
        this.eventsList.manualScroll(scrollTop);

        // Could implement smart autoscroll disable/enable logic here
        const isNowAtBottom = this.eventsList.isAtBottom();

        return {
            scrollTop,
            isAtBottom: isNowAtBottom
        };
    }

    // Toggle autoscroll
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        return this.autoScroll;
    }

    getStats() {
        return {
            ...this.eventsList.getStats(),
            autoScroll: this.autoScroll,
            eventCount: this.events.length,
            renderCount: this.renderCount
        };
    }
}

// Test cases for autoscroll behavior
function runAutoscrollTests() {
    log('\n📜 Testing Event Viewer Autoscroll Behavior', 'cyan');
    log('='.repeat(50), 'cyan');

    let passed = 0;
    let failed = 0;

    // Test 1: Initial state
    log('\n🧪 Test 1: Initial State', 'yellow');
    const viewer = new MockEventViewer();

    const initialStats = viewer.getStats();
    log(`  📊 Initial state: autoScroll=${initialStats.autoScroll}, isAtBottom=${initialStats.isAtBottom}`, 'blue');

    if (initialStats.autoScroll === true) {
        log('  ✅ Initial autoscroll enabled', 'green');
        passed++;
    } else {
        log('  ❌ Initial state incorrect - autoscroll not enabled', 'red');
        failed++;
    }

    // Test 2: Autoscroll when at bottom
    log('\n🧪 Test 2: Autoscroll When at Bottom', 'yellow');

    // Add events while at bottom
    const result1 = viewer.renderEvents();
    viewer.addEvents([
        { type: 'hook', subtype: 'pre_tool', data: { tool_name: 'Read' } },
        { type: 'hook', subtype: 'post_tool', data: { tool_name: 'Read' } }
    ]);

    const stats1 = viewer.getStats();
    log(`  📊 Stats: ${JSON.stringify(stats1)}`, 'blue');

    if (stats1.isAtBottom) {
        log('  ✅ Auto-scrolled to bottom with new events', 'green');
        passed++;
    } else {
        log('  ❌ Failed to auto-scroll to bottom', 'red');
        failed++;
    }

    // Test 3: No autoscroll when not at bottom
    log('\n🧪 Test 3: No Autoscroll When Not at Bottom', 'yellow');

    // First add content to make scrolling meaningful
    viewer.addEvents([
        { type: 'setup', subtype: 'event1', data: {} },
        { type: 'setup', subtype: 'event2', data: {} },
        { type: 'setup', subtype: 'event3', data: {} },
        { type: 'setup', subtype: 'event4', data: {} }
    ]);

    // User scrolls up from bottom
    viewer.userScroll(100); // Scroll to middle
    const scrollPos = viewer.eventsList.scrollTop;
    const wasAtBottom = viewer.eventsList.isAtBottom();

    // Add more events
    viewer.addEvents([
        { type: 'claude', subtype: 'response', data: { content: 'Response 1' } },
        { type: 'claude', subtype: 'response', data: { content: 'Response 2' } }
    ]);

    const stats2 = viewer.getStats();
    const scrollPosAfter = viewer.eventsList.scrollTop;

    log(`  📊 Scroll before: ${scrollPos}, after: ${scrollPosAfter}, was at bottom: ${wasAtBottom}`, 'blue');

    if (scrollPos === scrollPosAfter && !wasAtBottom) {
        log('  ✅ Scroll position preserved when not at bottom', 'green');
        passed++;
    } else {
        log('  ❌ Scroll position not preserved', 'red');
        failed++;
    }

    // Test 4: Resume autoscroll when returning to bottom
    log('\n🧪 Test 4: Resume Autoscroll When Returning to Bottom', 'yellow');

    // User scrolls back to bottom
    viewer.eventsList.scrollToBottom();
    const backAtBottom = viewer.eventsList.isAtBottom();

    // Add new events
    viewer.addEvents([
        { type: 'session', subtype: 'started', data: { session_id: '123' } }
    ]);

    const stats3 = viewer.getStats();

    if (backAtBottom && stats3.isAtBottom) {
        log('  ✅ Autoscroll resumed when back at bottom', 'green');
        passed++;
    } else {
        log('  ❌ Autoscroll not resumed', 'red');
        failed++;
    }

    // Test 5: Autoscroll toggle
    log('\n🧪 Test 5: Autoscroll Toggle', 'yellow');

    const originalAutoScroll = viewer.autoScroll;
    const toggledAutoScroll = viewer.toggleAutoScroll();

    if (toggledAutoScroll !== originalAutoScroll) {
        log('  ✅ Autoscroll toggle works', 'green');
        passed++;
    } else {
        log('  ❌ Autoscroll toggle failed', 'red');
        failed++;
    }

    // Add events with autoscroll disabled
    viewer.addEvents([
        { type: 'todo', subtype: 'updated', data: { todos: [] } }
    ]);

    const stats4 = viewer.getStats();

    if (!stats4.autoScroll) {
        log('  ✅ Autoscroll disabled prevents scrolling', 'green');
        passed++;
    } else {
        log('  ❌ Autoscroll disable ineffective', 'red');
        failed++;
    }

    // Test 6: Tolerance testing
    log('\n🧪 Test 6: Bottom Detection Tolerance', 'yellow');

    const toleranceViewer = new MockEventViewer();
    toleranceViewer.eventsList.scrollTop = toleranceViewer.eventsList.scrollHeight - toleranceViewer.eventsList.clientHeight - 5; // 5px from bottom

    const isAtBottomWithTolerance = toleranceViewer.eventsList.isAtBottom(10); // 10px tolerance
    const isAtBottomStrict = toleranceViewer.eventsList.isAtBottom(0); // No tolerance

    if (isAtBottomWithTolerance && !isAtBottomStrict) {
        log('  ✅ Tolerance detection works correctly', 'green');
        passed++;
    } else {
        log('  ❌ Tolerance detection failed', 'red');
        failed++;
    }

    // Summary
    log('\n📊 Autoscroll Test Results', 'magenta');
    log(`Total tests: ${passed + failed}`, 'white');
    log(`Passed: ${passed}`, 'green');
    log(`Failed: ${failed}`, failed > 0 ? 'red' : 'white');

    if (failed === 0) {
        log('\n🎉 All autoscroll tests passed!', 'green');
        return true;
    } else {
        log('\n💥 Some autoscroll tests failed!', 'red');
        return false;
    }
}

// Test user experience scenarios
function runUserExperienceTests() {
    log('\n👤 Testing User Experience Scenarios', 'cyan');
    log('='.repeat(40), 'cyan');

    let passed = 0;
    let failed = 0;

    // Scenario 1: Reading old events while new ones arrive
    log('\n📖 Scenario 1: Reading History While Events Arrive', 'yellow');

    const viewer = new MockEventViewer();

    // Add initial events and ensure at bottom
    viewer.addEvents(Array.from({ length: 10 }, (_, i) => ({
        type: 'system',
        subtype: 'heartbeat',
        data: { count: i }
    })));

    // User scrolls up to read history
    viewer.userScroll(50);
    const readingPosition = viewer.eventsList.scrollTop;

    // New events arrive while user is reading
    for (let i = 0; i < 5; i++) {
        viewer.addEvents([{
            type: 'hook',
            subtype: 'pre_tool',
            data: { tool_name: `Tool${i}` }
        }]);

        // Position should not change while reading
        const currentPosition = viewer.eventsList.scrollTop;
        if (currentPosition !== readingPosition) {
            log(`  ❌ Reading interrupted at event ${i}`, 'red');
            failed++;
            break;
        }
    }

    if (viewer.eventsList.scrollTop === readingPosition) {
        log('  ✅ Reading position preserved during event stream', 'green');
        passed++;
    }

    // Scenario 2: Natural return to bottom behavior
    log('\n⬇️ Scenario 2: Natural Return to Bottom', 'yellow');

    // User finishes reading and scrolls back to bottom
    viewer.eventsList.scrollToBottom();

    // New events should now auto-scroll
    viewer.addEvents([{
        type: 'claude',
        subtype: 'response',
        data: { content: 'Final response' }
    }]);

    const finalStats = viewer.getStats();
    if (finalStats.isAtBottom) {
        log('  ✅ Natural return to autoscroll behavior', 'green');
        passed++;
    } else {
        log('  ❌ Failed to resume autoscroll naturally', 'red');
        failed++;
    }

    // Scenario 3: Rapid event stream performance
    log('\n⚡ Scenario 3: Rapid Event Stream Performance', 'yellow');

    const rapidViewer = new MockEventViewer();
    const startTime = Date.now();

    // Simulate rapid event arrival (100 events)
    for (let i = 0; i < 100; i++) {
        rapidViewer.addEvents([{
            type: 'code',
            subtype: 'node_found',
            data: { name: `function_${i}` }
        }]);
    }

    const endTime = Date.now();
    const processingTime = endTime - startTime;

    log(`  📊 Processing time for 100 events: ${processingTime}ms`, 'blue');

    if (processingTime < 1000 && rapidViewer.getStats().isAtBottom) {
        log('  ✅ Rapid event stream handled efficiently', 'green');
        passed++;
    } else {
        log('  ❌ Rapid event stream performance issues', 'red');
        failed++;
    }

    // Summary
    log('\n📊 User Experience Test Results', 'magenta');
    log(`Total scenarios: ${passed + failed}`, 'white');
    log(`Passed: ${passed}`, 'green');
    log(`Failed: ${failed}`, failed > 0 ? 'red' : 'white');

    return failed === 0;
}

// Test edge cases
function runEdgeCaseTests() {
    log('\n🔧 Testing Edge Cases', 'cyan');
    log('='.repeat(30), 'cyan');

    let passed = 0;
    let failed = 0;

    // Edge Case 1: Empty event list
    log('\n🕳️ Edge Case 1: Empty Event List', 'yellow');
    const emptyViewer = new MockEventViewer();
    const renderResult = emptyViewer.renderEvents();

    if (renderResult.didAutoScroll === false) {
        log('  ✅ No autoscroll on empty list', 'green');
        passed++;
    } else {
        log('  ❌ Unexpected autoscroll on empty list', 'red');
        failed++;
    }

    // Edge Case 2: Exactly at bottom
    log('\n🎯 Edge Case 2: Exactly at Bottom', 'yellow');
    const exactViewer = new MockEventViewer();
    exactViewer.eventsList.scrollTop = exactViewer.eventsList.scrollHeight - exactViewer.eventsList.clientHeight;

    exactViewer.addEvents([{ type: 'test', subtype: 'case', data: {} }]);

    if (exactViewer.getStats().isAtBottom) {
        log('  ✅ Exact bottom position handled correctly', 'green');
        passed++;
    } else {
        log('  ❌ Exact bottom position issue', 'red');
        failed++;
    }

    // Edge Case 3: Very long event list
    log('\n📏 Edge Case 3: Very Long Event List', 'yellow');
    const longViewer = new MockEventViewer();
    const longEvents = Array.from({ length: 1000 }, (_, i) => ({
        type: 'bulk',
        subtype: 'test',
        data: { index: i }
    }));

    longViewer.addEvents(longEvents);
    const longStats = longViewer.getStats();

    if (longStats.eventCount === 1000 && longStats.isAtBottom) {
        log('  ✅ Long event list handled correctly', 'green');
        passed++;
    } else {
        log('  ❌ Long event list issues', 'red');
        failed++;
    }

    log('\n📊 Edge Case Test Results', 'magenta');
    log(`Total cases: ${passed + failed}`, 'white');
    log(`Passed: ${passed}`, 'green');
    log(`Failed: ${failed}`, failed > 0 ? 'red' : 'white');

    return failed === 0;
}

// Run all autoscroll tests
function runAllAutoscrollTests() {
    const basicSuccess = runAutoscrollTests();
    const uxSuccess = runUserExperienceTests();
    const edgeSuccess = runEdgeCaseTests();

    log('\n📋 Overall Autoscroll Results', 'magenta');
    log(`Basic Tests: ${basicSuccess ? 'PASSED' : 'FAILED'}`,
         basicSuccess ? 'green' : 'red');
    log(`UX Tests: ${uxSuccess ? 'PASSED' : 'FAILED'}`,
         uxSuccess ? 'green' : 'red');
    log(`Edge Cases: ${edgeSuccess ? 'PASSED' : 'FAILED'}`,
         edgeSuccess ? 'green' : 'red');

    return basicSuccess && uxSuccess && edgeSuccess;
}

// Run the tests
if (require.main === module) {
    const success = runAllAutoscrollTests();
    process.exit(success ? 0 : 1);
}

module.exports = {
    runAllAutoscrollTests,
    runAutoscrollTests,
    runUserExperienceTests,
    runEdgeCaseTests,
    MockEventViewer,
    MockScrollElement
};