# Output Style Deployment Investigation

**Date**: 2025-12-10
**Investigator**: Research Agent
**Scope**: Identify output style files, deployment mechanisms, and obsolete templates

## Executive Summary

The framework has **two output style files** that are currently deployed to the **wrong directory**. Deployment code references `.claude/output-styles/` but `OutputStyleManager` deploys to `.claude/styles/`. There is also a **BASE_AGENT_TEMPLATE.md** file that appears to be obsolete.

## Key Findings

### 1. Output Style Source Files (FOUND)

**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/`

1. **CLAUDE_MPM_OUTPUT_STYLE.md** (12,149 bytes)
   - Professional mode output style
   - Contains YAML frontmatter with metadata
   - Defines PM communication standards
   - Located at: `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`

2. **CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md** (58,561 bytes)
   - Teaching mode output style
   - Adaptive pedagogy for beginners
   - Much larger (4.8x size of professional style)
   - Located at: `src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`

### 2. Current Deployment Mechanism

**File**: `src/claude_mpm/core/output_style_manager.py`

**Deployment Targets**:
```python
# OutputStyleManager (line 54-55)
self.output_style_dir = Path.home() / ".claude" / "styles"
self.settings_file = Path.home() / ".claude" / "settings.json"
```

**Style Configuration** (lines 59-74):
```python
self.styles: Dict[str, StyleConfig] = {
    "professional": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm.md",  # ~/.claude/styles/claude-mpm.md
        name="claude-mpm",
    ),
    "teaching": StyleConfig(
        source=Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md",
        target=self.output_style_dir / "claude-mpm-teach.md",  # ~/.claude/styles/claude-mpm-teach.md
        name="claude-mpm-teach",
    ),
}
```

**Deployment Methods**:
- `deploy_output_style(content, style, activate)` - Deploy single style
- `deploy_all_styles(activate_default)` - Deploy all styles
- `_activate_output_style(style_name)` - Update settings.json with active style

**Version Requirements**:
- Requires Claude Code >= 1.0.83
- Falls back to injection for older versions

### 3. Startup Deployment Code

**File**: `src/claude_mpm/cli/startup.py`

**Function**: `deploy_output_style_on_startup()` (lines 222-294)

**CRITICAL BUG FOUND** (line 249):
```python
output_style_file = Path.home() / ".claude" / "output-styles" / "claude-mpm.md"
```

**This is WRONG!** Should be:
```python
output_style_file = Path.home() / ".claude" / "styles" / "claude-mpm.md"
```

**Legacy Reference** (line 275):
```python
output_style_path = Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"
```

**This file does NOT exist!** Should reference:
```python
# For professional style:
output_style_path = Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md"
```

### 4. Obsolete File Identified

**File**: `BASE_AGENT_TEMPLATE.md`
**Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md`
**Size**: 9,138 bytes
**Status**: **LIKELY OBSOLETE**

**Evidence**:
1. No references to this file in deployment code
2. Not referenced in `output_style_manager.py`
3. Not used by startup deployment
4. Name suggests it's a template for agent creation, not an output style
5. Content appears to be agent instruction template, not output style definition

**Purpose** (from content analysis):
- Provides base instructions for agent behavior
- Defines task management, response structure, memory protocols
- Used as template for creating new agents
- **Not an output style file**

**Recommendation**: Rename to clarify purpose or move to `templates/` directory.

### 5. What Needs to Change

**Priority 1: Fix Deployment Directory Mismatch**

**File**: `src/claude_mpm/cli/startup.py` line 249

**Current**:
```python
output_style_file = Path.home() / ".claude" / "output-styles" / "claude-mpm.md"
```

**Should be**:
```python
output_style_file = Path.home() / ".claude" / "styles" / "claude-mpm.md"
```

**Priority 2: Fix Legacy File Reference**

**File**: `src/claude_mpm/cli/startup.py` line 275

**Current**:
```python
output_style_path = Path(__file__).parent.parent / "agents" / "OUTPUT_STYLE.md"
```

**Should be**:
```python
output_style_path = Path(__file__).parent.parent / "agents" / "CLAUDE_MPM_OUTPUT_STYLE.md"
```

**Priority 3: Clarify BASE_AGENT_TEMPLATE.md Status**

**Options**:
1. **Keep as-is** if it's used elsewhere (need broader search)
2. **Rename** to `BASE_AGENT_INSTRUCTIONS.md` for clarity
3. **Move** to `templates/base-agent.md` to match other templates
4. **Delete** if truly obsolete (requires confirmation of no usage)

## Deployment Flow (As Designed)

```
Startup Sequence:
1. OutputStyleManager initialized
2. Detects Claude Code version (>= 1.0.83?)
3. If supported:
   a. Reads CLAUDE_MPM_OUTPUT_STYLE.md
   b. Deploys to ~/.claude/styles/claude-mpm.md
   c. Updates ~/.claude/settings.json with "activeOutputStyle": "claude-mpm"
4. If not supported (< 1.0.83):
   a. Injects content into framework instructions
   b. No file deployment
```

## Correct Deployment Paths

**Professional Style**:
- **Source**: `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`
- **Target**: `~/.claude/styles/claude-mpm.md`
- **Settings**: `activeOutputStyle: "claude-mpm"`

**Teaching Style**:
- **Source**: `src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`
- **Target**: `~/.claude/styles/claude-mpm-teach.md`
- **Settings**: `activeOutputStyle: "claude-mpm-teach"`

## Files Analyzed

1. ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`
2. ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md`
3. ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md`
4. ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/output_style_manager.py`
5. ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

## Recommendations

### Immediate Actions Required

1. **Fix `startup.py` line 249**: Change `output-styles` → `styles`
2. **Fix `startup.py` line 275**: Change `OUTPUT_STYLE.md` → `CLAUDE_MPM_OUTPUT_STYLE.md`
3. **Test deployment**: Verify styles deploy to correct directory
4. **Verify settings.json**: Ensure activation works correctly

### Follow-up Investigation

1. **BASE_AGENT_TEMPLATE.md**: Search for references across entire codebase
2. **OUTPUT_STYLE.md**: Confirm this file never existed (appears to be legacy reference)
3. **Test both styles**: Verify professional and teaching styles both deploy correctly

### Documentation Updates

1. Update deployment documentation to reflect correct paths
2. Document the two-style system (professional vs teaching)
3. Clarify that BASE_AGENT_TEMPLATE.md is for agent creation, not output styling

## Conclusion

The framework has the correct output style infrastructure in `OutputStyleManager`, but the startup deployment code has **two critical bugs**:

1. **Wrong directory**: References `.claude/output-styles/` instead of `.claude/styles/`
2. **Wrong filename**: References non-existent `OUTPUT_STYLE.md` instead of `CLAUDE_MPM_OUTPUT_STYLE.md`

Additionally, `BASE_AGENT_TEMPLATE.md` is **not an output style** but appears to be an agent instruction template that may be misplaced or obsolete.

**Impact**: Output styles are likely failing to deploy at startup due to incorrect path references.

**Fix Effort**: Low (2 line changes in `startup.py`)

**Testing Required**: Verify deployment to `~/.claude/styles/` and activation in `settings.json`
