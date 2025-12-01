# PM Instructions Optimization Analysis

**Date**: 2025-12-01
**Researcher**: Research Agent
**Files Analyzed**: PM_INSTRUCTIONS.md (2,556 lines, 95KB), WORKFLOW.md, MEMORY.md, BASE_PM.md
**Purpose**: Identify optimization opportunities for PM instructions through verbosity reduction, MCP dependency extraction, and conditional loading architecture

---

## Executive Summary

### Current State
- **Total Size**: 95,035 bytes (95KB)
- **Estimated Tokens**: 23,758 tokens
- **Line Count**: 2,556 lines
- **Major Sections**: 31 top-level sections
- **Subsections**: 81 subsections
- **Code Blocks**: 76 code examples
- **Visual Markers**: 291 emoji markers (❌, ✅, ⛔, 🚨)

### Optimization Potential

**Scenario 1: MCP Conditional Loading Only**
- Base instructions: 16,266 tokens
- Ticketing (conditional): 7,492 tokens
- **Savings when MCP unavailable**: 7,492 tokens (31.5%)

**Scenario 2: External Template References**
- Core with inline content: 23,758 tokens
- Core with template references: 10,130 tokens
- **Template savings**: 13,628 tokens (57.4%)

**Scenario 3: Combined Optimization (Recommended)**
- Core instructions: 2,638 tokens
- Ticketing (conditional): 7,492 tokens
- Templates (on-demand): 13,928 tokens
- **Total potential savings**: 21,120 tokens (88.9%)

### Key Findings
1. **MCP-ticketer content represents 31.5% of total instructions** (886 lines, 7,492 tokens)
2. **External templates are referenced but likely duplicated** (circuit-breakers.md: 34KB, validation-templates.md: 13KB)
3. **High verbosity in examples and demonstrations** (76 code blocks, 34 example markers)
4. **Significant redundancy in violation detection rules** (repeated across multiple sections)

---

## 1. Verbosity Analysis

### Major Compression Opportunities

#### 1.1 TICKETING SYSTEM INTEGRATION (Lines 891-1776)
- **Current**: 886 lines, ~30KB, 7,492 tokens
- **Potential**: 200 lines, ~7KB, 1,750 tokens
- **Strategy**: Conditional loading, move examples to template file
- **Compression**: 81% reduction when MCP unavailable

**Details**:
- Extensive examples of ticket reading patterns (lines 917-1000)
- Detailed context optimization explanations (lines 903-1000)
- Multiple delegation examples with full ticket data (lines 1001-1100)
- Scope protection protocol duplicates validation patterns (lines 1100-1300)

**Recommended Action**: Extract to `templates/ticketing-integration.md`, load conditionally only when `mcp__mcp-ticketer__*` tools detected.

#### 1.2 SIMPLIFIED DELEGATION RULES (Lines 518-894)
- **Current**: 377 lines, ~15KB, 3,750 tokens
- **Potential**: 150 lines, ~6KB, 1,500 tokens
- **Strategy**: Consolidate redundant examples, extract decision trees to template
- **Compression**: 60% reduction

**Details**:
- Research gate protocol (lines 527-758): Highly verbose with decision matrices
- Multiple redundant examples showing same delegation pattern
- Decision trees repeated in different contexts
- Violation checkpoints duplicated from circuit breakers section

**Recommended Action**:
- Keep high-level principles inline
- Extract research gate examples to `templates/research-gate-examples.md` (already exists: 2.6KB)
- Reference decision matrices instead of inline duplication

#### 1.3 FORBIDDEN ACTIONS (Lines 77-161)
- **Current**: 85 lines, ~3KB, 750 tokens
- **Potential**: 30 lines, ~1KB, 250 tokens
- **Strategy**: Consolidate violation lists, reference circuit-breakers.md
- **Compression**: 67% reduction

**Details**:
- Implementation violations listed 3 times (lines 79-87, 88-97, circuit breakers reference)
- Investigation violations duplicated (lines 98-108)
- Ticketing violations repeated (lines 109-117)

**Recommended Action**: Single consolidated list with references to `templates/circuit-breakers.md` for detailed examples.

#### 1.4 STRUCTURED QUESTIONS FOR USER INPUT (Lines 207-390)
- **Current**: 184 lines, ~7KB, 1,750 tokens
- **Potential**: 50 lines, ~2KB, 500 tokens
- **Strategy**: Extract question templates to external file
- **Compression**: 71% reduction

**Details**:
- PR strategy template (lines 231-252): 22 lines of example structure
- Multiple question template examples with full syntax
- Best practices section verbose (lines 270-283)

**Recommended Action**: Extract to `templates/structured-questions.md`, keep only 2-3 sentence overview with reference.

#### 1.5 GIT FILE TRACKING PROTOCOL (Lines 1778-2116)
- **Current**: 339 lines, ~13KB, 3,250 tokens
- **Potential**: 80 lines, ~3KB, 750 tokens
- **Strategy**: Extract to `templates/git-file-tracking.md` (already exists!)
- **Compression**: 77% reduction

**Details**:
- Detailed protocol steps with extensive examples
- Multiple violation scenarios with full explanations
- Template file already exists at `/templates/git-file-tracking.md`

**Recommended Action**: Replace inline content with reference to existing template file.

### Redundant Content Patterns

#### Pattern 1: Violation Detection Rules
**Occurrences**:
- Lines 63-76: Circuit breakers overview
- Lines 77-161: Forbidden actions
- Lines 1812-1850: Implementation detection reference
- `templates/circuit-breakers.md`: Complete 1,005-line template

**Issue**: Circuit breaker rules appear 4 times in different forms.

**Recommendation**:
- Keep 10-line summary in PM_INSTRUCTIONS.md
- Reference `templates/circuit-breakers.md` for details
- Remove redundant inline explanations
- **Savings**: ~500 lines, 2,000 tokens (8.4%)

#### Pattern 2: Delegation Examples
**Occurrences**:
- Lines 118-147: Ticket search delegation
- Lines 518-526: Delegation-first response patterns
- Lines 554-726: Research gate delegation
- Lines 1160-1262: Ticket context delegation
- `templates/pm-examples.md`: 474 lines of examples

**Issue**: Similar delegation patterns repeated across 5 sections.

**Recommendation**:
- Consolidate into 3 canonical examples inline
- Reference `templates/pm-examples.md` for additional scenarios
- **Savings**: ~200 lines, 800 tokens (3.4%)

#### Pattern 3: Verification Requirements
**Occurrences**:
- Lines 489-495: Assertion verification rule
- Lines 1894-1930: Deployment verification
- `templates/validation-templates.md`: 312 lines (13KB)

**Issue**: Verification matrices duplicated inline and in template.

**Recommendation**:
- Keep 5-line principle statement inline
- Reference `templates/validation-templates.md` for matrices
- **Savings**: ~150 lines, 600 tokens (2.5%)

### Example Extraction Candidates

**High-Value Extractions** (examples that could move to template files):

1. **Ticketing Integration Examples** (Lines 917-1100)
   - Move to: `templates/ticketing-integration-examples.md`
   - Content: Full ticket delegation workflows, context optimization patterns
   - Savings: 183 lines, ~730 tokens

2. **Research Gate Decision Matrices** (Lines 576-686)
   - Move to: `templates/research-gate-examples.md` (already exists, append)
   - Content: Detailed decision trees, scenario tables
   - Savings: 110 lines, ~440 tokens

3. **PR Workflow Examples** (Lines 1739-1777)
   - Move to: `templates/pr-workflow-examples.md`
   - Content: Main-based vs stacked PR strategies
   - Savings: 39 lines, ~156 tokens

4. **Context Management Examples** (Lines 370-449)
   - Move to: `templates/context-management-examples.md`
   - Content: Pause prompt templates, token usage scenarios
   - Savings: 80 lines, ~320 tokens

**Total Example Extraction Potential**: 412 lines, ~1,646 tokens (6.9%)

---

## 2. MCP Service Dependencies

### 2.1 mcp-ticketer Dependencies

**Primary Section**: Lines 891-1776 (886 lines, 29,968 bytes, 7,492 tokens)

**Content Breakdown**:
- Detection patterns (lines 891-920): 30 lines
- Context optimization (lines 921-1000): 80 lines
- Delegation patterns (lines 1001-1160): 160 lines
- Scope protection protocol (lines 1161-1500): 340 lines
- Ticket completeness verification (lines 1501-1776): 276 lines

**Tool References**:
```grep
Line 111: ❌ Using mcp-ticketer tools directly → MUST DELEGATE to ticketing
Line 123: PM: [Uses mcp__mcp-ticketer__ticket_search directly]  ← VIOLATION
Line 137: PM: [Uses mcp__mcp-ticketer__ticket_list directly]  ← VIOLATION
Line 858: **ALL Ticket CRUD Operations** (PM MUST NEVER use mcp-ticketer tools directly)
Line 867: ❌ **ANY mcp__mcp-ticketer__* tool whatsoever**
Line 947: [Uses: mcp__mcp-ticketer__ticket_read(ticket_id="1M-163")]
Line 1078: **Circuit Breaker #6 Extension**: PM using ANY mcp-ticketer tool = VIOLATION
Line 1155: Look for `mcp__mcp-ticketer__ticket_read` in available tools
Line 1219: Check tools → mcp-ticketer available
Line 1262: Check tools → mcp-ticketer available
```

**Conditional Loading Criteria**:
```python
# Detection method
if "mcp__mcp-ticketer__ticket_read" in available_tools:
    load_ticketing_integration_section()
```

**Impact**:
- **With ticketing**: 23,758 tokens (100%)
- **Without ticketing**: 16,266 tokens (68.5%)
- **Savings**: 7,492 tokens (31.5%)

### 2.2 mcp-vector-search Dependencies

**References**: Lines 169, 499-506 (minimal, ~50 lines total)

**Content**:
- Line 169: Tool usage permission for PM
- Lines 499-506: Vector search workflow for PM (8 lines)
- Lines 502-504: Three allowed vector search tools

**Tool References**:
```
mcp__mcp-vector-search__get_project_status
mcp__mcp-vector-search__search_code
mcp__mcp-vector-search__search_context
```

**Impact**: Minimal (50 lines, ~200 tokens, 0.8%)

**Recommendation**: Keep inline, not worth conditional loading due to small size.

### 2.3 mcp-browser Dependencies

**References**: None found in PM_INSTRUCTIONS.md

**Analysis**: mcp-browser is not referenced in PM instructions. May be used by specialized agents (web-qa, web-ui) but not PM-specific.

### 2.4 Other MCP Service References

**None detected** in PM_INSTRUCTIONS.md. Only mcp-ticketer and mcp-vector-search are referenced.

### MCP Dependency Summary

| MCP Service | Lines | Tokens | % of Total | Conditional Load? |
|-------------|-------|--------|------------|-------------------|
| mcp-ticketer | 886 | 7,492 | 31.5% | ✅ YES - High value |
| mcp-vector-search | 50 | 200 | 0.8% | ❌ NO - Too small |
| mcp-browser | 0 | 0 | 0.0% | ❌ N/A |
| **Total MCP-dependent** | **936** | **7,692** | **32.3%** | |

---

## 3. Conditional Loading Architecture Recommendation

### 3.1 Proposed Approach: Marker-Based Section Loading

**Architecture**: Use HTML comment markers to denote conditional sections, with runtime detection of MCP services to determine loading.

**Advantages**:
- ✅ Minimal code changes to existing loader
- ✅ Backward compatible (markers ignored if not processed)
- ✅ Clear section boundaries
- ✅ Easy to add new conditional sections
- ✅ Works with existing `InstructionLoader` and `ContentFormatter`

**File Structure**:
```markdown
<!-- PM_INSTRUCTIONS.md -->

# Core PM Instructions
[Always loaded content]

<!-- CONDITIONAL_SECTION: mcp-ticketer -->
<!-- CONDITION: mcp__mcp-ticketer__ticket_read in tools -->
## TICKETING SYSTEM INTEGRATION
[Only loaded if mcp-ticketer tools available]
<!-- END_CONDITIONAL_SECTION -->

[More core content]
```

### 3.2 Detection Method

**Tool Availability Detection**:
```python
# In InstructionLoader or new ConditionalLoader class

def detect_available_mcp_services(self) -> set[str]:
    """Detect which MCP services are available at runtime.

    Returns:
        Set of available MCP service names (e.g., {'mcp-ticketer', 'mcp-vector-search'})
    """
    available_services = set()

    # Check for ticketing tools
    ticketing_tools = [
        "mcp__mcp-ticketer__ticket_read",
        "mcp__mcp-ticketer__ticket_search",
        "mcp__mcp-ticketer__ticket_list",
    ]
    if any(self._tool_available(tool) for tool in ticketing_tools):
        available_services.add("mcp-ticketer")

    # Check for vector search tools
    vector_tools = [
        "mcp__mcp-vector-search__search_code",
        "mcp__mcp-vector-search__get_project_status",
    ]
    if any(self._tool_available(tool) for tool in vector_tools):
        available_services.add("mcp-vector-search")

    return available_services

def _tool_available(self, tool_name: str) -> bool:
    """Check if a tool is available in the current Claude Code environment.

    This would integrate with Claude Code's tool discovery mechanism.
    """
    # Implementation depends on Claude Code's tool API
    # Placeholder: return tool_name in get_available_tools()
    pass
```

**Conditional Section Parser**:
```python
def parse_conditional_sections(self, content: str, available_services: set[str]) -> str:
    """Parse and filter conditional sections based on available MCP services.

    Args:
        content: Raw instruction content with conditional markers
        available_services: Set of available MCP service names

    Returns:
        Filtered content with only applicable conditional sections
    """
    import re

    # Pattern: <!-- CONDITIONAL_SECTION: service-name -->...<!-- END_CONDITIONAL_SECTION -->
    pattern = r'<!-- CONDITIONAL_SECTION: ([a-z\-]+) -->\s*<!-- CONDITION: ([^>]+) -->(.*?)<!-- END_CONDITIONAL_SECTION -->'

    def should_include_section(match):
        service_name = match.group(1)
        condition = match.group(2)  # e.g., "mcp__mcp-ticketer__ticket_read in tools"
        section_content = match.group(3)

        # Check if service is available
        if service_name in available_services:
            return section_content
        else:
            # Return placeholder or omit entirely
            return f"\n<!-- {service_name} integration not available -->\n"

    # Replace all conditional sections
    filtered = re.sub(pattern, should_include_section, content, flags=re.DOTALL)

    return filtered
```

### 3.3 Integration with Existing Loader

**Modified `InstructionLoader.load_framework_instructions()`**:
```python
def load_framework_instructions(self, content: Dict[str, Any]) -> None:
    """Load framework INSTRUCTIONS.md or PM_INSTRUCTIONS.md with conditional sections."""

    # Existing loading logic...
    if pm_instructions_path.exists():
        raw_content = self.file_loader.try_load_file(
            pm_instructions_path, "consolidated PM_INSTRUCTIONS.md"
        )

        if raw_content:
            # NEW: Detect available MCP services
            available_services = self.detect_available_mcp_services()
            self.logger.info(f"Available MCP services: {available_services}")

            # NEW: Parse and filter conditional sections
            filtered_content = self.parse_conditional_sections(raw_content, available_services)

            content["framework_instructions"] = filtered_content
            content["loaded"] = True
            content["conditional_sections_applied"] = True
            content["available_mcp_services"] = list(available_services)

            self.logger.info(
                f"Loaded PM_INSTRUCTIONS.md with {len(available_services)} conditional sections"
            )
```

### 3.4 Template Reference Architecture

**For external templates** (circuit-breakers.md, validation-templates.md, etc.):

**Option A: Lazy Loading via References**
```markdown
## 🚨 DELEGATION VIOLATION CIRCUIT BREAKERS 🚨

PM must delegate ALL implementation and investigation work. See [Circuit Breakers](templates/circuit-breakers.md) for:
- Circuit Breaker #1: Implementation Detection
- Circuit Breaker #2: Investigation Detection
- Circuit Breaker #3: Unverified Assertions
- Circuit Breaker #4: Implementation Before Delegation
- Circuit Breaker #5: File Tracking
- Circuit Breaker #6: Ticketing Tool Misuse

**Quick Summary**: PM coordinates, agents execute. Zero tolerance for violations.
```

**Option B: On-Demand Template Injection**
```python
def load_template_on_demand(self, template_name: str, content: Dict[str, Any]) -> str:
    """Load external template only when referenced by instruction content.

    Args:
        template_name: Name of template file (e.g., "circuit-breakers")
        content: Framework content dictionary

    Returns:
        Template content or empty string if not needed
    """
    template_path = (
        self.framework_path / "src" / "claude_mpm" / "agents" / "templates" / f"{template_name}.md"
    )

    if template_path.exists():
        return self.file_loader.try_load_file(template_path, f"template {template_name}")

    return ""

# In ContentFormatter.format_full_framework():
# Check for template references and inject on-demand
if "See [Circuit Breakers]" in instructions:
    circuit_breakers = loader.load_template_on_demand("circuit-breakers", framework_content)
    if circuit_breakers:
        instructions += f"\n\n<!-- TEMPLATE: circuit-breakers -->\n{circuit_breakers}\n"
```

**Recommendation**: Use **Option A (References)** initially, as it's simpler and non-breaking. Option B can be added later if context limits become critical.

### 3.5 Backward Compatibility

**Ensuring No Breaking Changes**:

1. **Graceful Degradation**: If conditional section parsing fails, fall back to loading full content
2. **Marker Tolerance**: Existing systems without conditional parser ignore HTML comments naturally
3. **Default Behavior**: If MCP detection fails, load ALL conditional sections (conservative approach)
4. **Version Metadata**: Add `<!-- CONDITIONAL_LOADING_VERSION: 1 -->` to track files using this feature

**Compatibility Code**:
```python
def load_framework_instructions_safe(self, content: Dict[str, Any]) -> None:
    """Load framework instructions with safe fallback for conditional loading."""
    try:
        # Try new conditional loading
        self.load_framework_instructions_with_conditionals(content)
        content["conditional_loading_enabled"] = True
    except Exception as e:
        self.logger.warning(f"Conditional loading failed, using full content: {e}")
        # Fall back to existing loader
        self._load_filesystem_framework_instructions(content)
        content["conditional_loading_enabled"] = False
```

### 3.6 Implementation Steps

**Phase 1: Marker Addition** (Non-Breaking)
1. Add conditional section markers to PM_INSTRUCTIONS.md
2. Markers are HTML comments, ignored by current parser
3. No code changes needed yet
4. Test existing system still works

**Phase 2: Detection Infrastructure**
1. Implement `detect_available_mcp_services()` method
2. Add tool availability checking logic
3. Log detected services (for debugging)
4. No filtering yet, just detection

**Phase 3: Conditional Parsing**
1. Implement `parse_conditional_sections()` method
2. Integrate with `InstructionLoader`
3. Add feature flag to enable/disable conditional loading
4. Test with and without mcp-ticketer

**Phase 4: Template References**
1. Replace inline duplications with references
2. Update circuit-breakers, validation-templates sections
3. Measure token savings
4. Validate PM behavior unchanged

**Phase 5: Validation & Rollout**
1. Test with multiple MCP configurations
2. Verify backward compatibility
3. Update documentation
4. Roll out to production

---

## 4. Compression Strategy

### High Priority (>20% token reduction)

#### 1. Conditional MCP-Ticketer Loading (31.5% reduction when unavailable)
- **Current**: 7,492 tokens always loaded
- **Target**: 7,492 tokens only when mcp-ticketer available
- **Method**: Marker-based conditional loading
- **Implementation**: Phase 1-3 (4 weeks)
- **Risk**: Low (graceful degradation)
- **Value**: High (significant savings for non-ticketing projects)

#### 2. External Template References - Circuit Breakers (8.4% reduction)
- **Current**: Circuit breaker rules duplicated inline (2,000 tokens)
- **Target**: 100-token summary with reference (1,900 tokens saved)
- **Method**: Replace duplication with references to templates/circuit-breakers.md
- **Implementation**: Phase 4 (1 week)
- **Risk**: Low (template already exists)
- **Value**: High (reduces redundancy)

### Medium Priority (10-20% token reduction)

#### 3. Research Gate Protocol Consolidation (15% reduction)
- **Current**: 377 lines in SIMPLIFIED DELEGATION RULES section (3,750 tokens)
- **Target**: 150 lines with external examples (1,500 tokens)
- **Method**: Extract decision matrices to templates/research-gate-examples.md (exists)
- **Implementation**: 2 weeks
- **Risk**: Medium (affects core workflow understanding)
- **Value**: Medium (significant size reduction)

#### 4. Git File Tracking Externalization (12% reduction)
- **Current**: 339 lines inline (3,250 tokens)
- **Target**: 80 lines with reference to templates/git-file-tracking.md (750 tokens)
- **Method**: Replace with reference to existing template file
- **Implementation**: 1 week
- **Risk**: Low (template already exists)
- **Value**: High (easy win, low effort)

### Low Priority (<10% token reduction)

#### 5. Example Extraction to Templates (6.9% reduction)
- **Current**: 412 lines of examples inline (1,646 tokens)
- **Target**: Brief examples inline, detailed in templates (400 tokens inline)
- **Method**: Create new template files for specialized examples
- **Implementation**: 2 weeks
- **Risk**: Low (examples are supplementary)
- **Value**: Medium (improves readability, reduces cognitive load)

#### 6. Structured Questions Simplification (5% reduction)
- **Current**: 184 lines of question templates (1,750 tokens)
- **Target**: 50 lines with template reference (500 tokens)
- **Method**: Extract to templates/structured-questions.md
- **Implementation**: 1 week
- **Risk**: Low (rarely used feature)
- **Value**: Low (minor improvement)

### Compression Strategy Summary

| Priority | Item | Current Tokens | Target Tokens | Savings | % Reduction | Effort | Risk | Value |
|----------|------|----------------|---------------|---------|-------------|--------|------|-------|
| **High** | MCP-Ticketer Conditional | 7,492 | 0-7,492* | 7,492 | 31.5% | 4 weeks | Low | High |
| **High** | Circuit Breakers Refs | 2,000 | 100 | 1,900 | 8.4% | 1 week | Low | High |
| **Medium** | Research Gate Consolidation | 3,750 | 1,500 | 2,250 | 9.5% | 2 weeks | Medium | Medium |
| **Medium** | Git File Tracking Refs | 3,250 | 750 | 2,500 | 10.5% | 1 week | Low | High |
| **Low** | Example Extraction | 1,646 | 400 | 1,246 | 5.2% | 2 weeks | Low | Medium |
| **Low** | Structured Questions | 1,750 | 500 | 1,250 | 5.3% | 1 week | Low | Low |
| | **TOTAL** | **19,888** | **3,250-10,742** | **16,638** | **70.0%** | **11 weeks** | | |

*Note: Ticketing tokens loaded conditionally based on MCP availability

---

## 5. Recommended Action Plan

### Phase 1: Quick Wins (2 weeks)

**Goal**: Achieve 18.9% token reduction with minimal risk

**Tasks**:
1. **Git File Tracking Externalization** (1 week)
   - Replace lines 1778-2116 with reference to existing `templates/git-file-tracking.md`
   - Add 5-line summary inline
   - Savings: 2,500 tokens (10.5%)

2. **Circuit Breakers Reference** (1 week)
   - Replace lines 63-161 with reference to `templates/circuit-breakers.md`
   - Keep 10-line summary inline
   - Savings: 1,900 tokens (8.4%)

**Deliverables**:
- Updated PM_INSTRUCTIONS.md with references
- No loader code changes needed
- Backward compatible
- Total savings: 4,400 tokens (18.5%)

### Phase 2: Conditional Loading Infrastructure (4 weeks)

**Goal**: Implement MCP service detection and conditional section loading

**Tasks**:
1. **Add Conditional Markers** (1 week)
   - Add HTML comment markers to ticketing section (lines 891-1776)
   - No code changes, fully backward compatible
   - Test existing system unchanged

2. **Implement MCP Detection** (1 week)
   - Add `detect_available_mcp_services()` method to InstructionLoader
   - Implement tool availability checking
   - Log detected services for debugging

3. **Implement Conditional Parser** (1 week)
   - Add `parse_conditional_sections()` method
   - Integrate with InstructionLoader.load_framework_instructions()
   - Add feature flag for gradual rollout

4. **Testing & Validation** (1 week)
   - Test with mcp-ticketer present/absent
   - Verify graceful degradation
   - Measure actual token savings
   - Update documentation

**Deliverables**:
- Conditional loading architecture implemented
- Feature flag for controlled rollout
- MCP service detection working
- Savings: 7,492 tokens (31.5%) when ticketing unavailable

### Phase 3: Advanced Optimizations (5 weeks)

**Goal**: Further reduce token usage through consolidation and extraction

**Tasks**:
1. **Research Gate Consolidation** (2 weeks)
   - Extract decision matrices to templates/research-gate-examples.md
   - Consolidate inline content to core principles
   - Update references
   - Savings: 2,250 tokens (9.5%)

2. **Example Template Extraction** (2 weeks)
   - Create templates/ticketing-integration-examples.md
   - Create templates/context-management-examples.md
   - Create templates/pr-workflow-examples.md
   - Update inline references
   - Savings: 1,246 tokens (5.2%)

3. **Final Validation** (1 week)
   - End-to-end testing
   - Performance benchmarking
   - Documentation updates
   - User migration guide

**Deliverables**:
- Comprehensive template library
- Optimized PM instructions
- Updated documentation
- Additional savings: 3,496 tokens (14.7%)

### Total Optimization Roadmap

**Timeline**: 11 weeks total

**Cumulative Savings**:
- After Phase 1: 4,400 tokens (18.5%)
- After Phase 2: 11,892 tokens (50.0%)
- After Phase 3: 15,388 tokens (64.8%)

**Final State**:
- Core instructions: ~8,370 tokens (always loaded)
- Conditional sections: ~7,492 tokens (loaded when MCP available)
- External templates: ~13,928 tokens (referenced, not loaded)
- **Total reduction from 23,758 to 8,370 base tokens (64.8% reduction)**

### Risk Mitigation

**Feature Flags**:
```python
# Enable gradual rollout
ENABLE_CONDITIONAL_LOADING = os.getenv("MPM_CONDITIONAL_LOADING", "false") == "true"
ENABLE_TEMPLATE_REFERENCES = os.getenv("MPM_TEMPLATE_REFERENCES", "false") == "true"
```

**Monitoring**:
- Log actual token usage before/after
- Track PM behavior changes
- Monitor error rates
- Collect user feedback

**Rollback Plan**:
- Keep original PM_INSTRUCTIONS.md as PM_INSTRUCTIONS.md.bak
- Feature flags allow instant rollback
- Graceful degradation prevents breakage

---

## 6. Technical Specifications

### 6.1 Conditional Section Marker Syntax

```markdown
<!-- CONDITIONAL_SECTION: service-identifier -->
<!-- CONDITION: tool-check-expression -->
<!-- DESCRIPTION: Human-readable explanation -->

[Section content here]

<!-- END_CONDITIONAL_SECTION -->
```

**Example**:
```markdown
<!-- CONDITIONAL_SECTION: mcp-ticketer -->
<!-- CONDITION: mcp__mcp-ticketer__ticket_read in available_tools -->
<!-- DESCRIPTION: Ticketing system integration instructions for PM -->

## TICKETING SYSTEM INTEGRATION WITH SCOPE PROTECTION (mcp-ticketer)

[Full ticketing integration content...]

<!-- END_CONDITIONAL_SECTION -->
```

### 6.2 Template Reference Syntax

```markdown
## Section Title

[Brief 3-5 line summary of key points]

**See [Template Name](path/to/template.md) for:**
- Detail 1
- Detail 2
- Detail 3

**Quick Reference**: [One-sentence core principle]
```

**Example**:
```markdown
## 🚨 DELEGATION VIOLATION CIRCUIT BREAKERS 🚨

Circuit breakers prevent PM from implementing, investigating, or asserting without delegation. They detect violations before they happen.

**See [Circuit Breakers](templates/circuit-breakers.md) for:**
- Implementation Detection (Edit/Write/Bash)
- Investigation Detection (Read/Grep/Glob)
- Assertion Verification (Evidence requirements)
- File Tracking Protocol
- Ticketing Tool Misuse

**Quick Reference**: PM coordinates, agents execute. Zero tolerance for violations.
```

### 6.3 Loader Integration Points

**File**: `src/claude_mpm/core/framework/loaders/instruction_loader.py`

**New Methods**:
```python
def detect_available_mcp_services(self) -> set[str]:
    """Detect available MCP services at runtime."""
    pass

def parse_conditional_sections(self, content: str, available_services: set[str]) -> str:
    """Parse and filter conditional sections."""
    pass

def load_template_on_demand(self, template_name: str) -> Optional[str]:
    """Load external template file."""
    pass
```

**Modified Methods**:
```python
def load_framework_instructions(self, content: Dict[str, Any]) -> None:
    """Load framework instructions with conditional section support."""
    # Existing code...

    # NEW: Conditional section parsing
    if raw_content:
        available_services = self.detect_available_mcp_services()
        filtered_content = self.parse_conditional_sections(raw_content, available_services)
        content["framework_instructions"] = filtered_content
```

### 6.4 Feature Flag Configuration

**Environment Variables**:
```bash
# Enable conditional loading feature
export MPM_CONDITIONAL_LOADING=true

# Enable template reference system
export MPM_TEMPLATE_REFERENCES=true

# Debug: Log conditional section decisions
export MPM_DEBUG_CONDITIONAL=true
```

**Configuration File** (`.claude-mpm/config.json`):
```json
{
  "features": {
    "conditional_loading": {
      "enabled": true,
      "services": ["mcp-ticketer", "mcp-vector-search"]
    },
    "template_references": {
      "enabled": true,
      "on_demand": false
    }
  }
}
```

---

## 7. Success Metrics

### Token Efficiency Metrics

**Before Optimization**:
- Base tokens (all scenarios): 23,758

**After Phase 1** (Git + Circuit Breaker refs):
- Base tokens: 19,358
- Reduction: 4,400 tokens (18.5%)

**After Phase 2** (+ Conditional MCP):
- With MCP: 19,358 tokens
- Without MCP: 11,866 tokens
- Average reduction: 7,492 tokens (31.5%)

**After Phase 3** (+ All optimizations):
- Core: 8,370 tokens
- + MCP conditional: 7,492 tokens
- + Templates (on-demand): 13,928 tokens
- Maximum reduction: 15,388 tokens (64.8%)

### Quality Metrics

**Maintain**:
- ✅ PM delegation behavior unchanged
- ✅ Circuit breaker effectiveness unchanged
- ✅ Ticketing integration quality unchanged
- ✅ Research gate protocol adherence unchanged

**Improve**:
- ✅ Faster context loading (less parsing)
- ✅ Better readability (less cognitive load)
- ✅ Easier maintenance (single source of truth for templates)
- ✅ Flexible MCP service support

### Performance Metrics

**Expected**:
- Context loading time: -30% (less content to parse)
- PM response latency: -15% (smaller context window)
- Token budget available: +64.8% (more room for task context)

---

## 8. Conclusion

### Key Takeaways

1. **Significant optimization potential exists** (64.8% reduction possible)
2. **MCP-ticketer content dominates instructions** (31.5% of total)
3. **Template duplication is widespread** (circuit-breakers, validation-templates, pm-examples)
4. **Conditional loading is feasible** with marker-based architecture
5. **Backward compatibility is maintainable** through graceful degradation

### Recommended Next Steps

1. **Immediate**: Implement Phase 1 (git + circuit breaker references) - 2 weeks, 18.5% savings
2. **Short-term**: Implement Phase 2 (conditional MCP loading) - 4 weeks, +31.5% savings
3. **Long-term**: Implement Phase 3 (advanced optimizations) - 5 weeks, +14.8% savings

### Trade-offs

**Pros**:
- ✅ Dramatic token savings (64.8% potential)
- ✅ Better scalability for MCP service additions
- ✅ Improved maintainability (single source of truth)
- ✅ Flexible loading based on environment

**Cons**:
- ⚠️ Additional complexity in loader logic
- ⚠️ Need to test multiple MCP configurations
- ⚠️ Template references may be less discoverable than inline content
- ⚠️ Requires careful validation to ensure PM behavior unchanged

### Final Recommendation

**Proceed with phased implementation starting with Phase 1** (quick wins with low risk), then evaluate results before committing to Phase 2 (conditional loading). Phase 3 can be deferred based on observed benefits from Phase 1-2.

The marker-based conditional loading architecture is the most practical approach, offering flexibility, backward compatibility, and clear section boundaries. External template references reduce duplication and improve maintainability without sacrificing functionality.

---

## Appendix A: Section Size Analysis

### Top 15 Largest Sections (by line count)

| Rank | Section | Lines | Est. Tokens | % of Total |
|------|---------|-------|-------------|------------|
| 1 | TICKETING SYSTEM INTEGRATION | 886 | 7,492 | 31.5% |
| 2 | SIMPLIFIED DELEGATION RULES | 377 | 3,750 | 15.8% |
| 3 | GIT FILE TRACKING PROTOCOL | 339 | 3,250 | 13.7% |
| 4 | STRUCTURED QUESTIONS | 184 | 1,750 | 7.4% |
| 5 | FORBIDDEN ACTIONS | 85 | 750 | 3.2% |
| 6 | AUTO-CONFIGURATION | 67 | 650 | 2.7% |
| 7 | CORE IMPERATIVE | 52 | 500 | 2.1% |
| 8 | Workflow Pipeline | 46 | 450 | 1.9% |
| 9 | ONLY ALLOWED PM TOOLS | 45 | 425 | 1.8% |
| 10 | Quick Reference | 40 | 400 | 1.7% |
| 11 | PR WORKFLOW | 39 | 380 | 1.6% |
| 12 | TICKET-BASED WORK | 38 | 370 | 1.6% |
| 13 | ENFORCEMENT | 31 | 300 | 1.3% |
| 14 | CLAUDE MPM COMMANDS | 31 | 300 | 1.3% |
| 15 | DELEGATION SCORECARD | 30 | 290 | 1.2% |

### Cumulative Analysis

- Top 3 sections: 1,602 lines (62.7% of total)
- Top 5 sections: 1,871 lines (73.2% of total)
- Top 10 sections: 2,128 lines (83.2% of total)

**Insight**: Focusing on the top 5 sections captures 73% of optimization potential.

---

## Appendix B: Template File Inventory

### Existing Template Files

| Template | Size (KB) | Lines | Est. Tokens | Status | Referenced? |
|----------|-----------|-------|-------------|--------|-------------|
| circuit-breakers.md | 34 | 1,005 | 8,704 | ✅ Exists | ✅ Yes (line 69) |
| validation-templates.md | 13 | 312 | 3,328 | ✅ Exists | ✅ Yes (line 495) |
| pm-examples.md | ~7 | 474 | 1,896 | ✅ Exists | ✅ Yes (line 2093) |
| research-gate-examples.md | 2.6 | ~80 | 650 | ✅ Exists | ✅ Yes (line 758) |
| git-file-tracking.md | ~5 | ~150 | 1,250 | ✅ Exists | ❌ No |
| ticket-completeness-examples.md | ~4 | ~120 | 1,000 | ✅ Exists | ✅ Yes (line 1764) |
| response-format.md | ~3 | ~90 | 750 | ✅ Exists | ❌ No |

**Total Existing Templates**: 7 files, ~68KB, ~2,331 lines, ~17,578 tokens

### Potential New Templates

| Template | Est. Size | Est. Tokens | Purpose |
|----------|-----------|-------------|---------|
| ticketing-integration-examples.md | 10KB | 2,500 | Detailed ticket delegation workflows |
| context-management-examples.md | 5KB | 1,250 | Pause prompt templates, token scenarios |
| pr-workflow-examples.md | 3KB | 750 | Main-based vs stacked PR strategies |
| structured-questions.md | 6KB | 1,500 | Question template library |

**Total Potential New Templates**: 4 files, ~24KB, ~6,000 tokens

---

## Appendix C: Redundancy Detection

### Duplicate Content Patterns

**Pattern**: Delegation violation lists

**Occurrences**:
- Lines 79-87: Implementation violations (9 lines)
- Lines 88-97: Implementation violations (doing work) (10 lines)
- Lines 98-108: Investigation violations (11 lines)
- Lines 109-117: Ticketing violations (9 lines)
- Circuit-breakers.md: Complete violation catalog (1,005 lines)

**Consolidation Opportunity**: Replace 39 lines with 10-line summary + reference

---

**Pattern**: Verification requirements

**Occurrences**:
- Lines 489-495: Assertion verification (7 lines)
- Lines 1894-1902: Deployment verification (9 lines)
- Lines 1902-1915: Validation templates reference (14 lines)
- Lines 1915-1930: Local deployment verification (16 lines)
- validation-templates.md: Complete verification matrices (312 lines)

**Consolidation Opportunity**: Replace 46 lines with 10-line principle + reference

---

**Pattern**: Example delegation workflows

**Occurrences**:
- Lines 118-147: Ticket search delegation (30 lines)
- Lines 518-526: Delegation-first patterns (9 lines)
- Lines 554-726: Research gate delegation (173 lines)
- Lines 1160-1262: Ticket context delegation (103 lines)
- pm-examples.md: Comprehensive examples (474 lines)

**Consolidation Opportunity**: Replace 315 lines with 30 lines canonical + references

---

## Appendix D: Code Block Analysis

### Code Block Distribution

**Total Code Blocks**: 76

**By Type**:
- Delegation examples: 23 blocks (30.3%)
- Violation scenarios: 18 blocks (23.7%)
- Decision trees/flowcharts: 12 blocks (15.8%)
- Configuration examples: 8 blocks (10.5%)
- Template structures: 7 blocks (9.2%)
- Command examples: 8 blocks (10.5%)

**Average Size**: ~15 lines per block

**Largest Blocks**:
1. Lines 554-686: Research gate decision matrix (132 lines)
2. Lines 891-1100: Ticketing delegation workflow (209 lines)
3. Lines 1778-2000: Git file tracking protocol (222 lines)

**Optimization**: Large code blocks (>50 lines) are prime candidates for template extraction.

---

## Appendix E: MCP Service Extension Framework

### Adding New Conditional MCP Services

**Process**:

1. **Add conditional marker** to PM_INSTRUCTIONS.md:
```markdown
<!-- CONDITIONAL_SECTION: mcp-browser -->
<!-- CONDITION: mcp__mcp-browser__navigate in available_tools -->
<!-- DESCRIPTION: Browser automation instructions for PM -->

## BROWSER AUTOMATION INTEGRATION

[Section content...]

<!-- END_CONDITIONAL_SECTION -->
```

2. **Update MCP detection** in `instruction_loader.py`:
```python
def detect_available_mcp_services(self) -> set[str]:
    # ... existing ticketing detection ...

    # Check for browser tools
    browser_tools = [
        "mcp__mcp-browser__navigate",
        "mcp__mcp-browser__screenshot",
    ]
    if any(self._tool_available(tool) for tool in browser_tools):
        available_services.add("mcp-browser")

    return available_services
```

3. **No changes needed** to parser - it automatically handles new services

**Scalability**: System designed to support unlimited MCP services without code changes (after initial infrastructure).

---

**Research Complete**: 2025-12-01
**Next Steps**: Review findings with PM, prioritize action plan phases, implement Phase 1 quick wins.
