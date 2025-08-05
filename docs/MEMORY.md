# Agent Memory System Documentation

The Agent Memory System in Claude MPM enables agents to learn and apply knowledge over time, creating persistent learnings that improve agent effectiveness across sessions.

Last Updated: 2025-01-24

## Overview

### What is the Memory System?

The memory system allows agents to accumulate project-specific knowledge, patterns, and learnings in persistent memory files. When agents encounter situations they've learned from before, they can apply that knowledge to make better decisions and provide more contextually relevant assistance.

### Why is it Important?

- **Continuity**: Agents remember insights across sessions, building expertise over time
- **Context-Awareness**: Agents learn project-specific patterns, conventions, and requirements
- **Efficiency**: Reduces repetitive explanations and accelerates problem-solving
- **Quality**: Agents learn from mistakes and successful patterns to improve output quality

### How Agents Learn

Agents accumulate knowledge through:
1. **Explicit Memory Commands**: Users say "remember this" or "add to memory"
2. **Auto-Learning**: Automatic extraction from agent outputs (when enabled)
3. **Documentation Building**: Automated extraction from project documentation
4. **Manual Addition**: Direct memory file editing or CLI commands

### Benefits

**For Users:**
- Agents provide more relevant, project-specific assistance
- Reduced need to repeat context or preferences
- Faster problem resolution based on learned patterns

**For Developers:**
- Agents learn coding patterns and architectural decisions
- Reduced debugging time through learned common mistakes
- Better adherence to project conventions and standards

## Core Features

### Memory Storage

Agents store memories in structured markdown files located in `.claude-mpm/memories/`:

```
.claude-mpm/memories/
├── engineer_agent.md
├── research_agent.md  
├── qa_agent.md
└── documentation_agent.md
```

**Memory Commands Recognized:**
- "remember this for next time"
- "memorize this pattern"
- "add to memory"
- "learn from this mistake"
- "store this insight"

### Show Memories Functionality

View agent memories through:
- **CLI Command**: `claude-mpm memory show [agent_id]`
- **Format Options**: Summary view or full content display
- **Cross-References**: Identify common patterns across agents

### Optimize Memories Capability

Automatic memory maintenance through:
- **Duplicate Removal**: Eliminates redundant entries
- **Consolidation**: Merges similar items for clarity
- **Priority Reordering**: Places important insights first
- **Size Management**: Maintains memory within configured limits

### Build Memories from Documentation

Automated knowledge extraction from:
- Project documentation (CLAUDE.md, STRUCTURE.md, QA.md)
- Code comments and patterns
- Configuration files and guidelines
- Custom documentation sources

## Usage Guide

### Adding Memories

**Natural Language (Recommended):**
```
User: "Remember that we use the src/ layout pattern for this project"
Agent: I'll remember that architectural decision for future reference.
```

**CLI Command:**
```bash
# Add a specific learning
claude-mpm memory add engineer pattern "Use src/ layout for Python packages"

# Add a mistake to avoid
claude-mpm memory add qa error "Missing test coverage causes deployment failures"
```

**Memory Categories:**
- `pattern`: Architectural or design patterns
- `error`: Common mistakes to avoid
- `optimization`: Performance or efficiency improvements
- `preference`: User or team preferences
- `context`: Current project state or decisions

### Viewing Memories

**Show All Agent Memories (Summary):**
```bash
claude-mpm memory show
```

**Show Specific Agent Memory:**
```bash
# Summary view
claude-mpm memory show engineer

# Full content view
claude-mpm memory show engineer --format full
```

**Memory Status Overview:**
```bash
claude-mpm memory status
```

Example output:
```
Agent Memory System Status
--------------------------------------------------------------------------------
🧠 Memory System Health: ✅ healthy
📁 Memory Directory: /project/.claude-mpm/memories
🔧 System Enabled: Yes
📚 Auto Learning: No
📊 Total Agents: 4

📋 Agent Memory Details:
   🟢 engineer
      Size: 6.2 KB / 8 KB (77.5%)
      Content: 4 sections, 23 items
      Auto-learning: Off
      Last modified: 2025-01-24 10:30:15
```

### Optimizing Memories

**Optimize Specific Agent:**
```bash
claude-mpm memory optimize engineer
```

**Optimize All Agents:**
```bash
claude-mpm memory optimize
```

**Preview Optimization (Analysis Only):**
```bash
claude-mpm memory analyze engineer
```

Optimization performs:
- Removes exact duplicates
- Consolidates similar items (70%+ similarity)
- Reorders by priority keywords
- Maintains structured format

### Building from Documentation

**Build from All Documentation:**
```bash
claude-mpm memory build
```

**Force Rebuild (Ignore Timestamps):**
```bash
claude-mpm memory build --force-rebuild
```

**Process Specific Files:**
The system automatically processes:
- `CLAUDE.md` → PM and Engineer agents
- `docs/STRUCTURE.md` → Engineer and Documentation agents
- `docs/QA.md` → QA and Engineer agents
- `docs/DEPLOY.md` → Engineer and PM agents

### PM Agent Memory Command Routing

The PM agent automatically routes memory commands to appropriate agents:

**Test Routing Logic:**
```bash
claude-mpm memory route --content "Use pytest for unit testing"
```

Example output:
```
🎯 Routing Decision:
   Target Agent: qa
   Section: Testing Strategies
   Confidence: 0.87
   Reasoning: Strong match for qa agent; matched keywords: pytest, unit, testing
```

## CLI Commands Reference

### memory status
Shows comprehensive memory system status including:
- System health and configuration
- Per-agent memory statistics
- Size utilization and optimization opportunities
- Auto-learning status

### memory show [agent_id] [--format]
Displays agent memories in readable format:
- **No agent_id**: Shows all agents with cross-references
- **With agent_id**: Shows specific agent memory
- **--format summary**: Brief overview (default)
- **--format full**: Complete memory content

### memory optimize [agent_id]
Optimizes memory files by removing duplicates and consolidating:
- **No agent_id**: Optimizes all agent memories
- **With agent_id**: Optimizes specific agent only
- Creates backup before optimization
- Reports size reduction and improvements

### memory build [--force-rebuild]
Builds memories from project documentation:
- **--force-rebuild**: Processes all files regardless of timestamps
- Extracts actionable insights and guidelines
- Routes content to appropriate agents
- Updates last-processed timestamps

### memory route --content "text"
Tests memory command routing logic:
- Analyzes content for agent relevance
- Shows routing decision and reasoning
- Displays agent relevance scores
- Useful for debugging and customization

### memory cross-ref [--query]
Finds cross-references and patterns across memories:
- **No query**: Shows common patterns across all agents
- **With query**: Searches for specific content
- Identifies knowledge correlations
- Helps find knowledge gaps

## Agent Memory Integration

### How Agents Use Memory

1. **Pre-Task Loading**: Agents load their memory before starting tasks
2. **Context Integration**: Memory content is integrated into agent prompts
3. **Decision Making**: Agents reference learned patterns and guidelines
4. **Post-Task Learning**: New insights are extracted and stored

### Memory Format Specification

Memory files follow a structured markdown format:

```markdown
# Agent Memory: Engineer

<!-- Last Updated: 2025-01-24 10:30:15 | Auto-updated by: system -->

## Memory Usage
- Size: 6.2 KB / 8.0 KB (77.5%)
- Sections: 4 active
- Last optimized: 2025-01-20

## Project Architecture
- Use src/ layout pattern for Python packages
- Follow service-oriented architecture with clear separation
- Store all scripts in /scripts/, never in project root

## Implementation Guidelines  
- All imports use full package name: from claude_mpm.module import ...
- Run E2E tests after significant changes
- Create backups before major optimizations

## Common Mistakes to Avoid
- Don't place test files outside of /tests/ directory
- Never update git config in automated scripts
- Avoid using search commands like find and grep in bash

## Current Technical Context
- Project uses pytest for testing framework
- Memory files limited to 8KB with auto-truncation
- Socket.IO integration optional for notifications
```

### Memory Categories

**Architectural Patterns:**
- Design decisions and structural guidelines
- Component relationships and dependencies
- Technology stack choices and rationale

**Implementation Guidelines:**
- Coding standards and conventions
- Best practices and recommended approaches
- Tool usage and configuration patterns

**Common Mistakes:**
- Known pitfalls and how to avoid them
- Error patterns and their solutions
- Debugging insights and troubleshooting

**Technical Context:**
- Current project state and decisions
- Temporary constraints or considerations
- Environmental or configuration specifics

### Agent-Specific Memory Guidelines

**Engineer Agent:**
- Focus on implementation patterns and coding standards
- Learn from build errors and performance issues
- Store architectural decisions and refactoring insights

**Research Agent:**
- Collect domain knowledge and research findings
- Document investigation methodologies
- Store external resource references and insights

**QA Agent:**
- Learn testing strategies and coverage patterns
- Remember quality standards and acceptance criteria
- Store common bug patterns and testing insights

**Documentation Agent:**
- Learn writing standards and formatting preferences
- Store documentation patterns and organization methods
- Remember audience-specific communication styles

## Technical Details

### Memory File Structure

```
.claude-mpm/memories/
├── engineer_agent.md          # Engineer-specific memories
├── research_agent.md          # Research findings and insights
├── qa_agent.md               # Quality assurance learnings
├── documentation_agent.md    # Documentation patterns
├── .last_processed.json      # Documentation build timestamps
└── README.md                 # Memory system overview
```

### Memory Routing Algorithm

The routing system uses keyword analysis and pattern matching:

1. **Content Normalization**: Remove noise words, normalize spacing
2. **Agent Scoring**: Calculate relevance scores based on keyword matches
3. **Context Application**: Apply hints from task type or explicit instructions
4. **Target Selection**: Choose highest-scoring agent with confidence threshold
5. **Section Determination**: Map content type to appropriate memory section

**Agent Keyword Patterns:**
- **Engineer**: implementation, code, function, architecture, performance
- **Research**: research, analysis, findings, documentation, security
- **QA**: test, quality, bug, validation, coverage, standards
- **Documentation**: document, readme, guide, explanation, reference

### Optimization Strategies

**Duplicate Detection:**
- Exact content matching (case-insensitive)
- Similarity scoring using SequenceMatcher
- 85% similarity threshold for duplicate removal

**Consolidation Logic:**
- 70% similarity threshold for related items
- Merge strategy preserves most detailed content
- Additional context appended in parentheses

**Priority-Based Reordering:**
- High priority: critical, important, essential, must, always, never
- Medium priority: should, recommended, prefer, avoid, consider
- Low priority: note, tip, hint, example, reference

### Memory Size Management

**Size Limits:**
- Default: 8KB per memory file (~2000 tokens)
- Configurable per agent through overrides
- Auto-truncation when limits exceeded

**Section Limits:**
- Maximum 10 sections per memory file
- Maximum 15 items per section
- Maximum 120 characters per line item

**Optimization Triggers:**
- Manual optimization commands
- Automatic optimization when size limits approached
- Periodic cleanup through scheduled tasks

## Best Practices

### When to Add Memories

**High-Value Situations:**
- Architectural decisions and their rationale
- Successful problem-solving patterns
- Common mistakes and their solutions
- Project-specific conventions and preferences
- Performance optimizations and their impact

**Avoid Adding:**
- Temporary workarounds or hacks
- Overly specific implementation details
- Information readily available in documentation
- Personal preferences without team consensus

### Memory Size Guidelines

**Optimal Memory Size:**
- Keep individual items under 100 characters
- Aim for 15-20 key insights per section
- Target 70-80% of size limit for growth room
- Regular cleanup maintains relevance

**Content Quality:**
- Focus on actionable insights over descriptions
- Use clear, concise language
- Include context when patterns are non-obvious
- Prioritize learnings with broad applicability

### Categorization Tips

**Use Appropriate Sections:**
- **Architecture**: High-level design decisions
- **Guidelines**: Day-to-day implementation practices
- **Mistakes**: Known pitfalls and their solutions
- **Context**: Current project state and constraints

**Agent Assignment:**
- **Engineer**: Implementation and technical details
- **Research**: Domain knowledge and external insights
- **QA**: Quality standards and testing approaches
- **PM**: Process, coordination, and project management

### Cross-Agent Knowledge Sharing

**Identify Common Patterns:**
- Use `memory cross-ref` to find shared knowledge
- Consolidate duplicate insights across agents
- Ensure consistent terminology and approaches

**Knowledge Distribution:**
- Share architectural decisions across relevant agents
- Duplicate critical safety guidelines
- Maintain agent-specific perspectives on shared concepts

## Troubleshooting

### Common Issues and Solutions

**Memory Files Not Updating:**
```bash
# Check system status
claude-mpm memory status

# Verify configuration
cat .claude-mpm/config.yml

# Check permissions
ls -la .claude-mpm/memories/
```

**Memory Files Growing Too Large:**
```bash
# Check current usage
claude-mpm memory status

# Optimize memories
claude-mpm memory optimize

# Adjust size limits in config
# memory.limits.default_size_kb: 4
```

**Auto-Learning Not Working:**
```bash
# Enable auto-learning in config
# memory.auto_learning: true

# Check agent-specific settings
# memory.agent_overrides.engineer.auto_learning: true

# Verify memory extraction patterns
claude-mpm memory route --content "test content"
```

**Routing to Wrong Agent:**
```bash
# Test routing logic
claude-mpm memory route --content "your content here"

# Review agent patterns in memory_router.py
# Consider adding custom keywords for your domain
```

### Memory File Repair

**Corrupted Memory Files:**
```bash
# Backup existing file
cp .claude-mpm/memories/agent_agent.md agent_backup.md

# Recreate from template
rm .claude-mpm/memories/agent_agent.md
claude-mpm memory add agent context "Rebuilding memory file"
```

**Missing Memory Directory:**
```bash
# Reinitialize memory system
mkdir -p .claude-mpm/memories
claude-mpm memory status
```

### Performance Considerations

**Large Memory Files:**
- Optimize regularly to prevent size bloat
- Use agent-specific size limits for high-volume agents
- Consider memory archiving for historical data

**Slow Memory Operations:**
- Check file system permissions and disk space
- Monitor memory file sizes and section counts
- Use memory analysis to identify optimization opportunities

**Memory Build Performance:**
- Use selective rebuilding (avoid --force-rebuild)
- Process documentation files in priority order
- Monitor last-processed timestamps for efficiency

### Configuration Issues

**Default Settings Not Applied:**
```bash
# Verify configuration file location
ls -la .claude-mpm/config.*

# Check configuration syntax
python -c "from claude_mpm.core.config import Config; print(Config().get('memory'))"
```

**Agent-Specific Overrides Not Working:**
```yaml
# Ensure correct agent ID in config
memory:
  agent_overrides:
    engineer:  # Must match exact agent ID
      size_kb: 16
```

**Memory System Disabled:**
```yaml
# Enable in configuration
memory:
  enabled: true  # Must be explicitly true
```

---

For additional configuration options, see [MEMORY_CONFIG.md](MEMORY_CONFIG.md).

For implementation details, see the source code in `src/claude_mpm/services/` and `src/claude_mpm/cli/commands/memory.py`.