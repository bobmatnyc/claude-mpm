# Web QA Agent: MCP-Browser Tool Integration Research

**Date**: 2025-12-18
**Researcher**: Claude Code (Research Agent)
**Status**: Research Complete - Ready for Implementation

---

## Executive Summary

Research conducted to identify the SOURCE file for the web-qa agent and document available mcp-browser MCP tools for integration. The web-qa agent currently references mcp-browser in dependencies but does not explicitly prioritize the five MCP tool functions available in the Claude Code environment.

**Key Finding**: The web-qa agent should be updated to explicitly prioritize mcp-browser MCP tools over WebFetch and other indirect methods for web content inspection.

---

## 1. Source File Location (CONFIRMED)

### Editable Source File

**Path**: `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/qa/web-qa.md`

**Verification**:
- File size: 21KB (503 lines)
- Last modified: 2025-12-18 09:36
- Current version: 3.0.2
- File is located in the agent cache repository (NOT deployment artifact)
- This is the CORRECT source file for editing

**Deployment Flow**:
```
SOURCE (editable):
└─ ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/qa/web-qa.md

    ↓ (agent deployment)

DEPLOYMENT ARTIFACT (auto-generated, DO NOT EDIT):
└─ .claude/agents/web-qa.md
```

---

## 2. Available MCP-Browser Tools

The following five MCP tools are available in the Claude Code environment for browser automation and inspection:

### 2.1 `mcp__mcp-browser__browser_action`

**Purpose**: Perform browser actions (navigate, click, fill, select, wait)

**Actions**:
- `navigate`: Navigate to URL
- `click`: Click elements by CSS selector, XPath, or text content
- `fill`: Fill single form field
- `select`: Select dropdown option (by value, text, or index)
- `wait`: Wait for element to appear

**Key Parameters**:
- `action` (required): Action type
- `url`: For navigate action
- `selector`: CSS selector for element
- `xpath`: XPath expression for element
- `text`: Text content to match for clicking
- `value`: Value to fill in field
- `timeout`: Wait timeout in milliseconds (default: 5000ms)
- `port`: Browser port (optional, auto-detected)

**Use Cases**:
- Navigate to web pages for testing
- Interact with forms and UI elements
- Wait for dynamic content to load
- Automate user interactions

---

### 2.2 `mcp__mcp-browser__browser_query`

**Purpose**: Query browser state (console logs, element info, capabilities)

**Query Types**:
- `logs`: Get console logs (debug, info, log, warn, error)
- `element`: Get element information by selector/xpath/text
- `capabilities`: Get browser capabilities

**Key Parameters**:
- `query` (required): Type of query
- `selector`: CSS selector for element query
- `xpath`: XPath for element query
- `text`: Text content to match
- `level_filter`: Filter logs by level (array)
- `last_n`: Number of recent logs to return (default: 100)
- `port`: Browser port (optional)

**Use Cases**:
- Monitor JavaScript errors in console
- Inspect element properties and attributes
- Verify browser capabilities before testing
- Track performance warnings

---

### 2.3 `mcp__mcp-browser__browser_screenshot`

**Purpose**: Capture screenshot of browser viewport

**Key Parameters**:
- `url`: Optional URL to navigate to before screenshot
- `port`: Browser port (optional)

**Use Cases**:
- Visual regression testing
- Capture error states
- Document UI issues
- Generate test evidence

---

### 2.4 `mcp__mcp-browser__browser_form`

**Purpose**: Form operations (fill multiple fields, submit)

**Actions**:
- `fill`: Fill multiple form fields at once
- `submit`: Submit form by selector or xpath

**Key Parameters**:
- `action` (required): Form action type
- `form_data`: Object mapping selectors to values (for fill)
- `selector`: CSS selector for form (for submit)
- `xpath`: XPath for form (for submit)
- `submit`: Submit after filling (boolean, default: false)
- `port`: Browser port (optional)

**Use Cases**:
- Efficient multi-field form testing
- Login and authentication flows
- Complex form submission scenarios
- Batch input testing

---

### 2.5 `mcp__mcp-browser__browser_extract`

**Purpose**: Extract page content (readable article or semantic DOM)

**Extraction Types**:
- `content`: Readable article content (main content extraction)
- `semantic_dom`: Semantic DOM structure with landmarks, headings, links, forms

**Key Parameters**:
- `extract` (required): Extraction type
- `include_landmarks`: Extract ARIA landmarks (default: true)
- `include_headings`: Extract h1-h6 headings (default: true)
- `include_links`: Extract links with text (default: true)
- `include_forms`: Extract forms and fields (default: true)
- `max_text_length`: Max characters per text field (default: 100)
- `tab_id`: Optional specific tab ID
- `port`: Browser port (optional)

**Use Cases**:
- Content accessibility analysis
- DOM structure inspection
- Semantic HTML validation
- Link and form discovery
- ARIA landmark verification

---

## 3. Current Web-QA Agent Analysis

### 3.1 Current MCP-Browser References

The web-qa agent currently mentions mcp-browser in:

1. **Dependencies** (lines 52, 57):
   - Listed as system dependency
   - Listed as npm dependency

2. **Knowledge Domain** (line 76-79):
   - MCP Browser Extension setup and verification
   - Enhanced browser control via MCP protocol
   - DOM inspection and manipulation through extension
   - Network request interception with MCP browser

3. **Phase 0: MCP Browser Extension Setup** (lines 378-396):
   - Setup verification commands
   - Benefits listed (DOM inspection, console monitoring, etc.)

### 3.2 Current Tool Usage Patterns

**Search Results**: No explicit usage of the five MCP tools found in the agent instructions.

**Current Pattern**:
- Agent references mcp-browser as a dependency and capability
- No explicit tool prioritization in testing protocols
- WebFetch and other tools may be used implicitly

**Gap Identified**:
- Agent knows ABOUT mcp-browser but doesn't explicitly USE the MCP tools
- No guidance on WHEN to use each of the five mcp-browser tools
- No prioritization over WebFetch for web content inspection

---

## 4. Integration Recommendations

### 4.1 Prioritization Strategy

**Tool Selection Hierarchy** (add to agent instructions):

```
Web Content Inspection Priority:
1. mcp__mcp-browser__browser_extract (semantic_dom mode)
   - Use for: DOM structure, accessibility analysis, link/form discovery
   - Benefit: No Playwright overhead, fast semantic analysis

2. mcp__mcp-browser__browser_query (element/logs queries)
   - Use for: Element inspection, console error monitoring
   - Benefit: Real-time browser state without page reloads

3. mcp__mcp-browser__browser_action (navigate, wait, click)
   - Use for: Lightweight navigation and interaction
   - Benefit: Faster than full Playwright automation

4. mcp__mcp-browser__browser_screenshot
   - Use for: Visual evidence capture
   - Benefit: Quick visual validation without full test suite

5. WebFetch (fallback only)
   - Use when: mcp-browser tools unavailable
   - Limitation: No JavaScript execution, no DOM inspection
```

### 4.2 Phase-Specific Integration

**Phase 0: MCP Browser Extension Setup**
- Add explicit check for mcp-browser MCP tools availability
- Use `browser_query(query="capabilities")` to verify browser readiness

**Phase 1: API Testing**
- No change (API-focused, not browser-focused)

**Phase 2: Routes Testing**
- **BEFORE**: Use fetch/curl for HTTP testing
- **AFTER**: Add `browser_action(action="navigate")` + `browser_query(query="logs")` for early JavaScript error detection

**Phase 3: Links2 Testing**
- **BEFORE**: Use links2 for text-based validation
- **AFTER**: Supplement with `browser_extract(extract="semantic_dom")` for richer DOM analysis

**Phase 4: Safari Testing**
- **BEFORE**: AppleScript + console monitoring
- **AFTER**: Add `browser_query(query="logs", level_filter=["error", "warn"])` for structured console output

**Phase 5: Playwright Testing**
- **BEFORE**: Full Playwright automation
- **AFTER**: Use mcp-browser tools for lightweight checks BEFORE invoking Playwright

### 4.3 New Tool Usage Guidelines

Add this section to the agent instructions:

```markdown
## MCP-Browser Tool Usage Guidelines

### When to Use mcp-browser MCP Tools vs Playwright

**Use mcp-browser MCP tools for**:
- Quick DOM structure inspection (browser_extract)
- Console error monitoring (browser_query with logs)
- Lightweight navigation and clicking (browser_action)
- Element existence checks (browser_query with element)
- Visual evidence capture (browser_screenshot)

**Use Playwright for**:
- Complex multi-step user flows
- Visual regression testing suites
- Performance profiling (Core Web Vitals)
- Cross-browser matrix testing
- Video recording of test sessions

**Prioritization Rule**: Always attempt mcp-browser MCP tools BEFORE escalating to Playwright. Only use Playwright when:
1. mcp-browser tools insufficient (complex interactions)
2. Full automation script needed (CI/CD integration)
3. Cross-browser testing required (browser matrix)
4. Performance profiling needed (Lighthouse integration)

### Tool Selection Decision Tree

```
Need to inspect web page?
    ↓
Is it a simple DOM/content check?
    YES → Use browser_extract(extract="semantic_dom")
    NO  → Continue
        ↓
    Is it console error monitoring?
        YES → Use browser_query(query="logs")
        NO  → Continue
            ↓
        Is it a simple click/navigate?
            YES → Use browser_action(action="click/navigate")
            NO  → Continue
                ↓
            Is it a complex multi-step flow?
                YES → Use Playwright
                NO  → Use browser_extract or browser_query
```
```

---

## 5. Example Integration Patterns

### 5.1 Early JavaScript Error Detection (Phase 2)

**Current Pattern**:
```bash
# Use fetch/curl for HTTP testing
curl -I https://example.com
```

**Enhanced Pattern**:
```python
# Step 1: Navigate with mcp-browser
browser_action(action="navigate", url="https://example.com")

# Step 2: Check console for errors
browser_query(query="logs", level_filter=["error", "warn"], last_n=50)

# Step 3: Extract semantic DOM
browser_extract(extract="semantic_dom", include_landmarks=True)
```

### 5.2 Accessibility Analysis (Phase 3)

**Current Pattern**:
```bash
# Use links2 for text-based validation
links2 -dump https://example.com
```

**Enhanced Pattern**:
```python
# Step 1: Extract semantic DOM with full accessibility info
browser_extract(
    extract="semantic_dom",
    include_landmarks=True,
    include_headings=True,
    include_forms=True,
    include_links=True
)

# Step 2: Supplement with links2 for text-only rendering
# (Keep links2 as complementary tool)
```

### 5.3 Console Monitoring (Phase 4 & 5)

**Current Pattern**:
```bash
# Monitor console with AppleScript + log files
osascript -e '...' > console.log
```

**Enhanced Pattern**:
```python
# Step 1: Use structured console query
browser_query(
    query="logs",
    level_filter=["error", "warn"],
    last_n=100
)

# Step 2: Correlate with test actions
# (Parse structured JSON output instead of log files)
```

---

## 6. Implementation Checklist

### Phase 1: Update Agent Instructions

- [ ] Add "MCP-Browser Tool Usage Guidelines" section after Phase 0
- [ ] Insert tool prioritization hierarchy before Phase 1
- [ ] Add decision tree for tool selection
- [ ] Update Phase 2 to include `browser_action` + `browser_query`
- [ ] Update Phase 3 to include `browser_extract`
- [ ] Update Phase 4 to include structured `browser_query`
- [ ] Add examples section with integration patterns

### Phase 2: Update Knowledge Domain

- [ ] Add explicit knowledge of the five mcp-browser MCP tools
- [ ] Document tool parameters and use cases
- [ ] Add decision-making guidance (when to use each tool)

### Phase 3: Testing and Validation

- [ ] Test web-qa agent with mcp-browser tool prioritization
- [ ] Verify faster testing cycles (less Playwright usage)
- [ ] Validate console monitoring improvements
- [ ] Confirm accessibility analysis enhancements

### Phase 4: Documentation

- [ ] Update agent changelog (version bump to 3.1.0)
- [ ] Document breaking changes (if any)
- [ ] Add migration guide for existing test scripts

---

## 7. Risk Assessment

### Low Risk

- **Tool Availability**: All five mcp-browser tools are available in Claude Code environment
- **Backward Compatibility**: Changes are additive (prioritization, not removal)
- **Graceful Degradation**: Agent can fall back to existing tools if mcp-browser unavailable

### Medium Risk

- **Learning Curve**: QA agent must learn new tool selection patterns
- **Performance**: Unknown if mcp-browser tools are faster than current methods (needs benchmarking)

### Mitigation Strategies

1. **Gradual Rollout**: Update Phase 2 first, then Phase 3, then Phase 4/5
2. **Fallback Protocol**: Always include WebFetch and existing tools as fallback
3. **Performance Benchmarking**: Compare mcp-browser vs Playwright speeds in Phase 5

---

## 8. Next Steps

### Immediate Actions

1. **Edit SOURCE file**: `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/qa/web-qa.md`
2. **Add tool prioritization section** after Phase 0 (around line 396)
3. **Update Phase 2-5** with mcp-browser tool integration patterns
4. **Bump version** from 3.0.2 → 3.1.0 (minor feature addition)

### Follow-Up Actions

1. **Test deployment**: Deploy updated agent to test project
2. **Validate behavior**: Run web-qa tests and confirm tool usage
3. **Benchmark performance**: Compare testing speeds before/after
4. **Document learnings**: Update this research document with results

---

## 9. Related Documentation

### Claude MPM Framework

- **Agent Modification Workflow**: `docs/developer/agent-modification-workflow.md`
- **Agent Cache Architecture**: `CLAUDE.md` (lines 19-42)
- **Source vs Deployment**: `CLAUDE.md` (lines 65-137)

### MCP-Browser Documentation

- **MCP Browser Extension**: https://github.com/modelcontextprotocol/mcp-browser
- **MCP Protocol Specification**: https://modelcontextprotocol.io/
- **Claude Code MCP Integration**: Claude Code documentation

---

## 10. Appendix: Tool Function Signatures

### A. browser_action

```typescript
browser_action(
  action: "navigate" | "click" | "fill" | "select" | "wait",
  url?: string,              // For navigate
  selector?: string,         // CSS selector
  xpath?: string,            // XPath expression
  text?: string,             // Text content to match
  value?: string,            // Value to fill
  timeout?: number,          // Wait timeout (ms)
  index?: number,            // Element index if multiple matches
  option_value?: string,     // Select option value
  option_text?: string,      // Select option text
  option_index?: number,     // Select option index
  port?: number              // Browser port (auto-detected)
)
```

### B. browser_query

```typescript
browser_query(
  query: "logs" | "element" | "capabilities",
  selector?: string,         // For element query
  xpath?: string,            // For element query
  text?: string,             // For element query
  level_filter?: string[],   // For logs: ["debug", "info", "log", "warn", "error"]
  last_n?: number,           // For logs: default 100
  port?: number              // Browser port (auto-detected)
)
```

### C. browser_screenshot

```typescript
browser_screenshot(
  url?: string,              // Optional URL to navigate first
  port?: number              // Browser port (auto-detected)
)
```

### D. browser_form

```typescript
browser_form(
  action: "fill" | "submit",
  form_data?: Record<string, string>,  // For fill: selector → value mapping
  selector?: string,                   // For submit
  xpath?: string,                      // For submit
  submit?: boolean,                    // For fill: submit after filling
  port?: number                        // Browser port (auto-detected)
)
```

### E. browser_extract

```typescript
browser_extract(
  extract: "content" | "semantic_dom",
  include_landmarks?: boolean,         // Default: true
  include_headings?: boolean,          // Default: true
  include_links?: boolean,             // Default: true
  include_forms?: boolean,             // Default: true
  max_text_length?: number,            // Default: 100
  tab_id?: number,                     // Optional specific tab
  port?: number                        // Browser port (auto-detected)
)
```

---

## Research Metadata

**Agent**: Research Agent (evidence-based analysis)
**Task Type**: Informational Research (no actionable subtasks)
**Tools Used**: Bash, Read, Grep, Write
**File Operations**: 1 research document created
**Outcome**: Source file identified, MCP tools documented, integration recommendations provided

**Research Quality**: High confidence
- Source file verified with file metadata
- All five MCP tools documented from function definitions
- Current agent behavior analyzed (lines 52, 57, 76-79, 378-396)
- Integration patterns proposed with examples
- Risk assessment and implementation checklist provided

**Capture Status**: ✅ Saved to `/Users/masa/Projects/claude-mpm/docs/research/web-qa-mcp-browser-integration-2025-12-18.md`

---

*End of Research Document*
