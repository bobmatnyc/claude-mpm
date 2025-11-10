# Code Tree Analyzer Module

## Overview

The Code Tree Analyzer provides AST-based analysis of source code files across multiple programming languages.

## Architecture

This module has been refactored from a single 1,825-line file into focused, maintainable components:

### Core Components

- **`core.py`** - Main CodeTreeAnalyzer orchestrator
- **`models.py`** - CodeNode data structure
- **`gitignore.py`** - GitignoreManager for pattern matching
- **`python_analyzer.py`** - Python AST analysis
- **`multilang_analyzer.py`** - Multi-language support via tree-sitter

### Supporting Modules

- **`cache.py`** - Caching logic for analyzed files
- **`discovery.py`** - Directory traversal and file discovery
- **`events.py`** - Event emission for UI updates
- **`analysis.py`** - File analysis coordination

## Design Principles

- **Single Responsibility**: Each module handles one clear concern
- **Backward Compatibility**: All existing imports work unchanged
- **Testability**: Isolated components are easier to test
- **Maintainability**: ~200-300 lines per file, well-documented

## Usage

```python
from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer, CodeNode

# Create analyzer
analyzer = CodeTreeAnalyzer(emit_events=True)

# Analyze directory
result = analyzer.analyze_directory(Path("/path/to/code"))

# Access results
print(result['stats'])
for node in result['nodes']:
    print(f"{node.name} ({node.node_type})")
```

## Supported Languages

- Python (via AST module)
- JavaScript/TypeScript (via tree-sitter)
- Generic support for other languages

## Event System

The analyzer emits real-time events during analysis:
- File discovery
- Analysis progress
- Node extraction
- Error handling

These events enable live UI updates in the dashboard.
