// =============================================================================
// MPM Commander Pro - Frontend Application
// =============================================================================

// State
const state = {
    projects: [],
    currentProject: null,
    currentSession: null,
    pollInterval: null,
    activityPollInterval: null,
    debugLogs: [],
    debugPanelOpen: false,
    ansiUp: null,
    sessionActivity: {},  // session_id -> activity stats
    hasUserScrolled: false,  // Track if user manually scrolled up
    // Browser Terminal State
    browserTerminal: null,       // xterm.js Terminal instance
    terminalSocket: null,        // WebSocket connection
    terminalFitAddon: null,      // FitAddon for auto-sizing
    terminalFullscreen: false,   // Fullscreen mode
    terminalResizeObserver: null // ResizeObserver for container
};

// Config
const CONFIG = {
    API_BASE: '/api',
    POLL_INTERVAL: 1000,  // 1 second like iTerm Claude Manager
    OUTPUT_POLL_INTERVAL: 500,  // Faster for output
    ACTIVITY_POLL_INTERVAL: 1000,  // Activity stats refresh
    MAX_DEBUG_LOGS: 100
};

// =============================================================================
// Utilities
// =============================================================================

function log(message, level = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
    state.debugLogs.unshift(logEntry);
    if (state.debugLogs.length > CONFIG.MAX_DEBUG_LOGS) {
        state.debugLogs.pop();
    }
    updateDebugPanel();
    console.log(logEntry);
}

function getAnsiUp() {
    if (!state.ansiUp && typeof AnsiUp !== 'undefined') {
        state.ansiUp = new AnsiUp();
        state.ansiUp.use_classes = false;
    }
    return state.ansiUp;
}

async function fetchAPI(endpoint, options = {}) {
    try {
        const res = await fetch(`${CONFIG.API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.error?.message || error.detail?.error?.message || 'API Error');
        }
        return res.status === 204 ? null : res.json();
    } catch (err) {
        log(`API Error: ${endpoint} - ${err.message}`, 'error');
        throw err;
    }
}

// =============================================================================
// State Icons & Helpers
// =============================================================================

function stateIcon(state) {
    const icons = {
        working: '🟢',
        blocked: '🟡',
        idle: '⚪',
        paused: '⏸️',
        error: '🔴',
        running: '🟢',
        stopped: '⚫'
    };
    return icons[state] || '⚪';
}

function getLastLine(content) {
    if (!content) return '';
    const lines = content.trim().split('\n');
    for (let i = lines.length - 1; i >= 0; i--) {
        const line = lines[i].trim();
        // Skip empty lines and common prompts
        if (line && !line.match(/^[$#>%]\s*$/)) {
            // Strip ANSI codes for preview
            return line.replace(/\x1b\[[0-9;]*m/g, '').substring(0, 60);
        }
    }
    return '';
}

// =============================================================================
// Project Tree Rendering
// =============================================================================

async function loadProjects() {
    try {
        state.projects = await fetchAPI('/projects');
        renderProjectTree();
        log(`Loaded ${state.projects.length} projects`);
    } catch (err) {
        log(`Failed to load projects: ${err.message}`, 'error');
    }
}

function renderProjectTree() {
    const container = document.getElementById('project-tree');

    if (state.projects.length === 0) {
        container.innerHTML = `
            <div class="text-gray-500 text-sm text-center py-8">
                <div class="text-2xl mb-2">📁</div>
                <div>No projects registered</div>
                <button onclick="showRegisterModal()" class="text-blue-400 hover:text-blue-300 mt-2">
                    + Add Project
                </button>
            </div>
        `;
        return;
    }

    // Get all sessions for numbering (Ctrl+1, Ctrl+2, etc.)
    let sessionIndex = 0;

    container.innerHTML = state.projects.map(project => `
        <div class="project-item" data-id="${project.id}">
            <!-- Project Header -->
            <div class="project-header flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-800 cursor-pointer transition"
                 onclick="toggleProject('${project.id}')">
                <span class="expand-icon text-gray-500 text-xs transition-transform rotate-90" id="expand-${project.id}">▶</span>
                <span class="text-base">${stateIcon(project.state)}</span>
                <span class="font-medium text-sm flex-1 truncate">${project.name}</span>
                <span class="text-xs text-gray-500">${project.sessions.length}</span>
            </div>

            <!-- Sessions (EXPANDED by default) -->
            <div class="sessions-container ml-4 border-l border-gray-800 pl-2" id="sessions-${project.id}">
                ${project.sessions.length === 0
                    ? `<div class="text-gray-500 text-xs py-2 pl-2">No sessions</div>`
                    : project.sessions.map((session, idx) => {
                        const globalIdx = sessionIndex++;
                        const shortcutHint = globalIdx < 9 ? `<span class="text-gray-600 text-[10px] ml-1">^${globalIdx + 1}</span>` : '';
                        return `
                        <div class="session-item flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-800 cursor-pointer transition ${state.currentSession === session.id ? 'bg-gray-800' : ''}"
                             onclick="selectSession('${project.id}', '${session.id}')" data-session="${session.id}">
                            <span class="text-xs ${session.status === 'running' ? 'text-green-400' : 'text-gray-500'}">●</span>
                            <span class="text-sm truncate flex-1">${session.id.slice(0, 8)}...${shortcutHint}</span>
                            <span class="text-xs text-gray-500">${session.runtime}</span>
                        </div>
                    `}).join('')
                }
                <!-- New Session Button -->
                <button onclick="createSession('${project.id}')"
                        class="w-full text-left text-xs text-blue-400 hover:text-blue-300 px-2 py-1 mt-1">
                    + New Session
                </button>
            </div>
        </div>
    `).join('');

    // Load session previews for all expanded projects
    for (const project of state.projects) {
        loadSessionPreviews(project.id);
    }
}

function toggleProject(projectId) {
    const sessionsContainer = document.getElementById(`sessions-${projectId}`);
    const expandIcon = document.getElementById(`expand-${projectId}`);

    if (sessionsContainer.classList.contains('hidden')) {
        sessionsContainer.classList.remove('hidden');
        expandIcon.classList.add('rotate-90');
        // Load session previews
        loadSessionPreviews(projectId);
    } else {
        sessionsContainer.classList.add('hidden');
        expandIcon.classList.remove('rotate-90');
    }
}

async function loadSessionPreviews(projectId) {
    const project = state.projects.find(p => p.id === projectId);
    if (!project) return;

    for (const session of project.sessions) {
        try {
            const data = await fetchAPI(`/sessions/${session.id}/output?lines=50`);
            const lastLine = getLastLine(data.output);
            const el = document.getElementById(`lastline-${session.id}`);
            if (el) {
                el.textContent = lastLine || '(empty)';
            }
        } catch (err) {
            // Ignore errors for previews
        }
    }
}

// =============================================================================
// Session Selection & Output
// =============================================================================

async function selectSession(projectId, sessionId) {
    state.currentProject = projectId;
    state.currentSession = sessionId;

    // Update UI selection
    document.querySelectorAll('.session-item').forEach(el => {
        el.classList.remove('bg-gray-800');
        if (el.dataset.session === sessionId) {
            el.classList.add('bg-gray-800');
        }
    });

    // Update output header
    const project = state.projects.find(p => p.id === projectId);
    const session = project?.sessions.find(s => s.id === sessionId);

    document.getElementById('output-title').textContent = `${project?.name} / ${sessionId.slice(0, 8)}...`;

    const statusEl = document.getElementById('output-status');
    if (session) {
        statusEl.textContent = session.status;
        statusEl.className = `text-xs px-2 py-0.5 rounded ${session.status === 'running' ? 'bg-green-600/20 text-green-400' : 'bg-gray-700 text-gray-400'}`;
        statusEl.classList.remove('hidden');
    }

    // Show actions and activity panel
    document.getElementById('output-actions').classList.remove('hidden');
    document.getElementById('quick-input-bar').classList.remove('hidden');
    document.getElementById('activity-panel').classList.remove('hidden');

    // Load output
    await loadSessionOutput();

    // Start output polling
    startOutputPoll();

    // Start activity polling
    startActivityPoll();

    log(`Selected session ${sessionId.slice(0, 8)}`);
}

async function loadSessionOutput() {
    if (!state.currentSession) return;

    try {
        const data = await fetchAPI(`/sessions/${state.currentSession}/output?lines=10000`);
        const outputEl = document.getElementById('output-content');

        // Check if user has scrolled up (don't auto-scroll if they're reading history)
        const wasAtBottom = outputEl.scrollHeight - outputEl.scrollTop <= outputEl.clientHeight + 50;

        const converter = getAnsiUp();
        if (converter) {
            outputEl.innerHTML = converter.ansi_to_html(data.output || '(no output)');
        } else {
            outputEl.textContent = data.output || '(no output)';
        }

        // Auto-scroll to bottom (always for new content, or if was at bottom)
        if (wasAtBottom || !state.hasUserScrolled) {
            outputEl.scrollTop = outputEl.scrollHeight;
        }
    } catch (err) {
        document.getElementById('output-content').innerHTML = `
            <div class="text-red-400">Error loading output: ${err.message}</div>
        `;
    }
}

function startOutputPoll() {
    // Clear existing poll
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
    }

    // Store current session for comparison
    const targetSession = state.currentSession;

    state.pollInterval = setInterval(async () => {
        // Stop if session changed
        if (state.currentSession !== targetSession) {
            clearInterval(state.pollInterval);
            return;
        }

        await loadSessionOutput();
    }, CONFIG.OUTPUT_POLL_INTERVAL);
}

// =============================================================================
// Session Actions
// =============================================================================

async function createSession(projectId) {
    try {
        await fetchAPI(`/projects/${projectId}/sessions`, {
            method: 'POST',
            body: JSON.stringify({ runtime: 'claude-code' })
        });
        await loadProjects();
        log(`Created new session for project`);
    } catch (err) {
        alert('Failed to create session: ' + err.message);
    }
}

async function openInTerminal() {
    if (!state.currentSession) return;

    const mode = getTerminalMode();

    if (mode === 'browser') {
        // Open Browser Terminal
        await openBrowserTerminal();
    } else {
        // Open external terminal (existing logic)
        const terminal = getPreferredTerminal();
        try {
            await fetchAPI(`/sessions/${state.currentSession}/open-terminal?terminal=${terminal}`, {
                method: 'POST'
            });
            log(`Opened in ${terminal}`);
        } catch (err) {
            log(`Failed to open terminal: ${err.message}`, 'error');
        }
    }
}

async function sendEscape() {
    if (!state.currentSession) return;
    try {
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=Escape&enter=false`, {
            method: 'POST'
        });
        log('ESC sent');
    } catch (err) {
        log(`Failed to send ESC: ${err.message}`, 'error');
    }
}

async function sendCtrlC() {
    if (!state.currentSession) return;
    try {
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=C-c&enter=false`, {
            method: 'POST'
        });
        log('Ctrl+C sent');
    } catch (err) {
        log(`Failed to send Ctrl+C: ${err.message}`, 'error');
    }
}

async function sendEnter() {
    if (!state.currentSession) return;
    try {
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=&enter=true`, {
            method: 'POST'
        });
        log('Enter sent');
    } catch (err) {
        log(`Failed to send Enter: ${err.message}`, 'error');
    }
}

async function sendShiftTab() {
    if (!state.currentSession) return;
    try {
        // BTab is tmux's key name for Shift+Tab (Back-Tab)
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=BTab&enter=false`, {
            method: 'POST'
        });
        log('Shift+Tab sent (cycle permissions)');
    } catch (err) {
        log(`Failed to send Shift+Tab: ${err.message}`, 'error');
    }
}

async function sendText() {
    const input = document.getElementById('send-text-input');
    const text = input.value.trim();
    if (!text || !state.currentSession) return;

    try {
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=${encodeURIComponent(text)}&enter=true`, {
            method: 'POST'
        });
        input.value = '';
        log(`Sent: ${text.substring(0, 30)}...`);
    } catch (err) {
        log(`Failed to send text: ${err.message}`, 'error');
    }
}

/**
 * Terminate the current session.
 * Kills the tmux pane and removes the session.
 */
async function terminateSession() {
    if (!state.currentSession) return;

    // Confirm before terminating
    if (!confirm('Are you sure you want to terminate this session? This cannot be undone.')) {
        return;
    }

    try {
        // Close browser terminal if open
        closeBrowserTerminal();

        // Delete the session
        await fetchAPI(`/sessions/${state.currentSession}`, {
            method: 'DELETE'
        });

        log(`Session ${state.currentSession.slice(0, 8)}... terminated`);

        // Clear current session and refresh
        state.currentSession = null;
        document.getElementById('output-content').textContent = 'Session terminated. Select another session.';
        document.getElementById('output-header').classList.add('hidden');
        document.getElementById('output-actions').classList.add('hidden');
        document.getElementById('activity-panel').classList.add('hidden');

        // Refresh project list
        await loadProjects();

    } catch (err) {
        log(`Failed to terminate session: ${err.message}`, 'error');
    }
}

async function sendQuickMessage() {
    const input = document.getElementById('quick-input');
    const text = input.value.trim();
    if (!text || !state.currentSession) return;

    try {
        // Send each line separately (for multi-line input)
        const lines = text.split('\n');
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const isLast = i === lines.length - 1;
            await fetchAPI(`/sessions/${state.currentSession}/keys?keys=${encodeURIComponent(line)}&enter=true`, {
                method: 'POST'
            });
            // Small delay between lines
            if (!isLast) {
                await new Promise(resolve => setTimeout(resolve, 50));
            }
        }
        input.value = '';
        // Reset textarea to minimum height (3 rows)
        input.style.height = 'auto';
        input.style.overflowY = 'hidden';
        autoResizeTextarea(input);
        log(`Sent message: ${text.substring(0, 30)}${text.length > 30 ? '...' : ''}`);
    } catch (err) {
        alert('Failed to send message: ' + err.message);
    }
}

// =============================================================================
// Modal Functions & Filesystem Browser
// =============================================================================

let currentBrowsePath = '';
const MAX_RECENT_PROJECTS = 8;

function getRecentProjects() {
    const stored = localStorage.getItem('recent-projects');
    return stored ? JSON.parse(stored) : [];
}

function addToRecentProjects(path, name) {
    let recent = getRecentProjects();
    // Remove if already exists
    recent = recent.filter(p => p.path !== path);
    // Add to front
    recent.unshift({ path, name, addedAt: Date.now() });
    // Keep only MAX_RECENT_PROJECTS
    recent = recent.slice(0, MAX_RECENT_PROJECTS);
    localStorage.setItem('recent-projects', JSON.stringify(recent));
}

function renderRecentProjects() {
    const recent = getRecentProjects();
    const section = document.getElementById('recent-projects-section');
    const list = document.getElementById('recent-projects-list');

    if (recent.length === 0) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    list.innerHTML = recent.map(p => `
        <button onclick="quickAddProject('${p.path.replace(/'/g, "\\'")}', '${p.name.replace(/'/g, "\\'")}')"
                class="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm transition group">
            <span>📁</span>
            <span>${p.name}</span>
            <span class="text-gray-500 text-xs hidden group-hover:inline">${p.path.split('/').slice(-2, -1)[0]}/</span>
        </button>
    `).join('');
}

async function quickAddProject(path, name) {
    try {
        await fetchAPI('/projects', {
            method: 'POST',
            body: JSON.stringify({ path, name })
        });
        hideRegisterModal();
        await loadProjects();
        log(`Added project: ${name}`);
    } catch (err) {
        // If already exists, just close and refresh
        if (err.message.includes('already')) {
            hideRegisterModal();
            await loadProjects();
            log(`Project already registered: ${name}`);
        } else {
            alert('Failed to add project: ' + err.message);
        }
    }
}

async function showRegisterModal() {
    document.getElementById('register-modal').classList.remove('hidden');
    // Show recent projects
    renderRecentProjects();
    // Start browsing from home directory
    await browsePath('');
}

function hideRegisterModal() {
    document.getElementById('register-modal').classList.add('hidden');
    document.getElementById('project-path').value = '';
    document.getElementById('project-name').value = '';
}

async function browsePath(path) {
    const listEl = document.getElementById('directory-list');
    const pathInput = document.getElementById('current-browse-path');

    listEl.innerHTML = '<div class="p-4 text-gray-500 text-center">Loading...</div>';

    try {
        const url = path ? `/filesystem/browse?path=${encodeURIComponent(path)}` : '/filesystem/browse';
        const data = await fetchAPI(url);

        currentBrowsePath = data.current_path;
        pathInput.value = data.current_path;

        if (data.error) {
            listEl.innerHTML = `<div class="p-4 text-red-400 text-center">${data.error}</div>`;
            return;
        }

        if (data.directories.length === 0) {
            listEl.innerHTML = '<div class="p-4 text-gray-500 text-center">No subdirectories</div>';
            return;
        }

        listEl.innerHTML = data.directories.map(dir => `
            <div class="flex items-center px-3 py-2 hover:bg-gray-800 cursor-pointer border-b border-gray-800 group"
                 ondblclick="browsePath('${dir.path.replace(/'/g, "\\'")}')"
                 onclick="selectDirectory('${dir.path.replace(/'/g, "\\'")}', '${dir.name.replace(/'/g, "\\'")}')">
                <span class="mr-2">${dir.is_git ? '📁' : '📂'}</span>
                <span class="flex-1">${dir.name}</span>
                ${dir.is_git ? '<span class="text-xs text-green-500 px-2 py-0.5 bg-green-900/30 rounded">git</span>' : ''}
                <button onclick="event.stopPropagation(); browsePath('${dir.path.replace(/'/g, "\\'")}')"
                        class="ml-2 px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 rounded opacity-0 group-hover:opacity-100 transition">
                    Open →
                </button>
            </div>
        `).join('');

    } catch (err) {
        listEl.innerHTML = `<div class="p-4 text-red-400 text-center">Error: ${err.message}</div>`;
    }
}

function browseParent() {
    const pathInput = document.getElementById('current-browse-path');
    const currentPath = pathInput.value;
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    browsePath(parentPath);
}

function selectDirectory(path, name) {
    document.getElementById('project-path').value = path;
    document.getElementById('project-name').value = name;
}

async function registerProject() {
    const path = document.getElementById('project-path').value.trim();
    const name = document.getElementById('project-name').value.trim() || path.split('/').pop();

    if (!path) {
        alert('Please select a project folder');
        return;
    }

    try {
        await fetchAPI('/projects', {
            method: 'POST',
            body: JSON.stringify({ path, name })
        });
        // Add to recent projects
        addToRecentProjects(path, name);
        hideRegisterModal();
        await loadProjects();
        log(`Registered project: ${name}`);
    } catch (err) {
        alert('Failed to register: ' + err.message);
    }
}

// =============================================================================
// Settings Modal
// =============================================================================

function showSettingsModal() {
    document.getElementById('settings-modal').classList.remove('hidden');
    // Load current settings
    const terminal = localStorage.getItem('preferred-terminal') || 'iterm';
    const radio = document.querySelector(`input[name="terminal"][value="${terminal}"]`);
    if (radio) radio.checked = true;

    // Load terminal mode
    const mode = localStorage.getItem('terminal-mode') || 'external';
    const modeRadio = document.querySelector(`input[name="terminal-mode"][value="${mode}"]`);
    if (modeRadio) modeRadio.checked = true;
}

function hideSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

function saveSettings() {
    const terminal = document.querySelector('input[name="terminal"]:checked')?.value || 'iterm';
    localStorage.setItem('preferred-terminal', terminal);

    const mode = document.querySelector('input[name="terminal-mode"]:checked')?.value || 'external';
    localStorage.setItem('terminal-mode', mode);

    hideSettingsModal();
    log(`Settings saved: Terminal = ${terminal}, Mode = ${mode}`);
}

function getPreferredTerminal() {
    return localStorage.getItem('preferred-terminal') || 'iterm';
}

function getTerminalMode() {
    return localStorage.getItem('terminal-mode') || 'external';
}

function setTerminalMode(mode) {
    localStorage.setItem('terminal-mode', mode);
}

// =============================================================================
// Debug Panel
// =============================================================================

function toggleDebugPanel() {
    const panel = document.getElementById('debug-panel');
    const toggle = document.getElementById('debug-toggle');

    state.debugPanelOpen = !state.debugPanelOpen;

    if (state.debugPanelOpen) {
        panel.style.height = '200px';
        toggle.textContent = '▼';
    } else {
        panel.style.height = '0px';
        toggle.textContent = '▲';
    }
}

function updateDebugPanel() {
    const content = document.getElementById('debug-content');
    if (content) {
        content.innerHTML = state.debugLogs.map(log => {
            let color = 'text-gray-400';
            if (log.includes('[ERROR]')) color = 'text-red-400';
            else if (log.includes('[WARN]')) color = 'text-yellow-400';
            return `<div class="${color}">${log}</div>`;
        }).join('');
    }
}

// =============================================================================
// Global Functions
// =============================================================================

async function refreshAll() {
    log('Refreshing all data...');

    // First sync tmux windows with registry
    try {
        const syncResult = await fetchAPI('/sessions/sync', { method: 'POST' });
        log(`Synced ${syncResult.synced} sessions with tmux`);
    } catch (err) {
        log(`Sync failed: ${err.message}`, 'warn');
    }

    // Then reload projects
    await loadProjects();
    if (state.currentSession) {
        await loadSessionOutput();
    }
}

// =============================================================================
// Project Polling (like iTerm Claude Manager)
// =============================================================================

function startProjectPoll() {
    setInterval(async () => {
        try {
            const projects = await fetchAPI('/projects');

            // Check for changes
            const changed = JSON.stringify(projects) !== JSON.stringify(state.projects);
            if (changed) {
                state.projects = projects;
                renderProjectTree();

                // Re-expand previously expanded projects
                // (preserving UI state would require more complex state management)
            }
        } catch (err) {
            // Silent fail for background polling
        }
    }, CONFIG.POLL_INTERVAL);
}

// =============================================================================
// Activity Tracking
// =============================================================================

async function loadSessionActivity(sessionId) {
    try {
        const data = await fetchAPI(`/sessions/${sessionId}/activity`);
        state.sessionActivity[sessionId] = data;
        return data;
    } catch (err) {
        // Session might not be tracked yet, ignore
        return null;
    }
}

function formatSeconds(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
}

function getStatusColor(status) {
    const colors = {
        'active': 'text-green-400',
        'thinking': 'text-yellow-400',
        'stalled': 'text-red-400',
        'finished': 'text-blue-400',
        'idle': 'text-gray-500'
    };
    return colors[status] || 'text-gray-500';
}

function getStatusBgColor(status) {
    const colors = {
        'active': 'bg-green-600/20',
        'thinking': 'bg-yellow-600/20',
        'stalled': 'bg-red-600/20',
        'finished': 'bg-blue-600/20',
        'idle': 'bg-gray-700'
    };
    return colors[status] || 'bg-gray-700';
}

function renderActivityStats(activity) {
    if (!activity) return '';

    const statusColor = getStatusColor(activity.status);
    const statusBg = getStatusBgColor(activity.status);

    return `
        <div class="activity-stats flex items-center gap-3 text-xs">
            <!-- Status Badge -->
            <span class="px-2 py-0.5 rounded ${statusBg} ${statusColor} font-medium uppercase">
                ${activity.status}
            </span>

            <!-- Lines -->
            <span class="text-gray-400" title="Total lines / Lines since prompt">
                📝 ${activity.total_lines} <span class="text-gray-600">(+${activity.lines_since_prompt})</span>
            </span>

            <!-- Time Since Change -->
            <span class="${activity.seconds_since_change < 5 ? 'text-green-400' : activity.seconds_since_change < 30 ? 'text-yellow-400' : 'text-red-400'}"
                  title="Time since last output">
                ⏱️ ${formatSeconds(activity.seconds_since_change)}
            </span>

            <!-- Time Since Prompt -->
            <span class="text-gray-400" title="Time since last prompt">
                💬 ${formatSeconds(activity.seconds_since_prompt)}
            </span>
        </div>
    `;
}

function renderActivityPanel() {
    const panel = document.getElementById('activity-panel');
    if (!panel || !state.currentSession) return;

    const activity = state.sessionActivity[state.currentSession];

    const metricsEl = document.getElementById('activity-metrics');
    const promptEl = document.getElementById('activity-last-prompt');
    const responseEl = document.getElementById('activity-last-response');

    if (!activity) {
        if (metricsEl) metricsEl.innerHTML = '<span class="text-gray-500">Loading...</span>';
        if (promptEl) promptEl.textContent = '';
        if (responseEl) responseEl.textContent = '';
        return;
    }

    const statusColor = getStatusColor(activity.status);
    const statusBg = getStatusBgColor(activity.status);

    // Metrics row (compact)
    if (metricsEl) {
        // Build Claude state badge if present
        let claudeStateBadge = '';
        if (activity.claude_state) {
            const stateColor = activity.claude_state.toLowerCase().includes('bypass')
                ? 'bg-orange-600/20 text-orange-400'
                : activity.claude_state.toLowerCase().includes('update')
                ? 'bg-blue-600/20 text-blue-400'
                : 'bg-purple-600/20 text-purple-400';
            claudeStateBadge = `
                <span class="px-2 py-0.5 rounded ${stateColor} text-[10px]" title="Claude Code State">
                    ${activity.claude_state}
                </span>
            `;
        }

        metricsEl.innerHTML = `
            <span class="px-2 py-0.5 rounded ${statusBg} ${statusColor} font-medium uppercase text-[10px]">
                ${activity.status}
            </span>
            ${claudeStateBadge}
            <span class="text-gray-400" title="Lines total / since prompt">
                📝 ${activity.total_lines} <span class="text-gray-600">(+${activity.lines_since_prompt})</span>
            </span>
            <span class="${activity.seconds_since_change < 5 ? 'text-green-400' : activity.seconds_since_change < 30 ? 'text-yellow-400' : 'text-red-400'}" title="Since last output">
                ⏱️ ${formatSeconds(activity.seconds_since_change)}
            </span>
        `;
    }

    // Last prompt (inline)
    if (promptEl) {
        promptEl.textContent = activity.last_user_input || '—';
        promptEl.title = activity.last_user_input || '';
    }

    // Last response (inline)
    if (responseEl) {
        if (activity.is_working) {
            responseEl.innerHTML = '<span class="text-yellow-400 animate-pulse">⏳ working...</span>';
            responseEl.title = '';
        } else {
            responseEl.textContent = activity.last_agent_output || '—';
            responseEl.title = activity.last_agent_output || '';
        }
    }
}

function startActivityPoll() {
    // Clear existing poll
    if (state.activityPollInterval) {
        clearInterval(state.activityPollInterval);
    }

    const targetSession = state.currentSession;
    if (!targetSession) return;

    // Immediate load
    loadSessionActivity(targetSession).then(() => renderActivityPanel());

    state.activityPollInterval = setInterval(async () => {
        if (state.currentSession !== targetSession) {
            clearInterval(state.activityPollInterval);
            return;
        }

        await loadSessionActivity(targetSession);
        renderActivityPanel();
    }, CONFIG.ACTIVITY_POLL_INTERVAL);
}

function stopActivityPoll() {
    if (state.activityPollInterval) {
        clearInterval(state.activityPollInterval);
        state.activityPollInterval = null;
    }
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    log('MPM Commander Pro initializing...');

    await loadProjects();
    startProjectPoll();

    // Auto-select first session if available
    autoSelectFirstSession();

    log('Ready!');
});

/**
 * Auto-select the first available session on page load.
 * Prioritizes running sessions, then falls back to any session.
 */
function autoSelectFirstSession() {
    if (!state.projects || state.projects.length === 0) return;

    // Find first project with sessions
    for (const project of state.projects) {
        if (project.sessions && project.sessions.length > 0) {
            // Prefer running session, otherwise first session
            const runningSession = project.sessions.find(s => s.status === 'running');
            const session = runningSession || project.sessions[0];

            log(`Auto-selecting session ${session.id.slice(0, 8)}...`);
            selectSession(project.id, session.id);
            return;
        }
    }
}

// =============================================================================
// Help Modal
// =============================================================================

function showHelpModal() {
    document.getElementById('help-modal').classList.remove('hidden');
}

function hideHelpModal() {
    document.getElementById('help-modal').classList.add('hidden');
}

// =============================================================================
// Quick Input Keyboard Handler
// =============================================================================

function handleQuickInputKeydown(e) {
    // Cmd/Ctrl + Enter = Send
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        sendQuickMessage();
        return;
    }

    // Shift + Enter = Allow newline (default behavior)
    if (e.shiftKey && e.key === 'Enter') {
        return; // Let default happen (newline)
    }

    // Plain Enter = Send (for quick typing)
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuickMessage();
    }
}

// =============================================================================
// Auto-resize Textarea
// =============================================================================

function autoResizeTextarea(textarea) {
    const MIN_ROWS = 3;
    const MAX_ROWS = 20;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';

    // Calculate line height from computed style
    const computedStyle = window.getComputedStyle(textarea);
    const lineHeight = parseFloat(computedStyle.lineHeight) || 20;
    const paddingTop = parseFloat(computedStyle.paddingTop) || 0;
    const paddingBottom = parseFloat(computedStyle.paddingBottom) || 0;

    // Calculate content height
    const contentHeight = textarea.scrollHeight - paddingTop - paddingBottom;
    const currentRows = Math.ceil(contentHeight / lineHeight);

    // Clamp between MIN and MAX rows
    const newRows = Math.max(MIN_ROWS, Math.min(MAX_ROWS, currentRows));

    // Calculate new height
    const newHeight = (newRows * lineHeight) + paddingTop + paddingBottom;
    textarea.style.height = `${newHeight}px`;

    // Enable/disable scrolling based on row count
    if (currentRows > MAX_ROWS) {
        textarea.style.overflowY = 'auto';
    } else {
        textarea.style.overflowY = 'hidden';
    }
}

// =============================================================================
// Session Navigation
// =============================================================================

function getAllSessions() {
    const sessions = [];
    for (const project of state.projects) {
        for (const session of project.sessions) {
            sessions.push({ projectId: project.id, sessionId: session.id, name: `${project.name}/${session.id.slice(0, 8)}` });
        }
    }
    return sessions;
}

function navigateToSession(index) {
    const sessions = getAllSessions();
    if (index >= 0 && index < sessions.length) {
        const { projectId, sessionId } = sessions[index];
        // Expand project first
        const sessionsContainer = document.getElementById(`sessions-${projectId}`);
        if (sessionsContainer && sessionsContainer.classList.contains('hidden')) {
            toggleProject(projectId);
        }
        selectSession(projectId, sessionId);
    }
}

function navigateNextSession() {
    const sessions = getAllSessions();
    if (sessions.length === 0) return;

    const currentIndex = sessions.findIndex(s => s.sessionId === state.currentSession);
    const nextIndex = (currentIndex + 1) % sessions.length;
    navigateToSession(nextIndex);
}

function navigatePrevSession() {
    const sessions = getAllSessions();
    if (sessions.length === 0) return;

    const currentIndex = sessions.findIndex(s => s.sessionId === state.currentSession);
    const prevIndex = currentIndex <= 0 ? sessions.length - 1 : currentIndex - 1;
    navigateToSession(prevIndex);
}

// Track double-escape for sending ESC to session
let lastEscapeTime = 0;

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    const activeElement = document.activeElement;
    const isInputFocused = activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA';

    // ? = Show help (when not in input)
    if (e.key === '?' && !isInputFocused) {
        e.preventDefault();
        showHelpModal();
        return;
    }

    // Escape handling
    if (e.key === 'Escape') {
        // Close modals first
        if (!document.getElementById('help-modal').classList.contains('hidden')) {
            hideHelpModal();
            return;
        }
        if (!document.getElementById('register-modal').classList.contains('hidden')) {
            hideRegisterModal();
            return;
        }
        if (!document.getElementById('settings-modal').classList.contains('hidden')) {
            hideSettingsModal();
            return;
        }

        // Double-escape = Send ESC to session
        const now = Date.now();
        if (now - lastEscapeTime < 500 && state.currentSession) {
            sendEscape();
            lastEscapeTime = 0;
        } else {
            lastEscapeTime = now;
        }
        return;
    }

    // Ctrl+D = Toggle debug panel
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        toggleDebugPanel();
        return;
    }

    // Ctrl+Tab = Next session
    if (e.ctrlKey && e.key === 'Tab') {
        e.preventDefault();
        if (e.shiftKey) {
            navigatePrevSession();
        } else {
            navigateNextSession();
        }
        return;
    }

    // Ctrl+1-9 = Jump to session
    if (e.ctrlKey && e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        navigateToSession(index);
        return;
    }

    // / = Focus input (when not in input)
    if (e.key === '/' && !isInputFocused) {
        e.preventDefault();
        const input = document.getElementById('quick-input');
        if (input && !input.closest('#quick-input-bar').classList.contains('hidden')) {
            input.focus();
        }
        return;
    }
});

// Track user scrolling in output panel
document.addEventListener('DOMContentLoaded', () => {
    const outputEl = document.getElementById('output-content');
    if (outputEl) {
        outputEl.addEventListener('scroll', () => {
            const atBottom = outputEl.scrollHeight - outputEl.scrollTop <= outputEl.clientHeight + 50;
            state.hasUserScrolled = !atBottom;
        });

        // Double-click output panel to jump to bottom
        outputEl.addEventListener('dblclick', () => {
            outputEl.scrollTop = outputEl.scrollHeight;
            state.hasUserScrolled = false;
        });
    }
});

// =============================================================================
// Browser Terminal Functions
// =============================================================================

/**
 * Open the Browser Terminal for the current session.
 * Initializes xterm.js, connects WebSocket, and shows the terminal panel.
 */
async function openBrowserTerminal() {
    if (!state.currentSession) {
        log('No session selected for browser terminal', 'error');
        return;
    }

    // Close existing terminal if open
    closeBrowserTerminal();

    log(`Opening browser terminal for session ${state.currentSession.slice(0, 8)}...`);

    // Show terminal panel - output content will shrink to accommodate
    const terminalPanel = document.getElementById('browser-terminal-panel');
    const outputContent = document.getElementById('output-content');
    const statusEl = document.getElementById('terminal-connection-status');

    terminalPanel.classList.remove('hidden');
    // Terminal has fixed height in CSS (for exactly 24 rows)
    // Output content will flex to fill remaining space

    statusEl.textContent = 'connecting...';
    statusEl.className = 'text-xs px-2 py-0.5 rounded bg-yellow-600/20 text-yellow-400';

    // Initialize xterm.js
    const container = document.getElementById('xterm-container');
    container.innerHTML = '';  // Clear any previous content

    try {
        // Create terminal instance
        // Note: We use minimal scrollback since we're mirroring a tmux pane
        // which has its own scrollback. The terminal acts as a "viewport".
        state.browserTerminal = new Terminal({
            cursorBlink: true,
            cursorStyle: 'block',
            fontSize: 13,  // Standard terminal size
            fontFamily: "'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', monospace",
            lineHeight: 1.0,  // Tight line height for proper alignment
            letterSpacing: 0,
            fontWeight: 'normal',
            fontWeightBold: 'bold',
            theme: {
                background: '#0a0a0f',
                foreground: '#e4e4e7',  // Brighter foreground for better readability
                cursor: '#f4f4f5',
                cursorAccent: '#0a0a0f',
                selectionBackground: 'rgba(59, 130, 246, 0.3)',
                selectionForeground: '#ffffff',
                // Standard ANSI colors (0-7) - matched to typical terminal themes
                black: '#1e1e1e',
                red: '#f44747',
                green: '#6a9955',
                yellow: '#d7ba7d',
                blue: '#569cd6',
                magenta: '#c586c0',
                cyan: '#4ec9b0',
                white: '#d4d4d4',
                // Bright variants (8-15)
                brightBlack: '#808080',
                brightRed: '#f44747',
                brightGreen: '#6a9955',
                brightYellow: '#d7ba7d',
                brightBlue: '#569cd6',
                brightMagenta: '#c586c0',
                brightCyan: '#4ec9b0',
                brightWhite: '#ffffff'
            },
            allowProposedApi: true,
            scrollback: 0,  // Fix 3: Disabled - xterm.js mirrors tmux pane, no scrollback needed
            disableStdin: false,
            convertEol: false,  // Don't convert EOL - tmux handles this
            windowsMode: false
        });

        // Add FitAddon for auto-sizing
        state.terminalFitAddon = new FitAddon.FitAddon();
        state.browserTerminal.loadAddon(state.terminalFitAddon);

        // Add WebLinksAddon for clickable URLs
        if (typeof WebLinksAddon !== 'undefined') {
            const webLinksAddon = new WebLinksAddon.WebLinksAddon();
            state.browserTerminal.loadAddon(webLinksAddon);
        }

        // Open terminal in container
        state.browserTerminal.open(container);

        // Note: We do NOT call fit() initially anymore
        // The terminal will start with default dimensions (80x24)
        // and then resize to match the tmux pane when we receive
        // the pane_size message from the server.
        // This prevents the browser from breaking Claude Code's UI
        // by resizing the tmux pane to fit the browser window.

        // We keep ResizeObserver but it no longer triggers resizes
        state.terminalResizeObserver = new ResizeObserver(() => {
            // Intentionally empty - terminal size comes from server
        });
        state.terminalResizeObserver.observe(container);

        // Connect WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/sessions/${state.currentSession}/terminal`;

        state.terminalSocket = new WebSocket(wsUrl);

        state.terminalSocket.binaryType = 'arraybuffer';

        state.terminalSocket.onopen = () => {
            log('Browser terminal WebSocket connected');
            statusEl.textContent = 'connected';
            statusEl.className = 'text-xs px-2 py-0.5 rounded bg-green-600/20 text-green-400';

            // We no longer send initial size from browser to server
            // Instead, the server sends us the tmux pane dimensions
            // via a pane_size message, and we resize xterm.js to match.
            // This prevents breaking Claude Code's UI by resizing tmux.

            // Focus terminal
            state.browserTerminal.focus();
        };

        state.terminalSocket.onmessage = (event) => {
            let text;
            if (event.data instanceof ArrayBuffer) {
                text = new TextDecoder().decode(event.data);
            } else {
                text = event.data;
            }

            // Check for pane_size message from server
            // This tells us the actual tmux pane dimensions to match
            if (text.startsWith('{"type":"pane_size"')) {
                try {
                    const msg = JSON.parse(text);
                    if (msg.type === 'pane_size' && msg.cols && msg.rows) {
                        log(`Server pane size: ${msg.cols}x${msg.rows}`);

                        // Resize xterm.js to match the tmux pane exactly
                        if (state.browserTerminal) {
                            state.browserTerminal.resize(msg.cols, msg.rows);
                            log(`Terminal resized to: ${msg.cols}x${msg.rows}`);
                        }
                    }
                    return; // Don't write JSON to terminal
                } catch (e) {
                    // Not valid JSON, treat as terminal output
                }
            }

            // Write the data to terminal immediately
            if (state.browserTerminal) {
                state.browserTerminal.write(text);
            }
        };

        state.terminalSocket.onclose = (event) => {
            log(`Browser terminal WebSocket closed: ${event.code} ${event.reason}`);
            statusEl.textContent = 'disconnected';
            statusEl.className = 'text-xs px-2 py-0.5 rounded bg-red-600/20 text-red-400';
        };

        state.terminalSocket.onerror = (error) => {
            log(`Browser terminal WebSocket error: ${error}`, 'error');
            statusEl.textContent = 'error';
            statusEl.className = 'text-xs px-2 py-0.5 rounded bg-red-600/20 text-red-400';
        };

        // Handle terminal input - send to WebSocket
        state.browserTerminal.onData((data) => {
            if (state.terminalSocket && state.terminalSocket.readyState === WebSocket.OPEN) {
                state.terminalSocket.send(data);
            }
        });

        log('Browser terminal initialized');

    } catch (err) {
        log(`Failed to initialize browser terminal: ${err.message}`, 'error');
        statusEl.textContent = 'error';
        statusEl.className = 'text-xs px-2 py-0.5 rounded bg-red-600/20 text-red-400';
    }
}

/**
 * Close the Browser Terminal and cleanup resources.
 */
function closeBrowserTerminal() {
    // Close WebSocket
    if (state.terminalSocket) {
        state.terminalSocket.close();
        state.terminalSocket = null;
    }

    // Dispose ResizeObserver
    if (state.terminalResizeObserver) {
        state.terminalResizeObserver.disconnect();
        state.terminalResizeObserver = null;
    }

    // Dispose terminal
    if (state.browserTerminal) {
        state.browserTerminal.dispose();
        state.browserTerminal = null;
        state.terminalFitAddon = null;
    }

    // Hide terminal panel - output content will expand automatically
    const terminalPanel = document.getElementById('browser-terminal-panel');

    if (terminalPanel) {
        terminalPanel.classList.add('hidden');
    }

    // Reset fullscreen if active
    if (state.terminalFullscreen) {
        state.terminalFullscreen = false;
        const outputPanel = document.getElementById('output-panel');
        if (outputPanel) {
            outputPanel.classList.remove('terminal-fullscreen');
        }
    }

    log('Browser terminal closed');
}

/**
 * Toggle Browser Terminal fullscreen mode.
 */
function toggleTerminalFullscreen() {
    state.terminalFullscreen = !state.terminalFullscreen;

    const terminalPanel = document.getElementById('browser-terminal-panel');
    const outputContent = document.getElementById('output-content');
    const outputHeader = document.getElementById('output-header');
    const activityPanel = document.getElementById('activity-panel');
    const quickInputBar = document.getElementById('quick-input-bar');

    if (state.terminalFullscreen) {
        // Fullscreen: Hide other elements, terminal takes full space
        if (outputContent) outputContent.classList.add('hidden');
        if (outputHeader) outputHeader.classList.add('hidden');
        if (activityPanel) activityPanel.classList.add('hidden');
        if (quickInputBar) quickInputBar.classList.add('hidden');
        if (terminalPanel) {
            terminalPanel.style.flex = '1';
            terminalPanel.classList.remove('border-t');
        }
        log('Terminal fullscreen enabled');
    } else {
        // Exit fullscreen: Restore split view
        if (outputContent) {
            outputContent.classList.remove('hidden');
            outputContent.style.flex = '0.6';
        }
        if (outputHeader) outputHeader.classList.remove('hidden');
        if (activityPanel) activityPanel.classList.remove('hidden');
        if (quickInputBar) quickInputBar.classList.remove('hidden');
        if (terminalPanel) {
            terminalPanel.style.flex = '0.4';
            terminalPanel.classList.add('border-t');
        }
        log('Terminal fullscreen disabled');
    }

    // Re-fit terminal after layout change
    if (state.terminalFitAddon) {
        setTimeout(() => {
            state.terminalFitAddon.fit();
            // Send resize to backend
            if (state.terminalSocket && state.terminalSocket.readyState === WebSocket.OPEN) {
                const dims = state.terminalFitAddon.proposeDimensions();
                if (dims) {
                    state.terminalSocket.send(JSON.stringify({
                        resize: { cols: dims.cols, rows: dims.rows }
                    }));
                }
            }
        }, 100);
    }
}
