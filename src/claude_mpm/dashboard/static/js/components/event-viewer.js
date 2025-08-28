/**
 * Event Viewer Component
 * Handles event display, filtering, and selection
 */

class EventViewer {
    constructor(containerId, socketClient) {
        this.container = document.getElementById(containerId);
        this.socketClient = socketClient;

        // State
        this.events = [];
        this.filteredEvents = [];
        this.selectedEventIndex = -1;
        this.filteredEventElements = [];
        this.autoScroll = true;

        // Filters
        this.searchFilter = '';
        this.typeFilter = '';
        this.sessionFilter = '';

        // Event type tracking
        this.eventTypeCount = {};
        this.availableEventTypes = new Set();
        this.errorCount = 0;
        this.eventsThisMinute = 0;
        this.lastMinute = new Date().getMinutes();

        this.init();
    }

    /**
     * Initialize the event viewer
     */
    init() {
        this.setupEventHandlers();
        this.setupKeyboardNavigation();

        // Subscribe to socket events
        this.socketClient.onEventUpdate((events, sessions) => {
            // Ensure we always have a valid events array
            this.events = Array.isArray(events) ? events : [];
            this.updateDisplay();
        });
    }

    /**
     * Setup event handlers for UI controls
     */
    setupEventHandlers() {
        // Search input
        const searchInput = document.getElementById('events-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchFilter = e.target.value.toLowerCase();
                this.applyFilters();
            });
        }

        // Type filter
        const typeFilter = document.getElementById('events-type-filter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                this.typeFilter = e.target.value;
                this.applyFilters();
            });
        }
    }

    /**
     * Setup keyboard navigation for events
     * Note: This is now handled by the unified Dashboard navigation system
     */
    setupKeyboardNavigation() {
        // Keyboard navigation is now handled by Dashboard.setupUnifiedKeyboardNavigation()
        // This method is kept for backward compatibility but does nothing
    }

    /**
     * Handle arrow key navigation
     * @param {number} direction - Direction: 1 for down, -1 for up
     */
    handleArrowNavigation(direction) {
        if (this.filteredEventElements.length === 0) return;

        // Calculate new index
        let newIndex = this.selectedEventIndex + direction;

        // Wrap around
        if (newIndex >= this.filteredEventElements.length) {
            newIndex = 0;
        } else if (newIndex < 0) {
            newIndex = this.filteredEventElements.length - 1;
        }

        this.showEventDetails(newIndex);
    }

    /**
     * Apply filters to events
     */
    applyFilters() {
        // Defensive check to ensure events array exists
        if (!this.events || !Array.isArray(this.events)) {
            console.warn('EventViewer: events array is not initialized, using empty array');
            this.events = [];
        }

        this.filteredEvents = this.events.filter(event => {
            // NO AUTOMATIC FILTERING - All events are shown by default for complete visibility
            // Users can apply their own filters using the search and type filter controls
            
            // User-controlled search filter
            if (this.searchFilter) {
                const searchableText = [
                    event.type || '',
                    event.subtype || '',
                    JSON.stringify(event.data || {})
                ].join(' ').toLowerCase();

                if (!searchableText.includes(this.searchFilter)) {
                    return false;
                }
            }

            // User-controlled type filter - handles full hook types (like "hook.user_prompt") and main types
            if (this.typeFilter) {
                // Use the same logic as formatEventType to get the full event type
                const eventType = event.type && event.type.trim() !== '' ? event.type : '';
                const fullEventType = event.subtype && eventType ? `${eventType}.${event.subtype}` : eventType;
                if (fullEventType !== this.typeFilter) {
                    return false;
                }
            }

            // User-controlled session filter
            if (this.sessionFilter && this.sessionFilter !== '') {
                if (!event.data || event.data.session_id !== this.sessionFilter) {
                    return false;
                }
            }

            // Allow all events through unless filtered by user controls
            return true;
        });

        this.renderEvents();
        this.updateMetrics();
    }

    /**
     * Update available event types and populate dropdown
     */
    updateEventTypeDropdown() {
        const dropdown = document.getElementById('events-type-filter');
        if (!dropdown) return;

        // Extract unique event types from current events
        // Use the same logic as formatEventType to get full event type names
        const eventTypes = new Set();
        // Defensive check to ensure events array exists
        if (!this.events || !Array.isArray(this.events)) {
            console.warn('EventViewer: events array is not initialized in updateEventTypeDropdown');
            this.events = [];
        }

        this.events.forEach(event => {
            if (event.type && event.type.trim() !== '') {
                // Combine type and subtype if subtype exists, otherwise just use type
                const fullType = event.subtype ? `${event.type}.${event.subtype}` : event.type;
                eventTypes.add(fullType);
            }
        });

        // Check if event types have changed
        const currentTypes = Array.from(eventTypes).sort();
        const previousTypes = Array.from(this.availableEventTypes).sort();

        if (JSON.stringify(currentTypes) === JSON.stringify(previousTypes)) {
            return; // No change needed
        }

        // Update our tracking
        this.availableEventTypes = eventTypes;

        // Store the current selection
        const currentSelection = dropdown.value;

        // Clear existing options except "All Events"
        dropdown.innerHTML = '<option value="">All Events</option>';

        // Add new options sorted alphabetically
        const sortedTypes = Array.from(eventTypes).sort();
        sortedTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            dropdown.appendChild(option);
        });

        // Restore selection if it still exists
        if (currentSelection && eventTypes.has(currentSelection)) {
            dropdown.value = currentSelection;
        } else if (currentSelection && !eventTypes.has(currentSelection)) {
            // If the previously selected type no longer exists, clear the filter
            dropdown.value = '';
            this.typeFilter = '';
        }
    }

    /**
     * Update the display with current events
     */
    updateDisplay() {
        this.updateEventTypeDropdown();
        this.applyFilters();
    }

    /**
     * Render events in the UI
     */
    renderEvents() {
        const eventsList = document.getElementById('events-list');
        if (!eventsList) return;

        // Check if user is at bottom BEFORE rendering (for autoscroll decision)
        const wasAtBottom = (eventsList.scrollTop + eventsList.clientHeight >= eventsList.scrollHeight - 10);

        if (this.filteredEvents.length === 0) {
            eventsList.innerHTML = `
                <div class="no-events">
                    ${this.events.length === 0 ?
                        'Connect to Socket.IO server to see events...' :
                        'No events match current filters...'}
                </div>
            `;
            this.filteredEventElements = [];
            return;
        }

        const html = this.filteredEvents.map((event, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            const eventClass = event.type ? `event-${event.type}` : 'event-default';
            const isSelected = index === this.selectedEventIndex;

            // Get main content and timestamp separately
            const mainContent = this.formatSingleRowEventContent(event);

            // Check if this is an Edit/MultiEdit tool event and add diff viewer
            const diffViewer = this.createInlineEditDiffViewer(event, index);

            return `
                <div class="event-item single-row ${eventClass} ${isSelected ? 'selected' : ''}"
                     onclick="eventViewer.showEventDetails(${index})"
                     data-index="${index}">
                    <span class="event-single-row-content">
                        <span class="event-content-main">${mainContent}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </span>
                    ${diffViewer}
                </div>
            `;
        }).join('');

        eventsList.innerHTML = html;

        // Update filtered elements reference
        this.filteredEventElements = Array.from(eventsList.querySelectorAll('.event-item'));

        // Update Dashboard navigation items if we're in the events tab
        if (window.dashboard && window.dashboard.currentTab === 'events' &&
            window.dashboard.tabNavigation && window.dashboard.tabNavigation.events) {
            window.dashboard.tabNavigation.events.items = this.filteredEventElements;
        }

        // Auto-scroll only if user was already at bottom before rendering
        if (this.filteredEvents.length > 0 && wasAtBottom && this.autoScroll) {
            // Use requestAnimationFrame to ensure DOM has updated
            requestAnimationFrame(() => {
                eventsList.scrollTop = eventsList.scrollHeight;
            });
        }
    }

    /**
     * Format event type for display
     * @param {Object} event - Event object
     * @returns {string} Formatted event type
     */
    formatEventType(event) {
        // If we have type and subtype, use them
        if (event.type && event.subtype) {
            // Check if type and subtype are identical or subtype is 'generic' to prevent redundant display
            if (event.type === event.subtype || event.subtype === 'generic') {
                return event.type;
            }
            return `${event.type}.${event.subtype}`;
        }
        // If we have just type, use it
        if (event.type) {
            return event.type;
        }
        // If we have originalEventName (from transformation), use it as fallback
        if (event.originalEventName) {
            return event.originalEventName;
        }
        // Last resort fallback
        return 'unknown';
    }

    /**
     * Format event data for display
     * @param {Object} event - Event object
     * @returns {string} Formatted event data
     */
    formatEventData(event) {
        if (!event.data) return 'No data';

        // Special formatting for different event types
        switch (event.type) {
            case 'session':
                return this.formatSessionEvent(event);
            case 'claude':
                return this.formatClaudeEvent(event);
            case 'agent':
                return this.formatAgentEvent(event);
            case 'hook':
                return this.formatHookEvent(event);
            case 'todo':
                return this.formatTodoEvent(event);
            case 'memory':
                return this.formatMemoryEvent(event);
            case 'log':
                return this.formatLogEvent(event);
            case 'code':
                return this.formatCodeEvent(event);
            default:
                return this.formatGenericEvent(event);
        }
    }

    /**
     * Format session event data
     */
    formatSessionEvent(event) {
        const data = event.data;
        if (event.subtype === 'started') {
            return `<strong>Session started:</strong> ${data.session_id || 'Unknown'}`;
        } else if (event.subtype === 'ended') {
            return `<strong>Session ended:</strong> ${data.session_id || 'Unknown'}`;
        }
        return `<strong>Session:</strong> ${JSON.stringify(data)}`;
    }

    /**
     * Format Claude event data
     */
    formatClaudeEvent(event) {
        const data = event.data;
        if (event.subtype === 'request') {
            const prompt = data.prompt || data.message || '';
            const truncated = prompt.length > 100 ? prompt.substring(0, 100) + '...' : prompt;
            return `<strong>Request:</strong> ${truncated}`;
        } else if (event.subtype === 'response') {
            const response = data.response || data.content || '';
            const truncated = response.length > 100 ? response.substring(0, 100) + '...' : response;
            return `<strong>Response:</strong> ${truncated}`;
        }
        return `<strong>Claude:</strong> ${JSON.stringify(data)}`;
    }

    /**
     * Format agent event data
     */
    formatAgentEvent(event) {
        const data = event.data;
        if (event.subtype === 'loaded') {
            return `<strong>Agent loaded:</strong> ${data.agent_type || data.name || 'Unknown'}`;
        } else if (event.subtype === 'executed') {
            return `<strong>Agent executed:</strong> ${data.agent_type || data.name || 'Unknown'}`;
        }
        return `<strong>Agent:</strong> ${JSON.stringify(data)}`;
    }

    /**
     * Format hook event data
     */
    formatHookEvent(event) {
        const data = event.data;
        const eventType = data.event_type || event.subtype || 'unknown';

        // Format based on specific hook event type
        switch (eventType) {
            case 'user_prompt':
                const prompt = data.prompt_text || data.prompt_preview || '';
                const truncated = prompt.length > 80 ? prompt.substring(0, 80) + '...' : prompt;
                return `<strong>User Prompt:</strong> ${truncated || 'No prompt text'}`;

            case 'pre_tool':
                const toolName = data.tool_name || 'Unknown tool';
                const operation = data.operation_type || 'operation';
                return `<strong>Pre-Tool (${operation}):</strong> ${toolName}`;

            case 'post_tool':
                const postToolName = data.tool_name || 'Unknown tool';
                const status = data.success ? 'success' : data.status || 'failed';
                const duration = data.duration_ms ? ` (${data.duration_ms}ms)` : '';
                return `<strong>Post-Tool (${status}):</strong> ${postToolName}${duration}`;

            case 'notification':
                const notifType = data.notification_type || 'notification';
                const message = data.message_preview || data.message || 'No message';
                return `<strong>Notification (${notifType}):</strong> ${message}`;

            case 'stop':
                const reason = data.reason || 'unknown';
                const stopType = data.stop_type || 'normal';
                return `<strong>Stop (${stopType}):</strong> ${reason}`;

            case 'subagent_start':
                // Try multiple locations for agent type
                const startAgentType = data.agent_type || data.agent || data.subagent_type || 'Unknown';
                const startPrompt = data.prompt || data.description || data.task || 'No description';
                const startTruncated = startPrompt.length > 60 ? startPrompt.substring(0, 60) + '...' : startPrompt;
                // Format with proper agent type display
                const startAgentDisplay = this.formatAgentType(startAgentType);
                return `<strong>Subagent Start (${startAgentDisplay}):</strong> ${startTruncated}`;

            case 'subagent_stop':
                // Try multiple locations for agent type
                const agentType = data.agent_type || data.agent || data.subagent_type || 'Unknown';
                const stopReason = data.reason || data.stop_reason || 'completed';
                // Format with proper agent type display
                const stopAgentDisplay = this.formatAgentType(agentType);
                // Include task completion status if available
                const isCompleted = data.structured_response?.task_completed;
                const completionStatus = isCompleted !== undefined ? (isCompleted ? ' ✓' : ' ✗') : '';
                return `<strong>Subagent Stop (${stopAgentDisplay})${completionStatus}:</strong> ${stopReason}`;

            default:
                // Fallback to original logic for unknown hook types
                const hookName = data.hook_name || data.name || data.event_type || 'Unknown';
                const phase = event.subtype || eventType;
                return `<strong>Hook ${phase}:</strong> ${hookName}`;
        }
    }

    /**
     * Format todo event data
     */
    formatTodoEvent(event) {
        const data = event.data;
        if (data.todos && Array.isArray(data.todos)) {
            const count = data.todos.length;
            return `<strong>Todo updated:</strong> ${count} item${count !== 1 ? 's' : ''}`;
        }
        return `<strong>Todo:</strong> ${JSON.stringify(data)}`;
    }

    /**
     * Format memory event data
     */
    formatMemoryEvent(event) {
        const data = event.data;
        const operation = data.operation || 'unknown';
        return `<strong>Memory ${operation}:</strong> ${data.key || 'Unknown key'}`;
    }

    /**
     * Format log event data
     */
    formatLogEvent(event) {
        const data = event.data;
        const level = data.level || 'info';
        const message = data.message || '';
        const truncated = message.length > 80 ? message.substring(0, 80) + '...' : message;
        return `<strong>[${level.toUpperCase()}]</strong> ${truncated}`;
    }

    /**
     * Format code analysis event data
     */
    formatCodeEvent(event) {
        const data = event.data || {};
        
        // Handle different code event subtypes
        if (event.subtype === 'progress') {
            const message = data.message || 'Processing...';
            const percentage = data.percentage;
            if (percentage !== undefined) {
                return `<strong>Progress:</strong> ${message} (${Math.round(percentage)}%)`;
            }
            return `<strong>Progress:</strong> ${message}`;
        } else if (event.subtype === 'analysis:queued') {
            return `<strong>Queued:</strong> Analysis for ${data.path || 'Unknown path'}`;
        } else if (event.subtype === 'analysis:start') {
            return `<strong>Started:</strong> Analyzing ${data.path || 'Unknown path'}`;
        } else if (event.subtype === 'analysis:complete') {
            const duration = data.duration ? ` (${data.duration.toFixed(2)}s)` : '';
            return `<strong>Complete:</strong> Analysis finished${duration}`;
        } else if (event.subtype === 'analysis:error') {
            return `<strong>Error:</strong> ${data.message || 'Analysis failed'}`;
        } else if (event.subtype === 'analysis:cancelled') {
            return `<strong>Cancelled:</strong> Analysis stopped for ${data.path || 'Unknown path'}`;
        } else if (event.subtype === 'file:start') {
            return `<strong>File:</strong> Processing ${data.file || 'Unknown file'}`;
        } else if (event.subtype === 'file:complete') {
            const nodes = data.nodes_count !== undefined ? ` (${data.nodes_count} nodes)` : '';
            return `<strong>File done:</strong> ${data.file || 'Unknown file'}${nodes}`;
        } else if (event.subtype === 'node:found') {
            return `<strong>Node:</strong> Found ${data.node_type || 'element'} "${data.name || 'unnamed'}"`;
        } else if (event.subtype === 'error') {
            return `<strong>Error:</strong> ${data.error || 'Unknown error'} in ${data.file || 'file'}`;
        }
        
        // Generic fallback for code events
        const json = JSON.stringify(data);
        return `<strong>Code:</strong> ${json.length > 100 ? json.substring(0, 100) + '...' : json}`;
    }

    /**
     * Format generic event data
     */
    formatGenericEvent(event) {
        const data = event.data;
        if (typeof data === 'string') {
            return data.length > 100 ? data.substring(0, 100) + '...' : data;
        }
        return JSON.stringify(data);
    }

    /**
     * Format agent type for display with proper capitalization
     * @param {string} agentType - The raw agent type string
     * @returns {string} Formatted agent type for display
     */
    formatAgentType(agentType) {
        // Handle common agent type patterns
        const agentTypeMap = {
            'research': 'Research',
            'architect': 'Architect',
            'engineer': 'Engineer',
            'qa': 'QA',
            'pm': 'PM',
            'project_manager': 'PM',
            'research_agent': 'Research',
            'architect_agent': 'Architect',
            'engineer_agent': 'Engineer',
            'qa_agent': 'QA',
            'unknown': 'Unknown'
        };
        
        // Try to find a match in the map (case-insensitive)
        const lowerType = (agentType || 'unknown').toLowerCase();
        if (agentTypeMap[lowerType]) {
            return agentTypeMap[lowerType];
        }
        
        // If not in map, try to extract the agent name from patterns like "Research Agent" or "research_agent"
        const match = agentType.match(/^(\w+)(?:_agent|Agent)?$/i);
        if (match && match[1]) {
            // Capitalize first letter
            return match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase();
        }
        
        // Fallback: just capitalize first letter of whatever we have
        return agentType.charAt(0).toUpperCase() + agentType.slice(1);
    }

    /**
     * Format event content for single-row display (without timestamp)
     * Format: "{type}.{subtype}" followed by data details
     * @param {Object} event - Event object
     * @returns {string} Formatted single-row event content string
     */
    formatSingleRowEventContent(event) {
        const eventType = this.formatEventType(event);
        const data = event.data || {};
        
        // Include source if it's not the default 'system' source
        const sourcePrefix = event.source && event.source !== 'system' ? `[${event.source}] ` : '';

        // Extract meaningful details from the data package for different event types
        let dataDetails = '';

        switch (event.type) {
            case 'hook':
                // Hook events: show tool name and operation details
                const toolName = event.tool_name || data.tool_name || 'Unknown';
                const hookType = event.subtype || 'Unknown';
                
                // Format specific hook types
                if (hookType === 'pre_tool' || hookType === 'post_tool') {
                    const operation = data.operation_type || '';
                    const status = hookType === 'post_tool' && data.success !== undefined 
                        ? (data.success ? '✓' : '✗') 
                        : '';
                    dataDetails = `${toolName}${operation ? ` (${operation})` : ''}${status ? ` ${status}` : ''}`;
                } else if (hookType === 'user_prompt') {
                    const prompt = data.prompt_text || data.prompt_preview || '';
                    const truncated = prompt.length > 60 ? prompt.substring(0, 60) + '...' : prompt;
                    dataDetails = truncated || 'No prompt text';
                } else if (hookType === 'subagent_start') {
                    // Enhanced agent type detection
                    const agentType = data.agent_type || data.agent || data.subagent_type || 'Unknown';
                    const agentDisplay = this.formatAgentType(agentType);
                    const prompt = data.prompt || data.description || data.task || '';
                    const truncated = prompt.length > 40 ? prompt.substring(0, 40) + '...' : prompt;
                    dataDetails = truncated ? `${agentDisplay} - ${truncated}` : agentDisplay;
                } else if (hookType === 'subagent_stop') {
                    // Enhanced agent type detection for subagent_stop
                    const agentType = data.agent_type || data.agent || data.subagent_type || 'Unknown';
                    const agentDisplay = this.formatAgentType(agentType);
                    const reason = data.reason || data.stop_reason || 'completed';
                    const isCompleted = data.structured_response?.task_completed;
                    const status = isCompleted !== undefined ? (isCompleted ? '✓' : '✗') : '';
                    dataDetails = `${agentDisplay}${status ? ' ' + status : ''} - ${reason}`;
                } else if (hookType === 'stop') {
                    const reason = data.reason || 'completed';
                    const stopType = data.stop_type || 'normal';
                    dataDetails = `${stopType} - ${reason}`;
                } else {
                    dataDetails = toolName;
                }
                break;

            case 'agent':
                // Agent events: show agent name and status
                const agentName = event.subagent_type || data.subagent_type || 'PM';
                const status = data.status || '';
                dataDetails = `${agentName}${status ? ` - ${status}` : ''}`;
                break;

            case 'todo':
                // Todo events: show item count and status changes
                if (data.todos && Array.isArray(data.todos)) {
                    const count = data.todos.length;
                    const completed = data.todos.filter(t => t.status === 'completed').length;
                    const inProgress = data.todos.filter(t => t.status === 'in_progress').length;
                    dataDetails = `${count} items (${completed} completed, ${inProgress} in progress)`;
                } else {
                    dataDetails = 'Todo update';
                }
                break;

            case 'memory':
                // Memory events: show operation and key
                const operation = data.operation || 'unknown';
                const key = data.key || 'unknown';
                const value = data.value ? ` = ${JSON.stringify(data.value).substring(0, 30)}...` : '';
                dataDetails = `${operation}: ${key}${value}`;
                break;

            case 'session':
                // Session events: show session ID
                const sessionId = data.session_id || 'unknown';
                dataDetails = `ID: ${sessionId}`;
                break;

            case 'claude':
                // Claude events: show request/response preview
                if (event.subtype === 'request') {
                    const prompt = data.prompt || data.message || '';
                    const truncated = prompt.length > 60 ? prompt.substring(0, 60) + '...' : prompt;
                    dataDetails = truncated || 'Empty request';
                } else if (event.subtype === 'response') {
                    const response = data.response || data.content || '';
                    const truncated = response.length > 60 ? response.substring(0, 60) + '...' : response;
                    dataDetails = truncated || 'Empty response';
                } else {
                    dataDetails = data.message || 'Claude interaction';
                }
                break;

            case 'log':
                // Log events: show log level and message
                const level = data.level || 'info';
                const message = data.message || '';
                const truncated = message.length > 60 ? message.substring(0, 60) + '...' : message;
                dataDetails = `[${level.toUpperCase()}] ${truncated}`;
                break;

            case 'test':
                // Test events: show test name or details
                const testName = data.test_name || data.name || 'Test';
                dataDetails = testName;
                break;

            default:
                // Generic events: show any available data
                if (typeof data === 'string') {
                    dataDetails = data.length > 60 ? data.substring(0, 60) + '...' : data;
                } else if (data.message) {
                    dataDetails = data.message.length > 60 ? data.message.substring(0, 60) + '...' : data.message;
                } else if (data.name) {
                    dataDetails = data.name;
                } else if (Object.keys(data).length > 0) {
                    // Show first meaningful field from data
                    const firstKey = Object.keys(data).find(k => !['timestamp', 'id'].includes(k));
                    if (firstKey) {
                        const value = data[firstKey];
                        dataDetails = `${firstKey}: ${typeof value === 'object' ? JSON.stringify(value).substring(0, 40) + '...' : value}`;
                    }
                }
                break;
        }

        // Return formatted string: "[source] {type}.{subtype} - {data details}"
        // The eventType already contains the type.subtype format from formatEventType()
        const fullType = `${sourcePrefix}${eventType}`;
        return dataDetails ? `${fullType} - ${dataDetails}` : fullType;
    }

    /**
     * Get display name for hook types
     * @param {string} hookType - Hook subtype
     * @param {Object} data - Event data
     * @returns {string} Display name
     */
    getHookDisplayName(hookType, data) {
        const hookNames = {
            'pre_tool': 'Pre-Tool',
            'post_tool': 'Post-Tool',
            'user_prompt': 'User-Prompt',
            'stop': 'Stop',
            'subagent_start': 'Subagent-Start',
            'subagent_stop': 'Subagent-Stop',
            'notification': 'Notification'
        };

        // Handle non-string hookType safely
        if (hookNames[hookType]) {
            return hookNames[hookType];
        }
        
        // Convert to string and handle null/undefined
        const typeStr = String(hookType || 'unknown');
        return typeStr.replace(/_/g, ' ');
    }

    /**
     * Get event category for display
     * @param {Object} event - Event object
     * @returns {string} Category
     */
    getEventCategory(event) {
        const data = event.data || {};
        const toolName = event.tool_name || data.tool_name || '';

        // Categorize based on tool type
        if (['Read', 'Write', 'Edit', 'MultiEdit'].includes(toolName)) {
            return 'file_operations';
        } else if (['Bash', 'grep', 'Glob'].includes(toolName)) {
            return 'system_operations';
        } else if (toolName === 'TodoWrite') {
            return 'task_management';
        } else if (toolName === 'Task') {
            return 'agent_delegation';
        } else if (event.subtype === 'subagent_start' || event.subtype === 'subagent_stop') {
            return 'agent_delegation';
        } else if (event.subtype === 'stop') {
            return 'session_control';
        }

        return 'general';
    }

    /**
     * Show event details and update selection
     * @param {number} index - Index of event to show
     */
    showEventDetails(index) {
        // Defensive checks
        if (!this.filteredEvents || !Array.isArray(this.filteredEvents)) {
            console.warn('EventViewer: filteredEvents array is not initialized');
            return;
        }
        if (index < 0 || index >= this.filteredEvents.length) return;

        // Update selection
        this.selectedEventIndex = index;

        // Get the selected event
        const event = this.filteredEvents[index];

        // Coordinate with Dashboard unified navigation system
        if (window.dashboard) {
            // Update the dashboard's navigation state for events tab
            if (window.dashboard.tabNavigation && window.dashboard.tabNavigation.events) {
                window.dashboard.tabNavigation.events.selectedIndex = index;
            }
            if (window.dashboard.selectCard) {
                window.dashboard.selectCard('events', index, 'event', event);
            }
        }

        // Update visual selection (this will be handled by Dashboard.updateCardSelectionUI())
        this.filteredEventElements.forEach((el, i) => {
            el.classList.toggle('selected', i === index);
        });

        // Notify other components about selection
        document.dispatchEvent(new CustomEvent('eventSelected', {
            detail: { event, index }
        }));

        // Scroll to selected event if not visible
        const selectedElement = this.filteredEventElements[index];
        if (selectedElement) {
            selectedElement.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }

    /**
     * Clear event selection
     */
    clearSelection() {
        this.selectedEventIndex = -1;
        this.filteredEventElements.forEach(el => {
            el.classList.remove('selected');
        });

        // Coordinate with Dashboard unified navigation system
        if (window.dashboard) {
            if (window.dashboard.tabNavigation && window.dashboard.tabNavigation.events) {
                window.dashboard.tabNavigation.events.selectedIndex = -1;
            }
            if (window.dashboard.clearCardSelection) {
                window.dashboard.clearCardSelection();
            }
        }

        // Notify other components
        document.dispatchEvent(new CustomEvent('eventSelectionCleared'));
    }

    /**
     * Update metrics display
     */
    updateMetrics() {
        // Update event type counts
        this.eventTypeCount = {};
        this.errorCount = 0;

        // Defensive check to ensure events array exists
        if (!this.events || !Array.isArray(this.events)) {
            console.warn('EventViewer: events array is not initialized in updateMetrics');
            this.events = [];
        }

        this.events.forEach(event => {
            const type = event.type || 'unknown';
            this.eventTypeCount[type] = (this.eventTypeCount[type] || 0) + 1;

            if (event.type === 'log' &&
                event.data &&
                ['error', 'critical'].includes(event.data.level)) {
                this.errorCount++;
            }
        });

        // Update events per minute
        const currentMinute = new Date().getMinutes();
        if (currentMinute !== this.lastMinute) {
            this.lastMinute = currentMinute;
            this.eventsThisMinute = 0;
        }

        // Count events in the last minute
        const oneMinuteAgo = new Date(Date.now() - 60000);
        this.eventsThisMinute = this.events.filter(event =>
            new Date(event.timestamp) > oneMinuteAgo
        ).length;

        // Update UI
        this.updateMetricsUI();
    }

    /**
     * Update metrics in the UI
     */
    updateMetricsUI() {
        const totalEventsEl = document.getElementById('total-events');
        const eventsPerMinuteEl = document.getElementById('events-per-minute');
        const uniqueTypesEl = document.getElementById('unique-types');
        const errorCountEl = document.getElementById('error-count');

        if (totalEventsEl) totalEventsEl.textContent = this.events.length;
        if (eventsPerMinuteEl) eventsPerMinuteEl.textContent = this.eventsThisMinute;
        if (uniqueTypesEl) uniqueTypesEl.textContent = Object.keys(this.eventTypeCount).length;
        if (errorCountEl) errorCountEl.textContent = this.errorCount;
    }

    /**
     * Export events to JSON
     */
    exportEvents() {
        const dataStr = JSON.stringify(this.filteredEvents, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `claude-mpm-events-${new Date().toISOString().split('T')[0]}.json`;
        link.click();

        URL.revokeObjectURL(url);
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.socketClient.clearEvents();
        this.selectedEventIndex = -1;
        this.updateDisplay();
    }

    /**
     * Set session filter
     * @param {string} sessionId - Session ID to filter by
     */
    setSessionFilter(sessionId) {
        this.sessionFilter = sessionId;
        this.applyFilters();
    }

    /**
     * Get current filter state
     * @returns {Object} Current filters
     */
    getFilters() {
        return {
            search: this.searchFilter,
            type: this.typeFilter,
            session: this.sessionFilter
        };
    }

    /**
     * Get filtered events (used by HUD and other components)
     * @returns {Array} Array of filtered events
     */
    getFilteredEvents() {
        return this.filteredEvents;
    }

    /**
     * Get all events (unfiltered, used by HUD for complete visualization)
     * @returns {Array} Array of all events
     */
    getAllEvents() {
        return this.events;
    }

    /**
     * Create inline diff viewer for Edit/MultiEdit tool events
     * WHY: Provides immediate visibility of file changes without needing to open modals
     * DESIGN DECISION: Shows inline diffs only for Edit/MultiEdit events to avoid clutter
     * @param {Object} event - Event object
     * @param {number} index - Event index for unique IDs
     * @returns {string} HTML for inline diff viewer
     */
    createInlineEditDiffViewer(event, index) {
        const data = event.data || {};
        const toolName = event.tool_name || data.tool_name || '';

        // Only show for Edit and MultiEdit tools
        if (!['Edit', 'MultiEdit'].includes(toolName)) {
            return '';
        }

        // Extract edit parameters based on tool type
        let edits = [];
        if (toolName === 'Edit') {
            // Single edit
            const parameters = event.tool_parameters || data.tool_parameters || {};
            if (parameters.old_string && parameters.new_string) {
                edits.push({
                    old_string: parameters.old_string,
                    new_string: parameters.new_string,
                    file_path: parameters.file_path || 'unknown'
                });
            }
        } else if (toolName === 'MultiEdit') {
            // Multiple edits
            const parameters = event.tool_parameters || data.tool_parameters || {};
            if (parameters.edits && Array.isArray(parameters.edits)) {
                edits = parameters.edits.map(edit => ({
                    ...edit,
                    file_path: parameters.file_path || 'unknown'
                }));
            }
        }

        if (edits.length === 0) {
            return '';
        }

        // Create collapsible diff section
        const diffId = `edit-diff-${index}`;
        const isMultiEdit = edits.length > 1;

        let diffContent = '';
        edits.forEach((edit, editIndex) => {
            const editId = `${diffId}-${editIndex}`;
            const diffHtml = this.createDiffHtml(edit.old_string, edit.new_string);

            diffContent += `
                <div class="edit-diff-section">
                    ${isMultiEdit ? `<div class="edit-diff-header">Edit ${editIndex + 1}</div>` : ''}
                    <div class="diff-content">${diffHtml}</div>
                </div>
            `;
        });

        return `
            <div class="inline-edit-diff-viewer">
                <div class="diff-toggle-header" onclick="eventViewer.toggleEditDiff('${diffId}', event)">
                    <span class="diff-toggle-icon">📋</span>
                    <span class="diff-toggle-text">Show ${isMultiEdit ? edits.length + ' edits' : 'edit'}</span>
                    <span class="diff-toggle-arrow">▼</span>
                </div>
                <div id="${diffId}" class="diff-content-container" style="display: none;">
                    ${diffContent}
                </div>
            </div>
        `;
    }

    /**
     * Create HTML diff visualization
     * WHY: Provides clear visual representation of text changes similar to git diff
     * @param {string} oldText - Original text
     * @param {string} newText - Modified text
     * @returns {string} HTML diff content
     */
    createDiffHtml(oldText, newText) {
        // Simple line-by-line diff implementation
        const oldLines = oldText.split('\n');
        const newLines = newText.split('\n');

        let diffHtml = '';
        let i = 0, j = 0;

        // Simple diff algorithm - can be enhanced with proper diff library if needed
        while (i < oldLines.length || j < newLines.length) {
            const oldLine = i < oldLines.length ? oldLines[i] : null;
            const newLine = j < newLines.length ? newLines[j] : null;

            if (oldLine === null) {
                // New line added
                diffHtml += `<div class="diff-line diff-added">+ ${this.escapeHtml(newLine)}</div>`;
                j++;
            } else if (newLine === null) {
                // Old line removed
                diffHtml += `<div class="diff-line diff-removed">- ${this.escapeHtml(oldLine)}</div>`;
                i++;
            } else if (oldLine === newLine) {
                // Lines are the same
                diffHtml += `<div class="diff-line diff-unchanged">  ${this.escapeHtml(oldLine)}</div>`;
                i++;
                j++;
            } else {
                // Lines are different - show both
                diffHtml += `<div class="diff-line diff-removed">- ${this.escapeHtml(oldLine)}</div>`;
                diffHtml += `<div class="diff-line diff-added">+ ${this.escapeHtml(newLine)}</div>`;
                i++;
                j++;
            }
        }

        return `<div class="diff-container">${diffHtml}</div>`;
    }

    /**
     * Toggle edit diff visibility
     * @param {string} diffId - Diff container ID
     * @param {Event} event - Click event
     */
    toggleEditDiff(diffId, event) {
        // Prevent event bubbling to parent event item
        event.stopPropagation();

        const diffContainer = document.getElementById(diffId);
        const arrow = event.currentTarget.querySelector('.diff-toggle-arrow');

        if (diffContainer) {
            const isVisible = diffContainer.style.display !== 'none';
            diffContainer.style.display = isVisible ? 'none' : 'block';
            if (arrow) {
                arrow.textContent = isVisible ? '▼' : '▲';
            }
        }
    }

    /**
     * Escape HTML characters for safe display
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ES6 Module export
export { EventViewer };
export default EventViewer;

// Backward compatibility - keep window export for non-module usage
window.EventViewer = EventViewer;
