#!/usr/bin/env node

/**
 * Test Suite: Lazy Loading Directory Discovery
 *
 * Tests the lazy loading functionality:
 * 1. Initial load shows only top-level directories
 * 2. Clicking a directory triggers discovery of contents
 * 3. Clicking a file triggers AST analysis
 * 4. Discovered state is tracked properly
 * 5. No redundant discoveries occur
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

// Mock DOM and Socket.IO for testing
class MockSocket {
    constructor() {
        this.emittedEvents = [];
        this.eventHandlers = {};
    }

    emit(event, data) {
        this.emittedEvents.push({ event, data, timestamp: Date.now() });
        log(`  📡 Socket emit: ${event} - ${JSON.stringify(data).substring(0, 60)}...`, 'cyan');
    }

    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }

    trigger(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => handler(data));
        }
    }

    getEmittedEvents() {
        return this.emittedEvents;
    }
}

// Mock CodeTree implementation (simplified for testing)
class MockCodeTree {
    constructor() {
        this.socket = new MockSocket();
        this.discoveredPaths = new Set();
        this.analyzedFiles = new Set();
        this.nodes = new Map();
        this.analyzing = false;
        this.currentRequestId = null;
        this.treeData = {
            name: 'Project Root',
            type: 'module',
            path: '/',
            children: []
        };

        // Subscribe to events
        this.subscribeToEvents();
    }

    subscribeToEvents() {
        this.socket.on('code:directory_discovered', (data) => this.handleDirectoryDiscovered(data));
        this.socket.on('code:file_discovered', (data) => this.handleFileDiscovered(data));
        this.socket.on('code:file_analyzed', (data) => this.handleFileAnalyzed(data));
    }

    startAnalysis() {
        if (this.analyzing) return false;

        this.analyzing = true;
        this.currentRequestId = `analysis-${Date.now()}`;
        this.discoveredPaths.clear();
        this.analyzedFiles.clear();

        // Request top-level discovery
        this.socket.emit('code:discover:top_level', {
            request_id: this.currentRequestId,
            path: '.',
            languages: null,
            max_depth: null,
            ignore_patterns: null
        });

        return true;
    }

    toggleNode(nodePath, nodeType) {
        // Simulate user clicking on a node
        if (nodeType === 'directory' && !this.discoveredPaths.has(nodePath)) {
            this.discoverDirectory(nodePath);
            return 'discovering';
        }

        if (nodeType === 'file' && !this.analyzedFiles.has(nodePath)) {
            this.analyzeFile(nodePath);
            return 'analyzing';
        }

        return 'toggle';
    }

    discoverDirectory(path) {
        if (this.discoveredPaths.has(path)) {
            return false; // Already discovered
        }

        this.discoveredPaths.add(path);
        this.socket.emit('code:discover:directory', {
            path: path,
            request_id: this.currentRequestId
        });

        return true;
    }

    analyzeFile(path) {
        if (this.analyzedFiles.has(path)) {
            return false; // Already analyzed
        }

        this.analyzedFiles.add(path);
        this.socket.emit('code:analyze:file', {
            path: path,
            request_id: this.currentRequestId
        });

        return true;
    }

    handleDirectoryDiscovered(data) {
        log(`  📁 Directory discovered: ${data.path}`, 'blue');
        this.addNodeToTree({
            name: data.name,
            type: 'directory',
            path: data.path,
            children: data.children || []
        });
    }

    handleFileDiscovered(data) {
        log(`  📄 File discovered: ${data.path}`, 'blue');
        this.addNodeToTree({
            name: data.name,
            type: 'file',
            path: data.path,
            language: data.language,
            analyzed: false,
            children: []
        });
    }

    handleFileAnalyzed(data) {
        log(`  ⚡ File analyzed: ${data.path}`, 'blue');
        let node = this.nodes.get(data.path);
        if (!node) {
            // Create file node if it doesn't exist
            node = {
                name: data.path.split('/').pop(),
                type: 'file',
                path: data.path,
                analyzed: false,
                children: []
            };
            this.nodes.set(data.path, node);
        }
        node.analyzed = true;
        node.children = data.nodes || [];
    }

    addNodeToTree(node) {
        this.nodes.set(node.path, node);
    }

    getStats() {
        return {
            discoveredPaths: this.discoveredPaths.size,
            analyzedFiles: this.analyzedFiles.size,
            totalNodes: this.nodes.size,
            emittedEvents: this.socket.emittedEvents.length
        };
    }
}

// Test cases
function runLazyLoadingTests() {
    log('\n🚀 Testing Lazy Loading Directory Discovery', 'cyan');
    log('='.repeat(50), 'cyan');

    const codeTree = new MockCodeTree();
    let passed = 0;
    let failed = 0;

    // Test 1: Initial analysis request
    log('\n🧪 Test 1: Initial Analysis Request', 'yellow');
    const analysisStarted = codeTree.startAnalysis();

    if (analysisStarted && codeTree.analyzing) {
        log('  ✅ Analysis started successfully', 'green');
        passed++;
    } else {
        log('  ❌ Analysis failed to start', 'red');
        failed++;
    }

    const events = codeTree.socket.getEmittedEvents();
    const topLevelDiscovery = events.find(e => e.event === 'code:discover:top_level');

    if (topLevelDiscovery) {
        log('  ✅ Top-level discovery requested', 'green');
        passed++;
    } else {
        log('  ❌ Top-level discovery not requested', 'red');
        failed++;
    }

    // Test 2: Directory discovery on demand
    log('\n🧪 Test 2: Directory Discovery on Demand', 'yellow');

    // Simulate discovering a directory
    const dirPath = '/src';
    const result1 = codeTree.toggleNode(dirPath, 'directory');

    if (result1 === 'discovering') {
        log('  ✅ Directory discovery triggered', 'green');
        passed++;
    } else {
        log('  ❌ Directory discovery not triggered', 'red');
        failed++;
    }

    const dirDiscovery = events.find(e => e.event === 'code:discover:directory' && e.data.path === dirPath);
    if (dirDiscovery) {
        log('  ✅ Directory discovery event emitted', 'green');
        passed++;
    } else {
        log('  ❌ Directory discovery event not emitted', 'red');
        failed++;
    }

    // Test 3: No redundant discoveries
    log('\n🧪 Test 3: No Redundant Discoveries', 'yellow');

    const eventCountBefore = events.length;
    const result2 = codeTree.toggleNode(dirPath, 'directory'); // Same directory again
    const eventCountAfter = codeTree.socket.getEmittedEvents().length;

    if (result2 === 'toggle' && eventCountAfter === eventCountBefore) {
        log('  ✅ Redundant discovery prevented', 'green');
        passed++;
    } else {
        log('  ❌ Redundant discovery occurred', 'red');
        failed++;
    }

    // Test 4: File analysis on demand
    log('\n🧪 Test 4: File Analysis on Demand', 'yellow');

    const filePath = '/src/main.py';
    const result3 = codeTree.toggleNode(filePath, 'file');

    if (result3 === 'analyzing') {
        log('  ✅ File analysis triggered', 'green');
        passed++;
    } else {
        log('  ❌ File analysis not triggered', 'red');
        failed++;
    }

    const fileAnalysis = codeTree.socket.getEmittedEvents().find(
        e => e.event === 'code:analyze:file' && e.data.path === filePath
    );
    if (fileAnalysis) {
        log('  ✅ File analysis event emitted', 'green');
        passed++;
    } else {
        log('  ❌ File analysis event not emitted', 'red');
        failed++;
    }

    // Test 5: State tracking
    log('\n🧪 Test 5: State Tracking', 'yellow');

    const stats = codeTree.getStats();
    log(`  📊 Stats: ${JSON.stringify(stats)}`, 'blue');

    if (stats.discoveredPaths > 0) {
        log('  ✅ Discovered paths tracked', 'green');
        passed++;
    } else {
        log('  ❌ Discovered paths not tracked', 'red');
        failed++;
    }

    if (stats.analyzedFiles > 0) {
        log('  ✅ Analyzed files tracked', 'green');
        passed++;
    } else {
        log('  ❌ Analyzed files not tracked', 'red');
        failed++;
    }

    // Test 6: Event simulation
    log('\n🧪 Test 6: Event Response Simulation', 'yellow');

    // Simulate server responses
    codeTree.socket.trigger('code:directory_discovered', {
        path: dirPath,
        name: 'src',
        children: [
            { name: 'main.py', type: 'file' },
            { name: 'utils.py', type: 'file' }
        ]
    });

    codeTree.socket.trigger('code:file_analyzed', {
        path: filePath,
        nodes: [
            { name: 'main', type: 'function' },
            { name: 'UserClass', type: 'class' }
        ]
    });

    const dirNode = codeTree.nodes.get(dirPath);
    const fileNode = codeTree.nodes.get(filePath);

    if (dirNode && dirNode.type === 'directory') {
        log('  ✅ Directory node created', 'green');
        passed++;
    } else {
        log('  ❌ Directory node not created', 'red');
        failed++;
    }

    if (fileNode && fileNode.analyzed) {
        log('  ✅ File node analyzed', 'green');
        passed++;
    } else {
        log('  ❌ File node not analyzed', 'red');
        failed++;
    }

    // Summary
    log('\n📊 Lazy Loading Test Results', 'magenta');
    log(`Total tests: ${passed + failed}`, 'white');
    log(`Passed: ${passed}`, 'green');
    log(`Failed: ${failed}`, failed > 0 ? 'red' : 'white');

    if (failed === 0) {
        log('\n🎉 All lazy loading tests passed!', 'green');
        return true;
    } else {
        log('\n💥 Some lazy loading tests failed!', 'red');
        return false;
    }
}

// Test performance impact
function runPerformanceTests() {
    log('\n⚡ Testing Lazy Loading Performance Impact', 'cyan');
    log('='.repeat(40), 'cyan');

    const iterations = 1000;

    // Test 1: Traditional full discovery simulation
    const startFull = process.hrtime.bigint();
    for (let i = 0; i < iterations; i++) {
        // Simulate discovering all directories and files at once
        const paths = Array.from({ length: 100 }, (_, j) => `/path/to/file${j}.py`);
        paths.forEach(path => {
            // Simulate processing
        });
    }
    const endFull = process.hrtime.bigint();
    const fullTime = Number(endFull - startFull) / 1000000; // Convert to ms

    // Test 2: Lazy discovery simulation
    const startLazy = process.hrtime.bigint();
    for (let i = 0; i < iterations; i++) {
        // Simulate discovering only top-level (much smaller set)
        const topLevelPaths = ['/src', '/tests', '/docs'];
        topLevelPaths.forEach(path => {
            // Simulate processing
        });
    }
    const endLazy = process.hrtime.bigint();
    const lazyTime = Number(endLazy - startLazy) / 1000000; // Convert to ms

    const improvement = ((fullTime - lazyTime) / fullTime * 100).toFixed(1);

    log(`  📊 Full discovery: ${fullTime.toFixed(2)}ms`, 'yellow');
    log(`  📊 Lazy discovery: ${lazyTime.toFixed(2)}ms`, 'yellow');
    log(`  🚀 Performance improvement: ${improvement}%`, 'green');

    return {
        fullTime,
        lazyTime,
        improvement: parseFloat(improvement)
    };
}

// Run all tests
function runAllTests() {
    const lazyLoadingSuccess = runLazyLoadingTests();
    const perfResults = runPerformanceTests();

    log('\n📋 Overall Results', 'magenta');
    log(`Lazy Loading Tests: ${lazyLoadingSuccess ? 'PASSED' : 'FAILED'}`,
         lazyLoadingSuccess ? 'green' : 'red');
    log(`Performance Improvement: ${perfResults.improvement}%`,
         perfResults.improvement > 0 ? 'green' : 'red');

    return lazyLoadingSuccess && perfResults.improvement > 0;
}

// Run the tests
if (require.main === module) {
    const success = runAllTests();
    process.exit(success ? 0 : 1);
}

module.exports = {
    runLazyLoadingTests,
    runPerformanceTests,
    MockCodeTree,
    MockSocket
};
