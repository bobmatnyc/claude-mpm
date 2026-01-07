# Dashboard Agent Detection Bug Analysis

**Date**: 2026-01-07
**Researcher**: Research Agent
**Issue**: Dashboard "Agents" tab only shows "Research" when multiple agents are active

---

## Executive Summary

The dashboard's agent detection system has a **critical design flaw** that causes it to display only the **most recently delegated agent** instead of tracking all active agents throughout a session. This occurs because agent tracking uses a **single-value storage pattern** (replacing rather than accumulating) in `active_sessions`.

**Root Cause**: Line 422 in `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/main.py`

**Impact**: Users cannot see the full list of agents that have been used during a session, making it appear as if only one agent is working.

---

## Technical Details

### Bug Location

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/main.py`

**Function**: `agent_delegated()` (lines 418-426)

```python
def agent_delegated(self, agent: str, task: str, status: str = "started"):
    """Notify agent delegation."""
    # Update active session with current agent
    if self.session_id and self.session_id in self.active_sessions:
        self.active_sessions[self.session_id]["agent"] = agent  # ← BUG HERE (line 422)
        self.active_sessions[self.session_id]["status"] = status

    if self.broadcaster:
        self.broadcaster.agent_delegated(agent, task, status)
```

### The Problem

**Current Behavior** (line 422):
```python
self.active_sessions[self.session_id]["agent"] = agent  # Singular, replaces previous value
```

This **overwrites** the previous agent value instead of accumulating all agents used.

**Data Structure** (line 383-390):
```python
self.active_sessions[session_id] = {
    "session_id": session_id,
    "start_time": datetime.now(timezone.utc).isoformat(),
    "agent": "pm",  # ← Single value, not a list/set
    "status": ServiceState.RUNNING,
    "launch_method": launch_method,
    "working_dir": working_dir,
}
```

### Example Timeline

```
Time 0:  session_started() → active_sessions["sess1"]["agent"] = "pm"
Time 1:  agent_delegated("engineer") → active_sessions["sess1"]["agent"] = "engineer"  ❌ (PM lost)
Time 2:  agent_delegated("qa") → active_sessions["sess1"]["agent"] = "qa"  ❌ (Engineer lost)
Time 3:  agent_delegated("research") → active_sessions["sess1"]["agent"] = "research"  ❌ (QA lost)

Result: Dashboard shows only "Research" (the last agent)
```

**Expected Behavior**:
```
Time 0:  session_started() → active_sessions["sess1"]["agents"] = ["pm"]
Time 1:  agent_delegated("engineer") → active_sessions["sess1"]["agents"] = ["pm", "engineer"]
Time 2:  agent_delegated("qa") → active_sessions["sess1"]["agents"] = ["pm", "engineer", "qa"]
Time 3:  agent_delegated("research") → active_sessions["sess1"]["agents"] = ["pm", "engineer", "qa", "research"]

Result: Dashboard shows all 4 agents
```

---

## Solution Design

### Option 1: Track Agent History (Recommended)

**Changes Required**:

1. **Update data structure** (line 383-390):
```python
self.active_sessions[session_id] = {
    "session_id": session_id,
    "start_time": datetime.now(timezone.utc).isoformat(),
    "current_agent": "pm",  # Current/most recent agent
    "agents": ["pm"],  # All agents used (ordered list)
    "agent_history": [],  # Optional: with timestamps and tasks
    "status": ServiceState.RUNNING,
    "launch_method": launch_method,
    "working_dir": working_dir,
}
```

2. **Update agent_delegated()** (lines 418-426):
```python
def agent_delegated(self, agent: str, task: str, status: str = "started"):
    """Notify agent delegation."""
    # Update active session with current agent
    if self.session_id and self.session_id in self.active_sessions:
        session = self.active_sessions[self.session_id]

        # Track current agent and status
        session["current_agent"] = agent
        session["status"] = status

        # Add to agent list if not already present (unique agents)
        if agent not in session["agents"]:
            session["agents"].append(agent)

        # Optional: Track detailed history
        session.setdefault("agent_history", []).append({
            "agent": agent,
            "task": task[:100],  # Truncate long tasks
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
        })

    if self.broadcaster:
        self.broadcaster.agent_delegated(agent, task, status)
```

3. **Update dashboard display** to use `agents` list instead of `agent` field.

### Option 2: Track Only Unique Agents (Minimal Change)

**Simpler but less information**:

```python
def agent_delegated(self, agent: str, task: str, status: str = "started"):
    """Notify agent delegation."""
    if self.session_id and self.session_id in self.active_sessions:
        session = self.active_sessions[self.session_id]

        # Initialize agents set if needed
        if "agents" not in session:
            session["agents"] = set([session.get("agent", "pm")])

        # Add new agent to set (automatically handles duplicates)
        session["agents"].add(agent)

        # Keep current_agent for backward compatibility
        session["current_agent"] = agent
        session["status"] = status

    if self.broadcaster:
        self.broadcaster.agent_delegated(agent, task, status)
```

**Pros**: Minimal code change, backward compatible
**Cons**: No ordering, no timestamp tracking, no task history

---

## Impact Analysis

### Affected Components

1. **Backend** (Python):
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/main.py` - Agent tracking logic
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/dashboard_server.py` - Dashboard server relay
   - Any code using `get_active_sessions()` return value

2. **Frontend** (Dashboard):
   - Dashboard Svelte components (need to locate - compiled files found at `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/svelte-build/`)
   - Agents tab display logic
   - Socket.IO event handlers for `agent_delegated` events

### Backward Compatibility

**Breaking Changes**:
- `active_sessions[session_id]["agent"]` → `active_sessions[session_id]["current_agent"]`
- New field: `active_sessions[session_id]["agents"]` (list)

**Migration Path**:
```python
# Maintain backward compatibility
session_data = {
    "agent": agent,  # Deprecated but maintained
    "current_agent": agent,  # New field
    "agents": [...],  # New field
}
```

---

## Testing Requirements

### Unit Tests

```python
def test_agent_delegation_tracking():
    """Test that multiple agent delegations are tracked correctly."""
    server = SocketIOServer()
    server.session_started("test-session", "cli", "/test/dir")

    # Delegate to multiple agents
    server.agent_delegated("engineer", "Implement feature X")
    server.agent_delegated("qa", "Test feature X")
    server.agent_delegated("research", "Research patterns")

    # Verify all agents are tracked
    sessions = server.get_active_sessions()
    assert len(sessions) == 1
    session = sessions[0]

    assert session["current_agent"] == "research"  # Most recent
    assert set(session["agents"]) == {"pm", "engineer", "qa", "research"}
    assert len(session["agent_history"]) == 3  # PM not in history (only delegations)
```

### Integration Tests

1. **Multi-Agent Session Test**: Start session, delegate to 5+ agents, verify dashboard shows all
2. **Session Cleanup Test**: Verify old sessions are pruned correctly with new data structure
3. **Event Broadcasting Test**: Verify `agent_delegated` events broadcast correctly
4. **Dashboard Display Test**: Verify frontend renders all agents in "Agents" tab

---

## Recommendations

### Immediate Actions (High Priority)

1. ✅ **Fix agent tracking logic** using Option 1 (agent history)
2. ✅ **Update frontend dashboard** to display `agents` list instead of single `agent` field
3. ✅ **Add unit tests** for multi-agent tracking
4. ✅ **Add integration test** simulating realistic multi-agent workflow

### Follow-Up Actions (Medium Priority)

1. **Add agent activity timeline** in dashboard (use `agent_history` for visualization)
2. **Add agent performance metrics** (time spent per agent, tasks completed)
3. **Add session replay feature** using detailed agent history
4. **Document agent tracking API** for future dashboard enhancements

### Documentation Updates (Low Priority)

1. Update architecture docs to explain agent tracking system
2. Update dashboard docs to explain "Agents" tab functionality
3. Add troubleshooting guide for agent detection issues

---

## Related Issues

### Potential Similar Bugs

Search for other single-value storage patterns that should accumulate:
```bash
grep -r "self\\..*\\[.*\\] = " src/claude_mpm/services/socketio/ | grep -v "__"
```

**Candidates for review**:
- `claude_status` - Should this track status history?
- `event_history` - Already uses `deque`, ✅ correct pattern
- `client_info` - Overwrite is correct (per-client data)

---

## Appendix A: README Analysis

### Sections to Extract from README

The current README mixes installation instructions with use case narratives. The following sections should be extracted into separate documentation:

#### 1. "Absolute Beginner's Guide" Content (Lines 16-18)

**Current Location**: Inline callout in README
```markdown
> **🆕 NEW for Founders!** Not a software engineer? **[Start with our Absolute Beginner's Guide](docs/absolute-beginners-guide.md)** — designed specifically for non-technical founders and business leaders who want to understand and oversee their technical projects. No coding experience required!
```

**Recommendation**:
- Extract to: `docs/usecases/non-technical-users.md`
- Include: Terminology guide, workflow overview, delegation examples
- Link from README with simple one-liner: "👥 [For Non-Technical Users](docs/usecases/non-technical-users.md)"

#### 2. Founder/PM Use Cases (Scattered Throughout)

**Current Mentions**:
- Line 17: "non-technical founders and business leaders"
- Agent descriptions mention "project oversight" capabilities
- Resume logs section mentions "complex codebases" (PM context)

**Recommendation**:
- Extract to: `docs/usecases/project-managers.md`
- Include: Delegation patterns, agent selection guide, monitoring workflows
- Include: Resume logs for PM handoffs, session management for team oversight

#### 3. Developer Use Cases (Implicit, Not Explicit)

**Current State**: Developer use cases are embedded in feature descriptions

**Recommendation**:
- Create: `docs/usecases/developers.md`
- Include: Multi-agent workflows for coding tasks
- Include: Integration with existing dev tools (git, testing, CI/CD)
- Include: Agent selection for development tasks (Engineer, QA, Security, etc.)

#### 4. Detailed Feature Explanations (Currently in README)

**Sections That Are Too Detailed for README**:
- Lines 92-93: Resume Log System (entire section ~50 lines)
- Lines 658-672: Agent Memory System (implementation details)
- Lines 673-707: Skills System (detailed configuration)

**Recommendation**:
- Keep brief overview in README (3-5 lines each)
- Move detailed documentation to:
  - `docs/features/resume-logs.md` (already exists, ✅ good)
  - `docs/features/agent-memory.md` (create)
  - `docs/features/skills-system.md` (create)

### Suggested README Structure (Simplified)

```markdown
# Claude MPM - Multi-Agent Project Manager

[Brief description - 2-3 paragraphs]

## Quick Start
[Installation - 5 lines max]
[First steps - 5 lines max]

## Who Should Use Claude MPM?
- 👥 [Non-Technical Users](docs/usecases/non-technical-users.md) - Founders, PMs, business leaders
- 💻 [Developers](docs/usecases/developers.md) - Software engineers, DevOps, QA
- 🏢 [Teams](docs/usecases/teams.md) - Collaboration and project oversight

## Key Features (Brief)
- Multi-Agent Orchestration → [Learn More](docs/features/agents.md)
- Git Repository Integration → [Learn More](docs/features/git-repos.md)
- Skills System → [Learn More](docs/features/skills.md)
- Real-Time Monitoring → [Learn More](docs/features/monitoring.md)
- Session Management → [Learn More](docs/features/sessions.md)

## Documentation
[Links to comprehensive docs]

## Development
[Contributing guide links]

## License
[License info]
```

### Files to Create

1. `docs/usecases/non-technical-users.md` - For founders, PMs, non-engineers
2. `docs/usecases/developers.md` - For software engineers
3. `docs/usecases/teams.md` - For collaborative workflows
4. `docs/features/agent-memory.md` - Detailed memory system docs
5. `docs/features/skills-system.md` - Detailed skills docs (may already exist)

### Benefits of Extraction

1. **README Clarity**: Reduce README from ~918 lines to ~200 lines
2. **Audience Segmentation**: Users can jump directly to relevant content
3. **Maintenance**: Easier to update specific use cases without touching README
4. **Discoverability**: Better SEO and navigation for specific user types
5. **Onboarding**: Clearer entry points for different user personas

---

## Appendix B: Dashboard Source Code Location

### Compiled Dashboard

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/svelte-build/`

**Structure**:
```
dashboard/
├── api/           # Backend API handlers
├── static/
│   └── svelte-build/  # Compiled Svelte application
│       ├── _app/
│       │   ├── immutable/
│       │   │   ├── chunks/    # Compiled JS chunks
│       │   │   ├── entry/     # Entry points
│       │   │   └── nodes/     # Route nodes
│       │   └── env.js
│       └── index.html (likely)
```

**Note**: Original Svelte source files (.svelte) are **not in the repository** - only compiled JavaScript is present. This makes frontend debugging difficult.

### Source Code Repository

**Recommendation**: Locate the Svelte source code repository:
1. Check git submodules: `git submodule status`
2. Check package.json or build scripts for source location
3. Search for separate dashboard repository

**Alternative**: Use browser DevTools to inspect:
1. Open dashboard in browser
2. Use DevTools → Sources tab
3. Examine Socket.IO event handlers for agent display logic
4. Search for "agent" in compiled JavaScript to find rendering logic

---

## Appendix C: Agent Delegation Event Flow

### Complete Event Flow

```
1. PM Agent delegates to Engineer
   ↓
2. claude_runner.py calls websocket_server.agent_delegated("engineer", task)
   ↓
3. SocketIOServer.agent_delegated() (main.py:418)
   ├─→ Update active_sessions[session_id]["agent"] = "engineer"  ❌ BUG
   └─→ broadcaster.agent_delegated("engineer", task)
       ↓
4. SocketIOEventBroadcaster.broadcast_event("agent_delegated", {...})
   ↓
5. Socket.IO emits event to all connected dashboard clients
   ↓
6. Dashboard receives event → Updates "Agents" tab display
```

### Event Payload

**Current** (from broadcaster.py:451-455):
```python
{
    "agent": "engineer",  # Agent name
    "task": "Implement feature X",  # Task description
    "status": "started"  # Status: started, completed, failed
}
```

**Proposed** (enhanced):
```python
{
    "agent": "engineer",
    "task": "Implement feature X",
    "status": "started",
    "timestamp": "2026-01-07T10:30:00Z",  # NEW
    "session_id": "sess-123",  # NEW (for multi-session dashboards)
    "all_agents": ["pm", "engineer", "qa", "research"],  # NEW
}
```

---

## Conclusion

The dashboard agent detection bug is caused by a **single-value storage pattern** in `active_sessions[session_id]["agent"]` that overwrites previous agents instead of accumulating them. The fix requires changing this to a **list-based accumulation pattern** (`agents` field) with optional detailed history tracking (`agent_history` field).

**Estimated Effort**:
- Backend fix: 2-4 hours (including tests)
- Frontend update: 2-4 hours (locate source, update display logic)
- Testing and validation: 2-4 hours
- **Total**: 6-12 hours

**Priority**: **High** - This affects core dashboard functionality and user experience.

---

**Next Steps**:
1. Confirm fix approach with team (Option 1 vs Option 2)
2. Locate dashboard Svelte source code
3. Implement backend changes with tests
4. Update frontend display logic
5. Conduct integration testing with realistic multi-agent workflows
