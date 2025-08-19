# Intelligent QA Routing Guide

## Overview of Specialized QA Testing

Claude MPM's PM workflow features intelligent QA routing that automatically selects the most appropriate QA agent based on implementation context. This ensures specialized testing that matches the technical domain while maintaining comprehensive coverage across all aspects of the application.

### Key Benefits

- **Specialized Expertise**: Each QA agent focuses on their area of expertise (APIs, Web UI, or General testing)
- **Comprehensive Coverage**: Full-stack features receive testing at all appropriate layers
- **Efficient Resource Use**: Right tool for the right testing job reduces redundancy
- **Consistent Quality**: Standardized testing approaches and output formats
- **Intelligent Automation**: PM automatically routes based on implementation context

## When to Use Each QA Agent

### API QA Agent

**Primary Use Cases**:
- REST API endpoints and GraphQL services
- Authentication and authorization systems
- Database operations and data validation
- Microservices and inter-service communication
- API performance and load testing
- Backend security validation

**When PM Routes to API QA**:
- Implementation includes server-side code or API endpoints
- Backend keywords detected (api, endpoint, route, rest, graphql, server, backend, auth, database)
- Backend file structures found (/api/, /routes/, /controllers/, /services/)
- Server-side technologies identified (.py, .js/.ts server, .go, .java, .php, .rb)

**Example Scenarios**:
```
✅ "Create user management REST API with JWT authentication"
✅ "Implement GraphQL schema for product catalog"
✅ "Add OAuth2 integration for third-party login"
✅ "Build microservice for payment processing"
✅ "Create database migration for user roles"
```

### Web QA Agent

**Primary Use Cases**:
- User interface components and page layouts
- Browser compatibility and responsive design
- User experience and interaction flows
- Accessibility compliance (WCAG standards)
- Client-side performance optimization
- Progressive Web App (PWA) features

**When PM Routes to Web QA**:
- Implementation includes frontend UI components or pages
- Frontend keywords detected (web, ui, page, frontend, browser, component, responsive, accessibility)
- Frontend file structures found (/components/, /pages/, /views/, /public/)
- Client-side technologies identified (.jsx/.tsx, .vue, .svelte, .html, .css/.scss)

**Example Scenarios**:
```
✅ "Build responsive dashboard with interactive charts"
✅ "Create user registration form with validation"
✅ "Implement dark mode toggle for the application"
✅ "Add accessibility features for screen readers"
✅ "Optimize Core Web Vitals for better performance"
```

### General QA Agent

**Primary Use Cases**:
- Command-line tools and utilities
- Libraries and reusable components
- Configuration and build systems
- Data processing and algorithms
- Integration testing across multiple systems
- Legacy systems without specific UI/API focus

**When PM Routes to General QA**:
- No specific API or Web indicators detected
- CLI tools, libraries, or utility implementations
- Configuration files and build scripts
- Pure logic or algorithm implementations
- Cross-platform compatibility requirements

**Example Scenarios**:
```
✅ "Create CLI tool for database migrations"
✅ "Implement utility library for data parsing"
✅ "Build configuration management system"
✅ "Create automated deployment scripts"
✅ "Implement data processing algorithms"
```

## Full-Stack Testing Coordination

### Sequential Testing Process

When a feature spans both backend and frontend implementations, the PM coordinates **sequential testing** to ensure comprehensive validation:

1. **API QA Phase** (First)
   - Validates backend functionality and data flows
   - Tests API endpoints, authentication, and business logic
   - Ensures data consistency and security measures
   - Must complete successfully before proceeding

2. **Web QA Phase** (Second)
   - Tests frontend integration with validated backend
   - Validates user experience and interface functionality
   - Tests client-side interactions and responsiveness
   - Verifies proper error handling and user feedback

3. **Integration Validation** (Final)
   - End-to-end user workflow testing
   - Data flow validation across all layers
   - Performance testing under realistic conditions
   - Cross-browser and cross-device validation

### Full-Stack Examples

**Example: E-commerce Checkout System**
```
User Request: "Implement complete checkout flow with payment processing"

Implementation: 
- Backend: Payment API endpoints, order processing, inventory management
- Frontend: Shopping cart UI, checkout forms, payment integration

QA Coordination:
1. API QA Tests:
   ✓ POST /cart/add endpoint validation
   ✓ POST /checkout/process payment flow
   ✓ GET /orders/{id} order retrieval
   ✓ Payment gateway integration security
   ✓ Inventory decrement verification

2. Web QA Tests:
   ✓ Shopping cart UI interactions
   ✓ Checkout form validation and UX
   ✓ Payment form security and accessibility
   ✓ Order confirmation page display
   ✓ Mobile responsive checkout flow

3. Integration Tests:
   ✓ Complete user purchase journey
   ✓ Payment success/failure scenarios
   ✓ Inventory synchronization
   ✓ Email notification integration
```

## Configuration and Customization

### Agent Configuration

Each QA agent can be configured for specific project requirements:

**API QA Agent Configuration**:
```json
{
  "name": "api_qa",
  "model": "sonnet",
  "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "TodoWrite", "WebFetch"],
  "capabilities": {
    "api_testing": ["REST", "GraphQL", "WebSocket"],
    "auth_testing": ["JWT", "OAuth2", "API_Keys"],
    "performance_testing": true,
    "security_testing": true
  },
  "output_format": "API QA Complete: [Pass/Fail] - [Endpoints: X, Response time: Xms, Security: X, Issues: X]"
}
```

**Web QA Agent Configuration**:
```json
{
  "name": "web_qa", 
  "model": "sonnet",
  "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "TodoWrite", "WebFetch"],
  "capabilities": {
    "browser_testing": ["Chrome", "Firefox", "Safari", "Edge"],
    "responsive_testing": true,
    "accessibility_testing": true,
    "performance_testing": ["Core Web Vitals", "Lighthouse"]
  },
  "output_format": "Web QA Complete: [Pass/Fail] - [Browsers: X, Pages: X, Accessibility: X%, Performance: X%, Issues: X]"
}
```

### Custom Testing Requirements

Projects can customize QA requirements by defining specific criteria:

**Performance Benchmarks**:
```yaml
api_qa_requirements:
  response_time_max: "200ms"
  concurrent_users: 100
  error_rate_max: "0.1%"

web_qa_requirements:
  lighthouse_score_min: 90
  accessibility_score_min: 95
  core_web_vitals: "good"
```

**Security Standards**:
```yaml
security_requirements:
  owasp_compliance: true
  input_validation: "strict"
  auth_testing: "comprehensive"
  vulnerability_scanning: true
```

## Best Practices

### For Project Managers

1. **Context Analysis**: Always analyze implementation output for technical indicators before QA routing
2. **Clear Communication**: Pass original user requirements to QA agents for proper context
3. **Sequential Coordination**: For full-stack features, ensure API QA completes before Web QA begins
4. **Documentation**: Maintain clear records of QA decisions and routing rationale
5. **Feedback Integration**: Use QA results to improve future routing decisions

### For QA Agents

1. **Scope Adherence**: Stay within your specialized testing domain
2. **Comprehensive Coverage**: Test edge cases and error scenarios thoroughly
3. **Standard Reporting**: Use consistent output formats for tracking and comparison
4. **Integration Awareness**: Consider how your component interacts with other system parts
5. **Performance Focus**: Include performance metrics in all testing activities

### For Development Teams

1. **Clear Implementation**: Provide specific context about technologies and architectures used
2. **Documentation**: Include sufficient detail for QA agents to understand the implementation
3. **Test Data**: Provide realistic test data and scenarios for comprehensive testing
4. **Environment Setup**: Ensure QA environments match production configurations
5. **Collaboration**: Be available for clarification during QA processes

## Troubleshooting

### QA Agent Selection Issues

**Problem**: PM routes to wrong QA agent type
```
Solution: Check implementation context for missing keywords or file indicators
- Add explicit technology mentions (e.g., "FastAPI endpoints", "React components")
- Include file paths in implementation descriptions
- Specify both backend and frontend for full-stack features
```

**Problem**: No specialized QA agents available
```
Solution: Deploy required QA agents or use General QA as fallback
- Run: claude-mpm deploy api_qa
- Run: claude-mpm deploy web_qa  
- Verify: claude-mpm list-agents
```

### Test Environment Problems

**Problem**: QA tests fail due to environment issues
```
API QA Environment Issues:
- Check server is running and accessible
- Verify database connections and test data
- Confirm API endpoint URLs and authentication
- Test network connectivity and firewall rules

Web QA Environment Issues:
- Ensure frontend build is current and deployed
- Check browser driver installations and versions
- Verify test URLs and routing configurations
- Confirm responsive design test viewports
```

### Integration Test Failures

**Problem**: Individual QA passes but integration fails
```
Common Causes:
- API and frontend using different data formats
- Authentication tokens not properly shared
- Client-server state synchronization issues
- Network latency or timeout configurations

Resolution Steps:
1. Review API QA results for data contract validation
2. Check Web QA results for proper API integration
3. Test end-to-end data flow manually
4. Verify error handling across system boundaries
```

### Performance Bottlenecks

**Problem**: QA performance tests reveal issues
```
API Performance Issues:
- Database query optimization needed
- Caching strategies implementation
- Load balancing configuration
- Resource pooling adjustments

Web Performance Issues:
- Asset optimization (images, CSS, JS)
- Bundle size reduction and code splitting
- CDN configuration for static assets
- Browser caching strategy implementation
```

## Advanced Features

### Custom QA Workflows

Projects can define custom QA workflows for specific scenarios:

**Microservices Testing**:
```yaml
microservice_qa_workflow:
  1. api_qa: "Test individual service endpoints"
  2. integration_qa: "Test service-to-service communication"
  3. load_qa: "Test system under load"
  4. security_qa: "Test inter-service security"
```

**Mobile-First Development**:
```yaml
mobile_qa_workflow:
  1. api_qa: "Test mobile API optimizations"
  2. web_qa: "Test responsive mobile design"
  3. pwa_qa: "Test Progressive Web App features"
  4. performance_qa: "Test mobile network conditions"
```

### Continuous Integration

Integrate intelligent QA routing with CI/CD pipelines:

```yaml
# .github/workflows/qa-routing.yml
qa-routing:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Analyze Changes
      run: |
        # Detect changed files and technologies
        CHANGED_FILES=$(git diff --name-only HEAD~1)
        if echo "$CHANGED_FILES" | grep -E '\.(py|go|java)$|/api/|/routes/'; then
          echo "API_QA=true" >> $GITHUB_ENV
        fi
        if echo "$CHANGED_FILES" | grep -E '\.(jsx|tsx|vue)$|/components/|/pages/'; then
          echo "WEB_QA=true" >> $GITHUB_ENV
        fi
    
    - name: Run API QA
      if: env.API_QA == 'true'
      run: claude-mpm run api_qa
    
    - name: Run Web QA  
      if: env.WEB_QA == 'true'
      run: claude-mpm run web_qa
```

### Monitoring and Metrics

Track QA routing effectiveness:

```python
# QA Routing Metrics
qa_metrics = {
    "routing_accuracy": "95%",
    "avg_testing_time": {
        "api_qa": "8 minutes",
        "web_qa": "12 minutes", 
        "general_qa": "6 minutes"
    },
    "defect_detection_rate": {
        "api_qa": "89%",
        "web_qa": "92%",
        "integration": "94%"
    }
}
```

## Future Enhancements

### Planned Improvements

1. **Mobile QA Agent**: Specialized testing for native mobile applications
2. **Performance QA Agent**: Dedicated load and performance testing capabilities
3. **Security QA Agent**: Comprehensive penetration testing and vulnerability assessment
4. **Database QA Agent**: Specialized testing for database operations and migrations

### AI-Enhanced Routing

Future versions will include:
- Machine learning models for improved routing accuracy
- Historical project analysis for better context understanding
- Automated test case generation based on implementation patterns
- Predictive QA resource allocation

### Integration Expansions

Planned integrations:
- Popular testing frameworks (Jest, Cypress, Selenium, Postman)
- Cloud testing services (BrowserStack, Sauce Labs)
- Performance monitoring tools (Lighthouse CI, WebPageTest)
- Security scanning services (OWASP ZAP, Snyk)

---

## Getting Started

To begin using intelligent QA routing in your project:

1. **Deploy QA Agents**:
   ```bash
   claude-mpm deploy api_qa
   claude-mpm deploy web_qa
   ```

2. **Verify Configuration**:
   ```bash
   claude-mpm list-agents
   ```

3. **Test Routing**:
   Request implementation work and observe PM routing decisions

4. **Customize as Needed**:
   Adjust agent configurations for your project requirements

5. **Monitor Results**:
   Track QA effectiveness and routing accuracy over time

The intelligent QA routing system will automatically improve your development workflow by ensuring the right expertise is applied to the right testing challenges, resulting in higher quality software and more efficient development cycles.