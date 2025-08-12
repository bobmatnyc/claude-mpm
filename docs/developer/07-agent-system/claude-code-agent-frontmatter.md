# Claude Code Agent Frontmatter: Anthropic's Official Standard

> **⚠️ IMPORTANT NOTE**: This document describes **Anthropic's Claude Code** agent standard, not Claude MPM's agent format. Claude Code is Anthropic's official agent system for Claude Desktop and IDE integrations. For Claude MPM's agent format, see [frontmatter.md](./frontmatter.md).

## Executive Summary

This specification documents **Anthropic's Claude Code** agent format - the official standard used by Claude Desktop, Claude for VS Code, and other Anthropic tooling. Claude Code agents use a straightforward YAML frontmatter structure in Markdown files with two required fields (`name` and `description`), one optional field (`tools`), and one unofficial field (`model`) found in community implementations. 

**Key Distinction**: Claude Code agents are designed for Anthropic's ecosystem, while Claude MPM provides an extended agent format with additional capabilities. This document focuses exclusively on the Anthropic Claude Code standard.

## Relationship to Claude MPM

Claude MPM supports **both** formats to ensure compatibility:

- **Claude Code Format** (.claude files): Full compatibility with Anthropic's standard
- **Claude MPM Format** (.claude-mpm files): Extended format with additional metadata and features

When using Claude Code agents in Claude MPM:
- ✅ All Claude Code agents work seamlessly in Claude MPM
- ✅ Automatic format detection handles both standards
- ✅ No migration required - use existing `.claude` files directly
- ✅ Claude MPM's validation system recognizes both formats

## Core frontmatter structure and requirements

The Claude Code agent frontmatter follows a simple yet powerful YAML structure embedded in Markdown files. Every agent file **must** begin with triple dashes (`---`), contain valid YAML metadata, and close with another set of triple dashes. This frontmatter must be the very first content in the file, with no preceding whitespace or byte order marks.

The basic structure requires two elements: a unique `name` field that serves as the agent's identifier using only lowercase letters and hyphens (matching the pattern `^[a-z0-9]+(-[a-z0-9]+)*$`), and a `description` field containing natural language text that Claude uses for automatic task delegation. The description should be detailed and action-oriented, ideally including trigger words like "PROACTIVELY" or "MUST BE USED" to enhance automatic invocation.

Agents are stored in two possible locations with clear precedence rules. Project-level agents in `.claude/agents/` take priority over user-level agents in `~/.claude/agents/`, allowing teams to share specialized agents while individuals maintain personal collections. Files must use the `.md` extension and follow standard UTF-8 encoding without BOM headers.

## Complete field specifications with validation rules

The **name field** (required) identifies each agent uniquely within its scope. It must contain only lowercase letters, numbers, and hyphens, cannot start or end with hyphens, and should match the filename (without the `.md` extension). Claude uses this identifier for explicit invocation and internal routing. Validation fails if names conflict within the same scope or contain invalid characters.

The **description field** (required) provides Claude with context for automatic delegation decisions. This natural language description should clearly explain when the agent should be invoked, what tasks it handles, and any specific expertise areas. Descriptions shorter than 10 characters are typically insufficient for proper task routing. Including specific trigger conditions and use cases improves delegation accuracy significantly.

The **tools field** (optional) restricts agent access to specific capabilities following the principle of least privilege. When omitted, agents inherit all tools from the main thread. Tools can be specified as a comma-separated string (`"Read, Edit, Write, Bash"`) or a YAML array. Invalid tool names are silently ignored rather than causing failures. Available tools include file operations (Read, Edit, MultiEdit, Write), search capabilities (Grep, Glob, search_files), terminal access (Bash, terminal), version control (git_commit, git_push), container operations (docker_build, docker_run), package management (npm_install, pip_install), and MCP server tools following the format `mcp__server_name__tool_name`.

The **model field** (unofficial, optional) appears in community implementations but lacks official documentation. When present, it accepts values of "sonnet", "opus", or "haiku" to override the default model selection. This field enables resource optimization by using appropriate model tiers for different task complexities.

## JSON Schema for validation implementation

Based on the specification analysis, here's the authoritative JSON Schema for validating Claude Code agent frontmatter:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Claude Code Agent Frontmatter",
  "type": "object",
  "required": ["name", "description"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
      "minLength": 1,
      "maxLength": 50,
      "description": "Unique agent identifier using lowercase letters, numbers, and hyphens"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500,
      "description": "Natural language description of agent purpose and invocation triggers"
    },
    "tools": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[A-Za-z0-9_]+(,\\s*[A-Za-z0-9_]+)*$",
          "description": "Comma-separated list of tool names"
        },
        {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z0-9_]+$"
          },
          "uniqueItems": true,
          "description": "Array of tool names"
        }
      ]
    },
    "model": {
      "type": "string",
      "enum": ["sonnet", "opus", "haiku"],
      "description": "Model selection override (unofficial field)"
    }
  },
  "additionalProperties": false
}
```

## Validation implementation strategy

Implementing robust validation requires a multi-layer approach. **Syntax validation** ensures the YAML parses correctly and the Markdown structure is valid. This includes checking for proper delimiters, valid indentation (spaces only, no tabs), and UTF-8 encoding. **Schema validation** applies the JSON Schema to verify field types, patterns, and constraints. **Semantic validation** goes beyond structure to verify tool availability, name uniqueness within scope, and meaningful content in the system prompt section.

Error handling should follow Claude's graceful degradation pattern. Invalid agents are logged but don't crash the system, allowing other valid agents to function normally. Validation errors should produce clear, actionable messages indicating the specific issue and location. When agents fail validation, Claude falls back to built-in capabilities or other valid agents.

The validation pipeline should check files in order: first ensure the file exists and is readable, parse the YAML frontmatter, validate against the schema, check semantic constraints, and finally verify the system prompt content exists and provides meaningful instructions.

## Working examples and patterns

A minimal valid agent requires only name and description:

```yaml
---
name: code-reviewer
description: Reviews code for quality, security, and best practices. Use after writing or modifying code.
---

You are an expert code reviewer focused on maintaining high code quality standards.
```

A fully-featured agent with tool restrictions demonstrates the complete specification:

```yaml
---
name: security-auditor
description: Proactively audits code for security vulnerabilities and OWASP compliance. Must be used for security-sensitive code changes.
tools: Read, Grep, Glob, search_files
---

You are a senior security engineer specializing in vulnerability assessment.

When invoked:
1. Scan for OWASP Top 10 vulnerabilities
2. Check authentication and authorization patterns
3. Verify input validation and sanitization
4. Review cryptographic implementations
5. Identify information disclosure risks

Provide findings with severity levels (Critical/High/Medium/Low).
```

## Recent updates and version compatibility

Claude Code's agent system has evolved significantly since initial release. Prior to v1.0.60, agents required manual invocation through explicit commands. Version 1.0.60 introduced automatic delegation, transforming agents from passive tools to proactive assistants. The current implementation maintains backward compatibility while enhancing intelligent task routing based on description matching and context analysis.

The terminology has unified around "agents" (previously distinguished as "sub-agents" versus "custom agents"), though both terms remain in use. The file format and frontmatter structure have remained stable, ensuring existing agents continue functioning across updates. No fields have been deprecated, maintaining full backward compatibility.

## Field purposes and agent lifecycle

Each frontmatter field serves specific architectural purposes in Claude's agent ecosystem. The **name** field acts as the primary key for agent registry and explicit invocation, enabling Claude to maintain a catalog of available specialists. The **description** field drives automatic delegation through natural language processing, with Claude analyzing task context against agent descriptions to determine optimal routing. The **tools** field enforces security boundaries and improves focus by limiting agent capabilities to necessary operations, preventing capability drift and reducing attack surface. The unofficial **model** field enables resource optimization, allowing different model tiers for varying task complexities.

The agent lifecycle follows a predictable pattern: discovery (scanning directories on startup), parsing (validating YAML and structure), registration (adding to available agent pool), invocation (automatic or manual based on context), execution (isolated context window with specified tools), and result integration (merging outputs back to main thread). This architecture enables parallel execution of multiple agents while maintaining isolation and security boundaries.

## Claude Code Compatibility in Claude MPM

Claude MPM provides full compatibility with Anthropic's Claude Code agent format while extending capabilities through its own format.

### File Extensions and Detection

| File Extension | Format Detected | Validation Applied |
|----------------|-----------------|-------------------|
| `.claude` | Claude Code | Anthropic's schema |
| `.md` (with simple frontmatter) | Claude Code | Anthropic's schema |
| `.claude-mpm` | Claude MPM | Extended schema |
| `.md` (with `schema_version`) | Claude MPM | Extended schema |

### Migration Path

**From Claude Code to Claude MPM**:
1. Keep existing `.claude` files - they work as-is
2. For enhanced features, create `.claude-mpm` versions
3. Use conversion tools: `./claude-mpm agents convert --from claude-code --to claude-mpm`

**Best Practices for Dual Compatibility**:
- Maintain Claude Code versions for Anthropic tool compatibility
- Create Claude MPM versions for advanced project features
- Use naming conventions: `agent_name.claude` and `agent_name.claude-mpm`

### Feature Comparison

| Feature | Claude Code | Claude MPM |
|---------|-------------|------------|
| Required fields | `name`, `description` | Extended metadata |
| Tools specification | String or array | Structured array |
| Model selection | Tier names | Full model IDs |
| Resource management | Basic | Advanced |
| Testing framework | None | Built-in |
| Hook system | None | Pre/post execution |
| Validation | Basic YAML | Full JSON Schema |

### Validation Differences

**Claude Code Validation**:
- Focuses on YAML syntax and required fields
- Lenient tool name validation
- Basic model tier checking

**Claude MPM Validation**:
- Complete JSON Schema validation
- Strict field type checking
- Advanced resource constraint validation
- Cross-field dependency validation

## Conclusion

This document provides the complete specification for **Anthropic's Claude Code** agent format. While Claude Code offers simplicity and broad compatibility, Claude MPM extends these capabilities with advanced features for enterprise and project-specific use cases.

**For Anthropic tool compatibility**: Use the Claude Code format documented here.
**For enhanced Claude MPM features**: See [frontmatter.md](./frontmatter.md) for the extended format.
**For compatibility guidance**: See [compatibility.md](./compatibility.md) for detailed migration and interoperability information.

The key to successful implementation lies in understanding which format serves your specific use case while maintaining compatibility across the broader Claude ecosystem.