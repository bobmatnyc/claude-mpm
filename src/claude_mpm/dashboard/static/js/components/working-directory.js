/**
 * Working Directory Module
 *
 * Manages working directory state, session-specific directory tracking,
 * and git branch monitoring for the dashboard.
 *
 * WHY: Extracted from main dashboard to isolate working directory management
 * logic that involves coordination between UI updates, local storage persistence,
 * and git integration. This provides better maintainability for directory state.
 *
 * DESIGN DECISION: Maintains per-session working directories with persistence
 * in localStorage, provides git branch integration, and coordinates with
 * footer directory display for consistent state management.
 */
class WorkingDirectoryManager {
    constructor(socketManager) {
        this.socketManager = socketManager;
        this.currentWorkingDir = null;
        this.footerDirObserver = null;
        this._updatingFooter = false;

        this.setupEventHandlers();
        this.initialize();

        console.log('Working directory manager initialized');
    }

    /**
     * Initialize working directory management
     */
    initialize() {
        this.initializeWorkingDirectory();
        this.watchFooterDirectory();
    }

    /**
     * Set up event handlers for working directory controls
     */
    setupEventHandlers() {
        const changeDirBtn = document.getElementById('change-dir-btn');
        const workingDirPath = document.getElementById('working-dir-path');

        if (changeDirBtn) {
            changeDirBtn.addEventListener('click', () => {
                this.showChangeDirDialog();
            });
        }

        if (workingDirPath) {
            workingDirPath.addEventListener('click', (e) => {
                // Check if Shift key is held for directory change, otherwise show file viewer
                if (e.shiftKey) {
                    this.showChangeDirDialog();
                } else {
                    this.showWorkingDirectoryViewer();
                }
            });
        }

        // Listen for session changes to update working directory
        document.addEventListener('sessionChanged', (e) => {
            const sessionId = e.detail.sessionId;
            console.log('[WORKING-DIR-DEBUG] sessionChanged event received, sessionId:', this.repr(sessionId));
            if (sessionId) {
                this.loadWorkingDirectoryForSession(sessionId);
            }
        });

        // Listen for git branch responses
        if (this.socketManager && this.socketManager.getSocket) {
            const socket = this.socketManager.getSocket();
            if (socket) {
                console.log('[WORKING-DIR-DEBUG] Setting up git_branch_response listener');
                socket.on('git_branch_response', (response) => {
                    console.log('[GIT-BRANCH-DEBUG] Received git_branch_response:', response);
                    this.handleGitBranchResponse(response);
                });
            }
        }
    }

    /**
     * Initialize working directory for current session
     */
    initializeWorkingDirectory() {
        // Set initial loading state to prevent early Git requests
        const pathElement = document.getElementById('working-dir-path');
        if (pathElement && !pathElement.textContent.trim()) {
            pathElement.textContent = 'Loading...';
        }

        // Check if there's a selected session
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value && sessionSelect.value !== 'all') {
            // Load working directory for selected session
            this.loadWorkingDirectoryForSession(sessionSelect.value);
        } else {
            // Use default working directory
            this.setWorkingDirectory(this.getDefaultWorkingDir());
        }
    }

    /**
     * Watch footer directory for changes and sync working directory
     */
    watchFooterDirectory() {
        const footerDir = document.getElementById('footer-working-dir');
        if (!footerDir) return;

        // Store observer reference for later use
        this.footerDirObserver = new MutationObserver((mutations) => {
            // Skip if we're updating from setWorkingDirectory
            if (this._updatingFooter) return;

            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const newDir = footerDir.textContent.trim();
                    console.log('Footer directory changed to:', newDir);

                    // Only update if it's different from current
                    if (newDir && newDir !== this.currentWorkingDir) {
                        console.log('Syncing working directory from footer change');
                        this.setWorkingDirectory(newDir);
                    }
                }
            });
        });

        // Observe changes to footer directory
        this.footerDirObserver.observe(footerDir, {
            childList: true,
            characterData: true,
            subtree: true
        });

        console.log('Started watching footer directory for changes');
    }

    /**
     * Load working directory for a specific session
     * @param {string} sessionId - Session ID
     */
    loadWorkingDirectoryForSession(sessionId) {
        console.log('[WORKING-DIR-DEBUG] loadWorkingDirectoryForSession called with sessionId:', this.repr(sessionId));

        if (!sessionId || sessionId === 'all') {
            console.log('[WORKING-DIR-DEBUG] No sessionId or sessionId is "all", using default working dir');
            const defaultDir = this.getDefaultWorkingDir();
            console.log('[WORKING-DIR-DEBUG] Default working dir:', this.repr(defaultDir));
            this.setWorkingDirectory(defaultDir);
            return;
        }

        // Load from localStorage
        const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
        console.log('[WORKING-DIR-DEBUG] Session directories from localStorage:', sessionDirs);

        const sessionDir = sessionDirs[sessionId];
        const defaultDir = this.getDefaultWorkingDir();
        const dir = sessionDir || defaultDir;

        console.log('[WORKING-DIR-DEBUG] Directory selection:', {
            sessionId: sessionId,
            sessionDir: this.repr(sessionDir),
            defaultDir: this.repr(defaultDir),
            finalDir: this.repr(dir)
        });

        this.setWorkingDirectory(dir);
    }

    /**
     * Set the working directory for the current session
     * @param {string} dir - Directory path
     */
    setWorkingDirectory(dir) {
        console.log('[WORKING-DIR-DEBUG] setWorkingDirectory called with:', this.repr(dir));

        this.currentWorkingDir = dir;
        
        // Store in session storage for persistence during the session
        if (dir && this.validateDirectoryPath(dir)) {
            sessionStorage.setItem('currentWorkingDirectory', dir);
            console.log('[WORKING-DIR-DEBUG] Stored working directory in session storage:', dir);
        }

        // Update UI
        const pathElement = document.getElementById('working-dir-path');
        if (pathElement) {
            console.log('[WORKING-DIR-DEBUG] Updating UI path element to:', dir);
            pathElement.textContent = dir;
        } else {
            console.warn('[WORKING-DIR-DEBUG] working-dir-path element not found');
        }

        // Update footer directory (sync across components)
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir) {
            const currentFooterText = footerDir.textContent;
            console.log('[WORKING-DIR-DEBUG] Footer directory current text:', this.repr(currentFooterText), 'new text:', this.repr(dir));

            if (currentFooterText !== dir) {
                // Set flag to prevent observer from triggering
                this._updatingFooter = true;
                footerDir.textContent = dir;
                console.log('[WORKING-DIR-DEBUG] Updated footer directory to:', dir);

                // Clear flag after a short delay
                setTimeout(() => {
                    this._updatingFooter = false;
                    console.log('[WORKING-DIR-DEBUG] Cleared _updatingFooter flag');
                }, 100);
            } else {
                console.log('[WORKING-DIR-DEBUG] Footer directory already has correct text');
            }
        } else {
            console.warn('[WORKING-DIR-DEBUG] footer-working-dir element not found');
        }

        // Save to localStorage for session persistence
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value && sessionSelect.value !== 'all') {
            const sessionId = sessionSelect.value;
            const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
            sessionDirs[sessionId] = dir;
            localStorage.setItem('sessionWorkingDirs', JSON.stringify(sessionDirs));
            console.log(`[WORKING-DIR-DEBUG] Saved working directory for session ${sessionId}:`, dir);
        } else {
            console.log('[WORKING-DIR-DEBUG] No session selected or session is "all", not saving to localStorage');
        }

        // Update git branch for new directory - only if it's a valid path
        console.log('[WORKING-DIR-DEBUG] About to call updateGitBranch with:', this.repr(dir));
        if (this.validateDirectoryPath(dir)) {
            this.updateGitBranch(dir);
        } else {
            console.log('[WORKING-DIR-DEBUG] Skipping git branch update for invalid directory:', this.repr(dir));
        }

        // Dispatch event for other modules
        document.dispatchEvent(new CustomEvent('workingDirectoryChanged', {
            detail: { directory: dir }
        }));

        console.log('[WORKING-DIR-DEBUG] Working directory set to:', dir);
    }

    /**
     * Update git branch display for current working directory
     * @param {string} dir - Working directory path
     */
    updateGitBranch(dir) {
        console.log('[GIT-BRANCH-DEBUG] updateGitBranch called with dir:', this.repr(dir), 'type:', typeof dir);

        if (!this.socketManager || !this.socketManager.isConnected()) {
            console.log('[GIT-BRANCH-DEBUG] Not connected to socket server');
            // Not connected, set to unknown
            const footerBranch = document.getElementById('footer-git-branch');
            if (footerBranch) {
                footerBranch.textContent = 'Not Connected';
                footerBranch.style.display = 'inline';
            }
            return;
        }

        // Enhanced validation with specific checks for common invalid states
        const isValidPath = this.validateDirectoryPath(dir);
        const isLoadingState = dir === 'Loading...' || dir === 'Loading';
        const isUnknown = dir === 'Unknown';
        const isEmptyOrWhitespace = !dir || (typeof dir === 'string' && dir.trim() === '');

        console.log('[GIT-BRANCH-DEBUG] Validation results:', {
            dir: dir,
            isValidPath: isValidPath,
            isLoadingState: isLoadingState,
            isUnknown: isUnknown,
            isEmptyOrWhitespace: isEmptyOrWhitespace,
            shouldReject: !isValidPath || isLoadingState || isUnknown || isEmptyOrWhitespace
        });

        // Validate directory before sending to server - reject common invalid states
        if (!isValidPath || isLoadingState || isUnknown || isEmptyOrWhitespace) {
            console.warn('[GIT-BRANCH-DEBUG] Invalid working directory for git branch request:', dir);
            const footerBranch = document.getElementById('footer-git-branch');
            if (footerBranch) {
                if (isLoadingState) {
                    footerBranch.textContent = 'Loading...';
                } else if (isUnknown || isEmptyOrWhitespace) {
                    footerBranch.textContent = 'No Directory';
                } else {
                    footerBranch.textContent = 'Invalid Directory';
                }
                footerBranch.style.display = 'inline';
            }
            return;
        }

        // Request git branch from server
        const socket = this.socketManager.getSocket();
        if (socket) {
            console.log('[GIT-BRANCH-DEBUG] Requesting git branch for directory:', dir);
            console.log('[GIT-BRANCH-DEBUG] Socket state:', {
                connected: socket.connected,
                id: socket.id
            });
            // Server expects working_dir as a direct parameter, not as an object
            socket.emit('get_git_branch', dir);
        } else {
            console.error('[GIT-BRANCH-DEBUG] No socket available for git branch request');
        }
    }

    /**
     * Get default working directory
     * @returns {string} - Default directory path
     */
    getDefaultWorkingDir() {
        console.log('[WORKING-DIR-DEBUG] getDefaultWorkingDir called');
        
        // Try to get from the current working directory if set
        if (this.currentWorkingDir && this.validateDirectoryPath(this.currentWorkingDir)) {
            console.log('[WORKING-DIR-DEBUG] Using current working directory:', this.currentWorkingDir);
            return this.currentWorkingDir;
        }
        
        // Try to get from header display
        const headerWorkingDir = document.querySelector('.working-dir-text');
        if (headerWorkingDir?.textContent?.trim()) {
            const headerPath = headerWorkingDir.textContent.trim();
            if (headerPath !== 'Loading...' && headerPath !== 'Unknown' && this.validateDirectoryPath(headerPath)) {
                console.log('[WORKING-DIR-DEBUG] Using header working directory:', headerPath);
                return headerPath;
            }
        }

        // Try to get from footer
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir?.textContent?.trim()) {
            const footerPath = footerDir.textContent.trim();
            console.log('[WORKING-DIR-DEBUG] Footer path found:', this.repr(footerPath));

            // Don't use 'Unknown' as a valid directory
            const isUnknown = footerPath === 'Unknown';
            const isValid = this.validateDirectoryPath(footerPath);

            console.log('[WORKING-DIR-DEBUG] Footer path validation:', {
                footerPath: this.repr(footerPath),
                isUnknown: isUnknown,
                isValid: isValid,
                shouldUse: !isUnknown && isValid
            });

            if (!isUnknown && isValid) {
                console.log('[WORKING-DIR-DEBUG] Using footer path as default:', footerPath);
                return footerPath;
            }
        } else {
            console.log('[WORKING-DIR-DEBUG] No footer directory element or no text content');
        }

        // Fallback to a reasonable default - try to get the current project directory
        // This should be set when the dashboard initializes

        // Try getting from events that have a working directory
        if (window.socketClient && window.socketClient.events) {
            // Look for the most recent event with a working directory
            const eventsWithDir = window.socketClient.events
                .filter(e => e.data && (e.data.working_directory || e.data.cwd || e.data.working_dir))
                .reverse();
            
            if (eventsWithDir.length > 0) {
                const recentEvent = eventsWithDir[0];
                const dir = recentEvent.data.working_directory || 
                           recentEvent.data.cwd || 
                           recentEvent.data.working_dir;
                console.log('[WORKING-DIR-DEBUG] Using working directory from recent event:', dir);
                return dir;
            }
        }
        const workingDirPath = document.getElementById('working-dir-path');
        if (workingDirPath?.textContent?.trim()) {
            const pathText = workingDirPath.textContent.trim();
            console.log('[WORKING-DIR-DEBUG] Found working-dir-path element text:', this.repr(pathText));
            if (pathText !== 'Unknown' && this.validateDirectoryPath(pathText)) {
                console.log('[WORKING-DIR-DEBUG] Using working-dir-path as fallback:', pathText);
                return pathText;
            }
        }

        // Try to get from session storage or environment
        const sessionWorkingDir = sessionStorage.getItem('currentWorkingDirectory');
        if (sessionWorkingDir && this.validateDirectoryPath(sessionWorkingDir)) {
            console.log('[WORKING-DIR-DEBUG] Using session storage working directory:', this.repr(sessionWorkingDir));
            return sessionWorkingDir;
        }
        
        // Try to get the current working directory from environment/process
        // This should be the directory where claude-mpm was started from
        const processWorkingDir = window.processWorkingDirectory || process?.cwd?.() || null;
        if (processWorkingDir && this.validateDirectoryPath(processWorkingDir)) {
            console.log('[WORKING-DIR-DEBUG] Using process working directory:', this.repr(processWorkingDir));
            return processWorkingDir;
        }
        
        // Final fallback - use current working directory if available, otherwise home directory
        // Never default to root "/" as it's not a useful default for code viewing
        const homeDir = window.homeDirectory || process?.env?.HOME || process?.env?.USERPROFILE || null;
        const fallback = homeDir || process?.cwd?.() || os?.homedir?.() || '/Users/masa';
        console.log('[WORKING-DIR-DEBUG] Using fallback directory (home or cwd):', this.repr(fallback));
        return fallback;
    }

    /**
     * Show change directory dialog
     */
    showChangeDirDialog() {
        const newDir = prompt('Enter new working directory:', this.currentWorkingDir || '');
        if (newDir && newDir.trim() !== '') {
            this.setWorkingDirectory(newDir.trim());
        }
    }

    /**
     * Show working directory file viewer overlay
     * WHY: Provides quick file browsing from the header without opening a full modal
     * DESIGN DECISION: Uses overlay positioned below the blue bar for easy access
     */
    showWorkingDirectoryViewer() {
        // Create or show the directory viewer overlay
        this.createDirectoryViewerOverlay();
    }

    /**
     * Create directory viewer overlay positioned below the working directory display
     * WHY: Positions overlay near the trigger for intuitive user experience
     * without disrupting the main dashboard layout
     */
    createDirectoryViewerOverlay() {
        // Remove existing overlay if present
        this.removeDirectoryViewerOverlay();

        const workingDirDisplay = document.querySelector('.working-dir-display');
        if (!workingDirDisplay) return;

        // Create overlay element
        const overlay = document.createElement('div');
        overlay.id = 'directory-viewer-overlay';
        overlay.className = 'directory-viewer-overlay';

        // Create overlay content
        overlay.innerHTML = `
            <div class="directory-viewer-content">
                <div class="directory-viewer-header">
                    <h3 class="directory-viewer-title">
                        📁 ${this.currentWorkingDir || 'Working Directory'}
                    </h3>
                    <button class="close-btn" onclick="workingDirectoryManager.removeDirectoryViewerOverlay()">✕</button>
                </div>
                <div class="directory-viewer-body">
                    <div class="loading-indicator">Loading directory contents...</div>
                </div>
                <div class="directory-viewer-footer">
                    <span class="directory-hint">Click file to view • Shift+Click directory path to change</span>
                </div>
            </div>
        `;

        // Position overlay below the working directory display
        const rect = workingDirDisplay.getBoundingClientRect();
        overlay.style.cssText = `
            position: fixed;
            top: ${rect.bottom + 5}px;
            left: ${rect.left}px;
            min-width: 400px;
            max-width: 600px;
            max-height: 400px;
            z-index: 1001;
            background: white;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            border: 1px solid #e2e8f0;
        `;

        // Add to document
        document.body.appendChild(overlay);

        // Load directory contents
        this.loadDirectoryContents();

        // Add click outside to close
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick.bind(this), true);
        }, 100);
    }

    /**
     * Remove directory viewer overlay
     */
    removeDirectoryViewerOverlay() {
        const overlay = document.getElementById('directory-viewer-overlay');
        if (overlay) {
            overlay.remove();
            document.removeEventListener('click', this.handleOutsideClick.bind(this), true);
        }
    }

    /**
     * Handle clicks outside the overlay to close it
     * @param {Event} event - Click event
     */
    handleOutsideClick(event) {
        const overlay = document.getElementById('directory-viewer-overlay');
        const workingDirPath = document.getElementById('working-dir-path');

        if (overlay && !overlay.contains(event.target) && event.target !== workingDirPath) {
            this.removeDirectoryViewerOverlay();
        }
    }

    /**
     * Load directory contents using socket connection
     * WHY: Uses existing socket infrastructure to get directory listing
     * without requiring new endpoints
     */
    loadDirectoryContents() {
        if (!this.socketManager || !this.socketManager.isConnected()) {
            this.showDirectoryError('Not connected to server');
            return;
        }

        const socket = this.socketManager.getSocket();
        if (!socket) {
            this.showDirectoryError('No socket connection available');
            return;
        }

        // Request directory listing
        socket.emit('get_directory_listing', {
            directory: this.currentWorkingDir,
            limit: 50 // Reasonable limit for overlay display
        });

        // Listen for response
        const responseHandler = (data) => {
            socket.off('directory_listing_response', responseHandler);
            this.handleDirectoryListingResponse(data);
        };

        socket.on('directory_listing_response', responseHandler);

        // Timeout after 5 seconds
        setTimeout(() => {
            socket.off('directory_listing_response', responseHandler);
            const overlay = document.getElementById('directory-viewer-overlay');
            if (overlay && overlay.querySelector('.loading-indicator')) {
                this.showDirectoryError('Request timeout');
            }
        }, 5000);
    }

    /**
     * Handle directory listing response from server
     * @param {Object} data - Directory listing data
     */
    handleDirectoryListingResponse(data) {
        const bodyElement = document.querySelector('.directory-viewer-body');
        if (!bodyElement) return;

        if (!data.success) {
            this.showDirectoryError(data.error || 'Failed to load directory');
            return;
        }

        // Create file listing
        const files = data.files || [];
        const directories = data.directories || [];

        let html = '';

        // Add parent directory link if not root
        if (this.currentWorkingDir && this.currentWorkingDir !== '/') {
            const parentDir = this.currentWorkingDir.split('/').slice(0, -1).join('/') || '/';
            html += `
                <div class="file-item directory-item" onclick="workingDirectoryManager.setWorkingDirectory('${parentDir}')">
                    <span class="file-icon">📁</span>
                    <span class="file-name">..</span>
                    <span class="file-type">parent directory</span>
                </div>
            `;
        }

        // Add directories
        directories.forEach(dir => {
            const fullPath = `${this.currentWorkingDir}/${dir}`.replace(/\/+/g, '/');
            html += `
                <div class="file-item directory-item" onclick="workingDirectoryManager.setWorkingDirectory('${fullPath}')">
                    <span class="file-icon">📁</span>
                    <span class="file-name">${dir}</span>
                    <span class="file-type">directory</span>
                </div>
            `;
        });

        // Add files
        files.forEach(file => {
            const filePath = `${this.currentWorkingDir}/${file}`.replace(/\/+/g, '/');
            const fileExt = file.split('.').pop().toLowerCase();
            const fileIcon = this.getFileIcon(fileExt);

            html += `
                <div class="file-item" onclick="workingDirectoryManager.viewFile('${filePath}')">
                    <span class="file-icon">${fileIcon}</span>
                    <span class="file-name">${file}</span>
                    <span class="file-type">${fileExt}</span>
                </div>
            `;
        });

        if (html === '') {
            html = '<div class="no-files">Empty directory</div>';
        }

        bodyElement.innerHTML = html;
    }

    /**
     * Show directory error in the overlay
     * @param {string} message - Error message
     */
    showDirectoryError(message) {
        const bodyElement = document.querySelector('.directory-viewer-body');
        if (bodyElement) {
            bodyElement.innerHTML = `
                <div class="directory-error">
                    <span class="error-icon">⚠️</span>
                    <span class="error-message">${message}</span>
                </div>
            `;
        }
    }

    /**
     * Get file icon based on extension
     * @param {string} extension - File extension
     * @returns {string} - File icon emoji
     */
    getFileIcon(extension) {
        const iconMap = {
            'js': '📄',
            'py': '🐍',
            'html': '🌐',
            'css': '🎨',
            'json': '📋',
            'md': '📝',
            'txt': '📝',
            'yml': '⚙️',
            'yaml': '⚙️',
            'xml': '📄',
            'pdf': '📕',
            'png': '🖼️',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'gif': '🖼️',
            'svg': '🖼️',
            'zip': '📦',
            'tar': '📦',
            'gz': '📦',
            'sh': '🔧',
            'bat': '🔧',
            'exe': '⚙️',
            'dll': '⚙️'
        };

        return iconMap[extension] || '📄';
    }

    /**
     * View a file using the existing file viewer modal
     * @param {string} filePath - Path to the file to view
     */
    viewFile(filePath) {
        // Close the directory viewer overlay
        this.removeDirectoryViewerOverlay();

        // Use the existing file viewer modal functionality
        if (window.showFileViewerModal) {
            window.showFileViewerModal(filePath);
        } else {
            console.warn('File viewer modal function not available');
        }
    }

    /**
     * Get current working directory
     * @returns {string} - Current working directory
     */
    getCurrentWorkingDir() {
        return this.currentWorkingDir;
    }

    /**
     * Get session working directories from localStorage
     * @returns {Object} - Session directories mapping
     */
    getSessionDirectories() {
        return JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
    }

    /**
     * Set working directory for a specific session
     * @param {string} sessionId - Session ID
     * @param {string} directory - Directory path
     */
    setSessionDirectory(sessionId, directory) {
        const sessionDirs = this.getSessionDirectories();
        sessionDirs[sessionId] = directory;
        localStorage.setItem('sessionWorkingDirs', JSON.stringify(sessionDirs));

        // If this is the current session, update the current directory
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value === sessionId) {
            this.setWorkingDirectory(directory);
        }
    }

    /**
     * Remove session directory from storage
     * @param {string} sessionId - Session ID to remove
     */
    removeSessionDirectory(sessionId) {
        const sessionDirs = this.getSessionDirectories();
        delete sessionDirs[sessionId];
        localStorage.setItem('sessionWorkingDirs', JSON.stringify(sessionDirs));
    }

    /**
     * Clear all session directories from storage
     */
    clearAllSessionDirectories() {
        localStorage.removeItem('sessionWorkingDirs');
    }

    /**
     * Extract working directory from event pair
     * Used by file operations tracking
     * @param {Object} pair - Event pair object
     * @returns {string} - Working directory path
     */
    extractWorkingDirectoryFromPair(pair) {
        // Try different sources for working directory
        if (pair.pre?.working_dir) return pair.pre.working_dir;
        if (pair.post?.working_dir) return pair.post.working_dir;
        if (pair.pre?.data?.working_dir) return pair.pre.data.working_dir;
        if (pair.post?.data?.working_dir) return pair.post.data.working_dir;

        // Fallback to current working directory
        return this.currentWorkingDir || this.getDefaultWorkingDir();
    }

    /**
     * Validate directory path
     * @param {string} path - Directory path to validate
     * @returns {boolean} - True if path appears valid
     */
    validateDirectoryPath(path) {
        if (!path || typeof path !== 'string') return false;

        // Basic path validation
        const trimmed = path.trim();
        if (trimmed.length === 0) return false;

        // Check for obviously invalid paths
        if (trimmed.includes('\0')) return false;

        // Check for common invalid placeholder states
        const invalidStates = [
            'Loading...',
            'Loading',
            'Unknown',
            'undefined',
            'null',
            'Not Connected',
            'Invalid Directory',
            'No Directory'
        ];

        if (invalidStates.includes(trimmed)) return false;

        // Basic path structure validation - should start with / or drive letter on Windows
        if (!trimmed.startsWith('/') && !(/^[A-Za-z]:/.test(trimmed))) {
            // Allow relative paths that look reasonable
            if (trimmed.startsWith('./') || trimmed.startsWith('../') ||
                /^[a-zA-Z0-9._-]+/.test(trimmed)) {
                return true;
            }
            return false;
        }

        return true;
    }

    /**
     * Handle git branch response from server
     * @param {Object} response - Git branch response
     */
    handleGitBranchResponse(response) {
        console.log('[GIT-BRANCH-DEBUG] handleGitBranchResponse called with:', response);

        const footerBranch = document.getElementById('footer-git-branch');
        if (!footerBranch) {
            console.warn('[GIT-BRANCH-DEBUG] footer-git-branch element not found');
            return;
        }

        if (response.success) {
            console.log('[GIT-BRANCH-DEBUG] Git branch request successful, branch:', response.branch);
            footerBranch.textContent = response.branch;
            footerBranch.style.display = 'inline';

            // Optional: Add a class to indicate successful git status
            footerBranch.classList.remove('git-error');
            footerBranch.classList.add('git-success');
        } else {
            // Handle different error types more gracefully
            let displayText = 'Git Error';
            const error = response.error || 'Unknown error';

            if (error.includes('Directory not found') || error.includes('does not exist')) {
                displayText = 'Dir Not Found';
            } else if (error.includes('Not a directory')) {
                displayText = 'Invalid Path';
            } else if (error.includes('Not a git repository')) {
                displayText = 'No Git Repo';
            } else if (error.includes('git')) {
                displayText = 'Git Error';
            } else {
                displayText = 'Unknown';
            }

            console.log('[GIT-BRANCH-DEBUG] Git branch request failed:', error, '- showing as:', displayText);
            footerBranch.textContent = displayText;
            footerBranch.style.display = 'inline';

            // Optional: Add a class to indicate error state
            footerBranch.classList.remove('git-success');
            footerBranch.classList.add('git-error');
        }

        // Log additional debug info from server
        if (response.original_working_dir) {
            console.log('[GIT-BRANCH-DEBUG] Server received original working_dir:', this.repr(response.original_working_dir));
        }
        if (response.working_dir) {
            console.log('[GIT-BRANCH-DEBUG] Server used working_dir:', this.repr(response.working_dir));
        }
        if (response.git_error) {
            console.log('[GIT-BRANCH-DEBUG] Git command stderr:', response.git_error);
        }
    }

    /**
     * Check if working directory is ready for Git operations
     * @returns {boolean} - True if directory is ready
     */
    isWorkingDirectoryReady() {
        const dir = this.getCurrentWorkingDir();
        return this.validateDirectoryPath(dir) && dir !== 'Loading...' && dir !== 'Unknown';
    }

    /**
     * Wait for working directory to be ready, then execute callback
     * @param {Function} callback - Function to call when directory is ready
     * @param {number} timeout - Maximum time to wait in milliseconds
     */
    whenDirectoryReady(callback, timeout = 5000) {
        const startTime = Date.now();

        const checkReady = () => {
            if (this.isWorkingDirectoryReady()) {
                callback();
            } else if (Date.now() - startTime < timeout) {
                setTimeout(checkReady, 100); // Check every 100ms
            } else {
                console.warn('[WORKING-DIR-DEBUG] Timeout waiting for directory to be ready');
            }
        };

        checkReady();
    }

    /**
     * Helper function for detailed logging
     * @param {*} value - Value to represent
     * @returns {string} - String representation
     */
    repr(value) {
        if (value === null) return 'null';
        if (value === undefined) return 'undefined';
        if (typeof value === 'string') return `"${value}"`;
        return String(value);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.footerDirObserver) {
            this.footerDirObserver.disconnect();
            this.footerDirObserver = null;
        }

        console.log('Working directory manager cleaned up');
    }
}
// ES6 Module export
export { WorkingDirectoryManager };
export default WorkingDirectoryManager;
