/**
 * Connection Debug Panel
 * 
 * Provides detailed connection metrics and debugging tools
 * for troubleshooting connection issues.
 */

class ConnectionDebugPanel {
    constructor(connectionManager) {
        this.connectionManager = connectionManager;
        this.isVisible = false;
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        // Create debug panel HTML
        this.createPanel();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start metric updates when visible
        this.connectionManager.onStatusChange(() => {
            if (this.isVisible) {
                this.updateMetrics();
            }
        });
    }
    
    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'connection-debug-panel';
        panel.className = 'connection-debug-panel';
        panel.style.display = 'none';
        
        panel.innerHTML = `
            <div class="debug-panel-header">
                <h3>🔧 Connection Debug</h3>
                <button id="close-debug-panel" class="btn-close">✕</button>
            </div>
            
            <div class="debug-panel-content">
                <!-- Connection Info -->
                <div class="debug-section">
                    <h4>Connection Info</h4>
                    <div class="debug-info">
                        <div class="info-row">
                            <span class="info-label">Client ID:</span>
                            <span id="debug-client-id" class="info-value">--</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Socket ID:</span>
                            <span id="debug-socket-id" class="info-value">--</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">State:</span>
                            <span id="debug-state" class="info-value">--</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Quality:</span>
                            <span id="debug-quality" class="info-value">--</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Last Sequence:</span>
                            <span id="debug-sequence" class="info-value">--</span>
                        </div>
                    </div>
                </div>
                
                <!-- Connection Metrics -->
                <div class="debug-section">
                    <h4>Metrics</h4>
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <span class="metric-value" id="debug-total-events">0</span>
                            <span class="metric-label">Total Events</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-value" id="debug-events-acked">0</span>
                            <span class="metric-label">Acknowledged</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-value" id="debug-buffered">0</span>
                            <span class="metric-label">Buffered</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-value" id="debug-reconnects">0</span>
                            <span class="metric-label">Reconnects</span>
                        </div>
                    </div>
                </div>
                
                <!-- Connection Timeline -->
                <div class="debug-section">
                    <h4>Connection Timeline</h4>
                    <div id="debug-timeline" class="debug-timeline">
                        <!-- Timeline events will be added here -->
                    </div>
                </div>
                
                <!-- Debug Actions -->
                <div class="debug-section">
                    <h4>Debug Actions</h4>
                    <div class="debug-actions">
                        <button id="debug-force-reconnect" class="btn-action">Force Reconnect</button>
                        <button id="debug-request-stats" class="btn-action">Request Stats</button>
                        <button id="debug-clear-buffer" class="btn-action">Clear Buffer</button>
                        <button id="debug-simulate-disconnect" class="btn-action">Simulate Disconnect</button>
                        <button id="debug-export-logs" class="btn-action">Export Logs</button>
                    </div>
                </div>
                
                <!-- Network Tests -->
                <div class="debug-section">
                    <h4>Network Tests</h4>
                    <div class="network-tests">
                        <div class="test-row">
                            <button id="test-latency" class="btn-test">Test Latency</button>
                            <span id="latency-result" class="test-result">--</span>
                        </div>
                        <div class="test-row">
                            <button id="test-throughput" class="btn-test">Test Throughput</button>
                            <span id="throughput-result" class="test-result">--</span>
                        </div>
                        <div class="test-row">
                            <button id="test-stability" class="btn-test">Test Stability</button>
                            <span id="stability-result" class="test-result">--</span>
                        </div>
                    </div>
                </div>
                
                <!-- Event Log -->
                <div class="debug-section">
                    <h4>Recent Events</h4>
                    <div id="debug-event-log" class="event-log">
                        <!-- Recent events will be shown here -->
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Add styles
        this.addStyles();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .connection-debug-panel {
                position: fixed;
                right: 20px;
                top: 80px;
                width: 400px;
                max-height: 80vh;
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.15);
                z-index: 1001;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            
            .debug-panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                background: linear-gradient(135deg, #667eea 0%, #4299e1 100%);
                color: white;
            }
            
            .debug-panel-header h3 {
                margin: 0;
                font-size: 16px;
            }
            
            .btn-close {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 16px;
                transition: background 0.2s;
            }
            
            .btn-close:hover {
                background: rgba(255,255,255,0.3);
            }
            
            .debug-panel-content {
                overflow-y: auto;
                padding: 16px;
                max-height: calc(80vh - 60px);
            }
            
            .debug-section {
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .debug-section:last-child {
                border-bottom: none;
            }
            
            .debug-section h4 {
                margin: 0 0 12px 0;
                font-size: 14px;
                color: #2d3748;
                font-weight: 600;
            }
            
            .debug-info {
                background: #f7fafc;
                padding: 12px;
                border-radius: 8px;
            }
            
            .info-row {
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                font-size: 13px;
            }
            
            .info-label {
                color: #718096;
            }
            
            .info-value {
                font-family: 'SF Mono', Monaco, monospace;
                color: #2d3748;
                font-weight: 500;
            }
            
            .debug-actions {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }
            
            .btn-action {
                padding: 8px 12px;
                background: #4299e1;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            .btn-action:hover {
                background: #3182ce;
            }
            
            .network-tests {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .test-row {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .btn-test {
                flex: 0 0 120px;
                padding: 6px 12px;
                background: #805ad5;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
            }
            
            .test-result {
                flex: 1;
                padding: 6px 12px;
                background: #f7fafc;
                border-radius: 6px;
                font-size: 12px;
                font-family: 'SF Mono', Monaco, monospace;
            }
            
            .debug-timeline {
                max-height: 150px;
                overflow-y: auto;
                background: #f7fafc;
                padding: 8px;
                border-radius: 8px;
                font-size: 12px;
            }
            
            .timeline-event {
                padding: 4px 0;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .timeline-event:last-child {
                border-bottom: none;
            }
            
            .timeline-time {
                color: #718096;
                font-size: 11px;
            }
            
            .timeline-desc {
                color: #2d3748;
                margin-top: 2px;
            }
            
            .event-log {
                max-height: 200px;
                overflow-y: auto;
                background: #1a202c;
                color: #e2e8f0;
                padding: 12px;
                border-radius: 8px;
                font-family: 'SF Mono', Monaco, monospace;
                font-size: 11px;
            }
            
            .log-entry {
                padding: 2px 0;
            }
            
            .log-time {
                color: #718096;
            }
            
            .log-type {
                color: #4299e1;
                font-weight: 600;
            }
            
            .log-data {
                color: #cbd5e0;
            }
            
            @media (max-width: 768px) {
                .connection-debug-panel {
                    right: 10px;
                    left: 10px;
                    width: auto;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        // Close button
        document.getElementById('close-debug-panel').addEventListener('click', () => {
            this.hide();
        });
        
        // Debug actions
        document.getElementById('debug-force-reconnect').addEventListener('click', () => {
            this.forceReconnect();
        });
        
        document.getElementById('debug-request-stats').addEventListener('click', () => {
            this.requestStats();
        });
        
        document.getElementById('debug-clear-buffer').addEventListener('click', () => {
            this.clearBuffer();
        });
        
        document.getElementById('debug-simulate-disconnect').addEventListener('click', () => {
            this.simulateDisconnect();
        });
        
        document.getElementById('debug-export-logs').addEventListener('click', () => {
            this.exportLogs();
        });
        
        // Network tests
        document.getElementById('test-latency').addEventListener('click', () => {
            this.testLatency();
        });
        
        document.getElementById('test-throughput').addEventListener('click', () => {
            this.testThroughput();
        });
        
        document.getElementById('test-stability').addEventListener('click', () => {
            this.testStability();
        });
    }
    
    show() {
        const panel = document.getElementById('connection-debug-panel');
        panel.style.display = 'flex';
        this.isVisible = true;
        
        // Start metric updates
        this.startMetricUpdates();
        
        // Initial update
        this.updateMetrics();
    }
    
    hide() {
        const panel = document.getElementById('connection-debug-panel');
        panel.style.display = 'none';
        this.isVisible = false;
        
        // Stop metric updates
        this.stopMetricUpdates();
    }
    
    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    startMetricUpdates() {
        this.updateInterval = setInterval(() => {
            this.updateMetrics();
        }, 1000);
    }
    
    stopMetricUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    updateMetrics() {
        const metrics = this.connectionManager.getMetrics();
        const socket = this.connectionManager.socket;
        
        // Update connection info
        document.getElementById('debug-client-id').textContent = metrics.clientId || '--';
        document.getElementById('debug-socket-id').textContent = socket?.id || '--';
        document.getElementById('debug-state').textContent = metrics.connectionState || '--';
        document.getElementById('debug-quality').textContent = 
            `${Math.round(metrics.connectionQuality * 100)}%`;
        document.getElementById('debug-sequence').textContent = metrics.lastSequence || '0';
        
        // Update metrics
        document.getElementById('debug-total-events').textContent = metrics.totalEvents || '0';
        document.getElementById('debug-events-acked').textContent = metrics.eventsAcked || '0';
        document.getElementById('debug-buffered').textContent = metrics.bufferedEvents || '0';
        document.getElementById('debug-reconnects').textContent = metrics.totalReconnections || '0';
    }
    
    addTimelineEvent(description) {
        const timeline = document.getElementById('debug-timeline');
        const event = document.createElement('div');
        event.className = 'timeline-event';
        
        const now = new Date();
        event.innerHTML = `
            <div class="timeline-time">${now.toLocaleTimeString()}</div>
            <div class="timeline-desc">${description}</div>
        `;
        
        timeline.insertBefore(event, timeline.firstChild);
        
        // Keep only last 20 events
        while (timeline.children.length > 20) {
            timeline.removeChild(timeline.lastChild);
        }
    }
    
    addLogEntry(type, data) {
        const log = document.getElementById('debug-event-log');
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        const now = new Date();
        entry.innerHTML = `
            <span class="log-time">${now.toLocaleTimeString()}</span>
            <span class="log-type">${type}</span>
            <span class="log-data">${JSON.stringify(data)}</span>
        `;
        
        log.insertBefore(entry, log.firstChild);
        
        // Keep only last 50 entries
        while (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }
    
    // Debug actions
    forceReconnect() {
        this.addTimelineEvent('Force reconnect initiated');
        if (this.connectionManager.socket) {
            this.connectionManager.socket.disconnect();
            setTimeout(() => {
                this.connectionManager.socket.connect();
            }, 100);
        }
    }
    
    requestStats() {
        this.addTimelineEvent('Requesting connection stats');
        if (this.connectionManager.socket) {
            this.connectionManager.socket.emit('get_connection_stats');
        }
    }
    
    clearBuffer() {
        this.addTimelineEvent('Clearing event buffer');
        this.connectionManager.eventBuffer = [];
        localStorage.removeItem('claude_mpm_event_buffer');
        this.updateMetrics();
    }
    
    simulateDisconnect() {
        this.addTimelineEvent('Simulating disconnect');
        if (this.connectionManager.socket) {
            this.connectionManager.socket.disconnect();
        }
    }
    
    exportLogs() {
        const logs = {
            metrics: this.connectionManager.getMetrics(),
            timeline: [],
            events: []
        };
        
        // Collect timeline events
        const timeline = document.getElementById('debug-timeline');
        Array.from(timeline.children).forEach(child => {
            logs.timeline.push(child.textContent.trim());
        });
        
        // Collect event log
        const eventLog = document.getElementById('debug-event-log');
        Array.from(eventLog.children).forEach(child => {
            logs.events.push(child.textContent.trim());
        });
        
        // Download as JSON
        const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `connection-debug-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.addTimelineEvent('Logs exported');
    }
    
    // Network tests
    async testLatency() {
        const resultEl = document.getElementById('latency-result');
        resultEl.textContent = 'Testing...';
        
        const start = Date.now();
        this.connectionManager.socket.emit('ping');
        
        // Wait for pong
        const pongHandler = () => {
            const latency = Date.now() - start;
            resultEl.textContent = `${latency}ms`;
            this.connectionManager.socket.off('pong', pongHandler);
            this.addTimelineEvent(`Latency test: ${latency}ms`);
        };
        
        this.connectionManager.socket.on('pong', pongHandler);
        
        // Timeout after 5 seconds
        setTimeout(() => {
            this.connectionManager.socket.off('pong', pongHandler);
            if (resultEl.textContent === 'Testing...') {
                resultEl.textContent = 'Timeout';
            }
        }, 5000);
    }
    
    async testThroughput() {
        const resultEl = document.getElementById('throughput-result');
        resultEl.textContent = 'Testing...';
        
        // Send 100 events rapidly
        const start = Date.now();
        let received = 0;
        
        const handler = () => {
            received++;
            if (received === 100) {
                const duration = (Date.now() - start) / 1000;
                const throughput = Math.round(100 / duration);
                resultEl.textContent = `${throughput} evt/s`;
                this.addTimelineEvent(`Throughput test: ${throughput} events/sec`);
            }
        };
        
        this.connectionManager.socket.on('test_response', handler);
        
        for (let i = 0; i < 100; i++) {
            this.connectionManager.socket.emit('test_event', { index: i });
        }
        
        // Cleanup after 10 seconds
        setTimeout(() => {
            this.connectionManager.socket.off('test_response', handler);
            if (received < 100) {
                resultEl.textContent = `${received}/100 received`;
            }
        }, 10000);
    }
    
    async testStability() {
        const resultEl = document.getElementById('stability-result');
        resultEl.textContent = 'Testing (30s)...';
        
        let disconnects = 0;
        let reconnects = 0;
        const startMetrics = { ...this.connectionManager.metrics };
        
        // Monitor for 30 seconds
        setTimeout(() => {
            const endMetrics = this.connectionManager.metrics;
            disconnects = endMetrics.totalConnections - startMetrics.totalConnections;
            
            if (disconnects === 0) {
                resultEl.textContent = 'Stable ✓';
            } else {
                resultEl.textContent = `${disconnects} drops`;
            }
            
            this.addTimelineEvent(`Stability test: ${disconnects} disconnections`);
        }, 30000);
    }
}

// Export for use
export { ConnectionDebugPanel };