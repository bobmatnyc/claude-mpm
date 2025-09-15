/**
 * Logger Service
 * 
 * Centralized logging service with levels, formatting, and performance timing.
 * Provides consistent logging across dashboard components.
 * 
 * @module logger
 */

class Logger {
    constructor() {
        this.logLevels = {
            DEBUG: 0,
            INFO: 1,
            WARN: 2,
            ERROR: 3,
            NONE: 4
        };
        
        this.currentLevel = this.logLevels.INFO;
        this.enableTimestamps = true;
        this.enableColors = true;
        this.logHistory = [];
        this.maxHistorySize = 500;
        this.performanceMarks = new Map();
        this.componentLoggers = new Map();
    }

    /**
     * Set the current log level
     * @param {string|number} level - Log level name or value
     */
    setLevel(level) {
        if (typeof level === 'string') {
            level = level.toUpperCase();
            if (level in this.logLevels) {
                this.currentLevel = this.logLevels[level];
            }
        } else if (typeof level === 'number') {
            this.currentLevel = level;
        }
    }

    /**
     * Create a logger for a specific component
     * @param {string} componentName - Name of the component
     * @returns {Object} Component logger instance
     */
    createComponentLogger(componentName) {
        if (this.componentLoggers.has(componentName)) {
            return this.componentLoggers.get(componentName);
        }

        const componentLogger = {
            debug: (...args) => this.debug(`[${componentName}]`, ...args),
            info: (...args) => this.info(`[${componentName}]`, ...args),
            warn: (...args) => this.warn(`[${componentName}]`, ...args),
            error: (...args) => this.error(`[${componentName}]`, ...args),
            time: (label) => this.time(`${componentName}:${label}`),
            timeEnd: (label) => this.timeEnd(`${componentName}:${label}`),
            group: (label) => this.group(`${componentName}: ${label}`),
            groupEnd: () => this.groupEnd()
        };

        this.componentLoggers.set(componentName, componentLogger);
        return componentLogger;
    }

    /**
     * Debug level logging
     * @param {...any} args - Arguments to log
     */
    debug(...args) {
        if (this.currentLevel <= this.logLevels.DEBUG) {
            this.log('DEBUG', args, '#6c757d');
        }
    }

    /**
     * Info level logging
     * @param {...any} args - Arguments to log
     */
    info(...args) {
        if (this.currentLevel <= this.logLevels.INFO) {
            this.log('INFO', args, '#0d6efd');
        }
    }

    /**
     * Warning level logging
     * @param {...any} args - Arguments to log
     */
    warn(...args) {
        if (this.currentLevel <= this.logLevels.WARN) {
            this.log('WARN', args, '#ffc107');
        }
    }

    /**
     * Error level logging
     * @param {...any} args - Arguments to log
     */
    error(...args) {
        if (this.currentLevel <= this.logLevels.ERROR) {
            this.log('ERROR', args, '#dc3545');
        }
    }

    /**
     * Core logging function
     * @private
     * @param {string} level - Log level
     * @param {Array} args - Arguments to log
     * @param {string} color - Color for the log level
     */
    log(level, args, color) {
        const timestamp = this.enableTimestamps ? new Date().toISOString() : '';
        const prefix = this.formatPrefix(level, timestamp, color);
        
        // Console output
        const method = level === 'ERROR' ? 'error' : level === 'WARN' ? 'warn' : 'log';
        if (this.enableColors && color) {
            console[method](`%c${prefix}`, `color: ${color}; font-weight: bold;`, ...args);
        } else {
            console[method](prefix, ...args);
        }
        
        // Add to history
        this.addToHistory(level, timestamp, args);
    }

    /**
     * Format log prefix
     * @private
     * @param {string} level - Log level
     * @param {string} timestamp - Timestamp
     * @param {string} color - Color
     * @returns {string} Formatted prefix
     */
    formatPrefix(level, timestamp, color) {
        const parts = [];
        if (timestamp) {
            parts.push(`[${timestamp}]`);
        }
        parts.push(`[${level}]`);
        return parts.join(' ');
    }

    /**
     * Add log entry to history
     * @private
     * @param {string} level - Log level
     * @param {string} timestamp - Timestamp
     * @param {Array} args - Log arguments
     */
    addToHistory(level, timestamp, args) {
        this.logHistory.push({
            level,
            timestamp,
            message: args.map(arg => 
                typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
            ).join(' ')
        });
        
        // Limit history size
        if (this.logHistory.length > this.maxHistorySize) {
            this.logHistory.shift();
        }
    }

    /**
     * Start a performance timer
     * @param {string} label - Timer label
     */
    time(label) {
        this.performanceMarks.set(label, {
            start: performance.now(),
            memory: performance.memory ? performance.memory.usedJSHeapSize : null
        });
        this.debug(`Timer started: ${label}`);
    }

    /**
     * End a performance timer and log the result
     * @param {string} label - Timer label
     * @returns {number} Elapsed time in milliseconds
     */
    timeEnd(label) {
        const mark = this.performanceMarks.get(label);
        if (!mark) {
            this.warn(`Timer not found: ${label}`);
            return null;
        }
        
        const elapsed = performance.now() - mark.start;
        const memoryDelta = performance.memory 
            ? performance.memory.usedJSHeapSize - mark.memory 
            : null;
        
        this.performanceMarks.delete(label);
        
        const message = [`Timer ended: ${label} - ${elapsed.toFixed(2)}ms`];
        if (memoryDelta !== null) {
            message.push(`(Memory: ${this.formatBytes(memoryDelta)})`);
        }
        
        this.info(...message);
        return elapsed;
    }

    /**
     * Log a performance mark
     * @param {string} name - Mark name
     */
    mark(name) {
        if (performance.mark) {
            performance.mark(name);
            this.debug(`Performance mark: ${name}`);
        }
    }

    /**
     * Log a performance measure
     * @param {string} name - Measure name
     * @param {string} startMark - Start mark name
     * @param {string} endMark - End mark name
     */
    measure(name, startMark, endMark) {
        if (performance.measure) {
            try {
                performance.measure(name, startMark, endMark);
                const entries = performance.getEntriesByName(name);
                if (entries.length > 0) {
                    const duration = entries[entries.length - 1].duration;
                    this.info(`Performance measure: ${name} - ${duration.toFixed(2)}ms`);
                }
            } catch (error) {
                this.error(`Failed to measure performance: ${error.message}`);
            }
        }
    }

    /**
     * Create a log group
     * @param {string} label - Group label
     */
    group(label) {
        if (console.group) {
            console.group(label);
        }
    }

    /**
     * Create a collapsed log group
     * @param {string} label - Group label
     */
    groupCollapsed(label) {
        if (console.groupCollapsed) {
            console.groupCollapsed(label);
        }
    }

    /**
     * End a log group
     */
    groupEnd() {
        if (console.groupEnd) {
            console.groupEnd();
        }
    }

    /**
     * Log a table
     * @param {Array|Object} data - Data to display as table
     * @param {Array} columns - Optional column names
     */
    table(data, columns) {
        if (console.table) {
            console.table(data, columns);
        }
    }

    /**
     * Clear the console
     */
    clear() {
        if (console.clear) {
            console.clear();
        }
    }

    /**
     * Get log history
     * @param {string} level - Optional level filter
     * @returns {Array} Log history
     */
    getHistory(level) {
        if (level) {
            return this.logHistory.filter(entry => entry.level === level);
        }
        return this.logHistory.slice();
    }

    /**
     * Export log history as text
     * @returns {string} Log history as text
     */
    exportHistory() {
        return this.logHistory
            .map(entry => `${entry.timestamp} [${entry.level}] ${entry.message}`)
            .join('\n');
    }

    /**
     * Clear log history
     */
    clearHistory() {
        this.logHistory = [];
    }

    /**
     * Format bytes for display
     * @private
     * @param {number} bytes - Number of bytes
     * @returns {string} Formatted string
     */
    formatBytes(bytes) {
        const sign = bytes < 0 ? '-' : '+';
        bytes = Math.abs(bytes);
        
        if (bytes === 0) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB'];
        const index = Math.floor(Math.log(bytes) / Math.log(1024));
        const value = bytes / Math.pow(1024, index);
        
        return `${sign}${value.toFixed(2)} ${units[index]}`;
    }

    /**
     * Assert a condition
     * @param {boolean} condition - Condition to assert
     * @param {string} message - Error message if condition is false
     */
    assert(condition, message) {
        if (!condition) {
            this.error(`Assertion failed: ${message}`);
            if (console.trace) {
                console.trace();
            }
        }
    }

    /**
     * Count occurrences
     * @param {string} label - Counter label
     */
    count(label = 'default') {
        if (console.count) {
            console.count(label);
        }
    }

    /**
     * Reset a counter
     * @param {string} label - Counter label
     */
    countReset(label = 'default') {
        if (console.countReset) {
            console.countReset(label);
        }
    }
}

// Create singleton instance
const logger = new Logger();

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = logger;
} else if (typeof define === 'function' && define.amd) {
    define([], () => logger);
} else {
    window.logger = logger;
}