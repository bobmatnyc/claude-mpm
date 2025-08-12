# Best Practices for Writing Agent Definition YAMLs

## 1. Structural Foundation & Format

### **Document Structure**
Begin all YAML files with three dashes (---) to indicate document start and end with ellipsis (...) as part of standard YAML formatting. Use UTF-8 encoding exclusively for maximum Unicode compatibility.

```yaml
---
# Agent Definition
name: "security-auditor"
version: "1.0.0"
# ... rest of configuration
...
```

### **Indentation Rules**
Use consistent spacing (typically 2 spaces) for indentation levels and never use tabs, as YAML does not support them. Maintain consistent indentation throughout the entire file.

```yaml
---
agent:
  profile:
    name: "data-analyst"        # 2 spaces
    specializations:
      - "data-processing"       # 4 spaces
      - "visualization"         # 4 spaces
  configuration:
    timeout: 300               # 2 spaces
    memory_limit: 1024         # 2 spaces
```

## 2. Agent Metadata Best Practices

### **Essential Frontmatter Schema**
Based on the Claude PM Framework examples, implement comprehensive metadata:

```yaml
---
# Core Identity
name: "performance-optimizer"
description: "Database and application performance specialist"
version: "2.1.0"
author: "performance-team@company.com"
created: "2025-07-25T10:00:00Z"
updated: "2025-07-25T15:30:00Z"

# Categorization
tags: ["performance", "database", "optimization", "monitoring"]
team: "infrastructure-team"
project: "payment-service"
priority: "high"

# Behavioral Configuration
tools: ["Read", "Write", "Edit", "Bash", "ProfilerTools"]
timeout: 600
max_tokens: 8192
model: "claude-3-5-sonnet-20241022"
temperature: 0.1

# Access Control
file_access: "project"
network_access: false
dangerous_tools: false
review_required: true

# Resource Management
memory_limit: 2048
cpu_limit: 50
execution_timeout: 900
```

### **Clear Naming Conventions**
Use descriptive keys that convey their purpose to aid in readability and maintainability. Follow consistent naming patterns across all agent definitions.

## 3. Agent Capabilities Definition

### **When/Why/What Structure**
Every agent should clearly define its usage context:

```yaml
---
name: "api-security-auditor"

# WHEN to use this agent
when_to_use:
  - "API endpoint security validation needed"
  - "Authentication mechanism review required" 
  - "Authorization flow analysis needed"
  - "Input validation security assessment"

# WHY this agent exists
rationale:
  specialized_knowledge:
    - "OAuth 2.0 and JWT security patterns"
    - "API rate limiting and DDoS protection"
    - "Input sanitization and injection prevention"
  unique_capabilities:
    - "OWASP API Security Top 10 compliance"
    - "Authentication bypass detection"
    - "Authorization escalation analysis"

# WHAT the agent does
capabilities:
  primary_role: "API security assessment and vulnerability analysis"
  specializations: ["security", "api", "authentication", "authorization"]
  authority: "Security recommendations and vulnerability reporting"
  
  specific_tasks:
    - task: "Authentication Analysis"
      description: "Verify proper authentication implementation"
    - task: "Authorization Validation" 
      description: "Ensure proper access controls and permissions"
    - task: "Input Validation Review"
      description: "Check for injection vulnerabilities and input sanitization"
```

### **Tool Configuration**
Clearly define tool access and inheritance patterns:

```yaml
# Explicit tool specification
tools:
  allowed: ["Read", "Write", "Edit", "SecurityScan", "PenetrationTest"]
  inherit_from_parent: false
  custom_tools:
    - name: "VulnerabilityScanner"
      config:
        scan_depth: "deep"
        compliance_checks: ["OWASP", "NIST"]

# Alternative: Inheritance pattern
tools: "*"  # Inherit all tools from parent
tool_restrictions:
  blocked: ["Terminal", "NetworkAccess"]
  require_approval: ["ModifyProduction", "DataExport"]
```

## 4. Context and Environment Management

### **Environment Variables**
Structure environment configuration clearly and document complex configurations:

```yaml
environment:
  # Security scanning configuration
  SECURITY_SCAN_DEPTH: "comprehensive"
  COMPLIANCE_FRAMEWORKS: "OWASP,NIST,ISO27001"
  REPORT_FORMAT: "json"
  
  # Performance settings
  MAX_SCAN_TIME: "3600"
  PARALLEL_SCANS: "3"
  CACHE_RESULTS: "true"

# Context filtering
context_management:
  isolation_level: "strict"
  preserve_context: true
  context_window_size: 100000
  relevant_paths:
    - "/src/api/"
    - "/src/auth/"
    - "/config/security/"
```

### **Integration Patterns**
Define how the agent works with other agents and systems:

```yaml
collaboration:
  upstream_agents:
    - "code-reviewer"
    - "vulnerability-scanner"
  downstream_agents:
    - "compliance-reporter"
    - "incident-manager"
  
  coordination_patterns:
    - pattern: "security_pipeline"
      description: "Automated security assessment workflow"
      triggers: ["code_commit", "deployment_request"]

  communication_protocols:
    input_format: "security_context"
    output_format: "security_report"
    notification_channels: ["slack", "email", "dashboard"]
```

## 5. Performance and Resource Management

### **Resource Constraints**
Define clear limits to prevent resource exhaustion:

```yaml
performance:
  # Execution limits
  max_execution_time: 1800  # 30 minutes
  memory_limit_mb: 4096
  cpu_limit_percent: 75
  
  # Concurrency controls
  max_parallel_tasks: 3
  queue_size: 50
  
  # Optimization settings
  cache_enabled: true
  cache_ttl_seconds: 3600
  batch_processing: true
  batch_size: 10

# Monitoring and metrics
monitoring:
  performance_tracking: true
  success_rate_threshold: 0.95
  average_response_time_ms: 2000
  error_rate_threshold: 0.05
```

### **Lifecycle Management**
Configure agent initialization, execution, and cleanup:

```yaml
lifecycle:
  initialization:
    pre_execution_hooks:
      - "validate_environment"
      - "load_security_policies"
      - "initialize_scanning_tools"
    
    startup_checks:
      - "verify_tool_availability"
      - "check_permissions"
      - "validate_configuration"
  
  execution:
    retry_policy:
      max_attempts: 3
      backoff_strategy: "exponential"
      retry_conditions: ["timeout", "network_error"]
    
    progress_reporting:
      enabled: true
      interval_seconds: 30
      include_metrics: true
  
  cleanup:
    post_execution_hooks:
      - "cleanup_temp_files"
      - "save_audit_logs"
      - "update_metrics"
    
    timeout_handling:
      graceful_shutdown_seconds: 60
      force_kill_after_seconds: 120
```

## 6. Schema Validation and Quality Assurance

### **Schema Definition**
Implement validation rules to ensure configuration integrity:

```yaml
schema_validation:
  required_fields:
    - "name"
    - "description" 
    - "version"
    - "capabilities"
    - "tools"
  
  field_constraints:
    name:
      pattern: "^[a-z][a-z0-9-]*[a-z0-9]$"
      max_length: 50
    version:
      pattern: "^\\d+\\.\\d+\\.\\d+$"
    timeout:
      min: 30
      max: 3600
    memory_limit:
      min: 256
      max: 8192

  custom_validators:
    - name: "tool_compatibility"
      description: "Validate tool combinations are compatible"
    - name: "resource_limits"
      description: "Ensure resource limits are within bounds"
```

### **Documentation Requirements**
Comprehensive documentation for maintainability:

```yaml
documentation:
  # Inline documentation
  usage_examples:
    - name: "Basic security scan"
      description: "Standard API endpoint security assessment"
      command: "@security-auditor scan api endpoints in /src/api/"
    
    - name: "Compliance audit"
      description: "Full OWASP compliance assessment"
      command: "@security-auditor audit compliance OWASP /src/"
  
  # External references
  references:
    - type: "documentation"
      url: "https://docs.company.com/security-agents/api-auditor"
    - type: "training"
      url: "https://training.company.com/security-best-practices"
    - type: "compliance"
      url: "https://compliance.company.com/OWASP-requirements"

  # Change management
  changelog:
    - version: "2.1.0"
      date: "2025-07-25"
      changes:
        - "Added JWT validation capabilities"
        - "Enhanced OAuth 2.0 flow analysis"
        - "Improved error reporting"
    - version: "2.0.0"
      date: "2025-07-01"
      changes:
        - "Major refactor for Claude Code integration"
        - "Added multi-framework compliance support"
```

## 7. Security and Access Control

### **Security Configuration**
Implement comprehensive security measures:

```yaml
security:
  # Access control
  permissions:
    read_access:
      - "/src/**"
      - "/config/security/**"
      - "/docs/api/**"
    write_access:
      - "/reports/security/**"
      - "/logs/audit/**"
    restricted_paths:
      - "/config/secrets/**"
      - "/keys/**"
      - "/.env*"
  
  # Data handling
  data_classification:
    input_sensitivity: "internal"
    output_sensitivity: "confidential"
    retention_policy: "90_days"
  
  # Audit requirements
  audit_logging:
    enabled: true
    log_level: "detailed"
    include_payloads: false
    retention_days: 365
    
  compliance:
    frameworks: ["SOC2", "GDPR", "HIPAA"]
    data_residency: "US"
    encryption_required: true
```

## 8. Testing and Validation

### **Test Configuration**
Built-in testing capabilities for agent validation:

```yaml
testing:
  # Unit tests
  unit_tests:
    - name: "basic_functionality"
      description: "Test core security scanning capabilities"
      test_cases:
        - input: "simple API endpoint"
          expected_output: "security_report"
        - input: "complex authentication flow"
          expected_output: "detailed_analysis"
  
  # Integration tests
  integration_tests:
    - name: "tool_integration"
      description: "Verify security tools work correctly"
      dependencies: ["SecurityScanner", "VulnerabilityDB"]
    
    - name: "agent_collaboration"
      description: "Test interaction with other agents"
      collaborators: ["code-reviewer", "compliance-reporter"]
  
  # Performance tests
  performance_tests:
    - name: "large_codebase_scan"
      description: "Test performance on large codebases"
      metrics:
        - "execution_time"
        - "memory_usage"
        - "accuracy"
      thresholds:
        max_execution_time: 1800
        max_memory_mb: 4096
        min_accuracy: 0.95
```

## 9. Error Handling and Recovery

### **Error Management**
Robust error handling and recovery mechanisms:

```yaml
error_handling:
  # Error categorization
  error_types:
    - type: "configuration_error"
      severity: "high"
      action: "abort"
      notification: true
    
    - type: "tool_failure"
      severity: "medium"
      action: "retry"
      max_retries: 3
    
    - type: "timeout"
      severity: "medium"
      action: "partial_results"
      graceful_degradation: true
  
  # Recovery strategies
  recovery:
    automatic_retry:
      enabled: true
      max_attempts: 3
      backoff_multiplier: 2
    
    fallback_behavior:
      enabled: true
      fallback_agent: "basic-security-scanner"
      partial_execution: true
    
    notification:
      on_failure: true
      channels: ["email", "slack"]
      escalation_threshold: 3
```

## 10. Complete Example: Production-Ready Agent Definition

```yaml
---
# =============================================================================
# API Security Auditor Agent Definition
# =============================================================================

# Core Identity
name: "api-security-auditor"
description: "Comprehensive API security assessment and vulnerability analysis specialist"
version: "2.1.0"
author: "security-team@company.com"
created: "2025-07-25T10:00:00Z"
updated: "2025-07-25T15:30:00Z"

# Categorization
tags: ["security", "api", "authentication", "authorization", "vulnerability"]
team: "security-team"
project: "api-security-platform"
priority: "high"

# When/Why/What Structure
when_to_use:
  - "API endpoint security validation needed"
  - "Authentication mechanism review required"
  - "Authorization flow analysis needed"
  - "OWASP compliance assessment required"

rationale:
  specialized_knowledge:
    - "OAuth 2.0 and JWT security patterns"
    - "API rate limiting and DDoS protection"
    - "Input sanitization and injection prevention"
    - "OWASP API Security Top 10 compliance"
  
  unique_capabilities:
    - "Deep authentication flow analysis"
    - "Authorization escalation detection"
    - "Automated vulnerability reporting"
    - "Compliance framework mapping"

capabilities:
  primary_role: "API security assessment and vulnerability analysis"
  specializations: ["security", "api", "authentication", "authorization", "compliance"]
  authority: "Security recommendations and vulnerability reporting"
  
  specific_tasks:
    - task: "Authentication Analysis"
      description: "Verify proper authentication implementation and identify weaknesses"
    - task: "Authorization Validation"
      description: "Ensure proper access controls and detect privilege escalation"
    - task: "Input Validation Review"
      description: "Check for injection vulnerabilities and input sanitization"
    - task: "Compliance Assessment"
      description: "Evaluate against OWASP, NIST, and other security frameworks"

# Tool Configuration
tools:
  allowed: ["Read", "Write", "Edit", "Bash", "SecurityScan", "VulnerabilityTest"]
  inherit_from_parent: false
  custom_tools:
    - name: "OWASPScanner"
      config:
        scan_depth: "comprehensive"
        compliance_checks: ["OWASP_API_Top10", "NIST", "ISO27001"]
    - name: "AuthFlowAnalyzer"
      config:
        supported_flows: ["oauth2", "jwt", "saml", "basic"]

# Performance and Resource Management
performance:
  timeout: 1800
  max_tokens: 12288
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.1
  memory_limit_mb: 4096
  cpu_limit_percent: 75
  max_parallel_tasks: 3

# Context Management
context_management:
  isolation_level: "strict"
  preserve_context: true
  context_window_size: 100000
  relevant_paths:
    - "/src/api/**"
    - "/src/auth/**"
    - "/config/security/**"
    - "/tests/security/**"

# Environment Configuration
environment:
  SECURITY_SCAN_DEPTH: "comprehensive"
  COMPLIANCE_FRAMEWORKS: "OWASP,NIST,ISO27001"
  REPORT_FORMAT: "json"
  MAX_SCAN_TIME: "1800"
  PARALLEL_SCANS: "3"
  CACHE_RESULTS: "true"
  AUDIT_LOGGING: "enabled"

# Security Configuration
security:
  file_access: "project"
  network_access: false
  dangerous_tools: false
  review_required: true
  
  permissions:
    read_access:
      - "/src/**"
      - "/config/security/**"
      - "/docs/api/**"
    write_access:
      - "/reports/security/**"
      - "/logs/audit/**"
    restricted_paths:
      - "/config/secrets/**"
      - "/keys/**"
      - "/.env*"

# Lifecycle Management
lifecycle:
  initialization:
    pre_execution_hooks:
      - "validate_security_tools"
      - "load_compliance_policies"
      - "verify_permissions"
    
    startup_checks:
      - "check_tool_availability"
      - "validate_target_scope"
      - "initialize_audit_logging"
  
  execution:
    retry_policy:
      max_attempts: 3
      backoff_strategy: "exponential"
      retry_conditions: ["timeout", "tool_failure"]
    
    progress_reporting:
      enabled: true
      interval_seconds: 60
      include_metrics: true
  
  cleanup:
    post_execution_hooks:
      - "generate_final_report"
      - "cleanup_temp_files"
      - "update_security_metrics"

# Agent Collaboration
collaboration:
  upstream_agents:
    - "code-reviewer"
    - "vulnerability-scanner"
  
  downstream_agents:
    - "compliance-reporter"
    - "incident-manager"
    - "security-dashboard"
  
  coordination_patterns:
    - pattern: "security_pipeline"
      description: "Automated security assessment in CI/CD"
      triggers: ["pre_deployment", "code_review"]

# Testing and Validation
testing:
  unit_tests:
    - name: "authentication_analysis"
      description: "Test OAuth 2.0 flow analysis"
    - name: "vulnerability_detection"
      description: "Test injection vulnerability detection"
  
  integration_tests:
    - name: "compliance_reporting"
      description: "Test OWASP compliance assessment"
    - name: "agent_coordination"
      description: "Test integration with other security agents"

# Error Handling
error_handling:
  error_types:
    - type: "scan_failure"
      severity: "high"
      action: "retry_with_fallback"
    - type: "tool_unavailable"
      severity: "medium"
      action: "use_alternative_tool"
    - type: "timeout"
      severity: "medium"
      action: "return_partial_results"
  
  recovery:
    automatic_retry: true
    max_attempts: 3
    fallback_agent: "basic-security-scanner"
    notification_on_failure: true

# Documentation
documentation:
  usage_examples:
    - name: "API endpoint scan"
      command: "@api-security-auditor scan endpoints /src/api/"
    - name: "Full compliance audit"
      command: "@api-security-auditor audit compliance OWASP /src/"
  
  references:
    - type: "documentation"
      url: "https://security-docs.company.com/api-auditor"
    - type: "compliance"
      url: "https://compliance.company.com/security-standards"

# Monitoring and Metrics
monitoring:
  performance_tracking: true
  success_rate_threshold: 0.95
  average_response_time_ms: 3000
  error_rate_threshold: 0.05
  
  metrics_collection:
    - "vulnerabilities_detected"
    - "compliance_score"
    - "scan_coverage_percentage"
    - "false_positive_rate"

# Schema Validation
schema_version: "2.1"
validation_rules:
  required_fields: ["name", "description", "capabilities", "tools"]
  custom_validators: ["security_tool_compatibility", "compliance_framework_validation"]

...
```

## 11. Validation and Quality Assurance

### **Pre-Deployment Checklist**
- [ ] YAML syntax validation using `yamllint`
- [ ] Schema validation against agent framework requirements
- [ ] Tool compatibility verification
- [ ] Resource limit validation
- [ ] Security policy compliance check
- [ ] Documentation completeness review
- [ ] Performance benchmark testing
- [ ] Integration testing with existing agents

### **Continuous Improvement**
- Version control all agent definitions
- Regular reviews and updates based on usage patterns
- Performance monitoring and optimization
- Security audit and compliance validation
- Community feedback integration
- Automated testing in CI/CD pipelines

This comprehensive guide provides the foundation for creating robust, maintainable, and secure agent definition YAMLs that follow industry best practices and integrate seamlessly with modern AI orchestration frameworks.