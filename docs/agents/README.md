# Claude MPM Agents Catalog

This directory contains comprehensive documentation for all specialized agents available in the Claude MPM framework. Each agent is designed for specific domains and workflows, providing expert-level assistance for development, operations, and project management tasks.

## Available Agents

### Core Development Agents
- **[Engineer](../AGENTS.md#core-development)** - Software development and implementation
- **[Research](../AGENTS.md#core-development)** - Code analysis and research  
- **[Documentation](../AGENTS.md#core-development)** - Documentation creation and maintenance
- **[QA](../AGENTS.md#core-development)** - Testing and quality assurance
- **[Security](../AGENTS.md#core-development)** - Security analysis and implementation

### Operations & Infrastructure Agents
- **[Ops](../AGENTS.md#operations--infrastructure)** - Operations and deployment
- **[Vercel Ops](VERCEL_OPS_AGENT.md)** - Vercel platform deployment and optimization
- **[Version Control](../AGENTS.md#operations--infrastructure)** - Git and version management
- **[Data Engineer](../AGENTS.md#operations--infrastructure)** - Data pipeline and ETL development

### Web Development Agents
- **[Web UI](../AGENTS.md#web-development)** - Frontend and UI development
- **[Web QA](../AGENTS.md#web-development)** - Web testing and E2E validation

### Project Management Agents
- **[Ticketing](../AGENTS.md#project-management)** - Issue tracking and management
- **[Project Organizer](../AGENTS.md#project-management)** - File organization and structure
- **[Memory Manager](../AGENTS.md#project-management)** - Project memory and context management

### Code Quality Agents
- **[Refactoring Engineer](../AGENTS.md#code-quality)** - Code refactoring and optimization
- **[Code Analyzer](../AGENTS.md#code-quality)** - Static code analysis with AST and tree-sitter

## Featured Agent: Vercel Ops

### Overview
The **[Vercel Ops Agent](VERCEL_OPS_AGENT.md)** is a specialized operations agent designed for comprehensive Vercel platform management. It provides expert-level deployment, environment management, and optimization capabilities for modern serverless applications.

### Key Capabilities
- **Deployment Management**: Preview deployments, production releases, and rolling releases
- **Environment Configuration**: Multi-environment variable management and isolation
- **Performance Optimization**: Edge functions, serverless optimization, and caching strategies
- **Domain Management**: Custom domains with automatic SSL certificate provisioning
- **Monitoring & Analytics**: Performance tracking, error monitoring, and Core Web Vitals
- **Security**: Security headers, CORS configuration, and best practices
- **CI/CD Integration**: GitHub Actions workflows and automated deployments

### Supported Frameworks
- Next.js, React, Vue, Svelte, Angular
- Nuxt, Gatsby, Remix, Astro, SolidStart, Qwik

### Quick Start
```bash
# Deploy to preview
PM: "Deploy feature branch to Vercel for testing"

# Production deployment
PM: "Deploy v2.0 to production with rolling release"

# Environment setup
PM: "Configure staging environment with custom domain"
```

### Documentation Sections
- **[Getting Started](VERCEL_OPS_AGENT.md#getting-started)** - Prerequisites and quick setup
- **[Core Features](VERCEL_OPS_AGENT.md#core-features)** - Deployment, environment management, optimization
- **[Usage Examples](VERCEL_OPS_AGENT.md#usage-examples)** - Real-world deployment scenarios
- **[Configuration Guide](VERCEL_OPS_AGENT.md#configuration-guide)** - vercel.json, security, and optimization
- **[Integration](VERCEL_OPS_AGENT.md#integration-with-pm-workflow)** - PM workflow and agent coordination
- **[Best Practices](VERCEL_OPS_AGENT.md#best-practices)** - Security, performance, and team collaboration
- **[Troubleshooting](VERCEL_OPS_AGENT.md#troubleshooting)** - Common issues and solutions

## Agent Documentation Structure

Each agent documentation follows a consistent structure:

### Standard Sections
1. **Overview** - Agent purpose and capabilities
2. **Getting Started** - Prerequisites and setup
3. **Core Features** - Main functionalities and tools
4. **Usage Examples** - Practical implementation scenarios
5. **Configuration** - Setup and customization options
6. **Integration** - PM workflow and agent coordination
7. **Best Practices** - Security, performance, and standards
8. **Troubleshooting** - Common issues and solutions
9. **Reference** - Commands, APIs, and technical details

### Documentation Standards
- **Clear Navigation** - Table of contents and cross-references
- **Practical Examples** - Real-world code snippets and scenarios
- **Step-by-Step Guides** - Detailed procedures for common tasks
- **Troubleshooting** - Common issues with solutions
- **Best Practices** - Security, performance, and team guidelines
- **Reference Materials** - Commands, configurations, and APIs

## Using Agents in Claude MPM

### Agent Selection
The PM automatically selects the most appropriate agent based on task requirements:

```bash
# Engineering tasks → Engineer Agent
PM: "Add user authentication to the application"

# Deployment tasks → Vercel Ops Agent  
PM: "Deploy the application to Vercel with custom domain"

# Testing tasks → QA Agent
PM: "Run comprehensive tests on the preview deployment"

# Documentation tasks → Documentation Agent
PM: "Update the API documentation with new endpoints"
```

### Agent Coordination
Agents coordinate seamlessly through the PM workflow:

```
Engineer → Vercel Ops → QA → Documentation
   ↓           ↓         ↓         ↓
Feature    Deployment  Testing   Update Docs
Complete   to Preview  Preview   with Changes
```

### Multi-Agent Workflows
Complex tasks involve multiple agents working together:

```
1. Engineer: Implement new payment feature
2. Security: Review payment security implementation
3. Vercel Ops: Deploy to preview with payment API integration
4. QA: Test payment flows in preview environment
5. Vercel Ops: Deploy to production with rolling release
6. Documentation: Update payment integration guide
```

## Agent Customization

### Project-Level Agents
Create project-specific agents in `.claude-mpm/agents/`:

```bash
# Create project directory
mkdir -p .claude-mpm/agents

# Add custom Vercel Ops configuration
cat > .claude-mpm/agents/vercel_ops.json << 'EOF'
{
  "agent_id": "vercel_ops",
  "version": "2.0.0",
  "metadata": {
    "description": "Custom Vercel Ops for this project"
  },
  "knowledge": {
    "project_domains": ["app.mycompany.com", "staging.mycompany.com"],
    "environments": ["development", "staging", "production"],
    "frameworks": ["nextjs"],
    "integrations": ["auth0", "stripe", "sendgrid"]
  },
  "instructions": "# Project Vercel Ops\n\nCustom configuration for MyCompany application deployment..."
}
EOF
```

### Agent Precedence
Project agents override system agents:
- **PROJECT** (`.claude-mpm/agents/`) - Highest precedence
- **USER** (`~/.claude-mpm/agents/`) - Medium precedence  
- **SYSTEM** (Built-in framework agents) - Lowest precedence

## Getting Help

### Documentation Resources
- **[Main Agent Guide](../AGENTS.md)** - Comprehensive agent system documentation
- **[Agent Creation Guide](../developer/07-agent-system/creation-guide.md)** - Create custom agents
- **[Agent Schema Reference](../developer/07-agent-system/schema.md)** - Agent configuration schema
- **[Agent Frontmatter Guide](../developer/07-agent-system/frontmatter.md)** - Configuration fields

### CLI Commands
```bash
# List all agents by tier
claude-mpm agents list --by-tier

# View specific agent details
claude-mpm agents view vercel_ops

# Fix agent configuration issues
claude-mpm agents fix --all --dry-run
```

### Support
- **Framework Documentation**: [docs/README.md](../README.md)
- **Issue Tracking**: GitHub Issues
- **Community**: GitHub Discussions

---

## Contributing to Agent Documentation

### Documentation Standards
1. **Follow the standard structure** outlined above
2. **Include practical examples** for all major features
3. **Provide troubleshooting guidance** for common issues
4. **Use consistent formatting** and terminology
5. **Cross-reference related documentation** when appropriate

### Adding New Agents
1. Create comprehensive documentation following the template
2. Update this catalog with agent entry
3. Add agent to main [AGENTS.md](../AGENTS.md) if applicable
4. Test all examples and procedures
5. Review for consistency with existing documentation

### Updating Existing Documentation
1. Keep documentation current with agent capabilities
2. Add new examples and use cases as they emerge
3. Update troubleshooting sections based on user feedback
4. Maintain consistency across all agent documentation
5. Update cross-references when structure changes

This catalog serves as the central hub for all agent documentation in the Claude MPM framework, providing teams with the resources they need to effectively utilize specialized agents for their development and operations workflows.