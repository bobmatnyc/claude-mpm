# Subprocess Design

This document details the subprocess architecture that forms the core of Claude MPM's orchestration capabilities.

## Overview

Claude MPM's subprocess design enables:
- Full control over Claude's execution environment
- Real-time I/O stream interception and modification
- Pattern detection and automated actions
- Resource monitoring and management
- Parallel agent execution

## Core Subprocess Components

### 1. Subprocess Creation

```python
# From src/claude_mpm/core/claude_launcher.py
self.process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,  # Line buffered
    env=env,
    preexec_fn=os.setsid if platform.system() != 'Windows' else None
)
```

Key design decisions:
- **Line buffering**: Enables real-time stream processing
- **Text mode**: Simplifies string handling
- **Process group**: Allows killing entire process trees
- **Separate stderr**: Captures errors independently

### 2. I/O Stream Management

#### Input Stream Processing
```python
def send_to_claude(self, message: str):
    # Pre-process message
    processed = self.pre_process_message(message)
    
    # Inject framework if needed
    if self.should_inject_framework():
        processed = self.inject_framework(processed)
    
    # Send to subprocess
    self.process.stdin.write(processed + '\n')
    self.process.stdin.flush()
```

#### Output Stream Processing
```python
def read_from_claude(self):
    while True:
        line = self.process.stdout.readline()
        if not line:
            break
            
        # Pattern detection
        patterns = self.detect_patterns(line)
        
        # Trigger actions
        for pattern in patterns:
            self.handle_pattern(pattern)
            
        # Post-process
        processed = self.post_process_output(line)
        
        # Send to user
        self.display_output(processed)
```

### 3. Pattern Detection Engine

The pattern detection system identifies actionable content:

```python
class PatternDetector:
    PATTERNS = {
        'ticket': r'(?:TODO|BUG|FEATURE):\s*(.+)',
        'delegation': r'\*\*([^*]+)\*\*:\s*(.+)',
        'task_tool': r'Task\(([^)]+)\)',
        'error': r'Error:\s*(.+)',
        'warning': r'Warning:\s*(.+)'
    }
    
    def detect(self, text: str) -> List[Pattern]:
        detected = []
        for pattern_type, regex in self.PATTERNS.items():
            matches = re.finditer(regex, text)
            for match in matches:
                detected.append(Pattern(
                    type=pattern_type,
                    content=match.group(0),
                    groups=match.groups()
                ))
        return detected
```

### 4. Process Lifecycle Management

#### Starting Processes
```python
class ProcessManager:
    def start_process(self, cmd: List[str]) -> Process:
        # Pre-start checks
        self.validate_command(cmd)
        self.check_resources()
        
        # Create process
        process = subprocess.Popen(
            cmd,
            **self.get_popen_kwargs()
        )
        
        # Register for monitoring
        self.register_process(process)
        
        # Start monitoring thread
        self.start_monitoring(process)
        
        return process
```

#### Monitoring Processes
```python
def monitor_process(self, process: Process):
    while process.poll() is None:
        # Check memory usage
        memory_mb = self.get_memory_usage(process.pid)
        if memory_mb > self.memory_limit_mb:
            self.handle_memory_exceeded(process)
            
        # Check CPU usage
        cpu_percent = self.get_cpu_usage(process.pid)
        if cpu_percent > self.cpu_limit_percent:
            self.handle_cpu_exceeded(process)
            
        # Check runtime
        if self.get_runtime(process) > self.timeout:
            self.handle_timeout(process)
            
        time.sleep(self.monitor_interval)
```

#### Terminating Processes
```python
def terminate_process_tree(self, pid: int):
    """Terminate process and all children"""
    try:
        if platform.system() == 'Windows':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)])
        else:
            # Kill process group
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            
            # Wait for graceful shutdown
            time.sleep(1)
            
            # Force kill if still running
            if self.is_process_running(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception as e:
        logger.error(f"Failed to terminate process tree: {e}")
```

## Agent Subprocess Architecture

### Parallel Agent Execution

```python
class AgentExecutor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_agents = {}
        
    def execute_agents(self, delegations: List[Delegation]):
        futures = []
        
        for delegation in delegations:
            future = self.executor.submit(
                self.run_agent,
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
                results.append(AgentResult(
                    agent=delegation.agent_type,
                    task=delegation.task,
                    output=result,
                    success=True
                ))
            except Exception as e:
                results.append(AgentResult(
                    agent=delegation.agent_type,
                    task=delegation.task,
                    error=str(e),
                    success=False
                ))
                
        return results
```

### Agent Process Isolation

Each agent runs in complete isolation:

```python
def run_agent(self, agent_type: str, task: str, context: dict):
    # Create isolated environment
    env = self.create_agent_environment(agent_type)
    
    # Prepare agent command
    cmd = [
        sys.executable,
        '-m', 'claude_mpm.agents.runner',
        '--agent', agent_type,
        '--framework', self.get_agent_framework(agent_type)
    ]
    
    # Create subprocess with limits
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=self.get_agent_workspace(agent_type),
        preexec_fn=self.set_resource_limits
    )
    
    # Send task and context
    input_data = json.dumps({
        'task': task,
        'context': context
    })
    
    # Execute with timeout
    try:
        stdout, stderr = process.communicate(
            input=input_data,
            timeout=300
        )
        return self.parse_agent_output(stdout)
    except subprocess.TimeoutExpired:
        process.kill()
        raise AgentTimeoutError(f"{agent_type} exceeded time limit")
```

## Resource Management

### Memory Limits

```python
def set_resource_limits():
    """Set resource limits for subprocess"""
    if platform.system() != 'Windows':
        import resource
        
        # Limit memory to 512MB
        resource.setrlimit(
            resource.RLIMIT_AS,
            (512 * 1024 * 1024, 512 * 1024 * 1024)
        )
        
        # Limit CPU time to 5 minutes
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (300, 300)
        )
        
        # Limit number of open files
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (256, 256)
        )
```

### Process Monitoring

```python
class ProcessMonitor:
    def get_process_info(self, pid: int) -> dict:
        try:
            import psutil
            process = psutil.Process(pid)
            
            return {
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections()),
                'children': [p.pid for p in process.children()]
            }
        except Exception:
            return {}
```

## Error Handling

### Subprocess Errors

```python
class SubprocessErrorHandler:
    def handle_error(self, process: Process, error: Exception):
        error_type = type(error).__name__
        
        handlers = {
            'TimeoutExpired': self.handle_timeout,
            'CalledProcessError': self.handle_command_error,
            'OSError': self.handle_os_error,
            'MemoryError': self.handle_memory_error
        }
        
        handler = handlers.get(error_type, self.handle_generic_error)
        return handler(process, error)
        
    def handle_timeout(self, process: Process, error: Exception):
        # Kill process tree
        self.terminate_process_tree(process.pid)
        
        # Log details
        logger.error(f"Process timeout: {error}")
        
        # Return timeout result
        return ProcessResult(
            success=False,
            error="Process exceeded time limit",
            timeout=True
        )
```

### Recovery Strategies

```python
class ProcessRecovery:
    def recover_from_crash(self, process_info: dict):
        strategies = [
            self.restart_process,
            self.use_fallback,
            self.notify_user
        ]
        
        for strategy in strategies:
            if strategy(process_info):
                return True
                
        return False
        
    def restart_process(self, process_info: dict) -> bool:
        if process_info['restart_count'] < 3:
            logger.info("Attempting process restart...")
            return self.start_process(process_info['cmd'])
        return False
```

## Security Considerations

### Command Injection Prevention

```python
def validate_command(self, cmd: List[str]):
    """Validate command to prevent injection"""
    # Whitelist allowed commands
    allowed_commands = ['claude', 'python', 'node']
    
    if not cmd or cmd[0] not in allowed_commands:
        raise SecurityError(f"Command not allowed: {cmd[0]}")
        
    # Validate arguments
    for arg in cmd[1:]:
        if any(char in arg for char in ['|', '&', ';', '$', '`']):
            raise SecurityError(f"Dangerous character in argument: {arg}")
```

### Environment Isolation

```python
def create_safe_environment(self, base_env: dict) -> dict:
    """Create isolated environment for subprocess"""
    # Start with minimal environment
    safe_env = {
        'PATH': self.get_safe_path(),
        'HOME': self.get_sandbox_home(),
        'TEMP': self.get_sandbox_temp(),
        'TMP': self.get_sandbox_temp()
    }
    
    # Add allowed variables
    allowed_vars = ['CLAUDE_API_KEY', 'PYTHONPATH']
    for var in allowed_vars:
        if var in base_env:
            safe_env[var] = base_env[var]
            
    return safe_env
```

## Performance Optimizations

### Stream Buffering

```python
class StreamBuffer:
    def __init__(self, max_size=1024*1024):  # 1MB
        self.buffer = []
        self.size = 0
        self.max_size = max_size
        
    def add(self, data: str):
        data_size = len(data.encode('utf-8'))
        
        if self.size + data_size > self.max_size:
            self.flush()
            
        self.buffer.append(data)
        self.size += data_size
        
    def flush(self) -> str:
        result = ''.join(self.buffer)
        self.buffer = []
        self.size = 0
        return result
```

### Process Pool

```python
class ProcessPool:
    def __init__(self, size=4):
        self.size = size
        self.available = queue.Queue()
        self.all_processes = []
        
        # Pre-create processes
        for _ in range(size):
            process = self.create_worker_process()
            self.available.put(process)
            self.all_processes.append(process)
            
    def get_process(self) -> Process:
        try:
            return self.available.get(timeout=30)
        except queue.Empty:
            raise ResourceError("No available processes")
            
    def return_process(self, process: Process):
        if process.poll() is None:  # Still running
            self.available.put(process)
        else:
            # Replace dead process
            new_process = self.create_worker_process()
            self.available.put(new_process)
            self.all_processes.append(new_process)
```

## Testing Subprocess Behavior

### Mock Subprocess for Testing

```python
class MockProcess:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.stdin = io.StringIO()
        self.returncode = returncode
        self.pid = 12345
        
    def poll(self):
        return self.returncode
        
    def communicate(self, input=None, timeout=None):
        if input:
            self.stdin.write(input)
        return self.stdout.read(), self.stderr.read()
```

### Integration Testing

```python
def test_subprocess_lifecycle():
    # Create orchestrator
    orchestrator = SubprocessOrchestrator()
    
    # Start subprocess
    orchestrator.start()
    assert orchestrator.is_running()
    
    # Send message
    orchestrator.send_message("Test message")
    
    # Read response
    response = orchestrator.read_response()
    assert "Test" in response
    
    # Stop subprocess
    orchestrator.stop()
    assert not orchestrator.is_running()
```

## Debugging Tips

### Enable Subprocess Logging

```python
# Set environment variable
export CLAUDE_MPM_SUBPROCESS_DEBUG=true

# Or in code
os.environ['CLAUDE_MPM_SUBPROCESS_DEBUG'] = 'true'
```

### Monitor Process Tree

```bash
# Watch process tree
watch -n 1 'ps aux | grep claude'

# Monitor specific process
strace -p <pid> -f

# Check file descriptors
lsof -p <pid>
```

### Analyze Stream Data

```python
# Log all I/O
class DebugOrchestrator(SubprocessOrchestrator):
    def send_to_claude(self, message: str):
        logger.debug(f"SEND: {message}")
        super().send_to_claude(message)
        
    def read_from_claude(self):
        output = super().read_from_claude()
        logger.debug(f"RECV: {output}")
        return output
```