/**
 * Socket Manager Module
 *
 * Handles all socket connection management, event dispatching, and connection state.
 * Provides a centralized interface for socket operations across the dashboard.
 *
 * WHY: Extracted from main dashboard to centralize socket connection logic and
 * provide better separation of concerns. This allows for easier testing and
 * maintenance of connection handling code.
 *
 * DESIGN DECISION: Acts as a wrapper around SocketClient to provide dashboard-specific
 * connection management while maintaining the existing SocketClient interface.
 * Uses event dispatching to notify other modules of connection state changes.
 */

// Import SocketClient (assuming it will be converted to ES6 modules too)
import { SocketClient } from '../socket-client.js';
class SocketManager {
    constructor() {
        this.socketClient = null;
        this.connectionCallbacks = new Set();
        this.eventUpdateCallbacks = new Set();

        // Initialize socket client
        this.socketClient = new SocketClient();

        // Make socketClient globally available (for backward compatibility)
        window.socketClient = this.socketClient;

        this.setupSocketEventHandlers();

        // Force initial status update after a short delay to ensure DOM is ready
        setTimeout(() => {
            this.updateInitialConnectionStatus();
        }, 100);

        console.log('Socket manager initialized');
    }

    /**
     * Set up socket event handlers for connection status and events
     */
    setupSocketEventHandlers() {
        // Listen for connection status changes
        document.addEventListener('socketConnectionStatus', (e) => {
            console.log(`SocketManager: Processing connection status update: ${e.detail.status} (${e.detail.type})`);
            this.handleConnectionStatusChange(e.detail.status, e.detail.type);

            // Notify all registered callbacks
            this.connectionCallbacks.forEach(callback => {
                try {
                    callback(e.detail.status, e.detail.type);
                } catch (error) {
                    console.error('Error in connection callback:', error);
                }
            });
        });

        // Set up event update handling
        if (this.socketClient) {
            this.socketClient.onEventUpdate((events) => {
                // Notify all registered callbacks
                this.eventUpdateCallbacks.forEach(callback => {
                    try {
                        callback(events);
                    } catch (error) {
                        console.error('Error in event update callback:', error);
                    }
                });
            });
        }
    }

    /**
     * Handle connection status changes
     * @param {string} status - Connection status text
     * @param {string} type - Connection type ('connected', 'disconnected', etc.)
     */
    handleConnectionStatusChange(status, type) {
        this.updateConnectionStatus(status, type);

        // Set up git branch listener when connected
        if (type === 'connected' && this.socketClient && this.socketClient.socket) {
            // Expose socket globally for components like CodeTree
            window.socket = this.socketClient.socket;
            console.log('SocketManager: Exposed socket globally as window.socket');
            
            this.setupGitBranchListener();
        }
    }

    /**
     * Update initial connection status on dashboard load
     */
    updateInitialConnectionStatus() {
        console.log('SocketManager: Updating initial connection status');

        // Force status check on socket client (uses fallback mechanism)
        if (this.socketClient && typeof this.socketClient.checkAndUpdateStatus === 'function') {
            console.log('SocketManager: Using socket client checkAndUpdateStatus method');
            this.socketClient.checkAndUpdateStatus();
        } else if (this.socketClient && this.socketClient.socket) {
            console.log('SocketManager: Checking socket state directly', {
                connected: this.socketClient.socket.connected,
                connecting: this.socketClient.socket.connecting,
                isConnecting: this.socketClient.isConnecting,
                isConnected: this.socketClient.isConnected
            });

            if (this.socketClient.socket.connected) {
                console.log('SocketManager: Socket is already connected, updating status');
                // Expose socket globally for components like CodeTree
                window.socket = this.socketClient.socket;
                console.log('SocketManager: Exposed socket globally as window.socket');
                this.updateConnectionStatus('Connected', 'connected');
            } else if (this.socketClient.isConnecting || this.socketClient.socket.connecting) {
                console.log('SocketManager: Socket is connecting, updating status');
                this.updateConnectionStatus('Connecting...', 'connecting');
            } else {
                console.log('SocketManager: Socket is disconnected, updating status');
                this.updateConnectionStatus('Disconnected', 'disconnected');
            }
        } else {
            console.log('SocketManager: No socket client or socket found, setting disconnected status');
            this.updateConnectionStatus('Disconnected', 'disconnected');
        }

        // Additional fallback - check again after a longer delay in case connection is still establishing
        setTimeout(() => {
            console.log('SocketManager: Secondary status check after 1 second');
            if (this.socketClient && this.socketClient.socket && this.socketClient.socket.connected) {
                console.log('SocketManager: Socket connected in secondary check, updating status');
                // Expose socket globally if not already done
                if (!window.socket) {
                    window.socket = this.socketClient.socket;
                    console.log('SocketManager: Exposed socket globally as window.socket (secondary check)');
                }
                this.updateConnectionStatus('Connected', 'connected');
            }
        }, 1000);
    }

    /**
     * Set up git branch response listener for connected socket
     */
    setupGitBranchListener() {
        // Remove any existing listener first
        this.socketClient.socket.off('git_branch_response');

        // Add the listener
        this.socketClient.socket.on('git_branch_response', (data) => {
            if (data.success) {
                const footerBranch = document.getElementById('footer-git-branch');
                if (footerBranch) {
                    footerBranch.textContent = data.branch || 'unknown';
                }
                if (footerBranch) {
                    footerBranch.style.display = 'inline';
                }
            } else {
                console.error('Git branch request failed:', data.error);
            }
        });
    }

    /**
     * Update connection status display
     * @param {string} status - Status text to display
     * @param {string} type - Status type for styling
     */
    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            // Check if there's a span indicator first
            const indicator = statusElement.querySelector('span');
            if (indicator) {
                // If there's a span, update the text content after the span
                const statusIndicator = type === 'connected' ? '●' : '●';
                statusElement.innerHTML = `<span>${statusIndicator}</span> ${status}`;
            } else {
                // If no span, just update text content
                statusElement.textContent = status;
            }

            statusElement.className = `status-badge status-${type}`;
            console.log(`SocketManager: UI updated - status: '${status}' (${type})`);
        } else {
            console.error('SocketManager: Could not find connection-status element in DOM');
        }
    }

    /**
     * Connect to socket server
     * @param {number} port - Port number to connect to
     */
    connect(port) {
        if (this.socketClient) {
            this.socketClient.connect(port);
        }
    }

    /**
     * Disconnect from socket server
     */
    disconnect() {
        if (this.socketClient) {
            this.socketClient.disconnect();
        }
    }

    /**
     * Check if socket is connected
     * @returns {boolean} - True if connected
     */
    isConnected() {
        return this.socketClient && this.socketClient.isConnected;
    }

    /**
     * Check if socket is connecting
     * @returns {boolean} - True if connecting
     */
    isConnecting() {
        return this.socketClient && this.socketClient.isConnecting;
    }

    /**
     * Get the underlying socket client
     * @returns {SocketClient} - The socket client instance
     */
    getSocketClient() {
        return this.socketClient;
    }

    /**
     * Get the raw socket connection
     * @returns {Socket|null} - The raw socket or null
     */
    getSocket() {
        return this.socketClient ? this.socketClient.socket : null;
    }

    /**
     * Register a callback for connection status changes
     * @param {Function} callback - Callback function(status, type)
     */
    onConnectionStatusChange(callback) {
        this.connectionCallbacks.add(callback);
    }

    /**
     * Unregister a connection status callback
     * @param {Function} callback - Callback to remove
     */
    offConnectionStatusChange(callback) {
        this.connectionCallbacks.delete(callback);
    }

    /**
     * Register a callback for event updates
     * @param {Function} callback - Callback function(events)
     */
    onEventUpdate(callback) {
        this.eventUpdateCallbacks.add(callback);
    }

    /**
     * Unregister an event update callback
     * @param {Function} callback - Callback to remove
     */
    offEventUpdate(callback) {
        this.eventUpdateCallbacks.delete(callback);
    }

    /**
     * Toggle connection controls visibility
     */
    toggleConnectionControls() {
        const controlsRow = document.getElementById('connection-controls-row');
        const toggleBtn = document.getElementById('connection-toggle-btn');

        if (controlsRow && toggleBtn) {
            const isVisible = controlsRow.classList.contains('show');

            if (isVisible) {
                controlsRow.classList.remove('show');
                controlsRow.style.display = 'none';
                toggleBtn.textContent = 'Connection Settings';
            } else {
                controlsRow.classList.add('show');
                controlsRow.style.display = 'block';
                toggleBtn.textContent = 'Hide Settings';
            }
        }
    }

    /**
     * Setup connection control event handlers
     * Called during dashboard initialization
     */
    setupConnectionControls() {
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const connectionToggleBtn = document.getElementById('connection-toggle-btn');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                const port = document.getElementById('port-input').value || 8765;
                this.connect(port);
            });
        }

        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                this.disconnect();
            });
        }

        if (connectionToggleBtn) {
            connectionToggleBtn.addEventListener('click', () => {
                this.toggleConnectionControls();
            });
        }
    }

    /**
     * Initialize connection from URL parameters
     * @param {URLSearchParams} params - URL search parameters
     */
    initializeFromURL(params) {
        const port = params.get('port');
        const portInput = document.getElementById('port-input');

        // Determine the port to use:
        // 1. URL parameter 'port'
        // 2. Current page port (if served via HTTP)
        // 3. Default port value from input field
        // 4. Fallback to 8765
        let connectPort = port;
        if (!connectPort && window.location.protocol === 'http:') {
            connectPort = window.location.port || '8765';
        }
        if (!connectPort) {
            connectPort = portInput?.value || '8765';
        }

        // Update the port input field with the determined port
        if (portInput) {
            portInput.value = connectPort;
        }

        // Auto-connect by default unless explicitly disabled
        // Changed: Always auto-connect by default even without URL params
        const shouldAutoConnect = params.get('connect') !== 'false';
        if (shouldAutoConnect && !this.isConnected() && !this.isConnecting()) {
            console.log(`SocketManager: Auto-connecting to port ${connectPort}`);
            this.connect(connectPort);
        }
    }
}

// ES6 Module export
export { SocketManager };
export default SocketManager;
