# Research Amendments Log

This file tracks corrections and amendments to the auto-configuration research documents in this directory. Amendments preserve the original text (via strikethrough) for research integrity while clearly marking what changed and why.

---

## Amendment 1: Agent Directory Path Change Correction (2026-02-21)

### What was reported

Document 04 (CLI Impact Assessment), Section 2.6, reported that `agent_management_service.py` contained a **behavioral change** on the `ui-agents-skills-config` branch: the `PROJECT_AGENTS_DIR` constant was changed from `.claude-mpm/agents/` to `.claude/agents/`. This was characterized as a **Medium risk** change that could affect agent resolution and require user migration.

This finding propagated into:
- Document 04's summary risk matrix and overall risk rating
- Document 05's devil's advocate challenges (Section 1.3, 1.5)
- Document 05's unification plan (Phase 6)
- Document 05's open questions (Question 8)

### What is actually correct

**The path change does not exist.** Both branches (`main` and `ui-agents-skills-config`) have identical code in `agent_management_service.py`. The `PROJECT_AGENTS_DIR` constant is `.claude/agents/` on both branches.

The confusion arose because two directories with similar names serve **entirely different purposes**:

| Directory | Purpose | Owner | Contents |
|-----------|---------|-------|----------|
| `.claude-mpm/agents/` | MPM internal configuration and agent templates/source definitions | MPM framework | Currently empty on disk |
| `.claude/agents/` | Claude Code runtime deployment target | Claude Code | 44 deployed `.md` agent files |
| `.claude-mpm/config/agents/` | Agent tier configuration (YAML sources) | MPM config system | Agent definition YAML files |

**Deployment flow**: Source tiers (cache, project config `.claude-mpm/config/agents/`, user config) are compiled and deployed as `.md` files to `.claude/agents/` for Claude Code consumption.

There IS a pre-existing bug worth noting: `get_path_manager().CONFIG_DIR` references a non-existent attribute (should be `CONFIG_DIR_NAME`). However, this bug exists identically on both branches, is not reached by any production code path, and is unrelated to the auto-configure feature.

### Documents affected

| Document | Sections Amended | Nature of Amendment |
|----------|-----------------|---------------------|
| **01-main-branch-cli-path.md** | None | No references to the incorrect claim found |
| **02-dashboard-branch-api-path.md** | None | No references to the incorrect claim found |
| **03-comparison-overlap-divergence.md** | None | No references to the incorrect claim found |
| **04-cli-impact-assessment.md** | Section 1 table, Section 2.6, Section 7 (summary matrix, rationale, caveats, overall risk rating) | 6 corrections. Risk downgraded from Medium to Low. Path change claims struck through and replaced with correct architecture explanation. |
| **05-devils-advocate-and-unification.md** | Section 1.3, Section 1.5, Phase 6, Open Question 8 | 4 corrections. Path change challenges marked as moot. "Three simultaneous changes" corrected to "two". Migration question struck through. |

### Impact on conclusions

**Document 04 -- CLI Impact Assessment:**
- Overall risk rating remains **Low Risk** but the number of caveats is reduced from two to one
- The surviving caveat is the `preview_configuration()` sync-to-async rewrite
- The `agent_management_service.py` changes are now correctly characterized as **additive only** (new UI enrichment methods `get_agent_details()` and `get_enriched_agents()`)
- The behavioral change count drops from three to one (only the `preview_configuration` rewrite)

**Document 05 -- Devil's Advocate and Unification:**
- The "compound risk" argument weakens: two simultaneous changes instead of three
- The migration question (Open Question 8) is moot -- no migration path needed
- The Phase 6 unification plan item about `CONFIG_DIR` is correctly identified as a pre-existing bug fix, not a branch-introduced change
- The overall devil's advocate challenge to "Low Risk" classification loses one of its supporting arguments

**Net effect:** The original "Low Risk (with caveats)" conclusion in Document 04 is **strengthened** by this correction. One of the two cited caveats (the path change) does not exist, leaving only the `preview_configuration` rewrite as a genuine concern.

---

## Amendment Format Convention

All corrections in the research documents follow this format:

1. **Original text preserved** with ~~strikethrough~~ formatting
2. **Correction block** marked with:
   ```
   > **CORRECTION (YYYY-MM-DD):** Explanation of what changed and why.
   ```
3. **Cross-references** to related corrections in other documents
4. **This changelog** updated with each amendment

This approach ensures:
- Full research audit trail is maintained
- Original reasoning is visible for context
- Corrections are clearly distinguishable from original content
- Amendments are traceable by date
