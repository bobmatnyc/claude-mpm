# Claude Code Skills Management Guide

Quick reference for managing skills in Claude Code.

## TL;DR

**Problem**: Skills in `.claude/skills/` are project-specific and need to be copied to each project.

**Solution**: Move skills to `~/.claude/skills/` for **global availability** across all projects.

```bash
# Quick migration (from project root)
./scripts/migrate-skills-to-user.sh

# Restart Claude Code (required for skill discovery)
```

---

## Skill Storage Locations

| Location | Scope | When to Use |
|----------|-------|-------------|
| `~/.claude/skills/` | **User-level** (all projects) | Universal skills you want everywhere |
| `.claude/skills/` | **Project-level** | Project-specific skills to share with team |
| `.claude/skills.local/` | **Local override** | Machine-specific customizations |

---

## Common Operations

### Add Skill to All Projects

```bash
# 1. Create skill directory
mkdir -p ~/.claude/skills/my-new-skill

# 2. Create SKILL.md
cat > ~/.claude/skills/my-new-skill/SKILL.md << 'EOF'
---
name: my-new-skill
description: Brief description of what this skill does
keywords: [keyword1, keyword2]
---

# Skill Instructions

Your skill prompt and instructions here...
EOF

# 3. Restart Claude Code (skills load at startup only!)
```

### Migrate Project Skills to User Level

```bash
# From project root
./scripts/migrate-skills-to-user.sh

# Or manually
cp -r .claude/skills/* ~/.claude/skills/

# Restart Claude Code
```

### Check Which Skills Are Loaded

```bash
# In Claude Code
/skills

# Or check directories
ls -1 ~/.claude/skills/        # User skills
ls -1 .claude/skills/           # Project skills
```

### Remove User Skill

```bash
# Remove skill directory
rm -rf ~/.claude/skills/skill-name

# Restart Claude Code
```

---

## Skill Directory Structure

**Minimal skill** (only SKILL.md required):
```
my-skill/
└── SKILL.md
```

**Full-featured skill**:
```
my-skill/
├── SKILL.md              # Required: Skill prompt and instructions
├── metadata.json         # Optional: Skill metadata
├── scripts/              # Optional: Executable scripts
│   ├── helper.py
│   └── validator.sh
├── references/           # Optional: Reference documentation
│   ├── api-docs.md
│   └── examples.md
└── assets/               # Optional: Templates and files
    └── template.json
```

---

## Important Notes

### ⚠️ Skills Load at Startup ONLY

Skills are NOT dynamically discovered. You MUST restart Claude Code after:
- Adding new skills
- Removing skills
- Modifying skill metadata
- Changing SKILL.md frontmatter

### ✅ Skills Persist Across Sessions

Once skills are in `~/.claude/skills/`, they:
- ✅ Are available in every project
- ✅ Persist across Claude Code restarts
- ✅ Do NOT get overwritten when switching projects
- ❌ Are NOT shared via git (user-specific)

### 📝 settings.json NOT Required

Skills are auto-discovered from directory structure. No configuration needed in `settings.json`.

---

## Troubleshooting

### Skills Not Showing Up

**Check:**
1. ✅ Skill directory exists in `~/.claude/skills/`
2. ✅ `SKILL.md` file exists in skill directory
3. ✅ SKILL.md has valid YAML frontmatter
4. ✅ Claude Code was restarted after adding skill

**Verify:**
```bash
# Check skill exists
ls ~/.claude/skills/my-skill/SKILL.md

# Check YAML frontmatter (first 10 lines)
head -10 ~/.claude/skills/my-skill/SKILL.md

# Should see:
# ---
# name: my-skill
# description: ...
# ---
```

### Duplicate Skills

**Symptom**: Same skill appears twice in `/skills` command

**Cause**: Skill exists in both user and project directories

**Fix**:
```bash
# Remove from project directory (keep user-level)
rm -rf .claude/skills/duplicate-skill-name

# Or remove from user directory (keep project-level)
rm -rf ~/.claude/skills/duplicate-skill-name

# Restart Claude Code
```

### Skills Disappear When Switching Projects

**Cause**: Skills are in `.claude/skills/` (project-level) not `~/.claude/skills/` (user-level)

**Fix**: Run migration script to move to user directory
```bash
./scripts/migrate-skills-to-user.sh
```

---

## Migration Script Reference

### Usage

```bash
# Dry run (preview changes)
./scripts/migrate-skills-to-user.sh --dry-run

# Perform migration
./scripts/migrate-skills-to-user.sh

# Force overwrite existing skills
./scripts/migrate-skills-to-user.sh --force

# Help
./scripts/migrate-skills-to-user.sh --help
```

### What It Does

1. ✅ Creates `~/.claude/skills/` directory if needed
2. ✅ Copies all skills from `.claude/skills/` → `~/.claude/skills/`
3. ✅ Skips skills that already exist (use `--force` to overwrite)
4. ✅ Preserves all skill files (SKILL.md, metadata.json, scripts/, etc.)
5. ✅ Provides summary of migrated/skipped skills

---

## Best Practices

### ✅ DO:

- Store universal skills in `~/.claude/skills/`
- Keep SKILL.md concise (<5,000 words)
- Use references/ for detailed documentation
- Add metadata.json for skill tracking
- Restart Claude Code after skill changes
- Test skills in different projects

### ❌ DON'T:

- Expect skills to load without restarting
- Commit user-level skills to git
- Mix user and project skills in same directory
- Assume settings.json controls skill loading
- Forget to verify skills loaded with `/skills`

---

## Quick Reference

### File Locations

```bash
~/.claude/skills/              # User-level skills (all projects)
.claude/skills/                # Project-level skills (this project only)
~/.claude/settings.json        # User settings (not for skills)
.claude/settings.json          # Project settings (not for skills)
```

### Common Commands

```bash
# List user skills
ls -1 ~/.claude/skills/

# Count skills
ls -1 ~/.claude/skills/ | wc -l

# Check specific skill
cat ~/.claude/skills/skill-name/SKILL.md

# Verify metadata
cat ~/.claude/skills/skill-name/metadata.json

# Migrate project → user
./scripts/migrate-skills-to-user.sh
```

### In Claude Code

```bash
# List all available skills
/skills

# Check if skill is loaded
/skills | grep skill-name

# Get skill help
/help skills
```

---

## Additional Resources

- **Detailed Research**: [`docs/research/claude-code-user-skills-persistence-2025-12-22.md`](/Users/masa/Projects/claude-mpm/docs/research/claude-code-user-skills-persistence-2025-12-22.md)
- **Migration Script**: [`scripts/migrate-skills-to-user.sh`](/Users/masa/Projects/claude-mpm/scripts/migrate-skills-to-user.sh)
- **Official Docs**: [Claude Code Settings](https://code.claude.com/docs/en/settings)
- **Skills Deep Dive**: [Claude Agent Skills](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

---

**Last Updated**: 2025-12-22
