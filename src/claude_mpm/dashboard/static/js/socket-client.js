/**
 * Socket.IO Client for Claude MPM Dashboard
 * Handles WebSocket connections and event processing
 */

// Access the global io from window object in ES6 module context
const io = window.io;

class SocketClient {
    constructor() {
        this.socket = null;
        this.port = null; // Store the current port
        this.connectionCallbacks = {
            connect: [],
            disconnect: [],
            error: [],
            event: []
        };
        
        // Event schema validation
        this.eventSchema = {
            required: ['source', 'type', 'subtype', 'timestamp', 'data'],
            optional: ['event', 'session_id']
        };

        // Connection state
        this.isConnected = false;
        this.isConnecting = false;
        this.lastConnectTime = null;
        this.disconnectTime = null;

        // Event processing
        this.events = [];
        this.sessions = new Map();
        this.currentSessionId = null;

        // Event queue for disconnection periods
        this.eventQueue = [];
        this.maxQueueSize = 100;
        
        // Retry configuration
        this.retryAttempts = 0;
        this.maxRetryAttempts = 3;
        this.retryDelays = [1000, 2000, 4000]; // Exponential backoff
        this.pendingEmissions = new Map(); // Track pending emissions for retry
        
        // Health monitoring
        this.lastPingTime = null;
        this.lastPongTime = null;
        this.pingTimeout = 40000; // 40 seconds (server sends every 30s)
        this.healthCheckInterval = null;
        
        // Start periodic status check as fallback mechanism
        this.startStatusCheckFallback();
        this.startHealthMonitoring();
    }

    /**
     * Connect to Socket.IO server
     * @param {string} port - Port number to connect to
     */
    connect(port = '8765') {
        // Store the port for later use
        this.port = port;
        const url = `http://localhost:${port}`;

        // Prevent multiple simultaneous connections
        if (this.socket && (this.socket.connected || this.socket.connecting)) {
            console.log('Already connected or connecting, disconnecting first...');
            this.socket.disconnect();
            // Wait a moment for cleanup
            setTimeout(() => this.doConnect(url), 100);
            return;
        }

        this.doConnect(url);
    }

    /**
     * Perform the actual connection
     * @param {string} url - Socket.IO server URL
     */
    doConnect(url) {
        console.log(`Connecting to Socket.IO server at ${url}`);
        
        // Check if io is available
        if (typeof io === 'undefined') {
            console.error('Socket.IO library not loaded! Make sure socket.io.min.js is loaded before this script.');
            this.notifyConnectionStatus('Socket.IO library not loaded', 'error');
            return;
        }
        
        this.isConnecting = true;
        this.notifyConnectionStatus('Connecting...', 'connecting');

        this.socket = io(url, {
            autoConnect: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 10000,
            maxReconnectionAttempts: 10,
            timeout: 10000,
            forceNew: true,
            transports: ['websocket', 'polling']
        });

        this.setupSocketHandlers();
    }

    /**
     * Setup Socket.IO event handlers
     */
    setupSocketHandlers() {
        this.socket.on('connect', () => {
            console.log('Connected to Socket.IO server');
            const previouslyConnected = this.isConnected;
            this.isConnected = true;
            this.isConnecting = false;
            this.lastConnectTime = Date.now();
            this.retryAttempts = 0; // Reset retry counter on successful connect
            
            // Calculate downtime if this is a reconnection
            if (this.disconnectTime && previouslyConnected === false) {
                const downtime = (Date.now() - this.disconnectTime) / 1000;
                console.log(`Reconnected after ${downtime.toFixed(1)}s downtime`);
                
                // Flush queued events after reconnection
                this.flushEventQueue();
            }
            
            this.notifyConnectionStatus('Connected', 'connected');

            // Emit connect callback
            this.connectionCallbacks.connect.forEach(callback =>
                callback(this.socket.id)
            );

            this.requestStatus();
            // History is now automatically sent by server on connection
            // No need to explicitly request it
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this.isConnected = false;
            this.isConnecting = false;
            this.disconnectTime = Date.now();
            
            // Calculate uptime
            if (this.lastConnectTime) {
                const uptime = (Date.now() - this.lastConnectTime) / 1000;
                console.log(`Connection uptime was ${uptime.toFixed(1)}s`);
            }
            
            this.notifyConnectionStatus(`Disconnected: ${reason}`, 'disconnected');

            // Emit disconnect callback
            this.connectionCallbacks.disconnect.forEach(callback =>
                callback(reason)
            );
            
            // Start auto-reconnect if it was an unexpected disconnect
            if (reason === 'transport close' || reason === 'ping timeout') {
                this.scheduleReconnect();
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.isConnecting = false;
            const errorMsg = error.message || error.description || 'Unknown error';
            this.notifyConnectionStatus(`Connection Error: ${errorMsg}`, 'disconnected');

            // Add error event
            this.addEvent({
                type: 'connection.error',
                timestamp: new Date().toISOString(),
                data: { 
                    error: errorMsg, 
                    url: this.socket.io.uri,
                    retry_attempt: this.retryAttempts
                }
            });

            // Emit error callback
            this.connectionCallbacks.error.forEach(callback =>
                callback(errorMsg)
            );
            
            // Schedule reconnect with backoff
            this.scheduleReconnect();
        });

        // Primary event handler - this is what the server actually emits
        this.socket.on('claude_event', (data) => {
            console.log('Received claude_event:', data);
            
            // Validate event schema
            const validatedEvent = this.validateEventSchema(data);
            if (!validatedEvent) {
                console.warn('Invalid event schema received:', data);
                return;
            }
            
            // Transform event to match expected format (for backward compatibility)
            const transformedEvent = this.transformEvent(validatedEvent);
            console.log('Transformed event:', transformedEvent);
            this.addEvent(transformedEvent);
        });

        // Add ping/pong handlers for health monitoring
        this.socket.on('ping', (data) => {
            // console.log('Received ping from server');
            this.lastPingTime = Date.now();
            
            // Send pong response immediately
            this.socket.emit('pong', { 
                timestamp: data.timestamp,
                client_time: Date.now()
            });
        });
        
        // Session and event handlers (legacy/fallback)
        this.socket.on('session.started', (data) => {
            this.addEvent({ type: 'session', subtype: 'started', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('session.ended', (data) => {
            this.addEvent({ type: 'session', subtype: 'ended', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('claude.request', (data) => {
            this.addEvent({ type: 'claude', subtype: 'request', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('claude.response', (data) => {
            this.addEvent({ type: 'claude', subtype: 'response', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('agent.loaded', (data) => {
            this.addEvent({ type: 'agent', subtype: 'loaded', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('agent.executed', (data) => {
            this.addEvent({ type: 'agent', subtype: 'executed', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('hook.pre', (data) => {
            this.addEvent({ type: 'hook', subtype: 'pre', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('hook.post', (data) => {
            this.addEvent({ type: 'hook', subtype: 'post', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('todo.updated', (data) => {
            this.addEvent({ type: 'todo', subtype: 'updated', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('memory.operation', (data) => {
            this.addEvent({ type: 'memory', subtype: 'operation', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('log.entry', (data) => {
            this.addEvent({ type: 'log', subtype: 'entry', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('history', (data) => {
            console.log('Received event history:', data);
            if (data && Array.isArray(data.events)) {
                console.log(`Processing ${data.events.length} historical events (${data.count} sent, ${data.total_available} total available)`);
                // Add events in the order received (should already be chronological - oldest first)
                // Transform each historical event to match expected format
                data.events.forEach(event => {
                    const transformedEvent = this.transformEvent(event);
                    this.addEvent(transformedEvent, false);
                });
                this.notifyEventUpdate();
                console.log(`Event history loaded: ${data.events.length} events added to dashboard`);
            } else if (Array.isArray(data)) {
                // Handle legacy format for backward compatibility
                console.log('Received legacy event history format:', data.length, 'events');
                data.forEach(event => {
                    const transformedEvent = this.transformEvent(event);
                    this.addEvent(transformedEvent, false);
                });
                this.notifyEventUpdate();
            }
        });

        this.socket.on('system.status', (data) => {
            console.log('Received system status:', data);
            if (data.sessions) {
                this.updateSessions(data.sessions);
            }
            if (data.current_session) {
                this.currentSessionId = data.current_session;
            }
        });
    }

    /**
     * Disconnect from Socket.IO server
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.port = null; // Clear the stored port
        this.isConnected = false;
        this.isConnecting = false;
    }

    /**
     * Emit an event with retry support
     * @param {string} event - Event name
     * @param {any} data - Event data
     * @param {Object} options - Options for retry behavior
     */
    emitWithRetry(event, data = null, options = {}) {
        const { 
            maxRetries = 3,
            retryDelays = [1000, 2000, 4000],
            onSuccess = null,
            onFailure = null
        } = options;
        
        const emissionId = `${event}_${Date.now()}_${Math.random()}`;
        
        const attemptEmission = (attemptNum = 0) => {
            if (!this.socket || !this.socket.connected) {
                // Queue for later if disconnected
                if (attemptNum === 0) {
                    this.queueEvent(event, data);
                    console.log(`Queued ${event} for later emission (disconnected)`);
                    if (onFailure) onFailure('disconnected');
                }
                return;
            }
            
            try {
                // Attempt emission
                this.socket.emit(event, data);
                console.log(`Emitted ${event} successfully`);
                
                // Remove from pending
                this.pendingEmissions.delete(emissionId);
                
                if (onSuccess) onSuccess();
                
            } catch (error) {
                console.error(`Failed to emit ${event} (attempt ${attemptNum + 1}):`, error);
                
                if (attemptNum < maxRetries - 1) {
                    const delay = retryDelays[attemptNum] || retryDelays[retryDelays.length - 1];
                    console.log(`Retrying ${event} in ${delay}ms...`);
                    
                    // Store pending emission
                    this.pendingEmissions.set(emissionId, {
                        event,
                        data,
                        attemptNum: attemptNum + 1,
                        scheduledTime: Date.now() + delay
                    });
                    
                    setTimeout(() => attemptEmission(attemptNum + 1), delay);
                } else {
                    console.error(`Failed to emit ${event} after ${maxRetries} attempts`);
                    this.pendingEmissions.delete(emissionId);
                    if (onFailure) onFailure('max_retries_exceeded');
                }
            }
        };
        
        attemptEmission();
    }
    
    /**
     * Queue an event for later emission
     * @param {string} event - Event name
     * @param {any} data - Event data
     */
    queueEvent(event, data) {
        if (this.eventQueue.length >= this.maxQueueSize) {
            // Remove oldest event if queue is full
            const removed = this.eventQueue.shift();
            console.warn(`Event queue full, dropped oldest event: ${removed.event}`);
        }
        
        this.eventQueue.push({
            event,
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * Flush queued events after reconnection
     */
    flushEventQueue() {
        if (this.eventQueue.length === 0) return;
        
        console.log(`Flushing ${this.eventQueue.length} queued events...`);
        const events = [...this.eventQueue];
        this.eventQueue = [];
        
        // Emit each queued event with a small delay between them
        events.forEach((item, index) => {
            setTimeout(() => {
                if (this.socket && this.socket.connected) {
                    this.socket.emit(item.event, item.data);
                    console.log(`Flushed queued event: ${item.event}`);
                }
            }, index * 100); // 100ms between each event
        });
    }
    
    /**
     * Schedule a reconnection attempt with exponential backoff
     */
    scheduleReconnect() {
        if (this.retryAttempts >= this.maxRetryAttempts) {
            console.log('Max reconnection attempts reached, stopping auto-reconnect');
            this.notifyConnectionStatus('Reconnection failed', 'disconnected');
            return;
        }
        
        const delay = this.retryDelays[this.retryAttempts] || this.retryDelays[this.retryDelays.length - 1];
        this.retryAttempts++;
        
        console.log(`Scheduling reconnect attempt ${this.retryAttempts}/${this.maxRetryAttempts} in ${delay}ms...`);
        this.notifyConnectionStatus(`Reconnecting in ${delay/1000}s...`, 'connecting');
        
        setTimeout(() => {
            if (!this.isConnected && this.port) {
                console.log(`Attempting reconnection ${this.retryAttempts}/${this.maxRetryAttempts}...`);
                this.connect(this.port);
            }
        }, delay);
    }
    
    /**
     * Request server status
     */
    requestStatus() {
        if (this.socket && this.socket.connected) {
            console.log('Requesting server status...');
            this.emitWithRetry('request.status', null, {
                maxRetries: 2,
                retryDelays: [500, 1000]
            });
        }
    }

    /**
     * Request event history from server
     * @param {Object} options - History request options
     * @param {number} options.limit - Maximum number of events to retrieve (default: 50)
     * @param {Array<string>} options.event_types - Optional filter by event types
     */
    requestHistory(options = {}) {
        if (this.socket && this.socket.connected) {
            const params = {
                limit: options.limit || 50,
                event_types: options.event_types || []
            };
            console.log('Requesting event history...', params);
            this.emitWithRetry('get_history', params, {
                maxRetries: 3,
                retryDelays: [1000, 2000, 3000],
                onFailure: (reason) => {
                    console.error(`Failed to request history: ${reason}`);
                }
            });
        } else {
            console.warn('Cannot request history: not connected to server');
        }
    }

    /**
     * Add event to local storage and notify listeners
     * @param {Object} eventData - Event data
     * @param {boolean} notify - Whether to notify listeners (default: true)
     */
    addEvent(eventData, notify = true) {
        // Ensure event has required fields
        if (!eventData.timestamp) {
            eventData.timestamp = new Date().toISOString();
        }
        if (!eventData.id) {
            eventData.id = Date.now() + Math.random();
        }

        this.events.push(eventData);

        // Update session tracking
        if (eventData.data && eventData.data.session_id) {
            const sessionId = eventData.data.session_id;
            if (!this.sessions.has(sessionId)) {
                this.sessions.set(sessionId, {
                    id: sessionId,
                    startTime: eventData.timestamp,
                    lastActivity: eventData.timestamp,
                    eventCount: 0
                });
            }
            const session = this.sessions.get(sessionId);
            session.lastActivity = eventData.timestamp;
            session.eventCount++;
        }

        if (notify) {
            this.notifyEventUpdate();
        }
    }

    /**
     * Update sessions from server data
     * @param {Array} sessionsData - Sessions data from server
     */
    updateSessions(sessionsData) {
        if (Array.isArray(sessionsData)) {
            sessionsData.forEach(session => {
                this.sessions.set(session.id, session);
            });
        }
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.events = [];
        this.sessions.clear();
        this.notifyEventUpdate();
    }

    /**
     * Clear events and request fresh history from server
     * @param {Object} options - History request options (same as requestHistory)
     */
    refreshHistory(options = {}) {
        this.clearEvents();
        this.requestHistory(options);
    }

    /**
     * Get filtered events by session
     * @param {string} sessionId - Session ID to filter by (null for all)
     * @returns {Array} Filtered events
     */
    getEventsBySession(sessionId = null) {
        if (!sessionId) {
            return this.events;
        }
        return this.events.filter(event =>
            event.data && event.data.session_id === sessionId
        );
    }

    /**
     * Register callback for connection events
     * @param {string} eventType - Type of event (connect, disconnect, error)
     * @param {Function} callback - Callback function
     */
    onConnection(eventType, callback) {
        if (this.connectionCallbacks[eventType]) {
            this.connectionCallbacks[eventType].push(callback);
        }
    }

    /**
     * Register callback for event updates
     * @param {Function} callback - Callback function
     */
    onEventUpdate(callback) {
        this.connectionCallbacks.event.push(callback);
    }

    /**
     * Notify connection status change
     * @param {string} status - Status message
     * @param {string} type - Status type (connected, disconnected, connecting)
     */
    notifyConnectionStatus(status, type) {
        console.log(`SocketClient: Connection status changed to '${status}' (${type})`);

        // Direct DOM update - immediate and reliable
        this.updateConnectionStatusDOM(status, type);

        // Also dispatch custom event for other modules
        document.dispatchEvent(new CustomEvent('socketConnectionStatus', {
            detail: { status, type }
        }));
    }

    /**
     * Directly update the connection status DOM element
     * @param {string} status - Status message
     * @param {string} type - Status type (connected, disconnected, connecting)
     */
    updateConnectionStatusDOM(status, type) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            // Update the text content while preserving the indicator span
            statusElement.innerHTML = `<span>●</span> ${status}`;

            // Update the CSS class for styling
            statusElement.className = `status-badge status-${type}`;

            console.log(`SocketClient: Direct DOM update - status: '${status}' (${type})`);
        } else {
            console.warn('SocketClient: Could not find connection-status element in DOM');
        }
    }

    /**
     * Notify event update
     */
    notifyEventUpdate() {
        this.connectionCallbacks.event.forEach(callback =>
            callback(this.events, this.sessions)
        );

        // Also dispatch custom event
        document.dispatchEvent(new CustomEvent('socketEventUpdate', {
            detail: { events: this.events, sessions: this.sessions }
        }));
    }

    /**
     * Get connection state
     * @returns {Object} Connection state
     */
    getConnectionState() {
        return {
            isConnected: this.isConnected,
            isConnecting: this.isConnecting,
            socketId: this.socket ? this.socket.id : null
        };
    }

    /**
     * Validate event against expected schema
     * @param {Object} eventData - Raw event data
     * @returns {Object|null} Validated event or null if invalid
     */
    validateEventSchema(eventData) {
        if (!eventData || typeof eventData !== 'object') {
            console.warn('Event data is not an object:', eventData);
            return null;
        }
        
        // Make a copy to avoid modifying the original
        const validated = { ...eventData };
        
        // Check and provide defaults for required fields
        if (!validated.source) {
            validated.source = 'system';  // Default source for backward compatibility
        }
        if (!validated.type) {
            // If there's an event field, use it as the type
            if (validated.event) {
                validated.type = validated.event;
            } else {
                validated.type = 'unknown';
            }
        }
        if (!validated.subtype) {
            validated.subtype = 'generic';
        }
        if (!validated.timestamp) {
            validated.timestamp = new Date().toISOString();
        }
        if (!validated.data) {
            validated.data = {};
        }
        
        // Ensure data field is an object
        if (validated.data && typeof validated.data !== 'object') {
            validated.data = { value: validated.data };
        }
        
        console.log('Validated event:', validated);
        return validated;
    }
    
    /**
     * Transform received event to match expected dashboard format
     * @param {Object} eventData - Raw event data from server
     * @returns {Object} Transformed event
     */
    transformEvent(eventData) {
        // Handle multiple event structures:
        // 1. Hook events: { type: 'hook.pre_tool', timestamp: '...', data: {...} }
        // 2. Legacy events: { event: 'TestStart', timestamp: '...', ... }
        // 3. Standard events: { type: 'session', subtype: 'started', ... }

        if (!eventData) {
            return eventData; // Return as-is if null/undefined
        }

        let transformedEvent = { ...eventData };

        // Handle legacy format with 'event' field but no 'type'
        if (!eventData.type && eventData.event) {
            // Map common event names to proper type/subtype
            const eventName = eventData.event;
            
            // Check for known event patterns
            if (eventName === 'TestStart' || eventName === 'TestEnd') {
                transformedEvent.type = 'test';
                transformedEvent.subtype = eventName.toLowerCase().replace('test', '');
            } else if (eventName === 'SubagentStart' || eventName === 'SubagentStop') {
                transformedEvent.type = 'subagent';
                transformedEvent.subtype = eventName.toLowerCase().replace('subagent', '');
            } else if (eventName === 'ToolCall') {
                transformedEvent.type = 'tool';
                transformedEvent.subtype = 'call';
            } else if (eventName === 'UserPrompt') {
                transformedEvent.type = 'hook';
                transformedEvent.subtype = 'user_prompt';
            } else {
                // Generic fallback for unknown event names
                // Use 'unknown' for type and the actual eventName for subtype
                transformedEvent.type = 'unknown';
                transformedEvent.subtype = eventName.toLowerCase();
                
                // Prevent duplicate type/subtype values
                if (transformedEvent.type === transformedEvent.subtype) {
                    transformedEvent.subtype = 'event';
                }
            }
            
            // Remove the 'event' field to avoid confusion
            delete transformedEvent.event;
        }
        // Handle standard format with 'type' field
        else if (eventData.type) {
            const type = eventData.type;
            
            // Transform 'hook.subtype' format to separate type and subtype
            if (type.startsWith('hook.')) {
                const subtype = type.substring(5); // Remove 'hook.' prefix
                transformedEvent.type = 'hook';
                transformedEvent.subtype = subtype;
            }
            // Transform other dotted types like 'session.started' -> type: 'session', subtype: 'started'
            else if (type.includes('.')) {
                const [mainType, ...subtypeParts] = type.split('.');
                transformedEvent.type = mainType;
                transformedEvent.subtype = subtypeParts.join('.');
            }
        }
        // If no type and no event field, mark as unknown
        else {
            transformedEvent.type = 'unknown';
            transformedEvent.subtype = '';
        }

        // Store original event name for display purposes (before any transformation)
        if (!eventData.type && eventData.event) {
            transformedEvent.originalEventName = eventData.event;
        } else if (eventData.type) {
            transformedEvent.originalEventName = eventData.type;
        }

        // Extract and flatten data fields to top level for dashboard compatibility
        // The dashboard expects fields like tool_name, agent_type, etc. at the top level
        if (eventData.data && typeof eventData.data === 'object') {
            // Protected fields that should never be overwritten by data fields
            const protectedFields = ['type', 'subtype', 'timestamp', 'id', 'event', 'event_type', 'originalEventName'];
            
            // Copy all data fields to the top level, except protected ones
            Object.keys(eventData.data).forEach(key => {
                // Only copy if not a protected field
                if (!protectedFields.includes(key)) {
                    // Special handling for tool_parameters to ensure it's properly preserved
                    // This is critical for file path extraction in file-tool-tracker
                    if (key === 'tool_parameters' && typeof eventData.data[key] === 'object') {
                        // Deep copy the tool_parameters object to preserve all nested fields
                        transformedEvent[key] = JSON.parse(JSON.stringify(eventData.data[key]));
                    } else {
                        transformedEvent[key] = eventData.data[key];
                    }
                } else {
                    // Log warning if data field would overwrite a protected field
                    console.warn(`Protected field '${key}' in data object was not copied to top level to preserve event structure`);
                }
            });
            
            // Keep the original data object for backward compatibility
            transformedEvent.data = eventData.data;
        }

        // Debug logging for tool events
        if (transformedEvent.type === 'hook' && (transformedEvent.subtype === 'pre_tool' || transformedEvent.subtype === 'post_tool')) {
            console.log('Transformed tool event:', {
                type: transformedEvent.type,
                subtype: transformedEvent.subtype,
                tool_name: transformedEvent.tool_name,
                has_tool_parameters: !!transformedEvent.tool_parameters,
                tool_parameters: transformedEvent.tool_parameters,
                has_data: !!transformedEvent.data,
                keys: Object.keys(transformedEvent).filter(k => k !== 'data')
            });
            
            // Extra debug logging for file-related tools
            const fileTools = ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'];
            if (fileTools.includes(transformedEvent.tool_name)) {
                console.log('File tool event details:', {
                    tool_name: transformedEvent.tool_name,
                    file_path: transformedEvent.tool_parameters?.file_path,
                    path: transformedEvent.tool_parameters?.path,
                    notebook_path: transformedEvent.tool_parameters?.notebook_path,
                    full_parameters: transformedEvent.tool_parameters
                });
            }
        }

        return transformedEvent;
    }

    /**
     * Get current events and sessions
     * @returns {Object} Current state
     */
    getState() {
        return {
            events: this.events,
            sessions: this.sessions,
            currentSessionId: this.currentSessionId
        };
    }

    /**
     * Start health monitoring
     * Detects stale connections and triggers reconnection
     */
    startHealthMonitoring() {
        this.healthCheckInterval = setInterval(() => {
            if (this.isConnected && this.lastPingTime) {
                const timeSinceLastPing = Date.now() - this.lastPingTime;
                
                if (timeSinceLastPing > this.pingTimeout) {
                    console.warn(`No ping from server for ${timeSinceLastPing/1000}s, connection may be stale`);
                    
                    // Force reconnection
                    if (this.socket) {
                        console.log('Forcing reconnection due to stale connection...');
                        this.socket.disconnect();
                        setTimeout(() => {
                            if (this.port) {
                                this.connect(this.port);
                            }
                        }, 1000);
                    }
                }
            }
        }, 10000); // Check every 10 seconds
    }
    
    /**
     * Stop health monitoring
     */
    stopHealthMonitoring() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }
    
    /**
     * Start periodic status check as fallback mechanism
     * This ensures the UI stays in sync with actual socket state
     */
    startStatusCheckFallback() {
        // Check status every 2 seconds
        setInterval(() => {
            this.checkAndUpdateStatus();
        }, 2000);

        // Initial check after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => this.checkAndUpdateStatus(), 100);
            });
        } else {
            setTimeout(() => this.checkAndUpdateStatus(), 100);
        }
    }

    /**
     * Check actual socket state and update UI if necessary
     */
    checkAndUpdateStatus() {
        let actualStatus = 'Disconnected';
        let actualType = 'disconnected';

        if (this.socket) {
            if (this.socket.connected) {
                actualStatus = 'Connected';
                actualType = 'connected';
                this.isConnected = true;
                this.isConnecting = false;
            } else if (this.socket.connecting || this.isConnecting) {
                actualStatus = 'Connecting...';
                actualType = 'connecting';
                this.isConnected = false;
            } else {
                actualStatus = 'Disconnected';
                actualType = 'disconnected';
                this.isConnected = false;
                this.isConnecting = false;
            }
        }

        // Check if UI needs updating
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            const currentText = statusElement.textContent.replace('●', '').trim();
            const currentClass = statusElement.className;
            const expectedClass = `status-badge status-${actualType}`;

            // Update if status text or class doesn't match
            if (currentText !== actualStatus || currentClass !== expectedClass) {
                console.log(`SocketClient: Fallback update - was '${currentText}' (${currentClass}), now '${actualStatus}' (${expectedClass})`);
                this.updateConnectionStatusDOM(actualStatus, actualType);
            }
        }
    }

    /**
     * Clean up resources
     */
    destroy() {
        this.stopHealthMonitoring();
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.eventQueue = [];
        this.pendingEmissions.clear();
    }
    
    /**
     * Get connection metrics
     * @returns {Object} Connection metrics
     */
    getConnectionMetrics() {
        return {
            isConnected: this.isConnected,
            uptime: this.lastConnectTime ? (Date.now() - this.lastConnectTime) / 1000 : 0,
            lastPing: this.lastPingTime ? (Date.now() - this.lastPingTime) / 1000 : null,
            queuedEvents: this.eventQueue.length,
            pendingEmissions: this.pendingEmissions.size,
            retryAttempts: this.retryAttempts
        };
    }
}

// ES6 Module export
export { SocketClient };
export default SocketClient;

// Backward compatibility - keep window export for non-module usage
window.SocketClient = SocketClient;
