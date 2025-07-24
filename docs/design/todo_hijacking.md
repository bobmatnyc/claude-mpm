# Claude PM Framework: Orchestration Control Design & Implementation

**Document Version:** 1.0  
**Date:** July 23, 2025  
**Status:** Design Phase  
**Authors:** Framework Architecture Team  

## Executive Summary

This document outlines the architectural changes required to restore orchestration control in the Claude PM Framework v1.4.0+. The current Python launcher uses `os.execvp` which completely replaces the orchestrator process with Claude Code, preventing multi-agent coordination, automatic ticket creation, and PM oversight. This design proposes a subprocess-based architecture that maintains orchestrator control while preserving full Claude Code functionality.

## Problem Statement

### Current Architecture Limitations

The Claude PM Framework v1.4.0 migration to pure Python introduced a critical architectural flaw:

```python
# Current problematic implementation
import os
os.execvp(claude_command, claude_args)
# ☠️ Process replacement - orchestrator dies here
```

**Impact:**
- **No PM orchestration**: PM agent never executes after Claude Code launch
- **No multi-agent coordination**: Cannot delegate to specialized agents
- **No automatic ticket creation**: Framework cannot process Claude Code outputs
- **No context injection**: Limited to static CLAUDE.md file
- **No process monitoring**: Cannot track Claude Code execution or results

### Root Cause Analysis

The architectural decision to use `os.execvp` was likely made for simplicity - it directly executes Claude Code as if the user ran it manually. However, this approach fundamentally breaks the orchestration model that defines the Claude PM Framework's value proposition.

**Process Flow Comparison:**

```
❌ Current (os.execvp):
[User] → [claude-pm launcher] → [REPLACED BY] → [Claude Code]
                                  ⚰️ PM dies

✅ Proposed (subprocess):  
[User] → [claude-pm launcher] → [spawns] → [Claude Code]
         [PM Orchestrator]       [monitors/manages]
```

## Design Objectives

### Primary Goals
1. **Restore PM Orchestration**: Enable the PM agent to coordinate multi-agent workflows
2. **Maintain Claude Code Compatibility**: Preserve all existing Claude Code functionality
3. **Enable Automatic Ticket Creation**: Process Claude Code outputs for workflow management
4. **Support Context Injection**: Dynamic instruction passing beyond static CLAUDE.md
5. **Provide Process Control**: Monitor, timeout, and manage Claude Code execution

### Secondary Goals
1. **Backward Compatibility**: Existing claude-pm commands continue working
2. **Performance Optimization**: Minimal overhead from subprocess management
3. **Error Handling**: Robust failure recovery and debugging capabilities
4. **Cross-Platform Support**: Windows, Linux, macOS compatibility
5. **Future Extensibility**: Architecture supports advanced orchestration features

## Proposed Solution Architecture

### Core Architecture: Orchestrator-Managed Subprocess

Replace `os.execvp` with `subprocess.Popen` to maintain orchestrator control:

```python
import subprocess
import json
import os
from typing import Dict, Any, Optional

class ClaudeCodeOrchestrator:
    """Manages Claude Code execution while maintaining PM control"""
    
    def __init__(self, framework_context: Dict[str, Any]):
        self.framework_context = framework_context
        self.pm_agent = None
        self.process = None
        
    def launch_claude_code(self, args: List[str]) -> int:
        """Launch Claude Code as managed subprocess"""
        
        # 1. Initialize PM orchestrator
        self.pm_agent = PMOrchestrator(self.framework_context)
        
        # 2. Prepare enhanced environment
        env = self._prepare_orchestrated_environment()
        
        # 3. Launch Claude Code as subprocess
        self.process = subprocess.Popen(
            ['claude'] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1  # Line buffered for real-time interaction
        )
        
        # 4. Start orchestration management
        return self._manage_orchestrated_session()
```

### Component Design

#### 1. Process Manager (`claude_pm/orchestration/process_manager.py`)

**Responsibilities:**
- Subprocess lifecycle management
- I/O stream handling and interception
- Process monitoring and health checks
- Timeout and resource management

```python
class ProcessManager:
    """Manages Claude Code subprocess execution"""
    
    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout
        self.process = None
        
    def create_process(self, command: List[str], env: Dict[str, str]) -> subprocess.Popen:
        """Create and return managed subprocess"""
        
    def monitor_process(self) -> ProcessStatus:
        """Monitor process health and resource usage"""
        
    def communicate_with_process(self, input_data: str) -> Tuple[str, str]:
        """Send input and receive output from process"""
        
    def terminate_process(self, graceful: bool = True) -> int:
        """Terminate process with optional graceful shutdown"""
```

#### 2. Context Manager (`claude_pm/orchestration/context_manager.py`)

**Responsibilities:**
- Environment variable preparation
- Dynamic context injection
- CLAUDE.md enhancement
- Configuration management

```python
class ContextManager:
    """Manages orchestration context and environment"""
    
    def prepare_environment(self, framework_context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for orchestrated execution"""
        env = os.environ.copy()
        
        # Add orchestration markers
        env['CLAUDE_PM_ORCHESTRATED'] = 'true'
        env['CLAUDE_PM_SESSION_ID'] = self._generate_session_id()
        env['CLAUDE_PM_FRAMEWORK_VERSION'] = self._get_framework_version()
        
        # Serialize complex context
        env['CLAUDE_PM_CONTEXT'] = base64.b64encode(
            json.dumps(framework_context).encode()
        ).decode()
        
        return env
        
    def enhance_claude_md(self, base_content: str, orchestration_context: Dict) -> str:
        """Enhance CLAUDE.md with orchestration instructions"""
```

#### 3. I/O Interceptor (`claude_pm/orchestration/io_interceptor.py`)

**Responsibilities:**
- Stream interception and processing
- Output parsing for ticket creation
- Input augmentation with PM instructions
- Real-time communication management

```python
class IOInterceptor:
    """Intercepts and processes Claude Code I/O streams"""
    
    def __init__(self, pm_agent):
        self.pm_agent = pm_agent
        self.output_buffer = []
        
    def intercept_output(self, output: str) -> str:
        """Process Claude Code output for orchestration"""
        # Parse for ticket creation triggers
        tickets = self._extract_ticket_information(output)
        if tickets:
            self.pm_agent.create_tickets(tickets)
            
        # Log for agent training
        self._log_for_agent_learning(output)
        
        return output  # Pass through to user
        
    def augment_input(self, user_input: str) -> str:
        """Enhance user input with PM context"""
        if self._should_add_pm_context(user_input):
            return self._add_orchestration_instructions(user_input)
        return user_input
```

#### 4. PM Agent Integration (`claude_pm/agents/pm_orchestrator.py`)

**Enhanced PM orchestrator that runs alongside Claude Code:**

```python
class PMOrchestrator:
    """Project Manager agent for multi-agent coordination"""
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.active_agents = {}
        self.session_log = []
        
    def coordinate_agents(self, task_context: str) -> Dict[str, Any]:
        """Coordinate specialized agents based on Claude Code activity"""
        
        # Analyze task requirements
        required_agents = self._analyze_required_agents(task_context)
        
        # Delegate to specialized agents
        results = {}
        for agent_type in required_agents:
            agent = self._get_or_create_agent(agent_type)
            results[agent_type] = agent.execute_task(task_context)
            
        return self._integrate_agent_results(results)
        
    def create_tickets(self, ticket_data: List[Dict]) -> List[str]:
        """Create tickets from Claude Code output analysis"""
        
    def track_session_progress(self, activity: str) -> None:
        """Track and log session progress for reporting"""
```

### Implementation Phases

#### Phase 1: Core Subprocess Architecture (Week 1-2)
**Deliverables:**
- ProcessManager implementation
- Basic subprocess launching with maintained orchestrator
- Environment variable context passing
- Smoke tests for basic functionality

**Success Criteria:**
- Claude Code launches as subprocess
- PM orchestrator remains active during session
- Basic I/O passthrough works correctly
- No regression in Claude Code functionality

#### Phase 2: I/O Interception & Context Injection (Week 3-4)
**Deliverables:**
- IOInterceptor implementation
- Enhanced CLAUDE.md generation
- Basic output parsing for ticket triggers
- Input augmentation with PM instructions

**Success Criteria:**
- Can intercept and process Claude Code outputs
- PM context successfully injected into Claude Code session
- Automatic ticket creation from parsed outputs
- Enhanced CLAUDE.md includes orchestration instructions

#### Phase 3: Full PM Integration & Multi-Agent Coordination (Week 5-6)
**Deliverables:**
- Complete PMOrchestrator integration
- Multi-agent delegation based on Claude Code activity
- Session logging and progress tracking
- Agent training data collection

**Success Criteria:**
- PM can delegate tasks to specialized agents
- Multi-agent workflows coordinate with Claude Code
- Session progress tracked and reported
- Agent learning data collected for training

#### Phase 4: Advanced Features & Optimization (Week 7-8)
**Deliverables:**
- Process monitoring and resource management
- Advanced error handling and recovery
- Performance optimization
- Comprehensive testing and documentation

**Success Criteria:**
- Robust error handling and process recovery
- Optimized performance with minimal overhead
- Complete test coverage
- Production-ready documentation

## Technical Implementation Details

### Subprocess Configuration

```python
# Optimal subprocess configuration for orchestration
process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,    # Enable input injection
    stdout=subprocess.PIPE,   # Capture output for processing
    stderr=subprocess.PIPE,   # Capture errors for handling
    text=True,               # String I/O vs bytes
    bufsize=1,               # Line buffered for real-time
    universal_newlines=True, # Cross-platform line endings
    env=enhanced_env,        # Orchestration environment
    cwd=project_root,       # Proper working directory
    preexec_fn=None,        # Linux process group setup
    creationflags=0         # Windows process creation flags
)
```

### Environment Variable Schema

```python
# Orchestration environment variables
ORCHESTRATION_ENV = {
    'CLAUDE_PM_ORCHESTRATED': 'true',
    'CLAUDE_PM_SESSION_ID': 'session_uuid',
    'CLAUDE_PM_FRAMEWORK_VERSION': '1.4.0',
    'CLAUDE_PM_CONTEXT': 'base64_encoded_json',
    'CLAUDE_PM_PM_AGENT_PID': 'orchestrator_process_id',
    'CLAUDE_PM_PROJECT_ROOT': '/path/to/project',
    'CLAUDE_PM_LOG_LEVEL': 'INFO',
    'CLAUDE_PM_TICKET_AUTO_CREATE': 'true'
}
```

### Output Parsing for Ticket Creation

```python
class TicketExtractor:
    """Extract ticket information from Claude Code output"""
    
    TICKET_PATTERNS = [
        r'TODO:\s*(.+)',
        r'FIXME:\s*(.+)', 
        r'BUG:\s*(.+)',
        r'FEATURE:\s*(.+)',
        r'Created:\s*(.+)',
        r'Fixed:\s*(.+)',
        r'Implemented:\s*(.+)'
    ]
    
    def extract_tickets(self, output: str) -> List[Dict[str, Any]]:
        """Extract structured ticket data from output"""
        tickets = []
        
        for pattern in self.TICKET_PATTERNS:
            matches = re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                tickets.append({
                    'type': self._determine_ticket_type(pattern),
                    'title': match.group(1).strip(),
                    'context': self._extract_surrounding_context(output, match),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'claude_code_output'
                })
                
        return tickets
```

## Risk Analysis & Mitigation

### Technical Risks

#### Risk: Subprocess Overhead
**Impact:** Performance degradation from process management  
**Probability:** Medium  
**Mitigation:** 
- Optimize subprocess configuration
- Use line buffering for minimal latency
- Profile and benchmark against current implementation
- Implement connection pooling for multiple sessions

#### Risk: I/O Stream Deadlocks
**Impact:** Process hanging or freezing  
**Probability:** Medium  
**Mitigation:**
- Use threading for concurrent I/O handling
- Implement proper timeout mechanisms
- Add comprehensive error handling
- Use select() or asyncio for non-blocking I/O

#### Risk: Environment Variable Conflicts
**Impact:** Claude Code behavior changes unexpectedly  
**Probability:** Low  
**Mitigation:**
- Use CLAUDE_PM_ prefix for all orchestration variables
- Document all environment modifications
- Provide opt-out mechanisms
- Test with various Claude Code configurations

### Implementation Risks

#### Risk: Backward Compatibility Breakage
**Impact:** Existing workflows stop working  
**Probability:** Medium  
**Mitigation:**
- Maintain existing command-line interface
- Add feature flags for orchestration mode
- Comprehensive regression testing
- Gradual rollout with fallback options

#### Risk: Complex Error Scenarios
**Impact:** Difficult debugging and user confusion  
**Probability:** High  
**Mitigation:**
- Extensive error handling and logging
- Clear error messages with suggested solutions
- Debug mode with verbose output
- Comprehensive troubleshooting documentation

## Success Metrics

### Functional Metrics
- **PM Orchestration Restored**: PM agent executes during Claude Code sessions
- **Automatic Ticket Creation**: Tickets created from Claude Code outputs
- **Multi-Agent Coordination**: Specialized agents coordinate with Claude Code
- **Context Injection**: Dynamic instructions passed to Claude Code
- **Process Control**: Can monitor, timeout, and manage Claude Code

### Performance Metrics
- **Startup Time**: <500ms additional overhead for orchestration
- **I/O Latency**: <50ms additional delay for stream processing
- **Memory Usage**: <10MB additional memory for orchestrator
- **CPU Overhead**: <5% additional CPU usage during active sessions

### Quality Metrics
- **Reliability**: 99.9% successful orchestration sessions
- **Error Recovery**: 95% automatic recovery from process failures
- **Compatibility**: 100% backward compatibility with existing commands
- **Test Coverage**: 90% code coverage for orchestration components

## Future Considerations

### Advanced Orchestration Features
1. **Multi-Claude-Code Sessions**: Coordinate multiple Claude Code instances
2. **Agent Communication**: Direct communication between Claude Code and framework agents
3. **Workflow Automation**: Automated multi-step development workflows
4. **Session Persistence**: Resume orchestration sessions across restarts

### Integration Opportunities
1. **Claude Code Plugin**: Official plugin for deeper integration
2. **MCP Server**: Model Context Protocol server for orchestration
3. **IDE Extensions**: VS Code/IntelliJ plugins for orchestration
4. **CI/CD Integration**: GitHub Actions for orchestrated development

### Scalability Considerations
1. **Distributed Orchestration**: Multi-machine agent coordination
2. **Cloud Orchestration**: Serverless orchestration functions
3. **Enterprise Features**: Team coordination and management
4. **Performance Optimization**: Advanced caching and optimization

## TODO Hijacking Implementation

### File-Based TODO Manipulation Strategy

Based on research into existing frameworks that successfully hijack Claude Code's TODO system, we can implement a **file-based TODO manipulation approach** that intercepts and transforms Claude's TODO operations in real-time.

#### How Claude Code Stores TODOs

Claude Code stores TODO lists as JSON files in the user's file system:

```bash
# TODO storage location
~/.claude/todos/[session-id]-agent-[agent-id].json

# Example file structure
{
  "todos": [
    {
      "id": "1",
      "content": "Implement user authentication system",
      "status": "pending",
      "priority": "high"
    },
    {
      "id": "2", 
      "content": "Write unit tests for auth module",
      "status": "in_progress",
      "priority": "medium"
    }
  ]
}
```

#### Hijacking Mechanisms

**1. Environment Variable Override**
```python
# Redirect TODO storage to custom location
os.environ['CLAUDE_CONFIG_DIR'] = '/custom/claude-pm/config'
os.environ['CLAUDE_TODO_STORAGE'] = '/custom/claude-pm/todos'
```

**2. Real-time File System Monitoring**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TodoHijacker(FileSystemEventHandler):
    def on_modified(self, event):
        if self._is_claude_todo_file(event.src_path):
            # Intercept TODO file changes
            self._process_todo_changes(event.src_path)
    
    def _process_todo_changes(self, todo_file):
        # 1. Read Claude's TODO format
        claude_todos = self._parse_claude_todos(todo_file)
        
        # 2. Transform to PM framework format
        pm_tickets = self._convert_to_pm_tickets(claude_todos)
        
        # 3. Create external tickets
        external_tickets = self._create_external_tickets(pm_tickets)
        
        # 4. Delegate to specialized agents
        self._delegate_to_agents(pm_tickets)
```

**3. TODO-to-Ticket Transformation Pipeline**
```python
def transform_claude_todo_to_pm_ticket(claude_todo):
    """Convert Claude TODO to PM framework ticket"""
    
    # Determine agent type from content analysis
    agent_type = analyze_todo_content(claude_todo.content)
    
    # Create PM ticket
    pm_ticket = PMTicket(
        ticket_id=f"PM-{counter:04d}",
        title=claude_todo.content,
        agent_type=agent_type,  # engineer, qa, documentation, etc.
        priority=claude_todo.priority,
        status=map_claude_status(claude_todo.status),
        claude_todo_id=claude_todo.id
    )
    
    return pm_ticket
```

#### Agent Type Detection Algorithm

The system uses intelligent content analysis to determine which specialized agent should handle each TODO:

```python
AGENT_MAPPINGS = {
    'implement': 'engineer',
    'code': 'engineer',
    'fix': 'engineer',
    'test': 'qa',
    'validate': 'qa', 
    'review': 'qa',
    'document': 'documentation',
    'api docs': 'documentation',
    'security': 'security',
    'audit': 'security',
    'deploy': 'ops',
    'setup': 'ops',
    'research': 'researcher'
}

def determine_agent_type(todo_content):
    content_lower = todo_content.lower()
    
    # Check for keyword matches
    for keyword, agent_type in AGENT_MAPPINGS.items():
        if keyword in content_lower:
            return agent_type
    
    # Default classification logic
    if any(indicator in content_lower for indicator in ['file', 'function', 'class']):
        return 'engineer'
    
    return 'documentation'  # Safe default
```

#### Integration with Subprocess Architecture

The TODO hijacking integrates seamlessly with the subprocess orchestration approach:

```python
class ClaudeCodeOrchestrator:
    def __init__(self):
        self.pm_orchestrator = PMOrchestrator()
        self.todo_hijacker = TodoHijacker(self.pm_orchestrator)
        
    def launch_claude_code(self, args):
        # 1. Setup TODO monitoring
        self._setup_todo_monitoring()
        
        # 2. Launch Claude Code as subprocess
        self.process = subprocess.Popen(['claude'] + args, ...)
        
        # 3. TODO operations are automatically hijacked via file monitoring
        # 4. PM orchestrator coordinates multi-agent workflows
        
        return self._manage_orchestrated_session()
```

#### Production Examples

Multiple frameworks successfully use this approach:

1. **Claude Task Master**: Hijacks TODOs for PRD-driven development with Linear/GitHub integration
2. **TDD Guard**: Intercepts TODOs to enforce red-green-refactor cycles
3. **Specification-Driven Framework**: Transforms TODOs into staged workflow management

#### Benefits of File-Based Hijacking

- **Non-invasive**: No Claude Code modifications required
- **Real-time**: Processes TODO operations as they occur
- **Transparent**: Claude Code continues working normally
- **Persistent**: Works across Claude Code sessions
- **Extensible**: Can transform TODOs into any external format

### Implementation Architecture

```python
# Complete hijacking workflow
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│   TODO Hijacker  │───▶│ PM Orchestrator │
│                 │    │                  │    │                 │
│ Writes todos to │    │ Monitors files & │    │ Creates tickets │
│ JSON files      │    │ transforms data  │    │ & delegates     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ External Tickets │    │ Specialized     │
                       │ (GitHub/Linear)  │    │ Agents          │
                       └──────────────────┘    └─────────────────┘
```

This file-based TODO hijacking approach provides the foundation for full PM orchestration while maintaining complete compatibility with Claude Code's existing functionality.

## Conclusion

The proposed subprocess-based architecture with TODO hijacking restores the Claude PM Framework's core orchestration capabilities while maintaining full Claude Code compatibility. This design enables:

- **Immediate Value**: Automatic ticket creation and PM coordination through TODO hijacking
- **Scalable Architecture**: Foundation for advanced orchestration features with file-based monitoring
- **Backward Compatibility**: No disruption to existing workflows - Claude Code operates normally
- **Future Extensibility**: Platform for enhanced multi-agent capabilities through real-time TODO transformation

Implementation should proceed in phases to ensure stability and allow for iterative improvements based on user feedback and performance metrics.

The technical approach leverages Python's robust subprocess capabilities, proven file system monitoring patterns, and successful TODO hijacking techniques used by production frameworks. By maintaining the orchestrator process while spawning Claude Code as a managed subprocess, and intercepting TODO operations through file system monitoring, we achieve the best of both worlds: full Claude Code functionality with comprehensive orchestration control.

This design represents a critical architectural improvement that restores the Claude PM Framework's unique value proposition in the AI orchestration landscape, while providing a proven, non-invasive path to integration that doesn't require any modifications to Claude Code itself.