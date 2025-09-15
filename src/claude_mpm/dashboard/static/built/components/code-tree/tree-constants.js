/**
 * Tree Constants and Configuration
 * 
 * Constants and default configurations for the code tree visualization.
 * 
 * @module tree-constants
 */

const treeConstants = {
    // Layout dimensions
    DEFAULT_MARGIN: { top: 20, right: 20, bottom: 20, left: 20 },
    DEFAULT_WIDTH: 960,
    DEFAULT_HEIGHT: 600,
    
    // Animation settings
    ANIMATION_DURATION: 750,
    TOOLTIP_FADE_DURATION: 200,
    TOOLTIP_HIDE_DELAY: 500,
    
    // Node visualization
    NODE_RADIUS: {
        DEFAULT: 6,
        SMALL: 4,
        LARGE: 8,
        EXPANDED: 10
    },
    
    // Colors
    COLORS: {
        // Complexity colors
        COMPLEXITY_LOW: '#52c41a',      // Green
        COMPLEXITY_MEDIUM: '#faad14',   // Orange
        COMPLEXITY_HIGH: '#f5222d',      // Red
        
        // Node state colors
        NODE_DEFAULT: '#69b7ff',
        NODE_SELECTED: '#1890ff',
        NODE_HOVER: '#40a9ff',
        NODE_LOADING: '#ffc53d',
        NODE_ERROR: '#ff4d4f',
        
        // Link colors
        LINK_DEFAULT: '#d9d9d9',
        LINK_SELECTED: '#1890ff',
        
        // Text colors
        TEXT_PRIMARY: '#262626',
        TEXT_SECONDARY: '#8c8c8c',
        TEXT_DISABLED: '#bfbfbf'
    },
    
    // Tree layout
    TREE_LAYOUT: {
        NODE_SIZE: [100, 40],
        SEPARATION: (a, b) => (a.parent === b.parent ? 1 : 2),
        RADIAL_SEPARATION: (a, b) => (a.parent === b.parent ? 1 : 2) / a.depth
    },
    
    // File type mappings
    LANGUAGE_EXTENSIONS: {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'jsx': 'javascript',
        'tsx': 'typescript',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'cs': 'csharp',
        'go': 'go',
        'rs': 'rust',
        'rb': 'ruby',
        'php': 'php',
        'swift': 'swift',
        'kt': 'kotlin',
        'scala': 'scala',
        'r': 'r',
        'lua': 'lua',
        'dart': 'dart',
        'html': 'html',
        'css': 'css',
        'scss': 'scss',
        'sass': 'sass',
        'less': 'less',
        'json': 'json',
        'xml': 'xml',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'ini': 'ini',
        'sql': 'sql',
        'sh': 'shell',
        'bash': 'bash',
        'ps1': 'powershell',
        'bat': 'batch',
        'md': 'markdown'
    },
    
    // Default filters
    DEFAULT_FILTERS: {
        language: 'all',
        searchTerm: '',
        minComplexity: 0,
        maxComplexity: 999,
        showHidden: false
    },
    
    // API endpoints
    API_ENDPOINTS: {
        FILE_READ: '/api/file/read',
        ANALYZE_FILE: '/api/analyze/file',
        ANALYZE_DIRECTORY: '/api/analyze/directory',
        SEARCH: '/api/search'
    },
    
    // WebSocket events
    SOCKET_EVENTS: {
        CONNECT: 'connect',
        DISCONNECT: 'disconnect',
        CODE_UPDATE: 'code_update',
        ANALYSIS_START: 'analysis_start',
        ANALYSIS_PROGRESS: 'analysis_progress',
        ANALYSIS_COMPLETE: 'analysis_complete',
        ANALYSIS_ERROR: 'analysis_error',
        FILE_SELECTED: 'file_selected',
        NODE_EXPANDED: 'node_expanded',
        NODE_COLLAPSED: 'node_collapsed'
    },
    
    // Messages
    MESSAGES: {
        NO_WORKING_DIR: 'Please select a working directory to view the code tree',
        LOADING: 'Loading code tree...',
        ANALYZING: 'Analyzing code structure...',
        NO_DATA: 'No code structure data available',
        ERROR: 'Error loading code tree',
        EMPTY_DIR: 'Directory is empty',
        NO_RESULTS: 'No matching files found',
        CLICK_TO_EXPLORE: 'Click to explore contents',
        CLICK_TO_ANALYZE: 'Click to analyze file'
    },
    
    // Performance thresholds
    PERFORMANCE: {
        MAX_NODES_RENDER: 1000,
        MAX_NODES_EXPAND: 100,
        DEBOUNCE_SEARCH: 300,
        DEBOUNCE_RESIZE: 150,
        CACHE_TTL: 300000  // 5 minutes
    },
    
    // Icon mappings
    ICONS: {
        // Node type icons
        MODULE: '📦',
        CLASS: '🏗️',
        FUNCTION: '⚡',
        METHOD: '🔧',
        PROPERTY: '📌',
        VARIABLE: '📍',
        DIRECTORY: '📁',
        FILE: '📄',
        
        // State icons
        LOADING: '⏳',
        ERROR: '❌',
        WARNING: '⚠️',
        SUCCESS: '✅',
        
        // Action icons
        EXPAND: '▶',
        COLLAPSE: '▼',
        SEARCH: '🔍',
        FILTER: '🔽',
        REFRESH: '🔄',
        SETTINGS: '⚙️'
    },
    
    // CSS classes
    CSS_CLASSES: {
        // Container classes
        CONTAINER: 'code-tree-container',
        SVG: 'code-tree-svg',
        GROUP: 'code-tree-group',
        
        // Node classes
        NODE: 'tree-node',
        NODE_SELECTED: 'tree-node-selected',
        NODE_HOVER: 'tree-node-hover',
        NODE_LOADING: 'tree-node-loading',
        NODE_ERROR: 'tree-node-error',
        
        // Link classes
        LINK: 'tree-link',
        LINK_SELECTED: 'tree-link-selected',
        
        // Text classes
        LABEL: 'tree-label',
        LABEL_PRIMARY: 'tree-label-primary',
        LABEL_SECONDARY: 'tree-label-secondary',
        
        // Tooltip classes
        TOOLTIP: 'code-tree-tooltip',
        TOOLTIP_VISIBLE: 'code-tree-tooltip-visible',
        
        // Control classes
        CONTROLS: 'tree-controls',
        CONTROL_BTN: 'tree-control-btn',
        CONTROL_ACTIVE: 'tree-control-active'
    }
};

// Freeze constants to prevent modification
Object.freeze(treeConstants);
Object.freeze(treeConstants.DEFAULT_MARGIN);
Object.freeze(treeConstants.NODE_RADIUS);
Object.freeze(treeConstants.COLORS);
Object.freeze(treeConstants.TREE_LAYOUT);
Object.freeze(treeConstants.LANGUAGE_EXTENSIONS);
Object.freeze(treeConstants.DEFAULT_FILTERS);
Object.freeze(treeConstants.API_ENDPOINTS);
Object.freeze(treeConstants.SOCKET_EVENTS);
Object.freeze(treeConstants.MESSAGES);
Object.freeze(treeConstants.PERFORMANCE);
Object.freeze(treeConstants.ICONS);
Object.freeze(treeConstants.CSS_CLASSES);

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = treeConstants;
} else if (typeof define === 'function' && define.amd) {
    define([], () => treeConstants);
} else {
    window.treeConstants = treeConstants;
}