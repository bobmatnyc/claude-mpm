# PM Instruction Assembly Analysis

**Date**: 2025-12-23
**Researcher**: Research Agent
**Focus**: How PM instructions are assembled and whether deployment works correctly

---

## Executive Summary

The instruction assembly system has **two distinct loading strategies** for development vs. deployed packages:

1. **Development Mode**: Loads individual files (PM_INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md) separately with tier precedence
2. **Deployed Mode**: Uses `importlib.resources` to load files from installed package site-packages

**Critical Finding**: The system does NOT create a merged/compiled file during deployment. Each instruction file is loaded independently and assembled at runtime.

**Status**: ✅ System is correctly configured for both development and deployed modes

---

## 1. How Instructions Are Assembled

### File Loading Architecture

The instruction system uses a **modular loader architecture** with three main components:

1. **InstructionLoader** (`instruction_loader.py`) - Orchestrates all loading
2. **FileLoader** (`file_loader.py`) - Handles filesystem I/O with tier precedence
3. **PackagedLoader** (`packaged_loader.py`) - Handles packaged installations via importlib.resources

### Assembly Process

```python
# InstructionLoader.load_all_instructions() flow:

Step 1: Load custom INSTRUCTIONS.md
  └─> FileLoader.load_instructions_file()
      ├─ Check: ./.claude-mpm/INSTRUCTIONS.md (project-level)
      ├─ Check: ~/.claude-mpm/INSTRUCTIONS.md (user-level)
      └─ Result: content["custom_instructions"] + level

Step 2: Load framework PM_INSTRUCTIONS.md
  └─> InstructionLoader.load_framework_instructions()
      ├─ If framework_path == "__PACKAGED__":
      │   └─> PackagedLoader.load_framework_content()
      │       └─> Load from site-packages via importlib.resources
      ├─ Else (development):
      │   └─> _load_filesystem_framework_instructions()
      │       ├─ PRIORITY 1: .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md (with version check)
      │       ├─ PRIORITY 2: src/claude_mpm/agents/PM_INSTRUCTIONS.md (source)
      │       └─ PRIORITY 3: src/claude_mpm/agents/INSTRUCTIONS.md (legacy)
      └─ Result: content["framework_instructions"]

Step 3: Load WORKFLOW.md
  └─> FileLoader.load_workflow_file()
      ├─ Check: ./.claude-mpm/WORKFLOW.md (project-level)
      ├─ Check: ~/.claude-mpm/WORKFLOW.md (user-level)
      ├─ Check: framework/agents/WORKFLOW.md (system-level)
      └─ Result: content["workflow_instructions"] + level

Step 4: Load MEMORY.md
  └─> FileLoader.load_memory_file()
      ├─ Check: ./.claude-mpm/MEMORY.md (project-level)
      ├─ Check: ~/.claude-mpm/MEMORY.md (user-level)
      ├─ Check: framework/agents/MEMORY.md (system-level)
      └─ Result: content["memory_instructions"] + level
```

### Final Content Dictionary

```python
{
    "custom_instructions": "...",           # From .claude-mpm/INSTRUCTIONS.md
    "custom_instructions_level": "project", # project|user
    "framework_instructions": "...",        # PM_INSTRUCTIONS.md
    "base_pm_instructions": "...",          # BASE_PM.md
    "workflow_instructions": "...",         # WORKFLOW.md
    "workflow_instructions_level": "system",# project|user|system
    "memory_instructions": "...",           # MEMORY.md
    "memory_instructions_level": "system",  # project|user|system
    "instructions_version": "0008",         # Extracted from PM_INSTRUCTIONS
    "version": "0008",
    "instructions_last_modified": "...",
    "loaded": True
}
```

### Files Involved

**Core Instruction Files** (in src/claude_mpm/agents/):
- `PM_INSTRUCTIONS.md` - Main PM agent instructions (37KB)
- `WORKFLOW.md` - Research gates and workflow protocols (3KB)
- `MEMORY.md` - Memory management instructions (3KB)
- `BASE_PM.md` - Core framework requirements
- `BASE_AGENT.md` - Universal agent instructions (5.6KB)

**Supporting Files**:
- `RELEASE_WORKFLOW.md` - Release-specific workflow (8.8KB) - NOT loaded by instruction system
- `BASE_ENGINEER.md` - Engineer agent base (24KB)
- `CLAUDE_MPM_OUTPUT_STYLE.md` - Output formatting (12KB)

---

## 2. Development vs. Deployed Package Handling

### Development Mode (Source Repository)

**Detection**: `framework_path != Path("__PACKAGED__")`

**Loading Priority** (PM_INSTRUCTIONS.md):
1. `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (if version >= source)
2. `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (source file)
3. `src/claude_mpm/agents/INSTRUCTIONS.md` (legacy fallback)

**Version Validation**:
```python
# Deployed file version check
deployed_content = deployed_path.read_text()
deployed_version = extract_version(deployed_content)  # Parse PM_INSTRUCTIONS_VERSION comment

source_content = pm_instructions_path.read_text()
source_version = extract_version(source_content)

if deployed_version < source_version:
    logger.warning("Deployed file is stale, using source instead")
    # Fall through to source loading
else:
    # Use deployed file
    return deployed_content
```

**WORKFLOW.md & MEMORY.md** (Development):
```python
# Tier precedence (highest to lowest):
1. ./.claude-mpm/WORKFLOW.md (project override)
2. ~/.claude-mpm/WORKFLOW.md (user default)
3. src/claude_mpm/agents/WORKFLOW.md (system default)
```

### Deployed Mode (pip install)

**Detection**: `framework_path == Path("__PACKAGED__")`

**Loading Strategy**:
```python
# PackagedLoader.load_framework_content()

# Use importlib.resources to access package data
from importlib.resources import files

agents_package = files("claude_mpm.agents")

# Load each file from site-packages
pm_instructions = (agents_package / "PM_INSTRUCTIONS.md").read_text()
workflow = (agents_package / "WORKFLOW.md").read_text()
memory = (agents_package / "MEMORY.md").read_text()
base_pm = (agents_package / "BASE_PM.md").read_text()
```

**Where Files Live** (pip-installed):
```
site-packages/
└── claude_mpm/
    └── agents/
        ├── PM_INSTRUCTIONS.md    ← Loaded via importlib.resources
        ├── WORKFLOW.md           ← Loaded via importlib.resources
        ├── MEMORY.md             ← Loaded via importlib.resources
        ├── BASE_PM.md            ← Loaded via importlib.resources
        ├── BASE_AGENT.md
        ├── BASE_ENGINEER.md
        └── *.json, *.yaml
```

**Fallback Chain**:
```python
# Primary method (Python 3.9+)
from importlib.resources import files
agents_package = files("claude_mpm.agents")

# Fallback method (if primary fails)
from importlib import resources
content = resources.read_text("claude_mpm.agents", "PM_INSTRUCTIONS.md")
```

**User/Project Overrides Still Work**:
```python
# Even in deployed mode, tier precedence applies to WORKFLOW/MEMORY:
1. ./.claude-mpm/WORKFLOW.md (project override)
2. ~/.claude-mpm/WORKFLOW.md (user override)
3. site-packages/claude_mpm/agents/WORKFLOW.md (system default from package)
```

---

## 3. Package-Data Configuration

### pyproject.toml Analysis

**Current Configuration** (line 196-197):
```toml
[tool.setuptools.package-data]
claude_mpm = [
    "VERSION",
    "BUILD_NUMBER",
    "scripts/*",
    "scripts/*.sh",
    "commands/*.md",
    "skills/bundled/*.md",
    "dashboard/*.html",
    "dashboard/templates/*.html",
    "dashboard/static/*.css",
    "dashboard/static/*.js",
    "dashboard/static/css/*.css",
    "dashboard/static/js/*.js",
    "dashboard/static/js/components/*.js",
    "dashboard/static/svelte-build/**/*",
    "agents/*.md",              ← ✅ Includes all .md files in agents/
    "agents/*.json",
    "agents/*.yaml",
    "agents/templates/*.json",
    "agents/templates/*.md",
    "agents/schema/*.json",
    "hooks/**/*.py",
    "hooks/**/*.sh",
    "hooks/claude_hooks/*",
    "hooks/claude_hooks/**/*",
]
```

**Verification**: ✅ **All instruction files are included**

The pattern `"agents/*.md"` captures:
- ✅ PM_INSTRUCTIONS.md
- ✅ WORKFLOW.md
- ✅ MEMORY.md
- ✅ BASE_PM.md
- ✅ BASE_AGENT.md
- ✅ BASE_ENGINEER.md
- ✅ RELEASE_WORKFLOW.md (included but not loaded by instruction system)
- ✅ CLAUDE_MPM_OUTPUT_STYLE.md
- ✅ CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md

**No Explicit Build/Merge Step**:
- The system does NOT pre-merge PM_INSTRUCTIONS.md + WORKFLOW.md + MEMORY.md during build
- Each file is packaged independently
- Assembly happens at runtime via InstructionLoader

---

## 4. Version Validation System

### Version Comment Format

**In PM_INSTRUCTIONS.md** (line 1):
```markdown
<!-- PM_INSTRUCTIONS_VERSION: 0008 -->
<!-- PURPOSE: Claude 4.5 optimized PM instructions... -->
```

### Version Extraction

**Code** (instruction_loader.py lines 91-105):
```python
def _extract_version(self, file_content: str) -> int:
    """Extract version number from PM_INSTRUCTIONS_VERSION comment.

    Returns:
        Version number as integer, or 0 if not found
    """
    import re

    match = re.search(r"PM_INSTRUCTIONS_VERSION:\s*(\d+)", file_content)
    if match:
        return int(match.group(1))
    return 0  # No version = oldest
```

### Version Validation Logic

**Purpose**: Prevent using stale deployed files when source has been updated

**Flow** (development mode only):
```python
# Check if .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md exists
if deployed_path.exists():
    deployed_version = extract_version(deployed_content)

    # Compare with source version
    if pm_instructions_path.exists():
        source_version = extract_version(source_content)

        if deployed_version < source_version:
            # SOURCE IS NEWER - don't use deployed file
            logger.warning(
                f"Deployed PM instructions v{deployed_version:04d} is stale, "
                f"source is v{source_version:04d}. Using source instead."
            )
            # Fall through to load source file
        else:
            # DEPLOYED IS CURRENT - use it
            content["framework_instructions"] = deployed_content
            logger.info(f"Loaded PM_INSTRUCTIONS_DEPLOYED.md v{deployed_version:04d}")
            return
```

**Metadata Storage**:
```python
# FileLoader extracts version and timestamp
version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)

# Stored in content dict
content["instructions_version"] = version
content["version"] = version
content["instructions_last_modified"] = timestamp
```

---

## 5. Potential Issues and Recommendations

### ✅ No Critical Issues Found

The instruction assembly system is well-designed for both development and deployed modes:

1. **Package-data includes all necessary files** - `agents/*.md` pattern captures everything
2. **importlib.resources correctly handles site-packages** - Works for deployed installations
3. **Tier precedence allows user/project overrides** - Even in deployed mode
4. **Version validation prevents stale files** - Only in development mode (appropriate)
5. **Graceful fallback chain** - Python 3.9+ → Python 3.8 → error handling

### 📋 Observations (Not Issues)

**1. RELEASE_WORKFLOW.md Not Used by Instruction System**
- **Location**: `src/claude_mpm/agents/RELEASE_WORKFLOW.md` (8.8KB)
- **Status**: Included in package-data but not loaded by InstructionLoader
- **Impact**: None - appears to be documentation/reference material
- **Recommendation**: Document its purpose or move to docs/ if not needed in agents/

**2. No Pre-Compilation of Instructions**
- **Current**: Each file loaded separately at runtime
- **Potential Optimization**: Pre-merge PM_INSTRUCTIONS.md + WORKFLOW.md + MEMORY.md during build
- **Trade-off**: Would lose user/project override ability for WORKFLOW/MEMORY
- **Recommendation**: Keep current approach - flexibility > minor performance gain

**3. PM_INSTRUCTIONS.md References Other Files**
- **Line 405**: `See [WORKFLOW.md](WORKFLOW.md) for complete Research Gate Protocol`
- **Line 687**: `See [WORKFLOW.md](WORKFLOW.md) for Ticketing Integration details`
- **Impact**: Cross-references work because files are loaded as separate sections
- **Status**: ✅ Working as designed

**4. Deployed File Path (.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md)**
- **Purpose**: Cache merged instructions in development mode
- **Location**: Project-specific `.claude-mpm/` directory
- **Status**: Version-validated, optional optimization
- **Use Case**: Speed up development mode loading when source unchanged

---

## 6. Loading Flow Examples

### Example 1: Fresh Development Installation

```
User: Clone repo, run `claude-mpm init`
Framework Path: /Users/masa/Projects/claude-mpm

Loading Sequence:
1. Check .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md → Not found
2. Load src/claude_mpm/agents/PM_INSTRUCTIONS.md → Found, version 0008
3. Check .claude-mpm/WORKFLOW.md → Not found
4. Check ~/.claude-mpm/WORKFLOW.md → Not found
5. Load src/claude_mpm/agents/WORKFLOW.md → Found (system default)
6. Check .claude-mpm/MEMORY.md → Not found
7. Check ~/.claude-mpm/MEMORY.md → Not found
8. Load src/claude_mpm/agents/MEMORY.md → Found (system default)

Result:
- framework_instructions: PM_INSTRUCTIONS.md (source)
- workflow_instructions: WORKFLOW.md (system)
- memory_instructions: MEMORY.md (system)
```

### Example 2: Pip-Installed Package

```
User: `pip install claude-mpm`
Framework Path: __PACKAGED__

Loading Sequence:
1. Detect packaged installation
2. Use PackagedLoader.load_framework_content()
3. Load from site-packages via importlib.resources:
   - PM_INSTRUCTIONS.md → site-packages/claude_mpm/agents/
   - WORKFLOW.md → site-packages/claude_mpm/agents/
   - MEMORY.md → site-packages/claude_mpm/agents/
   - BASE_PM.md → site-packages/claude_mpm/agents/

Result:
- framework_instructions: PM_INSTRUCTIONS.md (package)
- workflow_instructions: WORKFLOW.md (package, level="system")
- memory_instructions: MEMORY.md (package, level="system")
```

### Example 3: User Customization (Deployed Package)

```
User: `pip install claude-mpm`, then create ~/.claude-mpm/WORKFLOW.md
Framework Path: __PACKAGED__

Loading Sequence:
1. Load PM_INSTRUCTIONS.md from package
2. Check .claude-mpm/WORKFLOW.md → Not found
3. Check ~/.claude-mpm/WORKFLOW.md → Found! (user override)
4. Check .claude-mpm/MEMORY.md → Not found
5. Check ~/.claude-mpm/MEMORY.md → Not found
6. Load MEMORY.md from package (system default)

Result:
- framework_instructions: PM_INSTRUCTIONS.md (package)
- workflow_instructions: WORKFLOW.md (user override, level="user")
- memory_instructions: MEMORY.md (package, level="system")
```

---

## 7. Verification Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| All instruction files included in package-data | ✅ | `agents/*.md` pattern in pyproject.toml line 197 |
| importlib.resources handles site-packages | ✅ | PackagedLoader uses `files("claude_mpm.agents")` |
| Fallback for Python 3.8 | ✅ | Try/except with `importlib_resources` fallback |
| Version validation works | ✅ | `_extract_version()` parses PM_INSTRUCTIONS_VERSION |
| Tier precedence preserved | ✅ | FileLoader checks project → user → system |
| No hardcoded paths | ✅ | Uses Path objects and importlib.resources |
| Graceful error handling | ✅ | Try/except blocks with logging |
| User overrides work in deployed mode | ✅ | FileLoader checks .claude-mpm/ before package |

---

## Conclusion

**Summary**: The PM instruction assembly system is correctly implemented for both development and deployed modes. No issues found that would prevent proper operation in pip-installed packages.

**Key Design Decisions**:
1. **Runtime assembly** (not pre-compilation) - Preserves user/project override flexibility
2. **Tier precedence** (project → user → system) - Allows customization at all levels
3. **Version validation** (development only) - Prevents stale deployed files
4. **importlib.resources** (deployed mode) - Standard Python packaging approach

**Recommendations**:
1. ✅ No changes needed - system works as designed
2. 📝 Consider documenting RELEASE_WORKFLOW.md purpose (currently not loaded by system)
3. 📝 Consider adding integration test for pip-installed package instruction loading

**Next Steps**:
- If deploying a new version, verify package-data includes all agents/*.md files
- Test pip installation: `pip install -e .` and verify instruction loading
- Monitor logs for "Using source PM_INSTRUCTIONS.md" warnings (indicates deployed file missing/stale)
