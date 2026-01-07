# PM Skills "0 deployed" Investigation

**Date**: 2025-12-30
**Investigator**: Research Agent
**Issue**: User sees `✓ PM skills: 0 deployed` during startup, but PM skills should always deploy

## Summary

The "0 deployed" message occurs when:
1. PM skills verification fails (no registry or missing skills)
2. Auto-deployment is triggered
3. Bundled skills path doesn't exist → discovery returns empty list
4. Deployment completes with `deployed=[]` and `skipped=[]`

The root cause is incomplete handling when the bundled skills path is missing.

## Code Flow Analysis

### Normal Flow (Working)

```
Startup
  → verify_and_show_pm_skills() [startup.py:1346]
    → deployer.verify_pm_skills(project_dir) [pm_skills_deployer.py:523]
      → _load_registry() finds registry with 5 skills
      → Checks all files exist and checksums match
      → Returns VerificationResult(verified=True, skill_count=5)
    → Prints: "✓ PM skills: 5 verified" [startup.py:1364]
```

### Problem Flow (User's Issue)

```
Startup
  → verify_and_show_pm_skills() [startup.py:1346]
    → deployer.verify_pm_skills(project_dir)
      → _load_registry() finds NO registry
      → Returns VerificationResult(verified=False, skill_count=0)
    → Auto-deploy triggered [startup.py:1367-1373]
      → deployer.deploy_pm_skills(project_dir)
        → _discover_bundled_pm_skills()
          → bundled_pm_skills_path.exists() == False
          → Returns [] [pm_skills_deployer.py:337-341]
        → Returns DeploymentResult(deployed=[], skipped=[])
      → total = len([]) + len([]) = 0
      → Prints: "✓ PM skills: 0 deployed" [startup.py:1371]
```

## Root Cause

### Path Resolution Logic

**Location**: `src/claude_mpm/services/pm_skills_deployer.py:153-178`

```python
def __init__(self) -> None:
    package_dir = Path(__file__).resolve().parent.parent  # Go up to claude_mpm
    self.bundled_pm_skills_path = package_dir / "skills" / "bundled" / "pm"

    if not self.bundled_pm_skills_path.exists():
        # Fallback: try .claude-mpm/templates/ at project root
        self.project_root = self._find_project_root()
        alt_path = self.project_root / ".claude-mpm" / "templates"
        if alt_path.exists():
            self.bundled_pm_skills_path = alt_path
        else:
            # ISSUE: Logs warning but continues with non-existent path
            self.logger.warning(
                "PM skills templates path not found (non-critical, uses defaults)"
            )
            # bundled_pm_skills_path still points to non-existent directory
```

**Problem**: When both paths don't exist, `bundled_pm_skills_path` remains set to a non-existent path. Later calls to `_discover_bundled_pm_skills()` return empty list.

### Discovery Returns Empty List

**Location**: `src/claude_mpm/services/pm_skills_deployer.py:337-341`

```python
if not self.bundled_pm_skills_path.exists():
    self.logger.warning(
        f"Bundled PM skills path not found: {self.bundled_pm_skills_path}"
    )
    return skills  # Returns empty []
```

### Deployment Returns Zero Skills

**Location**: `src/claude_mpm/services/pm_skills_deployer.py:397-409`

```python
skills = self._discover_bundled_pm_skills()  # Returns []
deployed = []
skipped = []
errors = []

if not skills:  # True when skills = []
    return DeploymentResult(
        success=True,
        deployed=[],  # Empty
        skipped=[],   # Empty
        errors=[],
        message="No PM skills found to deploy",
    )
```

### Startup Displays "0 deployed"

**Location**: `src/claude_mpm/cli/startup.py:1367-1371`

```python
# Auto-deploy if missing
print("Deploying PM skills...", end="", flush=True)
deploy_result = deployer.deploy_pm_skills(project_dir)
if deploy_result.success:
    total = len(deploy_result.deployed) + len(deploy_result.skipped)  # 0 + 0 = 0
    print(f"\r✓ PM skills: {total} deployed" + " " * 20, flush=True)
```

## Verification in Dev Environment

Tested in current dev environment:

```bash
$ python -c "from pathlib import Path; from src.claude_mpm.services.pm_skills_deployer import PMSkillsDeployerService; d = PMSkillsDeployerService(); r = d.verify_pm_skills(Path.cwd()); print(f'verified: {r.verified}, skill_count: {r.skill_count}')"

verified: True, skill_count: 5
```

**Working correctly** because:
1. Registry exists at `.claude-mpm/pm_skills_registry.yaml` with 5 skills
2. Bundled path exists at `src/claude_mpm/skills/bundled/pm/` with 5 skill directories
3. All deployed files exist in `.claude-mpm/skills/pm/`

## Possible Scenarios for "0 deployed"

### Scenario 1: Missing Bundled Skills (Package Installation Issue)

**When**: `pip install` or `pipx install` doesn't include `skills/bundled/pm/` directory

**Cause**: Missing `MANIFEST.in` entry or incorrect `pyproject.toml` package data configuration

**Fix**: Verify package includes bundled PM skills in distribution

### Scenario 2: Fresh Project Without PM Skills

**When**: New project, first startup, no previous PM skills deployment

**Cause**: No registry exists → verification fails → auto-deploy triggered
But if bundled skills missing → deploys 0 skills

**Fix**: Ensure bundled skills path is always valid

### Scenario 3: Corrupted Installation

**When**: Partial installation or corrupted package files

**Cause**: `skills/bundled/pm/` directory deleted or inaccessible

**Fix**: Reinstall package or provide fallback PM skills source

## Message Semantics

Important distinction between two messages:

- **"X verified"**: Skills already deployed, verification passed, no action needed
- **"X deployed"**: Verification failed, auto-deployment just ran, X skills were installed

User seeing "0 deployed" means auto-deployment ran but found nothing to deploy.

## Fix Required

The issue is NOT in the display logic or `skill_count` attribute (already fixed in v5.4.59).

The issue IS in path resolution when bundled skills are missing:

**Current behavior**:
- Logs warning: "PM skills templates path not found (non-critical, uses defaults)"
- Continues with non-existent path
- Discovery returns `[]`
- Deployment returns `deployed=[], skipped=[]`
- Displays "0 deployed"

**Expected behavior**:
- Detect missing bundled skills path
- Either:
  - **Option A**: Fail fast with clear error message
  - **Option B**: Provide embedded fallback PM skills (inline in code)
  - **Option C**: Download PM skills from remote source on-demand
  - **Option D**: Skip PM skills deployment gracefully and warn user

## Recommended Fix

**Option D** (Least disruptive):

1. When bundled path doesn't exist, skip PM skills deployment entirely
2. Don't print "0 deployed" (confusing)
3. Print warning: "⚠ PM skills not available (reinstall claude-mpm to restore)"
4. Allow claude-mpm to continue working without PM skills

**Implementation**:

```python
# In verify_and_show_pm_skills() at startup.py:1346

def verify_and_show_pm_skills():
    try:
        deployer = PMSkillsDeployerService()

        # NEW: Check if bundled skills path exists
        if not deployer.bundled_pm_skills_path.exists():
            print("⚠ PM skills not available (bundled templates missing)", flush=True)
            return  # Skip PM skills entirely

        # Existing verification logic...
        result = deployer.verify_pm_skills(project_dir)
        if result.verified:
            print(f"✓ PM skills: {result.skill_count} verified", flush=True)
        else:
            # Auto-deploy logic...
```

This prevents confusing "0 deployed" message when bundled skills are truly missing.

## Related Commits

- **v5.4.59** (2e2ca793): Added `skill_count` attribute to `VerificationResult`
  - Fixed display to show count of verified skills
  - This was NOT the root cause - it fixed the attribute but not the missing bundled skills issue

- **v5.4.60** (1517e116): Fixed skills field preservation in agent deployment
  - Unrelated to PM skills (different skill system)

## Files Involved

- `src/claude_mpm/services/pm_skills_deployer.py` - PM skills deployment service
- `src/claude_mpm/cli/startup.py` - Startup verification and display
- `src/claude_mpm/skills/bundled/pm/` - Bundled PM skill templates (5 skills)
- `.claude-mpm/pm_skills_registry.yaml` - Deployment registry
- `.claude-mpm/skills/pm/` - Deployed PM skill files

## Testing Recommendation

To reproduce the "0 deployed" issue:

```bash
# Temporarily hide bundled skills
mv src/claude_mpm/skills/bundled/pm src/claude_mpm/skills/bundled/pm.bak

# Delete PM skills registry
rm .claude-mpm/pm_skills_registry.yaml

# Run startup
python -m claude_mpm doctor

# Should see: "✓ PM skills: 0 deployed" (current behavior)
# Should see: "⚠ PM skills not available (bundled templates missing)" (after fix)

# Restore
mv src/claude_mpm/skills/bundled/pm.bak src/claude_mpm/skills/bundled/pm
```

## Conclusion

**Root Cause**: When bundled PM skills path doesn't exist (package installation issue or missing files), the deployer continues with non-existent path, discovers 0 skills, and displays "0 deployed".

**Fix Needed**: Add explicit check in `verify_and_show_pm_skills()` to detect missing bundled path and skip PM skills with clear warning instead of showing "0 deployed".

**Priority**: Medium - PM skills are optional for claude-mpm operation, but confusing "0 deployed" message should be fixed.
