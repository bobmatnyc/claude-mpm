# Agent Registry Modular Architecture

## Overview
This directory contains the refactored Agent Registry service, which has been split from the original monolithic `agent_registry_sync.py` (1,527 lines) into smaller, more maintainable modules.

## Module Structure

### Core Modules

1. **`__init__.py`** (484 lines)
   - Main `AgentRegistry` class
   - Core orchestration of agent discovery, validation, and management
   - Provides backward compatibility proxies for internal methods
   - Exposes public API methods

2. **`metadata.py`** (38 lines)
   - `AgentMetadata` dataclass definition
   - Contains all agent metadata fields including specializations and model configuration

3. **`discovery.py`** (417 lines)
   - `AgentDiscovery` class for agent file discovery
   - Directory scanning logic
   - Metadata extraction from agent files
   - Model configuration extraction

4. **`classification.py`** (77 lines)
   - Agent type classification logic
   - Pattern-based agent type detection
   - Supports core and specialized agent types

5. **`validation.py`** (229 lines)
   - `AgentValidator` class for agent validation
   - Specialized agent validation
   - Hybrid agent validation
   - Framework compatibility checking

6. **`cache.py`** (73 lines)
   - `AgentRegistryCache` class for caching functionality
   - Discovery result caching
   - Cache validity checking
   - Cache health testing

7. **`utils.py`** (362 lines)
   - Shared constants and utility functions
   - Agent type definitions (core and specialized)
   - Classification patterns
   - Helper functions for tier determination and metadata extraction

## Key Features Preserved

- **Two-tier hierarchy discovery**: User → System agent precedence
- **Agent type classification**: Support for 35+ agent types
- **Model configuration**: Intelligent model selection based on agent characteristics
- **Caching**: SharedPromptCache integration for performance
- **Validation**: Comprehensive agent validation with scoring
- **Backward compatibility**: All existing imports continue to work

## Usage

The refactored modules maintain full backward compatibility:

```python
# Original import still works
from claude_pm.services.agent_registry_sync import AgentRegistry, AgentMetadata

# New modular import also available
from claude_pm.services.agent_registry import AgentRegistry, AgentMetadata
```

## Benefits of Refactoring

1. **Maintainability**: Each module has a clear, focused responsibility
2. **Testability**: Smaller modules are easier to unit test
3. **Readability**: Files under 500 lines are more approachable
4. **Extensibility**: New features can be added to specific modules
5. **Performance**: No impact on runtime performance

## Testing

All existing tests continue to pass without modification, confirming that the refactoring maintains full backward compatibility and functionality.