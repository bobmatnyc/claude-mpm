# Research: Display Full SKILL.md Content in Dashboard

**Date**: 2026-02-15
**Status**: Complete
**Scope**: Research only -- no code changes

---

## 1. Current State

### Backend: Skill Detail Endpoint

**File**: `src/claude_mpm/services/monitor/config_routes.py`
**Route**: `GET /api/config/skills/{name}/detail` (line 111, handler at line 749)
**Handler**: `handle_skill_detail()`

The endpoint currently:
1. Validates the skill name against path traversal attacks via `validate_safe_name()` (line 759)
2. Resolves the skill path: `Path.cwd() / ".claude" / "skills" / skill_name / "SKILL.md"` (lines 772-774)
3. **Reads the SKILL.md file** (line 781) -- but ONLY to parse YAML frontmatter (lines 782-810)
4. Extracts structured fields from frontmatter: `when_to_use`, `languages`, `summary`, `quick_start`, `description`, `name`, `tags`, and `progressive_disclosure.references` (lines 785-808)
5. Cross-references with manifest metadata for `version`, `toolchain`, `framework`, `tags`, `full_tokens`, `entry_point_tokens`, `requires`, `author`, `updated`, `source_path` (lines 812-835)
6. Adds agent usage data from skill-to-agent links (lines 837-860)

**Key finding**: The backend already reads the full SKILL.md content (line 781: `content = skill_md.read_text(encoding="utf-8")`), but **discards the markdown body** after extracting frontmatter. The raw content is never included in the API response.

### Frontend: SkillDetailPanel Component

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` (364 lines)

The component renders in a **right-side detail panel** (master-detail layout in `ConfigView.svelte`). It currently displays:

- **Header**: Skill name, version badge, deployed/available badge, user-requested badge
- **Description**: From frontmatter or manifest
- **MetadataGrid**: Toolchain, full tokens, entry tokens, framework, updated date
- **Tags**: From frontmatter and manifest combined
- **Summary**: From progressive_disclosure frontmatter (rare -- only 19/188 skills have frontmatter)
- **Collapsible sections**: "When to Use", "Used By" (agents), "Dependencies", "References"
- **Footer**: Author, updated date, languages, source path
- **Action button**: Deploy/Undeploy

**Key finding**: There is NO raw markdown content display. The component only shows structured/extracted data. For the ~90% of skills without YAML frontmatter, the detail panel shows very little beyond basic manifest data.

### Data Flow

```
User clicks skill in SkillsList
  -> ConfigView sets selectedSkill
  -> SkillDetailPanel.$effect triggers fetchSkillDetail(name)
  -> GET /api/config/skills/{name}/detail
  -> _get_skill_detail() reads SKILL.md, parses frontmatter only
  -> Response: structured JSON (no raw content)
  -> SkillDetailPanel renders structured fields
```

### TypeScript Interface

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` (lines 282-304)

```typescript
export interface SkillDetailData {
    name: string;
    description?: string;
    version?: string;
    toolchain?: string | null;
    framework?: string | null;
    tags?: string[];
    full_tokens?: number;
    entry_point_tokens?: number;
    requires?: string[];
    author?: string;
    updated?: string;
    source_path?: string;
    when_to_use?: string;
    languages?: string;
    summary?: string;
    quick_start?: string;
    frontmatter_name?: string;
    frontmatter_tags?: string[];
    references?: { path: string; purpose: string }[];
    used_by_agents?: string[];
    agent_count?: number;
    // NOTE: No "content" or "raw_markdown" field exists
}
```

---

## 2. SKILL.md Structure

### File Organization

Skills are deployed to `$CWD/.claude/skills/<skill-name>/SKILL.md`. Each skill lives in its own directory. The file is always named `SKILL.md`.

Path resolution in the detail endpoint (line 772-774):
```python
project_skills_dir = Path.cwd() / ".claude" / "skills"
skill_dir = project_skills_dir / skill_name
skill_md = skill_dir / "SKILL.md"
```

### Frontmatter Prevalence

- **19 out of 188 skills** (10%) have YAML frontmatter (delimited by `---`)
- The remaining **169 skills** (90%) are plain markdown with NO frontmatter
- All 19 frontmatter skills are `mpm-*` or `toolchains-rust-desktop-applications`

### File Size Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Under 5 KB | 69 | 37% |
| 5-20 KB | 68 | 36% |
| Over 20 KB | 51 | 27% |

- **Smallest**: 387 bytes (`toolchains-python-frameworks-fastapi-local-dev`)
- **Largest**: 59,219 bytes / ~58 KB (`toolchains-ai-techniques-session-compression`)
- **Median**: 8,651 bytes / ~8.5 KB
- **Average**: 13,849 bytes / ~13.5 KB

### Markdown Features Used

Based on sampling 10 SKILL.md files, typical content includes:

- **Headers** (h1-h6): Universal, every file
- **Code blocks** (fenced with language tags): Very common (~80%+ of files)
- **Bullet lists** and **numbered lists**: Very common
- **Tables**: Common in larger skills (~40%)
- **Bold/italic**: Common
- **Inline code**: Very common
- **Blockquotes**: Occasional
- **Links**: Occasional (usually relative references to `references/` files)
- **Mermaid diagrams**: Rare but possible
- **Task lists/checkboxes**: Occasional

### Content Categories

1. **Tiny reference cards** (under 1 KB): Quick-reference cheat sheets with a few commands
   - Example: `fastapi-local-dev` -- 11 lines, dev commands + anti-patterns

2. **Structured guides** (1-10 KB): Well-organized skill documentation with sections
   - Example: `mpm` -- 38 lines, commands list + overview + quick start
   - Example: `skill-creator` -- 171 lines, creation workflow with navigation

3. **Comprehensive references** (10-30 KB): Deep technical documentation
   - Example: `pdf` -- 307 lines, Python/CLI examples for PDF operations
   - Example: `test-driven-development` -- 379 lines, multi-language TDD patterns

4. **Exhaustive skill manuals** (30-60 KB): Complete framework guides
   - Example: `langgraph` -- 1,459 lines, full LangGraph API reference
   - Example: `session-compression` -- full compression techniques guide

### Content That Should Not Be Filtered

All sampled SKILL.md content is user-facing documentation. There are no internal notes, secrets, or sensitive data. The files ARE the source of truth and are meant to be read by Claude/users.

---

## 3. Gap Analysis

### Backend Gaps

| What Exists | What's Missing |
|-------------|---------------|
| Endpoint reads SKILL.md content (line 781) | Content is discarded after frontmatter parsing |
| Path resolution works correctly | No `content` field in response |
| Path traversal protection in place | No file size check or content truncation |
| Runs in thread pool (line 864) | No lazy-loading endpoint for content-only |

**Specific change needed**: In `_get_skill_detail()` (line 770), after reading `content = skill_md.read_text()`, add the raw content to the result dict. The content variable already exists at line 781 but is only used for frontmatter regex matching.

### Frontend Gaps

| What Exists | What's Missing |
|-------------|---------------|
| `MarkdownViewer.svelte` component with full styling | Not imported in `SkillDetailPanel.svelte` |
| `marked` v17 in `package.json` dependencies | No usage in config components |
| `mermaid` rendering support in MarkdownViewer | Not connected to skill detail flow |
| `CollapsibleSection` pattern for progressive disclosure | No collapsible section for "Full Content" |
| `SkillDetailData` TypeScript interface | No `content` field in the interface |

**Key advantage**: The `MarkdownViewer.svelte` component (354 lines) is a production-ready markdown renderer with:
- GitHub Flavored Markdown support
- Mermaid diagram rendering
- Full dark mode support via CSS variables
- Code block styling with monospace fonts
- Table, blockquote, list, and image styling
- Error handling for rendering failures

---

## 4. Implementation Approach

### Backend Changes

**File**: `src/claude_mpm/services/monitor/config_routes.py`

**Change 1: Add raw content to response** (in `_get_skill_detail()`, around line 781)

The `content` variable already exists. After the frontmatter parsing block, add it to the result:

```python
# Line ~781 (existing code):
content = skill_md.read_text(encoding="utf-8")

# After the frontmatter parsing try/except block (after line ~810):
# Strip frontmatter from content for display
display_content = content
fm_match = re.match(r"^---\n.*?\n---\n?", content, re.DOTALL)
if fm_match:
    display_content = content[fm_match.end():]
result["content"] = display_content.strip()
result["content_size"] = len(display_content)
```

**Rationale for stripping frontmatter**: Users do not need to see the YAML frontmatter block in the rendered view. The structured fields from frontmatter are already displayed separately in the detail panel.

**Performance note**: The file is already being read at line 781. Adding the content to the response adds zero additional I/O. The only overhead is the additional bytes in the JSON response, which is acceptable given the median file size of 8.5 KB.

### Frontend Changes

**File 1**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

Add `content` and `content_size` to the `SkillDetailData` interface (line 282):

```typescript
export interface SkillDetailData {
    // ... existing fields ...
    content?: string;         // Raw markdown body (frontmatter stripped)
    content_size?: number;    // Size in bytes for UI decisions
}
```

**File 2**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte`

Add a collapsible "Skill Content" section using the existing `MarkdownViewer`:

```svelte
<script lang="ts">
    // Add import:
    import MarkdownViewer from '$lib/components/MarkdownViewer.svelte';
</script>

<!-- After the References CollapsibleSection (after line ~297), add: -->
{#if detailData.content}
    <CollapsibleSection
        title="Skill Content"
        defaultExpanded={true}
    >
        <div class="max-h-[600px] overflow-y-auto">
            <MarkdownViewer content={detailData.content} />
        </div>
    </CollapsibleSection>
{/if}
```

### Summary of Files to Modify

| File | Change | Lines Affected |
|------|--------|---------------|
| `src/claude_mpm/services/monitor/config_routes.py` | Add `content` and `content_size` to response | ~3 lines after line 810 |
| `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` | Add fields to `SkillDetailData` interface | 2 lines at line ~303 |
| `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillDetailPanel.svelte` | Import MarkdownViewer, add collapsible content section | ~10 lines total |

**Total estimated changes**: ~15 lines across 3 files.

---

## 5. Content Samples

### Sample 1: Small Skill (fastapi-local-dev, 387 bytes)

What users would see rendered:

> # FastAPI Local Dev
>
> - Dev: `uvicorn app.main:app --reload`
> - Imports: run from repo root; use `python -m uvicorn ...` or `PYTHONPATH=.`
> - WSL: `WATCHFILES_FORCE_POLLING=true` if reload misses changes
> - Prod: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w <n> --bind :8000`
>
> Anti-patterns:
> - `--reload --workers > 1`
> - PM2 `watch: true` for Python
>
> References: `references/`.

### Sample 2: Medium Skill with Frontmatter (mpm, 38 lines)

After frontmatter stripping, users would see:

> # /mpm
>
> Access Claude MPM functionality and manage your multi-agent orchestration.
>
> ## Available MPM Commands
>
> - `/mpm-agents` - Show available agents and versions
> - `/mpm-doctor` - Run diagnostic checks
> - `/mpm-help` - Show command help
> - `/mpm-status` - Show MPM status
> [...]

### Sample 3: Large Skill (test-driven-development, 379 lines, ~13 KB)

Would render as a comprehensive guide with:
- Multi-language code blocks (Python, JavaScript, Go)
- Tables for coverage guidelines
- Nested bullet lists
- Anti-pattern examples with code comparisons
- Section headers for navigation

This demonstrates why a scrollable container with `max-h-[600px]` is important for larger skills.

---

## 6. Dependencies

### No New Dependencies Required

All required libraries are already in place:

| Library | Version | Location | Purpose |
|---------|---------|----------|---------|
| `marked` | v17.0.1 | `package.json` line 36 | Markdown to HTML parsing |
| `mermaid` | v11.12.2 | `package.json` line 37 | Diagram rendering |
| `shiki` | v3.20.0 | `package.json` line 38 | Syntax highlighting (available if needed) |

### Existing Component Ready for Reuse

`MarkdownViewer.svelte` (`src/claude_mpm/dashboard-svelte/src/lib/components/MarkdownViewer.svelte`, 354 lines):
- Already configured for GFM (GitHub Flavored Markdown)
- Dark mode support via `data-theme` attribute and CSS variables
- Mermaid diagram rendering with theme-awareness
- Full styling for headers, code blocks, tables, lists, blockquotes, images
- Error handling for rendering failures
- Currently used by `FileViewer.svelte` for `.md` file display

---

## 7. Edge Cases

### Empty Files
- SKILL.md exists but is empty
- **Handling**: `content` will be empty string; the CollapsibleSection simply won't show (guarded by `{#if detailData.content}`)

### Very Large Files (50+ KB)
- 51 skills are over 20 KB; largest is ~58 KB
- **Handling**: The `max-h-[600px] overflow-y-auto` container provides scrolling. The JSON response size increase is modest (58 KB max). Consider adding `content_size` to the response so the frontend can optionally show a "Large skill" indicator.
- **Performance**: File is already being read by the endpoint. No additional I/O. JSON serialization of 58 KB is negligible. The `marked` parser handles large documents efficiently.

### Missing Files
- Skill directory exists but SKILL.md does not
- **Handling**: Already handled -- the existing code checks `if skill_md.exists()` (line 779). If the file doesn't exist, `content` simply won't be in the result dict, and the frontend guard `{#if detailData.content}` prevents rendering.

### Binary Content
- Not a realistic concern -- SKILL.md files are always text/markdown
- **Handling**: `read_text(encoding="utf-8")` would raise an exception, caught by the existing try/except at line 809

### Frontmatter-Only Files
- A SKILL.md that is 100% frontmatter with no markdown body
- **Handling**: After stripping frontmatter, `display_content.strip()` would be empty string, and the section won't render

### File Read Errors (Permission Denied, etc.)
- **Handling**: Already wrapped in try/except (line 809). The `content` field simply won't be present in the response.

### Concurrent Reads
- Multiple users viewing different skill details simultaneously
- **Handling**: Already handled -- the endpoint uses `asyncio.to_thread()` (line 864) for non-blocking I/O. File reads are inherently safe for concurrent access (read-only).

### Cache Considerations
- The frontend caches `SkillDetailData` in an LRU cache (max 50 entries, line 311)
- Including content in the cache means ~50 * 13.5 KB avg = ~675 KB of cached content
- **Handling**: This is acceptable browser memory usage. The LRU eviction already handles cache growth.

---

## 8. Alternative Approaches Considered

### A: Separate Content Endpoint (Rejected)

Creating a `GET /api/config/skills/{name}/content` endpoint that returns raw content only.

**Pros**: Smaller detail response, lazy-loading possible
**Cons**: Extra HTTP request, extra latency, more code, the file is already being read in the detail endpoint

**Decision**: Not recommended. The file is already read at line 781. Adding 8.5 KB (median) to a response that's already a few hundred bytes is simpler and faster than a separate round-trip.

### B: Truncated Content with "Show More" (Possible Enhancement)

Return only the first N characters (e.g., 2000 chars) with a flag indicating truncation, and have a "Show Full Content" button that fetches the rest.

**Pros**: Faster initial load for very large skills
**Cons**: More complexity, extra endpoint needed, content already read server-side

**Decision**: Not recommended for initial implementation. Only 51 of 188 skills are over 20 KB. The `max-h-[600px]` scrollable container handles large content well. Can be added later if performance metrics warrant it.

### C: Pre-rendered HTML (Rejected)

Render the markdown to HTML on the server and return pre-rendered HTML.

**Pros**: No client-side parsing overhead
**Cons**: Larger response, no client-side theme-awareness, duplicates MarkdownViewer capability, SSR complexity

**Decision**: Not recommended. The `MarkdownViewer` component handles this correctly with theme-aware styling.

---

## 9. Implementation Checklist

For the implementing developer:

1. [ ] Add `content` and `content_size` fields to `_get_skill_detail()` response in `config_routes.py` (after line ~810)
2. [ ] Strip YAML frontmatter from content before adding to response
3. [ ] Add `content?: string` and `content_size?: number` to `SkillDetailData` interface in `config.svelte.ts`
4. [ ] Import `MarkdownViewer` in `SkillDetailPanel.svelte`
5. [ ] Add a `CollapsibleSection` with `MarkdownViewer` for displaying content
6. [ ] Add `max-h-[600px] overflow-y-auto` to the content container for scroll support
7. [ ] Test with: empty file, small file, large file (50+ KB), frontmatter-only file, missing file
8. [ ] Verify dark mode rendering looks correct
9. [ ] Verify the detail panel scroll behavior with long content
