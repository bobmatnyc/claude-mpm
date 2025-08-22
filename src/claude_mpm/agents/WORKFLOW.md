<!-- WORKFLOW_VERSION: 0002 -->
<!-- LAST_MODIFIED: 2025-01-14T18:30:00Z -->

# PM Workflow Configuration

## Mandatory Workflow Sequence

**STRICT PHASES - MUST FOLLOW IN ORDER**:

### Phase 1: Research (ALWAYS FIRST)
- Analyze requirements and gather context
- Investigate existing patterns and architecture
- Identify constraints and dependencies
- Output feeds directly to implementation phase

### Phase 2: Implementation (AFTER Research)
- Engineer Agent for code implementation
- Data Engineer Agent for data pipelines/ETL
- Security Agent for security implementations
- Ops Agent for infrastructure/deployment

### Phase 3: Quality Assurance (AFTER Implementation)

**Intelligent QA Agent Selection**:

The PM must analyze the implementation context to route to the appropriate QA agent based on a comprehensive decision tree. This ensures that each QA type focuses on their area of expertise while maintaining comprehensive coverage.

#### QA Agent Types and Capabilities

1. **API QA Agent** - Specialized for server-side and backend testing:
   - **Primary Focus**: REST APIs, GraphQL, server routes, authentication systems
   - **Triggered by keywords**: API, endpoint, route, REST, GraphQL, server, backend, authentication, authorization, database, microservice, webhook
   - **File indicators**: 
     - Directories: `/api`, `/routes`, `/controllers`, `/services`, `/models`, `/middleware`
     - Files: `.py` (FastAPI/Flask/Django), `.js/.ts` (Express/NestJS), `.go`, `.java`, `.php`, `.rb`
   - **Testing capabilities**:
     - REST endpoint validation (CRUD operations, status codes, headers)
     - GraphQL query and mutation testing
     - Authentication and authorization flows (JWT, OAuth2, API keys)
     - Database operation validation and data integrity
     - Request/response schema validation (OpenAPI/Swagger)
     - API performance and load testing
     - Contract testing between services
     - Security testing (OWASP API Security Top 10)
   - **Tools and frameworks**: Postman/Newman, curl, HTTPie, Jest/Mocha for API tests
   - **Required Output**: "API QA Complete: [Pass/Fail] - [Endpoints tested: X, Avg response time: Xms, Auth flows: X, Security checks: X, Issues: X]"

2. **Web QA Agent** - Specialized for browser-based and frontend testing:
   - **Primary Focus**: Web pages, UI components, browser testing, user experience
   - **Triggered by keywords**: web, UI, page, frontend, browser, component, responsive, accessibility, user interface, client-side, SPA
   - **File indicators**:
     - Directories: `/components`, `/pages`, `/views`, `/public`, `/assets`, `/styles`
     - Files: `.jsx/.tsx` (React), `.vue` (Vue.js), `.svelte`, `.html`, `.css/.scss`, `.js` (client-side)
   - **Testing capabilities**:
     - UI component functionality and rendering
     - User flow validation (registration, login, checkout, etc.)
     - Responsive design testing across devices and screen sizes
     - Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
     - Accessibility compliance (WCAG 2.1 AA standards)
     - Client-side performance (Core Web Vitals, load times)
     - Interactive element testing (forms, buttons, navigation)
     - Visual regression testing
   - **Tools and frameworks**: Selenium, Playwright, Cypress, browser dev tools
   - **Required Output**: "Web QA Complete: [Pass/Fail] - [Browsers tested: X, Pages validated: X, Accessibility score: X%, Performance score: X%, Issues: X]"

3. **General QA Agent** - Default for comprehensive testing needs:
   - **Primary Focus**: Libraries, CLI tools, utilities, integration testing
   - **Default selection**: When neither API nor Web indicators are present
   - **File indicators**: CLI tools, libraries, utilities, scripts, configuration files, test files
   - **Testing capabilities**:
     - Unit test execution and coverage analysis
     - Integration testing between components
     - CLI functionality and command validation
     - Library method and function testing
     - Configuration file validation
     - Build and deployment process testing
     - Cross-platform compatibility
   - **Tools and frameworks**: pytest, Jest, JUnit, Mocha, CLI testing frameworks
   - **Required Output**: "QA Complete: [Pass/Fail] - [Tests run: X, Coverage: X%, CLI commands: X, Issues: X]"

4. **Full-Stack Testing** - Coordinated testing for complete features:
   - **Triggered when**: Both backend AND frontend changes detected in implementation
   - **Sequential execution order**:
     a. **First: API QA** validates backend functionality and data flows
     b. **Then: Web QA** validates frontend integration and user experience
     c. **Finally: Integration validation** between all layers
   - **Coordination requirements**:
     - API QA must complete successfully before Web QA begins
     - Both agents receive original user requirements
     - Integration testing covers end-to-end user workflows
     - Data consistency validation across frontend and backend
   - **Required Output**: "Full-Stack QA Complete: [Pass/Fail] - API: [API results], Web: [Web results], Integration: [End-to-end results]"

#### QA Selection Decision Tree

The PM follows this decision logic to route QA testing appropriately:

```
📊 QA ROUTING DECISION TREE
│
├─ 🔍 ANALYZE IMPLEMENTATION CONTEXT
│   ├─ Keywords Analysis
│   ├─ File Path Analysis  
│   ├─ Technology Stack Detection
│   └─ Feature Scope Assessment
│
├─ 🌐 BACKEND INDICATORS → API QA Agent
│   ├─ Keywords: api, endpoint, route, rest, graphql, server, backend, auth, database, microservice
│   ├─ File Paths: /api/, /routes/, /controllers/, /services/, /models/, /middleware/
│   ├─ Extensions: .py, .js/.ts (server), .go, .java, .php, .rb
│   ├─ Content: @app.route, router.get, API decorators, database schemas
│   └─ Output: "API QA Complete: [detailed API testing results]"
│
├─ 💻 FRONTEND INDICATORS → Web QA Agent  
│   ├─ Keywords: web, ui, page, frontend, browser, component, responsive, accessibility, spa
│   ├─ File Paths: /components/, /pages/, /views/, /public/, /assets/, /styles/
│   ├─ Extensions: .jsx/.tsx, .vue, .svelte, .html, .css/.scss, .js (client)
│   ├─ Content: React components, Vue templates, CSS frameworks, client-side logic
│   └─ Output: "Web QA Complete: [detailed UI/UX testing results]"
│
├─ 🔄 FULL-STACK INDICATORS → Sequential QA (API → Web)
│   ├─ Mixed Context: Both backend AND frontend changes
│   ├─ User Stories: End-to-end feature requirements
│   ├─ Integration: Frontend consumes backend APIs
│   ├─ Execution: API QA first, then Web QA, then integration validation
│   └─ Output: "Full-Stack QA Complete: [combined testing results]"
│
└─ ⚙️  DEFAULT → General QA Agent
    ├─ No specific indicators detected
    ├─ CLI tools, libraries, utilities
    ├─ Configuration files, scripts
    ├─ Pure logic/algorithm implementations
    └─ Output: "QA Complete: [general testing results]"
```

**Detailed Detection Logic**:

```
Backend Indicators → Route to API QA:
- API route definitions (e.g., @app.route, router.get, @api.route)
- Database models, migrations, or ORM configurations
- Authentication/authorization middleware and logic
- GraphQL schemas, resolvers, or mutations
- Server configuration files (server.js, app.py, main.go)
- Backend service implementations and business logic
- Microservice definitions and inter-service communication
- API documentation or OpenAPI specifications

Frontend Indicators → Route to Web QA:
- React/Vue/Angular/Svelte components and pages
- HTML templates, views, or page definitions
- CSS/SCSS/Tailwind style files and responsive design
- Client-side JavaScript for user interactions
- Static assets (images, fonts, icons) and asset optimization
- Frontend build configurations (webpack, vite, rollup)
- Progressive Web App (PWA) configurations
- Client-side routing and navigation logic

Mixed Indicators → Sequential QA (API QA → Web QA → Integration):
- Both backend and frontend files modified in implementation
- Full-stack feature implementation (e.g., auth system, e-commerce)
- End-to-end user stories spanning multiple layers
- Features requiring backend API and frontend UI coordination
- Real-time features (WebSocket, SSE) with client-server interaction
- Data flow from database through API to user interface

Default Indicators → General QA:
- CLI tools and command-line applications
- Libraries, utilities, and helper functions
- Configuration file processing
- Data processing scripts and algorithms
- Testing frameworks and test utilities
- Build tools and automation scripts
```

#### Practical Usage Examples

**Example 1: API Implementation**
```
User Request: "Create a REST API for user management with CRUD operations"
Engineer Output: "Implemented FastAPI endpoints in /api/users.py with authentication"

PM Analysis:
✅ Backend Keywords: "REST API", "endpoints", "authentication"
✅ File Indicators: "/api/users.py"
✅ Technology: FastAPI (Python backend)

PM Decision: Route to API QA Agent
API QA Tasks:
- Test GET /users (list users)
- Test POST /users (create user) 
- Test PUT /users/{id} (update user)
- Test DELETE /users/{id} (delete user)
- Validate authentication headers
- Check error responses (400, 401, 404, 500)
- Verify response schemas match OpenAPI spec
- Performance test with 100 concurrent requests

API QA Output: "API QA Complete: Pass - [Endpoints tested: 4, Avg response time: 45ms, Auth flows: 2, Security checks: 3, Issues: 0]"
```

**Example 2: Web UI Implementation**
```
User Request: "Build a responsive dashboard with charts and user profile"
Web UI Output: "Created React dashboard in /components/Dashboard.tsx with mobile-first design"

PM Analysis:
✅ Frontend Keywords: "responsive dashboard", "charts", "user profile"
✅ File Indicators: "/components/Dashboard.tsx"
✅ Technology: React (frontend framework)

PM Decision: Route to Web QA Agent
Web QA Tasks:
- Test dashboard rendering on desktop (1920x1080)
- Test mobile responsiveness (375x667, 768x1024)
- Verify chart interactivity and data visualization
- Test user profile edit functionality
- Check accessibility (WCAG 2.1 AA compliance)
- Cross-browser testing (Chrome, Firefox, Safari)
- Measure Core Web Vitals (LCP, FID, CLS)

Web QA Output: "Web QA Complete: Pass - [Browsers tested: 3, Pages validated: 2, Accessibility score: 95%, Performance score: 88%, Issues: 1 minor]"
```

**Example 3: Full-Stack Feature**
```
User Request: "Implement complete authentication system with login UI and JWT backend"
Engineer Output: "Built auth API in /api/auth.py and login components in /components/auth/"

PM Analysis:
✅ Backend Keywords: "JWT backend", "auth API"
✅ Frontend Keywords: "login UI", "components"
✅ File Indicators: "/api/auth.py", "/components/auth/"
✅ Full-Stack Feature: Both backend and frontend implementation

PM Decision: Sequential QA (API QA → Web QA → Integration)

Phase 1 - API QA:
- Test POST /auth/login endpoint
- Test POST /auth/register endpoint  
- Test JWT token generation and validation
- Test protected endpoint access with tokens
- Verify password hashing and security

API QA Output: "API QA Complete: Pass - [Endpoints tested: 3, Auth flows: 2, Security checks: 5, Issues: 0]"

Phase 2 - Web QA:
- Test login form submission and validation
- Test registration form with field validation
- Test token storage and automatic logout
- Test protected route navigation
- Test error handling for invalid credentials

Web QA Output: "Web QA Complete: Pass - [Forms tested: 2, User flows: 3, Error states: 4, Issues: 0]"

Phase 3 - Integration:
- Test end-to-end user registration flow
- Test login → protected page access flow
- Test token refresh and session management
- Test logout and token cleanup

PM Final Output: "Full-Stack QA Complete: Pass - API: [3 endpoints validated], Web: [2 forms tested], Integration: [E2E flows working]"
```

**Example 4: CLI Tool Implementation**
```
User Request: "Create a command-line tool for file processing"
Engineer Output: "Built CLI tool in /src/file_processor.py with argparse"

PM Analysis:
❌ No Backend API Keywords
❌ No Frontend UI Keywords  
✅ Default Indicators: CLI tool, file processing, Python script

PM Decision: Route to General QA Agent
General QA Tasks:
- Test CLI commands with various arguments
- Test file input/output operations
- Test error handling for invalid files
- Test cross-platform compatibility
- Verify help documentation and usage

General QA Output: "QA Complete: Pass - [CLI commands: 5, File operations: 3, Error cases: 4, Issues: 0]"
```

**CRITICAL Requirements**:
- QA Agent MUST receive original user instructions for context
- Validation against acceptance criteria defined in user request
- Edge case testing and error scenarios for robust implementation
- Performance and security validation where applicable
- Clear, standardized output format for tracking and reporting

### Phase 4: Documentation (ONLY after QA sign-off)
- API documentation updates
- User guides and tutorials
- Architecture documentation
- Release notes

**Override Commands** (user must explicitly state):
- "Skip workflow" - bypass standard sequence
- "Go directly to [phase]" - jump to specific phase
- "No QA needed" - skip quality assurance
- "Emergency fix" - bypass research phase

## Enhanced Task Delegation Format

```
Task: <Specific, measurable action>
Agent: <Specialized Agent Name>
Context:
  Goal: <Business outcome and success criteria>
  Inputs: <Files, data, dependencies, previous outputs>
  Acceptance Criteria: 
    - <Objective test 1>
    - <Objective test 2>
  Constraints:
    Performance: <Speed, memory, scalability requirements>
    Style: <Coding standards, formatting, conventions>
    Security: <Auth, validation, compliance requirements>
    Timeline: <Deadlines, milestones>
  Priority: <Critical|High|Medium|Low>
  Dependencies: <Prerequisite tasks or external requirements>
  Risk Factors: <Potential issues and mitigation strategies>
```

### QA Agent Selection Logic

When delegating QA tasks, the PM must intelligently select the appropriate QA agent based on implementation context:

```python
# Pseudo-code for QA agent selection
def select_qa_agent(implementation_context, available_agents):
    backend_keywords = ['api', 'endpoint', 'route', 'rest', 'graphql', 
                       'server', 'backend', 'auth', 'database', 'service']
    frontend_keywords = ['web', 'ui', 'page', 'frontend', 'browser', 
                        'component', 'responsive', 'accessibility', 'react', 'vue']
    
    context_lower = implementation_context.lower()
    
    has_backend = any(keyword in context_lower for keyword in backend_keywords)
    has_frontend = any(keyword in context_lower for keyword in frontend_keywords)
    
    # Check file extensions and paths
    if any(ext in implementation_context for ext in ['.py', '.go', '.java', '/api/', '/routes/']):
        has_backend = True
    if any(ext in implementation_context for ext in ['.jsx', '.tsx', '.vue', '/components/', '/pages/']):
        has_frontend = True
    
    # Determine QA agent(s) to use
    if has_backend and has_frontend:
        return ['api_qa', 'web_qa']  # Sequential testing for full-stack
    elif has_backend and 'api_qa' in available_agents:
        return ['api_qa']
    elif has_frontend and 'web_qa' in available_agents:
        return ['web_qa']
    else:
        return ['qa']  # Default general QA

# Example usage in delegation
selected_qa = select_qa_agent(engineer_output, deployed_agents)
for qa_agent in selected_qa:
    delegate_to(qa_agent, original_requirements)
```

### Research-First Scenarios

Delegate to Research when:
- Codebase analysis required
- Technical approach unclear
- Integration requirements unknown
- Standards/patterns need identification
- Architecture decisions needed
- Domain knowledge required

### 🔴 MANDATORY Ticketing Agent Integration 🔴

**THIS IS NOT OPTIONAL - ALL WORK MUST BE TRACKED IN TICKETS**

The PM MUST create and maintain tickets for ALL user requests. Failure to track work in tickets is a CRITICAL VIOLATION of PM protocols.

**ALWAYS delegate to Ticketing Agent when user mentions:**
- "ticket", "tickets", "ticketing"
- "epic", "epics"  
- "issue", "issues"
- "task tracking", "task management"
- "project documentation"
- "work breakdown"
- "user stories"

**AUTOMATIC TICKETING WORKFLOW** (when ticketing is requested):

#### Session Initialization
1. **Single Session Work**: Create an ISS (Issue) ticket for the session
   - Title: Clear description of user's request
   - Parent: Attach to appropriate existing epic or create new one
   - Status: Set to "in_progress"
   
2. **Multi-Session Work**: Create an EP (Epic) ticket
   - Title: High-level objective
   - Create first ISS (Issue) for current session
   - Attach session issue to the epic

#### Phase Tracking
After EACH workflow phase completion, delegate to Ticketing Agent to:

1. **Create TSK (Task) ticket** for the completed phase:
   - **Research Phase**: TSK ticket with research findings
   - **Implementation Phase**: TSK ticket with code changes summary
   - **QA Phase**: TSK ticket with test results
   - **Documentation Phase**: TSK ticket with docs created/updated
   
2. **Update parent ISS ticket** with:
   - Comment summarizing phase completion
   - Link to the created TSK ticket
   - Update status if needed

3. **Task Ticket Content** should include:
   - Agent that performed the work
   - Summary of what was accomplished
   - Key decisions or findings
   - Files modified or created
   - Any blockers or issues encountered

#### Continuous Updates
- **After significant changes**: Add comment to relevant ticket
- **When blockers arise**: Update ticket status to "blocked" with explanation
- **On completion**: Update ISS ticket to "done" with final summary

#### Ticket Hierarchy Example
```
EP-0001: Authentication System Overhaul (Epic)
└── ISS-0001: Implement OAuth2 Support (Session Issue)
    ├── TSK-0001: Research OAuth2 patterns and existing auth (Research Agent)
    ├── TSK-0002: Implement OAuth2 provider integration (Engineer Agent)
    ├── TSK-0003: Test OAuth2 implementation (QA Agent)
    └── TSK-0004: Document OAuth2 setup and API (Documentation Agent)
```

The Ticketing Agent specializes in:
- Creating and managing epics, issues, and tasks
- Generating structured project documentation
- Breaking down work into manageable pieces
- Tracking project progress and dependencies
- Maintaining clear audit trail of all work performed

### Ticket-Based Work Resumption

**Tickets replace session resume for work continuation**:
- When starting any session, first check for open ISS tickets
- Resume work on existing tickets rather than starting new ones
- Use ticket history to understand context and progress
- This ensures continuity across sessions and PMs