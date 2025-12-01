# Claude MPM v5.0 Documentation Audit Report

**Research Date**: 2025-12-01
**Version**: 5.0.0
**Purpose**: Comprehensive documentation audit for v5.0 publishing readiness
**Status**: Complete

---

## Executive Summary

Claude MPM v5.0 has **242 documentation files** across multiple categories, with **59 research documents** (24%) that should be evaluated for promotion to user-facing documentation. The release includes 8 major feature areas, of which **4 are underdocumented** for end users.

**Key Findings**:
- ✅ Implementation docs are thorough (8 files in /docs/implementation/)
- ✅ CHANGELOG.md comprehensively documents all features
- ✅ UPGRADING_TO_V5.md provides excellent migration guide
- ⚠️ **Critical Gap**: Auto-configuration system lacks user-facing docs
- ⚠️ **Critical Gap**: Agent preset deployment system undocumented
- ⚠️ **Critical Gap**: PR-based workflow for agents/skills undocumented
- ⚠️ Slash commands documented but not integrated into main docs
- ⚠️ Research docs contain valuable content not exposed to users

**Publishing Blocker**: Auto-configuration and preset systems need user guides before v5.0 can be considered "complete" documentation.

---

## Documentation Inventory

### Summary Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **Total Documentation Files** | 242 | 100% |
| Research Documents | 59 | 24.4% |
| User Documentation | 14 | 5.8% |
| Developer Documentation | 29 | 12.0% |
| Reference Documentation | 19 | 7.9% |
| Implementation Guides | 8 | 3.3% |
| Feature Documentation | 3 | 1.2% |
| Archived Documents | 28 | 11.6% |
| Root-Level Docs | 11 | 4.5% |

### Directory Structure Analysis

```
docs/
├── _archive/               # 28 files (archived sessions, designs)
├── agents/                 # 6 files (agent patterns, creation, PM workflow)
├── architecture/           # 2 files (single-tier design)
├── design/                 # 6 files (skills integration, structured questions)
├── developer/              # 29 files (architecture, extending, publishing)
│   ├── 03-development/
│   ├── 07-agent-system/
│   ├── 10-schemas/
│   ├── 11-dashboard/
│   ├── 13-mcp-gateway/
│   ├── code-navigation/    # 8 files (detailed code maps)
│   └── verification-reports/ # 8 files (QA reports)
├── development/            # 3 files (internals, test hang investigation)
├── engineering/            # 2 files (thread safety audit)
├── examples/               # 2 files (resume log examples)
├── features/               # 3 files ⚠️ (git history, hierarchical base agents, instruction caching)
├── guides/                 # 14 files (doctor, skills, tickets, single-tier)
├── implementation/         # 8 files ✅ (Anthropic skills, flat deployment, two-phase progress)
├── migration/              # 4 files (JSON to MD, v5 agent migration, session files)
├── reference/              # 19 files ✅ (agent sources API, CLI review, skills API, slash commands)
├── releases/               # 2 files (release evidence)
├── research/               # 59 files ⚠️ (24% of all docs - many should be promoted)
├── security/               # 1 file (pre-release scan)
├── testing/                # 8 files (verification reports)
├── tickets/                # 5 files (ticket tracking)
├── user/                   # 14 files ✅ (getting started, agent sources, skills guide)
├── workflows/              # 1 file (ticketing delegation)
└── [Root Level]/           # 11 files (AGENTS.md, API.md, ARCHITECTURE.md, etc.)
```

---

## v5.0 Features Inventory

### Feature 1: Git Repository Integration for Agents ✅ WELL-DOCUMENTED

**Status**: ✅ Complete documentation

**Implementation Files**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/git_source_manager.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**User Documentation**:
- ✅ `docs/user/agent-sources.md` (comprehensive, 36KB)
- ✅ `README.md` sections (quick start, features)
- ✅ `CHANGELOG.md` entry
- ✅ `UPGRADING_TO_V5.md` section

**Reference Documentation**:
- ✅ `docs/reference/agent-sources-api.md` (28KB)
- ✅ `docs/reference/cli-agent-source.md` (23KB)

**Implementation Documentation**:
- ✅ `docs/implementation/git-sources-default.md`
- ✅ `docs/implementation/startup-agent-sync-integration.md`

**Research Documents** (should review for promotion):
- `docs/research/agent-git-sources-sync-mechanism-2025-11-30.md` (50KB)
- `docs/research/git-agents-deployment-architecture-analysis-2025-11-30.md`
- `docs/research/remote-agent-sync-path-filtering-2025-12-01.md`

**Gaps**: None - this feature is thoroughly documented at all levels.

---

### Feature 2: Git Repository Integration for Skills ✅ WELL-DOCUMENTED

**Status**: ✅ Complete documentation

**Implementation Files**:
- Skills use same `GitSourceSyncService` as agents
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_deployer.py`

**User Documentation**:
- ✅ `docs/user/skills-guide.md` (comprehensive)
- ✅ `README.md` sections
- ✅ `CHANGELOG.md` entry

**Reference Documentation**:
- ✅ `docs/reference/skills-api.md` (32KB)
- ✅ `docs/reference/skills-quick-reference.md` (15KB)

**Implementation Documentation**:
- ✅ `docs/implementation/anthropic-skills-integration.md`
- ✅ `docs/implementation/flat-skill-deployment.md`

**Research Documents**:
- `docs/research/skills-git-system-analysis-2025-11-30.md`
- `docs/research/claude-code-nested-skills-discovery-2025-11-30.md`
- `docs/research/skills-deployment-location-analysis-2025-12-01.md`

**Gaps**: None - this feature is thoroughly documented.

---

### Feature 3: Auto-Configuration System ⚠️ UNDERDOCUMENTED

**Status**: ⚠️ **CRITICAL GAP** - Implementation complete, user docs missing

**Implementation Files**:
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/auto_configure.py`
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/auto_config_manager.py`
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/auto_deploy_index_parser.py`
- ✅ Slash commands: `mpm-agents-detect.md`, `mpm-agents-recommend.md`, `mpm-agents-auto-configure.md`

**User Documentation**:
- ⚠️ `docs/user/getting-started.md` mentions auto-configuration (line 17) but no details
- ⚠️ **MISSING**: Dedicated auto-configuration user guide
- ⚠️ **MISSING**: Tutorial showing detection → recommendation → deployment workflow
- ⚠️ **MISSING**: Examples of auto-detected projects
- ⚠️ **MISSING**: Troubleshooting guide for auto-configuration

**Slash Command Documentation**:
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-agents-detect.md` (178 lines, detailed)
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-agents-recommend.md` (224 lines, detailed)
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/mpm-agents-auto-configure.md` (exists in codebase)

**Reference Documentation**:
- ⚠️ **MISSING**: CLI reference for `claude-mpm agents detect`
- ⚠️ **MISSING**: CLI reference for `claude-mpm agents recommend`

**Research Documents** (valuable content):
- `docs/research/agents-skills-cli-structure-research-2025-12-01.md` (50KB)

**Gaps**:
1. ❌ No user-facing guide in `docs/user/`
2. ❌ No integration with getting-started flow
3. ❌ Slash command docs not discoverable in main documentation
4. ❌ CLI commands not documented in reference section
5. ❌ No examples of auto-configuration in action
6. ❌ No troubleshooting section for detection failures

**Priority**: **HIGH** - This is a marquee feature that needs visibility.

---

### Feature 4: Agent Preset Deployment System ⚠️ UNDERDOCUMENTED

**Status**: ⚠️ **CRITICAL GAP** - Implementation complete, no user documentation

**Implementation Files**:
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/config/agent_presets.py` (259 lines, 11 presets)
- ✅ `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/agent_preset_service.py`
- ✅ Presets: minimal, python-dev, python-fullstack, javascript-backend, react-dev, nextjs-fullstack, rust-dev, golang-dev, java-dev, mobile-flutter, data-eng

**User Documentation**:
- ❌ **MISSING**: No mention of presets in any user documentation
- ❌ **MISSING**: No guide showing `claude-mpm agents deploy --preset python-dev`
- ❌ **MISSING**: No list of available presets
- ❌ **MISSING**: No examples of preset usage

**Reference Documentation**:
- ❌ **MISSING**: CLI reference for `--preset` flag
- ❌ **MISSING**: API documentation for preset system

**Research Documents**:
- None found - this feature was implemented without research docs

**Gaps**:
1. ❌ No user guide for preset system
2. ❌ Not mentioned in `docs/user/getting-started.md`
3. ❌ Not mentioned in `docs/user/agent-sources.md`
4. ❌ Not documented in CLI reference
5. ❌ No examples showing preset vs manual deployment
6. ❌ No preset comparison guide

**Priority**: **HIGH** - Major feature with zero user-facing documentation.

**Recommendation**: Create `docs/user/agent-presets.md` with:
- Overview of preset system
- List of all 11 presets with descriptions
- Usage examples: `claude-mpm agents deploy --preset python-dev`
- Comparison: preset vs auto-configure vs manual
- How to customize presets for teams

---

### Feature 5: Hierarchical BASE-AGENT.md Inheritance ✅ DOCUMENTED

**Status**: ✅ Good documentation

**Implementation Files**:
- Part of agent deployment system
- Implemented in agent source sync service

**User Documentation**:
- ✅ `docs/features/hierarchical-base-agents.md` (12KB)
- ✅ `UPGRADING_TO_V5.md` section (detailed example)
- ✅ `README.md` section with example

**Implementation Documentation**:
- ✅ `docs/implementation/base-agent-hierarchy.md`

**Gaps**: Minor - feature documentation exists but could be cross-linked better.

---

### Feature 6: Two-Phase Progress Bars ✅ DOCUMENTED

**Status**: ✅ Complete implementation documentation

**Implementation Files**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`

**Implementation Documentation**:
- ✅ `docs/implementation/two-phase-progress-bars.md` (9KB)

**User Documentation**:
- ✅ Mentioned in `CHANGELOG.md`
- ✅ Visual examples in `UPGRADING_TO_V5.md`

**Gaps**: None - user sees feature in action, implementation documented.

---

### Feature 7: PR-Based Workflow for Agents/Skills ⚠️ UNDERDOCUMENTED

**Status**: ⚠️ Research document exists, no user guide

**Research Documents**:
- ✅ `docs/research/agent-skill-pr-workflow-2025-12-01.md` (42KB, comprehensive)

**User Documentation**:
- ❌ **MISSING**: No guide in `docs/user/`
- ❌ **MISSING**: No contribution guide for agents/skills
- ❌ **MISSING**: No PR workflow documentation

**Gaps**:
1. ❌ No user-facing documentation for PR workflow
2. ❌ No contribution guide for community agents/skills
3. ❌ Research doc contains valuable workflow but not exposed

**Priority**: **MEDIUM** - Important for community contributions.

**Recommendation**: Promote `agent-skill-pr-workflow-2025-12-01.md` to `docs/guides/contributing-agents-skills.md`.

---

### Feature 8: Homebrew Tap Automation ✅ DOCUMENTED

**Status**: ✅ Complete documentation (Phase 5.5)

**Implementation Files**:
- `/Users/masa/Projects/claude-mpm/scripts/manage_version.py` (update-homebrew functionality)

**Developer Documentation**:
- ✅ `docs/reference/DEPLOY.md` section on Homebrew
- ✅ `docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md` (11KB)
- ✅ `CLAUDE.md` section on Homebrew tap integration

**Gaps**: None - thoroughly documented for developers.

---

### Feature 9: Template Deployment Architecture ✅ DOCUMENTED

**Status**: ✅ Implementation documented

**Recent Commits**:
- `1ca2f21c feat: fix PM instructions deployment architecture`
- `9400b9d5 docs: clarify template deployment design in startup flow`
- `9c824343 feat: integrate template deployment with PM instructions build`

**Implementation Documentation**:
- Documented in recent commit messages and code comments

**Gaps**: None - internal architecture change, no user-facing docs needed.

---

### Feature 10: Instruction Caching ✅ DOCUMENTED

**Status**: ✅ Complete documentation

**Implementation Files**:
- File-based caching system for agent instructions

**User Documentation**:
- ✅ `README.md` section on performance

**Feature Documentation**:
- ✅ `docs/features/instruction_caching.md` (15KB)

**Implementation Documentation**:
- ✅ `docs/implementation/instruction-cache-migration.md`

**Research Documents**:
- `docs/research/1M-446-instruction-cache-research.md` (25KB)
- `docs/research/arg-max-limit-analysis-2025-12-01.md` (34KB)

**Gaps**: None - well documented.

---

## Documentation Gap Analysis

### Critical Gaps (Publishing Blockers)

1. **Auto-Configuration System** ⚠️
   - **Impact**: HIGH - Marquee feature
   - **Missing**: User guide, CLI reference, examples
   - **Action Required**: Create `docs/user/auto-configuration.md`
   - **Estimated Effort**: 2-3 hours

2. **Agent Preset Deployment** ⚠️
   - **Impact**: HIGH - 11 presets implemented with zero docs
   - **Missing**: User guide, preset list, usage examples
   - **Action Required**: Create `docs/user/agent-presets.md`
   - **Estimated Effort**: 1-2 hours

### High-Priority Gaps

3. **PR-Based Workflow** ⚠️
   - **Impact**: MEDIUM - Important for community
   - **Missing**: Contribution guide
   - **Action Required**: Promote research doc to `docs/guides/contributing-agents-skills.md`
   - **Estimated Effort**: 30 minutes (cleanup and promotion)

4. **Slash Command Discoverability** ⚠️
   - **Impact**: MEDIUM - Commands exist but hidden
   - **Missing**: Integration with main documentation
   - **Action Required**: Add slash command reference to user guides
   - **Estimated Effort**: 1 hour

### Medium-Priority Improvements

5. **Research Document Promotion**
   - **Impact**: MEDIUM - Valuable content locked away
   - **Missing**: User-facing versions of research insights
   - **Action Required**: Review and promote key research docs
   - **Estimated Effort**: 3-4 hours

6. **Feature Documentation Cross-Linking**
   - **Impact**: LOW - Docs exist but not well connected
   - **Missing**: Navigation between related features
   - **Action Required**: Add cross-references
   - **Estimated Effort**: 1-2 hours

---

## Documentation Structure Assessment

### Current Organization

**Strengths**:
- ✅ Clear separation: user/ vs developer/ vs reference/
- ✅ Implementation docs in dedicated directory
- ✅ Research docs properly isolated
- ✅ Good use of CHANGELOG.md and UPGRADING_TO_V5.md

**Weaknesses**:
- ⚠️ 24% of docs are in research/ (59 files)
- ⚠️ Some research docs should be user-facing
- ⚠️ Slash command docs not integrated
- ⚠️ Root-level docs redundant with deeper docs
- ⚠️ guides/ directory overlaps with user/ and reference/

### Redundancies Identified

1. **Root-Level Redundancy**:
   - `AGENTS.md` vs `docs/agents/`
   - `API.md` vs `docs/reference/` APIs
   - `ARCHITECTURE.md` vs `docs/developer/ARCHITECTURE.md`

   **Recommendation**: Consolidate or clearly differentiate purpose (overview vs deep-dive).

2. **guides/ vs user/ Overlap**:
   - `docs/guides/skills-system.md` vs `docs/user/skills-guide.md`
   - Both contain user-facing content

   **Recommendation**: Merge guides into user/ or reserve guides/ for workflows.

3. **Multiple "Getting Started" Paths**:
   - `docs/user/getting-started.md`
   - `docs/user/quickstart.md`
   - `docs/native-agents-quickstart.md`

   **Recommendation**: Single canonical getting-started with quick-reference card.

### Navigation Issues

1. **No Documentation Index**:
   - 242 files with no master index
   - Difficult to discover documentation

   **Recommendation**: Create `docs/INDEX.md` with categorized links.

2. **Missing Cross-References**:
   - Related docs don't link to each other
   - Example: auto-configure docs should link to preset docs

   **Recommendation**: Add "Related Documentation" sections.

3. **Slash Command Isolation**:
   - Excellent slash command docs exist in `/src/claude_mpm/commands/`
   - Not discoverable from main documentation

   **Recommendation**: Link from `docs/reference/slash-commands.md`.

---

## Research Documents: Promotion Candidates

Of 59 research documents, the following contain valuable user-facing content:

### High-Priority Promotions

1. **`agent-skill-pr-workflow-2025-12-01.md`** (42KB)
   - Promote to: `docs/guides/contributing-agents-skills.md`
   - Rationale: Comprehensive PR workflow guide for community

2. **`agents-skills-cli-structure-research-2025-12-01.md`** (50KB)
   - Extract sections to: `docs/reference/cli-agents.md`
   - Rationale: CLI command documentation

3. **`claude-4-5-best-practices-2025-11-25.md`** (36KB)
   - Promote to: `docs/user/best-practices.md`
   - Rationale: User-facing best practices

### Medium-Priority Extractions

4. **`git-agents-deployment-architecture-analysis-2025-11-30.md`**
   - Extract user-relevant sections to agent-sources.md
   - Keep technical architecture in research/

5. **`skills-deployment-location-analysis-2025-12-01.md`**
   - Extract deployment rationale to skills-guide.md
   - Archive technical analysis

### Keep in Research (Implementation Details)

- All `1M-*` ticket research docs (historical record)
- Performance analysis docs (technical deep-dives)
- Bug investigation docs (troubleshooting history)
- Optimization research (implementation-focused)

---

## Recommendations

### Immediate Actions (Before Publishing)

1. **Create Auto-Configuration User Guide** (2-3 hours)
   - File: `docs/user/auto-configuration.md`
   - Content: Detection → Recommendation → Deployment workflow
   - Include: Examples, troubleshooting, comparison with presets

2. **Create Agent Preset Guide** (1-2 hours)
   - File: `docs/user/agent-presets.md`
   - Content: All 11 presets with use cases
   - Include: Usage examples, customization guide

3. **Update CLI Reference** (1 hour)
   - File: `docs/reference/cli-agents.md`
   - Add: `agents detect`, `agents recommend`, `--preset` flag
   - Cross-link with slash commands

4. **Integrate Slash Commands** (30 minutes)
   - Update: `docs/reference/slash-commands.md`
   - Add links to command docs in `/src/claude_mpm/commands/`

### Short-Term Improvements (Post-Publishing)

5. **Promote PR Workflow Guide** (30 minutes)
   - Move: research doc to guides/
   - Clean up and format for end users

6. **Create Documentation Index** (1-2 hours)
   - File: `docs/INDEX.md`
   - Categorized links to all major docs
   - Add to README.md

7. **Consolidate Root-Level Docs** (2 hours)
   - Decide: Keep as overview or merge into docs/
   - Add clear navigation from root to deeper docs

8. **Review Research Documents** (3-4 hours)
   - Identify user-facing content
   - Extract to appropriate locations
   - Archive pure research

### Long-Term Enhancements

9. **Documentation Website** (future)
   - Consider: MkDocs or similar
   - Organization: By user role (user/developer/contributor)

10. **Cross-Linking Audit** (2-3 hours)
    - Add "Related Documentation" sections
    - Ensure navigation between related features

11. **Examples and Tutorials** (ongoing)
    - Add: Real-world examples for each feature
    - Create: Video tutorials for key workflows

---

## Publishing Readiness Assessment

### Documentation Completeness by Feature

| Feature | Implementation | Developer Docs | User Docs | Reference Docs | Status |
|---------|---------------|----------------|-----------|----------------|--------|
| Git Agents | ✅ | ✅ | ✅ | ✅ | **READY** |
| Git Skills | ✅ | ✅ | ✅ | ✅ | **READY** |
| Auto-Configuration | ✅ | ⚠️ | ❌ | ❌ | **BLOCKED** |
| Agent Presets | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| Hierarchical BASE | ✅ | ✅ | ✅ | N/A | **READY** |
| Two-Phase Progress | ✅ | ✅ | ✅ | N/A | **READY** |
| PR Workflow | ✅ | ❌ | ❌ | ❌ | **GAP** |
| Homebrew Tap | ✅ | ✅ | N/A | N/A | **READY** |
| Template Deploy | ✅ | ✅ | N/A | N/A | **READY** |
| Instruction Cache | ✅ | ✅ | ✅ | ✅ | **READY** |

### Overall Assessment

**Publishing Status**: ⚠️ **NOT READY**

**Blockers**:
1. Auto-configuration system lacks user documentation
2. Agent preset system completely undocumented

**Completion**: 80% (8/10 features ready)

**Estimated Time to Publishing Readiness**: 4-6 hours
- 2-3 hours: Auto-configuration guide
- 1-2 hours: Agent presets guide
- 1 hour: CLI reference updates
- 30 minutes: Slash command integration

---

## Priority Areas for Immediate Attention

### Priority 1: Critical (Publishing Blockers)

1. **Auto-Configuration User Guide**
   - Target: `docs/user/auto-configuration.md`
   - Deadline: Before v5.0 publishing
   - Owner: Documentation team

2. **Agent Preset User Guide**
   - Target: `docs/user/agent-presets.md`
   - Deadline: Before v5.0 publishing
   - Owner: Documentation team

### Priority 2: High (Feature Visibility)

3. **CLI Reference Updates**
   - Target: `docs/reference/cli-agents.md`
   - Deadline: Week 1 post-publishing
   - Owner: Technical writer

4. **Slash Command Integration**
   - Target: `docs/reference/slash-commands.md`
   - Deadline: Week 1 post-publishing
   - Owner: Technical writer

### Priority 3: Medium (Quality Improvements)

5. **Research Document Promotion**
   - Target: `docs/guides/contributing-agents-skills.md`
   - Deadline: Month 1 post-publishing
   - Owner: Community manager

6. **Documentation Index**
   - Target: `docs/INDEX.md`
   - Deadline: Month 1 post-publishing
   - Owner: Documentation team

---

## Conclusion

Claude MPM v5.0 has solid implementation and developer documentation, but **two critical user-facing gaps** prevent full publishing readiness:

1. **Auto-configuration system**: Implementation complete, slash commands documented, but no user guide
2. **Agent preset system**: 11 presets implemented with zero user-facing documentation

**Recommendation**: Allocate 4-6 hours to create these two user guides before publishing v5.0. The additional documentation will significantly improve user experience and feature discoverability.

**Post-Publishing**: Focus on promoting valuable research content to user-facing documentation and improving cross-linking between related features.

---

## Appendix A: Full Documentation Tree

See bash output above for complete file listing (242 files).

## Appendix B: v5.0 Feature Commit History

```
1ca2f21c feat: fix PM instructions deployment architecture
9400b9d5 docs: clarify template deployment design in startup flow
f4f401f2 refactor: optimize startup process and remove redundancies
9c824343 feat: integrate template deployment with PM instructions build
e1986e7f feat: implement PR-based workflow for agent and skill management (Phase 1-3)
c2a2e278 refactor: optimize PM instructions with content consolidation (Phase 3)
0307c3c8 refactor: optimize PM instructions with template references (Phase 2)
168bb7b5 docs: add comprehensive CLI command structure review
e83de397 docs: add agent and skill repository git synchronization guide
59b0e813 feat: add 'claude-mpm agents cleanup' command for agent migration
8f28813a refactor: extract MCP-specific instructions to agent files
75185c4c refactor: standardize template filenames to use dashes instead of underscores
cfec5916 feat: implement parallel downloads for skills sync with thread-safe ETag caching
```

## Appendix C: Slash Command Documentation Files

All slash commands have comprehensive documentation in `/src/claude_mpm/commands/`:

- `mpm-agents-detect.md` (178 lines)
- `mpm-agents-recommend.md` (224 lines)
- `mpm-agents-auto-configure.md` (exists)
- `mpm-agents-list.md`
- `mpm-init.md`
- `mpm-help.md`

These are NOT currently linked from main documentation.

---

**End of Report**
