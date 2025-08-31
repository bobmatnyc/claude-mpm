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
     * Apply agents tab filtering for unique instances
     * @param {Array} uniqueInstances - Unique agent instances to filter
     * @returns {Array} - Filtered unique instances
     */
    applyAgentsFilters(uniqueInstances) {
        const searchInput = document.getElementById('agents-search-input');
        const typeFilter = document.getElementById('agents-type-filter');

        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';

        return uniqueInstances.filter(instance => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    instance.agentName || '',
                    instance.type || '',
                    instance.isImplied ? 'implied' : 'explicit'
                ].join(' ').toLowerCase();

                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }

            // Type filter
            if (typeValue) {
                const agentName = instance.agentName || 'unknown';
                if (!agentName.toLowerCase().includes(typeValue.toLowerCase())) {
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
     * Generate HTML for unique agent instances (one row per PM delegation)
     * @param {Array} events - Agent events to render (not used, kept for compatibility)
     * @returns {string} - HTML string
     */
    generateAgentHTML(events) {
        // Get unique agent instances from agent inference
        const uniqueInstances = this.agentInference.getUniqueAgentInstances();

        // Apply filtering
        const filteredInstances = this.applyAgentsFilters(uniqueInstances);

        return filteredInstances.map((instance, index) => {
            const agentName = instance.agentName;
            const timestamp = this.formatTimestamp(instance.firstTimestamp || instance.timestamp);
            const delegationType = instance.isImplied ? 'implied' : 'explicit';
            // Fix: Use totalEventCount which is the actual property name from getUniqueAgentInstances()
            const eventCount = instance.totalEventCount || instance.eventCount || 0;

            const onclickString = `dashboard.selectCard('agents', ${index}, 'agent_instance', '${instance.id}'); dashboard.showAgentInstanceDetails('${instance.id}');`;

            // Format: "[Agent Name] (delegationType, eventCount events)" with separate timestamp
            const agentMainContent = `${agentName} (${delegationType}, ${eventCount} events)`;

            return `
                <div class="event-item single-row event-agent" onclick="${onclickString}">
                    <span class="event-single-row-content">
                        <span class="event-content-main">${agentMainContent}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </span>
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
            const rawAgent = toolCall.agent_type || 'Unknown';
            const timestamp = this.formatTimestamp(toolCall.timestamp);
            const status = toolCall.post_event ? 'completed' : 'pending';
            const statusClass = status === 'completed' ? 'status-success' : 'status-pending';

            // Convert agent name: show "pm" for PM agent, otherwise show actual agent name
            const agentName = rawAgent.toLowerCase() === 'pm' ? 'pm' : rawAgent;

            // Format: "Tool Name (Agent Name)" - removed duration from main display
            const toolMainContent = `${toolName} (${agentName})`;

            return `
                <div class="event-item single-row event-tool ${statusClass}" onclick="dashboard.selectCard('tools', ${index}, 'toolCall', '${key}'); dashboard.showToolCallDetails('${key}')">
                    <span class="event-single-row-content">
                        <span class="event-content-main">${toolMainContent}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </span>
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
            const timestamp = this.formatTimestamp(fileData.lastOperation);

            // Count operations by type for display: "read(2), write(1)"
            const operationCounts = {};
            operations.forEach(op => {
                operationCounts[op] = (operationCounts[op] || 0) + 1;
            });

            const operationSummary = Object.entries(operationCounts)
                .map(([op, count]) => `${op}(${count})`)
                .join(', ');

            // Get unique agents that worked on this file
            const uniqueAgents = [...new Set(fileData.operations.map(op => op.agent))];
            const agentSummary = uniqueAgents.length > 1 ? `by ${uniqueAgents.length} agents` : `by ${uniqueAgents[0] || 'unknown'}`;

            // Format: "[file path] read(2), write(1) by agent" with separate timestamp
            const fileName = this.getRelativeFilePath(filePath);
            const fileMainContent = `${fileName} ${operationSummary} ${agentSummary}`;

            return `
                <div class="event-item single-row file-item" onclick="dashboard.selectCard('files', ${index}, 'file', '${filePath}'); dashboard.showFileDetails('${filePath}')">
                    <span class="event-single-row-content">
                        <span class="event-content-main">${fileMainContent}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </span>
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

    /**
     * Get unique tool instances (one row per unique tool call)
     * This deduplicates tool calls to show unique instances only
     * @param {Array} toolCallsArray - Tool calls array
     * @returns {Array} - Unique tool instances
     */
    getUniqueToolInstances(toolCallsArray) {
        // The toolCallsArray already represents unique tool calls
        // since it's generated from paired pre/post events in FileToolTracker
        // Just apply filtering and return
        return this.applyToolCallFilters(toolCallsArray);
    }

    /**
     * Get unique file instances (one row per unique file)
     * This aggregates all operations on each file
     * @param {Array} fileOperations - File operations array
     * @returns {Array} - Unique file instances (same as input since already unique per file)
     */
    getUniqueFileInstances(fileOperations) {
        // The fileOperations array already represents unique files
        // since it's keyed by file path in FileToolTracker
        // Just apply filtering and return
        return this.applyFilesFilters(fileOperations);
    }



    /**
     * Show agent instance details for unique instance view
     * @param {string} instanceId - Agent instance ID
     */
    showAgentInstanceDetails(instanceId) {
        const pmDelegations = this.agentInference.getPMDelegations();
        const instance = pmDelegations.get(instanceId);

        if (!instance) {
            console.error('Agent instance not found:', instanceId);
            return;
        }

        // Show details about this PM delegation and its events
        console.log('Showing agent instance details for:', instanceId, instance);

        // This would integrate with the existing detail view system
        // For now, just log the details - can be expanded to show in a modal/sidebar
        const detailsHtml = `
            <div class="agent-instance-details">
                <h3>Agent Instance: ${instance.agentName}</h3>
                <p><strong>Type:</strong> ${instance.isImplied ? 'Implied PM Delegation' : 'Explicit PM Delegation'}</p>
                <p><strong>Start Time:</strong> ${this.formatTimestamp(instance.timestamp)}</p>
                <p><strong>Event Count:</strong> ${instance.agentEvents.length}</p>
                <p><strong>Session:</strong> ${instance.sessionId}</p>
                ${instance.pmCall ? `<p><strong>PM Call:</strong> Task delegation to ${instance.agentName}</p>` : '<p><strong>Note:</strong> Implied delegation (no explicit PM call found)</p>'}
            </div>
        `;

        // You would integrate this with your existing detail display system
        console.log('Agent instance details HTML:', detailsHtml);
    }
}

// ES6 Module export
export { EventProcessor };
export default EventProcessor;
