/**
 * Module Viewer Component
 * Displays detailed information about selected events organized by class/type
 * Now uses UnifiedDataViewer for consistent data formatting
 */

import { UnifiedDataViewer } from './unified-data-viewer.js';

class ModuleViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.dataContainer = null;
        this.jsonContainer = null;
        this.currentEvent = null;
        this.eventsByClass = new Map();

        // Global JSON visibility state - persisted across all events
        // When true, all events show JSON expanded; when false, all collapsed
        this.globalJsonExpanded = localStorage.getItem('dashboard-json-expanded') === 'true';
        
        // Separate state for Full Event Data sections
        this.fullEventDataExpanded = localStorage.getItem('dashboard-full-event-expanded') === 'true';
        
        // Track if keyboard listener has been added to avoid duplicates
        this.keyboardListenerAdded = false;
        
        // Initialize unified data viewer
        this.unifiedViewer = new UnifiedDataViewer('module-data-content');
        
        // Sync unified viewer's JSON state with module viewer's state
        // This ensures both viewers maintain consistent JSON visibility
        this.unifiedViewer.globalJsonExpanded = this.globalJsonExpanded;
        this.unifiedViewer.fullEventDataExpanded = this.fullEventDataExpanded;
        
        // Listen for JSON state changes from unified viewer
        document.addEventListener('jsonToggleChanged', (e) => {
            this.globalJsonExpanded = e.detail.expanded;
            // Also update the unified viewer's state if it's different
            if (this.unifiedViewer.globalJsonExpanded !== e.detail.expanded) {
                this.unifiedViewer.globalJsonExpanded = e.detail.expanded;
            }
        });
        
        // Listen for Full Event Data state changes
        document.addEventListener('fullEventToggleChanged', (e) => {
            this.fullEventDataExpanded = e.detail.expanded;
            // Also update the unified viewer's state if it's different
            if (this.unifiedViewer.fullEventDataExpanded !== e.detail.expanded) {
                this.unifiedViewer.fullEventDataExpanded = e.detail.expanded;
            }
        });

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
        this.jsonContainer = null; // No longer used - JSON is handled via collapsible sections

        if (!this.dataContainer) {
            console.error('Module viewer data container not found');
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

        // JSON container no longer exists - handled via collapsible sections

        this.currentEvent = null;
    }

    /**
     * Show details for a selected event using UnifiedDataViewer
     * @param {Object} event - The selected event
     */
    showEventDetails(event) {
        this.currentEvent = event;
        
        if (!this.unifiedViewer) {
            console.warn('ModuleViewer: UnifiedDataViewer not available');
            // Fallback to legacy rendering
            this.renderStructuredData(event);
            this.renderJsonData(event);
            return;
        }
        
        // Use unified viewer to display event data
        this.unifiedViewer.display(event, 'event');
    }

    /**
     * Render structured data in the data pane with collapsible JSON section
     * @param {Object} event - The event to render
     */
    renderStructuredData(event) {
        if (!this.dataContainer) return;

        // Create contextual header
        const contextualHeader = this.createContextualHeader(event);

        // Create structured view based on event type
        const structuredView = this.createEventStructuredView(event);

        // Create collapsible JSON section
        const collapsibleJsonSection = this.createCollapsibleJsonSection(event);

        // Combine all sections in data container
        this.dataContainer.innerHTML = contextualHeader + structuredView + collapsibleJsonSection;

        // Initialize JSON toggle functionality
        this.initializeJsonToggle();
    }

    /**
     * Render JSON data in the JSON pane (legacy support - now using collapsible section)
     * @param {Object} event - The event to render
     */
    renderJsonData(event) {
        // JSON is now integrated into data container as collapsible section
        // Hide the JSON pane completely by clearing it
        // JSON container no longer exists - handled via collapsible sections
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

        // Note: Git diff functionality moved to Files tab only
        // Events tab no longer shows git diff buttons

        // Create inline tool result content if available (without separate section header)
        const toolResultContent = this.createInlineToolResultContent(data, event);

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
                    ${toolResultContent}
                </div>
            </div>
        `;
    }

    /**
     * Create inline tool result content (no separate section header)
     * @param {Object} data - Event data
     * @param {Object} event - Full event object (optional, for phase checking)
     * @returns {string} HTML content for inline tool result display
     */
    createInlineToolResultContent(data, event = null) {
        const resultSummary = data.result_summary;

        // Determine if this is a post-tool event
        // Check multiple possible locations for the event phase
        const eventPhase = event?.subtype || data.event_type || data.phase;
        const isPostTool = eventPhase === 'post_tool' || eventPhase?.includes('post');

        // Debug logging to help troubleshoot tool result display issues
        if (window.DEBUG_TOOL_RESULTS) {
            console.log('🔧 createInlineToolResultContent debug:', {
                hasResultSummary: !!resultSummary,
                eventPhase,
                isPostTool,
                eventSubtype: event?.subtype,
                dataEventType: data.event_type,
                dataPhase: data.phase,
                toolName: data.tool_name,
                resultSummaryKeys: resultSummary ? Object.keys(resultSummary) : []
            });
        }

        // Only show results if we have result data and this is a post-tool event
        // OR if we have result_summary regardless of phase (some events may not have proper phase info)
        if (!resultSummary) {
            return '';
        }

        // If we know this is a pre-tool event, don't show results
        if (eventPhase === 'pre_tool' || (eventPhase?.includes('pre') && !eventPhase?.includes('post'))) {
            return '';
        }

        let resultContent = '';

        // Add output preview if available
        if (resultSummary.has_output && resultSummary.output_preview) {
            resultContent += `
                ${this.createProperty('Output', this.truncateText(resultSummary.output_preview, 200))}
                ${resultSummary.output_lines ? this.createProperty('Output Lines', resultSummary.output_lines) : ''}
            `;
        }

        // Add error preview if available
        if (resultSummary.has_error && resultSummary.error_preview) {
            resultContent += `
                ${this.createProperty('Error', this.truncateText(resultSummary.error_preview, 200))}
            `;
        }

        // If no specific output or error, but we have other result info
        if (!resultSummary.has_output && !resultSummary.has_error && Object.keys(resultSummary).length > 3) {
            // Show other result fields
            const otherFields = Object.entries(resultSummary)
                .filter(([key, value]) => !['has_output', 'has_error', 'exit_code'].includes(key) && value !== undefined)
                .map(([key, value]) => this.createProperty(this.formatFieldName(key), String(value)))
                .join('');

            resultContent += otherFields;
        }

        return resultContent;
    }

    /**
     * Create tool result section if result data is available
     * @param {Object} data - Event data
     * @param {Object} event - Full event object (optional, for phase checking)
     * @returns {string} HTML content for tool result section
     */
    createToolResultSection(data, event = null) {
        const resultSummary = data.result_summary;

        // Determine if this is a post-tool event
        // Check multiple possible locations for the event phase
        const eventPhase = event?.subtype || data.event_type || data.phase;
        const isPostTool = eventPhase === 'post_tool' || eventPhase?.includes('post');

        // Debug logging to help troubleshoot tool result display issues
        if (window.DEBUG_TOOL_RESULTS) {
            console.log('🔧 createToolResultSection debug:', {
                hasResultSummary: !!resultSummary,
                eventPhase,
                isPostTool,
                eventSubtype: event?.subtype,
                dataEventType: data.event_type,
                dataPhase: data.phase,
                toolName: data.tool_name,
                resultSummaryKeys: resultSummary ? Object.keys(resultSummary) : []
            });
        }

        // Only show results if we have result data and this is a post-tool event
        // OR if we have result_summary regardless of phase (some events may not have proper phase info)
        if (!resultSummary) {
            return '';
        }

        // If we know this is a pre-tool event, don't show results
        if (eventPhase === 'pre_tool' || (eventPhase?.includes('pre') && !eventPhase?.includes('post'))) {
            return '';
        }

        // Determine result status and icon
        let statusIcon = '⏳';
        let statusClass = 'tool-running';
        let statusText = 'Unknown';

        if (data.success === true) {
            statusIcon = '✅';
            statusClass = 'tool-success';
            statusText = 'Success';
        } else if (data.success === false) {
            statusIcon = '❌';
            statusClass = 'tool-failure';
            statusText = 'Failed';
        } else if (data.exit_code === 0) {
            statusIcon = '✅';
            statusClass = 'tool-success';
            statusText = 'Completed';
        } else if (data.exit_code === 2) {
            statusIcon = '⚠️';
            statusClass = 'tool-blocked';
            statusText = 'Blocked';
        } else if (data.exit_code !== undefined && data.exit_code !== 0) {
            statusIcon = '❌';
            statusClass = 'tool-failure';
            statusText = 'Error';
        }

        let resultContent = '';

        // Add basic result info
        resultContent += `
            <div class="tool-result-status ${statusClass}">
                <span class="tool-result-icon">${statusIcon}</span>
                <span class="tool-result-text">${statusText}</span>
                ${data.exit_code !== undefined ? `<span class="tool-exit-code">Exit Code: ${data.exit_code}</span>` : ''}
            </div>
        `;

        // Add output preview if available
        if (resultSummary.has_output && resultSummary.output_preview) {
            resultContent += `
                <div class="tool-result-output">
                    <div class="tool-result-label">📄 Output:</div>
                    <div class="tool-result-preview">
                        <pre>${this.escapeHtml(resultSummary.output_preview)}</pre>
                    </div>
                    ${resultSummary.output_lines ? `<div class="tool-result-meta">Lines: ${resultSummary.output_lines}</div>` : ''}
                </div>
            `;
        }

        // Add error preview if available
        if (resultSummary.has_error && resultSummary.error_preview) {
            resultContent += `
                <div class="tool-result-error">
                    <div class="tool-result-label">⚠️ Error:</div>
                    <div class="tool-result-preview error-preview">
                        <pre>${this.escapeHtml(resultSummary.error_preview)}</pre>
                    </div>
                </div>
            `;
        }

        // If no specific output or error, but we have other result info
        if (!resultSummary.has_output && !resultSummary.has_error && Object.keys(resultSummary).length > 3) {
            // Show other result fields
            const otherFields = Object.entries(resultSummary)
                .filter(([key, value]) => !['has_output', 'has_error', 'exit_code'].includes(key) && value !== undefined)
                .map(([key, value]) => this.createProperty(this.formatFieldName(key), String(value)))
                .join('');

            if (otherFields) {
                resultContent += `
                    <div class="tool-result-other">
                        <div class="tool-result-label">📊 Result Details:</div>
                        <div class="structured-data">
                            ${otherFields}
                        </div>
                    </div>
                `;
            }
        }

        // Only return content if we have something to show
        if (!resultContent.trim()) {
            return '';
        }

        return `
            <div class="tool-result-section">
                <div class="contextual-header">
                    <h3 class="contextual-header-text">🔧 Tool Result</h3>
                </div>
                <div class="tool-result-content">
                    ${resultContent}
                </div>
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
     * Determines if a file operation is read-only or modifies the file
     * @param {string} operation - The operation type
     * @returns {boolean} True if operation is read-only, false if it modifies the file
     */
    isReadOnlyOperation(operation) {
        if (!operation) return true; // Default to read-only for safety

        const readOnlyOperations = ['read'];
        const editOperations = ['write', 'edit', 'multiedit', 'create', 'delete', 'move', 'copy'];

        const opLower = operation.toLowerCase();

        // Explicitly read-only operations
        if (readOnlyOperations.includes(opLower)) {
            return true;
        }

        // Explicitly edit operations
        if (editOperations.includes(opLower)) {
            return false;
        }

        // Default to read-only for unknown operations
        return true;
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
     * Create collapsible JSON section that appears below main content
     * WHY: Uses global state to maintain consistent JSON visibility across all events
     * DESIGN DECISION: Sticky toggle improves debugging workflow by maintaining JSON
     * visibility preference as user navigates through different events
     * @param {Object} event - The event to render
     * @returns {string} HTML content
     */
    createCollapsibleJsonSection(event) {
        const uniqueId = 'json-section-' + Math.random().toString(36).substr(2, 9);
        const jsonString = this.formatJSON(event);
        
        // Use global state to determine initial visibility
        const isExpanded = this.globalJsonExpanded;
        const display = isExpanded ? 'block' : 'none';
        const arrow = isExpanded ? '▲' : '▼';
        const ariaExpanded = isExpanded ? 'true' : 'false';
        
        return `
            <div class="collapsible-json-section" id="${uniqueId}">
                <div class="json-toggle-header"
                     onclick="window.moduleViewer.toggleJsonSection()"
                     role="button"
                     tabindex="0"
                     aria-expanded="${ariaExpanded}"
                     onkeydown="if(event.key==='Enter'||event.key===' '){window.moduleViewer.toggleJsonSection();event.preventDefault();}">
                    <span class="json-toggle-text">Raw JSON</span>
                    <span class="json-toggle-arrow">${arrow}</span>
                </div>
                <div class="json-content-collapsible" style="display: ${display};" aria-hidden="${!isExpanded}">
                    <div class="json-display" onclick="window.moduleViewer.copyJsonToClipboard(event)">
                        <pre>${jsonString}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Copy JSON content to clipboard
     * @param {Event} event - Click event
     */
    async copyJsonToClipboard(event) {
        // Only trigger on the copy icon area (top-right corner)
        const rect = event.currentTarget.getBoundingClientRect();
        const clickX = event.clientX - rect.left;
        const clickY = event.clientY - rect.top;

        // Check if click is in the top-right corner (copy icon area)
        if (clickX > rect.width - 50 && clickY < 30) {
            const preElement = event.currentTarget.querySelector('pre');
            if (preElement) {
                try {
                    await navigator.clipboard.writeText(preElement.textContent);
                    this.showNotification('JSON copied to clipboard', 'success');
                } catch (err) {
                    console.error('Failed to copy JSON:', err);
                    this.showNotification('Failed to copy JSON', 'error');
                }
            }
            event.stopPropagation();
        }
    }

    /**
     * Initialize JSON toggle functionality
     * WHY: Ensures newly rendered events respect the current global JSON visibility state
     */
    initializeJsonToggle() {
        // Make sure the moduleViewer is available globally for onclick handlers
        window.moduleViewer = this;

        // Apply global state to newly rendered JSON sections
        // This ensures new events respect the current global state
        if (this.globalJsonExpanded) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                this.updateAllJsonSections();
            }, 0);
        }

        // Add keyboard navigation support (only add once to avoid duplicates)
        if (!this.keyboardListenerAdded) {
            this.keyboardListenerAdded = true;
            document.addEventListener('keydown', (e) => {
                if (e.target.classList.contains('json-toggle-header')) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        this.toggleJsonSection();
                        e.preventDefault();
                    }
                }
            });
        }
    }

    /**
     * Toggle JSON section visibility globally - affects ALL events
     * WHY: Sticky toggle maintains user preference across all events for better debugging
     * DESIGN DECISION: Uses localStorage to persist preference across page refreshes
     */
    toggleJsonSection() {
        // Toggle the global state
        this.globalJsonExpanded = !this.globalJsonExpanded;
        
        // Persist the preference to localStorage
        localStorage.setItem('dashboard-json-expanded', this.globalJsonExpanded.toString());
        
        // Update ALL JSON sections on the page
        this.updateAllJsonSections();
        
        // Dispatch event to notify other components of the change
        document.dispatchEvent(new CustomEvent('jsonToggleChanged', {
            detail: { expanded: this.globalJsonExpanded }
        }));
    }

    /**
     * Update all JSON sections on the page to match global state
     * WHY: Ensures consistent JSON visibility across all displayed events
     */
    updateAllJsonSections() {
        // Find all JSON content sections and toggle headers
        const allJsonContents = document.querySelectorAll('.json-content-collapsible');
        const allArrows = document.querySelectorAll('.json-toggle-arrow');
        const allHeaders = document.querySelectorAll('.json-toggle-header');
        
        // Update each JSON section
        allJsonContents.forEach((jsonContent, index) => {
            if (this.globalJsonExpanded) {
                // Show JSON content
                jsonContent.style.display = 'block';
                jsonContent.setAttribute('aria-hidden', 'false');
                if (allArrows[index]) {
                    allArrows[index].textContent = '▲';
                }
                if (allHeaders[index]) {
                    allHeaders[index].setAttribute('aria-expanded', 'true');
                }
            } else {
                // Hide JSON content
                jsonContent.style.display = 'none';
                jsonContent.setAttribute('aria-hidden', 'true');
                if (allArrows[index]) {
                    allArrows[index].textContent = '▼';
                }
                if (allHeaders[index]) {
                    allHeaders[index].setAttribute('aria-expanded', 'false');
                }
            }
        });
        
        // If expanded and there's content, scroll the first visible one into view
        if (this.globalJsonExpanded && allJsonContents.length > 0) {
            setTimeout(() => {
                const firstVisible = allJsonContents[0];
                if (firstVisible) {
                    firstVisible.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }, 100);
        }
    }

    /**
     * Create a property display element with optional file path detection
     */
    createProperty(key, value) {
        const displayValue = this.truncateText(String(value), 300);

        // Check if this is a file path property that should be clickable
        if (this.isFilePathProperty(key, value)) {
            return `
                <div class="event-property">
                    <span class="event-property-key">${key}:</span>
                    <span class="event-property-value">
                        ${this.createClickableFilePath(value)}
                    </span>
                </div>
            `;
        }

        return `
            <div class="event-property">
                <span class="event-property-key">${key}:</span>
                <span class="event-property-value">${displayValue}</span>
            </div>
        `;
    }

    /**
     * Check if a property represents a file path that should be clickable
     * @param {string} key - Property key
     * @param {string} value - Property value
     * @returns {boolean} True if this should be a clickable file path
     */
    isFilePathProperty(key, value) {
        const filePathKeys = [
            'File Path',
            'file_path',
            'notebook_path',
            'Full Path',
            'Working Directory',
            'working_directory'
        ];

        // Check if key indicates a file path
        if (filePathKeys.some(pathKey => key.toLowerCase().includes(pathKey.toLowerCase()))) {
            // Ensure value looks like a file path (contains / or \\ and has reasonable length)
            const strValue = String(value);
            return strValue.length > 0 &&
                   (strValue.includes('/') || strValue.includes('\\')) &&
                   strValue.length < 500; // Reasonable path length limit
        }

        return false;
    }

    /**
     * Create a clickable file path element
     * @param {string} filePath - The file path to make clickable
     * @returns {string} HTML for clickable file path
     */
    createClickableFilePath(filePath) {
        const displayPath = this.truncateText(String(filePath), 300);
        const escapedPath = filePath.replace(/'/g, "\\'");

        return `
            <span class="clickable-file-path"
                  onclick="showFileViewerModal('${escapedPath}')"
                  title="Click to view file contents with syntax highlighting&#10;Path: ${filePath}">
                ${displayPath}
            </span>
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
     * Format operation details object for display
     * @param {Object} details - Details object containing operation information
     * @returns {string} Formatted HTML string
     */
    formatOperationDetails(details) {
        if (!details || typeof details !== 'object') {
            return '';
        }
        
        let formattedDetails = '';
        
        // Display the bash command if available
        if (details.parameters && details.parameters.command) {
            formattedDetails += `<br><strong>Command:</strong> <code>${this.escapeHtml(details.parameters.command)}</code>`;
        }
        
        // Display success/error status
        if (details.success !== undefined) {
            formattedDetails += `<br><strong>Status:</strong> ${details.success ? '✅ Success' : '❌ Failed'}`;
        }
        
        // Display exit code if available
        if (details.exit_code !== undefined && details.exit_code !== null) {
            formattedDetails += `<br><strong>Exit Code:</strong> ${details.exit_code}`;
        }
        
        // Display duration if available
        if (details.duration_ms !== undefined && details.duration_ms !== null) {
            const duration = details.duration_ms > 1000 
                ? `${(details.duration_ms / 1000).toFixed(2)}s` 
                : `${details.duration_ms}ms`;
            formattedDetails += `<br><strong>Duration:</strong> ${duration}`;
        }
        
        // Display error message if available
        if (details.error) {
            formattedDetails += `<br><strong>Error:</strong> ${this.escapeHtml(this.truncateText(details.error, 200))}`;
        }
        
        return formattedDetails;
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
     * Escape HTML characters to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format field name for display (convert snake_case to Title Case)
     * @param {string} fieldName - Field name to format
     * @returns {string} Formatted field name
     */
    formatFieldName(fieldName) {
        return fieldName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
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
        if (this.unifiedViewer) {
            this.unifiedViewer.clear();
        }
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

            // Create collapsible JSON section
            const toolCallData = {
                toolCall: toolCall,
                preEvent: preEvent,
                postEvent: postEvent
            };
            const collapsibleJsonSection = this.createCollapsibleJsonSection(toolCallData);

            if (this.dataContainer) {
                this.dataContainer.innerHTML = contextualHeader + todoContent + collapsibleJsonSection;
            }

            // Initialize JSON toggle functionality
            this.initializeJsonToggle();
        } else if (toolName === 'Grep' || toolName === 'Search' || (parameters && parameters.pattern && !parameters.file_path)) {
            // Special handling for search operations (Grep tool or any tool with pattern parameter)
            const searchPattern = parameters.pattern || 'No pattern specified';
            const searchPath = parameters.path || parameters.directory || '.';
            const searchType = parameters.type || parameters.glob || 'all files';
            
            // Extract search results from result_summary
            let searchResultsContent = '';
            if (toolCall.result_summary) {
                if (typeof toolCall.result_summary === 'string') {
                    searchResultsContent = toolCall.result_summary;
                } else if (toolCall.result_summary.output_preview) {
                    searchResultsContent = toolCall.result_summary.output_preview;
                } else {
                    searchResultsContent = JSON.stringify(toolCall.result_summary, null, 2);
                }
            }

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
                                <strong>Search Pattern:</strong> <code>${searchPattern}</code>
                            </div>
                            <div class="structured-field">
                                <strong>Search Path:</strong> ${searchPath}
                            </div>
                            <div class="structured-field">
                                <strong>File Type:</strong> ${searchType}
                            </div>
                            <div class="structured-field">
                                <strong>Started:</strong> ${new Date(toolCall.timestamp).toLocaleString()}
                            </div>
                            ${duration && duration !== '-' ? `
                                <div class="structured-field">
                                    <strong>Duration:</strong> ${duration}
                                </div>
                            ` : ''}
                        </div>

                        <div class="search-view-action" style="margin-top: 20px;">
                            <button class="btn-view-search" data-search-params='${JSON.stringify(parameters)}' data-search-results='${JSON.stringify(searchResultsContent).replace(/'/g, "&#39;")}' onclick="window.showSearchViewerModal(JSON.parse(this.getAttribute('data-search-params')), JSON.parse(this.getAttribute('data-search-results')))">
                                🔍 View Search Details
                            </button>
                        </div>

                        ${this.createToolResultFromToolCall(toolCall)}
                    </div>
                </div>
            `;

            // Create collapsible JSON section
            const toolCallData = {
                toolCall: toolCall,
                preEvent: preEvent,
                postEvent: postEvent
            };
            const collapsibleJsonSection = this.createCollapsibleJsonSection(toolCallData);

            if (this.dataContainer) {
                this.dataContainer.innerHTML = contextualHeader + content + collapsibleJsonSection;
            }

            // Initialize JSON toggle functionality
            this.initializeJsonToggle();
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
                            ${duration && duration !== '-' ? `
                                <div class="structured-field">
                                    <strong>Duration:</strong> ${duration}
                                </div>
                            ` : ''}
                            ${toolCall.session_id ? `
                                <div class="structured-field">
                                    <strong>Session ID:</strong> ${toolCall.session_id}
                                </div>
                            ` : ''}
                        </div>

                        ${this.createToolResultFromToolCall(toolCall)}
                    </div>
                </div>
            `;

            // Create collapsible JSON section
            const toolCallData = {
                toolCall: toolCall,
                preEvent: preEvent,
                postEvent: postEvent
            };
            const collapsibleJsonSection = this.createCollapsibleJsonSection(toolCallData);

            if (this.dataContainer) {
                this.dataContainer.innerHTML = contextualHeader + content + collapsibleJsonSection;
            }

            // Initialize JSON toggle functionality
            this.initializeJsonToggle();
        }

        // Hide JSON pane since data is integrated above
        // JSON container no longer exists - handled via collapsible sections
    }

    /**
     * Show file operations using UnifiedDataViewer for consistency
     * @param {Object} fileData - The file operations data
     * @param {string} filePath - The file path
     */
    showFileOperations(fileData, filePath) {
        if (!fileData || !filePath) {
            this.showEmptyState();
            return;
        }

        // Initialize UnifiedDataViewer if not already available
        if (!this.unifiedViewer) {
            this.unifiedViewer = new UnifiedDataViewer('module-data-content');
        }

        // Convert file data to standardized format
        const standardizedFileData = {
            file_path: filePath,
            operations: fileData.operations || [],
            lastOperation: fileData.lastOperation,
            ...fileData // Preserve any additional data
        };

        // Use UnifiedDataViewer for consistent display
        this.unifiedViewer.display(standardizedFileData, 'file_operation');

        // Update module header for consistency
        const moduleHeader = document.querySelector('.module-data-header h5');
        if (moduleHeader) {
            const fileName = filePath.split('/').pop() || filePath;
            moduleHeader.textContent = `📄 File: ${fileName}`;
        }

        // Check git tracking status and show track control if needed
        this.checkAndShowTrackControl(filePath);
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

        // Create collapsible JSON section for error data
        const errorData = { title, message };
        const collapsibleJsonSection = this.createCollapsibleJsonSection(errorData);

        if (this.dataContainer) {
            this.dataContainer.innerHTML = content + collapsibleJsonSection;
        }

        // Initialize JSON toggle functionality
        this.initializeJsonToggle();

        // JSON container no longer exists - handled via collapsible sections
    }

    /**
     * Show agent event details (backward compatibility method)
     * @param {Object} event - The agent event
     * @param {number} index - Event index
     */
    showAgentEvent(event, index) {
        // Show comprehensive agent-specific data instead of just single event
        this.showAgentSpecificDetails(event, index);
    }

    /**
     * Show comprehensive agent-specific details including prompt, todos, and tools
     * @param {Object} event - The selected agent event
     * @param {number} index - Event index
     */
    showAgentSpecificDetails(event, index) {
        if (!event) {
            this.showEmptyState();
            return;
        }

        // Get agent inference to determine which agent this is
        const agentInference = window.dashboard?.agentInference;
        const eventViewer = window.dashboard?.eventViewer;

        if (!agentInference || !eventViewer) {
            console.warn('AgentInference or EventViewer not available, falling back to single event view');
            this.showEventDetails(event);
            return;
        }

        const inference = agentInference.getInferredAgentForEvent(event);
        const agentName = inference?.agentName || this.extractAgent(event) || 'Unknown';

        // Get all events from this agent
        const allEvents = eventViewer.events || [];
        const agentEvents = this.getAgentSpecificEvents(allEvents, agentName, agentInference);

        console.log(`Showing details for agent: ${agentName}, found ${agentEvents.length} related events`);

        // Extract agent-specific data
        const agentData = this.extractAgentSpecificData(agentName, agentEvents);

        // Render agent-specific view
        this.renderAgentSpecificView(agentName, agentData, event);
    }

    /**
     * Get all events related to a specific agent
     * @param {Array} allEvents - All events
     * @param {string} agentName - Name of the agent to filter for
     * @param {Object} agentInference - Agent inference system
     * @returns {Array} - Events related to this agent
     */
    getAgentSpecificEvents(allEvents, agentName, agentInference) {
        return allEvents.filter(event => {
            // Use agent inference to determine if this event belongs to the agent
            const inference = agentInference.getInferredAgentForEvent(event);
            const eventAgentName = inference?.agentName || this.extractAgent(event) || 'Unknown';

            // Match agent names (case insensitive)
            return eventAgentName.toLowerCase() === agentName.toLowerCase();
        });
    }

    /**
     * Extract agent-specific data from events
     * @param {string} agentName - Name of the agent
     * @param {Array} agentEvents - Events from this agent
     * @returns {Object} - Extracted agent data
     */
    extractAgentSpecificData(agentName, agentEvents) {
        const data = {
            agentName: agentName,
            totalEvents: agentEvents.length,
            prompt: null,
            todos: [],
            toolsCalled: [],
            sessions: new Set(),
            firstSeen: null,
            lastSeen: null,
            eventTypes: new Set()
        };

        agentEvents.forEach(event => {
            const eventData = event.data || {};
            const timestamp = new Date(event.timestamp);

            // Track timing
            if (!data.firstSeen || timestamp < data.firstSeen) {
                data.firstSeen = timestamp;
            }
            if (!data.lastSeen || timestamp > data.lastSeen) {
                data.lastSeen = timestamp;
            }

            // Track sessions
            if (event.session_id || eventData.session_id) {
                data.sessions.add(event.session_id || eventData.session_id);
            }

            // Track event types
            const eventType = event.hook_event_name || event.type || 'unknown';
            data.eventTypes.add(eventType);

            // Extract prompt from Task delegation events
            if (event.type === 'hook' && eventData.tool_name === 'Task' && eventData.tool_parameters) {
                const taskParams = eventData.tool_parameters;
                if (taskParams.prompt && !data.prompt) {
                    data.prompt = taskParams.prompt;
                }
                if (taskParams.description && !data.description) {
                    data.description = taskParams.description;
                }
                if (taskParams.subagent_type === agentName && taskParams.prompt) {
                    // Prefer prompts that match the specific agent
                    data.prompt = taskParams.prompt;
                }
            }

            // Also check for agent-specific prompts in other event types
            if (eventData.prompt && (eventData.agent_type === agentName || eventData.subagent_type === agentName)) {
                data.prompt = eventData.prompt;
            }

            // Extract todos from TodoWrite events
            if (event.type === 'todo' || (event.type === 'hook' && eventData.tool_name === 'TodoWrite')) {
                const todos = eventData.todos || eventData.tool_parameters?.todos;
                if (todos && Array.isArray(todos)) {
                    // Merge todos, keeping the most recent status for each
                    todos.forEach(todo => {
                        const existingIndex = data.todos.findIndex(t => t.id === todo.id || t.content === todo.content);
                        if (existingIndex >= 0) {
                            // Update existing todo with newer data
                            data.todos[existingIndex] = { ...data.todos[existingIndex], ...todo, timestamp };
                        } else {
                            // Add new todo
                            data.todos.push({ ...todo, timestamp });
                        }
                    });
                }
            }

            // Extract tool calls - collect pre and post events separately first
            if (event.type === 'hook' && eventData.tool_name) {
                const phase = event.subtype || eventData.event_type;
                const toolCallId = this.generateToolCallId(eventData.tool_name, eventData.tool_parameters, timestamp);

                if (phase === 'pre_tool') {
                    // Store pre-tool event data
                    if (!data._preToolEvents) data._preToolEvents = new Map();
                    data._preToolEvents.set(toolCallId, {
                        toolName: eventData.tool_name,
                        timestamp: timestamp,
                        target: this.extractToolTarget(eventData.tool_name, eventData.tool_parameters, null),
                        parameters: eventData.tool_parameters
                    });
                } else if (phase === 'post_tool') {
                    // Store post-tool event data
                    if (!data._postToolEvents) data._postToolEvents = new Map();
                    data._postToolEvents.set(toolCallId, {
                        toolName: eventData.tool_name,
                        timestamp: timestamp,
                        success: eventData.success,
                        duration: eventData.duration_ms,
                        resultSummary: eventData.result_summary,
                        exitCode: eventData.exit_code
                    });
                }
            }
        });

        // Sort todos by timestamp (most recent first)
        data.todos.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

        // Consolidate pre and post tool events into single tool calls
        data.toolsCalled = this.consolidateToolCalls(data._preToolEvents, data._postToolEvents);

        // Clean up temporary data
        delete data._preToolEvents;
        delete data._postToolEvents;

        // Sort tools by timestamp (most recent first)
        data.toolsCalled.sort((a, b) => b.timestamp - a.timestamp);

        return data;
    }

    /**
     * Generate a unique ID for a tool call to match pre and post events
     * @param {string} toolName - Name of the tool
     * @param {Object} parameters - Tool parameters
     * @param {Date} timestamp - Timestamp of the event
     * @returns {string} - Unique tool call ID
     */
    generateToolCallId(toolName, parameters, timestamp) {
        // Create a unique identifier based on tool name, key parameters, and approximate timestamp
        // Use a wider time window to account for timing differences between pre/post events
        const timeWindow = Math.floor(timestamp.getTime() / 5000); // Group by 5-second windows

        // Include key parameters that uniquely identify a tool call
        let paramKey = '';
        if (parameters) {
            // Include important parameters that distinguish tool calls
            const keyParams = [];
            if (parameters.file_path) keyParams.push(parameters.file_path);
            if (parameters.command) keyParams.push(parameters.command.substring(0, 50));
            if (parameters.pattern) keyParams.push(parameters.pattern);
            if (parameters.subagent_type) keyParams.push(parameters.subagent_type);
            if (parameters.notebook_path) keyParams.push(parameters.notebook_path);
            if (parameters.url) keyParams.push(parameters.url);
            if (parameters.prompt) keyParams.push(parameters.prompt.substring(0, 30));

            paramKey = keyParams.join('|');
        }

        // If no specific parameters, use just tool name and time window
        if (!paramKey) {
            paramKey = 'default';
        }

        return `${toolName}:${timeWindow}:${paramKey}`;
    }

    /**
     * Consolidate pre and post tool events into single consolidated tool calls
     * @param {Map} preToolEvents - Map of pre-tool events by tool call ID
     * @param {Map} postToolEvents - Map of post-tool events by tool call ID
     * @returns {Array} - Array of consolidated tool calls
     */
    consolidateToolCalls(preToolEvents, postToolEvents) {
        const consolidatedCalls = [];
        const processedIds = new Set();

        if (!preToolEvents) preToolEvents = new Map();
        if (!postToolEvents) postToolEvents = new Map();

        // Process all pre-tool events first
        for (const [toolCallId, preEvent] of preToolEvents) {
            if (processedIds.has(toolCallId)) continue;

            const postEvent = postToolEvents.get(toolCallId);

            // Create consolidated tool call
            const consolidatedCall = {
                toolName: preEvent.toolName,
                timestamp: preEvent.timestamp, // Use pre-tool timestamp as the start time
                target: preEvent.target,
                parameters: preEvent.parameters,
                status: this.determineToolCallStatus(preEvent, postEvent),
                statusIcon: this.getToolCallStatusIcon(preEvent, postEvent),
                phase: postEvent ? 'completed' : 'running'
            };

            // Add post-event data if available
            if (postEvent) {
                consolidatedCall.success = postEvent.success;
                consolidatedCall.duration = postEvent.duration;
                consolidatedCall.resultSummary = postEvent.resultSummary;
                consolidatedCall.exitCode = postEvent.exitCode;
                consolidatedCall.completedAt = postEvent.timestamp;
            }

            consolidatedCalls.push(consolidatedCall);
            processedIds.add(toolCallId);
        }

        // Process any post-tool events that don't have matching pre-tool events (edge case)
        for (const [toolCallId, postEvent] of postToolEvents) {
            if (processedIds.has(toolCallId)) continue;

            // This is a post-tool event without a corresponding pre-tool event
            const consolidatedCall = {
                toolName: postEvent.toolName,
                timestamp: postEvent.timestamp,
                target: 'Unknown target', // We don't have pre-event data
                parameters: null,
                status: this.determineToolCallStatus(null, postEvent),
                statusIcon: this.getToolCallStatusIcon(null, postEvent),
                phase: 'completed',
                success: postEvent.success,
                duration: postEvent.duration,
                resultSummary: postEvent.resultSummary,
                exitCode: postEvent.exitCode,
                completedAt: postEvent.timestamp
            };

            consolidatedCalls.push(consolidatedCall);
            processedIds.add(toolCallId);
        }

        return consolidatedCalls;
    }

    /**
     * Determine the status of a tool call based on pre and post events
     * @param {Object} preEvent - Pre-tool event data
     * @param {Object} postEvent - Post-tool event data
     * @returns {string} - Status text
     */
    determineToolCallStatus(preEvent, postEvent) {
        if (!postEvent) {
            return 'Running...';
        }

        if (postEvent.success === true) {
            return 'Success';
        } else if (postEvent.success === false) {
            return 'Failed';
        } else if (postEvent.exitCode === 0) {
            return 'Completed';
        } else if (postEvent.exitCode === 2) {
            return 'Blocked';
        } else if (postEvent.exitCode !== undefined && postEvent.exitCode !== 0) {
            return 'Error';
        }

        return 'Completed';
    }

    /**
     * Get the status icon for a tool call
     * @param {Object} preEvent - Pre-tool event data
     * @param {Object} postEvent - Post-tool event data
     * @returns {string} - Status icon
     */
    getToolCallStatusIcon(preEvent, postEvent) {
        if (!postEvent) {
            return '⏳'; // Still running
        }

        if (postEvent.success === true) {
            return '✅'; // Success
        } else if (postEvent.success === false) {
            return '❌'; // Failed
        } else if (postEvent.exitCode === 0) {
            return '✅'; // Completed successfully
        } else if (postEvent.exitCode === 2) {
            return '⚠️'; // Blocked
        } else if (postEvent.exitCode !== undefined && postEvent.exitCode !== 0) {
            return '❌'; // Error
        }

        return '✅'; // Default to success for completed calls
    }

    /**
     * Estimate token count for text using a simple approximation
     * @param {string} text - Text to estimate tokens for
     * @returns {number} - Estimated token count
     */
    estimateTokenCount(text) {
        if (!text || typeof text !== 'string') return 0;

        // Simple token estimation: words * 1.3 (accounts for subwords)
        // Alternative: characters / 4 (common rule of thumb)
        const wordCount = text.trim().split(/\s+/).length;
        const charBasedEstimate = Math.ceil(text.length / 4);

        // Use the higher of the two estimates for safety
        return Math.max(wordCount * 1.3, charBasedEstimate);
    }

    /**
     * Trim excessive whitespace from text while preserving structure
     * @param {string} text - Text to trim
     * @returns {string} - Trimmed text
     */
    trimPromptWhitespace(text) {
        if (!text || typeof text !== 'string') return '';

        // Remove leading/trailing whitespace from the entire text
        text = text.trim();

        // Reduce multiple consecutive newlines to maximum of 2
        text = text.replace(/\n\s*\n\s*\n+/g, '\n\n');

        // Trim whitespace from each line while preserving intentional indentation
        text = text.split('\n').map(line => {
            // Only trim trailing whitespace, preserve leading whitespace for structure
            return line.replace(/\s+$/, '');
        }).join('\n');

        return text;
    }

    /**
     * Render agent-specific view with comprehensive data
     * @param {string} agentName - Name of the agent
     * @param {Object} agentData - Extracted agent data
     * @param {Object} originalEvent - The original clicked event
     */
    renderAgentSpecificView(agentName, agentData, originalEvent) {
        // Create contextual header
        const timestamp = this.formatTimestamp(originalEvent.timestamp);
        const contextualHeader = `
            <div class="contextual-header">
                <h3 class="contextual-header-text">🤖 ${agentName} Agent Details ${timestamp}</h3>
            </div>
        `;

        // Build comprehensive agent view
        let content = `
            <div class="agent-overview-section">
                <div class="structured-data">
                    ${this.createProperty('Agent Name', agentName)}
                    ${this.createProperty('Total Events', agentData.totalEvents)}
                    ${this.createProperty('Active Sessions', agentData.sessions.size)}
                    ${this.createProperty('Event Types', Array.from(agentData.eventTypes).join(', '))}
                    ${agentData.firstSeen ? this.createProperty('First Seen', agentData.firstSeen.toLocaleString()) : ''}
                    ${agentData.lastSeen ? this.createProperty('Last Seen', agentData.lastSeen.toLocaleString()) : ''}
                </div>
            </div>
        `;

        // Add prompt section if available
        if (agentData.prompt) {
            const trimmedPrompt = this.trimPromptWhitespace(agentData.prompt);
            const tokenCount = Math.round(this.estimateTokenCount(trimmedPrompt));
            const wordCount = trimmedPrompt.trim().split(/\s+/).length;

            content += `
                <div class="agent-prompt-section">
                    <div class="contextual-header">
                        <h3 class="contextual-header-text">📝 Agent Task Prompt</h3>
                        <div class="prompt-stats" style="font-size: 11px; color: #64748b; margin-top: 4px;">
                            ~${tokenCount} tokens • ${wordCount} words • ${trimmedPrompt.length} characters
                        </div>
                    </div>
                    <div class="structured-data">
                        <div class="agent-prompt" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.4; border: 1px solid #e2e8f0;">
                            ${this.escapeHtml(trimmedPrompt)}
                        </div>
                    </div>
                </div>
            `;
        }

        // Add todos section if available
        if (agentData.todos.length > 0) {
            content += `
                <div class="agent-todos-section">
                    <div class="contextual-header">
                        <h3 class="contextual-header-text">✅ Agent Todo List (${agentData.todos.length} items)</h3>
                    </div>
                    <div class="todo-checklist">
                        ${agentData.todos.map(todo => `
                            <div class="todo-item todo-${todo.status || 'pending'}">
                                <span class="todo-status">${this.getTodoStatusIcon(todo.status)}</span>
                                <span class="todo-content">${todo.content || 'No content'}</span>
                                <span class="todo-priority priority-${todo.priority || 'medium'}">${this.getTodoPriorityIcon(todo.priority)}</span>
                                ${todo.timestamp ? `<span class="todo-timestamp">${new Date(todo.timestamp).toLocaleTimeString()}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Add tools section if available
        if (agentData.toolsCalled.length > 0) {
            content += `
                <div class="agent-tools-section">
                    <div class="contextual-header">
                        <h3 class="contextual-header-text">🔧 Tools Called by Agent (${agentData.toolsCalled.length} calls)</h3>
                    </div>
                    <div class="tools-list">
                        ${agentData.toolsCalled.map(tool => {
                            // Determine CSS class for status
                            let statusClass = '';
                            if (tool.statusIcon === '✅') statusClass = 'status-success';
                            else if (tool.statusIcon === '❌') statusClass = 'status-failed';
                            else if (tool.statusIcon === '⚠️') statusClass = 'status-blocked';
                            else if (tool.statusIcon === '⏳') statusClass = 'status-running';

                            return `
                                <div class="tool-call-item">
                                    <div class="tool-call-header">
                                        <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                                            <span class="tool-name">🔧 ${tool.toolName}</span>
                                            <span class="tool-agent">${agentName}</span>
                                            <span class="tool-status-indicator ${statusClass}">${tool.statusIcon} ${tool.status}</span>
                                        </div>
                                        <span class="tool-timestamp" style="margin-left: auto;">${tool.timestamp.toLocaleTimeString()}</span>
                                    </div>
                                    <div class="tool-call-details">
                                        ${tool.target ? `<span class="tool-target">Target: ${tool.target}</span>` : ''}
                                        ${tool.duration ? `<span class="tool-duration">Duration: ${tool.duration}ms</span>` : ''}
                                        ${tool.completedAt && tool.completedAt !== tool.timestamp ? `<span class="tool-completed">Completed: ${tool.completedAt.toLocaleTimeString()}</span>` : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        // Create collapsible JSON section for agent data
        const agentJsonData = {
            agentName: agentName,
            agentData: agentData,
            originalEvent: originalEvent
        };
        const collapsibleJsonSection = this.createCollapsibleJsonSection(agentJsonData);

        // Show structured data with JSON section in data pane
        if (this.dataContainer) {
            this.dataContainer.innerHTML = contextualHeader + content + collapsibleJsonSection;
        }

        // Initialize JSON toggle functionality
        this.initializeJsonToggle();

        // Hide JSON pane since data is integrated above
        // JSON container no longer exists - handled via collapsible sections
    }

    /**
     * Create tool result section for backward compatibility with showToolCall method
     * @param {Object} toolCall - Tool call data
     * @returns {string} HTML content for tool result section
     */
    createToolResultFromToolCall(toolCall) {
        // Check if we have result data
        if (!toolCall.result_summary) {
            return '';
        }

        // Convert toolCall data to match the format expected by createInlineToolResultContent
        const mockData = {
            event_type: 'post_tool',
            result_summary: toolCall.result_summary,
            success: toolCall.success,
            exit_code: toolCall.exit_code
        };

        // Create a mock event object with proper subtype
        const mockEvent = {
            subtype: 'post_tool'
        };

        // Get inline result content
        const inlineContent = this.createInlineToolResultContent(mockData, mockEvent);

        // If we have content, wrap it in a simple section
        if (inlineContent.trim()) {
            return `
                <div class="tool-result-inline">
                    <div class="structured-data">
                        ${inlineContent}
                    </div>
                </div>
            `;
        }

        return '';
    }

    /**
     * Extract tool target from tool name and parameters
     * @param {string} toolName - Name of the tool
     * @param {Object} parameters - Tool parameters
     * @param {Object} altParameters - Alternative parameters
     * @returns {string} - Tool target description
     */
    extractToolTarget(toolName, parameters, altParameters) {
        const params = parameters || altParameters || {};

        switch (toolName?.toLowerCase()) {
            case 'write':
            case 'read':
            case 'edit':
            case 'multiedit':
                return params.file_path || 'Unknown file';
            case 'bash':
                return params.command ? `${params.command.substring(0, 50)}${params.command.length > 50 ? '...' : ''}` : 'Unknown command';
            case 'grep':
                return params.pattern ? `Pattern: ${params.pattern}` : 'Unknown pattern';
            case 'glob':
                return params.pattern ? `Pattern: ${params.pattern}` : 'Unknown glob';
            case 'todowrite':
                return `${params.todos?.length || 0} todos`;
            case 'task':
                return params.subagent_type || params.agent_type || 'Subagent delegation';
            default:
                // Try to find a meaningful parameter
                if (params.file_path) return params.file_path;
                if (params.pattern) return `Pattern: ${params.pattern}`;
                if (params.command) return `Command: ${params.command.substring(0, 30)}...`;
                if (params.path) return params.path;
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

    /**
     * Check git tracking status and show track control if needed
     * @param {string} filePath - Path to the file to check
     */
    async checkAndShowTrackControl(filePath) {
        if (!filePath) return;

        try {
            // Get the Socket.IO client
            const socket = window.socket || window.dashboard?.socketClient?.socket;
            if (!socket) {
                console.warn('No socket connection available for git tracking check');
                return;
            }

            // Get working directory from dashboard with proper fallback
            let workingDir = window.dashboard?.currentWorkingDir;

            // Don't use 'Unknown' as a working directory
            if (!workingDir || workingDir === 'Unknown' || workingDir.trim() === '') {
                // Try to get from footer element
                const footerDir = document.getElementById('footer-working-dir');
                if (footerDir?.textContent?.trim() && footerDir.textContent.trim() !== 'Unknown') {
                    workingDir = footerDir.textContent.trim();
                } else {
                    // Final fallback to current directory
                    workingDir = '.';
                }
                console.log('[MODULE-VIEWER-DEBUG] Working directory fallback used:', workingDir);
            }

            // Set up one-time listener for tracking status response
            const responsePromise = new Promise((resolve, reject) => {
                const responseHandler = (data) => {
                    if (data.file_path === filePath) {
                        socket.off('file_tracked_response', responseHandler);
                        resolve(data);
                    }
                };

                socket.on('file_tracked_response', responseHandler);

                // Timeout after 5 seconds
                setTimeout(() => {
                    socket.off('file_tracked_response', responseHandler);
                    reject(new Error('Request timeout'));
                }, 5000);
            });

            // Send tracking status request
            socket.emit('check_file_tracked', {
                file_path: filePath,
                working_dir: workingDir
            });

            // Wait for response
            const result = await responsePromise;
            this.displayTrackingStatus(filePath, result);

        } catch (error) {
            console.error('Error checking file tracking status:', error);
            this.displayTrackingStatus(filePath, {
                success: false,
                error: error.message,
                file_path: filePath
            });
        }
    }

    /**
     * Display tracking status and show track control if needed
     * @param {string} filePath - Path to the file
     * @param {Object} result - Result from tracking status check
     */
    displayTrackingStatus(filePath, result) {
        const statusElementId = `git-track-status-${filePath.replace(/[^a-zA-Z0-9]/g, '-')}`;
        const statusElement = document.getElementById(statusElementId);

        if (!statusElement) return;

        if (result.success && result.is_tracked === false) {
            // File is not tracked - show track button
            statusElement.innerHTML = `
                <div class="untracked-file-notice">
                    <span class="untracked-icon">⚠️</span>
                    <span class="untracked-text">This file is not tracked by git</span>
                    <button class="track-file-button"
                            onclick="window.moduleViewer.trackFile('${filePath}')"
                            title="Add this file to git tracking">
                        <span class="git-icon">📁</span> Track File
                    </button>
                </div>
            `;
        } else if (result.success && result.is_tracked === true) {
            // File is tracked - show status
            statusElement.innerHTML = `
                <div class="tracked-file-notice">
                    <span class="tracked-icon">✅</span>
                    <span class="tracked-text">This file is tracked by git</span>
                </div>
            `;
        } else if (!result.success) {
            // Error checking status
            statusElement.innerHTML = `
                <div class="tracking-error-notice">
                    <span class="error-icon">❌</span>
                    <span class="error-text">Could not check git status: ${result.error || 'Unknown error'}</span>
                </div>
            `;
        }
    }

    /**
     * Track a file using git add
     * @param {string} filePath - Path to the file to track
     */
    async trackFile(filePath) {
        if (!filePath) return;

        try {
            // Get the Socket.IO client
            const socket = window.socket || window.dashboard?.socketClient?.socket;
            if (!socket) {
                console.warn('No socket connection available for git add');
                return;
            }

            // Get working directory from dashboard with proper fallback
            let workingDir = window.dashboard?.currentWorkingDir;

            // Don't use 'Unknown' as a working directory
            if (!workingDir || workingDir === 'Unknown' || workingDir.trim() === '') {
                // Try to get from footer element
                const footerDir = document.getElementById('footer-working-dir');
                if (footerDir?.textContent?.trim() && footerDir.textContent.trim() !== 'Unknown') {
                    workingDir = footerDir.textContent.trim();
                } else {
                    // Final fallback to current directory
                    workingDir = '.';
                }
                console.log('[MODULE-VIEWER-DEBUG] Working directory fallback used:', workingDir);
            }

            // Update button to show loading state
            const statusElementId = `git-track-status-${filePath.replace(/[^a-zA-Z0-9]/g, '-')}`;
            const statusElement = document.getElementById(statusElementId);

            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="tracking-file-notice">
                        <span class="loading-icon">⏳</span>
                        <span class="loading-text">Adding file to git tracking...</span>
                    </div>
                `;
            }

            // Set up one-time listener for git add response
            const responsePromise = new Promise((resolve, reject) => {
                const responseHandler = (data) => {
                    if (data.file_path === filePath) {
                        socket.off('git_add_response', responseHandler);
                        resolve(data);
                    }
                };

                socket.on('git_add_response', responseHandler);

                // Timeout after 10 seconds
                setTimeout(() => {
                    socket.off('git_add_response', responseHandler);
                    reject(new Error('Request timeout'));
                }, 10000);
            });

            // Send git add request
            socket.emit('git_add_file', {
                file_path: filePath,
                working_dir: workingDir
            });

            console.log('📁 Git add request sent:', {
                filePath,
                workingDir
            });

            // Wait for response
            const result = await responsePromise;
            console.log('📦 Git add result:', result);

            // Update UI based on result
            if (result.success) {
                if (statusElement) {
                    statusElement.innerHTML = `
                        <div class="tracked-file-notice">
                            <span class="tracked-icon">✅</span>
                            <span class="tracked-text">File successfully added to git tracking</span>
                        </div>
                    `;
                }

                // Show success notification
                this.showNotification('File tracked successfully', 'success');
            } else {
                if (statusElement) {
                    statusElement.innerHTML = `
                        <div class="tracking-error-notice">
                            <span class="error-icon">❌</span>
                            <span class="error-text">Failed to track file: ${result.error || 'Unknown error'}</span>
                            <button class="track-file-button"
                                    onclick="window.moduleViewer.trackFile('${filePath}')"
                                    title="Try again">
                                <span class="git-icon">📁</span> Retry
                            </button>
                        </div>
                    `;
                }

                // Show error notification
                this.showNotification(`Failed to track file: ${result.error}`, 'error');
            }

        } catch (error) {
            console.error('❌ Failed to track file:', error);

            // Update UI to show error
            const statusElementId = `git-track-status-${filePath.replace(/[^a-zA-Z0-9]/g, '-')}`;
            const statusElement = document.getElementById(statusElementId);

            if (statusElement) {
                statusElement.innerHTML = `
                    <div class="tracking-error-notice">
                        <span class="error-icon">❌</span>
                        <span class="error-text">Error: ${error.message}</span>
                        <button class="track-file-button"
                                onclick="window.moduleViewer.trackFile('${filePath}')"
                                title="Try again">
                            <span class="git-icon">📁</span> Retry
                        </button>
                    </div>
                `;
            }

            // Show error notification
            this.showNotification(`Error tracking file: ${error.message}`, 'error');
        }
    }


    /**
     * Show notification to user
     * @param {string} message - Message to show
     * @param {string} type - Type of notification (success, error, info)
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
            <span class="notification-message">${message}</span>
        `;

        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
            color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
            border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
            border-radius: 6px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
            z-index: 2000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: flex;
            align-items: center;
            gap: 8px;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        `;

        // Add animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);

        // Add to page
        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                if (style.parentNode) {
                    style.parentNode.removeChild(style);
                }
            }, 300);
        }, 5000);
    }

    /**
     * Show agent instance details for PM delegations
     * @param {Object} instance - Agent instance from PM delegation
     */
    showAgentInstance(instance) {
        if (!instance) {
            this.showEmptyState();
            return;
        }

        // Create a synthetic event object to work with existing showAgentSpecificDetails method
        const syntheticEvent = {
            type: 'pm_delegation',
            subtype: instance.agentName,
            agent_type: instance.agentName,
            timestamp: instance.timestamp,
            session_id: instance.sessionId,
            metadata: {
                delegation_type: 'explicit',
                event_count: instance.agentEvents.length,
                pm_call: instance.pmCall || null,
                agent_events: instance.agentEvents
            }
        };

        console.log('Showing PM delegation details:', instance);
        this.showAgentSpecificDetails(syntheticEvent, 0);
    }

    /**
     * Show implied agent details for agents without explicit PM delegation
     * @param {Object} impliedInstance - Implied agent instance
     */
    showImpliedAgent(impliedInstance) {
        if (!impliedInstance) {
            this.showEmptyState();
            return;
        }

        // Create a synthetic event object to work with existing showAgentSpecificDetails method
        const syntheticEvent = {
            type: 'implied_delegation',
            subtype: impliedInstance.agentName,
            agent_type: impliedInstance.agentName,
            timestamp: impliedInstance.timestamp,
            session_id: impliedInstance.sessionId,
            metadata: {
                delegation_type: 'implied',
                event_count: impliedInstance.eventCount,
                pm_call: null,
                note: 'No explicit PM call found - inferred from agent activity'
            }
        };

        console.log('Showing implied agent details:', impliedInstance);
        this.showAgentSpecificDetails(syntheticEvent, 0);
    }
}

// Export for global use
// ES6 Module export
export { ModuleViewer };
export default ModuleViewer;

// Backward compatibility - keep window export for non-module usage
window.ModuleViewer = ModuleViewer;

// Debug helper function for troubleshooting tool result display
window.enableToolResultDebugging = function() {
    window.DEBUG_TOOL_RESULTS = true;
    console.log('🔧 Tool result debugging enabled. Click on tool events to see debug info.');
};

window.disableToolResultDebugging = function() {
    window.DEBUG_TOOL_RESULTS = false;
    console.log('🔧 Tool result debugging disabled.');
};
