# Claude MPM Agent Memory System - Complete Design & Implementation

**Document Version:** 2.0  
**Date:** August 5, 2025  
**Status:** Implementation Ready  
**Scope:** Complete design and implementation guide for agent memory system

## Overview and Intent

The Agent Memory System enables Claude MPM agents to accumulate and persist project-specific knowledge in publicly visible markdown files. This creates adaptive agents that become progressively smarter about specific codebases over time while maintaining full developer visibility and control.

### Key Principles

- **Project-Specific Learning**: Each project maintains independent agent memories
- **Local Storage**: All memory files stored locally in `.claude-mpm/memories/`
- **Public Visibility**: Memory files are human-readable markdown, version controlled
- **Developer Control**: Full manual editing capabilities with graceful degradation
- **Incremental Intelligence**: Agents become more effective through accumulated experience

### Benefits

**For Agents:**
- Project-specific intelligence accumulated over time
- Reduced repetition of learning same patterns
- Better decision making based on project history
- Adaptive behavior that improves with experience

**For Developers:**
- Full transparency into what agents have learned
- Manual control over agent knowledge and behavior
- Collaborative improvement through team editing
- Version control integration for team knowledge sharing

**For Project Quality:**
- Consistent patterns applied across development
- Institutional knowledge preservation
- Reduced onboarding time for new team members
- Better code quality through accumulated best practices

## Architecture and Design

### Directory Structure

```
claude-mpm/
├── .claude-mpm/
│   ├── memories/
│   │   ├── README.md                 # System documentation
│   │   ├── research_agent.md         # Research agent project memory
│   │   ├── engineer_agent.md         # Engineer agent project memory
│   │   ├── qa_agent.md              # QA agent project memory
│   │   ├── documentation_agent.md    # Documentation agent memory
│   │   ├── security_agent.md        # Security agent project memory
│   │   ├── ops_agent.md             # Ops agent project memory
│   │   └── data_engineer_agent.md   # Data engineer project memory
├── src/claude_mpm/
│   ├── services/
│   │   └── agent_memory_manager.py  # Memory management service
│   ├── hooks/
│   │   └── memory_integration_hook.py  # Memory system hooks
│   └── cli/commands/
│       └── memory.py                # Memory CLI commands
└── docs/
    └── agent_memory_guide.md       # User documentation
```

### Local Deployment Model

**Memory Storage:**
- **Per-Project**: Each project has its own `.claude-mpm/memories/` directory
- **Local Only**: Memory files are stored on the user's local filesystem
- **No Cloud Sync**: Memory remains private to each installation
- **Version Control**: Teams can share memory via git if desired

**Directory Hierarchy:**
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

## Memory Types and Structure

### Static Context Limits (Phase 1)

```yaml
# Memory file constraints for initial implementation
memory_limits:
  max_file_size_kb: 8        # ~2000 tokens
  max_sections: 10           # Structured organization
  max_items_per_section: 15  # Prevent information overload
  max_line_length: 120       # Readable formatting
  auto_truncate: true        # Enforce limits automatically
```

### Standard Memory File Template

```markdown
# {Agent Name} Memory - {Project Name}

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: {timestamp} | Auto-updated by: {agent_id} -->

## Project Architecture (Max: 15 items)
- Service-oriented architecture with clear module boundaries
- Three-tier agent hierarchy: project → user → system
- Agent definitions use standardized JSON schema validation
- Factory and Strategy patterns used throughout orchestration layer
- Core services in src/claude_mpm/services/ handle business logic

## Coding Patterns Learned (Max: 15 items)
- Always use PathResolver for path operations, never hardcode paths
- SubprocessRunner utility for external command execution
- LoggerMixin provides consistent logging across all services
- Schema validation required for all agent definitions
- Error handling follows three-attempt protocol with escalation

## Implementation Guidelines (Max: 15 items)
- Check docs/STRUCTURE.md before creating new files
- Follow existing import patterns: from claude_mpm.module import Class
- Use existing utilities instead of reimplementing functionality
- All new services inherit from EnhancedBaseService base class
- Integration tests required for orchestrator modifications

## Domain-Specific Knowledge (Max: 15 items)
<!-- Agent-specific knowledge accumulates here -->

## Effective Strategies (Max: 15 items)
<!-- Successful approaches discovered through experience -->

## Common Mistakes to Avoid (Max: 15 items)
- Don't modify Claude Code core functionality, only extend it
- Avoid duplicating code - check utils/ for existing implementations
- Never hardcode file paths, use PathResolver utilities
- Don't skip validation when creating new agents or configurations

## Integration Points (Max: 15 items)
<!-- Key interfaces and integration patterns -->

## Performance Considerations (Max: 15 items)
<!-- Performance insights and optimization patterns -->

## Current Technical Context (Max: 15 items)
- EP-0001: Technical debt reduction in progress
- Target: 80% test coverage (current: 23.6%)
- Code duplication reduced to ~8-10% (target: <10%)
- Focus: Completing god class refactoring and complexity reduction
- Integration with Claude Code 1.0.60+ native agent framework

## Recent Learnings (Max: 15 items)
<!-- Most recent discoveries and insights -->
```

### Agent-Specific Memory Examples

#### Research Agent Memory
```markdown
# Research Agent Memory - claude-mpm

## Project Architecture (Max: 15 items)
- Codebase uses service-oriented architecture with 72 service files
- Agent definitions in src/claude_mpm/agents/templates/ with standardized schema
- Tree-sitter integration enables AST-level code analysis for 41+ languages
- PathResolver utility centralizes all path operations with caching
- Three-tier hierarchy: project (.claude-mpm/) → user (~/.claude-mpm/) → system

## Research Strategies Learned (Max: 15 items)
- Start with docs/STRUCTURE.md for file organization understanding
- Use tree-sitter for semantic code analysis, not just grep patterns
- Check existing utilities in utils/ before suggesting new implementations
- Agent registry follows precedence rules - check all tiers
- Focus on src/claude_mpm/services/ for business logic patterns

## Effective Analysis Patterns (Max: 15 items)
- Combine `find`, `grep`, and `tree-sitter` for comprehensive codebase analysis
- Look for import patterns to understand module dependencies
- Check test files for usage examples and expected behaviors
- Examine recent tickets/ for current development priorities
- Use glob patterns for targeted file discovery

## Integration Points (Max: 15 items)
- AgentRegistryAdapter is main entry point for agent discovery
- FrameworkLoader handles INSTRUCTIONS.md generation and template processing
- SubprocessOrchestrator manages agent delegation through Claude's Task tool
- HookService provides extensibility points for workflow automation
- PathResolver handles all path resolution with project/user/system precedence

## Current Technical Context (Max: 15 items)
- EP-0001 focuses on code complexity reduction (40 functions >10 complexity)
- God class refactoring in progress (7 classes with 20+ methods)
- Test coverage improvement from 23.6% toward 80% target
- Code duplication eliminated through utility consolidation
- Agent schema standardization for predictable behavior
```

#### Engineer Agent Memory
```markdown
# Engineer Agent Memory - claude-mpm

## Implementation Patterns (Max: 15 items)
- Follow service-oriented architecture - create services in src/claude_mpm/services/
- Use Factory pattern for orchestrator creation (OrchestratorFactory)
- Inherit from EnhancedBaseService for consistent service behavior
- Apply LoggerMixin for standardized logging across all classes
- Use PathResolver for all path operations, never hardcode paths

## Code Quality Standards (Max: 15 items)
- Maximum function complexity: 10 (current focus of EP-0001)
- Classes should have <20 methods (god class refactoring in progress)
- Use type hints for all function parameters and return values
- Follow existing import patterns: from claude_mpm.module import Class
- All new code requires corresponding tests per docs/QA.md

## Common Implementation Patterns (Max: 15 items)
- Services use dependency injection through constructor parameters
- Error handling follows three-attempt protocol with escalation to TodoWrite
- Configuration loading uses YAML with validation and schema checking
- File operations use atomic writes with backup/rollback capabilities
- Subprocess execution always uses SubprocessRunner utility

## Integration Requirements (Max: 15 items)
- New orchestrators must implement MPMOrchestrator base class
- Agent definitions require schema validation before deployment
- Hook system integration for extensible workflow automation
- CLI commands follow click framework patterns in src/claude_mpm/cli/
- All services must support graceful shutdown and resource cleanup

## Current Technical Context (Max: 15 items)
- Complexity reduction: Target all functions <10 complexity
- Utility integration: SubprocessRunner, PathOperations, ConfigurationManager applied
- Test coverage: Focus on orchestration layer and core services
- Performance: Optimize agent discovery and initialization time
- Claude integration: Work with native Task tool, don't replace it
```

## Implementation Details

### 1. Agent Memory Manager Service

```python
# File: src/claude_mpm/services/agent_memory_manager.py

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

from claude_mpm.core import LoggerMixin
from claude_mpm.utils.paths import PathResolver


class AgentMemoryManager(LoggerMixin):
    """Manages agent memory files with size limits and validation."""
    
    MEMORY_LIMITS = {
        'max_file_size_kb': 8,
        'max_sections': 10,
        'max_items_per_section': 15,
        'max_line_length': 120
    }
    
    REQUIRED_SECTIONS = [
        'Project Architecture',
        'Implementation Guidelines', 
        'Common Mistakes to Avoid',
        'Current Technical Context'
    ]
    
    def __init__(self):
        super().__init__()
        self.project_root = PathResolver.get_project_root()
        self.memories_dir = self.project_root / ".claude-mpm" / "memories"
        self._ensure_memories_directory()
    
    def load_agent_memory(self, agent_id: str) -> str:
        """Load agent memory file content."""
        memory_file = self.memories_dir / f"{agent_id}.md"
        
        if not memory_file.exists():
            return self._create_default_memory(agent_id)
        
        content = memory_file.read_text()
        return self._validate_and_repair(content, agent_id)
    
    def update_agent_memory(self, agent_id: str, section: str, new_item: str) -> bool:
        """Add new learning item to specified section."""
        current_memory = self.load_agent_memory(agent_id)
        updated_memory = self._add_item_to_section(current_memory, section, new_item)
        
        # Enforce limits
        if self._exceeds_limits(updated_memory):
            updated_memory = self._truncate_to_limits(updated_memory)
        
        # Save with timestamp
        return self._save_memory_file(agent_id, updated_memory)
    
    def add_learning(self, agent_id: str, learning_type: str, content: str) -> bool:
        """Add structured learning to appropriate section."""
        section_mapping = {
            'pattern': 'Coding Patterns Learned',
            'architecture': 'Project Architecture', 
            'guideline': 'Implementation Guidelines',
            'mistake': 'Common Mistakes to Avoid',
            'strategy': 'Effective Strategies',
            'integration': 'Integration Points',
            'performance': 'Performance Considerations'
        }
        
        section = section_mapping.get(learning_type, 'Recent Learnings')
        return self.update_agent_memory(agent_id, section, content)
    
    def _create_default_memory(self, agent_id: str) -> str:
        """Create default memory file for agent."""
        agent_name = agent_id.replace('_', ' ').title()
        project_name = self.project_root.name
        
        template = f"""# {agent_name} Memory - {project_name}

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-updated by: {agent_id} -->

## Project Architecture (Max: 15 items)
- Service-oriented architecture with clear module boundaries
- Three-tier agent hierarchy: project → user → system
- Agent definitions use standardized JSON schema validation

## Implementation Guidelines (Max: 15 items)
- Check docs/STRUCTURE.md before creating new files
- Follow existing import patterns: from claude_mpm.module import Class
- Use existing utilities instead of reimplementing functionality

## Common Mistakes to Avoid (Max: 15 items)
- Don't modify Claude Code core functionality, only extend it
- Avoid duplicating code - check utils/ for existing implementations
- Never hardcode file paths, use PathResolver utilities

## Current Technical Context (Max: 15 items)
- EP-0001: Technical debt reduction in progress
- Target: 80% test coverage (current: 23.6%)
- Integration with Claude Code 1.0.60+ native agent framework

## Recent Learnings (Max: 15 items)
<!-- New learnings will be added here -->
"""
        
        # Save default file
        memory_file = self.memories_dir / f"{agent_id}.md"
        memory_file.write_text(template)
        return template
    
    def _add_item_to_section(self, content: str, section: str, new_item: str) -> str:
        """Add item to specified section, respecting limits."""
        lines = content.split('\n')
        section_start = None
        section_end = None
        
        # Find section boundaries
        for i, line in enumerate(lines):
            if line.startswith(f'## {section}'):
                section_start = i
            elif section_start is not None and line.startswith('## '):
                section_end = i
                break
        
        if section_start is None:
            # Section doesn't exist, add it
            return self._add_new_section(content, section, new_item)
        
        if section_end is None:
            section_end = len(lines)
        
        # Count existing items in section
        item_count = 0
        for i in range(section_start + 1, section_end):
            if lines[i].strip().startswith('- '):
                item_count += 1
        
        # Check if we can add more items
        if item_count >= self.MEMORY_LIMITS['max_items_per_section']:
            # Remove oldest item (first one) to make room
            for i in range(section_start + 1, section_end):
                if lines[i].strip().startswith('- '):
                    lines.pop(i)
                    break
        
        # Add new item (find insertion point)
        insert_point = section_start + 1
        while insert_point < section_end and not lines[insert_point].strip().startswith('- '):
            insert_point += 1
        
        lines.insert(insert_point, f"- {new_item}")
        
        # Update timestamp
        updated_content = '\n'.join(lines)
        return self._update_timestamp(updated_content)
    
    def _exceeds_limits(self, content: str) -> bool:
        """Check if content exceeds size limits."""
        size_kb = len(content.encode('utf-8')) / 1024
        return size_kb > self.MEMORY_LIMITS['max_file_size_kb']
    
    def _truncate_to_limits(self, content: str) -> str:
        """Truncate content to fit within limits."""
        # Simple truncation strategy: remove oldest items from "Recent Learnings"
        lines = content.split('\n')
        
        # Find Recent Learnings section and remove items until under limit
        while self._exceeds_limits('\n'.join(lines)):
            removed = False
            
            for i, line in enumerate(lines):
                if line.startswith('## Recent Learnings'):
                    # Find and remove first item in this section
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith('- '):
                            lines.pop(j)
                            removed = True
                            break
                        elif lines[j].startswith('## '):
                            break
                    break
            
            if not removed:
                # Fallback: truncate from end
                lines = lines[:-10]
        
        return '\n'.join(lines)
    
    def _update_timestamp(self, content: str) -> str:
        """Update the timestamp in the file header."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return re.sub(
            r'<!-- Last Updated: .+ \| Auto-updated by: .+ -->',
            f'<!-- Last Updated: {timestamp} | Auto-updated by: system -->',
            content
        )
    
    def _ensure_memories_directory(self):
        """Ensure memories directory exists with README."""
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        
        readme_path = self.memories_dir / "README.md"
        if not readme_path.exists():
            readme_content = """# Agent Memory System

## Purpose
Each agent maintains project-specific knowledge in these files. Agents read their memory file before tasks and update it when they learn something new.

## Manual Editing
Feel free to edit these files to:
- Add project-specific guidelines
- Remove outdated information  
- Reorganize for better clarity
- Add domain-specific knowledge

## Memory Limits
- Max file size: 8KB (~2000 tokens)
- Max sections: 10
- Max items per section: 15
- Files auto-truncate when limits exceeded

## File Format
Standard markdown with structured sections. Agents expect:
- Project Architecture
- Implementation Guidelines
- Common Mistakes to Avoid
- Current Technical Context

## How It Works
1. Agents read their memory file before starting tasks
2. Agents add learnings during or after task completion
3. Files automatically enforce size limits
4. Developers can manually edit for accuracy

## Memory File Lifecycle
- Created automatically when agent first runs
- Updated through hook system after delegations
- Manually editable by developers
- Version controlled with project
"""
            readme_path.write_text(readme_content)
```

### 2. Memory Integration Hook

```python
# File: src/claude_mpm/hooks/memory_integration_hook.py

from claude_mpm.hooks.base_hook import PreDelegationHook, PostDelegationHook
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from typing import Dict, Any
import re


class MemoryPreDelegationHook(PreDelegationHook):
    """Inject agent memory into delegation context."""
    
    def __init__(self):
        super().__init__()
        self.memory_manager = AgentMemoryManager()
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add agent memory to delegation context."""
        agent_id = context.get('agent', '').lower().replace(' ', '_').replace('agent', '').strip('_')
        
        if agent_id:
            # Load agent memory
            memory_content = self.memory_manager.load_agent_memory(agent_id)
            
            # Add to context with clear formatting
            context['agent_memory'] = f"""
AGENT MEMORY - PROJECT-SPECIFIC KNOWLEDGE:
{memory_content}

INSTRUCTIONS: Review your memory above before proceeding. Apply learned patterns and avoid known mistakes.
"""
        
        return context


class MemoryPostDelegationHook(PostDelegationHook):
    """Extract learnings from delegation results."""
    
    def __init__(self):
        super().__init__()
        self.memory_manager = AgentMemoryManager()
        
        # Map of supported types to memory sections
        self.type_mapping = {
            'pattern': 'pattern',           # Coding Patterns Learned
            'architecture': 'architecture', # Project Architecture
            'guideline': 'guideline',      # Implementation Guidelines
            'mistake': 'mistake',          # Common Mistakes to Avoid
            'strategy': 'strategy',        # Effective Strategies
            'integration': 'integration',  # Integration Points
            'performance': 'performance',  # Performance Considerations
            'context': 'context'           # Current Technical Context
        }
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and store learnings from delegation result."""
        agent_id = context.get('agent', '').lower().replace(' ', '_').replace('agent', '').strip('_')
        result_text = context.get('result', {}).get('content', '')
        
        if agent_id and result_text:
            # Extract learnings using patterns
            learnings = self._extract_learnings(result_text)
            
            # Store each learning
            for learning_type, items in learnings.items():
                for item in items:
                    self.memory_manager.add_learning(agent_id, learning_type, item)
        
        return context
    
    def _extract_learnings(self, text: str) -> Dict[str, List[str]]:
        """Extract structured learnings from text using explicit markers."""
        learnings = {learning_type: [] for learning_type in self.type_mapping.keys()}
        seen_learnings = set()  # Avoid duplicates
        
        # Pattern to find memory blocks: # Add To Memory:\n...\n#
        memory_pattern = r'#\s*Add\s+To\s+Memory:\s*\n((?:(?!#\s*Add\s+To\s+Memory:)(?!^\s*#\s*$).)*?)\n\s*#\s*$'
        matches = re.finditer(memory_pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            block_content = match.group(1).strip()
            
            # Extract type and content from the block
            type_match = re.search(r'Type:\s*(\w+)', block_content, re.IGNORECASE)
            content_match = re.search(r'Content:\s*(.+)', block_content, re.IGNORECASE | re.DOTALL)
            
            if type_match and content_match:
                learning_type = type_match.group(1).lower().strip()
                content = content_match.group(1).strip()
                
                # Clean up multi-line content - take first line if multiple
                if '\n' in content:
                    content = content.split('\n')[0].strip()
                
                # Validate type is supported and check content length
                if learning_type in self.type_mapping and 5 < len(content) <= 100:
                    # Normalize for duplicate detection
                    normalized = content.lower()
                    if normalized not in seen_learnings:
                        learnings[learning_type].append(content)
                        seen_learnings.add(normalized)
        
        return learnings
```

## API and Interfaces

### Configuration Schema

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

### CLI Commands

```python
# File: src/claude_mpm/cli/commands/memory.py

import click
from claude_mpm.services.agent_memory_manager import AgentMemoryManager


@click.group()
def memory():
    """Manage agent memory files."""
    pass


@memory.command()
def status():
    """Show memory file status."""
    memory_manager = AgentMemoryManager()
    # Show file sizes, last updated, etc.


@memory.command()
@click.argument('agent_id')
@click.argument('learning_type')
@click.argument('content')
def add(agent_id, learning_type, content):
    """Manually add learning to agent memory."""
    memory_manager = AgentMemoryManager()
    if memory_manager.add_learning(agent_id, learning_type, content):
        click.echo(f"✅ Added {learning_type} to {agent_id} memory")
    else:
        click.echo(f"❌ Failed to add learning")


@memory.command()
@click.argument('agent_id')
def view(agent_id):
    """View agent memory file."""
    memory_manager = AgentMemoryManager()
    content = memory_manager.load_agent_memory(agent_id)
    click.echo(content)


@memory.command()
def clean():
    """Clean up old/unused memory files."""
    # Implementation for cleanup
    pass
```

### Enhanced Agent Instructions Template

```markdown
# Agent Instructions Template with Memory Integration

## Core Agent Identity
You are the {Agent Name} specialized for {domain expertise}.

## MEMORY INTEGRATION PROTOCOL
**CRITICAL**: You have access to project-specific memory in your context. This memory contains:
- Patterns you've learned about this specific project
- Successful strategies from previous tasks
- Mistakes to avoid based on past experience
- Current project context and priorities

**ALWAYS**:
1. Read your AGENT MEMORY section carefully before starting
2. Apply learned patterns and avoid known mistakes
3. When you discover new patterns, state them clearly for memory capture
4. When you make mistakes, explicitly identify them for future avoidance

## Memory Learning Protocol

### Explicit Memory Markers (Recommended)
For precise control over what gets memorized, use the following format:

```
# Add To Memory:
Type: pattern
Content: All services use dependency injection for flexibility
#
```

**Supported Types:**
- `pattern` - Coding patterns and conventions
- `architecture` - Architectural insights and design decisions
- `guideline` - Implementation guidelines and best practices
- `mistake` - Common mistakes to avoid
- `strategy` - Effective problem-solving strategies
- `integration` - Integration points and dependencies
- `performance` - Performance considerations and optimizations
- `context` - Current technical context and environment details

**Guidelines:**
- Keep content under 100 characters for quick reference
- Be specific and actionable
- Use multiple blocks for multiple learnings
- The markers are case-insensitive

### Legacy Pattern Recognition (Deprecated)
The system also recognizes natural language patterns:

**Pattern Discovery**: "Discovered pattern: [specific pattern]"
**Best Practice**: "Best practice: [specific guideline]" 
**Mistake Identification**: "Mistake: [what went wrong and why]"
**Architecture Insight**: "Architecture: [structural understanding]"

Note: The explicit marker format is preferred for reliability.

## Standard Task Execution
[Existing agent instructions continue here...]

## Memory-Enhanced Decision Making
Before executing any task:
1. Review your memory for relevant patterns
2. Check for similar past experiences
3. Apply learned optimizations
4. Avoid documented mistakes

Your memory makes you progressively better at this specific project. Use it wisely.
```

## Workflow and Operations

### Integration with Existing Systems

#### 1. Framework Generator Integration
```python
# Update to include memory in agent context generation
def generate_agent_instructions(self, agent_id: str) -> str:
    base_instructions = self.load_agent_template(agent_id)
    memory_content = self.memory_manager.load_agent_memory(agent_id)
    
    return f"""
{base_instructions}

## PROJECT-SPECIFIC MEMORY
{memory_content}
"""
```

#### 2. Hook Service Registration
```python
# File: src/claude_mpm/services/hook_service.py (enhancement)

def register_memory_hooks(self):
    """Register memory integration hooks."""
    pre_hook = MemoryPreDelegationHook()
    post_hook = MemoryPostDelegationHook()
    
    self.register_hook('pre_delegation', pre_hook)
    self.register_hook('post_delegation', post_hook)
```

### Implementation Decisions

#### 1. Scope & Priority
**Decision**: Implement in phases, starting with Phase 1 (Core System)

- **Phase 1 Focus**: Core memory manager, basic file operations, and manual CLI commands
- **Initial Agents**: Start with 3 core agents:
  - Research Agent (most likely to discover patterns)
  - Engineer Agent (implements based on research)
  - QA Agent (validates implementations)
- **Expansion**: Add remaining agents (Documentation, Security, Ops, Data Engineer) in Phase 2

**Rationale**: This allows us to validate the core concept with the most active agents before full rollout.

#### 2. Memory Persistence & Learning
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

#### 3. Integration Points
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

#### 4. File Management
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

#### 5. User Control
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

#### 6. Backwards Compatibility
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

## Testing and Validation

### Testing Strategy
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

### Success Metrics

1. **Adoption**: 80% of delegations use memory within 1 month
2. **Effectiveness**: 25% reduction in repeated mistakes
3. **Performance**: <50ms overhead per delegation
4. **Quality**: 90% of captured learnings are relevant
5. **Stability**: Zero memory-related failures in production

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

## Future Evolution

When static limits become insufficient:

### Dynamic Memory Management
- Automatic summarization of old learnings
- Tag-based categorization and retrieval
- Importance scoring for memory retention
- Cross-agent knowledge sharing

### Advanced Learning
- Pattern recognition for common learnings
- Automatic categorization of discoveries
- Learning effectiveness measurement
- Memory-based agent performance optimization

## Conclusion

The Agent Memory System provides a comprehensive foundation for project-specific agent learning while maintaining simplicity, transparency, and developer control. The phased implementation approach ensures stability and allows for validation at each stage.

Key benefits include:
- **Progressive Intelligence**: Agents become smarter about specific projects over time
- **Full Transparency**: All learnings are visible and editable by developers
- **Local Control**: No external dependencies, all data stays local
- **Team Collaboration**: Optional knowledge sharing via version control
- **Backwards Compatibility**: Zero disruption to existing workflows

This system transforms Claude MPM agents from stateless task executors into adaptive, project-aware collaborators that accumulate institutional knowledge and improve their effectiveness through experience.