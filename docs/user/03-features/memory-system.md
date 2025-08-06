# Agent Memory System User Guide

Learn how to effectively use the Claude MPM Agent Memory System to help agents learn and improve over time.

## What is Agent Memory?

The Agent Memory System allows Claude agents to remember important insights, patterns, and learnings from your project across sessions. Instead of starting fresh each time, agents build up project-specific knowledge that makes them more effective helpers.

### Key Benefits

- **Continuity**: Agents remember past conversations and learnings
- **Context-Awareness**: Agents learn your project's specific patterns and conventions
- **Efficiency**: Less time explaining the same concepts repeatedly
- **Quality**: Agents learn from mistakes and successful patterns

## Getting Started

### Quick Start

1. **Initialize memories for your project:**
   ```bash
   claude-mpm memory init
   ```

2. **Check memory system status:**
   ```bash
   claude-mpm memory status
   ```

3. **View what agents have learned:**
   ```bash
   claude-mpm memory show
   ```

### How Agents Learn

Agents accumulate knowledge automatically through:

- **Natural conversations**: When you say "remember this for next time"
- **Project analysis**: Automatic analysis of your codebase and documentation
- **Pattern recognition**: Learning from successful solutions and common mistakes
- **Manual additions**: You can directly add important insights

## Using Memory Commands

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

Example output:
```
🤖 Engineer Agent
📚 8 sections, 24 total items

📖 Project Architecture:
   • React TypeScript SPA with Node.js backend
   • Component-based architecture with atomic design
   • State management using Redux Toolkit
   ... and 3 more

📖 Implementation Guidelines:
   • Use functional components with hooks pattern
   • All API calls go through service layer
   • Follow ESLint and Prettier configurations
   ... and 5 more
```

### Adding Memories Manually

**Add specific learnings:**
```bash
claude-mpm memory add engineer pattern "Use dependency injection for service classes"
claude-mpm memory add qa error "Missing test coverage causes deployment failures"  
claude-mpm memory add documentation context "API docs are in OpenAPI 3.0 format"
```

**Learning types you can add:**
- `pattern`: Architectural or design patterns
- `error`: Common mistakes to avoid
- `optimization`: Performance improvements
- `preference`: Team preferences and standards
- `context`: Current project state or decisions

### Natural Language Learning

Agents also learn when you use these phrases in conversation:

- "Remember this for next time"
- "Add this to memory"
- "Learn from this mistake"
- "Store this insight"
- "Don't forget that we..."

**Example conversation:**
```
You: The authentication service uses JWT tokens with 24-hour expiration. 
     Remember this for future API development.

Agent: I'll remember that the authentication service uses JWT tokens 
       with 24-hour expiration for future API development tasks.
```

## Understanding Agent Types

The system supports 10 specialized agents, each focusing on different aspects:

### Core Development Agents

**Engineer Agent** (`engineer`)
- Focuses on coding patterns, architecture, performance
- Learns implementation techniques and best practices
- Example memory: "Use async/await pattern for all API calls"

**QA Agent** (`qa`) 
- Focuses on testing strategies, quality standards, bug patterns
- Learns testing approaches and common issues
- Example memory: "Integration tests require database seeding"

**Research Agent** (`research`)
- Focuses on analysis, investigation, domain knowledge
- Learns research findings and technical insights
- Example memory: "GraphQL preferred over REST for this project"

### Specialized Agents

**Data Engineer** (`data_engineer`)
- Focuses on data pipelines, databases, analytics, AI APIs
- Learns data processing patterns and optimization techniques
- Example memory: "Use connection pooling for PostgreSQL queries"

**Security Agent** (`security`)
- Focuses on security analysis, compliance, threat assessment
- Learns security patterns and compliance requirements
- Example memory: "All user inputs must be sanitized for XSS prevention"

**Documentation Agent** (`documentation`)
- Focuses on technical writing, user guides, API docs
- Learns documentation standards and content organization
- Example memory: "Code examples must include error handling"

And 4 more specialized agents for ops, version control, project management, and test integration.

## System Status and Health

### Checking Memory Status

```bash
claude-mpm memory status
```

Example output:
```
Agent Memory System Status
────────────────────────────────────────────────────────────────────────────────
🧠 Memory System Health: ✅ healthy
📁 Memory Directory: /project/.claude-mpm/memories
🔧 System Enabled: Yes
📚 Auto Learning: Yes
📊 Total Agents: 4
💾 Total Size: 28.4 KB

📋 Agent Memory Details:
   🟢 engineer
      Size: 8.2 KB / 8 KB (102.5%)
      Content: 6 sections, 23 items
      Auto-learning: On
      Last modified: 2025-08-06 10:30:15
   
   🟡 qa
      Size: 6.1 KB / 8 KB (76.3%)
      Content: 5 sections, 18 items
      Auto-learning: On
      Last modified: 2025-08-06 09:45:20
```

**Status indicators:**
- 🟢 Green: Low usage (< 70%)
- 🟡 Yellow: Medium usage (70-90%) 
- 🔴 Red: High usage (> 90%)

## Memory Optimization

### When to Optimize

Optimize agent memories when:
- Memory files are near size limits (red indicators)
- You notice duplicate or redundant information
- Agent responses seem outdated or inconsistent
- Monthly maintenance (recommended)

### Running Optimization

**Optimize all agents:**
```bash
claude-mpm memory optimize
```

**Optimize specific agent:**
```bash
claude-mpm memory optimize engineer
```

Example output:
```
✅ Optimization completed for engineer
   Original size: 8,456 bytes
   Optimized size: 6,823 bytes
   Size reduction: 1,633 bytes (19.3%)
   
   Duplicates removed: 3
   Items consolidated: 5
   Sections reordered: 2
   Backup created: /project/.claude-mpm/memories/engineer_agent.md.backup
```

### What Optimization Does

- **Removes duplicates**: Eliminates identical or very similar items
- **Consolidates similar items**: Merges related learnings
- **Reorders by priority**: Moves important items to the top
- **Creates backups**: Saves original before changes

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

### Effective Memory Usage

**1. Be Specific and Actionable**
```bash
# ✅ Good: Specific and actionable
claude-mpm memory add engineer pattern "Use React.memo for components that re-render frequently"

# ❌ Poor: Too generic
claude-mpm memory add engineer pattern "Use React best practices"
```

**2. Include Context**
```bash
# ✅ Good: Includes project context
claude-mpm memory add qa context "E2E tests run against staging environment with real database"

# ❌ Poor: Missing context  
claude-mpm memory add qa context "Run E2E tests"
```

**3. Focus on Project-Specific Knowledge**
```bash
# ✅ Good: Project-specific
claude-mpm memory add data_engineer pattern "User events pipeline processes 10M+ events/day via Kafka"

# ❌ Poor: Generic knowledge
claude-mpm memory add data_engineer pattern "Kafka is good for streaming"
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

**Weekly:**
- Review memory status: `claude-mpm memory status`
- Check for optimization opportunities

**Monthly:**
- Run optimization: `claude-mpm memory optimize`
- Review and clean outdated memories manually
- Rebuild from docs: `claude-mpm memory build --force-rebuild`

**Project milestones:**
- Add key learnings from completed features
- Document architectural decisions
- Update context for major changes

## Troubleshooting

### Common Issues

**Memories not updating:**
1. Check if memory system is enabled: `claude-mpm memory status`
2. Verify directory permissions on `.claude-mpm/memories/`
3. Check available disk space

**Wrong agent getting memories:**
1. Test routing: `claude-mpm memory route --content "your content"`
2. Use more specific keywords
3. Manually specify the agent: `claude-mpm memory add <agent> <type> "content"`

**Memory files too large:**
1. Run optimization: `claude-mpm memory optimize`
2. Review and remove outdated content
3. Consider increasing size limits in configuration

**Agent responses seem outdated:**
1. Check last modified dates: `claude-mpm memory status`
2. Rebuild from documentation: `claude-mpm memory build --force-rebuild`
3. Add recent learnings manually

### Getting Help

**View all available commands:**
```bash
claude-mpm memory --help
```

**Get command-specific help:**
```bash
claude-mpm memory show --help
claude-mpm memory add --help
```

**Debug memory issues:**
```bash
# Enable verbose output
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm memory status
```

The Agent Memory System makes Claude agents more effective by learning from your project over time. Start with `claude-mpm memory init` and let agents begin learning from your specific codebase and working patterns.