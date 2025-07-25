# Data Flow

This document describes how data flows through the Claude MPM system, from user input to final output, including all transformations and decision points.

## Overview

Claude MPM's data flow follows a pipeline architecture where each stage can transform, analyze, or redirect the data based on patterns and configurations.

## Primary Data Flow

### 1. User Input Flow

```
User Types Message
        │
        ▼
┌──────────────────┐
│ Terminal Input   │
│ (stdin/readline) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ CLI Input Handler│
│ - Validate input │
│ - Check commands │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Pre-Message Hooks│
│ - Transform input│
│ - Add metadata   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Orchestrator     │
│ - Queue message  │
│ - Add framework  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Claude Process   │
│ (subprocess)     │
└──────────────────┘
```

### 2. Claude Processing Flow

```
Message Received by Claude
         │
         ▼
┌──────────────────────┐
│ Framework Processing │
│ - Parse instructions │
│ - Identify role      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Task Analysis        │
│ - Decompose request  │
│ - Plan approach      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Response Generation  │
│ - Create delegations │
│ - Format output      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Stream Output        │
│ (stdout)             │
└──────────────────────┘
```

### 3. Response Processing Flow

```
Claude Output Stream
         │
         ▼
┌──────────────────────┐
│ Output Buffer        │
│ - Line buffering     │
│ - Overflow handling  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Pattern Detection    │
│ - Regex matching     │
│ - Pattern priority   │
└──────────┬───────────┘
           │
     ┌─────┴─────┬──────────┬──────────┐
     ▼           ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌────────┐ ┌────────┐
│ Tickets │ │Delegates│ │ Errors │ │ Normal │
└─────────┘ └─────────┘ └────────┘ └────────┘
     │           │          │          │
     ▼           ▼          ▼          ▼
┌──────────────────────────────────────────┐
│         Action Dispatcher                │
└──────────────────────────────────────────┘
```

## Detailed Data Transformations

### Input Transformation Pipeline

```python
# 1. Raw Input
user_input = "Create a Python function to calculate fibonacci"

# 2. CLI Processing
message = {
    'content': user_input,
    'timestamp': datetime.now(),
    'session_id': session.id,
    'user': os.getenv('USER')
}

# 3. Hook Enhancement
message = {
    **message,
    'metadata': {
        'hooks_applied': ['input_validator', 'context_enhancer'],
        'original_length': len(user_input)
    }
}

# 4. Framework Injection
enhanced_message = f"""
{FRAMEWORK_INSTRUCTIONS}

User: {message['content']}
"""

# 5. Final Message to Claude
final_message = {
    'role': 'user',
    'content': enhanced_message,
    'metadata': message['metadata']
}
```

### Output Transformation Pipeline

```python
# 1. Raw Claude Output
raw_output = """
I'll help you create a Python function to calculate Fibonacci numbers.

**Engineer Agent**: Create a Python function that calculates the nth Fibonacci number with both recursive and iterative implementations.

Here's what I'll implement:
1. Recursive approach (simple but inefficient)
2. Iterative approach (more efficient)
3. Memoized approach (optimal)
"""

# 2. Pattern Detection Results
patterns = [
    {
        'type': 'delegation',
        'agent': 'Engineer Agent',
        'task': 'Create a Python function that calculates...',
        'position': (50, 150)
    }
]

# 3. Action Execution
actions = [
    {
        'type': 'spawn_agent',
        'agent': 'engineer',
        'input': {
            'task': patterns[0]['task'],
            'context': current_context
        }
    }
]

# 4. Response Augmentation
augmented_response = {
    'original': raw_output,
    'patterns': patterns,
    'actions': actions,
    'agent_results': []  # Filled after agent execution
}

# 5. Final Display
formatted_output = format_for_display(augmented_response)
```

## Pattern Detection Data Flow

### Pattern Types and Handlers

```
┌─────────────────────────────────────────┐
│          Pattern Detector               │
├─────────────────────────────────────────┤
│ Input: Raw text line                    │
│ Output: List of detected patterns       │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐      ┌──────────────────┐
│Ticket Pattern│      │Delegation Pattern│
├──────────────┤      ├──────────────────┤
│TODO: .*      │      │\*\*(.+)\*\*: .* │
│BUG: .*       │      │Task\(.*\)       │
│FEATURE: .*   │      │                  │
└──────┬───────┘      └────────┬──────────┘
       │                       │
       ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│Create Ticket │      │ Spawn Agent      │
└──────────────┘      └──────────────────┘
```

### Pattern Processing Pipeline

```python
class PatternProcessor:
    def process_line(self, line: str) -> List[Action]:
        actions = []
        
        # 1. Detect all patterns
        patterns = self.detector.detect_patterns(line)
        
        # 2. Sort by priority
        patterns.sort(key=lambda p: p.priority)
        
        # 3. Process each pattern
        for pattern in patterns:
            # 4. Get handler for pattern type
            handler = self.handlers.get(pattern.type)
            
            # 5. Execute handler
            if handler:
                action = handler.handle(pattern)
                actions.append(action)
                
        # 6. Return all actions
        return actions
```

## Agent Delegation Data Flow

### Delegation Detection and Execution

```
Claude Output with Delegation
            │
            ▼
┌───────────────────────┐
│ Delegation Detector   │
│ - Pattern matching    │
│ - Agent identification│
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Agent Task Extractor  │
│ - Parse task content  │
│ - Extract context     │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Agent Spawner         │
│ - Create subprocess   │
│ - Setup environment   │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Task Executor         │
│ - Send task to agent  │
│ - Monitor execution   │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Result Collector      │
│ - Capture output      │
│ - Format results      │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Result Integration    │
│ - Merge with response │
│ - Update context      │
└───────────────────────┘
```

### Agent Communication Protocol

```python
# 1. Task Message Format
task_message = {
    'version': '1.0',
    'agent': 'engineer',
    'task': {
        'description': 'Create fibonacci function',
        'requirements': ['recursive', 'iterative'],
        'constraints': ['Python 3.8+', 'Type hints']
    },
    'context': {
        'session_id': 'abc123',
        'previous_messages': [...],
        'project_info': {...}
    }
}

# 2. Agent Response Format
agent_response = {
    'version': '1.0',
    'agent': 'engineer',
    'status': 'success',
    'result': {
        'code': '...',
        'explanation': '...',
        'tests': '...'
    },
    'metadata': {
        'execution_time': 2.5,
        'tokens_used': 1500
    }
}

# 3. Error Response Format
error_response = {
    'version': '1.0',
    'agent': 'engineer',
    'status': 'error',
    'error': {
        'type': 'TimeoutError',
        'message': 'Agent execution exceeded 5 minutes',
        'traceback': '...'
    }
}
```

## Session Data Flow

### Session State Management

```
┌─────────────────────────────────────────┐
│            Session Manager              │
├─────────────────────────────────────────┤
│ - Session ID generation                 │
│ - State persistence                     │
│ - Context accumulation                  │
└──────────────┬──────────────────────────┘
               │
     ┌─────────┴─────────┬───────────┐
     ▼                   ▼           ▼
┌──────────┐     ┌──────────┐   ┌──────────┐
│ Message  │     │ Agent    │   │ Ticket   │
│ History  │     │ Results  │   │ Registry │
└──────────┘     └──────────┘   └──────────┘
```

### Session Data Structure

```python
session_data = {
    'id': 'uuid-v4',
    'started_at': datetime.now(),
    'user': 'username',
    'messages': [
        {
            'timestamp': datetime,
            'role': 'user|assistant|system',
            'content': str,
            'metadata': dict
        }
    ],
    'agents_executed': [
        {
            'agent': str,
            'task': str,
            'result': dict,
            'execution_time': float
        }
    ],
    'tickets_created': [
        {
            'id': str,
            'type': 'task|bug|feature',
            'content': str,
            'created_at': datetime
        }
    ],
    'context': {
        'project_path': Path,
        'framework_version': str,
        'active_agents': List[str]
    }
}
```

## Hook System Data Flow

### Hook Execution Pipeline

```
Message/Response
        │
        ▼
┌──────────────────┐
│ Hook Registry    │
│ - Get hooks list │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Hook Executor    │
│ - Sort by order  │
│ - Execute chain  │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Hook 1 │ │ Hook 2 │ ...
└────┬───┘ └───┬────┘
     │         │
     ▼         ▼
┌──────────────────┐
│ Merge Results    │
└────────┬─────────┘
         │
         ▼
Modified Message/Response
```

### Hook Data Transformation

```python
# Hook Chain Example
original_message = "Calculate fibonacci(10)"

# Hook 1: Add context
def context_hook(message):
    return f"[Project: MathUtils] {message}"

# Hook 2: Add timestamp
def timestamp_hook(message):
    return f"[{datetime.now()}] {message}"

# Hook 3: Add user info
def user_hook(message):
    return f"[User: {os.getenv('USER')}] {message}"

# Result after hook chain
# "[User: john] [2024-01-25 10:30:00] [Project: MathUtils] Calculate fibonacci(10)"
```

## Error Handling Data Flow

### Error Propagation

```
Error Occurrence
        │
        ▼
┌──────────────────┐
│ Error Capture    │
│ - Type           │
│ - Context        │
│ - Traceback      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Error Classifier │
│ - Severity       │
│ - Recoverable?   │
└────────┬─────────┘
         │
    ┌────┴────┬────────┐
    ▼         ▼        ▼
┌────────┐ ┌──────┐ ┌──────┐
│Recover │ │ Log  │ │ Halt │
└────────┘ └──────┘ └──────┘
```

### Error Recovery Strategies

```python
class ErrorHandler:
    def handle_error(self, error: Exception, context: dict):
        error_type = type(error).__name__
        
        # 1. Timeout errors - retry with longer timeout
        if error_type == 'TimeoutError':
            return self.retry_with_timeout(context, timeout=600)
            
        # 2. Memory errors - reduce batch size
        elif error_type == 'MemoryError':
            return self.retry_with_reduced_load(context)
            
        # 3. Connection errors - retry with backoff
        elif error_type == 'ConnectionError':
            return self.retry_with_backoff(context)
            
        # 4. Unrecoverable - log and notify
        else:
            self.log_error(error, context)
            self.notify_user(error)
            raise
```

## Performance Optimization Points

### Data Buffering

```python
class OutputBuffer:
    def __init__(self, max_size=1024*1024):  # 1MB
        self.buffer = []
        self.size = 0
        self.max_size = max_size
        
    def add(self, data: str):
        # Check if would exceed buffer
        if self.size + len(data) > self.max_size:
            self.flush()
            
        self.buffer.append(data)
        self.size += len(data)
        
    def flush(self) -> str:
        result = ''.join(self.buffer)
        self.buffer = []
        self.size = 0
        return result
```

### Parallel Processing

```python
# Parallel pattern detection
def detect_patterns_parallel(lines: List[str]) -> List[Pattern]:
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all lines for processing
        futures = [
            executor.submit(detect_patterns, line)
            for line in lines
        ]
        
        # Collect results
        all_patterns = []
        for future in futures:
            patterns = future.result()
            all_patterns.extend(patterns)
            
        return all_patterns
```

### Caching Strategy

```python
class DataCache:
    def __init__(self):
        self.cache = {}
        self.max_entries = 1000
        
    def get_or_compute(self, key: str, compute_func):
        # Check cache
        if key in self.cache:
            return self.cache[key]
            
        # Compute value
        value = compute_func()
        
        # Store in cache (with eviction)
        if len(self.cache) >= self.max_entries:
            # Remove oldest entry
            oldest = min(self.cache.items(), key=lambda x: x[1]['accessed'])
            del self.cache[oldest[0]]
            
        self.cache[key] = {
            'value': value,
            'accessed': time.time()
        }
        
        return value
```

## Monitoring and Metrics

### Data Flow Metrics

```python
class FlowMetrics:
    def __init__(self):
        self.metrics = {
            'messages_processed': 0,
            'patterns_detected': 0,
            'agents_spawned': 0,
            'tickets_created': 0,
            'errors_handled': 0,
            'average_response_time': 0
        }
        
    def record_message(self, processing_time: float):
        self.metrics['messages_processed'] += 1
        self.update_average_time(processing_time)
        
    def record_pattern(self, pattern_type: str):
        self.metrics['patterns_detected'] += 1
        self.metrics[f'pattern_{pattern_type}'] = \
            self.metrics.get(f'pattern_{pattern_type}', 0) + 1
```

### Flow Visualization

```
┌─────────────────────────────────────────────┐
│           Data Flow Monitor                 │
├─────────────────────────────────────────────┤
│ Messages/min: 12                            │
│ Patterns/min: 3                             │
│ Agents active: 2                            │
│ Buffer usage: 45%                           │
│ Error rate: 0.1%                            │
│                                             │
│ [████████████░░░░░░░] 65% CPU               │
│ [██████░░░░░░░░░░░░] 30% Memory             │
└─────────────────────────────────────────────┘
```