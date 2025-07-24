# Agent Modification Tracker Module

This directory contains the refactored Agent Modification Tracker implementation for ISS-0118.

## Module Structure

The agent modification tracker has been refactored from a single 1,174-line file into a well-organized directory structure:

### Core Modules

- **`models.py`** (~100 lines)
  - Data models: `AgentModification`, `ModificationHistory`
  - Enums: `ModificationType`, `ModificationTier`
  - Serialization/deserialization methods

- **`file_monitor.py`** (~150 lines)
  - Real-time file system monitoring
  - Watchdog event handlers
  - Path discovery for agent directories

- **`metadata_analyzer.py`** (~150 lines)
  - File metadata extraction
  - Python AST analysis for code files
  - Markdown structure analysis
  - Agent info extraction from paths

- **`tree_sitter_analyzer.py`** (~200 lines)
  - Advanced code analysis using tree-sitter parsing
  - Support for 41+ programming languages through tree-sitter-language-pack
  - AST-level understanding for syntax-aware modifications
  - Incremental parsing for real-time performance

- **`backup_manager.py`** (~100 lines)
  - Agent file backup creation
  - Restore functionality
  - Backup cleanup and statistics

- **`validation.py`** (~100 lines)
  - Python syntax validation
  - Markdown structure validation
  - Modification conflict detection

- **`persistence.py`** (~150 lines)
  - History persistence to JSON
  - State loading/saving
  - Directory management

- **`cache_integration.py`** (~100 lines)
  - SharedPromptCache invalidation
  - Specialized cache patterns
  - Batch invalidation support

- **`specialized_agent_handler.py`** (~100 lines)
  - Specialized agent type support
  - Metadata enrichment
  - Complexity analysis

- **`__init__.py`** (~250 lines)
  - Main `AgentModificationTracker` facade class
  - Service initialization and lifecycle
  - Public API methods
  - Background task management

## Backward Compatibility

The original `agent_modification_tracker.py` file has been replaced with a stub that imports all public APIs from the refactored module, ensuring complete backward compatibility.

## Usage

```python
from claude_pm.services.agent_modification_tracker import AgentModificationTracker

# Initialize tracker
tracker = AgentModificationTracker()

# Track modifications
await tracker.track_modification(
    agent_name="example_agent",
    modification_type=ModificationType.MODIFY,
    file_path="/path/to/agent.py",
    tier=ModificationTier.PROJECT
)

# Get modification history
history = await tracker.get_modification_history("example_agent")

# Get statistics
stats = await tracker.get_modification_stats()
```

## Features

- Real-time file system monitoring for agent changes
- Comprehensive modification history with persistence
- Automatic backup creation before modifications
- Syntax and structure validation
- Cache invalidation on modifications
- Support for specialized agent types
- Three-tier hierarchy support (project/user/system)
- AST-level code analysis for 41+ programming languages

## Dependencies

The agent modification tracker requires the following dependencies for advanced code analysis:

- **tree-sitter** (>=0.21.0) - Core parsing library providing fast, incremental syntax analysis
- **tree-sitter-language-pack** (>=0.20.0) - Language support package providing parsers for:
  - Python, JavaScript, TypeScript, Go, Rust, Java, C/C++
  - Ruby, PHP, Swift, Kotlin, Scala, Haskell, Elixir
  - And 25+ additional languages

These dependencies enable the TreeSitterAnalyzer component to provide:
- Syntax-aware code understanding for Research Agent operations
- Real-time AST analysis during agent modifications
- Language-agnostic parsing with consistent API
- Incremental parsing for performance-critical scenarios

## Performance

- <50ms change detection and processing
- Intelligent cache invalidation
- Background persistence (5-minute intervals)
- Automatic cleanup of old data (30-day retention)
- Incremental tree-sitter parsing for real-time analysis