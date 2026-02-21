# Verification Results: End-to-End Testing and Edge Cases

## 1. Code Path Verification

### Deployed Agents Name Origin

**Verified**: `AgentManager.list_agents()` uses file stems as dict keys.

```python
# agent_management_service.py:327-330
for agent_file in self.project_dir.glob("*.md"):
    agent_name = agent_file.stem          # e.g., "svelte-engineer"
    entry = _build_agent_entry(agent_file, agent_name, "project")
    if entry:
        agents[agent_name] = entry        # key = "svelte-engineer"
```

```python
# config_routes.py:316-318
agents_list = [
    {"name": name, **details} for name, details in agents_data.items()
]
# name = "svelte-engineer" (dict key = file stem)
```

**Result**: Deployed agent names are always kebab-case file stems.

### Available Agents Name Origin

**Verified**: `RemoteAgentDiscoveryService._parse_markdown_agent()` extracts two separate fields.

```python
# remote_agent_discovery_service.py:612-616
if frontmatter and "name" in frontmatter:
    name = frontmatter["name"]           # "Svelte Engineer"
```

```python
# remote_agent_discovery_service.py:700-709
return {
    "agent_id": agent_id,               # "svelte-engineer"
    "metadata": {
        "name": name,                    # "Svelte Engineer"
    },
}
```

```python
# config_routes.py:368-372
for agent in agents:
    metadata = agent.get("metadata", {})
    agent.setdefault("name", metadata.get("name", agent.get("agent_id", "")))
    # Sets name = "Svelte Engineer" (because "name" key doesn't exist yet)
```

**Result**: Available agent `name` = human-readable from YAML frontmatter.

### is_deployed Comparison

**Verified**: Comparison uses wrong field.

```python
# config_routes.py:388-392
deployed_names = agent_mgr.list_agent_names(location="project")
# → {"svelte-engineer", "python-engineer", ...}

for agent in agents:
    agent_name = agent.get("name", agent.get("agent_id", ""))
    # → "Svelte Engineer" (because "name" was set to metadata.name above)
    agent["is_deployed"] = agent_name in deployed_names
    # → False (always)
```

**Result**: `is_deployed` is structurally broken - always returns false.

## 2. Edge Cases Identified

### Edge Case 1: Agents Without YAML Frontmatter

If an agent markdown file has no YAML frontmatter:
- `agent_id` falls back to `md_file.stem` (e.g., "custom-agent")
- `name` falls back to first heading, then to `md_file.stem.replace("-", " ").title()` (e.g., "Custom Agent")
- The mismatch still occurs because the fallback name is title-cased.

### Edge Case 2: Agents Without `agent_id` in Frontmatter

If frontmatter exists but lacks `agent_id`:
- `agent_id` falls back to `md_file.stem`
- `name` comes from frontmatter `name` field
- Standard mismatch scenario.

### Edge Case 3: Agents Where name == agent_id

If an agent's YAML has `name: python-engineer` (kebab-case, matching agent_id):
- Both fields would be "python-engineer"
- `is_deployed` comparison would work correctly for this specific agent
- This is unlikely in practice - most agents use human-readable names

### Edge Case 4: Underscore vs Hyphen

The original prompt mentions `svelte_engineer` (underscore). In the codebase:
- Filenames use hyphens: `svelte-engineer.md`
- YAML `agent_id` uses hyphens: `svelte-engineer`
- If a file uses underscores (e.g., `svelte_engineer.md`), the file stem would be "svelte_engineer"
- The comparison would fail even harder: "Svelte Engineer" vs "svelte_engineer"

### Edge Case 5: Deploy Action with Wrong Name

When deploying via the UI:
```typescript
await deployAgent(agent.name);  // Sends "Svelte Engineer"
```

The deploy handler receives `agent_name = "Svelte Engineer"` and:
1. Validates it: `validate_safe_name("Svelte Engineer", "agent")` - **may reject** due to spaces
2. If it passes, tries to find it in cache: `svc.deploy_agent("Svelte Engineer", agents_dir)`
3. The deployment service may fail to find the cached agent

**Severity**: This could prevent deployment from the UI entirely.

### Edge Case 6: Agent Names with Special Characters

Agents like "C++ Engineer" or "C# Engineer" would have:
- `agent_id`: "cpp-engineer" or "csharp-engineer"
- `name`: "C++ Engineer" or "C# Engineer"
- File stem: "cpp-engineer" or "csharp-engineer"
- Deploy would definitely fail if `name` is sent instead of `agent_id`

### Edge Case 7: Duplicate Display Names

Two agents could have the same `name` but different `agent_id`:
- `engineer.md` with `name: "Engineer"`
- `backend-engineer.md` with `name: "Engineer"`
- The `name` field alone cannot disambiguate these

## 3. Cross-Reference: get_agent_path() Normalization

The `GitSourceManager.get_agent_path()` method (line 482-493) does handle some normalization:
```python
if name.lower().replace(" ", "-") == agent_name or agent_id == agent_name:
    return Path(agent.get("source_file", ""))
```

This converts "Svelte Engineer" → "svelte-engineer" for comparison. However, this normalization is:
1. Only applied in `get_agent_path()`, not in the API endpoint
2. Lossy: "AWS Ops" → "aws-ops" but the actual ID might be "aws-ops-agent"
3. Doesn't handle underscores, abbreviations, or other edge cases

## 4. Test Coverage Analysis

### Existing Tests

**File**: `tests/test_config_routes.py`

The test file likely has tests for the API endpoints, but the naming consistency issue may not be explicitly tested because:
- Tests may use mock data where `name` and `agent_id` happen to match
- The `is_deployed` comparison isn't tested against real discovery data
- Version comparison isn't tested end-to-end

### Recommended Test Additions

1. **Test `is_deployed` with realistic data**: Verify that agents with different `name` and `agent_id` formats still get correct `is_deployed` flags
2. **Test name consistency**: Verify that the `name` field in both deployed and available responses uses the same format
3. **Test deploy with available agent name**: Verify that deploying using the name from available agents response succeeds
4. **Test version comparison**: Verify that frontend can match deployed and available agents for version comparison

## 5. Related Previous Fixes

The codebase shows evidence of previous naming-related fixes:

1. **"MISMATCH FIX"** comments in `remote_agent_discovery_service.py` (lines 597-607)
   - Fixed: agent_id now uses YAML frontmatter value instead of hierarchical path
   - This was a partial fix that addressed agent_id consistency but didn't fix the name promotion

2. **Bug #2 fixes** in `git_source_manager.py` (line 402-418)
   - Fixed: deduplication uses `agent_id` for uniqueness
   - Confirms `agent_id` is recognized as the canonical identifier

3. **Test file**: `tests/test_agent_name_normalization.py`
   - Suggests awareness of naming normalization issues
   - May contain relevant test patterns for the fix

## 6. Summary of Findings

| Verification Area | Status | Finding |
|-------------------|--------|---------|
| Deployed name origin | Confirmed | File stems (kebab-case) |
| Available name origin | Confirmed | metadata.name (human-readable) |
| is_deployed comparison | **Broken** | Compares different formats |
| Frontend version match | **Broken** | name field format mismatch |
| Deploy action | **Risk** | May send wrong name format |
| agent_id consistency | Confirmed | Already consistent across sources |
| Previous fixes | Partial | agent_id fixed, name promotion not |
