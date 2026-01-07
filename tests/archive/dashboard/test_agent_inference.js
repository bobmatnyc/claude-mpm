#!/usr/bin/env node

/**
 * Test Suite: Agent Inference Component
 *
 * Tests the agent inference display component including:
 * - Inference message parsing and display
 * - Real-time updates via Socket.IO
 * - Error state handling
 * - Memory management for inference history
 */

const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

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

// Mock Socket.IO for testing
class MockSocketIO {
    constructor() {
        this.events = {};
        this.emitted = [];
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }

    emit(event, data) {
        this.emitted.push({ event, data });
        // Trigger callbacks for testing
        if (this.events[event]) {
            this.events[event].forEach(cb => cb(data));
        }
    }

    simulate(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(cb => cb(data));
        }
    }
}

// Mock Agent Inference Component
class AgentInferenceComponent {
    constructor(container, socket) {
        this.container = container;
        this.socket = socket;
        this.inferences = [];
        this.maxInferences = 100;
        this.currentAgent = null;
        this.errorCount = 0;

        this.init();
    }

    init() {
        // Set up socket event listeners
        this.socket.on('agent:inference', (data) => this.handleInference(data));
        this.socket.on('agent:error', (data) => this.handleError(data));
        this.socket.on('agent:clear', () => this.clearInferences());

        // Create DOM structure
        this.render();
    }

    render() {
        this.container.innerHTML = `
            <div class="agent-inference">
                <div class="inference-header">
                    <h3>Agent Inferences</h3>
                    <span class="inference-count">0</span>
                </div>
                <div class="inference-list"></div>
                <div class="inference-errors" style="display:none;"></div>
            </div>
        `;

        this.listElement = this.container.querySelector('.inference-list');
        this.countElement = this.container.querySelector('.inference-count');
        this.errorElement = this.container.querySelector('.inference-errors');
    }

    handleInference(data) {
        // Validate inference data
        if (!data || !data.agent || !data.message) {
            this.handleError({ message: 'Invalid inference data' });
            return;
        }

        // Add to inferences array
        const inference = {
            id: `inf-${Date.now()}-${Math.random()}`,
            agent: data.agent,
            message: data.message,
            timestamp: data.timestamp || new Date().toISOString(),
            confidence: data.confidence || 0.0,
            metadata: data.metadata || {}
        };

        this.inferences.push(inference);

        // Limit stored inferences
        if (this.inferences.length > this.maxInferences) {
            this.inferences = this.inferences.slice(-this.maxInferences);
        }

        // Update display
        this.addInferenceToDOM(inference);
        this.updateCount();
    }

    addInferenceToDOM(inference) {
        const inferenceElement = document.createElement('div');
        inferenceElement.className = 'inference-item';
        inferenceElement.dataset.id = inference.id;

        // Format confidence as percentage
        const confidencePercent = Math.round(inference.confidence * 100);
        const confidenceClass = confidencePercent > 80 ? 'high' :
                               confidencePercent > 50 ? 'medium' : 'low';

        inferenceElement.innerHTML = `
            <div class="inference-agent">${this.escapeHtml(inference.agent)}</div>
            <div class="inference-message">${this.escapeHtml(inference.message)}</div>
            <div class="inference-meta">
                <span class="confidence ${confidenceClass}">${confidencePercent}%</span>
                <span class="timestamp">${this.formatTime(inference.timestamp)}</span>
            </div>
        `;

        // Add to list (newest first)
        this.listElement.insertBefore(inferenceElement, this.listElement.firstChild);

        // Limit DOM elements
        while (this.listElement.children.length > this.maxInferences) {
            this.listElement.removeChild(this.listElement.lastChild);
        }
    }

    handleError(data) {
        this.errorCount++;

        const errorMessage = data.message || 'Unknown error';

        // Show error element
        this.errorElement.style.display = 'block';
        this.errorElement.innerHTML = `
            <div class="error-message">
                ⚠️ Error: ${this.escapeHtml(errorMessage)}
                <span class="error-count">(${this.errorCount} errors)</span>
            </div>
        `;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (this.errorElement) {
                this.errorElement.style.display = 'none';
            }
        }, 5000);
    }

    clearInferences() {
        this.inferences = [];
        this.listElement.innerHTML = '';
        this.updateCount();
        this.errorCount = 0;
        this.errorElement.style.display = 'none';
    }

    updateCount() {
        this.countElement.textContent = this.inferences.length;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString();
        } catch {
            return timestamp;
        }
    }

    // Memory management
    cleanup() {
        this.inferences = [];
        this.listElement = null;
        this.countElement = null;
        this.errorElement = null;
        this.container.innerHTML = '';
    }

    getMemoryUsage() {
        return {
            inferenceCount: this.inferences.length,
            domElements: this.listElement ? this.listElement.children.length : 0,
            errorCount: this.errorCount
        };
    }
}

// Test Suite
class AgentInferenceTests {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }

    setup() {
        // Create a DOM environment
        const dom = new JSDOM('<!DOCTYPE html><div id="container"></div>');
        global.document = dom.window.document;
        global.window = dom.window;

        this.container = document.getElementById('container');
        this.socket = new MockSocketIO();
        this.component = new AgentInferenceComponent(this.container, this.socket);
    }

    teardown() {
        if (this.component) {
            this.component.cleanup();
        }
    }

    test(name, testFunc) {
        this.tests.push({ name, testFunc });
    }

    async runTests() {
        log('\n=== Agent Inference Component Tests ===\n', 'cyan');

        for (const test of this.tests) {
            try {
                this.setup();
                await test.testFunc.call(this);
                this.passed++;
                log(`✓ ${test.name}`, 'green');
            } catch (error) {
                this.failed++;
                log(`✗ ${test.name}`, 'red');
                log(`  Error: ${error.message}`, 'red');
            } finally {
                this.teardown();
            }
        }

        // Summary
        log('\n=== Test Summary ===', 'cyan');
        log(`Total: ${this.tests.length}`, 'white');
        log(`Passed: ${this.passed}`, 'green');
        log(`Failed: ${this.failed}`, this.failed > 0 ? 'red' : 'green');

        return this.failed === 0;
    }

    // Assertion helpers
    assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    }

    assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `Expected ${expected}, got ${actual}`);
        }
    }

    assertContains(text, substring, message) {
        if (!text.includes(substring)) {
            throw new Error(message || `"${text}" does not contain "${substring}"`);
        }
    }
}

// Define tests
const testSuite = new AgentInferenceTests();

testSuite.test('Component initialization', function() {
    this.assert(this.component, 'Component should be created');
    this.assert(this.container.querySelector('.agent-inference'), 'Should create inference container');
    this.assertEqual(this.component.inferences.length, 0, 'Should start with no inferences');
});

testSuite.test('Handle valid inference', function() {
    const inferenceData = {
        agent: 'TestAgent',
        message: 'Processing user request',
        confidence: 0.85,
        timestamp: '2024-01-01T12:00:00Z'
    };

    this.socket.simulate('agent:inference', inferenceData);

    this.assertEqual(this.component.inferences.length, 1, 'Should add inference');
    this.assertEqual(this.component.inferences[0].agent, 'TestAgent', 'Should store agent name');
    this.assertEqual(this.component.inferences[0].confidence, 0.85, 'Should store confidence');

    const domItem = this.container.querySelector('.inference-item');
    this.assert(domItem, 'Should create DOM element');
    this.assertContains(domItem.textContent, 'TestAgent', 'Should display agent name');
    this.assertContains(domItem.textContent, '85%', 'Should display confidence percentage');
});

testSuite.test('Handle invalid inference', function() {
    const invalidData = {
        // Missing required fields
        someField: 'value'
    };

    this.socket.simulate('agent:inference', invalidData);

    this.assertEqual(this.component.inferences.length, 0, 'Should not add invalid inference');
    this.assertEqual(this.component.errorCount, 1, 'Should increment error count');

    const errorElement = this.container.querySelector('.inference-errors');
    this.assert(errorElement, 'Should show error element');
    this.assertContains(errorElement.textContent, 'Invalid inference data', 'Should show error message');
});

testSuite.test('Memory limit enforcement', function() {
    // Add more than max inferences
    for (let i = 0; i < 150; i++) {
        this.socket.simulate('agent:inference', {
            agent: `Agent${i}`,
            message: `Message ${i}`,
            confidence: Math.random()
        });
    }

    this.assertEqual(this.component.inferences.length, 100, 'Should limit to maxInferences');

    const domItems = this.container.querySelectorAll('.inference-item');
    this.assertEqual(domItems.length, 100, 'Should limit DOM elements');
});

testSuite.test('Clear inferences', function() {
    // Add some inferences
    for (let i = 0; i < 5; i++) {
        this.socket.simulate('agent:inference', {
            agent: `Agent${i}`,
            message: `Message ${i}`
        });
    }

    this.assertEqual(this.component.inferences.length, 5, 'Should have inferences');

    // Clear
    this.socket.simulate('agent:clear');

    this.assertEqual(this.component.inferences.length, 0, 'Should clear inferences');
    this.assertEqual(this.component.errorCount, 0, 'Should reset error count');

    const domItems = this.container.querySelectorAll('.inference-item');
    this.assertEqual(domItems.length, 0, 'Should clear DOM elements');
});

testSuite.test('Error handling and recovery', function() {
    // Trigger error
    this.socket.simulate('agent:error', {
        message: 'Connection lost'
    });

    this.assertEqual(this.component.errorCount, 1, 'Should count error');

    const errorElement = this.container.querySelector('.inference-errors');
    this.assertContains(errorElement.textContent, 'Connection lost', 'Should display error message');

    // Should still handle valid inferences after error
    this.socket.simulate('agent:inference', {
        agent: 'RecoveryAgent',
        message: 'Recovered from error'
    });

    this.assertEqual(this.component.inferences.length, 1, 'Should handle inference after error');
});

testSuite.test('Memory cleanup', function() {
    // Add inferences
    for (let i = 0; i < 10; i++) {
        this.socket.simulate('agent:inference', {
            agent: `Agent${i}`,
            message: `Message ${i}`
        });
    }

    const usageBefore = this.component.getMemoryUsage();
    this.assertEqual(usageBefore.inferenceCount, 10, 'Should track inference count');

    // Cleanup
    this.component.cleanup();

    this.assertEqual(this.component.inferences.length, 0, 'Should clear inferences');
    this.assertEqual(this.container.innerHTML, '', 'Should clear DOM');
});

testSuite.test('Real-time updates', function() {
    const updates = [];

    // Override addInferenceToDOM to track updates
    const originalAdd = this.component.addInferenceToDOM.bind(this.component);
    this.component.addInferenceToDOM = function(inference) {
        updates.push(inference);
        originalAdd(inference);
    };

    // Simulate rapid updates
    for (let i = 0; i < 10; i++) {
        this.socket.simulate('agent:inference', {
            agent: 'RealtimeAgent',
            message: `Update ${i}`,
            confidence: 0.9
        });
    }

    this.assertEqual(updates.length, 10, 'Should process all updates');
    this.assertEqual(this.component.inferences.length, 10, 'Should store all inferences');

    // Check order (newest first in DOM)
    const firstItem = this.container.querySelector('.inference-item');
    this.assertContains(firstItem.textContent, 'Update 9', 'Newest should be first');
});

// Run tests
testSuite.runTests().then(success => {
    process.exit(success ? 0 : 1);
});
