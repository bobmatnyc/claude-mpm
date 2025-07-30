# Agent Memory System Implementation Plan

**Document Version:** 1.0  
**Date:** July 30, 2025  
**Status:** Active Development  
**Feature Branch:** `feature/agent-memory-system`

## Executive Summary

This document outlines the implementation approach for the Agent Memory System, addressing key questions and providing a phased development plan. The system will enable agents to accumulate project-specific knowledge while maintaining simplicity and developer control.

**Deployment Model**: This feature is designed for local claude-mpm installations. Memory files are stored locally in each project's `.claude-mpm/memories/` directory and are project-specific.

## Implementation Decisions

### 1. Scope & Priority

**Decision**: Implement in phases, starting with Phase 1 (Core System)

- **Phase 1 Focus**: Core memory manager, basic file operations, and manual CLI commands
- **Initial Agents**: Start with 3 core agents:
  - Research Agent (most likely to discover patterns)
  - Engineer Agent (implements based on research)
  - QA Agent (validates implementations)
- **Expansion**: Add remaining agents (Documentation, Security, Ops, Data Engineer) in Phase 2

**Rationale**: This allows us to validate the core concept with the most active agents before full rollout.

### 2. Memory Persistence & Learning

**Decision**: Opt-in automatic learning with manual override

- **Default State**: Memory reading enabled, automatic learning disabled
- **Enable Learning**: Via CLI flag `--enable-learning` or config setting
- **Pattern Matching**: Start with regex patterns, add NLP in future phase
- **Learning Formats**:
  ```
  Pattern: "Discovered pattern: [description]"
  Mistake: "Mistake: [what went wrong]"
  Guideline: "Best practice: [guideline]"
  Architecture: "Architecture: [insight]"
  ```

**Rationale**: Prevents noise in memory files while allowing power users to enable automatic learning.

### 3. Integration Points

**Decision**: Minimal invasive changes with new modules

- **New Modules**:
  - `src/claude_mpm/services/agent_memory_manager.py`
  - `src/claude_mpm/hooks/memory_integration_hook.py`
  - `src/claude_mpm/cli/commands/memory.py`
- **Modified Files**:
  - `src/claude_mpm/services/hook_service.py` (register memory hooks)
  - `src/claude_mpm/core/config.py` (add memory settings)
- **Integration Flow**:
  1. Hook service loads memory hooks if enabled
  2. Pre-delegation hook injects memory into context
  3. Post-delegation hook extracts learnings (if enabled)

**Rationale**: Maintains separation of concerns and makes feature easy to disable.

### 4. File Management

**Decision**: Track in version control with automatic deployment

- **Version Control**: Memory files ARE tracked (not in .gitignore)
- **Location**: `.claude-mpm/memories/` directory (automatic deployment)
- **Automatic Creation**: Memory directory and files created on first use
- **Size Limits**:
  - Default: 8KB (configurable in config.yml)
  - Per-agent overrides supported
  - Auto-truncation removes oldest items from "Recent Learnings"
- **File Naming**: `{agent_id}_agent.md` (e.g., `research_agent.md`)

**Rationale**: Team knowledge sharing and transparency outweigh merge conflict concerns.

### 5. User Control

**Decision**: Full control with sensible defaults

- **CLI Flags**:
  - `--no-memory`: Disable memory for specific run
  - `--enable-learning`: Enable automatic learning extraction
  - `--memory-limit KB`: Override size limit for session
- **Validation**:
  - Soft validation: Warn on schema violations
  - Auto-repair: Fix common issues (missing sections, timestamps)
  - Never fail on memory errors (graceful degradation)
- **Manual Editing**: Fully supported with validation on next load

**Rationale**: Memory should enhance, never hinder, agent operations.

### 6. Testing Strategy

**Decision**: Comprehensive test coverage with fixtures

- **Test Fixtures**:
  - `tests/fixtures/memories/` with sample memory files
  - Various states: empty, full, corrupted, over-limit
- **Test Categories**:
  - Unit tests for memory manager operations
  - Integration tests for hook system
  - E2E tests for full delegation flow with memory
- **Learning Pattern Tests**:
  - Regex pattern matching validation
  - Edge case handling (multiline, special characters)
  - Performance tests for large files

**Rationale**: Memory system must be reliable and predictable.

### 7. Backwards Compatibility

**Decision**: Full backwards compatibility maintained

- **Agent Templates**: No required changes (memory injection is additive)
- **Opt-in Enhancement**: Agents can add memory-aware instructions later
- **Graceful Degradation**: System works without memory files
- **Migration Path**:
  1. Deploy system with memory disabled by default
  2. Create memory files for agents gradually
  3. Enable memory reading (safe, read-only)
  4. Enable learning extraction for specific agents
  5. Update agent templates to be memory-aware

**Rationale**: Zero disruption to existing workflows.

## Implementation Phases

### Phase 1: Core System (Week 1)
**Goal**: Basic memory infrastructure

1. **Day 1-2**: Core Implementation
   - Create `AgentMemoryManager` service
   - Implement file operations (load, save, validate)
   - Add size limit enforcement and truncation

2. **Day 3-4**: CLI Integration
   - Create memory command group
   - Implement view, add, status commands
   - Add configuration options

3. **Day 5**: Testing & Documentation
   - Unit tests for memory manager
   - Create test fixtures
   - Write user documentation

**Deliverables**:
- Working memory manager service
- CLI commands for manual memory management
- Test coverage >80% for new code

### Phase 2: Hook Integration (Week 2)
**Goal**: Automatic memory injection and learning

1. **Day 1-2**: Hook Implementation
   - Create pre/post delegation hooks
   - Implement memory injection logic
   - Add learning extraction patterns

2. **Day 3-4**: Integration Testing
   - Test with real agent delegations
   - Validate memory updates
   - Performance testing

3. **Day 5**: Agent Expansion
   - Add memory files for remaining agents
   - Test with all agent types
   - Document agent-specific patterns

**Deliverables**:
- Working hook system
- Memory files for all agents
- Integration test suite

### Phase 3: Agent Template Enhancement (Week 3)
**Goal**: Memory-aware agent behavior

1. **Day 1-3**: Template Updates
   - Update Research, Engineer, QA templates
   - Add memory-aware instructions
   - Test improved agent behavior

2. **Day 4-5**: Remaining Agents
   - Update Documentation, Security, Ops, Data Engineer
   - Validate learning capture
   - Fine-tune extraction patterns

**Deliverables**:
- All agents memory-aware
- Improved agent effectiveness
- Learning capture validation

### Phase 4: Polish & Optimization (Week 4)
**Goal**: Production readiness

1. **Day 1-2**: Performance
   - Optimize file operations
   - Add caching layer
   - Benchmark impact

2. **Day 3-4**: Advanced Features
   - Memory cleanup utilities
   - Export/import commands
   - Memory diff visualization

3. **Day 5**: Release Preparation
   - Final documentation
   - Migration guide
   - Release notes

**Deliverables**:
- Production-ready system
- Complete documentation
- Performance benchmarks

## Configuration Schema

```yaml
# .claude-mpm/config.yml
memory:
  enabled: true                    # Master switch
  auto_learning: false            # Automatic learning extraction
  limits:
    default_size_kb: 8            # Default file size limit
    max_sections: 10              # Maximum sections per file
    max_items_per_section: 15     # Maximum items per section
  agent_overrides:
    research_agent:
      size_kb: 16                 # Research agent can have larger memory
      auto_learning: true         # Enable learning for research
    qa_agent:
      auto_learning: true         # QA agent learns from test results
```

## Local Deployment Architecture

**Memory Storage Model**:
- **Per-Project**: Each project has its own `.claude-mpm/memories/` directory
- **Local Only**: Memory files are stored on the user's local filesystem
- **No Cloud Sync**: Memory remains private to each installation
- **Version Control**: Teams can share memory via git if desired

**Benefits for Local Deployment**:
1. **Privacy**: All learnings stay on local machine
2. **Customization**: Each project develops unique agent knowledge
3. **No Dependencies**: Works offline, no external services required
4. **Team Sharing**: Optional via version control

**Directory Hierarchy**:
```
~/Projects/
├── project-a/
│   └── .claude-mpm/
│       └── memories/           # Project A's agent memories
├── project-b/
│   └── .claude-mpm/
│       └── memories/           # Project B's agent memories
└── project-c/
    └── .claude-mpm/
        └── memories/           # Project C's agent memories
```

Each project maintains completely independent agent memories, allowing agents to specialize for each codebase.

## Risk Mitigation

### Performance Impact
- **Risk**: Memory loading slows delegations
- **Mitigation**: 
  - Lazy loading only when needed
  - In-memory caching with TTL
  - Size limits prevent large files

### Memory Noise
- **Risk**: Irrelevant information accumulates
- **Mitigation**:
  - Manual curation encouraged
  - Cleanup utilities provided
  - Learning patterns refined over time

### Merge Conflicts
- **Risk**: Team members edit same memory files
- **Mitigation**:
  - Structured format reduces conflicts
  - Section-based organization
  - Clear ownership guidelines

## Success Metrics

1. **Adoption**: 80% of delegations use memory within 1 month
2. **Effectiveness**: 25% reduction in repeated mistakes
3. **Performance**: <50ms overhead per delegation
4. **Quality**: 90% of captured learnings are relevant
5. **Stability**: Zero memory-related failures in production

## Next Steps

1. **Immediate**: Begin Phase 1 implementation
2. **Week 1**: Deploy core system to test environment
3. **Week 2**: Start hook integration with select users
4. **Week 3**: Update agent templates based on feedback
5. **Week 4**: Production deployment with gradual rollout

This plan provides a pragmatic approach to implementing the agent memory system while maintaining stability and backwards compatibility. The phased approach allows for validation and refinement at each stage.