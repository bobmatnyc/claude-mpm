# Skills Deployment Quick Reference

Quick reference card for Claude MPM's skills deployment system.

## Common Commands

| Command | Description | Example |
|---------|-------------|---------|
| `claude-mpm skills deploy-github --toolchain <name>` | Deploy skills for specific toolchain | `--toolchain python` |
| `claude-mpm skills deploy-github --categories <cats>` | Deploy skills by categories | `--categories testing,devops` |
| `claude-mpm skills deploy-github --collection <name>` | Deploy from specific collection | `--collection obra-superpowers` |
| `claude-mpm skills list-available` | Browse all available skills | Lists all skills from repository |
| `claude-mpm skills list-available --toolchain <name>` | Filter by toolchain | `--toolchain typescript` |
| `claude-mpm skills check-deployed` | View currently deployed skills | Shows what's in `~/.claude/skills/` |
| `claude-mpm skills remove --all` | Remove all deployed skills | Clears skills directory |
| `claude-mpm skills remove --name <skill>` | Remove specific skill | `--name test-driven-development` |

## Collection Management Commands

| Command | Description | Example |
|---------|-------------|---------|
| `claude-mpm skills collection-list` | List all configured collections | Shows enabled/disabled, priority, last update |
| `claude-mpm skills collection-add NAME URL` | Add new collection | `collection-add obra-superpowers https://github.com/obra/superpowers` |
| `claude-mpm skills collection-add NAME URL --priority N` | Add with custom priority | `--priority 2` (lower = higher priority) |
| `claude-mpm skills collection-remove NAME` | Remove collection | Removes config and deployed skills |
| `claude-mpm skills collection-enable NAME` | Enable disabled collection | Re-activates collection for deployment |
| `claude-mpm skills collection-disable NAME` | Disable collection temporarily | Keeps config but skips in deployment |
| `claude-mpm skills collection-set-default NAME` | Set default collection | Used when no --collection specified |

## Toolchain Options

Available toolchain filters:

- `python` - Python development skills
- `typescript` - TypeScript/JavaScript skills
- `javascript` - Vanilla JavaScript skills
- `rust` - Rust development skills
- `go` - Go development skills
- `devops` - Infrastructure and CI/CD skills
- `testing` - Testing framework skills
- `frontend` - Frontend development skills
- `backend` - Backend API development skills

## Technology → Skills Mapping

Quick reference for what skills to deploy based on your technology stack:

### Python Projects

| Your Tech Stack | Recommended Skills | Priority |
|----------------|-------------------|----------|
| Python + pytest | test-driven-development | High |
| Python general | python-style | High |
| FastAPI/Flask/Django | backend-engineer | High |
| Data science (pandas, numpy) | data-scientist, scientific-packages | Medium |
| AWS infrastructure | aws-cdk-development, aws-serverless-eda | Medium |

**Deploy command:**
```bash
claude-mpm skills deploy-github --toolchain python
```

### TypeScript/JavaScript Projects

| Your Tech Stack | Recommended Skills | Priority |
|----------------|-------------------|----------|
| React | frontend-development | High |
| Next.js | web-frameworks | High |
| Playwright testing | webapp-testing | High |
| Node.js backend | backend-engineer | Medium |
| Authentication | better-auth | Medium |

**Deploy command:**
```bash
claude-mpm skills deploy-github --toolchain typescript
```

### Rust Projects

| Your Tech Stack | Recommended Skills | Priority |
|----------------|-------------------|----------|
| Rust general | pragmatic-rust-guidelines | High |
| Async Rust | claude-flow-rust | Medium |
| Systems programming | backend-engineer | Medium |

**Deploy command:**
```bash
claude-mpm skills deploy-github --toolchain rust
```

### Go Projects

| Your Tech Stack | Recommended Skills | Priority |
|----------------|-------------------|----------|
| Go general | effective-go-development | High |
| Concurrency | claude-flow-go | Medium |
| Backend APIs | backend-engineer | High |

**Deploy command:**
```bash
claude-mpm skills deploy-github --toolchain go
```

### DevOps/Infrastructure

| Your Tech Stack | Recommended Skills | Priority |
|----------------|-------------------|----------|
| GitHub Actions | ci-cd-pipeline-builder | High |
| Docker | docker-workflow | High |
| AWS CDK | aws-cdk-development | Medium |
| Terraform | devops-claude-skills | Medium |
| Kubernetes | kubernetes-operations | Medium |

**Deploy command:**
```bash
claude-mpm skills deploy-github --categories devops,ci-cd
```

## Category Filters

Available category filters for targeted deployment:

| Category | What It Includes |
|----------|-----------------|
| `testing` | TDD, test automation, quality assurance |
| `devops` | Infrastructure, deployment, operations |
| `ci-cd` | Pipeline automation, GitHub Actions, GitLab CI |
| `frontend` | React, Next.js, UI/UX development |
| `backend` | API design, server development |
| `security` | Security scanning, vulnerability detection |
| `debugging` | Systematic debugging, troubleshooting |
| `development-workflow` | General development practices |
| `language-specific` | Python, TypeScript, Rust, Go specifics |

## Workflow Examples

### Example 1: New Python Project Setup

**Scenario:** Starting a new FastAPI project with pytest

```bash
# Deploy Python toolchain skills
claude-mpm skills deploy-github --toolchain python

# What gets deployed:
# - test-driven-development (TDD workflow)
# - python-style (PEP 8, best practices)
# - backend-engineer (API design)
# - systematic-debugging (debugging)

# Restart Claude Code to activate
```

### Example 2: Adding Testing to Existing Project

**Scenario:** Project has no testing skills deployed

```bash
# Deploy only testing skills
claude-mpm skills deploy-github --categories testing

# What gets deployed:
# - test-driven-development
# - webapp-testing (if Playwright detected)
# - systematic-debugging

# Restart Claude Code to activate
```

### Example 3: Full Stack Web Application

**Scenario:** Next.js frontend + Python backend

```bash
# Deploy frontend skills
claude-mpm skills deploy-github --toolchain typescript

# Deploy backend skills
claude-mpm skills deploy-github --toolchain python

# Deploy DevOps skills
claude-mpm skills deploy-github --categories devops

# Single restart activates all skills
```

### Example 4: Checking and Removing Skills

```bash
# See what's currently deployed
claude-mpm skills check-deployed

# Remove specific skill
claude-mpm skills remove --name webapp-testing

# Remove all skills and start fresh
claude-mpm skills remove --all

# Restart Claude Code for changes to take effect
```

## Important Notes

### Restart Requirements

Skills are loaded at Claude Code STARTUP ONLY:

| Action | Restart Required? |
|--------|------------------|
| Deploy new skills | YES |
| Remove skills | YES |
| Modify skill YAML frontmatter | YES |
| Modify skill content (instructions) | NO (takes effect on next activation) |
| Add MCP servers | Varies by server |

**Best Practice:** Batch deploy all needed skills before restarting Claude Code.

### Performance Considerations

| Skill Count | Performance Impact |
|-------------|-------------------|
| 1-20 skills | Minimal impact, optimal |
| 21-50 skills | Slight startup delay |
| 51-100 skills | Noticeable startup delay |
| 100+ skills | Performance degradation |

**Recommendation:** Keep total skills <50 for best performance

### Skill Priority

When deploying multiple skills, prioritize:

1. **High Priority (Deploy First)**
   - test-driven-development (if you write tests)
   - Language-specific skills (python-style, etc.)
   - Framework skills (backend-engineer for APIs)

2. **Medium Priority (Deploy Second)**
   - DevOps/infrastructure skills
   - Testing automation skills
   - Debugging skills

3. **Low Priority (Deploy Last)**
   - Specialized domain skills
   - Experimental/beta skills
   - Nice-to-have workflow enhancements

## Troubleshooting

### Skills Not Appearing

**Problem:** Deployed skills don't show up in Claude Code

**Solution:**
```bash
# 1. Verify deployment
claude-mpm skills check-deployed

# 2. Restart Claude Code COMPLETELY
# macOS: Cmd+Q (not just close window)
# Windows: Alt+F4 or Exit from tray
# Linux: Quit application completely

# 3. Check Claude Code version
claude --version
# Need v1.0.92+ for skills support

# 4. Verify skill files exist
ls -la ~/.claude/skills/
```

### Skills Not Activating

**Problem:** Skills are deployed but don't activate during use

**Solution:**
1. Manually invoke skill: "Use the test-driven-development skill"
2. Check trigger keywords in skill YAML frontmatter
3. Verify skill file has proper YAML frontmatter structure
4. Check Claude Code console for skill loading errors

### Deployment Failures

**Problem:** `claude-mpm skills deploy-github` fails

**Solution:**
```bash
# Check internet connection
ping github.com

# Verify GitHub repository access
curl -I https://github.com/bobmatnyc/claude-mpm-skills

# Check permissions on skills directory
ls -la ~/.claude/
mkdir -p ~/.claude/skills/  # Create if missing

# Try verbose output for debugging
claude-mpm skills deploy-github --toolchain python -v
```

### Too Many Skills

**Problem:** Claude Code slow to start or sluggish

**Solution:**
```bash
# Audit current skills
claude-mpm skills check-deployed

# Remove unused skills
claude-mpm skills remove --name <unused-skill>

# Or start fresh with only essential skills
claude-mpm skills remove --all
claude-mpm skills deploy-github --categories testing,development-workflow

# Keep count <50 for optimal performance
```

## Research Agent Integration

The Research Agent automatically recommends skills during project analysis:

### When Recommendations Appear

1. **Project Initialization** - First-time analysis of new project
2. **Technology Changes** - New dependencies or frameworks added
3. **Work Type Detection** - Starting testing, debugging, deployment work
4. **Quality Issues** - Code review, test failures, style violations

### Sample Research Agent Output

```markdown
## Technology Stack Detected
- Python 3.11
- FastAPI 0.109.0
- pytest 8.0.0
- Docker

## Skill Gap Analysis

Currently Deployed: None

Recommended Skills:
1. test-driven-development (HIGH) - TDD workflow
2. backend-engineer (HIGH) - API design patterns
3. docker-workflow (MEDIUM) - Container practices

Deploy with:
claude-mpm skills deploy-github --toolchain python
```

### Following Recommendations

```bash
# Option 1: Deploy exact recommendations
claude-mpm skills deploy-github --toolchain python

# Option 2: Deploy specific skills only
claude-mpm skills deploy-github --categories testing

# Option 3: Review available skills first
claude-mpm skills list-available --toolchain python
# Then deploy selected skills
```

## Collection Deployment Examples

### Add and Deploy from New Collection

```bash
# Add obra's superpowers
claude-mpm skills collection-add obra-superpowers https://github.com/obra/superpowers

# Deploy testing skills from superpowers
claude-mpm skills deploy-github --collection obra-superpowers --categories testing

# Set as default
claude-mpm skills collection-set-default obra-superpowers
```

### Manage Multiple Collections

```bash
# List all collections
claude-mpm skills collection-list

# Deploy from each
claude-mpm skills deploy-github --collection claude-mpm --toolchain python
claude-mpm skills deploy-github --collection obra-superpowers --categories testing

# Disable one temporarily
claude-mpm skills collection-disable claude-mpm

# List available from all enabled
claude-mpm skills list-available
```

### Priority and Conflict Resolution

```bash
# Add collections with specific priorities (lower = higher)
claude-mpm skills collection-add official https://github.com/company/official-skills --priority 1
claude-mpm skills collection-add community https://github.com/obra/superpowers --priority 2
claude-mpm skills collection-add experimental https://github.com/dev/experimental --priority 3

# If duplicate skill names exist, priority 1 wins
```

### Git-Based Updates

Collections use git for version control:

```bash
# First deployment clones repository
claude-mpm skills deploy-github --collection obra-superpowers
# → git clone https://github.com/obra/superpowers ~/.claude/skills/obra-superpowers/

# Subsequent deployments update via git pull
claude-mpm skills deploy-github --collection obra-superpowers
# → cd ~/.claude/skills/obra-superpowers && git pull

# Inspect changes
cd ~/.claude/skills/obra-superpowers
git log --oneline -n 10

# Rollback if needed
git checkout <previous-commit>
```

---

## Advanced Usage

### Combining Multiple Filters

```bash
# Deploy Python testing skills only
claude-mpm skills deploy-github --toolchain python --categories testing

# Deploy all DevOps and CI/CD skills
claude-mpm skills deploy-github --categories devops,ci-cd

# Deploy backend skills across multiple languages
claude-mpm skills deploy-github --categories backend
```

### Scripted Deployment

```bash
#!/bin/bash
# deploy-project-skills.sh

# Deploy foundational skills
echo "Deploying foundational skills..."
claude-mpm skills deploy-github --categories testing,development-workflow

# Deploy language-specific skills
echo "Deploying Python skills..."
claude-mpm skills deploy-github --toolchain python

# Deploy DevOps skills
echo "Deploying DevOps skills..."
claude-mpm skills deploy-github --categories devops

echo "Skills deployed! Restart Claude Code to activate."
```

### Version Tracking

Create a `.claude/SKILLS.md` file to track deployed skills:

```markdown
# Deployed Skills

## Last Updated: 2025-01-21

### Development Workflow
- test-driven-development v2.1.0 (obra/superpowers)
- systematic-debugging v1.5.0 (obra/superpowers)

### Language-Specific
- python-style v1.0.0 (hoelzro/dotfiles)
- backend-engineer v3.0.0 (alirezarezvani/claude-skills)

### Operations
- docker-workflow v2.0.0 (djacobsmeyer/claude-skills-engineering)
- ci-cd-pipeline-builder v1.5.0 (djacobsmeyer/claude-skills-engineering)

## Deployment History
- 2025-01-21: Initial skill deployment
- 2025-01-15: Added docker-workflow for containerization
```

## Related Documentation

- **[Skills Deployment Guide](../guides/skills-deployment-guide.md)** - Comprehensive deployment guide
- **[Research Agent Documentation](../agents/research-agent.md)** - Research agent skill detection
- **[claude-mpm-skills Repository](https://github.com/bobmatnyc/claude-mpm-skills)** - Skills source repository

## Quick Decision Tree

```
Need skills for your project?
│
├─ New project?
│  └─> Deploy toolchain skills: `claude-mpm skills deploy-github --toolchain <language>`
│
├─ Adding testing?
│  └─> Deploy testing skills: `claude-mpm skills deploy-github --categories testing`
│
├─ Setting up CI/CD?
│  └─> Deploy DevOps skills: `claude-mpm skills deploy-github --categories devops,ci-cd`
│
├─ Full stack project?
│  ├─> Deploy frontend: `--toolchain typescript`
│  ├─> Deploy backend: `--toolchain python` (or your backend language)
│  └─> Deploy DevOps: `--categories devops`
│
└─ Not sure what you need?
   └─> Let Research Agent analyze: Run `claude-mpm` and let agent recommend
```

## Version Information

**Last Updated:** 2025-01-21
**Compatible with:**
- Claude MPM v4.25.0+
- Claude Code v1.0.92+
- claude-mpm-skills repository (latest)

**Changelog:**
- 2025-01-21: Initial quick reference creation
- Added research agent integration examples
- Added troubleshooting section
- Added technology mapping tables
