/**
 * DOM Helper Utilities
 * 
 * Common DOM manipulation utilities for dashboard components.
 * Provides safe, consistent methods for element creation and manipulation.
 * 
 * @module dom-helpers
 */

const domHelpers = {
    /**
     * Create an element with attributes and content
     * @param {string} tag - Element tag name
     * @param {Object} attrs - Attributes to set
     * @param {string|Element|Array} content - Element content
     * @returns {HTMLElement} Created element
     */
    createElement(tag, attrs = {}, content = null) {
        const element = document.createElement(tag);
        
        // Set attributes
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(element.style, value);
            } else if (key === 'dataset' && typeof value === 'object') {
                for (const [dataKey, dataValue] of Object.entries(value)) {
                    element.dataset[dataKey] = dataValue;
                }
            } else if (key.startsWith('on') && typeof value === 'function') {
                const eventName = key.slice(2).toLowerCase();
                element.addEventListener(eventName, value);
            } else {
                element.setAttribute(key, value);
            }
        }
        
        // Add content
        if (content !== null) {
            this.setContent(element, content);
        }
        
        return element;
    },

    /**
     * Set element content (supports text, HTML, elements, and arrays)
     * @param {HTMLElement} element - Target element
     * @param {string|Element|Array} content - Content to set
     */
    setContent(element, content) {
        if (typeof content === 'string') {
            element.textContent = content;
        } else if (content instanceof HTMLElement) {
            element.appendChild(content);
        } else if (Array.isArray(content)) {
            content.forEach(item => {
                if (typeof item === 'string') {
                    element.appendChild(document.createTextNode(item));
                } else if (item instanceof HTMLElement) {
                    element.appendChild(item);
                }
            });
        }
    },

    /**
     * Safely query selector with null check
     * @param {string} selector - CSS selector
     * @param {Element} context - Context element (default: document)
     * @returns {Element|null} Found element or null
     */
    query(selector, context = document) {
        try {
            return context.querySelector(selector);
        } catch (e) {
            console.error(`Invalid selector: ${selector}`, e);
            return null;
        }
    },

    /**
     * Safely query all matching elements
     * @param {string} selector - CSS selector
     * @param {Element} context - Context element (default: document)
     * @returns {Array} Array of elements
     */
    queryAll(selector, context = document) {
        try {
            return Array.from(context.querySelectorAll(selector));
        } catch (e) {
            console.error(`Invalid selector: ${selector}`, e);
            return [];
        }
    },

    /**
     * Add classes to element
     * @param {HTMLElement} element - Target element
     * @param {...string} classes - Classes to add
     */
    addClass(element, ...classes) {
        if (element && element.classList) {
            element.classList.add(...classes.filter(c => c));
        }
    },

    /**
     * Remove classes from element
     * @param {HTMLElement} element - Target element
     * @param {...string} classes - Classes to remove
     */
    removeClass(element, ...classes) {
        if (element && element.classList) {
            element.classList.remove(...classes);
        }
    },

    /**
     * Toggle classes on element
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class to toggle
     * @param {boolean} force - Force add (true) or remove (false)
     * @returns {boolean} Whether class is now present
     */
    toggleClass(element, className, force) {
        if (element && element.classList) {
            return element.classList.toggle(className, force);
        }
        return false;
    },

    /**
     * Check if element has class
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class to check
     * @returns {boolean} Whether element has class
     */
    hasClass(element, className) {
        return element && element.classList && element.classList.contains(className);
    },

    /**
     * Set multiple styles on element
     * @param {HTMLElement} element - Target element
     * @param {Object} styles - Style properties and values
     */
    setStyles(element, styles) {
        if (element && element.style && styles) {
            Object.assign(element.style, styles);
        }
    },

    /**
     * Get computed style value
     * @param {HTMLElement} element - Target element
     * @param {string} property - CSS property name
     * @returns {string} Computed style value
     */
    getStyle(element, property) {
        if (element) {
            return window.getComputedStyle(element).getPropertyValue(property);
        }
        return '';
    },

    /**
     * Show element (removes display: none)
     * @param {HTMLElement} element - Element to show
     * @param {string} displayValue - Display value to use (default: '')
     */
    show(element, displayValue = '') {
        if (element && element.style) {
            element.style.display = displayValue;
        }
    },

    /**
     * Hide element (sets display: none)
     * @param {HTMLElement} element - Element to hide
     */
    hide(element) {
        if (element && element.style) {
            element.style.display = 'none';
        }
    },

    /**
     * Toggle element visibility
     * @param {HTMLElement} element - Element to toggle
     * @param {boolean} show - Force show (true) or hide (false)
     */
    toggle(element, show) {
        if (element) {
            if (show === undefined) {
                show = element.style.display === 'none';
            }
            if (show) {
                this.show(element);
            } else {
                this.hide(element);
            }
        }
    },

    /**
     * Remove element from DOM
     * @param {HTMLElement} element - Element to remove
     */
    remove(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    },

    /**
     * Empty element content
     * @param {HTMLElement} element - Element to empty
     */
    empty(element) {
        if (element) {
            while (element.firstChild) {
                element.removeChild(element.firstChild);
            }
        }
    },

    /**
     * Insert element after reference element
     * @param {HTMLElement} newElement - Element to insert
     * @param {HTMLElement} referenceElement - Reference element
     */
    insertAfter(newElement, referenceElement) {
        if (referenceElement && referenceElement.parentNode) {
            referenceElement.parentNode.insertBefore(newElement, referenceElement.nextSibling);
        }
    },

    /**
     * Wrap element with wrapper element
     * @param {HTMLElement} element - Element to wrap
     * @param {HTMLElement} wrapper - Wrapper element
     */
    wrap(element, wrapper) {
        if (element && element.parentNode) {
            element.parentNode.insertBefore(wrapper, element);
            wrapper.appendChild(element);
        }
    },

    /**
     * Get element dimensions
     * @param {HTMLElement} element - Target element
     * @returns {Object} Width and height
     */
    getDimensions(element) {
        if (element) {
            return {
                width: element.offsetWidth,
                height: element.offsetHeight,
                innerWidth: element.clientWidth,
                innerHeight: element.clientHeight
            };
        }
        return { width: 0, height: 0, innerWidth: 0, innerHeight: 0 };
    },

    /**
     * Get element position relative to viewport
     * @param {HTMLElement} element - Target element
     * @returns {Object} Position coordinates
     */
    getPosition(element) {
        if (element) {
            const rect = element.getBoundingClientRect();
            return {
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
                left: rect.left,
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            };
        }
        return { top: 0, right: 0, bottom: 0, left: 0, x: 0, y: 0, width: 0, height: 0 };
    },

    /**
     * Check if element is visible in viewport
     * @param {HTMLElement} element - Element to check
     * @param {boolean} partial - Allow partial visibility
     * @returns {boolean} Whether element is visible
     */
    isInViewport(element, partial = false) {
        if (!element) return false;
        
        const rect = element.getBoundingClientRect();
        const windowHeight = window.innerHeight || document.documentElement.clientHeight;
        const windowWidth = window.innerWidth || document.documentElement.clientWidth;
        
        const vertInView = partial
            ? rect.top < windowHeight && rect.bottom > 0
            : rect.top >= 0 && rect.bottom <= windowHeight;
            
        const horInView = partial
            ? rect.left < windowWidth && rect.right > 0
            : rect.left >= 0 && rect.right <= windowWidth;
        
        return vertInView && horInView;
    },

    /**
     * Smoothly scroll element into view
     * @param {HTMLElement} element - Element to scroll to
     * @param {Object} options - Scroll options
     */
    scrollIntoView(element, options = {}) {
        if (element && element.scrollIntoView) {
            const defaultOptions = {
                behavior: 'smooth',
                block: 'nearest',
                inline: 'nearest'
            };
            element.scrollIntoView({ ...defaultOptions, ...options });
        }
    },

    /**
     * Create DocumentFragment from HTML string
     * @param {string} html - HTML string
     * @returns {DocumentFragment} Document fragment
     */
    createFragment(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content;
    },

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Debounce function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
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
    },

    /**
     * Throttle function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in ms
     * @returns {Function} Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = domHelpers;
} else if (typeof define === 'function' && define.amd) {
    define([], () => domHelpers);
} else {
    window.domHelpers = domHelpers;
}