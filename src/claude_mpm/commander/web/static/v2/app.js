// =============================================================================
// MPM Commander Pro - Frontend Application
// =============================================================================

// State
const state = {
    projects: [],
    currentProject: null,
    currentSession: null,
    pollInterval: null,
    debugLogs: [],
    debugPanelOpen: false,
    ansiUp: null
};

// Config
const CONFIG = {
    API_BASE: '/api',
    POLL_INTERVAL: 1000,  // 1 second like iTerm Claude Manager
    OUTPUT_POLL_INTERVAL: 500,  // Faster for output
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

    container.innerHTML = state.projects.map(project => `
        <div class="project-item" data-id="${project.id}">
            <!-- Project Header -->
            <div class="project-header flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-800 cursor-pointer transition"
                 onclick="toggleProject('${project.id}')">
                <span class="expand-icon text-gray-500 text-xs transition-transform" id="expand-${project.id}">▶</span>
                <span class="text-base">${stateIcon(project.state)}</span>
                <span class="font-medium text-sm flex-1 truncate">${project.name}</span>
                <span class="text-xs text-gray-500">${project.sessions.length}</span>
            </div>

            <!-- Sessions (collapsed by default) -->
            <div class="sessions-container hidden ml-4 border-l border-gray-800 pl-2" id="sessions-${project.id}">
                ${project.sessions.length === 0
                    ? `<div class="text-gray-500 text-xs py-2 pl-2">No sessions</div>`
                    : project.sessions.map(session => `
                        <div class="session-item flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-800 cursor-pointer transition ${state.currentSession === session.id ? 'bg-gray-800' : ''}"
                             onclick="selectSession('${project.id}', '${session.id}')" data-session="${session.id}">
                            <span class="text-xs ${session.status === 'running' ? 'text-green-400' : 'text-gray-500'}">●</span>
                            <span class="text-sm truncate flex-1">${session.id.slice(0, 8)}...</span>
                            <span class="text-xs text-gray-500">${session.runtime}</span>
                        </div>
                        <div class="last-line text-xs text-gray-500 pl-6 pb-1 truncate" id="lastline-${session.id}">
                            <!-- Last line preview -->
                        </div>
                    `).join('')
                }
                <!-- New Session Button -->
                <button onclick="createSession('${project.id}')"
                        class="w-full text-left text-xs text-blue-400 hover:text-blue-300 px-2 py-1 mt-1">
                    + New Session
                </button>
            </div>
        </div>
    `).join('');
}

function toggleProject(projectId) {
    const sessionsContainer = document.getElementById(`sessions-${projectId}`);
    const expandIcon = document.getElementById(`expand-${projectId}`);

    if (sessionsContainer.classList.contains('hidden')) {
        sessionsContainer.classList.remove('hidden');
        expandIcon.style.transform = 'rotate(90deg)';
        // Load session previews
        loadSessionPreviews(projectId);
    } else {
        sessionsContainer.classList.add('hidden');
        expandIcon.style.transform = 'rotate(0deg)';
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

    // Show actions
    document.getElementById('output-actions').classList.remove('hidden');
    document.getElementById('quick-input-bar').classList.remove('hidden');

    // Load output
    await loadSessionOutput();

    // Start output polling
    startOutputPoll();

    log(`Selected session ${sessionId.slice(0, 8)}`);
}

async function loadSessionOutput() {
    if (!state.currentSession) return;

    try {
        const data = await fetchAPI(`/sessions/${state.currentSession}/output?lines=10000`);
        const outputEl = document.getElementById('output-content');

        const converter = getAnsiUp();
        if (converter) {
            outputEl.innerHTML = converter.ansi_to_html(data.output || '(no output)');
        } else {
            outputEl.textContent = data.output || '(no output)';
        }

        // Auto-scroll to bottom
        outputEl.scrollTop = outputEl.scrollHeight;
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

async function sendQuickMessage() {
    const input = document.getElementById('quick-input');
    const text = input.value.trim();
    if (!text || !state.currentSession) return;

    try {
        await fetchAPI(`/sessions/${state.currentSession}/keys?keys=${encodeURIComponent(text)}&enter=true`, {
            method: 'POST'
        });
        input.value = '';
        log(`Sent message: ${text.substring(0, 30)}...`);
    } catch (err) {
        alert('Failed to send message: ' + err.message);
    }
}

// =============================================================================
// Modal Functions & Filesystem Browser
// =============================================================================

let currentBrowsePath = '';

async function showRegisterModal() {
    document.getElementById('register-modal').classList.remove('hidden');
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
    const name = document.getElementById('project-name').value.trim() || undefined;

    if (!path) {
        alert('Please select a project folder');
        return;
    }

    try {
        await fetchAPI('/projects', {
            method: 'POST',
            body: JSON.stringify({ path, name })
        });
        hideRegisterModal();
        await loadProjects();
        log(`Registered project: ${name || path}`);
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
}

function hideSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

function saveSettings() {
    const terminal = document.querySelector('input[name="terminal"]:checked')?.value || 'iterm';
    localStorage.setItem('preferred-terminal', terminal);
    hideSettingsModal();
    log(`Settings saved: Terminal = ${terminal}`);
}

function getPreferredTerminal() {
    return localStorage.getItem('preferred-terminal') || 'iterm';
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
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    log('MPM Commander Pro initializing...');

    await loadProjects();
    startProjectPoll();

    log('Ready!');
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape to close modals
    if (e.key === 'Escape') {
        hideRegisterModal();
    }

    // Ctrl+D to toggle debug panel
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        toggleDebugPanel();
    }
});
