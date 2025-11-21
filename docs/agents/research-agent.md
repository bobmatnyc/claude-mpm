# Research Agent

## Overview

The Research Agent is a specialized AI agent designed to analyze projects, understand codebases, and provide actionable insights for development workflows. Enhanced with **skill gap detection** and **intelligent recommendations**, it automatically identifies missing Claude Code skills based on your project's technology stack.

**Version:** 2.6.0
**Specialization:** Project analysis, technology stack detection, skill recommendations, codebase understanding
**Key Capabilities:**
- Technology stack detection from configuration files
- Skill gap analysis and recommendations
- Project architecture mapping
- Dependency analysis
- Proactive workflow optimization

## Core Capabilities

### Traditional Research Capabilities

1. **Codebase Analysis**
   - Project structure understanding
   - Dependency mapping
   - Code pattern identification
   - Architecture documentation review

2. **Technology Stack Detection**
   - Programming language identification
   - Framework detection (web, testing, infrastructure)
   - Development tool discovery
   - Library and package analysis

3. **Documentation Discovery**
   - README and documentation scanning
   - API documentation identification
   - Configuration file analysis
   - Project convention extraction

4. **Quality Assessment**
   - Test coverage evaluation
   - Code organization review
   - Best practice alignment
   - Technical debt identification

## Skill Gap Detection (NEW)

The Research Agent has been enhanced with **automatic skill gap detection** and **proactive skill recommendations** based on your project's technology stack.

### Technology Stack Detection

The agent automatically detects your project's technology stack by scanning:

**Configuration Files:**
- `package.json`, `tsconfig.json` - TypeScript/JavaScript projects
- `pyproject.toml`, `setup.py`, `requirements.txt` - Python projects
- `Cargo.toml`, `Cargo.lock` - Rust projects
- `go.mod`, `go.sum` - Go projects
- `pom.xml`, `build.gradle` - Java projects

**Framework Markers:**
- **Web Frameworks:** FastAPI, Flask, Django, Express, Next.js, React
- **Testing Frameworks:** pytest, Jest, Vitest, Playwright, Cypress
- **Build Tools:** Vite, webpack, esbuild, Rollup
- **Package Managers:** npm, yarn, pnpm, pip, cargo, go modules

**Infrastructure Patterns:**
- **Containerization:** `Dockerfile`, `docker-compose.yml`
- **CI/CD:** `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`
- **Cloud Platforms:** AWS CDK, Terraform, Pulumi configurations
- **Kubernetes:** K8s manifests, Helm charts

### Skill Recommendations

Based on detected technologies, the agent recommends relevant Claude Code skills from the [claude-mpm-skills repository](https://github.com/bobmatnyc/claude-mpm-skills):

**Example Technology → Skill Mappings:**

| Detected Technology | Recommended Skill | Source |
|---------------------|-------------------|--------|
| Python + pytest | test-driven-development | obra/superpowers |
| FastAPI/Flask | backend-engineer | alirezarezvani/claude-skills |
| React/Next.js | frontend-development, web-frameworks | mrgoonie/claudekit-skills |
| Docker | docker-workflow | djacobsmeyer/claude-skills-engineering |
| GitHub Actions | ci-cd-pipeline-builder | djacobsmeyer/claude-skills-engineering |
| Playwright | webapp-testing | anthropics/skills |

### Recommendation Format

When the Research Agent detects skill gaps, it provides recommendations in this format:

```markdown
## Skill Gap Analysis

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

## Recommended Skills

### High Priority

**test-driven-development** (obra/superpowers)
- **Why:** pytest detected but no TDD workflow skill
- **Benefits:** Enforces RED-GREEN-REFACTOR cycle, reduces bugs
- **Installation:**
  ```bash
  /plugin marketplace add obra/superpowers
  /plugin install test-driven-development@superpowers
  ```

**backend-engineer** (alirezarezvani/claude-skills)
- **Why:** FastAPI backend but no API design skill
- **Benefits:** API design patterns, request validation, error handling
- **Installation:**
  ```bash
  /plugin marketplace add alirezarezvani/claude-skills
  /plugin install backend-engineer@alirezarezvani-claude-skills
  ```

### Medium Priority

**docker-workflow** (djacobsmeyer/claude-skills-engineering)
- **Why:** Docker usage detected
- **Benefits:** Container best practices, optimization
- **Installation:**
  ```bash
  /plugin marketplace add djacobsmeyer/claude-skills-engineering
  /plugin install docker-workflow@djacobsmeyer-claude-skills-engineering
  ```

**Note:** Restart Claude Code after deploying skills to activate them.
```

### When Skills Are Recommended

The Research Agent proactively recommends skills in these scenarios:

**1. Project Initialization Analysis**
- First-time project analysis
- New project setup
- Recommends foundational skill stack based on detected technologies

**2. Technology Stack Changes**
- New dependencies added
- New frameworks introduced
- Infrastructure changes detected

**3. Work Type Detection**
- User starts testing work → recommends TDD skills
- User begins debugging → recommends systematic-debugging
- User works on deployment → recommends CI/CD skills

**4. Quality Issues Detected**
- Test failures suggest TDD skill needed
- Code style issues suggest language-specific skills
- Security vulnerabilities suggest security-engineer skill

**5. Performance Bottlenecks**
- Slow queries → data-scientist skill for optimization
- Container performance → docker-workflow skill
- Build performance → build optimization skills

## Integration with Skills Deployment

The Research Agent works seamlessly with the Skills Deployment system:

**Workflow:**
1. **Detection:** Research Agent analyzes project
2. **Analysis:** Identifies technology stack and patterns
3. **Gap Analysis:** Compares deployed skills to detected needs
4. **Recommendations:** Provides prioritized skill deployment suggestions
5. **Deployment:** User deploys skills via CLI or marketplace
6. **Activation:** Skills become available after Claude Code restart

**CLI Integration:**

```bash
# Research agent recommends skills, then user deploys
claude-mpm skills deploy-github --toolchain python

# Check what's deployed
claude-mpm skills check-deployed

# List available skills for detected tech stack
claude-mpm skills list-available --toolchain python
```

## Examples

### Example 1: New Python FastAPI Project

**Research Agent Analysis:**

```
Analyzing project structure...

Technology Stack Detected:
✓ Python 3.11
✓ FastAPI 0.109.0
✓ pytest 8.0.0
✓ PostgreSQL client (psycopg2)
✓ Docker (Dockerfile, docker-compose.yml)

Currently Deployed Skills: None

Skill Gap Analysis: 4 critical gaps identified
```

**Recommendation Output:**

```markdown
## Recommended Skill Stack

### Foundational (Deploy First)
1. test-driven-development - TDD workflow enforcement
2. python-style - Python best practices and PEP 8

### Framework-Specific
3. backend-engineer - FastAPI API design patterns
4. systematic-debugging - Debugging methodology

### Operations
5. docker-workflow - Container best practices
6. ci-cd-pipeline-builder - GitHub Actions optimization

### Deployment Commands
```bash
# Install foundational skills
/plugin marketplace add obra/superpowers
/plugin install test-driven-development@superpowers
/plugin install systematic-debugging@superpowers

# Install framework skills
/plugin marketplace add alirezarezvani/claude-skills
/plugin install backend-engineer@alirezarezvani-claude-skills

# Restart Claude Code to activate
```
```

### Example 2: React + TypeScript Project

**Research Agent Analysis:**

```
Analyzing project structure...

Technology Stack Detected:
✓ TypeScript 5.2
✓ React 18.2
✓ Next.js 14 (App Router)
✓ Playwright (E2E testing)
✓ GitHub Actions
✓ Vercel deployment

Currently Deployed Skills:
- frontend-development (mrgoonie/claudekit-skills)

Skill Gap Analysis: 3 gaps identified
```

**Recommendation Output:**

```markdown
## Recommended Additional Skills

### High Priority

**web-frameworks** (mrgoonie/claudekit-skills)
- Why: Next.js App Router detected but no App Router skill
- Benefits: SSR patterns, server components, caching strategies

**webapp-testing** (anthropics/skills)
- Why: Playwright detected but no E2E testing skill
- Benefits: Test organization, page object patterns, best practices

### Medium Priority

**ci-cd-pipeline-builder** (djacobsmeyer/claude-skills-engineering)
- Why: GitHub Actions detected
- Benefits: Workflow optimization, caching strategies

### Deployment
```bash
/plugin marketplace add mrgoonie/claudekit-skills
/plugin install web-frameworks@claudekit-skills

/plugin marketplace add anthropics/skills
/plugin install webapp-testing@anthropic-agent-skills

# Restart Claude Code
```
```

### Example 3: Skill Recommendation During Development

**User Request:** "Help me write comprehensive tests for the authentication module"

**Research Agent Response:**

```markdown
## Test Development Assistance

I notice you're working on testing but don't have test-driven-development skill deployed.

### Recommended Skill

**test-driven-development** (obra/superpowers)

**Why This Helps:**
- Enforces RED-GREEN-REFACTOR cycle
- Prevents writing implementation before tests
- Provides structured testing workflow
- Reduces bugs through test-first approach

**Installation:**
```bash
/plugin marketplace add obra/superpowers
/plugin install test-driven-development@superpowers
```

**Alternative:** I can proceed without this skill, but having it provides:
- Mandatory test-first workflow enforcement
- Comprehensive testing patterns
- Best practice guidance at each step

Would you like to deploy this skill before continuing?
```

## Best Practices

### For Users

**1. Trust the Recommendations**
- Research Agent analyzes your entire tech stack
- Recommendations are based on industry best practices
- Skills are curated from proven repositories

**2. Deploy Skills in Batches**
- Install multiple related skills before restarting Claude Code
- Minimizes disruption from restarts
- Skills only load at Claude Code startup

**3. Review Skill Descriptions**
- Use `claude-mpm skills list-available` to browse
- Read skill documentation before deploying
- Understand what each skill provides

**4. Start with High Priority Skills**
- High priority skills address immediate needs
- Medium/low priority can be deferred
- Focus on your current work type

### For Integration

**1. Automatic Detection**
- Research Agent runs automatically during project analysis
- No manual configuration needed
- Detection happens in background

**2. Non-Intrusive Recommendations**
- Recommendations don't block work
- Skills are suggestions, not requirements
- User decides what to deploy

**3. Continuous Monitoring**
- Agent monitors for tech stack changes
- Updates recommendations as project evolves
- Suggests new skills when patterns change

## Technical Details

### Detection Algorithms

**File Pattern Matching:**
```python
# Python project detection
if exists("pyproject.toml") or exists("setup.py"):
    language = "python"
    if "pytest" in dependencies:
        recommend("test-driven-development")
    if "fastapi" in dependencies:
        recommend("backend-engineer")
```

**Dependency Analysis:**
```python
# Framework detection from package.json
dependencies = parse_json("package.json").get("dependencies", {})
if "react" in dependencies:
    recommend("frontend-development")
if "next" in dependencies:
    recommend("web-frameworks")
if "@playwright/test" in devDependencies:
    recommend("webapp-testing")
```

**Infrastructure Pattern Detection:**
```python
# CI/CD detection
if exists(".github/workflows/"):
    recommend("ci-cd-pipeline-builder")
if exists("Dockerfile"):
    recommend("docker-workflow")
if exists("terraform/"):
    recommend("devops-claude-skills")
```

### Integration with SkillsDeployer

The Research Agent uses the SkillsDeployer service for deployment commands:

```python
from claude_mpm.services.skills_deployer import SkillsDeployer

deployer = SkillsDeployer()

# Recommend skills based on detected toolchain
recommendations = deployer.get_toolchain_skills("python")

# Format installation commands
for skill in recommendations:
    print(f"/plugin install {skill['name']}@{skill['source']}")
```

## Troubleshooting

### Skills Not Being Recommended

**Problem:** Research Agent doesn't recommend skills even though technology is present

**Solutions:**
1. Check if configuration files are in project root
2. Verify technology is properly declared in config files
3. Run explicit analysis: `claude-mpm analyze-project`
4. Check if skills are already deployed

### Incorrect Skill Recommendations

**Problem:** Recommended skills don't match project needs

**Solutions:**
1. Check technology stack detection accuracy
2. Review deployed skills: `claude-mpm skills check-deployed`
3. Manually specify toolchain: `--toolchain python`
4. Provide feedback to improve detection

### Deployment Issues

**Problem:** Skills don't appear after deployment

**Solutions:**
1. Restart Claude Code (skills load at startup only)
2. Verify skill installation: `/plugin list`
3. Check Claude Code version: `claude --version` (need v1.0.92+)
4. Review installation logs for errors

## Related Documentation

- **[Skills Deployment Guide](../guides/skills-deployment-guide.md)** - Comprehensive deployment guide
- **[Skills Quick Reference](../reference/skills-quick-reference.md)** - Quick command reference
- **[Agent Capabilities Reference](agent-capabilities-reference.md)** - All agent capabilities
- **[PM Workflow](pm-workflow.md)** - How PM orchestrates agents

## Version History

**v2.6.0** (Current)
- Added skill gap detection and recommendations
- Technology stack detection enhancement
- Integration with SkillsDeployer service
- Proactive skill recommendations during workflows

**v2.5.0**
- Enhanced project analysis capabilities
- Improved dependency detection
- Better architecture mapping

**v2.0.0**
- Initial release with basic research capabilities
- Project structure analysis
- Documentation discovery
