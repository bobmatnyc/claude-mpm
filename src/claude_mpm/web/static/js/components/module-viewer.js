/**
 * Module Viewer Component
 * Displays detailed information about selected events organized by class/type
 */

class ModuleViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.dataContainer = null;
        this.jsonContainer = null;
        this.currentEvent = null;
        this.eventsByClass = new Map();
        
        this.init();
    }

    /**
     * Initialize the module viewer
     */
    init() {
        this.setupContainers();
        this.setupEventHandlers();
        this.showEmptyState();
    }

    /**
     * Setup container references for the two-pane layout
     */
    setupContainers() {
        this.dataContainer = document.getElementById('module-data-content');
        this.jsonContainer = document.getElementById('module-json-content');
        
        if (!this.dataContainer || !this.jsonContainer) {
            console.error('Module viewer pane containers not found');
        }
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
        if (this.dataContainer) {
            this.dataContainer.innerHTML = `
                <div class="module-empty">
                    <p>Click on an event to view structured data</p>
                    <p class="module-hint">Data is organized by event type</p>
                </div>
            `;
        }
        
        if (this.jsonContainer) {
            this.jsonContainer.innerHTML = `
                <div class="module-empty">
                    <p>Raw JSON data will appear here</p>
                </div>
            `;
        }
        
        this.currentEvent = null;
    }

    /**
     * Show details for a selected event
     * @param {Object} event - The selected event
     */
    showEventDetails(event) {
        this.currentEvent = event;
        
        // Render structured data in top pane
        this.renderStructuredData(event);
        
        // Render JSON in bottom pane
        this.renderJsonData(event);
    }

    /**
     * Render structured data in the data pane
     * @param {Object} event - The event to render
     */
    renderStructuredData(event) {
        if (!this.dataContainer) return;
        
        // Create contextual header
        const contextualHeader = this.createContextualHeader(event);
        
        // Create structured view based on event type
        const structuredView = this.createEventStructuredView(event);
        
        // Show header and structured view in data container
        this.dataContainer.innerHTML = contextualHeader + structuredView;
    }

    /**
     * Render JSON data in the JSON pane
     * @param {Object} event - The event to render
     */
    renderJsonData(event) {
        if (!this.jsonContainer) return;
        
        // Create formatted JSON display
        this.jsonContainer.innerHTML = `
            <pre>${this.formatJSON(event)}</pre>
        `;
    }

    /**
     * Ingest method that determines how to render event(s)
     * @param {Object|Array} eventData - Single event or array of events
     */
    ingest(eventData) {
        if (Array.isArray(eventData)) {
            // Handle multiple events - for now, show the first one
            if (eventData.length > 0) {
                this.showEventDetails(eventData[0]);
            } else {
                this.showEmptyState();
            }
        } else if (eventData && typeof eventData === 'object') {
            // Handle single event
            this.showEventDetails(eventData);
        } else {
            // Invalid data
            this.showEmptyState();
        }
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
     * Create contextual header for the structured data
     * @param {Object} event - Event to display
     * @returns {string} HTML content
     */
    createContextualHeader(event) {
        const timestamp = this.formatTimestamp(event.timestamp);
        const data = event.data || {};
        let headerText = '';
        
        // Determine header text based on event type
        switch (event.type) {
            case 'hook':
                // For Tools: "ToolName: [Agent] [time]"
                const toolName = this.extractToolName(data);
                const agent = this.extractAgent(event) || 'Unknown';
                if (toolName) {
                    headerText = `${toolName}: ${agent} ${timestamp}`;
                } else {
                    const hookName = this.getHookDisplayName(event, data);
                    headerText = `${hookName}: ${agent} ${timestamp}`;
                }
                break;
                
            case 'agent':
                // For Agents: "Agent: [AgentType] [time]"
                const agentType = data.agent_type || data.name || 'Unknown';
                headerText = `Agent: ${agentType} ${timestamp}`;
                break;
                
            case 'todo':
                // For TodoWrite: "TodoWrite: [Agent] [time]"
                const todoAgent = this.extractAgent(event) || 'PM';
                headerText = `TodoWrite: ${todoAgent} ${timestamp}`;
                break;
                
            case 'memory':
                // For Memory: "Memory: [Operation] [time]"
                const operation = data.operation || 'Unknown';
                headerText = `Memory: ${operation} ${timestamp}`;
                break;
                
            case 'session':
            case 'claude':
            case 'log':
            case 'connection':
                // For Events: "Event: [Type.Subtype] [time]"
                const eventType = event.type;
                const subtype = event.subtype || 'default';
                headerText = `Event: ${eventType}.${subtype} ${timestamp}`;
                break;
                
            default:
                // For Files and other events: "File: [filename] [time]" or generic
                const fileName = this.extractFileName(data);
                if (fileName) {
                    headerText = `File: ${fileName} ${timestamp}`;
                } else {
                    const eventType = event.type || 'Unknown';
                    const subtype = event.subtype || 'default';
                    headerText = `Event: ${eventType}.${subtype} ${timestamp}`;
                }
                break;
        }
        
        return `
            <div class="contextual-header">
                <h3 class="contextual-header-text">${headerText}</h3>
            </div>
        `;
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
                ${this.createEventDetailCard(event.type, event, eventCount)}
            </div>
        `;

        // Add type-specific content
        switch (event.type) {
            case 'agent':
                content += this.createAgentStructuredView(event);
                break;
            case 'hook':
                // Check if this is actually a Task delegation (agent-related hook)
                if (event.data?.tool_name === 'Task' && event.data?.tool_parameters?.subagent_type) {
                    content += this.createAgentStructuredView(event);
                } else {
                    content += this.createHookStructuredView(event);
                }
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

        // Note: JSON section is now rendered separately in the JSON pane
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
        
        // Handle Task delegation events (which appear as hook events but contain agent info)
        if (event.type === 'hook' && data.tool_name === 'Task' && data.tool_parameters?.subagent_type) {
            const taskData = data.tool_parameters;
            return `
                <div class="structured-view-section">
                    <div class="structured-data">
                        ${this.createProperty('Agent Type', taskData.subagent_type)}
                        ${this.createProperty('Task Type', 'Subagent Delegation')}
                        ${this.createProperty('Phase', event.subtype || 'pre_tool')}
                        ${taskData.description ? this.createProperty('Description', taskData.description) : ''}
                        ${taskData.prompt ? this.createProperty('Prompt Preview', this.truncateText(taskData.prompt, 200)) : ''}
                        ${data.session_id ? this.createProperty('Session ID', data.session_id) : ''}
                        ${data.working_directory ? this.createProperty('Working Directory', data.working_directory) : ''}
                    </div>
                    ${taskData.prompt ? `
                        <div class="prompt-section">
                            <div class="contextual-header">
                                <h3 class="contextual-header-text">📝 Task Prompt</h3>
                            </div>
                            <div class="structured-data">
                                <div class="task-prompt" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.4;">
                                    ${taskData.prompt}
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Handle regular agent events
        return `
            <div class="structured-view-section">
                <div class="structured-data">
                    ${this.createProperty('Agent Type', data.agent_type || data.subagent_type || 'Unknown')}
                    ${this.createProperty('Name', data.name || 'N/A')}
                    ${this.createProperty('Phase', event.subtype || 'N/A')}
                    ${data.config ? this.createProperty('Config', typeof data.config === 'object' ? Object.keys(data.config).join(', ') : String(data.config)) : ''}
                    ${data.capabilities ? this.createProperty('Capabilities', data.capabilities.join(', ')) : ''}
                    ${data.result ? this.createProperty('Result', typeof data.result === 'object' ? '[Object]' : String(data.result)) : ''}
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
        
        // Check if this is a write operation that can show git diff
        const isWriteOperation = this.isWriteOperation(toolInfo.tool_name, data);
        const canShowGitDiff = isWriteOperation && filePath;
        
        let gitDiffButton = '';
        if (canShowGitDiff) {
            const timestamp = event.timestamp;
            const workingDir = data.working_directory || '';
            gitDiffButton = `
                <div class="git-diff-action">
                    <button class="git-diff-button" 
                            onclick="showGitDiffModal('${filePath}', '${timestamp}', '${workingDir}')"
                            title="View git diff for this file operation">
                        📋 View Git Diff
                    </button>
                </div>
            `;
        }
        
        return `
            <div class="structured-view-section">
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
                ${gitDiffButton}
            </div>
        `;
    }

    /**
     * Check if this is a write operation that modifies files
     * @param {string} toolName - Name of the tool used
     * @param {Object} data - Event data
     * @returns {boolean} True if this is a write operation
     */
    isWriteOperation(toolName, data) {
        // Common write operation tool names
        const writeTools = [
            'Write',
            'Edit', 
            'MultiEdit',
            'NotebookEdit'
        ];
        
        if (writeTools.includes(toolName)) {
            return true;
        }
        
        // Check for write-related parameters in the data
        if (data.tool_parameters) {
            const params = data.tool_parameters;
            
            // Check for content or editing parameters
            if (params.content || params.new_string || params.edits) {
                return true;
            }
            
            // Check for file modification indicators
            if (params.edit_mode && params.edit_mode !== 'read') {
                return true;
            }
        }
        
        // Check event subtype for write operations
        if (data.event_type === 'post_tool' || data.event_type === 'pre_tool') {
            // Additional heuristics based on tool usage patterns
            if (toolName && (
                toolName.toLowerCase().includes('write') ||
                toolName.toLowerCase().includes('edit') ||
                toolName.toLowerCase().includes('modify')
            )) {
                return true;
            }
        }
        
        return false;
    }

    /**
     * Create todo-specific structured view
     */
    createTodoStructuredView(event) {
        const data = event.data || {};
        
        let content = '';

        // Add todo checklist if available - start directly with checklist
        if (data.todos && Array.isArray(data.todos)) {
            content += `
                <div class="todo-checklist">
                    ${data.todos.map(todo => `
                        <div class="todo-item todo-${todo.status || 'pending'}">
                            <span class="todo-status">${this.getTodoStatusIcon(todo.status)}</span>
                            <span class="todo-content">${todo.content || 'No content'}</span>
                            <span class="todo-priority priority-${todo.priority || 'medium'}">${this.getTodoPriorityIcon(todo.priority)}</span>
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
                <div class="structured-data">
                    ${this.createProperty('Operation', data.operation || 'Unknown')}
                    ${this.createProperty('Key', data.key || 'N/A')}
                    ${data.value ? this.createProperty('Value', typeof data.value === 'object' ? '[Object]' : String(data.value)) : ''}
                    ${data.namespace ? this.createProperty('Namespace', data.namespace) : ''}
                    ${data.metadata ? this.createProperty('Metadata', typeof data.metadata === 'object' ? '[Object]' : String(data.metadata)) : ''}
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
                <div class="structured-data">
                    ${keys.map(key => 
                        this.createProperty(key, typeof data[key] === 'object' ? 
                            '[Object]' : String(data[key]))
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
     * Get todo priority icon
     */
    getTodoPriorityIcon(priority) {
        const icons = {
            high: '🔴',
            medium: '🟡',
            low: '🟢'
        };
        return icons[priority] || icons.medium;
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
     * Format timestamp for display
     * @param {string|number} timestamp - Timestamp to format
     * @returns {string} Formatted time
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown time';
        
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
        } catch (e) {
            return 'Invalid time';
        }
    }

    /**
     * Extract tool name from event data
     * @param {Object} data - Event data
     * @returns {string|null} Tool name
     */
    extractToolName(data) {
        // Check various locations where tool name might be stored
        if (data.tool_name) return data.tool_name;
        if (data.tool_parameters && data.tool_parameters.tool_name) return data.tool_parameters.tool_name;
        if (data.tool_input && data.tool_input.tool_name) return data.tool_input.tool_name;
        
        // Try to infer from other fields
        if (data.tool_parameters) {
            // Common tool patterns
            if (data.tool_parameters.file_path || data.tool_parameters.notebook_path) {
                return 'FileOperation';
            }
            if (data.tool_parameters.pattern) {
                return 'Search';
            }
            if (data.tool_parameters.command) {
                return 'Bash';
            }
            if (data.tool_parameters.todos) {
                return 'TodoWrite';
            }
        }
        
        return null;
    }

    /**
     * Extract agent information from event data
     * @param {Object} data - Event data
     * @returns {string|null} Agent identifier
     */
    extractAgent(data) {
        // First check if we have enhanced inference data from dashboard
        if (data._agentName && data._agentName !== 'Unknown Agent') {
            return data._agentName;
        }
        
        // Check inference data if available
        if (data._inference && data._inference.agentName && data._inference.agentName !== 'Unknown') {
            return data._inference.agentName;
        }
        
        // Check various locations where agent info might be stored
        if (data.agent) return data.agent;
        if (data.agent_type) return data.agent_type;
        if (data.agent_name) return data.agent_name;
        
        // Check session data
        if (data.session_id && typeof data.session_id === 'string') {
            // Extract agent from session ID if it contains agent info
            const sessionParts = data.session_id.split('_');
            if (sessionParts.length > 1) {
                return sessionParts[0].toUpperCase();
            }
        }
        
        // Infer from context
        if (data.todos) return 'PM'; // TodoWrite typically from PM agent
        if (data.tool_name === 'TodoWrite') return 'PM';
        
        return null;
    }

    /**
     * Extract file name from event data
     * @param {Object} data - Event data
     * @returns {string|null} File name
     */
    extractFileName(data) {
        const filePath = this.extractFilePathFromHook(data);
        if (filePath) {
            // Extract just the filename from the full path
            const pathParts = filePath.split('/');
            return pathParts[pathParts.length - 1];
        }
        
        // Check other common file fields
        if (data.filename) return data.filename;
        if (data.file) return data.file;
        
        return null;
    }

    /**
     * Clear the module viewer
     */
    clear() {
        this.showEmptyState();
    }

    /**
     * Show tool call details (backward compatibility method)
     * @param {Object} toolCall - The tool call data
     * @param {string} toolCallKey - The tool call key
     */
    showToolCall(toolCall, toolCallKey) {
        if (!toolCall) {
            this.showEmptyState();
            return;
        }

        const toolName = toolCall.tool_name || 'Unknown Tool';
        const agentName = toolCall.agent_type || 'PM';
        const timestamp = this.formatTimestamp(toolCall.timestamp);

        // Extract information from pre and post events
        const preEvent = toolCall.pre_event;
        const postEvent = toolCall.post_event;
        
        // Get parameters from pre-event
        const parameters = preEvent?.tool_parameters || {};
        const target = preEvent ? this.extractToolTarget(toolName, parameters) : 'Unknown target';
        
        // Get execution results from post-event
        const duration = toolCall.duration_ms ? `${toolCall.duration_ms}ms` : '-';
        const success = toolCall.success !== undefined ? toolCall.success : null;
        const exitCode = toolCall.exit_code !== undefined ? toolCall.exit_code : null;
        
        // Format result summary
        let resultSummary = toolCall.result_summary || 'No summary available';
        let formattedResultSummary = '';
        
        if (typeof resultSummary === 'object' && resultSummary !== null) {
            const parts = [];
            if (resultSummary.exit_code !== undefined) {
                parts.push(`Exit Code: ${resultSummary.exit_code}`);
            }
            if (resultSummary.has_output !== undefined) {
                parts.push(`Has Output: ${resultSummary.has_output ? 'Yes' : 'No'}`);
            }
            if (resultSummary.has_error !== undefined) {
                parts.push(`Has Error: ${resultSummary.has_error ? 'Yes' : 'No'}`);
            }
            if (resultSummary.output_lines !== undefined) {
                parts.push(`Output Lines: ${resultSummary.output_lines}`);
            }
            if (resultSummary.output_preview) {
                parts.push(`Output Preview: ${resultSummary.output_preview}`);
            }
            if (resultSummary.error_preview) {
                parts.push(`Error Preview: ${resultSummary.error_preview}`);
            }
            formattedResultSummary = parts.join('\n');
        } else {
            formattedResultSummary = String(resultSummary);
        }

        // Status information
        let statusIcon = '⏳';
        let statusText = 'Running...';
        let statusClass = 'tool-running';
        
        if (postEvent) {
            if (success === true) {
                statusIcon = '✅';
                statusText = 'Success';
                statusClass = 'tool-success';
            } else if (success === false) {
                statusIcon = '❌';
                statusText = 'Failed';
                statusClass = 'tool-failure';
            } else {
                statusIcon = '⏳';
                statusText = 'Completed';
                statusClass = 'tool-completed';
            }
        }

        // Create contextual header
        const contextualHeader = `
            <div class="contextual-header">
                <h3 class="contextual-header-text">${toolName}: ${agentName} ${timestamp}</h3>
            </div>
        `;

        // Special handling for TodoWrite
        if (toolName === 'TodoWrite' && parameters.todos) {
            const todoContent = `
                <div class="todo-checklist">
                    ${parameters.todos.map(todo => {
                        const statusIcon = this.getTodoStatusIcon(todo.status);
                        const priorityIcon = this.getTodoPriorityIcon(todo.priority);
                        
                        return `
                            <div class="todo-item todo-${todo.status || 'pending'}">
                                <span class="todo-status">${statusIcon}</span>
                                <span class="todo-content">${todo.content || 'No content'}</span>
                                <span class="todo-priority priority-${todo.priority || 'medium'}">${priorityIcon}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
            
            if (this.dataContainer) {
                this.dataContainer.innerHTML = contextualHeader + todoContent;
            }
        } else {
            // For other tools, show detailed information
            const content = `
                <div class="structured-view-section">
                    <div class="tool-call-details">
                        <div class="tool-call-info ${statusClass}">
                            <div class="structured-field">
                                <strong>Tool Name:</strong> ${toolName}
                            </div>
                            <div class="structured-field">
                                <strong>Agent:</strong> ${agentName}
                            </div>
                            <div class="structured-field">
                                <strong>Status:</strong> ${statusIcon} ${statusText}
                            </div>
                            <div class="structured-field">
                                <strong>Target:</strong> ${target}
                            </div>
                            <div class="structured-field">
                                <strong>Started:</strong> ${new Date(toolCall.timestamp).toLocaleString()}
                            </div>
                            <div class="structured-field">
                                <strong>Duration:</strong> ${duration}
                            </div>
                            ${success !== null ? `
                                <div class="structured-field">
                                    <strong>Success:</strong> ${success}
                                </div>
                            ` : ''}
                            ${exitCode !== null ? `
                                <div class="structured-field">
                                    <strong>Exit Code:</strong> ${exitCode}
                                </div>
                            ` : ''}
                            ${toolCall.session_id ? `
                                <div class="structured-field">
                                    <strong>Session ID:</strong> ${toolCall.session_id}
                                </div>
                            ` : ''}
                        </div>
                        
                        ${formattedResultSummary && formattedResultSummary !== 'No summary available' ? `
                            <div class="result-section">
                                <div class="structured-view-header">
                                    <h4>📊 Result Summary</h4>
                                </div>
                                <div class="structured-data">
                                    <div class="result-summary" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.4;">
                                        ${formattedResultSummary}
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        ${Object.keys(parameters).length > 0 && toolName !== 'TodoWrite' ? `
                            <div class="parameters-section">
                                <div class="structured-view-header">
                                    <h4>⚙️ Parameters</h4>
                                </div>
                                <div class="structured-data">
                                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.4;">${JSON.stringify(parameters, null, 2)}</pre>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            
            if (this.dataContainer) {
                this.dataContainer.innerHTML = contextualHeader + content;
            }
        }

        // Show JSON data in bottom pane
        if (this.jsonContainer) {
            const toolCallData = {
                toolCall: toolCall,
                preEvent: preEvent,
                postEvent: postEvent
            };
            this.jsonContainer.innerHTML = `<pre>${JSON.stringify(toolCallData, null, 2)}</pre>`;
        }
    }

    /**
     * Show file operations details (backward compatibility method)
     * @param {Object} fileData - The file operations data
     * @param {string} filePath - The file path
     */
    showFileOperations(fileData, filePath) {
        if (!fileData || !filePath) {
            this.showEmptyState();
            return;
        }

        // Get file name from path for header
        const fileName = filePath.split('/').pop() || filePath;
        const operations = fileData.operations || [];
        const lastOp = operations[operations.length - 1];
        const headerTimestamp = lastOp ? this.formatTimestamp(lastOp.timestamp) : '';
        
        // Create contextual header
        const contextualHeader = `
            <div class="contextual-header">
                <h3 class="contextual-header-text">File: ${fileName} ${headerTimestamp}</h3>
            </div>
        `;

        const content = `
            <div class="structured-view-section">
                <div class="file-details">
                    <div class="file-path-display">
                        <strong>Full Path:</strong> ${filePath}
                    </div>
                    <div class="operations-list">
                        ${operations.map(op => `
                            <div class="operation-item">
                                <div class="operation-header">
                                    <span class="operation-icon">${this.getOperationIcon(op.operation)}</span>
                                    <span class="operation-type">${op.operation}</span>
                                    <span class="operation-timestamp">${new Date(op.timestamp).toLocaleString()}</span>
                                    ${(['edit', 'write'].includes(op.operation)) ? `
                                        <span class="git-diff-icon" 
                                              onclick="showGitDiffModal('${filePath}', '${op.timestamp}')"
                                              title="View git diff for this file operation"
                                              style="margin-left: 8px; cursor: pointer; font-size: 16px;">
                                            📋
                                        </span>
                                    ` : ''}
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

        // Show structured data in top pane
        if (this.dataContainer) {
            this.dataContainer.innerHTML = contextualHeader + content;
        }
        
        // Show JSON data in bottom pane
        if (this.jsonContainer) {
            this.jsonContainer.innerHTML = `<pre>${JSON.stringify(fileData, null, 2)}</pre>`;
        }
    }

    /**
     * Show error message (backward compatibility method)
     * @param {string} title - Error title
     * @param {string} message - Error message
     */
    showErrorMessage(title, message) {
        const content = `
            <div class="module-error">
                <div class="error-header">
                    <h3>❌ ${title}</h3>
                </div>
                <div class="error-message">
                    <p>${message}</p>
                </div>
            </div>
        `;
        
        if (this.dataContainer) {
            this.dataContainer.innerHTML = content;
        }
        
        if (this.jsonContainer) {
            this.jsonContainer.innerHTML = `
                <div class="module-empty">
                    <p>No additional data available</p>
                </div>
            `;
        }
    }

    /**
     * Show agent event details (backward compatibility method)
     * @param {Object} event - The agent event
     * @param {number} index - Event index
     */
    showAgentEvent(event, index) {
        // Use the existing showEventDetails method which handles agent events
        this.showEventDetails(event);
    }

    /**
     * Extract tool target from tool name and parameters
     * @param {string} toolName - Name of the tool
     * @param {Object} parameters - Tool parameters
     * @returns {string} - Tool target description
     */
    extractToolTarget(toolName, parameters) {
        if (!parameters) return 'Unknown target';
        
        switch (toolName) {
            case 'Write':
            case 'Read':
            case 'Edit':
            case 'MultiEdit':
                return parameters.file_path || 'Unknown file';
            case 'Bash':
                return parameters.command ? `Command: ${parameters.command.substring(0, 50)}...` : 'Unknown command';
            case 'Grep':
                return parameters.pattern ? `Pattern: ${parameters.pattern}` : 'Unknown pattern';
            case 'Glob':
                return parameters.pattern ? `Pattern: ${parameters.pattern}` : 'Unknown glob';
            case 'TodoWrite':
                return `${parameters.todos?.length || 0} todos`;
            case 'Task':
                return parameters.subagent_type || 'Subagent delegation';
            default:
                // Try to find a meaningful parameter
                if (parameters.file_path) return parameters.file_path;
                if (parameters.pattern) return `Pattern: ${parameters.pattern}`;
                if (parameters.command) return `Command: ${parameters.command.substring(0, 50)}...`;
                if (parameters.path) return parameters.path;
                return 'Unknown target';
        }
    }

    /**
     * Get operation icon for file operations
     * @param {string} operation - Operation type
     * @returns {string} - Icon for the operation
     */
    getOperationIcon(operation) {
        const icons = {
            'read': '👁️',
            'write': '✏️',
            'edit': '📝',
            'multiedit': '📝',
            'create': '🆕',
            'delete': '🗑️',
            'move': '📦',
            'copy': '📋'
        };
        return icons[operation?.toLowerCase()] || '📄';
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