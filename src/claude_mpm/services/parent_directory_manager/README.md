# Parent Directory Manager

This directory contains the modularized components of the Parent Directory Manager service.

## Module Structure

The Parent Directory Manager has been refactored into specialized modules following the single-responsibility principle:

### Core Module
- `__init__.py` - Main ParentDirectoryManager class that orchestrates all operations

### Specialized Modules

1. **backup_manager.py** - Handles backup operations
   - Creates backups of files before modifications
   - Manages backup retention and cleanup
   - Handles framework template backup protection

2. **template_deployer.py** - Manages template deployment
   - Handles version comparison and deployment decisions
   - Renders templates with variable substitution
   - Integrates with framework template generator

3. **framework_protector.py** - Framework protection mechanisms
   - Protects critical framework files
   - Manages protection rules and validation

4. **version_control_helper.py** - Version control integration
   - Git operations and version control checks
   - Branch management support

5. **deduplication_manager.py** - CLAUDE.md deduplication
   - Detects and removes duplicate CLAUDE.md files
   - Manages deduplication hierarchy and precedence

6. **operations.py** (formerly parent_directory_operations.py) - Directory operations
   - Auto-detection of parent directory contexts
   - Directory registration and management

7. **config_manager.py** - Configuration management
   - Manages directory configurations
   - Handles registration and configuration persistence

8. **state_manager.py** - State and lifecycle management
   - Initialization and cleanup operations
   - Operation history tracking
   - Logging and error handling

9. **validation_manager.py** - Validation operations
   - Template validation
   - Compatibility checking
   - Directory status validation

10. **version_manager.py** - Version tracking
    - Subsystem version management
    - Version compatibility validation
    - Version reporting

## Usage

The main entry point remains the `ParentDirectoryManager` class, which delegates to these specialized modules:

```python
from claude_pm.services.parent_directory_manager import ParentDirectoryManager

# Initialize the manager
manager = ParentDirectoryManager()

# All public APIs remain the same
await manager.deploy_framework_template(target_dir)
```

## Backward Compatibility

A stub file at `claude_pm/services/parent_directory_manager.py` ensures backward compatibility for existing imports.

## Design Principles

1. **Single Responsibility** - Each module has a focused purpose
2. **Delegation Pattern** - Main class delegates to specialized modules
3. **Dependency Injection** - Modules receive dependencies via constructor
4. **Async Support** - All operations support async/await patterns
5. **Comprehensive Logging** - Each module uses consistent logging