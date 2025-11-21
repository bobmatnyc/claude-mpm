# Claude Code Skills Deployment Guide

**A comprehensive guide for research agents and developers on deploying, organizing, and recommending Claude Code skills**

## Table of Contents

1. [Overview](#overview)
2. [Architecture & Integration](#architecture--integration)
3. [Deployment Model](#deployment-model)
4. [Skill Structure](#skill-structure)
5. [Deployment Locations](#deployment-locations)
6. [Toolchain Detection](#toolchain-detection)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Examples](#examples)
10. [Research Agent Integration](#research-agent-integration)

---

## Overview

### What Are Claude Code Skills?

Claude Code Skills are **modular capabilities** that extend Claude's functionality through specialized instruction sets, scripts, and resources. They enable Claude to:

- Access expert-level domain knowledge on-demand
- Follow specialized workflows and methodologies
- Integrate with external tools and services
- Maintain consistent practices across projects

### Progressive Disclosure Architecture

Skills use a two-tier loading system to maintain efficiency:

**Tier 1: Metadata (~100 tokens)**
- Skill name, description, categories
- Trigger conditions and activation rules
- Loaded at startup, always in memory

**Tier 2: Full Content (<5k tokens)**
- Detailed instructions and workflows
- Code examples and templates
- Loaded only when skill is activated

**Benefits:**
- Minimal memory overhead for inactive skills
- Fast activation when needed
- Efficient token usage during conversations

### Why Use Skills?

**For Users:**
- Consistent expert-level guidance across sessions
- Reduced need to re-explain project conventions
- Access to battle-tested workflows and patterns

**For Research Agents:**
- Proactive detection of skill gaps during analysis
- Toolchain-specific recommendations
- Enhanced project understanding through skill inventory

---

## Architecture & Integration

### How Claude Code Discovers Skills

Claude Code uses a **startup-only loading** model:

```
1. Claude Code starts
   ↓
2. Scans skill directories for .md files with YAML frontmatter
   ↓
3. Loads Tier 1 metadata for all discovered skills
   ↓
4. Watches for trigger conditions during conversations
   ↓
5. Activates skills (loads Tier 2) when conditions match
   ↓
6. Skills remain active for conversation duration
```

**Critical Insight:** Skills are **only discovered at startup**. Adding new skills requires restarting Claude Code.

### Skill Lifecycle

```
[Deployment] → [Startup Scan] → [Metadata Load] → [Idle State]
                                                      ↓
                                    [Trigger Match] ← [Active Use]
                                                      ↓
                                    [Session End] → [Unload Tier 2]
```

### Integration with MCP Servers

Skills can reference and utilize MCP (Model Context Protocol) servers:

**MCP Servers vs Skills:**

| Aspect | MCP Servers | Skills |
|--------|-------------|--------|
| **Purpose** | External tool integration | Instruction sets & workflows |
| **Loading** | Persistent connections | Progressive disclosure |
| **Examples** | GitHub API, Database access | TDD workflows, Code review |
| **Configuration** | `claude_desktop_config.json` | YAML frontmatter in `.md` |

**Best Practice:** Use skills to orchestrate MCP server usage with domain expertise.

---

## Deployment Model

### Startup-Only Loading

**Key Principle:** Skills are discovered **only at Claude Code startup**.

**Implications:**

✅ **Do:**
- Deploy skills before starting Claude Code sessions
- Restart Claude Code after adding new skills
- Plan skill deployments in batches to minimize restarts

❌ **Don't:**
- Expect hot-reloading of skills during sessions
- Deploy skills mid-conversation and expect immediate availability
- Rely on skills that weren't present at startup

### Restart Requirements

**When Restart is Required:**
- Adding new skill files to skill directories
- Modifying skill YAML frontmatter (name, categories, triggers)
- Removing skills from skill directories

**When Restart is NOT Required:**
- Modifying skill content (Tier 2 instructions) - takes effect on next activation
- Changing MCP server configurations (varies by server)
- Updating project-specific documents (CLAUDE.md, etc.)

### Timing Considerations

**Optimal Deployment Timing:**

1. **Project Initialization** - Deploy all anticipated skills before first session
2. **Toolchain Changes** - Deploy new toolchain skills before working with new tech
3. **Batch Deployment** - Add multiple related skills together to minimize restarts
4. **Maintenance Windows** - Schedule skill updates during natural break points

---

## Skill Structure

### YAML Frontmatter Requirements

Every skill file must start with YAML frontmatter containing metadata:

```yaml
---
name: skill-name
description: Brief description of skill purpose and capabilities
categories:
  - category1
  - category2
triggers:
  - keyword1
  - keyword2
version: "1.0.0"
author: Author Name
license: MIT
---
```

**Required Fields:**
- `name` - Unique identifier for skill (kebab-case recommended)
- `description` - Concise explanation of skill purpose (1-2 sentences)
- `categories` - List of applicable categories for discovery

**Optional Fields:**
- `triggers` - Keywords that auto-activate the skill
- `version` - Semantic version for tracking updates
- `author` - Skill creator attribution
- `license` - License type (MIT, Apache 2.0, etc.)
- `dependencies` - Required MCP servers or other skills

### Progressive Disclosure Structure

**Tier 1: Metadata Section (After YAML)**

```markdown
## Quick Reference

Brief 2-3 sentence overview of core capability.

**When to Use:** Specific trigger scenarios
**Key Features:** Bullet list of 3-5 main capabilities
```

**Tier 2: Detailed Instructions**

```markdown
## Detailed Workflow

### Step 1: Initial Setup
Detailed instructions...

### Step 2: Core Process
Comprehensive guidance...

### Step 3: Validation
Verification steps...

## Examples

Code examples and templates...

## Common Pitfalls

Known issues and solutions...
```

### Example: Complete Skill Structure

```markdown
---
name: test-driven-development
description: Enforce RED-GREEN-REFACTOR TDD cycle for all feature development
categories:
  - testing
  - development-workflow
  - quality
triggers:
  - tdd
  - test-driven
  - write tests
version: "2.1.0"
author: obra
license: MIT
---

# Test-Driven Development

## Quick Reference

Mandatory RED-GREEN-REFACTOR cycle enforcement for all features and bugfixes.

**When to Use:** Before implementing any new feature or bug fix
**Key Features:**
- Write failing test first (RED)
- Implement minimal passing code (GREEN)
- Refactor with safety (REFACTOR)

---

## Detailed Workflow

### Phase 1: RED - Write Failing Test
[Detailed instructions for writing comprehensive failing tests]

### Phase 2: GREEN - Minimal Implementation
[Instructions for implementing just enough code to pass]

### Phase 3: REFACTOR - Improve Design
[Guidance on safe refactoring with test coverage]

## Examples

```python
# Example test-first approach
def test_user_authentication():
    # Write this FIRST
    assert authenticate_user("valid", "password") == True
    assert authenticate_user("invalid", "wrong") == False

# Then implement
def authenticate_user(username, password):
    # Minimal implementation to pass tests
    return username == "valid" and password == "password"
```

## Common Pitfalls

- ❌ Writing implementation before tests
- ❌ Skipping RED phase (test must fail first)
- ❌ Over-engineering in GREEN phase
```

---

## Deployment Locations

### Global Skills Directory

**Location:** `~/.claude/skills/`

**Purpose:** System-wide skills available to all projects

**Use Cases:**
- General development workflows (TDD, debugging, code review)
- Language-agnostic practices (documentation, git workflows)
- Personal preferences and coding standards

**Example Structure:**
```
~/.claude/skills/
├── test-driven-development/
│   └── skill.md
├── systematic-debugging/
│   └── skill.md
├── git-worktrees/
│   └── skill.md
└── code-review-checklist/
    └── skill.md
```

### Project-Local Skills Directory

**Location:** `.claude/skills/` (in project root)

**Purpose:** Project-specific or team-wide skills

**Use Cases:**
- Project-specific conventions and standards
- Team-agreed workflows
- Toolchain-specific configurations
- Domain-specific business logic patterns

**Example Structure:**
```
/path/to/project/
├── .claude/
│   └── skills/
│       ├── project-architecture/
│       │   └── skill.md
│       ├── api-design-standards/
│       │   └── skill.md
│       └── deployment-workflow/
│           └── skill.md
├── src/
└── tests/
```

### Marketplace Plugins

**Installation:** `/plugin marketplace add <organization>/<repository>`

**Official Marketplaces:**
- `anthropics/skills` - Official Anthropic skills
- `obra/superpowers-marketplace` - Battle-tested development workflows
- `djacobsmeyer/claude-skills-engineering` - DevOps and CI/CD
- `zxkane/aws-skills` - AWS-specific development

**Advantages:**
- One-command installation
- Automatic updates
- Version management
- Curated and tested collections

**Example Usage:**
```bash
# Add marketplace
/plugin marketplace add obra/superpowers-marketplace

# Install specific skill
/plugin install test-driven-development@superpowers-marketplace

# List installed skills
/plugin list
```

### Directory Scanning Priority

Claude Code scans in this order:

1. **Project-local skills** (`.claude/skills/`)
2. **Marketplace plugins** (managed by plugin system)
3. **Global skills** (`~/.claude/skills/`)

**Conflict Resolution:** If same skill name exists in multiple locations, project-local takes precedence.

---

## Toolchain Detection

### Technology Stack → Skills Mapping

Research agents should detect project technology and recommend relevant skills:

#### Python Projects

**Detection Signals:**
- `pyproject.toml`, `setup.py`, `requirements.txt`
- `.py` files, `tests/` directory with pytest
- Virtual environment (`venv/`, `.venv/`)

**Recommended Skills:**
- `test-driven-development` - TDD with pytest
- `python-style` - PEP 8 and best practices
- `scientific-packages` - For data science projects
- `aws-cdk-development` - For AWS infrastructure projects

**Example Detection Logic:**
```python
if file_exists("pyproject.toml"):
    if grep_match("pytest", "pyproject.toml"):
        recommend_skill("test-driven-development")
    if grep_match("fastapi|flask|django", "pyproject.toml"):
        recommend_skill("backend-engineer")
    if grep_match("pandas|numpy|scikit", "pyproject.toml"):
        recommend_skill("data-scientist")
```

#### TypeScript/JavaScript Projects

**Detection Signals:**
- `package.json`, `tsconfig.json`
- `.ts`, `.tsx`, `.js`, `.jsx` files
- `node_modules/`, `.next/`, `dist/`

**Recommended Skills:**
- `webapp-testing` - Playwright testing
- `frontend-development` - React/Next.js patterns
- `better-auth` - Authentication frameworks
- `web-frameworks` - Next.js App Router, SSR, SSG

**Example Detection Logic:**
```typescript
if file_exists("package.json"):
    const pkg = parse_json("package.json")
    if (pkg.dependencies["react"]) {
        recommend_skill("frontend-development")
    }
    if (pkg.dependencies["next"]) {
        recommend_skill("web-frameworks")
    }
    if (pkg.devDependencies["playwright"]) {
        recommend_skill("webapp-testing")
    }
```

#### Go Projects

**Detection Signals:**
- `go.mod`, `go.sum`
- `.go` files
- `cmd/`, `pkg/`, `internal/` directory structure

**Recommended Skills:**
- `effective-go-development` - Go best practices
- `claude-flow-go` - Concurrency patterns
- `backend-engineer` - API development

#### Rust Projects

**Detection Signals:**
- `Cargo.toml`, `Cargo.lock`
- `.rs` files
- `src/main.rs`, `src/lib.rs`

**Recommended Skills:**
- `pragmatic-rust-guidelines` - Microsoft Rust standards
- `claude-flow-rust` - Memory safety patterns
- `backend-engineer` - Systems programming

#### DevOps/Infrastructure

**Detection Signals:**
- `.github/workflows/` - GitHub Actions
- `.gitlab-ci.yml` - GitLab CI
- `Dockerfile`, `docker-compose.yml` - Docker
- `terraform/`, `*.tf` - Terraform
- `pulumi/` - Pulumi

**Recommended Skills:**
- `claude-skills-engineering` - CI/CD pipelines
- `devops-claude-skills` - Infrastructure as Code
- `aws-skills` - AWS CDK, serverless
- `kubernetes-operations` - K8s management

### Multi-Dimensional Detection

**Consider Multiple Factors:**

1. **Primary Language** - Core development language
2. **Framework** - Web framework, testing framework
3. **Infrastructure** - Cloud platform, deployment method
4. **Development Stage** - New project vs. maintenance
5. **Team Size** - Solo vs. team collaboration needs

**Example Multi-Factor Analysis:**

```
Project: Next.js application with TypeScript
├── Language: TypeScript → frontend-development
├── Framework: Next.js → web-frameworks
├── Testing: Playwright → webapp-testing
├── Auth: NextAuth → better-auth
├── Deployment: Vercel → (Vercel MCP server)
└── CI/CD: GitHub Actions → claude-skills-engineering

Recommended Skill Stack:
1. web-frameworks (Next.js App Router, SSR)
2. frontend-development (React/TypeScript)
3. webapp-testing (Playwright E2E)
4. better-auth (Authentication)
5. claude-skills-engineering (CI/CD)
```

---

## Best Practices

### Skill Organization

#### Categorization System

Use consistent categories for skill discovery:

**Development Workflow:**
- `testing` - Testing methodologies
- `debugging` - Debugging approaches
- `code-review` - Review processes
- `refactoring` - Code improvement

**Language-Specific:**
- `python` - Python practices
- `typescript` - TypeScript/JavaScript
- `rust` - Rust development
- `go` - Go programming

**Operations:**
- `devops` - DevOps practices
- `ci-cd` - Pipeline automation
- `security` - Security scanning
- `deployment` - Deployment workflows

**Domain-Specific:**
- `frontend` - UI/UX development
- `backend` - Server-side development
- `data-science` - ML/AI workflows
- `mobile` - Mobile development

#### Naming Conventions

**Skill Names:**
- Use kebab-case: `test-driven-development`, not `TestDrivenDevelopment`
- Be descriptive: `systematic-debugging`, not `debug`
- Avoid redundancy: `git-worktrees`, not `git-worktrees-skill`

**File Structure:**
```
good-skill-name/
├── skill.md          # Main skill file
├── README.md         # Optional documentation
└── examples/         # Optional code examples
    ├── example1.py
    └── example2.py
```

### Skill Deployment Strategy

#### Progressive Deployment

**Phase 1: Core Skills (Week 1)**
Deploy essential development workflows:
- `test-driven-development`
- `systematic-debugging`
- `code-review-checklist`

**Phase 2: Language Skills (Week 2)**
Add language-specific practices:
- Python: `python-style`, `scientific-packages`
- TypeScript: `frontend-development`, `web-frameworks`

**Phase 3: Toolchain Skills (Week 3)**
Include infrastructure and deployment:
- `claude-skills-engineering` (CI/CD)
- `aws-skills` or cloud platform skills
- `kubernetes-operations` if applicable

**Phase 4: Domain Skills (Week 4)**
Specialize for project domain:
- `data-scientist` for data projects
- `security-engineer` for security-critical apps
- `ux-researcher-designer` for user-facing products

#### Maintenance Strategy

**Regular Reviews:**
- **Weekly:** Check for new marketplace skills
- **Monthly:** Review active skill usage and relevance
- **Quarterly:** Update skill versions and remove unused skills

**Version Control:**
Track skill deployments in project documentation:

```markdown
# .claude/SKILLS.md

## Deployed Skills

### Development Workflow
- test-driven-development v2.1.0 (obra/superpowers)
- systematic-debugging v1.5.0 (obra/superpowers)

### Language-Specific
- python-style v1.0.0 (hoelzro/dotfiles)
- frontend-development v3.2.0 (mrgoonie/claudekit-skills)

### Operations
- aws-cdk-development v2.0.0 (zxkane/aws-skills)
- claude-skills-engineering v1.0.0 (djacobsmeyer)

## Update History
- 2025-01-15: Added aws-cdk-development for infrastructure work
- 2025-01-01: Initial skill deployment
```

### Skill Combination Patterns

#### Web Development Stack

**Frontend Application:**
```
Skills:
1. web-frameworks (Next.js/React)
2. frontend-development (TypeScript)
3. webapp-testing (Playwright)
4. better-auth (Authentication)
5. test-driven-development (TDD)

MCP Servers:
- GitHub (version control)
- Vercel (deployment)
- playwright (browser automation)
```

#### Backend API Stack

**RESTful API Service:**
```
Skills:
1. backend-engineer (API design)
2. test-driven-development (TDD)
3. systematic-debugging (debugging)
4. security-engineer (API security)
5. aws-serverless-eda (serverless)

MCP Servers:
- GitHub (version control)
- PostgreSQL (database)
- AWS services (deployment)
```

#### Data Science Stack

**ML/Data Analysis:**
```
Skills:
1. data-scientist (ML workflows)
2. scientific-packages (58 packages)
3. scientific-databases (26 databases)
4. test-driven-development (testing)
5. python-style (coding standards)

MCP Servers:
- jupyter (notebooks)
- postgresql (data storage)
- github (version control)
```

---

## Troubleshooting

### Common Issues

#### Issue: Skills Not Appearing

**Symptoms:**
- Skill deployed but not activating
- `/plugin list` doesn't show skill

**Solutions:**

1. **Verify YAML frontmatter syntax**
   ```bash
   # Check for YAML errors
   python -c "import yaml; yaml.safe_load(open('.claude/skills/my-skill/skill.md').read())"
   ```

2. **Restart Claude Code**
   ```bash
   # Skills only load at startup
   # Exit Claude Code and restart
   ```

3. **Check file naming**
   ```bash
   # Skill file must be .md
   ls -la .claude/skills/*/
   # Should see skill.md, not skill.txt
   ```

4. **Verify directory structure**
   ```bash
   # Correct structure
   .claude/skills/my-skill/skill.md

   # NOT
   .claude/skills/my-skill.md
   ```

#### Issue: Skill Conflicts

**Symptoms:**
- Multiple skills with same name
- Unexpected skill activating

**Solutions:**

1. **Check skill priority**
   - Project-local (`.claude/skills/`) overrides global (`~/.claude/skills/`)
   - Rename conflicting skills

2. **Review trigger keywords**
   ```yaml
   # Avoid overly broad triggers
   triggers:
     - test  # TOO BROAD - triggers on every "test" mention

   # Better
   triggers:
     - test-driven-development
     - tdd workflow
     - red-green-refactor
   ```

3. **Use specific categories**
   ```yaml
   # Avoid generic categories
   categories:
     - development  # Too broad

   # Better
   categories:
     - testing
     - development-workflow
     - quality-assurance
   ```

#### Issue: Skill Not Activating

**Symptoms:**
- Skill present but doesn't activate when expected

**Solutions:**

1. **Manually invoke skill**
   ```
   User: Use the test-driven-development skill
   ```

2. **Check trigger keywords**
   - Mention skill name or trigger in conversation
   - Example: "Let's use TDD for this feature"

3. **Verify skill content**
   - Ensure Tier 2 content is well-structured
   - Check for markdown errors

#### Issue: Performance Degradation

**Symptoms:**
- Slow Claude Code startup
- Sluggish responses during conversations

**Solutions:**

1. **Audit skill count**
   ```bash
   # Count deployed skills
   find ~/.claude/skills/ -name "*.md" | wc -l
   find .claude/skills/ -name "*.md" | wc -l
   ```
   - **Recommendation:** <50 skills for optimal performance

2. **Remove unused skills**
   ```bash
   # Archive instead of delete
   mkdir -p ~/.claude/skills-archive/
   mv ~/.claude/skills/unused-skill/ ~/.claude/skills-archive/
   ```

3. **Optimize skill size**
   - Keep Tier 1 metadata concise (<100 tokens)
   - Keep Tier 2 content focused (<5k tokens)
   - Split large skills into multiple smaller skills

---

## Examples

### Example 1: New Python Project Setup

**Scenario:** Starting a new FastAPI backend project with PostgreSQL.

**Skill Deployment Workflow:**

```bash
# 1. Create project structure
mkdir fastapi-project
cd fastapi-project
mkdir -p .claude/skills

# 2. Deploy foundational skills (global)
cd ~/.claude/skills/
git clone https://github.com/obra/superpowers.git
# Restart Claude Code

# 3. Install project-specific skills (marketplace)
# In Claude Code:
/plugin marketplace add zxkane/aws-skills
/plugin install aws-cdk-development@aws-skills

# 4. Create project-specific skill
# .claude/skills/api-standards/skill.md
---
name: api-standards
description: FastAPI REST API design standards for this project
categories:
  - backend
  - api-design
triggers:
  - api endpoint
  - rest api
  - fastapi
---

# API Design Standards

## Quick Reference
REST API standards for our FastAPI backend.

**When to Use:** When designing new API endpoints
**Key Principles:**
- RESTful resource naming
- Pydantic models for validation
- Async/await for database operations

## Detailed Guidelines
[Project-specific API standards...]

# 5. Deploy MCP servers
# Edit ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "postgresql": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_URL": "postgresql://localhost/mydb"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@github/mcp-server"]
    }
  }
}

# 6. Restart Claude Code to activate all skills
```

**Expected Skills Active:**
- `test-driven-development` (obra/superpowers - global)
- `systematic-debugging` (obra/superpowers - global)
- `aws-cdk-development` (zxkane/aws-skills - marketplace)
- `api-standards` (project-local)
- Backend-related skills from global collection

### Example 2: Enhancing Existing TypeScript Project

**Scenario:** Adding Playwright testing to an existing Next.js project.

**Skill Deployment Workflow:**

```bash
# 1. Analyze current project
cd /path/to/nextjs-project

# 2. Check existing skills
ls -la .claude/skills/
# Currently: web-frameworks, frontend-development

# 3. Add testing skills
/plugin marketplace add anthropics/skills
/plugin install webapp-testing@anthropic-agent-skills

# 4. Install Playwright MCP server
# Edit claude_desktop_config.json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"]
    }
  }
}

# 5. Add project-specific testing conventions
# .claude/skills/testing-standards/skill.md
---
name: testing-standards
description: E2E testing conventions for Next.js app
categories:
  - testing
  - quality
triggers:
  - write test
  - e2e test
  - playwright
---

# Testing Standards

## Quick Reference
E2E testing with Playwright for our Next.js application.

**Test Organization:**
- `tests/e2e/` - End-to-end tests
- `tests/integration/` - API integration tests
- `tests/unit/` - Component unit tests

**Naming Convention:**
- `*.test.ts` - Unit tests
- `*.spec.ts` - E2E tests

## Detailed Guidelines
[Project-specific testing requirements...]

# 6. Restart Claude Code
```

**Expected Skills Active:**
- `web-frameworks` (existing project-local)
- `frontend-development` (existing project-local)
- `webapp-testing` (newly added from marketplace)
- `testing-standards` (newly added project-local)
- `test-driven-development` (global, if deployed)

### Example 3: Research Agent Proactive Recommendation

**Scenario:** Research agent analyzing a project detects missing skills.

**Research Agent Analysis:**

```python
# Research agent detection logic
def analyze_project_skills(project_path: str) -> dict:
    """Analyze project and recommend skills."""

    # 1. Detect technology stack
    tech_stack = detect_technologies(project_path)
    # Found: Python 3.11, FastAPI, PostgreSQL, Docker, GitHub Actions

    # 2. Check deployed skills
    deployed_skills = list_deployed_skills(project_path)
    # Found: python-style, systematic-debugging

    # 3. Identify gaps
    skill_gaps = []

    if "fastapi" in tech_stack and "backend-engineer" not in deployed_skills:
        skill_gaps.append({
            "skill": "backend-engineer",
            "reason": "FastAPI detected but no backend API skill",
            "source": "alirezarezvani/claude-skills",
            "priority": "high"
        })

    if "pytest" in tech_stack and "test-driven-development" not in deployed_skills:
        skill_gaps.append({
            "skill": "test-driven-development",
            "reason": "Pytest detected but no TDD skill",
            "source": "obra/superpowers",
            "priority": "high"
        })

    if "docker" in tech_stack and "docker-workflow" not in deployed_skills:
        skill_gaps.append({
            "skill": "docker-workflow",
            "reason": "Docker usage but no Docker skill",
            "source": "djacobsmeyer/claude-skills-engineering",
            "priority": "medium"
        })

    if ".github/workflows" in tech_stack and "ci-cd-pipeline" not in deployed_skills:
        skill_gaps.append({
            "skill": "ci-cd-pipeline-builder",
            "reason": "GitHub Actions detected but no CI/CD skill",
            "source": "djacobsmeyer/claude-skills-engineering",
            "priority": "medium"
        })

    return {
        "tech_stack": tech_stack,
        "deployed_skills": deployed_skills,
        "skill_gaps": skill_gaps,
        "recommendations": generate_recommendations(skill_gaps)
    }

def generate_recommendations(skill_gaps: list) -> str:
    """Generate user-facing recommendations."""

    recs = []
    recs.append("## Recommended Skill Deployments\n")
    recs.append("Based on project analysis, consider deploying:\n")

    # High priority
    high = [s for s in skill_gaps if s["priority"] == "high"]
    if high:
        recs.append("\n### High Priority\n")
        for skill in high:
            recs.append(f"- **{skill['skill']}** ({skill['source']})")
            recs.append(f"  - Reason: {skill['reason']}\n")

    # Medium priority
    medium = [s for s in skill_gaps if s["priority"] == "medium"]
    if medium:
        recs.append("\n### Medium Priority\n")
        for skill in medium:
            recs.append(f"- **{skill['skill']}** ({skill['source']})")
            recs.append(f"  - Reason: {skill['reason']}\n")

    # Installation commands
    recs.append("\n### Installation\n")
    recs.append("```bash\n")
    for skill in skill_gaps:
        recs.append(f"/plugin marketplace add {skill['source']}\n")
        recs.append(f"/plugin install {skill['skill']}@{skill['source']}\n")
    recs.append("```\n")

    return "".join(recs)
```

**Research Agent Output:**

```markdown
## Project Analysis Complete

### Technology Stack Detected
- Python 3.11
- FastAPI 0.109.0
- PostgreSQL 15
- Docker & Docker Compose
- GitHub Actions CI/CD
- pytest 8.0.0

### Currently Deployed Skills
- python-style (hoelzro/dotfiles)
- systematic-debugging (obra/superpowers)

## Recommended Skill Deployments

Based on project analysis, consider deploying:

### High Priority

- **backend-engineer** (alirezarezvani/claude-skills)
  - Reason: FastAPI detected but no backend API skill
  - Benefits: API design patterns, request validation, error handling

- **test-driven-development** (obra/superpowers)
  - Reason: Pytest detected but no TDD skill
  - Benefits: RED-GREEN-REFACTOR workflow, test-first development

### Medium Priority

- **docker-workflow** (djacobsmeyer/claude-skills-engineering)
  - Reason: Docker usage but no Docker skill
  - Benefits: Container best practices, docker-compose patterns

- **ci-cd-pipeline-builder** (djacobsmeyer/claude-skills-engineering)
  - Reason: GitHub Actions detected but no CI/CD skill
  - Benefits: Pipeline optimization, GitHub Actions best practices

### Installation

```bash
/plugin marketplace add obra/superpowers
/plugin install test-driven-development@superpowers

/plugin marketplace add alirezarezvani/claude-skills
/plugin install backend-engineer@alirezarezvani-claude-skills

/plugin marketplace add djacobsmeyer/claude-skills-engineering
/plugin install docker-workflow@djacobsmeyer-claude-skills-engineering
/plugin install ci-cd-pipeline-builder@djacobsmeyer-claude-skills-engineering
```

**Note:** Restart Claude Code after installation to activate new skills.
```

---

## Research Agent Integration

### When to Recommend Skills

Research agents should proactively recommend skills in these scenarios:

#### 1. Project Initialization Analysis

**Trigger:** First-time project analysis or new project setup

**Actions:**
- Detect primary programming language
- Identify framework and toolchain
- Recommend foundational skill stack
- Suggest project-specific skill creation

**Example Output:**
```
Analyzing new Python FastAPI project...

Recommended foundational skills:
1. test-driven-development (development workflow)
2. python-style (language standards)
3. backend-engineer (API design)
4. systematic-debugging (troubleshooting)

Installation: /plugin marketplace add obra/superpowers
```

#### 2. Technology Stack Changes

**Trigger:** New technology detected (new dependencies, new files)

**Actions:**
- Compare current tech stack to last analysis
- Identify newly introduced technologies
- Recommend technology-specific skills
- Suggest MCP server integrations

**Example Output:**
```
New technology detected: Docker

Current skills: python-style, test-driven-development
Recommended addition: docker-workflow (djacobsmeyer/claude-skills-engineering)

This skill provides:
- Dockerfile best practices
- docker-compose patterns
- Container optimization
```

#### 3. Work Type Detection

**Trigger:** User starts specific type of work (testing, debugging, deployment)

**Actions:**
- Identify work type from user request
- Check if relevant skill is deployed
- Recommend skill if missing
- Offer to activate skill for session

**Example Output:**
```
User requested: "Help me write comprehensive tests"

Detected work type: Testing/QA

Available skills:
✓ python-style (deployed)
✗ test-driven-development (not deployed)
✗ webapp-testing (not deployed)

Recommendation: Deploy test-driven-development skill for TDD workflow
Installation: /plugin marketplace add obra/superpowers
```

#### 4. Quality Issues Detected

**Trigger:** Code review, linting issues, test failures

**Actions:**
- Analyze type of quality issue
- Recommend preventive skills
- Suggest code review skills
- Offer debugging skills

**Example Output:**
```
Analysis: Multiple test failures detected

Root cause: Tests written after implementation (not test-first)

Recommendation: Deploy test-driven-development skill
Benefit: Enforces RED-GREEN-REFACTOR cycle to prevent this issue

Installation: /plugin marketplace add obra/superpowers
```

#### 5. Performance Bottlenecks

**Trigger:** Performance issues, slow queries, inefficient code

**Actions:**
- Identify performance domain
- Recommend optimization skills
- Suggest profiling skills
- Offer architecture skills

**Example Output:**
```
Performance issue: Slow database queries detected

Current skills: backend-engineer
Recommended addition: data-scientist (for query optimization)

Alternative: PostgreSQL MCP server for direct database analysis
```

### Skill Recommendation Decision Tree

```
User Request Received
    ↓
[Analyze Request Type]
    ↓
    ├─ New Project Setup
    │   └─> Recommend: Foundational skills (TDD, debugging, language-specific)
    │
    ├─ Specific Technology Work
    │   └─> Check: Is technology-specific skill deployed?
    │       ├─ Yes → Use existing skill
    │       └─ No → Recommend deployment
    │
    ├─ Quality/Testing Work
    │   └─> Recommend: test-driven-development, systematic-debugging
    │
    ├─ Infrastructure/Deployment
    │   └─> Recommend: CI/CD skills, cloud platform skills
    │
    ├─ Code Review/Refactoring
    │   └─> Recommend: code-review-checklist, refactoring skills
    │
    └─ Debugging/Troubleshooting
        └─> Recommend: systematic-debugging, root-cause-tracing
```

### Proactive Detection Patterns

**Pattern 1: Missing TDD Skill**

```python
def detect_tdd_skill_need(context: dict) -> bool:
    """Detect if TDD skill would be beneficial."""

    indicators = [
        "pytest" in context.dependencies,
        "tests/" in context.directories,
        "test_" in context.recent_files,
        "write test" in context.user_request.lower(),
        "testing" in context.user_request.lower()
    ]

    # If testing indicators present but TDD skill not deployed
    return (
        any(indicators) and
        "test-driven-development" not in context.deployed_skills
    )
```

**Pattern 2: Missing Backend Skill**

```python
def detect_backend_skill_need(context: dict) -> bool:
    """Detect if backend API skill would be beneficial."""

    api_frameworks = ["fastapi", "flask", "django", "express", "gin"]

    has_api_framework = any(
        fw in context.dependencies for fw in api_frameworks
    )

    return (
        has_api_framework and
        "backend-engineer" not in context.deployed_skills
    )
```

**Pattern 3: Missing CI/CD Skill**

```python
def detect_cicd_skill_need(context: dict) -> bool:
    """Detect if CI/CD skill would be beneficial."""

    cicd_indicators = [
        ".github/workflows/" in context.directories,
        ".gitlab-ci.yml" in context.files,
        "Jenkinsfile" in context.files,
        "circle.yml" in context.files
    ]

    return (
        any(cicd_indicators) and
        "ci-cd-pipeline" not in context.deployed_skills
    )
```

### Integration with Research Workflow

**Step 1: Initial Project Scan**

```python
def research_agent_project_scan(project_path: str) -> dict:
    """Initial project scan with skill recommendations."""

    # Standard research analysis
    tech_stack = analyze_technology_stack(project_path)
    architecture = map_architecture(project_path)
    dependencies = analyze_dependencies(project_path)

    # Skill gap analysis
    deployed_skills = list_deployed_skills(project_path)
    recommended_skills = recommend_skills_for_stack(
        tech_stack,
        deployed_skills
    )

    return {
        "tech_stack": tech_stack,
        "architecture": architecture,
        "dependencies": dependencies,
        "deployed_skills": deployed_skills,
        "recommended_skills": recommended_skills,
        "skill_deployment_commands": generate_install_commands(
            recommended_skills
        )
    }
```

**Step 2: Ongoing Monitoring**

```python
def monitor_skill_opportunities(session_context: dict) -> list:
    """Monitor conversation for skill deployment opportunities."""

    opportunities = []

    # Check user requests
    for request in session_context.recent_requests:
        if "write tests" in request and "tdd" not in deployed_skills:
            opportunities.append({
                "skill": "test-driven-development",
                "trigger": request,
                "confidence": "high"
            })

        if "deploy" in request and "ci-cd" not in deployed_skills:
            opportunities.append({
                "skill": "ci-cd-pipeline-builder",
                "trigger": request,
                "confidence": "medium"
            })

    return opportunities
```

**Step 3: Recommendation Delivery**

```python
def deliver_skill_recommendation(
    opportunity: dict,
    user_context: dict
) -> str:
    """Format and deliver skill recommendation to user."""

    skill = opportunity["skill"]
    skill_info = fetch_skill_metadata(skill)

    message = f"""
## Skill Recommendation

I noticed you're working on {opportunity['trigger']}.

Consider deploying the **{skill}** skill for enhanced guidance:

**Benefits:**
{format_benefits(skill_info.benefits)}

**Installation:**
```bash
/plugin marketplace add {skill_info.source}
/plugin install {skill}@{skill_info.source}
```

**Alternative:** I can proceed without this skill, but having it would provide:
- Structured workflow enforcement
- Best practices guidance
- Reduced error likelihood

Would you like to deploy this skill before continuing?
"""

    return message
```

### Research Agent Skill Report Format

When research agents complete project analysis, include skill recommendations in final report:

```markdown
# Project Analysis Report

## Executive Summary
[Standard project analysis summary...]

## Technology Stack
- Python 3.11
- FastAPI 0.109.0
- PostgreSQL 15
- Docker

## Architecture
[Architecture analysis...]

## Skill Deployment Analysis

### Currently Deployed Skills ✅
- python-style (hoelzro/dotfiles) - Python coding standards
- systematic-debugging (obra/superpowers) - Debugging methodology

### Recommended Skills 📚

#### High Priority
1. **test-driven-development** (obra/superpowers)
   - Why: pytest detected but no TDD workflow skill
   - Impact: Enforces test-first development, reduces bugs
   - Install: `/plugin marketplace add obra/superpowers`

2. **backend-engineer** (alirezarezvani/claude-skills)
   - Why: FastAPI backend but no API design skill
   - Impact: API design patterns, validation, error handling
   - Install: `/plugin marketplace add alirezarezvani/claude-skills`

#### Medium Priority
3. **docker-workflow** (djacobsmeyer/claude-skills-engineering)
   - Why: Docker usage detected
   - Impact: Container best practices, optimization

4. **aws-cdk-development** (zxkane/aws-skills)
   - Why: Deployment to AWS inferred from dependencies
   - Impact: Infrastructure as code best practices

### Skill Deployment Commands

```bash
# Install high priority skills
/plugin marketplace add obra/superpowers
/plugin install test-driven-development@superpowers

/plugin marketplace add alirezarezvani/claude-skills
/plugin install backend-engineer@alirezarezvani-claude-skills

# Install medium priority skills
/plugin marketplace add djacobsmeyer/claude-skills-engineering
/plugin install docker-workflow@djacobsmeyer-claude-skills-engineering

# Restart Claude Code to activate
```

## Recommendations
[Standard recommendations...]
```

---

## Top 10 Skill Deployment Recommendations

### 1. **Always Check for TDD Skills First**

**Why:** Test-driven development is the foundation of quality code across all languages and frameworks.

**When:** Every new project, especially if `tests/` directory or testing framework detected.

**Action:**
```bash
/plugin marketplace add obra/superpowers
/plugin install test-driven-development@superpowers
```

### 2. **Match Language-Specific Skills to Tech Stack**

**Why:** Language-specific best practices prevent common pitfalls and enforce idioms.

**Detection Map:**
- Python → `python-style`
- TypeScript/JavaScript → `frontend-development`, `web-frameworks`
- Rust → `pragmatic-rust-guidelines`
- Go → `effective-go-development`

### 3. **Deploy Debugging Skills Early**

**Why:** Systematic debugging prevents ad-hoc troubleshooting and saves time.

**When:** First sign of bugs or complex system behavior.

**Action:**
```bash
/plugin marketplace add obra/superpowers
/plugin install systematic-debugging@superpowers
```

### 4. **Recommend CI/CD Skills for GitHub Actions**

**Why:** Most projects have `.github/workflows/` but lack CI/CD expertise skills.

**Detection:** `.github/workflows/*.yml` files present

**Action:**
```bash
/plugin marketplace add djacobsmeyer/claude-skills-engineering
/plugin install ci-cd-pipeline-builder@djacobsmeyer-claude-skills-engineering
```

### 5. **Suggest Security Skills for Production Apps**

**Why:** Security scanning skills catch vulnerabilities early.

**When:** Production-grade applications, API backends, authentication systems.

**Action:**
```bash
/plugin marketplace add alirezarezvani/claude-skills
/plugin install security-engineer@alirezarezvani-claude-skills
```

### 6. **Batch Deploy Skills to Minimize Restarts**

**Why:** Skills only load at startup - multiple restarts are inefficient.

**Best Practice:** Analyze full tech stack, recommend all relevant skills at once, single restart.

**Example:**
```bash
# Single batch deployment
/plugin marketplace add obra/superpowers
/plugin marketplace add alirezarezvani/claude-skills
/plugin marketplace add djacobsmeyer/claude-skills-engineering

/plugin install test-driven-development@superpowers
/plugin install backend-engineer@alirezarezvani-claude-skills
/plugin install ci-cd-pipeline-builder@djacobsmeyer-claude-skills-engineering

# One restart activates all
```

### 7. **Prioritize Official Anthropic Skills**

**Why:** Production-grade quality, actively maintained, comprehensive documentation.

**Top Official Skills:**
- `webapp-testing` - Playwright E2E testing
- `mcp-server` - MCP server creation guide
- `skill-creator` - Interactive skill builder

**Action:**
```bash
/plugin marketplace add anthropics/skills
```

### 8. **Recommend Project-Specific Skill Creation**

**Why:** Unique project conventions benefit from dedicated skills.

**When:**
- Team coding standards differ from general best practices
- Domain-specific patterns emerge
- Custom workflows established

**Template:**
```markdown
---
name: project-api-standards
description: Team API design conventions
categories:
  - api-design
  - project-specific
---

# Project API Standards
[Team-specific guidelines...]
```

### 9. **Suggest Complementary MCP Servers**

**Why:** Skills provide expertise; MCP servers provide tool integration.

**Best Combinations:**

| Skill | Complementary MCP Server |
|-------|--------------------------|
| `backend-engineer` | PostgreSQL, Redis |
| `test-driven-development` | Playwright |
| `aws-cdk-development` | AWS services MCP |
| `frontend-development` | Browser MCP |
| `security-engineer` | Snyk, GitGuardian |

### 10. **Monitor Skill Usage and Prune Unused Skills**

**Why:** Too many skills degrade performance; inactive skills waste memory.

**Best Practice:**
- Track skill activation frequency
- Archive skills unused for >30 days
- Keep skill count <50 for optimal performance

**Monitoring:**
```python
def audit_skill_usage(session_logs: list) -> dict:
    """Analyze which skills are actually being used."""

    skill_usage = defaultdict(int)

    for log in session_logs:
        if "skill_activated" in log:
            skill_usage[log["skill_name"]] += 1

    unused_skills = [
        skill for skill in deployed_skills
        if skill_usage[skill] == 0
    ]

    return {
        "usage_counts": skill_usage,
        "unused_skills": unused_skills,
        "recommendation": f"Archive {len(unused_skills)} unused skills"
    }
```

---

## Conclusion

Effective skill deployment is critical for maximizing Claude Code capabilities. Research agents play a vital role in:

1. **Detecting skill gaps** during project analysis
2. **Recommending relevant skills** based on technology stack
3. **Prioritizing deployments** for maximum impact
4. **Educating users** on skill benefits and usage

By following this guide, research agents can proactively enhance Claude Code capabilities and deliver better outcomes for users.

---

## Additional Resources

### Official Documentation
- [Anthropic Skills Documentation](https://docs.anthropic.com/claude/docs/skills)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Claude Code User Guide](https://docs.anthropic.com/claude-code)

### Skill Repositories
- [anthropics/skills](https://github.com/anthropics/skills) - Official skills
- [obra/superpowers](https://github.com/obra/superpowers) - Battle-tested workflows
- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) - Comprehensive list

### Community
- [Skills Marketplace](https://skillsmp.com) - 13,000+ indexed skills
- [MCP Registry](https://registry.modelcontextprotocol.io) - Browse MCP servers

---

**Last Updated:** 2025-01-21
**Version:** 1.0.0
**Maintained by:** Claude MPM Research Agent
