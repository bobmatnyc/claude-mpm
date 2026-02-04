---
name: mpm-workflow
version: "1.0.0"
description: Manage and customize MPM workflow configurations with local overrides
when_to_use: workflow customization, phase configuration, verification gates, agent routing
category: pm-configuration
tags: [workflow, configuration, customization, phases, verification]
---

# MPM Workflow Configuration

## Overview

The MPM workflow system supports customizable workflow configurations with a priority-based override system. This allows projects to customize the standard 5-phase workflow while maintaining sensible defaults.

## Priority System

Workflow files are loaded with the following priority (highest to lowest):

1. **Project-level**: `.claude-mpm/WORKFLOW.md` - Project-specific customizations
2. **User-level**: `~/.claude-mpm/WORKFLOW.md` - User preferences across all projects
3. **System default**: Built-in framework WORKFLOW.md

## Commands

### `/mpm-workflow status`

Show current workflow configuration and source:

```
Workflow Configuration Status:
  Source: project (.claude-mpm/WORKFLOW.md)
  Phases: 5
  Verification Gates: Enabled
  Custom Overrides: Phase 2 (Code Analyzer) skipped
```

### `/mpm-workflow init`

Initialize a local workflow configuration file:

```bash
# Creates .claude-mpm/WORKFLOW.md with defaults
/mpm-workflow init

# Creates with minimal template
/mpm-workflow init --minimal
```

### `/mpm-workflow reset`

Reset to default workflow configuration:

```bash
# Removes local override, uses system default
/mpm-workflow reset
```

### `/mpm-workflow validate`

Validate the current workflow configuration:

```
Validating workflow configuration...
  [OK] Phase definitions complete
  [OK] Verification gates defined
  [OK] Agent routing valid
  [WARN] Custom phase 6 defined - ensure agent exists
```

## Workflow File Structure

### Required Sections

```markdown
# PM Workflow Configuration

## Mandatory Phase Sequence

### Phase 1: Research (ALWAYS FIRST)
**Agent**: Research
**Output**: Requirements, constraints, success criteria
**Template**: ...

### Phase 2: Code Analyzer Review
**Agent**: Code Analyzer
**Output**: APPROVED/NEEDS_IMPROVEMENT/BLOCKED
**Decision**: ...

### Phase 3: Implementation
**Agent**: Selected via delegation matrix
**Requirements**: Complete code, error handling, tests

### Phase 4: QA (MANDATORY)
**Agent**: qa/api-qa/web-qa
**Requirements**: Real-world testing with evidence

### Phase 5: Documentation
**Agent**: Documentation
**When**: Code changes made

## Verification Gates

| Phase | Verification Required | Evidence Format |
|-------|----------------------|-----------------|
| ... | ... | ... |

## Override Commands

- "Skip workflow" - bypass sequence
- "Go directly to [phase]" - jump to phase
```

## Customization Examples

### Skip Code Analyzer for Trusted Projects

```markdown
### Phase 2: Code Analyzer Review
**Agent**: Code Analyzer
**Status**: OPTIONAL
**Skip When**: Small fixes, documentation only
```

### Add Custom Phase

```markdown
### Phase 6: Security Scan (Custom)
**Agent**: Security
**When**: Changes to auth, API, or data handling
**Output**: Security report
```

### Modify Verification Requirements

```markdown
## Verification Gates

| Phase | Verification Required | Evidence Format |
|-------|----------------------|-----------------|
| Implementation | Tests pass + Coverage > 80% | pytest output with coverage |
```

## Integration with Instruction Builder

The workflow loader automatically injects workflow configuration into PM instructions:

1. Checks for project-level WORKFLOW.md
2. Falls back to user-level if not found
3. Uses system default as last resort
4. Injects into `workflow_instructions` content field

## Best Practices

1. **Start with defaults**: Only override what you need
2. **Document changes**: Add comments explaining why phases were modified
3. **Test workflows**: Use `/mpm-workflow validate` after changes
4. **Version control**: Commit `.claude-mpm/WORKFLOW.md` with your project
5. **Team alignment**: Ensure team agrees on workflow customizations

## Troubleshooting

### Workflow not loading

1. Check file exists: `ls -la .claude-mpm/WORKFLOW.md`
2. Validate syntax: `/mpm-workflow validate`
3. Check priority: `/mpm-workflow status`

### Phases not executing

1. Verify phase is defined in workflow
2. Check agent exists for custom phases
3. Review verification gate requirements

### Reset to defaults

```bash
/mpm-workflow reset
```
