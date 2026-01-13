# MPM Commander Phase 2 Scope

**Status:** Planning
**Related Issues:** #189-#196
**Phase 1 Issues:** #168-#176 (Complete)
**Target:** Autonomous multi-project orchestration daemon

---

## Overview

Phase 2 transforms Commander from a set of independent components into a **functional autonomous multi-project orchestration daemon**. Where Phase 1 built the foundation (tmux management, event detection, REST API, output parsing), Phase 2 integrates these components into a cohesive system that can autonomously manage multiple projects, execute work, detect blocking events, and coordinate human interaction.

**Core Capability:** Start the daemon, register projects, queue work items, and watch Commander autonomously execute tasks across multiple projects in parallel while handling blocking events through the inbox.

---

## Phase 1 Summary

Phase 1 (#168-#176) delivered 9 components with 4,569 LOC and 146 tests:

| Component | Ticket | Files | Key Features |
|-----------|--------|-------|--------------|
| **TmuxOrchestrator** | #168 | `tmux_orchestrator.py` | Session/pane management, I/O operations, process lifecycle |
| **Runtime Adapter** | #169 | `adapters/claude_code.py` | Launch command generation, message formatting, idle detection |
| **Project Registry** | #170 | `registry.py`, `models/project.py` | Thread-safe project CRUD, state machine, dual indexing |
| **Event Detection** | #171 | `polling/*.py` | Output buffering, event patterns, polling loops |
| **REST API v1** | #172 | `api/*.py` | 12 endpoints for projects, sessions, messages, thread |
| **Web Client** | #173 | `web/*.html` | Minimal UI placeholder |
| **Event Data Model** | #174 | `models/events.py`, `events/manager.py` | Event types, priorities, status, EventManager CRUD |
| **Output Parser** | #175 | `parsing/*.py` | Pattern-based detection (decisions, approvals, errors), option extraction |
| **Event Queue & Inbox** | #176 | `inbox/*.py` | Centralized inbox, multi-level filtering, deduplication |

**Phase 1 Achievement:** All building blocks exist, but they don't work together autonomously.

---

## Phase 2 Goals

**Primary Goal:** Deliver end-to-end autonomous orchestration with the following success criteria:

1. **Daemon Lifecycle**
   - Start Commander daemon with `claude-mpm --commander`
   - Daemon manages multiple projects in parallel tmux panes
   - Graceful shutdown persists state

2. **Work Execution**
   - Queue work items for projects via API
   - Daemon autonomously picks next work item and executes it
   - Tools (Claude Code) spawn in tmux and run to completion

3. **Event Resolution**
   - Tools ask questions → OutputParser detects → Event created in Inbox
   - Tool execution pauses automatically
   - Human responds via API → Tool resumes with response

4. **State Persistence**
   - All state (projects, events, threads) persists to disk
   - Daemon restart recovers state automatically
   - No data loss on crash

5. **Multi-Project Orchestration**
   - Handle 5+ projects concurrently
   - Isolated tool sessions per project
   - Resource limits prevent exhaustion

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Commander Daemon                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Main Loop:                                                │  │
│  │ 1. Poll inbox for resolved events                         │  │
│  │ 2. Check each ProjectSession for work                     │  │
│  │ 3. Spawn/monitor Runtime Executors                        │  │
│  │ 4. Persist state periodically                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↕                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ ProjectSession A │  │ ProjectSession B │  │ Session C ... │  │
│  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │               │  │
│  │ │Work Queue    │ │  │ │Work Queue    │ │  │               │  │
│  │ │- Item 1      │ │  │ │- Item 1      │ │  │               │  │
│  │ │- Item 2      │ │  │ │- Item 2      │ │  │               │  │
│  │ └──────────────┘ │  │ └──────────────┘ │  │               │  │
│  │ ┌──────────────┐ │  │ ┌──────────────┐ │  │               │  │
│  │ │Runtime       │ │  │ │Runtime       │ │  │               │  │
│  │ │Executor      │ │  │ │Executor      │ │  │               │  │
│  │ └──────────────┘ │  │ └──────────────┘ │  │               │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                              ↕                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              tmux Session: "mpm-commander"                │  │
│  │ ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │  │
│  │ │Pane: A  │  │Pane: B  │  │Pane: C  │  │Pane: D  │  ...  │  │
│  │ │(CC run) │  │(CC run) │  │(Idle)   │  │(Blocked)│       │  │
│  │ └─────────┘  └─────────┘  └─────────┘  └─────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    State Persistence (JSON)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ projects.json│  │ events.json  │  │ threads.json │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                         REST API / Client                        │
│  - Register projects                                             │
│  - Queue work items                                              │
│  - View inbox                                                    │
│  - Resolve events                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Key Workflows

#### 1. Work Execution Flow
```
Work Item Queued
    ↓
Daemon picks next item (ProjectSession.get_next_work)
    ↓
RuntimeExecutor spawns tool in tmux pane
    ↓
RuntimeMonitor polls output continuously
    ↓
OutputParser detects event → EventManager.create()
    ↓
RuntimeMonitor detects blocking event → PAUSE execution
    ↓
Event appears in Inbox
    ↓
Human resolves event via API
    ↓
EventHandler.resume() → send response to tool
    ↓
Tool continues execution
    ↓
Tool completes → Mark work item DONE
```

#### 2. State Persistence Flow
```
Daemon runs for N minutes
    ↓
Periodic save timer triggers (every 30s)
    ↓
StateStore.save_registry(registry)
    ↓
EventStore.save_events(event_manager)
    ↓
ThreadStore.save_threads(projects)
    ↓
Atomic write (temp file → rename)
```

#### 3. Daemon Recovery Flow
```
Daemon starts
    ↓
StateStore.load_registry() → ProjectRegistry
    ↓
EventStore.load_events() → EventManager
    ↓
ThreadStore.load_threads() → Restore conversation history
    ↓
Check tmux panes still exist
    ↓
Reattach RuntimeMonitors to live panes OR spawn new sessions
    ↓
Resume work execution where left off
```

---

## Components

### 1. Commander Daemon (`daemon.py`)

**Purpose:** Main entry point and orchestration loop for multi-project management.

**Key Files:**
- `src/claude_mpm/commander/daemon.py`

**Responsibilities:**
- Initialize ProjectRegistry, EventManager, Inbox, TmuxOrchestrator
- Load persisted state on startup
- Main event loop:
  - Poll for resolved events
  - Check each ProjectSession for runnable work
  - Spawn RuntimeExecutors for new work items
  - Persist state periodically (every 30s)
- Graceful shutdown on SIGINT/SIGTERM

**Interface:**
```python
class CommanderDaemon:
    def __init__(self, config: DaemonConfig):
        """Initialize with config (port, persistence dir, poll interval)"""

    def start(self) -> None:
        """Start daemon loop (blocking)"""

    def shutdown(self) -> None:
        """Graceful shutdown - persist state, kill sessions"""

    def _main_loop(self) -> None:
        """Poll → execute work → handle events → persist"""
```

**Acceptance Criteria:**
- [ ] Daemon starts with `claude-mpm --commander`
- [ ] Main loop runs continuously until SIGINT
- [ ] Loads persisted state on startup
- [ ] Saves state every 30 seconds
- [ ] Handles multiple projects concurrently (tested with 5)

---

### 2. Project Session (`project_session.py`)

**Purpose:** Manages lifecycle of a single project's work execution.

**Key Files:**
- `src/claude_mpm/commander/project_session.py`

**Responsibilities:**
- Manage work queue for single project
- Determine next work item to execute (priority, dependencies)
- Coordinate RuntimeExecutor and RuntimeMonitor
- Handle state transitions (IDLE → WORKING → BLOCKED → IDLE)
- Track active tool session

**Interface:**
```python
class ProjectSession:
    def __init__(self, project: Project, tmux: TmuxOrchestrator):
        """Initialize with Project model and tmux orchestrator"""

    def get_next_work(self) -> Optional[WorkItem]:
        """Get next executable work item (respects dependencies)"""

    def start_work(self, work_item: WorkItem) -> None:
        """Spawn RuntimeExecutor for work item"""

    def pause_on_event(self, event_id: str) -> None:
        """Pause execution, wait for event resolution"""

    def resume_after_event(self, event_id: str, response: str) -> None:
        """Resume execution with event response"""

    def is_ready(self) -> bool:
        """Check if session can start new work (not blocked/working)"""
```

**Acceptance Criteria:**
- [ ] Picks next work item based on priority and dependencies
- [ ] Spawns RuntimeExecutor when work starts
- [ ] Pauses execution when blocking event detected
- [ ] Resumes execution after event resolved
- [ ] Handles work completion (mark item DONE, pick next)

---

### 3. Runtime Executor (`runtime/executor.py`)

**Purpose:** Spawn and manage tool processes (Claude Code) in tmux panes.

**Key Files:**
- `src/claude_mpm/commander/runtime/executor.py`
- `src/claude_mpm/commander/runtime/monitor.py`

**Responsibilities:**
- Build launch command using RuntimeAdapter (ClaudeCodeAdapter)
- Create tmux pane with `TmuxOrchestrator.create_pane()`
- Send initial message to tool
- Start RuntimeMonitor for continuous output polling
- Handle tool crashes (detect, log, retry or escalate)

**Interface:**
```python
class RuntimeExecutor:
    def __init__(self, project: Project, tmux: TmuxOrchestrator, adapter: RuntimeAdapter):
        """Initialize with project, tmux client, and runtime adapter"""

    def spawn(self, work_item: WorkItem) -> str:
        """Spawn tool in tmux, return session ID"""

    def send_message(self, session_id: str, message: str) -> None:
        """Send message to running tool"""

    def is_alive(self, session_id: str) -> bool:
        """Check if tool process still running"""

    def kill(self, session_id: str) -> None:
        """Force kill tool session"""

class RuntimeMonitor:
    def __init__(self, session_id: str, tmux: TmuxOrchestrator, parser: OutputParser):
        """Initialize with session ID, tmux client, output parser"""

    def start(self) -> None:
        """Start polling loop in background thread"""

    def stop(self) -> None:
        """Stop polling loop"""

    def _poll_output(self) -> None:
        """Capture output → parse → create events → check for blocking"""
```

**Acceptance Criteria:**
- [ ] Spawns Claude Code in tmux pane with correct working directory
- [ ] Sends initial work item message to tool
- [ ] RuntimeMonitor polls output every 2s
- [ ] Detects blocking events and pauses execution
- [ ] Handles tool crashes (logs error, marks work item FAILED)

---

### 4. Event Resolution Workflow (`workflow/event_handler.py`)

**Purpose:** Coordinate pause/resume of tool execution based on events.

**Key Files:**
- `src/claude_mpm/commander/workflow/event_handler.py`

**Responsibilities:**
- Detect blocking events (EventType.DECISION_NEEDED, APPROVAL)
- Pause RuntimeMonitor when blocking event created
- Wait for event resolution (poll EventManager)
- Resume RuntimeExecutor with user's response
- Handle timeout/no-response scenarios (mark event DISMISSED after 1 hour)

**Interface:**
```python
class EventHandler:
    def __init__(self, event_manager: EventManager):
        """Initialize with EventManager"""

    def handle_event_created(self, event: Event) -> None:
        """Called when OutputParser creates event"""

    def is_blocking(self, event: Event) -> bool:
        """Check if event requires pausing execution"""

    def pause_execution(self, project_id: str) -> None:
        """Pause RuntimeMonitor for project"""

    def resume_execution(self, event: Event) -> None:
        """Resume with event response as tool input"""

    def handle_timeout(self, event: Event) -> None:
        """Auto-dismiss events older than 1 hour"""
```

**Acceptance Criteria:**
- [ ] Detects blocking events (DECISION_NEEDED, APPROVAL)
- [ ] Pauses RuntimeMonitor when blocking event created
- [ ] Resumes with user response after event resolved
- [ ] Auto-dismisses events after 1 hour timeout
- [ ] Non-blocking events (INFO, TASK_COMPLETE) don't pause execution

---

### 5. State Persistence (`persistence/`)

**Purpose:** Save/load all state to survive daemon restarts.

**Key Files:**
- `src/claude_mpm/commander/persistence/state_store.py`
- `src/claude_mpm/commander/persistence/event_store.py`
- `src/claude_mpm/commander/persistence/thread_store.py`

**Storage Format:** JSON files in `~/.claude-mpm/commander/`

**Responsibilities:**
- Serialize/deserialize ProjectRegistry, EventManager, conversation threads
- Atomic writes (write temp → rename) to prevent corruption
- Validation on load (schema checks, handle missing fields)
- Migration support for future schema changes

**Interface:**
```python
class StateStore:
    def __init__(self, persist_dir: Path):
        """Initialize with persistence directory"""

    def save_registry(self, registry: ProjectRegistry) -> None:
        """Save projects.json atomically"""

    def load_registry(self) -> ProjectRegistry:
        """Load projects.json, return empty registry if not found"""

class EventStore:
    def save_events(self, event_manager: EventManager) -> None:
        """Save events.json atomically"""

    def load_events(self) -> EventManager:
        """Load events.json, return empty manager if not found"""

class ThreadStore:
    def save_threads(self, projects: List[Project]) -> None:
        """Save threads.json with all conversation histories"""

    def load_threads(self) -> Dict[str, List[ThreadMessage]]:
        """Load threads.json, return empty dict if not found"""
```

**Acceptance Criteria:**
- [ ] All state saved to JSON files in `~/.claude-mpm/commander/`
- [ ] Atomic writes prevent corruption on crash
- [ ] Load validates schema and handles missing/malformed data
- [ ] Daemon restart recovers all state (projects, events, threads)
- [ ] No data loss when daemon crashes mid-execution

---

### 6. Work Queue (`work/queue.py`, `models/work.py`)

**Purpose:** Manage work items for projects (create, prioritize, execute, track).

**Key Files:**
- `src/claude_mpm/commander/models/work.py`
- `src/claude_mpm/commander/work/queue.py`

**Data Model:**
```python
@dataclass
class WorkItem:
    id: str                          # UUID
    project_id: str                  # Owning project
    title: str                       # Short description
    description: str                 # Full instructions
    priority: int                    # 0 (highest) to 100 (lowest)
    dependencies: List[str]          # Work item IDs that must complete first
    status: WorkStatus               # QUEUED → RUNNING → DONE/FAILED
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]             # Error message if FAILED
```

**Responsibilities:**
- Enqueue work items with priority and dependencies
- Determine next executable item (priority-based, respects dependencies)
- Track work item lifecycle (QUEUED → RUNNING → DONE/FAILED)
- Handle dependency resolution (linear dependencies only in Phase 2)

**Interface:**
```python
class WorkQueue:
    def __init__(self, project_id: str):
        """Initialize for specific project"""

    def enqueue(self, title: str, description: str, priority: int = 50,
                dependencies: List[str] = None) -> WorkItem:
        """Add work item to queue"""

    def get_next(self) -> Optional[WorkItem]:
        """Get next executable item (priority order, dependencies satisfied)"""

    def mark_running(self, work_id: str) -> None:
        """Update status to RUNNING"""

    def mark_done(self, work_id: str) -> None:
        """Update status to DONE"""

    def mark_failed(self, work_id: str, error: str) -> None:
        """Update status to FAILED with error"""

    def list_all(self) -> List[WorkItem]:
        """List all work items"""
```

**Acceptance Criteria:**
- [ ] Can enqueue work items with priority and dependencies
- [ ] `get_next()` respects priority and dependencies
- [ ] Linear dependencies work (A → B → C)
- [ ] Work item status tracked through lifecycle
- [ ] Failed work items don't block queue

---

## Execution Order

**Recommended implementation sequence with dependencies:**

### Sprint 1: Core Daemon (Week 1)

**Ticket #189: Commander Daemon Core**
- Implement `daemon.py` with main loop
- CLI integration: `claude-mpm --commander`
- Basic project session coordination
- Graceful shutdown
- **Blockers:** None (uses existing ProjectRegistry, TmuxOrchestrator)
- **Acceptance:** Daemon starts, runs loop, shuts down cleanly

**Ticket #191: Runtime Executor & Monitor**
- Implement `runtime/executor.py` to spawn tools
- Implement `runtime/monitor.py` for output polling
- Integration with ClaudeCodeAdapter
- Integration with OutputParser
- **Blockers:** None (uses existing TmuxOrchestrator, OutputParser)
- **Acceptance:** Tool spawns in tmux, output monitored, events detected

### Sprint 2: Work Flow & Persistence (Week 2)

**Ticket #192: Work Queue Implementation**
- Implement `models/work.py` WorkItem model
- Implement `work/queue.py` queue operations
- Linear dependency resolution
- Priority-based execution
- **Blockers:** None (standalone module)
- **Acceptance:** Can enqueue, get_next respects priority/deps

**Ticket #193: Project Session Coordinator**
- Implement `project_session.py`
- Work queue integration
- State transition logic
- Coordinate RuntimeExecutor/Monitor
- **Blockers:** Requires #191 (RuntimeExecutor), #192 (WorkQueue)
- **Acceptance:** Session picks work, spawns tools, tracks state

**Ticket #194: State Persistence**
- Implement `persistence/state_store.py`
- Implement `persistence/event_store.py`
- Implement `persistence/thread_store.py`
- Atomic write strategy
- Schema validation on load
- **Blockers:** None (standalone module)
- **Acceptance:** State persists, daemon restart recovers

### Sprint 3: Event Integration (Week 3)

**Ticket #195: Event Resolution Workflow**
- Implement `workflow/event_handler.py`
- Pause/resume logic
- Timeout handling
- Integration with EventManager and RuntimeMonitor
- **Blockers:** Requires #191 (RuntimeMonitor), #193 (ProjectSession)
- **Acceptance:** Tool pauses on event, resumes after resolution

**Ticket #196: End-to-End Integration**
- Wire all components together
- Integration testing
- Multi-project concurrency testing
- Daemon recovery testing
- **Blockers:** Requires ALL previous tickets
- **Acceptance:** Demo script works end-to-end

### Sprint 4: Testing & Documentation (Week 4)

**Ticket #190: Phase 2 Documentation** (This ticket)
- Create `docs/commander/phase2-scope.md` ✅
- Create `docs/commander/user-guide.md`
- Create `docs/commander/architecture.md`
- Create `examples/commander_full_demo.py`
- **Blockers:** None (documentation)

**Integration Tests:**
- `tests/integration/commander/test_daemon_lifecycle.py`
- `tests/integration/commander/test_multi_project.py`
- `tests/integration/commander/test_event_workflow.py`
- `tests/integration/commander/test_persistence.py`

---

## Success Criteria

**Phase 2 is complete when this end-to-end workflow works:**

### Demo Script

```bash
# Terminal 1: Start Commander Daemon
claude-mpm --commander
# Output: Commander daemon started on port 8000
#         Loaded 0 projects from persistence

# Terminal 2: Observe tmux (human monitoring)
tmux attach -t mpm-commander
# See: Empty session, waiting for work

# Terminal 3: Interact via API
# Register project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/user/my-project",
    "name": "My Project"
  }'
# Response: {"id": "proj-abc123", "name": "My Project", "state": "IDLE"}

# Queue work item
curl -X POST http://localhost:8000/api/projects/proj-abc123/work \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement OAuth2 login",
    "description": "Add OAuth2 authentication using Google provider",
    "priority": 10
  }'
# Response: {"id": "work-xyz789", "status": "QUEUED"}

# Watch Terminal 2: See tmux pane created, Claude Code spawning
# Watch Terminal 2: See tool output streaming

# After 30 seconds, check inbox
curl http://localhost:8000/api/inbox
# Response: [
#   {
#     "id": "event-001",
#     "type": "DECISION_NEEDED",
#     "title": "Which OAuth2 library?",
#     "options": ["authlib", "oauthlib", "requests-oauthlib"],
#     "priority": "HIGH"
#   }
# ]

# Watch Terminal 2: Tool execution PAUSED, waiting for response

# Resolve event
curl -X POST http://localhost:8000/api/events/event-001/resolve \
  -H "Content-Type: application/json" \
  -d '{"response": "Use authlib"}'
# Response: {"status": "resolved"}

# Watch Terminal 2: Tool resumes, continues execution

# Check work status
curl http://localhost:8000/api/projects/proj-abc123/work
# Response: [
#   {"id": "work-xyz789", "status": "RUNNING", "started_at": "..."}
# ]

# Wait for completion...
# Watch Terminal 2: Tool completes, pane shows "Done"

# Check final status
curl http://localhost:8000/api/projects/proj-abc123/work/work-xyz789
# Response: {"id": "work-xyz789", "status": "DONE", "completed_at": "..."}

# Kill daemon (Ctrl+C in Terminal 1)
# Restart daemon
claude-mpm --commander
# Output: Commander daemon started on port 8000
#         Loaded 1 project from persistence
#         Project "My Project" (proj-abc123) - state: IDLE

# Verify state recovered
curl http://localhost:8000/api/projects
# Response: [{"id": "proj-abc123", "name": "My Project", "state": "IDLE"}]

curl http://localhost:8000/api/inbox
# Response: [] (resolved events cleared)
```

**Pass Criteria:**
- ✅ Daemon starts and runs continuously
- ✅ Project registered successfully
- ✅ Work item queued and picked by daemon
- ✅ Tool spawns in tmux pane
- ✅ Tool output monitored, event detected
- ✅ Execution pauses on blocking event
- ✅ Event appears in inbox
- ✅ Execution resumes after event resolved
- ✅ Work completes successfully
- ✅ Daemon restart recovers all state

---

## Out of Scope (Deferred to Phase 3)

**Not included in Phase 2:**

1. **Complex Dependency Graphs**
   - DAG resolution (A → B, A → C, B+C → D)
   - Parallel work execution (multiple items per project)
   - Dependency visualization
   - **Rationale:** Phase 2 uses simple linear dependencies (A → B → C)

2. **Advanced Notification Channels**
   - Slack integration
   - Email notifications
   - Webhooks
   - Desktop notifications
   - **Rationale:** Phase 2 uses stdout logging and API polling

3. **WebSocket Support**
   - Real-time event streaming
   - Live output streaming
   - Bi-directional communication
   - **Rationale:** Phase 2 uses REST API polling

4. **Web UI Enhancements**
   - Rich dashboard
   - Work queue visualization
   - Event resolution UI
   - Multi-project timeline
   - **Rationale:** Phase 2 keeps minimal placeholder UI

5. **Multi-Tenancy**
   - User isolation
   - Authentication/authorization
   - Per-user project lists
   - Resource quotas
   - **Rationale:** Phase 2 is single-user daemon

6. **Load Balancing**
   - Intelligent work distribution
   - Resource-aware scheduling
   - Priority-based resource allocation
   - **Rationale:** Phase 2 uses simple round-robin

7. **Automatic Work Generation**
   - Ticket-to-work conversion
   - GitHub issue integration
   - AI-generated work plans
   - **Rationale:** Phase 2 requires manual work item creation via API

8. **Advanced Error Recovery**
   - Automatic retry with backoff
   - Alternative strategy execution
   - Rollback on failure
   - **Rationale:** Phase 2 marks work FAILED and moves to next item

---

## Risk Mitigation

### Known Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| **tmux dependency** | Breaks on Windows, some Unix systems | Check tmux on startup, fail fast with clear error | Planned |
| **Output parsing brittleness** | False positives/negatives | Comprehensive test suite with real outputs, tunable patterns | Existing |
| **State corruption on crash** | Data loss, unrecoverable state | Atomic writes (temp → rename), validation on load | Planned |
| **Event flooding** | Too many events, overwhelm inbox | Deduplication (existing), rate limiting (future) | Partial |
| **Resource exhaustion** | Many projects exhaust FDs/memory | Configurable concurrency limits, monitoring | Planned |
| **Dependency cycles** | Work queue deadlock | Validate on enqueue (reject cycles), timeout detection | Planned |

### Open Questions

1. **Work item creation?** Manual API calls only? Or auto-generate from tickets?
   - **Answer:** Phase 2 is manual API only. Auto-generation in Phase 3.

2. **What triggers work execution?** Immediate on enqueue? Or manual start?
   - **Answer:** Immediate on enqueue if project is IDLE.

3. **How to handle tool crashes?** Retry? Mark failed? Escalate?
   - **Answer:** Mark work FAILED with error, move to next item. Retry in Phase 3.

4. **Notification delivery?** Push (WebSocket) or pull (API polling)?
   - **Answer:** Pull (API polling) in Phase 2. Push in Phase 3.

5. **Multi-user support?** Single daemon for all users? Or per-user daemon?
   - **Answer:** Single-user daemon in Phase 2. Multi-tenancy in Phase 3.

---

## Timeline Estimate

**Total Effort:** 18-24 days (single developer, full-time)

| Sprint | Week | Focus | Tickets | Estimated Days |
|--------|------|-------|---------|----------------|
| **Sprint 1** | Week 1 | Core Daemon | #189, #191 | 5-7 days |
| **Sprint 2** | Week 2 | Work & Persistence | #192, #193, #194 | 5-7 days |
| **Sprint 3** | Week 3 | Event Integration | #195, #196 | 4-6 days |
| **Sprint 4** | Week 4 | Testing & Docs | #190, integration tests | 4-5 days |

**Critical Path:**
- #189 (Daemon) → #193 (ProjectSession) → #196 (Integration)
- #191 (RuntimeExecutor) → #193 (ProjectSession)
- #192 (WorkQueue) → #193 (ProjectSession)

**Parallel Work Opportunities:**
- #194 (Persistence) can develop in parallel with #189-#193
- #190 (Documentation) can write incrementally as features land
- #195 (EventHandler) can develop in parallel with #192-#193

---

## Next Steps

### Immediate Actions (This Week)

1. **Finalize Phase 2 Scope** (This document)
   - ✅ Create `docs/commander/phase2-scope.md`
   - Get stakeholder review and approval
   - Address any scope questions

2. **Create GitHub Issues** (0.5 days)
   - #189: Commander Daemon Core
   - #190: Phase 2 Documentation ✅
   - #191: Runtime Executor & Monitor
   - #192: Work Queue Implementation
   - #193: Project Session Coordinator
   - #194: State Persistence
   - #195: Event Resolution Workflow
   - #196: End-to-End Integration
   - Assign priorities, dependencies, acceptance criteria

3. **Set Up Development Environment** (0.5 days)
   - Verify tmux installed and configured
   - Create test projects for multi-project testing
   - Set up persistent test data directory (`~/.claude-mpm/commander-test/`)
   - Configure debugging tools (logs, tmux attach workflows)

### Week 1: Begin Implementation

- Start with #189 (Commander Daemon Core)
- Set up logging and monitoring infrastructure
- Create basic CLI integration (`claude-mpm --commander`)
- Establish development workflow (tmux debugging, log tailing)

---

## Appendix: File Inventory

### Files to Create (Phase 2)

```
src/claude_mpm/commander/
├── daemon.py                          # Main daemon loop (#189)
├── project_session.py                 # Project lifecycle management (#193)
├── runtime/
│   ├── __init__.py                    # NEW
│   ├── executor.py                    # Spawn tool processes (#191)
│   └── monitor.py                     # Output monitoring (#191)
├── workflow/
│   ├── __init__.py                    # NEW
│   └── event_handler.py               # Event resolution (#195)
├── persistence/
│   ├── __init__.py                    # NEW
│   ├── state_store.py                 # Project registry persistence (#194)
│   ├── event_store.py                 # Event queue persistence (#194)
│   └── thread_store.py                # Conversation persistence (#194)
├── work/
│   ├── __init__.py                    # NEW
│   └── queue.py                       # Work queue operations (#192)
└── models/
    └── work.py                        # WorkItem model (#192)

docs/commander/
├── phase2-scope.md                    # This document (#190) ✅
├── user-guide.md                      # User documentation (#190)
└── architecture.md                    # Architecture diagrams (#190)

tests/integration/commander/
├── __init__.py                        # NEW
├── test_daemon_lifecycle.py           # Daemon start/stop tests (#196)
├── test_multi_project.py              # Concurrent execution (#196)
├── test_event_workflow.py             # Pause/resume workflow (#196)
└── test_persistence.py                # State recovery (#196)

examples/
└── commander_full_demo.py             # Full demo script (#190)
```

### Files to Modify (Phase 2)

```
src/claude_mpm/cli/
├── parsers/base_parser.py             # Add --commander flag
└── __init__.py                        # Route to daemon on --commander

src/claude_mpm/commander/
├── __init__.py                        # Export new classes
└── api/app.py                         # Optional: integrate with daemon
```

### Estimated LOC Delta

**New Code:** ~2,500 lines
- Daemon core: ~400 lines
- ProjectSession: ~300 lines
- Runtime executor/monitor: ~500 lines
- Event handler: ~200 lines
- Persistence: ~400 lines
- Work queue: ~300 lines
- CLI integration: ~100 lines
- Examples/docs: ~300 lines

**Tests:** ~1,500 lines
- Integration tests: ~800 lines
- Unit tests for new components: ~700 lines

**Total Phase 2 Addition:** ~4,000 lines

---

**Document Status:** ✅ Complete
**Next Action:** Create GitHub issues #189-#196 and begin Sprint 1
