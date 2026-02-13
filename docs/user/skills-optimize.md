# Skills Optimization Command

The `claude-mpm skills optimize` command intelligently analyzes your project and recommends relevant skills based on detected technologies.

## Overview

This command automatically:
1. **Detects your technology stack** (languages, frameworks, tools, databases)
2. **Recommends relevant skills** with priority levels
3. **Optionally deploys** recommended skills to your project

## Basic Usage

```bash
# Analyze project and get skill recommendations
claude-mpm skills optimize

# Auto-deploy recommended skills without confirmation
claude-mpm skills optimize --auto-deploy

# Limit to 5 recommendations
claude-mpm skills optimize --max-skills 5

# Show only critical priority skills
claude-mpm skills optimize --priority critical
```

## How It Works

### 1. Project Inspection

The command analyzes your project files to detect:

**Languages:**
- Python (via `.py` files, `pyproject.toml`, `requirements.txt`)
- JavaScript/TypeScript (via `.js`, `.ts` files, `package.json`, `tsconfig.json`)
- Rust (via `.rs` files, `Cargo.toml`)
- Go (via `.go` files, `go.mod`)
- Java (via `.java` files, `pom.xml`, `build.gradle`)
- And more...

**Frameworks:**
- **Python**: FastAPI, Django, Flask, pytest, SQLAlchemy
- **JavaScript/TypeScript**: React, Next.js, Vue, Angular, Express, Jest, Vitest
- **Rust**: Actix-web, Rocket
- **Go**: Gin, Echo

**Tools:**
- Docker, Kubernetes, Terraform, Ansible
- GitHub Actions, GitLab CI, CircleCI
- Makefile

**Databases:**
- PostgreSQL, MySQL, MongoDB, Redis, SQLite

### 2. Skill Recommendation

Skills are scored based on:
- **Relevance**: How well skill tags match detected technologies
- **Confidence**: Detection confidence for each technology
- **Priority**: Critical, High, Medium, or Low based on importance

### 3. Priority Levels

**Critical** - Essential skills for your stack:
- Core language skills (e.g., `python-core`, `typescript-core`)
- Primary framework skills (e.g., `fastapi`, `react`)
- Testing framework skills (e.g., `pytest`, `jest`)

**High** - Highly recommended:
- Framework-specific skills for detected frameworks
- Infrastructure tools (Docker, Kubernetes)
- Database-specific skills

**Medium** - Nice-to-have:
- Optional enhancements
- Supporting libraries
- Performance optimizations

**Low** - Situational:
- Alternative tools
- Niche use cases
- Experimental features

## Command Options

### `--repos REPOS [REPOS ...]`

Specify additional skill repositories to consider (future feature).

```bash
claude-mpm skills optimize --repos https://github.com/org/custom-skills
```

### `--auto-deploy`

Automatically deploy recommended skills without prompting for confirmation.

```bash
claude-mpm skills optimize --auto-deploy
```

### `--max-skills MAX_SKILLS`

Maximum number of skills to recommend (default: 10).

```bash
claude-mpm skills optimize --max-skills 20
```

### `--priority {critical,high,medium,low,all}`

Filter recommendations by minimum priority level (default: high).

```bash
# Show only critical skills
claude-mpm skills optimize --priority critical

# Show all recommendations
claude-mpm skills optimize --priority all
```

## Example Output

```bash
$ claude-mpm skills optimize

🔍 Analyzing project...

Detected Technologies:
  Languages: python (100%), javascript (100%), typescript (70%)
  Frameworks: fastapi (95%), react (95%), pytest (95%)
  Tools: docker (100%), github-actions (90%)
  Databases: postgresql (100%)

Generating skill recommendations...

Recommended Skills (8):

CRITICAL (3):
  1. toolchains-python-frameworks-fastapi
     FastAPI framework detected (confidence: 95%)
     Install: claude-mpm skills deploy --skill toolchains-python-frameworks-fastapi

  2. toolchains-javascript-frameworks-react
     React framework detected (confidence: 95%)
     Install: claude-mpm skills deploy --skill toolchains-javascript-frameworks-react

  3. toolchains-python-testing-pytest
     Pytest framework detected (confidence: 95%)
     Install: claude-mpm skills deploy --skill toolchains-python-testing-pytest

HIGH (2):
  4. universal-infrastructure-docker
     Docker tool detected (confidence: 100%)
     Install: claude-mpm skills deploy --skill universal-infrastructure-docker

  5. toolchains-python-database-postgresql
     PostgreSQL database detected (confidence: 100%)
     Install: claude-mpm skills deploy --skill toolchains-python-database-postgresql

MEDIUM (3):
  6. toolchains-typescript-core
     TypeScript language detected (confidence: 70%)
     Install: claude-mpm skills deploy --skill toolchains-typescript-core

  7. universal-testing-test-driven-development
     Testing framework detected
     Install: claude-mpm skills deploy --skill universal-testing-test-driven-development

  8. universal-debugging-systematic-debugging
     General best practices skill
     Install: claude-mpm skills deploy --skill universal-debugging-systematic-debugging

Deploy recommended skills? [Y/n]: y

Deploying recommended skills...

Syncing skill sources...
Synced 1 skill source(s)

Deploying from cache to project...

✓ Deployed 8 skill(s):
  • toolchains-python-frameworks-fastapi
  • toolchains-javascript-frameworks-react
  • toolchains-python-testing-pytest
  • universal-infrastructure-docker
  • toolchains-python-database-postgresql
  • toolchains-typescript-core
  • universal-testing-test-driven-development
  • universal-debugging-systematic-debugging

✓ Successfully optimized skills for your project!
8 skills deployed, 0 already present
```

## Use Cases

### New Project Setup

When starting a new project, quickly get relevant skills deployed:

```bash
cd my-new-project
claude-mpm init
claude-mpm skills optimize --auto-deploy
```

### Adding to Existing Project

Discover missing skills for an existing project:

```bash
cd existing-project
claude-mpm skills optimize
# Review recommendations
# Deploy selectively
```

### Technology Migration

After adding new technologies, update your skills:

```bash
# Added React to backend-only project
claude-mpm skills optimize --priority high
# Get React skills recommended
```

### CI/CD Integration

Automate skill deployment in CI/CD:

```bash
# .github/workflows/setup.yml
- name: Optimize Skills
  run: claude-mpm skills optimize --auto-deploy --priority critical
```

## Tips

**Tip 1: Start with Critical Skills**
```bash
# Deploy only essential skills first
claude-mpm skills optimize --priority critical --auto-deploy
```

**Tip 2: Review Before Deploying**
```bash
# See recommendations without deploying
claude-mpm skills optimize
# Review carefully, then deploy specific skills
claude-mpm skills deploy --skill <skill-name>
```

**Tip 3: Periodic Re-optimization**
```bash
# As your stack evolves, re-run optimize
claude-mpm skills optimize
# Deployed skills are automatically skipped
```

**Tip 4: Check What's Already Deployed**
```bash
# See current skills
claude-mpm skills list
# Then optimize to find gaps
claude-mpm skills optimize
```

## Troubleshooting

### No Recommendations Found

**Cause**: Unusual stack or no config files detected.

**Solution**:
- Ensure project has dependency files (package.json, pyproject.toml, etc.)
- Check if technologies are listed in supported patterns
- Use `claude-mpm skills list` to browse all available skills manually

### Wrong Technologies Detected

**Cause**: False positives from test files or vendored code.

**Solution**:
- Detection ignores `tests/`, `test/`, `node_modules/`, `vendor/` directories
- If still detecting wrong tech, deploy skills manually:
  ```bash
  claude-mpm skills deploy --skill <correct-skill>
  ```

### Skills Already Deployed

**Cause**: Running optimize multiple times.

**Solution**:
- Already deployed skills are automatically filtered out
- Use `--force` flag with `deploy` command to redeploy:
  ```bash
  claude-mpm skills deploy --force
  ```

## Related Commands

- `claude-mpm skills list` - List all available skills
- `claude-mpm skills deploy` - Deploy specific skills
- `claude-mpm skills configure` - Interactive skill selection
- `claude-mpm skills check-deployed` - Check currently deployed skills

## See Also

- [Skills System Overview](./skills-guide.md)
- [Skills Deployment](./skills-deployment.md)
- [Creating Custom Skills](../developer/creating-skills.md)
