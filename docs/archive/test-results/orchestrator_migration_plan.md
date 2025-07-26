# Orchestrator Consolidation Migration Plan

## Overview

This document outlines the plan to consolidate 16+ orchestrator implementations down to 3 core strategies, as specified in ISS-0002.

## Current State

### Existing Orchestrators (16 files)
1. `orchestrator.py` - MPMOrchestrator (base with subprocess management)
2. `subprocess_orchestrator.py` - SubprocessOrchestrator (primary, uses ClaudeLauncher)
3. `system_prompt_orchestrator.py` - SystemPromptOrchestrator (uses --system-prompt)
4. `interactive_subprocess_orchestrator.py` - InteractiveSubprocessOrchestrator (pexpect)
5. `simple_orchestrator.py` - SimpleOrchestrator (print mode)
6. `direct_orchestrator.py` - DirectOrchestrator (minimal intervention)
7. `wrapper_orchestrator.py` - WrapperOrchestrator (wrapper scripts)
8. `pty_orchestrator.py` - PTYOrchestrator (Python pty module)
9. `pexpect_orchestrator.py` - PexpectOrchestrator (pexpect library)
10. `hook_enabled_orchestrator.py` - HookEnabledOrchestrator (example)
11. Plus backup files (`.bak`) and other experimental implementations

## Target State

### Core Orchestrators (3 files)
1. **SubprocessOrchestrator** (Primary)
   - Unified implementation using ClaudeLauncher
   - Supports interactive, non-interactive, and subprocess modes
   - Full feature set: agent delegation, TODO hijacking, hooks
   - Absorbs features from InteractiveSubprocessOrchestrator

2. **SystemPromptOrchestrator** (Alternative) 
   - Clean system prompt injection
   - Simpler subprocess handling
   - For when Claude CLI supports --system-prompt

3. **DirectOrchestrator** (Minimal)
   - Direct execution with minimal overhead
   - Good for testing and simple use cases
   - No complex delegation handling

### Supporting Files
- `base_orchestrator.py` - Abstract base class with common functionality
- `factory.py` - Simplified factory with 3 modes
- Helper modules remain unchanged (ticket_extractor, agent_delegator, etc.)

## Migration Steps

### Phase 1: Preparation (Completed)
- ✅ Created base_orchestrator.py with common functionality
- ✅ Created v2 versions of core orchestrators
- ✅ Created simplified factory_v2.py

### Phase 2: Feature Integration
1. Update SubprocessOrchestrator to include:
   - Interactive subprocess features from InteractiveSubprocessOrchestrator
   - PTY support from PTYOrchestrator
   - Any unique features from other implementations

2. Ensure all features are preserved:
   - Framework injection methods
   - Session management
   - Hook integration
   - Ticket extraction
   - Agent delegation

### Phase 3: Update Dependencies
1. Update imports in:
   - `cli.py` - Use new factory
   - `cli_main.py` - Import new orchestrators
   - Test files - Update orchestrator references

2. Update orchestrator selection logic:
   - Simplify mode determination
   - Remove obsolete flags

### Phase 4: Testing & Validation
1. Run E2E tests with new orchestrators
2. Test each mode:
   - Interactive sessions
   - Non-interactive runs
   - Subprocess delegations
3. Verify feature parity

### Phase 5: Cleanup
1. Move old implementations to archive:
   ```bash
   mkdir -p src/claude_mpm/orchestration/archive
   mv src/claude_mpm/orchestration/*_orchestrator.py src/claude_mpm/orchestration/archive/
   # Keep only new implementations
   ```

2. Update documentation:
   - Update STRUCTURE.md
   - Create orchestrator selection guide
   - Update examples

3. Remove backup files:
   ```bash
   find . -name "*.bak" -delete
   ```

## Code Reduction Analysis

### Before
- 16 orchestrator files
- ~5000+ lines of orchestrator code
- Significant duplication

### After
- 3 orchestrator files + 1 base class
- ~1500 lines of orchestrator code
- 70% code reduction
- Clear separation of concerns

## Risk Mitigation

1. **Feature Loss**: Carefully audit each orchestrator for unique features
2. **Breaking Changes**: Maintain API compatibility through factory
3. **Test Coverage**: Ensure comprehensive testing before removing old code
4. **Rollback Plan**: Keep archive of old implementations for 1 release cycle

## Success Metrics

1. Only 3 orchestrator implementations remain
2. All existing functionality preserved
3. Clear documentation on orchestrator selection
4. Simplified factory pattern
5. 60-70% reduction in orchestration code

## Timeline

- Phase 1-2: 1 day (implementation)
- Phase 3-4: 1 day (integration & testing)
- Phase 5: 0.5 days (cleanup)
- Total: 2.5 days

## Next Steps

1. Review and approve this plan
2. Complete Phase 2 feature integration
3. Begin systematic migration
4. Test thoroughly before cleanup