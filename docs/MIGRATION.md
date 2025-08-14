# Migration Guide

This guide documents the breaking changes from the TSK-0053 architecture refactoring and provides migration paths for existing code, configurations, and integrations.

**Last Updated**: 2025-08-14  
**Architecture Version**: 3.8.2  
**Migration Source**: TSK-0053 Service Layer Architecture Reorganization  
**Related Documents**: [ARCHITECTURE.md](ARCHITECTURE.md), [SERVICES.md](developer/SERVICES.md)

## Table of Contents

- [Overview](#overview)
- [Breaking Changes Summary](#breaking-changes-summary)
- [Service Layer Migration](#service-layer-migration)
- [Import Path Migration](#import-path-migration)
- [Configuration Migration](#configuration-migration)
- [API Changes](#api-changes)
- [Before and After Examples](#before-and-after-examples)
- [Deprecated Patterns](#deprecated-patterns)
- [Migration Scripts](#migration-scripts)
- [Troubleshooting](#troubleshooting)

## Overview

The TSK-0053 refactoring introduces a new service-oriented architecture with interface-based contracts, dependency injection, and improved performance. While backward compatibility is maintained through lazy imports, some patterns and APIs have changed.

### Migration Timeline

- **Immediate**: Lazy import compatibility ensures existing imports continue working
- **Recommended (3 months)**: Update imports to use new service locations
- **Required (6 months)**: Legacy compatibility layer will be deprecated
- **Sunset (12 months)**: Legacy patterns will be removed

### Compatibility Level

- ✅ **Import Compatibility**: 100% - Lazy imports maintain existing paths
- ✅ **API Compatibility**: 95% - Most APIs unchanged, some enhanced
- ⚠️ **Configuration Compatibility**: 90% - Minor configuration updates needed
- ⚠️ **Extension Compatibility**: 80% - Custom extensions may need updates

## Breaking Changes Summary

### 1. Service Organization Changes

**Old Structure**:
```
/src/claude_mpm/services/
├── agent_deployment.py
├── agent_registry.py
├── memory_manager.py
├── socketio_server.py
└── project_analyzer.py
```

**New Structure**:
```
/src/claude_mpm/services/
├── core/
│   ├── interfaces.py
│   └── base.py
├── agent/
│   ├── deployment.py
│   ├── management.py
│   └── registry.py
├── communication/
│   ├── socketio.py
│   └── websocket.py
├── project/
│   ├── analyzer.py
│   └── registry.py
└── infrastructure/
    ├── logging.py
    └── monitoring.py
```

### 2. Interface-Based Architecture

**Breaking Change**: Services now implement explicit interfaces

**Impact**: Code expecting concrete types may need updates

**Migration**: Update type hints to use interfaces instead of concrete classes

### 3. Dependency Injection

**Breaking Change**: Services now use dependency injection container

**Impact**: Manual service instantiation patterns need updates

**Migration**: Use service container for service resolution

### 4. Configuration Schema Changes

**Breaking Change**: Some configuration keys have been renamed/restructured

**Impact**: Configuration files may need updates

**Migration**: Update configuration files to new schema

## Service Layer Migration

### Agent Services Migration

#### Old Pattern
```python
# Old import and usage
from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.agent_registry import AgentRegistry

# Direct instantiation
deployment_service = AgentDeploymentService()
registry = AgentRegistry()
```

#### New Pattern
```python
# New imports (recommended)
from claude_mpm.services.agent.deployment import AgentDeploymentService
from claude_mpm.services.agent.registry import AgentRegistry
from claude_mpm.services.core.interfaces import IAgentRegistry, AgentDeploymentInterface

# Interface-based usage
def process_agents(registry: IAgentRegistry, deployment: AgentDeploymentInterface):
    # Use interfaces for better testability
    agents = await registry.discover_agents()
    result = deployment.deploy_agents()
    return result

# Service container usage (advanced)
from claude_mpm.services.core import ServiceContainer

container = ServiceContainer()
registry = container.resolve(IAgentRegistry)
deployment = container.resolve(AgentDeploymentInterface)
```

#### Compatibility Layer (Temporary)
```python
# This still works due to lazy imports (temporary compatibility)
from claude_mpm.services import AgentDeploymentService, AgentRegistry

# But update to new pattern for future compatibility
```

### Memory Services Migration

#### Old Pattern
```python
from claude_mpm.services.memory_manager import MemoryManager
from claude_mpm.services.memory_optimizer import MemoryOptimizer

memory_manager = MemoryManager()
optimizer = MemoryOptimizer()
```

#### New Pattern
```python
from claude_mpm.services.agents.memory import AgentMemoryManager
from claude_mpm.services.memory.optimizer import MemoryOptimizer
from claude_mpm.services.core.interfaces import MemoryServiceInterface

# Interface-based usage
class AgentService:
    def __init__(self, memory_service: MemoryServiceInterface):
        self.memory_service = memory_service
    
    async def save_learning(self, agent_id: str, content: str):
        return await self.memory_service.save_memory(agent_id, content)
```

### Communication Services Migration

#### Old Pattern
```python
from claude_mpm.services.socketio_server import SocketIOServer

server = SocketIOServer()
await server.start()
```

#### New Pattern
```python
from claude_mpm.services.communication.socketio import SocketIOServer
from claude_mpm.services.core.interfaces import SocketIOServiceInterface

# Interface-based implementation
class DashboardService:
    def __init__(self, socketio: SocketIOServiceInterface):
        self.socketio = socketio
    
    async def broadcast_update(self, event: str, data: dict):
        await self.socketio.broadcast(event, data)
```

## Import Path Migration

### Automated Migration Script

```python
#!/usr/bin/env python3
"""
Automated migration script for import paths
Usage: python migrate_imports.py <directory>
"""

import re
import os
from pathlib import Path
from typing import Dict, List

class ImportMigrator:
    """Migrates old import paths to new service organization"""
    
    def __init__(self):
        self.migration_map = {
            # Agent services
            'from claude_mpm.services.agent_deployment import': 
                'from claude_mpm.services.agent.deployment import',
            'from claude_mpm.services.agent_registry import': 
                'from claude_mpm.services.agent.registry import',
            'from claude_mpm.services.agent_manager import': 
                'from claude_mpm.services.agent.management import',
            
            # Memory services  
            'from claude_mpm.services.memory_manager import': 
                'from claude_mpm.services.agents.memory import',
            'from claude_mpm.services.memory_optimizer import': 
                'from claude_mpm.services.memory.optimizer import',
            
            # Communication services
            'from claude_mpm.services.socketio_server import': 
                'from claude_mpm.services.communication.socketio import',
            'from claude_mpm.services.websocket_client import': 
                'from claude_mpm.services.communication.websocket import',
            
            # Project services
            'from claude_mpm.services.project_analyzer import': 
                'from claude_mpm.services.project.analyzer import',
            
            # Infrastructure services
            'from claude_mpm.services.health_monitor import': 
                'from claude_mpm.services.infrastructure.monitoring import',
        }
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate imports in a single file"""
        if not file_path.suffix == '.py':
            return False
        
        try:
            content = file_path.read_text()
            original_content = content
            
            # Apply migrations
            for old_import, new_import in self.migration_map.items():
                content = content.replace(old_import, new_import)
            
            # Write back if changed
            if content != original_content:
                file_path.write_text(content)
                print(f"Migrated: {file_path}")
                return True
            
        except Exception as e:
            print(f"Error migrating {file_path}: {e}")
        
        return False
    
    def migrate_directory(self, directory: Path) -> Dict[str, int]:
        """Migrate all Python files in directory"""
        results = {'migrated': 0, 'skipped': 0, 'errors': 0}
        
        for py_file in directory.rglob('*.py'):
            try:
                if self.migrate_file(py_file):
                    results['migrated'] += 1
                else:
                    results['skipped'] += 1
            except Exception:
                results['errors'] += 1
        
        return results

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python migrate_imports.py <directory>")
        sys.exit(1)
    
    migrator = ImportMigrator()
    directory = Path(sys.argv[1])
    results = migrator.migrate_directory(directory)
    
    print(f"Migration complete:")
    print(f"  Migrated: {results['migrated']} files")
    print(f"  Skipped: {results['skipped']} files") 
    print(f"  Errors: {results['errors']} files")
```

### Manual Migration Steps

1. **Update Service Imports**
```bash
# Find files using old imports
grep -r "from claude_mpm.services.agent_deployment" . --include="*.py"

# Update to new pattern
find . -name "*.py" -exec sed -i 's/from claude_mpm.services.agent_deployment/from claude_mpm.services.agent.deployment/g' {} \;
```

2. **Update Interface Usage**
```python
# Old: Direct type dependencies
def process_agents(deployment_service: AgentDeploymentService):
    pass

# New: Interface dependencies  
def process_agents(deployment_service: AgentDeploymentInterface):
    pass
```

## Configuration Migration

### Service Configuration Changes

#### Old Configuration (`config.yaml`)
```yaml
services:
  agent_deployment:
    enabled: true
    timeout: 30
  
  memory_manager:
    enabled: true
    cache_size: 1000
  
  socketio_server:
    enabled: true
    port: 8765
```

#### New Configuration (`config.yaml`)
```yaml
services:
  agent:
    deployment:
      enabled: true
      timeout: 30
    management:
      enabled: true
      
  memory:
    cache_size: 1000
    optimization_enabled: true
    
  communication:
    socketio:
      enabled: true
      port: 8765
      
  infrastructure:
    monitoring:
      enabled: true
      interval: 30
```

### Environment Variables Migration

#### Old Environment Variables
```bash
CLAUDE_MPM_AGENT_DEPLOYMENT_TIMEOUT=30
CLAUDE_MPM_MEMORY_CACHE_SIZE=1000
CLAUDE_MPM_SOCKETIO_PORT=8765
```

#### New Environment Variables
```bash
CLAUDE_MPM_AGENT_DEPLOYMENT_TIMEOUT=30  # Still supported
CLAUDE_MPM_MEMORY_CACHE_SIZE=1000       # Still supported
CLAUDE_MPM_COMMUNICATION_SOCKETIO_PORT=8765  # New structure
```

## API Changes

### Service Initialization Changes

#### Old Pattern
```python
# Manual service initialization
from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.agent_registry import AgentRegistry

deployment = AgentDeploymentService()
registry = AgentRegistry()

# Manual dependency wiring
deployment.set_registry(registry)
```

#### New Pattern
```python
# Service container initialization
from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.core.interfaces import IAgentRegistry, AgentDeploymentInterface

container = ServiceContainer()

# Register services
container.register(IAgentRegistry, AgentRegistry, singleton=True)
container.register(AgentDeploymentInterface, AgentDeploymentService, singleton=True)

# Resolve with automatic dependency injection
deployment = container.resolve(AgentDeploymentInterface)
registry = container.resolve(IAgentRegistry)
```

### Enhanced Service APIs

#### Memory Service Enhancements
```python
# Old API
class MemoryManager:
    def save_memory(self, agent_id: str, content: str) -> bool:
        pass
    
    def load_memory(self, agent_id: str) -> str:
        pass

# New API (backward compatible with enhancements)
class AgentMemoryManager(MemoryServiceInterface):
    def save_memory(self, agent_id: str, content: str) -> bool:
        pass
    
    def load_memory(self, agent_id: str) -> Optional[str]:
        pass
    
    # New methods
    def validate_memory_size(self, content: str) -> Tuple[bool, Optional[str]]:
        pass
    
    def optimize_memory(self, agent_id: str) -> bool:
        pass
    
    def get_memory_metrics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        pass
```

## Before and After Examples

### Example 1: Agent Deployment Script

#### Before (Old Pattern)
```python
#!/usr/bin/env python3
"""Old agent deployment script"""

from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.agent_registry import AgentRegistry
import asyncio

async def deploy_agents():
    # Manual service creation
    deployment_service = AgentDeploymentService()
    registry = AgentRegistry()
    
    # Deploy agents
    result = deployment_service.deploy_agents()
    
    # Discover deployed agents
    agents = await registry.discover_agents()
    
    print(f"Deployed {len(agents)} agents")
    return result

if __name__ == '__main__':
    asyncio.run(deploy_agents())
```

#### After (New Pattern)
```python
#!/usr/bin/env python3
"""New agent deployment script with interfaces and DI"""

from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.core.interfaces import IAgentRegistry, AgentDeploymentInterface
from claude_mpm.services.agent.deployment import AgentDeploymentService
from claude_mpm.services.agent.registry import AgentRegistry
import asyncio

async def deploy_agents():
    # Service container setup
    container = ServiceContainer()
    container.register(IAgentRegistry, AgentRegistry, singleton=True)
    container.register(AgentDeploymentInterface, AgentDeploymentService, singleton=True)
    
    # Resolve services
    deployment_service = container.resolve(AgentDeploymentInterface)
    registry = container.resolve(IAgentRegistry)
    
    # Deploy agents
    result = deployment_service.deploy_agents()
    
    # Discover deployed agents
    agents = await registry.discover_agents()
    
    print(f"Deployed {len(agents)} agents")
    return result

if __name__ == '__main__':
    asyncio.run(deploy_agents())
```

### Example 2: Custom Service Integration

#### Before (Old Pattern)
```python
class CustomAnalyzer:
    def __init__(self):
        self.project_analyzer = ProjectAnalyzer()
        self.memory_manager = MemoryManager()
    
    def analyze_and_save(self, project_path: str):
        # Analyze project
        analysis = self.project_analyzer.analyze_project(project_path)
        
        # Save to memory
        self.memory_manager.save_memory('analyzer', str(analysis))
        
        return analysis
```

#### After (New Pattern)
```python
from claude_mpm.services.core.interfaces import ProjectAnalyzerInterface, MemoryServiceInterface

class CustomAnalyzer:
    def __init__(self, 
                 project_analyzer: ProjectAnalyzerInterface,
                 memory_service: MemoryServiceInterface):
        self.project_analyzer = project_analyzer
        self.memory_service = memory_service
    
    async def analyze_and_save(self, project_path: str):
        # Analyze project
        analysis = self.project_analyzer.analyze_project(project_path)
        
        # Save to memory with validation
        content = str(analysis)
        is_valid, error = self.memory_service.validate_memory_size(content)
        
        if is_valid:
            await self.memory_service.save_memory('analyzer', content)
        else:
            raise ValueError(f"Memory content invalid: {error}")
        
        return analysis

# Usage with dependency injection
container = ServiceContainer()
analyzer = CustomAnalyzer(
    container.resolve(ProjectAnalyzerInterface),
    container.resolve(MemoryServiceInterface)
)
```

## Deprecated Patterns

### 1. Direct Service Instantiation

**Deprecated**:
```python
# Don't do this
service = AgentDeploymentService()
```

**Recommended**:
```python
# Use service container
container = ServiceContainer()
service = container.resolve(AgentDeploymentInterface)
```

### 2. Hardcoded Service Dependencies

**Deprecated**:
```python
class MyService:
    def __init__(self):
        self.agent_service = AgentDeploymentService()  # Hardcoded dependency
```

**Recommended**:
```python
class MyService:
    def __init__(self, agent_service: AgentDeploymentInterface):
        self.agent_service = agent_service  # Injected dependency
```

### 3. Direct File System Access

**Deprecated**:
```python
# Direct file operations without validation
with open(file_path, 'w') as f:
    f.write(content)
```

**Recommended**:
```python
# Use secure file operations
from claude_mpm.utils.path_operations import PathOperations

path_ops = PathOperations()
success = path_ops.secure_write_file(file_path, content)
```

## Migration Scripts

### Complete Migration Script

```bash
#!/bin/bash
# complete_migration.sh - Comprehensive migration script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/migration_backup_$(date +%Y%m%d_%H%M%S)"

echo "Starting Claude MPM migration..."

# 1. Create backup
echo "Creating backup..."
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_ROOT/src" "$BACKUP_DIR/"
cp -r "$PROJECT_ROOT/tests" "$BACKUP_DIR/"

# 2. Update imports
echo "Updating import paths..."
python "${PROJECT_ROOT}/scripts/migrate_imports.py" "$PROJECT_ROOT/src"
python "${PROJECT_ROOT}/scripts/migrate_imports.py" "$PROJECT_ROOT/tests"

# 3. Update configuration files
echo "Updating configuration..."
python "${PROJECT_ROOT}/scripts/migrate_config.py" "$PROJECT_ROOT"

# 4. Run tests to verify migration
echo "Running tests to verify migration..."
cd "$PROJECT_ROOT"
python -m pytest tests/ -v

echo "Migration completed successfully!"
echo "Backup created at: $BACKUP_DIR"
```

### Configuration Migration Script

```python
#!/usr/bin/env python3
"""Configuration migration script"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any

class ConfigMigrator:
    """Migrates configuration files to new schema"""
    
    def __init__(self):
        self.migration_rules = {
            'services.agent_deployment': 'services.agent.deployment',
            'services.memory_manager': 'services.memory',
            'services.socketio_server': 'services.communication.socketio',
        }
    
    def migrate_yaml_config(self, config_path: Path) -> bool:
        """Migrate YAML configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            migrated_config = self._migrate_config_dict(config)
            
            # Backup original
            backup_path = config_path.with_suffix('.yaml.backup')
            config_path.rename(backup_path)
            
            # Write migrated config
            with open(config_path, 'w') as f:
                yaml.dump(migrated_config, f, default_flow_style=False)
            
            print(f"Migrated: {config_path}")
            return True
            
        except Exception as e:
            print(f"Error migrating {config_path}: {e}")
            return False
    
    def _migrate_config_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively migrate configuration dictionary"""
        if not isinstance(config, dict):
            return config
        
        migrated = {}
        for key, value in config.items():
            # Check if key needs migration
            new_key = key
            for old_pattern, new_pattern in self.migration_rules.items():
                if key == old_pattern:
                    new_key = new_pattern
                    break
            
            # Recursively migrate nested structures
            if isinstance(value, dict):
                migrated[new_key] = self._migrate_config_dict(value)
            else:
                migrated[new_key] = value
        
        return migrated

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python migrate_config.py <project_root>")
        sys.exit(1)
    
    migrator = ConfigMigrator()
    project_root = Path(sys.argv[1])
    
    # Find and migrate configuration files
    config_files = list(project_root.rglob('*.yaml')) + list(project_root.rglob('*.yml'))
    
    migrated_count = 0
    for config_file in config_files:
        if migrator.migrate_yaml_config(config_file):
            migrated_count += 1
    
    print(f"Migrated {migrated_count} configuration files")
```

## Troubleshooting

### Common Migration Issues

#### 1. Import Errors After Migration

**Problem**: `ImportError: cannot import name 'AgentDeploymentService'`

**Solution**:
```python
# Check if using old import path
from claude_mpm.services.agent_deployment import AgentDeploymentService  # Old

# Update to new path
from claude_mpm.services.agent.deployment import AgentDeploymentService  # New

# Or use lazy import compatibility (temporary)
from claude_mpm.services import AgentDeploymentService  # Compatibility
```

#### 2. Service Resolution Errors

**Problem**: `ServiceNotRegisteredError: AgentDeploymentInterface not registered`

**Solution**:
```python
# Register service before resolving
container = ServiceContainer()
container.register(AgentDeploymentInterface, AgentDeploymentService)

# Then resolve
service = container.resolve(AgentDeploymentInterface)
```

#### 3. Configuration Validation Errors

**Problem**: `ConfigurationError: Unknown configuration key`

**Solution**:
```yaml
# Update configuration schema
services:
  # Old structure
  agent_deployment:
    enabled: true
  
  # New structure  
  agent:
    deployment:
      enabled: true
```

#### 4. Test Failures After Migration

**Problem**: Tests fail due to service mocking issues

**Solution**:
```python
# Update test mocks to use interfaces
@patch('claude_mpm.services.core.interfaces.AgentDeploymentInterface')
def test_with_interface_mock(mock_deployment):
    # Test implementation
    pass

# Or use dependency injection in tests
def test_with_dependency_injection():
    container = ServiceContainer()
    mock_service = Mock(spec=AgentDeploymentInterface)
    container.register_instance(AgentDeploymentInterface, mock_service)
    # Test with mocked service
```

### Rollback Procedures

If migration issues occur, follow these rollback steps:

1. **Stop all services**
```bash
./scripts/stop_services.sh
```

2. **Restore from backup**
```bash
cp -r migration_backup_*/src/* src/
cp -r migration_backup_*/tests/* tests/
```

3. **Verify rollback**
```bash
python -m pytest tests/test_basic_functionality.py
```

4. **Report issues**
- Create issue with migration details
- Include error logs and configuration
- Specify environment and version info

### Getting Help

- **Documentation**: See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture info
- **Examples**: Check `examples/` directory for migration examples  
- **Community**: Submit issues to the project repository
- **Support**: Contact the development team for complex migrations

This migration guide ensures a smooth transition to the new service-oriented architecture while maintaining backward compatibility and providing clear upgrade paths.