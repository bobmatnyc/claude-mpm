# Auto-Configuration

**Version**: 4.10.0+
**Last Updated**: 2025-10-21

## Overview

The Auto-Configuration feature automatically detects your project's technology stack (languages, frameworks, deployment targets) and configures the appropriate Claude MPM agents without manual intervention. It eliminates guesswork and ensures you always have the right agents for your project.

### Why Use Auto-Configuration?

- **Zero Configuration**: Get started immediately without studying agent documentation
- **Intelligent Detection**: Analyzes your project files to identify technologies
- **Confidence Scoring**: Only recommends agents it's confident about (default 80%+)
- **Safe Deployment**: Preview recommendations before deploying
- **Time Saving**: What takes minutes manually happens in seconds automatically

### Key Benefits

- **Accuracy**: Multi-strategy detection with evidence tracking
- **Flexibility**: Supports Python, Node.js, Rust, Go, and more
- **Safety**: Preview mode and confirmation prompts prevent mistakes
- **Transparency**: Clear reasoning for every recommendation
- **Extensibility**: Easy to add support for new languages/frameworks

## Quick Start

### Basic Usage

The fastest way to configure your project:

```bash
# Navigate to your project
cd /path/to/your/project

# Auto-configure (interactive with preview)
claude-mpm auto-configure
```

This will:
1. Analyze your project toolchain
2. Show detected technologies with confidence scores
3. Recommend appropriate agents
4. Ask for confirmation before deploying

### Non-Interactive Mode

For automation or CI/CD pipelines:

```bash
# Auto-configure without confirmation prompts
claude-mpm auto-configure --yes

# Preview only (no deployment)
claude-mpm auto-configure --preview

# JSON output for scripting
claude-mpm auto-configure --json
```

## Supported Technologies

### Languages

| Language | Detection Methods | Version Detection | Confidence Factors |
|----------|------------------|-------------------|-------------------|
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py` | Python version in files | File presence, syntax validity |
| **Node.js** | `package.json`, `package-lock.json` | Node version in package.json | Dependencies, scripts, engines |
| **Rust** | `Cargo.toml`, `Cargo.lock` | Edition in Cargo.toml | Manifest validity, dependencies |
| **Go** | `go.mod`, `go.sum` | Go version in go.mod | Module structure, dependencies |

### Frameworks

Auto-detected frameworks include:

**Python Frameworks:**
- FastAPI (via dependencies in requirements.txt/pyproject.toml)
- Django (Django in dependencies)
- Flask (Flask in dependencies)

**Node.js Frameworks:**
- Next.js (next in package.json dependencies)
- React (react in dependencies)
- Express (express in dependencies)
- Nuxt.js (nuxt in dependencies)
- Vue.js (vue in dependencies)

**Rust Frameworks:**
- Actix-web (actix-web in Cargo.toml)
- Rocket (rocket in dependencies)
- Axum (axum in dependencies)

**Go Frameworks:**
- Gin (github.com/gin-gonic/gin in go.mod)
- Echo (github.com/labstack/echo in go.mod)
- Fiber (github.com/gofiber/fiber in go.mod)

### Deployment Targets

Auto-detected deployment configurations:

- **Vercel**: `vercel.json`, `.vercel/` directory
- **Docker**: `Dockerfile`, `docker-compose.yml`
- **Google Cloud Platform**: `app.yaml`, `cloudbuild.yaml`
- **AWS**: Various AWS configuration files
- **Kubernetes**: `k8s/`, `kubernetes/` directories

## Commands

### `claude-mpm auto-configure`

Automatically configure agents based on detected project toolchain.

**Syntax:**
```bash
claude-mpm auto-configure [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--preview` | Preview recommendations without deploying | `false` |
| `--yes`, `-y` | Skip confirmation prompts | `false` |
| `--min-confidence FLOAT` | Minimum confidence threshold (0.0-1.0) | `0.8` |
| `--project-path PATH` | Path to project directory | Current directory |
| `--json` | Output results as JSON | `false` |
| `--dry-run` | Alias for `--preview` | `false` |

**Examples:**

```bash
# Interactive mode (recommended for first use)
claude-mpm auto-configure

# Preview what would be configured
claude-mpm auto-configure --preview

# Auto-configure without prompts (CI/CD)
claude-mpm auto-configure --yes

# Lower confidence threshold (more recommendations)
claude-mpm auto-configure --min-confidence 0.6

# Configure a different project
claude-mpm auto-configure --project-path /path/to/project

# JSON output for scripting
claude-mpm auto-configure --json
```

### `claude-mpm agents detect`

Detect project toolchain without configuring agents.

**Syntax:**
```bash
claude-mpm agents detect [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--project-path PATH` | Path to project directory | Current directory |
| `--json` | Output results as JSON | `false` |

**Examples:**

```bash
# Detect toolchain for current project
claude-mpm agents detect

# Detect for a specific project
claude-mpm agents detect --project-path /path/to/project

# JSON output
claude-mpm agents detect --json
```

**Sample Output:**
```
📊 Detected Toolchain:

Component          Version    Confidence
────────────────────────────────────────
Python             3.11       ██████████ 100%
FastAPI            0.104.1    █████████░ 95%
Vercel             Unknown    ████████░░ 85%
```

### `claude-mpm agents recommend`

Get agent recommendations based on detected toolchain.

**Syntax:**
```bash
claude-mpm agents recommend [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--min-confidence FLOAT` | Minimum confidence threshold | `0.8` |
| `--project-path PATH` | Path to project directory | Current directory |
| `--json` | Output results as JSON | `false` |

**Examples:**

```bash
# Get recommendations for current project
claude-mpm agents recommend

# Lower confidence threshold
claude-mpm agents recommend --min-confidence 0.6

# JSON output
claude-mpm agents recommend --json
```

**Sample Output:**
```
🤖 Recommended Agents:

  ✓ python-engineer (95% confidence)
    Reason: Python 3.11 detected with high confidence

  ✓ fastapi-specialist (90% confidence)
    Reason: FastAPI framework detected in dependencies

  ○ devops-engineer (75% confidence)
    Reason: Vercel deployment configuration detected
    (Below threshold of 80%)
```

## Configuration Options

### Confidence Threshold

The `--min-confidence` option controls which agents are recommended:

- **0.9-1.0**: Very high confidence (extremely strict)
- **0.8-0.9**: High confidence (recommended default)
- **0.7-0.8**: Medium confidence (more inclusive)
- **0.6-0.7**: Lower confidence (may include false positives)

**Choosing the Right Threshold:**

```bash
# Strict mode (only obvious matches)
claude-mpm auto-configure --min-confidence 0.9

# Balanced mode (recommended)
claude-mpm auto-configure --min-confidence 0.8

# Exploratory mode (discover more agents)
claude-mpm auto-configure --min-confidence 0.6
```

### Preview Mode

Preview mode shows what would be configured without making changes:

```bash
# Preview with interactive display
claude-mpm auto-configure --preview

# Preview with JSON output
claude-mpm auto-configure --preview --json
```

**Use Preview Mode When:**
- First time using auto-configuration
- Testing detection on a new project type
- Debugging why certain agents aren't recommended
- Reviewing changes before deployment

### Non-Interactive Mode

Use `--yes` flag for automation:

```bash
# In CI/CD pipeline
claude-mpm auto-configure --yes

# In scripts
claude-mpm auto-configure --yes --min-confidence 0.9
```

**Warning**: `--yes` skips all confirmation prompts. Use with caution in production environments.

## Examples

### Example 1: Python FastAPI Project

**Project Structure:**
```
my-project/
├── requirements.txt      # Contains: fastapi, uvicorn
├── pyproject.toml        # Python 3.11+
├── app/
│   └── main.py
└── vercel.json
```

**Command:**
```bash
claude-mpm auto-configure
```

**Output:**
```
📊 Detected Toolchain:

Component          Version    Confidence
────────────────────────────────────────
Python             3.11       ██████████ 100%
FastAPI            0.104.1    █████████░ 95%
Vercel             Unknown    ████████░░ 85%

🤖 Recommended Agents:

  ✓ python-engineer (95% confidence)
    Reason: Python 3.11 detected with FastAPI framework

  ✓ api-specialist (90% confidence)
    Reason: FastAPI framework detected for API development

  ✓ devops-engineer (85% confidence)
    Reason: Vercel deployment configuration found

Deploy these agents? (y/n/s for select): y

✅ python-engineer deployed successfully
✅ api-specialist deployed successfully
✅ devops-engineer deployed successfully

✅ Auto-configuration completed successfully!
```

### Example 2: Next.js TypeScript Project

**Project Structure:**
```
my-app/
├── package.json          # next, react, typescript
├── tsconfig.json
├── next.config.js
└── app/
    └── page.tsx
```

**Command:**
```bash
claude-mpm auto-configure --preview
```

**Output:**
```
📊 Detected Toolchain:

Component          Version    Confidence
────────────────────────────────────────
Node.js            18.x       ██████████ 100%
Next.js            14.0       █████████░ 98%
TypeScript         5.x        █████████░ 95%

🤖 Recommended Agents:

  ✓ nextjs-engineer (98% confidence)
    Reason: Next.js 14.0 with App Router detected

  ✓ typescript-engineer (95% confidence)
    Reason: TypeScript configuration found

  ✓ frontend-specialist (90% confidence)
    Reason: React framework detected in dependencies
```

### Example 3: Rust CLI Tool

**Project Structure:**
```
my-tool/
├── Cargo.toml
├── Cargo.lock
└── src/
    └── main.rs
```

**Command:**
```bash
claude-mpm auto-configure --min-confidence 0.7
```

**Output:**
```
📊 Detected Toolchain:

Component          Version    Confidence
────────────────────────────────────────
Rust               1.75       ██████████ 100%
Cargo              1.75       ██████████ 100%

🤖 Recommended Agents:

  ✓ rust-engineer (95% confidence)
    Reason: Rust project with Cargo build system

  ○ systems-engineer (75% confidence)
    Reason: Systems programming language detected
    (Included with threshold 0.7)
```

### Example 4: Multi-Language Monorepo

**Project Structure:**
```
monorepo/
├── backend/
│   ├── go.mod           # Go API
│   └── main.go
├── frontend/
│   ├── package.json     # Next.js
│   └── app/
└── scripts/
    └── deploy.py        # Python scripts
```

**Command:**
```bash
claude-mpm auto-configure
```

**Output:**
```
📊 Detected Toolchain:

Component          Version    Confidence
────────────────────────────────────────
Go                 1.21       ██████████ 100%
Node.js            18.x       █████████░ 98%
Next.js            14.0       █████████░ 95%
Python             3.11       ████████░░ 85%

🤖 Recommended Agents:

  ✓ go-engineer (95% confidence)
    Reason: Go module detected in backend/

  ✓ nextjs-engineer (95% confidence)
    Reason: Next.js detected in frontend/

  ✓ fullstack-engineer (90% confidence)
    Reason: Multiple frontend and backend technologies

  ✓ python-engineer (85% confidence)
    Reason: Python scripts detected
```

## Common Workflows

### Initial Project Setup

When starting with a new project:

```bash
# 1. First, preview what would be configured
claude-mpm auto-configure --preview

# 2. Review the recommendations

# 3. If satisfied, run full configuration
claude-mpm auto-configure

# 4. Verify deployed agents
claude-mpm agents list
```

### Project Type Detection

Understand what your project looks like to Claude MPM:

```bash
# 1. Detect toolchain
claude-mpm agents detect

# 2. See what agents would be recommended
claude-mpm agents recommend

# 3. Adjust confidence if needed
claude-mpm agents recommend --min-confidence 0.7
```

### CI/CD Integration

For automated environments:

```bash
# In your CI/CD script
claude-mpm auto-configure \
  --yes \
  --min-confidence 0.9 \
  --json > config-results.json

# Check exit code
if [ $? -eq 0 ]; then
  echo "Auto-configuration successful"
else
  echo "Auto-configuration failed"
  exit 1
fi
```

### Troubleshooting Detection

When auto-configuration doesn't detect what you expect:

```bash
# 1. Check what's being detected
claude-mpm agents detect --json

# 2. Try lower confidence threshold
claude-mpm agents recommend --min-confidence 0.6

# 3. If still not working, manually check detection files
# For Python: Check for requirements.txt, pyproject.toml
# For Node.js: Check for package.json
# For Rust: Check for Cargo.toml
# For Go: Check for go.mod
```

## Troubleshooting

### No Agents Recommended

**Symptoms:**
```
🤖 Recommended Agents:
  No agents recommended
```

**Possible Causes & Solutions:**

1. **No toolchain detected:**
   - Ensure your project has standard configuration files (package.json, requirements.txt, etc.)
   - Check that files are in the project root or accessible subdirectories

2. **Confidence threshold too high:**
   ```bash
   # Try lower threshold
   claude-mpm auto-configure --min-confidence 0.6
   ```

3. **Unsupported technology:**
   - Check [Supported Technologies](#supported-technologies) section
   - Consider creating a custom agent for your stack

### Wrong Agents Recommended

**Symptoms:**
Agents recommended don't match your project type.

**Solutions:**

1. **Review detection results:**
   ```bash
   claude-mpm agents detect --json
   ```

2. **Check for false positives:**
   - Remove unused dependency files
   - Clean up old configuration files
   - Ensure your primary technology has the strongest signals

3. **Increase confidence threshold:**
   ```bash
   claude-mpm auto-configure --min-confidence 0.9
   ```

### Detection Fails or Errors

**Symptoms:**
```
❌ Auto-configuration failed: [error message]
```

**Common Issues:**

1. **Permission errors:**
   - Ensure you have read access to project files
   - Check file permissions on configuration files

2. **Malformed configuration files:**
   - Validate JSON syntax in package.json
   - Check TOML syntax in Cargo.toml, pyproject.toml
   - Verify YAML syntax in configuration files

3. **Path issues:**
   - Use absolute paths with `--project-path`
   - Ensure the directory exists
   - Check that the path points to project root

**Debugging:**

```bash
# Enable debug logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm auto-configure --preview

# Check for specific files
ls -la package.json requirements.txt Cargo.toml go.mod

# Validate JSON files
python -m json.tool package.json
```

### Performance Issues

**Symptoms:**
Auto-configuration takes too long.

**Solutions:**

1. **Large project optimization:**
   - Detection uses caching (5-minute TTL)
   - Subsequent runs within 5 minutes use cached results

2. **Network-related delays:**
   - Detection is local-only (no network calls)
   - If slow, check disk I/O performance

3. **Clear cache:**
   ```bash
   # Cache automatically expires after 5 minutes
   # Or restart claude-mpm to clear cache
   ```

## Integration with Claude MPM

### Agent Deployment

Auto-configuration integrates with the agent deployment system:

- **Project-Level**: Agents deploy to `.claude/agents/` in your project
- **Three-Tier System**: Follows PROJECT > USER > SYSTEM hierarchy
- **Version Control**: Deployed agents can be committed to git

### Agent Registry

Auto-configuration uses the agent registry:

- Accesses all available agents (system, user, project tiers)
- Filters based on capabilities and requirements
- Respects agent metadata and dependencies

### Configuration Persistence

Auto-configuration results are persisted:

```bash
# Configuration saved to:
.claude-mpm/auto-config-state.json

# Contains:
# - Detection results
# - Deployed agents
# - Confidence scores
# - Timestamp
```

## Best Practices

### When to Use Auto-Configuration

**✅ Good Use Cases:**
- New projects with standard toolchains
- Onboarding new team members
- Switching between projects
- CI/CD pipelines
- Quick experiments and prototypes

**❌ When to Configure Manually:**
- Highly customized or non-standard setups
- Projects with strict agent requirements
- When you need specific agent versions
- Projects with unique constraints

### Confidence Threshold Guidelines

| Project Type | Recommended Threshold | Reasoning |
|--------------|---------------------|-----------|
| **Production** | 0.9 | High precision, fewer false positives |
| **Development** | 0.8 | Balanced precision and recall (default) |
| **Exploration** | 0.7 | Discover more possibilities |
| **Experimental** | 0.6 | Maximum agent suggestions |

### Review Before Deploying

Always use preview mode first on new project types:

```bash
# 1. Preview
claude-mpm auto-configure --preview

# 2. Review recommendations and reasoning

# 3. Deploy if satisfied
claude-mpm auto-configure
```

### Version Control

Consider committing auto-configuration results:

```bash
# .gitignore
# Don't ignore .claude/ for team sharing
# !.claude/agents/

# Commit deployed agents
git add .claude/agents/
git commit -m "Add auto-configured agents"
```

## Advanced Usage

### Custom Detection Strategies

For developers who want to extend detection:

See [Developer Documentation](../../developer/AUTO_CONFIGURATION.md#adding-new-language-support) for details on implementing custom detection strategies.

### Programmatic Usage

Use auto-configuration from Python code:

```python
from claude_mpm.services.agents.auto_config_manager import AutoConfigManagerService
from claude_mpm.services.agents.recommender import AgentRecommenderService
from claude_mpm.services.project.toolchain_analyzer import ToolchainAnalyzerService

# Initialize services
analyzer = ToolchainAnalyzerService()
recommender = AgentRecommenderService()
manager = AutoConfigManagerService(
    toolchain_analyzer=analyzer,
    agent_recommender=recommender
)

# Preview configuration
preview = manager.preview_configuration("/path/to/project", min_confidence=0.8)

# Execute configuration
result = manager.execute_configuration("/path/to/project", min_confidence=0.8)

print(f"Deployed {len(result.deployed_agents)} agents")
```

### JSON Output for Scripting

Parse JSON output in scripts:

```bash
# Get JSON output
OUTPUT=$(claude-mpm auto-configure --preview --json)

# Parse with jq
echo "$OUTPUT" | jq '.recommendations[] | select(.confidence > 0.9)'

# Example: Extract agent IDs
AGENTS=$(echo "$OUTPUT" | jq -r '.recommendations[].agent_id')
echo "Recommended agents: $AGENTS"
```

## See Also

- [Agent System Guide](../../AGENTS.md) - Complete agent development reference
- [Configure Command](configure-command.md) - Manual agent configuration
- [Developer Auto-Configuration Docs](../../developer/AUTO_CONFIGURATION.md) - Architecture and extension guide
- [Quick Start Guide](../../user/quickstart.md) - Getting started with Claude MPM
