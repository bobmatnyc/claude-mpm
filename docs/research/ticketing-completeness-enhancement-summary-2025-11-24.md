# PM Instructions Enhancement: Ticket Completeness Protocol

**Date**: 2025-11-24  
**Type**: Critical instruction enhancement  
**Target File**: `/src/claude_mpm/agents/PM_INSTRUCTIONS.md`  
**Lines Added**: +533 lines (2750 → 3283 total)

## Executive Summary

Enhanced PM_INSTRUCTIONS.md with comprehensive Ticket Completeness Protocol to ensure engineers receive complete context when picking up tickets. This eliminates the need for PM availability during engineer handoff by enforcing attachment of all research findings, technical context, acceptance criteria, and discovered work to tickets.

## Changes Made

### 1. Ticket Completeness Protocol Section (NEW - ~530 lines)

**Location**: After line 1779 (after "MANDATORY: Ticket Context Propagation" section)

**Key Components**:

#### A. The "Zero PM Context" Test
- **5-question completeness verification**
- Engineer handoff test: Can engineer proceed with ONLY ticket context?
- If ANY answer is NO → Ticket is INCOMPLETE → PM VIOLATION

#### B. 5-Point Engineer Handoff Checklist
1. **Acceptance Criteria Attached** ✅
   - Clear definition of "done"
   - Measurable success criteria
   - User-facing behavior changes
   - Technical acceptance criteria

2. **Research Findings Attached** ✅
   - ALL research outputs from research-agent
   - Technical analysis results
   - Architecture decisions and rationale
   - Third-party API documentation references

3. **Technical Context Attached** ✅
   - Code patterns to follow
   - Dependencies and installation requirements
   - Environment setup requirements
   - Integration points with existing systems

4. **Success Criteria and Constraints Attached** ✅
   - How to verify the work
   - Performance requirements
   - Browser/platform compatibility
   - Security requirements

5. **Discovered Work Attached** ✅
   - ALL follow-up work discovered during research/implementation
   - Related bugs found during work
   - Enhancement opportunities identified
   - Scope boundaries documented

#### C. Ticket Attachment Decision Tree
Decision tree for PM to determine what to attach vs. reference:
- **Research Findings**: Attach summaries as comments, link detailed docs
- **Code Analysis**: Attach key patterns, list file locations
- **QA/Test Results**: Attach as comments with code blocks
- **Implementation Notes**: Attach key decisions with rationale
- **External References**: Link with context/excerpts
- **DO NOT ATTACH**: CLAUDE.md patterns, project-wide conventions (reference only)

#### D. Completeness Verification Workflow
5-step workflow PM MUST execute before marking work complete:
1. Collect All Work Artifacts
2. Run 5-Point Checklist
3. Apply Decision Tree
4. Run Zero PM Context Test
5. Final Verification

#### E. Integration with Existing Protocols
- **Ticket Context Propagation** = Input (context TO agents)
- **Ticket Completeness** = Output (context BACK to ticket)
- **Scope Protection** = Validates WHAT to track
- **Circuit Breaker #6** = Enforces delegation

#### F. Examples Section
Four detailed examples:
1. ✅ **COMPLETE TICKET**: Full OAuth2 ticket with all context attached
2. ❌ **INCOMPLETE TICKET**: Same ticket with no context (shows engineer questions)
3. ✅ **CORRECT DELEGATION**: PM uses ticketing-agent for attachments
4. ❌ **WRONG DELEGATION**: PM uses mcp-ticketer tools directly

#### G. Enforcement and Violations
**Circuit Breaker #6 Extension** - Four new violation types:
1. **Missing Context Attachment**: Agent work not attached to ticket
2. **Incomplete Checklist**: Checklist fails but PM proceeds anyway
3. **Direct Ticket Tool Usage**: PM bypasses ticketing-agent delegation
4. **No Completeness Verification**: PM skips verification before marking done

#### H. PM Self-Check Before Session End
5-category self-check protocol with checklist items:
- 5-Point Checklist completion
- Attachment Decision Tree usage
- Zero PM Context Test execution
- Protocol integration verification
- Attachment success verification

### 2. Quick Delegation Matrix Strengthening

**Location**: Line 1052

**Enhancement**:
```markdown
# BEFORE:
| "ticket", "epic", "issue", ... | "I'll delegate to ticketing agent for ALL ticket operations" | ticketing-agent (ALWAYS - handles ALL ticket operations including search) |

# AFTER:
| "ticket", "epic", "issue", "find ticket", "search ticket", "list tickets", "create ticket", "update ticket", "comment on ticket", "attach to ticket", ... | "I'll delegate to ticketing-agent for ALL ticket operations" | **ticketing-agent (MANDATORY - PM MUST NEVER use mcp-ticketer tools directly)** |
```

**Impact**:
- Added explicit operations: "update ticket", "comment on ticket", "attach to ticket"
- Changed formatting to **bold MANDATORY** emphasis
- Added explicit prohibition: "PM MUST NEVER use mcp-ticketer tools directly"

### 3. CRITICAL CLARIFICATION Section (NEW - ~35 lines)

**Location**: After Quick Delegation Matrix (line 1068)

**Content**:
- Explicit list of ALL prohibited mcp-ticketer tools (14 specific tools listed)
- Rule of Thumb: "If it touches a ticket, delegate to ticketing-agent. NO EXCEPTIONS."
- Enforcement reminder: "PM using ANY mcp-ticketer tool directly = VIOLATION (Circuit Breaker #6)"
- **Correct Pattern** example (delegate → agent uses tools → summary returned)
- **Violation Pattern** example (PM uses tools directly → violation)

## Integration Points

### Existing Protocols Referenced
1. **Ticket Context Propagation** (line 1743): Context flowing TO agents
2. **Scope Protection Protocol** (line 1589): Validates WHAT work to track
3. **Circuit Breaker #6** (line 91, 1292): Enforces ticketing delegation
4. **Quick Delegation Matrix** (line 1039): Agent delegation rules

### Bidirectional Flow Established
```
INPUT: Ticket Context Propagation
  ↓
[Agent Work]
  ↓
OUTPUT: Ticket Completeness Protocol
  ↓
[Complete Ticket Ready for Engineer Handoff]
```

## Success Metrics

### Completeness Verification
- ✅ "Zero PM Context" Test passes (5 questions)
- ✅ 5-Point Checklist complete
- ✅ All artifacts attached via Decision Tree
- ✅ Engineer can proceed without PM availability

### Delegation Enforcement
- ✅ Quick Delegation Matrix explicitly requires ticketing-agent
- ✅ CRITICAL CLARIFICATION lists all prohibited tools
- ✅ Circuit Breaker #6 extended with 4 new violation types
- ✅ Examples demonstrate correct vs. incorrect patterns

## Examples Provided

### Complete Ticket Example (Lines 2057-2136)
**Ticket**: PROJ-123 "Implement OAuth2 authentication"

**Includes**:
- Acceptance Criteria (6 specific criteria)
- Technical Context comment (code patterns, files, dependencies)
- Research Findings comment (OAuth2 flow, security, references)
- Success Criteria comment (verification steps, performance targets)
- Discovered Work Summary comment (subtasks, separate tickets, deferred items)

**Engineer Assessment**: ✅ COMPLETE - Can proceed independently

### Incomplete Ticket Example (Lines 2140-2167)
**Ticket**: PROJ-123 "Implement OAuth2 authentication"  
**Content**: Only title and vague description

**Engineer Assessment**: ❌ INCOMPLETE - Must ask PM 7 questions before starting

### Delegation Examples (Lines 2169-2215)
1. **Correct**: PM delegates to ticketing-agent → agent attaches → PM verifies
2. **Wrong**: PM uses mcp-ticketer tools directly → Circuit Breaker #6 violation

## Key Outcomes

### For Engineers
- ✅ Complete context in every ticket
- ✅ No need to wait for PM availability
- ✅ Clear acceptance criteria and success criteria
- ✅ All research findings and technical context available
- ✅ Discovered work and scope boundaries documented

### For PM
- ✅ Clear protocol to follow before marking work complete
- ✅ 5-Point Checklist prevents incomplete handoffs
- ✅ Decision Tree guides attachment decisions
- ✅ Self-Check Protocol prevents violations
- ✅ Integration with existing protocols (Scope Protection, Circuit Breakers)

### For System Quality
- ✅ Enforces comprehensive ticket documentation
- ✅ Prevents engineer blockers due to missing context
- ✅ Ensures traceability of all work artifacts
- ✅ Maintains consistency with Circuit Breaker #6
- ✅ Strengthens delegation authority model

## File Statistics

```
Total Lines Added: +533
New Sections: 3 (Ticket Completeness Protocol, CRITICAL CLARIFICATION, PM Self-Check)
Examples: 4 (Complete ticket, Incomplete ticket, Correct delegation, Wrong delegation)
Checklists: 2 (5-Point Handoff, Self-Check Protocol)
Decision Trees: 1 (Attachment Decision Tree)
Violation Types: 4 (Circuit Breaker #6 extensions)
```

## Acceptance Criteria Met

- [x] Ticket Completeness Protocol section added (~530 lines)
- [x] Engineer Handoff Test includes 5 verification points
- [x] Quick Delegation Matrix explicitly requires ticketing-agent for ALL ticket ops
- [x] Decision tree guides PM on attachment vs. reference decisions
- [x] Circuit Breaker #6 includes ticket completeness violations (4 types)
- [x] Examples demonstrate complete vs. incomplete ticket handoffs (4 scenarios)
- [x] All additions reference existing sections (scope protection, ticket propagation)

## Next Steps

### Deployment
1. Test changes with `make quality`
2. Redeploy PM agent: `claude-mpm agents deploy pm --force`
3. Verify deployment: Check `~/.claude/agents/pm.md`

### Validation
1. Test PM behavior with ticket-based work
2. Verify PM runs 5-Point Checklist before marking work complete
3. Verify PM delegates ALL ticket operations to ticketing-agent
4. Verify PM attaches research findings to tickets
5. Verify engineers can work from ticket context alone

### Documentation
- [x] This summary document created
- [ ] Update CHANGELOG.md with enhancement details
- [ ] Consider adding to docs/guides/ for reference

## Related Files

- **Source**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- **Deployed**: `~/.claude/agents/pm.md` (after deployment)
- **Circuit Breakers**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/circuit_breakers.md`
- **Analysis**: `/Users/masa/Projects/claude-mpm/docs/research/ticketing-delegation-authority-analysis-2025-11-24.md`

---

**Generated**: 2025-11-24  
**Author**: Claude (Sonnet 4.5)  
**Framework Work**: ON Claude MPM Framework (not using it for project)
