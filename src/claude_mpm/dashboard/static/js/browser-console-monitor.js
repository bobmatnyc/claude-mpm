/**
 * Browser Console Monitor for Claude MPM
 * =====================================
 * 
 * Injectable script that captures browser console events and sends them
 * to the Claude MPM monitor server for centralized logging and debugging.
 * 
 * DESIGN DECISIONS:
 * - Generates unique browser ID for session tracking
 * - Intercepts all console methods without disrupting normal operation  
 * - Provides real-time streaming to monitor server via Socket.IO
 * - Includes visual indicator showing monitoring status
 * - Handles reconnection gracefully for reliability
 * - Captures stack traces for error context
 * 
 * USAGE:
 * Include this script in any page: <script src="http://localhost:8765/api/browser-monitor.js"></script>
 * The script will automatically connect to the monitor server and start capturing console events.
 */

(function() {
    'use strict';
    
    // Configuration - MONITOR_PORT will be replaced dynamically by server
    const MONITOR_PORT = __MONITOR_PORT__;
    const MONITOR_HOST = 'localhost';
    
    // Generate unique browser ID for this session
    const BROWSER_ID = `browser-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Console levels to intercept
    const CONSOLE_LEVELS = ['log', 'warn', 'error', 'info', 'debug', 'trace'];
    
    // State management
    let socket = null;
    let isConnected = false;
    let eventQueue = [];
    let indicator = null;
    let originalConsole = {};
    
    // Connection retry configuration
    const RETRY_CONFIG = {
        maxRetries: 5,
        retryDelay: 1000,
        currentRetries: 0
    };
    
    /**
     * Initialize the browser console monitoring system
     */
    function initializeMonitor() {
        try {
            console.log(`[Browser Monitor] Initializing for browser ID: ${BROWSER_ID}`);
            
            // Store original console methods before interception
            storeOriginalConsoleMethods();
            
            // Setup Socket.IO connection
            setupSocketConnection();
            
            // Intercept console methods
            interceptConsoleMethods();
            
            // Create visual indicator
            createStatusIndicator();
            
            // Setup cleanup handlers
            setupCleanupHandlers();
            
        } catch (error) {
            console.error('[Browser Monitor] Failed to initialize:', error);
        }
    }
    
    /**
     * Store references to original console methods
     */
    function storeOriginalConsoleMethods() {
        CONSOLE_LEVELS.forEach(level => {
            if (console[level] && typeof console[level] === 'function') {
                originalConsole[level] = console[level].bind(console);
            }
        });
    }
    
    /**
     * Setup Socket.IO connection to monitor server
     */
    function setupSocketConnection() {
        try {
            // Load Socket.IO if not already available
            if (typeof io === 'undefined') {
                loadSocketIO(() => {
                    createSocketConnection();
                });
            } else {
                createSocketConnection();
            }
        } catch (error) {
            console.error('[Browser Monitor] Socket setup error:', error);
            updateIndicatorStatus('error', 'Socket setup failed');
        }
    }
    
    /**
     * Load Socket.IO library dynamically
     */
    function loadSocketIO(callback) {
        const script = document.createElement('script');
        script.src = `http://${MONITOR_HOST}:${MONITOR_PORT}/socket.io/socket.io.js`;
        script.onload = callback;
        script.onerror = () => {
            console.error('[Browser Monitor] Failed to load Socket.IO');
            updateIndicatorStatus('error', 'Failed to load Socket.IO');
        };
        document.head.appendChild(script);
    }
    
    /**
     * Create the actual Socket.IO connection
     */
    function createSocketConnection() {
        try {
            socket = io(`http://${MONITOR_HOST}:${MONITOR_PORT}`, {
                transports: ['websocket', 'polling'],
                timeout: 5000,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: RETRY_CONFIG.maxRetries
            });
            
            // Connection event handlers
            socket.on('connect', handleSocketConnect);
            socket.on('disconnect', handleSocketDisconnect);
            socket.on('error', handleSocketError);
            socket.on('reconnect', handleSocketReconnect);
            
            // Send initial connection event
            setTimeout(() => {
                if (socket && socket.connected) {
                    sendBrowserEvent('connect', {
                        browser_id: BROWSER_ID,
                        user_agent: navigator.userAgent,
                        url: window.location.href,
                        timestamp: new Date().toISOString()
                    });
                }
            }, 100);
            
        } catch (error) {
            console.error('[Browser Monitor] Socket connection error:', error);
            updateIndicatorStatus('error', 'Connection failed');
        }
    }
    
    /**
     * Handle socket connection
     */
    function handleSocketConnect() {
        isConnected = true;
        RETRY_CONFIG.currentRetries = 0;
        
        updateIndicatorStatus('connected', `Connected: ${BROWSER_ID}`);
        
        // Send queued events
        flushEventQueue();
        
        console.log(`[Browser Monitor] Connected to monitor server: ${BROWSER_ID}`);
    }
    
    /**
     * Handle socket disconnection
     */
    function handleSocketDisconnect(reason) {
        isConnected = false;
        updateIndicatorStatus('disconnected', `Disconnected: ${reason}`);
        console.log(`[Browser Monitor] Disconnected from monitor server: ${reason}`);
    }
    
    /**
     * Handle socket errors
     */
    function handleSocketError(error) {
        console.error('[Browser Monitor] Socket error:', error);
        updateIndicatorStatus('error', 'Connection error');
    }
    
    /**
     * Handle socket reconnection
     */
    function handleSocketReconnect() {
        console.log('[Browser Monitor] Reconnected to monitor server');
        updateIndicatorStatus('connected', `Reconnected: ${BROWSER_ID}`);
    }
    
    /**
     * Intercept console methods and capture events
     */
    function interceptConsoleMethods() {
        CONSOLE_LEVELS.forEach(level => {
            if (originalConsole[level]) {
                console[level] = function(...args) {
                    // Capture the console event
                    captureConsoleEvent(level, args);
                    
                    // Call original console method
                    return originalConsole[level].apply(console, args);
                };
            }
        });
    }
    
    /**
     * Capture console event and send to monitor server
     */
    function captureConsoleEvent(level, args) {
        try {
            const timestamp = new Date().toISOString();
            const stack = (new Error()).stack;
            
            // Serialize arguments safely
            const serializedArgs = args.map(arg => {
                if (arg === null) return 'null';
                if (arg === undefined) return 'undefined';
                
                if (typeof arg === 'object') {
                    try {
                        return JSON.stringify(arg, null, 2);
                    } catch (e) {
                        return '[Circular Object]';
                    }
                } else if (typeof arg === 'function') {
                    return `[Function: ${arg.name || 'anonymous'}]`;
                } else {
                    return String(arg);
                }
            });
            
            const message = serializedArgs.join(' ');
            
            // Create event data
            const eventData = {
                browser_id: BROWSER_ID,
                level: level.toUpperCase(),
                timestamp: timestamp,
                message: message,
                args: serializedArgs,
                stack: stack,
                url: window.location.href,
                line_info: extractLineInfo(stack)
            };
            
            // Send to monitor server
            sendBrowserEvent('console', eventData);
            
        } catch (error) {
            // Use original console to avoid infinite recursion
            originalConsole.error('[Browser Monitor] Error capturing console event:', error);
        }
    }
    
    /**
     * Extract line information from stack trace
     */
    function extractLineInfo(stack) {
        if (!stack) return null;
        
        try {
            const lines = stack.split('\n');
            // Find the first line that's not from this monitoring script
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line && !line.includes('browser-console-monitor.js')) {
                    return line;
                }
            }
            return lines[1] || null;
        } catch (error) {
            return null;
        }
    }
    
    /**
     * Send browser event to monitor server
     */
    function sendBrowserEvent(eventType, data) {
        const event = {
            type: eventType,
            data: data,
            timestamp: new Date().toISOString()
        };
        
        if (isConnected && socket) {
            socket.emit('browser:' + eventType, data);
        } else {
            // Queue event for later sending
            eventQueue.push(event);
            
            // Limit queue size to prevent memory issues
            if (eventQueue.length > 1000) {
                eventQueue = eventQueue.slice(-500); // Keep last 500 events
            }
        }
    }
    
    /**
     * Flush queued events when connection is restored
     */
    function flushEventQueue() {
        if (eventQueue.length > 0 && isConnected && socket) {
            console.log(`[Browser Monitor] Sending ${eventQueue.length} queued events`);
            
            eventQueue.forEach(event => {
                socket.emit('browser:' + event.type, event.data);
            });
            
            eventQueue = [];
        }
    }
    
    /**
     * Create visual status indicator
     */
    function createStatusIndicator() {
        try {
            indicator = document.createElement('div');
            indicator.id = 'browser-console-monitor-indicator';
            indicator.style.cssText = `
                position: fixed !important;
                bottom: 10px !important;
                right: 10px !important;
                background: #2d3748 !important;
                color: #e2e8f0 !important;
                padding: 8px 12px !important;
                border-radius: 6px !important;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
                font-size: 11px !important;
                z-index: 999999 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
                border: 1px solid #4a5568 !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
                min-width: 180px !important;
                text-align: left !important;
            `;
            
            // Add hover effect
            indicator.onmouseover = () => {
                indicator.style.transform = 'scale(1.05)';
                indicator.style.boxShadow = '0 6px 20px rgba(0,0,0,0.25)';
            };
            
            indicator.onmouseout = () => {
                indicator.style.transform = 'scale(1)';
                indicator.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            };
            
            // Add click to toggle detailed info
            indicator.onclick = () => {
                showMonitorInfo();
            };
            
            updateIndicatorStatus('connecting', 'Connecting...');
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    document.body.appendChild(indicator);
                });
            } else {
                document.body.appendChild(indicator);
            }
            
        } catch (error) {
            console.error('[Browser Monitor] Error creating indicator:', error);
        }
    }
    
    /**
     * Update status indicator
     */
    function updateIndicatorStatus(status, message) {
        if (!indicator) return;
        
        const statusColors = {
            connecting: '#f6ad55',    // orange
            connected: '#48bb78',     // green
            disconnected: '#f56565',  // red
            error: '#e53e3e'          // dark red
        };
        
        const statusIcons = {
            connecting: '🔄',
            connected: '✅',
            disconnected: '❌',
            error: '⚠️'
        };
        
        indicator.style.backgroundColor = statusColors[status] || '#2d3748';
        indicator.innerHTML = `
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-size: 12px;">${statusIcons[status] || '📡'}</span>
                <span style="font-weight: 500;">Console Monitor</span>
            </div>
            <div style="font-size: 10px; opacity: 0.9; margin-top: 2px;">
                ${message || status}
            </div>
        `;
    }
    
    /**
     * Show detailed monitor information
     */
    function showMonitorInfo() {
        const info = {
            browserID: BROWSER_ID,
            status: isConnected ? 'Connected' : 'Disconnected',
            server: `${MONITOR_HOST}:${MONITOR_PORT}`,
            queuedEvents: eventQueue.length,
            url: window.location.href,
            userAgent: navigator.userAgent.substring(0, 50) + '...'
        };
        
        console.group('📡 Browser Console Monitor Info');
        Object.entries(info).forEach(([key, value]) => {
            console.log(`${key}:`, value);
        });
        console.groupEnd();
    }
    
    /**
     * Setup cleanup handlers for page unload
     */
    function setupCleanupHandlers() {
        window.addEventListener('beforeunload', () => {
            if (socket && isConnected) {
                sendBrowserEvent('disconnect', {
                    browser_id: BROWSER_ID,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // Cleanup on page hide (mobile support)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && socket && isConnected) {
                sendBrowserEvent('hide', {
                    browser_id: BROWSER_ID,
                    timestamp: new Date().toISOString()
                });
            }
        });
    }
    
    /**
     * Restore original console methods (for cleanup)
     */
    function restoreConsole() {
        CONSOLE_LEVELS.forEach(level => {
            if (originalConsole[level]) {
                console[level] = originalConsole[level];
            }
        });
    }
    
    // Expose cleanup function globally for manual cleanup if needed
    window.browserConsoleMonitor = {
        disconnect: () => {
            if (socket) {
                socket.disconnect();
            }
            restoreConsole();
            if (indicator && indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        },
        getInfo: () => ({
            browserID: BROWSER_ID,
            isConnected: isConnected,
            queuedEvents: eventQueue.length
        })
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeMonitor);
    } else {
        // DOM already loaded
        initializeMonitor();
    }
    
    // Also initialize immediately in case DOMContentLoaded has already fired
    setTimeout(initializeMonitor, 100);
    
})();