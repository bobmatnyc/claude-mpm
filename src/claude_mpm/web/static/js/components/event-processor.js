/**
 * Event Processor Module
 * 
 * Handles event processing, filtering, and rendering for different tabs in the dashboard.
 * Provides centralized event filtering and rendering logic for agents, tools, and files tabs.
 * 
 * WHY: Extracted from main dashboard to isolate complex event processing logic
 * that involves filtering, transforming, and rendering events across different views.
 * This improves maintainability and makes the event processing logic testable.
 * 
 * DESIGN DECISION: Maintains its own filtered event collections while relying on
 * eventViewer for source data. Provides separate filtering logic for each tab type
 * while sharing common filtering patterns and utilities.
 */
class EventProcessor {
    constructor(eventViewer, agentInference) {
        this.eventViewer = eventViewer;
        this.agentInference = agentInference;
        
        // Processed event collections for different tabs
        this.agentEvents = [];
        this.filteredAgentEvents = [];
        this.filteredToolEvents = [];
        this.filteredFileEvents = [];
        
        // Session filtering
        this.selectedSessionId = null;
        
        console.log('Event processor initialized');
    }

    /**
     * Get filtered events for a specific tab
     * @param {string} tabName - Tab name ('agents', 'tools', 'files', 'events')
     * @returns {Array} - Filtered events
     */
    getFilteredEventsForTab(tabName) {
        const events = this.eventViewer.events;
        console.log(`getFilteredEventsForTab(${tabName}) - using RAW events: ${events.length} total`);

        // Use session manager to filter events by session if needed
        const sessionManager = window.sessionManager;
        if (sessionManager && sessionManager.selectedSessionId) {
            const sessionEvents = sessionManager.getEventsForSession(sessionManager.selectedSessionId);
            console.log(`Filtering by session ${sessionManager.selectedSessionId}: ${sessionEvents.length} events`);
            return sessionEvents;
        }

        return events;
    }

    /**
     * Apply agents tab filtering
     * @param {Array} events - Events to filter
     * @returns {Array} - Filtered events
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
     * @param {Array} events - Events to filter
     * @returns {Array} - Filtered events
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
     * Apply tools tab filtering for tool calls
     * @param {Array} toolCallsArray - Tool calls array to filter
     * @returns {Array} - Filtered tool calls
     */
    applyToolCallFilters(toolCallsArray) {
        const searchInput = document.getElementById('tools-search-input');
        const typeFilter = document.getElementById('tools-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return toolCallsArray.filter(([key, toolCall]) => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    toolCall.tool_name || '',
                    toolCall.agent_type || '',
                    'tool_call'
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const toolName = toolCall.tool_name || '';
                if (toolName !== typeValue) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply files tab filtering
     * @param {Array} fileOperations - File operations to filter
     * @returns {Array} - Filtered file operations
     */
    applyFilesFilters(fileOperations) {
        const searchInput = document.getElementById('files-search-input');
        const typeFilter = document.getElementById('files-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return fileOperations.filter(([filePath, fileData]) => {
            // Session filter - filter operations within each file
            if (this.selectedSessionId) {
                // Filter operations for this file by session
                const sessionOperations = fileData.operations.filter(op => 
                    op.sessionId === this.selectedSessionId
                );
                
                // If no operations from this session, exclude the file
                if (sessionOperations.length === 0) {
                    return false;
                }
                
                // Update the fileData to only include session-specific operations
                // (Note: This creates a filtered view without modifying the original)
                fileData = {
                    ...fileData,
                    operations: sessionOperations,
                    lastOperation: sessionOperations[sessionOperations.length - 1]?.timestamp || fileData.lastOperation
                };
            }
            
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
                const operations = fileData.operations.map(op => op.operation);
                if (!operations.includes(typeValue)) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Extract operation type from event type
     * @param {string} eventType - Event type string
     * @returns {string} - Operation type
     */
    extractOperation(eventType) {
        if (!eventType) return 'unknown';
        
        const type = eventType.toLowerCase();
        if (type.includes('read')) return 'read';
        if (type.includes('write')) return 'write';
        if (type.includes('edit')) return 'edit';
        if (type.includes('create')) return 'create';
        if (type.includes('delete')) return 'delete';
        if (type.includes('move') || type.includes('rename')) return 'move';
        
        return 'other';
    }

    /**
     * Extract tool name from hook event type
     * @param {string} eventType - Hook event type
     * @returns {string} - Tool name
     */
    extractToolFromHook(eventType) {
        if (!eventType) return '';
        
        // Pattern: Pre{ToolName}Use or Post{ToolName}Use
        const match = eventType.match(/^(?:Pre|Post)(.+)Use$/);
        return match ? match[1] : '';
    }

    /**
     * Extract tool name from subtype
     * @param {string} subtype - Event subtype
     * @returns {string} - Tool name
     */
    extractToolFromSubtype(subtype) {
        if (!subtype) return '';
        
        // Handle various subtype patterns
        if (subtype.includes('_')) {
            const parts = subtype.split('_');
            return parts[0] || '';
        }
        
        return subtype;
    }

    /**
     * Extract target information from tool parameters
     * @param {string} toolName - Tool name
     * @param {Object} params - Tool parameters
     * @param {Object} toolParameters - Alternative tool parameters
     * @returns {string} - Target information
     */
    extractToolTarget(toolName, params, toolParameters) {
        const parameters = params || toolParameters || {};
        
        switch (toolName?.toLowerCase()) {
            case 'read':
            case 'write':
            case 'edit':
                return parameters.file_path || parameters.path || '';
            case 'bash':
                return parameters.command || '';
            case 'grep':
                return parameters.pattern || '';
            case 'task':
                return parameters.subagent_type || parameters.agent_type || '';
            default:
                // Try to find a meaningful parameter
                const keys = Object.keys(parameters);
                const meaningfulKeys = ['path', 'file_path', 'command', 'pattern', 'query', 'target'];
                for (const key of meaningfulKeys) {
                    if (parameters[key]) {
                        return parameters[key];
                    }
                }
                return keys.length > 0 ? `${keys[0]}: ${parameters[keys[0]]}` : '';
        }
    }

    /**
     * Generate HTML for agent events
     * @param {Array} events - Agent events to render
     * @returns {string} - HTML string
     */
    generateAgentHTML(events) {
        const agentEvents = this.applyAgentsFilters(events);
        
        return agentEvents.map((event, index) => {
            const inference = this.agentInference.getInferredAgentForEvent(event);
            
            // Improved fallback logic for agent name extraction
            let agentName = 'Unknown';
            let agentType = 'unknown';
            let confidence = 'unknown';
            
            if (inference) {
                agentName = inference.agentName || 'Unknown';
                agentType = inference.type || 'unknown';
                confidence = inference.confidence || 'unknown';
            } else {
                // Fallback: direct field extraction from event
                const data = event.data || {};
                agentName = event.subagent_type || data.subagent_type || 
                           event.agent_type || data.agent_type || 
                           event.agent_id || data.agent_id ||
                           data.delegation_details?.agent_type || 'Unknown';
                
                // Determine type based on available info
                if (agentName !== 'Unknown' && agentName !== 'PM') {
                    agentType = 'subagent';
                    confidence = 'fallback';
                } else if (agentName === 'PM' || event.hook_event_name === 'Stop' || event.type === 'hook.stop') {
                    agentName = 'PM';
                    agentType = 'main_agent';
                    confidence = 'fallback';
                }
            }
            
            const timestamp = this.formatTimestamp(event.timestamp);
            const eventType = event.hook_event_name || event.type || 'Unknown';
            
            // Debug logging for problematic events
            if (agentName === 'Unknown' && Math.random() < 0.2) {
                console.log('Agent display issue - Unknown agent:', {
                    event: event,
                    inference: inference,
                    eventType: eventType,
                    hasData: !!event.data,
                    dataKeys: event.data ? Object.keys(event.data) : [],
                    eventKeys: Object.keys(event)
                });
            }
            
            const onclickString = `dashboard.selectCard('agents', ${index}, 'agent', ${index}); dashboard.showAgentDetailsByIndex(${index});`;

            return `
                <div class="event-item event-agent" onclick="${onclickString}">
                    <div class="event-header">
                        <span class="event-type">🤖 ${agentName}</span>
                        <span class="agent-confidence ${confidence}">${confidence}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <span class="agent-type ${agentType}">${agentType}</span>
                        <span class="event-subtype">${eventType}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Generate HTML for tool events
     * @param {Array} toolCalls - Tool calls to render
     * @returns {string} - HTML string
     */
    generateToolHTML(toolCalls) {
        const filteredToolCalls = this.applyToolCallFilters(toolCalls);
        
        return filteredToolCalls.map(([key, toolCall], index) => {
            const toolName = toolCall.tool_name || 'Unknown';
            const agent = toolCall.agent || 'Unknown';
            const timestamp = this.formatTimestamp(toolCall.timestamp);
            const status = toolCall.post ? 'completed' : 'pending';
            const statusClass = status === 'completed' ? 'status-success' : 'status-pending';

            return `
                <div class="event-item event-tool ${statusClass}" onclick="dashboard.selectCard('tools', ${index}, 'toolCall', '${key}'); dashboard.showToolCallDetails('${key}')">
                    <div class="event-header">
                        <span class="event-type">🔧 ${toolName}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <span class="tool-agent">Agent: ${agent}</span>
                        <span class="tool-status ${statusClass}">${status}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Generate HTML for file operations
     * @param {Array} fileOperations - File operations to render
     * @returns {string} - HTML string
     */
    generateFileHTML(fileOperations) {
        const filteredFiles = this.applyFilesFilters(fileOperations);
        
        return filteredFiles.map(([filePath, fileData], index) => {
            const operations = fileData.operations.map(op => op.operation);
            const uniqueOperations = [...new Set(operations)];
            const icon = this.getFileOperationIcon(uniqueOperations);
            const timestamp = this.formatTimestamp(fileData.lastOperation);
            const operationCount = operations.length;

            // Generate git diff icons for operations that support it
            const gitDiffIcons = fileData.operations.map(op => {
                if (['edit', 'write'].includes(op.operation)) {
                    return `
                        <span class="git-diff-icon" 
                              onclick="event.stopPropagation(); showGitDiffModal('${filePath}', '${op.timestamp}')"
                              title="View git diff for this file operation"
                              style="margin-left: 8px; cursor: pointer; font-size: 16px;">
                            📋
                        </span>
                    `;
                }
                return '';
            }).join('');

            return `
                <div class="event-item file-item" onclick="dashboard.selectCard('files', ${index}, 'file', '${filePath}'); dashboard.showFileDetails('${filePath}')">
                    <div class="event-header">
                        <span class="event-type">${icon}</span>
                        <span class="file-path">${this.getRelativeFilePath(filePath)}</span>
                        <span class="event-timestamp">${timestamp}</span>
                        ${gitDiffIcons}
                    </div>
                    <div class="event-data">
                        <span class="file-operations">${uniqueOperations.join(', ')}</span>
                        <span class="operation-count">${operationCount} operations</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Get icon for file operations
     * @param {Array} operations - Array of operations
     * @returns {string} - Icon representation
     */
    getFileOperationIcon(operations) {
        if (operations.includes('write') || operations.includes('create')) return '📝';
        if (operations.includes('edit')) return '✏️';
        if (operations.includes('read')) return '👁️';
        if (operations.includes('delete')) return '🗑️';
        if (operations.includes('move')) return '📦';
        return '📄';
    }

    /**
     * Get relative file path
     * @param {string} filePath - Full file path
     * @returns {string} - Relative path
     */
    getRelativeFilePath(filePath) {
        if (!filePath) return '';
        
        // Simple relative path logic - can be enhanced
        const parts = filePath.split('/');
        if (parts.length > 3) {
            return '.../' + parts.slice(-2).join('/');
        }
        return filePath;
    }

    /**
     * Format timestamp for display
     * @param {string|number} timestamp - Timestamp to format
     * @returns {string} - Formatted timestamp
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }

    /**
     * Set selected session ID for filtering
     * @param {string} sessionId - Session ID to filter by
     */
    setSelectedSessionId(sessionId) {
        this.selectedSessionId = sessionId;
    }

    /**
     * Get selected session ID
     * @returns {string|null} - Current session ID
     */
    getSelectedSessionId() {
        return this.selectedSessionId;
    }
}