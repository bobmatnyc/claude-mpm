# Research: Agent Recommendation Asterisk Mismatch

**Date**: 2025-12-10
**Issue**: Configure command showing asterisks on wrong agents
**Status**: Root cause identified

## Executive Summary

The agent recommendation asterisks in `claude-mpm configure` are sourced from **AgentRecommendationService.CORE_AGENTS**, NOT from **ToolchainDetector.CORE_AGENTS**. These two constants have diverged, causing the mismatch.

**Quick Fix**: Update `AgentRecommendationService.CORE_AGENTS` to match the new core agent list.

---

## Root Cause Analysis

### The Problem

After updating `ToolchainDetector.CORE_AGENTS` to:
```python
CORE_AGENTS = [
    "qa-agent",
    "research-agent",
    "documentation-agent",
    "ticketing",
    "local-ops-agent",
]
```

The configure command still shows asterisks on OLD agents:
- ❌ HAS asterisk (wrong): code-analyzer, content-agent, mpm-agent-manager
- ❌ MISSING asterisk (should have): documentation-agent, research-agent, local-ops-agent, qa-agent

### Code Path That Determines Asterisks

**File**: `src/claude_mpm/cli/commands/configure.py`

**Flow**:
1. **Line 1074-1076**: Gets recommended agents
   ```python
   recommended_agents = self.recommendation_service.get_recommended_agents(
       str(self.project_dir)
   )
   ```

2. **Line 1160-1166**: Checks if agent is recommended
   ```python
   is_recommended = False
   for recommended_id in recommended_agents:
       recommended_leaf = recommended_id.split("/")[-1] if "/" in recommended_id else recommended_id
       if agent_full_path == recommended_id or agent_leaf_name == recommended_leaf:
           is_recommended = True
           recommended_count += 1
           break
   ```

3. **Line 1169-1171**: Adds asterisk to display
   ```python
   agent_id_display = agent.name
   if is_recommended:
       agent_id_display += " *"
   ```

4. **Line 1263-1268**: Same logic in `_deploy_agents_unified()`
   ```python
   recommended_agent_ids = self.recommendation_service.get_recommended_agents(
       str(self.project_dir)
   )
   ```

5. **Line 1417-1420**: Adds asterisk in checkbox UI
   ```python
   choice_text = f"    {display_name}"
   if is_recommended:
       choice_text += " *"
   ```

### The Source of Truth

**File**: `src/claude_mpm/services/agents/agent_recommendation_service.py`

**Line 33-52**: The CORE_AGENTS constant that's actually used
```python
CORE_AGENTS = {
    # Universal agents
    "universal/code-analyzer",
    "universal/content-agent",
    "universal/memory-manager",
    "universal/product-owner",
    "universal/project-organizer",
    "universal/research",

    # Claude MPM agents
    "claude-mpm/mpm-agent-manager",
    "claude-mpm/mpm-skills-manager",

    # Essential agents for development
    "ops/core/ops",
    "documentation/documentation",
    "documentation/ticketing",
    "version-control/version-control",
    "security/security",
}
```

**Line 187-188**: This is what configure.py actually uses
```python
def get_recommended_agents(...) -> Set[str]:
    # Start with core agents (always recommended)
    recommended = self.CORE_AGENTS.copy()
```

### Why ToolchainDetector.CORE_AGENTS Exists

**File**: `src/claude_mpm/services/agents/toolchain_detector.py`

**Line 162-168**: A separate CORE_AGENTS list
```python
# Core agents always included (use exact agent IDs from repository)
CORE_AGENTS = [
    "qa-agent",
    "research-agent",
    "documentation-agent",
    "ticketing",
    "local-ops-agent",
]
```

**Line 390-391**: Used in `recommend_agents()` method
```python
def recommend_agents(self, toolchain: Dict[str, List[str]]) -> List[str]:
    # Add core agents (always included)
    recommended.update(self.CORE_AGENTS)
```

**CRITICAL FINDING**: `ToolchainDetector.recommend_agents()` is **NOT used** by `configure.py`. The ToolchainDetector is never instantiated or called in the configure flow.

---

## Architectural Analysis

### Two Recommendation Services

The codebase has **two separate recommendation systems** that have diverged:

1. **AgentRecommendationService** (used by configure.py)
   - File: `src/claude_mpm/services/agents/agent_recommendation_service.py`
   - Uses: ToolchainAnalyzerService (full analysis)
   - CORE_AGENTS: 12 agents (universal/*, claude-mpm/*, ops/*)
   - Purpose: Higher-level recommendations with universal agents

2. **ToolchainDetector** (NOT used by configure.py)
   - File: `src/claude_mpm/services/agents/toolchain_detector.py`
   - Uses: File pattern matching
   - CORE_AGENTS: 5 agents (qa-agent, research-agent, etc.)
   - Purpose: Lightweight toolchain detection

### Why Two Systems Exist

From AgentRecommendationService docstring (line 3-13):
```
WHY: Provides intelligent agent recommendations based on toolchain detection
and always-recommended core agents. Helps users discover and install the
most relevant agents for their project without manual selection.

DESIGN DECISION: Uses toolchain analysis to map detected languages/frameworks
to specific engineer agents, plus always includes universal/core agents.
```

From ToolchainDetector docstring (line 1-30):
```
WHY: Automatically detect project toolchain (languages, frameworks, build tools)
to recommend appropriate agents. This eliminates manual agent selection and
ensures projects get the right agents for their technology stack.

Design Decision: File Pattern-Based Detection

Instead of AST parsing or dependency analysis, we use simple file pattern
matching. This is fast, reliable, and works across all languages without
requiring language-specific parsers.
```

**Analysis**: These were meant for different use cases, but AgentRecommendationService now delegates to ToolchainAnalyzerService (line 19), creating redundancy.

---

## Where Recommendations Are Used

### 1. Configure Command (Primary Use Case)

**File**: `src/claude_mpm/cli/commands/configure.py`

**Usage 1**: Agent list display (line 1074-1076)
```python
recommended_agents = self.recommendation_service.get_recommended_agents(
    str(self.project_dir)
)
```

**Usage 2**: Agent deployment UI (line 1263-1268)
```python
recommended_agent_ids = self.recommendation_service.get_recommended_agents(
    str(self.project_dir)
)
```

**Result**: Asterisks shown in:
- Agent list table
- Interactive checkbox selection
- Recommendation summary stats

### 2. Detection Summary (Secondary Use Case)

**File**: `src/claude_mpm/cli/commands/configure.py`

**Line 1186-1197**: Shows detected languages/frameworks
```python
summary = self.recommendation_service.get_detection_summary(
    str(self.project_dir)
)
detected_langs = ", ".join(summary.get("detected_languages", [])) or "None"
detected_fws = ", ".join(summary.get("detected_frameworks", [])) or "None"
self.console.print(
    f"\n[dim]* = recommended for this project "
    f"(detected: {detected_langs})[/dim]"
)
```

### 3. Where ToolchainDetector IS Used

**File**: `src/claude_mpm/services/agents/agent_selection_service.py`

**Line 103**: Instantiated for auto-configure deployment
```python
self.toolchain_detector = ToolchainDetector()
```

**Line 307-329**: Used in `deploy_auto_configure()` method
```python
# Step 2: Detect toolchain
toolchain = self.toolchain_detector.detect_toolchain(project_path)

# Step 3: Recommend agents based on toolchain
recommended_agents = self.toolchain_detector.recommend_agents(toolchain)
```

**Purpose**: Auto-configure deployment mode (NOT used by configure command)

**Workflow**:
1. User runs deployment with auto-configure mode
2. AgentSelectionService uses ToolchainDetector to detect project
3. ToolchainDetector.recommend_agents() returns agent list
4. Deployment service deploys those agents

**Key Finding**: ToolchainDetector is used for **automated deployment**, not for **interactive configuration UI**. The configure command uses AgentRecommendationService instead.

---

## Fix Options

### Option 1: Update AgentRecommendationService.CORE_AGENTS (Recommended)

**Why**: Minimal change, aligns with new core agent strategy.

**Change**:
```python
# File: src/claude_mpm/services/agents/agent_recommendation_service.py
# Line 33-52

CORE_AGENTS = {
    # Core operations agents
    "qa-agent",
    "research-agent",
    "documentation-agent",
    "ticketing",
    "local-ops-agent",

    # Keep version-control and security as universally recommended
    "version-control/version-control",
    "security/security",
}
```

**Pros**:
- Simple, single-location change
- Aligns with updated ToolchainDetector.CORE_AGENTS
- Maintains existing recommendation service architecture

**Cons**:
- Loses universal/* agents (code-analyzer, content-agent, etc.)
- May break expectations if users rely on those agents

### Option 2: Consolidate Recommendation Systems

**Why**: Eliminate redundancy and single source of truth.

**Change**:
1. Make AgentRecommendationService use ToolchainDetector.CORE_AGENTS
2. Remove AgentRecommendationService.CORE_AGENTS
3. Import from ToolchainDetector

```python
# File: src/claude_mpm/services/agents/agent_recommendation_service.py
from ..toolchain_detector import ToolchainDetector

class AgentRecommendationService:
    def get_recommended_agents(...) -> Set[str]:
        # Use ToolchainDetector's core agents
        recommended = set(ToolchainDetector.CORE_AGENTS)
        # ... rest of logic
```

**Pros**:
- Single source of truth
- No future divergence
- Clear ownership of core agent list

**Cons**:
- Larger refactor
- Need to ensure ToolchainDetector.CORE_AGENTS includes all necessary agents
- May affect other parts of codebase

### Option 3: Deprecate ToolchainDetector Completely

**Why**: AgentRecommendationService is the modern replacement.

**Change**:
1. Keep AgentRecommendationService as-is
2. Update ToolchainDetector to use AgentRecommendationService
3. Mark ToolchainDetector as legacy

**Pros**:
- Maintains backward compatibility
- No disruption to existing configure.py flow

**Cons**:
- Keeps redundancy
- ToolchainDetector becomes a thin wrapper
- Doesn't solve the original problem

---

## Caching Considerations

**Question**: Are recommendations cached anywhere?

**Search needed**:
- Check if AgentRecommendationService results are cached
- Look for configuration files that might store recommendations
- Verify if recommendations are persisted between runs

**Hypothesis**: No caching found in code review. Recommendations are computed fresh each time `get_recommended_agents()` is called.

---

## Testing Considerations

### Files to Test After Fix

1. **Unit Tests**:
   - `tests/services/agents/test_agent_recommendation_service.py` (if exists)
   - Verify CORE_AGENTS returns expected set

2. **Integration Tests**:
   - Configure command with various project types
   - Verify asterisks appear on correct agents
   - Test recommendation count matches asterisk count

3. **User Scenarios**:
   - Fresh Python project → should recommend qa-agent, research-agent, etc.
   - TypeScript project → should recommend language-specific + core agents
   - Empty directory → should only show core agents

### Test Command

```bash
# After fix, verify recommendations
cd /path/to/test-project
claude-mpm configure --list-agents

# Expected: Asterisks on qa-agent, research-agent, documentation-agent, ticketing, local-ops-agent
# Plus any language-specific agents based on project
```

---

## Recommendation

**Primary Fix**: Update `AgentRecommendationService.CORE_AGENTS` (Option 1)

**Rationale**:
1. Lowest risk, smallest change surface
2. Aligns with stated intention to change core agents
3. Doesn't break existing architecture
4. Can consolidate systems in future refactor if needed

**IMPORTANT**: Both CORE_AGENTS lists should be updated:

1. **AgentRecommendationService.CORE_AGENTS** (for configure UI) - PRIMARY FIX
   - Used by: `claude-mpm configure` command
   - Affects: Asterisks in agent list and checkbox UI

2. **ToolchainDetector.CORE_AGENTS** (for auto-configure deployment) - ALREADY UPDATED
   - Used by: `AgentSelectionService.deploy_auto_configure()`
   - Affects: Automated deployment decisions

**Follow-up Work**:
1. Verify both services use same core agent strategy
2. Consider consolidation in next major version
3. Document architectural decision for two systems
4. Add integration tests for recommendation accuracy

---

## Files Analyzed

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/agent_recommendation_service.py` (291 lines)
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/toolchain_detector.py` (476 lines)
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` (lines 1070-1430)

**Memory Usage**: 3 files read (strategic sampling), ~800 lines analyzed

---

## Next Steps

1. **User Decision**: Choose Option 1, 2, or 3
2. **Implementation**: Apply selected fix
3. **Testing**: Verify asterisks show on correct agents
4. **Documentation**: Update docs if core agent strategy changes
5. **Communication**: Inform users if universal/* agents removed

---

## Appendix: Agent ID Formats

### Current Recommendation Formats

**AgentRecommendationService.CORE_AGENTS** (hierarchical paths):
- `universal/code-analyzer`
- `universal/content-agent`
- `claude-mpm/mpm-agent-manager`
- `ops/core/ops`
- `documentation/documentation`

**ToolchainDetector.CORE_AGENTS** (leaf names):
- `qa-agent`
- `research-agent`
- `documentation-agent`
- `ticketing`
- `local-ops-agent`

### Matching Logic

**File**: `src/claude_mpm/cli/commands/configure.py`
**Line 1160-1166**:

```python
for recommended_id in recommended_agents:
    # Check if the recommended_id matches either the full path or just the leaf name
    recommended_leaf = recommended_id.split("/")[-1] if "/" in recommended_id else recommended_id
    if agent_full_path == recommended_id or agent_leaf_name == recommended_leaf:
        is_recommended = True
```

**Matching Strategy**: Supports both formats
- Full path match: `universal/code-analyzer` == `universal/code-analyzer`
- Leaf name match: `code-analyzer` (leaf of `universal/code-analyzer`) == `code-analyzer`

**Implication**: As long as leaf names are unique, either format works. The mismatch is purely about which agents are in the CORE_AGENTS set, not the format.
