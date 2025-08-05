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
            this.events = events;
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
        console.log('EventViewer: Keyboard navigation handled by unified Dashboard system');
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
        this.filteredEvents = this.events.filter(event => {
            // Search filter
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

            // Type filter - now handles both full hook types (like "hook.user_prompt") and main types
            if (this.typeFilter) {
                const eventType = event.type || '';
                if (eventType !== this.typeFilter) {
                    return false;
                }
            }

            // Session filter
            if (this.sessionFilter && this.sessionFilter !== '') {
                if (!event.data || event.data.session_id !== this.sessionFilter) {
                    return false;
                }
            }

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
        const eventTypes = new Set();
        this.events.forEach(event => {
            if (event.type) {
                eventTypes.add(event.type);
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
            
            return `
                <div class="event-item ${eventClass} ${isSelected ? 'selected' : ''}" 
                     onclick="eventViewer.showEventDetails(${index})" 
                     data-index="${index}">
                    <div class="event-header">
                        <span class="event-type">${this.formatEventType(event)}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        ${this.formatEventData(event)}
                    </div>
                </div>
            `;
        }).join('');

        eventsList.innerHTML = html;
        
        // Update filtered elements reference
        this.filteredEventElements = Array.from(eventsList.querySelectorAll('.event-item'));

        // Update Dashboard navigation items if we're in the events tab
        if (window.dashboard && window.dashboard.currentTab === 'events') {
            window.dashboard.tabNavigation.events.items = this.filteredEventElements;
        }

        // Auto-scroll to bottom if enabled
        if (this.autoScroll && this.filteredEvents.length > 0) {
            eventsList.scrollTop = eventsList.scrollHeight;
        }
    }

    /**
     * Format event type for display
     * @param {Object} event - Event object
     * @returns {string} Formatted event type
     */
    formatEventType(event) {
        if (event.subtype) {
            return `${event.type}.${event.subtype}`;
        }
        return event.type || 'unknown';
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
                
            case 'subagent_stop':
                const agentType = data.agent_type || 'unknown agent';
                const stopReason = data.reason || 'unknown';
                return `<strong>Subagent Stop (${agentType}):</strong> ${stopReason}`;
                
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
     * Show event details and update selection
     * @param {number} index - Index of event to show
     */
    showEventDetails(index) {
        if (index < 0 || index >= this.filteredEvents.length) return;

        // Update selection
        this.selectedEventIndex = index;
        
        // Get the selected event
        const event = this.filteredEvents[index];
        
        // Coordinate with Dashboard unified navigation system
        if (window.dashboard) {
            // Update the dashboard's navigation state for events tab
            window.dashboard.tabNavigation.events.selectedIndex = index;
            window.dashboard.selectCard('events', index, 'event', event);
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
            window.dashboard.tabNavigation.events.selectedIndex = -1;
            window.dashboard.clearCardSelection();
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
}

// Export for global use
window.EventViewer = EventViewer;