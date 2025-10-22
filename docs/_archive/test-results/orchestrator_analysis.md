# Orchestrator Analysis for ISS-0002

## Current State Analysis

### Orchestrator Inventory

Based on the codebase analysis, we have the following orchestrators:

1. **MPMOrchestrator** (`orchestrator.py`) - Base orchestrator with subprocess management
2. **SubprocessOrchestrator** (`subprocess_orchestrator.py`) - Primary orchestrator using ClaudeLauncher
3. **SystemPromptOrchestrator** (`system_prompt_orchestrator.py`) - Uses Claude's --system-prompt flag
4. **InteractiveSubprocessOrchestrator** (`interactive_subprocess_orchestrator.py`) - Uses pexpect for interactive control
5. **SimpleOrchestrator** (`simple_orchestrator.py`) - Uses Claude's print mode
6. **DirectOrchestrator** (`direct_orchestrator.py`) - Runs Claude with minimal intervention
7. **WrapperOrchestrator** (`wrapper_orchestrator.py`) - Creates wrapper scripts
8. **PTYOrchestrator** (`pty_orchestrator.py`) - Uses Python's pty module
9. **PexpectOrchestrator** (`pexpect_orchestrator.py`) - Uses pexpect library
10. **HookEnabledOrchestrator** (`hook_enabled_orchestrator.py`) - Example with hook integration

### Feature Analysis

#### Core Features Present in Most Orchestrators:
- Framework injection
- Ticket extraction
- Agent delegation
- Hook service integration
- Logging and session management

#### Key Differences:
1. **Subprocess Management Approach**:
   - SubprocessOrchestrator: Uses ClaudeLauncher (unified approach)
   - MPMOrchestrator: Direct subprocess.Popen
   - PTYOrchestrator: Python's pty module
   - PexpectOrchestrator: pexpect library
   - InteractiveSubprocessOrchestrator: pexpect with process monitoring

2. **Framework Injection Method**:
   - SystemPromptOrchestrator: --system-prompt flag
   - WrapperOrchestrator: Wrapper script generation
   - Others: Direct injection via stdin

3. **Session Type Support**:
   - Interactive: MPMOrchestrator, PTYOrchestrator, PexpectOrchestrator
   - Non-interactive: SubprocessOrchestrator, SimpleOrchestrator
   - Both: SystemPromptOrchestrator, InteractiveSubprocessOrchestrator

### Consolidation Strategy

#### Target Architecture (3 Core Orchestrators):

1. **SubprocessOrchestrator** (Primary)
   - Uses ClaudeLauncher for unified subprocess management
   - Supports both interactive and non-interactive modes
   - Includes TODO hijacking, hook integration, agent delegation
   - Already well-structured and feature-complete

2. **SystemPromptOrchestrator** (Alternative)
   - For scenarios requiring --system-prompt flag
   - Cleaner approach when Claude CLI supports it
   - Maintains compatibility with existing features

3. **DirectOrchestrator** (Minimal)
   - For simple use cases without complex orchestration
   - Minimal overhead, direct Claude execution
   - Good for testing and debugging

#### Orchestrators to Remove:
- MPMOrchestrator (redundant with SubprocessOrchestrator)
- SimpleOrchestrator (can be mode in DirectOrchestrator)
- WrapperOrchestrator (overly complex, rarely used)
- PTYOrchestrator (functionality covered by SubprocessOrchestrator)
- PexpectOrchestrator (functionality covered by SubprocessOrchestrator)
- InteractiveSubprocessOrchestrator (merge features into SubprocessOrchestrator)
- HookEnabledOrchestrator (just an example, not needed)

### Implementation Plan

1. **Phase 1: Feature Consolidation**
   - Merge InteractiveSubprocessOrchestrator features into SubprocessOrchestrator
   - Add session mode parameter to SubprocessOrchestrator
   - Ensure all features are preserved

2. **Phase 2: Create Base Class**
   - Extract common functionality into BaseOrchestrator
   - Implement strategy pattern for variations
   - Standardize interfaces

3. **Phase 3: Update Factory**
   - Simplify OrchestratorMode enum to 3 options
   - Update factory to use new structure
   - Add clear documentation on when to use each

4. **Phase 4: Remove Deprecated**
   - Remove redundant orchestrator files
   - Update all imports and references
   - Clean up related test files