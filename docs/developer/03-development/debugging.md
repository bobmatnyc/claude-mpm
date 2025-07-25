# Debugging Guide

This guide provides comprehensive debugging techniques for Claude MPM, focusing on the unique challenges of debugging multi-process orchestration systems.

## Debugging Overview

Debugging Claude MPM involves:
- **Subprocess Debugging**: Tracing subprocess execution and I/O
- **Async Debugging**: Handling concurrent operations
- **Pattern Detection**: Debugging regex and pattern matching
- **Performance Analysis**: Identifying bottlenecks
- **Memory Debugging**: Finding leaks and excessive usage

## Debug Configuration

### Environment Variables

```bash
# Enable all debug output
export CLAUDE_MPM_DEBUG=true

# Subprocess debugging
export CLAUDE_MPM_SUBPROCESS_DEBUG=true

# Hook debugging  
export CLAUDE_MPM_HOOK_DEBUG=true

# Agent debugging
export CLAUDE_MPM_AGENT_DEBUG=true

# Pattern detection debugging
export CLAUDE_MPM_PATTERN_DEBUG=true

# Log level
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Log to file
export CLAUDE_MPM_LOG_FILE=/tmp/claude-mpm-debug.log
```

### Debug Configuration File

```yaml
# .claude-pm/config/debug.yaml
debug:
  enabled: true
  log_level: DEBUG
  
  # Component-specific debugging
  components:
    orchestrator: true
    agents: true
    hooks: true
    patterns: true
    tickets: true
  
  # Output settings
  output:
    console: true
    file: true
    file_path: ./debug.log
    include_timestamps: true
    include_thread_info: true
    
  # Performance profiling
  profiling:
    enabled: true
    profile_file: ./profile.stats
```

## Subprocess Debugging

### Tracing Subprocess Execution

```python
# Enable subprocess tracing
import subprocess
import sys

class DebugSubprocessOrchestrator(SubprocessOrchestrator):
    """Orchestrator with enhanced debugging."""
    
    def start(self):
        """Start subprocess with debugging."""
        cmd = self.launcher.build_command()
        
        # Log full command
        logger.debug(f"Starting subprocess: {' '.join(cmd)}")
        logger.debug(f"Environment: {self.env}")
        
        # Use strace on Linux/Mac for system call tracing
        if sys.platform != 'win32' and self.config.get('strace'):
            cmd = ['strace', '-f', '-o', 'strace.log'] + cmd
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env=self.env
        )
        
        logger.debug(f"Process started with PID: {self.process.pid}")
```

### Debugging I/O Streams

```python
class IODebugger:
    """Debug I/O stream communication."""
    
    def __init__(self, stream_name: str):
        self.stream_name = stream_name
        self.log_file = open(f"{stream_name}_debug.log", 'w')
    
    def wrap_stream(self, stream):
        """Wrap a stream to log all data."""
        class DebugStream:
            def write(self, data):
                # Log to file
                self.log_file.write(f"[{datetime.now()}] WRITE: {repr(data)}\n")
                self.log_file.flush()
                
                # Write to actual stream
                return stream.write(data)
            
            def read(self, size=-1):
                data = stream.read(size)
                
                # Log to file
                self.log_file.write(f"[{datetime.now()}] READ: {repr(data)}\n")
                self.log_file.flush()
                
                return data
            
            def readline(self):
                line = stream.readline()
                
                # Log to file
                self.log_file.write(f"[{datetime.now()}] READLINE: {repr(line)}\n")
                self.log_file.flush()
                
                return line
        
        return DebugStream()

# Usage
stdin_debugger = IODebugger("stdin")
process.stdin = stdin_debugger.wrap_stream(process.stdin)
```

### Process Tree Visualization

```python
def visualize_process_tree(pid: int):
    """Visualize process tree for debugging."""
    try:
        import psutil
        
        def print_tree(proc, indent=0):
            try:
                info = proc.as_dict(['pid', 'name', 'status', 'cpu_percent', 'memory_info'])
                print(f"{'  ' * indent}├─ PID {info['pid']}: {info['name']} "
                      f"[{info['status']}] CPU: {info['cpu_percent']}% "
                      f"MEM: {info['memory_info'].rss / 1024 / 1024:.1f}MB")
                
                for child in proc.children():
                    print_tree(child, indent + 1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        root = psutil.Process(pid)
        print(f"Process tree for PID {pid}:")
        print_tree(root)
        
    except ImportError:
        print("Install psutil for process tree visualization")

# Usage during debugging
visualize_process_tree(orchestrator.process.pid)
```

## Pattern Debugging

### Pattern Detection Debugging

```python
class DebugPatternDetector(PatternDetector):
    """Pattern detector with debugging capabilities."""
    
    def detect_patterns(self, text: str) -> List[Pattern]:
        """Detect patterns with detailed logging."""
        logger.debug(f"Detecting patterns in text: {text[:100]}...")
        
        patterns = []
        
        for pattern_name, pattern_config in self.PATTERNS.items():
            regex = pattern_config['regex']
            logger.debug(f"Testing pattern '{pattern_name}': {regex}")
            
            matches = list(re.finditer(regex, text))
            
            if matches:
                logger.debug(f"  Found {len(matches)} matches")
                for i, match in enumerate(matches):
                    logger.debug(f"    Match {i}: {repr(match.group(0))}")
                    logger.debug(f"    Groups: {match.groups()}")
                    logger.debug(f"    Position: {match.span()}")
            else:
                logger.debug(f"  No matches found")
        
        return patterns
```

### Regex Testing Tool

```python
def test_regex_pattern(pattern: str, test_cases: List[str]):
    """Test regex pattern against multiple cases."""
    print(f"Testing pattern: {pattern}")
    print("-" * 50)
    
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        print(f"ERROR: Invalid regex: {e}")
        return
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i + 1}: {repr(test)}")
        
        # Find all matches
        matches = list(compiled.finditer(test))
        
        if matches:
            print(f"  ✓ {len(matches)} match(es)")
            for match in matches:
                print(f"    Full match: {repr(match.group(0))}")
                if match.groups():
                    for j, group in enumerate(match.groups(), 1):
                        print(f"    Group {j}: {repr(group)}")
        else:
            print("  ✗ No match")

# Usage
test_regex_pattern(
    r'\*\*([^*]+)\*\*:\s*(.+)',
    [
        "**Engineer Agent**: Create a function",
        "**QA**: Test the implementation",
        "Regular text without pattern",
        "**Agent Name With Spaces**: Complex task"
    ]
)
```

## Async Debugging

### Debugging Async Operations

```python
import asyncio
import functools

def async_debug(func):
    """Decorator for debugging async functions."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"[ASYNC] Starting {func_name}")
        logger.debug(f"[ASYNC] Args: {args}, Kwargs: {kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"[ASYNC] {func_name} completed successfully")
            logger.debug(f"[ASYNC] Result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[ASYNC] {func_name} failed: {e}")
            raise
    
    return wrapper

# Usage
class AsyncOrchestrator:
    @async_debug
    async def process_message(self, message: str):
        """Process message asynchronously."""
        # Your async code here
        result = await self._send_to_claude(message)
        return result
```

### Async Task Monitoring

```python
class AsyncTaskMonitor:
    """Monitor async tasks for debugging."""
    
    def __init__(self):
        self.tasks = {}
    
    def create_task(self, coro, name: str):
        """Create and monitor a task."""
        task = asyncio.create_task(coro)
        
        self.tasks[task] = {
            'name': name,
            'created_at': time.time(),
            'status': 'running'
        }
        
        task.add_done_callback(self._task_done)
        
        logger.debug(f"Created task '{name}' (ID: {id(task)})")
        return task
    
    def _task_done(self, task):
        """Handle task completion."""
        info = self.tasks.get(task, {})
        name = info.get('name', 'unknown')
        duration = time.time() - info.get('created_at', 0)
        
        if task.cancelled():
            logger.warning(f"Task '{name}' was cancelled after {duration:.2f}s")
            info['status'] = 'cancelled'
        elif task.exception():
            logger.error(f"Task '{name}' failed after {duration:.2f}s: {task.exception()}")
            info['status'] = 'failed'
        else:
            logger.debug(f"Task '{name}' completed after {duration:.2f}s")
            info['status'] = 'completed'
    
    def get_status(self):
        """Get status of all tasks."""
        return {
            'total': len(self.tasks),
            'running': sum(1 for t in self.tasks.values() if t['status'] == 'running'),
            'completed': sum(1 for t in self.tasks.values() if t['status'] == 'completed'),
            'failed': sum(1 for t in self.tasks.values() if t['status'] == 'failed'),
            'cancelled': sum(1 for t in self.tasks.values() if t['status'] == 'cancelled')
        }
```

## Performance Debugging

### CPU Profiling

```python
import cProfile
import pstats
from pstats import SortKey

def profile_function(func):
    """Decorator to profile function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            
            # Save to file
            profiler.dump_stats(f"{func.__name__}_profile.stats")
            
            # Print summary
            stats = pstats.Stats(profiler)
            stats.strip_dirs()
            stats.sort_stats(SortKey.CUMULATIVE)
            
            print(f"\nProfile for {func.__name__}:")
            stats.print_stats(20)  # Top 20 functions
    
    return wrapper

# Usage
@profile_function
def expensive_operation():
    # Your code here
    pass
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Function to profile for memory usage."""
    # Allocate large list
    big_list = [i for i in range(1000000)]
    
    # Process data
    processed = [x * 2 for x in big_list]
    
    # Clear references
    del big_list
    
    return len(processed)

# Run with: python -m memory_profiler script.py
```

### Performance Monitoring

```python
class PerformanceMonitor:
    """Monitor performance metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    @contextmanager
    def measure(self, operation: str):
        """Measure operation performance."""
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            self.metrics[operation].append({
                'duration': duration,
                'memory_delta': memory_delta,
                'timestamp': time.time()
            })
            
            logger.debug(f"[PERF] {operation}: {duration:.3f}s, "
                        f"Memory: {memory_delta:+.1f}MB")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def get_summary(self):
        """Get performance summary."""
        summary = {}
        
        for operation, measurements in self.metrics.items():
            durations = [m['duration'] for m in measurements]
            memory_deltas = [m['memory_delta'] for m in measurements]
            
            summary[operation] = {
                'count': len(measurements),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'avg_memory': sum(memory_deltas) / len(memory_deltas),
                'max_memory': max(memory_deltas)
            }
        
        return summary

# Usage
monitor = PerformanceMonitor()

with monitor.measure('subprocess_creation'):
    orchestrator.start()

with monitor.measure('message_processing'):
    orchestrator.send_message("Test")
    response = orchestrator.receive_output()

print(monitor.get_summary())
```

## Interactive Debugging

### Using PDB

```python
import pdb

def debug_orchestrator():
    """Debug orchestrator interactively."""
    orchestrator = SubprocessOrchestrator(launcher, config)
    
    # Set breakpoint
    pdb.set_trace()
    
    # Now you can inspect:
    # (Pdb) orchestrator.config
    # (Pdb) orchestrator.process
    # (Pdb) step
    
    orchestrator.start()
```

### IPython Debugging

```python
from IPython import embed

def debug_with_ipython():
    """Use IPython for interactive debugging."""
    orchestrator = create_orchestrator()
    patterns = detect_patterns(text)
    
    # Drop into IPython shell
    embed()
    
    # Now you have full IPython features:
    # In [1]: orchestrator?
    # In [2]: %timeit detect_patterns(text)
    # In [3]: %debug
```

### Remote Debugging

```python
# For VS Code
import debugpy

# Start debug server
debugpy.listen(5678)
print("Waiting for debugger attach...")
debugpy.wait_for_client()
debugpy.breakpoint()

# Now attach VS Code debugger to port 5678
```

## Logging Best Practices

### Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Use structured logging
logger.info("subprocess_started",
    pid=process.pid,
    command=cmd,
    timeout=timeout
)

logger.error("pattern_detection_failed",
    pattern=pattern_name,
    text=text[:50],
    error=str(e),
    exc_info=True
)
```

### Debug Log Analysis

```python
def analyze_debug_logs(log_file: str):
    """Analyze debug logs for common issues."""
    
    issues = {
        'timeouts': [],
        'errors': [],
        'warnings': [],
        'slow_operations': [],
        'memory_spikes': []
    }
    
    with open(log_file) as f:
        for line in f:
            # Check for timeouts
            if 'timeout' in line.lower():
                issues['timeouts'].append(line.strip())
            
            # Check for errors
            if 'ERROR' in line:
                issues['errors'].append(line.strip())
            
            # Check for slow operations
            if match := re.search(r'duration: (\d+\.\d+)s', line):
                duration = float(match.group(1))
                if duration > 5.0:
                    issues['slow_operations'].append((duration, line.strip()))
            
            # Check for memory issues
            if match := re.search(r'Memory: \+(\d+\.\d+)MB', line):
                memory = float(match.group(1))
                if memory > 100:
                    issues['memory_spikes'].append((memory, line.strip()))
    
    # Report findings
    print("Debug Log Analysis")
    print("=" * 50)
    
    for issue_type, items in issues.items():
        if items:
            print(f"\n{issue_type.upper()} ({len(items)} found):")
            for item in items[:5]:  # Show first 5
                if isinstance(item, tuple):
                    print(f"  - {item[0]}: {item[1][:100]}...")
                else:
                    print(f"  - {item[:100]}...")
```

## Common Issues and Solutions

### Issue: Subprocess Hangs

```python
# Debug hanging subprocess
def debug_hanging_subprocess(process):
    """Debug a hanging subprocess."""
    
    # Check if process is alive
    if process.poll() is None:
        print(f"Process {process.pid} is still running")
        
        # Check CPU usage
        import psutil
        try:
            proc = psutil.Process(process.pid)
            print(f"CPU: {proc.cpu_percent()}%")
            print(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f}MB")
            print(f"Threads: {proc.num_threads()}")
            
            # Check what it's doing
            print(f"Status: {proc.status()}")
            
            # On Linux/Mac, check open files
            if hasattr(proc, 'open_files'):
                print(f"Open files: {len(proc.open_files())}")
                for f in proc.open_files()[:5]:
                    print(f"  - {f.path}")
            
        except psutil.NoSuchProcess:
            print("Process no longer exists")
    
    # Try reading any pending output
    try:
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        print(f"Pending stdout: {stdout}")
        print(f"Pending stderr: {stderr}")
    except:
        print("Could not read pending output")
```

### Issue: Pattern Not Matching

```python
def debug_pattern_matching(pattern: str, text: str):
    """Debug why a pattern isn't matching."""
    
    print(f"Pattern: {repr(pattern)}")
    print(f"Text: {repr(text[:200])}...")
    print("-" * 50)
    
    # Try different regex flags
    flags = [
        (0, "No flags"),
        (re.IGNORECASE, "IGNORECASE"),
        (re.MULTILINE, "MULTILINE"),
        (re.DOTALL, "DOTALL"),
        (re.IGNORECASE | re.MULTILINE, "IGNORECASE + MULTILINE")
    ]
    
    for flag, flag_name in flags:
        try:
            regex = re.compile(pattern, flag)
            matches = list(regex.finditer(text))
            
            if matches:
                print(f"✓ Matches with {flag_name}: {len(matches)} found")
                for i, match in enumerate(matches[:3]):
                    print(f"  Match {i+1}: {repr(match.group(0))}")
            else:
                print(f"✗ No match with {flag_name}")
                
        except re.error as e:
            print(f"✗ Error with {flag_name}: {e}")
    
    # Check for common issues
    print("\nCommon issues to check:")
    if '\\n' in text and not (re.MULTILINE in [f[0] for f in flags]):
        print("- Text contains newlines, try MULTILINE flag")
    if '.' in pattern and '\n' in text:
        print("- Pattern has '.' which doesn't match newlines by default")
    if text.strip() != text:
        print("- Text has leading/trailing whitespace")
```

### Issue: Memory Leak

```python
import gc
import tracemalloc

def debug_memory_leak():
    """Debug memory leaks."""
    
    # Start tracing
    tracemalloc.start()
    
    # Take snapshot before
    snapshot1 = tracemalloc.take_snapshot()
    
    # Run suspicious code
    for i in range(100):
        orchestrator = SubprocessOrchestrator(launcher, config)
        orchestrator.start()
        orchestrator.stop()
    
    # Force garbage collection
    gc.collect()
    
    # Take snapshot after
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("Top 10 memory allocations:")
    for stat in top_stats[:10]:
        print(stat)
    
    # Check for uncollectable objects
    gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()
    
    print(f"\nGarbage collector stats:")
    for i, count in enumerate(gc.get_count()):
        print(f"  Generation {i}: {count} objects")
```

## Debug Commands

### Command-Line Debugging

```bash
# Run with maximum debugging
./claude-mpm --debug \
  --log-level DEBUG \
  --trace-subprocess \
  --profile \
  run -i "test"

# Debug specific component
./claude-mpm --debug-component orchestrator

# Save debug output
./claude-mpm --debug 2>&1 | tee debug.log

# Debug with strace (Linux/Mac)
strace -f -o strace.log ./claude-mpm

# Debug with Python trace
python -m trace -t -s claude-mpm
```

### Debug REPL

```python
# Create debug REPL script
# debug_repl.py
import code
from claude_mpm.core import ClaudeLauncher
from claude_mpm.orchestration import SubprocessOrchestrator

# Create components
launcher = ClaudeLauncher()
orchestrator = SubprocessOrchestrator(launcher, {})

# Start interactive session
code.interact(local=locals(), banner="""
Claude MPM Debug REPL
Available objects:
  - launcher: ClaudeLauncher instance
  - orchestrator: SubprocessOrchestrator instance
  
Try:
  >>> orchestrator.start()
  >>> orchestrator.send_message("Hello")
""")
```

## VS Code Debug Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Claude MPM",
            "type": "python",
            "request": "launch",
            "module": "claude_mpm.cli_main",
            "args": ["--debug", "run", "-i", "test prompt"],
            "env": {
                "CLAUDE_MPM_DEBUG": "true",
                "CLAUDE_MPM_SUBPROCESS_DEBUG": "true"
            },
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Attach to Process",
            "type": "python",
            "request": "attach",
            "port": 5678,
            "host": "localhost"
        }
    ]
}
```

## Next Steps

1. Set up [logging configuration](setup.md#environment-configuration)
2. Review [testing strategies](testing.md) for test-driven debugging
3. Learn about [performance optimization](../01-architecture/patterns.md#performance-optimizations)
4. Contribute debugging improvements back to the project