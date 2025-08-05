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
            workingDirPath.addEventListener('click', () => {
                this.showChangeDirDialog();
            });
        }

        // Listen for session changes to update working directory
        document.addEventListener('sessionChanged', (e) => {
            const sessionId = e.detail.sessionId;
            if (sessionId) {
                this.loadWorkingDirectoryForSession(sessionId);
            }
        });
    }

    /**
     * Initialize working directory for current session
     */
    initializeWorkingDirectory() {
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
        if (!sessionId || sessionId === 'all') {
            // Use default for 'all' sessions
            this.setWorkingDirectory(this.getDefaultWorkingDir());
            return;
        }
        
        // Load from localStorage
        const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
        const dir = sessionDirs[sessionId] || this.getDefaultWorkingDir();
        this.setWorkingDirectory(dir);
    }

    /**
     * Set the working directory for the current session
     * @param {string} dir - Directory path
     */
    setWorkingDirectory(dir) {
        this.currentWorkingDir = dir;
        
        // Update UI
        const pathElement = document.getElementById('working-dir-path');
        if (pathElement) {
            pathElement.textContent = dir;
        }
        
        // Update footer directory (sync across components)
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir && footerDir.textContent !== dir) {
            // Set flag to prevent observer from triggering
            this._updatingFooter = true;
            footerDir.textContent = dir;
            
            // Clear flag after a short delay
            setTimeout(() => {
                this._updatingFooter = false;
            }, 100);
        }
        
        // Save to localStorage for session persistence
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value && sessionSelect.value !== 'all') {
            const sessionId = sessionSelect.value;
            const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
            sessionDirs[sessionId] = dir;
            localStorage.setItem('sessionWorkingDirs', JSON.stringify(sessionDirs));
            console.log(`Saved working directory for session ${sessionId}:`, dir);
        }
        
        // Update git branch for new directory
        this.updateGitBranch(dir);
        
        // Dispatch event for other modules
        document.dispatchEvent(new CustomEvent('workingDirectoryChanged', {
            detail: { directory: dir }
        }));
        
        console.log('Working directory set to:', dir);
    }

    /**
     * Update git branch display for current working directory
     * @param {string} dir - Working directory path
     */
    updateGitBranch(dir) {
        if (!this.socketManager || !this.socketManager.isConnected()) {
            // Not connected, set to unknown
            const footerBranch = document.getElementById('footer-git-branch');
            if (footerBranch) {
                footerBranch.textContent = 'Not Connected';
                footerBranch.style.display = 'inline';
            }
            return;
        }
        
        // Request git branch from server
        const socket = this.socketManager.getSocket();
        if (socket) {
            console.log('Requesting git branch for directory:', dir);
            // Server expects working_dir as a direct parameter, not as an object
            socket.emit('get_git_branch', dir);
        }
    }

    /**
     * Get default working directory
     * @returns {string} - Default directory path
     */
    getDefaultWorkingDir() {
        // Try to get from footer first
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir?.textContent?.trim()) {
            return footerDir.textContent.trim();
        }
        
        // Fallback to current directory indicator
        return process?.cwd?.() || '/';
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
        
        return true;
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