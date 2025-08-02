/**
 * Main Dashboard Application
 * Coordinates all components and handles tab management
 */

class Dashboard {
    constructor() {
        // Components
        this.socketClient = null;
        this.eventViewer = null;
        this.moduleViewer = null;
        this.sessionManager = null;
        
        // State
        this.currentTab = 'events';
        this.autoScroll = true;
        
        // File tracking for files tab
        this.fileOperations = new Map(); // Map of file paths to operations
        
        this.init();
    }

    /**
     * Initialize the dashboard
     */
    init() {
        // Initialize components
        this.initializeComponents();
        this.setupEventHandlers();
        this.setupTabNavigation();
        this.initializeFromURL();
        
        console.log('Claude MPM Dashboard initialized');
    }

    /**
     * Initialize all components
     */
    initializeComponents() {
        // Initialize socket client
        this.socketClient = new SocketClient();
        
        // Initialize UI components
        this.eventViewer = new EventViewer('events-list', this.socketClient);
        this.moduleViewer = new ModuleViewer('module-content');
        this.sessionManager = new SessionManager(this.socketClient);
        
        // Store globally for backward compatibility
        window.socketClient = this.socketClient;
        window.eventViewer = this.eventViewer;
        window.moduleViewer = this.moduleViewer;
        window.sessionManager = this.sessionManager;
        
        // Setup component interactions
        this.setupComponentInteractions();
    }

    /**
     * Setup interactions between components
     */
    setupComponentInteractions() {
        // Update footer when socket connection changes
        this.socketClient.onConnection('connect', (socketId) => {
            const socketIdEl = document.getElementById('socket-id');
            if (socketIdEl) {
                socketIdEl.textContent = `Socket: ${socketId.substring(0, 8)}...`;
            }
        });

        this.socketClient.onConnection('disconnect', () => {
            const socketIdEl = document.getElementById('socket-id');
            if (socketIdEl) {
                socketIdEl.textContent = 'Socket: Not connected';
            }
            const serverInfoEl = document.getElementById('server-info');
            if (serverInfoEl) {
                serverInfoEl.textContent = 'Server: Offline';
            }
        });

        // Listen for socket events to update file operations
        this.socketClient.onEventUpdate((events) => {
            this.updateFileOperations(events);
            this.renderCurrentTab();
        });

        // Listen for connection status changes
        document.addEventListener('socketConnectionStatus', (e) => {
            this.updateConnectionStatus(e.detail.status, e.detail.type);
        });
    }

    /**
     * Setup general event handlers
     */
    setupEventHandlers() {
        // Connection controls
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const portInput = document.getElementById('port-input');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                const port = portInput ? portInput.value : '8765';
                this.socketClient.connect(port);
            });
        }

        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                this.socketClient.disconnect();
            });
        }

        // Action buttons
        const clearBtn = document.querySelector('button[onclick="clearEvents()"]');
        const exportBtn = document.querySelector('button[onclick="exportEvents()"]');
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearEvents();
            });
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportEvents();
            });
        }

        // Clear selection button
        const clearSelectionBtn = document.querySelector('button[onclick="clearSelection()"]');
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', () => {
                this.clearSelection();
            });
        }
    }

    /**
     * Setup tab navigation
     */
    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = this.getTabNameFromButton(button);
                this.switchTab(tabName);
            });
        });
    }

    /**
     * Get tab name from button text
     */
    getTabNameFromButton(button) {
        const text = button.textContent.toLowerCase();
        if (text.includes('events')) return 'events';
        if (text.includes('agents')) return 'agents';
        if (text.includes('tools')) return 'tools';
        if (text.includes('files')) return 'files';
        return 'events';
    }

    /**
     * Initialize from URL parameters
     */
    initializeFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const defaultPort = urlParams.get('port') || '8765';
        const autoConnect = urlParams.get('autoconnect') === 'true';
        
        const portInput = document.getElementById('port-input');
        if (portInput) {
            portInput.value = defaultPort;
        }
        
        if (autoConnect) {
            this.socketClient.connect(defaultPort);
        }
    }

    /**
     * Switch to a different tab
     */
    switchTab(tabName) {
        this.currentTab = tabName;
        
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            if (this.getTabNameFromButton(btn) === tabName) {
                btn.classList.add('active');
            }
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTab = document.getElementById(`${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
        }
        
        // Render content for the active tab
        this.renderCurrentTab();
        
        console.log(`Switched to ${tabName} tab`);
    }

    /**
     * Render content for the current tab
     */
    renderCurrentTab() {
        switch (this.currentTab) {
            case 'events':
                // Events are automatically rendered by EventViewer
                break;
            case 'agents':
                this.renderAgents();
                break;
            case 'tools':
                this.renderTools();
                break;
            case 'files':
                this.renderFiles();
                break;
        }
    }

    /**
     * Render agents tab
     */
    renderAgents() {
        const agentsList = document.getElementById('agents-list');
        if (!agentsList) return;

        const events = this.getFilteredEventsForTab('agents');
        console.log('Agent tab - total events:', events.length);
        
        const agentEvents = events
            .filter(event => {
                // Check for agent-related events
                const type = event.type || '';
                const subtype = event.subtype || '';
                const fullType = subtype ? `${type}.${subtype}` : type;
                
                // Check various conditions for agent events:
                // 1. Direct agent type events
                const isDirectAgentEvent = type === 'agent' || type.includes('agent');
                
                // 2. Delegation events (Task tool usage)
                const isDelegationEvent = event.data && (
                    event.data.subagent_type ||
                    event.data.tool_name === 'Task' ||
                    fullType.includes('delegation')
                );
                
                // 3. Events with agent_type that's not 'unknown' or empty
                const hasAgentType = event.data && event.data.agent_type && 
                                   event.data.agent_type !== 'unknown' && 
                                   event.data.agent_type !== 'main';
                
                // 4. Session events (agent switching)
                const isSessionEvent = type === 'session';
                
                const isAgentEvent = isDirectAgentEvent || isDelegationEvent || hasAgentType || isSessionEvent;
                
                if (isAgentEvent) {
                    console.log('Agent filter - found agent event:', {
                        type, subtype, fullType, 
                        isDirectAgentEvent, isDelegationEvent, hasAgentType, isSessionEvent,
                        agent_type: event.data?.agent_type,
                        subagent_type: event.data?.subagent_type,
                        tool_name: event.data?.tool_name
                    });
                }
                
                return isAgentEvent;
            })
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        console.log('Agent tab - filtered events:', agentEvents.length);

        if (agentEvents.length === 0) {
            agentsList.innerHTML = '<div class="no-events">No agent events found...</div>';
            return;
        }

        const agentsHtml = agentEvents.map((event, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            
            // Extract agent information in priority order
            let agentType = 'Unknown';
            let operation = 'operation';
            
            if (event.data?.subagent_type) {
                agentType = event.data.subagent_type;
                operation = 'delegation';
            } else if (event.data?.agent_type && event.data.agent_type !== 'unknown') {
                agentType = event.data.agent_type;
            } else if (event.data?.agent) {
                agentType = event.data.agent;
            } else if (event.data?.name) {
                agentType = event.data.name;
            }
            
            // Extract operation from event type/subtype
            if (event.subtype) {
                operation = event.subtype.replace(/_/g, ' ');
            } else {
                operation = this.extractOperation(event.type) || 'operation';
            }
            
            return `
                <div class="event-item event-agent" onclick="eventViewer.showEventDetails(${this.eventViewer.events.indexOf(event)})">
                    <div class="event-header">
                        <span class="event-type">🤖 ${agentType}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Operation:</strong> ${operation}
                        ${event.data?.session_id ? `<br><strong>Session:</strong> ${event.data.session_id.substring(0, 8)}...` : ''}
                        ${event.data?.subagent_type ? `<br><strong>Delegation:</strong> ${event.data.subagent_type}` : ''}
                    </div>
                </div>
            `;
        }).join('');

        agentsList.innerHTML = agentsHtml;
    }

    /**
     * Render tools tab
     */
    renderTools() {
        const toolsList = document.getElementById('tools-list');
        if (!toolsList) return;

        const events = this.getFilteredEventsForTab('tools');
        console.log('Tools tab - total events:', events.length);
        
        const toolEvents = events
            .filter(event => {
                // Check for tool-related events
                const type = event.type || '';
                const subtype = event.subtype || '';
                
                // Check various conditions for tool events:
                // 1. Hook events with tool subtypes
                const isHookToolEvent = type === 'hook' && (
                    subtype.includes('tool') || 
                    subtype.includes('pre_') || 
                    subtype.includes('post_')
                );
                
                // 2. Events with tool_name in data
                const hasToolName = event.data && event.data.tool_name;
                
                // 3. Events with tools array (multiple tools)
                const hasToolsArray = event.data && event.data.tools && Array.isArray(event.data.tools);
                
                // 4. Legacy hook events with tool patterns (backward compatibility)
                const isLegacyHookEvent = type.startsWith('hook.') && (
                    type.includes('tool') || 
                    type.includes('pre') || 
                    type.includes('post')
                );
                
                const isToolEvent = isHookToolEvent || hasToolName || hasToolsArray || isLegacyHookEvent;
                
                if (isToolEvent) {
                    console.log('Tool filter - found tool event:', {
                        type, subtype,
                        isHookToolEvent, hasToolName, hasToolsArray, isLegacyHookEvent,
                        tool_name: event.data?.tool_name,
                        tools: event.data?.tools
                    });
                }
                
                return isToolEvent;
            })
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        console.log('Tools tab - filtered events:', toolEvents.length);

        if (toolEvents.length === 0) {
            toolsList.innerHTML = '<div class="no-events">No tool events found...</div>';
            return;
        }

        const toolsHtml = toolEvents.map((event, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            
            // Extract tool name with priority order
            let toolName = 'Unknown Tool';
            if (event.data?.tool_name) {
                toolName = event.data.tool_name;
            } else if (event.data?.tools && Array.isArray(event.data.tools) && event.data.tools.length > 0) {
                toolName = event.data.tools[0]; // Use first tool if multiple
            } else {
                toolName = this.extractToolFromHook(event.type) || this.extractToolFromSubtype(event.subtype) || 'Unknown Tool';
            }
            
            const agentType = event.data?.agent_type || 'main';
            
            // Extract tool target/parameters
            const target = this.extractToolTarget(toolName, event.data?.parameters || event.data?.tool_parameters, event.data?.tool_parameters);
            
            // Determine operation type
            let operation = 'execution';
            if (event.subtype) {
                if (event.subtype.includes('pre_')) {
                    operation = 'pre-execution';
                } else if (event.subtype.includes('post_')) {
                    operation = 'post-execution';
                } else {
                    operation = event.subtype.replace(/_/g, ' ');
                }
            }
            
            return `
                <div class="event-item event-tool" onclick="eventViewer.showEventDetails(${this.eventViewer.events.indexOf(event)})">
                    <div class="event-header">
                        <span class="event-type">🔧 ${toolName}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Agent:</strong> ${agentType}<br>
                        <strong>Operation:</strong> ${operation}<br>
                        <strong>Target:</strong> ${target}
                        ${event.data?.session_id ? `<br><strong>Session:</strong> ${event.data.session_id.substring(0, 8)}...` : ''}
                    </div>
                </div>
            `;
        }).join('');

        toolsList.innerHTML = toolsHtml;
    }

    /**
     * Render files tab with file-centric view
     */
    renderFiles() {
        const filesList = document.getElementById('files-list');
        if (!filesList) return;

        console.log('Files tab - file operations:', this.fileOperations.size);
        console.log('Files tab - operations map:', this.fileOperations);

        if (this.fileOperations.size === 0) {
            filesList.innerHTML = '<div class="no-events">No file operations found...</div>';
            return;
        }

        // Convert to array and sort by oldest operation first (like original)
        const filesArray = Array.from(this.fileOperations.entries())
            .sort((a, b) => new Date(a[1].lastOperation) - new Date(b[1].lastOperation));

        const filesHtml = filesArray.map(([filePath, fileData]) => {
            const icon = this.getFileOperationIcon(fileData.operations);
            const lastOp = fileData.operations[fileData.operations.length - 1];
            const timestamp = new Date(lastOp.timestamp).toLocaleTimeString();
            
            return `
                <div class="event-item file-item" onclick="dashboard.showFileDetails('${filePath}')">
                    <div class="event-header">
                        <span class="event-type">${icon} ${lastOp.operation}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>File:</strong> ${this.getRelativeFilePath(filePath)}<br>
                        <strong>Operations:</strong> ${fileData.operations.length}<br>
                        <strong>Agent:</strong> ${lastOp.agent}
                    </div>
                </div>
            `;
        }).join('');

        filesList.innerHTML = filesHtml;
    }

    /**
     * Show detailed file operations in module viewer
     */
    showFileDetails(filePath) {
        const fileData = this.fileOperations.get(filePath);
        if (!fileData) return;

        const content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>📁 File Operations</h4>
                </div>
                <div class="file-details">
                    <div class="file-path-display">
                        <strong>File:</strong> ${filePath}
                    </div>
                    <div class="operations-list">
                        ${fileData.operations.map(op => `
                            <div class="operation-item">
                                <div class="operation-header">
                                    <span class="operation-icon">${this.getOperationIcon(op.operation)}</span>
                                    <span class="operation-type">${op.operation}</span>
                                    <span class="operation-timestamp">${new Date(op.timestamp).toLocaleString()}</span>
                                </div>
                                <div class="operation-details">
                                    <strong>Agent:</strong> ${op.agent}<br>
                                    <strong>Session:</strong> ${op.sessionId ? op.sessionId.substring(0, 8) + '...' : 'Unknown'}
                                    ${op.details ? `<br><strong>Details:</strong> ${op.details}` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        this.moduleViewer.container.innerHTML = content;
    }

    /**
     * Update file operations from events
     */
    updateFileOperations(events) {
        // Clear existing data
        this.fileOperations.clear();

        console.log('updateFileOperations - processing', events.length, 'events');

        // Process file-related events
        events.forEach((event, index) => {
            const isFileOp = this.isFileOperation(event);
            if (index < 5) { // Debug first 5 events
                console.log(`Event ${index}:`, event.type, 'isFileOp:', isFileOp, 'data:', event.data);
            }
            
            if (isFileOp) {
                const filePath = this.extractFilePath(event);
                console.log('File operation detected:', event.type, 'filePath:', filePath);
                
                if (filePath) {
                    if (!this.fileOperations.has(filePath)) {
                        this.fileOperations.set(filePath, {
                            path: filePath,
                            operations: [],
                            lastOperation: event.timestamp
                        });
                    }

                    const fileData = this.fileOperations.get(filePath);
                    fileData.operations.push({
                        operation: this.getFileOperation(event),
                        timestamp: event.timestamp,
                        agent: event.data?.agent_type || 'main',
                        sessionId: event.data?.session_id,
                        details: this.getFileOperationDetails(event)
                    });
                    fileData.lastOperation = event.timestamp;
                }
            }
        });
        
        console.log('updateFileOperations - found', this.fileOperations.size, 'file operations');
    }

    /**
     * Check if event is a file operation
     */
    isFileOperation(event) {
        const toolName = event.data?.tool_name;
        const fileTools = ['Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'LS', 'NotebookRead', 'NotebookEdit'];
        
        // Check for direct tool name match
        if (fileTools.includes(toolName)) {
            return true;
        }
        
        // Check for hook events that involve file tools (updated for new structure)
        const type = event.type || '';
        const subtype = event.subtype || '';
        
        // Check both legacy format and new format
        const isHookEvent = (type === 'hook' || type.startsWith('hook.')) && event.data;
        
        if (isHookEvent) {
            // Check if tool_name indicates file operation
            if (fileTools.includes(event.data.tool_name)) {
                return true;
            }
            
            // Check if parameters suggest file operation
            const params = event.data.parameters || event.data.tool_parameters || {};
            const hasFileParams = !!(params.file_path || params.path || params.notebook_path || params.pattern);
            
            // Also check top-level data for file parameters (some events structure differently)
            const hasDirectFileParams = !!(event.data.file_path || event.data.path || event.data.notebook_path || event.data.pattern);
            
            return hasFileParams || hasDirectFileParams;
        }
        
        return false;
    }

    /**
     * Extract file path from event
     */
    extractFilePath(event) {
        if (!event.data) return null;
        
        // Check parameters first
        const params = event.data.parameters || event.data.tool_parameters;
        if (params) {
            if (params.file_path) return params.file_path;
            if (params.path) return params.path;
            if (params.notebook_path) return params.notebook_path;
        }
        
        // Check top-level data (some events structure file paths differently)
        if (event.data.file_path) return event.data.file_path;
        if (event.data.path) return event.data.path;
        if (event.data.notebook_path) return event.data.notebook_path;
        
        return null;
    }

    /**
     * Get file operation type
     */
    getFileOperation(event) {
        const toolName = event.data?.tool_name;
        const operationMap = {
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'MultiEdit': 'edit',
            'Glob': 'search',
            'LS': 'list',
            'NotebookRead': 'read',
            'NotebookEdit': 'edit'
        };
        
        return operationMap[toolName] || 'operation';
    }

    /**
     * Get file operation details
     */
    getFileOperationDetails(event) {
        const toolName = event.data?.tool_name;
        const params = event.data?.parameters || event.data?.tool_parameters;
        
        switch (toolName) {
            case 'Edit':
            case 'MultiEdit':
                return `Modified content`;
            case 'Write':
                return `Created/updated file`;
            case 'Read':
                return `Read file content`;
            case 'NotebookRead':
                return `Read notebook content`;
            case 'NotebookEdit':
                return `Modified notebook`;
            case 'Glob':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'LS':
                return `Listed directory`;
            default:
                return '';
        }
    }

    /**
     * Get icon for file operations
     */
    getFileOperationIcon(operations) {
        // Check for notebook operations first
        const hasNotebook = operations.some(op => op.details && (op.details.includes('notebook') || op.details.includes('Notebook')));
        if (hasNotebook) return '📓';
        
        const hasWrite = operations.some(op => ['write', 'edit'].includes(op.operation));
        const hasRead = operations.some(op => op.operation === 'read');
        
        if (hasWrite && hasRead) return '📝';
        if (hasWrite) return '✏️';
        if (hasRead) return '📖';
        return '📄';
    }

    /**
     * Get icon for specific operation
     */
    getOperationIcon(operation) {
        const icons = {
            read: '📖',
            write: '📝',
            edit: '✏️',
            search: '🔍',
            list: '📋'
        };
        return icons[operation] || '📄';
    }

    /**
     * Get relative file path for display
     */
    getRelativeFilePath(filePath) {
        // Try to make path relative to common base paths
        const commonPaths = [
            '/Users/masa/Projects/claude-mpm/',
            process.cwd?.() || '',
            '.'
        ];
        
        for (const basePath of commonPaths) {
            if (filePath.startsWith(basePath)) {
                return filePath.substring(basePath.length).replace(/^\//, '');
            }
        }
        
        // If no common path found, show last 2-3 path segments
        const parts = filePath.split('/');
        if (parts.length > 3) {
            return '.../' + parts.slice(-2).join('/');
        }
        
        return filePath;
    }

    /**
     * Extract operation from event type
     */
    extractOperation(eventType) {
        if (!eventType) return 'unknown';
        
        if (eventType.includes('pre_')) return 'pre-' + eventType.split('pre_')[1];
        if (eventType.includes('post_')) return 'post-' + eventType.split('post_')[1];
        if (eventType.includes('delegation')) return 'delegation';
        if (eventType.includes('start')) return 'started';
        if (eventType.includes('end')) return 'ended';
        
        // Extract operation from type like "hook.pre_tool" -> "pre_tool"
        const parts = eventType.split('.');
        return parts.length > 1 ? parts[1] : eventType;
    }

    /**
     * Extract tool name from hook event type
     */
    extractToolFromHook(eventType) {
        if (!eventType || !eventType.startsWith('hook.')) return null;
        
        // For hook events, the tool name might be in the data
        return 'Tool'; // Fallback - actual tool name should be in event.data.tool_name
    }

    /**
     * Extract tool name from subtype
     */
    extractToolFromSubtype(subtype) {
        if (!subtype) return null;
        
        // Try to extract tool name from subtype patterns like 'pre_tool' or 'post_tool'
        if (subtype.includes('tool')) {
            return 'Tool'; // Generic fallback
        }
        
        return null;
    }

    /**
     * Extract tool target for display
     */
    extractToolTarget(toolName, params, toolParameters) {
        const allParams = { ...params, ...toolParameters };
        
        switch (toolName) {
            case 'Read':
            case 'Write':
            case 'Edit':
            case 'MultiEdit':
                return allParams.file_path || 'Unknown file';
            case 'Bash':
                return allParams.command || 'Unknown command';
            case 'Glob':
                return allParams.pattern || 'Unknown pattern';
            case 'Grep':
                return `"${allParams.pattern || 'unknown'}" in ${allParams.path || 'unknown path'}`;
            case 'LS':
                return allParams.path || 'Unknown path';
            default:
                if (Object.keys(allParams).length > 0) {
                    return JSON.stringify(allParams).substring(0, 50) + '...';
                }
                return 'No parameters';
        }
    }

    /**
     * Get filtered events for a specific tab
     */
    getFilteredEventsForTab(tabName) {
        // Use the event viewer's current filtered events
        const events = this.eventViewer.filteredEvents;
        console.log(`getFilteredEventsForTab(${tabName}) - returning ${events.length} events`);
        if (events.length > 0) {
            console.log('Sample event:', events[0]);
        }
        return events;
    }

    /**
     * Update connection status in UI
     */
    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status-badge status-${type}`;
            
            // Update status indicator
            const indicator = statusElement.querySelector('span');
            if (indicator) {
                indicator.textContent = type === 'connected' ? '●' : '●';
            }
        }
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.eventViewer.clearEvents();
        this.fileOperations.clear();
        this.renderCurrentTab();
    }

    /**
     * Export current events
     */
    exportEvents() {
        this.eventViewer.exportEvents();
    }

    /**
     * Clear current selection
     */
    clearSelection() {
        this.eventViewer.clearSelection();
        this.moduleViewer.clear();
    }
}

// Global functions for backward compatibility
window.connectSocket = function() {
    if (window.dashboard) {
        const port = document.getElementById('port-input')?.value || '8765';
        window.dashboard.socketClient.connect(port);
    }
};

window.disconnectSocket = function() {
    if (window.dashboard) {
        window.dashboard.socketClient.disconnect();
    }
};

window.clearEvents = function() {
    if (window.dashboard) {
        window.dashboard.clearEvents();
    }
};

window.exportEvents = function() {
    if (window.dashboard) {
        window.dashboard.exportEvents();
    }
};

window.clearSelection = function() {
    if (window.dashboard) {
        window.dashboard.clearSelection();
    }
};

window.switchTab = function(tabName) {
    if (window.dashboard) {
        window.dashboard.switchTab(tabName);
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
    console.log('Dashboard ready');
});

// Export for use in other modules
window.Dashboard = Dashboard;