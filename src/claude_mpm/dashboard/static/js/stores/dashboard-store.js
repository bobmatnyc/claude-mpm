/**
 * Shared Zustand Store for Dashboard Components
 * This store manages all dashboard state and socket events
 */

(function(window) {
    'use strict';

    // Store will be initialized when Zustand is loaded
    let store = null;
    let subscribe = null;
    let getState = null;
    let setState = null;

    /**
     * Initialize the dashboard store
     * @param {Object} zustand - The Zustand vanilla module
     */
    function initializeStore(zustand) {
        const storeApi = zustand.createStore((set, get) => ({
            // Connection State
            socket: null,
            isConnected: false,
            connectionError: null,
            reconnectAttempts: 0,
            lastHeartbeat: null,

            // Session State
            currentSession: null,
            sessions: [],

            // Events
            events: [],
            maxEvents: 1000,
            eventFilters: {
                type: null,
                agent: null,
                tool: null,
                search: ''
            },

            // Agents
            agents: new Map(),
            agentHierarchy: [],
            activeAgent: null,

            // Tools
            tools: new Map(),
            toolOperations: [],
            activeTools: new Set(),

            // Files
            files: new Map(),
            fileOperations: [],
            fileTree: {},
            workingDirectory: null,

            // Activity
            activityTree: [],
            activityNodes: new Map(),

            // UI State
            debugMode: false,
            autoScroll: true,
            theme: 'dark',

            // Statistics
            stats: {
                totalEvents: 0,
                eventsPerSecond: 0,
                agentCount: 0,
                toolCount: 0,
                fileCount: 0,
                sessionDuration: 0
            },

            // Actions
            actions: {
                // Connection Management
                setSocket: (socket) => set({ socket }),

                setConnected: (isConnected) => set({
                    isConnected,
                    connectionError: isConnected ? null : get().connectionError,
                    reconnectAttempts: isConnected ? 0 : get().reconnectAttempts
                }),

                setConnectionError: (error) => set({
                    connectionError: error,
                    isConnected: false
                }),

                incrementReconnectAttempts: () => set(state => ({
                    reconnectAttempts: state.reconnectAttempts + 1
                })),

                updateHeartbeat: () => set({ lastHeartbeat: Date.now() }),

                // Session Management
                setCurrentSession: (session) => set({ currentSession: session }),

                addSession: (session) => set(state => ({
                    sessions: [...state.sessions, session].slice(-50) // Keep last 50 sessions
                })),

                // Event Processing
                addEvent: (event) => set(state => {
                    const events = [...state.events, {
                        ...event,
                        timestamp: event.timestamp || Date.now(),
                        id: event.id || `${Date.now()}-${Math.random()}`
                    }];

                    // Keep only maxEvents
                    if (events.length > state.maxEvents) {
                        events.splice(0, events.length - state.maxEvents);
                    }

                    // Update statistics
                    const stats = { ...state.stats };
                    stats.totalEvents++;

                    return {
                        events,
                        stats
                    };
                }),

                clearEvents: () => set({
                    events: [],
                    stats: { ...get().stats, totalEvents: 0 }
                }),

                setEventFilter: (filterType, value) => set(state => ({
                    eventFilters: { ...state.eventFilters, [filterType]: value }
                })),

                // Agent Management
                updateAgent: (agentId, data) => set(state => {
                    const agents = new Map(state.agents);
                    const existing = agents.get(agentId) || {};
                    agents.set(agentId, {
                        ...existing,
                        ...data,
                        id: agentId,
                        lastUpdate: Date.now()
                    });

                    return {
                        agents,
                        stats: { ...state.stats, agentCount: agents.size }
                    };
                }),

                removeAgent: (agentId) => set(state => {
                    const agents = new Map(state.agents);
                    agents.delete(agentId);
                    return {
                        agents,
                        stats: { ...state.stats, agentCount: agents.size }
                    };
                }),

                setActiveAgent: (agentId) => set({ activeAgent: agentId }),

                updateAgentHierarchy: (hierarchy) => set({ agentHierarchy: hierarchy }),

                // Tool Management
                updateTool: (toolId, data) => set(state => {
                    const tools = new Map(state.tools);
                    const existing = tools.get(toolId) || {};
                    tools.set(toolId, {
                        ...existing,
                        ...data,
                        id: toolId,
                        lastUpdate: Date.now()
                    });

                    // Update active tools
                    const activeTools = new Set(state.activeTools);
                    if (data.status === 'active' || data.status === 'running') {
                        activeTools.add(toolId);
                    } else if (data.status === 'completed' || data.status === 'error') {
                        activeTools.delete(toolId);
                    }

                    return {
                        tools,
                        activeTools,
                        stats: { ...state.stats, toolCount: tools.size }
                    };
                }),

                addToolOperation: (operation) => set(state => ({
                    toolOperations: [...state.toolOperations, {
                        ...operation,
                        timestamp: Date.now(),
                        id: `${Date.now()}-${Math.random()}`
                    }].slice(-500) // Keep last 500 operations
                })),

                // File Management
                updateFile: (filePath, data) => set(state => {
                    const files = new Map(state.files);
                    const existing = files.get(filePath) || {};
                    files.set(filePath, {
                        ...existing,
                        ...data,
                        path: filePath,
                        lastUpdate: Date.now()
                    });

                    return {
                        files,
                        stats: { ...state.stats, fileCount: files.size }
                    };
                }),

                addFileOperation: (operation) => set(state => ({
                    fileOperations: [...state.fileOperations, {
                        ...operation,
                        timestamp: Date.now(),
                        id: `${Date.now()}-${Math.random()}`
                    }].slice(-500) // Keep last 500 operations
                })),

                updateFileTree: (tree) => set({ fileTree: tree }),

                setWorkingDirectory: (dir) => set({ workingDirectory: dir }),

                // Activity Management
                addActivityNode: (node) => set(state => {
                    const activityNodes = new Map(state.activityNodes);
                    activityNodes.set(node.id, {
                        ...node,
                        timestamp: Date.now()
                    });

                    // Build tree structure
                    const activityTree = buildActivityTree(activityNodes);

                    return { activityNodes, activityTree };
                }),

                clearActivity: () => set({
                    activityTree: [],
                    activityNodes: new Map()
                }),

                // UI State
                toggleDebugMode: () => set(state => ({ debugMode: !state.debugMode })),

                toggleAutoScroll: () => set(state => ({ autoScroll: !state.autoScroll })),

                setTheme: (theme) => set({ theme }),

                // Bulk Updates
                processSocketEvent: (eventType, data) => {
                    const actions = get().actions;

                    // Add to events list
                    actions.addEvent({ type: eventType, data });

                    // Process based on event type
                    switch(eventType) {
                        case 'agent_start':
                        case 'agent_update':
                        case 'agent_complete':
                            if (data.agent_id) {
                                actions.updateAgent(data.agent_id, data);
                            }
                            break;

                        case 'tool_start':
                        case 'tool_update':
                        case 'tool_complete':
                        case 'tool_error':
                            if (data.tool_id || data.tool) {
                                const toolId = data.tool_id || data.tool;
                                actions.updateTool(toolId, data);
                                actions.addToolOperation({
                                    type: eventType,
                                    tool: toolId,
                                    ...data
                                });
                            }
                            break;

                        case 'file_read':
                        case 'file_write':
                        case 'file_edit':
                        case 'file_delete':
                            if (data.file_path) {
                                actions.updateFile(data.file_path, {
                                    operation: eventType.replace('file_', ''),
                                    ...data
                                });
                                actions.addFileOperation({
                                    type: eventType,
                                    path: data.file_path,
                                    ...data
                                });
                            }
                            break;

                        case 'session_start':
                        case 'session_update':
                            actions.setCurrentSession(data);
                            actions.addSession(data);
                            break;

                        case 'working_directory':
                            actions.setWorkingDirectory(data.path || data.directory);
                            break;

                        case 'activity_node':
                            actions.addActivityNode(data);
                            break;

                        case 'heartbeat':
                            actions.updateHeartbeat();
                            break;

                        case 'connected':
                            actions.setConnected(true);
                            break;

                        case 'disconnected':
                            actions.setConnected(false);
                            break;

                        case 'error':
                            actions.setConnectionError(data.message || data.error);
                            break;
                    }

                    // Log in debug mode
                    if (get().debugMode) {
                        console.log(`[DashboardStore] Event: ${eventType}`, data);
                    }
                },

                // Reset store
                reset: () => set({
                    events: [],
                    agents: new Map(),
                    tools: new Map(),
                    files: new Map(),
                    toolOperations: [],
                    fileOperations: [],
                    activityTree: [],
                    activityNodes: new Map(),
                    stats: {
                        totalEvents: 0,
                        eventsPerSecond: 0,
                        agentCount: 0,
                        toolCount: 0,
                        fileCount: 0,
                        sessionDuration: 0
                    }
                })
            },

            // Computed getters
            getFilteredEvents: () => {
                const state = get();
                let filtered = state.events;

                if (state.eventFilters.type) {
                    filtered = filtered.filter(e => e.type === state.eventFilters.type);
                }
                if (state.eventFilters.agent) {
                    filtered = filtered.filter(e => e.data?.agent_id === state.eventFilters.agent);
                }
                if (state.eventFilters.tool) {
                    filtered = filtered.filter(e => e.data?.tool === state.eventFilters.tool);
                }
                if (state.eventFilters.search) {
                    const search = state.eventFilters.search.toLowerCase();
                    filtered = filtered.filter(e =>
                        JSON.stringify(e).toLowerCase().includes(search)
                    );
                }

                return filtered;
            },

            getAgentsList: () => Array.from(get().agents.values()),

            getToolsList: () => Array.from(get().tools.values()),

            getFilesList: () => Array.from(get().files.values()),

            getActiveToolsList: () => {
                const state = get();
                return Array.from(state.activeTools).map(id => state.tools.get(id)).filter(Boolean);
            }
        }));

        // Extract store methods
        store = storeApi;
        subscribe = storeApi.subscribe;
        getState = storeApi.getState;
        setState = storeApi.setState;

        return storeApi;
    }

    /**
     * Build hierarchical activity tree from flat nodes
     */
    function buildActivityTree(nodes) {
        const tree = [];
        const nodeMap = new Map();

        // First pass: create all nodes
        nodes.forEach((node, id) => {
            nodeMap.set(id, {
                ...node,
                children: []
            });
        });

        // Second pass: build tree structure
        nodeMap.forEach(node => {
            if (node.parentId && nodeMap.has(node.parentId)) {
                nodeMap.get(node.parentId).children.push(node);
            } else {
                tree.push(node);
            }
        });

        return tree;
    }

    /**
     * Format bytes to human readable
     */
    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Format duration to human readable
     */
    function formatDuration(ms) {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
        return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
    }

    /**
     * Connect to Socket.IO server
     */
    function connectSocket(io, url = 'http://localhost:8765') {
        if (!store) {
            console.error('[DashboardStore] Store not initialized');
            return null;
        }

        // Enhanced connection options for better compatibility
        const socket = io(url, {
            transports: ['polling', 'websocket'], // Start with polling for better compatibility
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            forceNew: true, // Force new connection
            withCredentials: false, // Disable credentials for CORS
            path: '/socket.io/' // Explicit Socket.IO path
        });

        const actions = getState().actions;
        actions.setSocket(socket);

        // Socket event handlers
        socket.on('connect', () => {
            console.log('[DashboardStore] Connected to server');
            console.log('[DashboardStore] Socket ID:', socket.id);
            actions.setConnected(true);
            actions.processSocketEvent('connected', { timestamp: Date.now(), socketId: socket.id });
        });

        socket.on('disconnect', (reason) => {
            console.log('[DashboardStore] Disconnected:', reason);
            actions.setConnected(false);
            actions.processSocketEvent('disconnected', { reason });
        });

        socket.on('connect_error', (error) => {
            console.error('[DashboardStore] Connection error:', error.message);
            console.error('[DashboardStore] Error type:', error.type);
            actions.setConnectionError(error.message || 'Connection error');
        });

        socket.on('error', (error) => {
            console.error('[DashboardStore] Socket error:', error);
            actions.setConnectionError(error.message || 'Socket error');
        });

        socket.on('reconnect_attempt', (attemptNumber) => {
            console.log('[DashboardStore] Reconnection attempt:', attemptNumber);
            actions.incrementReconnectAttempts();
        });

        socket.on('reconnect', (attemptNumber) => {
            console.log('[DashboardStore] Reconnected after', attemptNumber, 'attempts');
        });

        socket.on('heartbeat', (data) => {
            actions.updateHeartbeat();
        });

        // Listen for all events and process them
        const allEvents = [
            'agent_start', 'agent_update', 'agent_complete', 'agent_error',
            'tool_start', 'tool_update', 'tool_complete', 'tool_error',
            'file_read', 'file_write', 'file_edit', 'file_delete',
            'session_start', 'session_update', 'session_end',
            'working_directory', 'activity_node', 'code_analysis',
            'message', 'log', 'debug', 'info', 'warning', 'error'
        ];

        allEvents.forEach(eventType => {
            socket.on(eventType, (data) => {
                actions.processSocketEvent(eventType, data);
            });
        });

        // Generic event handler for unknown events
        socket.onAny((eventName, ...args) => {
            if (!allEvents.includes(eventName) && eventName !== 'connect' && eventName !== 'disconnect') {
                console.log('[DashboardStore] Unknown event:', eventName, args);
                actions.processSocketEvent(eventName, args[0] || {});
            }
        });

        return socket;
    }

    // Export public API
    window.DashboardStore = {
        initializeStore,
        connectSocket,
        getStore: () => store,
        getState: () => getState ? getState() : null,
        setState: (partial) => setState ? setState(partial) : null,
        subscribe: (listener) => subscribe ? subscribe(listener) : null,
        utils: {
            formatBytes,
            formatDuration,
            buildActivityTree
        }
    };

})(window);