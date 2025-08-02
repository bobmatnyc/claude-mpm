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

        // Tab-specific filters
        this.setupTabFilters();
    }

    /**
     * Setup filtering for each tab
     */
    setupTabFilters() {
        // Agents tab filters
        const agentsSearchInput = document.getElementById('agents-search-input');
        const agentsTypeFilter = document.getElementById('agents-type-filter');
        
        if (agentsSearchInput) {
            agentsSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'agents') this.renderCurrentTab();
            });
        }
        
        if (agentsTypeFilter) {
            agentsTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'agents') this.renderCurrentTab();
            });
        }

        // Tools tab filters
        const toolsSearchInput = document.getElementById('tools-search-input');
        const toolsTypeFilter = document.getElementById('tools-type-filter');
        
        if (toolsSearchInput) {
            toolsSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'tools') this.renderCurrentTab();
            });
        }
        
        if (toolsTypeFilter) {
            toolsTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'tools') this.renderCurrentTab();
            });
        }

        // Files tab filters
        const filesSearchInput = document.getElementById('files-search-input');
        const filesTypeFilter = document.getElementById('files-type-filter');
        
        if (filesSearchInput) {
            filesSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'files') this.renderCurrentTab();
            });
        }
        
        if (filesTypeFilter) {
            filesTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'files') this.renderCurrentTab();
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
        
        // Enhanced debugging: log first few events to understand structure
        if (events.length > 0) {
            console.log('Agent tab - sample events for analysis:');
            events.slice(0, 3).forEach((event, i) => {
                console.log(`  Event ${i}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    agent_type: event.agent_type,
                    subagent_type: event.subagent_type,
                    tool_parameters: event.tool_parameters
                });
            });
            
            // Count events by type and tool_name for debugging
            const eventCounts = {};
            const toolCounts = {};
            events.forEach(event => {
                const key = `${event.type}.${event.subtype || 'none'}`;
                eventCounts[key] = (eventCounts[key] || 0) + 1;
                
                if (event.tool_name) {
                    toolCounts[event.tool_name] = (toolCounts[event.tool_name] || 0) + 1;
                }
            });
            console.log('Agent tab - event type breakdown:', eventCounts);
            console.log('Agent tab - tool breakdown:', toolCounts);
        }
        
        let agentEvents = events
            .filter(event => {
                // Check for agent-related events
                const type = event.type || '';
                const subtype = event.subtype || '';
                const fullType = subtype ? `${type}.${subtype}` : type;
                
                // Check various conditions for agent events:
                // 1. Direct agent type events
                const isDirectAgentEvent = type === 'agent' || type.includes('agent');
                
                // 2. Pre-tool events with Task tool (contains subagent_type parameter)
                const isTaskDelegation = event.tool_name === 'Task' && 
                                        (subtype === 'pre_tool' || type === 'hook') &&
                                        event.tool_parameters?.subagent_type;
                
                // 3. Other delegation events
                const isDelegationEvent = event.subagent_type ||
                                         fullType.includes('delegation');
                
                // 4. Events with agent_type that's not 'unknown' or empty (include 'main' for now)
                const hasAgentType = event.agent_type && 
                                   event.agent_type !== 'unknown';
                
                // 5. Session events (agent switching)
                const isSessionEvent = type === 'session';
                
                const isAgentEvent = isDirectAgentEvent || isTaskDelegation || isDelegationEvent || hasAgentType || isSessionEvent;
                
                // Debug first few events
                const eventIndex = events.indexOf(event);
                if (eventIndex < 2 && isAgentEvent) {
                    console.log(`Agent filter [${eventIndex}] - MATCHED:`, {
                        type, subtype, tool_name: event.tool_name,
                        agent_type: event.agent_type,
                        subagent_type: event.subagent_type
                    });
                }
                
                // Removed redundant logging - we have summary stats below
                
                return isAgentEvent;
            })
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        // Apply tab-specific filters
        agentEvents = this.applyAgentsFilters(agentEvents);

        console.log('Agent tab - filtering summary:', {
            total_events: events.length,
            agent_events_found: agentEvents.length,
            percentage: agentEvents.length > 0 ? ((agentEvents.length / events.length) * 100).toFixed(1) + '%' : '0%'
        });

        if (agentEvents.length === 0) {
            agentsList.innerHTML = '<div class="no-events">No agent events found...</div>';
            return;
        }

        const agentsHtml = agentEvents.map((event, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            
            // Extract agent information with priority for Task tool subagent_type
            let agentName = 'Unknown';
            let operation = 'operation';
            let prompt = '';
            let description = '';
            let taskPreview = '';
            
            // Priority 1: Task tool with subagent_type parameter
            if (event.tool_name === 'Task' && event.tool_parameters?.subagent_type) {
                agentName = event.tool_parameters.subagent_type;
                operation = 'delegation';
                
                // Extract additional Task tool information
                if (event.tool_parameters.prompt) {
                    prompt = event.tool_parameters.prompt;
                    taskPreview = prompt.length > 200 ? prompt.substring(0, 200) + '...' : prompt;
                }
                if (event.tool_parameters.description) {
                    description = event.tool_parameters.description;
                }
            }
            // Priority 2: Direct subagent_type in event
            else if (event.subagent_type) {
                agentName = event.subagent_type;
                operation = 'delegation';
            } 
            // Priority 3: Other agent types
            else if (event.agent_type && event.agent_type !== 'unknown') {
                agentName = event.agent_type;
            } else if (event.agent) {
                agentName = event.agent;
            } else if (event.name) {
                agentName = event.name;
            }
            
            // Extract operation from event type/subtype
            if (event.subtype) {
                operation = event.subtype.replace(/_/g, ' ');
            } else {
                operation = this.extractOperation(event.type) || 'operation';
            }
            
            return `
                <div class="event-item event-agent" onclick="dashboard.showAgentDetails(${index}, ${this.eventViewer.events.indexOf(event)})">
                    <div class="event-header">
                        <span class="event-type">🤖 ${agentName}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Operation:</strong> ${operation}
                        ${taskPreview ? `<br><strong>Task Preview:</strong> ${taskPreview}` : ''}
                        ${description ? `<br><strong>Description:</strong> ${description}` : ''}
                        ${event.session_id ? `<br><strong>Session:</strong> ${event.session_id.substring(0, 8)}...` : ''}
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
        
        // Enhanced debugging: log first few events to understand structure
        if (events.length > 0) {
            console.log('Tools tab - sample events for analysis:');
            events.slice(0, 3).forEach((event, i) => {
                console.log(`  Event ${i}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tools: event.tools,
                    tool_parameters: event.tool_parameters
                });
            });
            
            // Count events by type and tool_name for debugging
            const eventCounts = {};
            const toolCounts = {};
            events.forEach(event => {
                const key = `${event.type}.${event.subtype || 'none'}`;
                eventCounts[key] = (eventCounts[key] || 0) + 1;
                
                if (event.tool_name) {
                    toolCounts[event.tool_name] = (toolCounts[event.tool_name] || 0) + 1;
                }
            });
            console.log('Tools tab - event type breakdown:', eventCounts);
            console.log('Tools tab - tool breakdown:', toolCounts);
        }
        
        let toolEvents = events
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
                
                // 2. Events with tool_name in event
                const hasToolName = event.tool_name;
                
                // 3. Events with tools array (multiple tools)
                const hasToolsArray = event.tools && Array.isArray(event.tools);
                
                // 4. Legacy hook events with tool patterns (backward compatibility)
                const isLegacyHookEvent = type.startsWith('hook.') && (
                    type.includes('tool') || 
                    type.includes('pre') || 
                    type.includes('post')
                );
                
                const isToolEvent = isHookToolEvent || hasToolName || hasToolsArray || isLegacyHookEvent;
                
                // Debug first few events
                const eventIndex = events.indexOf(event);
                if (eventIndex < 2 && isToolEvent) {
                    console.log(`Tool filter [${eventIndex}] - MATCHED:`, {
                        type, subtype, tool_name: event.tool_name,
                        tools: event.tools
                    });
                }
                
                // Removed redundant logging - we have summary stats below
                
                return isToolEvent;
            })
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        // Apply tab-specific filters
        toolEvents = this.applyToolsFilters(toolEvents);

        console.log('Tools tab - filtering summary:', {
            total_events: events.length,
            tool_events_found: toolEvents.length,
            percentage: toolEvents.length > 0 ? ((toolEvents.length / events.length) * 100).toFixed(1) + '%' : '0%'
        });

        if (toolEvents.length === 0) {
            toolsList.innerHTML = '<div class="no-events">No tool events found...</div>';
            return;
        }

        const toolsHtml = toolEvents.map((event, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            
            // Extract tool name with priority order
            let toolName = 'Unknown Tool';
            if (event.tool_name) {
                toolName = event.tool_name;
            } else if (event.tools && Array.isArray(event.tools) && event.tools.length > 0) {
                toolName = event.tools[0]; // Use first tool if multiple
            } else {
                toolName = this.extractToolFromHook(event.type) || this.extractToolFromSubtype(event.subtype) || 'Unknown Tool';
            }
            
            // Determine agent name - check for subagent context first
            let agentName = 'PM'; // Default to PM instead of 'main'
            
            // Priority 1: Check if this is part of a Task tool execution (subagent context)
            if (event.subagent_type) {
                agentName = event.subagent_type;
            }
            // Priority 2: Check for agent_type that's not 'main' or 'unknown'
            else if (event.agent_type && event.agent_type !== 'main' && event.agent_type !== 'unknown') {
                agentName = event.agent_type;
            }
            // Priority 3: Check in parameters for subagent_type (for Task tool events)
            else if (event.tool_parameters?.subagent_type) {
                agentName = event.tool_parameters.subagent_type;
            }
            // Priority 4: Look for context clues in the event structure
            else if (event.context_agent || event.triggering_agent) {
                agentName = event.context_agent || event.triggering_agent;
            }
            
            // Extract tool target/parameters
            const target = this.extractToolTarget(toolName, event.tool_parameters, event.tool_parameters);
            
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
                        <strong>Agent:</strong> ${agentName}<br>
                        <strong>Operation:</strong> ${operation}<br>
                        <strong>Target:</strong> ${target}
                        ${event.session_id ? `<br><strong>Session:</strong> ${event.session_id.substring(0, 8)}...` : ''}
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

        // Convert to array and sort by most recent operations at bottom (chronological order)
        let filesArray = Array.from(this.fileOperations.entries())
            .filter(([filePath, fileData]) => {
                // Ensure we have valid data
                return fileData.operations && fileData.operations.length > 0;
            })
            .sort((a, b) => {
                const timeA = a[1].lastOperation ? new Date(a[1].lastOperation) : new Date(0);
                const timeB = b[1].lastOperation ? new Date(b[1].lastOperation) : new Date(0);
                return timeA - timeB;
            });

        console.log('Files tab - after filtering:', filesArray.length, 'files');

        // Apply tab-specific filters
        filesArray = this.applyFilesFilters(filesArray);

        console.log('Files tab - after search/type filters:', filesArray.length, 'files');

        if (filesArray.length === 0) {
            filesList.innerHTML = '<div class="no-events">No files match current filters...</div>';
            return;
        }

        const filesHtml = filesArray.map(([filePath, fileData]) => {
            if (!fileData.operations || fileData.operations.length === 0) {
                console.warn('File with no operations:', filePath);
                return '';
            }
            
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
     * Show agent details in module viewer
     */
    showAgentDetails(agentIndex, eventIndex) {
        // Get the agent event
        const events = this.getFilteredEventsForTab('agents');
        const agentEvents = this.applyAgentsFilters(events.filter(event => {
            const type = event.type || '';
            const subtype = event.subtype || '';
            
            const isDirectAgentEvent = type === 'agent' || type.includes('agent');
            const isTaskDelegation = event.tool_name === 'Task' && 
                                    (subtype === 'pre_tool' || type === 'hook') &&
                                    event.tool_parameters?.subagent_type;
            const isDelegationEvent = event.subagent_type ||
                                     (type + '.' + subtype).includes('delegation');
            const hasAgentType = event.agent_type && 
                               event.agent_type !== 'unknown' && 
                               event.agent_type !== 'main';
            const isSessionEvent = type === 'session';
            
            return isDirectAgentEvent || isTaskDelegation || isDelegationEvent || hasAgentType || isSessionEvent;
        }));

        const event = agentEvents[agentIndex];
        if (!event) return;

        // Extract agent information
        let agentName = 'Unknown Agent';
        let prompt = '';
        let description = '';
        let fullPrompt = '';
        
        if (event.tool_name === 'Task' && event.tool_parameters?.subagent_type) {
            agentName = event.tool_parameters.subagent_type;
            prompt = event.tool_parameters.prompt || '';
            description = event.tool_parameters.description || '';
            fullPrompt = prompt;
        } else if (event.subagent_type) {
            agentName = event.subagent_type;
        } else if (event.agent_type && event.agent_type !== 'unknown') {
            agentName = event.agent_type;
        }

        const content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🤖 Agent Details</h4>
                </div>
                <div class="agent-details">
                    <div class="agent-info">
                        <div class="structured-field">
                            <strong>Agent Name:</strong> ${agentName}
                        </div>
                        ${description ? `
                            <div class="structured-field">
                                <strong>Description:</strong> ${description}
                            </div>
                        ` : ''}
                        <div class="structured-field">
                            <strong>Timestamp:</strong> ${new Date(event.timestamp).toLocaleString()}
                        </div>
                        <div class="structured-field">
                            <strong>Event Type:</strong> ${event.type}.${event.subtype || 'default'}
                        </div>
                        ${event.session_id ? `
                            <div class="structured-field">
                                <strong>Session ID:</strong> ${event.session_id}
                            </div>
                        ` : ''}
                    </div>
                    
                    ${fullPrompt ? `
                        <div class="prompt-section">
                            <div class="structured-view-header">
                                <h4>📝 Task Prompt</h4>
                            </div>
                            <div class="structured-data">
                                <div class="task-prompt" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.4;">
                                    ${fullPrompt}
                                </div>
                                <div style="margin-top: 10px; text-align: center;">
                                    <button onclick="dashboard.togglePromptExpansion(this)" style="font-size: 11px; padding: 4px 8px;">
                                        ${fullPrompt.length > 200 ? 'Show More' : 'Show Less'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        this.moduleViewer.container.innerHTML = content;
        
        // Also show the event details in EventViewer
        if (eventIndex >= 0) {
            this.eventViewer.showEventDetails(eventIndex);
        }
    }

    /**
     * Toggle prompt expansion
     */
    togglePromptExpansion(button) {
        const promptDiv = button.parentElement.previousElementSibling;
        const isExpanded = promptDiv.style.maxHeight !== '300px';
        
        if (isExpanded) {
            promptDiv.style.maxHeight = '300px';
            button.textContent = 'Show More';
        } else {
            promptDiv.style.maxHeight = 'none';
            button.textContent = 'Show Less';
        }
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

        // Group events by session and timestamp to match pre/post pairs
        const eventPairs = new Map(); // Key: session_id + timestamp + tool_name
        let fileOperationCount = 0;
        
        // First pass: collect all tool events and group them
        events.forEach((event, index) => {
            const isFileOp = this.isFileOperation(event);
            if (isFileOp) fileOperationCount++;
            
            if (index < 5) { // Debug first 5 events with more detail
                console.log(`Event ${index}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tool_parameters: event.tool_parameters,
                    isFileOp: isFileOp
                });
            }
            
            if (isFileOp) {
                const toolName = event.tool_name;
                const sessionId = event.session_id || 'unknown';
                const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`; // Group by second
                
                if (!eventPairs.has(eventKey)) {
                    eventPairs.set(eventKey, {
                        pre_event: null,
                        post_event: null,
                        tool_name: toolName,
                        session_id: sessionId
                    });
                }
                
                const pair = eventPairs.get(eventKey);
                if (event.subtype === 'pre_tool' || event.type === 'hook' && !event.subtype.includes('post')) {
                    pair.pre_event = event;
                } else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
                    pair.post_event = event;
                } else {
                    // For events without clear pre/post distinction, treat as both
                    pair.pre_event = event;
                    pair.post_event = event;
                }
            }
        });
        
        console.log('updateFileOperations - found', fileOperationCount, 'file operations in', eventPairs.size, 'event pairs');
        
        // Second pass: extract file paths and operations from paired events
        eventPairs.forEach((pair, key) => {
            const filePath = this.extractFilePathFromPair(pair);
            
            if (filePath) {
                console.log('File operation detected for:', filePath, 'from pair:', key);
                
                if (!this.fileOperations.has(filePath)) {
                    this.fileOperations.set(filePath, {
                        path: filePath,
                        operations: [],
                        lastOperation: null
                    });
                }

                const fileData = this.fileOperations.get(filePath);
                const operation = this.getFileOperationFromPair(pair);
                const timestamp = pair.post_event?.timestamp || pair.pre_event?.timestamp;
                
                fileData.operations.push({
                    operation: operation,
                    timestamp: timestamp,
                    agent: this.extractAgentFromPair(pair),
                    sessionId: pair.session_id,
                    details: this.getFileOperationDetailsFromPair(pair)
                });
                fileData.lastOperation = timestamp;
            } else {
                console.log('No file path found for pair:', key, pair);
            }
        });
        
        console.log('updateFileOperations - final result:', this.fileOperations.size, 'file operations');
        if (this.fileOperations.size > 0) {
            console.log('File operations map:', Array.from(this.fileOperations.entries()));
        }
    }

    /**
     * Check if event is a file operation
     */
    isFileOperation(event) {
        const toolName = event.tool_name;
        const fileTools = ['Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'LS', 'NotebookRead', 'NotebookEdit', 'Grep'];
        
        // Check for direct tool name match
        if (fileTools.includes(toolName)) {
            console.log('isFileOperation - direct tool match:', toolName);
            return true;
        }
        
        // Check for hook events that involve file tools (updated for new structure)
        const type = event.type || '';
        const subtype = event.subtype || '';
        
        // Check both legacy format and new format
        const isHookEvent = type === 'hook' || type.startsWith('hook.');
        
        if (isHookEvent) {
            // Check if tool_name indicates file operation
            if (fileTools.includes(event.tool_name)) {
                console.log('isFileOperation - hook tool match:', event.tool_name);
                return true;
            }
            
            // Check if parameters suggest file operation
            const params = event.tool_parameters || {};
            const hasFileParams = !!(params.file_path || params.path || params.notebook_path || params.pattern);
            
            // Also check top-level event for file parameters (flat structure)
            const hasDirectFileParams = !!(event.file_path || event.path || event.notebook_path || event.pattern);
            
            const hasAnyFileParams = hasFileParams || hasDirectFileParams;
            if (hasAnyFileParams) {
                console.log('isFileOperation - file params match:', { hasFileParams, hasDirectFileParams, params, directParams: { file_path: event.file_path, path: event.path } });
            }
            
            return hasAnyFileParams;
        }
        
        return false;
    }

    /**
     * Extract file path from event
     */
    extractFilePath(event) {
        // Check tool_parameters first
        const params = event.tool_parameters;
        if (params) {
            if (params.file_path) return params.file_path;
            if (params.path) return params.path;
            if (params.notebook_path) return params.notebook_path;
        }
        
        // Check top-level event (flat structure)
        if (event.file_path) return event.file_path;
        if (event.path) return event.path;
        if (event.notebook_path) return event.notebook_path;
        
        // Check tool_input if available (sometimes path is here)
        if (event.tool_input) {
            if (event.tool_input.file_path) return event.tool_input.file_path;
            if (event.tool_input.path) return event.tool_input.path;
            if (event.tool_input.notebook_path) return event.tool_input.notebook_path;
        }
        
        // Check result/output if available (sometimes path is in result)
        if (event.result) {
            if (event.result.file_path) return event.result.file_path;
            if (event.result.path) return event.result.path;
        }
        
        return null;
    }
    
    /**
     * Extract file path from paired pre/post events
     */
    extractFilePathFromPair(pair) {
        // Try pre_event first, then post_event
        const preEvent = pair.pre_event;
        const postEvent = pair.post_event;
        
        if (preEvent) {
            const prePath = this.extractFilePath(preEvent);
            if (prePath) return prePath;
        }
        
        if (postEvent) {
            const postPath = this.extractFilePath(postEvent);
            if (postPath) return postPath;
        }
        
        return null;
    }

    /**
     * Get file operation type
     */
    getFileOperation(event) {
        const toolName = event.tool_name;
        const operationMap = {
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'MultiEdit': 'edit',
            'Glob': 'search',
            'LS': 'list',
            'NotebookRead': 'read',
            'NotebookEdit': 'edit',
            'Grep': 'search'
        };
        
        return operationMap[toolName] || 'operation';
    }
    
    /**
     * Get file operation type from paired events
     */
    getFileOperationFromPair(pair) {
        const toolName = pair.tool_name;
        const operationMap = {
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'MultiEdit': 'edit',
            'Glob': 'search',
            'LS': 'list',
            'NotebookRead': 'read',
            'NotebookEdit': 'edit',
            'Grep': 'search'
        };
        
        return operationMap[toolName] || 'operation';
    }
    
    /**
     * Extract agent from paired events
     */
    extractAgentFromPair(pair) {
        // Try to get agent from either event
        const preAgent = pair.pre_event?.agent_type || pair.pre_event?.subagent_type;
        const postAgent = pair.post_event?.agent_type || pair.post_event?.subagent_type;
        
        // Prefer non-'main' and non-'unknown' agents
        if (preAgent && preAgent !== 'main' && preAgent !== 'unknown') return preAgent;
        if (postAgent && postAgent !== 'main' && postAgent !== 'unknown') return postAgent;
        
        // Fallback to any agent
        return preAgent || postAgent || 'PM';
    }

    /**
     * Get file operation details
     */
    getFileOperationDetails(event) {
        const toolName = event.tool_name;
        const params = event.tool_parameters;
        
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
            case 'Grep':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'LS':
                return `Listed directory`;
            default:
                return '';
        }
    }
    
    /**
     * Get file operation details from paired events
     */
    getFileOperationDetailsFromPair(pair) {
        const toolName = pair.tool_name;
        
        // Get parameters from either event
        const preParams = pair.pre_event?.tool_parameters || {};
        const postParams = pair.post_event?.tool_parameters || {};
        const params = { ...preParams, ...postParams };
        
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
            case 'Grep':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'LS':
                return `Listed directory`;
            default:
                return '';
        }
    }

    /**
     * Get icon for file operations - shows combined icons for read+write
     */
    getFileOperationIcon(operations) {
        // Check for notebook operations first
        const hasNotebook = operations.some(op => op.details && (op.details.includes('notebook') || op.details.includes('Notebook')));
        if (hasNotebook) return '📓';
        
        const hasWrite = operations.some(op => ['write', 'edit'].includes(op.operation));
        const hasRead = operations.some(op => op.operation === 'read');
        const hasSearch = operations.some(op => op.operation === 'search');
        const hasList = operations.some(op => op.operation === 'list');
        
        // Show both icons for read+write combinations
        if (hasWrite && hasRead) return '📖✏️'; // Both read and write
        if (hasWrite) return '✏️'; // Write only
        if (hasRead) return '📖'; // Read only
        if (hasSearch) return '🔍'; // Search only
        if (hasList) return '📋'; // List only
        return '📄'; // Default
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
     * Apply agents tab filtering
     */
    applyAgentsFilters(events) {
        const searchInput = document.getElementById('agents-search-input');
        const typeFilter = document.getElementById('agents-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return events.filter(event => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    event.subagent_type || '',
                    event.agent_type || '',
                    event.name || '',
                    event.type || '',
                    event.subtype || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const agentType = event.subagent_type || event.agent_type || 'unknown';
                if (!agentType.toLowerCase().includes(typeValue.toLowerCase())) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply tools tab filtering
     */
    applyToolsFilters(events) {
        const searchInput = document.getElementById('tools-search-input');
        const typeFilter = document.getElementById('tools-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return events.filter(event => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    event.tool_name || '',
                    event.agent_type || '',
                    event.type || '',
                    event.subtype || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const toolName = event.tool_name || '';
                if (toolName !== typeValue) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply files tab filtering
     */
    applyFilesFilters(fileOperations) {
        const searchInput = document.getElementById('files-search-input');
        const typeFilter = document.getElementById('files-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return fileOperations.filter(([filePath, fileData]) => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    filePath,
                    ...fileData.operations.map(op => op.operation),
                    ...fileData.operations.map(op => op.agent)
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const hasOperationType = fileData.operations.some(op => op.operation === typeValue);
                if (!hasOperationType) {
                    return false;
                }
            }
            
            return true;
        });
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
        return 'Tool'; // Fallback - actual tool name should be in event.tool_name
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
        // Use ALL events, not the EventViewer's filtered events
        // Each tab will apply its own filtering logic
        const events = this.eventViewer.events;
        console.log(`getFilteredEventsForTab(${tabName}) - using RAW events: ${events.length} total`);
        
        // Enhanced debugging for empty events
        if (events.length === 0) {
            console.log(`❌ NO RAW EVENTS available!`);
            console.log('EventViewer state:', {
                total_events: this.eventViewer.events.length,
                filtered_events: this.eventViewer.filteredEvents.length,
                search_filter: this.eventViewer.searchFilter,
                type_filter: this.eventViewer.typeFilter,
                session_filter: this.eventViewer.sessionFilter
            });
        } else {
            console.log('✅ Raw events available for', tabName, '- sample:', events[0]);
            console.log('EventViewer filters (IGNORED for tabs):', {
                search_filter: this.eventViewer.searchFilter,
                type_filter: this.eventViewer.typeFilter,
                session_filter: this.eventViewer.sessionFilter
            });
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