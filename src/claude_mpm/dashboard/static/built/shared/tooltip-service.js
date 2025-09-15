/**
 * Unified Tooltip Service
 * 
 * Provides a consistent tooltip implementation for all dashboard components.
 * Supports different tooltip types and behaviors.
 * 
 * @module tooltip-service
 */

class TooltipService {
    constructor() {
        this.tooltips = new Map();
        this.defaultOptions = {
            className: 'dashboard-tooltip',
            duration: 200,
            offset: { x: 10, y: -28 },
            hideDelay: 500
        };
    }

    /**
     * Create a new tooltip instance
     * @param {string} id - Unique identifier for the tooltip
     * @param {Object} options - Configuration options
     * @returns {Object} Tooltip instance
     */
    create(id, options = {}) {
        const config = { ...this.defaultOptions, ...options };
        
        // Check if tooltip already exists
        if (this.tooltips.has(id)) {
            return this.tooltips.get(id);
        }

        // Create tooltip element
        const tooltip = d3.select('body').append('div')
            .attr('class', config.className)
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('pointer-events', 'none')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', '#fff')
            .style('padding', '8px 12px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('font-family', 'system-ui, -apple-system, sans-serif')
            .style('z-index', '10000');

        const instance = {
            element: tooltip,
            config,
            show: (event, content) => this.show(tooltip, event, content, config),
            hide: () => this.hide(tooltip, config),
            update: (content) => this.update(tooltip, content),
            destroy: () => this.destroy(id)
        };

        this.tooltips.set(id, instance);
        return instance;
    }

    /**
     * Show a tooltip
     * @param {Object} tooltip - D3 selection of tooltip element
     * @param {Event} event - Mouse event
     * @param {string|Array|Object} content - Content to display
     * @param {Object} config - Configuration options
     */
    show(tooltip, event, content, config) {
        // Cancel any pending hide transition
        tooltip.interrupt();

        // Format content
        const html = this.formatContent(content);
        
        tooltip.html(html)
            .style('left', (event.pageX + config.offset.x) + 'px')
            .style('top', (event.pageY + config.offset.y) + 'px');

        tooltip.transition()
            .duration(config.duration)
            .style('opacity', 0.9);

        // Ensure tooltip stays within viewport
        this.adjustPosition(tooltip, event, config);
    }

    /**
     * Hide a tooltip
     * @param {Object} tooltip - D3 selection of tooltip element
     * @param {Object} config - Configuration options
     */
    hide(tooltip, config) {
        tooltip.transition()
            .duration(config.hideDelay)
            .style('opacity', 0);
    }

    /**
     * Update tooltip content without changing position
     * @param {Object} tooltip - D3 selection of tooltip element
     * @param {string|Array|Object} content - New content
     */
    update(tooltip, content) {
        const html = this.formatContent(content);
        tooltip.html(html);
    }

    /**
     * Format content for display
     * @param {string|Array|Object} content - Content to format
     * @returns {string} HTML string
     */
    formatContent(content) {
        if (typeof content === 'string') {
            return content;
        }

        if (Array.isArray(content)) {
            return content.join('<br>');
        }

        if (typeof content === 'object' && content !== null) {
            const lines = [];
            
            // Handle title
            if (content.title) {
                lines.push(`<strong>${this.escapeHtml(content.title)}</strong>`);
            }

            // Handle fields
            if (content.fields) {
                for (const [key, value] of Object.entries(content.fields)) {
                    if (value !== undefined && value !== null) {
                        lines.push(`${this.escapeHtml(key)}: ${this.escapeHtml(String(value))}`);
                    }
                }
            }

            // Handle description
            if (content.description) {
                lines.push(`<em>${this.escapeHtml(content.description)}</em>`);
            }

            // Handle raw HTML (trusted content only)
            if (content.html) {
                lines.push(content.html);
            }

            return lines.join('<br>');
        }

        return String(content);
    }

    /**
     * Adjust tooltip position to stay within viewport
     * @param {Object} tooltip - D3 selection of tooltip element
     * @param {Event} event - Mouse event
     * @param {Object} config - Configuration options
     */
    adjustPosition(tooltip, event, config) {
        const node = tooltip.node();
        if (!node) return;

        const rect = node.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        let left = event.pageX + config.offset.x;
        let top = event.pageY + config.offset.y;

        // Adjust horizontal position
        if (rect.right > viewportWidth) {
            left = event.pageX - rect.width - config.offset.x;
        }

        // Adjust vertical position
        if (rect.bottom > viewportHeight) {
            top = event.pageY - rect.height - Math.abs(config.offset.y);
        }

        tooltip
            .style('left', left + 'px')
            .style('top', top + 'px');
    }

    /**
     * Destroy a tooltip instance
     * @param {string} id - Tooltip identifier
     */
    destroy(id) {
        const instance = this.tooltips.get(id);
        if (instance) {
            instance.element.remove();
            this.tooltips.delete(id);
        }
    }

    /**
     * Destroy all tooltips
     */
    destroyAll() {
        for (const [id] of this.tooltips) {
            this.destroy(id);
        }
    }

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Create a simple tooltip helper for basic use cases
     * @param {string} selector - CSS selector for target elements
     * @param {Function} contentFn - Function to generate content from data
     * @param {Object} options - Configuration options
     */
    attachToElements(selector, contentFn, options = {}) {
        const id = `tooltip-${selector.replace(/[^a-zA-Z0-9]/g, '-')}`;
        const tooltip = this.create(id, options);

        d3.selectAll(selector)
            .on('mouseenter', function(event, d) {
                const content = contentFn(d, this);
                tooltip.show(event, content);
            })
            .on('mouseleave', function() {
                tooltip.hide();
            });

        return tooltip;
    }
}

// Export as singleton
const tooltipService = new TooltipService();

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = tooltipService;
} else if (typeof define === 'function' && define.amd) {
    define([], () => tooltipService);
} else {
    window.tooltipService = tooltipService;
}