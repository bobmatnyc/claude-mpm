/**
 * Module Viewer Component
 * Displays detailed information about selected events organized by class/type
 */

class ModuleViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentEvent = null;
        this.eventsByClass = new Map();
        
        this.init();
    }

    /**
     * Initialize the module viewer
     */
    init() {
        this.setupEventHandlers();
        this.showEmptyState();
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Listen for event selection
        document.addEventListener('eventSelected', (e) => {
            this.showEventDetails(e.detail.event);
        });

        // Listen for selection cleared
        document.addEventListener('eventSelectionCleared', () => {
            this.showEmptyState();
        });

        // Listen for socket event updates to maintain event classification
        document.addEventListener('socketEventUpdate', (e) => {
            this.updateEventsByClass(e.detail.events);
        });
    }

    /**
     * Show empty state when no event is selected
     */
    showEmptyState() {
        this.container.innerHTML = `
            <div class="module-empty">
                <p>Click on an event to view details</p>
                <p class="module-hint">Events are organized by class</p>
            </div>
        `;
        this.currentEvent = null;
    }

    /**
     * Show details for a selected event
     * @param {Object} event - The selected event
     */
    showEventDetails(event) {
        this.currentEvent = event;
        
        // Create structured view based on event type
        const structuredView = this.createEventStructuredView(event);
        
        // Show in container
        this.container.innerHTML = structuredView;
    }

    /**
     * Update events grouped by class for analysis
     * @param {Array} events - All events
     */
    updateEventsByClass(events) {
        this.eventsByClass.clear();
        
        events.forEach(event => {
            const eventClass = this.getEventClass(event);
            if (!this.eventsByClass.has(eventClass)) {
                this.eventsByClass.set(eventClass, []);
            }
            this.eventsByClass.get(eventClass).push(event);
        });
    }

    /**
     * Get event class/category for grouping
     * @param {Object} event - Event object
     * @returns {string} Event class
     */
    getEventClass(event) {
        if (!event.type) return 'unknown';
        
        // Group similar event types
        switch (event.type) {
            case 'session':
                return 'Session Management';
            case 'claude':
                return 'Claude Interactions';
            case 'agent':
                return 'Agent Operations';
            case 'hook':
                return 'Hook System';
            case 'todo':
                return 'Task Management';
            case 'memory':
                return 'Memory Operations';
            case 'log':
                return 'System Logs';
            case 'connection':
                return 'Connection Events';
            default:
                return 'Other Events';
        }
    }

    /**
     * Create structured view for an event
     * @param {Object} event - Event to display
     * @returns {string} HTML content
     */
    createEventStructuredView(event) {
        const eventClass = this.getEventClass(event);
        const relatedEvents = this.eventsByClass.get(eventClass) || [];
        const eventCount = relatedEvents.length;

        let content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>📊 Event Details</h4>
                </div>
                ${this.createEventDetailCard(event.type, event, eventCount)}
            </div>
        `;

        // Add type-specific content
        switch (event.type) {
            case 'agent':
                content += this.createAgentStructuredView(event);
                break;
            case 'hook':
                content += this.createHookStructuredView(event);
                break;
            case 'todo':
                content += this.createTodoStructuredView(event);
                break;
            case 'memory':
                content += this.createMemoryStructuredView(event);
                break;
            case 'claude':
                content += this.createClaudeStructuredView(event);
                break;
            case 'session':
                content += this.createSessionStructuredView(event);
                break;
            default:
                content += this.createGenericStructuredView(event);
                break;
        }

        // Add raw JSON section
        content += this.createJsonSection(event);

        return content;
    }

    /**
     * Create event detail card
     */
    createEventDetailCard(eventType, event, count) {
        const timestamp = new Date(event.timestamp).toLocaleString();
        const eventIcon = this.getEventIcon(eventType);
        
        return `
            <div class="event-detail-card">
                <div class="event-detail-header">
                    <div class="event-detail-title">
                        ${eventIcon} ${eventType || 'Unknown'}.${event.subtype || 'default'}
                    </div>
                    <div class="event-detail-time">${timestamp}</div>
                </div>
                <div class="event-detail-content">
                    ${this.createProperty('Event ID', event.id || 'N/A')}
                    ${this.createProperty('Type', `${eventType}.${event.subtype || 'default'}`)}
                    ${this.createProperty('Class Events', count)}
                    ${event.data && event.data.session_id ? 
                        this.createProperty('Session', event.data.session_id) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create agent-specific structured view
     */
    createAgentStructuredView(event) {
        const data = event.data || {};
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🤖 Agent Information</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Agent Type', data.agent_type || 'Unknown')}
                    ${this.createProperty('Name', data.name || 'N/A')}
                    ${this.createProperty('Phase', event.subtype || 'N/A')}
                    ${data.config ? this.createProperty('Config', JSON.stringify(data.config)) : ''}
                    ${data.capabilities ? this.createProperty('Capabilities', data.capabilities.join(', ')) : ''}
                    ${data.result ? this.createProperty('Result', JSON.stringify(data.result)) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create hook-specific structured view
     */
    createHookStructuredView(event) {
        const data = event.data || {};
        
        // Extract file path information from tool parameters
        const filePath = this.extractFilePathFromHook(data);
        const toolInfo = this.extractToolInfoFromHook(data);
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🔗 Hook Information</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Hook Name', this.getHookDisplayName(event, data))}
                    ${this.createProperty('Event Type', data.event_type || event.subtype || 'N/A')}
                    ${filePath ? this.createProperty('File Path', filePath) : ''}
                    ${toolInfo.tool_name ? this.createProperty('Tool', toolInfo.tool_name) : ''}
                    ${toolInfo.operation_type ? this.createProperty('Operation', toolInfo.operation_type) : ''}
                    ${data.session_id ? this.createProperty('Session ID', data.session_id) : ''}
                    ${data.working_directory ? this.createProperty('Working Directory', data.working_directory) : ''}
                    ${data.duration_ms ? this.createProperty('Duration', `${data.duration_ms}ms`) : ''}
                    ${data.exit_code !== undefined ? this.createProperty('Exit Code', data.exit_code) : ''}
                    ${data.success !== undefined ? this.createProperty('Success', data.success ? 'Yes' : 'No') : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create todo-specific structured view
     */
    createTodoStructuredView(event) {
        const data = event.data || {};
        
        let content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>✅ Todo Information</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Operation', event.subtype || 'N/A')}
                    ${data.count ? this.createProperty('Total Items', data.count) : ''}
                </div>
            </div>
        `;

        // Add todo checklist if available
        if (data.todos && Array.isArray(data.todos)) {
            content += `
                <div class="todo-checklist">
                    <div class="todo-checklist-header">📋 Todo Items</div>
                    ${data.todos.map(todo => `
                        <div class="todo-item todo-${todo.status || 'pending'}">
                            <span class="todo-status">${this.getTodoStatusIcon(todo.status)}</span>
                            <span class="todo-content">${todo.content || 'No content'}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        return content;
    }

    /**
     * Create memory-specific structured view
     */
    createMemoryStructuredView(event) {
        const data = event.data || {};
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🧠 Memory Information</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Operation', data.operation || 'Unknown')}
                    ${this.createProperty('Key', data.key || 'N/A')}
                    ${data.value ? this.createProperty('Value', JSON.stringify(data.value)) : ''}
                    ${data.namespace ? this.createProperty('Namespace', data.namespace) : ''}
                    ${data.metadata ? this.createProperty('Metadata', JSON.stringify(data.metadata)) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create Claude-specific structured view
     */
    createClaudeStructuredView(event) {
        const data = event.data || {};
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🤖 Claude Interaction</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Type', event.subtype || 'N/A')}
                    ${data.prompt ? this.createProperty('Prompt', this.truncateText(data.prompt, 200)) : ''}
                    ${data.message ? this.createProperty('Message', this.truncateText(data.message, 200)) : ''}
                    ${data.response ? this.createProperty('Response', this.truncateText(data.response, 200)) : ''}
                    ${data.content ? this.createProperty('Content', this.truncateText(data.content, 200)) : ''}
                    ${data.tokens ? this.createProperty('Tokens', data.tokens) : ''}
                    ${data.model ? this.createProperty('Model', data.model) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create session-specific structured view
     */
    createSessionStructuredView(event) {
        const data = event.data || {};
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>📱 Session Information</h4>
                </div>
                <div class="structured-data">
                    ${this.createProperty('Action', event.subtype || 'N/A')}
                    ${this.createProperty('Session ID', data.session_id || 'N/A')}
                    ${data.working_directory ? this.createProperty('Working Dir', data.working_directory) : ''}
                    ${data.git_branch ? this.createProperty('Git Branch', data.git_branch) : ''}
                    ${data.agent_type ? this.createProperty('Agent Type', data.agent_type) : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create generic structured view
     */
    createGenericStructuredView(event) {
        const data = event.data || {};
        const keys = Object.keys(data);
        
        if (keys.length === 0) {
            return '';
        }
        
        return `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>📋 Event Data</h4>
                </div>
                <div class="structured-data">
                    ${keys.map(key => 
                        this.createProperty(key, typeof data[key] === 'object' ? 
                            JSON.stringify(data[key]) : String(data[key]))
                    ).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Create JSON section
     */
    createJsonSection(event) {
        return `
            <div class="json-section">
                <div class="json-header">
                    <h4>🔍 Raw JSON Data</h4>
                </div>
                <div class="json-display">
                    <pre>${this.formatJSON(event)}</pre>
                </div>
            </div>
        `;
    }

    /**
     * Create a property display element
     */
    createProperty(key, value) {
        const displayValue = this.truncateText(String(value), 300);
        return `
            <div class="event-property">
                <span class="event-property-key">${key}:</span>
                <span class="event-property-value">${displayValue}</span>
            </div>
        `;
    }

    /**
     * Get icon for event type
     */
    getEventIcon(eventType) {
        const icons = {
            session: '📱',
            claude: '🤖',
            agent: '🎯',
            hook: '🔗',
            todo: '✅',
            memory: '🧠',
            log: '📝',
            connection: '🔌',
            unknown: '❓'
        };
        return icons[eventType] || icons.unknown;
    }

    /**
     * Get todo status icon
     */
    getTodoStatusIcon(status) {
        const icons = {
            completed: '✅',
            'in_progress': '🔄',
            pending: '⏳',
            cancelled: '❌'
        };
        return icons[status] || icons.pending;
    }

    /**
     * Get meaningful hook display name from event data
     */
    getHookDisplayName(event, data) {
        // First check if there's a specific hook name in the data
        if (data.hook_name) return data.hook_name;
        if (data.name) return data.name;
        
        // Use event.subtype or data.event_type to determine hook name
        const eventType = event.subtype || data.event_type;
        
        // Map hook event types to meaningful display names
        const hookNames = {
            'user_prompt': 'User Prompt',
            'pre_tool': 'Tool Execution (Pre)',
            'post_tool': 'Tool Execution (Post)', 
            'notification': 'Notification',
            'stop': 'Session Stop',
            'subagent_stop': 'Subagent Stop'
        };
        
        if (hookNames[eventType]) {
            return hookNames[eventType];
        }
        
        // If it's a compound event type like "hook.user_prompt", extract the part after "hook."
        if (typeof event.type === 'string' && event.type.startsWith('hook.')) {
            const hookType = event.type.replace('hook.', '');
            if (hookNames[hookType]) {
                return hookNames[hookType];
            }
        }
        
        // Fallback to formatting the event type nicely
        if (eventType) {
            return eventType.split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        }
        
        return 'Unknown Hook';
    }

    /**
     * Extract file path from hook event data
     */
    extractFilePathFromHook(data) {
        // Check tool parameters for file path
        if (data.tool_parameters && data.tool_parameters.file_path) {
            return data.tool_parameters.file_path;
        }
        
        // Check direct file_path field
        if (data.file_path) {
            return data.file_path;
        }
        
        // Check nested in other common locations
        if (data.tool_input && data.tool_input.file_path) {
            return data.tool_input.file_path;
        }
        
        // Check for notebook path (alternative field name)
        if (data.tool_parameters && data.tool_parameters.notebook_path) {
            return data.tool_parameters.notebook_path;
        }
        
        return null;
    }

    /**
     * Extract tool information from hook event data
     */
    extractToolInfoFromHook(data) {
        return {
            tool_name: data.tool_name || (data.tool_parameters && data.tool_parameters.tool_name),
            operation_type: data.operation_type || (data.tool_parameters && data.tool_parameters.operation_type)
        };
    }

    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Format JSON for display
     */
    formatJSON(obj) {
        try {
            return JSON.stringify(obj, null, 2);
        } catch (e) {
            return String(obj);
        }
    }

    /**
     * Clear the module viewer
     */
    clear() {
        this.showEmptyState();
    }

    /**
     * Get current event
     */
    getCurrentEvent() {
        return this.currentEvent;
    }
}

// Export for global use
window.ModuleViewer = ModuleViewer;