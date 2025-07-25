# EPIC: Pivot to Claude Code Native Subagents

**Epic ID**: EP-0002  
**Title**: Migrate from Subprocess Management to Native Claude Subagent Configuration  
**Status**: In Progress  
**Created**: 2025-07-25  
**Priority**: High  
**Owner**: Claude MPM Team  

## Executive Summary

Pivot the Claude MPM framework from managing Claude subprocesses directly to leveraging Claude Code's new native subagent feature. This involves transitioning from subprocess orchestration to YAML-based agent configuration generation, enabling automatic agent discovery, configuration management, and integration with our existing ticket system.

## Background

Claude Code now supports native subagents through:
- YAML frontmatter configuration files in `.claude/agents/` directories
- Up to 10 parallel subagents with independent context windows
- Tool inheritance and access control
- Environment variable and flag-based configuration
- Both project-level and user-level agent definitions

## Goals

1. **Primary**: Generate and manage Claude subagent YAML configurations
2. **Enable**: Automatic creation of user-level agents based on our system templates
3. **Support**: Project customization of base agents and agent training via evals
4. **Integrate**: Ticket management system with native subagent workflow
5. **Maintain**: Backwards compatibility with existing MPM agent definitions

## Success Criteria

- [ ] POC validates Claude reads agent YAML files from specified directory
- [ ] Framework generates valid YAML configurations from existing agent templates
- [ ] Claude uses TodoWrite and Task tool to delegate to configured agents
- [ ] Project logging captures native subagent activity
- [ ] Ticket integration works with new subagent model

## Technical Architecture

### Directory Structure
```
Project/
├── .claude-mpm/
│   ├── agents/                    # Framework-generated agents
│   │   ├── engineer.yaml
│   │   ├── qa.yaml
│   │   ├── documentation.yaml
│   │   └── [custom agents]
│   ├── agent-templates/           # Base templates
│   ├── agent-training/            # Eval results for improvement
│   └── logs/                      # Existing logging structure
```

### Agent YAML Format
```yaml
---
name: "engineer"
description: "Software engineering and implementation specialist"
version: "1.0.0"
tags: ["implementation", "coding", "development"]
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
priority: "high"
timeout: 600
max_tokens: 8192

# Claude MPM specific metadata
source: "claude-mpm"
template: "engineer-base"
customizations:
  - "project-specific-context"
training_data: "agent-training/engineer-evals.json"
---

You are the Engineer Agent in the Claude PM Framework...
[System prompt content]
```

## Implementation Phases

### Phase 1: POC and Validation (1-2 days)
- Create test POC to validate agent YAML loading
- Test environment variable controls (`CLAUDE_CONFIG_DIR`)
- Verify Claude reads from `.claude-mpm/agents/`
- Confirm TodoWrite and Task delegation work with configured agents
- Document findings and limitations

### Phase 2: YAML Generation System (2-3 days)
- Create `AgentYAMLGenerator` class
- Convert existing agent templates to YAML format
- Implement frontmatter generation with proper metadata
- Add version management and tracking
- Create agent discovery mechanism

### Phase 3: Configuration Management (2-3 days)
- Build agent configuration API
- Support user customization overlays
- Implement project-specific agent variants
- Create agent inheritance system
- Add configuration validation

### Phase 4: Integration (3-4 days)
- Update `SubprocessOrchestrator` to work with native subagents
- Modify project logging to capture subagent metrics
- Integrate ticket system with subagent workflow
- Update hook system for subagent events
- Maintain backwards compatibility

### Phase 5: Training and Evaluation (2-3 days)
- Create agent evaluation framework
- Implement training data collection
- Build agent improvement pipeline
- Add performance metrics tracking
- Create feedback loop for agent refinement

## Key Technical Decisions

1. **Configuration Directory**: Use `.claude-mpm/agents/` within project
2. **Environment Control**: Set `CLAUDE_CONFIG_DIR` to our directory
3. **Agent Naming**: Use lowercase, hyphenated names (e.g., `qa-specialist`)
4. **Version Strategy**: Semantic versioning for agent configurations
5. **Tool Access**: Inherit main process tools by default

## Dependencies

- Claude Code with subagent support
- Access to `.claude/agents/` directory structure
- TodoWrite and Task tool functionality
- Environment variable control in subprocess

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|---------|------------|
| Claude doesn't read custom agent directory | High | Test with various CLAUDE_CONFIG_DIR settings |
| YAML format incompatibility | Medium | Validate against schema, test extensively |
| Performance degradation | Medium | Monitor metrics, optimize agent definitions |
| Breaking existing workflows | High | Maintain compatibility layer |

## Tasks Breakdown

### Immediate Tasks (Phase 1 POC)
1. **TSK-0046**: Create POC test script for agent YAML validation
2. **TSK-0047**: Test environment variable configuration
3. **TSK-0048**: Validate Claude reads from `.claude-mpm/agents/`
4. **TSK-0049**: Test TodoWrite/Task delegation with custom agents
5. **TSK-0050**: Document POC findings and limitations

### Phase 2 Tasks
6. **TSK-0051**: Create AgentYAMLGenerator class
7. **TSK-0052**: Convert engineer agent template to YAML
8. **TSK-0053**: Convert QA agent template to YAML
9. **TSK-0054**: Implement frontmatter validation
10. **TSK-0055**: Create agent discovery mechanism

### Phase 3 Tasks
11. **TSK-0056**: Build agent configuration API
12. **TSK-0057**: Implement project customization overlay
13. **TSK-0058**: Create agent inheritance system
14. **TSK-0059**: Add configuration validation
15. **TSK-0060**: Build agent registry integration

### Phase 4 Tasks
16. **TSK-0061**: Update SubprocessOrchestrator for native subagents
17. **TSK-0062**: Modify ProjectLogger for subagent metrics
18. **TSK-0063**: Integrate ticket system with subagents
19. **TSK-0064**: Update hook system for subagent events
20. **TSK-0065**: Create compatibility layer

### Phase 5 Tasks
21. **TSK-0066**: Create agent evaluation framework
22. **TSK-0067**: Implement training data collection
23. **TSK-0068**: Build agent improvement pipeline
24. **TSK-0069**: Add performance tracking
25. **TSK-0070**: Create feedback system

## Monitoring and Success Metrics

- Agent YAML files successfully generated
- Claude recognizes and uses custom agents
- Delegation success rate > 95%
- Performance metrics show improvement
- User feedback positive

## Notes

- MCP resources not available to subagents (known limitation)
- Maximum 10 concurrent subagents
- Context isolation is complete between subagents
- Tool inheritance from main process
- 200-500ms subagent startup latency

## References

- [Claude Subagents Technical Implementation](../design/claude-subagents-technical-implementation.md)
- [Original MPM Agent Templates](../../src/claude_mpm/agents/templates/)
- [Project Logging System](../../src/claude_mpm/core/project_logger.py)