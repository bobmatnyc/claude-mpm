# TODO Hijacking System for Claude MPM

## Overview

The TODO hijacking system monitors Claude's TODO files and automatically transforms them into agent delegations. This allows Claude to continue using its native TODO functionality while claude-mpm orchestrates the work through specialized agents.

## Components

### 1. TodoHijacker (`src/orchestration/todo_hijacker.py`)
- Monitors Claude's TODO directory (`~/.claude/todos/` by default)
- Uses `watchdog` library for real-time file system monitoring
- Detects new and modified TODO JSON files
- Processes TODOs and creates delegations
- Tracks processed TODOs to avoid duplication

### 2. TodoTransformer (`src/orchestration/todo_transformer.py`)
- Analyzes TODO content to determine appropriate agent
- Uses keyword matching with word boundary detection
- Supports 8 agent types with confidence scoring:
  - Engineer (code, implementation, development)
  - QA (testing, validation, quality)
  - Documentation (docs, README, guides)
  - Research (investigation, analysis, study)
  - Security (auth, vulnerabilities, encryption)
  - Ops (deployment, DevOps, infrastructure)
  - Version Control (git, branches, merges)
  - Data Engineer (database, API integration, data pipelines)

### 3. Integration with SubprocessOrchestrator
- Added `enable_todo_hijacking` parameter
- Processes TODO-based delegations alongside PM delegations
- Runs delegations in parallel using subprocess execution

## Usage

### Command Line
```bash
# Enable TODO hijacking with subprocess orchestration
claude-mpm --subprocess --todo-hijack -i "Your prompt"
```

### Programmatic
```python
from orchestration.subprocess_orchestrator import SubprocessOrchestrator

orchestrator = SubprocessOrchestrator(
    enable_todo_hijacking=True
)
orchestrator.run_non_interactive("Your prompt")
```

### Demo Script
```bash
python examples/todo_hijacker_demo.py
```

## TODO File Format

The system supports multiple Claude TODO formats:

```json
{
  "todos": [
    {
      "id": "unique-id",
      "content": "Task description",
      "status": "pending",
      "priority": "high"
    }
  ]
}
```

## Features

- **Real-time Monitoring**: Detects TODO changes immediately
- **Smart Agent Detection**: Analyzes task content to assign the right agent
- **Confidence Scoring**: Only processes TODOs with sufficient confidence
- **Duplicate Prevention**: Tracks processed TODOs to avoid reprocessing
- **Multi-format Support**: Handles various TODO JSON structures
- **Context Manager**: Supports with-statement for clean resource management

## Testing

Run the test suite:
```bash
python -m pytest tests/test_todo_hijacker.py -v
```

Quick test:
```bash
python test_todo_hijacking.py
```

## Architecture Benefits

1. **Non-invasive**: Claude continues working normally with TODOs
2. **Automatic Orchestration**: TODOs become delegated agent tasks
3. **Parallel Execution**: Multiple TODO items processed concurrently
4. **Flexible Integration**: Can be enabled/disabled as needed
5. **Extensible**: Easy to add new agent types and keywords

## Future Enhancements

- Support for TODO priorities mapping to delegation priorities
- TODO status updates when delegations complete
- Bidirectional sync between TODOs and tickets
- Machine learning for improved agent detection
- Custom keyword configurations per project