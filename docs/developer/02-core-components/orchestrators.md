# Orchestrators

Orchestrators are the heart of Claude MPM, managing the lifecycle of Claude subprocesses and coordinating all I/O operations. This document provides comprehensive details about each orchestrator type and their usage.

## Overview

Orchestrators implement different strategies for running and controlling Claude:
- **Subprocess Control**: Direct management of Claude processes
- **I/O Stream Handling**: Real-time interception and modification
- **Pattern Detection**: Identifying actionable patterns in output
- **Resource Management**: Memory and CPU monitoring

## Base Orchestrator

All orchestrators inherit from the `BaseOrchestrator` abstract class:

```python
from abc import ABC, abstractmethod

class BaseOrchestrator(ABC):
    """Abstract base class for all orchestrators"""
    
    @abstractmethod
    def start(self) -> None:
        """Start the orchestrator and Claude process"""
        pass
    
    @abstractmethod
    def send_message(self, message: str) -> None:
        """Send a message to Claude"""
        pass
    
    @abstractmethod
    def receive_output(self) -> str:
        """Receive output from Claude"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the orchestrator and cleanup"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if orchestrator is running"""
        pass
```

## Orchestrator Types

### 1. Subprocess Orchestrator

**File**: `src/claude_mpm/orchestration/subprocess_orchestrator.py`

The most powerful orchestrator, providing full subprocess control with pattern detection and agent delegation.

#### Key Features

- **Real-time I/O interception**: Captures all Claude output
- **Pattern detection**: Identifies delegations, tickets, and errors
- **Parallel agent execution**: Uses ThreadPoolExecutor
- **Resource tracking**: Monitors execution time and tokens

#### Architecture

```python
class SubprocessOrchestrator(BaseOrchestrator):
    def __init__(self, launcher: ClaudeLauncher, config: dict):
        self.launcher = launcher
        self.config = config
        self.process = None
        self.pattern_detector = PatternDetector()
        self.agent_executor = AgentExecutor()
        self.ticket_extractor = TicketExtractor()
```

#### Pattern Detection

The orchestrator detects multiple delegation patterns:

```python
# Pattern 1: Bold agent name
"**Engineer Agent**: Create a Python function..."

# Pattern 2: Task tool format
"Task(Engineer: implement fibonacci function)"

# Pattern 3: Direct delegation
"Delegating to QA Agent: test the implementation"
```

#### Agent Execution Flow

```python
def execute_delegations(self, delegations: List[Delegation]):
    """Execute agent delegations in parallel"""
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        
        for delegation in delegations:
            future = executor.submit(
                self._run_agent,
                delegation.agent_type,
                delegation.task,
                delegation.context
            )
            futures.append((delegation, future))
        
        # Collect results
        results = []
        for delegation, future in futures:
            try:
                result = future.result(timeout=300)
                results.append(self._format_result(delegation, result))
            except Exception as e:
                results.append(self._format_error(delegation, e))
        
        return results
```

#### Usage Example

```python
# Initialize orchestrator
orchestrator = SubprocessOrchestrator(
    launcher=ClaudeLauncher(config),
    config={
        'max_parallel_agents': 4,
        'agent_timeout': 300,
        'enable_tickets': True
    }
)

# Start session
orchestrator.start()

# Send message
orchestrator.send_message("Create a web scraper in Python")

# Process response (automatic delegation detection)
response = orchestrator.receive_output()

# Stop when done
orchestrator.stop()
```

### 2. System Prompt Orchestrator

**File**: `src/claude_mpm/orchestration/system_prompt_orchestrator.py`

Uses Claude's native `--system-prompt` flag for framework injection.

#### Key Features

- **Minimal overhead**: No I/O interception
- **Native Claude features**: Full Claude capabilities
- **Simple implementation**: Easiest to understand
- **Limited control**: Cannot intercept delegations

#### Implementation

```python
class SystemPromptOrchestrator(BaseOrchestrator):
    def __init__(self, launcher: ClaudeLauncher, framework_loader: FrameworkLoader):
        self.launcher = launcher
        self.framework = framework_loader.load()
        
    def start(self):
        # Build command with system prompt
        cmd = self.launcher.build_command()
        cmd.extend(['--system-prompt', self.framework])
        
        # Start Claude with framework as system prompt
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
```

#### Usage Example

```python
# Best for interactive sessions
orchestrator = SystemPromptOrchestrator(
    launcher=ClaudeLauncher(config),
    framework_loader=FrameworkLoader()
)

orchestrator.start()
# Claude now has framework instructions as system context
```

### 3. Interactive Subprocess Orchestrator

**File**: `src/claude_mpm/orchestration/interactive_subprocess_orchestrator.py`

Advanced orchestrator using `pexpect` for better interactive control.

#### Key Features

- **Terminal emulation**: Full PTY support
- **Better interactivity**: Handles special characters
- **Resource monitoring**: Memory and CPU tracking
- **Process management**: Advanced lifecycle control

#### Resource Monitoring

```python
class InteractiveSubprocessOrchestrator(BaseOrchestrator):
    def __init__(self, config: dict):
        self.memory_warning_mb = config.get('memory_warning_mb', 512)
        self.memory_critical_mb = config.get('memory_critical_mb', 1024)
        self.memory_hard_limit_mb = config.get('memory_hard_limit_mb', 2048)
        
    def monitor_resources(self):
        """Monitor subprocess resources"""
        while self.is_running():
            memory_mb = self.get_memory_usage()
            
            if memory_mb > self.memory_hard_limit_mb:
                self.logger.critical(f"Memory limit exceeded: {memory_mb}MB")
                self.terminate_process()
            elif memory_mb > self.memory_critical_mb:
                self.logger.warning(f"Critical memory usage: {memory_mb}MB")
            
            time.sleep(5)  # Check every 5 seconds
```

#### Pexpect Integration

```python
import pexpect

def start(self):
    # Start Claude with pexpect for better control
    self.process = pexpect.spawn(
        'claude',
        timeout=300,
        maxread=65536,
        searchwindowsize=4096
    )
    
    # Set up patterns to watch for
    self.process.expect_list([
        pexpect.EOF,
        pexpect.TIMEOUT,
        'Human:',  # Claude's input prompt
        'Assistant:'  # Claude's output marker
    ])
```

### 4. Agent Delegator Orchestrator

**File**: `src/claude_mpm/orchestration/agent_delegator.py`

Specialized orchestrator focused on multi-agent coordination.

#### Key Features

- **Agent-first design**: Optimized for delegations
- **Smart routing**: Selects best agent for tasks
- **Result synthesis**: Combines multi-agent outputs
- **Cross-agent coordination**: Manages dependencies

#### Agent Selection

```python
def select_agent(self, task: str) -> Agent:
    """Select the best agent for a task"""
    
    # Analyze task requirements
    requirements = self.analyze_task(task)
    
    # Score each agent
    scores = {}
    for agent in self.registry.list_agents():
        score = 0
        
        # Check specializations match
        for spec in requirements['specializations']:
            if spec in agent.specializations:
                score += 10
        
        # Check workload
        if agent.current_load < 0.8:
            score += 5
        
        # Check recent performance
        score += agent.success_rate * 10
        
        scores[agent.name] = score
    
    # Return best match
    best_agent = max(scores, key=scores.get)
    return self.registry.get_agent(best_agent)
```

## Orchestrator Selection Guide

### Decision Matrix

| Use Case | Recommended Orchestrator | Reason |
|----------|-------------------------|---------|
| Interactive development | System Prompt | Simple, full Claude features |
| Automated workflows | Subprocess | Pattern detection, automation |
| Terminal applications | Interactive Subprocess | Better terminal handling |
| Complex multi-agent tasks | Agent Delegator | Optimized for coordination |
| CI/CD pipelines | Subprocess | Reliable, scriptable |
| Resource-constrained | Interactive Subprocess | Memory monitoring |

### Configuration Examples

#### Development Setup
```yaml
orchestrator:
  type: system-prompt
  framework: enhanced
  logging: debug
```

#### Production Setup
```yaml
orchestrator:
  type: subprocess
  max_parallel_agents: 8
  agent_timeout: 600
  memory_limit_mb: 2048
  enable_monitoring: true
  patterns:
    - tickets
    - delegations
    - errors
```

#### CI/CD Setup
```yaml
orchestrator:
  type: subprocess
  non_interactive: true
  fail_on_error: true
  timeout: 1800
  log_format: json
```

## Advanced Features

### Custom Pattern Detection

Add custom patterns to any orchestrator:

```python
class CustomPatternDetector(PatternDetector):
    def __init__(self):
        super().__init__()
        
        # Add custom patterns
        self.add_pattern(
            name='code_block',
            regex=r'```(\w+)\n(.*?)```',
            handler=self.handle_code_block
        )
        
        self.add_pattern(
            name='metric',
            regex=r'METRIC:\s*(\w+)=(\d+)',
            handler=self.handle_metric
        )
    
    def handle_code_block(self, match):
        language = match.group(1)
        code = match.group(2)
        
        # Save code to file
        filename = f"generated_{language}_{timestamp}.{language}"
        Path(filename).write_text(code)
        
        return CodeBlockResult(language, filename)
```

### Hook Integration

All orchestrators support the hook system:

```python
orchestrator = SubprocessOrchestrator(launcher, config)

# Register hooks
orchestrator.hook_manager.register('pre_message', validate_input)
orchestrator.hook_manager.register('post_message', format_output)
orchestrator.hook_manager.register('pattern_detected', log_pattern)

# Hooks are called automatically during operation
```

### Resource Limits

Configure resource limits for subprocess orchestrators:

```python
config = {
    'resource_limits': {
        'memory_mb': 2048,
        'cpu_percent': 80,
        'disk_io_mb_per_sec': 100,
        'network_io_mb_per_sec': 50,
        'max_file_descriptors': 1024
    }
}

orchestrator = SubprocessOrchestrator(launcher, config)
```

## Error Handling

### Common Errors and Solutions

#### 1. Process Timeout
```python
try:
    orchestrator.send_message(message)
    response = orchestrator.receive_output()
except TimeoutError:
    # Extend timeout for long operations
    orchestrator.extend_timeout(600)
    # Or terminate and restart
    orchestrator.restart()
```

#### 2. Memory Exceeded
```python
except MemoryError:
    # Reduce parallel agents
    orchestrator.config['max_parallel_agents'] = 2
    # Clear caches
    orchestrator.clear_caches()
```

#### 3. Pattern Detection Failure
```python
except PatternError as e:
    # Log problematic output
    logger.error(f"Pattern detection failed: {e}")
    # Continue without pattern actions
    response = orchestrator.receive_raw_output()
```

## Performance Tuning

### Optimization Tips

1. **Buffer Sizes**
   ```python
   config['buffer_size'] = 65536  # Larger for high throughput
   config['line_buffer'] = True   # Line buffering for patterns
   ```

2. **Parallel Execution**
   ```python
   config['max_parallel_agents'] = os.cpu_count()
   config['agent_thread_pool_size'] = os.cpu_count() * 2
   ```

3. **Pattern Caching**
   ```python
   config['pattern_cache_size'] = 1000
   config['pattern_compile_cache'] = True
   ```

### Monitoring Performance

```python
# Enable performance monitoring
orchestrator.enable_monitoring()

# Get metrics
metrics = orchestrator.get_metrics()
print(f"Messages processed: {metrics['messages_processed']}")
print(f"Average response time: {metrics['avg_response_time']}ms")
print(f"Patterns detected: {metrics['patterns_detected']}")
print(f"Agents executed: {metrics['agents_executed']}")
```

## Testing Orchestrators

### Unit Testing

```python
def test_subprocess_orchestrator():
    # Mock subprocess
    with patch('subprocess.Popen') as mock_popen:
        mock_process = Mock()
        mock_process.stdout.readline.return_value = "Test output\n"
        mock_popen.return_value = mock_process
        
        orchestrator = SubprocessOrchestrator(launcher, config)
        orchestrator.start()
        
        output = orchestrator.receive_output()
        assert output == "Test output"
```

### Integration Testing

```python
def test_full_orchestration():
    orchestrator = SubprocessOrchestrator(launcher, config)
    
    try:
        orchestrator.start()
        
        # Test delegation detection
        orchestrator.send_message("**Engineer Agent**: Create a function")
        response = orchestrator.receive_output()
        
        # Verify agent was executed
        assert "Engineer Agent Result:" in response
        
    finally:
        orchestrator.stop()
```

## Best Practices

1. **Always use context managers**
   ```python
   with orchestrator:
       orchestrator.send_message(message)
       response = orchestrator.receive_output()
   ```

2. **Handle cleanup properly**
   ```python
   try:
       orchestrator.start()
       # ... work ...
   finally:
       orchestrator.stop()
       orchestrator.cleanup_resources()
   ```

3. **Monitor resource usage**
   ```python
   if orchestrator.get_memory_usage() > 1024:
       orchestrator.reduce_resource_usage()
   ```

4. **Log important events**
   ```python
   orchestrator.enable_debug_logging()
   orchestrator.log_patterns = True
   orchestrator.log_delegations = True
   ```

## Next Steps

- See [Agent System](agent-system.md) for agent coordination details
- Review [Hook Service](hook-service.md) for extensibility options
- Check [API Reference](../04-api-reference/orchestration-api.md) for complete API docs