# MCP Content Extraction Mapping

**Date**: 2025-12-01
**Researcher**: Claude (Research Agent)
**Purpose**: Identify MCP-specific content to extract from PM instructions to agent files
**Ticket Context**: Phase 3 of PM size reduction (extract MCP protocols to agents)

## Executive Summary

**Total Impact**:
- **PM_INSTRUCTIONS.md Current Size**: 2,556 lines, ~23,758 tokens
- **mcp-ticketer Content Identified**: 886 lines, ~7,500 tokens (31.6% of PM instructions)
- **mcp-vector-search Content Identified**: 28 lines, ~240 tokens (1.0% of PM instructions)
- **Total Extractable**: 914 lines, ~7,740 tokens (32.6% reduction potential)
- **PM Size After Extraction**: ~1,642 lines, ~16,018 tokens (32.6% reduction)

**Key Findings**:
1. **Massive ticketing content**: 886 lines of mcp-ticketer protocols, workflows, and examples
2. **Main extraction target**: Lines 891-1776 contain comprehensive ticketing integration
3. **Core delegation rules**: Only ~20 lines need to stay in PM for Circuit Breaker #6
4. **Vector search**: Small section (28 lines) with minimal PM-specific content

---

## 1. mcp-ticketer Content (Extract to ticketing.md)

### Section 1: Circuit Breaker #6 References
**Location**: PM_INSTRUCTIONS.md, Lines 73, 111-147, 856-890
**Size**: ~70 lines, ~590 tokens
**Content Type**: Violation detection, delegation rules
**Extract to agent**: ticketing.md (implementation protocols)
**Replacement in PM**: ~10 lines (core circuit breaker rule)

**Current Content**:
```markdown
Lines 73: Circuit Breaker #6: Ticketing Tool Misuse Detection
Lines 111-147: TICKETING VIOLATIONS section with examples
Lines 856-890: CRITICAL CLARIFICATION: Ticketing Operations (detailed tool list)
```

**Replacement for PM** (10 lines):
```markdown
### Circuit Breaker #6: Ticketing Tool Misuse

**RULE**: PM MUST NEVER use ANY mcp__mcp-ticketer__* tools directly.

**Detection**: PM uses ANY mcp__mcp-ticketer__* tool → VIOLATION
**Action**: ALL ticket operations MUST be delegated to ticketing agent

**Examples**:
- ❌ ticket_read, ticket_create, ticket_update, ticket_search, ticket_list
- ❌ epic_create, issue_create, task_create
- ❌ ANY mcp__mcp-ticketer__* tool whatsoever

See ticketing agent for complete ticket operation protocols.
```

**Dependencies**: References Circuit Breaker #6 throughout PM instructions

---

### Section 2: TICKETING SYSTEM INTEGRATION (MAIN EXTRACTION)
**Location**: PM_INSTRUCTIONS.md, Lines 891-1776
**Size**: 886 lines, ~7,500 tokens
**Content Type**: Complete ticketing workflow, protocols, examples
**Extract to agent**: ticketing.md (ALL content)
**Replacement in PM**: ~10 lines (delegation rule only)

**Subsections Within Main Extraction**:

#### 2.1 Detection Patterns (Lines 895-915)
- URL patterns (Linear, GitHub, Jira)
- Ticket ID patterns (PROJECT-###)
- User phrases detection
**Action**: Extract to ticketing.md (ticketing agent needs these patterns)

#### 2.2 Context Optimization for Ticket Reading (Lines 916-1004)
- The Context Problem (token bloat explanation)
- Delegation patterns (wrong vs correct)
- When to delegate ticket operations
**Action**: Extract to ticketing.md (implementation-level detail)

#### 2.3 Delegation Templates (Lines 1005-1073)
- Template 1: Single Ticket Fetch
- Template 2: Multiple Ticket Search
- Template 3: Epic Hierarchy
**Action**: Extract to ticketing.md (ticketing agent uses these)

#### 2.4 Circuit Breaker Integration (Lines 1074-1092)
- Violation patterns
- Enforcement rules
**Action**: Keep reference in PM, extract details to ticketing.md

#### 2.5 Expected Impact & Success Metrics (Lines 1093-1149)
- Token savings calculations
- Success indicators
- Decision tree
**Action**: Extract to ticketing.md (operational metrics)

#### 2.6 PM Protocol When Tickets Detected (Lines 1151-1199)
- Step-by-step workflow
- Tool availability checks
- Delegation enhancement patterns
**Action**: Keep ~5 lines in PM, extract details to ticketing.md

#### 2.7 Complete Examples (Lines 1200-1268)
- Linear URL example
- Ticket ID example
- Benefits section
**Action**: Extract to ticketing.md (examples for ticketing agent)

#### 2.8 SCOPE PROTECTION PROTOCOL (Lines 1296-1449)
- Scope definition and boundaries
- 4-step PM validation workflow
- Scope classification matrix
- Integration with Circuit Breakers
**Action**: Extract to ticketing.md (ticketing-specific workflow)

#### 2.9 Ticket Context Propagation (Lines 1450-1521)
- Template for ALL delegations
- Agent response verification
- User reporting format
**Action**: Keep ~5 lines in PM, extract details to ticketing.md

#### 2.10 TICKET COMPLETENESS PROTOCOL (Lines 1523-1776)
- Zero PM Context Test
- 5-Point Engineer Handoff Checklist
- Ticket Attachment Decision Tree
- Completeness Verification Workflow
**Action**: Extract to ticketing.md (ticketing agent enforces this)

**Total for Section 2**: 886 lines, ~7,500 tokens

**Replacement for PM** (10 lines):
```markdown
## TICKETING INTEGRATION

**RULE**: ALL ticket operations MUST be delegated to ticketing agent.

**Detection Patterns**:
- Ticket URLs (Linear, GitHub, Jira)
- Ticket IDs (PROJECT-###, TEAM-###)
- User phrases ("for ticket X", "issue Y")

**PM Workflow**:
1. Detect ticket reference → Delegate to ticketing for context fetch
2. Ticketing returns summary (150 tokens vs 800 tokens direct read)
3. PM uses summary to enhance delegation to other agents
4. PM ensures ALL work links back to ticket

**Circuit Breaker #6**: PM NEVER uses mcp__mcp-ticketer__* tools directly.

See ticketing agent for:
- Ticket operation protocols
- Scope Protection Protocol
- Ticket Completeness Protocol
- Context propagation templates
```

---

## 2. mcp-vector-search Content (Extract to research.md)

### Section 1: VECTOR SEARCH WORKFLOW FOR PM
**Location**: PM_INSTRUCTIONS.md, Lines 497-524
**Size**: 28 lines, ~240 tokens
**Content Type**: PM-specific usage rules
**Extract to agent**: research.md (partial - expand for research agent)
**Replacement in PM**: ~5 lines (delegation reference)

**Current Content**:
```markdown
Lines 497-524:
- Purpose statement
- Allowed vector search tools for PM
- PM Vector Search Rules (do/don't)
- Delegation-first response patterns
```

**Analysis**: This section is **PM-specific** (describes how PM should use vector search before delegation). Research agent needs different instructions (how to use vector search for deep analysis).

**Action**:
- Keep simplified version in PM (~5 lines)
- Create expanded version for research.md with deep analysis workflows

**Replacement for PM** (5 lines):
```markdown
## VECTOR SEARCH (Quick Context Only)

**PM MAY use mcp-vector-search tools for quick context BEFORE delegation**:
- get_project_status, search_code, search_context
- Purpose: Better task scoping before delegating to research/engineer
- NEVER use for deep analysis (delegate to research)

See research agent for comprehensive vector search workflows.
```

**Addition to research.md** (expand to ~100 lines):
```markdown
## VECTOR SEARCH INTEGRATION (mcp-vector-search)

### Research Agent Vector Search Protocol

**PRIMARY**: Use vector search for semantic code discovery and pattern analysis.

#### Vector Search Workflow:
1. **Check Indexing Status**: mcp__mcp-vector-search__get_project_status
2. **If Not Indexed**: mcp__mcp-vector-search__index_project
3. **Semantic Search**: mcp__mcp-vector-search__search_code
4. **Similarity Analysis**: mcp__mcp-vector-search__search_similar
5. **Context Search**: mcp__mcp-vector-search__search_context

#### When to Use Vector Search:
- ✅ Finding code patterns across codebase
- ✅ Identifying similar implementations
- ✅ Understanding functionality without reading all files
- ✅ Discovering related code for refactoring
- ✅ Mapping architecture through semantic relationships

#### Graceful Degradation:
If vector search unavailable, fall back to:
- Grep for pattern-based search
- Glob for file discovery
- Strategic file sampling (3-5 files max)

[Continue with detailed workflows, examples, best practices...]
```

---

## 3. Content to KEEP in PM (Core Delegation Rules)

### mcp-ticketer (Keep ~20 lines)

**Lines to Keep**:
```markdown
1. Circuit Breaker #6 rule (~10 lines) - Lines 73 reference
2. Detection patterns summary (~5 lines) - "ticket URLs, IDs, phrases"
3. Delegation instruction (~5 lines) - "delegate to ticketing for ALL operations"
```

**Total**: ~20 lines, ~170 tokens

**Purpose**:
- WHO to delegate to (ticketing agent)
- WHEN to delegate (ticket detected)
- WHY delegation required (Circuit Breaker #6)
- Reference to ticketing agent for HOW

---

### mcp-vector-search (Keep ~5 lines)

**Lines to Keep**:
```markdown
1. Allowed PM usage (~3 lines) - "PM may use for quick context"
2. Delegation reference (~2 lines) - "See research agent for deep analysis"
```

**Total**: ~5 lines, ~40 tokens

**Purpose**:
- PM knows vector search is allowed (exception to "delegate everything")
- PM knows limits (quick context only, not deep analysis)
- Reference to research agent for comprehensive workflows

---

## 4. Extraction Plan

### Step 1: Extract mcp-ticketer (highest savings)

**Actions**:
1. **Remove from PM_INSTRUCTIONS.md**: Lines 891-1776 (886 lines)
2. **Create ticketing.md**: Add extracted content (~886 lines)
3. **Replace in PM_INSTRUCTIONS.md**: Lines 891-1776 → ~20 lines delegation rule
4. **Update references**: Change "See Section X" → "See ticketing agent"

**Savings**:
- Before: 886 lines (7,500 tokens)
- After: 20 lines (170 tokens)
- **Net Reduction**: 866 lines (7,330 tokens) - 30.8% of PM instructions

---

### Step 2: Extract mcp-vector-search

**Actions**:
1. **Remove from PM_INSTRUCTIONS.md**: Lines 497-524 (28 lines)
2. **Add to research.md**: Expand to ~100 lines with detailed workflows
3. **Replace in PM_INSTRUCTIONS.md**: Lines 497-524 → ~5 lines reference
4. **Update references**: Add vector search protocols to research agent

**Savings**:
- Before: 28 lines (240 tokens)
- After: 5 lines (40 tokens)
- **Net Reduction**: 23 lines (200 tokens) - 0.9% of PM instructions

---

### Total Impact

**Before Extraction**:
- PM_INSTRUCTIONS.md: 2,556 lines, ~23,758 tokens

**After Extraction**:
- PM_INSTRUCTIONS.md: 1,667 lines, ~16,228 tokens
- ticketing.md: +886 lines, ~7,500 tokens (new agent file)
- research.md: +100 lines, ~850 tokens (addition to existing)

**Reduction**:
- Lines removed: 889 lines (34.8% reduction)
- Tokens saved: 7,530 tokens (31.7% reduction)
- **Final PM size**: ~16,228 tokens (31.7% smaller)

**Verification**:
- Target: <20,000 tokens for PM
- Result: 16,228 tokens ✅
- Headroom: 3,772 tokens (18.9%)

---

## 5. Detailed Line-by-Line Extraction List

### EXTRACT: Lines 891-1776 (Complete Ticketing Section)

**Start Marker**: `## TICKETING SYSTEM INTEGRATION WITH SCOPE PROTECTION (mcp-ticketer)`
**End Marker**: `## PR WORKFLOW DELEGATION` (line before this)

**Subsections to Extract**:

| Lines | Section | Tokens | Destination |
|-------|---------|--------|-------------|
| 891-894 | Section Header & Critical Note | ~30 | ticketing.md |
| 895-915 | Detection Patterns | ~180 | ticketing.md |
| 916-949 | Context Problem Explanation | ~280 | ticketing.md |
| 950-1004 | Delegation Patterns (Wrong vs Correct) | ~470 | ticketing.md |
| 1005-1073 | Delegation Templates (3 templates) | ~580 | ticketing.md |
| 1074-1092 | Circuit Breaker Integration | ~160 | ticketing.md (keep ref in PM) |
| 1093-1149 | Expected Impact & Metrics | ~480 | ticketing.md |
| 1150-1199 | PM Protocol When Tickets Detected | ~420 | ticketing.md (keep ~5 lines in PM) |
| 1200-1268 | Complete Examples (2 examples) | ~580 | ticketing.md |
| 1269-1279 | Benefits & Graceful Degradation | ~90 | ticketing.md |
| 1280-1295 | Circuit Breaker Reminder | ~130 | ticketing.md (keep ref in PM) |
| 1296-1449 | SCOPE PROTECTION PROTOCOL | ~1,300 | ticketing.md |
| 1450-1521 | Ticket Context Propagation | ~610 | ticketing.md (keep ~5 lines in PM) |
| 1523-1776 | TICKET COMPLETENESS PROTOCOL | ~2,140 | ticketing.md |

**Total**: 886 lines, ~7,500 tokens

---

### EXTRACT: Lines 497-524 (Vector Search Section)

**Start Marker**: `## VECTOR SEARCH WORKFLOW FOR PM`
**End Marker**: Line before next section header

**Content to Extract**:

| Lines | Section | Tokens | Destination |
|-------|---------|--------|-------------|
| 497-505 | Purpose & Allowed Tools | ~75 | Keep simplified in PM |
| 506-513 | PM Vector Search Rules | ~70 | Keep simplified in PM |
| 514-524 | Delegation-First Patterns | ~95 | Expand in research.md |

**Total**: 28 lines, ~240 tokens

**Action**:
- Simplify to ~5 lines in PM
- Expand to ~100 lines in research.md with deep workflows

---

### REPLACE: Circuit Breaker #6 References

**Current**: Lines 73, 111-147, 856-890 (scattered references)
**Action**: Consolidate to ~10 lines, reference ticketing.md

**Before** (scattered):
```markdown
Line 73: Brief mention in circuit breaker list
Lines 111-147: Detailed violation examples (37 lines)
Lines 856-890: Tool list and clarification (35 lines)
```

**After** (consolidated):
```markdown
### Circuit Breaker #6: Ticketing Tool Misuse Detection

PM MUST NEVER use ANY mcp__mcp-ticketer__* tools directly.

Detection: PM uses ANY mcp__mcp-ticketer__* tool
Violation: Zero tolerance - ALL ticket operations delegate to ticketing
Enforcement: See ticketing agent for complete protocols

Examples: ticket_read, ticket_create, ticket_search, ANY mcp__mcp-ticketer__*
```

**Savings**: 72 lines → 10 lines (62 lines saved, ~525 tokens)

---

## 6. Implementation Steps for Engineer

### Phase 1: Create ticketing.md

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/instructions/ticketing.md`

**Content Structure**:
```markdown
# Ticketing Agent Instructions - MCP Ticketer Protocol

## Detection Patterns
[Lines 895-915 from PM_INSTRUCTIONS.md]

## Context Optimization for Ticket Reading
[Lines 916-1004 from PM_INSTRUCTIONS.md]

## Delegation Templates
[Lines 1005-1073 from PM_INSTRUCTIONS.md]

## PM Protocol When Tickets Detected
[Lines 1150-1199 from PM_INSTRUCTIONS.md]

## Complete Examples
[Lines 1200-1268 from PM_INSTRUCTIONS.md]

## SCOPE PROTECTION PROTOCOL
[Lines 1296-1449 from PM_INSTRUCTIONS.md]

## Ticket Context Propagation
[Lines 1450-1521 from PM_INSTRUCTIONS.md]

## TICKET COMPLETENESS PROTOCOL
[Lines 1523-1776 from PM_INSTRUCTIONS.md]

## Circuit Breaker Integration
[Lines 1074-1092, 1280-1295 from PM_INSTRUCTIONS.md]

## Expected Impact & Success Metrics
[Lines 1093-1149 from PM_INSTRUCTIONS.md]

## Benefits & Graceful Degradation
[Lines 1269-1279 from PM_INSTRUCTIONS.md]
```

---

### Phase 2: Update PM_INSTRUCTIONS.md

**Replace Lines 891-1776** with:
```markdown
## TICKETING INTEGRATION

**RULE**: ALL ticket operations MUST be delegated to ticketing agent.
PM NEVER uses mcp__mcp-ticketer__* tools directly (Circuit Breaker #6).

**Detection Patterns**:
- Ticket URLs: Linear, GitHub, Jira
- Ticket IDs: PROJECT-###, TEAM-###
- User phrases: "for ticket X", "issue Y"

**PM Workflow**:
1. Detect ticket → Delegate to ticketing for context
2. Ticketing returns summary (saves 70-80% tokens)
3. PM uses summary for delegation to other agents
4. PM ensures work links back to ticket

**See ticketing agent for**:
- Complete ticket operation protocols
- Scope Protection Protocol
- Ticket Completeness Protocol
- Context propagation templates
- Circuit Breaker #6 enforcement details
```

**Replace Lines 497-524** with:
```markdown
## VECTOR SEARCH (Quick Context Only)

**PM MAY use mcp-vector-search for quick context BEFORE delegation**:
- Tools: get_project_status, search_code, search_context
- Purpose: Better task scoping
- Limit: Quick context only, NOT deep analysis

**Delegate to research agent for**:
- Comprehensive vector search workflows
- Semantic code analysis
- Architecture mapping via vector search
```

**Replace Lines 73, 111-147, 856-890** with consolidated Circuit Breaker #6 (shown above).

---

### Phase 3: Expand research.md

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/instructions/research.md` (or appropriate agent file)

**Add Section**:
```markdown
## VECTOR SEARCH INTEGRATION (mcp-vector-search)

### Tool Availability and Detection
[Workflow for checking if vector search available]

### Vector Search Protocol
[Step-by-step workflow with all 5 tools]

### When to Use Vector Search
[Decision tree for vector vs grep/glob]

### Semantic Search Patterns
[Examples of search_code usage]

### Similarity Analysis Workflows
[Examples of search_similar usage]

### Context Search Techniques
[Examples of search_context usage]

### Graceful Degradation
[Fallback strategies when vector search unavailable]

### Memory Management with Vector Search
[Token optimization strategies]

### Best Practices
[Tips for effective vector search usage]
```

**Estimated Addition**: ~100-150 lines

---

### Phase 4: Update References

**Files to Update**:
1. PM_INSTRUCTIONS.md: Change "See Section X" → "See ticketing agent"
2. Agent template files: Update any cross-references
3. Documentation: Update architecture docs with new agent responsibilities

**Search Patterns**:
```bash
# Find references to ticketing sections
grep -r "TICKETING SYSTEM INTEGRATION" .
grep -r "SCOPE PROTECTION PROTOCOL" .
grep -r "TICKET COMPLETENESS" .

# Find references to vector search
grep -r "VECTOR SEARCH WORKFLOW" .
```

---

### Phase 5: Validation

**Verification Steps**:
1. **Token Count**: Verify PM_INSTRUCTIONS.md is ~16,228 tokens
2. **Content Completeness**: Ensure no orphaned references
3. **Agent Files**: Verify ticketing.md and research.md are complete
4. **Cross-References**: Test that "See X agent" links are correct
5. **Functional Test**: Deploy agents and test ticket-based workflow

**Success Criteria**:
- ✅ PM_INSTRUCTIONS.md <20,000 tokens
- ✅ No broken references
- ✅ All MCP protocols in appropriate agent files
- ✅ Ticket-based workflows still function correctly
- ✅ Vector search workflows still function correctly

---

## 7. Risk Analysis

### Low Risk
- ✅ Content is self-contained (complete sections)
- ✅ Clear section boundaries (## headers)
- ✅ No complex cross-dependencies
- ✅ Agent files are appropriate destination

### Medium Risk
- ⚠️ Circuit Breaker #6 scattered across PM (needs consolidation)
- ⚠️ References to "See Section X" need updating
- ⚠️ Vector search is PM-specific (needs rewriting for research agent)

### Mitigation Strategies
1. **Consolidate Circuit Breaker #6** first (single location in PM)
2. **Update references** systematically (grep for all "See Section")
3. **Expand vector search** for research agent (don't just copy PM version)
4. **Test thoroughly** after extraction (ticket-based workflow verification)

---

## 8. Next Steps

### Immediate Actions
1. **Create ticketing.md**: Extract lines 891-1776
2. **Update PM_INSTRUCTIONS.md**: Replace with ~20 line delegation rule
3. **Consolidate Circuit Breaker #6**: Single location, reference ticketing.md
4. **Simplify vector search**: Replace lines 497-524 with ~5 line reference

### Follow-Up Actions
1. **Expand research.md**: Add comprehensive vector search workflows (~100 lines)
2. **Update references**: Change "See Section X" → "See Y agent"
3. **Test workflows**: Verify ticket-based workflows still function
4. **Measure impact**: Verify token reduction (target: 31.7% reduction)

### Success Metrics
- ✅ PM_INSTRUCTIONS.md: 2,556 → 1,667 lines (34.8% reduction)
- ✅ PM_INSTRUCTIONS.md: 23,758 → 16,228 tokens (31.7% reduction)
- ✅ Ticket operations: 100% delegated (no direct PM tool usage)
- ✅ Vector search: PM uses for context, research for deep analysis
- ✅ All protocols: Preserved in appropriate agent files

---

## Appendix A: Token Estimation Methodology

**Token Calculation**:
- Average: ~8.5 tokens per line (based on PM_INSTRUCTIONS.md analysis)
- Formula: Lines × 8.5 = Estimated Tokens
- Verification: 2,556 lines × 8.5 ≈ 21,726 tokens (within 10% of actual 23,758)

**Line Count Verification**:
```bash
wc -l PM_INSTRUCTIONS.md
# Output: 2556
```

**Section Measurements**:
- Ticketing section: Lines 891-1776 = 886 lines × 8.5 ≈ 7,531 tokens
- Vector search: Lines 497-524 = 28 lines × 8.5 ≈ 238 tokens
- Circuit Breaker refs: ~72 lines × 8.5 ≈ 612 tokens

**Total Extractable**: 886 + 28 + 72 = 986 lines × 8.5 ≈ 8,381 tokens

**Note**: Actual extraction is 889 lines (slightly less due to section header preservation).

---

## Appendix B: File Locations

**Source File**:
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md
```

**Destination Files**:
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/instructions/ticketing.md (new)
/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/instructions/research.md (update)
```

**Backup Recommendation**:
```bash
# Create backup before extraction
cp PM_INSTRUCTIONS.md PM_INSTRUCTIONS.md.backup-2025-12-01
```

---

## Appendix C: Grep Patterns Used

**Search Patterns**:
```bash
# Find all mcp-ticketer references
grep -n "mcp-ticketer\|mcp__mcp-ticketer__\|ticketing\|ticket_" PM_INSTRUCTIONS.md

# Find all mcp-vector-search references
grep -n "mcp-vector-search\|mcp__mcp-vector-search__\|vector search" PM_INSTRUCTIONS.md

# Find section headers
grep -n "^##" PM_INSTRUCTIONS.md

# Count lines in sections
sed -n '891,1776p' PM_INSTRUCTIONS.md | wc -l
# Output: 886
```

---

**Research Complete**: 2025-12-01
**File**: `/Users/masa/Projects/claude-mpm/docs/research/mcp-content-extraction-mapping-2025-12-01.md`
**Next Step**: Engineer uses this mapping to perform extraction (Phase 3 implementation)
