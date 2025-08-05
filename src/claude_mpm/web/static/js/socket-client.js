/**
 * Socket.IO Client for Claude MPM Dashboard
 * Handles WebSocket connections and event processing
 */

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
        
        // Connection state
        this.isConnected = false;
        this.isConnecting = false;
        
        // Event processing
        this.events = [];
        this.sessions = new Map();
        this.currentSessionId = null;
        
        // Start periodic status check as fallback mechanism
        this.startStatusCheckFallback();
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
            this.isConnected = true;
            this.isConnecting = false;
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
            this.notifyConnectionStatus(`Disconnected: ${reason}`, 'disconnected');
            
            // Emit disconnect callback
            this.connectionCallbacks.disconnect.forEach(callback => 
                callback(reason)
            );
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
                data: { error: errorMsg, url: this.socket.io.uri }
            });
            
            // Emit error callback
            this.connectionCallbacks.error.forEach(callback => 
                callback(errorMsg)
            );
        });

        // Primary event handler - this is what the server actually emits
        this.socket.on('claude_event', (data) => {
            console.log('Received claude_event:', data);
            
            // Transform event to match expected format
            const transformedEvent = this.transformEvent(data);
            console.log('Transformed event:', transformedEvent);
            this.addEvent(transformedEvent);
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
     * Request server status
     */
    requestStatus() {
        if (this.socket && this.socket.connected) {
            console.log('Requesting server status...');
            this.socket.emit('request.status');
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
            this.socket.emit('get_history', params);
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
     * Transform received event to match expected dashboard format
     * @param {Object} eventData - Raw event data from server
     * @returns {Object} Transformed event
     */
    transformEvent(eventData) {
        // Handle the actual event structure sent from hook_handler.py:
        // { type: 'hook.pre_tool', timestamp: '...', data: { tool_name: '...', agent_type: '...', etc } }
        
        if (!eventData || !eventData.type) {
            return eventData; // Return as-is if malformed
        }

        const type = eventData.type;
        let transformedEvent = { ...eventData };

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

        // Extract and flatten data fields to top level for dashboard compatibility
        // The dashboard expects fields like tool_name, agent_type, etc. at the top level
        if (eventData.data && typeof eventData.data === 'object') {
            // Copy all data fields to the top level
            Object.keys(eventData.data).forEach(key => {
                // Only copy if the key doesn't already exist at top level
                if (!(key in transformedEvent)) {
                    transformedEvent[key] = eventData.data[key];
                }
            });
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
}

// Export for use in other modules
window.SocketClient = SocketClient;