# Skill Parsing Failures - Quick Fix Guide

**Date:** 2025-12-23
**Issue:** 31 skill files failing to parse
**Root Cause:** Schema mismatch and YAML syntax errors

---

## TL;DR

Run these commands to fix all parsing failures:

```bash
# 1. Backup (safety first)
cp -r ~/.claude-mpm/cache/skills ~/.claude-mpm/cache/skills.backup.$(date +%Y%m%d)

# 2. Apply automated fixes
./fix-skill-schema.sh      # Fix 19 files with skill_id → name
./fix-yaml-colons.sh        # Fix 12 files with unquoted colons

# 3. Validate
python3 validate-skills.py  # Should show 100% success rate
```

**Expected Result:** All 31 previously failing skills will now parse successfully.

---

## Two Root Causes

### Issue 1: Missing 'name' Field (19 files)

**Problem:** Skills use `skill_id` instead of required `name` field

**Example:**
```yaml
# ❌ WRONG (old schema)
skill_id: git-workflow

# ✅ CORRECT (required schema)
name: git-workflow
```

**Files Affected:**
- All `universal/` skills using old schema
- Git workflow, TDD, API design, data handling skills

**Fix:** `./fix-skill-schema.sh`

### Issue 2: YAML Syntax Error (12 files)

**Problem:** Unquoted colons in description fields

**Example:**
```yaml
# ❌ WRONG (invalid YAML)
description: Threat modeling: scope, STRIDE analysis

# ✅ CORRECT (quoted string)
description: "Threat modeling: scope, STRIDE analysis"
```

**Files Affected:**
- All `toolchains/` skills with colons in descriptions
- Threat modeling, security scanning, observability skills

**Fix:** `./fix-yaml-colons.sh`

---

## Required Schema

The parser requires these fields:

```yaml
---
name: skill-name                    # REQUIRED
description: "Brief description"    # REQUIRED (quote if has colons)
version: 1.0.0                      # OPTIONAL (default: "1.0.0")
tags: [tag1, tag2]                  # OPTIONAL (default: [])
agent_types: [engineer, qa]         # OPTIONAL (default: None)
---
```

**Important:**
- Use `name`, not `skill_id` (skill_id is auto-generated)
- Use `version`, not `skill_version`
- Quote descriptions containing `:` characters

---

## Manual Fix (Alternative)

If scripts don't work, fix files manually:

### Fix Schema Issues
```bash
# Find files needing schema fix
grep -l "^skill_id:" ~/.claude-mpm/cache/skills/system/*/SKILL.md

# Edit each file and replace:
skill_id: value  →  name: value
skill_version: value  →  version: value
```

### Fix YAML Issues
```bash
# Find files needing YAML fix
grep -E "^description: .*:.*" ~/.claude-mpm/cache/skills/system/*/SKILL.md

# Edit each file and add quotes:
description: text with: colons  →  description: "text with: colons"
```

---

## Rollback (If Needed)

Both scripts create `.bak` backup files:

```bash
# Restore all backups
find ~/.claude-mpm/cache/skills -name "*.bak" -exec bash -c 'mv "$0" "${0%.bak}"' {} \;

# Or restore from full backup
rm -rf ~/.claude-mpm/cache/skills
mv ~/.claude-mpm/cache/skills.backup.YYYYMMDD ~/.claude-mpm/cache/skills
```

---

## Validation

Verify fixes worked:

```bash
# Option 1: Run validation script
python3 validate-skills.py

# Expected output:
# Total skill files found: XX
# Successfully parsed: XX
# Failed to parse: 0
# Success rate: 100.0%
# ✅ SUCCESS: All skills parsed successfully!

# Option 2: Check logs
grep "Successfully parsed skill" ~/.claude-mpm/logs/latest.log | wc -l
# Should be 31 more than before
```

---

## Why These Fixes?

**Parser is correctly strict:**
- YAML spec requires quoting strings with `:` (not a bug)
- Service expects consistent `name` field (not `skill_id`)
- Fixes ensure all skills follow same schema

**Alternative considered:** Relaxing parser validation
**Rejected because:** Creates tech debt, violates YAML spec, doesn't fix root cause

---

## Files Reference

**Research Document:** `docs/research/skill-parsing-failures-2025-12-23.md` (comprehensive analysis)
**Fix Scripts:** `fix-skill-schema.sh`, `fix-yaml-colons.sh`
**Validation:** `validate-skills.py`
**Parser Code:** `src/claude_mpm/services/skills/skill_discovery_service.py`

---

## Affected Skill Files

### Schema Fixes Needed (19)
```
universal/collaboration/git-workflow/SKILL.md
universal/collaboration/stacked-prs/SKILL.md
universal/collaboration/git-worktrees/SKILL.md
universal/web/web-performance-optimization/SKILL.md
universal/web/api-design-patterns/SKILL.md
universal/web/api-documentation/SKILL.md
universal/testing/test-driven-development/SKILL.md
universal/data/xlsx/SKILL.md
universal/data/database-migration/SKILL.md
universal/data/json-data-handling/SKILL.md
toolchains/universal/infrastructure/github-actions/SKILL.md
(+ 8 more toolchain files)
```

### YAML Fixes Needed (12)
```
universal/security/threat-modeling/SKILL.md
universal/security/security-scanning/SKILL.md
toolchains/universal/observability/opentelemetry/SKILL.md
toolchains/universal/infrastructure/terraform/SKILL.md
toolchains/universal/orchestration/kubernetes/SKILL.md
toolchains/elixir/deployment/phoenix-ops/SKILL.md
toolchains/golang/networking/grpc/SKILL.md
toolchains/golang/concurrency/SKILL.md
toolchains/typescript/frameworks/fastify/SKILL.md
toolchains/rust/cli/clap/SKILL.md
toolchains/rust/web/axum/SKILL.md
toolchains/javascript/testing/cypress/SKILL.md
```

---

## Questions?

See full analysis in `docs/research/skill-parsing-failures-2025-12-23.md`
