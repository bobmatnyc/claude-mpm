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
        
        // Global JSON visibility state - synchronized with localStorage
        // This ensures all JSON sections maintain consistent state
        this.globalJsonExpanded = localStorage.getItem('dashboard-json-expanded') === 'true';
        
        // Separate state for "Full Event Data" sections - uses its own localStorage key
        // This allows independent control of Full Event Data visibility
        this.fullEventDataExpanded = localStorage.getItem('dashboard-full-event-expanded') === 'true';
        
        // Listen for global JSON toggle changes from other components
        document.addEventListener('jsonToggleChanged', (e) => {
            this.globalJsonExpanded = e.detail.expanded;
            this.updateAllJsonSections();
        });
        
        // Listen for full event data toggle changes
        document.addEventListener('fullEventToggleChanged', (e) => {
            this.fullEventDataExpanded = e.detail.expanded;
            this.updateAllFullEventSections();
        });
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
                // Convert file tool to file operation format if needed
                if (data.name && (data.params || data.tool_parameters)) {
                    const convertedData = this.convertToolToFileOperation(data);
                    this.displayFileOperation(convertedData);
                } else {
                    this.displayFileOperation(data);
                }
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

        // File tool detection - handle file tools as file operations when they have file_path
        if ((data.name === 'Read' || data.name === 'Write' || data.name === 'Edit' || 
             data.name === 'MultiEdit' || data.name === 'Grep' || data.name === 'Glob') &&
            (data.params?.file_path || data.tool_parameters?.file_path)) {
            // Convert file tool to file operation format for better display
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
     * PRIMARY: Event type, timestamp, and key details
     * SECONDARY: Full event data in collapsible JSON
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

        // PRIMARY DATA: Event-specific key details
        html += `<div class="primary-data">`;
        html += this.formatEventDetails(data);
        
        // Show important tool parameters inline if present
        if (data.tool_name || data.data?.tool_name) {
            const toolName = data.tool_name || data.data.tool_name;
            html += `
                <div class="detail-row highlight">
                    <span class="detail-label">Tool:</span>
                    <span class="detail-value">${this.getToolIcon(toolName)} ${toolName}</span>
                </div>
            `;
            
            // Show key parameters for specific tools
            const params = data.tool_parameters || data.data?.tool_parameters;
            if (params) {
                if (params.file_path) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">File:</span>
                            <span class="detail-value code">${params.file_path}</span>
                        </div>
                    `;
                }
                if (params.command) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Command:</span>
                            <pre class="code-snippet">${this.escapeHtml(params.command)}</pre>
                        </div>
                    `;
                }
            }
        }
        html += `</div>`;

        // SECONDARY DATA: Collapsible JSON viewer for full event data
        html += this.createCollapsibleJSON(data, 'Full Event Data');

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display agent data with full details
     * PRIMARY: Agent status, active tools, and key info
     * SECONDARY: Full agent data in collapsible JSON
     */
    displayAgent(data) {
        const agentIcon = this.getAgentIcon(data.name || data.agentName);
        const agentName = data.name || data.agentName || 'Unknown Agent';
        const status = this.formatStatus(data.status);
        
        let html = `
            <div class="unified-viewer-header">
                <h6>${agentIcon} ${agentName}</h6>
                <span class="unified-viewer-status">${status}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        // PRIMARY DATA: Key agent information
        html += `<div class="primary-data">`;
        
        // Status with visual indicator
        html += `
            <div class="detail-row highlight">
                <span class="detail-label">Status:</span>
                <span class="detail-value ${this.formatStatusClass(status)}">${status}</span>
            </div>
        `;

        // Tools summary if present
        if (data.tools && data.tools.length > 0) {
            // Show active tools prominently
            const activeTools = data.tools.filter(t => t.status === 'in_progress');
            const completedTools = data.tools.filter(t => t.status === 'completed');
            
            if (activeTools.length > 0) {
                html += `
                    <div class="active-tools-section">
                        <span class="section-label">🔄 Active Tools:</span>
                        <div class="tools-grid">
                `;
                activeTools.forEach(tool => {
                    html += `
                        <div class="tool-chip active">
                            ${this.getToolIcon(tool.name)} ${tool.name}
                        </div>
                    `;
                });
                html += `</div></div>`;
            }
            
            html += `
                <div class="detail-row">
                    <span class="detail-label">Tools Summary:</span>
                    <span class="detail-value">
                        ${activeTools.length} active, ${completedTools.length} completed, ${data.tools.length} total
                    </span>
                </div>
            `;
        }

        // Current task if available
        if (data.currentTask || data.description) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Current Task:</span>
                    <span class="detail-value">${data.currentTask || data.description}</span>
                </div>
            `;
        }
        
        html += `</div>`;

        // SECONDARY DATA: Collapsible JSON viewer
        html += this.createCollapsibleJSON(data, 'Full Agent Details');

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display tool data with parameters and results
     * Special handling for TodoWrite to show todos prominently
     */
    displayTool(data) {
        const toolName = data.name || data.tool_name || 'Unknown Tool';
        const toolIcon = this.getToolIcon(toolName);
        const status = this.formatStatus(data.status);
        
        // Special handling for TodoWrite tool
        if (toolName === 'TodoWrite') {
            this.displayTodoWriteTool(data);
            return;
        }
        
        let html = `
            <div class="unified-viewer-header">
                <h6>${toolIcon} ${toolName}</h6>
                <span class="unified-viewer-status">${status}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        // PRIMARY DATA: Show important tool-specific information first
        const params = data.params || data.tool_parameters || {};
        
        // Tool-specific primary data display
        if (toolName === 'Read' || toolName === 'Edit' || toolName === 'Write') {
            // File tools - show file path prominently
            if (params.file_path) {
                html += `
                    <div class="primary-data">
                        <div class="detail-row highlight">
                            <span class="detail-label">📁 File:</span>
                            <span class="detail-value code">${params.file_path}</span>
                        </div>
                `;
                if (params.old_string) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Old Text:</span>
                            <pre class="code-snippet">${this.escapeHtml(params.old_string.substring(0, 200))}${params.old_string.length > 200 ? '...' : ''}</pre>
                        </div>
                    `;
                }
                if (params.new_string) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">New Text:</span>
                            <pre class="code-snippet">${this.escapeHtml(params.new_string.substring(0, 200))}${params.new_string.length > 200 ? '...' : ''}</pre>
                        </div>
                    `;
                }
                html += '</div>';
            }
        } else if (toolName === 'Bash') {
            // Bash tool - show command prominently
            if (params.command) {
                html += `
                    <div class="primary-data">
                        <div class="detail-row highlight">
                            <span class="detail-label">💻 Command:</span>
                            <pre class="code-snippet">${this.escapeHtml(params.command)}</pre>
                        </div>
                    </div>
                `;
            }
        } else if (toolName === 'Grep' || toolName === 'Glob') {
            // Search tools - show pattern prominently
            if (params.pattern) {
                html += `
                    <div class="primary-data">
                        <div class="detail-row highlight">
                            <span class="detail-label">🔍 Pattern:</span>
                            <span class="detail-value code">${this.escapeHtml(params.pattern)}</span>
                        </div>
                `;
                if (params.path) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Path:</span>
                            <span class="detail-value">${params.path}</span>
                        </div>
                    `;
                }
                html += '</div>';
            }
        } else if (toolName === 'Task') {
            // Task tool - show delegation info prominently
            if (params.subagent_type) {
                html += `
                    <div class="primary-data">
                        <div class="detail-row highlight">
                            <span class="detail-label">🤖 Delegating to:</span>
                            <span class="detail-value">${params.subagent_type} agent</span>
                        </div>
                `;
                if (params.description) {
                    html += `
                        <div class="detail-row">
                            <span class="detail-label">Task:</span>
                            <span class="detail-value">${params.description}</span>
                        </div>
                    `;
                }
                html += '</div>';
            }
        }

        // Status and metadata
        html += `
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">${status}</span>
            </div>
        `;

        if (data.callCount) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Call Count:</span>
                    <span class="detail-value">${data.callCount}</span>
                </div>
            `;
        }

        // Collapsible JSON viewer for full details
        html += this.createCollapsibleJSON(data, 'Full Tool Details');
        
        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display TodoWrite tool with todos list prominently after title
     */
    displayTodoWriteTool(data) {
        const status = this.formatStatus(data.status);
        const params = data.params || data.tool_parameters || {};
        const todos = params.todos || [];
        
        let html = `
            <div class="unified-viewer-header">
                <h6>📝 TodoWrite</h6>
                <span class="unified-viewer-status">${status}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        // PRIMARY DATA: Todo list and status summary immediately after title
        if (todos.length > 0) {
            const statusCounts = this.getTodoStatusCounts(todos);
            
            // Status summary - horizontal single line format
            html += `
                <div class="todo-status-line">
                    <span class="status-inline">✅ ${statusCounts.completed} Done</span>
                    <span class="status-inline">🔄 ${statusCounts.in_progress} Active</span>
                    <span class="status-inline">⏳ ${statusCounts.pending} Pending</span>
                </div>
            `;

            // Todo items list
            html += `
                <div class="todo-list-primary">
            `;
            
            todos.forEach((todo, index) => {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const displayText = todo.status === 'in_progress' ? 
                    (todo.activeForm || todo.content) : todo.content;
                const statusClass = this.formatStatusClass(todo.status);
                
                html += `
                    <div class="todo-item ${todo.status}">
                        <span class="todo-icon ${statusClass}">${statusIcon}</span>
                        <span class="todo-text">${this.escapeHtml(displayText)}</span>
                        ${todo.status === 'in_progress' ? '<span class="todo-badge active">ACTIVE</span>' : ''}
                    </div>
                `;
            });
            
            html += `
                </div>
            `;
        } else {
            html += `
                <div class="detail-row">
                    <span class="detail-value">No todos in list</span>
                </div>
            `;
        }

        // Metadata section
        if (data.callCount && data.callCount > 1) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Updates:</span>
                    <span class="detail-value">${data.callCount}</span>
                </div>
            `;
        }

        // Collapsible JSON viewer for full details
        html += this.createCollapsibleJSON(data, 'Full Details');
        
        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Display todo data with checklist formatting (for standalone todos, not TodoWrite)
     */
    displayTodo(data) {
        // Handle different data structures for standalone todos
        let todos;
        let toolName = 'Todo List';
        
        if (data.todos && Array.isArray(data.todos)) {
            todos = data.todos;
        } else if (Array.isArray(data)) {
            todos = data;
        } else if (data.content && data.activeForm && data.status) {
            todos = [data];
        } else {
            todos = [];
        }
        
        let html = `
            <div class="unified-viewer-header">
                <h6>📋 ${toolName}</h6>
            </div>
            <div class="unified-viewer-content">
        `;

        if (todos.length > 0) {
            // Show todos immediately
            html += `
                <div class="todo-list-primary">
            `;
            
            todos.forEach((todo) => {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const displayText = todo.status === 'in_progress' ? 
                    (todo.activeForm || todo.content) : todo.content;
                const statusClass = this.formatStatusClass(todo.status);
                
                html += `
                    <div class="todo-item ${todo.status}">
                        <span class="todo-icon ${statusClass}">${statusIcon}</span>
                        <span class="todo-text">${this.escapeHtml(displayText)}</span>
                        <span class="todo-status-text ${statusClass}">${todo.status.replace('_', ' ')}</span>
                    </div>
                `;
            });
            
            html += `
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
     * PRIMARY: Instruction text prominently displayed
     * SECONDARY: Metadata in collapsible section
     */
    displayInstruction(data) {
        let html = `
            <div class="unified-viewer-header">
                <h6>💬 User Instruction</h6>
                <span class="unified-viewer-timestamp">${this.formatTimestamp(data.timestamp)}</span>
            </div>
            <div class="unified-viewer-content">
        `;
        
        // PRIMARY DATA: The instruction text itself
        html += `
            <div class="primary-data">
                <div class="instruction-content">
                    ${this.escapeHtml(data.text)}
                </div>
                <div class="instruction-meta">
                    <span class="meta-item">📏 ${data.text.length} characters</span>
                    <span class="meta-item">🕐 ${this.formatTimestamp(data.timestamp)}</span>
                </div>
            </div>
        `;

        // SECONDARY DATA: Full instruction object if there's more data
        if (Object.keys(data).length > 3) {
            html += this.createCollapsibleJSON(data, 'Full Instruction Data');
        }
        
        html += '</div>';
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
     * Display file operation data with enhanced file viewing capabilities
     */
    displayFileOperation(data) {
        const fileName = data.file_path ? data.file_path.split('/').pop() : 'Unknown File';
        const isSingleFile = this.isSingleFileOperation(data);
        const fileIcon = this.getFileIcon(data.file_path);
        const fileType = this.getFileType(data.file_path);
        
        let html = `
            <div class="unified-viewer-header ${isSingleFile ? 'single-file-header' : ''}">
                <h6>${fileIcon} File: ${fileName}</h6>
                <span class="unified-viewer-count">${data.operations ? data.operations.length : 1} operation${data.operations && data.operations.length !== 1 ? 's' : ''}</span>
                ${fileType ? `<span class="file-type-badge">${fileType}</span>` : ''}
            </div>
            <div class="unified-viewer-content">
                <div class="primary-data">
                    <div class="detail-row highlight">
                        <span class="detail-label">📁 File Path:</span>
                        <span class="detail-value code clickable-file-path" 
                              onclick="window.showFileViewerModal && window.showFileViewerModal('${data.file_path}')"
                              title="Click to view file contents\\nKeyboard: Hover + V key or Ctrl/Cmd + Click\\nFile: ${data.file_path}"
                              tabindex="0"
                              role="button"
                              aria-label="Open file ${data.file_path} in viewer"
                              onkeypress="if(event.key==='Enter'||event.key===' '){window.showFileViewerModal && window.showFileViewerModal('${data.file_path}')}">${data.file_path}</span>
                    </div>
        `;

        // Enhanced file viewing for single file operations
        if (data.file_path) {
            const shouldShowPreview = this.shouldShowInlinePreview(data);
            
            html += `
                <div class="file-actions ${isSingleFile ? 'single-file-actions' : ''}">
                    <button class="file-action-btn view-file-btn ${isSingleFile ? 'primary-action' : ''}" 
                            onclick="window.showFileViewerModal && window.showFileViewerModal('${data.file_path}')"
                            title="View file contents with syntax highlighting">
                        ${fileIcon} View File Contents
                    </button>
                    ${isSingleFile && this.isTextFile(data.file_path) ? `
                        <button class="file-action-btn inline-preview-btn" 
                                onclick="window.unifiedDataViewer && window.unifiedDataViewer.toggleInlinePreview('${data.file_path}', this)"
                                title="Toggle inline preview">
                            📖 Quick Preview
                        </button>
                    ` : ''}
                </div>
            `;
            
            // Add inline preview container for single file operations
            if (isSingleFile && shouldShowPreview) {
                const previewId = this.generatePreviewId(data.file_path);
                html += `
                    <div class="inline-preview-container" id="preview-${previewId}" style="display: none;">
                        <div class="inline-preview-loading">Loading preview...</div>
                    </div>
                `;
            }
        }

        html += `</div>`;

        if (data.operations && Array.isArray(data.operations)) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Operations (${data.operations.length}):</span>
                    <div class="operations-list">
                        ${data.operations.map((op, index) => `
                            <div class="operation-item">
                                <div class="operation-header">
                                    <span class="operation-type">${this.getOperationIcon(op.operation)} ${op.operation}</span>
                                    <span class="operation-timestamp">${this.formatTimestamp(op.timestamp)}</span>
                                </div>
                                <div class="operation-details">
                                    <span class="operation-agent">by ${op.agent || 'Unknown'}</span>
                                    ${op.workingDirectory ? `<span class="operation-dir">in ${op.workingDirectory}</span>` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Add collapsible JSON viewer for full file data
        html += this.createCollapsibleJSON(data, 'Full File Data');

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

    // ==================== FILE OPERATION UTILITIES ====================

    /**
     * Determine if this is a single file operation
     */
    isSingleFileOperation(data) {
        // Single file if no operations array or only one operation
        if (!data.operations) return true;
        return data.operations.length === 1;
    }

    /**
     * Get file icon based on file extension
     */
    getFileIcon(filePath) {
        if (!filePath) return '📄';
        
        const ext = filePath.split('.').pop()?.toLowerCase();
        const iconMap = {
            // Code files
            'js': '🟨',
            'jsx': '⚛️',
            'ts': '🔷',
            'tsx': '⚛️',
            'py': '🐍',
            'java': '☕',
            'cpp': '⚡',
            'c': '⚡',
            'cs': '#️⃣',
            'php': '🐘',
            'rb': '💎',
            'go': '🐹',
            'rs': '🦀',
            'swift': '🦉',
            'kt': '🅺',
            'scala': '🎯',
            
            // Web files
            'html': '🌐',
            'htm': '🌐',
            'css': '🎨',
            'scss': '🎨',
            'sass': '🎨',
            'less': '🎨',
            'vue': '💚',
            
            // Config files
            'json': '📋',
            'xml': '📄',
            'yaml': '⚙️',
            'yml': '⚙️',
            'toml': '⚙️',
            'ini': '⚙️',
            'conf': '⚙️',
            'config': '⚙️',
            
            // Documentation
            'md': '📝',
            'txt': '📃',
            'rtf': '📃',
            'pdf': '📕',
            'doc': '📘',
            'docx': '📘',
            
            // Images
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'svg': '🎨',
            'webp': '🖼️',
            'ico': '🖼️',
            
            // Archives
            'zip': '🗜️',
            'tar': '🗜️',
            'gz': '🗜️',
            'rar': '🗜️',
            '7z': '🗜️',
            
            // Other
            'sql': '🗃️',
            'db': '🗃️',
            'log': '📊',
            'env': '🔐',
            'lock': '🔒'
        };
        
        return iconMap[ext] || '📄';
    }

    /**
     * Get file type description
     */
    getFileType(filePath) {
        if (!filePath) return null;
        
        const ext = filePath.split('.').pop()?.toLowerCase();
        const typeMap = {
            'js': 'JavaScript',
            'jsx': 'React JSX',
            'ts': 'TypeScript',
            'tsx': 'React TSX',
            'py': 'Python',
            'java': 'Java',
            'cpp': 'C++',
            'c': 'C',
            'cs': 'C#',
            'php': 'PHP',
            'rb': 'Ruby',
            'go': 'Go',
            'rs': 'Rust',
            'html': 'HTML',
            'css': 'CSS',
            'scss': 'SCSS',
            'json': 'JSON',
            'xml': 'XML',
            'yaml': 'YAML',
            'yml': 'YAML',
            'md': 'Markdown',
            'txt': 'Text',
            'sql': 'SQL',
            'log': 'Log File'
        };
        
        return typeMap[ext] || null;
    }

    /**
     * Check if file should show inline preview
     */
    shouldShowInlinePreview(data) {
        // Show preview for single file text operations
        return this.isSingleFileOperation(data) && this.isTextFile(data.file_path);
    }

    /**
     * Check if file is a text file suitable for preview
     */
    isTextFile(filePath) {
        if (!filePath) return false;
        
        const ext = filePath.split('.').pop()?.toLowerCase();
        const textExtensions = [
            'txt', 'md', 'json', 'xml', 'yaml', 'yml', 'ini', 'conf', 'config',
            'js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 'php', 'rb',
            'go', 'rs', 'swift', 'kt', 'scala', 'html', 'htm', 'css', 'scss', 'sass',
            'less', 'vue', 'sql', 'log', 'env', 'gitignore', 'dockerignore'
        ];
        
        return textExtensions.includes(ext);
    }

    /**
     * Toggle inline preview for a file
     */
    async toggleInlinePreview(filePath, buttonElement) {
        const containerId = `preview-${this.generatePreviewId(filePath)}`;
        const container = document.getElementById(containerId);
        
        if (!container) {
            console.warn('Preview container not found');
            return;
        }
        
        if (container.style.display === 'none') {
            // Show preview
            container.style.display = 'block';
            buttonElement.innerHTML = '📖 Hide Preview';
            await this.loadInlinePreview(filePath, container);
        } else {
            // Hide preview
            container.style.display = 'none';
            buttonElement.innerHTML = '📖 Quick Preview';
        }
    }

    /**
     * Load inline preview content
     */
    async loadInlinePreview(filePath, container) {
        try {
            // This would typically make an API call to get file contents
            // For now, show a placeholder
            container.innerHTML = `
                <div class="inline-preview-header">
                    <span class="preview-label">Quick Preview:</span>
                    <span class="preview-file">${filePath}</span>
                </div>
                <div class="inline-preview-content">
                    <div class="preview-note">
                        💡 Inline preview feature ready - API integration needed
                        <br>Click "View File Contents" for full syntax-highlighted view
                    </div>
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div class="inline-preview-error">
                    ❌ Could not load preview: ${error.message}
                </div>
            `;
        }
    }

    /**
     * Generate a unique ID for preview containers
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Generate preview ID based on file path
     */
    generatePreviewId(filePath) {
        return btoa(filePath).replace(/[^a-zA-Z0-9]/g, '');
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
     * Get icon for file operation type
     */
    getOperationIcon(operation) {
        const icons = {
            'read': '👁️',
            'write': '✍️',
            'edit': '✏️',
            'delete': '🗑️',
            'create': '📝',
            'search': '🔍',
            'list': '📂',
            'copy': '📋',
            'move': '📦',
            'bash': '💻'
        };
        return icons[operation.toLowerCase()] || '📄';
    }

    /**
     * Convert tool data to file operation format for better display
     */
    convertToolToFileOperation(toolData) {
        const params = toolData.params || toolData.tool_parameters || {};
        const filePath = params.file_path || params.path || params.notebook_path;
        
        if (!filePath) {
            return toolData; // Return original if no file path
        }

        // Create file operation format
        const operation = {
            operation: toolData.name.toLowerCase(),
            timestamp: toolData.timestamp || new Date().toISOString(),
            agent: 'Activity Tool',
            sessionId: toolData.sessionId || 'unknown',
            details: {
                parameters: params,
                tool_name: toolData.name,
                status: toolData.status || 'completed'
            }
        };

        return {
            file_path: filePath,
            operations: [operation],
            lastOperation: operation.timestamp,
            // Preserve original tool data for reference
            originalTool: toolData
        };
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
    
    /**
     * Toggle JSON section visibility and update global state
     * WHY: Maintains sticky state across all JSON sections for consistent behavior
     * @param {string} sectionId - ID of the specific section being toggled
     * @param {HTMLElement} button - The button element that was clicked
     */
    toggleJsonSection(sectionId, button) {
        // Toggle the global state
        this.globalJsonExpanded = !this.globalJsonExpanded;
        
        // Persist the preference to localStorage
        localStorage.setItem('dashboard-json-expanded', this.globalJsonExpanded.toString());
        
        // Update ALL JSON sections on the page
        this.updateAllJsonSections();
        
        // Dispatch event to notify other components (like module-viewer) of the change
        document.dispatchEvent(new CustomEvent('jsonToggleChanged', {
            detail: { expanded: this.globalJsonExpanded }
        }));
    }
    
    /**
     * Toggle Full Event Data section visibility and update state
     * WHY: Maintains separate sticky state for Full Event Data sections
     * @param {string} sectionId - ID of the specific section being toggled
     * @param {HTMLElement} button - The button element that was clicked
     */
    toggleFullEventSection(sectionId, button) {
        // Toggle the full event data state
        this.fullEventDataExpanded = !this.fullEventDataExpanded;
        
        // Persist the preference to localStorage
        localStorage.setItem('dashboard-full-event-expanded', this.fullEventDataExpanded.toString());
        
        // Update ALL Full Event sections on the page
        this.updateAllFullEventSections();
        
        // Dispatch event to notify other components of the change
        document.dispatchEvent(new CustomEvent('fullEventToggleChanged', {
            detail: { expanded: this.fullEventDataExpanded }
        }));
    }
    
    /**
     * Update all JSON sections on the page to match global state
     * WHY: Ensures all "Structured Data" sections maintain consistent visibility
     */
    updateAllJsonSections() {
        // Find all unified JSON sections (NOT full event sections)
        const allJsonContents = document.querySelectorAll('.unified-json-content');
        const allJsonButtons = document.querySelectorAll('.unified-json-toggle');
        
        // Update each JSON section
        allJsonContents.forEach(content => {
            if (this.globalJsonExpanded) {
                content.style.display = 'block';
            } else {
                content.style.display = 'none';
            }
        });
        
        // Update all button states
        allJsonButtons.forEach(button => {
            const title = button.textContent.substring(2); // Remove arrow
            if (this.globalJsonExpanded) {
                button.innerHTML = '▼ ' + title;
                button.classList.add('expanded');
            } else {
                button.innerHTML = '▶ ' + title;
                button.classList.remove('expanded');
            }
        });
    }
    
    /**
     * Update all Full Event Data sections on the page to match state
     * WHY: Ensures all "Full Event Data" sections maintain consistent visibility
     */
    updateAllFullEventSections() {
        // Find all full event sections
        const allFullEventContents = document.querySelectorAll('.full-event-content');
        const allFullEventButtons = document.querySelectorAll('.full-event-toggle');
        
        // Update each full event section
        allFullEventContents.forEach(content => {
            if (this.fullEventDataExpanded) {
                content.style.display = 'block';
            } else {
                content.style.display = 'none';
            }
        });
        
        // Update all button states
        allFullEventButtons.forEach(button => {
            const title = button.textContent.substring(2); // Remove arrow
            if (this.fullEventDataExpanded) {
                button.innerHTML = '▼ ' + title;
                button.classList.add('expanded');
            } else {
                button.innerHTML = '▶ ' + title;
                button.classList.remove('expanded');
            }
        });
    }

    /**
     * Create a collapsible JSON viewer for secondary details
     * Provides a clean way to show full data without cluttering the main view
     */
    createCollapsibleJSON(data, title = 'Full Details') {
        // Generate unique ID for this collapsible section
        const sectionId = `json-details-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        // Filter out sensitive or overly verbose properties
        const cleanData = this.cleanDataForDisplay(data);
        
        // Determine which state to use based on title
        // "Full Event Data" and similar titles use the fullEventDataExpanded state
        // Other titles use the global JSON state (for backward compatibility)
        const isFullEventData = title.includes('Full Event') || title.includes('Full Details') || 
                               title.includes('Full Agent') || title.includes('Full Tool');
        const isExpanded = isFullEventData ? this.fullEventDataExpanded : this.globalJsonExpanded;
        const display = isExpanded ? 'block' : 'none';
        const arrow = isExpanded ? '▼' : '▶';
        const expandedClass = isExpanded ? 'expanded' : '';
        
        // Use different toggle function based on section type
        const toggleFunction = isFullEventData ? 'toggleFullEventSection' : 'toggleJsonSection';
        
        return `
            <div class="collapsible-json-section">
                <button class="collapsible-json-toggle ${isFullEventData ? 'full-event-toggle' : 'unified-json-toggle'} ${expandedClass}" 
                        data-section-id="${sectionId}"
                        data-is-full-event="${isFullEventData}"
                        onclick="window.unifiedDataViewer.${toggleFunction}('${sectionId}', this)">
                    ${arrow} ${title}
                </button>
                <div id="${sectionId}" class="collapsible-json-content ${isFullEventData ? 'full-event-content' : 'unified-json-content'}" style="display: ${display};">
                    <pre class="json-viewer">${this.escapeHtml(JSON.stringify(cleanData, null, 2))}</pre>
                </div>
            </div>
        `;
    }

    /**
     * Clean data for display in JSON viewer
     * Removes circular references and limits string lengths
     */
    cleanDataForDisplay(data) {
        const seen = new WeakSet();
        
        return JSON.parse(JSON.stringify(data, (key, value) => {
            // Handle circular references
            if (typeof value === 'object' && value !== null) {
                if (seen.has(value)) {
                    return '[Circular Reference]';
                }
                seen.add(value);
            }
            
            // Truncate very long strings
            if (typeof value === 'string' && value.length > 1000) {
                return value.substring(0, 1000) + '... [truncated]';
            }
            
            // Handle functions
            if (typeof value === 'function') {
                return '[Function]';
            }
            
            return value;
        }));
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

// Create a global instance immediately for inline onclick handlers
// This ensures the instance is available when HTML is rendered dynamically
if (typeof window !== 'undefined') {
    // Always create/update the global instance
    window.unifiedDataViewer = new UnifiedDataViewer();
    
    // Also expose the methods directly on window as a fallback
    window.toggleFullEventSection = function(sectionId, button) {
        if (window.unifiedDataViewer) {
            window.unifiedDataViewer.toggleFullEventSection(sectionId, button);
        }
    };
    
    window.toggleJsonSection = function(sectionId, button) {
        if (window.unifiedDataViewer) {
            window.unifiedDataViewer.toggleJsonSection(sectionId, button);
        }
    };
}

// Create a global instance for inline preview functionality
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', function() {
        // Create global instance if one doesn't exist
        if (!window.unifiedDataViewer) {
            window.unifiedDataViewer = new UnifiedDataViewer();
        }
        
        // Add keyboard shortcuts for file operations
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + Click on file paths to open file viewer
            if ((e.ctrlKey || e.metaKey) && e.target.classList.contains('clickable-file-path')) {
                e.preventDefault();
                const filePath = e.target.textContent.trim();
                if (window.showFileViewerModal) {
                    window.showFileViewerModal(filePath);
                }
            }
            
            // 'V' key to open file viewer when hovering over clickable file paths
            if (e.key.toLowerCase() === 'v' && document.querySelector('.clickable-file-path:hover')) {
                const hoveredPath = document.querySelector('.clickable-file-path:hover');
                if (hoveredPath && window.showFileViewerModal) {
                    e.preventDefault();
                    const filePath = hoveredPath.textContent.trim();
                    window.showFileViewerModal(filePath);
                }
            }
        });
    });
}