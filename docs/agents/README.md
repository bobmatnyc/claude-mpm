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
- **[Agentic Coder Optimizer](AGENTIC_CODER_OPTIMIZER.md)** ⭐ **NEW** - Transform projects for AI agents with "ONE way to do ANYTHING"
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

## Featured Agent: Agentic Coder Optimizer 🎆

### Overview  
The **[Agentic Coder Optimizer](AGENTIC_CODER_OPTIMIZER.md)** is a breakthrough operations agent that transforms projects for optimal AI agent compatibility. Following the principle of **"ONE way to do ANYTHING,"** it eliminates complexity and creates discoverable, unified workflows.

### Key Transformations
- **⚡ 5-Minute Setup**: Reduces onboarding from hours to minutes
- **🎯 Unified Commands**: `make dev`, `make test`, `make build` work on ANY project
- **📚 Smart Documentation**: Creates discoverable hierarchy (README → CLAUDE → DEVELOPER)
- **🔧 Quality Gates**: Automated formatting, testing, and security checks
- **🤖 AI-Optimized**: Structure and language optimized for AI agent understanding

### Real Impact Examples
**React SaaS Project:**
- Setup time: 3.5 hours → 4 minutes (90% reduction)
- Test commands: 12 different ways → `make test` (100% consistency)
- Developer satisfaction: 95% "Much easier to contribute"

**Legacy Python API:**
- Consolidated 15 shell scripts into 5 `make` commands
- Documentation: 3-page wiki → single DEVELOPER.md
- New developer productivity: Day 1 instead of Week 1

### Quick Start
```bash
# Transform any project for agentic coding
PM: "Run the Agentic Coder Optimizer - implement ONE way to do everything"

# Focus on specific optimization
PM: "Create unified commands and 5-minute developer setup"

# Full project health analysis
PM: "Analyze optimization opportunities and show before/after impact"
```

### When to Use
- 🆕 **New Projects**: Set agentic standards from day one
- 🔄 **Legacy Modernization**: Consolidate complex, scattered tooling  
- 📚 **Documentation Chaos**: Create clear, discoverable information hierarchy
- 👥 **Team Onboarding**: Reduce setup time and improve developer experience
- 🤖 **AI Agent Workflows**: Optimize project structure for AI agent effectiveness

---

## Also Featured: Vercel Ops

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

### Agentic Coder Optimizer Documentation
- **[Overview & Philosophy](AGENTIC_CODER_OPTIMIZER.md#core-philosophy-one-way-to-do-anything)** - The "ONE way" principle
- **[Real-World Examples](AGENTIC_CODER_OPTIMIZER.md#real-world-usage-examples)** - React, Python, monorepo transformations
- **[Success Metrics](AGENTIC_CODER_OPTIMIZER.md#success-metrics-and-measurement)** - Measurable optimization impact
- **[Quick Reference](AGENTIC_CODER_OPTIMIZER.md#quick-reference-guide)** - Essential commands and patterns
- **[PM Integration](AGENTIC_CODER_OPTIMIZER.md#integration-with-pm-workflow)** - Multi-agent coordination

### Vercel Ops Documentation
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
# Project optimization → Agentic Coder Optimizer
PM: "Standardize this project for AI agents with unified commands"

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
Agents coordinate seamlessly through the PM workflow, with the Agentic Coder Optimizer often setting the foundation:

```
Agentic Coder Optimizer → Engineer → Vercel Ops → QA → Documentation
         ↓                   ↓           ↓         ↓         ↓
   Optimize Structure     Feature    Deployment  Testing   Update Docs
   Create Commands      Complete    to Preview  Preview   with Changes
   Set Quality Gates
```

### Multi-Agent Workflows
Complex tasks involve multiple agents working together, often starting with optimization:

#### New Feature with Optimization
```
1. Agentic Coder Optimizer: Ensure project has unified commands and quality gates
2. Engineer: Implement new payment feature using standard workflow (make test, make quality)
3. Security: Review payment security implementation
4. Vercel Ops: Deploy to preview with payment API integration  
5. QA: Test payment flows using unified test commands (make test, make test-e2e)
6. Documentation: Update payment guide in optimized documentation structure
7. Vercel Ops: Deploy to production with rolling release
```

#### Legacy Project Modernization  
```
1. Agentic Coder Optimizer: Transform project structure and create unified workflows
2. Engineer: Migrate features to new structure while maintaining functionality
3. QA: Validate all existing functionality works with new commands
4. Documentation: Update all guides to reflect optimized structure
5. Ops: Deploy using new unified deployment process
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
- **[Main Agent Guide](AGENTS.md)** - Comprehensive agent system documentation
- **[Agent Creation Guide](../developer/07-agent-system/creation-guide.md)** - Create custom agents
- **[Agent Schema Reference](../developer/10-schemas/agent_schema_documentation.md)** - Agent configuration schema
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
3. Add agent to main [AGENTS.md](AGENTS.md) if applicable
4. Test all examples and procedures
5. Review for consistency with existing documentation

### Updating Existing Documentation
1. Keep documentation current with agent capabilities
2. Add new examples and use cases as they emerge
3. Update troubleshooting sections based on user feedback
4. Maintain consistency across all agent documentation
5. Update cross-references when structure changes

This catalog serves as the central hub for all agent documentation in the Claude MPM framework, providing teams with the resources they need to effectively utilize specialized agents for their development and operations workflows.