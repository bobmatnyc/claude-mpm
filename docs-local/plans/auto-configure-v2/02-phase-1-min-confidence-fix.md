# Phase 1: Fix min_confidence Default Mismatch

## Objective

Fix the residual bug where the API auto-configure handler uses `min_confidence=0.8` as the default, while the CLI and all recommendation services use `0.5` after commit `62ba0f42`. This causes the dashboard to show fewer recommendations than the CLI for the same project.

## Prerequisites

None. This is an independent quick fix with no dependencies on other phases.

## Scope

**IN SCOPE:**
- Change two default values in `autoconfig_handler.py` from `0.8` to `0.5`

**NOT IN SCOPE:**
- Changing the recommendation logic itself
- Adding a UI control for confidence threshold
- Modifying the CLI argument parser (already correct at `0.5`)

## Current State

Commit `62ba0f42` ("fix(autoconf): resolve three interconnected recommender bugs") changed the default `min_confidence` from `0.8` to `0.5` in the following files:

- `src/claude_mpm/services/agents/recommender.py` -- All 7 threshold comparisons
- `src/claude_mpm/services/agents/auto_config_manager.py` -- Preview method
- `src/claude_mpm/cli/parsers/config_parser.py` line 109 -- CLI argument default set to `0.5`

However, the API handler was **not updated** in that commit:

**File:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

**Line 265 (preview endpoint):**
```python
min_confidence = body.get("min_confidence", 0.8)
```

**Line 305 (apply endpoint):**
```python
min_confidence = body.get("min_confidence", 0.8)
```

### Impact

When a user triggers auto-configure from the dashboard without specifying `min_confidence` in the request body (which is the default behavior since the dashboard does not expose this parameter), the API uses `0.8` while the CLI uses `0.5`. Agents with confidence scores between `0.5` and `0.8` appear in CLI preview but NOT in the dashboard preview.

Example: If a Python project gets a `python-engineer` recommendation with confidence `0.65`, the CLI shows it but the dashboard does not.

## Target State

Both lines use `0.5` as the default, matching the CLI and the recommendation services:

```python
# Line 265
min_confidence = body.get("min_confidence", 0.5)

# Line 305
min_confidence = body.get("min_confidence", 0.5)
```

## Implementation Steps

### Step 1: Change preview endpoint default

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py` line 265

Change:
```python
min_confidence = body.get("min_confidence", 0.8)
```
To:
```python
min_confidence = body.get("min_confidence", 0.5)
```

### Step 2: Change apply endpoint default

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py` line 305

Change:
```python
min_confidence = body.get("min_confidence", 0.8)
```
To:
```python
min_confidence = body.get("min_confidence", 0.5)
```

## Devil's Advocate Analysis

### "Why was this missed in commit 62ba0f42? Are there other defaults that were missed?"

Commit `62ba0f42` focused on the recommender service layer and CLI parser. The API handler has its own default extraction from the request body, which is a separate code path. This is a classic "shotgun surgery" miss -- the default is duplicated across layers rather than centralized.

**Action:** After this fix, grep the entire codebase for `0.8` in the context of `min_confidence` to confirm no other occurrences remain:
```bash
grep -rn "min_confidence.*0\.8\|0\.8.*min_confidence" src/
```

### "Should we centralize the default instead of changing two more hardcoded values?"

Ideally, yes. A `DEFAULT_MIN_CONFIDENCE = 0.5` constant in a shared location would prevent future drift. However:
- The CLI parser defines its own default via argparse (`default=0.5`)
- The recommender defines its own default via function signature
- The API handler defines its own default via `body.get()`

Centralizing would require touching all three layers. This is a valid improvement but outside the scope of a bug fix. The two-line change here achieves parity immediately; centralization can be a follow-up.

### "Could changing this break API clients that rely on the 0.8 default?"

The dashboard does not pass `min_confidence` in the request body (the Svelte store calls `applyAutoConfig()` without it). No external API clients are documented. If any client was relying on the `0.8` default, they would have been getting fewer recommendations than expected -- fixing this gives them MORE results, not fewer.

Any client that explicitly passes `min_confidence=0.8` in the request body is unaffected (their explicit value overrides the default).

### "Is 0.5 the right threshold, or should it be even lower?"

The threshold was carefully tuned in commit `62ba0f42` alongside scoring formula changes (`base_score * (0.5 + 0.5 * confidence_weight)`). The research for that commit tested the threshold against real-world projects. Re-evaluating the threshold is outside scope; the goal here is parity with the established value.

## Acceptance Criteria

1. `autoconfig_handler.py` line 265 uses `0.5` as the default min_confidence
2. `autoconfig_handler.py` line 305 uses `0.5` as the default min_confidence
3. A unit test verifies the default: calling the preview endpoint without `min_confidence` in the body should use `0.5`
4. No other files in the codebase contain `min_confidence.*0.8` patterns

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Other hardcoded 0.8 defaults exist | Grep codebase after fix to verify |
| Default drift in future | Consider follow-up to centralize `DEFAULT_MIN_CONFIDENCE` constant |

## Estimated Effort

**XS (5 minutes)**

Two line changes, no new files, no architectural decisions. The only non-trivial part is verifying no other occurrences exist via grep.
