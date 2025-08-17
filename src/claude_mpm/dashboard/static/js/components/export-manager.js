/**
 * Export Manager Module
 *
 * Handles export functionality and utility functions for the dashboard.
 * Provides data export capabilities and common utility functions used across modules.
 *
 * WHY: Extracted from main dashboard to centralize export logic and utility functions
 * that don't belong to specific functional areas. This provides a clean place for
 * shared utilities while keeping export logic organized and testable.
 *
 * DESIGN DECISION: Combines export functionality with general utilities to avoid
 * creating too many small modules while keeping related functionality together.
 * Provides both data export and UI utility functions.
 */
class ExportManager {
    constructor(eventViewer) {
        this.eventViewer = eventViewer;
        this.setupEventHandlers();

        console.log('Export manager initialized');
    }

    /**
     * Set up event handlers for export functionality
     */
    setupEventHandlers() {
        const clearBtn = document.querySelector('button[onclick="clearEvents()"]');
        const exportBtn = document.getElementById('export-btn');

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearEvents();
            });
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportEvents();
            });
        }
    }

    /**
     * Export current events to file
     * Delegates to the event viewer's export functionality
     */
    exportEvents() {
        if (this.eventViewer) {
            this.eventViewer.exportEvents();
        } else {
            console.error('Cannot export events: EventViewer not available');
        }
    }

    /**
     * Clear all events and reset dashboard state
     * This is a coordinated clear that notifies all relevant modules
     */
    clearEvents() {
        // Dispatch event to notify other modules
        document.dispatchEvent(new CustomEvent('eventsClearing'));

        // Clear events from event viewer
        if (this.eventViewer) {
            this.eventViewer.clearEvents();
        }

        // Dispatch event to notify clearing is complete
        document.dispatchEvent(new CustomEvent('eventsCleared'));

        console.log('Events cleared');
    }

    /**
     * Export events with custom filtering
     * @param {Object} options - Export options
     * @param {string} options.format - Export format ('json', 'csv', 'txt')
     * @param {Array} options.events - Events to export (optional, uses all if not provided)
     * @param {string} options.filename - Custom filename (optional)
     */
    exportEventsCustom(options = {}) {
        const {
            format = 'json',
            events = null,
            filename = null
        } = options;

        const eventsToExport = events || (this.eventViewer ? this.eventViewer.events : []);

        if (eventsToExport.length === 0) {
            console.warn('No events to export');
            return;
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const defaultFilename = `claude-mpm-events-${timestamp}`;
        const exportFilename = filename || defaultFilename;

        let content = '';
        let mimeType = '';
        let fileExtension = '';

        switch (format.toLowerCase()) {
            case 'json':
                content = JSON.stringify(eventsToExport, null, 2);
                mimeType = 'application/json';
                fileExtension = '.json';
                break;

            case 'csv':
                content = this.convertEventsToCSV(eventsToExport);
                mimeType = 'text/csv';
                fileExtension = '.csv';
                break;

            case 'txt':
                content = this.convertEventsToText(eventsToExport);
                mimeType = 'text/plain';
                fileExtension = '.txt';
                break;

            default:
                console.error('Unsupported export format:', format);
                return;
        }

        this.downloadFile(content, exportFilename + fileExtension, mimeType);
    }

    /**
     * Convert events to CSV format
     * @param {Array} events - Events to convert
     * @returns {string} - CSV content
     */
    convertEventsToCSV(events) {
        if (events.length === 0) return '';

        // Define CSV headers
        const headers = ['timestamp', 'type', 'subtype', 'tool_name', 'agent_type', 'session_id', 'data'];

        // Convert events to CSV rows
        const rows = events.map(event => {
            return [
                event.timestamp || '',
                event.type || '',
                event.subtype || '',
                event.tool_name || '',
                event.agent_type || '',
                event.session_id || '',
                JSON.stringify(event.data || {}).replace(/"/g, '""') // Escape quotes for CSV
            ];
        });

        // Combine headers and rows
        const csvContent = [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\n');

        return csvContent;
    }

    /**
     * Convert events to readable text format
     * @param {Array} events - Events to convert
     * @returns {string} - Text content
     */
    convertEventsToText(events) {
        if (events.length === 0) return 'No events to export.';

        return events.map((event, index) => {
            const timestamp = this.formatTimestamp(event.timestamp);
            const type = event.type || 'Unknown';
            const subtype = event.subtype ? ` (${event.subtype})` : '';
            const toolName = event.tool_name ? ` - Tool: ${event.tool_name}` : '';
            const agentType = event.agent_type ? ` - Agent: ${event.agent_type}` : '';

            let content = `Event ${index + 1}: ${type}${subtype}${toolName}${agentType}\n`;
            content += `  Time: ${timestamp}\n`;
            content += `  Session: ${event.session_id || 'Unknown'}\n`;

            if (event.data && Object.keys(event.data).length > 0) {
                content += `  Data: ${JSON.stringify(event.data, null, 2)}\n`;
            }

            return content;
        }).join('\n' + '='.repeat(80) + '\n');
    }

    /**
     * Download file with given content
     * @param {string} content - File content
     * @param {string} filename - Filename
     * @param {string} mimeType - MIME type
     */
    downloadFile(content, filename, mimeType) {
        try {
            const blob = new Blob([content], { type: mimeType });
            const url = window.URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Clean up the URL object
            window.URL.revokeObjectURL(url);

            console.log(`File exported: ${filename}`);
        } catch (error) {
            console.error('Failed to export file:', error);
        }
    }

    // =================
    // UTILITY FUNCTIONS
    // =================

    /**
     * Format timestamp for display
     * @param {string|number|Date} timestamp - Timestamp to format
     * @returns {string} - Formatted timestamp
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown time';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                return 'Invalid time';
            }

            return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            console.error('Error formatting timestamp:', error);
            return 'Error formatting time';
        }
    }

    /**
     * Format full timestamp with date for exports
     * @param {string|number|Date} timestamp - Timestamp to format
     * @returns {string} - Formatted full timestamp
     */
    formatFullTimestamp(timestamp) {
        if (!timestamp) return 'Unknown time';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                return 'Invalid time';
            }

            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (error) {
            console.error('Error formatting full timestamp:', error);
            return 'Error formatting time';
        }
    }

    /**
     * Scroll a list element to bottom
     * @param {string} listId - ID of list element to scroll
     */
    scrollListToBottom(listId) {
        console.log(`[DEBUG] scrollListToBottom called with listId: ${listId}`);

        // Use setTimeout to ensure DOM updates are completed
        setTimeout(() => {
            const listElement = document.getElementById(listId);
            console.log(`[DEBUG] Element found for ${listId}:`, listElement);

            if (listElement) {
                console.log(`[DEBUG] Scrolling ${listId} - scrollHeight: ${listElement.scrollHeight}, scrollTop before: ${listElement.scrollTop}`);
                listElement.scrollTop = listElement.scrollHeight;
                console.log(`[DEBUG] Scrolled ${listId} - scrollTop after: ${listElement.scrollTop}`);
            } else {
                console.warn(`[DEBUG] Element with ID '${listId}' not found for scrolling`);
            }
        }, 50); // Small delay to ensure content is rendered
    }

    /**
     * Debounce function to limit function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} - Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle function to limit function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Limit in milliseconds
     * @returns {Function} - Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Generate unique ID
     * @returns {string} - Unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    /**
     * Deep clone an object
     * @param {*} obj - Object to clone
     * @returns {*} - Cloned object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = this.deepClone(obj[key]);
                }
            }
            return cloned;
        }
        return obj;
    }
}
// ES6 Module export
export { ExportManager };
export default ExportManager;
