/**
 * Browser Extension Error Handler
 * 
 * WHY: Browser extensions (like password managers, ad blockers, etc.) often inject
 * scripts that use Chrome's message passing API. When these extensions have bugs
 * or async handlers that don't properly respond, they generate console errors.
 * 
 * This module prevents those external errors from affecting our dashboard and
 * provides clean error handling for known browser extension issues.
 * 
 * DESIGN DECISION: Rather than trying to fix third-party extension bugs, we:
 * 1. Detect and suppress known harmless extension errors
 * 2. Log them separately for debugging if needed
 * 3. Ensure our dashboard remains functional regardless of extension conflicts
 */

class ExtensionErrorHandler {
    constructor() {
        this.extensionErrors = [];
        this.suppressedPatterns = [
            // Chrome extension message passing error
            /listener indicated an asynchronous response.*message channel closed/i,
            // Other common extension errors
            /Extension context invalidated/i,
            /Unchecked runtime\.lastError/i,
            /Cannot access contents of url.*Extension/i,
            /Blocked a frame with origin.*from accessing a cross-origin frame/i
        ];
        
        this.setupErrorHandling();
    }
    
    /**
     * Set up global error handling to catch and suppress extension errors
     */
    setupErrorHandling() {
        // Store original console.error
        const originalConsoleError = console.error;
        
        // Override console.error to filter extension errors
        console.error = (...args) => {
            const errorString = args.join(' ');
            
            // Check if this is a known extension error
            if (this.isExtensionError(errorString)) {
                // Log to our internal list for debugging
                this.extensionErrors.push({
                    timestamp: new Date().toISOString(),
                    error: errorString,
                    suppressed: true
                });
                
                // Optionally log with a prefix if debug mode is enabled
                if (window.DEBUG_EXTENSION_ERRORS) {
                    originalConsoleError.call(console, '[SUPPRESSED EXTENSION ERROR]:', ...args);
                }
                
                // Don't propagate the error
                return;
            }
            
            // Pass through non-extension errors
            originalConsoleError.call(console, ...args);
        };
        
        // Handle uncaught promise rejections that might come from extensions
        window.addEventListener('unhandledrejection', (event) => {
            const errorString = event.reason?.toString() || '';
            
            if (this.isExtensionError(errorString)) {
                // Prevent the default error handling
                event.preventDefault();
                
                this.extensionErrors.push({
                    timestamp: new Date().toISOString(),
                    error: errorString,
                    type: 'unhandled_rejection',
                    suppressed: true
                });
                
                if (window.DEBUG_EXTENSION_ERRORS) {
                    console.warn('[SUPPRESSED EXTENSION REJECTION]:', event.reason);
                }
            }
        });
        
        // Add a global message event listener with proper error handling
        // This prevents our app from being affected by misbehaving extensions
        window.addEventListener('message', (event) => {
            // Only process messages from our own origin
            if (event.origin !== window.location.origin) {
                return;
            }
            
            // Add timeout protection for any async operations
            if (event.data && event.data.requiresResponse) {
                const timeoutId = setTimeout(() => {
                    console.warn('Message handler timeout - no response sent');
                }, 5000);
                
                // Clear timeout when response is sent
                if (event.ports && event.ports[0]) {
                    const originalPostMessage = event.ports[0].postMessage;
                    event.ports[0].postMessage = function(...args) {
                        clearTimeout(timeoutId);
                        return originalPostMessage.apply(this, args);
                    };
                }
            }
        });
    }
    
    /**
     * Check if an error string matches known extension error patterns
     * @param {string} errorString - The error message to check
     * @returns {boolean} - True if this is a known extension error
     */
    isExtensionError(errorString) {
        return this.suppressedPatterns.some(pattern => pattern.test(errorString));
    }
    
    /**
     * Get suppressed extension errors for debugging
     * @returns {Array} - List of suppressed errors
     */
    getSuppressedErrors() {
        return this.extensionErrors;
    }
    
    /**
     * Clear the suppressed errors list
     */
    clearSuppressedErrors() {
        this.extensionErrors = [];
    }
    
    /**
     * Enable or disable debug logging of extension errors
     * @param {boolean} enabled - Whether to enable debug logging
     */
    setDebugMode(enabled) {
        window.DEBUG_EXTENSION_ERRORS = enabled;
        
        if (enabled) {
            console.log('Extension error debug mode enabled. Suppressed errors will be logged with [SUPPRESSED] prefix.');
            console.log('Current suppressed errors:', this.getSuppressedErrors());
        } else {
            console.log('Extension error debug mode disabled. Extension errors will be silently suppressed.');
        }
    }
}

// Create and export singleton instance
const extensionErrorHandler = new ExtensionErrorHandler();

// Add to window for debugging access
window.extensionErrorHandler = extensionErrorHandler;

// Export for ES6 modules
export { ExtensionErrorHandler, extensionErrorHandler };
export default extensionErrorHandler;

// Log initialization
console.log('Extension error handler initialized. Use window.extensionErrorHandler.setDebugMode(true) to see suppressed errors.');