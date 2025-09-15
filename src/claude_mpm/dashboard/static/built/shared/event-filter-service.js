/**
 * EventFilterService - Comprehensive event filtering and normalization
 * Handles all event types across the Claude MPM dashboard
 */

class EventFilterService {
    constructor() {
        // Event type configurations for comprehensive detection
        this.eventConfigs = {
            agent: {
                // Direct type patterns
                typePatterns: [
                    /agent/i,
                    /subagent/i,
                    /pm_/i,
                    /engineer/i,
                    /qa/i,
                    /devops/i
                ],
                // Hook event patterns
                hookPatterns: [
                    'SubagentStart',
                    'SubagentStop',
                    'AgentInference',
                    'agent_inference',
                    'agent_start',
                    'agent_stop',
                    'agent_update',
                    'agent_complete',
                    'agent_error',
                    'agent_activity'
                ],
                // Field detection for nested data
                dataFields: [
                    'agent_name',
                    'agent_id',
                    'agent_type',
                    'agent',
                    'subagent',
                    'agent_role'
                ],
                // Subtype patterns
                subtypes: [
                    'agent_deployment',
                    'agent_initialization',
                    'agent_task'
                ]
            },
            tool: {
                typePatterns: [
                    /tool/i,
                    /bash/i,
                    /read/i,
                    /write/i,
                    /edit/i,
                    /search/i,
                    /grep/i,
                    /glob/i,
                    /webfetch/i,
                    /multiedit/i,
                    /notebookedit/i
                ],
                hookPatterns: [
                    'ToolStart',
                    'ToolStop',
                    'tool_start',
                    'tool_complete',
                    'tool_error',
                    'tool_execution',
                    'BashCommand',
                    'FileOperation'
                ],
                dataFields: [
                    'tool',
                    'tool_name',
                    'tool_id',
                    'command',
                    'operation',
                    'tool_type'
                ],
                subtypes: [
                    'bash_command',
                    'file_operation',
                    'search_operation'
                ]
            },
            file: {
                typePatterns: [
                    /file/i,
                    /read/i,
                    /write/i,
                    /edit/i,
                    /delete/i,
                    /create/i,
                    /modify/i
                ],
                hookPatterns: [
                    'FileRead',
                    'FileWrite',
                    'FileEdit',
                    'FileDelete',
                    'file_read',
                    'file_write',
                    'file_edit',
                    'file_delete',
                    'file_operation',
                    'file_change'
                ],
                dataFields: [
                    'file',
                    'file_path',
                    'path',
                    'filename',
                    'file_name',
                    'target_file'
                ],
                subtypes: [
                    'file_created',
                    'file_modified',
                    'file_removed'
                ]
            }
        };

        // Cache for performance
        this.eventTypeCache = new Map();
        this.debug = false;
    }

    /**
     * Enable/disable debug logging
     */
    setDebug(enabled) {
        this.debug = enabled;
    }

    /**
     * Main filtering method - determines if an event matches a category
     */
    isEventType(event, category) {
        if (!event || !category) return false;

        // Check cache first
        const cacheKey = `${JSON.stringify(event)}_${category}`;
        if (this.eventTypeCache.has(cacheKey)) {
            return this.eventTypeCache.get(cacheKey);
        }

        const config = this.eventConfigs[category];
        if (!config) {
            console.warn(`Unknown event category: ${category}`);
            return false;
        }

        // Comprehensive detection
        let matches = false;

        // 1. Check direct type field
        const eventType = this.getEventType(event);
        if (eventType) {
            // Check type patterns
            matches = config.typePatterns.some(pattern => {
                if (pattern instanceof RegExp) {
                    return pattern.test(eventType);
                }
                return eventType.toLowerCase().includes(pattern.toLowerCase());
            });

            // Check hook patterns
            if (!matches) {
                matches = config.hookPatterns.some(pattern =>
                    eventType.includes(pattern) || eventType === pattern
                );
            }

            // Check subtypes
            if (!matches && config.subtypes) {
                matches = config.subtypes.some(subtype =>
                    eventType.toLowerCase().includes(subtype.toLowerCase())
                );
            }
        }

        // 2. Check hook_event_name field
        if (!matches && event.hook_event_name) {
            matches = config.hookPatterns.includes(event.hook_event_name);
        }

        // 3. Check data fields for category-specific fields
        if (!matches && event.data) {
            matches = config.dataFields.some(field => {
                const value = this.getNestedValue(event.data, field);
                return value !== undefined && value !== null && value !== '';
            });
        }

        // 4. Check root level fields
        if (!matches) {
            matches = config.dataFields.some(field => {
                const value = event[field];
                return value !== undefined && value !== null && value !== '';
            });
        }

        // 5. Special case: Check for tool names in tool category
        if (!matches && category === 'tool') {
            matches = this.isToolEvent(event);
        }

        // 6. Special case: Check for file paths in file category
        if (!matches && category === 'file') {
            matches = this.isFileEvent(event);
        }

        // Cache the result
        this.eventTypeCache.set(cacheKey, matches);

        if (this.debug) {
            console.log(`Event ${matches ? 'MATCHES' : 'does not match'} category ${category}:`, {
                event,
                eventType,
                matches
            });
        }

        return matches;
    }

    /**
     * Special detection for tool events
     */
    isToolEvent(event) {
        // Known tool names
        const toolNames = [
            'Bash', 'Read', 'Write', 'Edit', 'MultiEdit',
            'Search', 'Grep', 'Glob', 'WebFetch', 'NotebookEdit',
            'TodoWrite', 'WebSearch', 'BashOutput', 'KillShell'
        ];

        // Check if event contains any tool name
        const eventStr = JSON.stringify(event).toLowerCase();
        return toolNames.some(tool => eventStr.includes(tool.toLowerCase()));
    }

    /**
     * Special detection for file events
     */
    isFileEvent(event) {
        // Check for file path patterns
        const eventStr = JSON.stringify(event);
        const pathPatterns = [
            /\/[\w\-\.]+\/[\w\-\.]+/,  // Unix paths
            /[a-zA-Z]:\\[\w\-\.\\]+/,   // Windows paths
            /\.(js|py|md|json|txt|html|css|jsx|ts|tsx|yml|yaml)(\s|"|'|$)/i
        ];

        return pathPatterns.some(pattern => pattern.test(eventStr));
    }

    /**
     * Get the event type from various possible fields
     */
    getEventType(event) {
        if (!event) return null;

        // Priority order for type detection
        const typeFields = [
            'type',
            'event_type',
            'eventType',
            'hook_event_name',
            'event_name',
            'name'
        ];

        for (const field of typeFields) {
            const value = event[field];
            if (value && typeof value === 'string') {
                return value;
            }
        }

        // Check nested data.type
        if (event.data) {
            for (const field of typeFields) {
                const value = event.data[field];
                if (value && typeof value === 'string') {
                    return value;
                }
            }
        }

        return null;
    }

    /**
     * Normalize event data for consistent access
     */
    normalizeEvent(event, category) {
        if (!event) return null;

        const normalized = {
            // Core fields
            type: this.getEventType(event) || 'unknown',
            timestamp: event.timestamp || event.data?.timestamp || Date.now(),
            category: category,

            // Original event
            raw: event
        };

        // Category-specific normalization
        switch (category) {
            case 'agent':
                normalized.agent = this.extractAgentInfo(event);
                break;
            case 'tool':
                normalized.tool = this.extractToolInfo(event);
                break;
            case 'file':
                normalized.file = this.extractFileInfo(event);
                break;
        }

        return normalized;
    }

    /**
     * Extract agent information from event
     */
    extractAgentInfo(event) {
        const info = {
            id: null,
            name: null,
            type: null,
            status: null,
            message: null
        };

        // Extract from various possible locations
        const data = event.data || event;

        // ID extraction
        info.id = data.agent_id || data.agent_name || data.agent ||
                 event.agent_id || event.agent || null;

        // Name extraction
        info.name = data.agent_name || data.agent || data.name ||
                   event.agent_name || event.agent || event.name || 'Unknown';

        // Type extraction
        info.type = data.agent_type || data.type || event.agent_type || 'Agent';

        // Status extraction
        const eventType = this.getEventType(event);
        if (eventType) {
            if (eventType.includes('complete') || eventType.includes('Complete')) {
                info.status = 'complete';
            } else if (eventType.includes('error') || eventType.includes('Error')) {
                info.status = 'error';
            } else if (eventType.includes('start') || eventType.includes('Start')) {
                info.status = 'active';
            } else {
                info.status = data.status || event.status || 'active';
            }
        } else {
            info.status = data.status || event.status || 'unknown';
        }

        // Message extraction
        info.message = data.message || data.task || event.message || '';

        return info;
    }

    /**
     * Extract tool information from event
     */
    extractToolInfo(event) {
        const info = {
            name: null,
            type: null,
            status: null,
            description: null,
            command: null
        };

        const data = event.data || event;

        // Name extraction
        info.name = data.tool || data.tool_name || event.tool ||
                   event.tool_name || this.getEventType(event) || 'Unknown';

        // Clean up tool name (remove prefixes like "tool_")
        if (info.name.startsWith('tool_')) {
            info.name = info.name.substring(5);
        }

        // Type extraction
        info.type = data.tool_type || data.type || event.tool_type || 'Tool';

        // Status extraction
        const eventType = this.getEventType(event);
        if (eventType) {
            if (eventType.includes('complete') || eventType.includes('success')) {
                info.status = 'completed';
            } else if (eventType.includes('error')) {
                info.status = 'error';
            } else if (eventType.includes('start')) {
                info.status = 'running';
            } else {
                info.status = data.status || event.status || 'running';
            }
        } else {
            info.status = data.status || event.status || 'unknown';
        }

        // Description extraction
        info.description = data.description || data.message ||
                          event.description || event.message || '';

        // Command extraction (for Bash tool)
        info.command = data.command || event.command || null;

        return info;
    }

    /**
     * Extract file information from event
     */
    extractFileInfo(event) {
        const info = {
            path: null,
            name: null,
            operation: null,
            size: null
        };

        const data = event.data || event;

        // Path extraction
        info.path = data.path || data.file_path || data.file || data.filename ||
                   event.path || event.file_path || event.file || 'Unknown';

        // Name extraction
        if (info.path && info.path !== 'Unknown') {
            const parts = info.path.split('/');
            info.name = parts[parts.length - 1] || info.path;
        } else {
            info.name = 'Unknown';
        }

        // Operation extraction
        const eventType = this.getEventType(event);
        if (eventType) {
            if (eventType.includes('read') || eventType.includes('Read')) {
                info.operation = 'read';
            } else if (eventType.includes('write') || eventType.includes('Write')) {
                info.operation = 'write';
            } else if (eventType.includes('edit') || eventType.includes('Edit')) {
                info.operation = 'edit';
            } else if (eventType.includes('delete') || eventType.includes('Delete')) {
                info.operation = 'delete';
            } else {
                info.operation = data.operation || event.operation || 'unknown';
            }
        } else {
            info.operation = data.operation || event.operation || 'unknown';
        }

        // Size extraction
        info.size = data.size || event.size || 0;

        return info;
    }

    /**
     * Get nested value from object using dot notation
     */
    getNestedValue(obj, path) {
        if (!obj || !path) return undefined;

        const keys = path.split('.');
        let value = obj;

        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return undefined;
            }
        }

        return value;
    }

    /**
     * Clear the cache (useful when debug mode changes)
     */
    clearCache() {
        this.eventTypeCache.clear();
    }

    /**
     * Get statistics about filtered events
     */
    getFilterStats(events) {
        const stats = {
            total: events.length,
            agent: 0,
            tool: 0,
            file: 0,
            unknown: 0
        };

        for (const event of events) {
            if (this.isEventType(event, 'agent')) {
                stats.agent++;
            } else if (this.isEventType(event, 'tool')) {
                stats.tool++;
            } else if (this.isEventType(event, 'file')) {
                stats.file++;
            } else {
                stats.unknown++;
            }
        }

        return stats;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EventFilterService;
}

// Make available globally in browser
if (typeof window !== 'undefined') {
    window.EventFilterService = EventFilterService;
}