# Design Patterns in Claude MPM

This document describes the design patterns implemented throughout Claude MPM, providing examples and rationale for each pattern's use.

## Overview

Claude MPM employs several well-established design patterns to achieve modularity, extensibility, and maintainability. These patterns enable the system to handle complex orchestration scenarios while remaining flexible for future enhancements.

## Structural Patterns

### 1. Strategy Pattern

**Purpose**: Allow different orchestration algorithms to be selected at runtime.

**Implementation**: Orchestrator hierarchy

```python
# Base strategy interface
class BaseOrchestrator(ABC):
    @abstractmethod
    def start(self) -> None:
        """Start the orchestrator"""
        pass
    
    @abstractmethod
    def send_message(self, message: str) -> None:
        """Send message to Claude"""
        pass
    
    @abstractmethod
    def receive_output(self) -> str:
        """Receive output from Claude"""
        pass

# Concrete strategies
class SubprocessOrchestrator(BaseOrchestrator):
    """Direct subprocess control with pattern detection"""
    def start(self):
        self.process = subprocess.Popen(...)
        
class SystemPromptOrchestrator(BaseOrchestrator):
    """Uses --system-prompt flag"""
    def start(self):
        self.process = subprocess.Popen([..., '--system-prompt', ...])

# Context that uses strategies
class ClaudeLauncher:
    def __init__(self, orchestrator: BaseOrchestrator):
        self.orchestrator = orchestrator
        
    def run(self):
        self.orchestrator.start()
        # Use orchestrator...
```

**Benefits**:
- Easy to add new orchestration strategies
- Runtime selection based on user preferences
- Isolated testing of each strategy

### 2. Factory Pattern

**Purpose**: Create objects without specifying their exact classes.

**Implementation**: Orchestrator factory

```python
class OrchestratorFactory:
    """Factory for creating orchestrators based on mode"""
    
    @staticmethod
    def create_orchestrator(mode: str, config: dict) -> BaseOrchestrator:
        orchestrators = {
            'subprocess': SubprocessOrchestrator,
            'system-prompt': SystemPromptOrchestrator,
            'interactive': InteractiveSubprocessOrchestrator,
            'agent-delegator': AgentDelegatorOrchestrator
        }
        
        orchestrator_class = orchestrators.get(mode)
        if not orchestrator_class:
            raise ValueError(f"Unknown orchestrator mode: {mode}")
            
        return orchestrator_class(**config)

# Usage
orchestrator = OrchestratorFactory.create_orchestrator(
    mode='subprocess',
    config={'timeout': 300}
)
```

**Benefits**:
- Centralized object creation logic
- Easy to extend with new types
- Consistent initialization

### 3. Singleton Pattern

**Purpose**: Ensure only one instance of certain services exist.

**Implementation**: Agent Registry

```python
class AgentRegistry:
    """Singleton registry for all agents"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._agents = {}
        self._initialized = True
        self.discover_agents()
    
    def register_agent(self, name: str, agent: Agent):
        self._agents[name] = agent
    
    def get_agent(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)
```

**Benefits**:
- Global access to agent registry
- Prevents duplicate agent discovery
- Thread-safe access

### 4. Adapter Pattern

**Purpose**: Allow incompatible interfaces to work together.

**Implementation**: AI-Trackdown integration

```python
class AITrackdownAdapter:
    """Adapts Claude MPM tickets to AI-Trackdown format"""
    
    def __init__(self, trackdown_client):
        self.client = trackdown_client
    
    def create_ticket(self, mpm_ticket: MPMTicket) -> TrackdownTicket:
        # Adapt MPM ticket format to Trackdown format
        trackdown_data = {
            'title': mpm_ticket.summary,
            'description': mpm_ticket.content,
            'type': self._map_ticket_type(mpm_ticket.type),
            'labels': self._extract_labels(mpm_ticket),
            'metadata': {
                'source': 'claude-mpm',
                'session_id': mpm_ticket.session_id
            }
        }
        
        return self.client.create_ticket(trackdown_data)
    
    def _map_ticket_type(self, mpm_type: str) -> str:
        type_mapping = {
            'TODO': 'task',
            'BUG': 'bug',
            'FEATURE': 'feature'
        }
        return type_mapping.get(mpm_type, 'task')
```

**Benefits**:
- Decouples Claude MPM from external systems
- Easy to add new integrations
- Maintains clean interfaces

### 5. Decorator Pattern

**Purpose**: Add new functionality to objects without altering structure.

**Implementation**: LoggerMixin

```python
class LoggerMixin:
    """Mixin to add logging capabilities to any class"""
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger
    
    def log_debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)
    
    def log_info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def log_error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)

# Usage
class SubprocessOrchestrator(BaseOrchestrator, LoggerMixin):
    def start(self):
        self.log_info("Starting subprocess orchestrator")
        # ... implementation ...
        self.log_debug("Process started", pid=self.process.pid)
```

**Benefits**:
- Consistent logging across all components
- No code duplication
- Easy to enhance logging functionality

## Behavioral Patterns

### 6. Observer Pattern

**Purpose**: Define a one-to-many dependency between objects.

**Implementation**: Hook system

```python
class HookManager:
    """Observable that notifies hooks of events"""
    
    def __init__(self):
        self._hooks = {
            'pre_message': [],
            'post_message': [],
            'error': [],
            'session_end': []
        }
    
    def register_hook(self, event: str, hook: Callable):
        if event in self._hooks:
            self._hooks[event].append(hook)
    
    def notify(self, event: str, data: Any) -> Any:
        result = data
        for hook in self._hooks.get(event, []):
            try:
                result = hook(result)
            except Exception as e:
                self.log_error(f"Hook error: {e}")
        return result

# Hook implementation
class LoggingHook:
    def pre_message(self, message: str) -> str:
        logger.info(f"User message: {message}")
        return message
    
    def post_message(self, response: str) -> str:
        logger.info(f"Claude response: {response[:100]}...")
        return response

# Registration
hook_manager = HookManager()
logging_hook = LoggingHook()
hook_manager.register_hook('pre_message', logging_hook.pre_message)
hook_manager.register_hook('post_message', logging_hook.post_message)
```

**Benefits**:
- Loose coupling between components
- Dynamic hook registration
- Easy to add new event types

### 7. Chain of Responsibility Pattern

**Purpose**: Pass requests along a chain of handlers.

**Implementation**: Pattern detection

```python
class PatternHandler(ABC):
    """Base handler in the chain"""
    
    def __init__(self):
        self._next_handler = None
    
    def set_next(self, handler: 'PatternHandler'):
        self._next_handler = handler
        return handler
    
    @abstractmethod
    def can_handle(self, text: str) -> bool:
        pass
    
    @abstractmethod
    def handle(self, text: str) -> Optional[Pattern]:
        pass
    
    def process(self, text: str) -> List[Pattern]:
        patterns = []
        
        if self.can_handle(text):
            pattern = self.handle(text)
            if pattern:
                patterns.append(pattern)
        
        if self._next_handler:
            patterns.extend(self._next_handler.process(text))
            
        return patterns

class TicketPatternHandler(PatternHandler):
    def can_handle(self, text: str) -> bool:
        return any(marker in text for marker in ['TODO:', 'BUG:', 'FEATURE:'])
    
    def handle(self, text: str) -> Optional[Pattern]:
        match = re.search(r'(TODO|BUG|FEATURE):\s*(.+)', text)
        if match:
            return Pattern(
                type='ticket',
                subtype=match.group(1),
                content=match.group(2)
            )
        return None

class DelegationPatternHandler(PatternHandler):
    def can_handle(self, text: str) -> bool:
        return '**' in text and ':' in text
    
    def handle(self, text: str) -> Optional[Pattern]:
        match = re.search(r'\*\*([^*]+)\*\*:\s*(.+)', text)
        if match:
            return Pattern(
                type='delegation',
                agent=match.group(1),
                task=match.group(2)
            )
        return None

# Build the chain
ticket_handler = TicketPatternHandler()
delegation_handler = DelegationPatternHandler()
error_handler = ErrorPatternHandler()

ticket_handler.set_next(delegation_handler).set_next(error_handler)

# Process text
patterns = ticket_handler.process("TODO: Fix the **Engineer Agent**: bug")
```

**Benefits**:
- Easy to add new pattern types
- Handlers can be reordered
- Each handler has single responsibility

### 8. Command Pattern

**Purpose**: Encapsulate requests as objects.

**Implementation**: Agent tasks

```python
class AgentTask:
    """Command that encapsulates an agent task"""
    
    def __init__(self, agent_type: str, task_description: str, context: dict):
        self.agent_type = agent_type
        self.task_description = task_description
        self.context = context
        self.result = None
        self.status = 'pending'
    
    def execute(self, executor: 'AgentExecutor') -> Any:
        self.status = 'running'
        try:
            self.result = executor.run_agent(
                self.agent_type,
                self.task_description,
                self.context
            )
            self.status = 'completed'
        except Exception as e:
            self.status = 'failed'
            self.result = str(e)
        return self.result
    
    def undo(self):
        # Cleanup any resources
        pass

class TaskQueue:
    """Manages and executes tasks"""
    
    def __init__(self, executor: AgentExecutor):
        self.tasks = []
        self.executor = executor
    
    def add_task(self, task: AgentTask):
        self.tasks.append(task)
    
    def execute_all(self):
        results = []
        for task in self.tasks:
            result = task.execute(self.executor)
            results.append(result)
        return results
```

**Benefits**:
- Tasks can be queued and executed later
- Easy to implement undo/redo
- Tasks are self-contained

### 9. Template Method Pattern

**Purpose**: Define skeleton of algorithm in base class.

**Implementation**: Base orchestrator

```python
class BaseOrchestrator(ABC):
    """Template for orchestrator workflow"""
    
    def run_session(self):
        """Template method defining the session workflow"""
        try:
            self.initialize()
            self.start_process()
            self.inject_framework()
            
            while self.is_running():
                message = self.get_user_input()
                if message == 'exit':
                    break
                    
                self.process_message(message)
                
        finally:
            self.cleanup()
    
    def initialize(self):
        """Initialize orchestrator resources"""
        self.logger.info("Initializing orchestrator")
        self.setup_directories()
        self.load_configuration()
    
    @abstractmethod
    def start_process(self):
        """Start the Claude process - must be implemented"""
        pass
    
    @abstractmethod
    def inject_framework(self):
        """Inject framework instructions - must be implemented"""
        pass
    
    def process_message(self, message: str):
        """Process a single message"""
        enhanced = self.pre_process(message)
        self.send_to_claude(enhanced)
        response = self.receive_from_claude()
        final = self.post_process(response)
        self.display_output(final)
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up")
        self.stop_process()
        self.save_session()

# Concrete implementation
class SubprocessOrchestrator(BaseOrchestrator):
    def start_process(self):
        self.process = subprocess.Popen(...)
    
    def inject_framework(self):
        framework = self.load_framework()
        self.send_to_claude(framework)
```

**Benefits**:
- Consistent workflow across orchestrators
- Subclasses only implement specific steps
- Easy to understand overall flow

### 10. State Pattern

**Purpose**: Allow object to alter behavior when internal state changes.

**Implementation**: Session state management

```python
class SessionState(ABC):
    """Base state for session"""
    
    @abstractmethod
    def handle_message(self, session: 'Session', message: str):
        pass
    
    @abstractmethod
    def can_transition_to(self, state: 'SessionState') -> bool:
        pass

class InitializingState(SessionState):
    def handle_message(self, session, message):
        raise ValueError("Session not ready for messages")
    
    def can_transition_to(self, state):
        return isinstance(state, (ActiveState, ErrorState))

class ActiveState(SessionState):
    def handle_message(self, session, message):
        # Process message normally
        result = session.orchestrator.process_message(message)
        
        # Check for state transitions
        if 'error' in result:
            session.set_state(ErrorState())
        elif message == 'pause':
            session.set_state(PausedState())
            
        return result
    
    def can_transition_to(self, state):
        return isinstance(state, (PausedState, ErrorState, TerminatingState))

class PausedState(SessionState):
    def handle_message(self, session, message):
        if message == 'resume':
            session.set_state(ActiveState())
            return "Session resumed"
        return "Session is paused. Type 'resume' to continue."

class Session:
    def __init__(self):
        self.state = InitializingState()
        self.orchestrator = None
    
    def set_state(self, state: SessionState):
        if self.state.can_transition_to(state):
            self.state = state
        else:
            raise ValueError(f"Invalid state transition")
    
    def process_message(self, message: str):
        return self.state.handle_message(self, message)
```

**Benefits**:
- Clean state transitions
- State-specific behavior
- Easy to add new states

## Creational Patterns

### 11. Builder Pattern

**Purpose**: Construct complex objects step by step.

**Implementation**: Claude command builder

```python
class ClaudeCommandBuilder:
    """Builder for complex Claude commands"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.command = ['claude']
        self.env = os.environ.copy()
        return self
    
    def with_model(self, model: str):
        self.command.extend(['--model', model])
        return self
    
    def with_system_prompt(self, prompt: str):
        self.command.extend(['--system-prompt', prompt])
        return self
    
    def with_context(self, context_file: str):
        self.command.extend(['--context', context_file])
        return self
    
    def with_environment(self, key: str, value: str):
        self.env[key] = value
        return self
    
    def with_timeout(self, timeout: int):
        self.command.extend(['--timeout', str(timeout)])
        return self
    
    def build(self) -> Tuple[List[str], dict]:
        return self.command.copy(), self.env.copy()

# Usage
builder = ClaudeCommandBuilder()
command, env = (builder
    .with_model('opus')
    .with_system_prompt('You are a helpful assistant')
    .with_context('/path/to/context.md')
    .with_environment('CLAUDE_API_KEY', 'xxx')
    .with_timeout(300)
    .build())
```

**Benefits**:
- Fluent interface
- Complex object construction simplified
- Easy to extend with new options

### 12. Object Pool Pattern

**Purpose**: Reuse expensive objects instead of creating new ones.

**Implementation**: Process pool for agents

```python
class AgentProcessPool:
    """Pool of reusable agent processes"""
    
    def __init__(self, size: int = 4):
        self.size = size
        self.available = queue.Queue()
        self.in_use = {}
        self._create_initial_processes()
    
    def _create_initial_processes(self):
        for _ in range(self.size):
            process = self._create_process()
            self.available.put(process)
    
    def _create_process(self):
        return subprocess.Popen(
            [sys.executable, '-m', 'claude_mpm.agent_worker'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    def acquire(self, timeout: float = 30) -> subprocess.Popen:
        try:
            process = self.available.get(timeout=timeout)
            self.in_use[process.pid] = process
            return process
        except queue.Empty:
            raise TimeoutError("No available processes in pool")
    
    def release(self, process: subprocess.Popen):
        if process.poll() is None:  # Still alive
            self.in_use.pop(process.pid, None)
            self.available.put(process)
        else:
            # Replace dead process
            self.in_use.pop(process.pid, None)
            new_process = self._create_process()
            self.available.put(new_process)
    
    def shutdown(self):
        # Terminate all processes
        while not self.available.empty():
            process = self.available.get()
            process.terminate()
        
        for process in self.in_use.values():
            process.terminate()
```

**Benefits**:
- Reduces process creation overhead
- Better resource management
- Improved performance

## Anti-Patterns to Avoid

### 1. God Object
**Avoid**: Creating classes that do too much.

```python
# Bad - God object
class ClaudeMPM:
    def parse_args(self): ...
    def start_subprocess(self): ...
    def detect_patterns(self): ...
    def create_tickets(self): ...
    def manage_agents(self): ...
    def handle_hooks(self): ...
    # ... 50 more methods

# Good - Separated concerns
class CLI: ...
class Orchestrator: ...
class PatternDetector: ...
class TicketManager: ...
class AgentManager: ...
class HookService: ...
```

### 2. Spaghetti Code
**Avoid**: Complex interdependencies between modules.

```python
# Bad - Circular dependencies
# orchestrator.py
from services import HookService

# services.py
from orchestrator import Orchestrator

# Good - Dependency injection
class Orchestrator:
    def __init__(self, hook_service: HookService):
        self.hook_service = hook_service
```

### 3. Copy-Paste Programming
**Avoid**: Duplicating code instead of abstracting.

```python
# Bad - Duplicated subprocess handling
def run_engineer_agent():
    proc = subprocess.Popen(...)
    # 20 lines of error handling
    
def run_qa_agent():
    proc = subprocess.Popen(...)
    # Same 20 lines of error handling

# Good - Shared abstraction
def run_agent(agent_type: str):
    proc = create_agent_process(agent_type)
    return handle_agent_execution(proc)
```

## Best Practices

1. **Favor Composition Over Inheritance**
   - Use mixins for shared behavior
   - Compose objects rather than deep inheritance

2. **Program to Interfaces**
   - Define abstract base classes
   - Depend on abstractions, not concrete classes

3. **Single Responsibility Principle**
   - Each class should have one reason to change
   - Split large classes into focused components

4. **Open/Closed Principle**
   - Open for extension, closed for modification
   - Use patterns like Strategy and Observer

5. **Dependency Inversion**
   - High-level modules shouldn't depend on low-level modules
   - Both should depend on abstractions