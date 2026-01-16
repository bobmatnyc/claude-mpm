// State
let currentView = 'list'; // list, detail, output
let currentProject = null;
let currentSession = null;
let pollInterval = null;

// API Base URL
const API_BASE = '/api';

// Utility functions
async function fetchAPI(endpoint, options = {}) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error?.message || 'API Error');
    }
    return res.status === 204 ? null : res.json();
}

// State icons
function stateIcon(state) {
    const icons = {
        working: '🟢',
        blocked: '🟡',
        idle: '⚪',
        paused: '⏸️',
        error: '🔴'
    };
    return icons[state] || '⚪';
}

// Load projects
async function loadProjects() {
    const projects = await fetchAPI('/projects');
    const container = document.getElementById('projects-container');

    if (projects.length === 0) {
        container.innerHTML = '<div class="text-gray-500 text-center py-8">No projects registered</div>';
        return;
    }

    container.innerHTML = projects.map(p => `
        <div class="bg-gray-800 rounded-lg p-4 flex justify-between items-center cursor-pointer hover:bg-gray-750"
             onclick="showProject('${p.id}')">
            <div>
                <div class="font-semibold">${stateIcon(p.state)} ${p.name}</div>
                <div class="text-sm text-gray-400">${p.path}</div>
            </div>
            <div class="text-sm text-gray-400">${p.sessions.length} sessions</div>
        </div>
    `).join('');
}

// Show project detail
async function showProject(projectId) {
    currentProject = await fetchAPI(`/projects/${projectId}`);
    currentView = 'detail';

    const view = document.getElementById('project-detail-view');
    view.innerHTML = `
        <button onclick="showList()" class="text-blue-400 hover:text-blue-300 mb-4">← Back to Projects</button>
        <div class="bg-gray-800 rounded-lg p-4 mb-4">
            <h2 class="text-lg font-semibold">${stateIcon(currentProject.state)} ${currentProject.name}</h2>
            <div class="text-sm text-gray-400">${currentProject.path}</div>
            <div class="text-sm text-gray-400 mt-2">State: ${currentProject.state}${currentProject.state_reason ? ` - ${currentProject.state_reason}` : ''}</div>
        </div>

        <div class="flex justify-between items-center mb-4">
            <h3 class="font-semibold">Sessions</h3>
            <button onclick="createSession()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm">
                + New Session
            </button>
        </div>

        <div id="sessions-container" class="space-y-2 mb-6">
            ${currentProject.sessions.length === 0
                ? '<div class="text-gray-500">No active sessions</div>'
                : currentProject.sessions.map(s => `
                    <div class="bg-gray-800 rounded p-3 flex justify-between items-center">
                        <div>
                            <span class="font-mono text-sm">${s.id.slice(0,8)}...</span>
                            <span class="text-sm text-gray-400 ml-2">${s.runtime}</span>
                            <span class="text-xs px-2 py-1 rounded ${s.status === 'running' ? 'bg-green-600' : 'bg-gray-600'} ml-2">${s.status}</span>
                        </div>
                        <button onclick="showSessionOutput('${s.id}')" class="text-blue-400 hover:text-blue-300 text-sm">
                            View Output →
                        </button>
                    </div>
                `).join('')
            }
        </div>

        <h3 class="font-semibold mb-2">Send Message</h3>
        <div class="flex space-x-2">
            <input type="text" id="message-input" placeholder="Enter message..."
                   class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2"
                   onkeypress="if(event.key==='Enter')sendMessage()">
            <button onclick="sendMessage()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Send</button>
        </div>
    `;

    document.getElementById('project-list-view').classList.add('hidden');
    view.classList.remove('hidden');
}

// Show list
function showList() {
    currentView = 'list';
    currentProject = null;
    document.getElementById('project-list-view').classList.remove('hidden');
    document.getElementById('project-detail-view').classList.add('hidden');
    document.getElementById('session-output-view').classList.add('hidden');
    loadProjects();
}

// Create session
async function createSession() {
    try {
        await fetchAPI(`/projects/${currentProject.id}/sessions`, {
            method: 'POST',
            body: JSON.stringify({ runtime: 'claude-code' })
        });
        showProject(currentProject.id);
    } catch (e) {
        alert('Failed to create session: ' + e.message);
    }
}

// Send message
async function sendMessage() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content) return;

    try {
        await fetchAPI(`/projects/${currentProject.id}/messages`, {
            method: 'POST',
            body: JSON.stringify({ content })
        });
        input.value = '';
    } catch (e) {
        alert('Failed to send message: ' + e.message);
    }
}

// Show session output
async function showSessionOutput(sessionId) {
    currentSession = sessionId;
    currentView = 'output';

    const view = document.getElementById('session-output-view');
    view.innerHTML = `
        <button onclick="showProject('${currentProject.id}')" class="text-blue-400 hover:text-blue-300 mb-4">← Back to Project</button>
        <div class="bg-gray-800 rounded-lg p-4">
            <h3 class="font-semibold mb-2">Session Output</h3>
            <div id="output-container" class="bg-black rounded p-4 font-mono text-sm h-96 overflow-auto">
                <pre id="output-content" class="whitespace-pre-wrap"></pre>
            </div>
            <div class="mt-2 text-xs text-gray-500">Auto-refreshing every 2s</div>
        </div>
    `;

    document.getElementById('project-detail-view').classList.add('hidden');
    view.classList.remove('hidden');

    // Start polling for output
    startOutputPoll();
}

// Output polling
function startOutputPoll() {
    if (pollInterval) clearInterval(pollInterval);

    async function pollOutput() {
        if (currentView !== 'output' || !currentSession) return;

        try {
            const project = await fetchAPI(`/projects/${currentProject.id}`);
            const session = project.sessions.find(s => s.id === currentSession);
            if (session) {
                // In Phase 1, we'd need an endpoint to get session output
                // For now, show placeholder
                document.getElementById('output-content').textContent =
                    `Session ${session.id}\nStatus: ${session.status}\nRuntime: ${session.runtime}\n\n[Output will be available when session is connected to tmux]`;
            }
        } catch (e) {
            console.error('Poll error:', e);
        }
    }

    pollOutput();
    pollInterval = setInterval(pollOutput, 2000);
}

// Modal functions
function showRegisterModal() {
    document.getElementById('register-modal').classList.remove('hidden');
}

function hideRegisterModal() {
    document.getElementById('register-modal').classList.add('hidden');
}

async function registerProject() {
    const path = document.getElementById('project-path').value.trim();
    const name = document.getElementById('project-name').value.trim() || undefined;

    if (!path) {
        alert('Path is required');
        return;
    }

    try {
        await fetchAPI('/projects', {
            method: 'POST',
            body: JSON.stringify({ path, name })
        });
        hideRegisterModal();
        loadProjects();
    } catch (e) {
        alert('Failed to register: ' + e.message);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    // Poll for project updates
    setInterval(() => {
        if (currentView === 'list') loadProjects();
    }, 5000);
});
