# Local Agents User Guide

Learn how to create, manage, and deploy local agents to customize your Claude MPM experience with project-specific AI assistants.

## What are Local Agents?

Local agents are custom AI assistants that you create and manage locally within your projects. Unlike system agents that come with Claude MPM, local agents are:

- **Project-specific**: Tailored to your specific codebase and workflows
- **Version-controlled**: Stored as JSON templates you can track in git
- **Priority-driven**: Override system agents with the same name
- **Shareable**: Export and import between projects and teams

### Key Benefits

- **Custom Expertise**: Create agents specialized for your domain or technology stack
- **Project Context**: Agents that understand your specific coding conventions and patterns
- **Team Consistency**: Share standardized agents across your development team
- **Rapid Iteration**: Quickly test and refine agent behavior without system changes

## Getting Started

### Quick Setup

1. **Create your first local agent:**
   ```bash
   claude-mpm agent-manager create-local --agent-id my-researcher --name "My Research Assistant" --description "Custom research agent for this project"
   ```

2. **Deploy the agent:**
   ```bash
   claude-mpm agent-manager deploy-local --agent-id my-researcher
   ```

3. **Use your agent:**
   ```bash
   claude-mpm run --agent my-researcher
   ```

### Directory Structure

Local agents are stored in `.claude-mpm/agents/` as JSON templates:

```
your-project/
├── .claude-mpm/
│   └── agents/
│       ├── custom-researcher.json
│       ├── domain-expert.json
│       └── versions/
│           └── custom-researcher/
│               └── 1.0.0.json
└── ...
```

## Creating Local Agents

### Interactive Creation

Create an agent interactively with guided prompts:

```bash
claude-mpm agent-manager create-local
```

You'll be prompted for:
- Agent ID (unique identifier)
- Display name
- Description
- Instructions/behavior
- Model preference (opus, sonnet, haiku)
- Tool access settings

### Command-Line Creation

Create an agent with all parameters specified:

```bash
claude-mpm agent-manager create-local \
  --agent-id domain-expert \
  --name "Domain Expert" \
  --description "Expert in our specific business domain" \
  --instructions "You are an expert in financial modeling and risk analysis..." \
  --model sonnet \
  --tools "*"
```

### From System Agent Template

Create a local agent based on an existing system agent:

```bash
claude-mpm agent-manager create-local \
  --agent-id custom-researcher \
  --parent research \
  --name "Custom Research Assistant" \
  --instructions "Like the research agent, but with additional focus on our industry..."
```

## Agent Configuration

### Template Structure

Local agent templates are JSON files with this structure:

```json
{
  "schema_version": "1.3.0",
  "agent_id": "custom-researcher",
  "agent_version": "1.0.0",
  "author": "my-project",
  "agent_type": "custom-researcher",
  "metadata": {
    "name": "Custom Research Assistant",
    "description": "Specialized research agent for financial analysis",
    "tier": "project",
    "tags": ["local", "custom", "finance"],
    "specializations": ["financial-modeling", "risk-analysis"]
  },
  "capabilities": {
    "model": "sonnet",
    "tools": "*"
  },
  "instructions": "You are a specialized research assistant with expertise in...",
  "configuration": {
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "priority": 2000,
  "parent_agent": "research"
}
```

### Key Fields

**Required Fields:**
- `agent_id`: Unique identifier for your agent
- `metadata.name`: Human-readable display name
- `instructions`: Core behavior and expertise definition

**Configuration Fields:**
- `capabilities.model`: AI model to use (opus/sonnet/haiku)
- `capabilities.tools`: Tool access ("*" for all, or specific tools)
- `configuration.temperature`: Response creativity (0.0-1.0)
- `priority`: Override priority (higher = higher priority)

**Inheritance:**
- `parent_agent`: Inherit from system agent as base template

## Priority System

Local agents follow a strict priority hierarchy:

1. **Project Agents** (Priority: 2000+)
   - Stored in `.claude-mpm/agents/`
   - Highest priority, overrides all others
   - Project-specific customizations

2. **User Agents** (Priority: 1500+)
   - Stored in `~/.claude-mpm/agents/`
   - Personal agent preferences
   - Available across all projects

3. **System Agents** (Priority: 1000)
   - Built into Claude MPM
   - Default framework agents

### Priority Examples

If you have:
- System agent: `research` (priority 1000)
- User agent: `research` (priority 1500)  
- Project agent: `research` (priority 2000)

Running `claude-mpm run --agent research` will use the project agent.

## Managing Local Agents

### List All Agents

See your local agents alongside system agents:

```bash
# List all agents with tier indicators
claude-mpm agent-manager list

# List only local agents
claude-mpm agent-manager list-local

# List project agents only
claude-mpm agent-manager list-local --tier project
```

Output shows the priority hierarchy:

```
=== Agent Hierarchy ===

[P] PROJECT LEVEL (Highest Priority)
    custom-researcher    - Custom Research Assistant [LOCAL-PROJECT]
    domain-expert        - Domain Expert [LOCAL-PROJECT]

[U] USER LEVEL
    my-analyzer          - Personal Analyzer [LOCAL-USER]

[S] SYSTEM LEVEL (Framework Defaults)
    research             - Research Assistant
    pm                   - Project Manager
```

### View Agent Details

```bash
# Show agent configuration
claude-mpm agent-manager show custom-researcher

# View local agent template
cat .claude-mpm/agents/custom-researcher.json
```

### Update Agent Instructions

Edit the JSON file directly or recreate:

```bash
# Edit manually
nano .claude-mpm/agents/custom-researcher.json

# Or recreate with new settings
claude-mpm agent-manager create-local \
  --agent-id custom-researcher \
  --instructions "Updated instructions..."
```

After changes, redeploy:

```bash
claude-mpm agent-manager deploy-local --agent-id custom-researcher --force
```

## Deployment and Synchronization

### Deploy Single Agent

Deploy a specific local agent:

```bash
# Deploy specific agent
claude-mpm agent-manager deploy-local --agent-id custom-researcher

# Force redeploy (overwrite existing)
claude-mpm agent-manager deploy-local --agent-id custom-researcher --force
```

### Deploy All Local Agents

Deploy all local agents at once:

```bash
# Deploy all local agents
claude-mpm agent-manager deploy-local

# Deploy only project-tier agents
claude-mpm agent-manager deploy-local --tier project

# Force redeploy all
claude-mpm agent-manager deploy-local --force
```

### Synchronization

Keep local templates in sync with deployed agents:

```bash
# Sync templates with deployed agents
claude-mpm agent-manager sync-local
```

This command:
- Adds missing templates for deployed local agents
- Updates templates that have changed
- Removes templates for agents no longer deployed

## Sharing and Team Collaboration

### Export Local Agents

Export agents for sharing with your team:

```bash
# Export all local agents to a directory
claude-mpm agent-manager export-local --output ./shared-agents

# Export creates individual JSON files
ls ./shared-agents/
# custom-researcher.json
# domain-expert.json
```

### Import Local Agents

Import agents from a shared directory:

```bash
# Import as project agents (default)
claude-mpm agent-manager import-local --input ./shared-agents

# Import as user agents
claude-mpm agent-manager import-local --input ./shared-agents --tier user
```

### Version Control Integration

**Recommended approach for team projects:**

```bash
# Include local agents in git
git add .claude-mpm/agents/
git commit -m "Add custom research agent for financial analysis"
```

**For personal agents, use gitignore:**

```bash
# In .gitignore
.claude-mpm/agents/personal-*
```

## Common Use Cases

### 1. Domain Expert Agent

Create an agent with deep knowledge of your business domain:

```json
{
  "agent_id": "finance-expert",
  "metadata": {
    "name": "Financial Analysis Expert",
    "description": "Expert in financial modeling, risk analysis, and regulatory compliance"
  },
  "instructions": "You are a senior financial analyst with 15 years of experience in investment banking. You specialize in financial modeling, risk analysis, DCF valuations, and regulatory compliance. When analyzing code or documents, focus on:\n- Financial accuracy and best practices\n- Regulatory compliance considerations\n- Risk assessment and mitigation\n- Performance and scalability for financial calculations"
}
```

### 2. Technology Stack Specialist

Create an agent specialized in your tech stack:

```json
{
  "agent_id": "react-specialist",
  "metadata": {
    "name": "React/TypeScript Specialist",
    "specializations": ["react", "typescript", "nextjs"]
  },
  "instructions": "You are a React and TypeScript expert specializing in modern web development. Focus on:\n- React best practices and hooks\n- TypeScript type safety\n- Next.js optimization\n- Performance and accessibility\n- Testing with Jest and React Testing Library"
}
```

### 3. Code Review Assistant

Create an agent focused on code quality:

```json
{
  "agent_id": "code-reviewer",
  "metadata": {
    "name": "Senior Code Reviewer",
    "description": "Thorough code review with focus on our coding standards"
  },
  "instructions": "You are a senior engineer conducting code reviews. Focus on:\n- Architecture and design patterns\n- Performance implications\n- Security considerations\n- Maintainability and readability\n- Testing coverage\n- Our specific coding standards (follow the conventions in our .eslintrc and style guide)"
}
```

### 4. Documentation Generator

Create an agent specialized in documentation:

```json
{
  "agent_id": "doc-writer",
  "parent_agent": "documentation",
  "metadata": {
    "name": "Technical Writer",
    "description": "Generates comprehensive documentation following our standards"
  },
  "instructions": "You are a technical writer creating documentation for our software projects. Follow our documentation standards:\n- Use our standard template format\n- Include practical examples\n- Write for both technical and non-technical audiences\n- Ensure all APIs are documented with parameters and return values\n- Include troubleshooting sections"
}
```

## Troubleshooting

### Common Issues

**Agent not found after creation:**
```bash
# Check if template was created
ls .claude-mpm/agents/

# Deploy the agent
claude-mpm agent-manager deploy-local --agent-id your-agent-id
```

**Agent using wrong version:**
```bash
# Check agent hierarchy
claude-mpm agent-manager list

# Force redeploy to update
claude-mpm agent-manager deploy-local --agent-id your-agent-id --force
```

**Template validation errors:**
```bash
# Test agent configuration
claude-mpm agent-manager test your-agent-id

# Common fixes:
# - Ensure agent_id is lowercase with hyphens only
# - Add required metadata.name field
# - Provide non-empty instructions
```

### Debugging Agent Behavior

**Test agent with simple query:**
```bash
claude-mpm run --agent your-agent-id "What is your expertise?"
```

**Check agent instructions are loaded:**
```bash
claude-mpm agent-manager show your-agent-id --format json
```

**Verify priority resolution:**
```bash
claude-mpm agent-manager list | grep your-agent-id
```

### Clean Up and Reset

**Remove all local agents:**
```bash
rm -rf .claude-mpm/agents/
```

**Remove specific agent:**
```bash
rm .claude-mpm/agents/agent-name.json
```

**Reset deployed agents:**
```bash
claude-mpm agent-manager sync-local
```

## Best Practices

### Agent Design
- **Single Responsibility**: Focus each agent on one domain or type of task
- **Clear Instructions**: Be specific about the agent's expertise and approach
- **Appropriate Model**: Use `opus` for complex reasoning, `sonnet` for balanced tasks, `haiku` for fast responses
- **Tool Restrictions**: Limit tools to what the agent actually needs

### Naming Conventions
- Use descriptive, lowercase IDs with hyphens: `financial-analyst`, `react-reviewer`
- Avoid generic names that conflict with system agents
- Include your domain or project prefix for clarity: `myapp-tester`

### Version Management
- Use semantic versioning for agent versions
- Document changes in agent descriptions or comments
- Keep versioned backups for important agents

### Team Collaboration
- Store project agents in git for team sharing
- Use consistent naming conventions across the team
- Document agent purposes and use cases in README
- Regular reviews of agent effectiveness and updates

### Performance Optimization
- Set appropriate temperature values (0.3-0.5 for factual, 0.7-0.9 for creative)
- Limit max_tokens based on typical use cases
- Use parent_agent inheritance to reduce duplication

This comprehensive system allows you to create a powerful, customized AI assistance experience tailored specifically to your project's needs while maintaining compatibility with the broader Claude MPM ecosystem.