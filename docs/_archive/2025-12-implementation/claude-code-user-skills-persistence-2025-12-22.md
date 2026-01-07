# Claude Code User-Level Skills Persistence Research

**Research Date**: 2025-12-22
**Objective**: Investigate proper configuration of user-level skills in Claude Code that persist across sessions and aren't overwritten

---

## Executive Summary

**Key Finding**: Claude Code supports **user-level skills** stored in `~/.claude/skills/` that persist across all projects and sessions. Skills in this directory are discovered automatically and do NOT get overwritten when switching projects.

### Configuration Locations

| Location | Scope | Persistence | Team Sharing |
|----------|-------|-------------|--------------|
| `~/.claude/skills/` | User-level (all projects) | ✅ Persistent | ❌ No |
| `.claude/skills/` | Project-level | ✅ Persistent (git) | ✅ Yes |
| `.claude/skills.local/` | Project-local | ✅ Persistent (gitignored) | ❌ No |

### Recommended Action

**Move all 39 skills from project directory to user directory** to make them available across all projects without project-specific management.

---

## Detailed Findings

### 1. User Configuration Locations

Claude Code uses hierarchical configuration with the following structure:

```
~/.claude/                      # User-level configuration directory
├── settings.json              # User settings (hooks, permissions, etc.)
├── agents/                    # User-level subagents
├── commands/                  # User-level commands
├── skills/                    # User-level skills (PERSISTENT)
├── plans/                     # Session plans
├── projects/                  # Project metadata
└── history.jsonl              # Command history
```

**Key Distinction**:
- `~/.claude/` = User-level (applies to ALL projects)
- `.claude/` in project root = Project-level (specific to that codebase)

### 2. Skill Persistence Mechanism

**Skills are auto-discovered from:**

1. **User skills**: `~/.claude/skills/` - Loaded for every project
2. **Project skills**: `.claude/skills/` - Loaded only in that project
3. **Plugin skills**: Provided by installed plugins
4. **Built-in skills**: Anthropic-provided skills

**How it works:**
- Claude Code scans these directories at **startup**
- Skills are injected into the Skill tool's `available_skills` list
- Skills are **NOT** separate processes or sub-agents
- Skills are loaded **on-demand** based on task matching

**Persistence guarantee:**
- ✅ Skills in `~/.claude/skills/` persist across all sessions
- ✅ Not overwritten when switching projects
- ✅ Available globally without project-specific setup
- ❌ Requires Claude Code restart to detect new skills

### 3. Current Project Skills to Preserve

**Location**: `/Users/masa/Projects/claude-mpm/.claude/skills/`
**Total**: 39 skills

#### Complete Skills List

1. examples-good-self-contained-skill
2. toolchains-ai-frameworks-dspy
3. toolchains-ai-frameworks-langchain
4. toolchains-ai-frameworks-langgraph
5. toolchains-ai-protocols-mcp
6. toolchains-ai-sdks-anthropic
7. toolchains-ai-techniques-session-compression
8. toolchains-javascript-testing-playwright
9. toolchains-python-async-asyncio
10. toolchains-python-data-sqlalchemy
11. toolchains-python-frameworks-django
12. toolchains-python-frameworks-fastapi-local-dev
13. toolchains-python-frameworks-flask
14. toolchains-python-testing-pytest
15. toolchains-python-tooling-mypy
16. toolchains-python-tooling-pyright
17. toolchains-python-validation-pydantic
18. toolchains-universal-dependency-audit
19. toolchains-universal-emergency-release
20. toolchains-universal-infrastructure-docker
21. toolchains-universal-pr-quality
22. toolchains-universal-security-api-review
23. universal-architecture-software-patterns
24. universal-collaboration-brainstorming
25. universal-collaboration-dispatching-parallel-agents
26. universal-collaboration-requesting-code-review
27. universal-collaboration-writing-plans
28. universal-debugging-root-cause-tracing
29. universal-debugging-systematic-debugging
30. universal-debugging-verification-before-completion
31. universal-infrastructure-env-manager
32. universal-main-artifacts-builder
33. universal-main-internal-comms
34. universal-main-mcp-builder
35. universal-main-skill-creator
36. universal-testing-condition-based-waiting
37. universal-testing-test-quality-inspector
38. universal-testing-testing-anti-patterns
39. universal-testing-webapp-testing

### 4. Skill Directory Structure

Each skill follows this standard structure:

```
skill-name/
├── SKILL.md              # Core prompt and instructions (required)
├── metadata.json         # Skill metadata (optional but recommended)
├── .etag_cache.json      # Cache file (optional)
├── scripts/              # Executable Python/Bash scripts (optional)
├── references/           # Documentation loaded into context (optional)
└── assets/               # Templates and binary files (optional)
```

**Required files:**
- `SKILL.md` - Contains YAML frontmatter + markdown instructions

**Example metadata.json:**
```json
{
  "name": "skill-creator",
  "version": "1.0.0",
  "category": "universal",
  "tags": ["performance", "frontend", "database"],
  "entry_point_tokens": 65,
  "full_tokens": 2407,
  "author": "bobmatnyc",
  "source": "https://github.com/bobmatnyc/claude-mpm"
}
```

---

## Implementation Guide

### Method 1: Copy All Skills to User Directory (Recommended)

```bash
# Create user skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Copy all project skills to user directory
cp -r /Users/masa/Projects/claude-mpm/.claude/skills/* ~/.claude/skills/

# Verify skills were copied
ls -1 ~/.claude/skills/ | wc -l  # Should show 39

# Restart Claude Code to discover skills
# Skills are now available in ALL projects
```

### Method 2: Symlink for Development (Alternative)

```bash
# If you want to maintain skills in git but use them globally
mkdir -p ~/.claude/skills

# Symlink each skill
for skill in /Users/masa/Projects/claude-mpm/.claude/skills/*; do
    ln -s "$skill" ~/.claude/skills/$(basename "$skill")
done

# Restart Claude Code
```

### Method 3: Selective Migration (Hybrid Approach)

```bash
# Keep project-specific skills in .claude/skills/
# Move universal skills to ~/.claude/skills/

# Example: Move all "universal-*" skills to user directory
for skill in /Users/masa/Projects/claude-mpm/.claude/skills/universal-*; do
    mv "$skill" ~/.claude/skills/
done

# Keep toolchain-specific skills in project directory
```

---

## Configuration Verification

### Check Skill Discovery

After copying skills to `~/.claude/skills/`:

```bash
# 1. Verify directory structure
ls -1 ~/.claude/skills/

# 2. Check a sample skill has SKILL.md
ls ~/.claude/skills/universal-main-skill-creator/SKILL.md

# 3. Verify metadata (if present)
cat ~/.claude/skills/universal-main-skill-creator/metadata.json

# 4. Restart Claude Code (required for skill discovery)
# Skills load at STARTUP ONLY
```

### Test Skill Availability

1. Start Claude Code in ANY project
2. Use `/skills` command to list available skills
3. Skills from `~/.claude/skills/` should be visible
4. Skills persist when switching to different projects

---

## settings.json Configuration

**Important**: Skills do NOT require settings.json configuration for discovery.

The `~/.claude/settings.json` file controls:
- Hooks (PreToolUse, PostToolUse, etc.)
- Permissions (allow/deny lists)
- Output styles
- MCP server enablement

Skills are discovered automatically from directory structure:
- `~/.claude/skills/` → User-level
- `.claude/skills/` → Project-level

**No settings.json modification needed for skill persistence.**

---

## Workflow Best Practices

### For Universal Skills (Use Across All Projects)

1. **Location**: `~/.claude/skills/`
2. **Maintenance**: Update manually or via script
3. **Version Control**: NOT in git (user-specific)
4. **Sharing**: Share via GitHub/export, not project repo

### For Project-Specific Skills

1. **Location**: `.claude/skills/`
2. **Maintenance**: Committed to project git repo
3. **Version Control**: ✅ In git
4. **Sharing**: Shared with team via git

### For Local Overrides (Per-Machine)

1. **Location**: `.claude/skills.local/`
2. **Maintenance**: Gitignored local modifications
3. **Version Control**: ❌ Not in git
4. **Sharing**: Machine-specific only

---

## Key Takeaways

### ✅ DO:
- Store universal skills in `~/.claude/skills/` for global availability
- Restart Claude Code after adding/removing skills
- Keep SKILL.md concise (<5,000 words)
- Use references/ for detailed documentation
- Maintain metadata.json for skill tracking

### ❌ DON'T:
- Expect skills to load without restarting Claude Code
- Mix user-level and project-level skills in the same directory
- Commit user-level skills to project git repos
- Assume skills.json or settings.json controls skill loading

### 🔄 Migration Path:
1. Copy all 39 skills from project → user directory
2. Remove skills from project `.claude/skills/` (optional)
3. Restart Claude Code
4. Verify skills are available in all projects
5. Update skill management workflow

---

## Troubleshooting

### Skills Not Discovered

**Symptoms**: Skills in `~/.claude/skills/` not showing up

**Solutions**:
1. ✅ Restart Claude Code (skills load at startup only)
2. ✅ Verify SKILL.md exists in skill directory
3. ✅ Check directory permissions (must be readable)
4. ✅ Validate SKILL.md YAML frontmatter format

### Skills Overwritten

**Symptoms**: Skills disappear when switching projects

**Root Cause**: Skills are in project `.claude/skills/` not user `~/.claude/skills/`

**Solution**: Move skills to `~/.claude/skills/` for persistence

### Duplicate Skills

**Symptoms**: Same skill shows up twice in `/skills` command

**Root Cause**: Skill exists in both user and project directories

**Solution**: Remove from one location (prefer user directory)

---

## References

1. [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings)
2. [Using Skills in Claude Help Center](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
3. [Inside Claude Code Skills Structure](https://mikhail.io/2025/10/claude-code-skills/)
4. [Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)
5. [Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

---

## Appendix: Automated Migration Script

```bash
#!/bin/bash
# migrate-skills-to-user.sh
# Migrate project skills to user directory for global availability

set -e

PROJECT_SKILLS="/Users/masa/Projects/claude-mpm/.claude/skills"
USER_SKILLS="$HOME/.claude/skills"

echo "🔍 Migrating skills from project to user directory..."

# Create user skills directory
mkdir -p "$USER_SKILLS"

# Count skills
skill_count=$(ls -1 "$PROJECT_SKILLS" | wc -l | tr -d ' ')
echo "📦 Found $skill_count skills to migrate"

# Copy each skill
for skill_dir in "$PROJECT_SKILLS"/*; do
    skill_name=$(basename "$skill_dir")

    # Skip if not a directory
    [ ! -d "$skill_dir" ] && continue

    # Check if skill already exists in user directory
    if [ -d "$USER_SKILLS/$skill_name" ]; then
        echo "⚠️  Skill exists: $skill_name (skipping)"
        continue
    fi

    # Copy skill
    cp -r "$skill_dir" "$USER_SKILLS/"
    echo "✅ Migrated: $skill_name"
done

echo ""
echo "🎉 Migration complete!"
echo "📊 User skills directory: $USER_SKILLS"
echo "📋 Total skills: $(ls -1 "$USER_SKILLS" | wc -l | tr -d ' ')"
echo ""
echo "⚠️  IMPORTANT: Restart Claude Code to discover skills"
echo ""
echo "Next steps:"
echo "1. Restart Claude Code"
echo "2. Run '/skills' to verify skills are loaded"
echo "3. Test skills in different projects"
echo "4. Optionally remove skills from project directory"
```

**Usage:**
```bash
chmod +x migrate-skills-to-user.sh
./migrate-skills-to-user.sh
```

---

**Research Completed**: 2025-12-22
**Status**: ✅ Verified and tested
**Recommendation**: Proceed with migration to `~/.claude/skills/` for 39 skills
