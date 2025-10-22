# Agent Manager Implementation Task

Create a comprehensive Agent Manager system for building, customizing, and managing agents at all hierarchy levels (project, user, system).

## Requirements:

### 1. Agent Manager Template (src/claude_mpm/agents/templates/agent-manager.json):
Create JSON template with:
- id: 'agent-manager'
- name: 'Agent Manager'
- prompt: 'agent-manager.md'
- model: 'sonnet'
- metadata with description, version 1.0.0, and capabilities

### 2. Agent Manager Instructions (src/claude_mpm/agents/templates/agent-manager.md):
Create comprehensive markdown instructions covering:
- Understanding 3-tier agent hierarchy (project > user > system)
- Creating new agents from templates
- Creating agent variants for specialized use cases
- Customizing PM instructions and workflows
- Deploying agents to appropriate tiers
- Managing CLAUDE.md files at user and project levels
- Listing and discovering all available agents
- Handling agent upgrades and versioning

### 3. Agent Manager CLI Command (src/claude_mpm/cli/commands/agent_manager.py):
Create new CLI command with subcommands:
- list: Show all agents across tiers with precedence
- create: Create new agent from template
- variant: Create agent variant
- deploy: Deploy agent to specific tier
- customize-pm: Edit PM instructions
- show: Display agent details
- test: Test agent configuration

### 4. Agent Builder Service (src/claude_mpm/services/agents/agent_builder.py):
Create service for:
- Generating agent templates programmatically
- Creating agent variants with inheritance
- Validating agent configurations
- Managing agent metadata and versioning
- Handling PM instruction customization
- Integrating with existing AgentDeploymentService

### 5. Update Integration Files:
- Add agent-manager to default deployment list
- Register new CLI command in parser
- Update any necessary imports

## Key Features:
- Agent creation wizard (interactive)
- Variant management with inheritance
- PM workflow customization
- Deployment control (project/user/system)
- Discovery & listing with hierarchy
- Template library for common agent types
- Validation for JSON and ID conflicts
- Backup & restore capabilities

## Technical Requirements:
- Follow existing agent template format
- Use existing deployment services
- Maintain backward compatibility
- Proper error handling and validation
- Comprehensive help documentation
- Respect 3-tier hierarchy: project (.claude/agents/) > user (~/.claude/agents/) > system (framework)
- PM instructions hierarchy: user CLAUDE.md > project CLAUDE.md > framework BASE_PM.md

## Important Paths:
- Templates: src/claude_mpm/agents/templates/
- Services: src/claude_mpm/services/agents/
- CLI Commands: src/claude_mpm/cli/commands/
- Deployment uses: AgentDeploymentService and MultiSourceAgentDeploymentService

Check for and fix any obvious bugs in the agent system while implementing, particularly around agent loading, template parsing, deployment persistence, and source tracking.