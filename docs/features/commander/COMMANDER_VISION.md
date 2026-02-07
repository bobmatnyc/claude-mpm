# MPM Commander: Vision & Architecture

**Document Type**: Vision & Architecture Design
**Created**: 2026-01-18
**Status**: Living Document
**Audience**: Contributors, Stakeholders, Future Developers

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Vision](#core-vision)
3. [The Evolution of Development Tools](#the-evolution-of-development-tools)
4. [Key Principles](#key-principles)
5. [Architecture Overview](#architecture-overview)
6. [User Experience Vision](#user-experience-vision)
7. [Technical Architecture](#technical-architecture)
8. [Differentiation & Market Position](#differentiation--market-position)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Success Metrics](#success-metrics)
11. [Future Possibilities](#future-possibilities)

---

## Executive Summary

**MPM Commander** is an event-driven, swarm-capable, framework-agnostic orchestration layer for AI-assisted development. It represents the next evolution in how developers interact with AI coding assistants.

### The Vision in One Sentence

> Commander abstracts CLI interactions with AI assistants the same way CLIs abstracted IDE interactions—providing **LLM-summarized oversight** of multiple autonomous workstreams instead of raw terminal output.

### Current State (January 2026)

- ✅ **Phase 1-2 Complete**: Robust infrastructure (tmux orchestration, REST API, event system, state persistence)
- 🟡 **Phase 3 Partial**: Chat interface exists but needs enhancement
- 🔴 **Phase 4-6**: Multi-runtime support, enhanced reliability, advanced UI features pending

### What Works Today

```bash
$ uv run claude-mpm commander
Commander v5.6+ - Multi-Project Orchestration

commander> /project add ~/my-app
✓ Registered project 'my-app'

commander> /framework claude-code
✓ Started Claude Code instance in tmux session

commander> Analyze the authentication flow and suggest improvements
[Commander proxies message to Claude Code, captures output, summarizes]

Summary: Found 3 security vulnerabilities in OAuth2 implementation.
Suggests: 1) Add PKCE flow, 2) Implement token rotation, 3) Add rate limiting

commander> /status
Active Sessions: 1
  └─ my-app (claude-code) - Analyzing authentication
Work Queue: Empty
Recent Events: None
```

### What's Coming Next

- **Multi-day autonomous execution** with checkpoint/resume
- **LLM-powered summarization** of all work (not just raw output)
- **Multiple concurrent workstreams** coordinated intelligently
- **Framework-agnostic** support (Claude Code, Aider, custom tools)
- **Observer/Drop-In/Director modes** for different interaction styles

---

## Core Vision

### From Tools to Orchestration

The progression of development assistance:

```
┌──────────────────────────────────────────────────────────┐
│ Phase 1: IDE Copilots (2021-2023)                       │
│ ─────────────────────────────────────────────────────── │
│ • Inline suggestions                                    │
│ • Single file/function scope                            │
│ • Synchronous, real-time                                │
│ • Duration: Minutes                                      │
│ • Example: GitHub Copilot                               │
└──────────────────────────────────────────────────────────┘
                        ↓ Evolution
┌──────────────────────────────────────────────────────────┐
│ Phase 2: CLI Assistants (2023-2025)                     │
│ ─────────────────────────────────────────────────────── │
│ • Conversational interaction                             │
│ • Multi-file project scope                               │
│ • Session-based context                                  │
│ • Duration: Hours                                        │
│ • Example: Claude Code, Aider, Cursor                   │
└──────────────────────────────────────────────────────────┘
                        ↓ Evolution
┌──────────────────────────────────────────────────────────┐
│ Phase 3: Orchestration Layer (2025+) ← WE ARE HERE      │
│ ─────────────────────────────────────────────────────── │
│ • Multi-workstream coordination                          │
│ • Days/weeks duration                                    │
│ • LLM-summarized oversight                               │
│ • Framework-agnostic backends                            │
│ • Event-driven automation                                │
│ • Example: MPM Commander                                 │
└──────────────────────────────────────────────────────────┘
```

### The Commander Philosophy

Commander embodies three fundamental shifts:

1. **From Output to Summaries**
   - Users don't want to see 1000 lines of LLM reasoning
   - They want to know: "What was accomplished? What's blocked? What needs my input?"
   - Commander uses LLMs to summarize LLM output—meta-intelligence

2. **From Sessions to Workstreams**
   - A session is a technical construct (one terminal, one instance)
   - A workstream is a business construct (implementing a feature across multiple files/projects)
   - Commander manages workstreams that span multiple sessions

3. **From Synchronous to Event-Driven**
   - Traditional: User asks → AI responds → User asks again
   - Commander: User sets goals → AI works autonomously → Events trigger user involvement
   - Humans intervene at decision points, not every step

---

## The Evolution of Development Tools

### Historical Context

Understanding where we came from helps clarify where we're going.

#### Era 1: Text Editors (1960s-1990s)
- **Tools**: vi, Emacs, Sublime Text
- **Interaction**: Manual typing, no assistance
- **Developer Role**: 100% hands-on
- **Scalability**: Linear (1 developer = 1 workspace)

#### Era 2: Integrated Development Environments (1990s-2020s)
- **Tools**: Visual Studio, IntelliJ, VS Code
- **Interaction**: Syntax highlighting, autocomplete, linting
- **Developer Role**: 95% hands-on, 5% tool-assisted
- **Scalability**: Linear (1 developer = 1 workspace)

#### Era 3: AI Copilots (2020-2023)
- **Tools**: GitHub Copilot, Tabnine
- **Interaction**: Inline suggestions, code completion
- **Developer Role**: 70% hands-on, 30% AI-assisted
- **Scalability**: Linear (1 developer = 1 workspace)

#### Era 4: Conversational AI Assistants (2023-2025)
- **Tools**: Claude Code, Aider, Cursor, v0.dev
- **Interaction**: Natural language conversation
- **Developer Role**: 40% hands-on, 60% AI-assisted
- **Scalability**: Linear (1 developer = 1 AI session)

#### Era 5: Orchestrated AI Swarms (2025+) ← **Commander Era**
- **Tools**: MPM Commander + Multiple AI backends
- **Interaction**: Goal-setting, decision-making, oversight
- **Developer Role**: 20% hands-on, 80% strategic direction
- **Scalability**: **Non-linear** (1 developer = N concurrent workstreams)

### The Abstraction Ladder

Each era abstracts away lower-level concerns:

```
┌─────────────────────────────────────────────┐
│  Developer Focus (2025+)                    │
│  "What should we build and why?"            │
│  ──────────────────────────────────────     │
│  Commander abstracts: How to coordinate     │
│  multiple AI workstreams                    │
└─────────────────────────────────────────────┘
                  ↑
┌─────────────────────────────────────────────┐
│  Session Management (2023-2025)             │
│  "How should this feature be implemented?"  │
│  ──────────────────────────────────────     │
│  CLI tools abstract: Code writing patterns  │
└─────────────────────────────────────────────┘
                  ↑
┌─────────────────────────────────────────────┐
│  Code Assistance (2020-2023)                │
│  "What code do I need to write?"            │
│  ──────────────────────────────────────     │
│  Copilots abstract: Syntax and APIs         │
└─────────────────────────────────────────────┘
                  ↑
┌─────────────────────────────────────────────┐
│  IDE Features (1990s-2020)                  │
│  "Where is this function defined?"          │
│  ──────────────────────────────────────     │
│  IDEs abstract: File management             │
└─────────────────────────────────────────────┘
```

Commander is not replacing CLI tools—it's adding a coordination layer above them.

---

## Key Principles

### 1. Framework Agnostic

Commander doesn't care what AI tool you use. It works with:

- **Claude Code**: Anthropic's official CLI
- **Aider**: Git-native AI pair programmer
- **MPM Framework**: Multi-agent project manager with delegation
- **Custom Tools**: Any CLI tool with stdin/stdout interface

```python
# Adapter Pattern
class RuntimeAdapter(ABC):
    @abstractmethod
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        """Generate command to launch this framework."""

class ClaudeCodeAdapter(RuntimeAdapter):
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        return ["claude", "--cwd", project_path]

class AiderAdapter(RuntimeAdapter):
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        return ["aider", "--yes", "--no-pretty", project_path]

class MPMAdapter(RuntimeAdapter):
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        return ["uv", "run", "claude-mpm", "--project", project_path]
```

**Why This Matters**: As new AI tools emerge, Commander adapts. No vendor lock-in.

---

### 2. Event-Driven Architecture

Everything that happens in Commander is an event:

```python
# Event Types
class EventType(Enum):
    # Runtime Events
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    OUTPUT_RECEIVED = "output_received"

    # Decision Events (require user input)
    DECISION_REQUIRED = "decision_required"
    APPROVAL_REQUESTED = "approval_requested"
    ERROR_OCCURRED = "error_occurred"

    # Work Events
    WORK_COMPLETED = "work_completed"
    WORK_FAILED = "work_failed"
    MILESTONE_REACHED = "milestone_reached"

    # System Events
    STATE_CHANGED = "state_changed"
    HEALTH_CHECK_FAILED = "health_check_failed"
```

**Event Flow Example**:

```
User queues work: "Implement user authentication"
    ↓
EVENT: work_queued
    ↓
RuntimeExecutor spawns Claude Code instance
    ↓
EVENT: session_started
    ↓
Work item sent to instance
    ↓
Claude Code asks: "Use JWT or session tokens?"
    ↓
EVENT: decision_required (blocks workstream)
    ↓
Commander notifies user
    ↓
User responds: "Use JWT"
    ↓
EVENT: decision_resolved
    ↓
RuntimeExecutor resumes work
    ↓
Claude Code completes implementation
    ↓
EVENT: work_completed
    ↓
Commander summarizes result
    ↓
User sees: "✓ Implemented JWT auth with refresh tokens"
```

**Why This Matters**: Events enable reactive UIs, integrations, and automation without tight coupling.

---

### 3. Swarm Coordination

Commander doesn't just manage one AI—it orchestrates many:

```
┌─────────────────────────────────────────────────────────┐
│                    Commander                             │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Workstream 1 │  │ Workstream 2 │  │ Workstream 3 │ │
│  │ frontend-ui  │  │ backend-api  │  │ mobile-app   │ │
│  │              │  │              │  │              │ │
│  │ Framework:   │  │ Framework:   │  │ Framework:   │ │
│  │ Claude Code  │  │ Aider        │  │ MPM          │ │
│  │              │  │              │  │              │ │
│  │ Task:        │  │ Task:        │  │ Task:        │ │
│  │ Build login  │  │ Add OAuth    │  │ Design UX    │ │
│  │ component    │  │ endpoints    │  │ flow         │ │
│  │              │  │              │  │              │ │
│  │ Status:      │  │ Status:      │  │ Status:      │ │
│  │ In Progress  │  │ Blocked on   │  │ Completed    │ │
│  │              │  │ frontend     │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         ↓                  ↓                  ↓         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ tmux pane 1  │  │ tmux pane 2  │  │ tmux pane 3  │ │
│  │ (Claude CLI) │  │ (Aider CLI)  │  │ (MPM CLI)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Coordination Features**:
- **Dependency tracking**: Workstream 2 waits for Workstream 1 to complete
- **Resource allocation**: Only N concurrent sessions (configurable)
- **Priority queuing**: High-priority work preempts low-priority
- **Conflict resolution**: Detect when workstreams touch same files

---

### 4. Long-Running Sessions

Commander is built for persistence:

```python
# State Persistence
class CommanderState:
    projects: Dict[str, ProjectSession]
    work_queue: WorkQueue
    event_inbox: EventInbox
    active_sessions: Dict[str, RuntimeSession]

    def save_to_disk(self, path: str):
        """Checkpoint entire state to JSON."""

    @classmethod
    def load_from_disk(cls, path: str) -> "CommanderState":
        """Restore state from checkpoint."""
```

**Multi-Day Workflow**:

```
Day 1:
  User: "Build a REST API for user management"
  Commander: Starts work, completes 60%, checkpoints state
  User: Ctrl+C (end of workday)
  Commander: Saves state, graceful shutdown

Day 2:
  User: Restarts Commander
  Commander: Recovers state, resumes work at 60%
  Commander: Asks decision question, user responds
  Commander: Continues to 85%, checkpoints

Day 3:
  Commander: Auto-resumes on startup
  Commander: Completes remaining 15%
  Commander: Notifies user of completion
```

**Why This Matters**: Real projects take days/weeks. Ephemeral sessions don't match reality.

---

### 5. Summary-First UX

Users don't need to see every token the AI generates. They need **signal, not noise**.

**Traditional CLI Output**:
```
> claude analyze authentication.py
Let me analyze this authentication module. First, I'll examine
the imports to understand dependencies...

[500 lines of reasoning]

...so in summary, there are 3 security issues.
```

**Commander Summary**:
```
commander> Analyze authentication module

✓ Analysis complete (45s)

Summary:
  • Found 3 security vulnerabilities
  • Suggests migrating from session to JWT auth
  • Recommends adding rate limiting

Vulnerabilities:
  1. Missing CSRF protection on login endpoint
  2. Passwords hashed with MD5 (use bcrypt)
  3. No brute-force protection

Next Steps:
  [ ] Fix CSRF issue
  [ ] Migrate to bcrypt
  [ ] Add rate limiting

Type 'detail' for full analysis | 'approve' to fix | 'dismiss'
```

**How It Works**:

```python
# LLM-Powered Summarization
class OutputSummarizer:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.client = openrouter_client

    async def summarize(self, raw_output: str, context: str) -> Summary:
        prompt = f"""
        You are summarizing output from a coding assistant.

        Context: {context}
        Raw Output: {raw_output}

        Provide:
        1. One-line summary
        2. Key findings (bullet points)
        3. Recommended next steps
        4. Any blockers/questions

        Be concise. Maximum 200 words.
        """

        response = await self.client.complete(prompt)
        return Summary.parse(response)
```

**Why This Matters**: Developers are time-constrained. Summaries = faster decision-making.

---

### 6. Drop-In Capability

Sometimes the AI gets stuck or heads in the wrong direction. Commander lets you **drop into any session** to correct course:

```
commander> /sessions
Active Sessions:
  1. frontend-ui (Claude Code) - Building login form
  2. backend-api (Aider) - Adding OAuth endpoints
  3. docs-update (MPM) - Updating API documentation

commander> /attach 1
Attached to frontend-ui session (Claude Code)

[frontend-ui]> what are you working on?
Claude Code: I'm implementing the login form component.
Currently adding form validation.

[frontend-ui]> Use Formik for form handling, not manual validation
Claude Code: Got it, switching to Formik.

[frontend-ui]> /detach
Detached from frontend-ui. Returning to Commander.

commander> /status
Sessions: 3 active
  └─ frontend-ui: Updated to use Formik (following user guidance)
```

**Why This Matters**: Full automation isn't always possible. Human course-correction is essential.

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│                  USER INTERFACE LAYER                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Chat CLI     │  │  REST API    │  │  Web UI      │  │
│  │ (Primary)    │  │ (Automation) │  │  (Future)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│               SUMMARIZATION LAYER                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ OpenRouter Client (LLM Provider)                  │  │
│  │ - Prompt templates for summarization              │  │
│  │ - Output → concise summaries                      │  │
│  │ - Event → natural language notifications          │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│               CONTEXT CONTROLLER                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Session      │  │  Memory      │  │  Context     │  │
│  │ Context      │  │  System      │  │  Manager     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  - Track active instance per user                       │
│  - Maintain conversation history                        │
│  - Prompt context optimization                          │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│                 EVENT BUS / SWARM                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ EventManager (Centralized Event Hub)              │  │
│  │ - Event queue (priority-based)                    │  │
│  │ - Event inbox (blocking events)                   │  │
│  │ - Event routing (session → user)                  │  │
│  │ - Event deduplication                             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Workstream   │  │ Workstream   │  │ Workstream   │  │
│  │ Coordinator  │  │ Scheduler    │  │ Monitor      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│               INSTANCE MANAGER                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ TmuxOrchestrator                                  │  │
│  │ - Session/pane lifecycle                          │  │
│  │ - I/O operations (send/capture)                   │  │
│  │ - Health monitoring                               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Runtime      │  │ Runtime      │  │ Output       │  │
│  │ Executor     │  │ Monitor      │  │ Poller       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│              FRAMEWORK ADAPTERS                          │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Claude Code  │  │    Aider     │  │     MPM      │  │
│  │  Adapter     │  │   Adapter    │  │   Adapter    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Each adapter provides:                                 │
│  - Launch command generation                            │
│  - Framework-specific prompt templates                  │
│  - Output parsing rules                                 │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│              PERSISTENCE LAYER                           │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  State       │  │    Event     │  │    Work      │  │
│  │  Store       │  │    Store     │  │    Store     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  - JSON-based persistence (current)                     │
│  - SQLite support (future)                              │
│  - Checkpoint/restore on crash                          │
└─────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│                 PROCESS LAYER                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              tmux: "mpm-commander"                │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │  │
│  │  │Pane 1│  │Pane 2│  │Pane 3│  │Pane 4│  ...     │  │
│  │  │ CC   │  │Aider │  │ MPM  │  │ CC   │          │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Data Flow: User Command to Response

```
1. User types: "Analyze auth module"
   ↓
2. Chat CLI parses input
   ↓
3. Context Controller determines active session
   ↓
4. Message sent to RuntimeExecutor for that session
   ↓
5. RuntimeExecutor sends to tmux pane (Claude Code instance)
   ↓
6. OutputPoller captures response from tmux
   ↓
7. OutputParser detects events (decisions, errors, completions)
   ↓
8. EventManager routes events to inbox (if blocking) or queue
   ↓
9. Summarizer sends raw output to OpenRouter for summarization
   ↓
10. Summary returned to Chat CLI
    ↓
11. User sees concise summary, not raw output
```

### Critical Components Deep Dive

#### Component 1: TmuxOrchestrator

**Responsibility**: Manage tmux sessions and panes for isolated AI instances

```python
class TmuxOrchestrator:
    """Low-level tmux session and pane management."""

    def create_session(self, session_name: str) -> str:
        """Create a new tmux session."""

    def create_pane(self, session_name: str) -> str:
        """Create a new pane in existing session."""

    def send_keys(self, target: str, keys: str):
        """Send input to a pane."""

    def capture_pane(self, target: str, start: int, end: int) -> str:
        """Capture output from a pane."""

    def kill_pane(self, target: str):
        """Terminate a pane."""
```

**Why tmux?**
- Process isolation (each AI instance in separate pane)
- Output capture without polluting Commander's stdout
- Persistent sessions (survive Commander restarts)
- Attach/detach for user drop-in

---

#### Component 2: RuntimeExecutor

**Responsibility**: Spawn and manage AI framework instances

```python
class RuntimeExecutor:
    """High-level runtime instance management."""

    def __init__(
        self,
        orchestrator: TmuxOrchestrator,
        adapter: RuntimeAdapter
    ):
        self.orchestrator = orchestrator
        self.adapter = adapter

    async def spawn(
        self,
        project_path: str,
        framework: str,
        **kwargs
    ) -> RuntimeSession:
        """
        Spawn a new AI instance in tmux.

        Steps:
        1. Create tmux pane
        2. Generate launch command from adapter
        3. Send launch command to pane
        4. Wait for instance to be ready
        5. Return RuntimeSession handle
        """

    async def send_message(self, session_id: str, message: str):
        """Send a message to running instance."""

    async def terminate(self, session_id: str):
        """Gracefully shut down instance."""
```

**Why This Matters**: Abstracts framework-specific launch details. Adding Aider support = write `AiderAdapter`, not modify RuntimeExecutor.

---

#### Component 3: EventManager

**Responsibility**: Centralized event hub for all system events

```python
class EventManager:
    """Event bus for Commander system."""

    def __init__(self):
        self.queue = PriorityQueue()  # Non-blocking events
        self.inbox = EventInbox()     # Blocking events
        self.handlers = {}            # Event type → handler mapping

    def emit(self, event: Event):
        """
        Emit an event.

        Routing logic:
        - Blocking events (decisions, approvals) → inbox
        - Non-blocking events → queue
        - All events → event store (persistence)
        """

    def subscribe(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type."""

    async def process_queue(self):
        """Process non-blocking events from queue."""

    def get_blocking_events(self) -> List[Event]:
        """Get events that need user resolution."""
```

**Event Priority Levels**:
- **CRITICAL**: System errors, health check failures
- **HIGH**: Blocking events (decisions, approvals)
- **MEDIUM**: Work completion, milestone reached
- **LOW**: Informational events (state changes)

---

#### Component 4: OpenRouter Client (Summarizer)

**Responsibility**: LLM-powered summarization of AI output

```python
class OpenRouterClient:
    """Client for OpenRouter API (multi-model provider)."""

    async def complete(
        self,
        prompt: str,
        model: str = "anthropic/claude-3-5-sonnet",
        max_tokens: int = 500
    ) -> str:
        """Send a completion request."""

class OutputSummarizer:
    """Summarize AI instance output for users."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def summarize_output(
        self,
        raw_output: str,
        context: str
    ) -> Summary:
        """
        Summarize lengthy AI output.

        Prompt template:
        - What was accomplished?
        - What's next?
        - Any blockers?
        - Concise bullet points
        """

    async def summarize_event(
        self,
        event: Event
    ) -> str:
        """
        Convert event to natural language.

        Example:
        Event(type=DECISION_REQUIRED, data="Choose auth library")
        → "Claude Code needs your input: Which authentication
           library should be used? (authlib or oauthlib)"
        """
```

**Cost Optimization**:
- Use smaller, faster models for summaries (Claude Haiku, GPT-3.5)
- Cache common summaries
- Batch summarization requests
- User-configurable summary verbosity

---

#### Component 5: WorkQueue

**Responsibility**: Priority-based work item queue for autonomous execution

```python
class WorkQueue:
    """Priority queue for work items."""

    def add(self, work_item: WorkItem):
        """Add work to queue."""

    def get_next(self, project_id: str) -> Optional[WorkItem]:
        """Get highest-priority unblocked work for a project."""

    def block(self, work_id: str, reason: str):
        """Mark work as blocked (paused)."""

    def unblock(self, work_id: str):
        """Resume blocked work."""

    def get_status(self) -> QueueStatus:
        """Get queue statistics."""
```

**Work Item Structure**:
```python
class WorkItem:
    id: str
    project_id: str
    description: str
    priority: Priority  # CRITICAL, HIGH, MEDIUM, LOW
    dependencies: List[str]  # Other work items that must complete first
    status: WorkStatus  # PENDING, IN_PROGRESS, BLOCKED, COMPLETED, FAILED
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
```

**Queue Behaviors**:
- **Priority**: CRITICAL > HIGH > MEDIUM > LOW
- **Dependencies**: Wait for dependencies to complete before starting
- **Blocking**: Pause work when decision/approval needed
- **Resume**: Auto-resume when blocking event resolved

---

## User Experience Vision

### Interaction Modes

Commander supports different levels of user involvement:

#### 1. Observer Mode (Minimal Interaction)

User sets long-term goals and receives periodic summaries.

```
Day 1:
commander> /project add ~/my-saas-app
commander> /framework mpm
commander> Queue work: Build MVP with user auth, payment integration,
           and admin dashboard. Target: 2 weeks.

✓ Work queued (3 major milestones, 47 sub-tasks)

Commander will work autonomously and notify you of:
  • Blocking decisions
  • Milestone completions
  • Critical errors

Notification preferences: [Slack, Email, Dashboard]

─────────────────────────────────────────────────

Day 3 (User checks in):
commander> /summary week

Week Summary (3 days):
  ✓ User authentication - COMPLETED
    - JWT with refresh tokens
    - Email verification flow
    - Password reset

  ⏳ Payment integration - 60% COMPLETE
    - Stripe SDK integrated
    - Checkout flow implemented
    - Waiting on: Webhook security decision (notification sent)

  ⏸ Admin dashboard - NOT STARTED
    - Blocked by: Payment completion

  📊 Progress: 40% complete overall

  Issues: 2 blockers (1 needs your input)

commander> /approve webhook-decision stripe-signature-verification

✓ Decision resolved. Work resuming...
```

**When to Use**: Multi-week projects, overnight/weekend work, high trust in AI

---

#### 2. Drop-In Mode (Tactical Intervention)

User monitors summaries and drops in when course correction needed.

```
commander> /status

Active Workstreams: 2

  1. backend-api (Aider) - IN_PROGRESS
     Current: Adding GraphQL subscriptions
     Progress: 70%

  2. frontend-app (Claude Code) - BLOCKED
     Blocked on: Design decision for state management

commander> /attach 2

Attached to frontend-app (Claude Code)

[frontend-app]> What's the state management question?

Claude Code: I'm choosing between Redux Toolkit and Zustand
for state management. The app has moderate complexity with
real-time updates.

My analysis:
- Redux Toolkit: More boilerplate, better DevTools, established
- Zustand: Minimal boilerplate, smaller bundle, sufficient for needs

Recommendation: Zustand (simpler, faster, adequate)

[frontend-app]> Agree. Use Zustand. Also, make sure WebSocket
                state is separate from UI state.

Claude Code: Got it. Using Zustand for UI state, custom hook
for WebSocket state separation.

[frontend-app]> /detach

Detached. Workstream unblocked.

commander> /status
Active Workstreams: 2
  1. backend-api - IN_PROGRESS (75%)
  2. frontend-app - IN_PROGRESS (resumed, 45%)
```

**When to Use**: Active development, learning new codebase, complex technical decisions

---

#### 3. Director Mode (High-Level Guidance)

User provides strategic direction across multiple workstreams.

```
commander> /workstreams

Workstreams (5 active):
  1. backend-api (Aider) - Adding real-time features
  2. frontend-app (Claude Code) - Building UI components
  3. mobile-app (MPM) - iOS implementation
  4. docs-site (Claude Code) - API documentation
  5. infra-deploy (Aider) - Kubernetes setup

commander> Prioritize mobile-app over docs-site.
           We need iOS ready for beta launch next week.

✓ Updated priorities:
  mobile-app: HIGH → CRITICAL
  docs-site: MEDIUM → LOW

  Reallocating resources...
  docs-site paused, mobile-app now has 2 instances (was 1)

commander> For backend-api: Make sure real-time features
           are compatible with mobile WebSocket implementation

✓ Noted. Constraint added to backend-api workstream.
  Will validate WebSocket protocol matches mobile expectations.

commander> /schedule overnight
           - Finish mobile-app critical path
           - Don't start infra-deploy until mobile is done
           - Notify me if any blockers

✓ Overnight schedule set (6 hours estimated work)

  Planned work:
    ✓ Finish iOS core features (mobile-app)
    ✓ Fix GraphQL subscription bugs (backend-api)
    ⏸ Pause infra-deploy (dependency constraint)

  You'll receive a summary report at 8:00 AM.
```

**When to Use**: Managing large projects, coordinating teams, strategic planning

---

#### 4. Hands-Off Mode (Full Autonomy)

User defines goals, Commander executes completely autonomously.

```
commander> /project add ~/analytics-platform
commander> /framework mpm
commander> /autonomous on

Autonomous mode enabled. Commander will:
  • Execute work without asking questions
  • Make reasonable technical decisions
  • Only notify on critical errors or major milestones

Set constraints? [Y/n] y

Constraints:
  Max concurrent sessions: 5
  Daily budget (LLM calls): $10
  Stop on test failures: Yes
  Auto-commit to git: Yes (with AI-generated messages)

commander> Build a real-time analytics dashboard with:
           - Data ingestion pipeline (Kafka)
           - Time-series database (TimescaleDB)
           - Query API (GraphQL)
           - Dashboard UI (React + D3.js)
           - Deploy to AWS EKS

           Follow best practices for:
           - Testing (80%+ coverage)
           - Security (OWASP compliance)
           - Performance (sub-second queries)
           - Monitoring (Prometheus + Grafana)

✓ Work decomposed into 127 tasks across 8 workstreams
✓ Estimated completion: 2-3 weeks
✓ Autonomous execution starting...

[Commander works for 2 weeks with minimal user interaction]

Week 1 Summary:
  ✓ Data ingestion pipeline - COMPLETE (Kafka + schema registry)
  ✓ Database setup - COMPLETE (TimescaleDB with partitioning)
  ⏳ Query API - 80% COMPLETE (GraphQL schema, resolvers done)
  ⏳ Dashboard UI - 60% COMPLETE (base components, D3 charts)
  ⏸ AWS deployment - NOT STARTED (dependency: API completion)

Week 2 Summary:
  ✓ Query API - COMPLETE (optimized, cached, tested)
  ✓ Dashboard UI - COMPLETE (interactive, responsive)
  ✓ AWS deployment - COMPLETE (EKS cluster, CI/CD pipeline)
  ✓ Monitoring - COMPLETE (Prometheus metrics, Grafana dashboards)

  🎉 PROJECT COMPLETE

  Final stats:
    - 127/127 tasks completed
    - 342 commits across 8 repositories
    - Test coverage: 87%
    - All security scans passed
    - Performance benchmarks: ✓ (avg query: 340ms)

  Ready for production deployment.
```

**When to Use**: Well-defined projects, proven AI reliability, trusted autonomous work

---

### Daily Workflow Examples

#### Example 1: Solo Developer with Commander

**Morning** (9:00 AM):
```
$ uv run claude-mpm commander

Welcome back! Overnight summary:

  ✓ Completed: OAuth2 implementation (backend-api)
  ✓ Completed: Login UI component (frontend-app)
  ⏸ Blocked: Email service integration
     Needs: SendGrid API key

  🔔 1 notification: PR ready for review (#127)

commander> Add SendGrid key: sg_1234567890abcdef

✓ Email service unblocked. Work resuming...

commander> /schedule today
           - Finish email verification flow
           - Add password reset
           - Start admin dashboard (low priority)

✓ Today's schedule set (6-8 hours estimated)
```

**Lunch Check** (12:30 PM):
```
commander> /status

Progress:
  ✓ Email verification - COMPLETED (11:45 AM)
  ⏳ Password reset - 70% COMPLETE (current)
  ⏸ Admin dashboard - PENDING

commander> Looking good. Continue as planned.
```

**End of Day** (6:00 PM):
```
commander> /summary today

Today's Accomplishments:
  ✓ Email verification flow (SendGrid integration)
  ✓ Password reset (email + token validation)
  ✓ Admin dashboard initial setup (30% complete)

  📊 5 commits, 847 lines of code, 12 tests added

  Overnight work planned:
    - Finish admin dashboard user management
    - Add admin audit log

commander> /schedule overnight
           Continue admin dashboard. Notify if blocked.

✓ Overnight schedule active. See you tomorrow!
```

---

#### Example 2: Team Lead Managing Multiple Projects

**Morning Standup** (9:30 AM):
```
commander> /projects

Projects (4 active):
  1. client-portal (3 workstreams, 80% complete)
  2. internal-tools (2 workstreams, 45% complete)
  3. mobile-app (1 workstream, 30% complete)
  4. ml-pipeline (2 workstreams, 10% complete)

commander> /summary client-portal

client-portal Summary:
  ✓ User dashboard - COMPLETED
  ✓ Billing integration - COMPLETED
  ⏳ Support ticketing - 60% COMPLETE

  Estimated completion: Tomorrow

commander> /summary internal-tools

internal-tools Summary:
  ⏳ Admin panel - 70% COMPLETE
  ⏸ Analytics dashboard - BLOCKED
     Needs: Database schema finalization

commander> @team: Database schema for analytics ready?
           [waits for team response]

[Team confirms schema is final]

commander> /unblock internal-tools analytics-dashboard

✓ Workstream unblocked. Resuming work...

commander> /priority mobile-app CRITICAL
           We need mobile ready for investor demo next week.

✓ mobile-app priority increased to CRITICAL
  Reallocating 2 more instances to mobile-app

commander> /schedule this-week
           - Complete client-portal (highest priority)
           - Finish mobile-app core features (deadline: Friday)
           - Continue internal-tools (background priority)
           - Defer ml-pipeline (low priority)

✓ Week schedule set. Estimated completion rates:
  client-portal: 100% (tomorrow)
  mobile-app: 85% (Friday EOD)
  internal-tools: 65% (Friday EOD)
  ml-pipeline: 15% (deferred)
```

---

## Technical Architecture

### Design Patterns

#### 1. Adapter Pattern (Framework Support)

```python
# Abstract interface
class RuntimeAdapter(ABC):
    @abstractmethod
    def build_launch_command(
        self,
        project_path: str,
        **kwargs
    ) -> List[str]:
        """Generate command to launch this framework."""

    @abstractmethod
    def get_ready_signal(self) -> str:
        """String that indicates instance is ready for input."""

    @abstractmethod
    def get_prompt_pattern(self) -> str:
        """Regex pattern to detect framework's prompt."""

# Concrete implementations
class ClaudeCodeAdapter(RuntimeAdapter):
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        return ["claude", "--cwd", project_path]

    def get_ready_signal(self) -> str:
        return "Claude Code is ready"

    def get_prompt_pattern(self) -> str:
        return r"^>\s"

class AiderAdapter(RuntimeAdapter):
    def build_launch_command(self, project_path: str, **kwargs) -> List[str]:
        cmd = ["aider", "--yes", "--no-pretty"]
        if kwargs.get("auto_commits"):
            cmd.append("--auto-commits")
        cmd.append(project_path)
        return cmd

    def get_ready_signal(self) -> str:
        return "Aider>"

    def get_prompt_pattern(self) -> str:
        return r"^Aider>\s"
```

**Benefit**: Adding new frameworks is isolated—no changes to core Commander logic.

---

#### 2. Event Sourcing (State Management)

Every state change is an event. State can be reconstructed from event log.

```python
class EventStore:
    """Persistent event log."""

    def append(self, event: Event):
        """Append event to log."""

    def get_events(
        self,
        since: datetime,
        event_types: List[EventType] = None
    ) -> List[Event]:
        """Query event log."""

    def replay(self) -> CommanderState:
        """Reconstruct state from event log."""

# State reconstruction
def rebuild_state_from_events():
    store = EventStore.load()
    events = store.get_events(since=datetime.min)

    state = CommanderState()
    for event in events:
        state.apply(event)  # Apply event to state

    return state
```

**Benefit**: Crash recovery, audit trail, debugging, time-travel debugging.

---

#### 3. Publisher-Subscriber (Event Handling)

Components subscribe to events they care about. Loose coupling.

```python
class EventBus:
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def publish(self, event: Event):
        handlers = self.subscribers.get(event.type, [])
        await asyncio.gather(*[h(event) for h in handlers])

# Usage
bus = EventBus()

# Session monitor subscribes to session events
bus.subscribe(EventType.SESSION_STARTED, session_monitor.on_session_start)
bus.subscribe(EventType.SESSION_ENDED, session_monitor.on_session_end)

# State persister subscribes to all events
bus.subscribe(EventType.STATE_CHANGED, state_persister.save_state)

# User notifier subscribes to blocking events
bus.subscribe(EventType.DECISION_REQUIRED, notifier.notify_user)
bus.subscribe(EventType.APPROVAL_REQUESTED, notifier.notify_user)
```

**Benefit**: Components don't need to know about each other. Easy to add features.

---

#### 4. Command Pattern (Work Queue)

Work items are commands that can be queued, executed, undone, retried.

```python
class WorkCommand(ABC):
    @abstractmethod
    async def execute(self, context: ExecutionContext):
        """Execute this work command."""

    @abstractmethod
    async def undo(self):
        """Undo this work (if possible)."""

    @abstractmethod
    def can_retry(self) -> bool:
        """Whether this command can be retried on failure."""

class ImplementFeatureCommand(WorkCommand):
    def __init__(self, description: str, project_id: str):
        self.description = description
        self.project_id = project_id

    async def execute(self, context: ExecutionContext):
        session = context.get_session(self.project_id)
        await session.send_message(self.description)
        # Wait for completion or blocking event

    async def undo(self):
        # Revert git commits, restore previous state
        pass

    def can_retry(self) -> bool:
        return True  # Can retry feature implementation
```

**Benefit**: Work can be queued, scheduled, retried, and undone.

---

### State Machine: Project Lifecycle

```
┌─────────────┐
│ UNREGISTERED│
└──────┬──────┘
       │ /project add
       ↓
┌─────────────┐
│ REGISTERED  │ ← Project added, no sessions yet
└──────┬──────┘
       │ /framework <name>
       ↓
┌─────────────┐
│ PROVISIONING│ ← Spawning tmux session
└──────┬──────┘
       │ Runtime ready
       ↓
┌─────────────┐
│    IDLE     │ ← Ready for work, no active tasks
└──────┬──────┘
       │ Work queued
       ↓
┌─────────────┐
│   WORKING   │ ← Executing work
└──────┬──────┘
       │ Decision/approval needed
       ↓
┌─────────────┐
│   BLOCKED   │ ← Waiting for user input
└──────┬──────┘
       │ Event resolved
       ↓
┌─────────────┐
│   WORKING   │ ← Resume execution
└──────┬──────┘
       │ Work completed
       ↓
┌─────────────┐
│    IDLE     │
└──────┬──────┘
       │ /project pause
       ↓
┌─────────────┐
│   PAUSED    │ ← Suspended, state preserved
└──────┬──────┘
       │ /project resume
       ↓
┌─────────────┐
│    IDLE     │
└──────┬──────┘
       │ /project remove
       ↓
┌─────────────┐
│ TERMINATING │ ← Graceful shutdown
└──────┬──────┘
       │ Cleanup complete
       ↓
┌─────────────┐
│ UNREGISTERED│
└─────────────┘
```

**State Transitions**:
- **UNREGISTERED → REGISTERED**: Project added
- **REGISTERED → PROVISIONING**: Framework selected, spawning instance
- **PROVISIONING → IDLE**: Instance ready
- **IDLE → WORKING**: Work dequeued and started
- **WORKING → BLOCKED**: Blocking event detected
- **BLOCKED → WORKING**: Event resolved
- **WORKING → IDLE**: Work completed
- **IDLE → PAUSED**: User pauses project
- **PAUSED → IDLE**: User resumes project
- **\* → TERMINATING**: User removes project

---

### Concurrency & Resource Management

Commander manages limited resources (tmux panes, LLM API calls, memory):

```python
class ResourceManager:
    """Manage limited resources."""

    def __init__(self, config: CommanderConfig):
        self.max_concurrent_sessions = config.max_concurrent_sessions
        self.max_api_calls_per_minute = config.max_api_calls_per_minute
        self.active_sessions = 0
        self.api_calls_this_minute = 0

    async def acquire_session_slot(self) -> bool:
        """Try to acquire a session slot."""
        if self.active_sessions >= self.max_concurrent_sessions:
            return False
        self.active_sessions += 1
        return True

    def release_session_slot(self):
        """Release a session slot."""
        self.active_sessions -= 1

    async def rate_limit_api_call(self):
        """Rate limit API calls to LLM providers."""
        if self.api_calls_this_minute >= self.max_api_calls_per_minute:
            # Wait until next minute
            await asyncio.sleep(60)
            self.api_calls_this_minute = 0
        self.api_calls_this_minute += 1
```

**Resource Limits** (configurable):
- **Max concurrent sessions**: Default 5 (prevents tmux pane exhaustion)
- **Max API calls/minute**: Default 60 (prevents OpenRouter rate limits)
- **Max memory per session**: Default 500MB (prevents OOM)
- **Max work queue size**: Default 100 items (prevents unbounded growth)

---

### Error Handling & Resilience

Commander must handle failures gracefully:

```python
class ErrorHandler:
    """Centralized error handling."""

    async def handle_runtime_error(self, error: RuntimeError):
        """Handle errors from AI instances."""
        if error.is_recoverable():
            # Retry with exponential backoff
            await self.retry_with_backoff(error.operation)
        else:
            # Notify user, mark work as failed
            await self.notify_user_of_failure(error)
            await self.mark_work_failed(error.work_id)

    async def handle_llm_api_error(self, error: LLMAPIError):
        """Handle LLM provider errors."""
        if error.is_rate_limit():
            # Back off and retry
            await asyncio.sleep(error.retry_after or 60)
            await self.retry_operation(error.operation)
        elif error.is_auth_error():
            # API key invalid, notify user
            await self.notify_user_api_key_invalid()
        else:
            # Other API error, log and notify
            await self.log_error(error)
            await self.notify_user_of_error(error)

    async def handle_tmux_error(self, error: TmuxError):
        """Handle tmux orchestration errors."""
        if error.is_pane_not_found():
            # Pane died, restart instance
            await self.restart_instance(error.session_id)
        elif error.is_session_not_found():
            # Session died, recreate
            await self.recreate_session(error.session_id)
```

**Failure Modes**:
1. **Runtime crash**: AI instance crashes → Restart instance, resume work
2. **LLM API failure**: API call fails → Retry with backoff, fallback to smaller model
3. **tmux failure**: Session/pane lost → Recreate session, restore state
4. **Commander crash**: Main process dies → State persisted to disk, restore on restart
5. **User interruption**: Ctrl+C during work → Graceful shutdown, save state

---

### Security & Sandboxing

Commander executes user-provided code and commands. Security is critical:

```python
class SecurityManager:
    """Enforce security constraints."""

    def __init__(self, config: CommanderConfig):
        self.allowed_commands = config.allowed_commands
        self.forbidden_paths = config.forbidden_paths
        self.require_approval_for_destructive = config.require_approval_for_destructive

    def validate_command(self, command: str) -> bool:
        """Check if command is allowed."""
        # Check against allowlist
        if not any(command.startswith(allowed) for allowed in self.allowed_commands):
            return False

        # Check for path traversal
        if any(forbidden in command for forbidden in self.forbidden_paths):
            return False

        # Check for destructive operations
        if self.is_destructive(command) and self.require_approval_for_destructive:
            return False  # Requires user approval

        return True

    def is_destructive(self, command: str) -> bool:
        """Check if command is potentially destructive."""
        destructive_patterns = [
            r"rm\s+-rf",
            r"git\s+push\s+--force",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM.*WHERE\s+1=1",
        ]
        return any(re.search(pattern, command) for pattern in destructive_patterns)
```

**Security Constraints**:
- **Command allowlist**: Only approved commands can be executed
- **Path restrictions**: Prevent access to sensitive directories
- **Destructive operation approval**: Force user approval for risky commands
- **Git hook integration**: Review commits before push
- **Secrets redaction**: Never log API keys, passwords

---

## Differentiation & Market Position

### Competitive Landscape

| Tool | Scope | Duration | Interaction | Autonomy | Multi-Project |
|------|-------|----------|-------------|----------|---------------|
| **GitHub Copilot** | Single file | Minutes | Inline | Low | No |
| **Cursor** | Project | Hours | Chat in IDE | Medium | No |
| **Aider** | Project | Hours | CLI chat | Medium | No |
| **Claude Code** | Project | Hours | CLI chat | Medium | No |
| **v0.dev** | Component | Minutes | Web UI | Low | No |
| **Devin** | Project | Days | Web UI | High | Limited |
| **MPM Commander** | Multi-project | Days/Weeks | CLI/API/Web | High | **Yes** |

### Unique Value Propositions

1. **Framework Agnostic**
   - Works with any AI backend (Claude, GPT, local models)
   - Competitors lock you into one tool
   - Commander: Orchestration layer above tools

2. **Multi-Project Orchestration**
   - Manage 5-10 projects simultaneously
   - Competitors: 1 project at a time
   - Commander: Swarm coordination

3. **Event-Driven Architecture**
   - React to changes across workstreams
   - Competitors: Linear request/response
   - Commander: Parallel, reactive

4. **LLM-Summarized Oversight**
   - Summaries instead of raw output
   - Competitors: Full output (noise)
   - Commander: Signal extraction

5. **Long-Running Sessions**
   - Days/weeks, persistent state
   - Competitors: Hours max, ephemeral
   - Commander: Multi-day workflows

6. **Drop-In Capability**
   - Take control of any workstream anytime
   - Competitors: All-or-nothing automation
   - Commander: Flexible intervention

---

### Use Cases Where Commander Excels

#### Use Case 1: Overnight Development

**Scenario**: Solo developer wants work to continue while sleeping.

**Without Commander**:
- Start work manually before bed
- Hope it doesn't hit a decision point
- If blocked, zero progress overnight

**With Commander**:
```
6:00 PM: Queue work for overnight
11:00 PM: AI hits decision point, notifies user (email/Slack)
11:15 PM: User resolves decision from phone
6:00 AM: Work completed, user wakes to PR ready for review
```

**Value**: 10x productivity (16-hour workday instead of 8)

---

#### Use Case 2: Multi-Repo Refactoring

**Scenario**: Refactoring across frontend, backend, mobile apps (3 repos).

**Without Commander**:
- Switch between projects manually
- Keep context in head
- Serialize work (frontend → backend → mobile)

**With Commander**:
```
commander> /project add ~/frontend
commander> /project add ~/backend
commander> /project add ~/mobile

commander> Refactor authentication to use new token format across all projects

✓ 3 workstreams started in parallel
  - frontend: Update API client
  - backend: Modify token generation
  - mobile: Update auth interceptor

✓ Coordination: Changes applied consistently across repos
✓ Validation: Tests run in all 3 projects
✓ Result: 3 PRs ready for review, zero conflicts
```

**Value**: 3x speed (parallel execution), consistency (no manual coordination)

---

#### Use Case 3: Proof-of-Concept Sprint

**Scenario**: Build a POC in 48 hours for investor demo.

**Without Commander**:
- Developer works 48 hours straight (unrealistic)
- OR incomplete POC

**With Commander**:
```
Day 1 (6 hours developer time):
  - Define POC requirements
  - Set up project structure
  - Queue autonomous work for overnight

Overnight (10 hours autonomous):
  - Commander implements core features
  - Runs tests, fixes bugs
  - Checkpoints progress

Day 2 (6 hours developer time):
  - Review overnight work
  - Course-correct as needed
  - Polish UI/UX
  - Queue final integration work

Overnight 2 (10 hours autonomous):
  - Integration testing
  - Deployment to staging
  - Documentation

Day 3 (2 hours developer time):
  - Final review
  - Deploy to production
  - Demo ready
```

**Value**: 36 hours of effective work in 48 hours (14 human + 22 autonomous)

---

## Implementation Roadmap

### Roadmap Overview

```
Phase 1: Foundation (COMPLETE ✅)
  ├─ TmuxOrchestrator
  ├─ RuntimeAdapter interface
  ├─ ProjectRegistry
  ├─ EventDetection
  └─ REST API v1

Phase 2: Event System (COMPLETE ✅)
  ├─ CommanderDaemon
  ├─ ProjectSession
  ├─ RuntimeExecutor & Monitor
  ├─ WorkQueue
  ├─ EventResolution workflow
  └─ State persistence

Phase 3: Chat Interface (PARTIAL 🟡)
  ├─ Chat CLI (basic implementation ✅)
  ├─ OpenRouter integration (exists ✅)
  ├─ Session context (needs enhancement 🔴)
  ├─ Command parser (basic ✅)
  └─ Interactive relay (needs work 🔴)

Phase 4: Multi-Runtime (PARTIAL 🟡)
  ├─ Claude Code adapter ✅
  ├─ MPM adapter ✅
  ├─ Aider adapter 🔴
  ├─ Custom adapter SDK 🔴
  └─ Framework discovery 🔴

Phase 5: Persistence & Reliability (PARTIAL 🟡)
  ├─ State persistence ✅
  ├─ Crash recovery ✅
  ├─ Event store ✅
  ├─ Health monitoring 🔴
  ├─ Resource limits 🔴
  └─ Performance optimization 🔴

Phase 6: Enhanced Interface (MINIMAL 🔴)
  ├─ Web dashboard (minimal exists 🟡)
  ├─ WebSocket real-time updates 🔴
  ├─ Notification integrations (Slack, email) 🔴
  ├─ Mobile app 🔴
  └─ Advanced visualizations 🔴
```

---

### Current Priority: Completing Phase 3 & 4

Based on gap analysis (see `docs/research/mpm-commander-gap-analysis-2026-01-15.md`), focus areas:

#### High Priority Issues

1. **Session Context Enhancement** (#205 equivalent)
   - Track active instance per user
   - Maintain conversation history
   - Improve context switching
   - **Estimated**: 2-3 days

2. **Interactive Command Relay** (#200 equivalent)
   - Direct messaging (bypass WorkQueue for chat)
   - Synchronous command/response
   - Output capture and summarization
   - **Estimated**: 2-3 days

3. **Response Routing** (#177)
   - Route instance responses back to correct user session
   - Handle multiple concurrent users
   - **Estimated**: 2 days

4. **Event Queue Completion** (#176)
   - Finish event queue implementation
   - Event deduplication
   - Priority handling
   - **Estimated**: 3 days

#### Medium Priority Issues

5. **Aider Adapter** (#159)
   - Implement AiderAdapter
   - Git integration support
   - Auto-commit configuration
   - **Estimated**: 3-4 days

6. **Framework Selection System** (#199 equivalent)
   - Framework registry
   - Framework discovery
   - Launch command generation
   - **Estimated**: 2-3 days

7. **Auto Session Management** (#152)
   - Automatically create sessions when work queued
   - Session pooling and reuse
   - **Estimated**: 2 days

#### Low Priority (Defer to Phase 5/6)

8. **Health Monitoring**
   - Instance health checks
   - Resource usage tracking
   - Auto-restart on failure
   - **Estimated**: 3 days

9. **WebSocket Real-Time Updates** (#179)
   - WebSocket server for dashboard
   - Real-time event streaming
   - **Estimated**: 5 days (deferred)

---

### Milestone Targets

#### Q1 2026 (Complete Phase 3 & 4)

**Target Date**: End of January 2026

**Deliverables**:
- ✅ Fully functional chat interface with session context
- ✅ Interactive command relay (real-time messaging)
- ✅ Event queue and response routing complete
- ✅ Aider adapter functional
- ✅ Framework selection system
- ✅ User documentation (guides and examples)

**Success Criteria**:
- User can manage 3-5 projects in chat interface
- Seamless switching between instances
- LLM-summarized responses for all output
- Aider integration for git-native workflows

---

#### Q2 2026 (Phase 5: Reliability & Scale)

**Target Date**: End of April 2026

**Deliverables**:
- ✅ Health monitoring and auto-recovery
- ✅ Resource limits and optimization
- ✅ Performance benchmarks (50+ concurrent sessions)
- ✅ SQLite backend (replace JSON persistence)
- ✅ Advanced error handling

**Success Criteria**:
- 99.9% uptime for daemon
- Handles 50 concurrent sessions
- Auto-recovery from crashes
- Resource usage optimized

---

#### Q3 2026 (Phase 6: Enhanced Interface)

**Target Date**: End of July 2026

**Deliverables**:
- ✅ Web dashboard (modern React UI)
- ✅ WebSocket real-time updates
- ✅ Slack/Discord notification integrations
- ✅ Mobile app (read-only monitoring)
- ✅ Advanced visualizations (progress charts, timelines)

**Success Criteria**:
- Web dashboard feature parity with CLI
- Real-time updates (<1s latency)
- Multi-user support
- Mobile monitoring app in app stores

---

## Success Metrics

### Technical Metrics

| Metric | Current | Q1 Target | Q2 Target | Q3 Target |
|--------|---------|-----------|-----------|-----------|
| **Uptime** | ~95% | 99% | 99.5% | 99.9% |
| **Max Concurrent Sessions** | 5 | 10 | 50 | 100 |
| **Event Response Time** | <2s | <1s | <500ms | <200ms |
| **Crash Recovery** | 100% | 100% | 100% | 100% |
| **Test Coverage** | 85% | 90% | 92% | 95% |
| **API Response Time** | <100ms | <50ms | <30ms | <20ms |

### User Experience Metrics

| Metric | Current | Q1 Target | Q2 Target | Q3 Target |
|--------|---------|-----------|-----------|-----------|
| **Time to First Value** | 10min | 5min | 2min | 1min |
| **User Retention (30-day)** | N/A | 40% | 60% | 75% |
| **Daily Active Users** | N/A | 50 | 200 | 500 |
| **Autonomous Completion Rate** | ~40% | 60% | 75% | 85% |
| **User Satisfaction (NPS)** | N/A | 40 | 60 | 70 |

### Business Metrics

| Metric | Current | Q1 Target | Q2 Target | Q3 Target |
|--------|---------|-----------|-----------|-----------|
| **Projects Managed/Day** | ~10 | 100 | 500 | 1000 |
| **Work Items Completed/Day** | ~20 | 200 | 1000 | 2000 |
| **LLM API Cost/User/Month** | $5 | $8 | $6 | $5 |
| **GitHub Stars** | N/A | 100 | 500 | 1000 |
| **Contributors** | 1 | 3 | 10 | 20 |

---

## Future Possibilities

### Natural Language Work Decomposition

**Vision**: User describes high-level goal, Commander decomposes into tasks automatically.

```
commander> Build an e-commerce site with Stripe payments

✓ Work decomposed using LLM:

Workstreams:
  1. Database schema (users, products, orders, payments)
  2. Backend API (REST + GraphQL)
  3. Frontend UI (product catalog, cart, checkout)
  4. Payment integration (Stripe SDK)
  5. Admin dashboard (order management)
  6. Deployment (Docker + AWS)

Tasks: 87 total across 6 workstreams
Estimated completion: 3-4 weeks

Approve work plan? [Y/n]
```

**Technology**:
- LLM-powered task decomposition
- Dependency graph generation
- Effort estimation using historical data

---

### Multi-User Collaboration

**Vision**: Multiple developers collaborate via shared Commander instance.

```
# Developer A
commander> /project add ~/shared-project
commander> Working on authentication module

# Developer B (same Commander instance)
commander> /attach shared-project
[shared-project]> I'll handle the payment integration
[shared-project]> /claim payment-integration

✓ Claimed task: payment-integration (assigned to Developer B)
```

**Features**:
- Multi-user sessions (WebSocket-based)
- Task claiming and assignment
- Real-time collaboration
- Conflict resolution (who's editing what)

---

### AI Code Review

**Vision**: Commander reviews code before committing.

```
commander> /review-mode strict

[Work completes]

Commander: Review required before commit.

Issues found:
  ⚠️ Missing error handling in payment.py:45
  ⚠️ SQL injection vulnerability in query.py:120
  ℹ️ Consider extracting duplicate logic in auth.py

Approve commit anyway? [y/N]
```

**Technology**:
- Static analysis integration (pylint, eslint, etc.)
- LLM-powered semantic review
- Security scanning (secrets, vulnerabilities)

---

### Workflow Templates

**Vision**: Reusable workflow templates for common tasks.

```
commander> /template use microservice-setup

Template: Microservice Setup
  ✓ Create FastAPI project structure
  ✓ Add Docker + docker-compose
  ✓ Set up PostgreSQL database
  ✓ Configure testing (pytest)
  ✓ Add CI/CD (GitHub Actions)
  ✓ Generate OpenAPI docs

Customize? [Y/n] y

Service name: user-service
Database: PostgreSQL
Auth: JWT

✓ Template applied. Starting work...
```

**Templates**:
- Microservice setup
- Full-stack app (frontend + backend)
- Mobile app (iOS + Android)
- Data pipeline (ETL)
- ML model training

---

### Learning & Improvement

**Vision**: Commander learns from user feedback and improves over time.

```
[Work completes]

commander> How did I do on this task?

User: Great work, but next time use Pydantic for validation instead of manual checks.

✓ Noted. I'll prefer Pydantic for validation in future tasks.

[Later, similar task]

commander> Using Pydantic for request validation (based on your previous feedback).
```

**Technology**:
- User feedback collection
- Preference learning
- Knowledge graph (KuzuMemory integration)
- Continuous improvement

---

### IDE Integration

**Vision**: Commander accessible from IDEs (VS Code, IntelliJ).

```
# VS Code Extension

[Commander Sidebar]
  Active Projects:
    ✓ my-app (working)
    ⏸ client-project (paused)

  Recent Events:
    🔔 Decision needed: Choose state management library
    ✓ Completed: User authentication

[Inline Command]
User types: `// commander: add logging to this function`
Commander: ✓ Added structured logging with contextual metadata
```

**Features**:
- Sidebar widget with project status
- Inline comments trigger Commander actions
- Real-time notifications in IDE
- Seamless integration with existing workflows

---

### Voice Control

**Vision**: Control Commander via voice commands (accessibility + convenience).

```
User: "Commander, start work on the user dashboard"
Commander: "Starting work on user dashboard for project my-app. Estimated completion in 2 hours."

User: "What's the status?"
Commander: "User dashboard is 60% complete. Currently implementing data table component."

User: "Pause work and switch to API project"
Commander: "Work paused. Switching to API project."
```

**Technology**:
- Speech-to-text (Whisper, Google Speech API)
- Natural language understanding
- Text-to-speech for responses
- Wake word detection ("Hey Commander")

---

### Self-Hosting & Enterprise Features

**Vision**: Enterprise-ready deployment with SSO, audit logs, compliance.

**Enterprise Features**:
- **SSO Integration**: SAML, OAuth2, LDAP
- **Audit Logs**: Complete event trail for compliance
- **Role-Based Access Control**: Admin, developer, viewer roles
- **Resource Quotas**: Per-team limits on sessions, API calls
- **Air-Gapped Deployment**: On-premise, no internet required
- **Custom LLM Backends**: Use private LLM deployments
- **SLA Guarantees**: 99.99% uptime, support contracts

---

## Conclusion

MPM Commander represents a fundamental shift in AI-assisted development:

### From Tools to Orchestration

- **CLI tools** abstract code writing
- **Commander** abstracts AI coordination

### From Hours to Days

- **Single sessions** last hours
- **Commander workstreams** last days/weeks

### From Output to Summaries

- **Traditional tools** show raw output
- **Commander** shows intelligently summarized insights

### From One to Many

- **Existing tools** manage one project
- **Commander** orchestrates multiple workstreams

---

### The North Star

> **Developers should focus on what to build and why, not how to coordinate multiple AI tools to build it.**

Commander is the orchestration layer that makes this possible.

---

### Contributing to the Vision

This document is a living vision. As Commander evolves, so will this document.

**How to Contribute**:
1. Propose new features via GitHub issues
2. Implement adapters for new frameworks
3. Improve documentation and examples
4. Share use cases and success stories
5. Submit PRs for bug fixes and enhancements

**Contact**:
- GitHub: https://github.com/your-org/claude-mpm
- Discussions: https://github.com/your-org/claude-mpm/discussions
- Discord: [Community Server Link]

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
**Next Review**: End of Q1 2026 (after Phase 3/4 completion)
**Maintainer**: MPM Core Team

---

## Related Documentation

- **Gap Analysis**: [mpm-commander-gap-analysis-2026-01-15.md](./mpm-commander-gap-analysis-2026-01-15.md)
- **Roadmap Visual**: [commander-roadmap-visual.md](./commander-roadmap-visual.md)
- **Architecture**: [../developer/ARCHITECTURE.md](../developer/ARCHITECTURE.md)
- **Contributing**: [../../CONTRIBUTING.md](../../CONTRIBUTING.md)
- **API Reference**: [../reference/commander-api.md](../reference/commander-api.md)

---

*This document embodies the vision, principles, and technical architecture of MPM Commander. It serves as the north star for all development efforts and the canonical reference for understanding Commander's purpose and direction.*
