/**
 * Tree Breadcrumb Navigation
 * 
 * Breadcrumb navigation and status display for the code tree.
 * Provides path navigation and activity status updates.
 * 
 * @module tree-breadcrumb
 */

class TreeBreadcrumb {
    constructor() {
        this.container = null;
        this.pathElement = null;
        this.statusElement = null;
        this.currentPath = '/';
        this.workingDirectory = null;
        this.navigationCallback = null;
        this.maxSegments = 10;
    }

    /**
     * Initialize breadcrumb component
     * @param {string} containerId - Container element ID
     * @param {Object} options - Configuration options
     */
    initialize(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Breadcrumb container not found: ${containerId}`);
            return;
        }

        // Set options
        this.maxSegments = options.maxSegments || 10;
        this.navigationCallback = options.onNavigate || null;

        // Create breadcrumb structure
        this.createBreadcrumbStructure();
    }

    /**
     * Create breadcrumb DOM structure
     */
    createBreadcrumbStructure() {
        // Clear existing content
        this.container.innerHTML = '';

        // Create path navigation
        const pathContainer = document.createElement('div');
        pathContainer.className = 'tree-breadcrumb-path-container';
        
        this.pathElement = document.createElement('div');
        this.pathElement.id = 'tree-breadcrumb-path';
        this.pathElement.className = 'tree-breadcrumb-path';
        pathContainer.appendChild(this.pathElement);

        // Create status/activity display
        const statusContainer = document.createElement('div');
        statusContainer.className = 'tree-breadcrumb-status-container';
        
        this.statusElement = document.createElement('div');
        this.statusElement.id = 'breadcrumb-content';
        this.statusElement.className = 'breadcrumb-content';
        statusContainer.appendChild(this.statusElement);

        // Add to container
        this.container.appendChild(pathContainer);
        this.container.appendChild(statusContainer);
    }

    /**
     * Set working directory
     * @param {string} directory - Working directory path
     */
    setWorkingDirectory(directory) {
        this.workingDirectory = directory;
        this.updatePath(this.currentPath);
    }

    /**
     * Update breadcrumb path
     * @param {string} path - Current navigation path
     */
    updatePath(path) {
        this.currentPath = path || '/';
        
        if (!this.pathElement) return;

        // Clear existing path
        this.pathElement.innerHTML = '';

        if (!this.workingDirectory || 
            this.workingDirectory === 'Loading...' || 
            this.workingDirectory === 'Not selected') {
            this.pathElement.textContent = 'No project selected';
            return;
        }

        // Build path segments
        const segments = this.buildSegments(this.currentPath);
        
        // Create clickable segments
        segments.forEach((segment, index) => {
            if (index > 0) {
                const separator = document.createElement('span');
                separator.className = 'breadcrumb-separator';
                separator.textContent = '/';
                this.pathElement.appendChild(separator);
            }

            const segmentElement = document.createElement('span');
            segmentElement.className = index === segments.length - 1 ? 
                'breadcrumb-segment current' : 'breadcrumb-segment';
            segmentElement.textContent = segment.name;
            
            // Add click handler for non-current segments
            if (index < segments.length - 1) {
                segmentElement.style.cursor = 'pointer';
                segmentElement.addEventListener('click', () => {
                    this.navigateToSegment(segment.path);
                });
                
                // Add hover effect
                segmentElement.addEventListener('mouseenter', () => {
                    segmentElement.classList.add('hover');
                });
                segmentElement.addEventListener('mouseleave', () => {
                    segmentElement.classList.remove('hover');
                });
            }
            
            this.pathElement.appendChild(segmentElement);
        });

        // Add overflow handling for long paths
        this.handlePathOverflow();
    }

    /**
     * Build path segments from current path
     * @param {string} path - Current path
     * @returns {Array} Array of segment objects
     */
    buildSegments(path) {
        const segments = [];
        
        // Add root/project segment
        const projectName = this.workingDirectory.split('/').pop() || 'Root';
        segments.push({
            name: projectName,
            path: '/'
        });

        // Add path segments if not at root
        if (path && path !== '/') {
            const pathParts = path.split('/').filter(p => p.length > 0);
            let currentPath = '';
            
            pathParts.forEach(part => {
                currentPath += '/' + part;
                segments.push({
                    name: part,
                    path: currentPath
                });
            });
        }

        // Truncate if too many segments
        if (segments.length > this.maxSegments) {
            const truncated = [
                segments[0],
                { name: '...', path: null },
                ...segments.slice(-(this.maxSegments - 2))
            ];
            return truncated;
        }

        return segments;
    }

    /**
     * Navigate to a path segment
     * @param {string} path - Path to navigate to
     */
    navigateToSegment(path) {
        if (path === null) return; // Skip ellipsis
        
        this.currentPath = path;
        this.updatePath(path);
        
        // Call navigation callback if provided
        if (this.navigationCallback) {
            this.navigationCallback(path);
        }
        
        // Dispatch custom event
        const event = new CustomEvent('breadcrumbNavigation', {
            detail: { path }
        });
        document.dispatchEvent(event);
    }

    /**
     * Update status/activity message
     * @param {string} message - Status message
     * @param {string} type - Message type (info/success/warning/error)
     */
    updateStatus(message, type = 'info') {
        if (!this.statusElement) return;
        
        this.statusElement.textContent = message;
        this.statusElement.className = `breadcrumb-content breadcrumb-${type}`;
        
        // Add fade animation for status changes
        this.statusElement.style.animation = 'none';
        setTimeout(() => {
            this.statusElement.style.animation = 'fadeIn 0.3s ease-in';
        }, 10);
    }

    /**
     * Update activity ticker with rotating messages
     * @param {string} message - Activity message
     * @param {string} type - Message type
     */
    updateActivityTicker(message, type = 'info') {
        this.updateStatus(message, type);
        
        // Optional: Add to activity history
        if (!this.activityHistory) {
            this.activityHistory = [];
        }
        
        this.activityHistory.push({
            message,
            type,
            timestamp: Date.now()
        });
        
        // Keep only last 100 activities
        if (this.activityHistory.length > 100) {
            this.activityHistory.shift();
        }
    }

    /**
     * Handle path overflow for long paths
     */
    handlePathOverflow() {
        if (!this.pathElement) return;
        
        // Check if path overflows
        if (this.pathElement.scrollWidth > this.pathElement.clientWidth) {
            // Add scroll buttons or implement horizontal scroll
            this.pathElement.style.overflowX = 'auto';
            this.pathElement.classList.add('overflow');
        } else {
            this.pathElement.style.overflowX = 'hidden';
            this.pathElement.classList.remove('overflow');
        }
    }

    /**
     * Show loading state
     * @param {string} message - Loading message
     */
    showLoading(message = 'Loading...') {
        this.updateStatus(message, 'info');
        
        // Add loading spinner if needed
        if (this.statusElement) {
            const spinner = document.createElement('span');
            spinner.className = 'breadcrumb-spinner';
            spinner.innerHTML = ' ⏳';
            this.statusElement.appendChild(spinner);
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        if (this.statusElement) {
            const spinner = this.statusElement.querySelector('.breadcrumb-spinner');
            if (spinner) {
                spinner.remove();
            }
        }
    }

    /**
     * Get current path
     * @returns {string} Current path
     */
    getCurrentPath() {
        return this.currentPath;
    }

    /**
     * Get activity history
     * @returns {Array} Activity history
     */
    getActivityHistory() {
        return this.activityHistory || [];
    }

    /**
     * Clear breadcrumb
     */
    clear() {
        this.currentPath = '/';
        this.workingDirectory = null;
        
        if (this.pathElement) {
            this.pathElement.innerHTML = '';
        }
        
        if (this.statusElement) {
            this.statusElement.textContent = '';
            this.statusElement.className = 'breadcrumb-content';
        }
        
        this.activityHistory = [];
    }

    /**
     * Destroy breadcrumb component
     */
    destroy() {
        this.clear();
        
        if (this.container) {
            this.container.innerHTML = '';
        }
        
        this.container = null;
        this.pathElement = null;
        this.statusElement = null;
        this.navigationCallback = null;
    }
}

// Export as singleton for consistent state
const treeBreadcrumb = new TreeBreadcrumb();

// Support both module and global usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = treeBreadcrumb;
} else if (typeof define === 'function' && define.amd) {
    define([], () => treeBreadcrumb);
} else {
    window.treeBreadcrumb = treeBreadcrumb;
}