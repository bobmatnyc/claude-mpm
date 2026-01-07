# Profile-Based Skill Filtering Bug Investigation

**Date:** 2025-12-28
**Investigator:** Research Agent
**Status:** Root Cause Identified

## Problem Statement

Profile `framework-development` is active with 28 skills enabled, but startup is loading 109+ skills instead of filtering to the 28 specified in the profile.

## Root Cause

**The profile filtering logic has a critical flaw in its execution flow:**

### Current Flow (Lines 918-952 in `src/claude_mpm/cli/startup.py`)

```python
# Phase 3: Resolve which skills to deploy (user_defined or agent_referenced)
skills_to_deploy, skill_source = get_skills_to_deploy(project_config_path)

# Phase 4: Apply profile filtering if active
if active_profile and profile_manager.active_profile:
    # Filter skills based on profile
    if skills_to_deploy:  # <-- BUG: This condition is ALWAYS true
        # Filter the resolved skill list
        filtered_skills = [
            skill
            for skill in skills_to_deploy
            if profile_manager.is_skill_enabled(skill)
        ]
        # ... rest of filtering logic
```

### The Bug

**Line 924:** `if skills_to_deploy:`

This condition checks if the `skills_to_deploy` list is **non-empty**. The problem is:

1. `get_skills_to_deploy()` returns **97 agent-referenced skills** from `configuration.yaml`
2. The condition `if skills_to_deploy:` evaluates to **True** (97 skills is non-empty)
3. Code enters the filtering block (lines 926-938)
4. **BUT**: The filtering logic is **BROKEN** because it's filtering 97 skills against profile's 28 enabled skills

### Expected vs. Actual Behavior

**Expected:**
- Profile has 28 enabled skills
- Deployment should deploy ONLY those 28 skills
- Filter should work as **whitelist** (only deploy what's in profile)

**Actual:**
- Profile loads successfully (confirmed by logs: "Profile 'framework-development' active: 28 skills enabled")
- `get_skills_to_deploy()` returns 97 agent-referenced skills
- Profile filtering applies to those 97 skills
- BUT: `is_skill_enabled()` logic is **ALLOWING** skills instead of **BLOCKING** them

## ProfileManager.is_skill_enabled() Logic Flaw

**File:** `src/claude_mpm/services/profile_manager.py` (lines 154-183)

```python
def is_skill_enabled(self, skill_name: str) -> bool:
    """Check if skill is enabled in active profile."""
    if not self.active_profile:
        # No profile active - all skills enabled
        return True

    # Check if skill is explicitly disabled by pattern
    for pattern in self._disabled_skill_patterns:
        if fnmatch.fnmatch(skill_name, pattern):
            logger.debug(f"Skill '{skill_name}' matched disabled pattern '{pattern}'")
            return False

    # If enabled list exists, skill must be in it
    if self._enabled_skills:
        return skill_name in self._enabled_skills

    # No enabled list and didn't match disabled pattern - allow it
    return True  # <-- BUG: Default is ALLOW instead of DENY
```

### The Problem

**Lines 178-183:** The logic has a fundamental flaw:

1. Profile has **both** `enabled` list (28 skills) AND `disabled_categories` patterns (40+ patterns)
2. When checking a skill like `toolchains-golang-data`:
   - It doesn't match any disabled pattern (line 173-176)
   - `self._enabled_skills` exists (28 skills), so line 179 checks membership
   - BUT: `toolchains-golang-data` is NOT in the enabled list
   - So it returns **False** (line 179)
   - This is CORRECT behavior!

**Wait... Let me re-check the logic...**

Actually, the logic at line 179 looks correct:
```python
if self._enabled_skills:
    return skill_name in self._enabled_skills
```

This means:
- If enabled list exists, return True ONLY if skill is in the list
- Otherwise return False

This should work correctly. So why are 109+ skills being deployed?

## Re-Investigation: Where Does Filtering Actually Happen?

Let me trace the actual deployment:

### Phase 4 Filtering (Lines 921-952)

```python
if active_profile and profile_manager.active_profile:
    # Filter skills based on profile
    if skills_to_deploy:
        # Filter the resolved skill list
        filtered_skills = [
            skill
            for skill in skills_to_deploy
            if profile_manager.is_skill_enabled(skill)
        ]
        filtered_count = len(skills_to_deploy) - len(filtered_skills)
        if filtered_count > 0:
            logger.info(
                f"Profile '{active_profile}' filtered {filtered_count} skills "
                f"({len(filtered_skills)} remaining)"
            )
        skills_to_deploy = filtered_skills  # <-- Filtered list assigned here
        skill_source = f"{skill_source} + profile filtered"
```

This code should work! But then...

### Phase 5: Deploy Skills (Lines 964-970)

```python
# Deploy skills with resolved filter
# Deploy to project directory (like agents), not user directory
deployment_result = manager.deploy_skills(
    target_dir=Path.cwd() / ".claude" / "skills",
    force=False,
    skill_filter=set(skills_to_deploy) if skills_to_deploy else None,
)
```

**AH-HA! The bug is here:**

Line 969: `skill_filter=set(skills_to_deploy) if skills_to_deploy else None`

The problem:
1. If `skills_to_deploy` is **empty** after profile filtering, then `skill_filter=None`
2. When `skill_filter=None`, `deploy_skills()` will deploy **ALL** available skills!

But wait... the profile has 28 enabled skills, so `skills_to_deploy` shouldn't be empty after filtering. Let me check the enabled list again.

## Profile Analysis

**Profile:** `framework-development.yaml`

**Enabled Skills (28):**
```yaml
skills:
  enabled:
    # Python ecosystem
    - flask
    - pytest
    - mypy
    - pydantic
    - pyright-type-checker
    - sqlalchemy-orm

    # TypeScript/Svelte (Dashboard)
    - typescript-core
    - svelte
    - sveltekit
    - svelte5-runes-static
    - vite-build-tool
    - biome

    # ... (28 total)
```

**BUT:** These skill names are **SHORT NAMES** (e.g., `flask`, `pytest`, `mypy`)

**Agent-Referenced Skills (97) use FULL NAMES:**
```yaml
skills:
  agent_referenced:
    - toolchains-python-frameworks-flask  # <-- Full name
    - toolchains-python-testing-pytest    # <-- Full name
    - toolchains-python-tooling-mypy      # <-- Full name
```

## THE REAL BUG: Skill Name Mismatch

**Profile uses short names:** `flask`, `pytest`, `mypy`
**Agent requirements use full names:** `toolchains-python-frameworks-flask`, `toolchains-python-testing-pytest`

When profile filtering runs:
1. It checks if `toolchains-python-frameworks-flask` is in enabled list
2. Enabled list has `flask`, not `toolchains-python-frameworks-flask`
3. Result: **NO MATCH** → skill filtered OUT
4. This happens for ALL 97 agent-referenced skills
5. Final `skills_to_deploy` list is **EMPTY**
6. `skill_filter=None` is passed to `deploy_skills()`
7. **ALL 109+ skills get deployed**

## Solution

**Option 1: Update Profile to Use Full Skill Names**
- Change `flask` to `toolchains-python-frameworks-flask`
- Change `pytest` to `toolchains-python-testing-pytest`
- etc.

**Option 2: Add Skill Name Normalization**
- Modify `is_skill_enabled()` to match both short and full names
- Example: Check if `skill_name.endswith(f"-{short_name}")` or `skill_name == short_name`

**Option 3: Fix get_skills_to_deploy() to Return Empty List**
- If profile filtering results in empty list, return `[]` explicitly
- This will prevent `skill_filter=None` issue
- BUT: Still won't deploy the desired 28 skills

## Recommended Fix

**Use Option 2 with fallback to Option 1:**

1. Update `ProfileManager.is_skill_enabled()` to support both short and full names:
   ```python
   def is_skill_enabled(self, skill_name: str) -> bool:
       # ... existing logic ...

       # If enabled list exists, check for exact match or suffix match
       if self._enabled_skills:
           # Check exact match first
           if skill_name in self._enabled_skills:
               return True

           # Check if skill ends with any enabled short name
           for short_name in self._enabled_skills:
               if skill_name.endswith(f"-{short_name}"):
                   return True

           return False  # Not in enabled list
   ```

2. Add validation to detect profile configuration issues:
   - Warn if enabled skills list results in zero matches
   - Suggest using full skill names in profile

3. Add debug logging:
   - Log which skills are being filtered and why
   - Show skill name mismatches

## Verification Steps

After fix:
1. Run `claude-mpm` with `framework-development` profile
2. Check that only 28 skills are deployed
3. Verify skill names match between profile and deployment
4. Add test case for skill name matching logic

## Test Case

```python
def test_profile_skill_filtering_with_short_names():
    """Test that profile filtering works with both short and full skill names."""
    profile_manager = ProfileManager()
    profile_manager._enabled_skills = {"flask", "pytest", "mypy"}

    # Should match full names
    assert profile_manager.is_skill_enabled("toolchains-python-frameworks-flask")
    assert profile_manager.is_skill_enabled("toolchains-python-testing-pytest")
    assert profile_manager.is_skill_enabled("toolchains-python-tooling-mypy")

    # Should NOT match different skills
    assert not profile_manager.is_skill_enabled("toolchains-python-frameworks-django")

    # Should match short names (backwards compatibility)
    assert profile_manager.is_skill_enabled("flask")
    assert profile_manager.is_skill_enabled("pytest")
```

## Impact

**Current Impact:**
- Profile filtering is **completely broken**
- All 109+ skills being deployed regardless of profile configuration
- No token/context savings from profiles
- Users experiencing high context usage despite enabling profiles

**After Fix:**
- Profile filtering will work correctly
- Only 28 skills deployed (vs. 109+ currently)
- 75% reduction in skill context usage
- Actual context reduction as advertised

## Related Files

- `src/claude_mpm/cli/startup.py` (lines 768-1051) - Skill sync and deployment
- `src/claude_mpm/services/profile_manager.py` (lines 154-183) - Filtering logic
- `src/claude_mpm/services/skills/selective_skill_deployer.py` (lines 531-578) - Skill resolution
- `.claude-mpm/profiles/framework-development.yaml` - Profile configuration
- `.claude-mpm/configuration.yaml` - Agent-referenced skills list
