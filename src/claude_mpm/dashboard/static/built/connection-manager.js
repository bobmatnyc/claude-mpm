/**
 * Enhanced Connection Manager for Dashboard
 * 
 * Provides robust connection management with:
 * - Persistent client ID across reconnections
 * - Event sequence tracking and replay
 * - Exponential backoff for reconnection
 * - Connection health monitoring
 * - Visual status indicators
 * - Local event buffering
 */

class EnhancedConnectionManager {
    constructor(socketClient) {
        this.socketClient = socketClient;
        this.socket = null;
        this.clientId = this.loadClientId();
        this.lastSequence = this.loadLastSequence();
        this.connectionState = 'disconnected';
        this.connectionQuality = 1.0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.baseReconnectDelay = 1000; // 1 second
        this.maxReconnectDelay = 30000; // 30 seconds
        this.heartbeatInterval = 30000; // 30 seconds
        this.heartbeatTimer = null;
        this.pingTimer = null;
        this.lastPingTime = null;
        this.lastPongTime = null;
        this.missedHeartbeats = 0;
        this.maxMissedHeartbeats = 3;
        
        // Event buffering for offline mode
        this.eventBuffer = [];
        this.maxEventBuffer = 100;
        
        // Connection metrics
        this.metrics = {
            connectTime: null,
            disconnectTime: null,
            totalConnections: 0,
            totalReconnections: 0,
            totalEvents: 0,
            eventsAcked: 0,
            lastActivity: null
        };
        
        // Status update callbacks
        this.statusCallbacks = new Set();
        this.qualityCallbacks = new Set();
        
        // Initialize
        this.setupEventHandlers();
        this.startHealthMonitoring();
    }
    
    /**
     * Load or generate client ID for persistent identification
     */
    loadClientId() {
        let clientId = localStorage.getItem('claude_mpm_client_id');
        if (!clientId) {
            clientId = 'client_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('claude_mpm_client_id', clientId);
        }
        return clientId;
    }
    
    /**
     * Load last received event sequence for replay
     */
    loadLastSequence() {
        const sequence = localStorage.getItem('claude_mpm_last_sequence');
        return sequence ? parseInt(sequence, 10) : 0;
    }
    
    /**
     * Save last received event sequence
     */
    saveLastSequence(sequence) {
        this.lastSequence = sequence;
        localStorage.setItem('claude_mpm_last_sequence', sequence.toString());
    }
    
    /**
     * Connect with enhanced options and authentication
     */
    connect(port = '8765') {
        const url = `http://localhost:${port}`;
        
        console.log(`[ConnectionManager] Connecting to ${url} with client ID: ${this.clientId}`);
        this.updateConnectionState('connecting');
        
        // Create socket with enhanced options
        this.socket = io(url, {
            auth: {
                client_id: this.clientId,
                last_sequence: this.lastSequence
            },
            reconnection: true,
            reconnectionDelay: this.calculateReconnectDelay(),
            reconnectionDelayMax: this.maxReconnectDelay,
            reconnectionAttempts: this.maxReconnectAttempts,
            timeout: 20000,
            transports: ['websocket', 'polling'],
            pingInterval: 25000,
            pingTimeout: 20000
        });
        
        this.setupSocketHandlers();
        this.socketClient.socket = this.socket;
    }
    
    /**
     * Calculate exponential backoff delay for reconnection
     */
    calculateReconnectDelay() {
        const delay = Math.min(
            this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        return delay + Math.random() * 1000; // Add jitter
    }
    
    /**
     * Setup socket event handlers
     */
    setupSocketHandlers() {
        if (!this.socket) return;
        
        // Connection established
        this.socket.on('connection_established', (data) => {
            console.log('[ConnectionManager] Connection established:', data);
            this.clientId = data.client_id;
            this.metrics.connectTime = Date.now();
            this.metrics.totalConnections++;
            this.reconnectAttempts = 0;
            this.missedHeartbeats = 0;
            this.updateConnectionState('connected');
            this.startHeartbeat();
            
            // Flush buffered events if any
            this.flushEventBuffer();
        });
        
        // Event replay after reconnection
        this.socket.on('event_replay', (data) => {
            console.log(`[ConnectionManager] Replaying ${data.count} events from sequence ${data.from_sequence}`);
            
            if (data.events && data.events.length > 0) {
                data.events.forEach(event => {
                    // Update sequence
                    if (event.sequence) {
                        this.saveLastSequence(event.sequence);
                    }
                    
                    // Process replayed event
                    this.socketClient.handleEvent('claude_event', event);
                });
                
                this.showNotification(`Replayed ${data.count} missed events`, 'info');
            }
        });
        
        // Normal event with sequence tracking
        this.socket.on('claude_event', (event) => {
            if (event.sequence) {
                this.saveLastSequence(event.sequence);
                
                // Send acknowledgment
                this.socket.emit('acknowledge_event', {
                    sequence: event.sequence
                });
                
                this.metrics.eventsAcked++;
            }
            
            this.metrics.totalEvents++;
            this.metrics.lastActivity = Date.now();
        });
        
        // Heartbeat response
        this.socket.on('heartbeat_response', (data) => {
            this.missedHeartbeats = 0;
            this.updateConnectionQuality(1.0);
        });
        
        // Pong response
        this.socket.on('pong', (data) => {
            this.lastPongTime = Date.now();
            const latency = this.lastPongTime - this.lastPingTime;
            this.updateLatency(latency);
        });
        
        // Connection stats response
        this.socket.on('connection_stats', (data) => {
            console.log('[ConnectionManager] Connection stats:', data);
            if (data.connection) {
                this.updateConnectionQuality(data.connection.quality);
            }
        });
        
        // Standard Socket.IO events
        this.socket.on('connect', () => {
            console.log('[ConnectionManager] Socket connected');
            if (this.metrics.disconnectTime) {
                const downtime = Date.now() - this.metrics.disconnectTime;
                console.log(`[ConnectionManager] Reconnected after ${(downtime / 1000).toFixed(1)}s`);
                this.metrics.totalReconnections++;
            }
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('[ConnectionManager] Socket disconnected:', reason);
            this.metrics.disconnectTime = Date.now();
            this.updateConnectionState('disconnected');
            this.stopHeartbeat();
            
            // Handle different disconnect reasons
            if (reason === 'io server disconnect') {
                // Server initiated disconnect
                this.showNotification('Server disconnected the connection', 'warning');
            } else if (reason === 'ping timeout') {
                // Connection timeout
                this.showNotification('Connection timeout - attempting to reconnect', 'warning');
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('[ConnectionManager] Connection error:', error.message);
            this.reconnectAttempts++;
            
            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                this.updateConnectionState('failed');
                this.showNotification('Failed to connect after multiple attempts', 'error');
            } else {
                const delay = this.calculateReconnectDelay();
                this.showNotification(
                    `Connection failed, retrying in ${(delay / 1000).toFixed(1)}s...`,
                    'warning'
                );
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`[ConnectionManager] Reconnected after ${attemptNumber} attempts`);
            this.showNotification('Reconnected successfully', 'success');
            
            // Request event replay
            this.socket.emit('request_replay', {
                last_sequence: this.lastSequence
            });
        });
        
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`[ConnectionManager] Reconnection attempt ${attemptNumber}`);
            this.updateConnectionState('reconnecting');
        });
    }
    
    /**
     * Start heartbeat monitoring
     */
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('heartbeat');
                this.missedHeartbeats++;
                
                if (this.missedHeartbeats >= this.maxMissedHeartbeats) {
                    console.warn('[ConnectionManager] Too many missed heartbeats, connection may be stale');
                    this.updateConnectionQuality(0.3);
                    this.updateConnectionState('stale');
                }
            }
        }, this.heartbeatInterval);
        
        // Also start ping monitoring for latency
        this.pingTimer = setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.lastPingTime = Date.now();
                this.socket.emit('ping');
            }
        }, 10000); // Every 10 seconds
    }
    
    /**
     * Stop heartbeat monitoring
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
        
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }
    
    /**
     * Start health monitoring
     */
    startHealthMonitoring() {
        // Periodic connection stats request
        setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('get_connection_stats');
            }
        }, 60000); // Every minute
        
        // Activity timeout detection
        setInterval(() => {
            if (this.connectionState === 'connected' && this.metrics.lastActivity) {
                const timeSinceActivity = Date.now() - this.metrics.lastActivity;
                if (timeSinceActivity > 120000) { // 2 minutes
                    console.warn('[ConnectionManager] No activity for 2 minutes');
                    this.updateConnectionQuality(0.5);
                }
            }
        }, 30000); // Check every 30 seconds
    }
    
    /**
     * Update connection state and notify listeners
     */
    updateConnectionState(state) {
        const previousState = this.connectionState;
        this.connectionState = state;
        
        if (previousState !== state) {
            console.log(`[ConnectionManager] State change: ${previousState} -> ${state}`);
            
            // Update UI
            this.updateConnectionUI(state);
            
            // Notify callbacks
            this.statusCallbacks.forEach(callback => {
                try {
                    callback(state, previousState);
                } catch (error) {
                    console.error('Error in status callback:', error);
                }
            });
        }
    }
    
    /**
     * Update connection quality score
     */
    updateConnectionQuality(quality) {
        this.connectionQuality = Math.max(0, Math.min(1, quality));
        
        // Notify callbacks
        this.qualityCallbacks.forEach(callback => {
            try {
                callback(this.connectionQuality);
            } catch (error) {
                console.error('Error in quality callback:', error);
            }
        });
        
        // Update UI indicator
        this.updateQualityUI(this.connectionQuality);
    }
    
    /**
     * Update latency display
     */
    updateLatency(latency) {
        const latencyElement = document.getElementById('connection-latency');
        if (latencyElement) {
            latencyElement.textContent = `${latency}ms`;
            
            // Color code based on latency
            if (latency < 50) {
                latencyElement.className = 'latency-good';
            } else if (latency < 150) {
                latencyElement.className = 'latency-moderate';
            } else {
                latencyElement.className = 'latency-poor';
            }
        }
    }
    
    /**
     * Update connection UI based on state
     */
    updateConnectionUI(state) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;
        
        const stateConfig = {
            'connecting': { text: 'Connecting...', class: 'status-connecting', icon: '⟳' },
            'connected': { text: 'Connected', class: 'status-connected', icon: '●' },
            'reconnecting': { text: 'Reconnecting...', class: 'status-reconnecting', icon: '⟳' },
            'disconnected': { text: 'Disconnected', class: 'status-disconnected', icon: '●' },
            'stale': { text: 'Connection Stale', class: 'status-stale', icon: '⚠' },
            'failed': { text: 'Connection Failed', class: 'status-failed', icon: '✕' }
        };
        
        const config = stateConfig[state] || stateConfig['disconnected'];
        statusElement.innerHTML = `<span>${config.icon}</span> ${config.text}`;
        statusElement.className = `status-badge ${config.class}`;
    }
    
    /**
     * Update connection quality UI
     */
    updateQualityUI(quality) {
        const qualityElement = document.getElementById('connection-quality');
        if (!qualityElement) return;
        
        const percentage = Math.round(quality * 100);
        let qualityClass = 'quality-good';
        let qualityText = 'Excellent';
        
        if (quality < 0.3) {
            qualityClass = 'quality-poor';
            qualityText = 'Poor';
        } else if (quality < 0.7) {
            qualityClass = 'quality-moderate';
            qualityText = 'Fair';
        }
        
        qualityElement.innerHTML = `
            <div class="quality-bar ${qualityClass}">
                <div class="quality-fill" style="width: ${percentage}%"></div>
            </div>
            <span class="quality-text">${qualityText} (${percentage}%)</span>
        `;
    }
    
    /**
     * Buffer events when disconnected
     */
    bufferEvent(event) {
        if (this.eventBuffer.length >= this.maxEventBuffer) {
            this.eventBuffer.shift(); // Remove oldest
        }
        
        this.eventBuffer.push({
            ...event,
            buffered_at: Date.now()
        });
        
        // Save to localStorage for persistence
        localStorage.setItem('claude_mpm_event_buffer', JSON.stringify(this.eventBuffer));
    }
    
    /**
     * Flush buffered events after reconnection
     */
    flushEventBuffer() {
        if (this.eventBuffer.length === 0) return;
        
        console.log(`[ConnectionManager] Flushing ${this.eventBuffer.length} buffered events`);
        
        // Process buffered events
        this.eventBuffer.forEach(event => {
            this.socketClient.handleEvent('claude_event', event);
        });
        
        // Clear buffer
        this.eventBuffer = [];
        localStorage.removeItem('claude_mpm_event_buffer');
    }
    
    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        const notificationArea = document.getElementById('connection-notifications');
        if (!notificationArea) return;
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        notificationArea.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    /**
     * Register status change callback
     */
    onStatusChange(callback) {
        this.statusCallbacks.add(callback);
    }
    
    /**
     * Register quality change callback
     */
    onQualityChange(callback) {
        this.qualityCallbacks.add(callback);
    }
    
    /**
     * Get connection metrics
     */
    getMetrics() {
        return {
            ...this.metrics,
            connectionState: this.connectionState,
            connectionQuality: this.connectionQuality,
            clientId: this.clientId,
            lastSequence: this.lastSequence,
            bufferedEvents: this.eventBuffer.length
        };
    }
    
    /**
     * Disconnect and cleanup
     */
    disconnect() {
        this.stopHeartbeat();
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        this.updateConnectionState('disconnected');
    }
}

// Export for use in other modules
export { EnhancedConnectionManager };