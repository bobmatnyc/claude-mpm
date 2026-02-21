# Alternative Theories: Devil's Advocate Analysis

## Theory 1: "The naming is intentional by design"

**Hypothesis**: The deployed list shows machine IDs and available list shows human-readable names on purpose, with the frontend responsible for normalization.

**Analysis**:
- The `handle_agents_available` code has an explicit comment: "Promote metadata fields to root level for **frontend compatibility**" (line 365-367). This suggests the promotion was intentional for the frontend.
- However, the resulting `is_deployed` comparison is clearly broken (always false), proving this was not a well-considered design choice.
- The `agent_id` field exists specifically to serve as a machine-friendly identifier, but it's being ignored in the comparison.

**Verdict**: **Partially valid**. The two naming conventions exist by design (machine ID vs display name), but the failure to properly cross-reference them is a bug, not a feature.

## Theory 2: "The problem is in caching/synchronization"

**Hypothesis**: The naming mismatch could be caused by stale cache data, where cached agents have outdated name formats.

**Analysis**:
- Cache staleness would affect the *content* of the name, not the *format*. Even with fresh cache, `metadata.name` will always be "Svelte Engineer" while file stems will always be "svelte-engineer".
- The `RemoteAgentDiscoveryService._parse_markdown_agent()` always extracts two separate fields: `agent_id` (kebab-case) and `metadata.name` (human-readable). This is structural, not temporal.
- Deduplication in `list_cached_agents()` (line 402-418) works on `agent_id`, confirming the system knows about the distinction.

**Verdict**: **Invalid**. The naming mismatch is structural, not caused by caching.

## Theory 3: "Agent markdown files have inconsistent naming"

**Hypothesis**: Some agent markdown files might have `agent_id` values that don't match their filenames, causing the mismatch.

**Analysis**:
- The `_parse_markdown_agent()` method (line 600-607) explicitly handles this:
  ```python
  if frontmatter and "agent_id" in frontmatter:
      agent_id = frontmatter["agent_id"]
  else:
      agent_id = md_file.stem
  ```
- If YAML `agent_id` doesn't match the filename, there could be a secondary mismatch. However, the primary issue is that `name` (human-readable) is used instead of `agent_id` in the comparison.
- Even if all agent_ids perfectly match filenames, the bug would persist because `metadata.name` ("Svelte Engineer") is what gets promoted to `name`.

**Verdict**: **Minor contributing factor**. Agent files with mismatched `agent_id` vs filename would create additional issues, but the core bug exists regardless.

## Theory 4: "The frontend should normalize names client-side"

**Hypothesis**: The API is correct, and the frontend should handle name normalization by converting between formats.

**Analysis**:
- The frontend already has `agent_id` available on `AvailableAgent` objects. It could use `agent_id` for matching and `name` for display.
- However, `DeployedAgent` does NOT have an `agent_id` field - it only has `name` (the file stem). Adding `agent_id` to deployed agents would require backend changes anyway.
- Client-side normalization (e.g., converting "Svelte Engineer" to "svelte-engineer") is fragile and would break for agents with non-standard naming (hyphens vs underscores, abbreviations, etc.).
- Example: "AWS Ops Agent" → normalized to "aws-ops-agent" but deployed filename might be "aws_ops_agent" or "aws-ops".

**Verdict**: **Partially valid but fragile**. The frontend SHOULD use `agent_id` for matching, but the backend should also provide consistent data. A backend fix is more robust than client-side normalization.

## Theory 5: "Standardizing on agent_id is wrong; use display names everywhere"

**Hypothesis**: Instead of using machine IDs everywhere, both lists should show human-readable display names.

**Analysis**:
- This would require the deployed agents endpoint to return frontmatter `name` instead of file stems.
- The `list_agents()` method currently enriches with frontmatter fields (description, category, etc.) but uses file stem as the key.
- The `_extract_enrichment_fields()` method (line 342-359 of agent_management_service.py) already parses frontmatter - adding `name` extraction is trivial.
- **Risk**: Human-readable names might not be unique. Two agents could both be named "Engineer" while having different file stems. File stems are guaranteed unique (filesystem constraint).
- **Risk**: Other parts of the system (deploy/undeploy endpoints, CLI) use file stems / agent_id. Switching to display names would create inconsistency elsewhere.

**Verdict**: **Not recommended**. Display names are not guaranteed unique and don't match the existing system conventions. Better to keep machine IDs as the primary identifier and add display names as a supplementary field.

## Theory 6: "Multiple sources of truth"

**Hypothesis**: The real problem is that agent identity has multiple sources of truth (filename, agent_id, name), and no single canonical identifier.

**Analysis**:
- This is the most accurate characterization of the underlying issue.
- Currently there are 3 identity sources:
  1. **Filesystem**: file stem (guaranteed unique per directory)
  2. **YAML `agent_id`**: intended as machine identifier (should match filesystem)
  3. **YAML `name`**: human-readable display name (not unique)
- The `canonical_id` field (`collection_id:agent_id`) was introduced to address this, but it's only used in the discovery service, not in the API responses.

**Verdict**: **Valid and important**. The solution should establish `agent_id` as THE canonical identifier used everywhere, with `name`/`display_name` reserved for UI display only.

## Conclusion

The primary root cause is **the name promotion logic in `handle_agents_available()`** combined with **the `is_deployed` comparison using the wrong field**. Alternative theories about caching, synchronization, or frontend responsibility are secondary concerns that don't explain the core bug.

The recommended approach is to fix the backend to use `agent_id` as the primary identifier while preserving human-readable names as a separate `display_name` field.
