# PM Skill: Agent Update Workflow

## Trigger Patterns
- "update agent", "fix agent", "improve agent", "modify agent"
- "change {agent-name} agent", "edit agent instructions"
- Any request to modify agent behavior

## FUNDAMENTAL RULE: Official vs Custom Agents

### Official MPM Agents (NEVER edit deployed copies)
**Source**: `~/.claude-mpm/cache/agents/` (from bobmatnyc/claude-mpm-agents repo)
**Deployed**: `.claude/agents/` - READ-ONLY for official agents

**Detection**: Check if agent exists in `~/.claude-mpm/cache/agents/`
- If YES → Official agent → Follow Official Agent Workflow
- If NO → Custom agent → Can edit `.claude/agents/` directly

### Custom/Localized Agents
- Created specifically for project
- Can be edited directly in `.claude/agents/`
- Not part of official MPM agent set

## Official Agent Update Workflow

### Step 1: Identify Agent Source
```bash
ls ~/.claude-mpm/cache/agents/  # Find the source file
```

### Step 2: Update Source
Edit the agent source in `~/.claude-mpm/cache/agents/{agent-name}.md`
(or appropriate path based on agent structure)

### Step 3: Rebuild and Redeploy
Use MPM deployment tools:
```bash
# Redeploy specific agent
mpm agents deploy {agent-name}

# Or redeploy all agents
mpm agents deploy --all
```

### Step 4: Validate (claude-mpm project only)
When working in the claude-mpm project itself:
```bash
# Run deepeval against deployed agent instructions
deepeval test --agent {agent-name}
```

## Circuit Breaker

**BLOCK** if attempting to edit `.claude/agents/{official-agent}.md` directly:
- Official agents in deployed location are BUILD OUTPUTS
- Must update source → rebuild → redeploy
- Violation = architectural breach

## Examples

### ❌ WRONG (Editing deployed official agent)
```
Edit: .claude/agents/web-qa.md  # VIOLATION - this is a built output
```

### ✅ CORRECT (Updating source and redeploying)
```
1. Edit: ~/.claude-mpm/cache/agents/web-qa.md  # Update source
2. Run: mpm agents deploy web-qa                # Rebuild/redeploy
3. Validate: deepeval test --agent web-qa       # (in claude-mpm project)
```

### ✅ CORRECT (Custom agent - can edit directly)
```
Edit: .claude/agents/my-custom-agent.md  # OK - not an official agent
```
