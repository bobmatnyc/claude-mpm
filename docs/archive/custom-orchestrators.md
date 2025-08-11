# Creating Custom Orchestrators

This guide explains how to create custom orchestrators for Claude MPM to implement new subprocess management strategies or integrate with different execution environments.

## Overview

Orchestrators are responsible for:
- Launching and managing Claude subprocesses
- Handling I/O between the user and Claude
- Injecting framework instructions
- Managing session lifecycle
- Extracting tickets and delegations

## Base Orchestrator

All custom orchestrators should inherit from `MPMOrchestrator`:

```python
from claude_mpm.orchestration.orchestrator import MPMOrchestrator

class CustomOrchestrator(MPMOrchestrator):
    """Your custom orchestrator implementation."""
    pass
```

## Required Methods

### Core Lifecycle Methods

#### start()

```python
def start(self) -> bool:
    """
    Start the orchestrated Claude session.
    
    Returns:
        True if successfully started, False otherwise
    """
    # Your implementation
    return super().start()
```

#### stop()

```python
def stop(self):
    """Stop the orchestrated session."""
    # Custom cleanup
    
    # Call parent implementation
    super().stop()
```

### I/O Methods

These methods are typically inherited but can be overridden:

```python
def send_input(self, text: str):
    """Send input to Claude."""
    # Custom preprocessing
    super().send_input(text)

def get_output(self, timeout: float = 0.1) -> Optional[str]:
    """Get output from Claude."""
    return super().get_output(timeout)
```

## Customization Points

### 1. Process Launch Strategy

Override the process launch logic:

```python
class DockerOrchestrator(MPMOrchestrator):
    """Run Claude in a Docker container."""
    
    def start(self) -> bool:
        try:
            # Build docker command
            cmd = [
                "docker", "run",
                "-it",
                "--rm",
                "claude-image",
                "claude",
                "--model", "opus"
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Start I/O threads
            self.running = True
            self._start_io_threads()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Docker: {e}")
            return False
```

### 2. Output Processing

Customize how output is processed:

```python
def _process_output_line(self, line: str):
    """Process a line of output from Claude."""
    # Custom processing
    if self._is_special_output(line):
        self._handle_special_output(line)
    
    # Continue with default processing
    super()._process_output_line(line)

def _is_special_output(self, line: str) -> bool:
    """Check if line contains special markers."""
    return "CUSTOM_MARKER" in line

def _handle_special_output(self, line: str):
    """Handle special output."""
    # Your logic here
    pass
```

### 3. Input Injection

Modify input before sending to Claude:

```python
def send_input(self, text: str):
    """Send input with custom preprocessing."""
    # Add custom prefix
    if self.add_prefix:
        text = f"[CUSTOM] {text}"
    
    # Transform input
    text = self._transform_input(text)
    
    # Send to parent
    super().send_input(text)

def _transform_input(self, text: str) -> str:
    """Transform user input."""
    # Your transformation logic
    return text.upper()  # Example: convert to uppercase
```

### 4. Session Management

Add custom session handling:

```python
class SessionOrchestrator(MPMOrchestrator):
    """Orchestrator with enhanced session management."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = self._generate_session_id()
        self.session_metadata = {}
    
    def start(self) -> bool:
        """Start with session tracking."""
        if super().start():
            self._initialize_session()
            return True
        return False
    
    def _initialize_session(self):
        """Initialize session tracking."""
        self.session_metadata.update({
            "start_time": datetime.now(),
            "user": os.getenv("USER"),
            "pid": self.process.pid
        })
    
    def stop(self):
        """Stop with session finalization."""
        self._finalize_session()
        super().stop()
    
    def _finalize_session(self):
        """Finalize session data."""
        self.session_metadata["end_time"] = datetime.now()
        self._save_session_metadata()
```

## Complete Example: Remote Orchestrator

Here's a complete example of an orchestrator that connects to a remote Claude instance:

```python
import socket
import json
from claude_mpm.orchestration.orchestrator import MPMOrchestrator

class RemoteOrchestrator(MPMOrchestrator):
    """Orchestrator for remote Claude instances."""
    
    def __init__(self, host: str, port: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.socket = None
    
    def start(self) -> bool:
        """Connect to remote Claude."""
        try:
            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Send initialization
            init_msg = {
                "type": "init",
                "model": "opus",
                "framework": self.framework_loader.get_framework_instructions()
            }
            self._send_message(init_msg)
            
            # Start receiver thread
            self.running = True
            self.receiver_thread = threading.Thread(
                target=self._receive_messages,
                daemon=True
            )
            self.receiver_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def send_input(self, text: str):
        """Send input to remote Claude."""
        msg = {
            "type": "input",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        self._send_message(msg)
    
    def _send_message(self, msg: dict):
        """Send JSON message over socket."""
        data = json.dumps(msg).encode() + b'\n'
        self.socket.sendall(data)
    
    def _receive_messages(self):
        """Receive messages from remote Claude."""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self._handle_message(json.loads(line))
                        
            except Exception as e:
                self.logger.error(f"Receive error: {e}")
                break
    
    def _handle_message(self, msg: dict):
        """Handle received message."""
        if msg["type"] == "output":
            self._process_output_line(msg["text"])
        elif msg["type"] == "error":
            self.logger.error(f"Remote error: {msg['error']}")
    
    def stop(self):
        """Disconnect from remote Claude."""
        self.running = False
        
        if self.socket:
            try:
                # Send termination message
                self._send_message({"type": "terminate"})
                self.socket.close()
            except:
                pass
        
        super().stop()
```

## Testing Custom Orchestrators

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

class TestCustomOrchestrator:
    def test_start(self):
        orchestrator = CustomOrchestrator()
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process
            
            assert orchestrator.start() == True
            assert orchestrator.process == mock_process
    
    def test_output_processing(self):
        orchestrator = CustomOrchestrator()
        orchestrator.custom_handler = Mock()
        
        orchestrator._process_output_line("CUSTOM_MARKER: test")
        
        orchestrator.custom_handler.assert_called_once()
```

### Integration Testing

```python
def test_full_session():
    orchestrator = CustomOrchestrator(log_level="DEBUG")
    
    try:
        assert orchestrator.start()
        
        # Send test input
        orchestrator.send_input("Hello, Claude!")
        
        # Wait for response
        import time
        time.sleep(2)
        
        # Check output
        output = orchestrator.get_output(timeout=1.0)
        assert output is not None
        
    finally:
        orchestrator.stop()
```

## Configuration

Make your orchestrator configurable:

```python
class ConfigurableOrchestrator(MPMOrchestrator):
    """Orchestrator with configuration support."""
    
    def __init__(self, config: Dict[str, Any], *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load configuration
        self.retry_attempts = config.get("retry_attempts", 3)
        self.timeout = config.get("timeout", 300)
        self.custom_flags = config.get("custom_flags", [])
    
    def start(self) -> bool:
        """Start with retry logic."""
        for attempt in range(self.retry_attempts):
            if super().start():
                return True
            
            self.logger.warning(f"Start attempt {attempt + 1} failed")
            time.sleep(2 ** attempt)  # Exponential backoff
        
        return False
```

## Error Handling

Implement robust error handling:

```python
class RobustOrchestrator(MPMOrchestrator):
    """Orchestrator with enhanced error handling."""
    
    def _output_reader(self):
        """Read output with error recovery."""
        consecutive_errors = 0
        max_errors = 5
        
        while self.running and consecutive_errors < max_errors:
            try:
                line = self.process.stdout.readline()
                if line:
                    consecutive_errors = 0  # Reset on success
                    self._process_output_line(line.rstrip())
                    
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Output error ({consecutive_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    self.logger.critical("Too many errors, stopping")
                    self.stop()
                else:
                    time.sleep(0.5)  # Brief pause before retry
```

## Performance Optimization

### Buffering

```python
class BufferedOrchestrator(MPMOrchestrator):
    """Orchestrator with output buffering."""
    
    def __init__(self, *args, buffer_size: int = 100, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer_size = buffer_size
        self.output_buffer = []
    
    def _process_output_line(self, line: str):
        """Buffer output for batch processing."""
        self.output_buffer.append(line)
        
        if len(self.output_buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Process buffered output."""
        # Batch process all lines
        for line in self.output_buffer:
            super()._process_output_line(line)
        
        self.output_buffer.clear()
```

### Async I/O

```python
import asyncio

class AsyncOrchestrator(MPMOrchestrator):
    """Orchestrator with async I/O."""
    
    async def start_async(self) -> bool:
        """Async start method."""
        if self.start():
            await self._setup_async_io()
            return True
        return False
    
    async def _setup_async_io(self):
        """Set up async I/O handling."""
        self.read_task = asyncio.create_task(self._async_reader())
        self.write_task = asyncio.create_task(self._async_writer())
    
    async def _async_reader(self):
        """Async output reader."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        await self.loop.connect_read_pipe(
            lambda: protocol,
            self.process.stdout
        )
        
        while self.running:
            line = await reader.readline()
            if line:
                self._process_output_line(line.decode().rstrip())
```

## Best Practices

1. **Always call parent methods** when overriding unless completely replacing functionality
2. **Handle subprocess lifecycle** properly - ensure processes are cleaned up
3. **Use logging** appropriately - don't log sensitive information
4. **Make it configurable** - avoid hardcoded values
5. **Document behavior** - especially deviations from base orchestrator
6. **Test thoroughly** - including error conditions and edge cases
7. **Consider performance** - especially for I/O intensive operations

## Registration

Register your orchestrator with the factory:

```python
# In your package's __init__.py or setup.py
from claude_mpm.orchestration.factory import register_orchestrator
from .custom_orchestrator import CustomOrchestrator

register_orchestrator("custom", CustomOrchestrator)
```

Users can then use your orchestrator:

```bash
claude-mpm --orchestrator custom
```

---

**Note**: This documentation is archived as orchestration features have been removed from the current version of Claude MPM. This reference is maintained for historical purposes and migration guidance.