# Auto-Configuration Guide

**Version**: 5.0.0
**Status**: Current
**Last Updated**: 2025-12-01

Claude MPM's auto-configuration feature automatically detects your project's technology stack and deploys the right agents for your workflow.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Detection Details](#detection-details)
- [Command Reference](#command-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Comparison with Other Methods](#comparison-with-other-methods)
- [Related Documentation](#related-documentation)

---

## Overview

Auto-configuration eliminates the guesswork from agent deployment. Instead of manually selecting agents, Claude MPM scans your project, understands your technology stack, and recommends the optimal agent configuration.

### What Auto-Configuration Does

1. **Detects** programming languages, frameworks, tools, and configurations
2. **Analyzes** your project structure and dependencies
3. **Recommends** agents based on detected technologies with confidence scores
4. **Deploys** recommended agents to your project

### When to Use Auto-Configuration

✅ **Use auto-configuration when:**
- Setting up a new project
- Adding Claude MPM to an existing project
- Working with mixed or custom technology stacks
- You want project-specific agent selection
- Learning which agents match your project

❌ **Use presets instead when:**
- You have a standard, well-known stack
- Speed is more important than accuracy
- You're following team standards
- You know exactly which agents you need

### Value Proposition

- **Accurate**: Detects 8+ languages, 20+ frameworks automatically
- **Fast**: Complete detection and deployment in under 60 seconds
- **Smart**: Confidence-based recommendations prevent false positives
- **Safe**: Preview mode lets you review before deploying
- **Flexible**: Customize confidence thresholds and filters

---

## Quick Start

### Basic Auto-Configuration

The simplest way to get started:

```bash
# Detect, recommend, and deploy agents (interactive)
claude-mpm agents auto-configure
```

This will:
1. Scan your project directory
2. Display detected technologies
3. Show recommended agents
4. Ask for confirmation
5. Deploy approved agents

### Preview Mode

See what would be configured without making changes:

```bash
# Preview recommendations only
claude-mpm agents auto-configure --preview
```

### Non-Interactive Mode

For scripts and CI/CD:

```bash
# Auto-approve recommendations
claude-mpm agents auto-configure --yes
```

---

## How It Works

Auto-configuration runs in three phases:

### Phase 1: Detection

```bash
claude-mpm agents detect
```

**What happens:**
- Scans project files and directories
- Identifies programming languages from file extensions
- Detects frameworks from configuration files
- Finds deployment targets (Docker, Vercel, etc.)
- Discovers tools and dependencies

**Detection methods:**
- File pattern matching (e.g., `*.py` → Python)
- Configuration file parsing (`package.json`, `requirements.txt`)
- Dependency analysis (npm packages, Python imports)
- Directory structure patterns (Django apps, Next.js pages)

### Phase 2: Recommendation

```bash
claude-mpm agents recommend
```

**What happens:**
- Maps detected technologies to relevant agents
- Calculates confidence scores (0-100%)
- Categorizes agents (Essential, Recommended, Optional)
- Provides rationale for each recommendation

**Confidence scoring:**
- **90-100%**: Strong evidence (multiple indicators)
- **70-89%**: Moderate evidence (clear indicators)
- **50-69%**: Weak evidence (indirect indicators)
- **<50%**: Insufficient evidence (not recommended by default)

### Phase 3: Deployment

Deploys recommended agents to `.claude-mpm/cache/agents/`:

```
.claude-mpm/
└── cache/
    └── agents/
        ├── python-engineer.md
        ├── react-engineer.md
        ├── api-qa.md
        └── ...
```

---

## Detection Details

### Supported Languages (8+)

| Language | Detection Method | Example Evidence |
|----------|------------------|------------------|
| **Python** | `*.py` files, `requirements.txt`, `pyproject.toml` | `main.py`, `setup.py` |
| **JavaScript** | `*.js` files, `package.json` | `index.js`, `node_modules/` |
| **TypeScript** | `*.ts` files, `tsconfig.json` | `app.ts`, `types.d.ts` |
| **Go** | `*.go` files, `go.mod` | `main.go`, `go.sum` |
| **Rust** | `*.rs` files, `Cargo.toml` | `lib.rs`, `Cargo.lock` |
| **PHP** | `*.php` files, `composer.json` | `index.php`, `vendor/` |
| **Ruby** | `*.rb` files, `Gemfile` | `app.rb`, `Rakefile` |
| **Java** | `*.java` files, `pom.xml`, `build.gradle` | `Main.java`, `target/` |

### Supported Frameworks (20+)

#### Backend Frameworks

| Framework | Language | Detection Evidence |
|-----------|----------|-------------------|
| **FastAPI** | Python | `from fastapi import`, `FastAPI()` in code |
| **Django** | Python | `django` in requirements, `manage.py` |
| **Flask** | Python | `from flask import`, `Flask(__name__)` |
| **Express** | JavaScript | `"express"` in package.json |
| **NestJS** | TypeScript | `@nestjs/core` dependency |
| **Spring Boot** | Java | `@SpringBootApplication` annotation |
| **Laravel** | PHP | `artisan` file, `composer.json` |
| **Rails** | Ruby | `Gemfile` with `rails` |

#### Frontend Frameworks

| Framework | Language | Detection Evidence |
|-----------|----------|-------------------|
| **React** | JavaScript/TypeScript | `"react"` in package.json, JSX files |
| **Next.js** | JavaScript/TypeScript | `next.config.js`, `pages/` directory |
| **Vue** | JavaScript/TypeScript | `"vue"` in package.json, `*.vue` files |
| **Svelte** | JavaScript/TypeScript | `"svelte"` in package.json |
| **Angular** | TypeScript | `angular.json`, `@angular/core` |

#### Testing Frameworks

| Framework | Language | Detection Evidence |
|-----------|----------|-------------------|
| **pytest** | Python | `pytest.ini`, `test_*.py` files |
| **Jest** | JavaScript | `"jest"` in package.json |
| **Playwright** | JavaScript/TypeScript | `playwright.config` |
| **Cypress** | JavaScript | `cypress.json`, `cypress/` dir |

### Deployment Targets

| Target | Detection Evidence | Confidence Boost |
|--------|-------------------|------------------|
| **Docker** | `Dockerfile`, `docker-compose.yml` | +20% to ops agents |
| **Vercel** | `vercel.json`, `.vercel/` directory | +30% to vercel-ops |
| **Railway** | `railway.json`, Railway button in README | +20% to ops agents |
| **Kubernetes** | `*.yaml` with `kind: Deployment` | +30% to ops agents |
| **GitHub Actions** | `.github/workflows/*.yml` | +10% to ops/qa agents |

---

## Command Reference

### `claude-mpm agents detect`

Scan project and display detected technologies.

**Usage:**
```bash
claude-mpm agents detect [OPTIONS]
```

**Options:**
- `--path PATH` - Project directory to scan (default: current directory)
- `--json` - Output JSON format (for scripting)
- `--verbose` - Show detailed evidence for detections
- `--debug` - Enable debug logging

**Examples:**
```bash
# Detect in current project
claude-mpm agents detect

# Detect in specific directory
claude-mpm agents detect --path /path/to/project

# JSON output for scripting
claude-mpm agents detect --json > detection.json

# Verbose output with evidence
claude-mpm agents detect --verbose
```

**Sample Output:**
```
📊 Project Toolchain Analysis
Project: /Users/dev/my-fastapi-project

🔤 Detected Languages:
┌──────────┬─────────┬────────────────────┐
│ Language │ Version │ Confidence         │
├──────────┼─────────┼────────────────────┤
│ Python   │ 3.11.0  │ ██████████ 100%    │
│ TypeScript│ 5.0.0  │ ████████░░  80%    │
└──────────┴─────────┴────────────────────┘

🏗️  Detected Frameworks:
┌──────────┬─────────┬──────────┬────────────────────┐
│ Framework│ Version │ Category │ Confidence         │
├──────────┼─────────┼──────────┼────────────────────┤
│ FastAPI  │ 0.104.1 │ backend  │ ██████████  95%    │
│ React    │ 18.2.0  │ frontend │ ████████░░  85%    │
└──────────┴─────────┴──────────┴────────────────────┘

✅ Analysis complete: 2 language(s), 2 framework(s), 1 deployment target(s)
```

---

### `claude-mpm agents recommend`

Get agent recommendations based on detection results.

**Usage:**
```bash
claude-mpm agents recommend [OPTIONS]
```

**Options:**
- `--path PATH` - Project directory (default: current directory)
- `--threshold INT` - Confidence threshold 0-100 (default: 70)
- `--preview` - Show recommendations without deploying
- `--json` - Output JSON format

**Examples:**
```bash
# Get recommendations
claude-mpm agents recommend

# Lower threshold for more suggestions
claude-mpm agents recommend --threshold 60

# Higher threshold for stricter matching
claude-mpm agents recommend --threshold 85

# Preview mode (no side effects)
claude-mpm agents recommend --preview
```

**Sample Output:**
```
💡 Agent Recommendations for your project

📋 ESSENTIAL (8 agents) - Core agents for detected technologies:
  ✓ universal/memory-manager      (95%) - Project memory management
  ✓ engineer/backend/python-engineer (95%) - Python/FastAPI development
  ✓ engineer/frontend/react-engineer (85%) - React development
  ✓ qa/api-qa                     (90%) - API testing
  ✓ qa/web-qa                     (85%) - Frontend testing
  ✓ ops/core/ops                  (80%) - Docker operations
  ✓ security/security             (75%) - Security scanning
  ✓ documentation/documentation   (70%) - Documentation generation

📋 RECOMMENDED (3 agents) - Enhance development workflow:
  ○ universal/research             (70%) - Research and analysis
  ○ documentation/ticketing        (65%) - Ticket management
  ○ universal/code-analyzer        (60%) - Code quality analysis

📋 OPTIONAL (2 agents) - Specialized capabilities:
  ○ ops/platform/vercel-ops        (55%) - Vercel deployment
  ○ qa/qa                          (50%) - General QA

💡 To deploy: claude-mpm agents auto-configure --yes
```

---

### `claude-mpm agents auto-configure`

Complete auto-configuration workflow (detect → recommend → deploy).

**Usage:**
```bash
claude-mpm agents auto-configure [OPTIONS]
```

**Options:**
- `--path PATH` - Project directory (default: current directory)
- `--threshold INT` - Confidence threshold 0-100 (default: 70)
- `--preview` - Preview without deploying
- `--yes` - Auto-approve without confirmation
- `--force` - Redeploy even if agents exist
- `--json` - JSON output

**Examples:**
```bash
# Interactive auto-configuration
claude-mpm agents auto-configure

# Non-interactive (for scripts/CI)
claude-mpm agents auto-configure --yes

# Preview what would be configured
claude-mpm agents auto-configure --preview

# Force reconfiguration
claude-mpm agents auto-configure --force --yes

# Custom threshold
claude-mpm agents auto-configure --threshold 80
```

**Interactive Workflow:**
```
🔍 Detecting project stack...
  ✓ Found: Python 3.11, FastAPI 0.104, React 18.2
  ✓ Detected 2 languages, 2 frameworks, 1 deployment target

💡 Recommending agents...
  ✓ 8 essential agents
  ✓ 3 recommended agents
  ✓ 2 optional agents

📦 Deploy 11 agents to .claude-mpm/cache/agents/? [Y/n]:
```

---

## Examples

### Example 1: FastAPI Backend Project

**Project structure:**
```
my-api/
├── app/
│   ├── main.py
│   ├── models.py
│   └── routers/
├── tests/
│   └── test_api.py
├── requirements.txt
├── pytest.ini
└── Dockerfile
```

**Auto-configuration:**
```bash
cd my-api
claude-mpm agents auto-configure
```

**Result:**
- **Detected**: Python 3.11, FastAPI 0.104, pytest, Docker
- **Deployed agents** (8):
  - `python-engineer` (backend development)
  - `api-qa` (API testing)
  - `ops` (Docker operations)
  - `security` (security scanning)
  - `memory-manager` (context management)
  - `research` (documentation lookup)
  - `documentation` (doc generation)
  - `qa` (general testing)

---

### Example 2: Next.js Full-Stack Project

**Project structure:**
```
my-nextjs-app/
├── app/
│   ├── page.tsx
│   └── api/
├── components/
├── package.json
├── tsconfig.json
├── next.config.js
└── vercel.json
```

**Auto-configuration:**
```bash
cd my-nextjs-app
claude-mpm agents auto-configure --threshold 75
```

**Result:**
- **Detected**: TypeScript 5.0, Next.js 14, React 18, Vercel
- **Deployed agents** (10):
  - `nextjs-engineer` (Next.js development)
  - `react-engineer` (React components)
  - `typescript-engineer` (TypeScript support)
  - `web-qa` (frontend testing)
  - `vercel-ops` (Vercel deployment)
  - `security` (security scanning)
  - `memory-manager` (context)
  - `research` (documentation)
  - `documentation` (docs)
  - `code-analyzer` (code quality)

---

### Example 3: Multi-Language Monorepo

**Project structure:**
```
monorepo/
├── backend/          # Python FastAPI
│   └── requirements.txt
├── frontend/         # React TypeScript
│   └── package.json
├── services/
│   ├── auth-service/ # Go
│   └── data-service/ # Rust
└── docker-compose.yml
```

**Auto-configuration:**
```bash
cd monorepo
claude-mpm agents auto-configure --verbose
```

**Result:**
- **Detected**: Python, TypeScript, Go, Rust, Docker
- **Deployed agents** (12):
  - Language-specific: `python-engineer`, `typescript-engineer`, `golang-engineer`, `rust-engineer`
  - Framework-specific: `react-engineer`, `api-qa`
  - Infrastructure: `ops`, `security`
  - Universal: `memory-manager`, `research`, `documentation`, `code-analyzer`

---

## Troubleshooting

### Detection Issues

#### Problem: Language Not Detected

**Symptoms:**
- Expected language missing from detection output
- Wrong agents recommended

**Solutions:**
1. **Check file extensions**: Ensure files have correct extensions (`.py`, `.js`, `.go`)
2. **Verify directory structure**: Auto-configuration scans recursively
3. **Use verbose mode**: `claude-mpm agents detect --verbose` to see evidence
4. **Check confidence threshold**: Lower threshold with `--threshold 60`

**Example:**
```bash
# Debug detection with verbose output
claude-mpm agents detect --verbose --debug

# Expected output should show evidence:
# Evidence: main.py, app.py, requirements.txt (3 files)
```

---

#### Problem: Wrong Framework Detected

**Symptoms:**
- Framework detected that isn't actually used
- High confidence for incorrect framework

**Solutions:**
1. **Check for leftover files**: Remove old configuration files
2. **Verify dependencies**: Ensure `package.json`/`requirements.txt` is current
3. **Manual override**: Use presets or manual deployment instead
4. **Increase threshold**: `--threshold 85` for stricter matching

---

#### Problem: Low Confidence Scores

**Symptoms:**
- All recommendations below 70%
- "Insufficient evidence" warnings

**Solutions:**
1. **Add configuration files**: Create `package.json`, `requirements.txt`, etc.
2. **Organize project structure**: Follow framework conventions
3. **Lower threshold**: `--threshold 50` to see more suggestions
4. **Use presets**: If you know your stack, use preset instead

**Example:**
```bash
# Try lower threshold
claude-mpm agents recommend --threshold 50

# Or use preset for known stack
claude-mpm agents deploy --preset python-dev
```

---

### Deployment Issues

#### Problem: Deployment Failed

**Symptoms:**
- Error during agent deployment
- Partial deployment (some agents missing)

**Solutions:**
1. **Check permissions**: Ensure write access to `.claude-mpm/`
2. **Force redeploy**: Use `--force` flag
3. **Clear cache**: Remove `.claude-mpm/cache/` and retry
4. **Check disk space**: Ensure sufficient storage

**Example:**
```bash
# Force clean deployment
rm -rf .claude-mpm/cache/agents/
claude-mpm agents auto-configure --force --yes
```

---

#### Problem: Wrong Agents Deployed

**Symptoms:**
- Agents don't match project needs
- Missing essential agents

**Solutions:**
1. **Review recommendations first**: Use `--preview` mode
2. **Adjust threshold**: Higher threshold = fewer agents
3. **Manual selection**: Use `claude-mpm agents deploy <agent-name>` for specific agents
4. **Use preset**: Preset might be more appropriate

---

### Performance Issues

#### Problem: Detection Takes Too Long

**Symptoms:**
- Scan runs for several minutes
- Timeout errors

**Solutions:**
1. **Exclude large directories**: Add `.claudempmignore` file
2. **Limit scan depth**: Use `--path` to scan subdirectories
3. **Check for large node_modules**: Detection skips these, but traversal takes time

**Example `.claudempmignore`:**
```
node_modules/
venv/
.venv/
dist/
build/
.git/
```

---

## Comparison with Other Methods

### Auto-Configure vs. Presets vs. Manual

| Feature | Auto-Configure | Presets | Manual |
|---------|---------------|---------|--------|
| **Speed** | Fast (30-60s) | Fastest (<5s) | Slow (minutes) |
| **Accuracy** | High (project-specific) | Medium (generic) | Highest (explicit) |
| **Customization** | Medium (threshold tuning) | Low (post-deploy only) | Full |
| **Learning Curve** | Low (automated) | Lowest (one command) | High (know all agents) |
| **Best For** | Greenfield projects | Known stacks | Specific needs |
| **Project Types** | Any | Standard stacks | Complex/custom |
| **Team Adoption** | Easy | Easiest | Requires expertise |

---

### When to Use Each Method

#### Choose Auto-Configure When:

✅ Working with mixed technology stacks
✅ Project has unique or custom architecture
✅ You want to discover which agents are available
✅ Learning Claude MPM capabilities
✅ Project doesn't fit standard presets
✅ You want confidence-based recommendations

**Example scenarios:**
- Microservices with multiple languages
- Custom framework or toolchain
- Legacy project migration
- Experimental or research projects

---

#### Choose Presets When:

✅ Using standard, well-known technology stack
✅ Speed is critical (onboarding, quick setup)
✅ Following team standards
✅ You know exactly which agents you need
✅ Deploying multiple similar projects

**Example scenarios:**
- Standard FastAPI backend
- Typical Next.js full-stack app
- Team-wide agent standardization
- Quick demos or prototypes

**See**: [Agent Presets Guide](agent-presets.md)

---

#### Choose Manual When:

✅ Very specific agent requirements
✅ Testing individual agents
✅ Custom agent configurations
✅ Debugging agent issues
✅ Expert user with clear goals

**Example scenarios:**
- Single-agent testing
- Custom agent development
- Minimal setups
- Troubleshooting

**See**: [Agent Sources Guide](agent-sources.md)

---

### Hybrid Approach

You can combine methods for optimal results:

```bash
# 1. Start with preset for core agents
claude-mpm agents deploy --preset python-dev

# 2. Add project-specific agents via auto-configure
claude-mpm agents recommend --threshold 80

# 3. Manually add specialized agents
claude-mpm agents deploy ops/platform/railway-ops
```

This gives you:
- **Speed** of presets
- **Accuracy** of auto-configure
- **Precision** of manual selection

---

## Related Documentation

### User Guides
- **[Agent Presets Guide](agent-presets.md)** - Pre-configured agent bundles for common stacks
- **[Agent Sources Guide](agent-sources.md)** - Managing agent repositories and custom agents
- **[Getting Started](getting-started.md)** - First steps with Claude MPM

### Reference
- **[CLI Agents Reference](../reference/cli-agents.md)** - Complete CLI command documentation
- **[Slash Commands](../reference/slash-commands.md)** - In-session command reference

### Slash Commands
- **`/mpm-agents-detect`** - Run detection from Claude session
- **`/mpm-agents-recommend`** - Get recommendations from Claude session
- **`/mpm-agents-auto-configure`** - Full auto-configuration from Claude session

### Implementation
- **[Toolchain Analysis Implementation](../implementation/toolchain-analyzer.md)** - Technical details
- **[Agent Recommendation Algorithm](../implementation/agent-recommendation.md)** - Scoring methodology

---

**Need Help?**
- Run `/mpm-doctor` to diagnose issues
- Check [Troubleshooting Guide](troubleshooting.md) for common problems
- See [FAQ](faq.md) for frequently asked questions

---

**Last Updated**: 2025-12-01
**Version**: 5.0.0
**Status**: Current
