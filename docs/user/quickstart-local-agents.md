# Local Agents Quick Start Guide

Get up and running with local agents in 5 minutes! Create your first custom AI assistant tailored to your project.

## What You'll Learn

- Create your first local agent in under 2 minutes
- Deploy and use the agent immediately
- Understand the priority system
- Share agents with your team

## Prerequisites

- Claude MPM installed and working
- A project directory (any will work)

## Step 1: Create Your First Local Agent (2 minutes)

Let's create a local agent specialized for your domain:

```bash
claude-mpm agent-manager create-local \
  --agent-id my-domain-expert \
  --name "My Domain Expert" \
  --description "Expert assistant for this specific project" \
  --instructions "You are an expert assistant specialized in this project. You understand our codebase, conventions, and business domain. Always provide practical, actionable advice tailored to our specific context."
```

**What this does:**
- Creates a JSON template in `.claude-mpm/agents/my-domain-expert.json`
- Sets it as a project-level agent (highest priority)
- Uses "sonnet" model by default (good balance of speed and capability)
- Gives full tool access

## Step 2: Deploy and Test (1 minute)

Deploy your agent to make it available:

```bash
# Deploy the agent
claude-mpm agent-manager deploy-local --agent-id my-domain-expert

# Test it immediately
claude-mpm run --agent my-domain-expert "What is your expertise and how can you help with this project?"
```

**You should see:**
- Deployment confirmation message
- Your agent responding with its specialized knowledge

## Step 3: Verify It's Working

Check that your agent is active and has highest priority:

```bash
claude-mpm agent-manager list
```

**You should see output like:**
```
=== Agent Hierarchy ===

[P] PROJECT LEVEL (Highest Priority)
    my-domain-expert     - My Domain Expert [LOCAL-PROJECT]

[S] SYSTEM LEVEL (Framework Defaults)
    pm                   - Project Manager
    research             - Research Assistant
    ...
```

The `[P]` indicates your local agent has the highest priority!

## Step 4: Use Your Agent

Now you can use your specialized agent for any task:

```bash
# For code analysis
claude-mpm run --agent my-domain-expert "Analyze the structure of this codebase and suggest improvements"

# For project-specific help
claude-mpm run --agent my-domain-expert "Help me understand the best way to implement feature X in this project"

# Interactive mode for longer sessions
claude-mpm run --interactive --agent my-domain-expert
```

## Common Customizations

### Specialized Expert Agent

Create an agent expert in your specific technology:

```bash
claude-mpm agent-manager create-local \
  --agent-id react-expert \
  --name "React/TypeScript Expert" \
  --instructions "You are a senior React and TypeScript developer. Focus on modern React patterns, hooks, TypeScript best practices, performance optimization, and testing with Jest/RTL." \
  --model sonnet
```

### Code Reviewer Agent

Create an agent focused on code quality:

```bash
claude-mpm agent-manager create-local \
  --agent-id senior-reviewer \
  --name "Senior Code Reviewer" \
  --instructions "You are a senior engineer conducting thorough code reviews. Focus on: architecture patterns, security, performance, maintainability, testing coverage, and adherence to team coding standards." \
  --model opus
```

### Documentation Writer Agent

Create an agent specialized in documentation:

```bash
claude-mpm agent-manager create-local \
  --agent-id tech-writer \
  --name "Technical Writer" \
  --instructions "You are a technical writer creating clear, comprehensive documentation. Focus on user-friendly language, practical examples, troubleshooting sections, and ensuring all features are documented with proper usage examples." \
  --parent documentation
```

## Understanding Priority

Claude MPM uses a priority system to determine which agent to use:

1. **PROJECT agents** (your local `.claude-mpm/agents/`) - **Priority 2000+**
2. **USER agents** (`~/.claude-mpm/agents/`) - **Priority 1500+**  
3. **SYSTEM agents** (built-in) - **Priority 1000**

**Example scenario:**
- System has a `research` agent
- You create a local `research` agent
- Your local agent automatically overrides the system one!

```bash
# This will use YOUR custom research agent, not the system one
claude-mpm run --agent research "Research best practices"
```

## Team Sharing (Bonus)

### Share Your Agents

Export your agents to share with teammates:

```bash
# Export all your local agents
claude-mpm agent-manager export-local --output ./team-agents

# Share the directory (git, Slack, email, etc.)
ls ./team-agents/
# my-domain-expert.json
# react-expert.json
# senior-reviewer.json
```

### Import Team Agents

Import agents shared by teammates:

```bash
# Import shared agents
claude-mpm agent-manager import-local --input ./team-agents

# Deploy them all
claude-mpm agent-manager deploy-local

# List to see what's available
claude-mpm agent-manager list
```

## Next Steps

### 🏗️ **Advanced Customization**
- Edit JSON templates directly for fine-tuned control
- Create agent variants with different models/settings
- Use parent agents to inherit and extend system agents

### 📚 **Learn More**
- [Complete User Guide](03-features/local-agents.md) - Comprehensive usage documentation
- [Developer Guide](../developer/LOCAL_AGENTS.md) - Technical implementation details
- [CLI Reference](../reference/CLI_COMMANDS.md) - All command options and examples

### 🔧 **Pro Tips**

**Version Control:**
```bash
# Include your agents in git for team sharing
git add .claude-mpm/agents/
git commit -m "Add custom domain expert agent"
```

**Quick Agent Updates:**
```bash
# Edit template
nano .claude-mpm/agents/my-domain-expert.json

# Redeploy
claude-mpm agent-manager deploy-local --agent-id my-domain-expert --force
```

**Troubleshooting:**
```bash
# Check what agents are active
claude-mpm agent-manager list

# Test agent configuration
claude-mpm agent-manager test my-domain-expert

# Sync if something seems wrong
claude-mpm agent-manager sync-local
```

## Troubleshooting

**Agent not found after creation?**
```bash
# Check if created
ls .claude-mpm/agents/

# Deploy it
claude-mpm agent-manager deploy-local --agent-id your-agent-name
```

**Agent giving generic responses?**
- Edit `.claude-mpm/agents/your-agent.json`
- Update the `instructions` field with more specific expertise
- Redeploy with `--force` flag

**Want to start over?**
```bash
# See what would be removed
claude-mpm agent-manager reset --dry-run

# Remove and start fresh
claude-mpm agent-manager reset --force
```

## Success! 🎉

You now have:
- ✅ A custom local agent tailored to your project
- ✅ Understanding of how the priority system works
- ✅ Knowledge of how to share agents with your team
- ✅ Foundation to create more specialized agents

Your local agent will now override system agents with the same name and provide responses tailored specifically to your project context!

**Ready for more?** Check out the [complete user guide](03-features/local-agents.md) for advanced features like agent inheritance, versioning, and complex deployment scenarios.