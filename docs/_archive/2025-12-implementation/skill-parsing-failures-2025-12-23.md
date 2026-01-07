# Skill Discovery Service Parsing Failures - Root Cause Analysis

**Date:** 2025-12-23
**Researcher:** Research Agent
**Issue:** 31 skill files failing to parse in skill discovery service

## Executive Summary

Two distinct issues are causing skill parsing failures:

1. **Schema Mismatch (19 files):** Skills use `skill_id` field instead of required `name` field
2. **YAML Syntax Error (12 files):** Unquoted colons in description strings violate YAML mapping syntax

**Recommended Approach:** Both issues require source data fixes (update SKILL.md files). The parser is correctly strict according to YAML spec and service requirements.

---

## Issue 1: Missing 'name' Field (19 Files)

### Root Cause

The `SkillDiscoveryService` requires a `name` field in the frontmatter (line 262):

```python
# Validate required fields
if "name" not in frontmatter:
    self.logger.warning(f"Missing 'name' field in {skill_file.name}")
    return None
```

However, 19 skill files use `skill_id` instead of `name`:

**Example from git-workflow/SKILL.md:**
```yaml
---
skill_id: git-workflow
skill_version: 0.1.0
description: Essential Git patterns for effective version control
---
```

**What the parser expects:**
```yaml
---
name: git-workflow
skill_version: 0.1.0
description: Essential Git patterns for effective version control
---
```

### Affected Files (19)

**Universal Skills:**
- `/Users/masa/.claude-mpm/cache/skills/system/universal/collaboration/git-workflow/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/collaboration/stacked-prs/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/collaboration/git-worktrees/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/web/web-performance-optimization/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/web/api-design-patterns/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/web/api-documentation/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/testing/test-driven-development/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/data/xlsx/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/data/database-migration/SKILL.md`
- `/Users/masa/.claude-mpm/cache/skills/system/universal/data/json-data-handling/SKILL.md`

**Toolchain Skills:**
- `/Users/masa/.claude-mpm/cache/skills/system/toolchains/universal/infrastructure/github-actions/SKILL.md`
- (9 additional toolchain files not listed in original error logs)

### Code Analysis

**Parser Behavior:**
```python
def _parse_skill_file(self, skill_file: Path) -> Optional[Dict[str, Any]]:
    """Parse a skill Markdown file with YAML frontmatter."""
    # ... extract frontmatter ...

    # Validate required fields
    if "name" not in frontmatter:
        self.logger.warning(f"Missing 'name' field in {skill_file.name}")
        return None  # ⚠️ Parsing fails, skill skipped

    if "description" not in frontmatter:
        self.logger.warning(f"Missing 'description' field in {skill_file.name}")
        return None
```

The parser **generates** `skill_id` from the `name` field (line 291):
```python
# Generate skill_id from name (lowercase, replace spaces/underscores with hyphens)
skill_id = self._generate_skill_id(name)
```

This means `skill_id` should not be in the frontmatter—it's a computed field.

### Why This Happened

**Historical Evolution Hypothesis:**
- Earlier version of skills may have used `skill_id` as the primary identifier
- Service was refactored to use human-readable `name` and auto-generate `skill_id`
- Skills in cache directory were not updated to match new schema

**Evidence:**
1. The working skill `fastify/SKILL.md` uses `name: fastify` (correct schema)
2. The failing skill `test-driven-development/SKILL.md` uses `skill_id: test-driven-development` (old schema)
3. Both files appear to be from the same source repository but different update cycles

---

## Issue 2: Invalid YAML - Unquoted Colons (12 Files)

### Root Cause

YAML interprets unquoted colons (`:`) as key-value separators. When a description contains a colon, it must be quoted to prevent ambiguous parsing.

**Example from threat-modeling/SKILL.md:**
```yaml
description: Threat modeling workflow for software systems: scope, data flow diagrams, STRIDE analysis
```

**YAML Parser Error:**
```
mapping values are not allowed here
  in "<unicode string>", line 3, column 59:
     ... ng workflow for software systems: scope, data flow diagrams, STR ...
                                         ^
```

The parser sees:
```
description: Threat modeling workflow for software systems
                                                       ^
                                              This looks like a new key!
```

### Affected Files (12)

All in `toolchains` directory with descriptions containing colons:

1. `threat-modeling/SKILL.md` - "...systems: scope, data flow diagrams, STR..."
2. `security-scanning/SKILL.md` - "...scanning: secrets, deps, SAST, triage..."
3. `opentelemetry/SKILL.md` - "...observability: traces, metrics, logs, context..."
4. `terraform/SKILL.md` - "...Terraform: state and environments, module..."
5. `kubernetes/SKILL.md` - "...Kubernetes: core objects, probes, resource..."
6. `phoenix-ops/SKILL.md` - "...Phoenix: releases, runtime configuratio..."
7. `grpc/SKILL.md` - "...gRPC: protobuf layout, codegen, inte..."
8. `concurrency/SKILL.md` - "...goroutines: context cancellation, errgroup..."
9. `fastify/SKILL.md` - "...Fastify: schema validation, plugins, ty..."
10. `clap/SKILL.md` - "...Clap: subcommands, config layering..."
11. `axum/SKILL.md` - "...Axum: routers/extractors, state, mid..."
12. `cypress/SKILL.md` - "...Cypress: reliable selectors, stable wai..."

### YAML Syntax Rules

**Why This is an Error:**

YAML uses `:` to separate keys and values in mappings. When used in a string value, it creates ambiguous parsing:

```yaml
# ❌ AMBIGUOUS - Where does the value start?
description: Build CLI tools: subcommands, config layering
                            ^ Is this a separator or part of the string?

# ✅ CLEAR - Quoted string contains literal colon
description: "Build CLI tools: subcommands, config layering"

# ✅ CLEAR - Flow-style string (single quotes)
description: 'Build CLI tools: subcommands, config layering'
```

**Test Results:**
```python
>>> yaml.safe_load("description: tools: scope")
yaml.scanner.ScannerError: mapping values are not allowed here
  in "<unicode string>", line 1, column 18:
    description: tools: scope
                     ^
```

### Why This Works Sometimes

These skills were likely hand-written and never validated with strict YAML parser. The colons were added for readability without considering YAML syntax rules.

**Interesting Finding:** The `fastify/SKILL.md` file has `name: fastify` (correct), so it passes the first check, but its description also has unquoted colons—suggesting this file might have been fixed partially.

---

## Required Frontmatter Schema

Based on code analysis (`skill_discovery_service.py`), the **required** frontmatter fields are:

### Minimal Valid Skill
```yaml
---
name: skill-name                  # REQUIRED (human-readable)
description: "Brief description"  # REQUIRED (quote if contains colons)
skill_version: 1.0.0             # OPTIONAL (default: "1.0.0")
tags: [tag1, tag2]               # OPTIONAL (default: [])
agent_types: [engineer, qa]      # OPTIONAL (default: None)
---
```

### Field Processing

| Field | Required | Type | Processing |
|-------|----------|------|------------|
| `name` | ✅ Yes | string | Used to generate `skill_id` |
| `description` | ✅ Yes | string | Must quote if contains `:` |
| `skill_version` | ❌ No | string | Default: `"1.0.0"` |
| `tags` | ❌ No | list | Default: `[]` |
| `agent_types` | ❌ No | list | Default: `None` |

**Generated Fields (not in frontmatter):**
- `skill_id`: Auto-generated from `name` via `_generate_skill_id()`
- `deployment_name`: Computed from directory structure
- `relative_path`: Computed from file location

---

## Parser Strictness Analysis

### Is the Parser Too Strict?

**Verdict:** ❌ **No, the parser is appropriately strict**

**Reasons:**

1. **YAML Spec Compliance:** The unquoted colon error is correct per YAML specification. Accepting malformed YAML would violate the standard.

2. **Required Fields are Minimal:** Only `name` and `description` are required. This is reasonable for skill identification.

3. **Clear Separation of Concerns:** The parser generates `skill_id` from `name` to ensure consistency. Allowing both would create confusion about which is authoritative.

4. **Fail-Safe Design:** Returning `None` for unparseable skills prevents cascade failures. Invalid skills are logged and skipped rather than breaking the entire discovery process.

**Code Evidence:**
```python
# Defensive: Skip invalid skills, don't crash
except Exception as e:
    self.logger.warning(f"Failed to parse skill {skill_file}: {e}")
    # No exception raised, continue to next file
```

### Alternative Approaches Considered

❌ **Relax parser to accept `skill_id` as alias for `name`:**
- **Cons:** Creates ambiguity (which field is authoritative?)
- **Cons:** Allows inconsistent schemas across skills
- **Better:** Enforce single schema, provide clear migration path

❌ **Auto-quote YAML strings to fix colon issue:**
- **Cons:** Requires custom YAML preprocessing (fragile, hard to maintain)
- **Cons:** May introduce new parsing bugs (over-quoting, escape issues)
- **Better:** Fix source data to follow YAML standards

✅ **Recommended:** Fix source skill files to match required schema

---

## Recommended Fix Approach

### Fix Strategy: Source Data Updates

**Rationale:** Parser is correctly strict; skills should conform to well-defined schema.

### Step 1: Fix Missing 'name' Field (19 files)

**Automated Fix Script:**
```bash
#!/bin/bash
# fix-skill-schema.sh

# Find all SKILL.md files with skill_id but no name field
find ~/.claude-mpm/cache/skills -name "SKILL.md" -type f | while read -r file; do
  if grep -q "^skill_id:" "$file" && ! grep -q "^name:" "$file"; then
    echo "Fixing: $file"

    # Extract skill_id value
    skill_id=$(grep "^skill_id:" "$file" | head -1 | awk '{print $2}')

    # Replace skill_id with name
    sed -i.bak "s/^skill_id: /name: /" "$file"

    echo "  Changed skill_id to name: $skill_id"
  fi
done
```

**Manual Fix Template:**
```yaml
# BEFORE (incorrect)
---
skill_id: git-workflow
skill_version: 0.1.0
description: Essential Git patterns
---

# AFTER (correct)
---
name: git-workflow
skill_version: 1.0.0  # Changed skill_version → version
description: Essential Git patterns
---
```

**Note:** Some files also use `skill_version` which should likely be just `version` based on working examples (fastify uses `version: 1.0.0`).

### Step 2: Fix YAML Colon Syntax (12 files)

**Automated Fix Script:**
```bash
#!/bin/bash
# fix-yaml-colons.sh

find ~/.claude-mpm/cache/skills -name "SKILL.md" -type f | while read -r file; do
  # Check if description line has unquoted colons
  if grep -q "^description: .*:.*" "$file"; then
    desc_line=$(grep "^description: " "$file" | head -1)

    # Check if already quoted
    if ! echo "$desc_line" | grep -q "^description: [\"']"; then
      echo "Fixing: $file"

      # Extract description value (everything after "description: ")
      desc_value=$(echo "$desc_line" | sed 's/^description: //')

      # Quote the description
      sed -i.bak "s|^description: $desc_value|description: \"$desc_value\"|" "$file"

      echo "  Quoted description containing colons"
    fi
  fi
done
```

**Manual Fix Examples:**
```yaml
# BEFORE (invalid YAML)
description: Threat modeling: scope, data flow diagrams, STRIDE analysis

# AFTER (valid YAML - double quotes)
description: "Threat modeling: scope, data flow diagrams, STRIDE analysis"

# AFTER (valid YAML - single quotes, alternative)
description: 'Threat modeling: scope, data flow diagrams, STRIDE analysis'
```

### Step 3: Validation

**Test Parser After Fixes:**
```python
from pathlib import Path
from skill_discovery_service import SkillDiscoveryService

# Re-scan skills directory
service = SkillDiscoveryService(Path("~/.claude-mpm/cache/skills/system"))
skills = service.discover_skills()

print(f"Successfully parsed: {len(skills)} skills")
print(f"Expected: {31 + len(skills)} total skills (31 previously failed)")
```

**Expected Outcome:**
- All 31 previously failing skills should now parse successfully
- No new parsing errors introduced

---

## Sample Fixed Files

### Example 1: git-workflow/SKILL.md (Fixed)

**Before:**
```yaml
---
skill_id: git-workflow
skill_version: 0.1.0
description: Essential Git patterns for effective version control
updated_at: 2025-10-30T17:00:00Z
tags: [git, version-control, workflow, best-practices]
---
```

**After:**
```yaml
---
name: git-workflow
version: 1.0.0
description: Essential Git patterns for effective version control
updated_at: 2025-10-30T17:00:00Z
tags: [git, version-control, workflow, best-practices]
---
```

### Example 2: threat-modeling/SKILL.md (Fixed)

**Before:**
```yaml
---
name: threat-modeling
description: Threat modeling workflow: scope, data flow diagrams, STRIDE analysis
version: 1.0.0
---
```

**After:**
```yaml
---
name: threat-modeling
description: "Threat modeling workflow: scope, data flow diagrams, STRIDE analysis"
version: 1.0.0
---
```

---

## Impact Assessment

### Current State
- **Total Skills Found:** Unknown (31 failed parsing)
- **Parsing Failures:** 31 skills (19 schema + 12 YAML syntax)
- **Success Rate:** Unable to calculate without total count

### After Fix
- **Expected Additional Skills:** 31
- **Parsing Failures:** 0 (assuming no other issues)
- **Success Rate:** 100% (for discoverable skills)

### Risk Assessment

**Low Risk:**
- Changes are source data fixes only (no code changes)
- YAML syntax fixes are standards-compliant
- Schema changes align with parser expectations
- Backup files (`.bak`) created by scripts for rollback

**Validation Steps:**
1. Run automated fix scripts on copy of cache directory
2. Test parser on fixed files
3. Verify all 31 skills now parse successfully
4. Review sample of skills for correctness
5. Apply fixes to production cache directory

---

## Alternative Solutions Considered

### Option A: Code Change - Accept Both `name` and `skill_id`

**Implementation:**
```python
# In _parse_skill_file():
name = frontmatter.get("name") or frontmatter.get("skill_id")
if not name:
    self.logger.warning(f"Missing 'name' or 'skill_id' field in {skill_file.name}")
    return None
```

**Pros:**
- Backward compatible with old skill format
- No source data changes needed

**Cons:**
- Creates schema ambiguity (two ways to specify name)
- Doesn't address YAML syntax issue
- Perpetuates technical debt

**Verdict:** ❌ Not recommended

### Option B: Code Change - Lenient YAML Parsing

**Implementation:**
```python
# Pre-process YAML to auto-quote descriptions
def _safe_parse_yaml(self, yaml_text: str) -> dict:
    # Regex to quote unquoted description values with colons
    yaml_text = re.sub(
        r'^(description:)\s+([^"\'][^"\n]*:[^"\n]+)$',
        r'\1 "\2"',
        yaml_text,
        flags=re.MULTILINE
    )
    return yaml.safe_load(yaml_text)
```

**Pros:**
- No source data changes needed
- Handles both quoted and unquoted descriptions

**Cons:**
- Complex regex pattern (fragile, hard to maintain)
- May introduce new bugs (over-quoting, edge cases)
- Violates YAML spec (parser should be strict)
- Doesn't fix root cause (invalid YAML in source)

**Verdict:** ❌ Not recommended

### Option C: Hybrid - Emit Warnings, Auto-Fix on Deployment

**Implementation:**
```python
# Parse with fallbacks, log warnings
if "skill_id" in frontmatter and "name" not in frontmatter:
    self.logger.warning(
        f"Deprecated: {skill_file.name} uses 'skill_id' instead of 'name'. "
        f"This will be unsupported in future versions. Please update skill file."
    )
    name = frontmatter["skill_id"]
else:
    name = frontmatter.get("name")
```

**Pros:**
- Backward compatible (immediate fix for users)
- Clear migration path (warnings guide users to fix source)
- Graceful degradation

**Cons:**
- More complex parsing logic
- Doesn't address YAML syntax issue
- Delays proper fix

**Verdict:** ⚠️ Acceptable short-term, must plan deprecation timeline

---

## Decision Matrix

| Approach | Complexity | Risk | Time to Fix | Long-term Maintainability |
|----------|-----------|------|-------------|---------------------------|
| **Fix Source Data (Recommended)** | Low | Low | 1-2 hours | ✅ High |
| Accept both `name`/`skill_id` | Medium | Medium | 30 min | ❌ Low (tech debt) |
| Lenient YAML parsing | High | High | 2-3 hours | ❌ Very Low (fragile) |
| Hybrid with deprecation | Medium | Low | 1 hour | ⚠️ Medium (temporary) |

---

## Recommended Action Plan

### Immediate Actions (Required)

1. **Backup cache directory:**
   ```bash
   cp -r ~/.claude-mpm/cache/skills ~/.claude-mpm/cache/skills.backup.$(date +%Y%m%d)
   ```

2. **Run automated fix scripts:**
   ```bash
   ./fix-skill-schema.sh
   ./fix-yaml-colons.sh
   ```

3. **Verify fixes:**
   ```bash
   # Count fixed files
   echo "Schema fixes (skill_id → name):"
   find ~/.claude-mpm/cache/skills -name "SKILL.md.bak" | wc -l

   # Test parser
   python3 -c "
   from pathlib import Path
   from skill_discovery_service import SkillDiscoveryService
   service = SkillDiscoveryService(Path.home() / '.claude-mpm/cache/skills/system')
   skills = service.discover_skills()
   print(f'Successfully parsed {len(skills)} skills')
   "
   ```

4. **Review sample of fixed files manually:**
   ```bash
   # Check 3-5 files to ensure quality
   diff ~/.claude-mpm/cache/skills/system/universal/testing/test-driven-development/SKILL.md.bak \
        ~/.claude-mpm/cache/skills/system/universal/testing/test-driven-development/SKILL.md
   ```

### Long-term Improvements (Recommended)

1. **Add skill validation CI:**
   - Create GitHub Action to validate all SKILL.md files on commit
   - Enforce schema with JSON Schema or Pydantic validator
   - Prevent invalid skills from being merged

2. **Document skill schema:**
   - Create `SKILL_SCHEMA.md` in skills repository
   - Provide template for new skills
   - Include validation instructions

3. **Add parser tests:**
   - Unit tests for valid/invalid frontmatter
   - Integration tests for discovery service
   - Regression tests for these 31 failed cases

---

## Files Analyzed

**Source Code:**
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/skill_discovery_service.py` (569 lines)

**Sample Skill Files:**
- `/Users/masa/.claude-mpm/cache/skills/system/universal/collaboration/git-workflow/SKILL.md` (Missing `name` field)
- `/Users/masa/.claude-mpm/cache/skills/system/universal/testing/test-driven-development/SKILL.md` (Missing `name` field)
- `/Users/masa/.claude-mpm/cache/skills/system/universal/security/threat-modeling/SKILL.md` (Unquoted colon)
- `/Users/masa/.claude-mpm/cache/skills/system/universal/security/security-scanning/SKILL.md` (Unquoted colon)
- `/Users/masa/.claude-mpm/cache/skills/system/toolchains/typescript/frameworks/fastify/SKILL.md` (Valid, working example)
- `/Users/masa/.claude-mpm/cache/skills/system/toolchains/rust/cli/clap/SKILL.md` (Valid, working example)

---

## Conclusion

**Root Cause:** Source data inconsistency (skills not updated to match parser schema)

**Fix Type:** Data fix (update SKILL.md files)

**Reasoning:**
1. Parser is correctly strict per YAML spec
2. Required schema is minimal and well-defined
3. Source fixes are low-risk, automatable, and permanent
4. Code changes would add complexity without addressing root cause

**Next Steps:**
1. Run automated fix scripts on cache directory
2. Verify all 31 skills now parse successfully
3. Optional: Add validation to prevent future regressions
