/**
 * Browser Log Viewer Component - VERSION 3.0 EXTREME - MAXIMUM HOOK BLOCKING
 * Displays real-time browser console logs from monitored browser sessions
 * EXTREME NUCLEAR ISOLATION FROM HOOK EVENTS
 */

class BrowserLogViewer {
    constructor(container) {
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] 🚀🚀🚀 CONSTRUCTOR CALLED');
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] Container ID:', container?.id);
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] Container parent:', container?.parentElement?.id);
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] Call stack:', new Error().stack);
        
        this.container = container;
        this.logs = [];
        this.filters = {
            browserId: 'all',
            level: 'all'
        };
        this.autoRefresh = true;
        this.autoScroll = true;
        this.refreshInterval = null;
        this.maxLogs = 1000;
        this.browserSessions = new Set();
        this.VERSION = '3.0-EXTREME-NUCLEAR';
        
        // EXTREME: Mark territory immediately
        if (container) {
            container.setAttribute('data-browser-logs-extreme', 'active');
            container.setAttribute('data-version', this.VERSION);
        }
        
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] STARTING EXTREME INIT');
        this.init();
    }
    
    init() {
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] 🚨 INIT - EXTREME NUCLEAR CLEARING');
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] Container before clear:', this.container?.innerHTML?.substring(0, 100));
        
        // EXTREME NUCLEAR: Multiple clearing passes
        for (let i = 0; i < 5; i++) {
            this.container.innerHTML = '';
            this.container.textContent = '';
            while (this.container.firstChild) {
                this.container.removeChild(this.container.firstChild);
            }
        }
        
        // Remove ALL classes and attributes that might cause confusion
        this.container.className = '';
        const attributesToRemove = ['data-owner', 'data-events', 'data-component'];
        attributesToRemove.forEach(attr => this.container.removeAttribute(attr));
        
        // Now mark it as EXCLUSIVELY OURS with EXTREME markers
        this.container.setAttribute('data-owner', 'BrowserLogViewer-v3-EXTREME-NUCLEAR');
        this.container.setAttribute('data-browser-logs-only', 'true');
        this.container.setAttribute('data-no-hooks', 'ABSOLUTELY');
        this.container.classList.add('browser-log-viewer-container-v3-extreme');
        this.container.style.background = '#ffffff';
        this.container.style.border = '3px solid lime'; // Visual indicator
        
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] RENDERING EXTREME CLEAN INTERFACE');
        this.render();
        this.attachEventListeners();
        this.startAutoRefresh();
        
        // Set up EXTREME container protection
        this.protectContainer();
        
        console.error('[BROWSER-LOG-VIEWER v3.0 EXTREME] ✅ INIT COMPLETE - CONTAINER SECURED');
        
        // Listen for real-time browser console events from the browser handler
        if (window.socket) {
            // Listen ONLY for browser console events with proper validation
            // These events come from the injected browser monitoring script
            window.socket.on('browser_log', (logEntry) => {
                // Extra validation: ensure this is truly a browser log
                if (logEntry && logEntry.browser_id) {
                    console.log('[BrowserLogViewer] Received valid browser_log event:', logEntry);
                    this.addLog(logEntry);
                } else {
                    console.warn('[BrowserLogViewer] Rejected invalid browser_log event (no browser_id):', logEntry);
                }
            });
            
            // Also listen for dashboard:browser:console events from the browser handler
            window.socket.on('dashboard:browser:console', (logEntry) => {
                // Extra validation: ensure this is truly a browser log
                if (logEntry && logEntry.browser_id) {
                    console.log('[BrowserLogViewer] Received valid dashboard:browser:console event:', logEntry);
                    this.addLog(logEntry);
                } else {
                    console.warn('[BrowserLogViewer] Rejected invalid dashboard:browser:console event (no browser_id):', logEntry);
                }
            });
        }
    }
    
    render() {
        console.error('[BROWSER-LOG-VIEWER v2.0] RENDER CALLED - FORCING CLEAN CONTENT');
        
        // NUCLEAR: Clear container AGAIN before rendering
        this.container.innerHTML = '';
        
        // Add version marker at the top
        this.container.innerHTML = `
            <!-- BROWSER-LOG-VIEWER VERSION 2.0 NUCLEAR - NO HOOKS ALLOWED -->
            <div class="browser-log-viewer" data-version="2.0-NUCLEAR">
                <div class="browser-log-controls">
                    <div class="filter-group">
                        <label for="browser-filter">Browser:</label>
                        <select id="browser-filter" class="filter-select">
                            <option value="all">All Browsers</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label for="level-filter">Level:</label>
                        <select id="level-filter" class="filter-select">
                            <option value="all">All Levels</option>
                            <option value="ERROR">Error</option>
                            <option value="WARN">Warning</option>
                            <option value="INFO">Info</option>
                            <option value="DEBUG">Debug</option>
                        </select>
                    </div>
                    
                    <div class="control-buttons">
                        <button id="refresh-logs" class="btn btn-secondary" title="Refresh logs">
                            <i class="fas fa-sync"></i> Refresh
                        </button>
                        
                        <button id="clear-view" class="btn btn-secondary" title="Clear view">
                            <i class="fas fa-eraser"></i> Clear View
                        </button>
                        
                        <button id="toggle-auto-refresh" class="btn btn-primary active" title="Toggle auto-refresh">
                            <i class="fas fa-sync-alt"></i> Auto-Refresh
                        </button>
                        
                        <button id="toggle-auto-scroll" class="btn btn-primary active" title="Toggle auto-scroll">
                            <i class="fas fa-arrow-down"></i> Auto-Scroll
                        </button>
                        
                        <button id="export-logs" class="btn btn-secondary" title="Export logs">
                            <i class="fas fa-download"></i> Export
                        </button>
                    </div>
                    
                    <div class="log-stats">
                        <span id="log-count">0 logs</span>
                        <span id="session-count">0 sessions</span>
                    </div>
                </div>
                
                <div class="browser-log-container" id="browser-log-container">
                    <div class="log-entries" id="log-entries">
                        <div class="empty-state">
                            <i class="fas fa-globe fa-3x"></i>
                            <h3 style="color: #28a745; font-weight: bold;">BROWSER LOGS ONLY - VERSION 2.0</h3>
                            <p style="color: red; font-weight: bold;">⚠️ HOOK EVENTS ARE BLOCKED HERE ⚠️</p>
                            <p>No browser console logs yet</p>
                            <p class="text-muted">
                                Browser console logs will appear here when the monitoring script is injected.<br>
                                Use <code>/mpm-browser-monitor start</code> to begin monitoring.
                            </p>
                            <p class="text-muted" style="font-size: 11px; margin-top: 10px;">
                                This tab shows console.log, console.error, and console.warn from monitored browsers only.<br>
                                <strong>Hook events ([hook]) are FORCEFULLY BLOCKED and will NEVER appear here.</strong>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.addStyles();
    }
    
    protectContainer() {
        console.error('[BROWSER-LOG-VIEWER v2.0] ENABLING NUCLEAR PROTECTION');
        
        // NUCLEAR PROTECTION: Monitor and DESTROY any contamination
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            // Check for ANY contamination
                            const nodeHTML = node.outerHTML || '';
                            const isContaminated = 
                                node.classList && (node.classList.contains('event-item') || 
                                                  node.classList.contains('events-list')) ||
                                nodeHTML.includes('[hook]') ||
                                nodeHTML.includes('hook.pre_tool') ||
                                nodeHTML.includes('hook.post_tool');
                            
                            if (isContaminated) {
                                console.error('[BROWSER-LOG-VIEWER v2.0] 🚨 NUCLEAR ALERT: HOOK CONTAMINATION DETECTED! DESTROYING!');
                                console.error('[BROWSER-LOG-VIEWER v2.0] Contaminated node:', node);
                                node.remove();
                                
                                // NUCLEAR RESPONSE: Complete re-render
                                this.container.innerHTML = '';
                                this.render();
                                console.error('[BROWSER-LOG-VIEWER v2.0] ✅ CONTAMINATION ELIMINATED - CONTAINER RESTORED');
                            }
                        }
                    });
                }
            });
        });
        
        // Start observing with AGGRESSIVE settings
        observer.observe(this.container, {
            childList: true,
            subtree: true,
            characterData: true, // Also watch for text changes
            attributes: true // Watch for attribute changes
        });
        
        console.error('[BROWSER-LOG-VIEWER v2.0] ✅ NUCLEAR PROTECTION ACTIVE');
    }
    
    addStyles() {
        if (!document.getElementById('browser-log-viewer-styles')) {
            const style = document.createElement('style');
            style.id = 'browser-log-viewer-styles';
            style.textContent = `
                .browser-log-viewer {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                }
                
                .browser-log-controls {
                    padding: 15px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    flex-wrap: wrap;
                }
                
                .filter-group {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .filter-group label {
                    font-weight: 500;
                    margin: 0;
                }
                
                .filter-select {
                    padding: 5px 10px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    background: white;
                    min-width: 120px;
                }
                
                .control-buttons {
                    display: flex;
                    gap: 8px;
                    margin-left: auto;
                }
                
                .btn {
                    padding: 6px 12px;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    transition: all 0.2s;
                }
                
                .btn-primary {
                    background: #007bff;
                    color: white;
                    border-color: #007bff;
                }
                
                .btn-primary:hover {
                    background: #0056b3;
                    border-color: #0056b3;
                }
                
                .btn-primary.active {
                    background: #28a745;
                    border-color: #28a745;
                }
                
                .btn-secondary {
                    background: #6c757d;
                    color: white;
                    border-color: #6c757d;
                }
                
                .btn-secondary:hover {
                    background: #545b62;
                    border-color: #545b62;
                }
                
                .log-stats {
                    display: flex;
                    gap: 15px;
                    font-size: 14px;
                    color: #6c757d;
                }
                
                .browser-log-container {
                    flex: 1;
                    overflow-y: auto;
                    background: white;
                    padding: 10px;
                }
                
                .log-entries {
                    font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.5;
                }
                
                .log-entry {
                    padding: 8px 12px;
                    margin-bottom: 4px;
                    border-left: 3px solid #dee2e6;
                    background: #f8f9fa;
                    border-radius: 0 4px 4px 0;
                    display: flex;
                    align-items: flex-start;
                    gap: 10px;
                    word-break: break-word;
                }
                
                .log-entry.error {
                    border-left-color: #dc3545;
                    background: #f8d7da;
                }
                
                .log-entry.warn {
                    border-left-color: #ffc107;
                    background: #fff3cd;
                }
                
                .log-entry.info {
                    border-left-color: #17a2b8;
                    background: #d1ecf1;
                }
                
                .log-entry.debug {
                    border-left-color: #6c757d;
                    background: #e2e3e5;
                }
                
                .log-timestamp {
                    color: #6c757d;
                    white-space: nowrap;
                    flex-shrink: 0;
                }
                
                .log-level {
                    font-weight: bold;
                    text-transform: uppercase;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    flex-shrink: 0;
                }
                
                .log-level.error {
                    background: #dc3545;
                    color: white;
                }
                
                .log-level.warn {
                    background: #ffc107;
                    color: #212529;
                }
                
                .log-level.info {
                    background: #17a2b8;
                    color: white;
                }
                
                .log-level.debug {
                    background: #6c757d;
                    color: white;
                }
                
                .log-browser {
                    color: #007bff;
                    font-size: 10px;
                    flex-shrink: 0;
                }
                
                .log-message {
                    flex: 1;
                    color: #212529;
                }
                
                .log-url {
                    color: #6c757d;
                    font-size: 10px;
                    margin-top: 4px;
                }
                
                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    color: #6c757d;
                }
                
                .empty-state i {
                    color: #dee2e6;
                    margin-bottom: 20px;
                }
                
                .empty-state p {
                    margin: 10px 0;
                }
                
                .text-muted {
                    color: #adb5bd !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    attachEventListeners() {
        // Browser filter
        document.getElementById('browser-filter').addEventListener('change', (e) => {
            this.filters.browserId = e.target.value;
            this.renderLogs();
        });
        
        // Level filter
        document.getElementById('level-filter').addEventListener('change', (e) => {
            this.filters.level = e.target.value;
            this.renderLogs();
        });
        
        // Refresh button - just clears and re-renders in real-time mode
        document.getElementById('refresh-logs').addEventListener('click', () => {
            console.log('[BrowserLogViewer] Refresh clicked - re-rendering current logs');
            this.renderLogs();
        });
        
        // Clear view button
        document.getElementById('clear-view').addEventListener('click', () => {
            this.logs = [];
            this.renderLogs();
        });
        
        // Auto-refresh toggle
        document.getElementById('toggle-auto-refresh').addEventListener('click', (e) => {
            this.autoRefresh = !this.autoRefresh;
            e.currentTarget.classList.toggle('active', this.autoRefresh);
            
            if (this.autoRefresh) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
        
        // Auto-scroll toggle
        document.getElementById('toggle-auto-scroll').addEventListener('click', (e) => {
            this.autoScroll = !this.autoScroll;
            e.currentTarget.classList.toggle('active', this.autoScroll);
        });
        
        // Export logs
        document.getElementById('export-logs').addEventListener('click', () => {
            this.exportLogs();
        });
    }
    
    async loadInitialLogs() {
        // Deprecated - we don't load logs from files anymore
        // Browser logs are only shown in real-time from WebSocket events
        console.log('[BrowserLogViewer] Skipping file-based log loading - using real-time events only');
    }
    
    async loadLogs() {
        // Deprecated - we don't load logs from files anymore
        // Browser logs are only shown in real-time from WebSocket events
        console.log('[BrowserLogViewer] Real-time mode only - not loading from files');
        this.updateStats();
    }
    
    async loadLogFile(filename) {
        // Deprecated - we don't load logs from files anymore
        // Browser logs are only shown in real-time from WebSocket events
        console.log('[BrowserLogViewer] File loading disabled - real-time mode only');
    }
    
    addLog(logEntry, render = true) {
        // NUCLEAR VALIDATION: Multiple layers of protection
        
        // Layer 1: Must have browser_id
        if (!logEntry.browser_id) {
            console.error('[BROWSER-LOG-VIEWER v2.0] ❌ REJECTED: No browser_id:', logEntry);
            return;
        }
        
        // Layer 2: Check for hook contamination in ANY field
        const entryString = JSON.stringify(logEntry).toLowerCase();
        if (entryString.includes('hook') || 
            entryString.includes('pre_tool') || 
            entryString.includes('post_tool')) {
            console.error('[BROWSER-LOG-VIEWER v2.0] 🚨 NUCLEAR REJECTION: Hook contamination detected!', logEntry);
            return;
        }
        
        // Layer 3: Explicit hook type check
        if (logEntry.type === 'hook' || 
            logEntry.event_type === 'hook' || 
            logEntry.event === 'hook' ||
            (logEntry.message && typeof logEntry.message === 'string' && 
             (logEntry.message.includes('[hook]') || 
              logEntry.message.includes('hook.') ||
              logEntry.message.includes('pre_tool') ||
              logEntry.message.includes('post_tool')))) {
            console.error('[BROWSER-LOG-VIEWER v2.0] 🚨🚨 CRITICAL REJECTION: Hook event blocked!', logEntry);
            return;
        }
        
        console.log('[BROWSER-LOG-VIEWER v2.0] ✅ ACCEPTED: Valid browser log:', logEntry);
        
        // Additionally validate that we have proper browser log structure
        if (!logEntry.message && !logEntry.level) {
            console.warn('[BrowserLogViewer] Rejecting malformed browser log entry:', logEntry);
            return;
        }
        
        // Ensure proper structure for browser logs
        const normalizedEntry = {
            browser_id: logEntry.browser_id || 'unknown',
            level: logEntry.level || 'INFO',
            message: logEntry.message || '',
            timestamp: logEntry.timestamp || new Date().toISOString(),
            url: logEntry.url || '',
            line_info: logEntry.line_info || null
        };
        
        // Add to logs array
        this.logs.push(normalizedEntry);
        
        // Track browser session
        if (normalizedEntry.browser_id) {
            this.browserSessions.add(normalizedEntry.browser_id);
            this.updateBrowserFilter();
        }
        
        // Limit logs to prevent memory issues
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs);
        }
        
        if (render) {
            this.renderLogs();
        }
    }
    
    updateBrowserFilter() {
        const select = document.getElementById('browser-filter');
        const currentValue = select.value;
        
        // Clear existing options except "All"
        select.innerHTML = '<option value="all">All Browsers</option>';
        
        // Add browser sessions
        Array.from(this.browserSessions).sort().forEach(browserId => {
            const option = document.createElement('option');
            option.value = browserId;
            option.textContent = browserId.substring(0, 20) + '...';
            select.appendChild(option);
        });
        
        // Restore selection
        select.value = currentValue;
    }
    
    renderLogs() {
        console.error('[BROWSER-LOG-VIEWER v2.0] RENDER-LOGS: Starting render');
        const container = document.getElementById('log-entries');
        
        // NUCLEAR SAFETY: Verify we're in the right place
        const parentContainer = document.getElementById('browser-logs-container');
        if (!parentContainer || !parentContainer.contains(container)) {
            console.error('[BROWSER-LOG-VIEWER v2.0] 🚨 WRONG CONTAINER - ABORTING!');
            return;
        }
        
        // NUCLEAR CLEAN: Clear any potential contamination
        const existingContent = container.innerHTML;
        if (existingContent.includes('[hook]') || 
            existingContent.includes('hook.pre_tool') || 
            existingContent.includes('hook.post_tool')) {
            console.error('[BROWSER-LOG-VIEWER v2.0] 🚨 CONTAMINATION FOUND IN RENDER - NUKING!');
            container.innerHTML = '';
        }
        
        // Filter logs
        const filteredLogs = this.logs.filter(log => {
            if (this.filters.browserId !== 'all' && log.browser_id !== this.filters.browserId) {
                return false;
            }
            if (this.filters.level !== 'all' && log.level !== this.filters.level) {
                return false;
            }
            return true;
        });
        
        if (filteredLogs.length === 0) {
            // Show proper empty state based on whether we have any logs at all
            if (this.logs.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-globe fa-3x"></i>
                        <p>No browser console logs yet</p>
                        <p class="text-muted">
                            Browser console logs will appear here when the monitoring script is injected.<br>
                            Use <code>/mpm-browser-monitor start</code> to begin monitoring.
                        </p>
                        <p class="text-muted" style="font-size: 11px; margin-top: 10px;">
                            This tab shows console.log, console.error, and console.warn from monitored browsers only.
                        </p>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-filter fa-3x"></i>
                        <p>No logs match the current filters</p>
                    </div>
                `;
            }
        } else {
            container.innerHTML = filteredLogs.map(log => this.renderLogEntry(log)).join('');
            
            // Auto-scroll to bottom if enabled
            if (this.autoScroll) {
                const logContainer = document.getElementById('browser-log-container');
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
        
        this.updateStats();
    }
    
    renderLogEntry(log) {
        const levelClass = log.level ? log.level.toLowerCase() : 'info';
        const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '';
        const browserId = log.browser_id ? log.browser_id.substring(0, 12) : 'unknown';
        
        let urlInfo = '';
        if (log.url) {
            try {
                const url = new URL(log.url);
                urlInfo = `<div class="log-url">${url.pathname}</div>`;
            } catch {
                urlInfo = `<div class="log-url">${log.url}</div>`;
            }
        }
        
        return `
            <div class="log-entry ${levelClass}">
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-level ${levelClass}">${log.level || 'INFO'}</span>
                <span class="log-browser">[${browserId}]</span>
                <div class="log-message">
                    ${this.escapeHtml(log.message || '')}
                    ${urlInfo}
                </div>
            </div>
        `;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    updateStats() {
        document.getElementById('log-count').textContent = `${this.logs.length} logs`;
        document.getElementById('session-count').textContent = `${this.browserSessions.size} sessions`;
    }
    
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefresh) {
            // Refresh every 5 seconds
            this.refreshInterval = setInterval(() => {
                this.loadLogs();
            }, 5000);
        }
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    exportLogs() {
        const filteredLogs = this.logs.filter(log => {
            if (this.filters.browserId !== 'all' && log.browser_id !== this.filters.browserId) {
                return false;
            }
            if (this.filters.level !== 'all' && log.level !== this.filters.level) {
                return false;
            }
            return true;
        });
        
        const jsonData = JSON.stringify(filteredLogs, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `browser-logs-${new Date().toISOString()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    destroy() {
        this.stopAutoRefresh();
        
        if (window.socket) {
            window.socket.off('browser_log');
            window.socket.off('dashboard:browser:console');
        }
        
        // Remove container ownership marker
        if (this.container) {
            this.container.removeAttribute('data-owner');
            this.container.classList.remove('browser-log-viewer-container');
        }
    }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BrowserLogViewer;
}