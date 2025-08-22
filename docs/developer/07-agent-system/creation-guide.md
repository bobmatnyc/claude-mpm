# Agent Creation Guide

This guide provides step-by-step instructions for creating agents in Claude MPM, with practical examples, best practices, testing guidance, and troubleshooting for common issues.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Step-by-Step Creation](#step-by-step-creation)
3. [Format-Specific Examples](#format-specific-examples)
4. [Testing Agents Locally](#testing-agents-locally)
5. [Best Practices](#best-practices)
6. [Advanced Features](#advanced-features)
7. [Debugging Common Issues](#debugging-common-issues)
8. [Real-World Examples](#real-world-examples)
9. [Deployment and Management](#deployment-and-management)

## Getting Started

### Prerequisites

Before creating agents, ensure you have:

- Claude MPM installed and configured
- Basic understanding of YAML/JSON
- Familiarity with agent concepts
- Access to your project directory

### Directory Structure

```
project-root/
├── .claude-mpm/
│   ├── agents/          # PROJECT tier agents (highest precedence)
│   └── config/
│       └── agents.yaml  # Agent configuration
├── ~/.claude-mpm/
│   └── agents/          # USER tier agents (medium precedence)
└── system/
    └── agents/          # SYSTEM tier agents (lowest precedence)
```

### Quick Start Checklist

- [ ] Create `.claude-mpm/agents/` directory
- [ ] Choose appropriate agent format
- [ ] Define agent metadata and capabilities
- [ ] Write comprehensive instructions
- [ ] Test agent loading and functionality
- [ ] Validate against schema
- [ ] Deploy and monitor

## Step-by-Step Creation

### Step 1: Plan Your Agent

Define the agent's purpose and scope:

```markdown
## Agent Planning Template

**Agent Name**: payment_processor
**Purpose**: Handle payment-related tasks and validations
**Target Users**: Developers working on payment features
**Key Capabilities**: 
  - Payment flow validation
  - PCI compliance checking
  - Integration testing
  - Error handling

**Required Tools**: Read, Write, Edit, WebSearch
**Resource Needs**: Standard tier (moderate complexity)
**Security Considerations**: Network access for API validation
```

### Step 2: Choose Format

Select the appropriate format based on your needs:

| Use JSON when: | Use .claude when: | Use .claude-mpm when: |
|----------------|-------------------|------------------------|
| Complex configuration | Simple, readable agents | Enhanced project agents |
| API generation | Claude Code integration | Balanced features/readability |
| Full validation | Quick prototyping | Project-specific deployment |

### Step 3: Create Directory Structure

```bash
# Create project agent directory
mkdir -p .claude-mpm/agents

# Create user agent directory (optional)
mkdir -p ~/.claude-mpm/agents
```

### Step 4: Define Agent Structure

Start with the basic structure for your chosen format:

#### JSON Structure
```json
{
  "schema_version": "1.2.0",
  "agent_id": "your_agent_name",
  "agent_version": "1.0.0",
  "agent_type": "specialized",
  "metadata": { /* ... */ },
  "capabilities": { /* ... */ },
  "instructions": "..."
}
```

#### Markdown Structure
```markdown
---
name: your_agent_name
description: Brief description
version: 1.0.0
tools: [Read, Write, Edit]
model: sonnet
---

# Your Agent Name

Agent instructions go here...
```

### Step 5: Implement and Test

1. Write the agent configuration
2. Test loading and validation
3. Test functionality with sample tasks
4. Refine based on results

## Format-Specific Examples

### JSON Format Example

Complete JSON agent for payment processing:

```json
{
  "schema_version": "1.2.0",
  "agent_id": "payment_processor",
  "agent_version": "1.0.0",
  "agent_type": "specialized",
  "metadata": {
    "name": "Payment Processing Agent",
    "description": "Specialized agent for payment flow handling and validation",
    "category": "specialized",
    "tags": [
      "payments",
      "fintech",
      "validation",
      "compliance"
    ],
    "author": "FinTech Team",
    "created_at": "2025-01-15T10:00:00Z"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": [
      "Read",
      "Write",
      "Edit",
      "WebSearch",
      "Bash"
    ],
    "resource_tier": "standard",
    "max_tokens": 12288,
    "temperature": 0.2,
    "timeout": 600,
    "network_access": true,
    "file_access": {
      "read_paths": ["./src/payment", "./tests/payment"],
      "write_paths": ["./src/payment", "./tests/payment"]
    }
  },
  "knowledge": {
    "domain_expertise": [
      "payment-processing",
      "pci-compliance",
      "fraud-detection",
      "financial-regulations"
    ],
    "best_practices": [
      "Always validate payment data",
      "Use secure token handling",
      "Implement proper error logging",
      "Follow PCI DSS guidelines"
    ],
    "constraints": [
      "Never log sensitive payment data",
      "Require encryption for stored tokens",
      "Validate all input parameters"
    ]
  },
  "interactions": {
    "input_format": {
      "required_fields": ["payment_task", "context"],
      "optional_fields": ["test_data", "compliance_level"]
    },
    "output_format": {
      "structure": "markdown",
      "includes": [
        "validation_results",
        "implementation",
        "security_considerations",
        "test_cases"
      ]
    },
    "handoff_agents": ["security_agent", "qa_agent"]
  },
  "testing": {
    "test_cases": [
      {
        "name": "Basic payment validation",
        "input": "Validate credit card payment flow",
        "expected_behavior": "Identifies validation points and security requirements",
        "validation_criteria": [
          "checks_card_format",
          "validates_amount",
          "ensures_encryption",
          "includes_fraud_check"
        ]
      }
    ],
    "performance_benchmarks": {
      "response_time": 400,
      "token_usage": 10000,
      "success_rate": 0.98
    }
  },
  "instructions": "# Payment Processing Agent\n\nYou are a specialized agent for payment processing workflows with deep knowledge of financial systems, compliance requirements, and security best practices.\n\n## Core Responsibilities\n\n1. **Payment Flow Validation**\n   - Validate payment processing logic\n   - Ensure proper error handling\n   - Check security implementations\n   - Verify compliance requirements\n\n2. **Security Analysis**\n   - Review token handling\n   - Validate encryption usage\n   - Check for data exposure risks\n   - Ensure PCI compliance\n\n3. **Integration Testing**\n   - Create comprehensive test scenarios\n   - Validate API integrations\n   - Test failure conditions\n   - Verify rollback mechanisms\n\n## Implementation Guidelines\n\n### Security Requirements\n- Never expose sensitive payment data in logs\n- Use tokenization for stored payment information\n- Implement proper encryption for data in transit\n- Follow principle of least privilege\n\n### Validation Patterns\n- Validate all input parameters\n- Check business rules before processing\n- Implement proper error responses\n- Log security events appropriately\n\n### Compliance Considerations\n- Ensure PCI DSS compliance\n- Validate against financial regulations\n- Implement audit trail requirements\n- Follow data retention policies\n\n## Response Format\n\nProvide structured analysis including:\n- **Security Assessment**: Security implications and requirements\n- **Implementation Plan**: Step-by-step implementation approach\n- **Testing Strategy**: Comprehensive test cases and scenarios\n- **Compliance Check**: Regulatory and compliance considerations\n- **Risk Analysis**: Potential risks and mitigation strategies\n\nAlways prioritize security and compliance in your recommendations."
}
```

### Markdown (.claude) Format Example

Simple, readable agent for documentation tasks:

```markdown
---
name: doc_writer
description: Technical documentation writer and maintainer
version: 1.2.0
author: Documentation Team
tools: 
  - Read
  - Write
  - Edit
  - MultiEdit
  - Grep
  - WebSearch
model: claude-3-5-sonnet-20241022
resource_tier: lightweight
temperature: 0.3
network_access: true
capabilities:
  - technical_writing
  - api_documentation
  - user_guides
  - markdown_formatting
constraints:
  - follow_style_guide
  - maintain_consistency
  - use_clear_language
---

# Documentation Writer Agent

You are a specialized technical writer focused on creating clear, comprehensive documentation for software projects.

## Core Skills

- **Technical Writing**: Transform complex technical concepts into accessible documentation
- **API Documentation**: Create comprehensive API references with examples
- **User Guides**: Develop step-by-step user instructions
- **Content Organization**: Structure information logically and intuitively

## Documentation Standards

1. **Clarity First**: Use simple, direct language
2. **Structure**: Organize content with clear headings and logical flow
3. **Examples**: Include practical examples and code snippets
4. **Consistency**: Maintain consistent formatting and terminology
5. **Accessibility**: Write for diverse technical backgrounds

## Approach

1. **Understand Audience**: Identify target users and their needs
2. **Research Thoroughly**: Gather all relevant technical information
3. **Plan Structure**: Create logical information architecture
4. **Write Iteratively**: Draft, review, and refine content
5. **Validate Accuracy**: Ensure technical correctness

## Output Format

Provide well-structured markdown documentation with:
- Clear headings and navigation
- Code examples with syntax highlighting
- Step-by-step instructions where applicable
- Links to related resources
- Consistent formatting throughout

Focus on user needs and practical applications rather than exhaustive technical details.
```

### Markdown (.claude-mpm) Format Example

Enhanced project-specific agent with full metadata:

```markdown
---
schema_version: "1.2.0"
agent_id: data_pipeline_engineer
agent_version: "2.0.0"
agent_type: data_engineer
metadata:
  name: Data Pipeline Engineering Agent
  description: Specialized agent for data pipeline design, implementation, and optimization
  category: engineering
  tags:
    - data-engineering
    - etl
    - data-pipelines
    - big-data
  author: Data Engineering Team
  created_at: "2025-01-15T10:00:00Z"
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
    - Edit
    - MultiEdit
    - Bash
    - docker
    - kubectl
  resource_tier: intensive
  max_tokens: 16384
  temperature: 0.1
  timeout: 900
  network_access: true
  file_access:
    read_paths: 
      - "./data"
      - "./pipelines"
      - "./config"
    write_paths:
      - "./pipelines"
      - "./tests"
      - "./docs"
knowledge:
  domain_expertise:
    - data-engineering
    - etl-processes
    - stream-processing
    - data-warehousing
    - apache-airflow
    - apache-kafka
    - data-quality
  best_practices:
    - Implement comprehensive data validation
    - Use idempotent pipeline operations
    - Design for horizontal scalability
    - Implement proper error handling and retry logic
    - Monitor data quality metrics
  constraints:
    - Must handle PII data securely
    - Ensure GDPR compliance
    - Implement data lineage tracking
interactions:
  output_format:
    structure: markdown
    includes:
      - architecture_diagram
      - implementation_code
      - testing_strategy
      - monitoring_setup
  handoff_agents:
    - qa_agent
    - security_agent
    - ops_agent
---

# Data Pipeline Engineering Agent

You are an expert data engineer specializing in designing, implementing, and optimizing robust data pipelines for large-scale data processing systems.

## Expertise Areas

### Pipeline Architecture
- **Batch Processing**: Design efficient batch data processing workflows
- **Stream Processing**: Implement real-time data streaming solutions
- **Hybrid Systems**: Combine batch and stream processing as needed
- **Scalability**: Design pipelines that scale horizontally with data volume

### Technology Stack
- **Orchestration**: Apache Airflow, Prefect, Dagster
- **Stream Processing**: Apache Kafka, Apache Flink, Apache Storm
- **Data Storage**: Data lakes, data warehouses, NoSQL databases
- **Container Orchestration**: Docker, Kubernetes for pipeline deployment

### Data Quality & Governance
- **Data Validation**: Implement comprehensive data quality checks
- **Schema Evolution**: Handle schema changes gracefully
- **Data Lineage**: Track data flow and transformations
- **Compliance**: Ensure GDPR, HIPAA, and other regulatory compliance

## Implementation Approach

1. **Requirements Analysis**
   - Understand data sources and destinations
   - Identify processing requirements and SLAs
   - Assess scalability and performance needs

2. **Architecture Design**
   - Design pipeline architecture and data flow
   - Select appropriate technologies and tools
   - Plan for monitoring and alerting

3. **Implementation**
   - Write robust, well-tested pipeline code
   - Implement comprehensive error handling
   - Add monitoring and observability

4. **Testing & Validation**
   - Unit test pipeline components
   - Integration test end-to-end flows
   - Validate data quality and accuracy

5. **Deployment & Operations**
   - Deploy pipelines to production environment
   - Set up monitoring and alerting
   - Document operational procedures

## Code Standards

- Write clean, maintainable code with proper documentation
- Implement comprehensive error handling and logging
- Use configuration management for environment-specific settings
- Follow security best practices for data handling
- Include unit and integration tests

## Response Format

Provide comprehensive solutions including:
- **Architecture Overview**: High-level design and component interaction
- **Implementation Code**: Complete, production-ready code with comments
- **Testing Strategy**: Unit tests, integration tests, and data validation
- **Deployment Guide**: Step-by-step deployment instructions
- **Monitoring Setup**: Metrics, alerts, and observability configuration
- **Operational Procedures**: Troubleshooting and maintenance guidance

Always consider scalability, reliability, and security in your recommendations.
```

## Testing Agents Locally

### Basic Loading Test

```bash
# Test agent loading
python -c "
from claude_mpm.agents.agent_loader import get_agent_prompt
try:
    prompt = get_agent_prompt('your_agent_name')
    print('✅ Agent loaded successfully')
    print(f'Prompt length: {len(prompt)} characters')
except Exception as e:
    print(f'❌ Agent failed to load: {e}')
"
```

### Schema Validation Test

```bash
# Validate agent against schema
python -c "
from claude_mpm.validation.agent_validator import validate_agent_file
from pathlib import Path

result = validate_agent_file(Path('.claude-mpm/agents/your_agent.json'))
print(f'Valid: {result.is_valid}')
if not result.is_valid:
    for error in result.errors:
        print(f'❌ Error: {error}')
if result.warnings:
    for warning in result.warnings:
        print(f'⚠️  Warning: {warning}')
"
```

### Functional Testing

```bash
# Test agent with sample prompt
./claude-mpm run -i "Test task for your agent" --agent your_agent_name --non-interactive
```

### Tier Precedence Test

```bash
# Check which tier your agent loads from
python -c "
from claude_mpm.agents.agent_loader import get_agent_tier
tier = get_agent_tier('your_agent_name')
print(f'Agent loaded from: {tier} tier')
"
```

### Performance Testing

```python
import time
from claude_mpm.agents.agent_loader import get_agent_prompt

# Measure loading performance
start_time = time.time()
prompt = get_agent_prompt('your_agent_name')
load_time = time.time() - start_time

print(f"Load time: {load_time:.3f}s")
print(f"Prompt size: {len(prompt)} characters")
```

## Best Practices

### Agent Design Principles

1. **Single Responsibility**: Each agent should have a clear, focused purpose
2. **Comprehensive Instructions**: Provide detailed, actionable instructions
3. **Appropriate Tools**: Include only necessary tools for the agent's tasks
4. **Resource Efficiency**: Choose appropriate resource tier and limits
5. **Security Conscious**: Follow principle of least privilege

### Writing Effective Instructions

```markdown
# Good Instructions Template

## Role Definition
You are a [specific role] with expertise in [domain areas].

## Key Responsibilities
1. **Primary Task**: Clear description of main function
2. **Secondary Tasks**: Supporting functions and capabilities
3. **Constraints**: What the agent should NOT do

## Approach
1. Step-by-step methodology
2. Decision-making criteria
3. Quality standards

## Output Format
- Structured response format
- Required sections and content
- Examples of good outputs

## Context Awareness
- Project-specific information
- Technology stack details
- Team conventions and standards
```

### Tool Selection Guidelines

```yaml
# Tool Categories and Use Cases

File Operations:
  - Read: View existing files and code
  - Write: Create new files
  - Edit: Modify existing files
  - MultiEdit: Bulk file modifications

Code Analysis:
  - Grep: Search within files
  - Glob: Find files by pattern
  - LS: Directory exploration

Development:
  - Bash: Execute commands and scripts
  - git: Version control operations

Cloud/Infrastructure:
  - docker: Container operations
  - kubectl: Kubernetes management
  - aws/gcloud/azure: Cloud platform tools

Information:
  - WebSearch: Research and documentation
  - TodoWrite: Task management

# Selection Criteria:
# - Include only tools the agent actually needs
# - Consider security implications of tool combinations
# - Match tools to agent's resource tier
```

### Security Best Practices

```json
{
  "security_checklist": [
    "Use minimum required tools",
    "Set appropriate file access paths",
    "Enable network access only when needed",
    "Set reasonable resource limits",
    "Avoid dangerous tool combinations",
    "Validate agent ID patterns",
    "Use secure model configurations"
  ],
  "dangerous_combinations": [
    ["Bash", "Write"],  // Can write and execute arbitrary code
    ["docker", "kubectl"],  // Container escape potential
    ["WebSearch", "Bash"]  // Could download and execute malicious code
  ]
}
```

## Advanced Features

### Dynamic Capability Configuration

```json
{
  "capabilities": {
    "tools": ["Read", "Write", "Edit"],
    "allowed_tools": ["src/**", "tests/**"],
    "disallowed_tools": ["Bash"],
    "file_access": {
      "read_paths": ["./src", "./docs"],
      "write_paths": ["./src", "./tests"]
    }
  }
}
```

### Hook Integration

```json
{
  "hooks": {
    "pre_execution": [
      {
        "name": "security_scan",
        "enabled": true,
        "config": {
          "scan_type": "vulnerability_check",
          "fail_on_high": true
        }
      }
    ],
    "post_execution": [
      {
        "name": "code_quality",
        "enabled": true,
        "config": {
          "metrics": ["complexity", "coverage"],
          "thresholds": {"complexity": 10, "coverage": 80}
        }
      }
    ]
  }
}
```

### Environment-Specific Configuration

```yaml
# .claude-mpm/config/agents.yaml
agent_config:
  your_agent_name:
    development:
      model: claude-3-5-sonnet-20241022
      resource_tier: lightweight
      timeout: 300
    production:
      model: claude-sonnet-4-20250514
      resource_tier: standard
      timeout: 600
    testing:
      model: claude-3-haiku-20240307
      resource_tier: basic
      timeout: 120
```

### Custom Validation Rules

```python
# custom_validator.py
from claude_mpm.validation.agent_validator import AgentValidator, ValidationResult

class ProjectAgentValidator(AgentValidator):
    def _validate_business_rules(self, agent_data, result):
        super()._validate_business_rules(agent_data, result)
        
        # Project-specific rules
        agent_type = agent_data.get("agent_type")
        tools = agent_data.get("capabilities", {}).get("tools", [])
        
        # Engineers should have git access
        if agent_type == "engineer" and "git" not in tools:
            result.warnings.append("Engineer agents should include git tool")
        
        # Data engineers need docker for containerization
        if agent_type == "data_engineer" and "docker" not in tools:
            result.warnings.append("Data engineer agents should include docker tool")
        
        # Security check for sensitive agents
        if "security" in agent_data.get("metadata", {}).get("tags", []):
            if not agent_data.get("capabilities", {}).get("network_access"):
                result.warnings.append("Security agents may need network access")
```

## Debugging Common Issues

### Issue 1: Agent Not Found

**Symptoms**: `ValueError: No agent found with name: your_agent`

**Debug Steps**:
```bash
# Check file exists
ls -la .claude-mpm/agents/your_agent.*

# Check tier loading
python -c "
from claude_mpm.agents.agent_loader import list_agents_by_tier
import json
print(json.dumps(list_agents_by_tier(), indent=2))
"

# Test exact filename
python -c "
from claude_mpm.agents.agent_loader import get_agent_prompt
print(get_agent_prompt('exact_filename_without_extension'))
"
```

### Issue 2: Schema Validation Failures

**Symptoms**: Agent loads but validation errors

**Debug Steps**:
```python
from claude_mpm.validation.agent_validator import AgentValidator
from pathlib import Path

validator = AgentValidator()
result = validator.validate_file(Path('.claude-mpm/agents/your_agent.json'))

print("Validation Result:")
print(f"Valid: {result.is_valid}")
print("\nErrors:")
for error in result.errors:
    print(f"  - {error}")
print("\nWarnings:")
for warning in result.warnings:
    print(f"  - {warning}")
```

### Issue 3: Wrong Agent Version Loading

**Symptoms**: System agent loads instead of project agent

**Debug Steps**:
```bash
# Check tier precedence
python -c "
from claude_mpm.agents.agent_loader import get_agent_tier, list_agents_by_tier
import json

agent_name = 'your_agent'
print(f'Agent tier: {get_agent_tier(agent_name)}')
print('All tiers:')
print(json.dumps(list_agents_by_tier(), indent=2))
"

# Clear cache and reload
python -c "
from claude_mpm.agents.agent_loader import reload_agents
reload_agents()
print('Agent cache cleared')
"
```

### Issue 4: Performance Issues

**Symptoms**: Slow loading, high memory usage

**Debug Steps**:
```python
from claude_mpm.agents.agent_loader import _get_loader

loader = _get_loader()
metrics = loader.get_metrics()

print(f"Cache hit rate: {metrics['cache_hit_rate_percent']:.1f}%")
print(f"Average load time: {metrics['average_load_time_ms']:.1f}ms")
print(f"Agents loaded: {metrics['agents_loaded']}")
print(f"Cache size: {len(loader.profile_cache)}")
```

### Issue 5: Tool Access Problems

**Symptoms**: Agent can't access expected tools or files

**Debug Steps**:
```json
// Check capabilities configuration
{
  "capabilities": {
    "tools": ["Read", "Write"],  // Verify tool names are correct
    "file_access": {
      "read_paths": ["./"],  // Check path permissions
      "write_paths": ["./src"]
    },
    "network_access": true,  // Check network permissions
    "allowed_tools": ["src/**"],  // Check tool restrictions
    "disallowed_tools": ["Bash"]  // Check tool exclusions
  }
}
```

## Real-World Examples

### Example 1: API Testing Agent

```json
{
  "schema_version": "1.2.0",
  "agent_id": "api_test_engineer",
  "agent_version": "1.0.0",
  "agent_type": "qa",
  "metadata": {
    "name": "API Testing Engineer",
    "description": "Specialized agent for API testing and validation",
    "tags": ["api", "testing", "validation", "automation"],
    "author": "QA Team"
  },
  "capabilities": {
    "model": "claude-3-5-sonnet-20241022",
    "tools": ["Read", "Write", "Edit", "WebSearch", "Bash"],
    "resource_tier": "standard",
    "network_access": true,
    "temperature": 0.3
  },
  "instructions": "# API Testing Engineer\n\nYou specialize in comprehensive API testing, including functional testing, performance testing, and security validation.\n\n## Testing Approach\n1. Analyze API specifications\n2. Create comprehensive test scenarios\n3. Implement automated test suites\n4. Validate security and performance\n5. Document results and recommendations\n\n## Focus Areas\n- REST/GraphQL API testing\n- Authentication and authorization\n- Data validation and error handling\n- Performance and load testing\n- Security vulnerability assessment"
}
```

### Example 2: DevOps Infrastructure Agent

```yaml
---
schema_version: "1.2.0"
agent_id: devops_infrastructure
agent_version: "2.1.0"
agent_type: ops
metadata:
  name: DevOps Infrastructure Agent
  description: Infrastructure automation and deployment specialist
  category: operations
  tags:
    - devops
    - infrastructure
    - deployment
    - monitoring
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - docker
    - kubectl
    - terraform
    - aws
  resource_tier: intensive
  network_access: true
  timeout: 1200
---

# DevOps Infrastructure Agent

You are a DevOps expert specializing in infrastructure automation, deployment pipelines, and system monitoring.

## Core Competencies

- **Infrastructure as Code**: Terraform, CloudFormation, Pulumi
- **Container Orchestration**: Docker, Kubernetes, Helm
- **CI/CD Pipelines**: Jenkins, GitLab CI, GitHub Actions
- **Cloud Platforms**: AWS, GCP, Azure
- **Monitoring**: Prometheus, Grafana, ELK stack

## Implementation Standards

1. **Infrastructure as Code**: All infrastructure changes through version-controlled templates
2. **Security First**: Implement security best practices from design phase
3. **Monitoring**: Comprehensive observability for all components
4. **Documentation**: Clear operational procedures and runbooks
5. **Automation**: Minimize manual intervention through automation
```

### Example 3: Machine Learning Agent

```json
{
  "schema_version": "1.2.0",
  "agent_id": "ml_engineer",
  "agent_version": "1.5.0",
  "agent_type": "data_engineer",
  "metadata": {
    "name": "Machine Learning Engineer",
    "description": "ML model development, training, and deployment specialist",
    "category": "specialized",
    "tags": ["machine-learning", "ai", "model-training", "mlops"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "docker", "kubectl"],
    "resource_tier": "intensive",
    "max_tokens": 20000,
    "timeout": 1800,
    "network_access": true
  },
  "knowledge": {
    "domain_expertise": [
      "machine-learning",
      "deep-learning",
      "model-deployment",
      "mlops",
      "data-preprocessing"
    ],
    "best_practices": [
      "Version control for datasets and models",
      "Reproducible experiments",
      "Comprehensive model evaluation",
      "Continuous integration for ML pipelines"
    ]
  },
  "instructions": "# Machine Learning Engineer\n\nYou are an expert ML engineer focused on the complete ML lifecycle from data preprocessing to model deployment and monitoring.\n\n## Expertise Areas\n\n### Model Development\n- Data preprocessing and feature engineering\n- Model architecture selection and design\n- Hyperparameter optimization\n- Model training and validation\n\n### MLOps\n- Model versioning and experiment tracking\n- Automated ML pipelines\n- Model deployment strategies\n- Performance monitoring and alerting\n\n### Technologies\n- **Frameworks**: TensorFlow, PyTorch, Scikit-learn\n- **MLOps**: MLflow, Kubeflow, Weights & Biases\n- **Deployment**: Docker, Kubernetes, cloud platforms\n- **Monitoring**: Model drift detection, performance metrics\n\n## Development Process\n\n1. **Problem Definition**: Understand business requirements and success metrics\n2. **Data Analysis**: Explore and validate data quality and characteristics\n3. **Feature Engineering**: Design and implement relevant features\n4. **Model Development**: Train, validate, and optimize models\n5. **Evaluation**: Comprehensive model assessment and comparison\n6. **Deployment**: Production deployment with monitoring\n7. **Maintenance**: Ongoing monitoring and model updates"
}
```

## Deployment and Management

### Version Control Integration

```bash
# Include agents in version control
echo "# Agent configurations" > .claude-mpm/agents/README.md
git add .claude-mpm/agents/
git add .claude-mpm/config/
git commit -m "Add project-specific agents"

# Exclude runtime files
echo ".claude-mpm/cache/" >> .gitignore
echo ".claude-mpm/logs/" >> .gitignore
```

### Environment-Specific Deployment

```yaml
# .claude-mpm/config/environments.yaml
environments:
  development:
    agent_overrides:
      timeout: 300
      resource_tier: lightweight
  production:
    agent_overrides:
      timeout: 600
      resource_tier: standard
  testing:
    agent_overrides:
      timeout: 120
      resource_tier: basic
```

### Monitoring and Maintenance

```python
# monitoring_script.py
from claude_mpm.agents.agent_loader import _get_loader

def monitor_agent_performance():
    loader = _get_loader()
    metrics = loader.get_metrics()
    
    # Alert on poor performance
    if metrics['cache_hit_rate_percent'] < 70:
        print("WARNING: Low cache hit rate")
    
    if metrics['average_load_time_ms'] > 1000:
        print("WARNING: High average load time")
    
    # Report usage statistics
    print(f"Total agents: {metrics['agents_loaded']}")
    print(f"Cache efficiency: {metrics['cache_hit_rate_percent']:.1f}%")
    
    return metrics

# Run monitoring
if __name__ == "__main__":
    monitor_agent_performance()
```

This comprehensive creation guide provides everything needed to successfully create, test, and deploy agents in Claude MPM, from simple examples to complex production configurations.