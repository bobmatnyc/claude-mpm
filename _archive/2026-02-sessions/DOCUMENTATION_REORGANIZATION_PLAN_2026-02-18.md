# Documentation Reorganization Plan

**Date**: 2026-02-18
**Current Version**: 5.9.12
**Prepared By**: Documentation Agent

## Executive Summary

This plan addresses documentation cleanup needs identified in the comprehensive documentation audit:
- 14 session summary files cluttering project root
- 2 quickstart files (one comprehensive, one minimal)
- GitHub multi-account documentation split between root and docs/
- Version numbers outdated in status files
- Potential broken links after reorganization

## Issues Identified

### 1. Session Summaries in Root Directory (14 files)
Root directory contains debugging/implementation session summaries that should be archived:
- 6 token tracking diagnostic files (Feb 7)
- 3 documentation summary files (Feb 18)
- 3 implementation summary files (Feb 10-18)
- 1 external package audit (Feb 18)
- 1 pending tasks file (Feb 8)

### 2. Quickstart File Confusion
- `docs/getting-started/quick-start.md` (2.6K) - Brief 5-minute guide
- `docs/getting-started/quickstart.md` (23K) - Comprehensive "Hello World" tutorial
- Both serve different purposes but naming is confusing
- Main README.md links to docs/user/quickstart.md which redirects to quick-start.md

### 3. GitHub Multi-Account Documentation
- `MULTI_ACCOUNT_SETUP_SUMMARY.md` (root) - Setup completion summary
- `docs/GITHUB_MULTI_ACCOUNT_SETUP.md` - Detailed setup guide
- Overlapping content, should consolidate

### 4. Outdated Version References
- `DOCUMENTATION_STATUS.md` shows v5.9.9 (current is 5.9.12)

### 5. Useful Guide in Root
- `PACKAGE_INSTALLER_UV_FIX.md` - Valuable reference, belongs in docs/guides/

## Reorganization Actions

### Phase 1: Archive Session Summaries

Create archive directory and move session files:

```bash
# Create archive directory
mkdir -p _archive/2026-02-sessions

# Archive token tracking diagnostics (Feb 7)
git mv DIAGNOSTIC_REPORT.md _archive/2026-02-sessions/DIAGNOSTIC_REPORT_2026-02-07.md
git mv TOKEN_EMISSION_DIAGNOSTIC.md _archive/2026-02-sessions/TOKEN_EMISSION_DIAGNOSTIC_2026-02-07.md
git mv TOKEN_TRACKING_DEBUG_SUMMARY.md _archive/2026-02-sessions/TOKEN_TRACKING_DEBUG_SUMMARY_2026-02-07.md
git mv TOKEN_USAGE_NEXT_STEPS.md _archive/2026-02-sessions/TOKEN_USAGE_NEXT_STEPS_2026-02-07.md
git mv TOKEN_USAGE_STRUCTURE_COMPARISON.md _archive/2026-02-sessions/TOKEN_USAGE_STRUCTURE_COMPARISON_2026-02-07.md
git mv STOP_EVENT_INVESTIGATION_FINAL.md _archive/2026-02-sessions/STOP_EVENT_INVESTIGATION_FINAL_2026-02-07.md

# Archive documentation summaries (Feb 18)
git mv DOCUMENTATION_REVIEW_SUMMARY.md _archive/2026-02-sessions/DOCUMENTATION_REVIEW_SUMMARY_2026-02-18.md
git mv DOCUMENTATION_UPDATE_SUMMARY.md _archive/2026-02-sessions/DOCUMENTATION_UPDATE_SUMMARY_2026-02-18.md

# Archive implementation summaries
git mv IMPLEMENTATION_SUMMARY.md _archive/2026-02-sessions/SKILLS_OPTIMIZE_IMPLEMENTATION_2026-02-18.md
git mv MERMAID_IMPLEMENTATION_SUMMARY.md _archive/2026-02-sessions/MERMAID_IMPLEMENTATION_SUMMARY_2026-02-10.md
git mv EXTERNAL_PACKAGE_SETUP_AUDIT.md _archive/2026-02-sessions/EXTERNAL_PACKAGE_SETUP_AUDIT_2026-02-18.md
git mv SKILLS_OPTIMIZE_README.md _archive/2026-02-sessions/SKILLS_OPTIMIZE_README_2026-02-18.md

# Archive GitHub multi-account summary
git mv MULTI_ACCOUNT_SETUP_SUMMARY.md _archive/2026-02-sessions/MULTI_ACCOUNT_SETUP_SUMMARY_2026-02-19.md

# Archive pending tasks
git mv PENDING_TASKS.md _archive/2026-02-sessions/PENDING_TASKS_2026-02-08.md
```

### Phase 2: Move Guides to Proper Location

```bash
# Move UV fix guide to docs/guides/
git mv PACKAGE_INSTALLER_UV_FIX.md docs/guides/package-installer-uv-fix.md
```

### Phase 3: Resolve Quickstart Naming

**Decision**: Keep both files but rename for clarity:
- `quick-start.md` → Keep as is (5-minute quick start)
- `quickstart.md` → Rename to `tutorial.md` (comprehensive tutorial)

```bash
# Rename comprehensive tutorial
git mv docs/getting-started/quickstart.md docs/getting-started/tutorial.md
```

### Phase 4: Consolidate GitHub Multi-Account Documentation

**Decision**: Keep docs/GITHUB_MULTI_ACCOUNT_SETUP.md as the authoritative guide. Move to guides directory for better discoverability:

```bash
# Move to guides directory
git mv docs/GITHUB_MULTI_ACCOUNT_SETUP.md docs/guides/github-multi-account-setup.md
```

### Phase 5: Update References

**Files to update**:
1. `README.md` - Update link from docs/user/quickstart.md to docs/getting-started/quick-start.md
2. `docs/README.md` - Update references if any
3. `docs/getting-started/README.md` - Add tutorial.md, update quickstart references
4. `docs/guides/README.md` - Add github-multi-account-setup.md and package-installer-uv-fix.md
5. `docs/user/quickstart.md` - Already redirects correctly

**Specific updates**:

**README.md**:
- Line 343: Update `docs/user/quickstart.md` to `docs/getting-started/quick-start.md`

**docs/getting-started/README.md**:
- Add entry for `tutorial.md` - comprehensive Hello World tutorial
- Clarify difference between quick-start.md and tutorial.md

**docs/guides/README.md**:
- Add `github-multi-account-setup.md` - Setup guide for multiple GitHub accounts
- Add `package-installer-uv-fix.md` - UV project detection and package installation

### Phase 6: Update Documentation Status

Update `DOCUMENTATION_STATUS.md`:
- Change version from 5.9.9 to 5.9.12
- Add section documenting this reorganization
- Summarize what was archived and why

### Phase 7: Create Archive Index

Create `_archive/2026-02-sessions/README.md`:

```markdown
# February 2026 Session Archives

Session summaries and diagnostic reports from development sessions.

## Token Tracking Investigation (Feb 7)
- DIAGNOSTIC_REPORT_2026-02-07.md
- TOKEN_EMISSION_DIAGNOSTIC_2026-02-07.md
- TOKEN_TRACKING_DEBUG_SUMMARY_2026-02-07.md
- TOKEN_USAGE_NEXT_STEPS_2026-02-07.md
- TOKEN_USAGE_STRUCTURE_COMPARISON_2026-02-07.md
- STOP_EVENT_INVESTIGATION_FINAL_2026-02-07.md

## Documentation Updates (Feb 18)
- DOCUMENTATION_REVIEW_SUMMARY_2026-02-18.md
- DOCUMENTATION_UPDATE_SUMMARY_2026-02-18.md

## Feature Implementation (Feb 10-18)
- SKILLS_OPTIMIZE_IMPLEMENTATION_2026-02-18.md
- MERMAID_IMPLEMENTATION_SUMMARY_2026-02-10.md
- EXTERNAL_PACKAGE_SETUP_AUDIT_2026-02-18.md
- SKILLS_OPTIMIZE_README_2026-02-18.md

## Setup Summaries
- MULTI_ACCOUNT_SETUP_SUMMARY_2026-02-19.md
- PENDING_TASKS_2026-02-08.md
```

### Phase 8: Verify GitHub Multi-Account Documentation

Verify `docs/guides/github-multi-account-setup.md`:
- ✅ References `claude-mpm gh` commands (not old scripts)
- ✅ Commands: switch, verify, status, setup
- ✅ No references to deprecated scripts

## Link Validation Checklist

After reorganization, validate these links:
- [ ] README.md → docs/getting-started/quick-start.md
- [ ] README.md → docs/getting-started/README.md
- [ ] docs/README.md → getting-started/quick-start.md
- [ ] docs/README.md → getting-started/tutorial.md (new)
- [ ] docs/getting-started/README.md → quick-start.md
- [ ] docs/getting-started/README.md → tutorial.md (new)
- [ ] docs/guides/README.md → github-multi-account-setup.md
- [ ] docs/guides/README.md → package-installer-uv-fix.md
- [ ] docs/user/quickstart.md → ../getting-started/quick-start.md (already correct)

## Expected Results

### Root Directory After Cleanup
```
README.md
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
CLAUDE.md
LICENSE-FAQ.md
DOCUMENTATION_STATUS.md (updated to v5.9.12)
```

### New/Updated Files
- `_archive/2026-02-sessions/` (14 archived files + README.md)
- `docs/guides/github-multi-account-setup.md` (moved from docs/)
- `docs/guides/package-installer-uv-fix.md` (moved from root)
- `docs/getting-started/tutorial.md` (renamed from quickstart.md)

### Removed Confusion
- Clear naming: quick-start (5 min) vs tutorial (60 min)
- Single authoritative GitHub multi-account guide
- Session summaries archived, not deleted
- Root directory contains only permanent documentation

## Risk Mitigation

1. **Use git mv**: Preserves file history
2. **No deletions**: Archive, don't delete
3. **Validate links**: Check all cross-references after moves
4. **Commit in phases**: Separate commits for archive, moves, updates
5. **Test documentation**: Verify getting-started guides still work

## Success Criteria

- [ ] Root directory has only 7 permanent documentation files
- [ ] All 14 session summaries archived with timestamps
- [ ] No broken links in README.md or docs/
- [ ] Quickstart naming clarified (quick-start vs tutorial)
- [ ] GitHub multi-account guide in docs/guides/
- [ ] UV fix guide in docs/guides/
- [ ] DOCUMENTATION_STATUS.md updated to v5.9.12
- [ ] Archive index created
- [ ] All git history preserved
