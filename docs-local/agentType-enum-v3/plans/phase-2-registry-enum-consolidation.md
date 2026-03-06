# Phase 2: Registry & Enum Consolidation

**Goal**: Unify the identity and type systems to reduce fragmentation.
**Effort**: ~3-4 hours
**Risk**: MEDIUM (touching type system used by multiple consumers)
**Branch**: `fix/agent-naming-mvf` off `main`
**PR Target**: `main`
**Depends On**: Phase 1 be completed

---

## Prerequisites

Phase 1 must be completed. Verify:
```bash
# 1. agent_name_registry.py exists (from Phase 1 cherry-pick)
ls src/claude_mpm/core/agent_name_registry.py

# 2. CANONICAL_NAMES reconciled (from Phase 1 Change 6)
python -c "from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer; print(len(AgentNameNormalizer.CANONICAL_NAMES))"

# 3. Archive deleted (from Phase 1 Change 7)
ls src/claude_mpm/agents/templates/archive/ 2>/dev/null && echo "FAIL: archive still exists" || echo "OK: archive removed"

# 4. Drift test passes
uv run pytest tests/test_agent_name_drift.py -v
```

---

## Change 1: Extend `AgentType` Enum in `agent_definition.py`

**Problem**: `AgentType` enum has only 5 values (`CORE`, `PROJECT`, `CUSTOM`, `SYSTEM`, `SPECIALIZED`) but agent frontmatter `agent_type:` field uses ~15 distinct string values (e.g., `engineer`, `qa`, `ops`, `research`). 87% of frontmatter values don't map to any enum member — they all fall through to `CUSTOM` or `None`.

**Impact**: `_safe_parse_agent_type()` (wherever it exists) returns `CUSTOM` for most agents. Any code filtering by `AgentType` is effectively broken.

**Decision**: Extend existing enum, do NOT rename to `AgentCategory` (blast radius too large per devil's advocate).

### File: `src/claude_mpm/models/agent_definition.py`

**Current enum (lines 25-36)**:
```python
class AgentType(str, Enum):
    """Type classification for agents."""
    CORE = "core"
    PROJECT = "project"
    CUSTOM = "custom"
    SYSTEM = "system"
    SPECIALIZED = "specialized"
```

**New enum**:
```python
class AgentType(str, Enum):
    """Type classification for agents.

    Categories match the `agent_type:` frontmatter field values
    found in deployed agent .md files.
    """
    # Original values (preserved for backward compatibility)
    CORE = "core"
    PROJECT = "project"
    CUSTOM = "custom"
    SYSTEM = "system"
    SPECIALIZED = "specialized"

    # Agent role categories (match frontmatter agent_type: values)
    ENGINEER = "engineer"
    QA = "qa"
    OPS = "ops"
    RESEARCH = "research"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    VERSION_CONTROL = "version_control"
    DATA = "data"
    CONTENT = "content"
    MANAGEMENT = "management"

    @classmethod
    def from_frontmatter(cls, value: str) -> "AgentType":
        """Parse agent_type from frontmatter, with fallback to CUSTOM.

        Handles exact matches, common aliases, and partial matches.

        Args:
            value: The agent_type string from YAML frontmatter

        Returns:
            Matching AgentType enum member, or CUSTOM if no match
        """
        if not value:
            return cls.CUSTOM

        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")

        # Direct match
        for member in cls:
            if member.value == normalized:
                return member

        # Common aliases
        aliases = {
            "core_agent": cls.CORE,
            "specialized_agent": cls.SPECIALIZED,
            "project_agent": cls.PROJECT,
            "engineer_agent": cls.ENGINEER,
            "qa_agent": cls.QA,
            "ops_agent": cls.OPS,
            "research_agent": cls.RESEARCH,
            "security_agent": cls.SECURITY,
            "documentation_agent": cls.DOCUMENTATION,
            "version_control_agent": cls.VERSION_CONTROL,
            "data_agent": cls.DATA,
            "content_agent": cls.CONTENT,
            "management_agent": cls.MANAGEMENT,
            # Specific frontmatter values observed in the wild
            "code_analysis": cls.RESEARCH,
            "product_management": cls.MANAGEMENT,
            "prompt_engineering": cls.ENGINEER,
            "image_processing": cls.SPECIALIZED,
        }

        if normalized in aliases:
            return aliases[normalized]

        return cls.CUSTOM
```

**Verification**:
```bash
# Verify backward compatibility - existing code using AgentType.CORE etc still works
python -c "from claude_mpm.models.agent_definition import AgentType; print(AgentType.CORE, AgentType.ENGINEER)"

# Verify from_frontmatter works
python -c "
from claude_mpm.models.agent_definition import AgentType
assert AgentType.from_frontmatter('engineer') == AgentType.ENGINEER
assert AgentType.from_frontmatter('core_agent') == AgentType.CORE
assert AgentType.from_frontmatter('unknown_thing') == AgentType.CUSTOM
print('All assertions passed')
"

make test
```

**Guard Rail**: Do NOT rename `AgentType` to `AgentCategory`. Do NOT change any import paths. Existing code using `AgentType.CORE`, `AgentType.PROJECT`, etc. must continue to work unchanged.

---

## Change 2: Update `_safe_parse_agent_type()` Consumers

**Problem**: Code that parses `agent_type:` from frontmatter needs to use the new `from_frontmatter()` method.

### Find all consumers:
```bash
grep -rn "_safe_parse_agent_type\|safe_parse_agent\|AgentType(" src/claude_mpm/ --include="*.py" | grep -v __pycache__
```

For each consumer found, replace manual parsing with:
```python
agent_type = AgentType.from_frontmatter(frontmatter.get("agent_type", ""))
```

**Known files to check** (from research):
- `src/claude_mpm/core/unified_agent_registry.py` — has its own `AgentType` enum
- `src/claude_mpm/services/agents/loading/framework_agent_loader.py`
- `src/claude_mpm/services/agents/deployment/single_agent_deployer.py`
- `src/claude_mpm/models/agent_definition.py`

### Note on `unified_agent_registry.py`:

This file has its OWN `AgentType` enum (different from `agent_definition.py`):
```python
class AgentType(Enum):
    CORE = "core"
    SPECIALIZED = "specialized"
    USER_DEFINED = "user_defined"
    PROJECT = "project"
    MEMORY_AWARE = "memory_aware"
```

**Decision**: Do NOT merge these enums. They serve different purposes:
- `agent_definition.py:AgentType` = Role/category classification (what the agent DOES)
- `unified_agent_registry.py:AgentType` = Deployment tier classification (where the agent COMES FROM)

**Action**: Rename `unified_agent_registry.py:AgentType` to `AgentSourceType` for clarity:
```python
class AgentSourceType(Enum):
    """Classification by source/tier, NOT by role."""
    CORE = "core"
    SPECIALIZED = "specialized"
    USER_DEFINED = "user_defined"
    PROJECT = "project"
    MEMORY_AWARE = "memory_aware"
```

Then update all internal references within `unified_agent_registry.py` from `AgentType` → `AgentSourceType`. This is INTERNAL to the file — check for external consumers:
```bash
grep -rn "from.*unified_agent_registry.*import.*AgentType" src/claude_mpm/ --include="*.py" | grep -v __pycache__
```

Update any external imports found.

**Verification**:
```bash
# Verify no import errors
python -c "from claude_mpm.core.unified_agent_registry import AgentSourceType; print(AgentSourceType.CORE)"
python -c "from claude_mpm.models.agent_definition import AgentType; print(AgentType.CORE)"

make test
```

---

## Change 3: Consolidate CORE_AGENTS Lists

**Problem**: 4-5 separate `CORE_AGENTS` lists across different files, each with different format and different agent sets.

### Find all occurrences:
```bash
grep -rn "CORE_AGENTS" src/claude_mpm/ --include="*.py" | grep -v __pycache__
```

**Known locations on main**:
1. `src/claude_mpm/config/agent_presets.py`
2. `src/claude_mpm/services/agents/agent_recommendation_service.py`
3. `src/claude_mpm/services/agents/loading/framework_agent_loader.py`
4. `src/claude_mpm/services/agents/toolchain_detector.py`
5. `src/claude_mpm/services/config_api/agent_deployment_handler.py`

### Solution: Single source of truth

Create ONE canonical list in `agent_name_registry.py` (which was created in Phase 1):

```python
# Add to agent_name_registry.py:

# Core agents that should always be available
# These are the agent_id values (filename stems without .md)
CORE_AGENT_IDS: frozenset[str] = frozenset({
    "research",
    "engineer",
    "qa",
    "security",
    "local-ops",
    "version-control",
    "documentation",
    "code-analyzer",
})
```

Then update all 5 files to import from the registry:
```python
from claude_mpm.core.agent_name_registry import CORE_AGENT_IDS
```

**For each file**, the pattern change is:
```python
# BEFORE (each file has its own list):
CORE_AGENTS = ["research", "engineer", "qa", ...]

# AFTER (import from registry):
from claude_mpm.core.agent_name_registry import CORE_AGENT_IDS
# Use CORE_AGENT_IDS where needed
```

**Verification**:
```bash
# Verify no more local CORE_AGENTS definitions
grep -rn "CORE_AGENTS\s*=" src/claude_mpm/ --include="*.py" | grep -v __pycache__ | grep -v agent_name_registry
# Should return 0 results (only the registry should define it)

make test
```

---

## Change 4: Add Dynamic Refresh to Agent Name Registry

**Problem**: Hardcoded name maps go stale (proven by CANONICAL_NAMES)
**Solution**: Lazy dynamic refresh from deployed `.claude/agents/` files

### File: `src/claude_mpm/core/agent_name_registry.py`

Add a function that reads deployed agents and refreshes the mapping:

```python
import re
from pathlib import Path
from typing import Dict, Optional

import yaml

# The hardcoded baseline (from Phase 1)
AGENT_NAME_MAP: Dict[str, str] = {
    # ... existing entries ...
}

# Runtime cache (populated lazily)
_runtime_name_map: Optional[Dict[str, str]] = None


def get_agent_name_map() -> Dict[str, str]:
    """Get agent name map with runtime refresh from deployed agents.

    Priority:
    1. Runtime-discovered agents from .claude/agents/ (most current)
    2. Cached agents from ~/.claude-mpm/cache/agents/ (second choice)
    3. Hardcoded AGENT_NAME_MAP (fallback for testing/CI)

    Returns:
        Dict mapping agent_id (filename stem) to name: field value
    """
    global _runtime_name_map

    if _runtime_name_map is not None:
        return _runtime_name_map

    # Start with hardcoded baseline
    result = dict(AGENT_NAME_MAP)

    # Try to discover from deployed agents
    discovered = _discover_agents_from_paths([
        Path.cwd() / ".claude" / "agents",
        Path.home() / ".claude-mpm" / "cache" / "agents",
    ])

    # Override hardcoded with discovered (discovered is fresher)
    result.update(discovered)

    _runtime_name_map = result
    return result


def invalidate_cache() -> None:
    """Invalidate the runtime cache (call after deployment)."""
    global _runtime_name_map
    _runtime_name_map = None


def _discover_agents_from_paths(search_paths: list[Path]) -> Dict[str, str]:
    """Read agent .md files and extract name: field values.

    Args:
        search_paths: Directories to search for agent .md files

    Returns:
        Dict mapping filename stem to name: value
    """
    discovered = {}
    for dir_path in search_paths:
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.glob("*.md")):
            content = md_file.read_text(errors="replace")
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1))
                    if isinstance(frontmatter, dict) and "name" in frontmatter:
                        discovered[md_file.stem] = frontmatter["name"]
                except (yaml.YAMLError, Exception):
                    pass
    return discovered
```

**Verification**:
```bash
# Test with cache available
python -c "
from claude_mpm.core.agent_name_registry import get_agent_name_map
name_map = get_agent_name_map()
print(f'Found {len(name_map)} agents')
for k, v in sorted(name_map.items())[:5]:
    print(f'  {k} → {v}')
"

make test
```

---

## Change 5: Align `agents_metadata.py` Type System (if file exists)

**Problem**: `agents_metadata.py` may have its own type constants/classes that duplicate `AgentType`
**Condition**: Only apply if `agents_metadata.py` exists on main after Phase 1

### Pre-check:
```bash
ls src/claude_mpm/core/agents_metadata.py 2>/dev/null
```

**If NOT found**: Skip this change. The file does not exist on main (confirmed by baseline audit).

**If found** (created by Phase 1 or future work): Ensure it imports `AgentType` from `agent_definition.py` rather than defining its own type constants.

---

## Change 6: Standardize Frontmatter Field `type:` → `agent_type:` (AMENDMENT)

**Problem**: The user's instructions explicitly require standardizing on `agent_type` as the frontmatter field name (Motivation 1b, Critical #3). Code is split — some reads `"type"`, some reads `"agent_type"`, creating inconsistency.

**Impact**: No immediate delegation failure (this is a metadata field, not `name:`), but creates confusion and bugs when filtering/categorizing agents.

### Discovery:
```bash
# Find all code that reads "type" from agent-related data (not "agent_type")
grep -rn '\.get.*"type"' src/claude_mpm/services/agents/ --include="*.py" | grep -v __pycache__ | grep -v agent_type
grep -rn 'getattr.*"type"' src/claude_mpm/services/agents/ --include="*.py" | grep -v __pycache__
grep -rn '\.get.*"type"' src/claude_mpm/core/ --include="*.py" | grep -v __pycache__ | grep -v agent_type
```

### Known files to fix (confirmed on main):

**A. `src/claude_mpm/services/agents/registry/deployed_agent_discovery.py`**:

Line 109: `agent.get("type", agent.get("name", "unknown"))` → `agent.get("agent_type", agent.get("type", agent.get("name", "unknown")))`
Line 133: `agent_type = getattr(agent, "type", None)` → `agent_type = getattr(agent, "agent_type", None) or getattr(agent, "type", None)`
Line 193: `json_data.get("agent_type", registry_info.get("type", "unknown"))` — already correct (reads agent_type first with type fallback)

**B. `src/claude_mpm/services/agents/deployment/deployment_wrapper.py`**:

Line 111: `"type": agent.get("type", "agent")` → `"type": agent.get("agent_type", agent.get("type", "agent"))`

### Pattern for all fixes:

```python
# BEFORE (reads only "type"):
agent_type = data.get("type", "")

# AFTER (reads "agent_type" first, falls back to "type" for backward compat):
agent_type = data.get("agent_type", data.get("type", ""))
```

The fallback to `"type"` ensures backward compatibility with any existing frontmatter that uses the old field name. Over time, the fallback can be deprecated.

### Additional: Upstream notification

Create a note/issue for the `claude-mpm-agents` repository: all agent `.md` files should use `agent_type:` (not `type:`) in their YAML frontmatter. This is an upstream change that doesn't block our work but should be tracked.

### Verification:
```bash
# After fixes, all agent-type reads should prefer "agent_type":
grep -rn '\.get.*"type"' src/claude_mpm/services/agents/ --include="*.py" | grep -v __pycache__ | grep -v agent_type | grep -v "content_type\|file_type\|event_type\|source_type\|msg_type\|check_type\|error_type\|log_type"
# Should return 0 results for agent-frontmatter-related code

make test
```

---

## Commit Strategy

Three logical commits (updated from two):

### Commit 1: Enum extension and `AgentSourceType` rename
```bash
git add src/claude_mpm/models/agent_definition.py
git add src/claude_mpm/core/unified_agent_registry.py
# Add any files that import AgentType from unified_agent_registry
git commit -m "refactor: extend AgentType enum with role categories, rename registry AgentType to AgentSourceType

- Add 10 new role-based categories to AgentType (engineer, qa, ops, etc.)
- Add AgentType.from_frontmatter() classmethod for safe parsing
- Rename unified_agent_registry.AgentType to AgentSourceType for clarity
- Update all internal consumers of the renamed enum

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### Commit 2: CORE_AGENTS consolidation and dynamic refresh
```bash
git add src/claude_mpm/core/agent_name_registry.py
git add src/claude_mpm/config/agent_presets.py
git add src/claude_mpm/services/agents/agent_recommendation_service.py
git add src/claude_mpm/services/agents/loading/framework_agent_loader.py
git add src/claude_mpm/services/agents/toolchain_detector.py
git add src/claude_mpm/services/config_api/agent_deployment_handler.py
git commit -m "refactor: consolidate CORE_AGENTS into registry and add dynamic refresh

- Define single CORE_AGENT_IDS in agent_name_registry.py
- Replace 5 separate CORE_AGENTS lists with registry import
- Add lazy dynamic refresh from deployed agent files
- Hardcoded map serves as fallback for testing/CI

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### Commit 3: Frontmatter field standardization
```bash
git add src/claude_mpm/services/agents/registry/deployed_agent_discovery.py
git add src/claude_mpm/services/agents/deployment/deployment_wrapper.py
# Add any other files found by discovery grep
git commit -m "fix: standardize frontmatter field 'agent_type' over 'type'

- All agent-frontmatter readers now prefer 'agent_type' with 'type' fallback
- Backward compatible: existing 'type' fields still work
- Aligns with upstream agent definition standard

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Tests to Add

### File: `tests/test_agent_type_enum.py`
```python
"""Test AgentType enum extension and from_frontmatter parsing."""

import pytest
from claude_mpm.models.agent_definition import AgentType


class TestAgentTypeEnum:
    """Verify AgentType enum covers all frontmatter values."""

    def test_original_values_preserved(self):
        """Original enum values must not change."""
        assert AgentType.CORE.value == "core"
        assert AgentType.PROJECT.value == "project"
        assert AgentType.CUSTOM.value == "custom"
        assert AgentType.SYSTEM.value == "system"
        assert AgentType.SPECIALIZED.value == "specialized"

    def test_new_role_categories(self):
        """New role categories exist."""
        assert AgentType.ENGINEER.value == "engineer"
        assert AgentType.QA.value == "qa"
        assert AgentType.OPS.value == "ops"
        assert AgentType.RESEARCH.value == "research"

    def test_from_frontmatter_exact_match(self):
        """Exact string values map correctly."""
        assert AgentType.from_frontmatter("engineer") == AgentType.ENGINEER
        assert AgentType.from_frontmatter("core") == AgentType.CORE
        assert AgentType.from_frontmatter("qa") == AgentType.QA

    def test_from_frontmatter_aliases(self):
        """Common aliases map correctly."""
        assert AgentType.from_frontmatter("core_agent") == AgentType.CORE
        assert AgentType.from_frontmatter("engineer_agent") == AgentType.ENGINEER

    def test_from_frontmatter_unknown(self):
        """Unknown values fall back to CUSTOM."""
        assert AgentType.from_frontmatter("totally_unknown") == AgentType.CUSTOM
        assert AgentType.from_frontmatter("") == AgentType.CUSTOM
        assert AgentType.from_frontmatter(None) == AgentType.CUSTOM

    def test_from_frontmatter_normalization(self):
        """Input is normalized before matching."""
        assert AgentType.from_frontmatter("  Engineer  ") == AgentType.ENGINEER
        assert AgentType.from_frontmatter("version-control") == AgentType.VERSION_CONTROL
        assert AgentType.from_frontmatter("Version_Control") == AgentType.VERSION_CONTROL
```

### File: `tests/test_agent_registry_dynamic.py`
```python
"""Test dynamic agent name registry refresh."""

from unittest.mock import patch
from pathlib import Path

import pytest
from claude_mpm.core.agent_name_registry import (
    AGENT_NAME_MAP,
    get_agent_name_map,
    invalidate_cache,
    CORE_AGENT_IDS,
)


class TestAgentNameRegistry:
    """Verify registry provides correct agent names."""

    def setup_method(self):
        """Reset cache before each test."""
        invalidate_cache()

    def test_hardcoded_baseline_exists(self):
        """AGENT_NAME_MAP has entries."""
        assert len(AGENT_NAME_MAP) > 20

    def test_core_agent_ids_are_subset(self):
        """Core agents must all be in the name map."""
        name_map = get_agent_name_map()
        for agent_id in CORE_AGENT_IDS:
            assert agent_id in name_map, f"Core agent '{agent_id}' not in name map"

    def test_get_agent_name_map_returns_dict(self):
        """get_agent_name_map() returns a dict."""
        result = get_agent_name_map()
        assert isinstance(result, dict)
        assert len(result) >= len(AGENT_NAME_MAP)  # At least hardcoded

    def test_invalidate_cache(self):
        """invalidate_cache() forces re-discovery on next call."""
        # Populate cache
        first = get_agent_name_map()
        # Invalidate
        invalidate_cache()
        # Next call should re-discover
        second = get_agent_name_map()
        assert isinstance(second, dict)

    def test_non_conforming_names_preserved(self):
        """Non-conforming upstream name: values must be exact."""
        name_map = get_agent_name_map()
        non_conforming = {
            "ticketing": "ticketing_agent",
            "nestjs-engineer": "nestjs-engineer",
            "real-user": "real-user",
        }
        for agent_id, expected_name in non_conforming.items():
            if agent_id in name_map:
                assert name_map[agent_id] == expected_name, (
                    f"Non-conforming name for '{agent_id}': "
                    f"expected '{expected_name}', got '{name_map[agent_id]}'"
                )
```

---

## Full Test Verification

```bash
# 1. Run full test suite
make test

# 2. Run new tests specifically
uv run pytest tests/test_agent_type_enum.py tests/test_agent_registry_dynamic.py tests/test_agent_name_drift.py -v

# 3. Verify no import errors across the codebase
python -c "import claude_mpm; print('Import OK')"

# 4. Verify AgentType backward compatibility
python -c "
from claude_mpm.models.agent_definition import AgentType
# Old code patterns still work
t = AgentType.CORE
assert t.value == 'core'
assert AgentType('core') == AgentType.CORE
print('Backward compatibility: OK')
"
```

---

## Rollback Strategy

**Commit 1** (enum + rename): Revert restores original `AgentType` and `AgentType` in registry.
```bash
git revert <commit-1-hash>
```

**Commit 2** (CORE_AGENTS + dynamic refresh): Revert restores local CORE_AGENTS lists.
```bash
git revert <commit-2-hash>
```

**Risk**: Medium. The `AgentSourceType` rename in `unified_agent_registry.py` requires updating external consumers. If consumers are missed, `ImportError` at runtime. Mitigated by:
1. grep for ALL `from.*unified_agent_registry.*import.*AgentType` patterns before committing
2. Full test suite catches import errors
3. Independent revertability per commit

---

## Success Criteria

1. `AgentType.from_frontmatter()` correctly parses ALL observed frontmatter `agent_type:` values
2. Zero `CUSTOM` fallbacks for known agent types
3. Single `CORE_AGENT_IDS` definition in registry (no duplicates across codebase)
4. Dynamic refresh discovers agents from `.claude/agents/` and cache
5. All existing tests pass (backward compatibility)
6. New tests verify enum parsing, registry refresh, and drift detection
7. `make test` passes with no regressions
