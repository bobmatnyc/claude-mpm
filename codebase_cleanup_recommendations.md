# Codebase Cleanup Recommendations

Based on Tree Sitter analysis of the claude-mpm codebase, here are the key findings and recommendations for removing large, obsolete, or unused code.

## Summary Statistics

- **Total files analyzed**: 298 Python files
- **Total lines of code**: 97,542
- **Total functions**: 3,268
- **Total classes**: 581

## Major Issues Identified

### 1. Extremely Large Files (>1000 lines)

These files are candidates for refactoring or splitting:

1. **`services/socketio_server.py`** - 1,934 lines, 64 functions, 2 classes
   - **Issue**: Monolithic server implementation
   - **Recommendation**: Split into separate modules for handlers, connection management, and core server logic

2. **`agents/agent_loader.py`** - 1,439 lines, 30 functions, 4 classes
   - **Issue**: Complex agent loading logic in single file
   - **Recommendation**: Extract agent validation, template processing, and loading strategies into separate modules

3. **`services/core/interfaces.py`** - 1,437 lines, 137 functions, 34 classes
   - **Issue**: All interfaces in one file
   - **Recommendation**: Split into domain-specific interface files (agent_interfaces.py, service_interfaces.py, etc.)

4. **`services/agents/deployment/agent_deployment.py`** - 1,369 lines, 32 functions, 1 class
   - **Issue**: Single massive deployment class
   - **Recommendation**: Extract deployment strategies, validation, and lifecycle management

5. **`services/standalone_socketio_server.py`** - 1,318 lines, 47 functions, 8 classes
   - **Issue**: Duplicate of socketio_server.py with additional complexity
   - **Recommendation**: Consolidate with main socketio_server.py or clearly separate concerns

### 2. Massive Functions (>100 lines)

These functions should be broken down:

1. **`cli/parser.py:175`** - 961 lines
   - **Issue**: Single function creates entire CLI parser
   - **Recommendation**: Extract subparser creation into separate functions

2. **`services/framework_claude_md_generator/section_generators/agents.py:15`** - 568 lines
   - **Issue**: Monolithic agent documentation generation
   - **Recommendation**: Split into template-based generation with smaller functions

3. **`services/socketio_server.py:1026`** - 537 lines
   - **Issue**: Large event handling function
   - **Recommendation**: Extract event handlers into separate methods

### 3. Obsolete Ticketing Code

Based on user preferences to remove ticketing implementations:

**Files to Remove:**
- `docs/api/claude_mpm.services.ticket_manager_di.rst`
- `docs/api/claude_mpm.services.ticketing_service_original.rst`
- Any remaining ticketing service implementations (already mostly cleaned up)

**Files to Keep:**
- `src/claude_mpm/services/ticket_manager.py` (already a stub)
- `src/claude_mpm/ticket_wrapper.py` (backward compatibility)
- `scripts/ticket.py` and `scripts/ticket` (wrappers for ai-trackdown)

### 4. Duplicate Patterns

Found multiple files with identical structure patterns:

1. **12 files with "2 imports, 0 functions, 0 classes"**
   - Mostly `__init__.py` files
   - **Recommendation**: Review if all are necessary

2. **11 files with "2 imports, 1 function, 1 class"**
   - Framework generator section files
   - **Recommendation**: Consider template-based approach

### 5. Dead Code Patterns

Files with potential dead code:

1. **`core/interfaces.py`** - 12 empty method definitions
2. **`services/core/interfaces.py`** - 12 empty method definitions
3. **`services/agents/deployment/agent_deployment.py`** - 2 commented blocks, 3 empty definitions
4. **`core/config_aliases.py`** - 4 empty method definitions

### 6. Unused Imports

Top files with potentially unused imports:
- `deployment_paths.py`: sys
- `ticket_wrapper.py`: os
- `core/interfaces.py`: asyncio
- `core/agent_registry.py`: importlib.util
- Multiple files with unused logging, json, os imports

## Immediate Action Items

### High Priority (Large Impact)

1. **Split CLI Parser** (`cli/parser.py`)
   ```python
   # Extract into separate files:
   # - cli/parsers/base_parser.py
   # - cli/parsers/run_parser.py
   # - cli/parsers/agent_parser.py
   # - cli/parsers/memory_parser.py
   ```

2. **Refactor SocketIO Server** (`services/socketio_server.py`)
   ```python
   # Split into:
   # - services/socketio/server.py (core server)
   # - services/socketio/handlers/ (event handlers)
   # - services/socketio/connection_manager.py
   ```

3. **Split Core Interfaces** (`services/core/interfaces.py`)
   ```python
   # Split into:
   # - core/interfaces/agent_interfaces.py
   # - core/interfaces/service_interfaces.py
   # - core/interfaces/memory_interfaces.py
   ```

### Medium Priority

4. **Consolidate SocketIO Implementations**
   - Merge `socketio_server.py` and `standalone_socketio_server.py`
   - Or clearly separate their responsibilities

5. **Refactor Agent Deployment**
   - Extract deployment strategies
   - Separate validation logic
   - Create deployment pipeline classes

### Low Priority (Cleanup)

6. **Remove Unused Imports**
   - Run automated import cleanup
   - Remove commented code blocks
   - Clean up empty method definitions

7. **Remove Obsolete Documentation**
   - Remove ticketing service RST files
   - Update API documentation

## Estimated Impact

- **Lines of code reduction**: ~15,000-20,000 lines (15-20%)
- **File count reduction**: ~10-15 files
- **Maintainability improvement**: High
- **Performance improvement**: Medium (reduced import times, smaller memory footprint)

## Completed Actions

### ✅ Immediate Cleanup (Completed)

1. **Removed Duplicate Files**
   - Removed `src/claude_mpm/services/communication/websocket.py` (identical to `socketio_client_manager.py`)
   - Updated imports in `src/claude_mpm/services/__init__.py`

2. **Removed Obsolete Documentation**
   - Removed `docs/api/claude_mpm.services.ticket_manager_di.rst`
   - Removed `docs/api/claude_mpm.services.ticketing_service_original.rst`

3. **Identified Minimal Files**
   - Found 4 minimal `__init__.py` files with only imports (kept for package structure)

### 📊 Analysis Results Summary

- **Files removed**: 3 files
- **Estimated lines saved**: ~500 lines
- **Import references updated**: 1 file
- **Documentation cleaned**: 2 obsolete RST files

## Implementation Strategy

### Phase 1: Split the largest files (parser.py, socketio_server.py, interfaces.py)
- **Status**: Recommended for next iteration
- **Impact**: High (would reduce ~4,000 lines to manageable modules)

### Phase 2: Remove obsolete ticketing documentation and unused imports
- **Status**: ✅ Partially completed (documentation removed)
- **Remaining**: Unused import cleanup across codebase

### Phase 3: Refactor agent deployment and framework generator
- **Status**: Recommended for future iteration
- **Impact**: Medium (would improve maintainability)

### Phase 4: Consolidate duplicate patterns and clean up dead code
- **Status**: Recommended for future iteration
- **Impact**: Low-Medium (code quality improvement)

Each phase should include:
- Comprehensive testing
- Documentation updates
- Backward compatibility verification
- Performance benchmarking
