# Research: Research Agent Work Capture Integration

**Date**: 2025-11-22
**Researcher**: Research Agent (via Engineer during development)
**Related Issue**: N/A
**Status**: Complete

## Executive Summary

Successfully integrated comprehensive work capture imperatives into the research agent (version 2.7.0), implementing dual behavioral modes for automatic research output capture. The research agent now autonomously saves all research to `docs/research/` in structured markdown format (Mode A) and integrates with ticketing systems when available (Mode B) to create issues/subtasks for actionable work or attach findings to existing tickets. This enhancement ensures research traceability, knowledge preservation, and seamless workflow integration without user intervention.

## Research Questions

1. How can research agent automatically capture all work outputs without blocking research delivery?
2. What are the best practices for structuring research documents for future reference?
3. How should research integrate with ticketing systems (mcp-ticketer) for traceability?
4. What classification criteria distinguish actionable work from informational findings?
5. How to handle errors gracefully with appropriate fallback chains?

## Methodology

**Tools Used**:
- File system analysis of existing research agent template (research.json)
- Review of documentation and ticketing agent patterns
- Design of work classification decision tree
- Error handling protocol design with fallback chains

**Scope**:
- Research agent template (research.json) version 2.6.0 → 2.7.0
- Integration of file-based and ticketing capture modes
- Structured markdown template design
- Priority-based routing logic for ticketing context

**Limitations**:
- Did not implement actual Python code changes (template-only update)
- No automated testing of work capture behavior (requires agent runtime testing)
- Assumed mcp-ticketer API patterns based on documentation review

## Findings

### Mode A: File-Based Capture (Mandatory for All Research)

**Implementation Details**:
- **Directory**: Always save to `docs/research/` unless user specifies otherwise
- **Filename Convention**: `{topic}-{type}-{YYYY-MM-DD}.md`
  - Example: `authentication-analysis-2025-11-22.md`
  - Uses kebab-case for multi-word topics
  - Includes ISO date for chronological organization
- **Fallback Chain**:
  1. `docs/research/{filename}.md`
  2. If failed: Create directory with `mkdir -p docs/research/`
  3. If still failed: `./research/{filename}.md`
  4. If still failed: `./{filename}.md`
  5. Final fallback: Return research to user with error message

**Structured Document Template**:
```markdown
# Research: {Topic}

**Date**: {ISO 8601 Date}
**Researcher**: Research Agent
**Related Issue**: {ISSUE_ID or "N/A"}
**Status**: {In Progress | Complete | Archived}

## Executive Summary
{1-2 paragraph overview}

## Research Questions
1. {Question 1}
2. {Question 2}

## Methodology
- {Tools used}
- {Scope}
- {Limitations}

## Findings
{Detailed findings organized by category}

## Analysis
{Synthesis of findings}

## Recommendations
### High Priority
### Medium Priority
### Low Priority / Future Considerations

## Action Items
- [ ] {Actionable tasks}

## References
{Sources, links, related documents}

## Appendix
{Optional: supplementary data}
```

**Benefits**:
- Consistent structure across all research outputs
- Easy to locate research by topic and date
- Graceful degradation with fallback locations
- Non-blocking behavior (research always delivered to user)

### Mode B: Ticketing Integration (When mcp-ticketer Available)

**Priority-Based Routing**:

**Option 1: Issue ID Available** (HIGHEST PRIORITY)
- **Detection**: User provides ticket ID or URL in request
- **Actionable Work**: Create subtask under parent issue
  - Tool: `mcp__mcp-ticketer__issue_create`
  - Parent: Original ISSUE_ID
  - Tags: `["research", "analysis"]`
- **Informational Findings**: Attach file + add comment
  - Tool: `mcp__mcp-ticketer__ticket_attach`
  - Tool: `mcp__mcp-ticketer__ticket_comment`
  - Summary in comment with link to full document

**Option 2: Project/Epic Available** (NO ISSUE ID)
- **Detection**: User mentions project or default project configured
- **Actionable Work**: Create new issue in project
  - Tool: `mcp__mcp-ticketer__issue_create`
  - epic_id: PROJECT_ID or EPIC_ID
- **Informational Findings**: Attach to project/epic
  - Similar to Option 1b

**Option 3: No Ticketing Context** (FALLBACK)
- File-based capture only
- Inform user: "No ticketing context available"
- Suggest providing issue ID or configuring default project

**Work Classification Criteria**:

**Actionable Work** (create issue/subtask):
- Research identifies implementation tasks
- Bugs or problems discovered
- Architectural changes proposed
- Contains TODO items or specific next steps
- Has measurable outcomes or deliverables

**Informational Findings** (attachment/comment):
- Pure analysis without immediate action items
- Background research for context
- Reference material compilation
- Comparative studies
- Documentation review

### Error Handling and Graceful Degradation

**Key Principles**:
1. **Non-Blocking**: Research MUST be delivered to user even if capture fails
2. **Fallback Chain**: Try multiple locations/methods before giving up
3. **Informative Errors**: Log details for debugging, inform user of fallback
4. **Graceful Degradation**: Ticketing failure → File-based only

**File Write Error Handling**:
```
Attempt 1: docs/research/{filename}.md
  ↓ (if fails)
Attempt 2: mkdir -p docs/research/ && retry
  ↓ (if fails)
Attempt 3: ./research/{filename}.md
  ↓ (if fails)
Attempt 4: ./{filename}.md
  ↓ (if fails)
Final: Return research to user + error message
```

**Ticketing API Error Handling**:
```
Attempt: Ticketing integration (create/attach/comment)
  ↓ (if fails)
Log error details
  ↓
Fallback: File-based capture only
  ↓
Inform user: "Ticketing integration failed, saved to docs/research/{filename}.md"
  ↓
Continue with research delivery (non-blocking)
```

### Agent Template Changes

**Version Update**: 2.6.0 → 2.7.0
**Agent Version**: 4.6.0 → 4.7.0

**New Sections Added**:
1. **WORK CAPTURE IMPERATIVES** (major new section in instructions)
   - Mode A: File-based capture (always)
   - Mode B: Ticketing integration (when available)
   - Priority-based routing logic
   - Work classification decision tree
   - Error handling protocols
   - 4 detailed examples demonstrating all scenarios

2. **Updated knowledge.domain_expertise**:
   - Added work capture expertise areas
   - Ticketing integration knowledge
   - Classification heuristics

3. **Updated knowledge.best_practices**:
   - Work capture best practices section
   - Filename conventions
   - Non-blocking behavior requirements
   - Fallback chain specifications

4. **Updated knowledge.constraints**:
   - Work capture must never block research
   - File write failures must not prevent delivery

5. **Updated memory_routing**:
   - New categories for work capture patterns
   - Ticketing integration context
   - Work classification heuristics

6. **Updated metadata**:
   - New tags: "work-capture", "ticketing-integration", "structured-output"
   - Updated description to mention automatic work capture

## Analysis

### Design Decisions and Trade-offs

**Decision 1: Dual Mode (File + Ticketing) vs. Single Mode**
- **Chosen**: Dual mode with file-based as mandatory fallback
- **Rationale**:
  - File-based capture works in all environments (no dependencies)
  - Ticketing integration enhances traceability when available
  - Graceful degradation ensures consistent behavior
- **Trade-off**: More complex logic but better adaptability

**Decision 2: Automatic Capture vs. User-Controlled**
- **Chosen**: Automatic capture with user notification
- **Rationale**:
  - Reduces friction (user doesn't have to request capture)
  - Ensures research is never lost
  - User can override location if needed
- **Trade-off**: Uses disk space but gains traceability

**Decision 3: Structured Template vs. Freeform**
- **Chosen**: Structured markdown template
- **Rationale**:
  - Consistency across all research outputs
  - Easy to locate information (predictable sections)
  - Machine-parseable for future automation
- **Trade-off**: Less flexibility but better organization

**Decision 4: Work Classification (Actionable vs. Informational)**
- **Chosen**: Explicit classification with clear criteria
- **Rationale**:
  - Prevents ticket spam (not everything needs a new issue)
  - Appropriate routing based on work type
  - Clear decision tree for agent to follow
- **Trade-off**: Requires judgment but produces cleaner ticketing

**Decision 5: Non-Blocking Behavior**
- **Chosen**: Research always delivered even if capture fails
- **Rationale**:
  - User's immediate need is research insights, not file management
  - Capture failures shouldn't block workflow
  - Error messages inform user for manual intervention if needed
- **Trade-off**: Potential for lost research if all fallbacks fail (extremely rare)

### Integration with Existing Agent Capabilities

**Synergy with Existing Features**:
1. **Memory Management**: Work capture doesn't conflict with memory discipline (uses Write tool, not Read)
2. **Vector Search Integration**: Research uses vector search, then captures findings
3. **Ticketing Context**: Enhances existing ticket URL detection (v2.5.0) with bidirectional integration
4. **Skills Gap Detection**: Skills recommendations can be captured in research documents
5. **Graceful Degradation**: Consistent with agent's philosophy of adapting to tool availability

**Potential Conflicts Addressed**:
- File write during research could add latency → Mitigated by writing after analysis complete
- Ticketing API failures could block workflow → Mitigated by non-blocking design with fallbacks
- Duplicate research documents → Mitigated by date-based filenames and descriptive topics

## Recommendations

### High Priority

1. **Runtime Testing**: Deploy updated research agent and test all work capture scenarios:
   - File-based capture to docs/research/
   - Ticketing integration with Issue ID context
   - Ticketing integration with Project context
   - Error handling fallbacks (permission errors, API failures)
   - Work classification (actionable vs. informational)

2. **Create Example Research**: Seed docs/research/ with 2-3 example research documents to:
   - Demonstrate template structure
   - Provide reference for consistent formatting
   - Validate directory creation works correctly

3. **Update Agent Documentation**: Add work capture capabilities to agent registry/documentation:
   - Highlight automatic research capture feature
   - Explain when/how ticketing integration activates
   - Document filename conventions and fallback behavior

### Medium Priority

4. **Index/Catalog System**: Create `docs/research/README.md` as an index:
   - List all research documents with brief summaries
   - Organize by topic or date
   - Update automatically (or manual for now)

5. **Research Search Tool**: Consider adding search functionality for research documents:
   - Full-text search across docs/research/
   - Tag-based filtering
   - Date range queries
   - Integration with vector search for semantic queries

6. **Template Customization**: Allow project-specific research templates:
   - `.mcp-research/template.md` override
   - Custom sections for domain-specific needs
   - Backward compatible with default template

### Low Priority / Future Considerations

7. **Research Metrics**: Track research effectiveness:
   - Number of research documents created
   - Actionable findings conversion rate (findings → issues → completion)
   - Research reuse frequency (how often research is referenced later)

8. **Research Lifecycle Management**: Implement research archival/cleanup:
   - Move old research to `docs/research/_archive/` after N days
   - Mark research as "superseded" when new research updates findings
   - Link related research documents (e.g., follow-up investigations)

9. **Visualization**: Generate research reports:
   - Summary dashboard of research activities
   - Topic clustering to identify focus areas
   - Timeline view of research evolution

## Action Items

- [x] Update research.json with work capture imperatives
- [x] Increment version to 2.7.0
- [x] Add comprehensive changelog entry
- [x] Update metadata tags and description
- [x] Create this research document demonstrating the feature
- [ ] Test work capture in runtime environment
- [ ] Create 2-3 example research documents
- [ ] Update agent documentation with work capture capabilities
- [ ] Create docs/research/README.md index
- [ ] Consider template customization options

## References

**Source Files**:
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json` (v2.6.0 → v2.7.0)
- User request specification (detailed work capture requirements)
- Existing ticketing integration patterns (v2.5.0 baseline)

**Related Research**:
- docs/research/skills-research.md (example of existing research document)
- docs/research/mcp-skills-architecture.md (example of technical research)
- docs/research/skills-configurator-integration.md (example of integration research)

**Design Inspiration**:
- Conventional documentation practices (executive summary, methodology, findings)
- Scientific research paper structure (adapted for software engineering)
- Engineering design documents (trade-offs, decisions, recommendations)

## Appendix

### Work Classification Decision Tree (Visual)

```
┌─────────────────────────────────────┐
│      Start Research Task            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│     Conduct Analysis & Synthesis    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│     Classify Work Type:             │
│                                     │
│  ┌─ Actionable?                    │
│  │   • Contains TODOs              │
│  │   • Identifies bugs             │
│  │   • Proposes changes            │
│  │                                 │
│  └─ Informational?                 │
│      • Background research         │
│      • Reference material          │
│      • Comparative analysis        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   ALWAYS: Save to docs/research/    │
│   {topic}-{type}-{YYYY-MM-DD}.md    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Check: mcp-ticketer available?     │
└─────────────────┬───────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
        YES               NO
         │                 │
         ▼                 ▼
┌────────────────┐   ┌──────────────────┐
│ Check Context: │   │ File-based only  │
│                │   │ Inform user      │
│ ├─ Issue ID?   │   └──────────────────┘
│ ├─ Project?    │
│ └─ None?       │
└────────┬───────┘
         │
    ┌────┴────┬─────────┬─────────┐
    │         │         │         │
 Issue ID   Project    None    (see above)
    │         │         │
    ▼         ▼         ▼
┌─────────┐ ┌──────────┐ ┌──────────┐
│Actionable│ │Actionable│ │File-based│
│→ Create  │ │→ Create  │ │only      │
│  subtask │ │  issue   │ │          │
│          │ │          │ │          │
│Info      │ │Info      │ │          │
│→ Attach  │ │→ Attach  │ │          │
│  +comment│ │  to proj │ │          │
└──────────┘ └──────────┘ └──────────┘
         │         │         │
         └─────────┴─────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  Inform User:                       │
│  • File path                        │
│  • Ticket ID (if created/attached)  │
│  • Action taken                     │
└─────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│        Done (Non-blocking)          │
└─────────────────────────────────────┘
```

### Example Filenames

**Good Examples**:
- ✅ `authentication-analysis-2025-11-22.md`
- ✅ `api-design-research-2025-11-22.md`
- ✅ `performance-investigation-2025-11-22.md`
- ✅ `database-scaling-options-2025-11-22.md`
- ✅ `oauth2-implementation-patterns-2025-11-22.md`

**Bad Examples**:
- ❌ `research.md` (too generic)
- ❌ `findings.md` (no topic)
- ❌ `auth_stuff.md` (informal, uses underscore)
- ❌ `nov-22-research.md` (date-first format)
- ❌ `TODO.md` (not research-specific)

### Template Size Comparison

**Before (v2.6.0)**:
- Instructions: ~5,800 words
- Total JSON: ~15KB

**After (v2.7.0)**:
- Instructions: ~10,500 words (81% increase)
- Total JSON: ~27KB (80% increase)

**Justification for Size Increase**:
- Comprehensive work capture imperatives are complex (dual modes, priority routing, error handling)
- Four detailed examples essential for agent understanding (each 150-200 words)
- Decision tree and classification criteria require explicit specification
- Error handling fallbacks need step-by-step protocols
- Non-blocking behavior requires careful explanation
- Trade-off: Larger template but autonomous work capture (reduces user friction)

### Backward Compatibility

**Breaking Changes**: None
- Research agent continues to function exactly as before if work capture fails
- Non-blocking design ensures existing workflows unaffected
- File-based capture is additive (creates files but doesn't modify behavior)

**Graceful Degradation**:
- If Write tool unavailable: Research still delivered to user verbally
- If mcp-ticketer unavailable: File-based capture only (no ticketing)
- If docs/research/ write fails: Fallback to alternative locations
- All errors logged and reported to user with suggestions

**Migration Path**:
- No migration needed (automatic activation on agent update)
- Existing research.md files can coexist with new structured documents
- No schema changes required in existing systems
