# PM_INSTRUCTIONS.md Modularization Plan

**Document Version**: 1.0.0
**Date**: 2025-10-20
**Status**: READY FOR IMPLEMENTATION
**Author**: Claude MPM Research Agent

---

## Executive Summary

### Current State Metrics

**After Phase 1 (Quick Wins) - Completed:**
- **Current file size**: 806 lines (reduced from 1,145 lines)
- **Lines extracted**: 339 lines (29.6% reduction)
- **Number of sections**: 32 major sections (## level)
- **Files created**: 3 template files
- **Complexity**: Still high - several large, complex sections remain

**Quick Wins Completed (Phase 1):**
1. ✅ `validation_templates.md` (312 lines) - Verification and QA requirements
2. ✅ `circuit_breakers.md` (638 lines) - Violation detection system
3. ✅ `pm_examples.md` (474 lines) - Concrete behavior examples

**Template Ecosystem Established:**
- Consistent markdown formatting
- Table of contents in each file
- Version tracking
- Parent document references
- Clear purpose statements

### Remaining Optimization Opportunities

**Analysis of PM_INSTRUCTIONS.md (current 806 lines):**

| Section | Lines | Modularization Priority | Rationale |
|---------|-------|------------------------|-----------|
| Git File Tracking Protocol | 192 | **HIGH** | Largest remaining section, self-contained topic |
| PM Red Flags - Phrases | 61 | **HIGH** | Reference material, frequently consulted |
| Simplified Delegation Rules | 57 | **MEDIUM** | Core logic but integrated with workflow |
| Forbidden Actions | 45 | **MEDIUM** | Could merge with circuit breakers |
| Response Format | 39 | **HIGH** | Template/reference material |
| Quick Reference | 39 | **LOW** | Should stay in main file for quick access |
| PM Delegation Scorecard | 29 | **MEDIUM** | Metrics/evaluation framework |
| Enforcement Implementation | 30 | **LOW** | Code-level implementation details |
| Workflow Pipeline | 28 | **MEDIUM** | Could expand into workflow guide |
| TodoWrite Format | 24 | **MEDIUM** | Template material |
| Vector Search Workflow | 22 | **MEDIUM** | Tool-specific workflow |
| PM Mindset Transformation | 22 | **LOW** | Core philosophy, keep in main |

### Recommended Modularization Phases

**Phase 1: Quick Wins** ✅ **COMPLETED**
- Validation templates (312 lines)
- Circuit breakers (638 lines)
- PM examples (474 lines)
- **Result**: 339 lines removed from PM_INSTRUCTIONS.md

**Phase 2: High-Priority Extractions (Next Session)**
- Git file tracking protocol module (~200 lines)
- PM red flags and phrases reference (~70 lines)
- Response format and templates (~50 lines)
- **Expected Result**: ~320 additional lines removed

**Phase 3: Medium-Priority Consolidation (Future)**
- Delegation rules and workflows (~100 lines)
- PM metrics and scorecards (~50 lines)
- Tool-specific workflows (~50 lines)
- **Expected Result**: ~200 additional lines removed

### Expected Benefits

**After Complete Modularization:**
- **PM_INSTRUCTIONS.md size**: ~286 lines (75% reduction from original 1,145 lines)
- **Maintainability**: Each concern in dedicated, focused file
- **Discoverability**: Table of contents guides to relevant templates
- **Consistency**: Standardized template structure
- **Testing**: Easier to validate individual components

**Timeline Estimate:**
- Phase 1: ✅ Completed (3 hours)
- Phase 2: 3-4 hours (2-3 modules)
- Phase 3: 2-3 hours (3-4 modules)
- **Total remaining effort**: 5-7 hours

---

## Candidate Modules for Extraction

### Phase 2: High-Priority Modules (RECOMMENDED NEXT)

#### Module 1: Git File Tracking Protocol

**Module Name**: `git_file_tracking.md`

**Content to Extract**:
- Section: "🔴 GIT FILE TRACKING PROTOCOL (PM RESPONSIBILITY)" (lines 595-806)
- Core Principle
- When Files Are Created (immediate PM actions)
- Tracking Decision Matrix
- PM Verification Checklist
- Integration with Git Commit Protocol
- Commit message templates and examples
- Circuit Breaker integration
- Why This is PM Responsibility
- PM Mindset Addition
- Session Completion Checklist Addition
- Red Flags for File Tracking
- Edge Cases and Special Considerations

**Priority**: **HIGH**

**Effort Estimate**: 1.5 hours

**Impact on PM_INSTRUCTIONS.md**: ~192 lines reduced

**Dependencies**:
- References circuit_breakers.md (Circuit Breaker #5)
- References validation_templates.md (verification principles)
- Standalone topic that doesn't interfere with core delegation logic

**Rationale**:
- Largest remaining section by far (192 lines = 23.8% of current file)
- Self-contained topic with clear boundaries
- Frequently referenced during file creation scenarios
- Has its own circuit breaker already extracted
- Contains templates and examples that belong in reference material

**Implementation Notes**:
- Keep brief summary in PM_INSTRUCTIONS.md with reference link
- Move all detailed protocols, checklists, and examples to template
- Maintain commit message examples in template file
- Cross-reference with circuit_breakers.md for enforcement

---

#### Module 2: PM Red Flags and Phrase Reference

**Module Name**: `pm_red_flags.md`

**Content to Extract**:
- Section: "PM RED FLAGS - PHRASES THAT INDICATE VIOLATIONS" (lines 350-411)
- Investigation Red Flags ("Let me check...", "Let me see...")
- Implementation Red Flags ("Let me fix...", "Let me create...")
- Assertion Red Flags ("It works", "Should work", "Probably")
- Localhost Assertion Red Flags ("Running on localhost")
- File Tracking Red Flags ("I'll let the agent track that...")
- Correct PM Phrases (what PM should say instead)

**Priority**: **HIGH**

**Effort Estimate**: 1 hour

**Impact on PM_INSTRUCTIONS.md**: ~61 lines reduced

**Dependencies**:
- References circuit_breakers.md (violation types)
- Used during violation detection
- Standalone reference material

**Rationale**:
- Pure reference material - list of phrases to avoid/use
- Frequently consulted during PM behavior validation
- Self-contained, no logic integration needed
- Easy to extract and maintain separately
- Could be enhanced with more examples over time

**Implementation Notes**:
- Organize by violation type (Investigation, Implementation, Assertion, File Tracking)
- Include severity indicators for each phrase type
- Add cross-references to circuit breakers for context
- Provide examples of correct phrase substitutions

---

#### Module 3: Response Format and Templates

**Module Name**: `response_templates.md`

**Content to Extract**:
- Section: "Response Format" (lines 412-451)
- JSON structure for session_summary
- delegation_summary format
- implementation tracking
- verification_results structure
- file_tracking section
- assertions_made format
- blockers and next_steps format

**Priority**: **HIGH**

**Effort Estimate**: 1 hour

**Impact on PM_INSTRUCTIONS.md**: ~39 lines reduced

**Dependencies**:
- Used by all PM responses
- References validation_templates.md (verification structure)
- References git_file_tracking.md (file_tracking section)

**Rationale**:
- Pure template/reference material
- Not frequently changed, but frequently consulted
- Should be easily accessible as separate reference
- Can be expanded with additional response types
- Currently duplicated knowledge with other docs

**Implementation Notes**:
- Include full JSON schema with descriptions
- Provide examples of complete, well-formed responses
- Document required vs. optional fields
- Add validation rules for each section
- Cross-reference with related templates (validation, file tracking)

---

### Phase 3: Medium-Priority Modules (FUTURE)

#### Module 4: PM Delegation Matrix and Workflows

**Module Name**: `delegation_workflows.md`

**Content to Extract**:
- Section: "SIMPLIFIED DELEGATION RULES" (lines 147-198)
- Section: "Quick Reference" (partial - workflows only, lines 494-528)
- Delegation-First Response Patterns
- Local-ops-agent Priority Rule
- Quick Delegation Matrix (table)
- Common Patterns (Full Stack, API, Web UI, etc.)
- Decision Flow diagram

**Priority**: **MEDIUM**

**Effort Estimate**: 1.5 hours

**Impact on PM_INSTRUCTIONS.md**: ~100 lines reduced

**Dependencies**:
- Core delegation logic
- References multiple agents
- Used constantly during PM operation

**Rationale**:
- Medium priority because it's frequently used reference material
- Could be enhanced with more workflow patterns
- Separating allows for easier updates when new agents added
- Decision flow could be expanded into visual diagrams
- Not extracted in Phase 2 because it's deeply integrated with core PM logic

**Implementation Notes**:
- Keep minimal delegation rules in PM_INSTRUCTIONS.md
- Extract detailed delegation matrix and workflows to template
- Consider creating visual workflow diagrams
- Document each agent's delegation triggers
- Include success criteria patterns

---

#### Module 5: PM Metrics and Evaluation Framework

**Module Name**: `pm_metrics.md`

**Content to Extract**:
- Section: "PM DELEGATION SCORECARD (AUTOMATIC EVALUATION)" (lines 534-563)
- Section: "ENFORCEMENT IMPLEMENTATION" (lines 565-591)
- Metrics tracked per session
- Session grading rubric (A+ through F)
- Automatic enforcement rules
- Pre-action hooks (code implementation)
- Post-action validation (code implementation)

**Priority**: **MEDIUM**

**Effort Estimate**: 1.5 hours

**Impact on PM_INSTRUCTIONS.md**: ~59 lines reduced

**Dependencies**:
- References circuit_breakers.md (violation types)
- Used for PM performance evaluation
- May involve code implementation

**Rationale**:
- Evaluation framework separate from core instructions
- Contains implementation-level details (code snippets)
- Could be expanded with more sophisticated metrics
- Not frequently consulted during normal PM operation
- Primarily for monitoring and quality assurance

**Implementation Notes**:
- Separate metrics definition from enforcement code
- Include implementation examples for hooks/validation
- Document how to add new metrics
- Provide dashboard/reporting format
- Cross-reference with circuit breakers for violation tracking

---

#### Module 6: Tool-Specific PM Workflows

**Module Name**: `pm_tool_workflows.md`

**Content to Extract**:
- Section: "CLAUDE MPM SLASH COMMANDS" (lines 85-115)
- Section: "VECTOR SEARCH WORKFLOW FOR PM" (lines 124-146)
- Section: "TodoWrite Format with Violation Tracking" (lines 302-326)
- Common MPM Commands
- How to Execute MPM Commands
- Vector Search usage rules
- Vector Search workflow example
- TodoWrite state management
- Violation tracking format in todos

**Priority**: **MEDIUM**

**Effort Estimate**: 1 hour

**Impact on PM_INSTRUCTIONS.md**: ~76 lines reduced

**Dependencies**:
- Tool-specific knowledge
- References broader PM workflows
- Used when PM interacts with specific tools

**Rationale**:
- Tool-specific workflows separate from delegation principles
- Can be updated independently when tools change
- Medium priority because tools are frequently used
- Could be expanded as new tools are added
- Not Phase 2 because it's not high-impact reduction

**Implementation Notes**:
- Group by tool type (slash commands, vector search, todo management)
- Include tool-specific best practices
- Document common patterns for each tool
- Add troubleshooting for tool-related issues
- Keep brief tool summary in main PM_INSTRUCTIONS.md

---

#### Module 7: PM Forbidden Actions Reference

**Module Name**: `forbidden_actions.md` OR merge into `circuit_breakers.md`

**Content to Extract**:
- Section: "FORBIDDEN ACTIONS (IMMEDIATE FAILURE)" (lines 24-69)
- Implementation Violations
- Investigation Violations
- Assertion Violations

**Priority**: **LOW-MEDIUM**

**Effort Estimate**: 0.5 hours (if merged into circuit_breakers.md)

**Impact on PM_INSTRUCTIONS.md**: ~45 lines reduced

**Dependencies**:
- Heavily overlaps with circuit_breakers.md
- Core reference material

**Rationale**:
- Consider merging into existing circuit_breakers.md rather than new file
- Content is very similar to circuit breaker definitions
- Extraction would eliminate duplication
- Low priority because it may be better to consolidate existing files
- Could be Phase 2 if we decide to merge into circuit_breakers.md

**Implementation Notes**:
- **RECOMMENDED**: Merge into circuit_breakers.md as "Forbidden Actions Quick Reference"
- Add cross-references between circuit breakers and forbidden actions
- Eliminate duplication between the two documents
- Keep only highest-level summary in PM_INSTRUCTIONS.md

---

### Phase 3: Low-Priority / Keep in Main File

#### Sections to KEEP in PM_INSTRUCTIONS.md

These sections should remain in the main file:

1. **"ABSOLUTE PM LAW - VIOLATIONS = TERMINATION"** (4 lines)
   - Critical header, sets tone immediately

2. **"CRITICAL MANDATE: DELEGATION-FIRST THINKING"** (3 lines)
   - Core principle, must be visible immediately

3. **"ONLY ALLOWED PM TOOLS"** (14 lines)
   - Frequently consulted, core operational knowledge

4. **"PM MINDSET TRANSFORMATION"** (22 lines)
   - Philosophy section, core to PM identity

5. **"VIOLATION CHECKPOINTS"** (25 lines)
   - Core operational checklist, consulted constantly

6. **"Workflow Pipeline"** (28 lines)
   - Core flow, central to PM operation

7. **"Quick Reference / Success Criteria"** (partial - keep essential parts)
   - Quick access for common scenarios

8. **"THE PM MANTRA"** (9 lines)
   - Core identity statement

9. **"SUMMARY: PM AS PURE COORDINATOR"** (18 lines)
   - Closing summary, reinforces core message

**Total to Keep**: ~123 lines (core PM identity and critical rules)

**Additional Content After Extractions**: ~163 lines (delegation rules, deployment matrix references, etc.)

**Final PM_INSTRUCTIONS.md Size After Full Modularization**: ~286 lines (75% reduction)

---

## Proposed Directory Structure

```
src/claude_mpm/agents/
├── PM_INSTRUCTIONS.md                    (~286 lines after full modularization)
│   ├── Core PM identity and mandates
│   ├── Quick reference tables
│   ├── Links to all template modules
│   └── Essential workflows
│
├── BASE_PM.md                            (existing - framework requirements)
├── WORKFLOW.md                           (existing - operational workflows)
│
└── templates/
    ├── validation_templates.md           (✅ 312 lines - Phase 1 DONE)
    ├── circuit_breakers.md               (✅ 638 lines - Phase 1 DONE)
    ├── pm_examples.md                    (✅ 474 lines - Phase 1 DONE)
    │
    ├── git_file_tracking.md              (📋 ~192 lines - Phase 2)
    ├── pm_red_flags.md                   (📋 ~61 lines - Phase 2)
    ├── response_templates.md             (📋 ~39 lines - Phase 2)
    │
    ├── delegation_workflows.md           (🔮 ~100 lines - Phase 3)
    ├── pm_metrics.md                     (🔮 ~59 lines - Phase 3)
    ├── pm_tool_workflows.md              (🔮 ~76 lines - Phase 3)
    │
    └── README.md                         (Template index and navigation)
```

**Template README.md Structure**:
```markdown
# PM Instruction Templates

This directory contains modular templates for PM agent behavior.

## Quick Navigation

### Core Validation and Enforcement
- [validation_templates.md](validation_templates.md) - Verification requirements
- [circuit_breakers.md](circuit_breakers.md) - Violation detection system
- [pm_examples.md](pm_examples.md) - Concrete behavior examples

### Operational Protocols
- [git_file_tracking.md](git_file_tracking.md) - File tracking protocol
- [response_templates.md](response_templates.md) - Response formats

### Reference Material
- [pm_red_flags.md](pm_red_flags.md) - Phrases to avoid/use
- [delegation_workflows.md](delegation_workflows.md) - Delegation patterns

### Advanced Topics
- [pm_metrics.md](pm_metrics.md) - Evaluation framework
- [pm_tool_workflows.md](pm_tool_workflows.md) - Tool-specific workflows

## Template Standards

All templates follow these conventions:
- Version tracking
- Table of contents
- Parent document reference
- Clear purpose statement
- Consistent markdown formatting
```

---

## Implementation Phases

### Phase 1: Quick Wins ✅ **COMPLETED**

**Status**: ✅ DONE (Completed 2025-10-20)

**Modules Created**:
1. ✅ `validation_templates.md` (312 lines)
2. ✅ `circuit_breakers.md` (638 lines)
3. ✅ `pm_examples.md` (474 lines)

**Results**:
- PM_INSTRUCTIONS.md reduced from 1,145 lines to 806 lines (29.6% reduction)
- Established template ecosystem with consistent formatting
- Created foundation for future extractions

**Time Invested**: ~3 hours

---

### Phase 2: High-Priority Extractions (NEXT SESSION)

**Recommended for Next Work Session**

**Target**: Extract 3 high-priority modules to reduce PM_INSTRUCTIONS.md by additional ~320 lines

**Modules to Create**:

1. **`git_file_tracking.md`** (~192 lines)
   - Effort: 1.5 hours
   - Priority: HIGH
   - Impact: Largest remaining section

2. **`pm_red_flags.md`** (~61 lines)
   - Effort: 1 hour
   - Priority: HIGH
   - Impact: Frequently consulted reference

3. **`response_templates.md`** (~39 lines)
   - Effort: 1 hour
   - Priority: HIGH
   - Impact: Template standardization

**Phase 2 Goals**:
- [ ] Extract git file tracking protocol
- [ ] Create red flags phrase reference
- [ ] Standardize response format templates
- [ ] Update PM_INSTRUCTIONS.md with references
- [ ] Verify no content loss
- [ ] Test PM behavior consistency
- [ ] Update template README.md

**Expected Results**:
- PM_INSTRUCTIONS.md reduced to ~486 lines (57.5% total reduction from original)
- 6 template modules in ecosystem
- Improved discoverability of file tracking and validation requirements

**Estimated Time**: 3.5-4 hours

---

### Phase 3: Medium-Priority Consolidation (FUTURE)

**Target**: Extract remaining medium-priority modules for final optimization

**Modules to Create**:

1. **`delegation_workflows.md`** (~100 lines)
   - Effort: 1.5 hours
   - Priority: MEDIUM
   - Impact: Delegation reference material

2. **`pm_metrics.md`** (~59 lines)
   - Effort: 1.5 hours
   - Priority: MEDIUM
   - Impact: Evaluation framework

3. **`pm_tool_workflows.md`** (~76 lines)
   - Effort: 1 hour
   - Priority: MEDIUM
   - Impact: Tool-specific guidance

4. **Consider**: Merge `forbidden_actions` into `circuit_breakers.md` (~45 lines)
   - Effort: 0.5 hours
   - Priority: LOW-MEDIUM
   - Impact: Eliminate duplication

**Phase 3 Goals**:
- [ ] Extract delegation workflows and patterns
- [ ] Create metrics/evaluation framework
- [ ] Consolidate tool-specific workflows
- [ ] Consider forbidden actions merge
- [ ] Final PM_INSTRUCTIONS.md optimization
- [ ] Complete template ecosystem
- [ ] Create comprehensive template index

**Expected Results**:
- PM_INSTRUCTIONS.md reduced to ~286 lines (75% total reduction from original 1,145)
- 9-10 template modules (depending on merge decision)
- Complete modularization of PM instruction system

**Estimated Time**: 4-5 hours

---

## Validation Strategy

### Content Preservation Validation

**Before Each Extraction**:
1. ✅ Identify exact line ranges to extract
2. ✅ Document all cross-references to/from section
3. ✅ Verify no circular dependencies
4. ✅ Identify parent/child relationships

**During Extraction**:
1. ✅ Copy content verbatim to new template file
2. ✅ Add metadata header (purpose, version, parent reference)
3. ✅ Create table of contents
4. ✅ Update cross-references to use relative links
5. ✅ Replace extracted section in PM_INSTRUCTIONS.md with reference

**After Extraction**:
1. ✅ Verify new template file is well-formed markdown
2. ✅ Verify PM_INSTRUCTIONS.md reference links work
3. ✅ Check for broken internal links
4. ✅ Ensure no content duplication between files
5. ✅ Validate consistent markdown formatting

### PM Behavior Consistency Testing

**Test Scenarios**:

1. **Delegation Behavior**:
   - [ ] PM still delegates all implementation work
   - [ ] PM still delegates all investigation work
   - [ ] PM references templates correctly when needed

2. **Violation Detection**:
   - [ ] Circuit breakers still trigger on violations
   - [ ] Red flags still prevent incorrect phrases
   - [ ] File tracking protocol still enforced

3. **Verification Requirements**:
   - [ ] PM still requires evidence for all assertions
   - [ ] Validation templates still accessible
   - [ ] Response format still followed

4. **Reference Material Access**:
   - [ ] PM can find and reference templates when needed
   - [ ] Cross-references work correctly
   - [ ] No broken links or missing sections

**Test Execution**:
- Run test scenarios after each phase
- Use QA agent to validate PM behavior
- Check that PM responses reference templates appropriately
- Verify no degradation in PM quality

### Quality Gates

**Phase Completion Criteria**:

Each phase is complete only when ALL of the following are verified:

- [ ] All planned modules created with proper metadata
- [ ] PM_INSTRUCTIONS.md updated with references
- [ ] No content loss (line count matches expected)
- [ ] All cross-references validated and working
- [ ] Markdown formatting consistent across all files
- [ ] Template README.md updated with new modules
- [ ] PM behavior testing shows no regressions
- [ ] Git commits made with proper context messages
- [ ] Documentation updated (if needed)

**Regression Testing**:
- Test PM with typical user requests
- Verify PM still enforces delegation discipline
- Check that PM references templates appropriately
- Ensure no violation patterns return

---

## Risks and Mitigations

### Risk 1: Content Loss During Extraction

**Risk**: Accidentally losing important instructions or creating gaps in PM behavior.

**Probability**: MEDIUM
**Impact**: HIGH

**Mitigation Strategies**:
1. ✅ Use systematic extraction process (copy exact line ranges)
2. ✅ Verify line counts match before/after extraction
3. ✅ Use git diff to confirm only expected changes
4. ✅ Keep git history of each extraction step
5. ✅ Test PM behavior after each extraction
6. ✅ Maintain rollback capability (git revert)

**Detection**:
- Compare total line counts across all files
- Run comprehensive PM behavior tests
- Check for broken references or missing sections

---

### Risk 2: Broken Cross-References

**Risk**: Template references breaking, causing PM to lose access to critical information.

**Probability**: MEDIUM
**Impact**: MEDIUM

**Mitigation Strategies**:
1. ✅ Use relative paths for all references
2. ✅ Create validation script to check all markdown links
3. ✅ Test links after each extraction
4. ✅ Document reference patterns in template README.md
5. ✅ Use consistent reference format: `See [Topic](templates/file.md#section)`

**Detection**:
- Run markdown link checker
- Manual verification of key references
- Test PM's ability to find referenced content

---

### Risk 3: Increased Cognitive Load

**Risk**: Too many files makes it harder for PM to find relevant information.

**Probability**: LOW
**Impact**: MEDIUM

**Mitigation Strategies**:
1. ✅ Create comprehensive template README.md with navigation
2. ✅ Keep most-used content in main PM_INSTRUCTIONS.md
3. ✅ Use clear, descriptive file names
4. ✅ Maintain table of contents in each template
5. ✅ Add "Quick Reference" summary in PM_INSTRUCTIONS.md
6. ✅ Extract only truly modular, self-contained topics

**Detection**:
- Monitor if PM struggles to find information
- Track how often templates are referenced
- Gather feedback on PM effectiveness

---

### Risk 4: Backward Compatibility Issues

**Risk**: Existing agents or workflows expecting old PM_INSTRUCTIONS.md structure break.

**Probability**: LOW
**Impact**: LOW

**Mitigation Strategies**:
1. ✅ Maintain all content, just reorganized
2. ✅ Keep references in PM_INSTRUCTIONS.md to all extracted content
3. ✅ Use gradual migration approach (phases)
4. ✅ Document migration in git commit messages
5. ✅ Keep old structure available via git history
6. ✅ Test all agent interactions after each phase

**Detection**:
- Monitor for errors in agent behavior
- Check Claude MPM system logs
- Verify all slash commands still work

---

### Risk 5: Maintenance Overhead

**Risk**: More files means more places to update when PM behavior changes.

**Probability**: LOW
**Impact**: LOW

**Mitigation Strategies**:
1. ✅ Use template version tracking
2. ✅ Document which templates are affected by common changes
3. ✅ Create update checklist for template modifications
4. ✅ Use consistent structure across all templates
5. ✅ Maintain single source of truth for each topic
6. ✅ Avoid duplication between templates

**Detection**:
- Track time spent on PM instruction updates
- Monitor for inconsistencies between templates
- Check for duplicate content across files

---

### Risk 6: Over-Modularization

**Risk**: Creating too many small files that fragment PM knowledge unnecessarily.

**Probability**: LOW
**Impact**: MEDIUM

**Mitigation Strategies**:
1. ✅ Only extract sections >40 lines (except phase 1 exceptions)
2. ✅ Extract only self-contained, modular topics
3. ✅ Keep core PM identity in main file
4. ✅ Prefer merging related content (e.g., forbidden actions into circuit breakers)
5. ✅ Stop modularization when diminishing returns
6. ✅ Maintain ~250-300 line minimum for main PM_INSTRUCTIONS.md

**Detection**:
- Monitor file count vs. usefulness
- Check if templates are being referenced
- Evaluate PM instruction effectiveness

---

## Migration Strategy for Existing Agents

### Impact Analysis

**Who is affected by PM_INSTRUCTIONS.md modularization?**

1. **PM Agent** (Primary Consumer)
   - Most affected - needs to adapt to new structure
   - Must learn to reference templates
   - Impact: MEDIUM (offset by better organization)

2. **Other Agents** (Secondary Consumers)
   - May reference PM behavior patterns
   - May check delegation rules
   - Impact: LOW (most content remains, just reorganized)

3. **Claude MPM Framework**
   - Loads PM_INSTRUCTIONS.md at runtime
   - May parse or validate PM instructions
   - Impact: MINIMAL (file still exists, content accessible)

4. **Developers**
   - Maintain PM instruction system
   - Add new rules or templates
   - Impact: POSITIVE (easier to maintain modular system)

### Migration Approach

**No Breaking Changes Required**:
- PM_INSTRUCTIONS.md file remains in same location
- All content preserved, just reorganized
- References added to template modules
- Gradual rollout through phases

**Communication**:
- Document modularization in CHANGELOG.md
- Update relevant documentation (CLAUDE.md, STRUCTURE.md)
- Include migration notes in git commit messages
- Add notes to PM_INSTRUCTIONS.md header about template structure

**Rollback Plan**:
- Each phase committed separately in git
- Can revert to any previous phase if issues arise
- Keep backup of original PM_INSTRUCTIONS.md in git history
- Test thoroughly before marking phase complete

---

## Success Metrics

### Quantitative Metrics

**File Size Reduction**:
- ✅ Phase 1: 1,145 → 806 lines (29.6% reduction) - **ACHIEVED**
- 🎯 Phase 2: 806 → 486 lines (57.5% total reduction) - **TARGET**
- 🎯 Phase 3: 486 → 286 lines (75% total reduction) - **TARGET**

**Template Ecosystem**:
- ✅ Phase 1: 3 template files created - **ACHIEVED**
- 🎯 Phase 2: 6 template files total - **TARGET**
- 🎯 Phase 3: 9-10 template files total - **TARGET**

**Content Distribution**:
- 🎯 Main file (PM_INSTRUCTIONS.md): ~286 lines (core identity)
- 🎯 Templates (total): ~859 lines (reference material)
- 🎯 Ratio: ~25% main / ~75% templates

### Qualitative Metrics

**Maintainability**:
- [ ] Can add new delegation rule without affecting other sections
- [ ] Can update validation requirements in isolation
- [ ] Can enhance circuit breakers independently
- [ ] Clear ownership of each template module

**Discoverability**:
- [ ] Can find relevant template in <30 seconds
- [ ] Table of contents guides to right module
- [ ] Template README.md provides clear navigation
- [ ] Cross-references work correctly

**Consistency**:
- [ ] All templates follow same structure
- [ ] Version tracking in every template
- [ ] Consistent markdown formatting
- [ ] Clear parent/child relationships

**PM Effectiveness**:
- [ ] PM behavior unchanged (delegation discipline maintained)
- [ ] PM can reference templates when needed
- [ ] No increase in violations or errors
- [ ] PM responses remain high-quality

---

## Next Steps

### Immediate Actions (Phase 2 Preparation)

1. **Review and Approve Plan**
   - [ ] Stakeholder review of modularization strategy
   - [ ] Confirm Phase 2 module selection
   - [ ] Validate risk mitigation strategies
   - [ ] Approve timeline and effort estimates

2. **Pre-Phase 2 Preparation**
   - [ ] Create git branch for Phase 2 work
   - [ ] Prepare validation test suite
   - [ ] Document current PM behavior baseline
   - [ ] Set up markdown link checker

3. **Phase 2 Execution Checklist**
   - [ ] Extract git_file_tracking.md (~1.5 hours)
   - [ ] Extract pm_red_flags.md (~1 hour)
   - [ ] Extract response_templates.md (~1 hour)
   - [ ] Update PM_INSTRUCTIONS.md with references
   - [ ] Update template README.md
   - [ ] Run validation tests
   - [ ] Commit with proper context messages
   - [ ] Mark Phase 2 complete

### Long-Term Actions (Phase 3 Planning)

1. **Evaluate Phase 2 Results**
   - [ ] Measure PM effectiveness after Phase 2
   - [ ] Gather feedback on template structure
   - [ ] Adjust Phase 3 plan if needed
   - [ ] Identify any new modularization opportunities

2. **Phase 3 Execution**
   - [ ] Follow Phase 3 implementation plan
   - [ ] Create remaining template modules
   - [ ] Finalize PM_INSTRUCTIONS.md optimization
   - [ ] Complete template ecosystem

3. **Post-Modularization**
   - [ ] Update all related documentation
   - [ ] Create maintenance guide for template system
   - [ ] Document template update procedures
   - [ ] Share learnings and best practices

---

## Appendix A: Detailed Module Specifications

### Module Template Structure

All extracted modules will follow this standard structure:

```markdown
# [Module Name]

**Purpose**: [One-sentence description of module purpose]

**Version**: [Semantic version, starting at 1.0.0]
**Last Updated**: [YYYY-MM-DD]
**Parent Document**: [PM_INSTRUCTIONS.md](../PM_INSTRUCTIONS.md)

---

## Table of Contents

1. [Section 1](#section-1)
2. [Section 2](#section-2)
...

---

## [Content Sections]

[Module content here]

---

## Notes

- This document is extracted from PM_INSTRUCTIONS.md for better organization
- [Any module-specific notes]
- PM agents should reference this document for [topic]
- Updates to [topic] should be made here and referenced in PM_INSTRUCTIONS.md
```

### Reference Format in PM_INSTRUCTIONS.md

When extracting a section, replace it with this standard reference:

```markdown
## [Section Title]

**[Brief 1-2 sentence summary of what this section contains]**

See **[Module Name](templates/module_file.md)** for complete [topic] including:
- [Key item 1]
- [Key item 2]
- [Key item 3]

**Quick Summary**: [One-line essence of the section]
```

---

## Appendix B: Cross-Reference Map

### Current Cross-References in PM_INSTRUCTIONS.md

**References TO templates** (already implemented in Phase 1):
- Line 15: → `circuit_breakers.md` (Circuit Breaker system)
- Line 122: → `validation_templates.md` (Evidence requirements)
- Line 201: → `circuit_breakers.md` (Circuit Breaker #1)
- Line 264: → `validation_templates.md` (Deployment verification)
- Line 272: → `validation_templates.md` (Universal verification)
- Line 285: → `validation_templates.md` (Local deployment verification)
- Line 300: → `validation_templates.md` (QA requirements)
- Line 454: → `circuit_breakers.md` (Final circuit breakers)
- Line 468: → `pm_examples.md` (Concrete examples)
- Line 492: → `pm_examples.md` (Detailed examples)
- Line 700: → `circuit_breakers.md` (Circuit Breaker #5)

**References FROM templates** (to other templates):
- `validation_templates.md` references `circuit_breakers.md`
- `circuit_breakers.md` references `validation_templates.md`
- `pm_examples.md` references `validation_templates.md` and `circuit_breakers.md`

**Future Phase 2 References** (to be added):
- `git_file_tracking.md` will reference `circuit_breakers.md` (Circuit Breaker #5)
- `pm_red_flags.md` will reference `circuit_breakers.md` (violation types)
- `response_templates.md` will reference `validation_templates.md` (verification structure)

### Cross-Reference Validation Checklist

After each extraction:
- [ ] All references use relative paths
- [ ] All references include anchor links where appropriate
- [ ] No broken links (validate with markdown checker)
- [ ] Bidirectional references are consistent
- [ ] Template README.md updated with new cross-references

---

## Appendix C: Git Commit Strategy

### Commit Message Template for Phase 2

```bash
git add src/claude_mpm/agents/templates/[module_name].md
git add src/claude_mpm/agents/PM_INSTRUCTIONS.md
git commit -m "refactor: extract [topic] to template module

- Created [module_name].md with [X] lines of [topic] content
- Reduced PM_INSTRUCTIONS.md by [X] lines ([X]% reduction)
- Added table of contents and metadata to new template
- Updated PM_INSTRUCTIONS.md with reference to new template
- Part of Phase 2 PM modularization (targeting 75% total reduction)

Benefits:
- Better organization of [topic] knowledge
- Easier to maintain and update [topic] independently
- Improved discoverability through template structure

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase 2 Commit Strategy

**Option 1: Single Commit per Module** (RECOMMENDED)
- Commit after each module extraction
- Easier to track and revert if needed
- Clear atomic changes
- 3 commits for Phase 2

**Option 2: Single Commit for Entire Phase**
- Commit after all Phase 2 modules extracted
- Fewer commits in git history
- Requires more discipline to validate
- 1 commit for Phase 2

**Recommendation**: Use Option 1 (single commit per module) for better granularity and easier rollback.

---

## Conclusion

This modularization plan provides a comprehensive, phased approach to optimizing the PM_INSTRUCTIONS.md file. By extracting self-contained topics into focused template modules, we achieve:

1. **75% size reduction** in the main PM_INSTRUCTIONS.md file
2. **Improved maintainability** through modular organization
3. **Better discoverability** via dedicated template files
4. **Easier updates** with single-responsibility modules
5. **Preserved functionality** with no loss of PM capabilities

**Phase 1 (Quick Wins)** has already delivered 29.6% reduction and established the template ecosystem foundation.

**Phase 2 (High-Priority Extractions)** is ready for immediate implementation, targeting an additional 320 line reduction through 3 focused modules.

**Phase 3 (Medium-Priority Consolidation)** will complete the modularization, bringing the main file to a lean ~286 lines focused on core PM identity and critical rules.

This plan balances aggressive optimization with careful risk management, ensuring that PM behavior remains consistent and effective throughout the transformation.

---

**Document Status**: Ready for Phase 2 Implementation
**Next Review Date**: After Phase 2 Completion
**Owner**: Claude MPM Development Team
