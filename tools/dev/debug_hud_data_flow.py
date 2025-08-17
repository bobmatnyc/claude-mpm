#!/usr/bin/env python3
"""
HUD Data Flow Debugging Script

This script helps debug why the HUD visualizer isn't showing data by:
1. Creating test HTML page that exposes debugging information
2. Adding comprehensive logging to trace data flow
3. Testing HUD components in isolation
4. Verifying event processing and visualization
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def create_debug_html():
    """Create a debug HTML page with comprehensive HUD testing"""
    
    debug_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HUD Debug Test</title>
    
    <!-- External Dependencies -->
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    
    <!-- Load Cytoscape libraries directly for testing -->
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <script src="https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"></script>
    <script src="https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
    
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        
        .debug-section {
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4299e1;
        }
        
        .debug-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2d3748;
        }
        
        .debug-log {
            background: #1a202c;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        .test-controls {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        
        button {
            background: #4299e1;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        
        button:hover {
            background: #3182ce;
        }
        
        button:disabled {
            background: #a0aec0;
            cursor: not-allowed;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-success { background: #48bb78; }
        .status-error { background: #e53e3e; }
        .status-warning { background: #ed8936; }
        .status-info { background: #4299e1; }
        
        #hud-test-container {
            width: 100%;
            height: 400px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            background: white;
        }
        
        .data-display {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <h1>🔬 HUD Data Flow Debugging</h1>
    
    <!-- Test Controls -->
    <div class="debug-section">
        <div class="debug-title">Test Controls</div>
        <div class="test-controls">
            <button onclick="testLibraryLoading()">Test Library Loading</button>
            <button onclick="testSampleData()">Test Sample Data</button>
            <button onclick="testEventProcessing()">Test Event Processing</button>
            <button onclick="testSessionFiltering()">Test Session Filtering</button>
            <button onclick="clearDebugLog()">Clear Log</button>
        </div>
    </div>
    
    <!-- Library Status -->
    <div class="debug-section">
        <div class="debug-title">Library Loading Status</div>
        <div id="library-status">
            <div><span class="status-indicator status-info" id="cytoscape-status"></span>Cytoscape.js: <span id="cytoscape-text">Checking...</span></div>
            <div><span class="status-indicator status-info" id="dagre-status"></span>Dagre: <span id="dagre-text">Checking...</span></div>
            <div><span class="status-indicator status-info" id="cytoscapedagre-status"></span>Cytoscape-Dagre: <span id="cytoscapedagre-text">Checking...</span></div>
        </div>
    </div>
    
    <!-- HUD Components Status -->
    <div class="debug-section">
        <div class="debug-title">HUD Components Status</div>
        <div id="component-status">
            <div><span class="status-indicator status-info" id="hudvisualizer-status"></span>HUD Visualizer: <span id="hudvisualizer-text">Checking...</span></div>
            <div><span class="status-indicator status-info" id="hudmanager-status"></span>HUD Manager: <span id="hudmanager-text">Checking...</span></div>
            <div><span class="status-indicator status-info" id="eventviewer-status"></span>Event Viewer: <span id="eventviewer-text">Checking...</span></div>
        </div>
    </div>
    
    <!-- Sample Data Display -->
    <div class="debug-section">
        <div class="debug-title">Sample Event Data</div>
        <div id="sample-data" class="data-display">Click "Test Sample Data" to load sample events...</div>
    </div>
    
    <!-- HUD Visualization Test -->
    <div class="debug-section">
        <div class="debug-title">HUD Visualization Test</div>
        <div id="hud-test-container"></div>
    </div>
    
    <!-- Debug Log -->
    <div class="debug-section">
        <div class="debug-title">Debug Log</div>
        <div id="debug-log" class="debug-log">Debug log will appear here...\n</div>
    </div>

    <script>
        // Debug logging function
        function debugLog(message, level = 'info') {
            const timestamp = new Date().toISOString().substring(11, 23);
            const logElement = document.getElementById('debug-log');
            const prefix = level.toUpperCase().padEnd(5);
            logElement.textContent += `[${timestamp}] ${prefix} ${message}\n`;
            logElement.scrollTop = logElement.scrollHeight;
            
            // Also log to browser console
            console.log(`[HUD-DEBUG] ${message}`);
        }
        
        function clearDebugLog() {
            document.getElementById('debug-log').textContent = '';
            debugLog('Debug log cleared');
        }
        
        function updateStatus(elementId, textId, status, message) {
            const statusEl = document.getElementById(elementId);
            const textEl = document.getElementById(textId);
            
            statusEl.className = `status-indicator status-${status}`;
            textEl.textContent = message;
        }
        
        // Test library loading
        function testLibraryLoading() {
            debugLog('Testing library loading...');
            
            // Test Cytoscape
            if (typeof window.cytoscape !== 'undefined') {
                updateStatus('cytoscape-status', 'cytoscape-text', 'success', 'Loaded');
                debugLog('✅ Cytoscape.js loaded successfully');
            } else {
                updateStatus('cytoscape-status', 'cytoscape-text', 'error', 'Not loaded');
                debugLog('❌ Cytoscape.js not loaded');
            }
            
            // Test Dagre
            if (typeof window.dagre !== 'undefined') {
                updateStatus('dagre-status', 'dagre-text', 'success', 'Loaded');
                debugLog('✅ Dagre loaded successfully');
            } else {
                updateStatus('dagre-status', 'dagre-text', 'error', 'Not loaded');
                debugLog('❌ Dagre not loaded');
            }
            
            // Test Cytoscape-Dagre
            if (typeof window.cytoscapeDagre !== 'undefined') {
                updateStatus('cytoscapedagre-status', 'cytoscapedagre-text', 'success', 'Loaded');
                debugLog('✅ Cytoscape-Dagre loaded successfully');
            } else {
                updateStatus('cytoscapedagre-status', 'cytoscapedagre-text', 'error', 'Not loaded');
                debugLog('❌ Cytoscape-Dagre not loaded');
            }
            
            // Test component loading
            testComponentLoading();
        }
        
        function testComponentLoading() {
            debugLog('Testing component loading...');
            
            // Test HUD Visualizer
            if (typeof window.HUDVisualizer !== 'undefined') {
                updateStatus('hudvisualizer-status', 'hudvisualizer-text', 'success', 'Class available');
                debugLog('✅ HUDVisualizer class available');
            } else {
                updateStatus('hudvisualizer-status', 'hudvisualizer-text', 'error', 'Class not found');
                debugLog('❌ HUDVisualizer class not found');
            }
            
            // Test HUD Manager
            if (typeof window.HUDManager !== 'undefined') {
                updateStatus('hudmanager-status', 'hudmanager-text', 'success', 'Class available');
                debugLog('✅ HUDManager class available');
            } else {
                updateStatus('hudmanager-status', 'hudmanager-text', 'error', 'Class not found');
                debugLog('❌ HUDManager class not found');
            }
            
            // Test Event Viewer
            if (typeof window.EventViewer !== 'undefined') {
                updateStatus('eventviewer-status', 'eventviewer-text', 'success', 'Class available');
                debugLog('✅ EventViewer class available');
            } else {
                updateStatus('eventviewer-status', 'eventviewer-text', 'error', 'Class not found');
                debugLog('❌ EventViewer class not found');
            }
        }
        
        // Generate sample event data
        function generateSampleEvents() {
            const sessionId = 'debug-session-' + Date.now();
            const baseTime = new Date();
            
            return [
                {
                    timestamp: new Date(baseTime.getTime() - 10000).toISOString(),
                    hook_event_name: 'session',
                    subtype: 'started',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId,
                        working_directory: '/Users/test/project',
                        git_branch: 'main'
                    }
                },
                {
                    timestamp: new Date(baseTime.getTime() - 8000).toISOString(),
                    hook_event_name: 'hook',
                    subtype: 'user_prompt',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId,
                        prompt_preview: 'Debug the HUD visualization'
                    }
                },
                {
                    timestamp: new Date(baseTime.getTime() - 6000).toISOString(),
                    hook_event_name: 'hook',
                    subtype: 'pre_tool',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId,
                        tool_name: 'Read'
                    }
                },
                {
                    timestamp: new Date(baseTime.getTime() - 4000).toISOString(),
                    hook_event_name: 'agent',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId,
                        agent_type: 'research',
                        agent_name: 'Research Agent'
                    }
                },
                {
                    timestamp: new Date(baseTime.getTime() - 2000).toISOString(),
                    hook_event_name: 'todo',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId,
                        todo_action: 'create'
                    }
                },
                {
                    timestamp: baseTime.toISOString(),
                    hook_event_name: 'hook',
                    subtype: 'claude_response',
                    session_id: sessionId,
                    data: {
                        session_id: sessionId
                    }
                }
            ];
        }
        
        function testSampleData() {
            debugLog('Generating sample event data...');
            const sampleEvents = generateSampleEvents();
            
            document.getElementById('sample-data').textContent = JSON.stringify(sampleEvents, null, 2);
            debugLog(`Generated ${sampleEvents.length} sample events`);
            
            // Store for other tests
            window.testEvents = sampleEvents;
            
            return sampleEvents;
        }
        
        function testEventProcessing() {
            debugLog('Testing event processing...');
            
            if (!window.testEvents) {
                testSampleData();
            }
            
            // Test if we can create a HUD visualizer instance
            try {
                if (typeof window.HUDVisualizer === 'undefined') {
                    debugLog('❌ HUDVisualizer class not available');
                    return;
                }
                
                // Create test container for HUD
                const testContainer = document.getElementById('hud-test-container');
                testContainer.innerHTML = '<div id="test-cytoscape" style="width: 100%; height: 100%;"></div>';
                
                debugLog('Creating HUD visualizer instance...');
                const hudVisualizer = new window.HUDVisualizer();
                
                // Override container for testing
                hudVisualizer.container = document.getElementById('test-cytoscape');
                
                debugLog('Initializing HUD visualizer...');
                const initResult = hudVisualizer.initialize();
                
                if (initResult) {
                    debugLog('✅ HUD visualizer initialized');
                    
                    // Force libraries to be loaded
                    debugLog('Forcing library loading...');
                    hudVisualizer.librariesLoaded = true;
                    
                    // Initialize Cytoscape directly
                    if (typeof window.cytoscape !== 'undefined') {
                        debugLog('Initializing Cytoscape directly...');
                        
                        if (typeof window.cytoscapeDagre !== 'undefined') {
                            window.cytoscape.use(window.cytoscapeDagre);
                        }
                        
                        hudVisualizer.cy = window.cytoscape({
                            container: hudVisualizer.container,
                            elements: [],
                            style: [
                                {
                                    selector: 'node',
                                    style: {
                                        'background-color': '#4299e1',
                                        'color': '#ffffff',
                                        'label': 'data(label)',
                                        'text-valign': 'center',
                                        'text-halign': 'center',
                                        'font-size': '12px',
                                        'width': '80px',
                                        'height': '40px'
                                    }
                                },
                                {
                                    selector: 'edge',
                                    style: {
                                        'width': 2,
                                        'line-color': '#718096',
                                        'target-arrow-color': '#718096',
                                        'target-arrow-shape': 'triangle'
                                    }
                                }
                            ],
                            layout: {
                                name: 'grid',
                                rows: 2,
                                cols: 3
                            }
                        });
                        
                        debugLog('✅ Cytoscape instance created');
                        
                        // Process test events
                        debugLog('Processing test events...');
                        hudVisualizer.processExistingEvents(window.testEvents);
                        
                        debugLog(`✅ Event processing completed. Nodes: ${hudVisualizer.nodes.size}`);
                        
                        // List created nodes
                        hudVisualizer.nodes.forEach((nodeData, nodeId) => {
                            debugLog(`  Node: ${nodeId} - ${nodeData.label} (${nodeData.type})`);
                        });
                        
                    } else {
                        debugLog('❌ Cytoscape not available for direct initialization');
                    }
                } else {
                    debugLog('❌ HUD visualizer initialization failed');
                }
                
            } catch (error) {
                debugLog(`❌ Error during event processing: ${error.message}`);
                console.error('Event processing error:', error);
            }
        }
        
        function testSessionFiltering() {
            debugLog('Testing session filtering...');
            
            if (!window.testEvents) {
                testSampleData();
            }
            
            const sessionId = window.testEvents[0].session_id;
            debugLog(`Testing with session ID: ${sessionId}`);
            
            // Filter events for session
            const sessionEvents = window.testEvents.filter(event => {
                const eventSessionId = event.session_id || (event.data && event.data.session_id);
                return eventSessionId === sessionId;
            });
            
            debugLog(`Filtered ${sessionEvents.length} events for session ${sessionId}`);
            
            sessionEvents.forEach((event, index) => {
                debugLog(`  Event ${index + 1}: ${event.hook_event_name} - ${event.subtype || 'no subtype'}`);
            });
        }
        
        // Initialize when page loads
        window.addEventListener('load', () => {
            debugLog('Page loaded, starting tests...');
            setTimeout(() => {
                testLibraryLoading();
            }, 1000);
        });
    </script>
    
    <!-- Load HUD components for testing -->
    <script src="../src/claude_mpm/dashboard/static/js/components/hud-library-loader.js"></script>
    <script src="../src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"></script>
    <script src="../src/claude_mpm/dashboard/static/js/components/hud-manager.js"></script>
</body>
</html>"""
    
    debug_html_path = project_root / "debug_hud.html"
    debug_html_path.write_text(debug_html)
    
    print(f"✅ Created HUD debug HTML at: {debug_html_path}")
    print(f"   Open in browser: file://{debug_html_path}")
    
    return debug_html_path

def enhance_hud_debugging():
    """Add comprehensive debugging to HUD components"""
    
    # Add debugging to HUD visualizer's processExistingEvents method
    hud_visualizer_path = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
    
    if not hud_visualizer_path.exists():
        print(f"❌ HUD visualizer not found at: {hud_visualizer_path}")
        return
    
    content = hud_visualizer_path.read_text()
    
    # Check if debugging is already added
    if "[HUD-VISUALIZER-DEBUG]" in content:
        print("✅ HUD visualizer already has debugging")
    else:
        # Add debugging to processExistingEvents method
        old_method = """    processExistingEvents(events) {
        if (!this.librariesLoaded || !this.cy) {
            console.warn('HUD libraries not loaded, cannot process existing events');
            return;
        }

        console.log(`🏗️ Building HUD tree structure from ${events.length} historical events`);"""
        
        new_method = """    processExistingEvents(events) {
        console.log(`[HUD-VISUALIZER-DEBUG] processExistingEvents called with ${events ? events.length : 0} events`);
        
        if (!events) {
            console.error('[HUD-VISUALIZER-DEBUG] No events provided to processExistingEvents');
            return;
        }
        
        if (!Array.isArray(events)) {
            console.error('[HUD-VISUALIZER-DEBUG] Events is not an array:', typeof events);
            return;
        }
        
        console.log(`[HUD-VISUALIZER-DEBUG] Libraries loaded: ${this.librariesLoaded}, Cytoscape available: ${!!this.cy}`);
        
        if (!this.librariesLoaded || !this.cy) {
            console.warn('[HUD-VISUALIZER-DEBUG] HUD libraries not loaded, cannot process existing events');
            console.log(`[HUD-VISUALIZER-DEBUG] Storing ${events.length} events as pending`);
            this.pendingEvents = [...events];
            return;
        }

        console.log(`[HUD-VISUALIZER-DEBUG] 🏗️ Building HUD tree structure from ${events.length} historical events`);
        
        // Log sample events to understand structure
        if (events.length > 0) {
            console.log('[HUD-VISUALIZER-DEBUG] Sample events:');
            events.slice(0, 3).forEach((event, i) => {
                console.log(`[HUD-VISUALIZER-DEBUG]   Event ${i + 1}:`, {
                    timestamp: event.timestamp,
                    hook_event_name: event.hook_event_name,
                    type: event.type,
                    subtype: event.subtype,
                    session_id: event.session_id,
                    data_session_id: event.data?.session_id,
                    data_keys: event.data ? Object.keys(event.data) : 'no data'
                });
            });
        }"""
        
        content = content.replace(old_method, new_method)
        
        # Add debugging to buildSessionTree method
        old_build = """    buildSessionTree(sessionId, sessionEvents) {
        const sessionNodes = new Map(); // Track nodes created for this session
        let sessionRootNode = null;
        
        // Sort events chronologically within the session
        const sortedEvents = sessionEvents.sort((a, b) => {
            return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        });"""
        
        new_build = """    buildSessionTree(sessionId, sessionEvents) {
        console.log(`[HUD-VISUALIZER-DEBUG] Building session tree for ${sessionId} with ${sessionEvents.length} events`);
        
        const sessionNodes = new Map(); // Track nodes created for this session
        let sessionRootNode = null;
        
        // Sort events chronologically within the session
        const sortedEvents = sessionEvents.sort((a, b) => {
            return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        });
        
        console.log(`[HUD-VISUALIZER-DEBUG] Sorted ${sortedEvents.length} events chronologically`);"""
        
        content = content.replace(old_build, new_build)
        
        # Add debugging to addNode method
        old_add_node = """    addNode(id, type, label, data = {}) {
        if (this.nodes.has(id)) {
            return; // Node already exists
        }"""
        
        new_add_node = """    addNode(id, type, label, data = {}) {
        console.log(`[HUD-VISUALIZER-DEBUG] Adding node: ${id} (${type}) - ${label}`);
        
        if (this.nodes.has(id)) {
            console.log(`[HUD-VISUALIZER-DEBUG] Node ${id} already exists, skipping`);
            return; // Node already exists
        }"""
        
        content = content.replace(old_add_node, new_add_node)
        
        # Add debugging to createNodeFromEvent method
        old_create_node = """    createNodeFromEvent(event, sessionId) {
        const eventType = event.hook_event_name || event.type || '';
        const subtype = event.subtype || '';
        const timestamp = new Date(event.timestamp || Date.now());
        
        let nodeId, nodeType, label, isSessionRoot = false;"""
        
        new_create_node = """    createNodeFromEvent(event, sessionId) {
        const eventType = event.hook_event_name || event.type || '';
        const subtype = event.subtype || '';
        const timestamp = new Date(event.timestamp || Date.now());
        
        console.log(`[HUD-VISUALIZER-DEBUG] Creating node from event: ${eventType}/${subtype} for session ${sessionId}`);
        
        let nodeId, nodeType, label, isSessionRoot = false;"""
        
        content = content.replace(old_create_node, new_create_node)
        
        hud_visualizer_path.write_text(content)
        print("✅ Enhanced HUD visualizer with debugging")
    
    # Add debugging to HUD manager's processExistingEventsForHUD method
    hud_manager_path = project_root / "src/claude_mpm/dashboard/static/js/components/hud-manager.js"
    
    if not hud_manager_path.exists():
        print(f"❌ HUD manager not found at: {hud_manager_path}")
        return
    
    content = hud_manager_path.read_text()
    
    # Check if debugging is already added
    if "[HUD-MANAGER-DEBUG]" in content:
        print("✅ HUD manager already has debugging")
    else:
        # Add debugging to processExistingEventsForHUD method
        old_process = """    processExistingEventsForHUD() {
        if (!this.hudVisualizer || !this.eventViewer) return;
        
        console.log('🔄 Processing existing events for HUD visualization...');
        
        // Clear existing visualization
        this.hudVisualizer.clear();
        
        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();"""
        
        new_process = """    processExistingEventsForHUD() {
        console.log('[HUD-MANAGER-DEBUG] processExistingEventsForHUD called');
        
        if (!this.hudVisualizer) {
            console.error('[HUD-MANAGER-DEBUG] No HUD visualizer available');
            return;
        }
        
        if (!this.eventViewer) {
            console.error('[HUD-MANAGER-DEBUG] No event viewer available');
            return;
        }
        
        console.log('[HUD-MANAGER-DEBUG] 🔄 Processing existing events for HUD visualization...');
        
        // Clear existing visualization
        this.hudVisualizer.clear();
        
        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();
        console.log(`[HUD-MANAGER-DEBUG] Retrieved ${allEvents ? allEvents.length : 0} events from event viewer`);
        
        if (!allEvents) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned null/undefined events');
            return;
        }
        
        if (!Array.isArray(allEvents)) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned non-array:', typeof allEvents);
            return;
        }"""
        
        content = content.replace(old_process, new_process)
        
        # Add session filtering debugging
        old_session_check = """        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();
        
        if (allEvents.length === 0) {
            console.log('⚠️ No events available for HUD processing');
            return;
        }
        
        console.log(`📊 Found ${allEvents.length} total events for HUD processing`);
        
        // Sort events by timestamp to ensure chronological processing
        const sortedEvents = allEvents.slice().sort((a, b) => {
            const timeA = new Date(a.timestamp).getTime();
            const timeB = new Date(b.timestamp).getTime();
            return timeA - timeB;
        });"""
        
        new_session_check = """        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();
        console.log(`[HUD-MANAGER-DEBUG] Retrieved ${allEvents ? allEvents.length : 0} events from event viewer`);
        
        if (!allEvents) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned null/undefined events');
            return;
        }
        
        if (!Array.isArray(allEvents)) {
            console.error('[HUD-MANAGER-DEBUG] Event viewer returned non-array:', typeof allEvents);
            return;
        }
        
        if (allEvents.length === 0) {
            console.log('[HUD-MANAGER-DEBUG] ⚠️ No events available for HUD processing');
            return;
        }
        
        console.log(`[HUD-MANAGER-DEBUG] 📊 Found ${allEvents.length} total events for HUD processing`);
        
        // Check if we should filter by selected session
        const selectedSessionId = this.sessionManager?.selectedSessionId;
        console.log(`[HUD-MANAGER-DEBUG] Selected session ID: ${selectedSessionId}`);
        
        let eventsToProcess = allEvents;
        
        if (selectedSessionId && selectedSessionId !== '' && selectedSessionId !== 'all') {
            console.log(`[HUD-MANAGER-DEBUG] Filtering events for session: ${selectedSessionId}`);
            eventsToProcess = allEvents.filter(event => {
                const eventSessionId = event.session_id || (event.data && event.data.session_id);
                const matches = eventSessionId === selectedSessionId;
                if (!matches) {
                    console.log(`[HUD-MANAGER-DEBUG] Event ${event.timestamp} session ${eventSessionId} does not match ${selectedSessionId}`);
                }
                return matches;
            });
            console.log(`[HUD-MANAGER-DEBUG] Filtered to ${eventsToProcess.length} events for session ${selectedSessionId}`);
        } else {
            console.log('[HUD-MANAGER-DEBUG] No session filtering - processing all events');
        }
        
        // Sort events by timestamp to ensure chronological processing
        const sortedEvents = eventsToProcess.slice().sort((a, b) => {
            const timeA = new Date(a.timestamp).getTime();
            const timeB = new Date(b.timestamp).getTime();
            return timeA - timeB;
        });
        
        console.log(`[HUD-MANAGER-DEBUG] Sorted ${sortedEvents.length} events chronologically`);"""
        
        # This replacement is tricky because the text spans multiple sections
        # Let's do it more carefully
        if "Retrieved ${allEvents ? allEvents.length : 0} events from event viewer" not in content:
            # Find and replace the section
            import re
            pattern = r"(// Get all events \(not just filtered ones\) to build complete tree structure\s+const allEvents = this\.eventViewer\.getAllEvents\(\);)\s+(if \(allEvents\.length === 0\) \{[\s\S]*?return;\s+\})\s+(console\.log\(`📊 Found \$\{allEvents\.length\} total events for HUD processing`\);)\s+(// Sort events by timestamp to ensure chronological processing\s+const sortedEvents = allEvents\.slice\(\)\.sort\(\(a, b\) => \{[\s\S]*?\}\);)"
            
            replacement = new_session_check.replace('        // Get all events (not just filtered ones) to build complete tree structure\n        const allEvents = this.eventViewer.getAllEvents();', '')
            
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        hud_manager_path.write_text(content)
        print("✅ Enhanced HUD manager with debugging")

def main():
    print("🔬 Setting up HUD debugging environment...")
    
    # Create debug HTML page
    debug_html_path = create_debug_html()
    
    # Enhance existing components with debugging
    enhance_hud_debugging()
    
    print("\n✅ HUD debugging setup complete!")
    print("\nNext steps:")
    print(f"1. Open the debug page: file://{debug_html_path}")
    print("2. Open browser developer console to see detailed logs")
    print("3. Click through the test buttons to diagnose issues")
    print("4. Check the browser console for [HUD-DEBUG] messages")
    print("5. Test with the actual dashboard after debugging")
    
    print("\nDebugging targets:")
    print("- Event data flow from EventViewer to HUD")
    print("- Session filtering logic")
    print("- Cytoscape library loading")
    print("- Node creation from events")
    print("- Tree structure building")

if __name__ == "__main__":
    main()