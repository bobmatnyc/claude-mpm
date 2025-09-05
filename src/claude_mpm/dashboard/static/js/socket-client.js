/**
 * Socket.IO Client for Claude MPM Dashboard
 * 
 * This module provides real-time WebSocket communication between the Claude MPM dashboard
 * and the backend Socket.IO server. It handles connection management, event processing,
 * retry logic, and health monitoring.
 * 
 * Architecture:
 * - Maintains persistent WebSocket connection to Claude MPM backend
 * - Implements robust retry logic with exponential backoff
 * - Provides event queuing during disconnections
 * - Validates event schemas for data integrity
 * - Monitors connection health with ping/pong mechanisms
 * 
 * Event Flow:
 * 1. Events from Claude Code hooks → Socket.IO server → Dashboard client
 * 2. Dashboard requests → Socket.IO server → Backend services
 * 3. Status updates → Socket.IO server → All connected clients
 * 
 * Thread Safety:
 * - Single-threaded JavaScript execution model ensures safety
 * - Event callbacks are queued and executed sequentially
 * - Connection state changes are atomic
 * 
 * Performance Considerations:
 * - Event queue limited to 100 items to prevent memory leaks
 * - Health checks run every 45s to match server ping interval
 * - Exponential backoff prevents connection spam
 * - Lazy event validation reduces overhead
 * 
 * Security:
 * - Connects only to localhost to prevent external access
 * - Event schema validation prevents malformed data processing
 * - Connection timeout prevents hanging connections
 * 
 * @author Claude MPM Team
 * @version 1.0
 * @since v4.0.25
 */

// Access the global io from window object in ES6 module context
// WHY: Socket.IO is loaded via CDN in HTML, available as window.io
const io = window.io;

/**
 * Primary Socket.IO client for dashboard communication.
 * 
 * Manages WebSocket connection lifecycle, event processing, and error handling.
 * Implements connection resilience with automatic retry and health monitoring.
 * 
 * Key Features:
 * - Automatic connection retry with exponential backoff
 * - Event queue management during disconnections  
 * - Schema validation for incoming events
 * - Health monitoring with ping/pong
 * - Session management and event history
 * 
 * Connection States:
 * - isConnected: Currently connected to server
 * - isConnecting: Connection attempt in progress
 * - disconnectTime: Timestamp of last disconnection
 * 
 * Event Processing:
 * - Validates against schema before processing
 * - Queues events during disconnection (max 100)
 * - Maintains event history and session tracking
 * 
 * @class SocketClient
 */
class SocketClient {
    /**
     * Initialize Socket.IO client with default configuration.
     * 
     * Sets up connection management, event processing, and health monitoring.
     * Configures retry logic and event queue management.
     * 
     * WHY this initialization approach:
     * - Lazy socket creation allows for port specification
     * - Event queue prevents data loss during reconnections
     * - Health monitoring detects server issues early
     * - Schema validation ensures data integrity
     * 
     * @constructor
     */
    constructor() {
        /**
         * Socket.IO connection instance.
         * @type {Socket|null}
         * @private
         */
        this.socket = null;
        
        /**
         * Current connection port.
         * @type {string|null}
         * @private
         */
        this.port = null; // Store the current port
        
        /**
         * Event callback registry for connection lifecycle events.
         * WHY: Allows multiple components to register for connection events.
         * @type {Object.<string, Function[]>}
         * @private
         */
        this.connectionCallbacks = {
            connect: [],    // Called on successful connection
            disconnect: [], // Called on disconnection  
            error: [],      // Called on connection errors
            event: []       // Called on incoming events
        };
        
        /**
         * Event schema definition for validation.
         * WHY: Ensures data integrity and prevents processing malformed events.
         * @type {Object}
         * @private
         */
        this.eventSchema = {
            required: ['source', 'type', 'subtype', 'timestamp', 'data'],
            optional: ['event', 'session_id']
        };

        /**
         * Current connection state.
         * @type {boolean}
         * @private
         */
        this.isConnected = false;
        
        /**
         * Connection attempt in progress flag.
         * WHY: Prevents multiple simultaneous connection attempts.
         * @type {boolean}
         * @private
         */
        this.isConnecting = false;
        
        /**
         * Timestamp of last successful connection.
         * @type {number|null}
         * @private
         */
        this.lastConnectTime = null;
        
        /**
         * Timestamp of last disconnection.
         * WHY: Used to calculate downtime and trigger reconnection logic.
         * @type {number|null}
         * @private
         */
        this.disconnectTime = null;

        /**
         * Event history storage.
         * WHY: Maintains event history for dashboard display and analysis.
         * @type {Array.<Object>}
         * @private
         */
        this.events = [];
        
        /**
         * Session tracking map.
         * WHY: Groups events by session for better organization.
         * @type {Map<string, Object>}
         * @private
         */
        this.sessions = new Map();
        
        /**
         * Current active session identifier.
         * @type {string|null}
         * @private
         */
        this.currentSessionId = null;

        /**
         * Event queue for disconnection periods.
         * WHY: Prevents event loss during temporary disconnections.
         * @type {Array.<Object>}
         * @private
         */
        this.eventQueue = [];
        
        /**
         * Maximum queue size to prevent memory leaks.
         * WHY: Limits memory usage during extended disconnections.
         * @type {number}
         * @private
         * @const
         */
        this.maxQueueSize = 100;
        
        /**
         * Current retry attempt counter.
         * WHY: Tracks retry attempts for exponential backoff logic.
         * @type {number}
         * @private
         */
        this.retryAttempts = 0;
        
        /**
         * Maximum retry attempts before giving up.
         * WHY: Prevents infinite retry loops that could impact performance.
         * @type {number}
         * @private
         * @const
         */
        this.maxRetryAttempts = 5;  // Increased from 3 to 5 for better stability
        
        /**
         * Retry delay intervals in milliseconds (exponential backoff).
         * WHY: Prevents server overload during connection issues.
         * @type {number[]}
         * @private
         * @const
         */
        this.retryDelays = [1000, 2000, 3000, 4000, 5000]; // Exponential backoff with 5 attempts
        
        /**
         * Map of pending emissions for retry logic.
         * WHY: Tracks failed emissions that need to be retried.
         * @type {Map<string, Object>}
         * @private
         */
        this.pendingEmissions = new Map(); // Track pending emissions for retry
        
        /**
         * Timestamp of last ping sent to server.
         * WHY: Used for health monitoring and connection validation.
         * @type {number|null}
         * @private
         */
        this.lastPingTime = null;
        
        /**
         * Timestamp of last pong received from server.
         * WHY: Confirms server is responsive and connection is healthy.
         * @type {number|null}
         * @private
         */
        this.lastPongTime = null;
        
        /**
         * Health check timeout in milliseconds.
         * WHY: More lenient than Socket.IO timeout to prevent false positives.
         * @type {number}
         * @private
         * @const
         */
        this.pingTimeout = 120000; // 120 seconds for health check (more lenient for stability)
        
        /**
         * Health check interval timer.
         * @type {number|null}
         * @private
         */
        this.healthCheckInterval = null;
        
        // Initialize background monitoring
        this.startStatusCheckFallback();
        this.startHealthMonitoring();
    }

    /**
     * Connect to Socket.IO server on specified port.
     * 
     * Initiates WebSocket connection to the Claude MPM Socket.IO server.
     * Handles connection conflicts and ensures clean state transitions.
     * 
     * Connection Process:
     * 1. Validates port and constructs localhost URL
     * 2. Checks for existing connections and cleans up if needed
     * 3. Delegates to doConnect() for actual connection logic
     * 
     * Thread Safety:
     * - Uses setTimeout for async cleanup to prevent race conditions
     * - Connection state flags prevent multiple simultaneous attempts
     * 
     * @param {string} [port='8765'] - Port number to connect to (defaults to 8765)
     * 
     * @throws {Error} If Socket.IO library is not loaded
     * 
     * @example
     * // Connect to default port
     * socketClient.connect();
     * 
     * // Connect to specific port
     * socketClient.connect('8766');
     */
    connect(port = '8765') {
        // Store the port for later use in reconnections
        this.port = port;
        const url = `http://localhost:${port}`;

        // WHY this check: Prevents connection conflicts that can cause memory leaks
        if (this.socket && (this.socket.connected || this.socket.connecting)) {
            console.log('Already connected or connecting, disconnecting first...');
            this.socket.disconnect();
            // WHY 100ms delay: Allows cleanup to complete before new connection
            setTimeout(() => this.doConnect(url), 100);
            return;
        }

        this.doConnect(url);
    }

    /**
     * Execute the actual Socket.IO connection with full configuration.
     * 
     * Creates and configures Socket.IO client with appropriate timeouts,
     * retry logic, and transport settings. Sets up event handlers for
     * connection lifecycle management.
     * 
     * Configuration Details:
     * - autoConnect: true - Immediate connection attempt
     * - reconnection: true - Built-in reconnection enabled
     * - pingInterval: 25000ms - Matches server configuration
     * - pingTimeout: 20000ms - Health check timeout
     * - transports: ['websocket', 'polling'] - Fallback options
     * 
     * WHY these settings:
     * - Ping intervals must match server to prevent timeouts
     * - Limited reconnection attempts prevent infinite loops
     * - forceNew prevents socket reuse issues
     * 
     * @param {string} url - Complete Socket.IO server URL (http://localhost:port)
     * @private
     * 
     * @throws {Error} If Socket.IO library is not available
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
            reconnectionDelayMax: 10000,  // Increased max delay for stability
            reconnectionAttempts: 10,  // Increased attempts for better resilience  
            timeout: 30000,  // Increased connection timeout to 30 seconds
            forceNew: true,
            transports: ['websocket', 'polling'],
            pingInterval: 30000,  // Increased ping interval for stability
            pingTimeout: 60000    // Much longer timeout for better stability
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

            // Expose socket globally for components that need direct access
            window.socket = this.socket;
            console.log('SocketClient: Exposed socket globally as window.socket');

            // Emit connect callback
            this.connectionCallbacks.connect.forEach(callback =>
                callback(this.socket.id)
            );

            this.requestStatus();
            // History is now automatically sent by server on connection
            // No need to explicitly request it
        });

        this.socket.on('disconnect', (reason) => {
            // Enhanced logging for debugging disconnection issues
            const disconnectInfo = {
                reason: reason,
                timestamp: new Date().toISOString(),
                wasConnected: this.isConnected,
                uptimeSeconds: this.lastConnectTime ? ((Date.now() - this.lastConnectTime) / 1000).toFixed(1) : 0,
                lastPing: this.lastPingTime ? ((Date.now() - this.lastPingTime) / 1000).toFixed(1) + 's ago' : 'never',
                lastPong: this.lastPongTime ? ((Date.now() - this.lastPongTime) / 1000).toFixed(1) + 's ago' : 'never'
            };
            
            console.log('Disconnected from server:', disconnectInfo);
            
            this.isConnected = false;
            this.isConnecting = false;
            this.disconnectTime = Date.now();
            
            this.notifyConnectionStatus(`Disconnected: ${reason}`, 'disconnected');

            // Emit disconnect callback
            this.connectionCallbacks.disconnect.forEach(callback =>
                callback(reason)
            );
            
            // Detailed reason analysis for auto-reconnect decision
            const reconnectReasons = [
                'transport close',      // Network issue
                'ping timeout',         // Server not responding
                'transport error',      // Connection error
                'io server disconnect', // Server initiated disconnect (might be restart)
            ];
            
            if (reconnectReasons.includes(reason)) {
                console.log(`Auto-reconnect triggered for reason: ${reason}`);
                this.scheduleReconnect();
            } else if (reason === 'io client disconnect') {
                console.log('Client-initiated disconnect, not auto-reconnecting');
            } else {
                console.log(`Unknown disconnect reason: ${reason}, attempting reconnect anyway`);
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
            
            // Code analysis events are now allowed to flow through to the events list for troubleshooting
            // They will appear in both the Events tab and the Code tab
            if (validatedEvent.type && validatedEvent.type.startsWith('code:')) {
                console.log('Code analysis event received via claude_event, adding to events list for troubleshooting:', validatedEvent.type);
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
        
        // Track pong responses from server
        this.socket.on('pong', (data) => {
            this.lastPongTime = Date.now();
            // console.log('Received pong from server');
        });
        
        // Listen for heartbeat events from server (every 3 minutes)
        this.socket.on('heartbeat', (data) => {
            console.log('🫀 Received server heartbeat:', data);
            // Add heartbeat to event list for visibility
            this.addEvent({
                type: 'system',
                subtype: 'heartbeat',
                timestamp: data.timestamp || new Date().toISOString(),
                data: data
            });
            
            // Update last ping time to indicate server is alive
            this.lastPingTime = Date.now();
            
            // Log to console for debugging
            console.log(`Server heartbeat #${data.heartbeat_number}: ${data.server_uptime_formatted} uptime, ${data.connected_clients} clients connected`);
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

        // DISABLED: Legacy hook handlers - events now come through claude_event pathway
        // to prevent duplication. Hook events are processed by the claude_event handler above.
        // this.socket.on('hook.pre', (data) => {
        //     this.addEvent({ type: 'hook', subtype: 'pre', timestamp: new Date().toISOString(), data });
        // });

        // this.socket.on('hook.post', (data) => {
        //     this.addEvent({ type: 'hook', subtype: 'post', timestamp: new Date().toISOString(), data });
        // });

        this.socket.on('todo.updated', (data) => {
            this.addEvent({ type: 'todo', subtype: 'updated', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('memory.operation', (data) => {
            this.addEvent({ type: 'memory', subtype: 'operation', timestamp: new Date().toISOString(), data });
        });

        this.socket.on('log.entry', (data) => {
            this.addEvent({ type: 'log', subtype: 'entry', timestamp: new Date().toISOString(), data });
        });

        // Code analysis events - now allowed to flow through for troubleshooting
        // These are ALSO handled by the code-tree component and shown in the footer
        // They will appear in both places: Events tab (for troubleshooting) and Code tab (for visualization)
        this.socket.on('code:analysis:queued', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis queued event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:queued', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:analysis:accepted', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis accepted event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:accepted', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:analysis:start', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis start event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:start', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:analysis:complete', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis complete event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:complete', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:analysis:error', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis error event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:error', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:file:start', (data) => {
            // Add to events list for troubleshooting
            console.log('Code file start event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'file:start', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:node:found', (data) => {
            // Add to events list for troubleshooting
            console.log('Code node found event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'node:found', timestamp: new Date().toISOString(), data });
        });
        
        this.socket.on('code:analysis:progress', (data) => {
            // Add to events list for troubleshooting
            console.log('Code analysis progress event received, adding to events list for troubleshooting');
            this.addEvent({ type: 'code', subtype: 'analysis:progress', timestamp: new Date().toISOString(), data });
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
                    eventCount: 0,
                    working_directory: null,
                    git_branch: null
                });
            }
            const session = this.sessions.get(sessionId);
            session.lastActivity = eventData.timestamp;
            session.eventCount++;
            
            // Extract working directory from event data if available (prioritize newer data)
            // Check multiple possible locations for working directory
            const possiblePaths = [
                eventData.data.cwd,
                eventData.data.working_directory,
                eventData.data.working_dir,
                eventData.data.workingDirectory,
                eventData.data.instance_info?.working_dir,
                eventData.data.instance_info?.working_directory,
                eventData.data.instance_info?.cwd,
                eventData.cwd,
                eventData.working_directory,
                eventData.working_dir
            ];
            
            for (const path of possiblePaths) {
                if (path && typeof path === 'string' && path.trim()) {
                    session.working_directory = path;
                    console.log(`[SOCKET-CLIENT] Found working directory for session ${sessionId}:`, path);
                    break;
                }
            }
            
            // Extract git branch if available
            if (eventData.data.git_branch) {
                session.git_branch = eventData.data.git_branch;
            } else if (eventData.data.instance_info && eventData.data.instance_info.git_branch) {
                session.git_branch = eventData.data.instance_info.git_branch;
            }
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
     * Subscribe to socket events (proxy to underlying socket)
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (this.socket) {
            return this.socket.on(event, callback);
        } else {
            console.warn(`Cannot subscribe to '${event}': socket not initialized`);
        }
    }

    /**
     * Unsubscribe from socket events (proxy to underlying socket)
     * @param {string} event - Event name
     * @param {Function} callback - Callback function (optional)
     */
    off(event, callback) {
        if (this.socket) {
            return this.socket.off(event, callback);
        } else {
            console.warn(`Cannot unsubscribe from '${event}': socket not initialized`);
        }
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
        // 4. Normalized events: { type: 'code', subtype: 'progress', ... } - already normalized, keep as-is

        if (!eventData) {
            return eventData; // Return as-is if null/undefined
        }

        let transformedEvent = { ...eventData };

        // Check if event is already normalized (has both type and subtype as separate fields)
        // This prevents double-transformation of events that were normalized on the backend
        const isAlreadyNormalized = eventData.type && eventData.subtype && 
                                   !eventData.type.includes('.') && 
                                   !eventData.type.includes(':');

        if (isAlreadyNormalized) {
            // Event is already properly normalized from backend, just preserve it
            // Store a composite originalEventName for display if needed
            if (!transformedEvent.originalEventName) {
                if (eventData.subtype === 'generic' || eventData.type === eventData.subtype) {
                    transformedEvent.originalEventName = eventData.type;
                } else {
                    transformedEvent.originalEventName = `${eventData.type}.${eventData.subtype}`;
                }
            }
            // Return early to avoid further transformation
        }
        // Handle legacy format with 'event' field but no 'type'
        else if (!eventData.type && eventData.event) {
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
            // Store original event name for display purposes
            transformedEvent.originalEventName = eventName;
        }
        // Handle standard format with 'type' field that needs transformation
        else if (eventData.type) {
            const type = eventData.type;
            
            // Transform 'hook.subtype' format to separate type and subtype
            if (type.startsWith('hook.')) {
                const subtype = type.substring(5); // Remove 'hook.' prefix
                transformedEvent.type = 'hook';
                transformedEvent.subtype = subtype;
                transformedEvent.originalEventName = type;
            }
            // Transform 'code:*' events to proper code type
            // Handle multi-level subtypes like 'code:analysis:queued'
            else if (type.startsWith('code:')) {
                transformedEvent.type = 'code';
                // Replace colons with underscores in subtype for consistency
                const subtypePart = type.substring(5); // Remove 'code:' prefix
                transformedEvent.subtype = subtypePart.replace(/:/g, '_');
                transformedEvent.originalEventName = type;
            }
            // Transform other dotted types like 'session.started' -> type: 'session', subtype: 'started'
            else if (type.includes('.')) {
                const [mainType, ...subtypeParts] = type.split('.');
                transformedEvent.type = mainType;
                transformedEvent.subtype = subtypeParts.join('.');
                transformedEvent.originalEventName = type;
            }
            // Transform any remaining colon-separated types generically
            else if (type.includes(':')) {
                const parts = type.split(':', 2); // Split into max 2 parts
                transformedEvent.type = parts[0];
                // Replace any remaining colons with underscores in subtype
                transformedEvent.subtype = parts.length > 1 ? parts[1].replace(/:/g, '_') : 'generic';
                transformedEvent.originalEventName = type;
            }
            // If type doesn't need transformation but has no subtype, set a default
            else if (!eventData.subtype) {
                transformedEvent.subtype = 'generic';
                transformedEvent.originalEventName = type;
            }
        }
        // If no type and no event field, mark as unknown
        else {
            transformedEvent.type = 'unknown';
            transformedEvent.subtype = '';
            transformedEvent.originalEventName = 'unknown';
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
                    // Log debug info if data field would overwrite a protected field
                    // Only log for non-timestamp fields to reduce noise
                    if (key !== 'timestamp') {
                        console.debug(`Protected field '${key}' in data object was not copied to top level to preserve event structure`);
                    }
                }
            });
            
            // Keep the original data object for backward compatibility
            transformedEvent.data = eventData.data;
        }

        // Add hook_event_name for ActivityTree compatibility
        // Map the type/subtype structure to the expected hook_event_name format
        if (transformedEvent.type === 'hook') {
            if (transformedEvent.subtype === 'pre_tool') {
                transformedEvent.hook_event_name = 'PreToolUse';
            } else if (transformedEvent.subtype === 'post_tool') {
                transformedEvent.hook_event_name = 'PostToolUse';
            } else if (transformedEvent.subtype === 'subagent_start') {
                transformedEvent.hook_event_name = 'SubagentStart';
            } else if (transformedEvent.subtype === 'subagent_stop') {
                transformedEvent.hook_event_name = 'SubagentStop';
            } else if (transformedEvent.subtype === 'todo_write') {
                transformedEvent.hook_event_name = 'TodoWrite';
            } else if (transformedEvent.subtype === 'start') {
                transformedEvent.hook_event_name = 'Start';
            } else if (transformedEvent.subtype === 'stop') {
                transformedEvent.hook_event_name = 'Stop';
            }
        } else if (transformedEvent.type === 'subagent') {
            if (transformedEvent.subtype === 'start') {
                transformedEvent.hook_event_name = 'SubagentStart';
            } else if (transformedEvent.subtype === 'stop') {
                transformedEvent.hook_event_name = 'SubagentStop';
            }
        } else if (transformedEvent.type === 'todo' && transformedEvent.subtype === 'updated') {
            transformedEvent.hook_event_name = 'TodoWrite';
        }

        // Debug logging for tool events
        if (transformedEvent.type === 'hook' && (transformedEvent.subtype === 'pre_tool' || transformedEvent.subtype === 'post_tool')) {
            console.log('Transformed tool event:', {
                type: transformedEvent.type,
                subtype: transformedEvent.subtype,
                hook_event_name: transformedEvent.hook_event_name,
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
