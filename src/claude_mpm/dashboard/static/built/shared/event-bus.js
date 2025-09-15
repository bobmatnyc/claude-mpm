/**
 * Event Bus Service
 * 
 * Central event management for decoupled component communication.
 * Implements a simple pub/sub pattern for dashboard components.
 * 
 * @module event-bus
 */

class EventBus {
    constructor() {
        this.events = new Map();
        this.onceEvents = new Map();
        this.eventHistory = [];
        this.maxHistorySize = 100;
        this.debugMode = false;
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {Function} handler - Event handler function
     * @param {Object} options - Subscription options
     * @returns {Function} Unsubscribe function
     */
    on(event, handler, options = {}) {
        if (typeof handler !== 'function') {
            throw new Error('Handler must be a function');
        }

        // Initialize event handlers array if needed
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }

        // Create handler wrapper with context and priority
        const wrapper = {
            handler,
            context: options.context || null,
            priority: options.priority || 0,
            id: this.generateId()
        };

        // Add to handlers array (sorted by priority)
        const handlers = this.events.get(event);
        handlers.push(wrapper);
        handlers.sort((a, b) => b.priority - a.priority);

        // Log subscription if debugging
        if (this.debugMode) {
            console.log(`[EventBus] Subscribed to "${event}" with handler ${wrapper.id}`);
        }

        // Return unsubscribe function
        return () => this.off(event, wrapper.id);
    }

    /**
     * Subscribe to an event only once
     * @param {string} event - Event name
     * @param {Function} handler - Event handler function
     * @param {Object} options - Subscription options
     * @returns {Function} Unsubscribe function
     */
    once(event, handler, options = {}) {
        const wrappedHandler = (...args) => {
            handler(...args);
            this.off(event, wrappedHandler);
        };
        wrappedHandler._originalHandler = handler;
        return this.on(event, wrappedHandler, options);
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {string|Function} handlerOrId - Handler function or ID
     */
    off(event, handlerOrId) {
        if (!this.events.has(event)) {
            return;
        }

        const handlers = this.events.get(event);
        const index = handlers.findIndex(wrapper => 
            wrapper.id === handlerOrId || 
            wrapper.handler === handlerOrId ||
            wrapper.handler._originalHandler === handlerOrId
        );

        if (index !== -1) {
            const removed = handlers.splice(index, 1)[0];
            if (this.debugMode) {
                console.log(`[EventBus] Unsubscribed from "${event}" handler ${removed.id}`);
            }
        }

        // Clean up empty event arrays
        if (handlers.length === 0) {
            this.events.delete(event);
        }
    }

    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {...any} args - Arguments to pass to handlers
     * @returns {Array} Results from all handlers
     */
    emit(event, ...args) {
        const results = [];

        // Record in history
        this.recordEvent(event, args);

        // Log emission if debugging
        if (this.debugMode) {
            console.log(`[EventBus] Emitting "${event}" with args:`, args);
        }

        // Call handlers for this specific event
        if (this.events.has(event)) {
            const handlers = this.events.get(event).slice(); // Clone to prevent modification during iteration
            for (const wrapper of handlers) {
                try {
                    const result = wrapper.context
                        ? wrapper.handler.call(wrapper.context, ...args)
                        : wrapper.handler(...args);
                    results.push(result);
                } catch (error) {
                    console.error(`[EventBus] Error in handler for "${event}":`, error);
                    if (this.debugMode) {
                        console.error('Handler details:', wrapper);
                    }
                }
            }
        }

        // Call wildcard handlers
        if (this.events.has('*')) {
            const wildcardHandlers = this.events.get('*').slice();
            for (const wrapper of wildcardHandlers) {
                try {
                    const result = wrapper.context
                        ? wrapper.handler.call(wrapper.context, event, ...args)
                        : wrapper.handler(event, ...args);
                    results.push(result);
                } catch (error) {
                    console.error(`[EventBus] Error in wildcard handler for "${event}":`, error);
                }
            }
        }

        return results;
    }

    /**
     * Emit an event asynchronously
     * @param {string} event - Event name
     * @param {...any} args - Arguments to pass to handlers
     * @returns {Promise<Array>} Promise resolving to results from all handlers
     */
    async emitAsync(event, ...args) {
        return new Promise(resolve => {
            setTimeout(() => {
                resolve(this.emit(event, ...args));
            }, 0);
        });
    }

    /**
     * Wait for an event to occur
     * @param {string} event - Event name to wait for
     * @param {number} timeout - Timeout in milliseconds (optional)
     * @returns {Promise} Promise resolving when event occurs
     */
    waitFor(event, timeout) {
        return new Promise((resolve, reject) => {
            let timeoutId;
            
            const handler = (...args) => {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                resolve(args);
            };

            this.once(event, handler);

            if (timeout) {
                timeoutId = setTimeout(() => {
                    this.off(event, handler);
                    reject(new Error(`Timeout waiting for event "${event}"`));
                }, timeout);
            }
        });
    }

    /**
     * Clear all handlers for an event
     * @param {string} event - Event name (optional, clears all if not provided)
     */
    clear(event) {
        if (event) {
            this.events.delete(event);
            if (this.debugMode) {
                console.log(`[EventBus] Cleared all handlers for "${event}"`);
            }
        } else {
            this.events.clear();
            if (this.debugMode) {
                console.log('[EventBus] Cleared all event handlers');
            }
        }
    }

    /**
     * Get all registered events
     * @returns {Array} Array of event names
     */
    getEvents() {
        return Array.from(this.events.keys());
    }

    /**
     * Get handler count for an event
     * @param {string} event - Event name
     * @returns {number} Number of handlers
     */
    getHandlerCount(event) {
        return this.events.has(event) ? this.events.get(event).length : 0;
    }

    /**
     * Check if event has handlers
     * @param {string} event - Event name
     * @returns {boolean} Whether event has handlers
     */
    hasHandlers(event) {
        return this.getHandlerCount(event) > 0;
    }

    /**
     * Enable or disable debug mode
     * @param {boolean} enabled - Debug mode state
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        if (enabled) {
            console.log('[EventBus] Debug mode enabled');
        }
    }

    /**
     * Get event history
     * @param {string} event - Optional event name filter
     * @returns {Array} Event history
     */
    getHistory(event) {
        if (event) {
            return this.eventHistory.filter(entry => entry.event === event);
        }
        return this.eventHistory.slice();
    }

    /**
     * Clear event history
     */
    clearHistory() {
        this.eventHistory = [];
    }

    /**
     * Record event in history
     * @private
     * @param {string} event - Event name
     * @param {Array} args - Event arguments
     */
    recordEvent(event, args) {
        this.eventHistory.push({
            event,
            args: args.slice(),
            timestamp: Date.now()
        });

        // Limit history size
        if (this.eventHistory.length > this.maxHistorySize) {
            this.eventHistory.shift();
        }
    }

    /**
     * Generate unique ID
     * @private
     * @returns {string} Unique ID
     */
    generateId() {
        return `handler_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Create a scoped event bus
     * @param {string} scope - Scope prefix
     * @returns {Object} Scoped event bus interface
     */
    createScope(scope) {
        const prefix = scope + ':';
        return {
            on: (event, handler, options) => this.on(prefix + event, handler, options),
            once: (event, handler, options) => this.once(prefix + event, handler, options),
            off: (event, handler) => this.off(prefix + event, handler),
            emit: (event, ...args) => this.emit(prefix + event, ...args),
            emitAsync: (event, ...args) => this.emitAsync(prefix + event, ...args),
            clear: (event) => this.clear(event ? prefix + event : undefined),
            hasHandlers: (event) => this.hasHandlers(prefix + event)
        };
    }
}

// Create singleton instance
const eventBus = new EventBus();

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = eventBus;
} else if (typeof define === 'function' && define.amd) {
    define([], () => eventBus);
} else {
    window.eventBus = eventBus;
}