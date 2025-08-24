# Framework Loader Routing Enhancement

## Overview

The framework loader has been enhanced to expose routing metadata from agent JSON templates for dynamic agent selection. This enables the PM to make more informed decisions about which agent to delegate tasks to based on keywords, file paths, and priorities.

## What Was Added

### 1. Routing Metadata Extraction

A new method `_load_routing_from_template()` was added to the `FrameworkLoader` class that:
- Loads routing information from agent JSON templates in `/src/claude_mpm/agents/templates/`
- Handles naming variations between deployed agents (e.g., `api_qa.md`) and templates (e.g., `api-qa.json`)
- Works with both packaged installations and development mode
- Caches results for performance

### 2. Enhanced Agent Metadata Parsing

The `_parse_agent_metadata()` method now:
- First attempts to extract routing from YAML frontmatter in deployed `.md` files
- Falls back to loading from JSON templates if not present
- Automatically handles name mapping variations (underscore vs dash)

### 3. Enriched Capabilities Section

The `_generate_agent_capabilities_section()` method now includes:
- **Routing keywords**: First 5 most relevant keywords for the agent
- **Path patterns**: First 3 file path patterns the agent specializes in
- **Priority**: Numeric priority for agent selection (higher = more specific)
- **When to use**: Human-readable description of when to select this agent

## Example Output

When the PM receives the framework instructions, agent capabilities now include routing hints:

```markdown
### API Qa (`api-qa`)
Specialized API and backend testing for REST, GraphQL, and server-side functionality
- **Routing**: Keywords: api, endpoint, rest, graphql, backend | Paths: /api/, /routes/, /controllers/ | Priority: 100
- **When to use**: Backend API, REST, GraphQL, and server-side testing
- **Model**: sonnet

### Web Qa (`web-qa`)
Web UI and frontend testing specialist
- **Routing**: Keywords: web, ui, frontend, browser, component | Paths: /components/, /pages/, /views/ | Priority: 100
- **When to use**: Frontend web UI, browser automation, and component testing
```

## How It Works

1. **Agent Discovery**: When agents are deployed, their metadata is parsed from YAML frontmatter
2. **Routing Lookup**: If no routing info exists in YAML, the loader checks the JSON template
3. **Name Mapping**: Handles variations like `api-qa` vs `api_qa` automatically
4. **Caching**: Results are cached for 60 seconds to improve performance
5. **Injection**: Routing hints are included in the PM's instructions for dynamic selection

## Benefits

- **Better Agent Selection**: PM can match tasks to agents based on keywords and paths
- **Priority-Based Routing**: More specific agents (priority 100) are preferred over general ones (priority 50)
- **Transparent Decision Making**: Routing criteria are visible in the capabilities section
- **Backward Compatible**: Works with existing agents that don't have routing metadata

## JSON Template Structure

Agent templates include routing information:

```json
{
  "routing": {
    "keywords": ["api", "endpoint", "rest", "graphql"],
    "paths": ["/api/", "/routes/", "/controllers/"],
    "priority": 100,
    "when_to_use": "Backend API, REST, GraphQL, and server-side testing"
  }
}
```

## Implementation Details

### Files Modified

- `/src/claude_mpm/core/framework_loader.py`:
  - Added `_load_routing_from_template()` method
  - Enhanced `_parse_agent_metadata()` to load routing data
  - Updated `_generate_agent_capabilities_section()` to display routing hints

### Performance Considerations

- Routing data is cached with a 60-second TTL
- JSON templates are only loaded if routing isn't in YAML frontmatter
- Name variations are checked efficiently using a set

### Testing

The enhancement was tested with:
- Multiple agent templates (api-qa, web-qa, qa)
- Deployed agents in `.claude/agents/`
- Both development and packaged installation modes
- Various naming conventions (underscore vs dash)

## Future Enhancements

Potential improvements for dynamic agent selection:
1. Use routing priorities for automatic agent ranking
2. Support regex patterns in paths
3. Add context-based keyword weighting
4. Enable custom routing rules per project
5. Implement routing statistics and analytics