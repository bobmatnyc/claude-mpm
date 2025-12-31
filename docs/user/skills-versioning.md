# Skills Versioning Guide

Complete guide to versioning skills in Claude MPM.

## Table of Contents

- [What is Skills Versioning?](#what-is-skills-versioning)
- [Version Format](#version-format)
- [Skill Frontmatter](#skill-frontmatter)
- [Creating Versioned Skills](#creating-versioned-skills)
- [Semantic Versioning for Skills](#semantic-versioning-for-skills)
- [Checking Skill Versions](#checking-skill-versions)
- [Best Practices](#best-practices)
- [Examples](#examples)

## What is Skills Versioning?

Skills versioning allows you to track and manage the evolution of your skills over time. Each skill can have:
- **Version number** - Semantic version (e.g., `0.1.0`, `1.2.3`)
- **Skill ID** - Unique identifier derived from filename
- **Updated timestamp** - Last modification date
- **Tags** - Keywords for categorization

**Benefits:**
- Track skill changes over time
- Know which version of a skill you're using
- Maintain compatibility across projects
- Document skill evolution
- Share skills with version information

## Version Format

Skills use **semantic versioning** (SemVer):

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ Bug fixes, typos, minor clarifications
  │     └─────── New features, additional guidance
  └───────────── Breaking changes, major rewrites
```

**Examples:**
- `0.1.0` - Initial version (development)
- `1.0.0` - First stable release
- `1.1.0` - Added new features
- `1.1.1` - Fixed typos
- `2.0.0` - Breaking changes

## Skill Frontmatter

Skills use YAML frontmatter to store version information and metadata:

```markdown
---
skill_id: test-driven-development
skill_version: 0.1.0
updated_at: 2025-10-30
tags:
  - testing
  - tdd
  - quality
---

# Test-Driven Development

Your skill content goes here...
```

### Frontmatter Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `skill_id` | Yes | Unique identifier (kebab-case) | `test-driven-development` |
| `skill_version` | Yes | Semantic version number | `0.1.0` |
| `updated_at` | No | Last update date (YYYY-MM-DD) | `2025-10-30` |
| `tags` | No | List of keywords | `[testing, tdd, quality]` |

### Backward Compatibility

**Skills without frontmatter still work!** If a skill doesn't have frontmatter:
- Version defaults to `"unknown"`
- Skill ID is generated from filename
- No tags or updated date
- Full backward compatibility maintained

## Creating Versioned Skills

### Step 1: Add Frontmatter

Start your skill file with YAML frontmatter:

```markdown
---
skill_id: my-awesome-skill
skill_version: 0.1.0
updated_at: 2025-10-30
tags:
  - category1
  - category2
---

# My Awesome Skill

Skill content starts after the frontmatter...
```

### Step 2: Write Your Content

After the frontmatter, write your skill content as usual:

```markdown
---
skill_id: my-awesome-skill
skill_version: 0.1.0
---

# My Awesome Skill

## Purpose

This skill provides guidance on...

## Key Principles

1. Principle one
2. Principle two

## Examples

```python
# Example code
```
\```

### Step 3: Version Your Changes

When you update the skill, increment the version:

```markdown
---
skill_id: my-awesome-skill
skill_version: 0.2.0  # ← Incremented from 0.1.0
updated_at: 2025-11-15  # ← Updated date
tags:
  - category1
  - category2
  - new-tag  # ← Added new tag
---

# My Awesome Skill (Updated!)

New content and improvements...
```

## Semantic Versioning for Skills

### When to Bump MAJOR (X.0.0)

Use MAJOR version for **breaking changes**:
- Complete skill rewrite
- Fundamental approach change
- Incompatible with previous version
- Different methodology

**Example:** `1.5.2` → `2.0.0`

```markdown
---
skill_id: debugging-guide
skill_version: 2.0.0  # ← MAJOR bump
updated_at: 2025-11-01
---

# Debugging Guide (Complete Rewrite)

This version completely changes the debugging approach...
```

### When to Bump MINOR (x.Y.0)

Use MINOR version for **new features**:
- Added new sections
- Additional guidance
- New examples
- Extended functionality
- Backward compatible additions

**Example:** `1.5.2` → `1.6.0`

```markdown
---
skill_id: debugging-guide
skill_version: 1.6.0  # ← MINOR bump
updated_at: 2025-10-30
---

# Debugging Guide

## New: Advanced Memory Debugging (Added in 1.6.0)

This section provides new guidance on memory debugging...
```

### When to Bump PATCH (x.y.Z)

Use PATCH version for **bug fixes**:
- Fixed typos
- Corrected errors
- Minor clarifications
- Updated examples
- Documentation improvements

**Example:** `1.5.2` → `1.5.3`

```markdown
---
skill_id: debugging-guide
skill_version: 1.5.3  # ← PATCH bump
updated_at: 2025-10-30
---

# Debugging Guide

Fixed typos and clarified examples throughout...
```

### Development Versions (0.x.y)

Use `0.x.y` versions for **development/preview**:
- Skill is still evolving
- Not yet stable
- Breaking changes may occur
- Experimental features

**Example:** `0.1.0`, `0.2.0`, `0.5.1`

Once stable, release as `1.0.0`.

## Checking Skill Versions

### Using /mpm-version Command

Check all skill versions with the `/mpm-version` command:

```bash
/mpm-version
```

**Output:**

```
Claude MPM Version Information
==============================

Project Version: 4.16.3
Build: 481

Skills (20 total)
-----------------

Bundled Skills (20):
  ├─ test-driven-development (0.1.0)
  ├─ systematic-debugging (0.1.0)
  ├─ async-testing (0.1.0)
  ├─ performance-profiling (0.1.0)
  └─ ... (16 more)

User Skills (2):
  ├─ my-custom-skill (1.0.0)
  └─ project-helper (0.3.0)

Project Skills (1):
  └─ domain-expert (2.1.0)

Summary
-------
• Project: v5.4.68
• Skills: 23 total (20 bundled, 2 user, 1 project)
```

### Skills Locations

Skills are loaded from three locations:

| Location | Path | Source | Use Case |
|----------|------|--------|----------|
| **Bundled** | `src/claude_mpm/skills/bundled/` | Built-in | Core skills |
| **User** | `~/.claude/skills/` | User-global | Personal skills |
| **Project** | `.claude/skills/` | Project-specific | Project skills |

## Best Practices

### ✅ Do's

1. **Start with 0.1.0** for new skills
2. **Use semantic versioning** consistently
3. **Update the date** when changing version
4. **Document breaking changes** in MAJOR versions
5. **Keep skill_id stable** (don't change it)
6. **Add meaningful tags** for discoverability
7. **Test skills** before bumping version
8. **Document version history** in skill content

### ❌ Don'ts

1. **Don't skip versions** (0.1.0 → 0.3.0 ❌)
2. **Don't change skill_id** after creation
3. **Don't use arbitrary versions** (1.0.5a-beta ❌)
4. **Don't bump MAJOR** for minor changes
5. **Don't forget to update** `updated_at` field
6. **Don't leave outdated** version info

### Versioning Workflow

```bash
# 1. Edit skill file
vim .claude/skills/my-skill.md

# 2. Update frontmatter
---
skill_id: my-skill
skill_version: 1.2.0  # ← Incremented
updated_at: 2025-10-30  # ← Updated
---

# 3. Commit changes
git add .claude/skills/my-skill.md
git commit -m "feat: add new section to my-skill (v1.2.0)"

# 4. Verify version
/mpm-version
```

## Examples

### Example 1: Initial Skill Creation

**File:** `.claude/skills/api-testing.md`

```markdown
---
skill_id: api-testing
skill_version: 0.1.0
updated_at: 2025-10-30
tags:
  - testing
  - api
  - rest
---

# API Testing Skill

## Purpose

Provides guidance on testing REST APIs...

## Key Techniques

1. Request validation
2. Response assertions
3. Error handling

## Examples

\```python
def test_api_endpoint():
    response = client.get("/api/users")
    assert response.status_code == 200
\```
```

### Example 2: Adding Features (MINOR Bump)

**File:** `.claude/skills/api-testing.md` (updated)

```markdown
---
skill_id: api-testing
skill_version: 0.2.0  # ← MINOR bump (new features)
updated_at: 2025-11-15
tags:
  - testing
  - api
  - rest
  - graphql  # ← New tag
---

# API Testing Skill

## Purpose

Provides guidance on testing REST and GraphQL APIs...

## Key Techniques

1. Request validation
2. Response assertions
3. Error handling
4. **GraphQL query testing** (NEW in 0.2.0)

## GraphQL Testing Examples (NEW)

\```python
def test_graphql_query():
    query = "{ users { id name } }"
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200
\```
```

### Example 3: Bug Fixes (PATCH Bump)

**File:** `.claude/skills/api-testing.md` (updated)

```markdown
---
skill_id: api-testing
skill_version: 0.2.1  # ← PATCH bump (bug fixes)
updated_at: 2025-11-20
tags:
  - testing
  - api
  - rest
  - graphql
---

# API Testing Skill

Fixed typos and corrected code examples throughout this document.

## Purpose

Provides guidance on testing REST and GraphQL APIs...
```

### Example 4: Breaking Changes (MAJOR Bump)

**File:** `.claude/skills/api-testing.md` (rewritten)

```markdown
---
skill_id: api-testing
skill_version: 1.0.0  # ← MAJOR bump (breaking changes)
updated_at: 2025-12-01
tags:
  - testing
  - api
  - rest
  - graphql
  - modern
---

# API Testing Skill (Version 1.0)

**⚠️ BREAKING CHANGES:** This version adopts a completely new testing framework
and methodology. Previous examples using the old framework will not work.

## New Testing Approach

This skill now uses the modern `httpx` async client...
```

### Example 5: Legacy Skill (No Frontmatter)

**File:** `.claude/skills/old-skill.md` (legacy)

```markdown
# Old Skill (Legacy Format)

This skill has no frontmatter, but still works!

Claude MPM will:
- Generate skill_id from filename: "old-skill"
- Set version to "unknown"
- Load and use normally

Consider adding frontmatter for version tracking.
```

## Related Documentation

- **[User Guide](user-guide.md)** - Complete user documentation
- **[Developer Guide](../developer/skills-versioning.md)** - Technical implementation details
- **[Skills System](user-guide.md#skills-system)** - Skills overview
- **[/mpm-version Command](../../src/claude_mpm/commands/mpm-version.md)** - Version checking

---

**Next Steps:**
1. Create your first versioned skill
2. Use `/mpm-version` to check versions
3. Establish versioning conventions for your team
4. Document version history in your skills
