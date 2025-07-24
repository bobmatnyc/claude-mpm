# [Agent Name] Agent

<!--
Agent Version Guidelines:
- Major version (X.0.0): Breaking changes to agent capabilities or authority
- Minor version (0.X.0): New capabilities, significant enhancements, or workflow additions
- Serial version (0.0.X): Bug fixes, documentation updates, minor tweaks, clarifications

Examples:
- 1.0.0 → 2.0.0: Agent authority scope fundamentally changed
- 1.0.0 → 1.1.0: Added new workflow or significant capability
- 1.0.0 → 1.0.1: Fixed typo, clarified documentation, minor adjustment
-->

## 🎯 Primary Role
[1-2 sentences defining the agent's core purpose and unique value]

## 🎯 When to Use This Agent
[Clear guidance on when the PM should delegate to this agent]
- **Use for**: [Specific scenarios where this agent excels]
- **Instead of**: [What agents NOT to use for these tasks]
- **Example triggers**: [Specific keywords or situations that indicate this agent is needed]

## 🔧 Core Capabilities
[3-5 bullet points of capabilities UNIQUE to this agent]
- **[Capability 1]**: [Brief description]
- **[Capability 2]**: [Brief description]
- **[Capability 3]**: [Brief description]

## 🔑 Authority & Permissions

### ✅ Exclusive Write Access
- `[file pattern]` - [what and why]
- `[file pattern]` - [what and why]

### ❌ Forbidden Operations
- [Specific operations this agent must NOT perform]
- [Areas outside this agent's authority]

## 📋 Agent-Specific Workflows

### [Workflow 1 Name]
```yaml
trigger: [When this workflow starts]
process:
  1. [Step 1]
  2. [Step 2]
  3. [Step 3]
output: [What is produced]
```

### [Workflow 2 Name]
```yaml
trigger: [When this workflow starts]
process:
  1. [Step 1]
  2. [Step 2]
output: [What is produced]
```

## 🚨 Unique Escalation Triggers
[Only triggers specific to this agent, not covered in base_agent.md]
- **[Situation]**: [Specific escalation action]
- **[Situation]**: [Specific escalation action]

## 📊 Key Performance Indicators
[3-5 measurable, agent-specific KPIs]
1. **[KPI Name]**: [Target value/metric]
2. **[KPI Name]**: [Target value/metric]
3. **[KPI Name]**: [Target value/metric]

## 🔄 Critical Dependencies
- **[Agent Name]**: [Why this dependency exists]
- **[Agent Name]**: [Why this dependency exists]

## 🛠️ Specialized Tools/Commands
[Only if agent has unique tools not in common set]
```bash
# Example command specific to this agent
[command] [options]
```

---
**Agent Type**: [core/specialist]
**Model Preference**: [claude-3-opus/claude-3-sonnet]
**Version**: 1.0.0

## 📝 Changelog

### Version 1.0.0 - [Date]
- Initial agent creation
- Core capabilities defined
- Authority boundaries established
- Workflows documented

<!--
Changelog Template for Future Updates:

### Version X.Y.Z - YYYY-MM-DD
- **[Added/Changed/Fixed/Removed]**: Description of change
- **[Added/Changed/Fixed/Removed]**: Description of change
- **Impact**: How this affects agent behavior or PM delegation

Categories:
- Added: New features or capabilities
- Changed: Modifications to existing behavior
- Fixed: Bug fixes or corrections
- Removed: Deprecated features or capabilities
-->