# Memory System Guide

Claude MPM v4.4.x features an advanced memory system combining traditional agent memories with the powerful kuzu-memory knowledge graph for comprehensive project context retention.

**Version**: 4.4.x
**Last Updated**: 2025-09-28

## Overview

The Claude MPM Memory System provides two complementary memory technologies:

### 1. Kuzu-Memory (Primary - v4.4.x+)
- **Graph Database**: Uses Kuzu for efficient storage and semantic search
- **Automatic Installation**: Installed via pipx on first run
- **Project-Specific**: Each project gets its own isolated memory store
- **Context Enrichment**: Automatically enhances prompts with relevant context
- **Conversation History**: Persistent memory across sessions

### 2. Agent Memory Files (Legacy)
- **File-Based**: Traditional text-based memory files per agent
- **Manual Management**: CLI commands for viewing and editing
- **Agent-Specific**: Each agent type has its own memory file
- **Backwards Compatible**: Still supported for existing workflows

### Key Benefits

- **Continuity**: Persistent memory across conversations and sessions
- **Context-Awareness**: Intelligent retrieval of relevant project knowledge
- **Efficiency**: Automated context enrichment reduces repetitive explanations
- **Quality**: Accumulated project knowledge improves response accuracy

## Getting Started

### Automatic Setup

Claude MPM v4.4.x automatically sets up the memory system:

1. **Kuzu-Memory Detection**: Checks for existing kuzu-memory installation
2. **Auto-Installation**: Installs kuzu-memory via pipx if not found
3. **Project Database**: Creates project-specific knowledge graph
4. **Graceful Fallback**: Falls back to agent memory files if kuzu-memory unavailable

### Quick Start

```bash
# Start claude-mpm (memory system auto-initializes)
claude-mpm

# Check memory system status
claude-mpm info  # Shows kuzu-memory status

# Traditional memory commands (still supported)
claude-mpm memory status
```

### How Memory Works

**Kuzu-Memory (Primary)**:
- Automatically stores conversation memories
- Enriches prompts with relevant context
- Uses semantic search for intelligent retrieval
- No manual intervention required

**Agent Memory Files (Legacy)**:
- Manual memory management via CLI
- Agent-specific knowledge storage
- Explicit memory commands

## Kuzu-Memory System (Primary)

### How It Works

The kuzu-memory system operates automatically:

1. **Context Collection**: Captures conversation context and project information
2. **Graph Storage**: Stores memories with tags and relationships in Kuzu database
3. **Semantic Search**: Finds relevant memories using advanced retrieval algorithms
4. **Context Enrichment**: Automatically adds relevant context to user prompts
5. **Project Isolation**: Each project maintains its own memory database

### Database Locations

```bash
# Project-specific databases
~/.claude-mpm/kuzu-memory/projects/<project-hash>/

# Shared memories (if enabled)
~/.claude-mpm/kuzu-memory/shared/
```

### Checking Kuzu-Memory Status

```bash
# General system information (includes kuzu-memory status)
claude-mpm info

# Output includes:
# ✅ Kuzu-Memory: Available at /path/to/kuzu-memory
# 📊 Project Database: /path/to/project/db
# 💾 Memory Count: X memories stored
```

## Agent Memory Files (Legacy)

### Viewing Agent Memories

**See all agent memories (summary):**
```bash
claude-mpm memory show
```

**View specific agent memory:**
```bash
claude-mpm memory show engineer
claude-mpm memory show qa
```

**Get detailed view with all content:**
```bash
claude-mpm memory show engineer --format detailed
```

### Memory Storage Methods

**Kuzu-Memory (Automatic)**:
- Memories are automatically stored during conversations
- Context is intelligently extracted and indexed
- No manual commands required
- Uses project-specific graph database

**Agent Memory Files (Manual)**:
```bash
# Add specific learnings to agent memory files
claude-mpm memory add engineer pattern "Use dependency injection for service classes"
claude-mpm memory add qa error "Missing test coverage causes deployment failures"
claude-mpm memory add documentation context "API docs are in OpenAPI 3.0 format"
```

**Learning types for agent files:**
- `pattern`: Architectural or design patterns
- `error`: Common mistakes to avoid
- `optimization`: Performance improvements
- `preference`: Team preferences and standards
- `context`: Current project state or decisions

### Natural Language Learning

Both memory systems respond to natural language cues:

- "Remember this for next time"
- "Add this to memory"
- "Learn from this mistake"
- "Store this insight"
- "Don't forget that we..."

**Example with kuzu-memory:**
```
You: The authentication service uses JWT tokens with 24-hour expiration.
     Remember this for future API development.

Agent: I'll store this information in the project knowledge graph.
       [Kuzu-memory automatically indexes this information]
```

## Memory System Architecture

### Kuzu-Memory vs Agent Files

**Kuzu-Memory (Recommended)**:
- Graph-based storage with semantic relationships
- Automatic context enrichment during conversations
- Project-specific isolation with shared knowledge option
- Advanced search and retrieval capabilities
- No manual maintenance required

**Agent Memory Files (Legacy)**:
- File-based storage per agent type
- Manual memory management via CLI
- Explicit memory commands and optimization
- Backwards compatible with existing workflows

### Agent Types (For Legacy Memory Files)

The system supports 10+ specialized agents:

**Core Development**:
- `engineer` - Coding patterns, architecture, performance
- `qa` - Testing strategies, quality standards, bug patterns
- `research` - Analysis, investigation, domain knowledge

**Specialized**:
- `data_engineer` - Data pipelines, databases, analytics
- `security` - Security analysis, compliance, threats
- `documentation` - Technical writing, user guides
- `devops` - Infrastructure, deployment, monitoring
- `version_control` - Git workflows, branching strategies
- `project_manager` - Planning, coordination, requirements
- `test_integration` - CI/CD, automated testing

## System Status and Health

### Checking Overall Memory Status

```bash
# Comprehensive system information (includes kuzu-memory)
claude-mpm info

# Legacy agent memory files status
claude-mpm memory status
```

**Claude MPM Info Output** (includes kuzu-memory):
```
Claude MPM v4.4.x System Information
────────────────────────────────────────────────────────────────────────────────
✅ Kuzu-Memory: Available at /opt/homebrew/bin/kuzu-memory
📊 Project Database: /Users/name/.claude-mpm/kuzu-memory/projects/abc123/
💾 Memory Count: 47 memories stored
🔧 Auto Context Enrichment: Enabled
📁 Agent Memory Files: 4 agents with legacy memories
```

**Agent Memory Status** (legacy system):
```
Agent Memory System Status
────────────────────────────────────────────────────────────────────────────────
🧠 Memory System Health: ✅ healthy
📁 Memory Directory: /project/.claude-mpm/memories
🔧 System Enabled: Yes
📚 Auto Learning: Yes
📊 Total Agents: 4
💾 Total Size: 28.4 KB
```

## Memory Maintenance

### Kuzu-Memory (No Maintenance Required)

The kuzu-memory system is self-managing:
- **Automatic Optimization**: Graph database handles storage efficiently
- **Smart Retrieval**: Advanced algorithms ensure relevant context
- **No Size Limits**: Scales automatically with project needs
- **Background Cleanup**: Handles duplicate detection internally

### Agent Memory Files (Manual Optimization)

**When to optimize legacy memory files:**
- Memory files near size limits (red indicators)
- Duplicate or redundant information
- Outdated or inconsistent responses
- Monthly maintenance (recommended)

**Running optimization:**
```bash
# Optimize all agent memory files
claude-mpm memory optimize

# Optimize specific agent
claude-mpm memory optimize engineer
```

**What optimization does:**
- Removes duplicates and consolidates similar items
- Reorders by priority and relevance
- Creates backups before changes
- Reduces file size and improves performance

## Finding Patterns and Cross-References

### Finding Common Patterns

```bash
claude-mpm memory cross-ref
```

This shows:
- Patterns that appear across multiple agents
- Knowledge correlations between agents
- Potential knowledge gaps

### Searching Memories

```bash
claude-mpm memory cross-ref --query "testing"
```

Example output:
```
🔗 Memory Cross-Reference Analysis
────────────────────────────────────────────────────────────────────────────────
🎯 Query matches for 'testing':
   📋 engineer:
      • Use Jest for unit testing with React components
      • Testing utilities in src/utils/test-helpers.js
      
   📋 qa:
      • Integration testing requires Docker environment
      • Test coverage must be above 85% for deployment
```

## Building Memories from Documentation

### Automatic Documentation Processing

```bash
claude-mpm memory build
```

This automatically:
- Scans your project documentation (README.md, docs/, etc.)
- Extracts actionable insights and patterns
- Routes information to appropriate agents
- Updates agent memories with project-specific knowledge

### Force Rebuild

```bash
claude-mpm memory build --force-rebuild
```

Use when:
- Documentation has significantly changed
- You want to refresh all memories
- Memory files seem outdated

## Testing Memory Routing

### Understanding How Content Gets Routed

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

📊 Agent Relevance Scores:
   qa: 0.850
      Keywords: pytest, unit, testing
   engineer: 0.123
      Keywords: testing
```

This helps you understand:
- Which agent will store specific information
- Why the routing decision was made
- How confident the system is in the decision

## Best Practices

### Working with Kuzu-Memory

**1. Natural Conversations**
- Use natural language to indicate important information
- The system automatically extracts and stores relevant context
- No manual commands needed for most use cases

**2. Project-Specific Context**
- Focus conversations on project-specific decisions and patterns
- Kuzu-memory automatically categorizes and relates information
- Context enrichment improves over time with more conversations

### Legacy Agent Memory Files

**1. Be Specific and Actionable**
```bash
# ✅ Good: Specific and actionable
claude-mpm memory add engineer pattern "Use React.memo for components that re-render frequently"

# ❌ Poor: Too generic
claude-mpm memory add engineer pattern "Use React best practices"
```

**2. Include Project Context**
```bash
# ✅ Good: Includes project context
claude-mpm memory add qa context "E2E tests run against staging environment with real database"

# ❌ Poor: Missing context
claude-mpm memory add qa context "Run E2E tests"
```

### When to Use Different Agents

**Engineer** - Implementation details, coding patterns, architecture decisions
```bash
claude-mpm memory add engineer pattern "API responses use camelCase, database uses snake_case"
```

**QA** - Testing strategies, quality standards, common bugs
```bash
claude-mpm memory add qa error "Race conditions in async tests - use waitFor() helpers"
```

**Research** - Domain knowledge, analysis findings, external integrations
```bash
claude-mpm memory add research context "Payment processing via Stripe - webhook verification required"
```

**Documentation** - Writing standards, content organization, user experience
```bash
claude-mpm memory add documentation preference "Code examples must show both success and error cases"
```

### Maintenance Schedule

**For Kuzu-Memory (Minimal)**:
- No regular maintenance required
- System self-optimizes and manages storage
- Monitor via `claude-mpm info` occasionally

**For Agent Memory Files (Legacy)**:

**Weekly:**
- Review memory status: `claude-mpm memory status`
- Check for optimization opportunities

**Monthly:**
- Run optimization: `claude-mpm memory optimize`
- Review and clean outdated memories manually

**Project milestones:**
- Document key architectural decisions explicitly
- Add important project-specific patterns

## Troubleshooting

### Kuzu-Memory Issues

**Kuzu-memory not found:**
1. Check installation: `which kuzu-memory`
2. Verify pipx installation: `pipx list | grep kuzu-memory`
3. Reinstall: `pipx install kuzu-memory`
4. Check system info: `claude-mpm info`

**Context not enriching properly:**
1. Verify project database exists: Check `~/.claude-mpm/kuzu-memory/projects/`
2. Ensure conversations are being stored
3. Try starting a new conversation to test memory

**Database corruption:**
1. Check database files in project memory directory
2. Consider deleting and recreating project database
3. Kuzu-memory will recreate on next conversation

### Agent Memory Files Issues

**Memories not updating:**
1. Check if memory system is enabled: `claude-mpm memory status`
2. Verify directory permissions on `.claude-mpm/memories/`
3. Check available disk space

**Memory files too large:**
1. Run optimization: `claude-mpm memory optimize`
2. Review and remove outdated content
3. Consider increasing size limits in configuration

### Getting Help

**System Information:**
```bash
# Overall system status (includes kuzu-memory)
claude-mpm info

# Legacy agent memory commands
claude-mpm memory --help
claude-mpm memory show --help
```

**Debug Memory Issues:**
```bash
# Enable verbose output
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm info
claude-mpm memory status
```

**Testing Memory Systems:**
```bash
# Test kuzu-memory availability
which kuzu-memory

# Test agent memory routing
claude-mpm memory route --content "test content"
```

## Summary

Claude MPM v4.4.x provides a dual-layer memory system:

1. **Kuzu-Memory (Primary)**: Automatic, graph-based knowledge storage with intelligent context enrichment
2. **Agent Memory Files (Legacy)**: Manual, file-based memory management for specific use cases

The kuzu-memory system handles most memory needs automatically, while legacy agent memory files remain available for explicit knowledge management. Both systems work together to provide comprehensive project context retention across conversations and sessions.