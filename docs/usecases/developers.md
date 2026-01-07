---
title: Claude MPM for Developers
version: 1.0.0
last_updated: 2026-01-07
audience: Software developers and engineers
status: current
---

# Claude MPM for Developers

**Multi-Agent Development Workflows**

This guide shows developers how to leverage Claude MPM's multi-agent orchestration, semantic code search, and advanced features for software development.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Multi-Agent Development](#multi-agent-development)
3. [Semantic Code Search](#semantic-code-search)
4. [Development Workflows](#development-workflows)
5. [Agent Selection Guide](#agent-selection-guide)
6. [Advanced Features](#advanced-features)
7. [Integration with Dev Tools](#integration-with-dev-tools)
8. [Best Practices](#best-practices)

---

## Quick Start

### Installation

```bash
# Install Claude Code (required)
npm install -g @anthropic-ai/claude-code

# Install Claude MPM with monitoring
pipx install "claude-mpm[monitor]"

# Optional: Recommended companion tools
pipx install kuzu-memory          # Persistent project context
pipx install mcp-vector-search    # Semantic code search
```

### Verify Installation

```bash
# Check versions
claude --version
claude-mpm --version

# Run diagnostics
claude-mpm doctor

# Verify Git repositories are synced
ls ~/.claude/agents/    # Should show 47+ agents

# Check MCP integration
claude-mpm verify
```

### First Session

```bash
# Navigate to your project
cd ~/Projects/your-project

# Start with monitoring dashboard
claude-mpm run --monitor

# Or use interactive mode
claude-mpm
```

---

## Multi-Agent Development

Claude MPM includes **47+ specialized agents** from Git repositories covering:

### Core Development Agents

#### **Engineer** - General software development
- Full-stack implementation
- API development
- Database design
- Architecture decisions
- Best for: General development tasks

#### **Python Engineer** (v2.3.0)
- Type-safe, async-first Python
- Service-oriented architecture with ABC interfaces
- Lightweight script patterns for automation
- Dependency injection containers
- **Use for:** Web applications, microservices, data pipelines (DI/SOA) or scripts, CLI tools (simple functions)

#### **Rust Engineer** (v1.1.0)
- Memory-safe, high-performance systems
- Trait-based service architecture
- Async programming with tokio
- Zero-cost abstractions
- **Use for:** Web services, microservices (DI/SOA) or CLI tools, scripts (simple code)

#### **Research** - Code analysis and investigation
- Codebase exploration
- Pattern detection
- Dependency analysis
- Technology stack assessment
- Best for: Understanding existing code

### Quality & Testing

#### **QA** - Testing and quality assurance
- Unit test creation
- Integration testing
- Test coverage analysis
- Bug reproduction
- Best for: Test-driven development

#### **Web QA** - Web testing and E2E validation
- Browser automation
- End-to-end testing
- Visual regression testing
- Performance testing
- Best for: Web application testing

#### **Security** - Security analysis
- Vulnerability scanning
- Security best practices
- Authentication/authorization review
- Dependency security audit
- Best for: Security-critical code

### Code Quality

#### **Refactoring Engineer** - Code optimization
- Code refactoring
- Performance optimization
- Design pattern application
- Technical debt reduction
- Best for: Legacy code improvement

#### **Code Analyzer** - Static analysis
- AST-based analysis
- Tree-sitter parsing
- Code metrics
- Complexity analysis
- Best for: Deep code analysis

### Operations & Infrastructure

#### **Ops** - Operations and deployment (v2.2.2+)
- CI/CD pipelines
- Docker containerization
- Infrastructure as Code
- Advanced git commit authority
- Security verification
- Best for: DevOps tasks

#### **Data Engineer** - Data pipeline development
- ETL pipeline design
- Data transformation
- Database optimization
- Data quality validation
- Best for: Data-intensive applications

### Documentation & Organization

#### **Documentation** - Documentation creation
- API documentation
- README generation
- Code comments
- Architecture diagrams
- Best for: Documentation tasks

#### **Project Organizer** - File organization
- Codebase restructuring
- Directory organization
- File consolidation
- Best for: Project cleanup

---

## Semantic Code Search

Claude MPM integrates with **mcp-vector-search** for AI-powered semantic code discovery.

### Installation

```bash
pipx install mcp-vector-search
```

### Usage

**Within Claude Code session:**
```
/mpm-search "authentication logic"
/mpm-search "database connection pooling"
/mpm-search "error handling patterns"
```

**CLI command:**
```bash
claude-mpm search "authentication logic"
```

### Search Capabilities

- **Semantic Discovery**: Find code by what it *does*, not just what it's *named*
- **Context-Aware**: Understand code relationships automatically
- **Pattern Recognition**: Discover similar implementations
- **Fast Indexing**: Efficient for large codebases
- **Live Updates**: Tracks code changes automatically

### Use Cases

1. **Discovering Existing Functionality**
   ```
   /mpm-search "user authentication"
   # Finds auth-related code even if it's named differently
   ```

2. **Finding Similar Patterns**
   ```
   /mpm-search "API rate limiting"
   # Discovers similar rate-limiting implementations
   ```

3. **Architectural Exploration**
   ```
   /mpm-search "dependency injection patterns"
   # Identifies DI usage across codebase
   ```

4. **Refactoring Opportunities**
   ```
   /mpm-search "similar database queries"
   # Finds duplicate or similar query patterns
   ```

---

## Development Workflows

### 1. Feature Implementation

**Goal:** Implement a new feature end-to-end

**Workflow:**
1. **Research Agent**: Analyze existing patterns
   ```
   /mpm-research "How is authentication currently implemented?"
   ```

2. **Engineer Agent**: Implement feature
   ```
   /mpm-engineer "Implement OAuth2 authentication"
   ```

3. **QA Agent**: Create tests
   ```
   /mpm-qa "Create comprehensive tests for OAuth2 flow"
   ```

4. **Documentation Agent**: Document the feature
   ```
   /mpm-docs "Document OAuth2 setup and usage"
   ```

### 2. Bug Investigation & Fix

**Goal:** Find and fix a bug

**Workflow:**
1. **QA Agent**: Reproduce the bug
   ```
   /mpm-qa "Reproduce login bug: users can't reset password"
   ```

2. **Research Agent**: Investigate root cause
   ```
   /mpm-research "Analyze password reset flow and identify issues"
   ```

3. **Engineer Agent**: Fix the bug
   ```
   /mpm-engineer "Fix password reset token expiration issue"
   ```

4. **QA Agent**: Verify fix
   ```
   /mpm-qa "Verify password reset fix works correctly"
   ```

### 3. Code Refactoring

**Goal:** Improve code quality

**Workflow:**
1. **Code Analyzer**: Identify issues
   ```
   /mpm-analyzer "Analyze API endpoint complexity and suggest improvements"
   ```

2. **Refactoring Engineer**: Refactor code
   ```
   /mpm-refactor "Simplify complex API endpoints using service layer"
   ```

3. **QA Agent**: Ensure no regressions
   ```
   /mpm-qa "Run full test suite and verify refactoring didn't break anything"
   ```

### 4. Security Audit

**Goal:** Improve security posture

**Workflow:**
1. **Security Agent**: Scan for vulnerabilities
   ```
   /mpm-security "Audit authentication and authorization implementation"
   ```

2. **Engineer Agent**: Fix vulnerabilities
   ```
   /mpm-engineer "Implement security recommendations from audit"
   ```

3. **QA Agent**: Test security fixes
   ```
   /mpm-qa "Verify security fixes don't introduce regressions"
   ```

### 5. Performance Optimization

**Goal:** Improve application performance

**Workflow:**
1. **Code Analyzer**: Identify bottlenecks
   ```
   /mpm-analyzer "Profile API endpoints and identify slow queries"
   ```

2. **Refactoring Engineer**: Optimize
   ```
   /mpm-refactor "Optimize database queries with proper indexing"
   ```

3. **QA Agent**: Benchmark improvements
   ```
   /mpm-qa "Run performance benchmarks before and after optimization"
   ```

---

## Agent Selection Guide

### When to Use Which Agent

| Task | Primary Agent | Supporting Agents |
|------|---------------|-------------------|
| New feature | Engineer | QA, Documentation |
| Bug fix | Engineer | Research, QA |
| Refactoring | Refactoring Engineer | Code Analyzer, QA |
| Security review | Security | Engineer, QA |
| Testing | QA | Engineer |
| Code analysis | Research, Code Analyzer | - |
| Documentation | Documentation | - |
| DevOps | Ops | Engineer |
| Data pipelines | Data Engineer | Engineer, QA |
| Web testing | Web QA | QA |
| Project cleanup | Project Organizer | - |

### Agent Collaboration Patterns

**Pattern 1: Research → Implement → Test**
```
/mpm-research "Analyze current payment processing"
# Then
/mpm-engineer "Implement Stripe payment integration"
# Then
/mpm-qa "Test payment flow end-to-end"
```

**Pattern 2: Analyze → Refactor → Verify**
```
/mpm-analyzer "Identify code smells in user service"
# Then
/mpm-refactor "Apply service layer pattern to user module"
# Then
/mpm-qa "Verify refactoring maintains functionality"
```

**Pattern 3: Audit → Fix → Document**
```
/mpm-security "Audit API security"
# Then
/mpm-engineer "Fix identified vulnerabilities"
# Then
/mpm-docs "Document security improvements"
```

---

## Advanced Features

### 1. Session Management

**Resume Previous Session:**
```bash
claude-mpm --resume
```

**Session Features:**
- Automatic context preservation
- Resume logs at 70%/85%/95% token thresholds
- 10k-token structured summaries
- Seamless continuation across sessions

See [Resume Logs Documentation](../user/resume-logs.md) for details.

### 2. Real-Time Monitoring

**Start with Dashboard:**
```bash
claude-mpm run --monitor
```

**Dashboard Features:**
- Live agent activity
- File operation tracking
- Session metrics
- Performance monitoring

See [Monitoring Documentation](../developer/11-dashboard/README.md) for details.

### 3. Memory Management

**Project Memory (kuzu-memory):**
```bash
# Install
pipx install kuzu-memory

# Automatic integration - no configuration needed
# Agents will remember project patterns across sessions
```

**Benefits:**
- Persistent context across sessions
- Project-specific knowledge graphs
- Intelligent prompt enrichment
- Pattern learning over time

**Agent Memory System:**
- Runtime memory loading (instant updates)
- Per-agent memory files: `.claude-mpm/memories/{agent_id}.md`
- No restart required for memory updates
- Event-driven observability

See [Memory Flow Architecture](../architecture/memory-flow.md) for details.

### 4. Git Repository Integration

**Agents from Git:**
- 47+ agents automatically deployed from repositories
- Always up-to-date on startup
- ETag-based caching (95%+ bandwidth reduction)
- Hierarchical BASE-AGENT.md inheritance

**Custom Agent Repositories:**
```bash
# Add custom agent repository
claude-mpm agent-source add https://github.com/yourorg/your-agents

# Test repository without saving
claude-mpm agent-source add https://github.com/yourorg/your-agents --test

# List configured sources
claude-mpm agent-source list

# Update from all sources
claude-mpm agent-source update
```

See [Agent Sources Guide](../user/agent-sources.md) for details.

### 5. Skills System

**17 Bundled Skills** covering essential workflows:
- Git workflow, TDD, code review, systematic debugging
- API documentation, refactoring patterns, performance profiling
- Docker containerization, database migrations, security scanning
- JSON/PDF/XLSX handling, async testing, ImageMagick operations
- Local dev servers: Next.js, FastAPI, Vite, Express
- Web performance: Lighthouse, Core Web Vitals

**Three-Tier Organization:**
- **Bundled**: Core skills (included)
- **User**: Custom skills (`~/.claude/skills/`)
- **Project**: Project-specific (`.claude/skills/`)

**Interactive Management:**
```bash
claude-mpm configure
# Choose option 2: Skills Management
```

**Custom Skills:**
```bash
# Add skill repository
claude-mpm skill-source add https://github.com/yourorg/custom-skills

# List sources
claude-mpm skill-source list

# Update from all sources
claude-mpm skill-source update
```

See [Skills Guide](../user/skills-guide.md) for details.

---

## Integration with Dev Tools

### GitHub Integration

**Via MCP GitHub Tools:**
- Create/update files
- Push commits
- Create pull requests
- Search repositories
- Manage issues

**Usage:**
```
/mpm-engineer "Create feature branch and implement OAuth"
# Engineer agent can use GitHub MCP tools directly
```

### CI/CD Integration

**Ops Agent Capabilities:**
- GitHub Actions workflows
- Docker containerization
- Deployment automation
- Infrastructure as Code

**Usage:**
```
/mpm-ops "Set up GitHub Actions for automated testing"
```

### Browser Automation

**Web QA Agent Features:**
- Playwright integration
- Chrome DevTools Protocol
- E2E testing
- Visual regression

**Usage:**
```
/mpm-webqa "Create E2E test for checkout flow using Playwright"
```

### File System Operations

**All agents have access to:**
- File read/write
- Directory operations
- Search and grep
- Git operations

---

## Best Practices

### 1. Agent Selection

- **Use specific agents** for specialized tasks (Python Engineer for Python, Rust Engineer for Rust)
- **Start with Research** when unfamiliar with codebase
- **Use QA agent** for all test creation (not Engineer)
- **Security agent** for security-critical code
- **Ops agent** for deployment and infrastructure

### 2. Session Management

- **Use `--resume`** to continue previous work
- **Monitor token usage** (dashboard shows current usage)
- **Save important context** before approaching limits
- **Resume logs** auto-generate at 70%/85%/95% thresholds

### 3. Code Quality

- **Always create tests** (use QA agent)
- **Document as you go** (use Documentation agent)
- **Regular security audits** (use Security agent)
- **Refactor proactively** (use Refactoring Engineer)
- **Use semantic search** before implementing new code (avoid duplication)

### 4. Memory & Context

- **Use kuzu-memory** for persistent project context
- **Update agent memories** with project-specific patterns
- **Leverage semantic search** to discover existing implementations
- **Review resume logs** when continuing work

### 5. Performance

- **Use monitoring dashboard** to track performance
- **Profile before optimizing** (Code Analyzer agent)
- **Benchmark improvements** (QA agent)
- **Cache intelligently** (ETag-based for Git repos)

### 6. Collaboration

- **Clear handoffs** between agents (PM agent orchestrates)
- **Document decisions** (Documentation agent)
- **Share context** via agent memories
- **Use resume logs** for team continuity

---

## Troubleshooting

### Common Issues

**Agent not responding:**
```bash
# Run diagnostics
claude-mpm doctor

# Check specific issues
claude-mpm doctor --checks agents mcp
```

**Memory issues:**
```bash
# Clean up old conversations
claude-mpm cleanup-memory

# Keep only recent
claude-mpm cleanup-memory --days 7
```

**MCP services not working:**
```bash
# Verify MCP services
claude-mpm verify

# Auto-fix issues
claude-mpm verify --fix

# Check specific service
claude-mpm verify --service kuzu-memory
```

**Performance issues:**
- Use `--monitor` to identify bottlenecks
- Check token usage in dashboard
- Clear old resume logs if disk space is low

See [Troubleshooting Guide](../user/troubleshooting.md) for comprehensive solutions.

---

## Next Steps

### Learn More

- **[Architecture Overview](../developer/ARCHITECTURE.md)** - System design
- **[API Reference](../reference/api-overview.md)** - Complete API documentation
- **[Contributing Guide](../developer/03-development/README.md)** - How to contribute
- **[Agent Development](../agents/creating-agents.md)** - Create custom agents
- **[Skills Development](../user/skills-guide.md)** - Create custom skills

### Advanced Topics

- **[MCP Gateway](../developer/13-mcp-gateway/README.md)** - Custom tool integration
- **[Memory Architecture](../architecture/memory-flow.md)** - Memory system design
- **[Resume Logs](../user/resume-logs.md)** - Context management
- **[Hierarchical Agents](../design/hierarchical-base-agents.md)** - Agent inheritance

### Community

- **GitHub**: https://github.com/bobmatnyc/claude-mpm
- **Issues**: Report bugs and request features
- **Discussions**: Ask questions and share knowledge
- **Pull Requests**: Contribute improvements

---

**Last updated:** 2026-01-07
**Version:** 1.0.0
**Feedback:** Submit issues at https://github.com/bobmatnyc/claude-mpm/issues
