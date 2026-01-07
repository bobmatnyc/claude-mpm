# Skills System User Guide

Complete guide to Claude MPM's Git-based skills system for extending agent capabilities.

**Status:** Active

## Table of Contents

- [Overview](#overview)
- [Skills vs. Slash Commands](#skills-vs-slash-commands)
- [Getting Started](#getting-started)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Creating Skills](#creating-skills)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Overview

### What is the Skills System?

The Skills System is a **Git-based skill discovery and management** framework that extends Claude MPM's agent capabilities without modifying the core codebase. Skills are self-contained instruction sets stored in Git repositories as Markdown files with YAML frontmatter.

### Why Use Skills?

**For Users:**
- **Extend Functionality**: Add new capabilities to agents without code changes
- **Share Knowledge**: Distribute best practices and workflows across teams
- **Version Control**: Track skill evolution through Git
- **Priority Control**: Manage conflicting skills with priority-based resolution

**For Organizations:**
- **Centralized Standards**: Maintain company-wide coding standards as skills
- **Team Collaboration**: Share skills across projects and teams
- **Custom Workflows**: Encode organization-specific processes
- **Quality Control**: Review skills through Git pull requests

### How Skills Differ from Agents

| Aspect | Agents | Skills |
|--------|--------|--------|
| **Purpose** | Task execution and delegation | Knowledge and workflows |
| **Format** | Markdown sections | Markdown + YAML frontmatter |
| **Discovery** | Agent deployment system | Skill discovery service |
| **Usage** | PM delegates to agents | Agents reference skills |
| **Example** | Research Agent, Code Agent | Code review checklist, TDD workflow |

## Skills vs. Slash Commands

**Framework skills** are context modules loaded into agents (from `.claude/skills/` or bundled in `src/claude_mpm/skills/bundled/`). Agents don't invoke skills; they use them as guidance.

**Slash commands** (e.g., `/mpm-init`) are user-invoked operations defined in `src/claude_mpm/commands/`. The PM can explain them, but only the user can run them.

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Claude MPM Startup                        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Skill Discovery Service                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  1. Load Configuration                                  │  │
│  │     - ~/.claude-mpm/config/skill_sources.yaml          │  │
│  │     - System repository (priority 0)                    │  │
│  │     - Custom repositories (priority 100+)               │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  2. Sync Git Repositories                               │  │
│  │     - ETag-based caching (reuses agent sync service)   │  │
│  │     - Download changed files only                       │  │
│  │     - Store in ~/.claude-mpm/cache/skills/{source}     │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  3. Discover Skills                                     │  │
│  │     - Scan cache for *.md files                         │  │
│  │     - Parse YAML frontmatter                            │  │
│  │     - Validate metadata                                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  4. Apply Priority Resolution                           │  │
│  │     - Group skills by skill_id                          │  │
│  │     - Select lowest priority for duplicates            │  │
│  │     - Build unified catalog                             │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Skills Available to Agents                       │
│  - Agents can reference skills by ID                         │
│  - Skills provide context and workflows                      │
│  - No code changes required                                  │
└──────────────────────────────────────────────────────────────┘
```

## Getting Started

### Quick Start (Bundled Skills Only)

**Default Setup - No Configuration Needed:**

Claude MPM includes bundled skills that work immediately after installation. No Git repositories or external sources required:

```bash
# Bundled skills are already available
claude-mpm configure
# → [2] Skills Management
# → [1] View bundled skills (shows 17 built-in skills)
```

### Advanced: Adding External Skill Sources (Optional)

If you want to use external skill repositories (not required):

1. **Check Current Configuration**
   ```bash
   claude-mpm skill-source list
   ```

2. **Add External Skill Source** (optional)
   ```bash
   # Add community repository (optional)
   claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills --priority 0
   ```

3. **Sync Skills from Repository**
   ```bash
   claude-mpm skill-source update
   ```

4. **Verify Health with Doctor**
   ```bash
   claude-mpm doctor
   # Look for "Skill Sources" section
   ```

5. **List Available Skills**
   ```bash
   # Bundled skills (always available):
   ls -la $(python -c "import claude_mpm.skills.bundled; import os; print(os.path.dirname(claude_mpm.skills.bundled.__file__))")

   # External skills (if configured):
   ls -la ~/.claude-mpm/cache/skills/
   ```

### Configuration File Location

External skill sources (if configured) are in:
```
~/.claude-mpm/config/skill_sources.yaml
```

**Default Configuration** (no external sources):
- Bundled skills are always available (no configuration needed)
- The configuration file only exists if you add external sources

**Example Configuration** (if you add external sources):
```yaml
sources:
  - id: community
    type: git
    url: https://github.com/bobmatnyc/claude-mpm-skills
    branch: main
    priority: 100
    enabled: true
```

### System Skills Repository (Optional)

**By default**, Claude MPM does NOT use external skill repositories. The Git-based skills system is **optional** for advanced users who want to:

- Access additional community-contributed skills
- Share skills across teams via Git repositories
- Maintain organization-specific skill collections

To use external skills, you can manually configure the system repository:
- **URL**: https://github.com/bobmatnyc/claude-mpm-skills
- **Priority**: 0 (highest precedence)
- **Skills**: Community-contributed skills beyond the bundled set

## CLI Commands

### List Skill Sources

```bash
claude-mpm skill-source list
```

**Output Example:**
```
Skill Sources (2 configured, 2 enabled)

✓ system (ENABLED)
  URL: https://github.com/bobmatnyc/claude-mpm-skills
  Branch: main
  Priority: 0 (highest)
  Last Update: 2025-11-30T10:00:00Z

✓ custom (ENABLED)
  URL: https://github.com/myorg/custom-skills
  Branch: main
  Priority: 100
  Last Update: Never
```

**Options:**
- `--by-priority`: Sort by priority (lowest first)
- `--enabled-only`: Show only enabled repositories
- `--json`: Output as JSON

### Add Skill Source

```bash
claude-mpm skill-source add <url> [--branch <branch>] [--priority <number>] [--disabled]
```

**Examples:**
```bash
# Add with default settings (branch: main, priority: 100)
claude-mpm skill-source add https://github.com/myorg/skills

# Add with custom priority (lower = higher precedence)
claude-mpm skill-source add https://github.com/myorg/skills --priority 50

# Add disabled (won't sync until enabled)
claude-mpm skill-source add https://github.com/myorg/skills --disabled

# Add with specific branch
claude-mpm skill-source add https://github.com/myorg/skills --branch develop
```

**URL Requirements:**
- Must be HTTPS GitHub URL
- Format: `https://github.com/owner/repo`
- Repository must be accessible (public or authenticated)

### Remove Skill Source

```bash
claude-mpm skill-source remove <source-id>
```

**Example:**
```bash
claude-mpm skill-source remove custom
```

**Note**: Removing a source deletes its cache but preserves configuration history.

### Show Skill Source Details

```bash
claude-mpm skill-source show <source-id>
```

**Output Example:**
```
Skill Source: system

Configuration:
  ID: system
  Type: git
  URL: https://github.com/bobmatnyc/claude-mpm-skills
  Branch: main
  Priority: 0
  Enabled: Yes

Status:
  Cache: /Users/user/.claude-mpm/cache/skills/system
  Skills Discovered: 25
  Last Sync: 2025-11-30T10:00:00Z
  Files Cached: 25

Skills:
  - code-review-checklist
  - test-driven-development
  - debugging-workflow
  ...
```

### Update (Sync) Skill Sources

```bash
claude-mpm skill-source update [source-id]
```

**Examples:**
```bash
# Update all enabled sources
claude-mpm skill-source update

# Update specific source
claude-mpm skill-source update system
```

**What Happens:**
1. Connects to Git repository
2. Downloads changed files (ETag-based caching)
3. Updates local cache
4. Discovers skills from new/changed files
5. Applies priority resolution

### Enable/Disable Skill Source

```bash
# Disable a source (keeps config, stops syncing)
claude-mpm skill-source disable <source-id>

# Re-enable a source
claude-mpm skill-source enable <source-id>
```

**Example:**
```bash
# Temporarily disable experimental skills
claude-mpm skill-source disable experimental

# Re-enable later
claude-mpm skill-source enable experimental
```

## Configuration

### Configuration File Structure

**Location**: `~/.claude-mpm/config/skill_sources.yaml`

**Full Example:**
```yaml
sources:
  # System repository (highest priority)
  - id: system
    type: git
    url: https://github.com/bobmatnyc/claude-mpm-skills
    branch: main
    priority: 0
    enabled: true

  # Team-specific skills
  - id: team
    type: git
    url: https://github.com/myorg/team-skills
    branch: main
    priority: 50
    enabled: true

  # Experimental skills (lowest priority)
  - id: experimental
    type: git
    url: https://github.com/myorg/experimental-skills
    branch: develop
    priority: 200
    enabled: false
```

### Source Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (alphanumeric + hyphens/underscores) |
| `type` | string | Yes | Source type (currently only "git" supported) |
| `url` | string | Yes | Full GitHub repository URL |
| `branch` | string | No | Git branch to use (default: "main") |
| `priority` | integer | No | Priority for conflict resolution (default: 100) |
| `enabled` | boolean | No | Whether to sync this source (default: true) |

### Priority System

**How Priority Works:**
- **Lower number = Higher precedence**
- **Range**: 0-1000 (recommended)
- **Reserved**: 0 for system repository
- **Default**: 100 for custom sources

**Priority Guidelines:**
- `0`: System repository (highest precedence)
- `1-99`: Critical organization-wide skills
- `100-199`: Standard team skills
- `200-999`: Experimental or optional skills
- `1000+`: Not recommended (unusually low precedence)

**Conflict Resolution:**

When multiple sources provide a skill with the same `skill_id`, the skill from the source with the **lowest priority number** wins.

**Example:**
```yaml
sources:
  - id: system
    priority: 0  # Has "code-review" skill
  - id: custom
    priority: 100  # Also has "code-review" skill

# Result: "code-review" from system (priority 0 < 100)
```

### Cache Directory Structure

**Location**: `~/.claude-mpm/cache/skills/`

**Structure:**
```
~/.claude-mpm/cache/skills/
├── system/                 # System repository cache
│   ├── code-review.md
│   ├── tdd-workflow.md
│   └── debugging.md
├── team/                   # Team repository cache
│   ├── api-standards.md
│   └── deploy-checklist.md
└── experimental/           # Experimental repository cache
    └── new-feature.md
```

Each source gets its own subdirectory identified by `source_id`.

## Creating Skills

### Skill File Format

Skills are **Markdown files with YAML frontmatter**. The frontmatter contains metadata, and the body contains instructions.

**Basic Structure:**
```markdown
---
skill_id: my-skill
name: My Skill
description: Brief description of what this skill does
version: "1.0.0"
tags:
  - category1
  - category2
agent_types:
  - research
  - code
---

# Skill Content

Detailed instructions, workflows, and examples go here.

## Section 1
...

## Section 2
...
```

### Required Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_id` | string | Yes | Unique identifier (kebab-case recommended) |
| `name` | string | Yes | Human-readable skill name |
| `description` | string | Yes | Brief description (1-2 sentences) |
| `version` | string | No | Semantic version (e.g., "1.0.0") |
| `tags` | list | No | Categorization tags |
| `agent_types` | list | No | Which agents can use this skill |

### Optional Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Skill creator |
| `license` | string | License type (MIT, Apache 2.0, etc.) |
| `dependencies` | list | Required skills or tools |
| `last_updated` | string | Last modification date (ISO 8601) |

### Skill Discovery Process

1. **File Scanning**: Discovery service scans cache directories for `*.md` files
2. **YAML Parsing**: Extracts frontmatter from each file
3. **Validation**: Checks required fields and format
4. **Metadata Extraction**: Builds skill catalog with metadata
5. **Priority Resolution**: Applies priority rules for duplicates

**Discovery Rules:**
- Only files with `.md` extension are scanned
- YAML frontmatter must be delimited by `---`
- Files without valid frontmatter are skipped (logged as warnings)
- Invalid metadata causes skill to be skipped (not fatal)

### Best Practices

**1. Skill ID Naming:**
```yaml
# Good: kebab-case, descriptive
skill_id: code-review-checklist
skill_id: test-driven-development

# Avoid: spaces, special characters
skill_id: Code Review!
skill_id: TDD_workflow
```

**2. Clear Descriptions:**
```yaml
# Good: concise, specific
description: Systematic code review checklist for quality assurance

# Avoid: vague, too long
description: A skill for reviewing code
description: This skill provides a comprehensive framework for conducting thorough code reviews...
```

**3. Versioning:**
```yaml
# Use semantic versioning
version: "1.0.0"   # Initial release
version: "1.1.0"   # Minor update (backward compatible)
version: "2.0.0"   # Major update (breaking changes)
```

**4. Tags for Discovery:**
```yaml
tags:
  - quality-assurance
  - code-review
  - best-practices
  - documentation
```

**5. Agent Type Targeting:**
```yaml
# General skills (all agents)
agent_types:
  - research
  - code
  - documentation

# Specialized skills (specific agents)
agent_types:
  - code  # Only code agent
```

### Example Skill

**File**: `code-review-checklist.md`

```markdown
---
skill_id: code-review-checklist
name: Code Review Checklist
description: Comprehensive checklist for systematic code reviews
version: "2.0.0"
tags:
  - quality-assurance
  - code-review
  - best-practices
agent_types:
  - code
  - research
author: Engineering Team
license: MIT
last_updated: "2025-11-30"
---

# Code Review Checklist

Systematic checklist for high-quality code reviews.

## Pre-Review

- [ ] Branch is up-to-date with main/master
- [ ] All tests pass locally
- [ ] No merge conflicts
- [ ] PR description is clear and complete

## Code Quality

- [ ] Code follows project style guidelines
- [ ] No commented-out code
- [ ] No debug statements (print, console.log)
- [ ] Proper error handling
- [ ] No magic numbers or strings

## Testing

- [ ] New features have tests
- [ ] Tests cover edge cases
- [ ] Test coverage ≥85%
- [ ] Tests are deterministic

## Documentation

- [ ] Public APIs have docstrings
- [ ] Complex logic is commented
- [ ] README updated if needed
- [ ] CHANGELOG updated

## Security

- [ ] No hardcoded credentials
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS prevention (if web)

## Performance

- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] Large lists/loops optimized
- [ ] Resource cleanup (files, connections)
```

## Troubleshooting

### Common Issues

#### Issue: Configuration Not Found

**Symptoms:**
```
Error: Skill sources configuration not found
```

**Solution:**
```bash
# Create default configuration
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills --priority 0

# Verify
claude-mpm skill-source list
```

#### Issue: Skills Not Syncing

**Symptoms:**
- `skill-source update` completes but no skills appear
- Cache directory is empty

**Diagnosis:**
```bash
# Check configuration
claude-mpm skill-source list

# Check doctor for errors
claude-mpm doctor

# Check cache manually
ls -la ~/.claude-mpm/cache/skills/
```

**Solutions:**

1. **Repository URL incorrect:**
   ```bash
   # Verify URL is accessible
   curl -I https://github.com/bobmatnyc/claude-mpm-skills

   # Update if needed
   claude-mpm skill-source remove system
   claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills --priority 0
   ```

2. **Branch doesn't exist:**
   ```bash
   # Check branch name (default: main)
   # Update if using different branch
   claude-mpm skill-source show system
   ```

3. **Source disabled:**
   ```bash
   # Enable the source
   claude-mpm skill-source enable system
   claude-mpm skill-source update
   ```

#### Issue: Priority Conflicts

**Symptoms:**
```
Warning: Priority 100 used by multiple sources: team, custom
```

**Impact:**
- Non-fatal warning (syncing continues)
- Unpredictable conflict resolution
- First source encountered wins (undefined order)

**Solution:**
```bash
# Adjust priorities to be unique
claude-mpm skill-source update team --priority 90
claude-mpm skill-source update custom --priority 110

# Verify
claude-mpm skill-source list --by-priority
```

#### Issue: Invalid YAML Frontmatter

**Symptoms:**
- Skills not appearing in discovery
- Doctor shows fewer skills than expected
- Warnings in verbose mode

**Diagnosis:**
```bash
# Check skill file manually
cat ~/.claude-mpm/cache/skills/system/my-skill.md

# Look for YAML errors:
# - Missing `---` delimiters
# - Invalid YAML syntax
# - Missing required fields (skill_id, name, description)
```

**Solution:**

Fix YAML frontmatter in your skill repository:
```yaml
# Correct format
---
skill_id: my-skill
name: My Skill
description: Description here
---

# Common errors to avoid:
# ❌ Missing closing ---
---
skill_id: my-skill
name: My Skill

# ❌ Invalid YAML
---
skill_id: my-skill
name My Skill  # Missing colon
---

# ❌ Missing required fields
---
skill_id: my-skill
# Missing name and description
---
```

#### Issue: Cache Corruption

**Symptoms:**
- Sync completes but skills are incomplete
- Partial file contents
- Random errors during discovery

**Solution:**
```bash
# Clear cache for specific source
rm -rf ~/.claude-mpm/cache/skills/system

# Re-sync
claude-mpm skill-source update system

# Or clear all caches
rm -rf ~/.claude-mpm/cache/skills/
claude-mpm skill-source update
```

#### Issue: Network/Git Errors

**Symptoms:**
```
Error: Failed to sync source 'system': Connection timeout
Error: Repository not found
```

**Solutions:**

1. **Network connectivity:**
   ```bash
   # Test connectivity
   ping github.com
   curl -I https://raw.githubusercontent.com/bobmatnyc/claude-mpm-skills/main/README.md
   ```

2. **Repository access:**
   ```bash
   # Verify repository exists and is public
   # Check URL in browser
   ```

3. **GitHub rate limiting:**
   ```bash
   # Wait and retry (rate limits reset hourly)
   # Or authenticate with GitHub (future enhancement)
   ```

### Using `claude-mpm doctor`

The `doctor` command includes comprehensive skill sources diagnostics.

**Run diagnostics:**
```bash
claude-mpm doctor
```

**Output Example:**
```
Diagnostic Results
==================

✓ Skill Sources (8 checks passed)
  ✓ Configuration file exists
  ✓ Configuration is valid YAML
  ✓ Sources configured (2 total, 2 enabled)
  ✓ System repository accessible
  ✓ All enabled sources reachable
  ✓ Cache directory healthy
  ! Priority conflicts detected (1 warning)
  ✓ Skills discovered (25 total)

  Details:
    - Total sources: 2
    - Enabled sources: 2
    - Skills discovered: 25
    - Priority conflicts: 1

  Fix: Adjust priorities to be unique
  Command: claude-mpm skill-source list --by-priority
```

**Verbose Mode** (detailed output):
```bash
claude-mpm doctor --verbose
```

Shows individual check results:
```
Skill Sources Detailed Checks:

1. Configuration File Exists
   ✓ PASS: /Users/user/.claude-mpm/config/skill_sources.yaml

2. Configuration Valid
   ✓ PASS: YAML syntax valid

3. Sources Configured
   ✓ PASS: 2 sources (2 enabled)

4. System Repository Accessible
   ✓ PASS: https://github.com/bobmatnyc/claude-mpm-skills

5. Source Reachability
   ✓ PASS: 2/2 sources reachable

6. Cache Directory
   ✓ PASS: ~/.claude-mpm/cache/skills/ (writable)

7. Priority Conflicts
   ! WARNING: Priority 100 used by: team, custom

8. Skills Discovery
   ✓ PASS: 25 skills discovered
```

### Doctor Diagnostics Reference

**8 Checks Performed:**

1. **Configuration Exists**: Verifies `skill_sources.yaml` exists
2. **Configuration Valid**: Validates YAML syntax and structure
3. **Sources Configured**: At least one source is configured
4. **System Repository**: System repository is accessible (if enabled)
5. **Source Reachability**: All enabled sources are reachable via HTTP
6. **Cache Health**: Cache directory exists and is writable
7. **Priority Conflicts**: Identifies duplicate priorities
8. **Skills Discovery**: Skills can be discovered from cache

**Interpreting Results:**

| Symbol | Meaning | Action Required |
|--------|---------|-----------------|
| ✓ | Pass | None |
| ! | Warning | Optional (non-blocking) |
| ✗ | Error | Required (blocking issue) |

## Examples

### Example 1: Adding a Custom Skill Repository

**Scenario**: Your organization has internal coding standards.

**Steps:**

1. **Create Git Repository** (GitHub, GitLab, etc.)
   ```
   myorg/coding-standards
   ├── README.md
   ├── python-style.md
   ├── api-design.md
   └── testing-standards.md
   ```

2. **Add Skills with YAML Frontmatter**

   **File**: `python-style.md`
   ```markdown
   ---
   skill_id: org-python-style
   name: Organization Python Style Guide
   description: Company-wide Python coding standards and best practices
   version: "1.0.0"
   tags:
     - python
     - style-guide
     - standards
   agent_types:
     - code
   ---

   # Organization Python Style Guide

   [Your organization's Python standards...]
   ```

3. **Add Repository to Claude MPM**
   ```bash
   # Add with high priority (org standards override system)
   claude-mpm skill-source add https://github.com/myorg/coding-standards --priority 10

   # Sync skills
   claude-mpm skill-source update

   # Verify
   claude-mpm doctor
   ```

4. **Verify Skills Are Available**
   ```bash
   # Check cache
   ls -la ~/.claude-mpm/cache/skills/coding-standards/

   # Should see:
   # python-style.md
   # api-design.md
   # testing-standards.md
   ```

### Example 2: Managing Multiple Skill Sources

**Scenario**: Use system skills + team skills + experimental skills.

**Configuration:**

```bash
# 1. System skills (highest priority)
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills --priority 0

# 2. Team skills (medium priority)
claude-mpm skill-source add https://github.com/myteam/skills --priority 50

# 3. Experimental skills (lowest priority, disabled by default)
claude-mpm skill-source add https://github.com/myteam/experimental --priority 200 --disabled

# Verify configuration
claude-mpm skill-source list --by-priority
```

**Output:**
```
Skill Sources (3 configured, 2 enabled)

✓ system (ENABLED, Priority: 0)
✓ team (ENABLED, Priority: 50)
✗ experimental (DISABLED, Priority: 200)
```

**Usage:**

```bash
# Daily workflow: sync enabled sources
claude-mpm skill-source update

# Enable experimental when needed
claude-mpm skill-source enable experimental
claude-mpm skill-source update experimental

# Disable when done testing
claude-mpm skill-source disable experimental
```

### Example 3: Overriding System Skills

**Scenario**: Customize a system skill for your organization.

**Approach:**

1. **Create custom repository with same skill_id**
   ```markdown
   ---
   skill_id: code-review-checklist  # Same as system skill
   name: Custom Code Review
   description: Organization-specific code review checklist
   version: "1.0.0"
   ---

   # Custom Code Review Checklist
   [Your organization's custom checklist...]
   ```

2. **Add with higher priority than system**
   ```bash
   # System is priority 0, custom should be lower (higher precedence)
   # But we want system skills generally, just override this one
   # Use priority 5 (between system 0 and default 100)
   claude-mpm skill-source add https://github.com/myorg/custom-skills --priority 5

   # Sync
   claude-mpm skill-source update
   ```

3. **Verify override**
   ```bash
   # Check which version is active
   claude-mpm skill-source show custom

   # Should show custom skill has priority 5, system has priority 0
   # But since custom has same skill_id, priority 5 wins for that specific skill
   ```

**Result**: Your custom `code-review-checklist` overrides the system version, but other system skills remain active.

### Example 4: Team Collaboration Workflow

**Scenario**: Share skills across team members.

**Setup:**

1. **Create shared Git repository**
   ```bash
   # In your team's Git repository
   mkdir skills
   cd skills

   # Add team skills
   touch python-testing.md
   touch deployment-checklist.md

   git add .
   git commit -m "Add team skills"
   git push
   ```

2. **Team members add repository**
   ```bash
   # Each team member runs:
   claude-mpm skill-source add https://github.com/teamname/repo --priority 50
   claude-mpm skill-source update
   ```

3. **Update skills**
   ```bash
   # When skills are updated in Git:
   # 1. Update repository (git commit, git push)

   # 2. Team members sync
   claude-mpm skill-source update teamname
   ```

**Benefits:**
- Consistent skills across team
- Version controlled through Git
- Pull request reviews for skill changes
- Automatic distribution via sync

---

## Related Documentation

- **[Skills API Reference](../reference/skills-api.md)** - Technical API documentation
- **[Agent Development Guide](../agents/creating-agents.md)** - How agents use skills
- **[Remote Agents Guide](../agents/remote-agents.md)** - Similar Git-based system for agents

---

**Last Updated**: 2025-11-30
**Version**: 1.0.0
