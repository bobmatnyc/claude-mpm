# Intelligent QA Routing Configuration

## Overview

The PM workflow has been enhanced with intelligent QA agent routing that automatically selects the appropriate QA agent based on the implementation context. This ensures that API endpoints get tested by API QA specialists, web interfaces get tested by Web QA specialists, and full-stack features receive comprehensive testing from both.

## Implementation Summary

### 1. New API QA Agent Template
**Location**: `src/claude_mpm/agents/templates/api_qa.json`

The API QA Agent specializes in:
- REST API and GraphQL endpoint testing
- Authentication and authorization validation  
- Request/response validation
- Performance and load testing capabilities
- Contract testing with OpenAPI/Swagger
- Database operation validation

**Key Features**:
- Model: sonnet (for efficiency)
- Tools: Read, Write, Edit, Bash, Grep, Glob, LS, TodoWrite, WebFetch
- Focus on server-side and backend testing
- Comprehensive API security testing

### 2. Updated PM Workflow (Phase 3: Quality Assurance)
**Location**: `src/claude_mpm/agents/WORKFLOW.md`

The workflow now includes intelligent QA routing with:

1. **API QA Agent** - For server-side testing:
   - Triggered by: API, endpoint, route, REST, GraphQL, server, backend keywords
   - File indicators: `/api`, `/routes`, `/controllers`, `.py`, `.js`, `.go`, `.java`
   - Output: "API QA Complete: [Pass/Fail] - [Endpoints tested, Response times]"

2. **Web QA Agent** - For browser-based testing:
   - Triggered by: web, UI, page, frontend, browser, component keywords
   - File indicators: `/components`, `/pages`, `.jsx`, `.tsx`, `.vue`, `.html`
   - Output: "Web QA Complete: [Pass/Fail] - [Browsers tested, Metrics]"

3. **General QA Agent** - Default for other testing:
   - Used when neither API nor Web indicators are present
   - Tests: Unit tests, integration tests, CLI tools
   - Output: "QA Complete: [Pass/Fail] - [Coverage, Issues]"

4. **Full-Stack Testing** - Sequential QA:
   - First: API QA validates backend
   - Then: Web QA validates frontend
   - Finally: Integration validation

### 3. Enhanced PM Instructions
**Location**: `src/claude_mpm/agents/INSTRUCTIONS.md`

Added comprehensive QA routing logic with:
- QA Type Detection Protocol
- Backend/Frontend indicator analysis
- QA Handoff Patterns with examples
- TodoWrite patterns for QA coordination

### 4. Agent Registry Updates
**Location**: `src/claude_mpm/agents/agents_metadata.py`

Added metadata for:
- API_QA_CONFIG with performance targets
- WEB_QA_CONFIG with browser testing metrics
- Updated ALL_AGENT_CONFIGS registry

### 5. Template Registry Updates
**Location**: `src/claude_mpm/agents/templates/__init__.py`

Added template mappings:
- "api_qa": "api_qa_agent.md"
- "web_qa": "web_qa_agent.md"
- Added nicknames: "API QA" and "Web QA"

## QA Selection Logic

```python
def select_qa_agent(implementation_context):
    backend_keywords = ['api', 'endpoint', 'route', 'rest', 'graphql', 'server', 'backend']
    frontend_keywords = ['web', 'ui', 'page', 'frontend', 'browser', 'component']
    
    has_backend = any(keyword in context for keyword in backend_keywords)
    has_frontend = any(keyword in context for keyword in frontend_keywords)
    
    if has_backend and has_frontend:
        return ['api_qa', 'web_qa']  # Sequential testing
    elif has_backend:
        return ['api_qa']
    elif has_frontend:
        return ['web_qa']
    else:
        return ['qa']  # General QA
```

## Usage Examples

### Example 1: API Implementation
```
Engineer: "Implemented REST API endpoints for user management"
PM: Routes to API QA for endpoint validation
API QA: Tests CRUD operations, auth, performance
```

### Example 2: Web UI Implementation
```
Web UI: "Created responsive dashboard"
PM: Routes to Web QA for browser testing
Web QA: Tests across browsers, validates accessibility
```

### Example 3: Full-Stack Feature
```
Engineer: "Implemented auth with backend API and React frontend"
PM: Routes to API QA first, then Web QA
API QA: Validates endpoints, JWT flow
Web QA: Tests login UI, session management
```

## Testing

A comprehensive test suite verifies the configuration:
- **Script**: `scripts/test_intelligent_qa_routing.py`
- **Tests**: QA selection logic, agent configuration, workflow updates
- **Result**: All tests passing ✅

## Benefits

1. **Specialized Testing**: Each QA type focuses on their expertise area
2. **Comprehensive Coverage**: Full-stack features get tested at all layers
3. **Efficient Resource Use**: Right tool for the right job
4. **Clear Output Requirements**: Standardized reporting format
5. **Backward Compatible**: General QA still works for non-specific needs

## Key Requirements

- PM must analyze implementation context before QA delegation
- Original user instructions must be passed to QA agents
- Sequential testing for full-stack features (API first, then Web)
- Clear output format requirements for each QA type
- Fallback to general QA when specialized agents unavailable

## Future Enhancements

Potential improvements could include:
- Mobile QA agent for native app testing
- Performance QA agent for specialized load testing
- Security QA agent for penetration testing
- Integration QA agent for third-party service testing

## Deployment

To deploy the new API QA agent:
```bash
# Deploy the API QA agent
claude-mpm deploy api_qa

# List deployed agents to verify
claude-mpm list-agents

# The PM will automatically route to API QA when appropriate
```

## Validation

The intelligent routing has been validated with:
- ✅ QA selection logic correctly identifies context
- ✅ API QA agent configuration is valid
- ✅ Workflow documentation updated
- ✅ PM instructions include routing logic
- ✅ Agent registries updated
- ✅ All tests passing

The system is ready for use with intelligent QA routing based on implementation context.