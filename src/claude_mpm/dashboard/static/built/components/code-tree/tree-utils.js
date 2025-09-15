/**
 * Tree Utility Functions
 * 
 * Common utility functions extracted from code-tree.js
 * Provides formatting, file type detection, and other helper functions.
 * 
 * @module tree-utils
 */

const treeUtils = {
    /**
     * Get complexity level from numeric complexity
     * @param {number} complexity - Complexity value
     * @returns {string} Complexity level (low/medium/high)
     */
    getComplexityLevel(complexity) {
        if (complexity <= 5) return 'low';
        if (complexity <= 10) return 'medium';
        return 'high';
    },

    /**
     * Format file size for display
     * @param {number} bytes - Size in bytes
     * @returns {string} Formatted size string
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },

    /**
     * Get file extension from path
     * @param {string} filePath - File path
     * @returns {string} File extension (lowercase)
     */
    getFileExtension(filePath) {
        if (!filePath) return '';
        const parts = filePath.split('.');
        return parts.length > 1 ? parts.pop().toLowerCase() : '';
    },

    /**
     * Get descriptive file type for user messages
     * @param {string} fileName - File name
     * @returns {string} Human-readable file type description
     */
    getFileTypeDescription(fileName) {
        if (!fileName) return 'File';

        const ext = this.getFileExtension(fileName);
        const baseName = fileName.toLowerCase();

        // Special cases
        if (baseName.endsWith('__init__.py')) {
            return 'Python package initialization';
        }
        if (baseName === 'makefile') {
            return 'Build configuration';
        }
        if (baseName.includes('config') || baseName.includes('settings')) {
            return 'Configuration file';
        }
        if (baseName.includes('test') || baseName.includes('spec')) {
            return 'Test file';
        }

        // By extension
        const typeMap = {
            'py': 'Python file',
            'js': 'JavaScript file',
            'ts': 'TypeScript file',
            'jsx': 'React component',
            'tsx': 'React TypeScript component',
            'html': 'HTML document',
            'css': 'Stylesheet',
            'scss': 'SCSS stylesheet',
            'sass': 'Sass stylesheet',
            'less': 'LESS stylesheet',
            'json': 'JSON data',
            'md': 'Markdown document',
            'txt': 'Text file',
            'yml': 'YAML configuration',
            'yaml': 'YAML configuration',
            'xml': 'XML document',
            'sql': 'SQL script',
            'sh': 'Shell script',
            'bash': 'Bash script',
            'toml': 'TOML configuration',
            'ini': 'INI configuration',
            'env': 'Environment variables',
            'dockerfile': 'Docker configuration',
            'makefile': 'Build configuration',
            'gitignore': 'Git ignore rules',
            'readme': 'Documentation'
        };

        return typeMap[ext] || typeMap[baseName] || 'File';
    },

    /**
     * Get file icon based on file type
     * @param {string} filePath - File path
     * @returns {string} Unicode emoji icon
     */
    getFileIcon(filePath) {
        if (!filePath) return '📄';

        const ext = this.getFileExtension(filePath);
        const fileName = filePath.toLowerCase().split('/').pop();
        
        const iconMap = {
            // Programming languages
            'py': '🐍',
            'js': '📜',
            'ts': '📘',
            'jsx': '⚛️',
            'tsx': '⚛️',
            'java': '☕',
            'c': '🔷',
            'cpp': '🔷',
            'cs': '🔷',
            'go': '🐹',
            'rs': '🦀',
            'rb': '💎',
            'php': '🐘',
            'swift': '🦉',
            'kt': '🎯',
            
            // Web files
            'html': '🌐',
            'css': '🎨',
            'scss': '🎨',
            'sass': '🎨',
            'less': '🎨',
            
            // Data files
            'json': '📋',
            'xml': '📰',
            'csv': '📊',
            'sql': '🗃️',
            
            // Documentation
            'md': '📝',
            'txt': '📄',
            'pdf': '📑',
            'doc': '📃',
            'docx': '📃',
            
            // Configuration
            'yml': '⚙️',
            'yaml': '⚙️',
            'toml': '⚙️',
            'ini': '⚙️',
            'env': '🔐',
            
            // Scripts
            'sh': '🐚',
            'bash': '🐚',
            'bat': '🖥️',
            'ps1': '🖥️',
            
            // Special files
            'dockerfile': '🐳',
            'docker-compose.yml': '🐳',
            'makefile': '🔨',
            'package.json': '📦',
            'requirements.txt': '📦',
            'gitignore': '🚫',
            '.gitignore': '🚫',
            'readme': '📖',
            'readme.md': '📖',
            'license': '📜',
            'license.md': '📜'
        };

        // Check full filename first, then extension
        return iconMap[fileName] || iconMap[ext] || '📄';
    },

    /**
     * Count different types of AST elements
     * @param {Array} elements - AST elements
     * @returns {Object} Element counts
     */
    getElementCounts(elements) {
        const counts = {
            classes: 0,
            functions: 0,
            methods: 0,
            total: elements.length
        };

        elements.forEach(elem => {
            if (elem.type === 'class') {
                counts.classes++;
                if (elem.methods) {
                    counts.methods += elem.methods.length;
                }
            } else if (elem.type === 'function') {
                counts.functions++;
            }
        });

        return counts;
    },

    /**
     * Format element counts into a readable summary
     * @param {Object} counts - Element counts
     * @returns {string} Formatted summary
     */
    formatElementSummary(counts) {
        const parts = [];

        if (counts.classes > 0) {
            parts.push(`${counts.classes} class${counts.classes !== 1 ? 'es' : ''}`);
        }
        if (counts.functions > 0) {
            parts.push(`${counts.functions} function${counts.functions !== 1 ? 's' : ''}`);
        }
        if (counts.methods > 0) {
            parts.push(`${counts.methods} method${counts.methods !== 1 ? 's' : ''}`);
        }

        if (parts.length === 0) {
            return 'Structural elements for tree view';
        } else if (parts.length === 1) {
            return parts[0] + ' found';
        } else if (parts.length === 2) {
            return parts.join(' and ') + ' found';
        } else {
            return parts.slice(0, -1).join(', ') + ', and ' + parts[parts.length - 1] + ' found';
        }
    },

    /**
     * Get node type from data
     * @param {Object} node - Node data
     * @returns {string} Node type
     */
    getNodeType(node) {
        if (!node) return 'unknown';
        if (node.type) return node.type;
        if (node.children && node.children.length > 0) return 'directory';
        if (node.path) return 'file';
        return 'unknown';
    },

    /**
     * Check if node is a directory
     * @param {Object} node - Node or node data
     * @returns {boolean} True if directory
     */
    isNodeDirectory(node) {
        if (!node) return false;
        
        // Handle D3 node structure
        if (node.data) {
            node = node.data;
        }
        
        return node.type === 'directory' || 
               node.type === 'folder' || 
               (node.children && node.children.length > 0) ||
               node.isDirectory === true;
    },

    /**
     * Get node icon for tree visualization
     * @param {string} type - Node type
     * @returns {string} Unicode icon
     */
    getNodeIcon(type) {
        const icons = {
            'module': '📦',
            'class': '🏗️',
            'function': '⚡',
            'method': '🔧',
            'property': '📌',
            'directory': '📁',
            'folder': '📁',
            'file': '📄',
            'python': '🐍',
            'javascript': '📜',
            'unknown': '❓'
        };
        return icons[type] || icons['unknown'];
    },

    /**
     * Sort nodes for tree display
     * @param {Array} nodes - Array of nodes
     * @returns {Array} Sorted nodes
     */
    sortNodes(nodes) {
        return nodes.sort((a, b) => {
            // Directories first
            const aIsDir = this.isNodeDirectory(a);
            const bIsDir = this.isNodeDirectory(b);
            
            if (aIsDir && !bIsDir) return -1;
            if (!aIsDir && bIsDir) return 1;
            
            // Then alphabetically
            const aName = (a.name || a.data?.name || '').toLowerCase();
            const bName = (b.name || b.data?.name || '').toLowerCase();
            
            return aName.localeCompare(bName);
        });
    },

    /**
     * Filter nodes based on criteria
     * @param {Array} nodes - Array of nodes
     * @param {Object} criteria - Filter criteria
     * @returns {Array} Filtered nodes
     */
    filterNodes(nodes, criteria = {}) {
        return nodes.filter(node => {
            // Language filter
            if (criteria.language && node.language !== criteria.language) {
                return false;
            }
            
            // Search term filter
            if (criteria.searchTerm) {
                const term = criteria.searchTerm.toLowerCase();
                const name = (node.name || '').toLowerCase();
                const path = (node.path || '').toLowerCase();
                
                if (!name.includes(term) && !path.includes(term)) {
                    return false;
                }
            }
            
            // Complexity filter
            if (criteria.minComplexity && node.complexity < criteria.minComplexity) {
                return false;
            }
            if (criteria.maxComplexity && node.complexity > criteria.maxComplexity) {
                return false;
            }
            
            return true;
        });
    },

    /**
     * Calculate tree statistics
     * @param {Object} node - Root node
     * @returns {Object} Tree statistics
     */
    calculateTreeStats(node) {
        const stats = {
            files: 0,
            directories: 0,
            classes: 0,
            functions: 0,
            methods: 0,
            lines: 0,
            maxDepth: 0
        };

        const traverse = (n, depth = 0) => {
            stats.maxDepth = Math.max(stats.maxDepth, depth);
            
            if (this.isNodeDirectory(n)) {
                stats.directories++;
            } else {
                stats.files++;
            }
            
            if (n.type === 'class') stats.classes++;
            if (n.type === 'function') stats.functions++;
            if (n.type === 'method') stats.methods++;
            if (n.lines) stats.lines += n.lines;
            
            if (n.children) {
                n.children.forEach(child => traverse(child, depth + 1));
            }
        };

        traverse(node);
        return stats;
    },

    /**
     * Get color based on complexity
     * @param {number} complexity - Complexity value
     * @returns {string} Color hex code
     */
    getComplexityColor(complexity) {
        if (!complexity || complexity <= 5) {
            return '#52c41a'; // Green - low complexity
        } else if (complexity <= 10) {
            return '#faad14'; // Orange - medium complexity
        } else {
            return '#f5222d'; // Red - high complexity
        }
    },

    /**
     * Format node path for display
     * @param {Object} node - Node object
     * @returns {string} Formatted path
     */
    formatNodePath(node) {
        const parts = [];
        let current = node;
        
        while (current) {
            if (current.data?.name) {
                parts.unshift(current.data.name);
            } else if (current.name) {
                parts.unshift(current.name);
            }
            current = current.parent;
        }
        
        return parts.join(' / ');
    }
};

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = treeUtils;
} else if (typeof define === 'function' && define.amd) {
    define([], () => treeUtils);
} else {
    window.treeUtils = treeUtils;
}