# Claude-MPM Codebase Analysis Report
================================================================================

## Executive Summary
- Total Files: 165
- Total Lines of Code: 37,275
- Total Functions: 1349
- Total Classes: 218
- Language Distribution:
  - Python: 165 files
  - Javascript: 0 files
  - Typescript: 0 files

## Code Structure Analysis

### Python Components
- Functions: 1349
- Classes: 218
- Async Functions: 218 (16.2%)

### Code Complexity
- Average Cyclomatic Complexity: 3.20
- Maximum Complexity: 29

## Architectural Patterns
- Service/Agent Classes: 49
  Key Components:
  - TestAgentDelegator
  - TestAgentRegistryAdapter
  - IServiceContainer
  - IConfigurationService
  - ICacheService
  - AgentMetadata
  - IAgentRegistry
  - IServiceFactory
  - IServiceLifecycle
  - SimpleAgentRegistry

## Dependency Analysis
- External Dependencies: 214
  Top Dependencies:
  - 
  - .
  - ...core.base_service
  - ...core.config
  - ...core.logging_config
  - ...utils.framework_detection
  - .._version
  - ..agent_registry
  - ..agent_training_integration
  - ..agents.base_agent_loader

## API Surface
- Entry Points: 4
  - /Users/masa/Projects/claude-mpm/tests/test_cli.py
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/cli_main.py
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/cli.py
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/__main__.py
- Exports: 0

## Recommendations
- Consider refactoring high-complexity functions (complexity > 10)