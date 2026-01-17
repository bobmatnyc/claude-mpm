# Skill Sources vs Collections: Understanding the Two Skill Management Systems

**Issue**: [#183 - Confusing overlap between skill-source and skills collection systems](https://github.com/bobmatnyc/claude-mpm/issues/183)

This guide explains why Claude MPM has two separate systems for managing skill repositories and when to use each.

## Table of Contents

1. [Overview](#overview)
2. [skill-source System (Recommended)](#skill-source-system-recommended)
3. [collection System (Legacy)](#collection-system-legacy)
4. [When to Use Which](#when-to-use-which)
5. [Migration Path](#migration-path)
6. [Troubleshooting](#troubleshooting)

---

## Overview

Claude MPM evolved from a single collection-based system to a more flexible skill-source architecture. Both systems currently coexist to maintain backward compatibility.

### Why Two Systems?

The architecture evolved in phases:

- **Phase 1 (Legacy)**: `collection` system using ZIP downloads and manifest.json
- **Phase 2**: Introduction of SKILL.md format with YAML frontmatter
- **Phase 3 (Current)**: `skill-source` system with Git-based sync and SKILL.md discovery

The `skill-source` system represents the modern architecture, while `collection` is maintained for backward compatibility with repositories still using the manifest.json format.

### Key Architectural Difference

```
┌─────────────────────────────────────────────────────────────┐
│                   skill-source System                        │
│  Git Clone → SKILL.md Discovery → Cache → Deploy            │
│  (YAML frontmatter format, incremental sync)                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   collection System                          │
│  ZIP Download → manifest.json Parsing → Deploy              │
│  (Metadata in JSON file, full download each time)           │
└─────────────────────────────────────────────────────────────┘
```

---

## skill-source System (Recommended)

The modern Git-based system for managing skill repositories with SKILL.md format.

### Architecture

```
~/.claude-mpm/
├── config/
│   └── skill_sources.yaml        # Configuration file
└── cache/
    └── skills/
        ├── system/                # Cached from priority 0 source
        │   └── universal/
        │       └── testing/
        │           └── SKILL.md   # YAML frontmatter + markdown
        └── custom-repo/           # Cached from custom source
```

### Commands

```bash
# Add a skill source
claude-mpm skill-source add https://github.com/owner/skills-repo

# List configured sources
claude-mpm skill-source list

# Update (sync) all sources
claude-mpm skill-source update

# Update specific source
claude-mpm skill-source update system

# Show source details with skills
claude-mpm skill-source show system --skills

# Enable/disable sources
claude-mpm skill-source enable custom-repo
claude-mpm skill-source disable custom-repo

# Remove a source
claude-mpm skill-source remove custom-repo
```

### Configuration File

Location: `~/.claude-mpm/config/skill_sources.yaml`

```yaml
sources:
  - id: system
    type: git
    url: https://github.com/bobmatnyc/claude-mpm-skills
    branch: main
    priority: 0
    enabled: true

  - id: anthropic-official
    type: git
    url: https://github.com/anthropics/skills
    branch: main
    priority: 1
    enabled: true

  - id: custom-repo
    type: git
    url: https://github.com/myorg/custom-skills
    branch: main
    priority: 100
    enabled: true
```

### Discovery Method

Scans for `SKILL.md` files with YAML frontmatter:

```markdown
---
name: systematic-debugging
description: Comprehensive debugging workflow
version: 1.0.0
tags:
  - debugging
  - troubleshooting
agent_types:
  - engineer
  - qa
---

# Systematic Debugging Skill

[Skill content in markdown...]
```

### Cache Location

- **Global cache**: `~/.claude-mpm/cache/skills/{source-name}/`
- Skills synced to cache first (Phase 1)
- Deployed from cache to projects (Phase 2)

### Authentication

For private repositories, set environment variable:

```bash
export GITHUB_TOKEN=ghp_your_token_here
# or
export GH_TOKEN=ghp_your_token_here
```

### Priority Resolution

When multiple sources have the same skill:
- **Lower priority number = higher precedence**
- Priority 0 (system) overrides all others
- Priority 1-99: High priority custom sources
- Priority 100-999: Normal priority
- Priority 1000+: Low priority

Example: If both `system` (priority 0) and `custom` (priority 100) have a skill named "debugging", the version from `system` wins.

### Best For

- ✅ Repositories using SKILL.md format with YAML frontmatter
- ✅ Git-based workflows with version control
- ✅ Incremental updates (ETag caching)
- ✅ Multi-project deployments from shared cache
- ✅ Priority-based skill resolution

---

## collection System (Legacy)

The original ZIP-based system using manifest.json for skill metadata.

### Architecture

```
~/.claude-mpm/
├── config/
│   └── skills_collections.yaml   # Configuration file
└── skills_collections/
    └── default/
        ├── manifest.json          # Skill metadata
        └── skills/
            ├── debugging/
            │   └── SKILL.md
            └── testing/
                └── SKILL.md
```

### Commands

```bash
# List collections
claude-mpm skills collection-list

# Add a collection
claude-mpm skills collection-add custom https://github.com/owner/skills/archive/main.zip

# Deploy from collection
claude-mpm skills deploy-github --collection default

# Remove collection
claude-mpm skills collection-remove custom

# Enable/disable collection
claude-mpm skills collection-enable custom
claude-mpm skills collection-disable custom

# Set default collection
claude-mpm skills collection-set-default custom
```

### Configuration File

Location: `~/.claude-mpm/config/skills_collections.yaml`

```yaml
default_collection: default
collections:
  default:
    url: https://github.com/bobmatnyc/claude-mpm-skills/archive/main.zip
    enabled: true
    priority: 0

  custom:
    url: https://github.com/myorg/skills/archive/main.zip
    enabled: true
    priority: 100
```

### Discovery Method

Parses `manifest.json` for skill metadata:

```json
{
  "skills": [
    {
      "name": "debugging",
      "display_name": "Systematic Debugging",
      "category": "development",
      "toolchain": "universal",
      "path": "skills/debugging/SKILL.md"
    }
  ]
}
```

### Deploy Target

- **Global deploy**: `~/.claude/skills/` (Claude Code global directory)
- No project-specific deployment
- Full re-download on each sync

### Best For

- ✅ Repositories with manifest.json format
- ✅ ZIP-based distribution
- ✅ Simple deployment to Claude Code global skills
- ⚠️ Backward compatibility (not recommended for new repos)

---

## When to Use Which

### Use skill-source (Recommended)

✅ **Your skills use SKILL.md format with YAML frontmatter**
```markdown
---
name: my-skill
description: My custom skill
---
```

✅ **You want incremental updates** (ETag caching)

✅ **You need priority-based skill resolution** (multiple sources)

✅ **You want project-specific skill deployments**

✅ **You're starting a new skill repository**

### Use collection (Legacy)

⚠️ **Your skills use manifest.json format**
```json
{
  "skills": [...]
}
```

⚠️ **You need to maintain compatibility with existing collection-based repos**

⚠️ **You only deploy to Claude Code global directory** (`~/.claude/skills/`)

---

## Migration Path

### Converting from collection to skill-source

**Step 1: Convert manifest.json to SKILL.md frontmatter**

Old format (manifest.json):
```json
{
  "skills": [
    {
      "name": "debugging",
      "display_name": "Systematic Debugging",
      "category": "development",
      "tags": ["debugging", "troubleshooting"]
    }
  ]
}
```

New format (SKILL.md):
```markdown
---
name: debugging
description: Systematic Debugging
version: 1.0.0
tags:
  - debugging
  - troubleshooting
agent_types:
  - engineer
  - qa
---

# Systematic Debugging

[Skill content...]
```

**Step 2: Add repository as skill source**

```bash
# Add the repository
claude-mpm skill-source add https://github.com/myorg/skills-repo

# Verify skills discovered
claude-mpm skill-source show skills-repo --skills
```

**Step 3: Remove old collection (optional)**

```bash
# Disable old collection
claude-mpm skills collection-disable old-collection

# Verify new source works
claude-mpm skill-source update skills-repo
```

### Automated Migration Tool

For bulk migration, use the skill-creator tool:

```bash
# Coming soon: automated manifest.json → SKILL.md converter
claude-mpm skills create-from-manifest manifest.json
```

---

## Troubleshooting

### "0 skills discovered" with skill-source

**Symptom**: `claude-mpm skill-source update` shows 0 skills discovered

**Cause**: Repository uses manifest.json format, not SKILL.md format

**Solution**:
1. Check repository structure - does it have SKILL.md files with YAML frontmatter?
2. If it uses manifest.json, use `collection` commands instead
3. Or migrate to SKILL.md format (see [Migration Path](#migration-path))

```bash
# Check what format your repo uses
git clone https://github.com/owner/repo
cd repo
find . -name "SKILL.md"       # skill-source format
find . -name "manifest.json"  # collection format
```

### Private repository access issues

**Symptom**: "Repository not accessible" or HTTP 403 errors

**Cause**: Missing GitHub authentication token

**Solution**: Set GITHUB_TOKEN environment variable

```bash
# Generate token at https://github.com/settings/tokens
export GITHUB_TOKEN=ghp_your_token_here

# Or add to ~/.bashrc / ~/.zshrc
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
source ~/.bashrc

# Verify access
claude-mpm skill-source add https://github.com/owner/private-repo
```

### Skills not loading in Claude Code

**Symptom**: Skills deployed but not appearing in Claude Code

**Cause**: Claude Code only loads skills at startup

**Solution**: Restart Claude Code application

```bash
# macOS
killall "Claude Code" && open -a "Claude Code"

# Linux
pkill -f "claude-code" && claude-code &

# Windows
# Close Claude Code and reopen
```

### Priority conflicts

**Symptom**: Warning about multiple sources with same priority

**Cause**: Two sources configured with same priority number

**Solution**: Adjust priorities to establish precedence

```bash
# List sources with priorities
claude-mpm skill-source list --by-priority

# Update priority
claude-mpm skill-source update custom-repo --priority 150
```

### Collection vs source confusion

**Symptom**: Commands failing or unexpected behavior

**Cause**: Using collection commands for skill-source repos (or vice versa)

**Solution**: Identify repository format first

```bash
# Check repository structure
curl -s https://api.github.com/repos/owner/repo/contents | jq -r '.[].name'

# Look for:
# - manifest.json → use collection commands
# - SKILL.md files → use skill-source commands
```

---

## Quick Reference

### skill-source Commands
```bash
claude-mpm skill-source add <url>
claude-mpm skill-source list
claude-mpm skill-source update [source-id]
claude-mpm skill-source show <source-id> --skills
claude-mpm skill-source enable/disable <source-id>
claude-mpm skill-source remove <source-id>
```

### collection Commands
```bash
claude-mpm skills collection-list
claude-mpm skills collection-add <name> <url>
claude-mpm skills deploy-github [--collection name]
claude-mpm skills collection-enable/disable <name>
claude-mpm skills collection-remove <name>
```

### Configuration Files
- `~/.claude-mpm/config/skill_sources.yaml` - skill-source config
- `~/.claude-mpm/config/skills_collections.yaml` - collection config

### Cache/Deploy Locations
- `~/.claude-mpm/cache/skills/{source}/` - skill-source cache
- `~/.claude-mpm/skills_collections/{name}/` - collection downloads
- `~/.claude/skills/` - Claude Code global skills directory
- `.claude-mpm/skills/` - Project-specific skills (skill-source only)

---

## Related Documentation

- [Skills System Overview](./skills-system.md)
- [Creating Custom Skills](./creating-skills.md)
- [CLI Reference - skill-source](../reference/cli-skill-source.md)
- [CLI Reference - skills](../reference/cli-skills.md)

---

**Last Updated**: 2026-01-17
**Issue Reference**: [#183](https://github.com/bobmatnyc/claude-mpm/issues/183)
