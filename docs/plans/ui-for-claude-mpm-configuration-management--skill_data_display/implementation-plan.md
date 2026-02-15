# Implementation Plan: Skill Content Display & Metadata Enrichment Fix

**Date:** 2026-02-15
**Branch:** ui-agents-skills-config
**Status:** Plan

---

## 1. Overview

### Primary Goal

Display the full SKILL.md markdown content (with frontmatter stripped) in the dashboard skill detail panel when a user clicks a skill. Currently, the backend reads the file but discards the body after extracting frontmatter fields. For the ~90% of skills without YAML frontmatter, the detail panel shows very little beyond basic manifest data.

### Secondary Goal

Fix the `_build_manifest_lookup()` function so it reads the locally cached manifest file from disk as the primary source, rather than depending on a `git pull` network call that intermittently fails. This ensures structured fields (version, toolchain, tags, tokens, etc.) populate reliably.

### Research References

- Primary: `docs/research/skill-content-display-2026-02-15.md` -- Full analysis of the content display gap, file size distribution, and implementation approach
- Secondary: `docs/research/skill-metadata-enrichment-2026-02-15.md` -- Manifest enrichment pipeline brittleness, metadata source analysis, and the `_build_manifest_lookup()` fix

---

## 2. Implementation Steps

### Step 1: Fix `_build_manifest_lookup()` to Read Local Cached Manifest

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Location:** `_build_manifest_lookup()` function, lines 128-150
**Why:** The current implementation calls `skills_svc.list_available_skills()` which triggers `_download_from_github()` -- a `git pull` subprocess with a 60-second timeout. When this fails (intermittently), the manifest lookup returns an empty dict and ALL manifest-derived enrichment silently produces no results. The manifest is already cached on disk at `~/.claude/skills/claude-mpm/manifest.json` and can be read directly without any network call. This fix applies regardless of the content display feature and makes the entire skill metadata pipeline reliable.

**Change:** Add local manifest file reading as the primary source, with the existing network call as a fallback. Reuse the existing nested-dict parsing logic already present in the function body.

**Code sketch:**

```python
import json as json_module  # Add at top of file if not already imported

def _build_manifest_lookup(skills_svc) -> dict:
    """Build a name-to-manifest-entry lookup dict from available skills.

    Reads local cached manifest first (no network), falls back to
    list_available_skills() which requires git pull.
    Returns empty dict on any error (graceful degradation).
    """
    manifest_lookup: dict = {}

    # --- Primary: read local cached manifest from disk (no network) ---
    local_manifest_paths = [
        Path.home() / ".claude" / "skills" / "claude-mpm" / "manifest.json",
        Path.home() / ".claude-mpm" / "cache" / "skills" / "system" / "manifest.json",
    ]
    for manifest_path in local_manifest_paths:
        try:
            if manifest_path.exists():
                raw = json_module.loads(manifest_path.read_text(encoding="utf-8"))
                available_skills = raw.get("skills", {})
                manifest_lookup = _parse_manifest_skills(available_skills)
                if manifest_lookup:
                    logger.debug(
                        f"Loaded manifest from {manifest_path} ({len(manifest_lookup)} skills)"
                    )
                    return manifest_lookup
        except Exception as e:
            logger.debug(f"Could not read local manifest {manifest_path}: {e}")

    # --- Fallback: network-dependent list_available_skills() ---
    try:
        available = skills_svc.list_available_skills()
        available_skills = available.get("skills", [])
        manifest_lookup = _parse_manifest_skills(available_skills)
    except Exception as e:
        logger.warning(f"Could not load manifest for skill enrichment: {e}")
    return manifest_lookup


def _parse_manifest_skills(available_skills) -> dict:
    """Parse manifest skills from either flat list or nested dict structure."""
    lookup: dict = {}
    if isinstance(available_skills, list):
        for skill in available_skills:
            if isinstance(skill, dict):
                lookup[skill.get("name", "")] = skill
    elif isinstance(available_skills, dict):
        for _category, cat_skills in available_skills.items():
            if isinstance(cat_skills, list):
                for skill in cat_skills:
                    if isinstance(skill, dict):
                        lookup[skill.get("name", "")] = skill
            elif isinstance(cat_skills, dict):
                # Handle nested subcategories (e.g., toolchains.python.*)
                for _subcat, sub_skills in cat_skills.items():
                    if isinstance(sub_skills, list):
                        for skill in sub_skills:
                            if isinstance(skill, dict):
                                lookup[skill.get("name", "")] = skill
    return lookup
```

**Notes:**
- The manifest at `~/.claude/skills/claude-mpm/manifest.json` uses a nested dict structure: `skills.universal` (flat list), `skills.toolchains` (subcategories with lists), `skills.examples` (flat list). The `_parse_manifest_skills()` helper handles all three levels.
- Extracting `_parse_manifest_skills()` as a separate function eliminates duplication between the local-read path and the network-fallback path.
- The local file is 110,783 bytes and reads in under 1ms. Zero network dependency.
- Two fallback paths on disk are checked: the git clone cache and the skills cache system copy.

---

### Step 2: Add `content` and `content_size` to the Detail Endpoint Response

**File:** `src/claude_mpm/services/monitor/config_routes.py`
**Location:** `_get_skill_detail()` function, inside the `if skill_md.exists():` block, after the frontmatter parsing try/except (after line 810)
**Why:** The variable `content` already exists at line 781 (`content = skill_md.read_text(encoding="utf-8")`), but the markdown body is discarded after frontmatter extraction. Adding it to the response requires zero additional I/O -- the file is already read.

**Change:** After the existing frontmatter parsing block, strip the frontmatter delimiter from the content and add the body and its size to the result dict.

**Code sketch:**

```python
            # Inside _get_skill_detail(), after the frontmatter try/except block (after line 810):

            # Add raw markdown content (frontmatter stripped) for display
            display_content = content
            fm_match = re.match(r"^---\n.*?\n---\n?", content, re.DOTALL)
            if fm_match:
                display_content = content[fm_match.end():]
            display_content = display_content.strip()
            if display_content:
                result["content"] = display_content
                result["content_size"] = len(display_content)
```

**Notes:**
- The `re.match(r"^---\n.*?\n---\n?", content, re.DOTALL)` pattern matches the standard YAML frontmatter delimiters. The same `re` module and `re.DOTALL` flag are already used at line 782.
- Stripping frontmatter avoids showing raw YAML to the user -- those structured fields are already rendered separately in the detail panel.
- Only setting `content` when non-empty means the frontend guard `{#if detailData.content}` naturally handles empty/frontmatter-only files.
- `content_size` allows the frontend to optionally display a size indicator or adjust rendering strategy for very large skills.
- Median file size is 8.5 KB, largest is ~58 KB. Adding this to the JSON response is negligible overhead.

---

### Step 3: Add `content` and `content_size` to the TypeScript Interface

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`
**Location:** `SkillDetailData` interface, lines 282-304 (add before the closing brace at line 304)
**Why:** TypeScript type safety. The interface must reflect the new fields returned by the backend.

**Change:** Add two optional fields.

**Code sketch:**

```typescript
export interface SkillDetailData {
    // ... existing fields (lines 283-303) ...
    agent_count?: number;
    content?: string;        // Raw markdown body (frontmatter stripped)
    content_size?: number;   // Size in bytes for UI decisions
}
```

**Notes:**
- Both fields are optional (`?`) because: (a) the backend only includes them when content exists and is non-empty, (b) backward compatibility with cached responses that lack the fields.
- No changes needed to `DeployedSkill` or `AvailableSkill` interfaces -- content is only returned by the detail endpoint.

---

### Step 4: Import `MarkdownViewer` in `SkillDetailPanel.svelte`

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte`
**Location:** `<script>` block, line 1-5 (add alongside existing imports)
**Why:** The `MarkdownViewer` component (at `$lib/components/MarkdownViewer.svelte`, 354 lines) is a production-ready markdown renderer with GFM support, mermaid diagrams, dark mode styling, code block formatting, and error handling. It is already used by `FileViewer.svelte` for `.md` file display.

**Change:** Add one import statement.

**Code sketch:**

```svelte
<script lang="ts">
    import { fetchSkillDetail, type SkillDetailData, type DeployedSkill, type AvailableSkill } from '$lib/stores/config.svelte';
    import Badge from '$lib/components/Badge.svelte';
    import CollapsibleSection from '$lib/components/shared/CollapsibleSection.svelte';
    import MetadataGrid from '$lib/components/shared/MetadataGrid.svelte';
    import MarkdownViewer from '$lib/components/MarkdownViewer.svelte';
```

---

### Step 5: Add Collapsible Skill Content Section with MarkdownViewer

**File:** `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte`
**Location:** After the "References" `CollapsibleSection` (after line 297), before the closing `</div>` at line 298
**Why:** This is the natural location in the progressive disclosure layout -- structured metadata first (header, description, metadata grid, tags, when-to-use, agents, dependencies, references), then the full source content last. The collapsible section pattern is consistent with the existing UI.

**Change:** Add a collapsible section containing the MarkdownViewer inside a scrollable container.

**Code sketch:**

```svelte
        <!-- After the References CollapsibleSection (after line 297) -->

        <!-- Full Skill Content -->
        {#if detailData.content}
            <CollapsibleSection
                title="Skill Content"
                defaultExpanded={true}
            >
                <div class="max-h-[600px] overflow-y-auto rounded border border-slate-200 dark:border-slate-700 p-4">
                    <MarkdownViewer content={detailData.content} />
                </div>
                {#if detailData.content_size && detailData.content_size > 20000}
                    <p class="mt-1 text-xs text-slate-400 dark:text-slate-500 italic">
                        Large skill ({Math.round(detailData.content_size / 1024)} KB) - scroll to see full content
                    </p>
                {/if}
            </CollapsibleSection>
        {/if}
```

**Notes:**
- `max-h-[600px] overflow-y-auto`: Creates a scrollable container for large skills. The largest skill is ~58 KB / 1,459 lines (langgraph). Without a max-height, the detail panel would become extremely long and push the footer/action buttons out of view.
- `rounded border ... p-4`: Provides a visual boundary for the rendered markdown, distinguishing it from the panel's own styling.
- The `{#if detailData.content}` guard handles: empty files (empty string is falsy), missing files (field absent from response), frontmatter-only files (stripped content is empty).
- `defaultExpanded={true}`: The content section opens by default since it is the primary reason users click a skill. Users can collapse it if they only want the structured metadata.
- The content size indicator only shows for files over 20 KB (51 of 188 skills), providing a visual cue that more content exists below the fold.

---

## 3. Edge Cases

| Case | How It Is Handled |
|---|---|
| **Empty SKILL.md files** | `display_content.strip()` produces empty string; `if display_content:` prevents adding to result; frontend `{#if detailData.content}` hides the section |
| **Very large files (>20 KB)** | `max-h-[600px] overflow-y-auto` container provides scrolling; size indicator shown for files >20 KB; no truncation -- full content rendered. 51 of 188 skills fall in this category. Largest is ~58 KB. |
| **Missing SKILL.md files** | Existing check `if skill_md.exists()` at line 779 skips the entire block; `content` field absent from response; frontend guard hides section |
| **Files with only frontmatter (no body)** | Frontmatter regex strips the `---..---` block; remaining content after `.strip()` is empty; section hidden |
| **Skills not found on disk** | Same as missing files -- `skill_md.exists()` returns False |
| **Binary/corrupted files** | `read_text(encoding="utf-8")` raises UnicodeDecodeError; caught by existing `except Exception` at line 809; `content` field absent |
| **Concurrent reads** | Endpoint already uses `asyncio.to_thread()` (line 864); file reads are read-only and safe for concurrent access |
| **Cache memory impact** | Frontend LRU cache holds max 50 entries; 50 x 13.5 KB median = ~675 KB; acceptable browser memory |
| **Local manifest file missing** | Fallback chain: try first disk path, try second disk path, fall back to network call, fall back to empty dict |
| **Malformed manifest JSON** | `json_module.loads()` raises `json.JSONDecodeError`; caught by `except Exception`; moves to next fallback |

---

## 4. Testing Approach

### What to Verify

1. **Content display**: Click a skill in the dashboard, verify the "Skill Content" collapsible section appears with rendered markdown
2. **Frontmatter stripping**: For skills with frontmatter (e.g., `mpm-*` skills), verify the `---` YAML block is NOT visible in the rendered content
3. **Markdown rendering**: Verify headers, code blocks, tables, lists, bold/italic, and inline code render correctly
4. **Dark mode**: Toggle dark mode and verify the rendered markdown respects the theme
5. **Scroll behavior**: For large skills, verify the 600px container shows a scrollbar and the rest of the detail panel remains accessible
6. **Size indicator**: For skills >20 KB, verify the "Large skill (XX KB)" message appears
7. **Empty/missing handling**: Verify no "Skill Content" section appears for skills with empty or missing SKILL.md
8. **Manifest enrichment reliability**: Verify version, toolchain, tags, and token counts appear consistently (no intermittent blanks)
9. **LRU cache**: Click a skill, navigate away, click back -- verify the cached response includes content without re-fetching

### Sample Skills to Test With

| Skill Name | Size | Category | What It Tests |
|---|---|---|---|
| `toolchains-python-frameworks-fastapi-local-dev` | 387 bytes | Tiny, no frontmatter | Minimal content rendering |
| `mpm` | ~1.5 KB | Small, has frontmatter | Frontmatter stripping, structured content |
| `universal-testing-test-driven-development` | ~13 KB | Medium, no frontmatter | Multi-language code blocks, tables, lists |
| `toolchains-ai-techniques-langgraph` | ~42 KB | Large, no frontmatter | Scroll container, size indicator, performance |
| `toolchains-ai-techniques-session-compression` | ~58 KB | Largest skill | Max-size stress test, scroll behavior |
| A skill with only frontmatter (if one exists) | Varies | Edge case | Empty body after stripping |
| A non-existent skill name (via URL manipulation) | N/A | Error case | 404 handling, no crash |

### Manual Test Procedure

1. Start the dashboard: `python -m claude_mpm`
2. Navigate to Config tab, Skills sub-tab
3. Click each test skill from the table above
4. Verify the "Skill Content" section renders correctly
5. Toggle dark mode and re-verify
6. Check browser console for JavaScript errors
7. Verify the detail panel scroll works correctly when content is long

---

## 5. Dependencies

### No New Dependencies Required

All required libraries are already in place:

| Library | Version | Purpose | Already Used By |
|---|---|---|---|
| `marked` | v17.0.1 | Markdown to HTML parsing | `MarkdownViewer.svelte` |
| `mermaid` | v11.12.2 | Diagram rendering | `MarkdownViewer.svelte` |
| `re` (Python stdlib) | N/A | Frontmatter regex stripping | Already used at line 782 in `config_routes.py` |
| `json` (Python stdlib) | N/A | Manifest file parsing | Already used elsewhere in `config_routes.py` |

### Existing Components Reused

| Component | Location | Lines |
|---|---|---|
| `MarkdownViewer.svelte` | `src/claude_mpm/dashboard-svelte/src/lib/components/MarkdownViewer.svelte` | 354 |
| `CollapsibleSection.svelte` | `src/claude_mpm/dashboard-svelte/src/lib/components/shared/CollapsibleSection.svelte` | Already imported in SkillDetailPanel |

---

## 6. Risk Assessment

### Low Risk

- **JSON response size increase**: Median 8.5 KB, max 58 KB added to the detail response. The detail endpoint is called once per skill click, not in bulk. This is comparable to loading a small image.
- **`marked` rendering performance**: The `marked` library handles 58 KB of markdown efficiently. Client-side parsing of this size is sub-100ms on modern hardware.
- **MarkdownViewer compatibility**: The component is already production-tested via `FileViewer.svelte`. No new rendering paths are introduced.

### Medium Risk

- **`_build_manifest_lookup()` refactor**: Extracting `_parse_manifest_skills()` and adding the local-file-first logic changes a function used by multiple endpoints (deployed skills list, available skills list, and skill detail). If the manifest JSON structure on disk differs from what `list_available_skills()` returns, parsing could silently produce fewer matches. **Mitigation**: The local file IS the same manifest -- it is the source that `list_available_skills()` reads after git pull. Verify match counts in testing (expect 160 skills from local file vs. the 130/188 enrichment observed in the HAR).

### Negligible Risk

- **Backward compatibility**: All new fields are optional. Older cached responses without `content` or `content_size` will simply not render the section (frontend guard handles this). The `_parse_manifest_skills()` extraction does not change the return type of `_build_manifest_lookup()`.

### Performance Considerations

- **File I/O**: The SKILL.md file is already read at line 781. Adding content to the response adds zero additional file reads. The manifest file (110 KB) is read once per request but could be cached in memory for further optimization (out of scope for this plan).
- **Memory**: The frontend LRU cache (max 50 entries) with content adds ~675 KB of cached data. This is well within acceptable browser memory.
- **Network**: The detail endpoint response grows by the content size (median 8.5 KB). For a single-skill click, this is negligible latency impact.

---

## 7. Summary of Changes

| # | File | Change | Lines Added (est.) |
|---|---|---|---|
| 1 | `src/claude_mpm/services/monitor/config_routes.py` | Refactor `_build_manifest_lookup()` to read local manifest first; extract `_parse_manifest_skills()` helper | ~35 net |
| 2 | `src/claude_mpm/services/monitor/config_routes.py` | Add `content` and `content_size` to `_get_skill_detail()` response | ~6 |
| 3 | `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Add `content` and `content_size` to `SkillDetailData` interface | 2 |
| 4 | `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` | Import `MarkdownViewer`; add collapsible content section | ~15 |
| | **Total** | **3 files modified** | **~58 lines** |
