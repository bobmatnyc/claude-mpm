/**
 * Test JavaScript file for Code Viewer functionality.
 * 
 * This file contains various JavaScript constructs to test AST parsing:
 * - Classes
 * - Functions
 * - Arrow functions
 * - Async/await
 * - Modules
 */

// Module imports (for testing)
// import { someFunction } from './other-module.js';

// Constants
const MODULE_CONSTANT = 'test_constant';
const CONFIG = {
    apiUrl: 'http://localhost:8765',
    timeout: 5000,
    retries: 3
};

/**
 * A test class with various methods
 */
class TestClass {
    /**
     * Constructor for TestClass
     * @param {string} name - The name of the instance
     */
    constructor(name) {
        this.name = name;
        this._privateValue = 0;
    }

    /**
     * Getter for private value
     * @returns {number} The private value
     */
    get privateValue() {
        return this._privateValue;
    }

    /**
     * Setter for private value
     * @param {number} value - The new value
     */
    set privateValue(value) {
        this._privateValue = value;
    }

    /**
     * A public method
     * @param {string} param - Parameter for the method
     * @returns {string} Formatted string
     */
    publicMethod(param) {
        return `Hello ${param} from ${this.name}`;
    }

    /**
     * A private method (convention)
     * @private
     */
    _privateMethod() {
        // Private implementation
    }

    /**
     * A static method
     * @param {number} x - First number
     * @param {number} y - Second number
     * @returns {number} Sum of x and y
     */
    static staticMethod(x, y) {
        return x + y;
    }

    /**
     * An async method
     * @param {number} delay - Delay in milliseconds
     * @returns {Promise<string>} Promise resolving to a string
     */
    async asyncMethod(delay = 1000) {
        await new Promise(resolve => setTimeout(resolve, delay));
        return 'Async operation completed';
    }
}

/**
 * A simple function
 * @param {number} a - First number
 * @param {number} b - Second number
 * @returns {number} Sum of a and b
 */
function simpleFunction(a, b) {
    return a + b;
}

/**
 * An arrow function
 */
const arrowFunction = (x, y) => x * y;

/**
 * An async function
 * @param {string} url - URL to fetch
 * @returns {Promise<Object>} Promise resolving to parsed JSON
 */
async function asyncFunction(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

/**
 * A complex function with nested logic
 * @param {Array<Object>} data - Array of data objects
 * @returns {Object} Grouped data by category
 */
function complexFunction(data) {
    const result = {};
    
    data.forEach(item => {
        const category = item.category || 'unknown';
        if (!result[category]) {
            result[category] = [];
        }
        
        if (item.name) {
            result[category].push(item.name);
        }
    });
    
    return result;
}

/**
 * Higher-order function example
 * @param {Function} fn - Function to wrap
 * @returns {Function} Wrapped function
 */
function withLogging(fn) {
    return function(...args) {
        console.log(`Calling ${fn.name} with args:`, args);
        const result = fn.apply(this, args);
        console.log(`${fn.name} returned:`, result);
        return result;
    };
}

// Function expressions
const functionExpression = function(x) {
    return x * 2;
};

// IIFE (Immediately Invoked Function Expression)
const moduleResult = (function() {
    const privateVar = 'private';
    
    return {
        getPrivate: () => privateVar,
        publicMethod: function() {
            return 'public';
        }
    };
})();

// Array methods and functional programming
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(x => x * 2);
const evens = numbers.filter(x => x % 2 === 0);
const sum = numbers.reduce((acc, x) => acc + x, 0);

// Object destructuring and spread
const { apiUrl, timeout } = CONFIG;
const newConfig = { ...CONFIG, debug: true };

// Template literals
const message = `API URL: ${apiUrl}, Timeout: ${timeout}ms`;

// Export (for testing module syntax)
// export { TestClass, simpleFunction, asyncFunction };
// export default TestClass;

// Main execution (if this were a script)
if (typeof window === 'undefined') {
    // Node.js environment
    console.log('Running in Node.js');
    
    const testInstance = new TestClass('TestInstance');
    console.log(testInstance.publicMethod('World'));
    
    const testData = [
        { name: 'item1', category: 'A' },
        { name: 'item2', category: 'B' },
        { name: 'item3', category: 'A' }
    ];
    
    const grouped = complexFunction(testData);
    console.log(grouped);
} else {
    // Browser environment
    console.log('Running in browser');
}
