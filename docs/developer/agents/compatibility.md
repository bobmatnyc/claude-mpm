# Agent Format Compatibility Guide

This document explains the relationship between Anthropic's Claude Code agent format and Claude MPM's extended agent format, providing practical guidance for interoperability, conversion, and best practices.

## Table of Contents

1. [Overview of Two Standards](#overview-of-two-standards)
2. [Format Comparison](#format-comparison)
3. [Interoperability Features](#interoperability-features)
4. [Conversion Guidelines](#conversion-guidelines)
5. [Best Practices](#best-practices)
6. [Common Use Cases](#common-use-cases)
7. [Troubleshooting](#troubleshooting)

## Overview of Two Standards

### Anthropic's Claude Code Format

**Purpose**: Official agent format for Anthropic's Claude Desktop, IDE extensions, and developer tools.

**Characteristics**:
- Simple YAML frontmatter in Markdown files
- Minimal required fields: `name` and `description`
- Focus on ease of use and human readability
- Direct integration with Anthropic tooling
- Community-driven tool and model specifications

**File Extensions**: `.claude`, `.md` (with simple frontmatter)

### Claude MPM Format

**Purpose**: Extended agent format for enterprise and project-specific deployments.

**Characteristics**:
- Comprehensive JSON Schema validation
- Rich metadata and configuration options
- Advanced resource management and testing
- Hook system and extensibility features
- Project-oriented deployment model

**File Extensions**: `.claude-mpm`, `.json`

## Format Comparison

### Core Differences

| Feature | Claude Code | Claude MPM | Impact |
|---------|-------------|------------|--------|
| **Schema Validation** | Basic YAML | Full JSON Schema | MPM provides stricter validation |
| **Required Fields** | 2 fields | 7+ fields | MPM requires more metadata |
| **Resource Management** | None | Advanced | MPM enables resource limits |
| **Testing Framework** | None | Built-in | MPM supports automated testing |
| **Versioning** | Optional | Required | MPM enforces version tracking |
| **Tool Specification** | String/Array | Structured Array | MPM has stricter tool validation |
| **Model Selection** | Tier names | Full model IDs | MPM supports specific model versions |

### Compatibility Benefits

| Benefit | Description | Use Case |
|---------|-------------|----------|
| **Bidirectional Support** | Claude MPM loads Claude Code agents | Use existing Claude Desktop agents |
| **Format Detection** | Automatic detection and appropriate validation | Mixed environment deployments |
| **Conversion Tools** | Automated format conversion utilities | Migration and interoperability |
| **Dual Maintenance** | Maintain both formats simultaneously | Cross-platform compatibility |

## Interoperability Features

### Automatic Format Detection

Claude MPM automatically detects agent format based on:

1. **File Extension Analysis**:
   ```
   .claude     → Claude Code format
   .claude-mpm → Claude MPM format  
   .json       → Claude MPM format
   .md         → Content-based detection
   ```

2. **Content Analysis**:
   ```yaml
   # Claude Code detection
   ---
   name: agent-name
   description: Agent description
   ---
   
   # Claude MPM detection  
   ---
   schema_version: "1.2.0"
   agent_id: agent_name
   ---
   ```

3. **Validation Selection**:
   - Claude Code → Basic YAML + required field validation
   - Claude MPM → Full JSON Schema validation

### Field Mapping and Translation

**Automatic Field Translation** (Claude Code → Claude MPM):

```yaml
# Claude Code Input
---
name: code-reviewer
description: Reviews code for quality and security
tools: Read, Write, Edit, Grep
model: sonnet
---

# Automatic Claude MPM Translation
{
  "schema_version": "1.2.0",
  "agent_id": "code_reviewer", 
  "agent_version": "1.0.0",
  "agent_type": "base",
  "metadata": {
    "name": "Code Reviewer", 
    "description": "Reviews code for quality and security",
    "tags": ["code-review"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit", "Grep"],
    "resource_tier": "standard"
  }
}
```

## Conversion Guidelines

### Claude Code to Claude MPM

#### Automated Conversion

```bash
# Convert single agent
./claude-mpm agents convert \
  --input path/to/agent.claude \
  --output-format claude-mpm \
  --output path/to/agent.claude-mpm

# Convert entire directory
./claude-mpm agents convert \
  --input-dir .claude/agents/ \
  --output-dir .claude-mpm/agents/ \
  --output-format claude-mpm
```

#### Manual Conversion Steps

1. **Add Required MPM Fields**:
   ```yaml
   # Add to frontmatter
   schema_version: "1.2.0"
   agent_id: snake_case_name
   agent_version: "1.0.0" 
   agent_type: "base" # or appropriate type
   ```

2. **Restructure Metadata**:
   ```yaml
   # From Claude Code
   name: agent-name
   description: Agent description
   
   # To Claude MPM
   metadata:
     name: Agent Name
     description: Agent description  
     tags:
       - relevant
       - tags
   ```

3. **Restructure Capabilities**:
   ```yaml
   # From Claude Code
   tools: Read, Write, Edit
   model: sonnet
   
   # To Claude MPM
   capabilities:
     model: claude-sonnet-4-20250514
     tools:
       - Read
       - Write  
       - Edit
     resource_tier: standard
   ```

4. **Add Instructions Field**:
   ```yaml
   # Move markdown body to instructions field
   instructions: |
     # Agent Instructions
     
     [Original markdown content here...]
   ```

### Claude MPM to Claude Code

#### Automated Conversion

```bash
# Simplify for Claude Desktop compatibility
./claude-mpm agents convert \
  --input path/to/agent.claude-mpm \
  --output-format claude-code \
  --simplify \
  --output path/to/agent.claude
```

#### Manual Conversion Steps

1. **Extract Basic Fields**:
   ```yaml
   # From Claude MPM metadata
   metadata:
     name: Advanced Agent
     description: Comprehensive agent
   
   # To Claude Code
   name: advanced-agent  
   description: Comprehensive agent
   ```

2. **Simplify Capabilities**:
   ```yaml
   # From Claude MPM
   capabilities:
     model: claude-sonnet-4-20250514
     tools: ["Read", "Write", "Edit"]
     resource_tier: standard
   
   # To Claude Code
   model: sonnet
   tools: Read, Write, Edit
   ```

3. **Extract Instructions**:
   ```yaml
   # Move instructions field to markdown body
   # Remove Claude MPM-specific frontmatter
   ```

## Best Practices

### Dual-Format Strategy

**Recommended Approach**: Maintain Claude MPM as source of truth, generate Claude Code versions.

```bash
# Development workflow
1. Create/edit .claude-mpm files
2. Run automated conversion to generate .claude files  
3. Test both formats in respective environments
4. Commit both formats to version control
```

**Directory Structure**:
```
project/
├── .claude-mpm/agents/          # Primary Claude MPM agents
│   ├── engineer.claude-mpm
│   ├── qa.claude-mpm
│   └── docs.claude-mpm
├── .claude/agents/              # Generated Claude Code compatibility
│   ├── engineer.claude  
│   ├── qa.claude
│   └── docs.claude
└── scripts/
    └── sync_agent_formats.sh    # Automation script
```

### Version Control Considerations

**Include in Repository**:
- Primary agent format (choose one as source of truth)
- Generated compatibility formats (with clear documentation)
- Conversion and synchronization scripts
- Format-specific documentation

**Git Configuration**:
```gitignore
# If Claude MPM is primary, optionally exclude generated Claude Code files
# .claude/agents/*.claude

# Always include primary formats
!.claude-mpm/agents/
!scripts/sync_agent_formats.sh
```

### Naming Conventions

**Consistent Agent Naming**:
```
# Agent ID in different formats
Claude Code name: "data-processor"      (kebab-case)
Claude MPM agent_id: "data_processor"   (snake_case)  
File names: data_processor.claude-mpm / data-processor.claude
```

**Version Synchronization**:
```yaml
# Keep versions synchronized
# Claude Code
version: "1.2.0"

# Claude MPM  
agent_version: "1.2.0"
```

## Common Use Cases

### Use Case 1: Cross-Platform Development

**Scenario**: Developer using Claude Desktop wants to deploy agents in Claude MPM environment.

**Solution**:
1. Develop agents in Claude Code format for Desktop compatibility
2. Use conversion tools to create Claude MPM versions for deployment
3. Maintain both formats with automated synchronization

### Use Case 2: Enterprise Migration

**Scenario**: Organization migrating from Claude Desktop to Claude MPM for advanced features.

**Solution**:
1. Inventory existing Claude Code agents
2. Batch convert using automated tools
3. Enhance converted agents with Claude MPM features
4. Maintain compatibility versions for transitional period

### Use Case 3: Team Collaboration

**Scenario**: Mixed team with some members using Claude Desktop, others using Claude MPM.

**Solution**:
1. Establish Claude MPM as team standard for features
2. Generate Claude Code compatibility versions automatically
3. Use CI/CD to maintain format synchronization
4. Document format-specific capabilities and limitations

### Use Case 4: Tool Integration

**Scenario**: Integration with external tools requiring specific agent formats.

**Solution**:
1. Identify format requirements for each tool
2. Create conversion pipeline for required formats
3. Implement validation for all target formats
4. Maintain format-specific test suites

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Format Detection Failures

**Symptoms**:
- Agent not loading correctly
- Wrong validation rules applied
- Format detection errors in logs

**Solutions**:
```bash
# Verify file extension and content alignment
./claude-mpm agents validate --format-detection path/to/agent

# Check frontmatter syntax
./claude-mpm agents lint path/to/agent

# Force specific format detection
./claude-mpm agents load --force-format claude-code path/to/agent
```

#### Issue 2: Conversion Failures

**Symptoms**:
- Converted agents missing functionality
- Validation errors after conversion
- Tools or model specifications lost

**Solutions**:
```bash
# Use verbose conversion for debugging
./claude-mpm agents convert --verbose --debug-mapping

# Validate converted agents
./claude-mpm agents validate path/to/converted-agent

# Compare original and converted versions
./claude-mpm agents diff original.claude converted.claude-mpm
```

#### Issue 3: Field Mapping Issues

**Symptoms**:
- Required fields missing after conversion
- Tool specifications not working
- Model selection errors

**Solutions**:
1. **Check Field Mapping Table**: Verify all fields are properly mapped
2. **Add Missing Fields**: Manually add required fields post-conversion
3. **Validate Tools**: Ensure tool names are correctly formatted
4. **Update Model Specifications**: Convert between tier names and full model IDs

#### Issue 4: Synchronization Problems

**Symptoms**:
- Formats out of sync
- Different behaviors between formats  
- Version mismatches

**Solutions**:
```bash
# Implement automated synchronization
scripts/sync_agent_formats.sh --check --report

# Force re-synchronization
scripts/sync_agent_formats.sh --force-sync

# Validate synchronization
./claude-mpm agents compare --format-sync
```

### Debugging Tools

#### Format Detection Testing

```bash
# Test format detection logic
./claude-mpm agents detect-format path/to/agent

# Verbose format analysis
./claude-mpm agents analyze --format --content path/to/agent
```

#### Conversion Validation

```bash
# Test conversion round-trip
./claude-mpm agents convert --test-round-trip path/to/agent

# Compare conversion outputs
./claude-mpm agents diff --ignore-format-specific original converted
```

#### Compatibility Testing

```bash
# Test agent in both formats
./claude-mpm agents test --format claude-code path/to/agent.claude
./claude-mpm agents test --format claude-mpm path/to/agent.claude-mpm

# Cross-format compatibility check  
./claude-mpm agents compatible-check path/to/agent.claude path/to/agent.claude-mpm
```

This compatibility guide ensures smooth interoperability between Claude Code and Claude MPM agent formats, enabling teams to leverage the strengths of both systems while maintaining compatibility and flexibility.