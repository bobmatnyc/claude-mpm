# Context Optimization Guide

**Version**: 1.0.0
**Last Updated**: January 2026
**Audience**: Intermediate MPM users (after initial learning phase)

---

## Table of Contents

1. [Overview](#overview)
2. [Understanding Context Bloat](#understanding-context-bloat)
3. [Initial Setup Strategy](#initial-setup-strategy)
4. [When to Optimize](#when-to-optimize)
5. [Agent Selection Optimization](#agent-selection-optimization)
6. [Skill Selection Optimization](#skill-selection-optimization)
7. [Optimization Decision Tree](#optimization-decision-tree)
8. [Configuration Audit Checklist](#configuration-audit-checklist)
9. [Before/After Examples](#beforeafter-examples)
10. [Iterative Optimization](#iterative-optimization)
11. [Related Documentation](#related-documentation)

---

## Overview

**TL;DR**: During quickstart, accepting all default agents and skills is easy for learning, but causes context bloat. Once familiar with MPM, optimize your configuration to match your actual project needs.

### What This Guide Covers

- Understanding context bloat and its impact
- Strategies for optimizing agent and skill selections
- Project-type-specific recommendations
- Step-by-step optimization workflow
- Measuring and validating improvements

### Who Should Use This Guide

✅ **You should optimize if**:
- You've used MPM for 2+ weeks or 10+ sessions
- You notice slow responses or confusion
- Your project uses a specific tech stack (Python-only, React-only, etc.)
- You understand which MPM features you use regularly

❌ **Wait to optimize if**:
- You're still learning MPM basics
- Your project tech stack is evolving
- You're exploring different workflows
- You haven't completed 5+ tasks with MPM

---

## Understanding Context Bloat

### What is Context Bloat?

**Context bloat** occurs when MPM loads too many agent instructions and skills into Claude's context window, leaving less room for your actual project code and conversation.

**Example**: Loading 47 agents + 100 skills = ~150,000 tokens of context. Your 200K token limit now has only 50K left for code and conversation.

### How It Affects MPM Performance

| Symptom | Cause | Impact |
|---------|-------|--------|
| **Slow Responses** | Claude processes more context before generating | 2-5x slower response times |
| **Agent Confusion** | Too many similar agents create routing ambiguity | Wrong agent delegations |
| **Irrelevant Suggestions** | Agents for unused tech suggest inappropriate solutions | Wasted time reviewing bad suggestions |
| **Reduced Code Context** | Less room for your actual codebase | Agents miss important code patterns |
| **Higher Costs** | Every token costs money (input + output) | 2-3x higher API costs |

### Signs Your Configuration Has Too Much Context

**Performance Indicators**:
- ⏱️ Responses take >30 seconds for simple tasks
- 🔄 Frequent "thinking..." pauses between agent delegations
- 📉 Quality degradation (agents missing obvious details)

**Behavioral Indicators**:
- 🤔 PM delegates to irrelevant agents (Java engineer for Python project)
- 🔀 Agents suggest tools/frameworks not in your project
- 📝 Responses include boilerplate for technologies you don't use
- ❓ Agents ask clarifying questions about stack you've already specified

**Configuration Indicators**:
- 📊 More than 15-20 agents deployed
- 🎯 Agents for 3+ languages when project uses 1-2
- 📦 Skills for frameworks/tools you don't use
- 🌐 Multiple frontend framework agents (React + Vue + Angular)

### Impact on Response Quality and Speed

**Quantitative Impact**:
```
Minimal Config (6 agents):
- Context usage: ~40K tokens
- Average response: 8-12 seconds
- Code context available: ~160K tokens

Default Config (47 agents):
- Context usage: ~150K tokens
- Average response: 25-40 seconds
- Code context available: ~50K tokens

Bloated Config (47 agents + 100 skills):
- Context usage: ~180K tokens
- Average response: 45-90 seconds
- Code context available: ~20K tokens
```

**Qualitative Impact**:
- **Focus**: Fewer agents = clearer delegation paths
- **Relevance**: Targeted skills = better suggestions
- **Speed**: Less context = faster processing
- **Accuracy**: More room for code = better understanding

---

## Initial Setup Strategy

### Why Defaults Are Acceptable for Learning

**During your first 1-2 weeks with MPM**, accepting all defaults is recommended:

✅ **Advantages**:
- **Explore capabilities**: See all available agents in action
- **Discover workflows**: Learn how different agents collaborate
- **Understand delegation**: Observe PM routing decisions
- **Avoid premature optimization**: Don't optimize what you don't understand yet

⚠️ **Trade-offs**:
- Slower responses (acceptable during learning)
- Higher token costs (learn first, optimize later)
- Some irrelevant suggestions (educational to see what agents do)

### The Learning Phase Timeline

**Week 1: Full Exploration**
- Deploy all default agents
- Try different task types
- Observe which agents get invoked
- Note which agents you never use

**Week 2: Pattern Recognition**
- Identify your common workflows
- Notice which agents handle most tasks
- Track which skills are actually useful
- Document which agents cause confusion

**Week 3+: Optimization**
- Remove unused agents
- Disable irrelevant skills
- Test optimized configuration
- Measure improvements

---

## When to Optimize

### Indicators It's Time to Optimize

**Time-Based Triggers**:
- ✅ After 2+ weeks of MPM usage
- ✅ After 10+ completed tasks/sessions
- ✅ When your tech stack has stabilized

**Experience-Based Triggers**:
- ✅ You can predict which agents will be invoked
- ✅ You recognize patterns in PM delegation
- ✅ You know which MPM features you use regularly

**Performance-Based Triggers**:
- 🚨 **Slow responses** (>30s for simple tasks)
- 🚨 **Agent confusion** (wrong delegations happening frequently)
- 🚨 **Irrelevant suggestions** (agents suggesting unused tech)
- 🚨 **High token costs** (>$5/day for small project)

**Project-Based Triggers**:
- ✅ Tech stack clearly defined (Python backend only, React frontend only, etc.)
- ✅ Framework decisions finalized (FastAPI, not Django)
- ✅ Project structure established (microservices vs monolith)
- ✅ Team workflow defined (how you use MPM daily)

### When NOT to Optimize

❌ **Too Early**:
- Less than 1 week of MPM usage
- Less than 5 completed tasks
- Still exploring what MPM can do
- Tech stack still evolving

❌ **Wrong Reasons**:
- "I want the fastest possible setup" (premature optimization)
- "I think I know what I need" (without data)
- "Someone told me to disable agents" (cargo culting)

---

## Agent Selection Optimization

### Essential Agents for All Projects

**Universal Core** (always keep these):
- `universal/memory-manager` - Project context and memory
- `universal/research` - Documentation lookup and research
- `documentation/documentation` - Doc generation
- `qa/qa` - General quality assurance
- `ops/core/ops` - Basic operations support

**Why**: These agents provide fundamental MPM capabilities regardless of tech stack.

### Project-Type-Specific Recommendations

#### Python Backend Only

**Keep**:
- `engineer/backend/python-engineer` - Python development
- `qa/api-qa` - API testing
- `security/security` - Security scanning
- Universal agents (listed above)

**Disable**:
- ❌ `engineer/frontend/*` - All frontend agents
- ❌ `engineer/backend/java-engineer` - Other backend languages
- ❌ `engineer/backend/rust-engineer`
- ❌ `qa/web-qa` - Frontend testing

**Result**: ~8 agents instead of 47 (85% reduction)

**Command**:
```bash
# Deploy Python backend preset
claude-mpm agents deploy --preset python-dev

# Or manually
claude-mpm agents deploy universal/memory-manager universal/research
claude-mpm agents deploy documentation/documentation
claude-mpm agents deploy engineer/backend/python-engineer
claude-mpm agents deploy qa/qa qa/api-qa
claude-mpm agents deploy ops/core/ops security/security
```

---

#### React Frontend Only

**Keep**:
- `engineer/frontend/react-engineer` - React development
- `engineer/data/typescript-engineer` - TypeScript support
- `qa/web-qa` - Frontend/UI testing
- Universal agents

**Disable**:
- ❌ `engineer/backend/*` - All backend agents
- ❌ `engineer/frontend/vue-engineer` - Other frontend frameworks
- ❌ `engineer/frontend/angular-engineer`
- ❌ `qa/api-qa` - Backend API testing (unless calling external APIs)

**Result**: ~9 agents instead of 47 (80% reduction)

**Command**:
```bash
# Deploy React frontend preset
claude-mpm agents deploy --preset react-dev
```

---

#### Full-Stack (Python + React)

**Keep**:
- `engineer/backend/python-engineer` - Backend development
- `engineer/frontend/react-engineer` - Frontend development
- `engineer/data/typescript-engineer` - TypeScript support
- `qa/qa`, `qa/api-qa`, `qa/web-qa` - Full testing coverage
- `documentation/ticketing` - Task management
- Universal agents + Security + Ops

**Disable**:
- ❌ Other language engineers (Java, Rust, Go, etc.)
- ❌ Other frontend frameworks (Vue, Angular, etc.)
- ❌ Specialized agents you don't need

**Result**: ~12 agents instead of 47 (75% reduction)

**Command**:
```bash
# Deploy full-stack preset
claude-mpm agents deploy --preset python-fullstack
```

---

#### Microservices (Multiple Languages)

**Keep**:
- Engineers for each language you actually use
- `ops/kubernetes/k8s-ops` - Container orchestration
- `ops/docker/docker-ops` - Containerization
- All QA agents (api-qa, integration-qa)
- Security agents
- Universal agents

**Disable**:
- ❌ Languages/frameworks not in your stack
- ❌ Monolith-specific agents

**Result**: ~15-18 agents (depends on language count)

---

#### Data/ML Projects

**Keep**:
- `engineer/data/data-engineer` - Data pipelines
- `engineer/backend/python-engineer` - Python for ML
- `engineer/data/sql-engineer` - Database work
- Universal agents
- Security (for data handling)

**Disable**:
- ❌ Frontend agents (unless building dashboards)
- ❌ API-focused agents (unless building APIs)
- ❌ Mobile agents

**Result**: ~10 agents

---

### How to Evaluate Agent Usefulness

**Step 1: Track Agent Invocations**

Monitor your sessions for 1-2 weeks and note which agents are invoked:

```bash
# After each session, review the session log
# Look for agent delegation patterns
# Example log excerpt:
[PM] Delegating to python-engineer...
[PM] Delegating to qa...
[PM] Delegating to documentation...
```

**Step 2: Create Agent Usage Matrix**

| Agent | Sessions Used | % of Total | Keep? |
|-------|---------------|------------|-------|
| python-engineer | 15/15 | 100% | ✅ Yes |
| qa | 12/15 | 80% | ✅ Yes |
| documentation | 8/15 | 53% | ✅ Yes |
| react-engineer | 6/15 | 40% | ✅ Yes (if doing frontend) |
| java-engineer | 0/15 | 0% | ❌ No |
| rust-engineer | 0/15 | 0% | ❌ No |

**Step 3: Apply 80/20 Rule**

- ✅ **Keep**: Agents used in 20%+ of sessions
- ⚠️ **Review**: Agents used in 10-20% of sessions (project-specific)
- ❌ **Remove**: Agents used in <10% of sessions

**Step 4: Consider Future Needs**

- Keep agents for planned work (e.g., if adding frontend next month)
- Remove agents for deprecated tech (e.g., old framework being replaced)
- Add agents as needs emerge (iterative optimization)

### Disabling vs. Removing Agents

**Disabling** (toggle off):
```bash
# Legacy toggle approach
claude-mpm configure
# Navigate to: Agent Management > Toggle agents
# Uncheck agents to disable
```

**Pros**: Agents stay in `.claude/agents/`, can re-enable easily
**Cons**: Still occupy disk space, may show in listings

---

**Removing** (delete):
```bash
# Recommended approach
claude-mpm agents remove engineer/backend/java-engineer
claude-mpm agents remove engineer/backend/rust-engineer
```

**Pros**: Cleaner configuration, no disk space used
**Cons**: Must re-deploy if needed later (but this is fast with presets)

---

**Recommendation**: **Remove unused agents**. Re-deploying is fast, and keeping only what you need is clearer.

---

## Skill Selection Optimization

### Understanding Skills vs. Agents

**Agents**: Specialized personas with domain expertise (Python Engineer, QA, etc.)
**Skills**: Reusable tools/workflows agents can invoke (pytest runner, docker deployment, etc.)

**Key Difference**: Agents are always loaded; skills are loaded when agents need them.

### Identifying Relevant Skills for Your Stack

**Step 1: List Deployed Skills**

```bash
# Check user-level skills
ls -1 ~/.claude/skills/

# Check project-level skills
ls -1 .claude/skills/
```

**Step 2: Match Skills to Tech Stack**

**Python Backend Example**:
- ✅ Keep: `pytest`, `black`, `mypy`, `fastapi-testing`
- ❌ Remove: `jest`, `cypress`, `react-testing-library`

**React Frontend Example**:
- ✅ Keep: `jest`, `react-testing-library`, `eslint`, `prettier`
- ❌ Remove: `pytest`, `black`, `mypy`

**Full-Stack Example**:
- ✅ Keep: Skills for both frontend and backend
- ⚠️ Review: Do you need BOTH jest AND pytest? (Yes, if full-stack)

### Removing Unused Skills

**Project-Level Skills** (shared with team):
```bash
# Remove from project
rm -rf .claude/skills/unused-skill-name

# Commit the change
git add .claude/skills/
git commit -m "Remove unused skill: unused-skill-name"
```

**User-Level Skills** (personal):
```bash
# Remove from user directory
rm -rf ~/.claude/skills/unused-skill-name

# Restart Claude Code (skills load at startup)
```

### Custom Skill Development vs. Using Existing

**Use Existing Skills When**:
- ✅ Skill matches your workflow
- ✅ Maintained and up-to-date
- ✅ Well-documented

**Create Custom Skill When**:
- ⚠️ Project has unique workflow
- ⚠️ Company-specific tools/processes
- ⚠️ Existing skill doesn't fit

**See**: [Skills Management Guide](skills-management.md) for skill development.

### Skill Optimization Checklist

- [ ] Audit deployed skills (`ls ~/.claude/skills/`)
- [ ] Match skills to current tech stack
- [ ] Remove skills for unused frameworks/tools
- [ ] Remove duplicate skills (multiple testing frameworks if only using one)
- [ ] Keep universal skills (git, docker if used, etc.)
- [ ] Document removed skills (in case needed later)
- [ ] Restart Claude Code after changes

---

## Optimization Decision Tree

Use this decision tree to determine your optimal configuration:

```
START: What is your project type?
│
├─ Single Backend Language (Python/Node.js/Java/etc.)
│  └─ Does it have a frontend?
│     ├─ No → Deploy: `minimal` or `{language}-dev` preset
│     │      Agents: ~6-8
│     └─ Yes → What frontend framework?
│        ├─ React → Deploy: `{language}-fullstack` preset
│        │         Agents: ~12
│        ├─ Vue/Angular → Deploy minimal + language + frontend agent
│        │              Agents: ~9-10
│        └─ None (API only) → Deploy: `{language}-dev` preset
│                             Agents: ~8
│
├─ Full-Stack (Backend + Frontend)
│  └─ Same language both sides?
│     ├─ Yes (e.g., Next.js) → Deploy: `nextjs-fullstack` preset
│     │                        Agents: ~10
│     └─ No (e.g., Python + React) → Deploy: `python-fullstack` preset
│                                     Agents: ~12
│
├─ Microservices (Multiple Services)
│  └─ How many different languages?
│     ├─ 1-2 → Deploy preset for each + ops agents
│     │        Agents: ~15-18
│     ├─ 3+ → Deploy minimal + needed language agents + ops
│     │      Agents: ~18-22
│     └─ Many → Keep defaults, use /mpm-config to toggle per task
│             Agents: ~30-35 (selective disabling)
│
├─ Data/ML Project
│  └─ Need web interface?
│     ├─ No → Deploy: minimal + data-engineer + python-engineer
│     │       Agents: ~8
│     └─ Yes → Deploy: minimal + data + python + react
│               Agents: ~12
│
└─ Mobile App
   └─ What framework?
      ├─ React Native → Deploy: minimal + react-engineer + mobile agents
      │                 Agents: ~10
      ├─ Flutter → Deploy: minimal + flutter-engineer
      │           Agents: ~8
      └─ Native (iOS/Android) → Deploy: minimal + platform agent
                                Agents: ~8
```

### Key Questions to Ask

1. **What languages does my project actually use?**
   - Deploy only engineers for those languages

2. **Do I have a frontend?**
   - No → Skip all frontend agents
   - Yes → Deploy only the framework you use

3. **Do I write tests?**
   - Yes → Keep qa agents
   - No → Keep minimal qa for code review

4. **Do I deploy to production?**
   - Yes → Keep ops agents (docker, k8s, etc.)
   - No (local dev only) → Skip ops agents

5. **Do I need security scanning?**
   - Production app → Keep security agents
   - Learning project → Optional

6. **Am I using microservices?**
   - Yes → Keep orchestration agents (k8s-ops, docker-ops)
   - No → Skip

---

## Configuration Audit Checklist

Use this checklist to audit your current configuration:

### Agent Audit

- [ ] **List all deployed agents**: `claude-mpm agents list`
- [ ] **Identify your project's primary language(s)**
- [ ] **Check for agents of unused languages**
  - [ ] Java agent in Python-only project?
  - [ ] Rust agent in JavaScript project?
  - [ ] Go agent in Ruby project?
- [ ] **Check for multiple frontend framework agents**
  - [ ] React + Vue + Angular all deployed? (pick one)
- [ ] **Verify essential agents present**
  - [ ] memory-manager
  - [ ] research
  - [ ] documentation
  - [ ] At least one engineer for your stack
  - [ ] qa
  - [ ] ops (if deploying)
- [ ] **Remove unused language agents**
- [ ] **Remove unused framework agents**

### Skill Audit

- [ ] **List user-level skills**: `ls -1 ~/.claude/skills/`
- [ ] **List project-level skills**: `ls -1 .claude/skills/`
- [ ] **Match skills to tech stack**
  - [ ] Testing framework skills match project (pytest/jest/etc.)
  - [ ] Linter skills match project (black/eslint/etc.)
  - [ ] Build tool skills match project (webpack/vite/etc.)
- [ ] **Remove skills for unused frameworks**
- [ ] **Remove duplicate testing tools** (if only using one)
- [ ] **Keep universal skills** (git, docker if used)

### Performance Audit

- [ ] **Test response time baseline**
  - [ ] Run simple task: "List all Python files"
  - [ ] Record response time
- [ ] **Count total agents**: Target <15 for single-stack projects
- [ ] **Count total skills**: Target <20 for single-stack projects
- [ ] **Estimate context usage**:
  - 6 agents ≈ 40K tokens
  - 12 agents ≈ 70K tokens
  - 20 agents ≈ 100K tokens
  - 47 agents ≈ 150K tokens

### Configuration Files Audit

- [ ] **Check `.claude/agents/` directory**
  - [ ] Only agents you actually use
  - [ ] No disabled agents (remove instead)
- [ ] **Check `.claude/skills/` directory**
  - [ ] Only skills for your tech stack
  - [ ] Remove unused skills
- [ ] **Check `~/.claude/skills/` directory**
  - [ ] User-level skills are globally useful
  - [ ] No project-specific skills here
- [ ] **Review `CLAUDE.md`**
  - [ ] Project info matches current stack
  - [ ] No references to removed frameworks

### Post-Optimization Validation

- [ ] **Restart Claude Code** (skills/agents load at startup)
- [ ] **Test basic task**: "Add a simple function with tests"
- [ ] **Verify correct agents invoked**
  - [ ] PM delegates to expected agents
  - [ ] No irrelevant agent suggestions
- [ ] **Measure improvement**
  - [ ] Response time faster?
  - [ ] Fewer confused delegations?
  - [ ] More relevant suggestions?
- [ ] **Document changes**
  - [ ] List removed agents/skills
  - [ ] Note why they were removed
  - [ ] Keep list for future reference

---

## Before/After Examples

### Example 1: Python Backend API

**Before Optimization** (Default Configuration):

```bash
# Deployed agents
claude-mpm agents list
# Output: 47 agents

# Includes unnecessary agents:
- engineer/frontend/react-engineer
- engineer/frontend/vue-engineer
- engineer/frontend/angular-engineer
- engineer/backend/java-engineer
- engineer/backend/rust-engineer
- engineer/backend/go-engineer
- qa/web-qa
- qa/mobile-qa
# ... and 39 others
```

**Performance Metrics**:
- Context usage: ~150K tokens
- Average response time: 35 seconds
- Agent confusion: High (PM occasionally delegates to frontend agents)
- Token cost: $8.50/day

---

**After Optimization** (Targeted Configuration):

```bash
# Deploy Python backend preset
claude-mpm agents deploy --preset python-dev

# Deployed agents (8 total):
- universal/memory-manager
- universal/research
- documentation/documentation
- engineer/backend/python-engineer
- qa/qa
- qa/api-qa
- ops/core/ops
- security/security
```

**Performance Metrics**:
- Context usage: ~45K tokens
- Average response time: 10 seconds
- Agent confusion: None (clear delegation paths)
- Token cost: $2.80/day

**Improvement**: 71% faster, 67% lower cost, zero confusion

---

### Example 2: React Frontend App

**Before Optimization** (Default Configuration):

```bash
# Deployed: 47 agents
# Including backend agents not needed:
- engineer/backend/python-engineer
- engineer/backend/java-engineer
- qa/api-qa
- ops/kubernetes/k8s-ops
# Plus other frontend frameworks:
- engineer/frontend/vue-engineer
- engineer/frontend/angular-engineer
```

**Performance Metrics**:
- Context usage: ~155K tokens
- Average response time: 38 seconds
- Irrelevant suggestions: Frequent (backend patterns for frontend code)
- Token cost: $9.20/day

---

**After Optimization**:

```bash
# Deploy React frontend preset
claude-mpm agents deploy --preset react-dev

# Deployed agents (9 total):
- universal/memory-manager
- universal/research
- documentation/documentation
- engineer/frontend/react-engineer
- engineer/data/typescript-engineer
- qa/qa
- qa/web-qa
- ops/core/ops
- security/security
```

**Performance Metrics**:
- Context usage: ~50K tokens
- Average response time: 11 seconds
- Irrelevant suggestions: Rare
- Token cost: $3.10/day

**Improvement**: 71% faster, 66% lower cost, better focus

---

### Example 3: Full-Stack (Python + React)

**Before Optimization**:

```bash
# Deployed: 47 agents
# Including agents for unused stacks:
- engineer/backend/java-engineer
- engineer/backend/rust-engineer
- engineer/frontend/vue-engineer
- engineer/frontend/angular-engineer
- engineer/mobile/*
- ops/kubernetes/* (not using k8s)
```

**Performance Metrics**:
- Context usage: ~160K tokens
- Average response time: 42 seconds
- Token cost: $11.50/day

---

**After Optimization**:

```bash
# Deploy full-stack preset
claude-mpm agents deploy --preset python-fullstack

# Deployed agents (12 total):
- universal/memory-manager
- universal/research
- universal/code-analyzer
- documentation/documentation
- documentation/ticketing
- engineer/backend/python-engineer
- engineer/frontend/react-engineer
- qa/qa
- qa/api-qa
- qa/web-qa
- ops/core/ops
- security/security
```

**Performance Metrics**:
- Context usage: ~70K tokens
- Average response time: 15 seconds
- Token cost: $4.20/day

**Improvement**: 64% faster, 63% lower cost, complete coverage

---

### Example 4: Microservices (Python + Node.js + React)

**Before Optimization**:

```bash
# Deployed: 47 agents (all defaults)
# Many unused for this specific stack
```

**After Optimization**:

```bash
# Custom deployment for multi-language stack
claude-mpm agents deploy universal/memory-manager universal/research
claude-mpm agents deploy documentation/documentation documentation/ticketing
claude-mpm agents deploy engineer/backend/python-engineer
claude-mpm agents deploy engineer/backend/javascript-engineer
claude-mpm agents deploy engineer/frontend/react-engineer
claude-mpm agents deploy qa/qa qa/api-qa qa/web-qa
claude-mpm agents deploy ops/docker/docker-ops ops/kubernetes/k8s-ops
claude-mpm agents deploy security/security

# Total: 15 agents
```

**Performance Metrics**:
- Context usage: ~85K tokens
- Average response time: 18 seconds
- Token cost: $5.50/day

**Improvement**: 57% faster, 52% lower cost, full stack coverage

---

## Iterative Optimization

### Testing Configuration Changes

**Step 1: Establish Baseline**

```bash
# Before optimization
# Run 3 representative tasks and record:
# - Response time
# - Agent delegation accuracy
# - Token usage (check Claude Code logs)

# Example baseline tasks:
# Task 1: "Add a simple endpoint to the API"
# Task 2: "Write tests for user authentication"
# Task 3: "Update documentation for deployment"
```

**Step 2: Make Incremental Changes**

```bash
# Don't optimize everything at once
# Start with obvious removals:

# Week 1: Remove clearly unused language agents
claude-mpm agents remove engineer/backend/java-engineer
claude-mpm agents remove engineer/backend/rust-engineer

# Test with same 3 tasks
# Measure improvement
```

**Step 3: Monitor and Adjust**

```bash
# Week 2: Remove unused frontend frameworks
claude-mpm agents remove engineer/frontend/vue-engineer
claude-mpm agents remove engineer/frontend/angular-engineer

# Test again
# Ensure no regressions
```

**Step 4: Fine-Tune**

```bash
# Week 3: Optimize skills
rm -rf ~/.claude/skills/jest  # If only using pytest
rm -rf ~/.claude/skills/cypress  # If not doing E2E testing

# Final validation
```

### A/B Testing Different Setups

**Scenario**: Unsure if you need `code-analyzer` agent?

**Setup A** (with code-analyzer):
```bash
# Deploy preset with code-analyzer
claude-mpm agents deploy --preset python-fullstack
```

**Setup B** (without code-analyzer):
```bash
# Deploy preset
claude-mpm agents deploy --preset python-dev
# Add only frontend agent
claude-mpm agents deploy engineer/frontend/react-engineer
```

**Test Both**:
- Use Setup A for 1 week (Mon-Wed)
- Use Setup B for 1 week (Thu-Fri + next Mon)
- Compare:
  - Code quality suggestions received
  - Usefulness of suggestions
  - Response time difference
  - Token cost difference

**Decision**: Keep the agent if:
- ✅ Suggestions are useful >50% of the time
- ✅ Adds <10% to response time
- ✅ Provides value you can't get elsewhere

### Measuring Improvement

**Quantitative Metrics**:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Avg. Response Time | 35s | 12s | -66% ⬆️ |
| Agent Count | 47 | 8 | -83% ⬆️ |
| Context Usage | 150K | 45K | -70% ⬆️ |
| Daily Token Cost | $8.50 | $2.80 | -67% ⬆️ |
| Confused Delegations | 3/day | 0/day | -100% ⬆️ |

**Qualitative Metrics**:

- **Agent Relevance**: Are delegated agents appropriate for the task?
  - Before: 70% relevant
  - After: 98% relevant

- **Suggestion Quality**: Are agent suggestions useful?
  - Before: 65% useful
  - After: 92% useful

- **Developer Experience**: Satisfaction with MPM performance
  - Before: "Slow but capable"
  - After: "Fast and focused"

**How to Measure**:

```bash
# 1. Time your tasks
time claude-mpm run
# Then run a standard task
# Record total time

# 2. Count agents
claude-mpm agents list | wc -l

# 3. Estimate context (see audit checklist)

# 4. Track delegations
# Review session logs, note which agents were invoked
# Flag irrelevant delegations

# 5. Document
# Keep a simple log:
# Date | Config | Task | Time | Agents Invoked | Notes
```

### Optimization Workflow

**Monthly Review Process**:

```bash
# Every 4 weeks, audit your configuration

# 1. Review agent usage
# Which agents were used in last month?
# Which agents were NEVER used?

# 2. Review new project needs
# Did tech stack change?
# New frameworks added?
# Old frameworks deprecated?

# 3. Update configuration
# Remove unused agents
# Add newly needed agents
# Update skills

# 4. Test and validate
# Run representative tasks
# Ensure quality maintained
# Measure improvements

# 5. Document changes
# Update project notes
# Share with team if applicable
```

**Team Synchronization**:

If working in a team:

```bash
# Option 1: Shared preset for team
# Define team preset in configuration
claude-mpm agents deploy --preset team-python-backend

# Option 2: Individual optimization with shared baseline
# Team agrees on minimal required agents
# Individuals add as needed

# Option 3: Profile-based configuration
# Use /mpm-config to toggle per task
# Keep larger set, selectively enable
```

**See**: [Agent Presets Guide](../user/agent-presets.md) for team workflows

---

## Related Documentation

### Getting Started
- **[Quickstart Guide](../getting-started/quickstart.md)** - Initial MPM setup (accepts defaults)
- **[Agent Presets Guide](../user/agent-presets.md)** - Pre-configured agent bundles

### Agent Management
- **[Agent Deployment Guide](single-tier-agent-system.md)** - How agents are deployed
- **[CLI Agents Reference](../reference/cli-agents.md)** - Command-line interface
- **[Auto-Configuration Guide](../user/auto-configuration.md)** - Stack detection and auto-setup

### Skills Management
- **[Skills Management Guide](skills-management.md)** - Managing skills
- **[Skills System Guide](skills-system.md)** - How skills work
- **[Skills Deployment Guide](skills-deployment-guide.md)** - Deploying skills

### Configuration
- **[Configurator Menu Guide](configurator-menu.md)** - Interactive configuration
- **[Configuration Reference](../configuration/reference.md)** - Configuration file format

### Monitoring & Debugging
- **[Monitoring Guide](monitoring.md)** - Track agent performance
- **[Doctor Command Guide](doctor-command.md)** - Diagnose issues

---

## Summary

**Key Takeaways**:

1. ✅ **Learn first, optimize later**: Accept defaults during first 2 weeks
2. 🎯 **Match agents to tech stack**: Only deploy agents for technologies you use
3. 📊 **Data-driven decisions**: Track agent usage before removing
4. 🔄 **Iterate incrementally**: Optimize gradually, test after each change
5. 📈 **Measure improvement**: Compare response times, costs, and quality
6. 👥 **Team coordination**: Agree on baseline configuration if working in team

**Quick Wins**:

- Remove agents for languages you don't use (instant 60-80% context reduction)
- Use agent presets for common stacks (one command deployment)
- Remove unused skills (10-20% additional context savings)
- Profile-based toggling for multi-stack projects (selective activation)

**Expected Results**:

After optimization, you should see:
- ⚡ 50-70% faster response times
- 💰 50-70% lower token costs
- 🎯 95%+ relevant agent delegations
- 📊 More context available for your actual code

---

**Questions or Issues?**

- See [FAQ](FAQ.md) for common questions
- Check [Doctor Command Guide](doctor-command.md) for diagnostics
- Review [Monitoring Guide](monitoring.md) for tracking performance

---

**Version History**:
- v1.0.0 (2026-01-08): Initial release
