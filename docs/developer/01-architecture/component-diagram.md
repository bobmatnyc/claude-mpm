# Component Diagram

This document provides visual representations and detailed descriptions of Claude MPM's component architecture.

## High-Level Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Claude MPM System                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────────────┐   │
│  │   CLI Layer │  │ Orchestration    │  │   Services Layer       │   │
│  │             │  │     Layer         │  │                        │   │
│  │ ┌─────────┐ │  │ ┌──────────────┐ │  │ ┌────────────────────┐ │   │
│  │ │   CLI   │ │  │ │ Subprocess   │ │  │ │   Hook Service     │ │   │
│  │ │  Main   │ │  │ │ Orchestrator │ │  │ └────────────────────┘ │   │
│  │ └─────────┘ │  │ └──────────────┘ │  │ ┌────────────────────┐ │   │
│  │ ┌─────────┐ │  │ ┌──────────────┐ │  │ │  Agent Service     │ │   │
│  │ │ Command │ │  │ │ System       │ │  │ └────────────────────┘ │   │
│  │ │ Parser  │ │  │ │ Prompt Orch  │ │  │ ┌────────────────────┐ │   │
│  │ └─────────┘ │  │ └──────────────┘ │  │ │ Ticket Extractor   │ │   │
│  └─────────────┘  │ ┌──────────────┐ │  │ └────────────────────┘ │   │
│                   │ │ Interactive   │ │  │ ┌────────────────────┐ │   │
│                   │ │ Subprocess    │ │  │ │ Session Logger     │ │   │
│                   │ └──────────────┘ │  │ └────────────────────┘ │   │
│                   └──────────────────┘  └────────────────────────┘   │
│                                                                         │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────────────┐   │
│  │ Agent Layer │  │   Core Layer     │  │   Utils Layer          │   │
│  │             │  │                  │  │                        │   │
│  │ ┌─────────┐ │  │ ┌──────────────┐ │  │ ┌────────────────────┐ │   │
│  │ │Engineer │ │  │ │Claude        │ │  │ │ Subprocess Utils   │ │   │
│  │ │ Agent   │ │  │ │Launcher      │ │  │ └────────────────────┘ │   │
│  │ └─────────┘ │  │ └──────────────┘ │  │ ┌────────────────────┐ │   │
│  │ ┌─────────┐ │  │ ┌──────────────┐ │  │ │   File Utils       │ │   │
│  │ │   QA    │ │  │ │Agent         │ │  │ └────────────────────┘ │   │
│  │ │ Agent   │ │  │ │Registry      │ │  │ ┌────────────────────┐ │   │
│  │ └─────────┘ │  │ └──────────────┘ │  │ │  Logger Mixin      │ │   │
│  │     ...     │  │ ┌──────────────┐ │  │ └────────────────────┘ │   │
│  └─────────────┘  │ │Framework     │ │  └────────────────────────┘   │
│                   │ │Loader        │ │                                │
│                   │ └──────────────┘ │                                │
│                   └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Descriptions

### CLI Layer

#### CLI Module (`cli/`)
- **Purpose**: Modular CLI implementation
- **Structure**:
  - `__init__.py`: Main entry point and orchestration
  - `parser.py`: Centralized argument parsing
  - `utils.py`: Shared utility functions
  - `commands/`: Individual command implementations
- **Responsibilities**:
  - Parse command-line arguments
  - Initialize configuration
  - Create and launch orchestrator
  - Handle top-level exceptions

#### Command Parser (`cli/parser.py`)
- **Purpose**: Command-line interface definition
- **Responsibilities**:
  - Define available commands
  - Parse user input
  - Validate arguments
  - Route to appropriate handlers

### Orchestration Layer

#### Base Orchestrator
```python
class BaseOrchestrator(ABC):
    @abstractmethod
    def start(self) -> None: ...
    
    @abstractmethod
    def send_message(self, message: str) -> None: ...
    
    @abstractmethod
    def receive_output(self) -> str: ...
    
    @abstractmethod
    def stop(self) -> None: ...
```

#### Subprocess Orchestrator
- **Purpose**: Direct subprocess control with pattern detection
- **Key Features**:
  - Real-time I/O interception
  - Pattern detection for delegations
  - Parallel agent execution
  - Resource monitoring

#### System Prompt Orchestrator
- **Purpose**: Uses Claude's --system-prompt flag
- **Key Features**:
  - Minimal overhead
  - Framework as system prompt
  - Direct Claude interaction
  - No delegation interception

#### Interactive Subprocess Orchestrator
- **Purpose**: Enhanced interactive mode with pexpect
- **Key Features**:
  - Terminal emulation
  - Better interactive support
  - Memory monitoring
  - Process lifecycle management

### Services Layer

#### Hook Service
```
┌─────────────────────────────────────┐
│          Hook Service               │
├─────────────────────────────────────┤
│ - Pre-message hooks                 │
│ - Post-message hooks                │
│ - Session hooks                     │
│ - Error hooks                       │
├─────────────────────────────────────┤
│ + register_hook()                   │
│ + execute_pre_hooks()               │
│ + execute_post_hooks()              │
│ + start_service()                   │
└─────────────────────────────────────┘
```

#### Agent Service
```
┌─────────────────────────────────────┐
│          Agent Service              │
├─────────────────────────────────────┤
│ - Agent lifecycle management        │
│ - Agent discovery                   │
│ - Profile loading                   │
│ - Result aggregation                │
├─────────────────────────────────────┤
│ + create_agent()                    │
│ + execute_agent()                   │
│ + get_agent_profile()               │
│ + aggregate_results()               │
└─────────────────────────────────────┘
```

#### Ticket Extractor
```
┌─────────────────────────────────────┐
│        Ticket Extractor             │
├─────────────────────────────────────┤
│ - Pattern matching                  │
│ - Ticket creation                   │
│ - AI-Trackdown integration          │
│ - Duplicate detection               │
├─────────────────────────────────────┤
│ + extract_tickets()                 │
│ + create_ticket()                   │
│ + check_duplicates()                │
│ + sync_with_trackdown()             │
└─────────────────────────────────────┘
```

### Agent Layer

#### Agent Hierarchy
```
┌─────────────────────────────────────┐
│         Base Agent                  │
├─────────────────────────────────────┤
│ Common agent behaviors              │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┬─────────────┬─────────────┐
     │                   │             │             │
┌────▼──────┐   ┌───────▼──────┐  ┌───▼──────┐  ┌───▼──────┐
│ Engineer  │   │     QA       │  │  Docs    │  │ Research │
│  Agent    │   │   Agent      │  │  Agent   │  │  Agent   │
└───────────┘   └──────────────┘  └──────────┘  └──────────┘
```

#### Agent Communication
```
Orchestrator                    Agent Process
    │                               │
    ├──── Create Subprocess ────────▶
    │                               │
    ├──── Send Task + Context ──────▶
    │                               │
    │                          ┌────┴────┐
    │                          │ Execute │
    │                          │  Task   │
    │                          └────┬────┘
    │                               │
    ◀──────── Return Results ────────┤
    │                               │
    ├──── Terminate Process ────────▶
    │                               │
```

### Core Layer

#### Claude Launcher
```
┌─────────────────────────────────────┐
│         Claude Launcher             │
├─────────────────────────────────────┤
│ - Unified subprocess creation       │
│ - Environment setup                 │
│ - Command building                  │
│ - Process management                │
├─────────────────────────────────────┤
│ + launch()                          │
│ + build_command()                   │
│ + setup_environment()               │
│ + cleanup()                         │
└─────────────────────────────────────┘
```

#### Agent Registry
```
┌─────────────────────────────────────┐
│         Agent Registry              │
├─────────────────────────────────────┤
│ - Agent discovery                   │
│ - Registration                      │
│ - Template loading                  │
│ - Capability mapping                │
├─────────────────────────────────────┤
│ + discover_agents()                 │
│ + register_agent()                  │
│ + get_agent()                       │
│ + list_agents()                     │
└─────────────────────────────────────┘
```

#### Framework Loader
```
┌─────────────────────────────────────┐
│        Framework Loader             │
├─────────────────────────────────────┤
│ - Load INSTRUCTIONS.md              │
│ - Load agent templates              │
│ - Merge configurations              │
│ - Cache management                  │
├─────────────────────────────────────┤
│ + load_framework()                  │
│ + get_agent_instructions()          │
│ + reload_if_changed()               │
│ + clear_cache()                     │
└─────────────────────────────────────┘
```

### Utils Layer

#### Subprocess Utils
```
┌─────────────────────────────────────┐
│        Subprocess Utils             │
├─────────────────────────────────────┤
│ - Safe subprocess execution         │
│ - Async subprocess support          │
│ - Process tree management           │
│ - Resource monitoring               │
├─────────────────────────────────────┤
│ + run_subprocess()                  │
│ + run_subprocess_async()            │
│ + terminate_process_tree()          │
│ + monitor_process_resources()       │
└─────────────────────────────────────┘
```

## Component Interactions

### Message Flow Through Components

```
User Input
    │
    ▼
┌─────────┐
│   CLI   │
└────┬────┘
     │
     ▼
┌─────────────┐     ┌──────────────┐
│ Orchestrator├─────▶ Hook Service │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌──────────────┐
│Claude Process│
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│Pattern Detect├─────▶Ticket       │
└──────┬───────┘     │Extractor    │
       │             └─────────────┘
       ▼
┌──────────────┐     ┌─────────────┐
│Agent Delegate├─────▶Agent Service│
└──────┬───────┘     └─────────────┘
       │
       ▼
   User Output
```

### Service Dependencies

```
┌────────────────┐
│ CLI Main       │
└───────┬────────┘
        │ creates
        ▼
┌────────────────┐     ┌─────────────────┐
│ Orchestrator   │────▶│ Claude Launcher │
└───────┬────────┘     └─────────────────┘
        │ uses
        ├──────────────────┐
        ▼                  ▼
┌────────────────┐  ┌──────────────────┐
│ Hook Service   │  │ Agent Service    │
└────────────────┘  └─────────┬────────┘
                              │ uses
                              ▼
                    ┌──────────────────┐
                    │ Agent Registry   │
                    └──────────────────┘
```

### Data Flow Between Components

```
┌─────────────────────────────────────────────────────┐
│                  User Message                       │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Pre-Message Hooks                      │
│  - Input validation                                 │
│  - Message enhancement                              │
│  - Logging                                          │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│            Framework Injection                      │
│  - Load INSTRUCTIONS.md                             │
│  - Inject agent context                             │
│  - Add system prompts                               │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Claude Processing                      │
│  - Message interpretation                           │
│  - Task generation                                  │
│  - Response creation                                │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│            Pattern Detection                        │
│  - Ticket patterns (TODO, BUG, FEATURE)             │
│  - Delegation patterns (**Agent**: task)            │
│  - Error patterns                                   │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Action Execution                       │
│  - Create tickets                                   │
│  - Spawn agent subprocesses                         │
│  - Execute hooks                                    │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│            Post-Message Hooks                       │
│  - Response transformation                          │
│  - Logging                                          │
│  - Cleanup                                          │
└──────────────────────────┬──────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                 User Response                       │
└─────────────────────────────────────────────────────┘
```

## Component Lifecycle

### Startup Sequence

```
1. CLI Main
   │
   ├─▶ 2. Parse Arguments
   │
   ├─▶ 3. Load Configuration
   │
   ├─▶ 4. Initialize Services
   │   ├─▶ Hook Service
   │   ├─▶ Agent Registry
   │   └─▶ Framework Loader
   │
   ├─▶ 5. Create Orchestrator
   │   └─▶ Select based on mode
   │
   ├─▶ 6. Start Claude Process
   │   ├─▶ Build command
   │   ├─▶ Setup environment
   │   └─▶ Launch subprocess
   │
   └─▶ 7. Enter Main Loop
```

### Shutdown Sequence

```
1. Receive Exit Signal
   │
   ├─▶ 2. Stop Main Loop
   │
   ├─▶ 3. Terminate Agent Processes
   │   └─▶ Kill process trees
   │
   ├─▶ 4. Stop Claude Process
   │   ├─▶ Send termination signal
   │   └─▶ Wait for cleanup
   │
   ├─▶ 5. Stop Services
   │   ├─▶ Hook Service
   │   └─▶ Session Logger
   │
   └─▶ 6. Cleanup Resources
       ├─▶ Close files
       ├─▶ Remove temp files
       └─▶ Log shutdown
```

## Component Configuration

### Configuration Flow

```
┌─────────────────┐
│ Environment Vars│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Config Files    │────▶│ Config Manager  │
└─────────────────┘     └────────┬────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
         ┌────────────────┐           ┌────────────────┐
         │  Orchestrator  │           │    Services    │
         │  Configuration │           │ Configuration  │
         └────────────────┘           └────────────────┘
```

### Component Registration

```python
# Component registry pattern
class ComponentRegistry:
    def __init__(self):
        self.components = {}
        
    def register(self, name: str, component: Any):
        self.components[name] = component
        
    def get(self, name: str) -> Any:
        return self.components.get(name)
        
    def initialize_all(self):
        for component in self.components.values():
            if hasattr(component, 'initialize'):
                component.initialize()
```

## Testing Component Interactions

### Component Mock Strategy

```python
# Mock individual components for testing
class MockOrchestrator(BaseOrchestrator):
    def __init__(self):
        self.messages = []
        self.responses = ["Mock response"]
        
    def send_message(self, message: str):
        self.messages.append(message)
        
    def receive_output(self) -> str:
        return self.responses.pop(0) if self.responses else ""
```

### Integration Test Pattern

```python
def test_component_integration():
    # Create real components
    registry = AgentRegistry()
    launcher = ClaudeLauncher()
    orchestrator = SubprocessOrchestrator(launcher, registry)
    
    # Test interaction
    orchestrator.start()
    orchestrator.send_message("Test")
    response = orchestrator.receive_output()
    orchestrator.stop()
    
    # Verify behavior
    assert response is not None
```