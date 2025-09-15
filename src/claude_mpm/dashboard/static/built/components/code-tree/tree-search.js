/**
 * Tree Search Functionality
 * 
 * Search and filter functionality for the code tree visualization.
 * Provides searching, filtering, and highlighting capabilities.
 * 
 * @module tree-search
 */

class TreeSearch {
    constructor() {
        this.searchTerm = '';
        this.languageFilter = 'all';
        this.complexityFilter = { min: 0, max: 999 };
        this.typeFilter = 'all';
        this.searchHistory = [];
        this.maxHistorySize = 20;
        this.debounceTimer = null;
        this.debounceDelay = 300;
    }

    /**
     * Set search term with optional debouncing
     * @param {string} term - Search term
     * @param {Function} callback - Callback to execute after debounce
     * @param {boolean} immediate - Execute immediately without debounce
     */
    setSearchTerm(term, callback, immediate = false) {
        this.searchTerm = term.toLowerCase();
        
        if (callback) {
            if (immediate) {
                callback(this.searchTerm);
            } else {
                this.debounce(() => callback(this.searchTerm), this.debounceDelay);
            }
        }
        
        // Add to history if not empty and not duplicate
        if (term && this.searchHistory[0] !== term) {
            this.searchHistory.unshift(term);
            if (this.searchHistory.length > this.maxHistorySize) {
                this.searchHistory.pop();
            }
        }
    }

    /**
     * Set language filter
     * @param {string} language - Language to filter by
     */
    setLanguageFilter(language) {
        this.languageFilter = language;
    }

    /**
     * Set complexity filter
     * @param {number} min - Minimum complexity
     * @param {number} max - Maximum complexity
     */
    setComplexityFilter(min, max) {
        this.complexityFilter = { min, max };
    }

    /**
     * Set type filter
     * @param {string} type - Node type to filter by
     */
    setTypeFilter(type) {
        this.typeFilter = type;
    }

    /**
     * Filter tree nodes based on current criteria
     * @param {Object} root - Root node of the tree
     * @returns {Object} Filtered tree structure
     */
    filterTree(root) {
        if (!root) return null;

        // Mark all nodes as visible initially
        this.resetNodeVisibility(root);

        // Apply filters
        root.descendants().forEach(node => {
            const shouldHide = !this.nodeMatchesFilters(node);
            node.data._hidden = shouldHide;
            
            // Mark node for search highlighting
            if (this.searchTerm && !shouldHide) {
                node.data._highlighted = this.nodeMatchesSearch(node);
            } else {
                node.data._highlighted = false;
            }
        });

        // Ensure parent nodes are visible if any child is visible
        this.ensureParentVisibility(root);

        return root;
    }

    /**
     * Check if node matches all active filters
     * @param {Object} node - Node to check
     * @returns {boolean} True if node matches all filters
     */
    nodeMatchesFilters(node) {
        // Language filter
        if (!this.matchesLanguageFilter(node)) {
            return false;
        }

        // Search term filter
        if (!this.matchesSearchTerm(node)) {
            return false;
        }

        // Complexity filter
        if (!this.matchesComplexityFilter(node)) {
            return false;
        }

        // Type filter
        if (!this.matchesTypeFilter(node)) {
            return false;
        }

        return true;
    }

    /**
     * Check if node matches language filter
     * @param {Object} node - Node to check
     * @returns {boolean} True if matches
     */
    matchesLanguageFilter(node) {
        if (this.languageFilter === 'all') {
            return true;
        }
        
        // Check node language
        if (node.data.language === this.languageFilter) {
            return true;
        }
        
        // Check if any children match (for directories)
        if (node.children || node._children) {
            const children = node.children || node._children;
            return children.some(child => this.matchesLanguageFilter(child));
        }
        
        return false;
    }

    /**
     * Check if node matches search term
     * @param {Object} node - Node to check
     * @returns {boolean} True if matches
     */
    matchesSearchTerm(node) {
        if (!this.searchTerm) {
            return true;
        }

        // Check node name
        if (node.data.name && node.data.name.toLowerCase().includes(this.searchTerm)) {
            return true;
        }

        // Check node path
        if (node.data.path && node.data.path.toLowerCase().includes(this.searchTerm)) {
            return true;
        }

        // Check if any children match (for directories)
        if (node.children || node._children) {
            const children = node.children || node._children;
            return children.some(child => this.matchesSearchTerm(child));
        }

        return false;
    }

    /**
     * Check if node matches complexity filter
     * @param {Object} node - Node to check
     * @returns {boolean} True if matches
     */
    matchesComplexityFilter(node) {
        if (node.data.complexity === undefined) {
            return true; // No complexity data, show by default
        }
        
        return node.data.complexity >= this.complexityFilter.min && 
               node.data.complexity <= this.complexityFilter.max;
    }

    /**
     * Check if node matches type filter
     * @param {Object} node - Node to check
     * @returns {boolean} True if matches
     */
    matchesTypeFilter(node) {
        if (this.typeFilter === 'all') {
            return true;
        }
        
        return node.data.type === this.typeFilter;
    }

    /**
     * Check if node matches search (for highlighting)
     * @param {Object} node - Node to check
     * @returns {boolean} True if node should be highlighted
     */
    nodeMatchesSearch(node) {
        if (!this.searchTerm) {
            return false;
        }
        
        const name = (node.data.name || '').toLowerCase();
        return name.includes(this.searchTerm);
    }

    /**
     * Reset visibility flags on all nodes
     * @param {Object} root - Root node
     */
    resetNodeVisibility(root) {
        if (!root) return;
        
        root.descendants().forEach(node => {
            node.data._hidden = false;
            node.data._highlighted = false;
        });
    }

    /**
     * Ensure parent nodes are visible if any child is visible
     * @param {Object} root - Root node
     */
    ensureParentVisibility(root) {
        // Bottom-up traversal to ensure parents are visible
        const checkVisibility = (node) => {
            if (node.children) {
                let hasVisibleChild = false;
                
                node.children.forEach(child => {
                    checkVisibility(child);
                    if (!child.data._hidden) {
                        hasVisibleChild = true;
                    }
                });
                
                // If node has visible children, it must be visible too
                if (hasVisibleChild && node.data._hidden) {
                    node.data._hidden = false;
                }
            }
        };
        
        checkVisibility(root);
    }

    /**
     * Search for nodes by path pattern
     * @param {Object} root - Root node
     * @param {string} pattern - Path pattern (supports wildcards)
     * @returns {Array} Matching nodes
     */
    searchByPath(root, pattern) {
        if (!root || !pattern) return [];
        
        const results = [];
        const regexPattern = this.pathPatternToRegex(pattern);
        
        root.descendants().forEach(node => {
            if (node.data.path && regexPattern.test(node.data.path)) {
                results.push(node);
            }
        });
        
        return results;
    }

    /**
     * Convert path pattern to regex
     * @param {string} pattern - Path pattern with wildcards
     * @returns {RegExp} Regular expression
     */
    pathPatternToRegex(pattern) {
        // Escape special regex characters except * and ?
        const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
        // Replace wildcards
        const regexStr = escaped
            .replace(/\*/g, '.*')  // * matches any characters
            .replace(/\?/g, '.');  // ? matches single character
        
        return new RegExp('^' + regexStr + '$', 'i');
    }

    /**
     * Get search suggestions based on current tree
     * @param {Object} root - Root node
     * @param {string} prefix - Search prefix
     * @returns {Array} Suggested search terms
     */
    getSearchSuggestions(root, prefix = '') {
        if (!root) return [];
        
        const suggestions = new Set();
        const lowerPrefix = prefix.toLowerCase();
        
        root.descendants().forEach(node => {
            if (node.data.name) {
                const name = node.data.name.toLowerCase();
                if (name.startsWith(lowerPrefix)) {
                    suggestions.add(node.data.name);
                }
            }
        });
        
        return Array.from(suggestions).sort().slice(0, 10);
    }

    /**
     * Highlight search results in node labels
     * @param {string} text - Text to highlight
     * @param {string} term - Search term
     * @returns {string} HTML with highlighted term
     */
    highlightSearchTerm(text, term = null) {
        const searchTerm = term || this.searchTerm;
        
        if (!searchTerm || !text) {
            return text;
        }
        
        const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.searchTerm = '';
        this.languageFilter = 'all';
        this.complexityFilter = { min: 0, max: 999 };
        this.typeFilter = 'all';
    }

    /**
     * Get current filter summary
     * @returns {string} Human-readable filter summary
     */
    getFilterSummary() {
        const parts = [];
        
        if (this.searchTerm) {
            parts.push(`Search: "${this.searchTerm}"`);
        }
        if (this.languageFilter !== 'all') {
            parts.push(`Language: ${this.languageFilter}`);
        }
        if (this.typeFilter !== 'all') {
            parts.push(`Type: ${this.typeFilter}`);
        }
        if (this.complexityFilter.min > 0 || this.complexityFilter.max < 999) {
            parts.push(`Complexity: ${this.complexityFilter.min}-${this.complexityFilter.max}`);
        }
        
        return parts.length > 0 ? parts.join(', ') : 'No filters applied';
    }

    /**
     * Debounce function calls
     * @private
     * @param {Function} func - Function to debounce
     * @param {number} delay - Delay in milliseconds
     */
    debounce(func, delay) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(func, delay);
    }

    /**
     * Escape regex special characters
     * @private
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}

// Export as singleton for consistent state
const treeSearch = new TreeSearch();

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = treeSearch;
} else if (typeof define === 'function' && define.amd) {
    define([], () => treeSearch);
} else {
    window.treeSearch = treeSearch;
}