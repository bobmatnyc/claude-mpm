# Output Styles Deployment Analysis for Claude MPM

**Date:** 2026-01-05  
**Analyst:** Research Agent  
**Scope:** Output style deployment mechanisms on install/startup

---

## Executive Summary

The **founders style is NOT automatically deployed** on install/startup, even though the infrastructure exists to support it. Only the professional and teaching styles are deployed. To auto-deploy the founders style, two changes are needed.

---

## Current Deployment Architecture

### 1. OutputStyleManager Class
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`

The `OutputStyleManager` class manages three output styles:

```python
self.styles: Dict[str, StyleConfig] = {
    "professional": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm.md",
        name="Claude MPM",
    ),
    "teaching": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm-teacher.md",
        name="Claude MPM Teacher",
    ),
    "founders": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm-founders.md",
        name="Claude MPM Founders",
    ),
}
```

**Key Methods:**
- `deploy_all_styles(activate_default=True)` - Deploys ALL three styles but only activates professional
- `deploy_output_style(style, activate=False)` - Deploys individual style
- `deploy_teaching_style(activate=False)` - Specific method for teaching style
- `_activate_output_style(style_name)` - Updates Claude settings to activate a style

---

### 2. Startup Deployment Points

#### Point A: CLI Startup Hook (Line 303-380)
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

```python
def deploy_output_style_on_startup():
    """
    Deploy claude-mpm output styles to PROJECT-LEVEL directory on CLI startup.
    
    Deploys two styles:
    - claude-mpm.md (professional mode)
    - claude-mpm-teacher.md (teaching mode)
    """
```

**Current Behavior:**
- Manually copies only 2 files using `shutil.copy2()`
- Does NOT use `OutputStyleManager`
- Does NOT deploy the founders style
- Compares file sizes to check if up-to-date
- Called from `run_background_services()` at line 1271

#### Point B: Claude Runner Method
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/claude_runner.py`

```python
def _deploy_output_style(self) -> None:
    """Deploy the Claude MPM output style before Claude Code launches."""
```

- Used in `claude_runner` when launching Claude Code
- Deploys individual output style (default: professional)
- Only runs if Claude >= 1.0.83

---

## Current Deployment Flow on Startup

```
cli startup
    └─> run_background_services()
        └─> deploy_output_style_on_startup()
            ├─> Copies CLAUDE_MPM_OUTPUT_STYLE.md → ~/.claude/output-styles/claude-mpm.md
            └─> Copies CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md → ~/.claude/output-styles/claude-mpm-teacher.md
                (FOUNDERS STYLE NOT DEPLOYED)
```

---

## Key Findings

### Finding 1: `deploy_all_styles()` is Defined but NOT Called
- **Status:** ✗ NOT USED ON STARTUP
- **Location:** `output_style_manager.py:433`
- **Why it matters:** This method can deploy all 3 styles but is never invoked during startup
- **Current behavior:** It would deploy all 3 styles AND activate professional (the default)

### Finding 2: Startup Hook Uses Direct File Copy
- **Status:** ✗ DOESN'T USE OutputStyleManager
- **Location:** `cli/startup.py:303-380`
- **Why it matters:** Hardcoded to deploy only professional and teaching, bypasses manager
- **Code pattern:** Uses `shutil.copy2()` instead of manager methods

### Finding 3: Founders Style Exists But Isn't Deployed
- **Status:** ✓ FILE EXISTS
- **Location:** `src/claude_mpm/agents/CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md`
- **Registered:** ✓ Defined in StyleConfig (lines 75-81)
- **Deployed:** ✗ No, not included in startup

### Finding 4: CLI Commands Can Deploy Founders Manually
- **Status:** ✓ POSSIBLE VIA mcp-style COMMANDS
- **How:** Not documented in current research, but OutputStyleManager supports it

---

## Impact Assessment

### Current State
✓ Professional style: Auto-deployed and activated  
✓ Teaching style: Auto-deployed but NOT activated  
✗ Founders style: **NOT deployed**

### User Experience
- Users get professional style by default (good)
- Teaching style available but must be manually activated
- Founders style completely unavailable (cannot be used)

### Business Impact
- Founders cannot benefit from non-technical communication style
- Founders style represents wasted development effort if not deployed

---

## Required Changes to Auto-Deploy Founders Style

### Change 1: Update `deploy_output_style_on_startup()` (RECOMMENDED)

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

**Option A: Use OutputStyleManager (BETTER)**

Replace lines 303-380 with:

```python
def deploy_output_style_on_startup():
    """
    Deploy all claude-mpm output styles to user-level directory on CLI startup.
    
    Deploys three styles:
    - claude-mpm.md (professional mode) - ACTIVATED by default
    - claude-mpm-teacher.md (teaching mode)
    - claude-mpm-founders.md (non-technical mode for startup founders)
    """
    try:
        from claude_mpm.core.output_style_manager import OutputStyleManager
        
        manager = OutputStyleManager()
        
        # Deploy all styles (only activates professional by default)
        results = manager.deploy_all_styles(activate_default=True)
        
        # Count deployed styles
        deployed_count = sum(1 for success in results.values() if success)
        
        if deployed_count > 0:
            print(f"✓ Output styles deployed ({deployed_count} styles)", flush=True)
        else:
            print("✓ Output styles ready", flush=True)
            
    except Exception as e:
        from ..core.logger import get_logger
        logger = get_logger("cli")
        logger.debug(f"Failed to deploy output styles: {e}")
        # Continue execution - non-blocking
```

**Benefits:**
- Cleaner, more maintainable code
- Uses existing manager infrastructure
- Automatically includes any new styles added to manager
- Consistent with how other deployments work (agents, skills)
- Reduces code duplication

**Option B: Minimal Change (Add Founders to Existing Code)**

Keep existing structure, add 3 lines:

```python
def deploy_output_style_on_startup():
    # ... existing professional_source and teacher_source setup ...
    
    # Add founders style
    founders_source = package_dir / "CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md"
    founders_target = output_styles_dir / "claude-mpm-founders.md"
    
    # ... existing professional and teacher deployment ...
    
    # Deploy founders style
    if founders_source.exists():
        shutil.copy2(founders_source, founders_target)
        deployed_count += 1
```

---

### Change 2: Document Founders Style Availability (SUPPORTING)

**File:** README or documentation

Add section explaining that users can switch to founders style:

```markdown
## Output Styles

Claude MPM includes three output styles:

1. **Professional** (default) - Technical communication optimized for developers
2. **Teaching** - Adaptive teaching mode with explanations
3. **Founders** - Non-technical mode for startup founders

To switch to founders mode, run:
```
claude mpm style activate founders
```
```

---

## Recommendation

**Action:** Implement Change 1 with Option A (Use OutputStyleManager)

**Rationale:**
1. **Better Architecture:** Leverages existing manager class
2. **Maintainability:** Single source of truth for style definitions
3. **Scalability:** New styles auto-included without code changes
4. **Consistency:** Matches pattern used for agents/skills deployment
5. **Non-Breaking:** Professional style still activated by default

**Implementation Effort:** Low (< 30 minutes)

**Risk Level:** Very Low
- Change is isolated to startup hook
- Doesn't affect running systems
- Founder style already fully implemented
- Professional style remains default and activated

---

## Technical Details

### Style Configuration Files

All three styles are properly configured source files:

```
src/claude_mpm/agents/
├── CLAUDE_MPM_OUTPUT_STYLE.md              ✓ Professional
├── CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md      ✓ Teaching  
└── CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md     ✓ Founders
```

### Deployment Target

All styles deploy to user's Claude configuration:

```
~/.claude/output-styles/
├── claude-mpm.md                    ← Professional (activated)
├── claude-mpm-teacher.md            ← Teaching (available)
└── claude-mpm-founders.md           ← Founders (currently not deployed)
```

### Version Requirement

Output styles require Claude Code >= 1.0.83

```python
def supports_output_styles(self) -> bool:
    """Check if Claude Code supports output styles (>= 1.0.83)."""
    if not self.claude_version:
        return False
    return self._compare_versions(self.claude_version, "1.0.83") >= 0
```

---

## Summary Table

| Style | File Exists | Registered | Auto-Deployed | Can Activate |
|-------|-----------|-----------|--------------|-------------|
| Professional | ✓ | ✓ | ✓ Yes | ✓ Yes |
| Teaching | ✓ | ✓ | ✗ No | ✓ Yes |
| Founders | ✓ | ✓ | ✗ **No** | ✓ Yes |

---

## Conclusion

The founders style is fully implemented and registered but **not included in automatic deployment**. This appears to be an oversight rather than an intentional exclusion. The infrastructure to deploy it exists—it's just not being called during startup.

**Next Steps:**
1. Implement Change 1 (use OutputStyleManager in startup hook)
2. Add documentation on style switching
3. Consider CLI command for manual style selection

