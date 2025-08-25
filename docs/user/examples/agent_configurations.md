# Agent Configuration Examples

This document provides comprehensive examples of valid and invalid agent configurations to help understand the schema requirements.

## Valid Agent Configurations

### 1. Minimal Valid Configuration

The absolute minimum required fields for a valid agent:

```json
{
  "schema_version": "1.2.0",
  "agent_id": "minimal_agent",
  "agent_version": "1.0.0",
  "agent_type": "base",
  "metadata": {
    "name": "Minimal Agent",
    "description": "A minimal agent configuration for basic tasks",
    "tags": ["basic"]
  },
  "capabilities": {
    "model": "claude-3-haiku-20240307",
    "tools": ["Read"],
    "resource_tier": "lightweight"
  },
  "instructions": "You are a basic assistant that can read files and provide information. Always be helpful and concise in your responses. Focus on accuracy and clarity."
}
```

### 2. Fully Featured Configuration

A comprehensive agent with all optional fields:

```json
{
  "schema_version": "1.2.0",
  "agent_id": "advanced_research_agent",
  "agent_version": "2.3.1",
  "agent_type": "research",
  "metadata": {
    "name": "Advanced Research Agent",
    "description": "Comprehensive code analysis with tree-sitter AST parsing and pattern detection",
    "category": "research",
    "tags": ["research", "analysis", "ast", "tree-sitter", "patterns"],
    "author": "Claude MPM Team",
    "created_at": "2025-07-01T10:00:00Z",
    "updated_at": "2025-07-27T15:30:00Z"
  },
  "capabilities": {
    "model": "claude-opus-4-20250514",
    "tools": ["Read", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"],
    "resource_tier": "intensive",
    "max_tokens": 16384,
    "temperature": 0.2,
    "timeout": 1800,
    "memory_limit": 8192,
    "cpu_limit": 90,
    "network_access": true,
    "file_access": {
      "read_paths": ["./src", "./tests", "./docs"],
      "write_paths": ["./analysis", "./reports"]
    },
    "allowed_tools": ["src/**/*.ts", "src/**/*.js"],
    "disallowed_tools": ["Bash", "Write"]
  },
  "instructions": "# Advanced Research Agent\n\nYou are an expert code analyst specializing in tree-sitter AST parsing...",
  "knowledge": {
    "domain_expertise": [
      "Tree-sitter AST parsing",
      "Design pattern recognition",
      "Code complexity analysis",
      "Security vulnerability detection"
    ],
    "best_practices": [
      "Always perform incremental analysis",
      "Cache parsed ASTs for performance",
      "Validate findings with multiple passes"
    ],
    "constraints": [
      "Cannot modify code directly",
      "Limited to read-only operations",
      "Must respect file access restrictions"
    ],
    "examples": [
      {
        "scenario": "Analyze React component patterns",
        "approach": "Use tree-sitter to parse JSX, identify component hierarchies"
      }
    ]
  },
  "interactions": {
    "input_format": {
      "required_fields": ["target_path", "analysis_type"],
      "optional_fields": ["depth", "filters", "output_format"]
    },
    "output_format": {
      "structure": "structured",
      "includes": ["summary", "findings", "recommendations", "metrics"]
    },
    "handoff_agents": ["engineer_agent", "security_agent"],
    "triggers": [
      {
        "condition": "security_vulnerability_found",
        "action": "handoff_to_security_agent"
      }
    ]
  },
  "testing": {
    "test_cases": [
      {
        "name": "Basic TypeScript Analysis",
        "input": "Analyze TypeScript patterns in src/",
        "expected_behavior": "Identifies interfaces, classes, and patterns",
        "validation_criteria": [
          "finds_all_interfaces",
          "detects_inheritance",
          "identifies_patterns"
        ]
      }
    ],
    "performance_benchmarks": {
      "response_time": 500,
      "token_usage": 12000,
      "success_rate": 0.98
    }
  },
  "hooks": {
    "pre_execution": [
      {"name": "validate_paths", "enabled": true},
      {"name": "check_permissions", "enabled": true}
    ],
    "post_execution": [
      {"name": "cache_results", "enabled": true},
      {"name": "log_metrics", "enabled": true}
    ]
  }
}
```

### 3. Specialized Agent Examples

#### QA Agent
```json
{
  "schema_version": "1.2.0",
  "agent_id": "qa_test_writer",
  "agent_version": "1.2.0",
  "agent_type": "qa",
  "metadata": {
    "name": "QA Test Writer",
    "description": "Automated test generation and validation for code quality",
    "category": "quality",
    "tags": ["testing", "qa", "automation", "validation"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
    "resource_tier": "standard",
    "max_tokens": 8192,
    "temperature": 0.1,
    "timeout": 600,
    "file_access": {
      "read_paths": ["./src", "./tests"],
      "write_paths": ["./tests"]
    }
  },
  "instructions": "You are a QA specialist focused on writing comprehensive test suites..."
}
```

#### Security Agent
```json
{
  "schema_version": "1.2.0",
  "agent_id": "security_scanner",
  "agent_version": "1.0.0",
  "agent_type": "security",
  "metadata": {
    "name": "Security Scanner",
    "description": "Vulnerability detection and security analysis specialist",
    "tags": ["security", "vulnerability", "scanning"]
  },
  "capabilities": {
    "model": "claude-opus-4-20250514",
    "tools": ["Read", "Grep", "Glob", "WebSearch"],
    "resource_tier": "intensive",
    "network_access": true,
    "disallowed_tools": ["Write", "Edit", "Bash"]
  },
  "instructions": "You are a security expert specializing in vulnerability detection..."
}
```

## Invalid Agent Configurations

### 1. Missing Required Fields

```json
{
  "schema_version": "1.2.0",
  "agent_id": "incomplete_agent",
  "metadata": {
    "name": "Incomplete Agent",
    "tags": ["broken"]
  }
}
```
**Errors**:
- Missing required field: `agent_version`
- Missing required field: `agent_type`
- Missing required field: `metadata.description`
- Missing required field: `capabilities`
- Missing required field: `instructions`

### 2. Pattern Validation Failures

```json
{
  "schema_version": "1.2",              // Invalid: Missing patch version
  "agent_id": "Invalid-Agent-ID",       // Invalid: Uppercase and hyphens
  "agent_version": "v1.0.0",            // Invalid: Has 'v' prefix
  "agent_type": "base",
  "metadata": {
    "name": "x",                        // Invalid: Too short (min 3)
    "description": "Too short",         // Invalid: Too short (min 10)
    "tags": ["INVALID_TAG", "tag!"]     // Invalid: Uppercase and special char
  },
  "capabilities": {
    "model": "claude-3-haiku-20240307",
    "tools": ["Read"],
    "resource_tier": "basic"
  },
  "instructions": "Short"               // Invalid: Too short (min 100)
}
```

### 3. Enum Validation Failures

```json
{
  "schema_version": "1.2.0",
  "agent_id": "enum_fail_agent",
  "agent_version": "1.0.0",
  "agent_type": "custom_type",          // Invalid: Not in enum
  "metadata": {
    "name": "Enum Fail Agent",
    "description": "Agent with invalid enum values",
    "category": "invalid_category",     // Invalid: Not in enum
    "tags": ["testing"]
  },
  "capabilities": {
    "model": "gpt-4",                   // Invalid: Not a Claude model
    "tools": ["Read", "CustomTool"],    // Invalid: CustomTool not in enum
    "resource_tier": "extreme"          // Invalid: Not in enum
  },
  "instructions": "This agent has invalid enum values throughout..."
}
```

### 4. Type Validation Failures

```json
{
  "schema_version": "1.2.0",
  "agent_id": "type_fail_agent",
  "agent_version": "1.0.0",
  "agent_type": "base",
  "metadata": {
    "name": "Type Fail Agent",
    "description": "Agent with type mismatches",
    "tags": "should-be-array"           // Invalid: Should be array
  },
  "capabilities": {
    "model": "claude-3-haiku-20240307",
    "tools": "Read",                    // Invalid: Should be array
    "resource_tier": "basic",
    "max_tokens": "8192",               // Invalid: Should be integer
    "temperature": "0.5",               // Invalid: Should be number
    "timeout": -1,                      // Invalid: Below minimum
    "network_access": "yes"             // Invalid: Should be boolean
  },
  "instructions": 123                   // Invalid: Should be string
}
```

### 5. Constraint Validation Failures

```json
{
  "schema_version": "1.2.0",
  "agent_id": "constraint_fail",
  "agent_version": "1.0.0",
  "agent_type": "base",
  "metadata": {
    "name": "This is a very long name that exceeds the fifty character limit",
    "description": "Valid description for the agent",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", 
             "tag6", "tag7", "tag8", "tag9", "tag10", "tag11"]  // Too many tags
  },
  "capabilities": {
    "model": "claude-3-haiku-20240307",
    "tools": ["Read", "Read"],          // Duplicate tools
    "resource_tier": "basic",
    "max_tokens": 500,                  // Below minimum (1000)
    "temperature": 1.5,                 // Above maximum (1.0)
    "timeout": 5000                     // Above maximum (3600)
  },
  "instructions": "a".repeat(8001)     // Exceeds maximum length (8000)
}
```

### 6. Additional Properties

```json
{
  "schema_version": "1.2.0",
  "agent_id": "extra_props_agent",
  "agent_version": "1.0.0",
  "agent_type": "base",
  "custom_field": "not allowed",        // Invalid: Additional property
  "metadata": {
    "name": "Extra Props Agent",
    "description": "Agent with additional properties",
    "tags": ["testing"],
    "custom_metadata": "not allowed"    // Invalid: Additional property
  },
  "capabilities": {
    "model": "claude-3-haiku-20240307",
    "tools": ["Read"],
    "resource_tier": "basic",
    "custom_capability": true           // Invalid: Additional property
  },
  "instructions": "Agent with extra properties that are not allowed"
}
```

## Common Validation Patterns

### Valid Patterns

#### Agent IDs
✅ `research_agent`
✅ `qa_test_runner`
✅ `security_scanner_v2`
✅ `data_pipeline_agent`

❌ `Research-Agent` (uppercase, hyphen)
❌ `2_agent` (starts with number)
❌ `agent-name` (hyphen)
❌ `Agent_Name` (uppercase)

#### Version Strings
✅ `1.0.0`
✅ `2.3.1`
✅ `10.20.30`

❌ `1.0` (missing patch)
❌ `v1.0.0` (has prefix)
❌ `1.0.0-beta` (has suffix)
❌ `1.0.0.0` (too many parts)

#### Tags
✅ `security`
✅ `code-analysis`
✅ `ast-parser`
✅ `pattern-detection`

❌ `Security` (uppercase)
❌ `code_analysis` (underscore)
❌ `ast!parser` (special char)
❌ `2fa` (starts with number)

## Validation Testing Script

Use this Python script to validate your agent configurations:

```python
import json
from pathlib import Path
from claude_mpm.validation.agent_validator import AgentValidator

def validate_agent_file(file_path):
    """Validate an agent configuration file."""
    with open(file_path, 'r') as f:
        agent_config = json.load(f)
    
    validator = AgentValidator()
    is_valid, errors = validator.validate(agent_config)
    
    if is_valid:
        print(f"✅ {file_path.name} is valid!")
    else:
        print(f"❌ {file_path.name} has errors:")
        for error in errors:
            print(f"  - {error}")
    
    return is_valid

# Validate all agent templates
templates_dir = Path("src/claude_mpm/agents/templates")
for template_file in templates_dir.glob("*.json"):
    validate_agent_file(template_file)
```

## Best Practices Summary

1. **Always validate** agent configurations before deployment
2. **Use descriptive IDs** that reflect the agent's purpose
3. **Follow semantic versioning** for both schema and agents
4. **Keep instructions focused** and under 8000 characters
5. **Match resource tiers** to actual agent requirements
6. **Test configurations** with the validation tools
7. **Document changes** when updating agent versions