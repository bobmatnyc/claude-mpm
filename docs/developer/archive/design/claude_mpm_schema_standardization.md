# Claude MPM Agent Schema Standardization

**Document Version:** 1.0  
**Date:** July 26, 2025  
**Status:** Implementation Ready  
**Authors:** Claude MPM Development Team  

## Executive Summary

This document focuses exclusively on standardizing the Claude MPM agent schema to ensure predictable and consistent agent behavior. The goal is to establish a solid foundation with complete, validated agent definitions before implementing advanced features.

## Current Schema Issues Analysis

### Critical Inconsistencies Found

1. **Versioning Chaos**
   ```json
   // Mixed approaches across agents
   "version": 2,        // engineer_agent.json (integer)
   "version": 3,        // documentation_agent.json (integer) 
   "version": 5,        // research_agent.json (integer)
   // No semantic versioning, no correlation to actual changes
   ```

2. **Model Naming Inconsistency**
   ```json
   // Different model naming conventions
   "model": "claude-4-sonnet-20250514",     // Some agents
   "model": "claude-sonnet-4-20250514",    // Other agents
   // Should standardize on one format
   ```

3. **Resource Allocation Inconsistency**
   ```json
   // Timeout variations without clear rationale
   "timeout": 600,    // Most agents
   "timeout": 900,    // research_agent.json
   "timeout": 1200,   // engineer_agent.json
   
   // Memory variations without clear rationale  
   "memory_limit": 2048,  // Most agents
   "memory_limit": 3072,  // Some agents
   ```

4. **Missing Required Fields**
   ```json
   // No tracking fields
   // No unique identifiers
   // No compatibility metadata
   // No validation metadata
   ```

5. **Tool Array Inconsistencies**
   ```json
   // Different tool combinations without clear reasoning
   "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"],  // Some
   "tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"], // Others
   ```

## Standardized Schema Definition

### Core Schema Structure

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Claude MPM Agent Definition Standard v1.0",
  "description": "Standardized schema for Claude MPM agent definitions",
  "type": "object",
  "required": ["schema_version", "agent_id", "agent_version", "agent_type", "metadata", "capabilities", "configuration"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0.0",
      "description": "Schema version for validation and migration"
    },
    "agent_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*[a-z0-9]$",
      "description": "Unique agent identifier (snake_case)"
    },
    "agent_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Agent definition version (semantic versioning)"
    },
    "agent_type": {
      "type": "string",
      "enum": ["research", "engineer", "qa", "security", "documentation", "ops", "data_engineer", "version_control"],
      "description": "Primary agent classification"
    },
    "metadata": {
      "type": "object",
      "required": ["name", "description", "created_at", "updated_at"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "minLength": 5,
          "maxLength": 50,
          "description": "Human-readable agent name"
        },
        "description": {
          "type": "string",
          "minLength": 20,
          "maxLength": 200,
          "description": "Clear description of agent purpose and capabilities"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 timestamp of creation"
        },
        "updated_at": {
          "type": "string", 
          "format": "date-time",
          "description": "ISO 8601 timestamp of last update"
        },
        "tags": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z0-9-]+$"
          },
          "uniqueItems": true,
          "minItems": 2,
          "maxItems": 8,
          "description": "Descriptive tags for categorization"
        },
        "specializations": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z0-9-]+$"
          },
          "uniqueItems": true,
          "minItems": 2,
          "maxItems": 6,
          "description": "Primary areas of specialization"
        }
      }
    },
    "capabilities": {
      "type": "object",
      "required": ["when_to_use", "specialized_knowledge", "unique_capabilities"],
      "additionalProperties": false,
      "properties": {
        "when_to_use": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 10,
            "maxLength": 100
          },
          "minItems": 3,
          "maxItems": 8,
          "description": "Clear criteria for when to select this agent"
        },
        "specialized_knowledge": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 10,
            "maxLength": 80
          },
          "minItems": 3,
          "maxItems": 8,
          "description": "Domain-specific knowledge areas"
        },
        "unique_capabilities": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 15,
            "maxLength": 100
          },
          "minItems": 3,
          "maxItems": 8,
          "description": "Unique value propositions of this agent"
        }
      }
    },
    "configuration": {
      "type": "object",
      "required": ["model", "tools", "parameters", "limits"],
      "additionalProperties": false,
      "properties": {
        "model": {
          "type": "string",
          "enum": [
            "claude-4-sonnet-20250514",
            "claude-4-opus-20250514", 
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229"
          ],
          "description": "Claude model to use (standardized naming)"
        },
        "tools": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "Read", "Write", "Edit", "MultiEdit", 
              "Bash", "Grep", "Glob", "LS",
              "WebSearch", "WebFetch", "TodoWrite"
            ]
          },
          "uniqueItems": true,
          "minItems": 3,
          "description": "Available tools for this agent"
        },
        "parameters": {
          "type": "object",
          "required": ["temperature", "max_tokens"],
          "additionalProperties": false,
          "properties": {
            "temperature": {
              "type": "number",
              "minimum": 0.0,
              "maximum": 1.0,
              "multipleOf": 0.01,
              "description": "Model temperature (0.00-1.00)"
            },
            "max_tokens": {
              "type": "integer",
              "enum": [4096, 8192, 12288, 16384],
              "description": "Maximum tokens per response"
            }
          }
        },
        "limits": {
          "type": "object",
          "required": ["timeout", "memory_limit", "cpu_limit"],
          "additionalProperties": false,
          "properties": {
            "timeout": {
              "type": "integer",
              "minimum": 60,
              "maximum": 1800,
              "multipleOf": 60,
              "description": "Execution timeout in seconds (60-1800, multiples of 60)"
            },
            "memory_limit": {
              "type": "integer",
              "enum": [1024, 2048, 3072, 4096],
              "description": "Memory limit in MB"
            },
            "cpu_limit": {
              "type": "integer",
              "minimum": 10,
              "maximum": 100,
              "multipleOf": 10,
              "description": "CPU limit percentage (10-100, multiples of 10)"
            }
          }
        },
        "permissions": {
          "type": "object",
          "required": ["file_access", "network_access", "dangerous_tools"],
          "additionalProperties": false,
          "properties": {
            "file_access": {
              "type": "string",
              "enum": ["none", "read_only", "project_only", "full"],
              "description": "File system access level"
            },
            "network_access": {
              "type": "boolean",
              "description": "Whether agent can access network resources"
            },
            "dangerous_tools": {
              "type": "boolean",
              "description": "Whether agent can use potentially dangerous tools"
            }
          }
        }
      }
    },
    "instructions": {
      "type": "string",
      "minLength": 200,
      "maxLength": 5000,
      "description": "Detailed agent instructions in markdown format"
    }
  }
}
```

## Standardized Agent Resource Tiers

### Resource Allocation Rationale

```json
{
  "resource_tiers": {
    "lightweight": {
      "description": "Simple, fast operations with minimal resources",
      "timeout": 300,
      "memory_limit": 1024,
      "cpu_limit": 30,
      "max_tokens": 4096,
      "suitable_for": ["version_control", "documentation"]
    },
    "standard": {
      "description": "Balanced resources for typical operations",
      "timeout": 600,
      "memory_limit": 2048,
      "cpu_limit": 50,
      "max_tokens": 8192,
      "suitable_for": ["qa", "ops", "security", "data_engineer"]
    },
    "intensive": {
      "description": "High-resource operations requiring deep analysis",
      "timeout": 900,
      "memory_limit": 3072,
      "cpu_limit": 70,
      "max_tokens": 12288,
      "suitable_for": ["research", "engineer"]
    }
  }
}
```

### Tool Assignment Rationale

```json
{
  "tool_assignments": {
    "core_tools": {
      "description": "Essential tools for all agents",
      "tools": ["Read", "TodoWrite"],
      "rationale": "All agents need to read files and track tasks"
    },
    "implementation_tools": {
      "description": "Tools for agents that create/modify code",
      "tools": ["Write", "Edit", "MultiEdit"],
      "suitable_for": ["engineer", "data_engineer", "ops"]
    },
    "analysis_tools": {
      "description": "Tools for agents that analyze existing content", 
      "tools": ["Grep", "Glob", "LS"],
      "suitable_for": ["research", "qa", "security", "documentation"]
    },
    "execution_tools": {
      "description": "Tools for agents that need to run commands",
      "tools": ["Bash"],
      "suitable_for": ["engineer", "ops", "qa", "version_control"]
    },
    "research_tools": {
      "description": "Tools for agents that need external information",
      "tools": ["WebSearch", "WebFetch"],
      "suitable_for": ["research", "security", "documentation"]
    }
  }
}
```

## Standardized Agent Definitions

### Research Agent (Tier: Intensive)

```json
{
  "schema_version": "1.0.0",
  "agent_id": "research_agent",
  "agent_version": "1.0.0",
  "agent_type": "research",
  "metadata": {
    "name": "Research Agent",
    "description": "Conducts comprehensive technical investigation and codebase analysis using tree-sitter for implementation guidance",
    "created_at": "2025-07-26T00:00:00Z",
    "updated_at": "2025-07-26T00:00:00Z",
    "tags": ["research", "analysis", "tree-sitter", "codebase", "investigation"],
    "specializations": ["tree-sitter-analysis", "pattern-recognition", "technical-research", "codebase-analysis"]
  },
  "capabilities": {
    "when_to_use": [
      "Pre-implementation codebase analysis with tree-sitter",
      "Technical pattern discovery and architectural assessment", 
      "Integration requirements and dependency mapping",
      "Code quality and security posture evaluation",
      "Best practices synthesis for implementation guidance"
    ],
    "specialized_knowledge": [
      "Tree-sitter AST analysis and code structure extraction",
      "Dependency graph analysis and circular dependency detection",
      "Security pattern recognition and vulnerability assessment",
      "Performance pattern identification and optimization opportunities",
      "Testing infrastructure analysis and coverage assessment"
    ],
    "unique_capabilities": [
      "Generate hierarchical code summaries optimized for LLM consumption",
      "Extract semantic patterns from AST structures using tree-sitter",
      "Identify critical integration points and API surfaces",
      "Synthesize agent-specific actionable insights from codebase analysis",
      "Create token-efficient context for specialized agent delegation"
    ]
  },
  "configuration": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "TodoWrite"],
    "parameters": {
      "temperature": 0.20,
      "max_tokens": 12288
    },
    "limits": {
      "timeout": 900,
      "memory_limit": 3072,
      "cpu_limit": 60
    },
    "permissions": {
      "file_access": "project_only",
      "network_access": true,
      "dangerous_tools": false
    }
  },
  "instructions": "# Research Agent - CODEBASE ANALYSIS SPECIALIST\n\nConduct comprehensive codebase analysis using tree-sitter to generate hierarchical summaries optimized for LLM consumption and agent delegation.\n\n## Core Analysis Protocol\n\n### Phase 1: Repository Structure Analysis (5 min)\n```bash\nfind . -name \"*.ts\" -o -name \"*.js\" -o -name \"*.py\" | head -20\ntree -I 'node_modules|.git|dist' -L 3\n```\n\n### Phase 2: Tree-sitter Structural Extraction (10-15 min)\n```bash\ntree-sitter parse [file] --quiet | grep -E \"(function_declaration|class_declaration)\"\n```\n\n### Phase 3: Pattern Detection (5-10 min) \n```bash\ngrep -r \"async\\|await\\|Promise\" --include=\"*.ts\" --include=\"*.js\" .\ngrep -r \"try.*catch\\|throw\\|Error\" --include=\"*.ts\" --include=\"*.js\" .\n```\n\n### Phase 4: Generate Hierarchical Summary\nProduce token-efficient analysis with agent-specific insights for implementation guidance.\n\n## Analysis Quality Standards\n- Token budget <2K for hierarchical summary\n- Agent-specific actionable insights\n- File paths and line numbers for reference\n- Security and performance concerns highlighted\n- Clear implementation recommendations"
}
```

### Engineer Agent (Tier: Intensive)

```json
{
  "schema_version": "1.0.0", 
  "agent_id": "engineer_agent",
  "agent_version": "1.0.0",
  "agent_type": "engineer",
  "metadata": {
    "name": "Engineer Agent",
    "description": "Implements production-ready code following research-identified patterns and established conventions",
    "created_at": "2025-07-26T00:00:00Z",
    "updated_at": "2025-07-26T00:00:00Z",
    "tags": ["engineering", "implementation", "coding", "development", "production"],
    "specializations": ["implementation", "debugging", "refactoring", "optimization"]
  },
  "capabilities": {
    "when_to_use": [
      "Code implementation following tree-sitter research analysis",
      "Bug fixes with research-identified patterns and constraints",
      "Refactoring based on AST analysis and architectural insights",
      "Feature implementation with research-validated approaches",
      "Integration work following dependency and pattern analysis"
    ],
    "specialized_knowledge": [
      "Implementation patterns derived from tree-sitter analysis",
      "Codebase-specific conventions and architectural decisions",
      "Integration constraints and dependency requirements",
      "Security patterns and vulnerability mitigation techniques",
      "Performance optimization based on code structure analysis"
    ],
    "unique_capabilities": [
      "Implement code following research-identified patterns and constraints",
      "Apply codebase-specific conventions discovered through AST analysis",
      "Integrate with existing architecture based on dependency mapping",
      "Implement security measures targeting research-identified vulnerabilities",
      "Optimize performance based on tree-sitter pattern analysis"
    ]
  },
  "configuration": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "TodoWrite"],
    "parameters": {
      "temperature": 0.05,
      "max_tokens": 12288
    },
    "limits": {
      "timeout": 900,
      "memory_limit": 3072,
      "cpu_limit": 70
    },
    "permissions": {
      "file_access": "project_only",
      "network_access": true,
      "dangerous_tools": false
    }
  },
  "instructions": "# Engineer Agent - RESEARCH-GUIDED IMPLEMENTATION\n\nImplement code solutions based on tree-sitter research analysis and codebase pattern discovery. Focus on production-quality implementation that adheres to discovered patterns and constraints.\n\n## Implementation Protocol\n\n### Phase 1: Research Validation (2-3 min)\n- Verify Research Context: Confirm tree-sitter analysis findings are current\n- Pattern Confirmation: Validate discovered patterns against current codebase\n- Constraint Assessment: Understand integration requirements and limitations\n- Security Review: Note research-identified security concerns\n\n### Phase 2: Implementation Planning (3-5 min)\n- Pattern Adherence: Follow established codebase conventions\n- Integration Strategy: Plan implementation based on dependency analysis  \n- Error Handling: Implement comprehensive error handling matching patterns\n- Testing Approach: Align with research-identified testing infrastructure\n\n### Phase 3: Code Implementation (15-30 min)\n- Follow research-identified patterns and conventions\n- Implement comprehensive error handling\n- Include proper documentation and typing\n- Ensure integration compatibility\n\n### Phase 4: Quality Assurance (5-10 min)\n- Pattern Compliance: Ensure implementation matches research findings\n- Integration Testing: Verify compatibility with existing codebase\n- Security Validation: Address research-identified security concerns\n- Performance Check: Optimize based on research patterns"
}
```

### QA Agent (Tier: Standard)

```json
{
  "schema_version": "1.0.0",
  "agent_id": "qa_agent", 
  "agent_version": "1.0.0",
  "agent_type": "qa",
  "metadata": {
    "name": "QA Agent",
    "description": "Validates implementation quality through systematic testing and comprehensive analysis",
    "created_at": "2025-07-26T00:00:00Z",
    "updated_at": "2025-07-26T00:00:00Z", 
    "tags": ["qa", "testing", "quality", "validation", "coverage"],
    "specializations": ["testing", "validation", "quality-metrics", "coverage-analysis"]
  },
  "capabilities": {
    "when_to_use": [
      "Testing validation after implementation",
      "Quality metrics assessment and coverage analysis",
      "Test coverage analysis and gap identification",
      "Performance validation against requirements",
      "Regression testing coordination and execution"
    ],
    "specialized_knowledge": [
      "Testing frameworks and methodologies across languages",
      "Quality assurance standards and best practices",
      "Test automation strategies and implementation",
      "Performance testing techniques and benchmarking",
      "Coverage analysis methods and interpretation"
    ],
    "unique_capabilities": [
      "Execute comprehensive test validation with detailed reporting",
      "Analyze test coverage and quality metrics systematically",
      "Identify testing gaps and edge cases proactively",
      "Validate performance against specified requirements",
      "Coordinate regression testing processes efficiently"
    ]
  },
  "configuration": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "TodoWrite"],
    "parameters": {
      "temperature": 0.05,
      "max_tokens": 8192
    },
    "limits": {
      "timeout": 600,
      "memory_limit": 2048,
      "cpu_limit": 50
    },
    "permissions": {
      "file_access": "project_only",
      "network_access": false,
      "dangerous_tools": false
    }
  },
  "instructions": "# QA Agent\n\nValidate implementation quality through systematic testing and analysis. Focus on comprehensive testing coverage and quality metrics.\n\n## Testing Protocol\n\n### Phase 1: Test Execution (10-15 min)\n- Run comprehensive test suites with detailed analysis\n- Execute unit, integration, and end-to-end tests\n- Document test results with pass/fail metrics\n- Identify any test failures or errors\n\n### Phase 2: Coverage Analysis (5-10 min)\n- Ensure adequate testing scope and identify gaps\n- Analyze code coverage metrics and reports\n- Identify untested code paths and edge cases\n- Recommend additional test scenarios\n\n### Phase 3: Quality Assessment (5-10 min)\n- Validate against acceptance criteria and standards\n- Check code quality metrics and standards compliance\n- Assess error handling and edge case coverage\n- Evaluate test maintainability and clarity\n\n### Phase 4: Performance Testing (5-10 min)\n- Verify system performance under various conditions\n- Run performance benchmarks and load tests\n- Validate response times and resource usage\n- Document performance characteristics\n\n## Quality Standards\n- Systematic test execution and validation\n- Comprehensive coverage analysis and reporting\n- Performance and regression testing coordination\n- Clear documentation of quality metrics and recommendations"
}
```

## Schema Validation Framework

### Validation Rules Implementation

```python
import jsonschema
import json
from datetime import datetime
from typing import Dict, List, Optional

class AgentSchemaValidator:
    """Validates agent definitions against the standardized schema."""
    
    def __init__(self, schema_path: str):
        """Initialize validator with schema file."""
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        self.validator = jsonschema.Draft7Validator(self.schema)
    
    def validate_agent(self, agent_definition: Dict) -> ValidationResult:
        """Validate a single agent definition."""
        
        errors = []
        warnings = []
        
        # Schema validation
        schema_errors = list(self.validator.iter_errors(agent_definition))
        errors.extend([f"Schema: {error.message}" for error in schema_errors])
        
        # Business rule validation
        business_warnings = self._validate_business_rules(agent_definition)
        warnings.extend(business_warnings)
        
        # Consistency validation
        consistency_warnings = self._validate_consistency(agent_definition)
        warnings.extend(consistency_warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            agent_id=agent_definition.get('agent_id', 'unknown')
        )
    
    def _validate_business_rules(self, agent: Dict) -> List[str]:
        """Validate business logic rules."""
        warnings = []
        
        # Resource tier consistency
        config = agent.get('configuration', {})
        limits = config.get('limits', {})
        
        timeout = limits.get('timeout', 0)
        memory = limits.get('memory_limit', 0)
        
        # Validate resource tier alignment
        if timeout >= 900 and memory < 3072:
            warnings.append("High timeout (900s+) should use intensive memory tier (3072MB+)")
        
        if memory >= 3072 and timeout < 900:
            warnings.append("High memory (3072MB+) should use intensive timeout tier (900s+)")
        
        # Tool assignment logic
        tools = config.get('tools', [])
        agent_type = agent.get('agent_type')
        
        if agent_type in ['engineer', 'data_engineer', 'ops'] and 'Write' not in tools:
            warnings.append(f"{agent_type} should have Write tool for implementation tasks")
        
        if agent_type == 'research' and 'WebSearch' not in tools:
            warnings.append("Research agent should have WebSearch tool for external information")
        
        # Temperature validation
        temp = config.get('parameters', {}).get('temperature', 0)
        if agent_type in ['engineer', 'qa', 'security'] and temp > 0.1:
            warnings.append(f"{agent_type} should use low temperature (≤0.1) for consistency")
        
        return warnings
    
    def _validate_consistency(self, agent: Dict) -> List[str]:
        """Validate internal consistency."""
        warnings = []
        
        metadata = agent.get('metadata', {})
        caps = agent.get('capabilities', {})
        
        # Check if specializations align with capabilities
        specializations = set(metadata.get('specializations', []))
        when_to_use = ' '.join(caps.get('when_to_use', [])).lower()
        
        for spec in specializations:
            if spec.replace('-', ' ') not in when_to_use:
                warnings.append(f"Specialization '{spec}' not reflected in when_to_use criteria")
        
        return warnings

class MigrationManager:
    """Manages migration from current format to standardized schema."""
    
    def migrate_v1_to_standard(self, v1_agent: Dict) -> Dict:
        """Migrate v1 agent definition to standardized format."""
        
        agent_type = v1_agent.get('agent_type', 'unknown')
        
        # Generate standard metadata
        standard_agent = {
            "schema_version": "1.0.0",
            "agent_id": f"{agent_type}_agent",
            "agent_version": "1.0.0",
            "agent_type": agent_type,
            "metadata": self._extract_metadata(v1_agent),
            "capabilities": self._extract_capabilities(v1_agent),
            "configuration": self._standardize_configuration(v1_agent),
            "instructions": self._extract_instructions(v1_agent)
        }
        
        return standard_agent
    
    def _extract_metadata(self, v1_agent: Dict) -> Dict:
        """Extract and standardize metadata."""
        narrative = v1_agent.get('narrative_fields', {})
        config = v1_agent.get('configuration_fields', {})
        
        return {
            "name": config.get('description', f"{v1_agent.get('agent_type', 'Unknown')} Agent"),
            "description": config.get('description', 'Migrated agent definition'),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": config.get('tags', []),
            "specializations": config.get('specializations', [])
        }
    
    def _standardize_configuration(self, v1_agent: Dict) -> Dict:
        """Standardize configuration format."""
        config = v1_agent.get('configuration_fields', {})
        agent_type = v1_agent.get('agent_type')
        
        # Apply resource tier based on agent type
        if agent_type in ['research', 'engineer']:
            tier = 'intensive'
            timeout, memory, cpu, tokens = 900, 3072, 70, 12288
        elif agent_type in ['qa', 'ops', 'security', 'data_engineer']:
            tier = 'standard'
            timeout, memory, cpu, tokens = 600, 2048, 50, 8192
        else:
            tier = 'lightweight'
            timeout, memory, cpu, tokens = 300, 1024, 30, 4096
        
        return {
            "model": self._standardize_model_name(config.get('model', 'claude-4-sonnet-20250514')),
            "tools": self._standardize_tools(config.get('tools', []), agent_type),
            "parameters": {
                "temperature": config.get('temperature', 0.1),
                "max_tokens": config.get('max_tokens', tokens)
            },
            "limits": {
                "timeout": config.get('timeout', timeout),
                "memory_limit": config.get('memory_limit', memory),
                "cpu_limit": config.get('cpu_limit', cpu)
            },
            "permissions": {
                "file_access": "project_only",
                "network_access": config.get('network_access', False),
                "dangerous_tools": config.get('dangerous_tools', False)
            }
        }
    
    def _standardize_model_name(self, model_name: str) -> str:
        """Standardize model naming convention."""
        # Map common variations to standard names
        model_mapping = {
            'claude-sonnet-4-20250514': 'claude-4-sonnet-20250514',
            'claude-4-sonnet': 'claude-4-sonnet-20250514',
            'claude-4-opus': 'claude-4-opus-20250514',
            'claude-3-5-sonnet': 'claude-3-5-sonnet-20241022'
        }
        
        return model_mapping.get(model_name, 'claude-4-sonnet-20250514')
```

## Implementation Plan

### Phase 1: Schema Definition (Week 1)
1. **Finalize Schema** - Complete schema validation rules
2. **Create Validation Tools** - Implement validation framework  
3. **Test Schema** - Validate against existing agents

### Phase 2: Agent Migration (Week 2) 
1. **Migrate Core Agents** - Research, Engineer, QA, Security
2. **Validate Migrations** - Ensure all agents pass validation
3. **Test Functionality** - Verify migrated agents work correctly

### Phase 3: Documentation & Deployment (Week 3)
1. **Create Documentation** - Schema guide and migration docs
2. **Update Build Process** - Integrate validation into CI/CD
3. **Deploy Standardized Agents** - Replace current definitions

## Quality Assurance

### Validation Checklist

- [ ] All agents validate against schema
- [ ] Resource tiers are consistently applied
- [ ] Tool assignments follow logical rules
- [ ] Model names are standardized
- [ ] Metadata is complete and accurate
- [ ] Instructions are clear and comprehensive
- [ ] Migration preserves functionality
- [ ] Performance characteristics are maintained

### Success Criteria

1. **100% Schema Compliance** - All agents validate without errors
2. **Consistent Resource Allocation** - Clear rationale for all resource decisions
3. **Predictable Behavior** - Agents behave according to their definitions
4. **Maintainable Definitions** - Easy to understand and modify
5. **Migration Success** - All existing functionality preserved

## Conclusion

This schema standardization provides a solid foundation for predictable agent behavior. By focusing on consistency and completeness first, we ensure that agents perform reliably before adding advanced features.

The standardized schema eliminates ambiguity, provides clear validation rules, and establishes consistent patterns that make the system more maintainable and reliable.