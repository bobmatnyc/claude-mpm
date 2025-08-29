/**
 * Unified Data Viewer Component
 * 
 * Consolidates all data formatting and display logic from event-driven tabs
 * (Activity, Events, Agents) into a single, reusable component.
 * 
 * WHY: Eliminates code duplication across multiple components and provides
 * consistent data display formatting throughout the dashboard.
 * 
 * DESIGN DECISION: Auto-detects data type and applies appropriate formatting,
 * while allowing manual type specification for edge cases.
 */

class UnifiedDataViewer {
    constructor(containerId = 'module-data-content') {
        this.container = document.getElementById(containerId);
        this.currentData = null;
        this.currentType = null;
    }

    /**
     * Main display method - auto-detects type and renders data
     * @param {Object|Array} data - Data to display
     * @param {string|null} type - Optional type override
     */
    display(data, type = null) {
        if (!this.container) {
            console.warn('UnifiedDataViewer: Container not found');
            return;
        }

        // Store current data for reference
        this.currentData = data;
        this.currentType = type;

        // Auto-detect type if not provided
        if (!type) {
            type = this.detectType(data);
        }

        // Clear container
        this.container.innerHTML = '';

        // Display based on type
        switch(type) {
            case 'event':
                this.displayEvent(data);
                break;
            case 'agent':
                this.displayAgent(data);
                break;
            case 'tool':
                this.displayTool(data);
                break;
            case 'todo':
                this.displayTodo(data);
                break;
            case 'instruction':
                this.displayInstruction(data);
                break;
            case 'session':
                this.displaySession(data);
                break;
            case 'file_operation':
                this.displayFileOperation(data);
                break;
            case 'hook':
                this.displayHook(data);
                break;
            default:
                this.displayGeneric(data);
        }
    }

    /**
     * Auto-detect data type based on object properties
     * @param {Object} data - Data to analyze
     * @returns {string} Detected type
     */
    detectType(data) {
        if (!data || typeof data !== 'object') return 'generic';

        // Event detection
        if (data.hook_event_name || data.event_type || (data.type && data.timestamp)) {
            return 'event';
        }

        // Agent detection  
        if (data.agent_name || data.agentName || 
            (data.name && (data.status === 'active' || data.status === 'completed'))) {
            return 'agent';
        }

        // Tool detection - PRIORITY: Check if it's a tool first
        // This includes TodoWrite tools which should always be displayed as tools, not todos
        if (data.tool_name || data.name === 'TodoWrite' || data.name === 'Read' || 
            data.tool_parameters || (data.params && data.icon) || 
            (data.name && data.type === 'tool')) {
            return 'tool';
        }

        // Todo detection - Only for standalone todo lists, not tool todos
        if (data.todos && !data.name && !data.params) {
            return 'todo';
        }

        // Single todo item detection
        if (data.content && data.activeForm && data.status && !data.name && !data.params) {
            return 'todo';
        }

        // Instruction detection
        if (data.text && data.preview && data.type === 'user_instruction') {
            return 'instruction';
        }

        // Session detection
        if (data.session_id && (data.startTime || data.lastActivity)) {
            return 'session';
        }

        // File operation detection
        if (data.file_path && (data.operations || data.operation)) {
            return 'file_operation';
        }

        // Hook detection
        if (data.event_type && (data.hook_name || data.subtype)) {
            return 'hook';
        }

        return 'generic';
    }

    /**
     * Display event data with comprehensive formatting
     */
    displayEvent(data) {
        const eventType = this.formatEventType(data);
        const timestamp = this.formatTimestamp(data.timestamp);
        
        let html = `
            <div class="unified-viewer-header">
                <h6>${eventType}</h6>
                <span class="unified-viewer-timestamp">${timestamp}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        // Event-specific details
        html += this.formatEventDetails(data);

        // Tool parameters if present
        if (data.tool_parameters || (data.data && data.data.tool_parameters)) {
            const params = data.tool_parameters || data.data.tool_parameters;
            html += this.formatParameters(params, 'Tool Parameters');
        }

        // Event data if present
        if (data.data && Object.keys(data.data).length > 0) {
            html += this.formatEventData(data);
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display agent data with full details
     */
    displayAgent(data) {
        const agentIcon = this.getAgentIcon(data.name || data.agentName);
        const status = this.formatStatus(data.status);
        
        let html = `
            <div class="unified-viewer-header">
                <h6>${agentIcon} ${data.name || data.agentName || 'Unknown Agent'}</h6>
                <span class="unified-viewer-status">${status}</span>
            </div>
            <div class="unified-viewer-content">
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">${status}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Session ID:</span>
                    <span class="detail-value">${data.sessionId || data.session_id || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Timestamp:</span>
                    <span class="detail-value">${this.formatTimestamp(data.timestamp)}</span>
                </div>
        `;

        // Tools used by agent
        if (data.tools && data.tools.length > 0) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Tools Used (${data.tools.length}):</span>
                    <div class="tools-list">
                        ${data.tools.map(tool => `
                            <div class="tool-summary">
                                <span class="tool-icon">${this.getToolIcon(tool.name)}</span>
                                <span class="tool-name">${tool.name}</span>
                                <span class="tool-status ${this.formatStatusClass(tool.status)}">${tool.status}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display tool data with parameters and results
     */
    displayTool(data) {
        const toolIcon = this.getToolIcon(data.name || data.tool_name);
        const status = this.formatStatus(data.status);
        
        let html = `
            <div class="unified-viewer-header">
                <h6>${toolIcon} ${data.name || data.tool_name || 'Unknown Tool'}</h6>
                <span class="unified-viewer-status">${status}</span>
            </div>
            <div class="unified-viewer-content">
                <div class="detail-row">
                    <span class="detail-label">Type:</span>
                    <span class="detail-value">Tool</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${data.name || data.tool_name || 'Unknown Tool'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">${status}</span>
                </div>
        `;

        // Tool parameters
        if (data.params || data.tool_parameters) {
            const params = data.params || data.tool_parameters;
            html += this.formatParameters(params, 'Parameters');
        }

        // Timestamp
        if (data.timestamp) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Timestamp:</span>
                    <span class="detail-value">${this.formatTimestamp(data.timestamp)}</span>
                </div>
            `;
        }

        // Tool result
        if (data.result) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Result:</span>
                    <pre class="tool-result">${this.escapeHtml(JSON.stringify(data.result, null, 2))}</pre>
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display todo data with checklist formatting
     */
    displayTodo(data) {
        // Handle different data structures for TodoWrite
        let todos;
        let toolName = 'Todo List';
        let timestamp = null;
        let status = null;
        
        if (data.todos && Array.isArray(data.todos)) {
            // Direct todo list format
            todos = data.todos;
        } else if (data.tool_parameters && data.tool_parameters.todos) {
            // TodoWrite tool format
            todos = data.tool_parameters.todos;
            toolName = 'TodoWrite';
            timestamp = data.timestamp;
            status = data.status;
        } else if (Array.isArray(data)) {
            // Array of todos
            todos = data;
        } else if (data.content && data.activeForm && data.status) {
            // Single todo item
            todos = [data];
        } else {
            // Fallback
            todos = [];
        }
        
        let html = `
            <div class="unified-viewer-header">
                <h6>📝 ${toolName}</h6>
                ${status ? `<span class="unified-viewer-status">${this.formatStatus(status)}</span>` : ''}
            </div>
            <div class="unified-viewer-content">
        `;

        // Show timestamp if available
        if (timestamp) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Timestamp:</span>
                    <span class="detail-value">${this.formatTimestamp(timestamp)}</span>
                </div>
            `;
        }

        if (todos.length > 0) {
            // Status summary with enhanced formatting
            const statusCounts = this.getTodoStatusCounts(todos);
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Todo Summary</span>
                    <div class="todo-summary">
                        <div class="summary-item completed">
                            <span class="summary-icon">✅</span>
                            <span class="summary-count">${statusCounts.completed}</span>
                            <span class="summary-label">Completed</span>
                        </div>
                        <div class="summary-item in_progress">
                            <span class="summary-icon">🔄</span>
                            <span class="summary-count">${statusCounts.in_progress}</span>
                            <span class="summary-label">In Progress</span>
                        </div>
                        <div class="summary-item pending">
                            <span class="summary-icon">⏳</span>
                            <span class="summary-count">${statusCounts.pending}</span>
                            <span class="summary-label">Pending</span>
                        </div>
                    </div>
                </div>
            `;

            // Enhanced todo items display
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Todo List (${todos.length} items)</span>
                    <div class="todo-checklist">
            `;
            
            todos.forEach((todo, index) => {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const displayText = todo.status === 'in_progress' ? 
                    (todo.activeForm || todo.content) : todo.content;
                const statusClass = this.formatStatusClass(todo.status);
                
                html += `
                    <div class="todo-checklist-item ${todo.status}">
                        <div class="todo-checkbox">
                            <span class="checkbox-icon ${statusClass}">${statusIcon}</span>
                        </div>
                        <div class="todo-text">
                            <span class="todo-content">${this.escapeHtml(displayText)}</span>
                            <span class="todo-status-badge ${statusClass}">${todo.status.replace('_', ' ')}</span>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="detail-section">
                    <div class="no-todos">No todo items found</div>
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display instruction data
     */
    displayInstruction(data) {
        let html = `
            <div class="unified-viewer-header">
                <h6>💬 User Instruction</h6>
                <span class="unified-viewer-timestamp">${this.formatTimestamp(data.timestamp)}</span>
            </div>
            <div class="unified-viewer-content">
                <div class="detail-row">
                    <span class="detail-label">Content:</span>
                    <div class="detail-value instruction-text">${this.escapeHtml(data.text)}</div>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Length:</span>
                    <span class="detail-value">${data.text.length} characters</span>
                </div>
            </div>
        `;
        this.container.innerHTML = html;
    }

    /**
     * Display session data
     */
    displaySession(data) {
        let html = `
            <div class="unified-viewer-header">
                <h6>🎯 Session: ${data.session_id || data.id}</h6>
                <span class="unified-viewer-status">${this.formatStatus(data.status || 'active')}</span>
            </div>
            <div class="unified-viewer-content">
                <div class="detail-row">
                    <span class="detail-label">Session ID:</span>
                    <span class="detail-value">${data.session_id || data.id}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Start Time:</span>
                    <span class="detail-value">${this.formatTimestamp(data.startTime || data.timestamp)}</span>
                </div>
        `;

        if (data.working_directory) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Working Directory:</span>
                    <span class="detail-value">${data.working_directory}</span>
                </div>
            `;
        }

        if (data.git_branch) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Git Branch:</span>
                    <span class="detail-value">${data.git_branch}</span>
                </div>
            `;
        }

        if (data.eventCount !== undefined) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Events:</span>
                    <span class="detail-value">${data.eventCount}</span>
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display file operation data
     */
    displayFileOperation(data) {
        let html = `
            <div class="unified-viewer-header">
                <h6>📄 File: ${data.file_path}</h6>
                <span class="unified-viewer-count">${data.operations ? data.operations.length : 1} operation${data.operations && data.operations.length !== 1 ? 's' : ''}</span>
            </div>
            <div class="unified-viewer-content">
                <div class="detail-row">
                    <span class="detail-label">File Path:</span>
                    <span class="detail-value">${data.file_path}</span>
                </div>
        `;

        if (data.operations && Array.isArray(data.operations)) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Operations:</span>
                    <div class="operations-list">
                        ${data.operations.map(op => `
                            <div class="operation-item">
                                <span class="operation-type">${op.operation}</span>
                                <span class="operation-timestamp">${this.formatTimestamp(op.timestamp)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display hook event data
     */
    displayHook(data) {
        const hookType = data.event_type || data.subtype || 'unknown';
        
        let html = `
            <div class="unified-viewer-header">
                <h6>🔗 Hook: ${hookType}</h6>
                <span class="unified-viewer-timestamp">${this.formatTimestamp(data.timestamp)}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        html += this.formatHookDetails(data);
        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display generic data with fallback formatting
     */
    displayGeneric(data) {
        let html = `
            <div class="unified-viewer-header">
                <h6>📊 Data Details</h6>
                ${data.timestamp ? `<span class="unified-viewer-timestamp">${this.formatTimestamp(data.timestamp)}</span>` : ''}
            </div>
            <div class="unified-viewer-content">
        `;

        if (typeof data === 'object' && data !== null) {
            // Display meaningful properties
            const meaningfulProps = ['id', 'name', 'type', 'status', 'timestamp', 'text', 'content', 'message'];
            
            for (let prop of meaningfulProps) {
                if (data[prop] !== undefined) {
                    let value = data[prop];
                    if (typeof value === 'string' && value.length > 200) {
                        value = value.substring(0, 200) + '...';
                    }
                    
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">${prop}:</span>
                            <span class="detail-value">${this.escapeHtml(String(value))}</span>
                        </div>
                    `;
                }
            }
        } else {
            html += `<div class="simple-value">${this.escapeHtml(String(data))}</div>`;
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    // ==================== FORMATTING UTILITIES ====================

    /**
     * Format event type for display
     */
    formatEventType(event) {
        if (event.type && event.subtype) {
            if (event.type === event.subtype || event.subtype === 'generic') {
                return event.type;
            }
            return `${event.type}.${event.subtype}`;
        }
        if (event.type) return event.type;
        if (event.hook_event_name) return event.hook_event_name;
        return 'unknown';
    }

    /**
     * Format detailed event data based on type
     */
    formatEventDetails(event) {
        const data = event.data || {};
        
        switch (event.type) {
            case 'hook':
                return this.formatHookDetails(event);
            case 'agent':
                return this.formatAgentEventDetails(event);
            case 'todo':
                return this.formatTodoEventDetails(event);
            case 'session':
                return this.formatSessionEventDetails(event);
            default:
                return this.formatGenericEventDetails(event);
        }
    }

    /**
     * Format hook event details
     */
    formatHookDetails(event) {
        const data = event.data || {};
        const hookType = event.subtype || event.event_type || 'unknown';
        
        let html = `
            <div class="detail-row">
                <span class="detail-label">Hook Type:</span>
                <span class="detail-value">${hookType}</span>
            </div>
        `;

        switch (hookType) {
            case 'user_prompt':
                const prompt = data.prompt_text || data.prompt_preview || '';
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Prompt:</span>
                        <div class="detail-value prompt-text">${this.escapeHtml(prompt)}</div>
                    </div>
                `;
                break;

            case 'pre_tool':
            case 'post_tool':
                const toolName = data.tool_name || 'Unknown tool';
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Tool:</span>
                        <span class="detail-value">${toolName}</span>
                    </div>
                `;
                if (data.operation_type) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Operation:</span>
                            <span class="detail-value">${data.operation_type}</span>
                        </div>
                    `;
                }
                if (hookType === 'post_tool' && data.duration_ms) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Duration:</span>
                            <span class="detail-value">${data.duration_ms}ms</span>
                        </div>
                    `;
                }
                break;

            case 'subagent_start':
            case 'subagent_stop':
                const agentType = data.agent_type || data.agent || 'Unknown';
                html += `
                    <div class="detail-row">
                        <span class="detail-label">Agent:</span>
                        <span class="detail-value">${agentType}</span>
                    </div>
                `;
                if (hookType === 'subagent_start' && data.prompt) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Task:</span>
                            <div class="detail-value">${this.escapeHtml(data.prompt)}</div>
                        </div>
                    `;
                }
                if (hookType === 'subagent_stop' && data.reason) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Reason:</span>
                            <span class="detail-value">${data.reason}</span>
                        </div>
                    `;
                }
                break;
        }

        return html;
    }

    /**
     * Format agent event details
     */
    formatAgentEventDetails(event) {
        const data = event.data || {};
        let html = '';

        if (data.agent_type || data.name) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Agent Type:</span>
                    <span class="detail-value">${data.agent_type || data.name}</span>
                </div>
            `;
        }

        if (event.subtype) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Action:</span>
                    <span class="detail-value">${event.subtype}</span>
                </div>
            `;
        }

        return html;
    }

    /**
     * Format todo event details
     */
    formatTodoEventDetails(event) {
        const data = event.data || {};
        let html = '';

        if (data.todos && Array.isArray(data.todos)) {
            const statusCounts = this.getTodoStatusCounts(data.todos);
            html += `
                <div class="detail-row">
                    <span class="detail-label">Todo Items:</span>
                    <span class="detail-value">${data.todos.length} total</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">${statusCounts.completed} completed, ${statusCounts.in_progress} in progress</span>
                </div>
            `;
        }

        return html;
    }

    /**
     * Format session event details
     */
    formatSessionEventDetails(event) {
        const data = event.data || {};
        let html = '';

        if (data.session_id) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Session ID:</span>
                    <span class="detail-value">${data.session_id}</span>
                </div>
            `;
        }

        if (event.subtype) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Action:</span>
                    <span class="detail-value">${event.subtype}</span>
                </div>
            `;
        }

        return html;
    }

    /**
     * Format generic event details
     */
    formatGenericEventDetails(event) {
        const data = event.data || {};
        let html = '';

        // Show basic data properties
        const basicProps = ['message', 'description', 'value', 'result'];
        for (let prop of basicProps) {
            if (data[prop] !== undefined) {
                let value = data[prop];
                if (typeof value === 'string' && value.length > 200) {
                    value = value.substring(0, 200) + '...';
                }
                html += `
                    <div class="detail-row">
                        <span class="detail-label">${prop}:</span>
                        <span class="detail-value">${this.escapeHtml(String(value))}</span>
                    </div>
                `;
            }
        }

        return html;
    }

    /**
     * Format event data section
     */
    formatEventData(event) {
        const data = event.data;
        if (!data || Object.keys(data).length === 0) return '';
        
        return `
            <div class="detail-section">
                <span class="detail-section-title">Event Data:</span>
                <pre class="event-data-json">${this.escapeHtml(JSON.stringify(data, null, 2))}</pre>
            </div>
        `;
    }

    /**
     * Format tool/event parameters
     */
    formatParameters(params, title = 'Parameters') {
        if (!params || Object.keys(params).length === 0) {
            return `
                <div class="detail-section">
                    <span class="detail-section-title">${title}:</span>
                    <div class="no-params">No parameters</div>
                </div>
            `;
        }

        const paramKeys = Object.keys(params);
        return `
            <div class="detail-section">
                <span class="detail-section-title">${title} (${paramKeys.length}):</span>
                <div class="params-list">
                    ${paramKeys.map(key => {
                        const value = params[key];
                        const displayValue = this.formatParameterValue(value);
                        return `
                            <div class="param-item">
                                <div class="param-key">${key}:</div>
                                <div class="param-value">${displayValue}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Format parameter value with appropriate styling
     */
    formatParameterValue(value) {
        if (typeof value === 'string') {
            if (value.length > 500) {
                return `<pre class="param-text-long">${this.escapeHtml(value.substring(0, 500) + '...\n\n[Content truncated - ' + value.length + ' total characters]')}</pre>`;
            } else if (value.length > 100) {
                return `<pre class="param-text">${this.escapeHtml(value)}</pre>`;
            } else {
                return `<span class="param-text-short">${this.escapeHtml(value)}</span>`;
            }
        } else if (typeof value === 'object' && value !== null) {
            // Special handling for todos array - display as formatted list instead of raw JSON
            if (Array.isArray(value) && value.length > 0 && 
                value[0].hasOwnProperty('content') && value[0].hasOwnProperty('status')) {
                return this.formatTodosAsParameter(value);
            }
            
            try {
                return `<pre class="param-json">${this.escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
            } catch (e) {
                return `<span class="param-error">Error displaying object</span>`;
            }
        } else {
            return `<span class="param-primitive">${this.escapeHtml(String(value))}</span>`;
        }
    }

    /**
     * Format todos array as a parameter value
     */
    formatTodosAsParameter(todos) {
        const statusCounts = this.getTodoStatusCounts(todos);
        
        let html = `
            <div class="param-todos">
                <div class="param-todos-header">
                    Array of todo objects (${todos.length} items)
                </div>
                <div class="param-todos-summary">
                    ${statusCounts.completed} completed • ${statusCounts.in_progress} in progress • ${statusCounts.pending} pending
                </div>
                <div class="param-todos-list">
        `;
        
        todos.forEach((todo, index) => {
            const statusIcon = this.getCheckboxIcon(todo.status);
            const displayText = todo.status === 'in_progress' ? 
                (todo.activeForm || todo.content) : todo.content;
            const statusClass = this.formatStatusClass(todo.status);
            
            html += `
                <div class="param-todo-item ${todo.status}">
                    <div class="param-todo-checkbox">
                        <span class="param-checkbox-icon ${statusClass}">${statusIcon}</span>
                    </div>
                    <div class="param-todo-text">
                        <span class="param-todo-content">${this.escapeHtml(displayText)}</span>
                        <span class="param-todo-status-badge ${statusClass}">${todo.status.replace('_', ' ')}</span>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }

    // ==================== UTILITY METHODS ====================

    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown time';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return 'Invalid date';
            return date.toLocaleString();
        } catch (error) {
            return 'Invalid date';
        }
    }

    /**
     * Format status with appropriate styling
     */
    formatStatus(status) {
        if (!status) return 'unknown';
        
        const statusMap = {
            'active': '🟢 Active',
            'completed': '✅ Completed', 
            'in_progress': '🔄 In Progress',
            'pending': '⏳ Pending',
            'error': '❌ Error',
            'failed': '❌ Failed'
        };
        
        return statusMap[status] || status;
    }

    /**
     * Get CSS class for status styling
     */
    formatStatusClass(status) {
        return `status-${status}`;
    }

    /**
     * Get icon for agent type
     */
    getAgentIcon(agentName) {
        const icons = {
            'PM': '🎯',
            'Engineer': '🔧',
            'Engineer Agent': '🔧',
            'Research': '🔍',
            'Research Agent': '🔍',
            'QA': '✅',
            'QA Agent': '✅',
            'Architect': '🏗️',
            'Architect Agent': '🏗️',
            'Ops': '⚙️',
            'Ops Agent': '⚙️'
        };
        return icons[agentName] || '🤖';
    }

    /**
     * Get icon for tool type
     */
    getToolIcon(toolName) {
        const icons = {
            'Read': '👁️',
            'Write': '✍️', 
            'Edit': '✏️',
            'MultiEdit': '📝',
            'Bash': '💻',
            'Grep': '🔍',
            'Glob': '📂',
            'LS': '📁',
            'TodoWrite': '📝',
            'Task': '📋',
            'WebFetch': '🌐'
        };
        return icons[toolName] || '🔧';
    }

    /**
     * Get checkbox icon for todo status
     */
    getCheckboxIcon(status) {
        const icons = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅'
        };
        return icons[status] || '❓';
    }

    /**
     * Get todo status counts
     */
    getTodoStatusCounts(todos) {
        const counts = { completed: 0, in_progress: 0, pending: 0 };
        
        todos.forEach(todo => {
            if (counts.hasOwnProperty(todo.status)) {
                counts[todo.status]++;
            }
        });
        
        return counts;
    }

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ==================== PUBLIC API METHODS ====================

    /**
     * Clear the viewer
     */
    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.currentData = null;
        this.currentType = null;
    }

    /**
     * Get current displayed data
     */
    getCurrentData() {
        return this.currentData;
    }

    /**
     * Get current data type
     */
    getCurrentType() {
        return this.currentType;
    }

    /**
     * Check if viewer has data
     */
    hasData() {
        return this.currentData !== null;
    }
}

// Export for module use
export { UnifiedDataViewer };
export default UnifiedDataViewer;

// Make globally available for non-module usage
window.UnifiedDataViewer = UnifiedDataViewer;