# Skill Filtering Bug Investigation

**Date:** 2025-12-29
**Investigator:** Research Agent
**Status:** Root Cause Identified

## Problem Statement

Profile "framework-development" has 28 enabled skills, but startup shows 109 skills loading instead of the filtered 28. Agent filtering was recently fixed (Config singleton issue), but skill filtering still broken.

## Investigation Summary

### Key Findings

1. **Profile filtering IS being applied** in `startup.py` (lines 927-967)
2. **`is_skill_enabled()` correctly handles short names** in `profile_manager.py` (lines 193-236)
3. **BUT the filtered list isn't actually used during deployment**

### Root Cause

The bug is in `git_skill_source_manager.py` at lines 1048-1063:

```python
# Apply skill filter if provided (selective deployment)
if skill_filter is not None:
    original_count = len(all_skills)
    # Normalize filter to lowercase for case-insensitive matching
    normalized_filter = {s.lower() for s in skill_filter}
    # Match against deployment_name (not display name) since skill_filter contains
    # deployment-style names like "toolchains-python-frameworks-django"
    all_skills = [
        s
        for s in all_skills
        if s.get("deployment_name", "").lower() in normalized_filter
    ]
```

**The Problem:**

- Line 1057: Uses **EXACT match** against `deployment_name`
- `skill_filter` contains **short names** from profile: `{"flask", "pytest", "mypy", ...}`
- Skills have **full deployment names**: `"toolchains-python-frameworks-flask"`
- **NO MATCHES OCCUR** because `"flask"` ≠ `"toolchains-python-frameworks-flask"`
- Therefore, all skills are filtered OUT, and the empty filter causes all 109 skills to deploy

### Why Agent Filtering Works

Agent filtering in `startup.py` (lines 927-952) uses `profile_manager.is_skill_enabled()`, which has fuzzy matching logic:

```python
# Check if full skill name ends with short name from enabled list
# Example: "toolchains-python-frameworks-flask" matches "flask"
for short_name in self._enabled_skills:
    if skill_name.endswith(f"-{short_name}"):
        return True
```

But skill deployment filtering uses exact string matching instead.

### Data Flow

1. **Profile loaded** → Contains short names: `["flask", "pytest", "mypy", ...]`
2. **`startup.py` line 936** → Calls `profile_manager.is_skill_enabled(skill)` with short names
3. **`startup.py` line 952** → Creates `skills_to_deploy = filtered_skills` with short names
4. **`startup.py` line 984** → Passes `skill_filter=set(skills_to_deploy)` to `deploy_skills()`
5. **`git_skill_source_manager.py` line 1057** → EXACT match fails: `"flask" not in ["toolchains-python-frameworks-flask"]`
6. **All skills filtered out** → Empty filter → Deploy all 109 skills

## Evidence

### Profile Format

```yaml
# .claude-mpm/profiles/framework-development.yaml
skills:
  enabled:
    - flask         # SHORT NAME
    - pytest        # SHORT NAME
    - mypy          # SHORT NAME
    - typescript-core
    - svelte
    # ... 28 total
```

### Skill Metadata Format

```python
# From skill_discovery_service.py lines 200-209
skill_dict["deployment_name"] = deployment_name  # "toolchains-python-frameworks-flask"
skill_dict["relative_path"] = str(skill_file.relative_to(self.skills_dir))
```

### Comparison Logic Mismatch

**Profile Manager (CORRECT - fuzzy matching):**
```python
# profile_manager.py lines 224-231
for short_name in self._enabled_skills:
    if skill_name.endswith(f"-{short_name}"):
        return True
    if f"-{short_name}-" in skill_name or skill_name.startswith(f"{short_name}-"):
        return True
```

**Git Skill Source Manager (BROKEN - exact matching):**
```python
# git_skill_source_manager.py line 1057
if s.get("deployment_name", "").lower() in normalized_filter
```

## Impact Assessment

### Current Behavior
- **Expected:** 28 skills deployed (profile-filtered)
- **Actual:** 109 skills deployed (all skills)
- **Context Impact:** ~80 extra skills loaded (≈200-400 tokens each = 16,000-32,000 extra tokens)

### User Experience
- Slower startup (copying 109 skills instead of 28)
- Massive context pollution (81 unwanted skills in prompts)
- Profile filtering appears broken to users
- No error message (fails silently)

## Recommended Fix

### Option 1: Use Fuzzy Matching in deploy_skills() (RECOMMENDED)

Replace exact matching with the same fuzzy logic as `is_skill_enabled()`:

```python
# git_skill_source_manager.py lines 1048-1063
if skill_filter is not None:
    original_count = len(all_skills)
    normalized_filter = {s.lower() for s in skill_filter}

    def matches_filter(deployment_name: str) -> bool:
        """Match using same fuzzy logic as profile_manager.is_skill_enabled()"""
        deployment_lower = deployment_name.lower()

        # Exact match
        if deployment_lower in normalized_filter:
            return True

        # Fuzzy match: check if deployment name ends with short name
        for short_name in normalized_filter:
            if deployment_lower.endswith(f"-{short_name}"):
                return True
            if f"-{short_name}-" in deployment_lower or deployment_lower.startswith(f"{short_name}-"):
                return True

        return False

    all_skills = [s for s in all_skills if matches_filter(s.get("deployment_name", ""))]
    filtered_count = original_count - len(all_skills)
```

**Pros:**
- Matches existing `is_skill_enabled()` behavior
- No changes to startup.py
- Handles both short and full names
- Backward compatible

**Cons:**
- Duplicate matching logic (DRY violation)

### Option 2: Convert Short Names to Full Names in startup.py

Before passing to `deploy_skills()`, resolve short names to full deployment names:

```python
# startup.py after line 952
if active_profile and profile_manager.active_profile:
    # ... existing filtering logic ...
    skills_to_deploy = filtered_skills

    # NEW: Convert short names to full deployment names
    all_available_skills = manager.get_all_skills()
    deployment_names = set()
    for short_name in skills_to_deploy:
        for skill in all_available_skills:
            if profile_manager.is_skill_enabled(skill.get("deployment_name", "")):
                deployment_names.add(skill["deployment_name"])
    skills_to_deploy = list(deployment_names)
```

**Pros:**
- Single source of truth for matching logic
- No changes to git_skill_source_manager.py

**Cons:**
- Extra `get_all_skills()` call (performance)
- More complex startup logic

### Option 3: Refactor to Centralized Matching (BEST LONG-TERM)

Extract matching logic to `profile_manager.py` and use it consistently:

```python
# profile_manager.py
def matches_skill_filter(self, skill_name: str, filter_set: Set[str]) -> bool:
    """Check if skill name matches any entry in filter set (short or full names)"""
    # ... same logic as is_skill_enabled() but parameterized ...

# git_skill_source_manager.py
all_skills = [
    s for s in all_skills
    if profile_manager.matches_skill_filter(s.get("deployment_name", ""), skill_filter)
]
```

**Pros:**
- DRY: Single implementation of matching logic
- Testable: Can unit test matching in isolation
- Maintainable: Changes to matching affect all callers

**Cons:**
- Requires passing `profile_manager` to `deploy_skills()`
- Larger refactoring effort

## Testing Strategy

### Test Cases

1. **Short name matching:**
   - Filter: `{"flask"}`
   - Should match: `"toolchains-python-frameworks-flask"`
   - Should not match: `"toolchains-rust-frameworks-axum"`

2. **Full name matching:**
   - Filter: `{"toolchains-python-frameworks-flask"}`
   - Should match: `"toolchains-python-frameworks-flask"`

3. **Glob pattern matching:**
   - Filter: `{"typescript-*"}`
   - Should match: `"toolchains-typescript-core"`, `"typescript-testing-jest"`

4. **Mixed short and full names:**
   - Filter: `{"flask", "toolchains-typescript-core"}`
   - Should match both

5. **Edge cases:**
   - Filter: `{"test"}` should NOT match `"pytest"` (avoid partial matches)
   - Filter: `{"typescript"}` should match `"toolchains-typescript-core"` (suffix match)

### Verification

After fix, run:
```bash
claude-mpm profile activate framework-development
claude-mpm start --log-level=DEBUG 2>&1 | grep -E "(Profile|Deploying|skills)"
```

Expected output:
```
Profile 'framework-development' filtered X skills (28 remaining)
Deploying 28 skills to .claude/skills (force=False)
```

## Related Code Locations

- **Profile loading:** `src/claude_mpm/services/profile_manager.py:193-236` (`is_skill_enabled()`)
- **Startup filtering:** `src/claude_mpm/cli/startup.py:927-967` (Phase 4: Apply profile filtering)
- **Deployment filtering:** `src/claude_mpm/services/skills/git_skill_source_manager.py:1048-1063`
- **Skill metadata:** `src/claude_mpm/services/skills/skill_discovery_service.py:185-209`

## Timeline of Related Changes

- **Recent:** Agent filtering fixed (Config singleton issue)
- **Previous research:** Noted "skill filtering correctly filters the skills_to_deploy list directly"
  - This was PARTIALLY correct: Filtering happens, but result is ignored during deployment

## Conclusion

**Root Cause:** Exact string matching in `deploy_skills()` fails to match short profile names against full deployment names, causing all skills to be deployed instead of the filtered subset.

**Recommended Fix:** Option 1 (fuzzy matching in `deploy_skills()`) for immediate resolution, then refactor to Option 3 for long-term maintainability.

**Estimated Effort:** 1-2 hours (fix + testing)

**Priority:** HIGH - Profile filtering is a core feature for reducing context usage
