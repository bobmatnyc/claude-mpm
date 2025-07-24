# Claude-MPM Enhanced Codebase Analysis
================================================================================

Generated using Tree-sitter semantic analysis with architectural insights

## 🏗️ Architecture Analysis

### Layer Distribution
- **_version.py**: 1 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **__init__.py**: 1 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **cli_main.py**: 1 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 1
- **cli.py**: 1 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 1
- **__main__.py**: 1 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **core**: 12 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **framework**: 3 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **config**: 2 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **agents**: 7 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **utils**: 2 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 0
- **hooks**: 8 files
  - Cohesion Score: 0.50
  - Internal Imports: 1
  - External Imports: 1
- **orchestration**: 16 files
  - Cohesion Score: 0.00
  - Internal Imports: 0
  - External Imports: 3
- **services**: 72 files
  - Cohesion Score: 0.57
  - Internal Imports: 4
  - External Imports: 3

### Design Patterns Detected
- **Singleton**: TicketingService
- **Factory**: IServiceFactory
- **Adapter**: TestAgentRegistryAdapter, AgentRegistryAdapter
- **Strategy**: BranchStrategyType, BranchStrategyManager, ResolutionStrategy

## 📊 Code Quality Metrics
- **Maintainability Index**: 84.0/100
- **Test Coverage Estimate**: 23.6%
- **Documentation Ratio**: 70.0%
- **Code Duplication Risk**: 29.4%

## 🔥 Code Hotspots

### High Complexity Functions
- `main` - Complexity: 12
  - File: /Users/masa/Projects/claude-mpm/.claude/hooks/subagent_stop_ticket_extractor.py
- `test_claude_modes` - Complexity: 11
  - File: /Users/masa/Projects/claude-mpm/scripts/tests/test_claude_direct.py
- `main` - Complexity: 16
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/cli.py
- `run_session` - Complexity: 19
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/cli.py
- `_load_framework_content` - Complexity: 23
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework_loader.py

### God Classes
- `EnhancedBaseService` - 34 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/core/enhanced_base_service.py
- `SharedPromptCache` - 21 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/shared_prompt_cache.py
- `AgentLifecycleManager` - 27 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/agent_lifecycle_manager.py
- `BranchStrategyManager` - 23 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/version_control/branch_strategy.py
- `SemanticVersionManager` - 22 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/version_control/semantic_versioning.py
- `ConflictResolutionManager` - 23 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/version_control/conflict_resolution.py
- `ParentDirectoryManager` - 26 methods
  - File: /Users/masa/Projects/claude-mpm/src/claude_mpm/services/parent_directory_manager/__init__.py

## 🔌 API Surface Analysis
- **Public Functions**: 74
- **Public Classes**: 218
- **CLI Commands**: 29
- **Services**: 15
- **Hooks**: 21

## 🕸️ Dependency Analysis
- **Total Modules**: 19
- **Total Dependencies**: 16
- **High-Connectivity Clusters**: 0

## 📋 Recommendations

### Complexity (High Priority)
**Issue**: 40 functions have cyclomatic complexity > 10
**Recommendation**: Refactor complex functions to improve maintainability
**Affected Items**:
  - main (complexity: 12)
  - test_claude_modes (complexity: 11)
  - main (complexity: 16)
  - run_session (complexity: 19)
  - _load_framework_content (complexity: 23)

### Class Design (High Priority)
**Issue**: 7 classes have more than 20 methods
**Recommendation**: Apply Single Responsibility Principle - split large classes
**Affected Items**:
  - EnhancedBaseService (34 methods)
  - SharedPromptCache (21 methods)
  - AgentLifecycleManager (27 methods)
  - BranchStrategyManager (23 methods)
  - SemanticVersionManager (22 methods)
  - ConflictResolutionManager (23 methods)
  - ParentDirectoryManager (26 methods)

### Testing (High Priority)
**Issue**: Test coverage estimate is low (23.6%)
**Recommendation**: Increase test coverage, especially for complex functions
**Affected Items**:
  - Add unit tests for core functionality
  - Focus on testing complex functions first

### File Size (Medium Priority)
**Issue**: 18 files exceed 500 lines
**Recommendation**: Consider splitting large files into smaller, more focused modules
**Affected Items**:
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/core/interfaces.py (537 lines)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/core/enhanced_base_service.py (748 lines)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/agents/system_agent_config.py (542 lines)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/agents/agent_loader.py (574 lines)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration/orchestrator.py (536 lines)

### Coupling (Medium Priority)
**Issue**: Several files have high import counts indicating tight coupling
**Recommendation**: Reduce coupling by introducing interfaces or dependency injection
**Affected Items**:
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration/subprocess_orchestrator.py (29 imports)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration/orchestrator.py (28 imports)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/cli.py (26 imports)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration/pty_orchestrator.py (25 imports)
  - /Users/masa/Projects/claude-mpm/src/claude_mpm/orchestration/interactive_subprocess_orchestrator.py (25 imports)

### Architecture (Medium Priority)
**Issue**: Some layers have low cohesion scores
**Recommendation**: Improve module boundaries and reduce cross-layer dependencies
**Affected Items**:
  - _version.py (cohesion: 0.00)
  - __init__.py (cohesion: 0.00)
  - cli_main.py (cohesion: 0.00)
  - cli.py (cohesion: 0.00)
  - __main__.py (cohesion: 0.00)
  - core (cohesion: 0.00)
  - framework (cohesion: 0.00)
  - config (cohesion: 0.00)
  - agents (cohesion: 0.00)
  - utils (cohesion: 0.00)
  - orchestration (cohesion: 0.00)

### API Design (Low Priority)
**Issue**: Large public API surface
**Recommendation**: Consider consolidating API endpoints or creating facade patterns
**Affected Items**:
  - Total public functions: 74
  - Total public classes: 218

## 🎯 Epic-Ready Improvement Areas

Based on the analysis, here are epic-sized improvement initiatives:

1. **Code Complexity Reduction Epic**
   - Refactor high-complexity functions
   - Split god classes following SRP
   - Introduce design patterns for better structure

2. **Test Coverage Improvement Epic**
   - Achieve 80% test coverage
   - Add integration tests for key workflows
   - Implement automated test generation

3. **Architecture Refactoring Epic**
   - Improve layer cohesion
   - Reduce coupling between modules
   - Implement dependency injection

4. **API Consolidation Epic**
   - Design unified API surface
   - Create API documentation
   - Implement API versioning

5. **Performance Optimization Epic**
   - Optimize async operations
   - Reduce import overhead
   - Implement caching strategies