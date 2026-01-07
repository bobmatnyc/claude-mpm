---
title: Claude MPM for Teams
version: 1.0.0
last_updated: 2026-01-07
audience: Development teams and project managers
status: current
---

# Claude MPM for Teams

**Collaboration Patterns and Team Workflows**

This guide shows how teams can leverage Claude MPM for effective collaboration, session management, and coordinated development workflows.

## Table of Contents

1. [Team Setup](#team-setup)
2. [Collaboration Patterns](#collaboration-patterns)
3. [Session Management](#session-management)
4. [PM Handoff Workflows](#pm-handoff-workflows)
5. [Multi-User Coordination](#multi-user-coordination)
6. [Shared Knowledge Management](#shared-knowledge-management)
7. [Best Practices](#best-practices)

---

## Team Setup

### Prerequisites

**All team members need:**
1. Claude Code CLI (v2.0.30+)
2. Claude MPM installed via pipx
3. Shared GitHub repository access
4. Anthropic API key (team or individual)

### Installation for Teams

**Standard Setup (each team member):**
```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Install Claude MPM with monitoring
pipx install "claude-mpm[monitor]"

# Install recommended tools
pipx install kuzu-memory
pipx install mcp-vector-search

# Verify installation
claude-mpm doctor
```

### Shared Configuration

**Project-Level Configuration:**

Create `.claude-mpm/configuration.yaml` in your repository:

```yaml
# .claude-mpm/configuration.yaml
project:
  name: "Your Project Name"

context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.70
    warning: 0.85
    critical: 0.95
  resume_logs:
    enabled: true
    auto_generate: true
    storage_dir: ".claude-mpm/resume-logs"

agents:
  default_preset: "engineering"  # or "qa", "research", etc.
```

**Commit to repository** so all team members share the same configuration.

### Custom Agents & Skills

**Project-Specific Agents:**
```bash
# Store custom agents in .claude-mpm/agents/
# All team members will use the same agents
```

**Project-Specific Skills:**
```bash
# Store custom skills in .claude/skills/
# Shared via repository
```

**Team Agent Repositories:**
```bash
# Add team's custom agent repository
claude-mpm agent-source add https://github.com/yourteam/custom-agents

# Priority ensures team agents override defaults
# Edit ~/.claude-mpm/config/agent_sources.yaml:
# repositories:
#   - url: https://github.com/yourteam/custom-agents
#     priority: 10  # Higher priority than default (100)
```

---

## Collaboration Patterns

### Pattern 1: Sequential Development

**Scenario:** Developer A starts work, Developer B continues

**Workflow:**

**Developer A (Session 1):**
```bash
cd ~/Projects/team-project
claude-mpm run --monitor

# Work on feature
/mpm-engineer "Implement user authentication API"

# Approaching token limit (70% warning)
# Resume log auto-generated: .claude-mpm/resume-logs/20260107_140000.md
```

**Developer B (Session 2):**
```bash
cd ~/Projects/team-project
claude-mpm run --resume

# Claude automatically loads previous resume log
# Full context preserved from Developer A's session

# Continue work
/mpm-engineer "Add unit tests for authentication API"
```

**Key Benefits:**
- Seamless handoff via resume logs
- No context loss between developers
- Structured 10k-token summaries
- Human-readable handoff documentation

### Pattern 2: Parallel Development

**Scenario:** Multiple developers working on different features simultaneously

**Workflow:**

**Developer A (Feature branch):**
```bash
git checkout -b feature/auth
claude-mpm run

# Work on authentication
/mpm-engineer "Implement OAuth2 flow"
```

**Developer B (Different feature branch):**
```bash
git checkout -b feature/payments
claude-mpm run

# Work on payments
/mpm-engineer "Integrate Stripe payment processing"
```

**Developer C (QA on main):**
```bash
git checkout main
claude-mpm run

# Test existing features
/mpm-qa "Run full test suite and identify failing tests"
```

**Key Benefits:**
- Independent session contexts
- Branch-specific work isolation
- Parallel feature development
- No interference between developers

### Pattern 3: PM → Developer Handoff

**Scenario:** PM analyzes requirements, hands off to developer

**PM (Planning session):**
```bash
claude-mpm run

# Analyze requirements
/mpm-research "Analyze current user management system"
/mpm-research "What's needed to add OAuth2 support?"

# Document plan
/mpm-docs "Document OAuth2 implementation plan with technical requirements"

# Approaching limit - resume log generated
```

**Developer (Implementation session):**
```bash
claude-mpm run --resume

# Resume log provides full context:
# - Requirements analysis
# - Technical plan
# - Architectural decisions
# - Next steps

# Implement directly
/mpm-engineer "Implement OAuth2 based on requirements in resume log"
```

**Key Benefits:**
- Clear requirements handoff
- Technical context preserved
- PM can delegate without technical details
- Developer has complete picture

### Pattern 4: Code Review Workflow

**Scenario:** Developer creates PR, reviewer uses Claude MPM

**Developer (Create PR):**
```bash
# Work on feature
/mpm-engineer "Implement feature X"

# Create tests
/mpm-qa "Create comprehensive tests for feature X"

# Self-review
/mpm-research "Review code changes and identify potential issues"

# Create PR via GitHub
```

**Reviewer (Review session):**
```bash
claude-mpm run

# Analyze PR
/mpm-research "Analyze PR #123 and summarize changes"
/mpm-security "Review PR #123 for security issues"
/mpm-qa "Verify PR #123 has adequate test coverage"

# Provide feedback
/mpm-docs "Generate code review summary for PR #123"
```

**Key Benefits:**
- Automated code analysis
- Security review
- Test coverage verification
- Consistent review process

---

## Session Management

### Resume Logs for Team Continuity

**Automatic Resume Log Generation:**
- Generated at 70%, 85%, 95% token usage
- Structured 10k-token summaries
- Stored in `.claude-mpm/resume-logs/`
- Git-committable for team access

**Resume Log Structure:**
```markdown
# Session Resume Log: 20260107_140000

## Context Metrics (500 tokens)
- Token usage and percentage

## Mission Summary (1,000 tokens)
- Overall goal and purpose

## Accomplishments (2,000 tokens)
- What was completed

## Key Findings (2,500 tokens)
- Important discoveries

## Decisions & Rationale (1,500 tokens)
- Why choices were made

## Next Steps (1,500 tokens)
- What to do next

## Critical Context (1,000 tokens)
- Essential state, IDs, paths
```

### Team Resume Workflow

**Best Practices:**

1. **Commit resume logs to Git:**
   ```bash
   git add .claude-mpm/resume-logs/
   git commit -m "docs: add session resume log for OAuth implementation"
   git push
   ```

2. **Reference in PRs:**
   ```markdown
   ## PR Description
   Implements OAuth2 authentication.

   See resume log: `.claude-mpm/resume-logs/20260107_140000.md`
   For full context and decisions.
   ```

3. **Use for sprint planning:**
   - Review resume logs from previous sprint
   - Understand where work left off
   - Plan next sprint based on documented next steps

4. **Onboarding new team members:**
   - Historical resume logs provide project context
   - Understand past architectural decisions
   - See evolution of features over time

See [Resume Logs Documentation](../user/resume-logs.md) for complete details.

---

## PM Handoff Workflows

### Planning to Implementation

**PM Planning Phase:**

```bash
# PM analyzes requirements
/mpm-research "Analyze current payment processing implementation"
/mpm-research "What's required to add Apple Pay support?"

# PM documents technical requirements
/mpm-docs "Create technical specification for Apple Pay integration"

# PM estimates effort
/mpm-research "Estimate effort required for Apple Pay integration"

# Resume log auto-generated with:
# - Requirements analysis
# - Technical specifications
# - Effort estimates
# - Architecture recommendations
```

**Developer Implementation Phase:**

```bash
# Developer resumes with full context
claude-mpm run --resume

# All PM's analysis and specs loaded automatically
/mpm-engineer "Implement Apple Pay integration per technical specification"
```

### Implementation to QA

**Developer Phase:**

```bash
# Developer completes implementation
/mpm-engineer "Implement Apple Pay payment flow"
/mpm-engineer "Add error handling and retry logic"

# Developer creates basic tests
/mpm-qa "Create unit tests for Apple Pay service"

# Resume log documents:
# - Implementation approach
# - Edge cases handled
# - Known limitations
# - Test coverage
```

**QA Phase:**

```bash
# QA engineer resumes
claude-mpm run --resume

# Full implementation context loaded
/mpm-qa "Create comprehensive E2E tests for Apple Pay flow"
/mpm-webqa "Create Playwright tests for Apple Pay UI"
/mpm-qa "Test error scenarios and edge cases"
```

### QA to Operations

**QA Phase:**

```bash
# QA verifies feature
/mpm-qa "Run full test suite for Apple Pay integration"
/mpm-security "Security audit of Apple Pay implementation"

# Resume log documents:
# - Test results
# - Security audit findings
# - Performance benchmarks
# - Deployment readiness
```

**Ops Phase:**

```bash
# Ops deploys feature
claude-mpm run --resume

# Full QA context loaded
/mpm-ops "Create deployment plan for Apple Pay feature"
/mpm-ops "Set up monitoring for Apple Pay transactions"
/mpm-ops "Configure production Apple Pay credentials"
```

---

## Multi-User Coordination

### Shared Agent Memories

**Project-Specific Patterns:**

Team members can update agent memories with project-specific learnings:

```markdown
<!-- .claude-mpm/memories/engineer.md -->
# Engineer Agent Memory

## Project Architecture
- Use service-oriented architecture for all features
- Repository pattern for database access
- Dependency injection via constructor

## Code Style
- TypeScript strict mode enabled
- ESLint configuration in .eslintrc.json
- 100-character line limit

## Testing Strategy
- Jest for unit tests
- Playwright for E2E tests
- 80% coverage minimum

## Deployment
- GitHub Actions for CI/CD
- Deploy to staging on PR merge
- Manual approval for production
```

**All team members benefit** from shared agent memories automatically.

### Monitoring & Observability

**Team Dashboard:**

```bash
# Start monitoring dashboard (accessible to entire team)
claude-mpm run --monitor

# Dashboard accessible at http://localhost:5001
# Shows:
# - Active sessions
# - Agent activity
# - File operations
# - Performance metrics
```

**Use Cases:**
- PM monitors team progress
- Developers see active sessions
- Ops tracks deployment activities
- QA observes test execution

### Semantic Code Search for Teams

**Shared Code Discovery:**

```bash
# Install once per developer
pipx install mcp-vector-search

# Index project (one person, commit index to Git)
claude-mpm search "authentication patterns"

# All team members can search
/mpm-search "payment processing logic"
/mpm-search "similar database queries"
/mpm-search "error handling patterns"
```

**Benefits:**
- Discover existing implementations before writing new code
- Find similar patterns for consistency
- Avoid duplicating functionality
- Learn from team's existing code

---

## Shared Knowledge Management

### Project Memory (kuzu-memory)

**Installation (each team member):**
```bash
pipx install kuzu-memory
```

**Shared Project Memory:**
- Stored in `.kuzu-memory/` directory
- Commit to Git for team access
- Automatically enriches all agent interactions
- Learns project patterns over time

**What Gets Remembered:**
- Architectural decisions
- Code patterns and conventions
- Common solutions to problems
- Project-specific constraints
- Team preferences

**Example Workflow:**

**Developer A:**
```
/mpm-engineer "Implement new API endpoint using our standard patterns"
# kuzu-memory provides context:
# - Existing API patterns
# - Authentication approach
# - Error handling conventions
# - Response format standards
```

**Developer B (different session):**
```
/mpm-engineer "Add another API endpoint"
# Same context automatically provided
# Consistency across team members
```

### Documentation as Knowledge Base

**Maintain Comprehensive Docs:**

```bash
# Documentation agent for team docs
/mpm-docs "Document API authentication approach"
/mpm-docs "Create architecture decision record for service layer"
/mpm-docs "Update deployment guide with new procedures"
```

**Commit all documentation:**
- README updates
- Architecture decision records (ADRs)
- API documentation
- Deployment guides
- Troubleshooting guides

**Benefits:**
- Single source of truth
- Onboarding resource
- Historical context
- Decision tracking

---

## Best Practices

### 1. Session Handoffs

**Always:**
- Commit resume logs to Git
- Reference resume logs in PRs
- Document key decisions
- Clearly state next steps

**Never:**
- Assume context carries over without resume log
- Skip documentation for "quick fixes"
- Leave session without generating resume log
- Delete resume logs (they're small and valuable)

### 2. Agent Memory Management

**Do:**
- Update agent memories with project conventions
- Commit `.claude-mpm/memories/` to Git
- Review and update memories periodically
- Document project-specific patterns

**Don't:**
- Store sensitive information in memories
- Over-document obvious patterns
- Duplicate information across agent memories
- Ignore outdated memories

### 3. Code Search & Discovery

**Before implementing:**
- Search for existing implementations
- Check for similar patterns
- Review team's code conventions
- Consult shared memories

**Use semantic search:**
```
/mpm-search "existing authentication implementations"
# Before writing new auth code
```

### 4. Team Configuration

**Project-level config:**
- Commit `.claude-mpm/configuration.yaml`
- Standardize agent presets
- Configure resume log settings
- Set consistent token budgets

**User-level config:**
- Individual preferences (`~/.claude-mpm/configuration.yaml`)
- Personal API keys
- User-specific skills
- Custom agent repositories

### 5. Communication

**Document in resume logs:**
- Key architectural decisions
- Technical trade-offs made
- Known issues or limitations
- Suggestions for next developer

**Use commit messages:**
- Reference resume logs
- Link to related PRs
- Explain context
- Tag team members

### 6. Quality Gates

**Before handoff:**
- Run full test suite
- Security audit (if applicable)
- Code review via Claude MPM
- Generate resume log

**QA checklist:**
- Test coverage ≥80%
- Security scan passed
- Performance benchmarks met
- Documentation updated

---

## Troubleshooting Team Issues

### Conflicting Sessions

**Issue:** Multiple users modifying same files

**Solution:**
- Use Git branches for parallel work
- Coordinate via PR reviews
- Use monitoring dashboard to see active sessions
- Resume logs for handoffs, not simultaneous editing

### Inconsistent Agent Behavior

**Issue:** Agents behaving differently for different team members

**Solution:**
- Ensure `.claude-mpm/` directory committed to Git
- Verify agent repositories synced (`claude-mpm agent-source list`)
- Check agent memories are shared (`.claude-mpm/memories/`)
- Update to same Claude MPM version

### Resume Log Not Loading

**Issue:** Resume log doesn't load automatically

**Solution:**
```bash
# Verify resume logs exist
ls .claude-mpm/resume-logs/

# Check configuration
cat .claude-mpm/configuration.yaml

# Manually load resume log
/mpm-resume "Load resume log from .claude-mpm/resume-logs/20260107_140000.md"
```

### Memory Not Syncing

**Issue:** kuzu-memory not working across team

**Solution:**
- Verify `.kuzu-memory/` directory exists
- Commit to Git
- Each user runs: `pipx install kuzu-memory`
- Verify: `claude-mpm verify --service kuzu-memory`

---

## Advanced Team Workflows

### Sprint Planning with Claude MPM

**Sprint Kickoff:**
```bash
# PM analyzes backlog
/mpm-research "Analyze sprint backlog and estimate effort for each ticket"

# PM creates technical specifications
/mpm-docs "Create technical specs for sprint stories"

# Generate resume log for team
```

**Sprint Execution:**
- Developers resume PM's planning session
- Full context for all sprint stories
- Consistent understanding across team

**Sprint Review:**
```bash
# Generate sprint summary
/mpm-docs "Summarize completed work this sprint with links to PRs"
/mpm-research "Identify technical debt introduced this sprint"
```

### Incident Response

**On-Call Engineer:**
```bash
# Investigate incident
/mpm-research "Analyze recent errors in production logs"
/mpm-security "Check if incident is security-related"

# Create incident report via resume log
```

**Follow-up Developer:**
```bash
# Resume incident investigation
claude-mpm run --resume

# Fix root cause
/mpm-engineer "Fix identified issue from incident investigation"
```

### Onboarding New Team Members

**Create onboarding guide:**
```bash
/mpm-docs "Create onboarding guide with project overview and setup instructions"
/mpm-research "Analyze codebase and create architecture overview for new developers"
```

**New developer workflow:**
```bash
# Read resume logs chronologically
cat .claude-mpm/resume-logs/*.md | less

# Learn from agent memories
cat .claude-mpm/memories/*.md

# Ask questions
/mpm-research "Explain authentication flow in plain terms"
```

---

## Next Steps

### Learn More

- **[User Guide](../user/user-guide.md)** - Complete user documentation
- **[Resume Logs](../user/resume-logs.md)** - Session continuity
- **[Agent Sources](../user/agent-sources.md)** - Managing agent repositories
- **[Skills Guide](../user/skills-guide.md)** - Custom skills

### Team Resources

- **[Architecture](../developer/ARCHITECTURE.md)** - System design
- **[Contributing](../developer/03-development/README.md)** - How to contribute
- **[API Reference](../reference/api-overview.md)** - Complete API documentation

### Tools for Teams

- **[kuzu-memory](https://github.com/bobmatnyc/kuzu-memory)** - Shared project memory
- **[mcp-vector-search](https://github.com/bobmatnyc/mcp-vector-search)** - Semantic code search
- **[Monitoring Dashboard](../developer/11-dashboard/README.md)** - Real-time observability

---

**Last updated:** 2026-01-07
**Version:** 1.0.0
**Feedback:** Submit issues at https://github.com/bobmatnyc/claude-mpm/issues
