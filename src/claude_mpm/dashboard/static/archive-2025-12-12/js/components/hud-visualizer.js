/**
 * HUD Visualizer Component
 * Manages the Cytoscape.js tree visualization for the HUD mode with lazy loading
 */

class HUDVisualizer {
    constructor() {
        this.cy = null;
        this.container = null;
        this.nodes = new Map(); // Map of node IDs to node data
        this.isActive = false;
        this.librariesLoaded = false;
        this.loadingPromise = null;
        this.pendingEvents = []; // Store events received before libraries are loaded

        // Layout configuration
        this.layoutConfig = {
            name: 'dagre',
            rankDir: 'TB', // Top to bottom
            animate: true,
            animationDuration: 500,
            fit: true,
            padding: 30,
            rankSep: 100,
            nodeSep: 80
        };

        // Node type configurations
        this.nodeTypes = {
            PM: {
                color: '#48bb78',
                shape: 'rectangle',
                width: 120,
                height: 40,
                icon: '👤'
            },
            AGENT: {
                color: '#9f7aea',
                shape: 'ellipse',
                width: 100,
                height: 60,
                icon: '🤖'
            },
            TOOL: {
                color: '#4299e1',
                shape: 'diamond',
                width: 80,
                height: 50,
                icon: '🔧'
            },
            TODO: {
                color: '#e53e3e',
                shape: 'triangle',
                width: 70,
                height: 40,
                icon: '📝'
            }
        };
    }

    /**
     * Initialize the HUD visualizer (called at startup)
     */
    initialize() {
        this.container = document.getElementById('hud-cytoscape');
        if (!this.container) {
            console.error('HUD container not found');
            return false;
        }

        // Ensure container has proper attributes for interaction
        this.container.style.pointerEvents = 'auto';
        this.container.style.cursor = 'default';
        this.container.style.position = 'relative';
        this.container.style.zIndex = '1';

        // Setup basic event handlers (not library-dependent)
        this.setupBasicEventHandlers();

        console.log('HUD Visualizer initialized (libraries will load lazily)');
        return true;
    }

    /**
     * Load libraries and initialize Cytoscape when HUD is first activated
     * @returns {Promise} - Promise that resolves when libraries are loaded and Cytoscape is initialized
     */
    async loadLibrariesAndInitialize() {
        if (this.librariesLoaded && this.cy) {
            return Promise.resolve();
        }

        // If already loading, return the existing promise
        if (this.loadingPromise) {
            return this.loadingPromise;
        }

        this.loadingPromise = this._performLazyLoading();
        return this.loadingPromise;
    }

    /**
     * Perform the actual lazy loading process
     * @private
     */
    async _performLazyLoading() {
        try {
            console.log('[HUD-VISUALIZER-DEBUG] _performLazyLoading() called');
            console.log('[HUD-VISUALIZER-DEBUG] Loading HUD visualization libraries...');

            // Show loading indicator
            this.showLoadingIndicator();

            // Load libraries using the HUD library loader
            if (!window.HUDLibraryLoader) {
                throw new Error('HUD Library Loader not available');
            }

            console.log('[HUD-VISUALIZER-DEBUG] HUD Library Loader found, loading libraries...');
            await window.HUDLibraryLoader.loadHUDLibraries((progress) => {
                console.log('[HUD-VISUALIZER-DEBUG] Loading progress:', progress);
                this.updateLoadingProgress(progress);
            });

            // Verify libraries are available
            console.log('[HUD-VISUALIZER-DEBUG] Verifying libraries are loaded...');
            if (typeof window.cytoscape === 'undefined') {
                throw new Error('Cytoscape.js not loaded');
            }
            if (typeof window.dagre === 'undefined') {
                throw new Error('Dagre not loaded');
            }
            if (typeof window.cytoscapeDagre === 'undefined') {
                throw new Error('Cytoscape-dagre not loaded');
            }

            console.log('[HUD-VISUALIZER-DEBUG] All HUD libraries loaded successfully');
            this.librariesLoaded = true;

            // Initialize Cytoscape instance
            console.log('[HUD-VISUALIZER-DEBUG] Initializing Cytoscape...');
            this.initializeCytoscape();

            // Setup library-dependent event handlers
            console.log('[HUD-VISUALIZER-DEBUG] Setting up Cytoscape event handlers...');
            this.setupCytoscapeEventHandlers();

            // Process any pending events
            console.log('[HUD-VISUALIZER-DEBUG] Processing pending events...');
            this.processPendingEvents();

            // Hide loading indicator
            this.hideLoadingIndicator();

            console.log('[HUD-VISUALIZER-DEBUG] HUD Visualizer fully initialized with lazy loading');
            return true;

        } catch (error) {
            console.error('[HUD-VISUALIZER-DEBUG] Failed to load HUD libraries:', error);
            console.error('[HUD-VISUALIZER-DEBUG] Error stack:', error.stack);
            this.showLoadingError(error.message);
            this.librariesLoaded = false;
            this.loadingPromise = null;
            throw error;
        }
    }

    /**
     * Initialize Cytoscape.js instance (called after libraries are loaded)
     */
    initializeCytoscape() {
        if (!this.librariesLoaded || !window.cytoscape) {
            console.error('Cannot initialize Cytoscape: libraries not loaded');
            return;
        }

        // Register dagre extension for hierarchical layouts
        if (typeof window.cytoscape !== 'undefined' && typeof window.cytoscapeDagre !== 'undefined') {
            window.cytoscape.use(window.cytoscapeDagre);
        }

        this.cy = window.cytoscape({
            container: this.container,

            elements: [],

            // Enable user interaction
            userZoomingEnabled: true,
            userPanningEnabled: true,
            boxSelectionEnabled: false,
            autoungrabify: false,
            autounselectify: false,

            style: [
                // Node styles
                {
                    selector: 'node',
                    style: {
                        'background-color': 'data(color)',
                        'border-color': 'data(borderColor)',
                        'border-width': 2,
                        'color': '#ffffff',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'width': 'data(width)',
                        'height': 'data(height)',
                        'shape': 'data(shape)',
                        'text-wrap': 'wrap',
                        'text-max-width': '100px'
                    }
                },

                // Edge styles
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#718096',
                        'target-arrow-color': '#718096',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.2
                    }
                },

                // Node type specific styles
                {
                    selector: '.pm-node',
                    style: {
                        'background-color': '#48bb78',
                        'border-color': '#38a169',
                        'shape': 'rectangle'
                    }
                },

                {
                    selector: '.agent-node',
                    style: {
                        'background-color': '#9f7aea',
                        'border-color': '#805ad5',
                        'shape': 'ellipse'
                    }
                },

                {
                    selector: '.tool-node',
                    style: {
                        'background-color': '#4299e1',
                        'border-color': '#3182ce',
                        'shape': 'diamond'
                    }
                },

                {
                    selector: '.todo-node',
                    style: {
                        'background-color': '#e53e3e',
                        'border-color': '#c53030',
                        'shape': 'triangle'
                    }
                },

                // Hover effects
                {
                    selector: 'node:active',
                    style: {
                        'overlay-opacity': 0.2,
                        'overlay-color': '#000000'
                    }
                }
            ],

            layout: this.layoutConfig
        });

        // Setup resize handler
        this.setupResizeHandler();
    }

    /**
     * Setup basic event handlers (not dependent on libraries)
     */
    setupBasicEventHandlers() {
        // Reset layout button
        const resetBtn = document.getElementById('hud-reset-layout');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetLayout();
            });
        }

        // Center view button
        const centerBtn = document.getElementById('hud-center-view');
        if (centerBtn) {
            centerBtn.addEventListener('click', () => {
                this.centerView();
            });
        }
    }

    /**
     * Setup Cytoscape-dependent event handlers (called after libraries are loaded)
     */
    setupCytoscapeEventHandlers() {
        if (!this.cy) {
            console.warn('[HUD-VISUALIZER-DEBUG] Cannot setup Cytoscape event handlers: no cy instance');
            return;
        }

        console.log('[HUD-VISUALIZER-DEBUG] Setting up Cytoscape event handlers...');

        // Node click events
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            const data = node.data();
            console.log('[HUD-VISUALIZER-DEBUG] Node clicked:', data);

            // Highlight connected nodes
            this.highlightConnectedNodes(node);
        });

        // Background click events
        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                console.log('[HUD-VISUALIZER-DEBUG] Background clicked - resetting highlights');
                // Reset all node styles
                this.cy.nodes().style({
                    'opacity': 1
                });

                this.cy.edges().style({
                    'opacity': 1
                });
            }
        });

        // Mouse events for debugging
        this.cy.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            node.style('opacity', 0.8);
        });

        this.cy.on('mouseout', 'node', (evt) => {
            const node = evt.target;
            node.style('opacity', 1);
        });

        console.log('[HUD-VISUALIZER-DEBUG] Cytoscape event handlers set up successfully');
    }

    /**
     * Setup resize handler for container
     */
    setupResizeHandler() {
        const resizeObserver = new ResizeObserver(() => {
            if (this.cy && this.isActive) {
                this.ensureContainerResize();
            }
        });

        if (this.container) {
            resizeObserver.observe(this.container);
        }
    }

    /**
     * Ensure container is properly resized and visible
     */
    ensureContainerResize() {
        if (!this.cy || !this.container) {
            console.log('[HUD-VISUALIZER-DEBUG] Cannot resize: missing cy or container');
            return;
        }

        // Ensure container can receive events
        this.ensureContainerInteractivity();

        // Log container dimensions
        const containerRect = this.container.getBoundingClientRect();
        console.log('[HUD-VISUALIZER-DEBUG] Container dimensions:', {
            width: containerRect.width,
            height: containerRect.height,
            offsetWidth: this.container.offsetWidth,
            offsetHeight: this.container.offsetHeight,
            isVisible: containerRect.width > 0 && containerRect.height > 0
        });

        // Only proceed if container is visible
        if (containerRect.width > 0 && containerRect.height > 0) {
            console.log('[HUD-VISUALIZER-DEBUG] Container is visible, resizing Cytoscape...');

            try {
                // Force Cytoscape to resize
                this.cy.resize();

                // Log Cytoscape elements
                const nodeCount = this.cy.nodes().length;
                const edgeCount = this.cy.edges().length;
                console.log('[HUD-VISUALIZER-DEBUG] Cytoscape elements after resize:', {
                    nodes: nodeCount,
                    edges: edgeCount
                });

                // If we have nodes, fit and run layout
                if (nodeCount > 0) {
                    console.log('[HUD-VISUALIZER-DEBUG] Running fit and layout...');
                    this.cy.fit();
                    this.runLayout();
                } else {
                    console.log('[HUD-VISUALIZER-DEBUG] No nodes to display');
                }

            } catch (error) {
                console.error('[HUD-VISUALIZER-DEBUG] Error during resize:', error);
            }
        } else {
            console.log('[HUD-VISUALIZER-DEBUG] Container not visible yet, skipping resize');
        }
    }

    /**
     * Ensure container can receive mouse and touch events
     */
    ensureContainerInteractivity() {
        if (!this.container) return;

        // Force container to be interactive
        this.container.style.pointerEvents = 'auto';
        this.container.style.cursor = 'default';
        this.container.style.userSelect = 'none';
        this.container.style.touchAction = 'manipulation';

        // Remove any overlapping elements that might block events
        const parent = this.container.parentElement;
        if (parent) {
            parent.style.pointerEvents = 'auto';
            parent.style.position = 'relative';
        }

        console.log('[HUD-VISUALIZER-DEBUG] Container interactivity ensured');
    }

    /**
     * Activate the HUD visualizer (triggers lazy loading if needed)
     */
    async activate() {
        console.log('[HUD-VISUALIZER-DEBUG] activate() called');
        this.isActive = true;

        try {
            console.log('[HUD-VISUALIZER-DEBUG] Loading libraries and initializing...');
            // Load libraries if not already loaded
            await this.loadLibrariesAndInitialize();

            console.log('[HUD-VISUALIZER-DEBUG] Libraries loaded, cy exists:', !!this.cy);

            // If Cytoscape was destroyed during clearing, recreate it
            if (!this.cy) {
                console.log('[HUD-VISUALIZER-DEBUG] Cytoscape instance missing, recreating...');
                this.initializeCytoscape();
                this.setupCytoscapeEventHandlers();
            }

            if (this.cy) {
                // Wait for container to be visible, then trigger resize and fit
                console.log('[HUD-VISUALIZER-DEBUG] Triggering resize and fit...');

                // Multiple resize attempts to ensure container visibility
                setTimeout(() => {
                    console.log('[HUD-VISUALIZER-DEBUG] First resize attempt...');
                    this.ensureContainerResize();
                }, 50);

                setTimeout(() => {
                    console.log('[HUD-VISUALIZER-DEBUG] Second resize attempt...');
                    this.ensureContainerResize();
                }, 200);

                setTimeout(() => {
                    console.log('[HUD-VISUALIZER-DEBUG] Final resize attempt...');
                    this.ensureContainerResize();
                }, 500);
            }
            console.log('[HUD-VISUALIZER-DEBUG] activate() completed successfully');
        } catch (error) {
            console.error('[HUD-VISUALIZER-DEBUG] Failed to activate HUD:', error);
            console.error('[HUD-VISUALIZER-DEBUG] Error stack:', error.stack);
            // Keep isActive true so user can retry
            throw error; // Re-throw so the promise rejects properly
        }
    }

    /**
     * Deactivate the HUD visualizer
     */
    deactivate() {
        this.isActive = false;
    }

    /**
     * Process pending events that were received before libraries loaded
     */
    processPendingEvents() {
        if (this.pendingEvents.length > 0) {
            console.log(`Processing ${this.pendingEvents.length} pending events`);

            for (const event of this.pendingEvents) {
                this._processEventInternal(event);
            }

            this.pendingEvents = [];
        }
    }

    /**
     * Process existing events from dashboard when HUD is activated
     * This builds the complete tree structure from historical events
     * @param {Array} events - Array of sorted historical events
     */
    processExistingEvents(events) {
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
        }

        // Clear any existing visualization
        this.clear();

        // Group events by session to build proper hierarchies
        const sessionGroups = this.groupEventsBySession(events);

        // Process each session group to build trees
        Object.entries(sessionGroups).forEach(([sessionId, sessionEvents]) => {
            console.log(`  📂 Processing session ${sessionId}: ${sessionEvents.length} events`);
            this.buildSessionTree(sessionId, sessionEvents);
        });

        // Run final layout to organize the complete visualization
        this.runLayout();

        console.log(`✅ HUD tree structure built successfully`);
    }

    /**
     * Group events by session ID for hierarchical processing
     * @param {Array} events - Array of events
     * @returns {Object} Object with session IDs as keys and event arrays as values
     */
    groupEventsBySession(events) {
        const sessionGroups = {};

        events.forEach(event => {
            const sessionId = event.session_id || event.data?.session_id || 'unknown';
            if (!sessionGroups[sessionId]) {
                sessionGroups[sessionId] = [];
            }
            sessionGroups[sessionId].push(event);
        });

        return sessionGroups;
    }

    /**
     * Build a tree structure for a specific session
     * @param {string} sessionId - Session identifier
     * @param {Array} sessionEvents - Events for this session
     */
    buildSessionTree(sessionId, sessionEvents) {
        console.log(`[HUD-VISUALIZER-DEBUG] Building session tree for ${sessionId} with ${sessionEvents.length} events`);

        const sessionNodes = new Map(); // Track nodes created for this session
        let sessionRootNode = null;

        // Sort events chronologically within the session
        const sortedEvents = sessionEvents.sort((a, b) => {
            return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        });

        console.log(`[HUD-VISUALIZER-DEBUG] Sorted ${sortedEvents.length} events chronologically`);

        sortedEvents.forEach((event, index) => {
            const nodeData = this.createNodeFromEvent(event, sessionId);
            if (!nodeData) return;

            // Add the node to visualization
            this.addNode(nodeData.id, nodeData.type, nodeData.label, {
                sessionId: sessionId,
                timestamp: event.timestamp,
                eventData: event,
                isSessionRoot: nodeData.isSessionRoot
            });

            sessionNodes.set(nodeData.id, {
                ...nodeData,
                event: event,
                index: index
            });

            // Track session root node
            if (nodeData.isSessionRoot && !sessionRootNode) {
                sessionRootNode = nodeData.id;
            }

            // Create relationships based on event context
            this.createHierarchicalRelationships(nodeData.id, event, sessionNodes, sessionRootNode);
        });
    }

    /**
     * Create node data from an event
     * @param {Object} event - Event object
     * @param {string} sessionId - Session ID
     * @returns {Object|null} Node data or null if event should be skipped
     */
    createNodeFromEvent(event, sessionId) {
        const eventType = event.hook_event_name || event.type || '';
        const subtype = event.subtype || '';
        const timestamp = new Date(event.timestamp || Date.now());

        console.log(`[HUD-VISUALIZER-DEBUG] Creating node from event: ${eventType}/${subtype} for session ${sessionId}`);

        let nodeId, nodeType, label, isSessionRoot = false;

        // Generate a unique timestamp-based ID suffix
        const timestampId = timestamp.getTime();
        const randomSuffix = Math.random().toString(36).substring(2, 7);

        // Determine node type and create appropriate visualization
        if (eventType === 'session' && subtype === 'started') {
            // Session root node
            nodeType = 'PM';
            label = `Session ${sessionId.substring(0, 8)}...`;
            nodeId = `session-${sessionId.replace(/[^a-zA-Z0-9]/g, '')}`;
            isSessionRoot = true;

        } else if (eventType === 'hook' && subtype === 'user_prompt') {
            // User prompts are major workflow nodes
            nodeType = 'PM';
            const promptPreview = event.data?.prompt_preview || 'User Prompt';
            label = promptPreview.length > 20 ? promptPreview.substring(0, 20) + '...' : promptPreview;
            nodeId = `user-prompt-${timestampId}-${randomSuffix}`;

        } else if (eventType === 'hook' && subtype === 'claude_response') {
            // Claude responses
            nodeType = 'PM';
            label = 'Claude Response';
            nodeId = `claude-response-${timestampId}-${randomSuffix}`;

        } else if (eventType === 'hook' && subtype === 'pre_tool') {
            // Tool calls - pre hook
            nodeType = 'TOOL';
            const toolName = event.data?.tool_name || 'Unknown Tool';
            // Clean tool name for ID
            const cleanToolName = toolName.replace(/[^a-zA-Z0-9]/g, '');
            label = `${toolName}`;
            nodeId = `tool-${cleanToolName}-${timestampId}-${randomSuffix}`;

        } else if (eventType === 'agent' || event.data?.agent_type) {
            // Agent operations
            nodeType = 'AGENT';
            const agentName = event.data?.agent_type || event.data?.agent_name || 'Agent';
            // Clean agent name for ID
            const cleanAgentName = agentName.replace(/[^a-zA-Z0-9]/g, '');
            label = agentName;
            nodeId = `agent-${cleanAgentName}-${timestampId}-${randomSuffix}`;

        } else if (eventType === 'todo' || subtype.includes('todo')) {
            // Todo operations
            nodeType = 'TODO';
            label = 'Todo Update';
            nodeId = `todo-${timestampId}-${randomSuffix}`;

        } else if (eventType === 'hook' && subtype === 'notification') {
            // Skip notifications for cleaner visualization
            return null;

        } else if (eventType === 'log') {
            // Skip log events for cleaner visualization unless they're errors
            const level = event.data?.level || 'info';
            if (!['error', 'critical'].includes(level)) {
                return null;
            }
            nodeType = 'PM';
            label = `${level.toUpperCase()} Log`;
            nodeId = `log-${level}-${timestampId}-${randomSuffix}`;

        } else {
            // Generic event node
            nodeType = 'PM';
            const cleanEventType = eventType.replace(/[^a-zA-Z0-9]/g, '') || 'Event';
            label = eventType || 'Event';
            nodeId = `generic-${cleanEventType}-${timestampId}-${randomSuffix}`;
        }

        return {
            id: nodeId,
            type: nodeType,
            label: label,
            isSessionRoot: isSessionRoot
        };
    }

    /**
     * Create hierarchical relationships between nodes based on event context
     * @param {string} nodeId - Current node ID
     * @param {Object} event - Current event
     * @param {Map} sessionNodes - Map of all nodes in this session
     * @param {string} sessionRootNode - Root node ID for this session
     */
    createHierarchicalRelationships(nodeId, event, sessionNodes, sessionRootNode) {
        const eventType = event.hook_event_name || event.type || '';
        const subtype = event.subtype || '';

        // Find appropriate parent node based on event context
        let parentNodeId = null;

        if (eventType === 'session' && subtype === 'started') {
            // Session start nodes have no parent
            return;

        } else if (eventType === 'hook' && subtype === 'pre_tool') {
            // Tool calls should connect to the most recent user prompt or agent
            parentNodeId = this.findRecentParentNode(sessionNodes, ['user-prompt', 'agent'], nodeId);

        } else if (eventType === 'hook' && subtype === 'claude_response') {
            // Claude responses should connect to user prompts
            parentNodeId = this.findRecentParentNode(sessionNodes, ['user-prompt'], nodeId);

        } else if (eventType === 'agent') {
            // Agents should connect to user prompts or other agents (delegation)
            parentNodeId = this.findRecentParentNode(sessionNodes, ['user-prompt', 'agent'], nodeId);

        } else if (eventType === 'todo') {
            // Todos should connect to agents or user prompts
            parentNodeId = this.findRecentParentNode(sessionNodes, ['agent', 'user-prompt'], nodeId);

        } else {
            // Default: connect to most recent significant node
            parentNodeId = this.findRecentParentNode(sessionNodes, ['user-prompt', 'agent', 'session'], nodeId);
        }

        // If no specific parent found, connect to session root
        if (!parentNodeId && sessionRootNode && nodeId !== sessionRootNode) {
            parentNodeId = sessionRootNode;
        }

        // Create the edge if parent exists
        if (parentNodeId && parentNodeId !== nodeId) {
            this.addEdge(parentNodeId, nodeId);
        }
    }

    /**
     * Find the most recent parent node of specified types
     * @param {Map} sessionNodes - Map of session nodes
     * @param {Array} nodeTypes - Array of node type prefixes to search for
     * @param {string} currentNodeId - Current node ID to exclude from search
     * @returns {string|null} Parent node ID or null
     */
    findRecentParentNode(sessionNodes, nodeTypes, currentNodeId) {
        const nodeEntries = Array.from(sessionNodes.entries()).reverse(); // Most recent first

        for (const [nodeId, nodeData] of nodeEntries) {
            if (nodeId === currentNodeId) continue; // Skip current node

            // Check if this node matches any of the desired parent types
            for (const typePrefix of nodeTypes) {
                if (nodeId.startsWith(typePrefix)) {
                    return nodeId;
                }
            }
        }

        return null;
    }

    /**
     * Process a socket event and add appropriate nodes/edges
     * @param {Object} event - Socket event data
     */
    processEvent(event) {
        if (!this.isActive) return;

        // If libraries aren't loaded yet, store the event for later processing
        if (!this.librariesLoaded || !this.cy) {
            this.pendingEvents.push(event);
            return;
        }

        this._processEventInternal(event);
    }

    /**
     * Internal event processing (assumes libraries are loaded)
     * @private
     */
    _processEventInternal(event) {
        const eventType = event.hook_event_name || event.type || '';
        const sessionId = event.session_id || 'unknown';
        const timestamp = new Date(event.timestamp || Date.now());

        // Create a unique node ID based on event type and data
        let nodeId = `${eventType}-${timestamp.getTime()}`;
        let nodeType = 'PM';
        let label = eventType;

        // Determine node type based on event
        if (eventType.includes('tool_call')) {
            nodeType = 'TOOL';
            const toolName = event.data?.tool_name || 'Unknown Tool';
            label = toolName;
            nodeId = `tool-${toolName}-${timestamp.getTime()}`;
        } else if (eventType.includes('agent')) {
            nodeType = 'AGENT';
            const agentName = event.data?.agent_name || 'Agent';
            label = agentName;
            nodeId = `agent-${agentName}-${timestamp.getTime()}`;
        } else if (eventType.includes('todo')) {
            nodeType = 'TODO';
            label = 'Todo List';
            nodeId = `todo-${timestamp.getTime()}`;
        } else if (eventType.includes('user_prompt') || eventType.includes('claude_response')) {
            nodeType = 'PM';
            label = eventType.includes('user_prompt') ? 'User Prompt' : 'Claude Response';
            nodeId = `pm-${label.replace(' ', '')}-${timestamp.getTime()}`;
        }

        // Add the node
        this.addNode(nodeId, nodeType, label, {
            sessionId: sessionId,
            timestamp: timestamp.toISOString(),
            eventData: event
        });

        // Add edges based on relationships
        this.createEventRelationships(nodeId, event);
    }

    /**
     * Add a node to the visualization
     * @param {string} id - Unique node identifier
     * @param {string} type - Node type (PM, AGENT, TOOL, TODO)
     * @param {string} label - Node label
     * @param {Object} data - Additional node data
     */
    addNode(id, type, label, data = {}) {
        console.log(`[HUD-VISUALIZER-DEBUG] Adding node: ${id} (${type}) - ${label}`);

        if (this.nodes.has(id)) {
            console.log(`[HUD-VISUALIZER-DEBUG] Node ${id} already exists, skipping`);
            return; // Node already exists
        }

        const nodeType = this.nodeTypes[type] || this.nodeTypes.PM;
        const nodeData = {
            id: id,
            label: `${nodeType.icon} ${label}`,
            type: type,
            color: nodeType.color,
            borderColor: this.darkenColor(nodeType.color, 20),
            shape: nodeType.shape,
            width: nodeType.width,
            height: nodeType.height,
            ...data
        };

        this.nodes.set(id, nodeData);

        if (this.cy) {
            const element = {
                group: 'nodes',
                data: nodeData,
                classes: `${type.toLowerCase()}-node`
            };

            console.log(`[HUD-VISUALIZER-DEBUG] Adding node element to Cytoscape:`, element);
            this.cy.add(element);
            console.log(`[HUD-VISUALIZER-DEBUG] Node added successfully. Total nodes in cy: ${this.cy.nodes().length}`);
            this.runLayout();
        }
    }

    /**
     * Add an edge between two nodes
     * @param {string} sourceId - Source node ID
     * @param {string} targetId - Target node ID
     * @param {string} edgeId - Unique edge identifier
     * @param {Object} data - Additional edge data
     */
    addEdge(sourceId, targetId, edgeId = null, data = {}) {
        if (!sourceId || !targetId) {
            console.warn(`[HUD-VISUALIZER-DEBUG] Cannot create edge: missing source (${sourceId}) or target (${targetId})`);
            return;
        }

        if (sourceId === targetId) {
            console.warn(`[HUD-VISUALIZER-DEBUG] Cannot create self-loop edge from ${sourceId} to itself`);
            return;
        }

        if (!edgeId) {
            edgeId = `edge-${sourceId}-to-${targetId}`;
        }

        if (this.cy) {
            // Check if edge already exists
            const existingEdge = this.cy.getElementById(edgeId);
            if (existingEdge.length > 0) {
                console.log(`[HUD-VISUALIZER-DEBUG] Edge ${edgeId} already exists, skipping`);
                return;
            }

            // Check if nodes exist
            const sourceNode = this.cy.getElementById(sourceId);
            const targetNode = this.cy.getElementById(targetId);

            if (sourceNode.length === 0) {
                console.warn(`[HUD-VISUALIZER-DEBUG] Source node ${sourceId} does not exist, cannot create edge`);
                return;
            }

            if (targetNode.length === 0) {
                console.warn(`[HUD-VISUALIZER-DEBUG] Target node ${targetId} does not exist, cannot create edge`);
                return;
            }

            const element = {
                group: 'edges',
                data: {
                    id: edgeId,
                    source: sourceId,
                    target: targetId,
                    ...data
                }
            };

            console.log(`[HUD-VISUALIZER-DEBUG] Adding edge element to Cytoscape:`, element);

            try {
                this.cy.add(element);
                console.log(`[HUD-VISUALIZER-DEBUG] Edge added successfully. Total edges in cy: ${this.cy.edges().length}`);
                this.runLayout();
            } catch (error) {
                console.error(`[HUD-VISUALIZER-DEBUG] Failed to add edge ${edgeId}:`, error);
                console.error(`[HUD-VISUALIZER-DEBUG] Element details:`, element);
            }
        }
    }

    /**
     * Create relationships between events
     * @param {string} nodeId - Current node ID
     * @param {Object} event - Event data
     */
    createEventRelationships(nodeId, event) {
        const eventType = event.hook_event_name || event.type || '';
        const sessionId = event.session_id || 'unknown';

        // Find parent nodes based on event relationships
        const allNodeEntries = Array.from(this.nodes.entries());

        // Tool call relationships
        if (eventType.includes('tool_call') && event.data?.tool_name) {
            // Connect tool calls to their invoking agent/PM nodes
            const parentNode = this.findParentNode(sessionId, ['PM', 'AGENT']);
            if (parentNode) {
                this.addEdge(parentNode, nodeId);
                return;
            }
        }

        // Agent delegation relationships
        if (eventType.includes('agent') || event.data?.agent_name) {
            // Connect agents to PM nodes
            const pmNode = this.findParentNode(sessionId, ['PM']);
            if (pmNode) {
                this.addEdge(pmNode, nodeId);
                return;
            }
        }

        // Todo relationships - connect to agent or PM nodes
        if (eventType.includes('todo')) {
            const parentNode = this.findParentNode(sessionId, ['AGENT', 'PM']);
            if (parentNode) {
                this.addEdge(parentNode, nodeId);
                return;
            }
        }

        // Default sequential relationship
        const allNodes = Array.from(this.nodes.keys());
        const currentIndex = allNodes.indexOf(nodeId);

        if (currentIndex > 0) {
            const previousNodeId = allNodes[currentIndex - 1];
            this.addEdge(previousNodeId, nodeId);
        }
    }

    /**
     * Find a parent node of specific types for the same session
     * @param {string} sessionId - Session ID
     * @param {Array} nodeTypes - Array of node types to search for
     * @returns {string|null} - Parent node ID or null
     */
    findParentNode(sessionId, nodeTypes) {
        const nodeEntries = Array.from(this.nodes.entries()).reverse(); // Start from most recent

        for (const [nodeId, nodeData] of nodeEntries) {
            if (nodeData.sessionId === sessionId && nodeTypes.includes(nodeData.type)) {
                return nodeId;
            }
        }

        return null;
    }

    /**
     * Highlight connected nodes
     * @param {Object} node - Cytoscape node object
     */
    highlightConnectedNodes(node) {
        if (!this.cy) return;

        // Reset all node styles
        this.cy.nodes().style({
            'opacity': 0.3
        });

        this.cy.edges().style({
            'opacity': 0.2
        });

        // Highlight selected node and its neighborhood
        const neighborhood = node.neighborhood();
        node.style('opacity', 1);
        neighborhood.style('opacity', 1);
    }

    /**
     * Reset layout
     */
    resetLayout() {
        if (this.cy) {
            this.cy.layout(this.layoutConfig).run();
        }
    }

    /**
     * Center view
     */
    centerView() {
        if (this.cy) {
            this.cy.fit();
            this.cy.center();
        }
    }

    /**
     * Run layout animation
     */
    runLayout() {
        console.log(`[HUD-VISUALIZER-DEBUG] runLayout called - isActive: ${this.isActive}, cy exists: ${!!this.cy}`);
        if (this.cy && this.isActive) {
            const nodeCount = this.cy.nodes().length;
            const edgeCount = this.cy.edges().length;
            console.log(`[HUD-VISUALIZER-DEBUG] Running layout with ${nodeCount} nodes and ${edgeCount} edges`);

            // Check container dimensions before layout
            if (this.container) {
                const rect = this.container.getBoundingClientRect();
                console.log(`[HUD-VISUALIZER-DEBUG] Container dimensions before layout:`, {
                    width: rect.width,
                    height: rect.height,
                    offsetWidth: this.container.offsetWidth,
                    offsetHeight: this.container.offsetHeight
                });
            }

            const layout = this.cy.layout(this.layoutConfig);

            // Listen for layout completion
            layout.on('layoutstop', () => {
                console.log(`[HUD-VISUALIZER-DEBUG] Layout completed. Final node positions:`);
                this.cy.nodes().forEach((node, index) => {
                    const position = node.position();
                    const data = node.data();
                    console.log(`[HUD-VISUALIZER-DEBUG]   Node ${index + 1}: ${data.label} at (${position.x.toFixed(1)}, ${position.y.toFixed(1)})`);
                });
            });

            layout.run();
        } else {
            console.log(`[HUD-VISUALIZER-DEBUG] Skipping layout - not active or no Cytoscape instance`);
        }
    }

    /**
     * Clear all nodes and edges
     */
    clear() {
        console.log(`[HUD-VISUALIZER-DEBUG] Clearing HUD: ${this.nodes.size} nodes, ${this.pendingEvents.length} pending events`);
        this.nodes.clear();
        this.pendingEvents = [];
        if (this.cy) {
            const elementCount = this.cy.elements().length;
            try {
                this.cy.elements().remove();
                console.log(`[HUD-VISUALIZER-DEBUG] Removed ${elementCount} Cytoscape elements`);
            } catch (error) {
                console.error(`[HUD-VISUALIZER-DEBUG] Error clearing Cytoscape elements:`, error);
                // Try to destroy and recreate if clearing fails
                try {
                    this.cy.destroy();
                    this.cy = null;
                    console.log(`[HUD-VISUALIZER-DEBUG] Destroyed Cytoscape instance due to clear error`);
                } catch (destroyError) {
                    console.error(`[HUD-VISUALIZER-DEBUG] Error destroying Cytoscape:`, destroyError);
                }
            }
        }
    }

    /**
     * Show loading indicator
     */
    showLoadingIndicator() {
        if (this.container) {
            this.container.innerHTML = `
                <div class="hud-loading-container">
                    <div class="hud-loading-spinner"></div>
                    <div class="hud-loading-text">Loading HUD visualization libraries...</div>
                    <div class="hud-loading-progress" id="hud-loading-progress"></div>
                </div>
            `;
        }
    }

    /**
     * Update loading progress
     */
    updateLoadingProgress(progress) {
        const progressElement = document.getElementById('hud-loading-progress');
        if (progressElement) {
            if (progress.error) {
                progressElement.innerHTML = `<span class="hud-error">❌ ${progress.message}</span>`;
            } else {
                progressElement.innerHTML = `
                    <div class="hud-progress-bar">
                        <div class="hud-progress-fill" style="width: ${(progress.current / progress.total) * 100}%"></div>
                    </div>
                    <div class="hud-progress-text">${progress.message} (${progress.current}/${progress.total})</div>
                `;
            }
        }
    }

    /**
     * Hide loading indicator
     */
    hideLoadingIndicator() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    /**
     * Show loading error
     */
    showLoadingError(message) {
        if (this.container) {
            this.container.innerHTML = `
                <div class="hud-error-container">
                    <div class="hud-error-icon">⚠️</div>
                    <div class="hud-error-text">Failed to load HUD libraries</div>
                    <div class="hud-error-message">${message}</div>
                    <button class="hud-retry-button" onclick="window.hudVisualizer && window.hudVisualizer.retryLoading()">
                        Retry Loading
                    </button>
                </div>
            `;
        }
    }

    /**
     * Retry loading libraries (called from error UI)
     */
    retryLoading() {
        this.librariesLoaded = false;
        this.loadingPromise = null;
        this.activate();
    }

    /**
     * Debug method to manually test HUD visualizer
     * Can be called from browser console: window.hudVisualizer.debugTest()
     */
    debugTest() {
        console.log('[HUD-VISUALIZER-DEBUG] debugTest() called manually');
        console.log('[HUD-VISUALIZER-DEBUG] Current state:', {
            isActive: this.isActive,
            librariesLoaded: this.librariesLoaded,
            hasCy: !!this.cy,
            hasContainer: !!this.container,
            nodeCount: this.nodes.size,
            pendingEventCount: this.pendingEvents.length,
            hasHUDLibraryLoader: !!window.HUDLibraryLoader
        });

        // Test container
        if (this.container) {
            console.log('[HUD-VISUALIZER-DEBUG] Container info:', {
                id: this.container.id,
                className: this.container.className,
                offsetWidth: this.container.offsetWidth,
                offsetHeight: this.container.offsetHeight,
                innerHTML: this.container.innerHTML ? 'has content' : 'empty'
            });
        }

        // Test library availability
        console.log('[HUD-VISUALIZER-DEBUG] Library availability:', {
            cytoscape: typeof window.cytoscape,
            dagre: typeof window.dagre,
            cytoscapeDagre: typeof window.cytoscapeDagre,
            HUDLibraryLoader: typeof window.HUDLibraryLoader
        });

        return {
            isActive: this.isActive,
            librariesLoaded: this.librariesLoaded,
            hasCy: !!this.cy,
            containerFound: !!this.container
        };
    }

    /**
     * Comprehensive debug method to identify blank screen issues
     * Can be called from browser console: window.hudVisualizer.debugBlankScreen()
     */
    debugBlankScreen() {
        console.log('[HUD-BLANK-SCREEN-DEBUG] =================================');
        console.log('[HUD-BLANK-SCREEN-DEBUG] COMPREHENSIVE BLANK SCREEN DEBUG');
        console.log('[HUD-BLANK-SCREEN-DEBUG] =================================');

        // 1. Check basic state
        const basicState = {
            isActive: this.isActive,
            librariesLoaded: this.librariesLoaded,
            hasCy: !!this.cy,
            hasContainer: !!this.container,
            nodeCount: this.nodes.size,
            cytoscapeElementCount: this.cy ? this.cy.elements().length : 0
        };
        console.log('[HUD-BLANK-SCREEN-DEBUG] 1. Basic State:', basicState);

        // 2. Check container visibility and dimensions
        if (this.container) {
            const containerInfo = this.getContainerDebugInfo();
            console.log('[HUD-BLANK-SCREEN-DEBUG] 2. Container Info:', containerInfo);

            // Add background color to verify container is visible
            this.debugAddContainerBackground();
        } else {
            console.error('[HUD-BLANK-SCREEN-DEBUG] 2. Container not found!');
            return false;
        }

        // 3. Check Cytoscape state
        if (this.cy) {
            const cytoscapeInfo = this.getCytoscapeDebugInfo();
            console.log('[HUD-BLANK-SCREEN-DEBUG] 3. Cytoscape Info:', cytoscapeInfo);
        } else {
            console.error('[HUD-BLANK-SCREEN-DEBUG] 3. Cytoscape instance not found!');
            return false;
        }

        // 4. Check node positions
        this.debugNodePositions();

        // 5. Try manual rendering triggers
        this.debugManualRenderingTriggers();

        // 6. Add test nodes if none exist
        if (this.cy && this.cy.nodes().length === 0) {
            console.log('[HUD-BLANK-SCREEN-DEBUG] 6. No nodes found, adding test nodes...');
            this.debugAddTestNodes();
        }

        // 7. Force zoom fit
        this.debugForceZoomFit();

        console.log('[HUD-BLANK-SCREEN-DEBUG] Debug complete. Check visual results.');
        return true;
    }

    /**
     * Get comprehensive container debug information
     */
    getContainerDebugInfo() {
        const rect = this.container.getBoundingClientRect();
        const computed = window.getComputedStyle(this.container);

        return {
            id: this.container.id,
            className: this.container.className,
            // Dimensions
            offsetWidth: this.container.offsetWidth,
            offsetHeight: this.container.offsetHeight,
            clientWidth: this.container.clientWidth,
            clientHeight: this.container.clientHeight,
            scrollWidth: this.container.scrollWidth,
            scrollHeight: this.container.scrollHeight,
            // Bounding rect
            boundingRect: {
                width: rect.width,
                height: rect.height,
                top: rect.top,
                left: rect.left,
                bottom: rect.bottom,
                right: rect.right
            },
            // Computed styles that affect visibility
            computedStyles: {
                display: computed.display,
                visibility: computed.visibility,
                opacity: computed.opacity,
                position: computed.position,
                overflow: computed.overflow,
                zIndex: computed.zIndex,
                backgroundColor: computed.backgroundColor,
                transform: computed.transform
            },
            // Check if visible
            isVisible: rect.width > 0 && rect.height > 0 && computed.display !== 'none' && computed.visibility !== 'hidden',
            // Parent info
            parentElement: this.container.parentElement ? {
                tagName: this.container.parentElement.tagName,
                className: this.container.parentElement.className,
                offsetWidth: this.container.parentElement.offsetWidth,
                offsetHeight: this.container.parentElement.offsetHeight
            } : null
        };
    }

    /**
     * Get comprehensive Cytoscape debug information
     */
    getCytoscapeDebugInfo() {
        const extent = this.cy.extent();
        const zoom = this.cy.zoom();
        const pan = this.cy.pan();
        const viewport = this.cy.viewport();

        return {
            // Elements
            nodeCount: this.cy.nodes().length,
            edgeCount: this.cy.edges().length,
            elementCount: this.cy.elements().length,
            // Viewport
            zoom: zoom,
            pan: pan,
            extent: extent,
            viewport: viewport,
            // Container
            containerWidth: this.cy.width(),
            containerHeight: this.cy.height(),
            // Check if initialized
            isInitialized: this.cy.scratch('_cytoscape-initialized') !== undefined,
            // Renderer info
            renderer: this.cy.renderer() ? {
                name: this.cy.renderer().name,
                options: this.cy.renderer().options
            } : null
        };
    }

    /**
     * Debug node positions to check if they're outside viewport
     */
    debugNodePositions() {
        if (!this.cy || this.cy.nodes().length === 0) {
            console.log('[HUD-BLANK-SCREEN-DEBUG] 4. No nodes to check positions');
            return;
        }

        console.log('[HUD-BLANK-SCREEN-DEBUG] 4. Node Positions:');
        const nodes = this.cy.nodes();
        const extent = this.cy.extent();
        const viewport = this.cy.viewport();

        console.log('[HUD-BLANK-SCREEN-DEBUG]   Viewport extent:', extent);
        console.log('[HUD-BLANK-SCREEN-DEBUG]   Current viewport:', viewport);

        nodes.forEach((node, index) => {
            const position = node.position();
            const data = node.data();
            const boundingBox = node.boundingBox();

            console.log(`[HUD-BLANK-SCREEN-DEBUG]   Node ${index + 1}:`, {
                id: data.id,
                label: data.label,
                position: position,
                boundingBox: boundingBox,
                isVisible: node.visible(),
                opacity: node.style('opacity'),
                width: node.style('width'),
                height: node.style('height')
            });
        });
    }

    /**
     * Add background color to container to verify it's visible
     */
    debugAddContainerBackground() {
        if (this.container) {
            this.container.style.backgroundColor = '#ff000020'; // Light red background
            this.container.style.border = '2px solid #ff0000'; // Red border
            this.container.style.minHeight = '400px'; // Ensure minimum height
            console.log('[HUD-BLANK-SCREEN-DEBUG] Added red background and border to container for visibility test');
        }
    }

    /**
     * Manual rendering triggers to force Cytoscape to render
     */
    debugManualRenderingTriggers() {
        if (!this.cy) {
            console.log('[HUD-BLANK-SCREEN-DEBUG] 5. No Cytoscape instance for manual rendering');
            return;
        }

        console.log('[HUD-BLANK-SCREEN-DEBUG] 5. Triggering manual rendering operations...');

        try {
            // Force resize
            console.log('[HUD-BLANK-SCREEN-DEBUG]   - Forcing resize...');
            this.cy.resize();

            // Force redraw
            console.log('[HUD-BLANK-SCREEN-DEBUG]   - Forcing redraw...');
            this.cy.forceRender();

            // Force layout
            if (this.cy.nodes().length > 0) {
                console.log('[HUD-BLANK-SCREEN-DEBUG]   - Running layout...');
                this.cy.layout(this.layoutConfig).run();
            }

            // Force viewport update
            console.log('[HUD-BLANK-SCREEN-DEBUG]   - Updating viewport...');
            this.cy.viewport({
                zoom: this.cy.zoom(),
                pan: this.cy.pan()
            });

            console.log('[HUD-BLANK-SCREEN-DEBUG]   Manual rendering triggers completed');
        } catch (error) {
            console.error('[HUD-BLANK-SCREEN-DEBUG]   Error during manual rendering:', error);
        }
    }

    /**
     * Add test nodes to verify Cytoscape is working
     */
    debugAddTestNodes() {
        if (!this.cy) return;

        console.log('[HUD-BLANK-SCREEN-DEBUG]   Adding test nodes...');

        try {
            // Clear existing elements
            this.cy.elements().remove();

            // Add test nodes
            const testNodes = [
                {
                    group: 'nodes',
                    data: {
                        id: 'test-node-1',
                        label: '🤖 Test Node 1',
                        color: '#48bb78',
                        borderColor: '#38a169',
                        shape: 'rectangle',
                        width: 120,
                        height: 40
                    },
                    classes: 'pm-node'
                },
                {
                    group: 'nodes',
                    data: {
                        id: 'test-node-2',
                        label: '🔧 Test Node 2',
                        color: '#4299e1',
                        borderColor: '#3182ce',
                        shape: 'diamond',
                        width: 80,
                        height: 50
                    },
                    classes: 'tool-node'
                },
                {
                    group: 'nodes',
                    data: {
                        id: 'test-node-3',
                        label: '📝 Test Node 3',
                        color: '#e53e3e',
                        borderColor: '#c53030',
                        shape: 'triangle',
                        width: 70,
                        height: 40
                    },
                    classes: 'todo-node'
                }
            ];

            // Add test edges
            const testEdges = [
                {
                    group: 'edges',
                    data: {
                        id: 'test-edge-1',
                        source: 'test-node-1',
                        target: 'test-node-2'
                    }
                },
                {
                    group: 'edges',
                    data: {
                        id: 'test-edge-2',
                        source: 'test-node-2',
                        target: 'test-node-3'
                    }
                }
            ];

            // Add elements to Cytoscape
            this.cy.add(testNodes);
            this.cy.add(testEdges);

            console.log('[HUD-BLANK-SCREEN-DEBUG]   Added 3 test nodes and 2 test edges');

            // Update our internal nodes map
            testNodes.forEach(nodeElement => {
                this.nodes.set(nodeElement.data.id, nodeElement.data);
            });

            // Run layout
            this.runLayout();

        } catch (error) {
            console.error('[HUD-BLANK-SCREEN-DEBUG]   Error adding test nodes:', error);
        }
    }

    /**
     * Force zoom fit after layout with multiple attempts
     */
    debugForceZoomFit() {
        if (!this.cy) return;

        console.log('[HUD-BLANK-SCREEN-DEBUG] 7. Forcing zoom fit...');

        const attemptZoomFit = (attemptNumber) => {
            try {
                console.log(`[HUD-BLANK-SCREEN-DEBUG]   Zoom fit attempt ${attemptNumber}...`);

                // Get current state before fit
                const beforeZoom = this.cy.zoom();
                const beforePan = this.cy.pan();
                const elements = this.cy.elements();

                console.log('[HUD-BLANK-SCREEN-DEBUG]   Before fit:', {
                    zoom: beforeZoom,
                    pan: beforePan,
                    elementCount: elements.length
                });

                if (elements.length > 0) {
                    // Try fit with specific options
                    this.cy.fit(elements, 50); // 50px padding

                    // Get state after fit
                    const afterZoom = this.cy.zoom();
                    const afterPan = this.cy.pan();

                    console.log('[HUD-BLANK-SCREEN-DEBUG]   After fit:', {
                        zoom: afterZoom,
                        pan: afterPan,
                        changed: beforeZoom !== afterZoom || beforePan.x !== afterPan.x || beforePan.y !== afterPan.y
                    });

                    // Force center
                    this.cy.center(elements);

                } else {
                    console.log('[HUD-BLANK-SCREEN-DEBUG]   No elements to fit');
                }

            } catch (error) {
                console.error(`[HUD-BLANK-SCREEN-DEBUG]   Zoom fit attempt ${attemptNumber} failed:`, error);
            }
        };

        // Multiple attempts with delays
        attemptZoomFit(1);
        setTimeout(() => attemptZoomFit(2), 100);
        setTimeout(() => attemptZoomFit(3), 500);
        setTimeout(() => attemptZoomFit(4), 1000);
    }

    /**
     * Quick test to draw a simple shape to verify Cytoscape canvas is working
     */
    debugDrawSimpleShape() {
        if (!this.cy) {
            console.log('[HUD-CANVAS-TEST] No Cytoscape instance');
            return false;
        }

        console.log('[HUD-CANVAS-TEST] Testing Cytoscape canvas rendering...');

        try {
            // Clear everything
            this.cy.elements().remove();

            // Add a single, simple node at center
            this.cy.add({
                group: 'nodes',
                data: {
                    id: 'canvas-test',
                    label: '✅ CANVAS TEST',
                    color: '#ff0000',
                    borderColor: '#000000',
                    width: 200,
                    height: 100,
                    shape: 'rectangle'
                },
                position: { x: 200, y: 200 } // Fixed position
            });

            // Force immediate render
            this.cy.forceRender();

            // Zoom to fit this single node
            this.cy.fit(this.cy.$('#canvas-test'), 50);

            console.log('[HUD-CANVAS-TEST] Canvas test node added and positioned');
            console.log('[HUD-CANVAS-TEST] If you see a red rectangle with "CANVAS TEST", rendering works!');

            return true;

        } catch (error) {
            console.error('[HUD-CANVAS-TEST] Canvas test failed:', error);
            return false;
        }
    }

    /**
     * Utility function to darken a color
     * @param {string} color - Hex color
     * @param {number} percent - Percentage to darken
     * @returns {string} - Darkened hex color
     */
    darkenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) - amt;
        const G = (num >> 8 & 0x00FF) - amt;
        const B = (num & 0x0000FF) - amt;
        return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }
}

// Export for use in dashboard
window.HUDVisualizer = HUDVisualizer;
