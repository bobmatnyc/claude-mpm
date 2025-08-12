# Claude Code Subagents: Technical Implementation & Programmatic Control

**Document Version:** 1.0  
**Date:** July 25, 2025  
**Target Audience:** Developers, DevOps Engineers, Technical Architects  

## Executive Summary

Claude Code's subagents feature enables programmatic spawning of up to 10 parallel AI instances, each with independent context windows and specialized capabilities. This document provides comprehensive technical implementation details, including flags, environment variables, SDK usage, and programmatic control mechanisms for production deployment and automation.

## Architecture Overview

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Claude Code Process                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Subagent 1  │  │ Subagent 2  │  │    ...      │       │
│  │ Context:    │  │ Context:    │  │ Context:    │       │
│  │ Independent │  │ Independent │  │ Independent │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                     Task Tool System                       │
│  • Process Management  • Context Isolation  • Tool Access │
└─────────────────────────────────────────────────────────────┘
```

### Technical Specifications

- **Maximum Concurrent Subagents**: 10
- **Queue Capacity**: 100+ tasks (automatically managed)
- **Context Isolation**: Complete separation between subagent contexts
- **Tool Inheritance**: Subagents inherit main agent's tool permissions
- **Memory Overhead**: ~50-100MB per active subagent
- **Latency**: 200-500ms subagent startup time

## Configuration Management

### Directory Structure

```
Project Root/
├── .claude/
│   ├── agents/                    # Project-level subagents (highest precedence)
│   │   ├── backend-specialist.md
│   │   ├── frontend-expert.md
│   │   └── security-auditor.md
│   ├── settings.json              # Shared team settings
│   ├── settings.local.json        # Personal settings (gitignored)
│   └── commands/                  # Custom slash commands
│
User Home/
├── ~/.claude/agents/              # User-level subagents (fallback)
│   ├── code-reviewer.md
│   └── performance-optimizer.md
└── ~/.claude/settings.json        # Global user settings

Alternative User Home (Linux):
└── ~/.config/claude/agents/       # XDG-compliant directory
```

### Environment Variables

#### Core Configuration

```bash
# Base configuration directory
export CLAUDE_CONFIG_DIR="/custom/path/to/claude"

# API Configuration
export ANTHROPIC_API_KEY="your-api-key-here"
export ANTHROPIC_API_URL="https://api.anthropic.com"  # Custom endpoint

# Model Selection
export CLAUDE_MODEL="claude-3-5-sonnet-20241022"  # Default model for subagents
export CLAUDE_MODEL_SUBAGENT="claude-3-5-haiku-20241022"  # Specific subagent model

# Performance Tuning
export CLAUDE_MAX_TOKENS="8192"                   # Max tokens per subagent
export CLAUDE_TIMEOUT="300000"                    # Timeout in milliseconds
export CLAUDE_MAX_PARALLEL_SUBAGENTS="10"         # Override default parallelism

# Context Management
export CLAUDE_CONTEXT_PRESERVATION="true"        # Preserve context between tasks
export CLAUDE_CONTEXT_ISOLATION="strict"         # Context isolation level

# Tool Access Control
export CLAUDE_ALLOWED_TOOLS="Read,Write,Edit,Bash"  # Comma-separated tool list
export CLAUDE_DISALLOWED_TOOLS="Terminal"           # Override specific tools

# MCP Configuration
export CLAUDE_MCP_TIMEOUT="30000"                 # MCP server timeout
export CLAUDE_MCP_RETRY_COUNT="3"                 # Retry attempts for MCP

# Debug and Monitoring
export CLAUDE_DEBUG="true"                        # Enable debug logging
export CLAUDE_LOG_LEVEL="info"                    # Log level: debug|info|warn|error
export CLAUDE_METRICS_ENABLED="true"              # Enable performance metrics
export CLAUDE_TRACE_SUBAGENTS="true"              # Trace subagent execution

# Performance Optimization
export CLAUDE_CACHE_ENABLED="true"                # Enable response caching
export CLAUDE_CACHE_TTL="3600"                    # Cache TTL in seconds
export CLAUDE_BATCH_SIZE="5"                      # Batch size for parallel execution

# Security
export CLAUDE_SANDBOX_MODE="true"                 # Enable sandboxing
export CLAUDE_RESTRICT_FILE_ACCESS="project"      # File access scope: project|user|system
export CLAUDE_AUDIT_LOG="true"                    # Enable audit logging
```

#### Advanced Environment Variables

```bash
# Resource Management
export CLAUDE_MEMORY_LIMIT="2048"                 # Memory limit per subagent (MB)
export CLAUDE_CPU_LIMIT="50"                      # CPU limit percentage
export CLAUDE_DISK_QUOTA="1024"                   # Disk quota (MB)

# Network Configuration
export CLAUDE_PROXY_URL="http://proxy:8080"       # HTTP proxy
export CLAUDE_NO_PROXY="localhost,127.0.0.1"     # Proxy bypass list
export CLAUDE_SSL_VERIFY="true"                   # SSL certificate verification

# Enterprise Features
export CLAUDE_ORGANIZATION_ID="org-xxx"           # Organization ID
export CLAUDE_WORKSPACE_ID="ws-xxx"               # Workspace ID
export CLAUDE_TEAM_ID="team-xxx"                  # Team ID for billing

# Experimental Features
export CLAUDE_EXPERIMENTAL_FEATURES="true"        # Enable experimental features
export CLAUDE_BETA_SUBAGENTS="true"              # Enable beta subagent features
export CLAUDE_FEATURE_FLAG_XYZ="enabled"         # Specific feature flags
```

### Command Line Flags

#### Core Flags

```bash
# Basic subagent control
claude --max-subagents 8                          # Override default parallelism
claude --subagent-timeout 600                     # Subagent timeout (seconds)
claude --subagent-model claude-3-opus-20240229    # Model for subagents
claude --disable-subagents                        # Disable subagent functionality

# Tool and permission management
claude --allowed-tools Read,Write,Edit            # Restrict tool access
claude --disallowed-tools Terminal,Network        # Block specific tools
claude --subagent-tools Read,Edit                 # Tools available to subagents
claude --inherit-tools                            # Subagents inherit all tools

# Context and memory management
claude --context-isolation strict                 # Context isolation level
claude --preserve-context                         # Maintain context between tasks
claude --context-window-size 100000               # Context window size
claude --memory-limit 1024                        # Memory limit per subagent

# Debug and monitoring
claude --debug                                    # Enable debug mode
claude --verbose                                  # Verbose logging
claude --trace-subagents                          # Trace subagent execution
claude --metrics                                  # Enable metrics collection
claude --log-file /path/to/logfile                # Custom log file location

# Configuration overrides
claude --config /path/to/config.json              # Custom config file
claude --agent-dir /path/to/agents                # Custom agent directory
claude --no-user-agents                           # Disable user-level agents
claude --project-agents-only                      # Use only project agents

# Performance tuning
claude --batch-size 3                             # Parallel execution batch size
claude --queue-size 50                            # Task queue size
claude --cache-enabled                            # Enable response caching
claude --preload-agents                           # Preload agent definitions

# Security and sandboxing
claude --sandbox                                  # Enable sandbox mode
claude --restrict-file-access                     # Restrict file system access
claude --audit-log                                # Enable audit logging
claude --secure-mode                              # Enable security restrictions
```

#### Advanced Flags

```bash
# Enterprise deployment
claude --enterprise-mode                          # Enterprise feature set
claude --sso-enabled                              # Single sign-on authentication
claude --audit-webhook https://audit.company.com  # Audit webhook endpoint
claude --policy-file /etc/claude/policy.json     # Security policy file

# Integration flags
claude --mcp-config /path/to/mcp.json             # MCP server configuration
claude --webhook-url https://hooks.company.com    # Webhook for notifications
claude --metrics-endpoint https://metrics.co      # Metrics collection endpoint
claude --health-check-port 8080                   # Health check HTTP port

# Development and testing
claude --dry-run                                  # Simulate without execution
claude --test-mode                                # Enable testing features
claude --mock-subagents                           # Use mock subagents for testing
claude --record-session /path/to/recording        # Record session for replay
claude --replay-session /path/to/recording        # Replay recorded session

# Performance profiling
claude --profile                                  # Enable performance profiling
claude --memory-profiling                         # Memory usage profiling
claude --cpu-profiling                            # CPU usage profiling
claude --flame-graph /path/to/output.svg          # Generate flame graph
```

## Subagent Definition Format

### YAML Frontmatter Schema

```yaml
---
name: "agent-name"                    # Required: Unique identifier
description: "Agent description"       # Required: When to use this agent
version: "1.0.0"                      # Optional: Version for tracking
author: "team@company.com"            # Optional: Author information
tags: ["backend", "api", "security"]  # Optional: Categorization tags

# Tool Configuration
tools: 
  - "Read"                            # Specific tools (overrides inheritance)
  - "Write" 
  - "Edit"
  - "Bash"
# Alternative: tools: "Read,Write,Edit" # Comma-separated string format
# Alternative: tools: "*"              # Inherit all tools (default)

# Advanced Configuration
priority: "high"                      # Optional: high|medium|low
timeout: 300                          # Optional: Timeout in seconds
max_tokens: 4096                      # Optional: Token limit override
model: "claude-3-5-sonnet-20241022"   # Optional: Model override
temperature: 0.1                      # Optional: Temperature setting

# Context Management
context_isolation: "strict"           # Optional: strict|moderate|relaxed
preserve_context: true                # Optional: Maintain context
context_window: 50000                 # Optional: Context window size

# Resource Limits
memory_limit: 512                     # Optional: Memory limit (MB)
cpu_limit: 25                         # Optional: CPU limit (%)
execution_timeout: 600                # Optional: Max execution time

# Access Control
file_access: "project"                # Optional: project|user|restricted
network_access: false                 # Optional: Allow network access
dangerous_tools: false                # Optional: Allow dangerous tools

# Metadata
created: "2025-07-25T10:00:00Z"       # Optional: Creation timestamp
updated: "2025-07-25T12:00:00Z"       # Optional: Last update
usage_count: 42                       # Optional: Usage statistics
success_rate: 0.95                    # Optional: Performance metrics

# Environment Variables
environment:
  NODE_ENV: "production"              # Optional: Custom environment vars
  DEBUG_MODE: "false"
  API_ENDPOINT: "https://api.internal.com"

# Hooks and Lifecycle
hooks:
  pre_execution: "setup.sh"           # Optional: Pre-execution script
  post_execution: "cleanup.sh"        # Optional: Post-execution script
  on_error: "error_handler.sh"        # Optional: Error handling script

# Team and Collaboration
team: "backend-team"                  # Optional: Team ownership
project: "payment-service"            # Optional: Project association
review_required: true                 # Optional: Require peer review
---

# System Prompt
You are a specialized backend API security auditor with expertise in authentication, 
authorization, and API vulnerability assessment.

## Core Responsibilities
- Review API endpoints for security vulnerabilities
- Validate authentication and authorization mechanisms
- Identify potential security weaknesses in code
- Suggest security improvements and best practices

## Analysis Framework
1. **Authentication Analysis**: Verify proper authentication implementation
2. **Authorization Checks**: Ensure proper access controls
3. **Input Validation**: Check for injection vulnerabilities
4. **Error Handling**: Review error responses for information leakage
5. **Rate Limiting**: Validate rate limiting implementation

## Output Format
Provide structured security assessment with:
- Risk level (Critical/High/Medium/Low)
- Vulnerability description
- Impact assessment
- Remediation recommendations
- Code examples for fixes

## Tools and Techniques
- Static code analysis
- Security pattern recognition
- OWASP guidelines compliance
- Industry best practices validation
```

## SDK and Programmatic Control

### Official Python SDK

```python
from anthropic import Claude
from claude_code import SubagentManager, SubagentConfig

class SubagentOrchestrator:
    def __init__(self, api_key: str, config_dir: str = None):
        self.claude = Claude(api_key=api_key)
        self.manager = SubagentManager(
            config_dir=config_dir or os.getenv('CLAUDE_CONFIG_DIR'),
            max_parallel=int(os.getenv('CLAUDE_MAX_PARALLEL_SUBAGENTS', '10')),
            timeout=int(os.getenv('CLAUDE_TIMEOUT', '300000'))
        )
        
    def create_subagent(self, 
                       name: str, 
                       description: str, 
                       tools: List[str] = None,
                       **kwargs) -> str:
        """Create a new subagent programmatically"""
        config = SubagentConfig(
            name=name,
            description=description,
            tools=tools or ['Read', 'Write', 'Edit'],
            model=kwargs.get('model', os.getenv('CLAUDE_MODEL_SUBAGENT')),
            timeout=kwargs.get('timeout', 300),
            max_tokens=kwargs.get('max_tokens', 4096),
            memory_limit=kwargs.get('memory_limit', 512),
            context_isolation=kwargs.get('context_isolation', 'strict')
        )
        
        return self.manager.create_agent(config)
    
    def spawn_subagent(self, 
                      agent_name: str, 
                      task: str, 
                      context: Dict[str, Any] = None) -> str:
        """Spawn a subagent for task execution"""
        return self.manager.spawn_agent(
            agent_name=agent_name,
            task=task,
            context=context or {},
            priority=context.get('priority', 'medium') if context else 'medium'
        )
    
    def spawn_parallel_subagents(self, 
                                tasks: List[Dict[str, Any]], 
                                max_parallel: int = None) -> List[str]:
        """Spawn multiple subagents in parallel"""
        task_ids = []
        semaphore = asyncio.Semaphore(max_parallel or self.manager.max_parallel)
        
        async def spawn_with_limit(task_config):
            async with semaphore:
                return await self.manager.spawn_agent_async(**task_config)
        
        # Execute tasks in parallel with concurrency limit
        loop = asyncio.get_event_loop()
        tasks_futures = [spawn_with_limit(task) for task in tasks]
        task_ids = loop.run_until_complete(asyncio.gather(*tasks_futures))
        
        return task_ids
    
    def monitor_subagents(self) -> Dict[str, Any]:
        """Monitor active subagents"""
        return self.manager.get_status()
    
    def wait_for_completion(self, 
                           task_ids: List[str], 
                           timeout: int = None) -> Dict[str, Any]:
        """Wait for subagent tasks to complete"""
        return self.manager.wait_for_tasks(
            task_ids, 
            timeout=timeout or int(os.getenv('CLAUDE_TIMEOUT', '300000'))
        )

# Usage Example
def main():
    orchestrator = SubagentOrchestrator(
        api_key=os.getenv('ANTHROPIC_API_KEY'),
        config_dir='/custom/claude/config'
    )
    
    # Create specialized subagents
    security_agent = orchestrator.create_subagent(
        name="security-auditor",
        description="Specialized security analysis agent",
        tools=['Read', 'Grep', 'Bash'],
        model="claude-3-5-sonnet-20241022",
        memory_limit=1024
    )
    
    # Parallel task execution
    tasks = [
        {
            'agent_name': 'security-auditor',
            'task': 'Audit authentication endpoints in /src/auth/',
            'context': {'priority': 'high', 'scope': 'authentication'}
        },
        {
            'agent_name': 'security-auditor', 
            'task': 'Review API input validation in /src/api/',
            'context': {'priority': 'medium', 'scope': 'validation'}
        },
        {
            'agent_name': 'security-auditor',
            'task': 'Analyze authorization mechanisms in /src/auth/rbac/',
            'context': {'priority': 'high', 'scope': 'authorization'}
        }
    ]
    
    # Execute in parallel
    task_ids = orchestrator.spawn_parallel_subagents(tasks, max_parallel=3)
    
    # Monitor and wait for completion
    results = orchestrator.wait_for_completion(task_ids, timeout=600)
    
    return results

if __name__ == "__main__":
    results = main()
    print(f"Completed {len(results)} security audit tasks")
```

### TypeScript/JavaScript SDK

```typescript
import { ClaudeCode, SubagentManager, type SubagentConfig } from '@anthropic-ai/claude-code';

interface SubagentTask {
  agentName: string;
  task: string;
  context?: Record<string, any>;
  priority?: 'low' | 'medium' | 'high';
}

class ClaudeSubagentOrchestrator {
  private manager: SubagentManager;
  private config: SubagentConfig;
  
  constructor(config?: Partial<SubagentConfig>) {
    this.config = {
      maxParallel: parseInt(process.env.CLAUDE_MAX_PARALLEL_SUBAGENTS || '10'),
      timeout: parseInt(process.env.CLAUDE_TIMEOUT || '300000'),
      model: process.env.CLAUDE_MODEL_SUBAGENT || 'claude-3-5-sonnet-20241022',
      configDir: process.env.CLAUDE_CONFIG_DIR || '.claude',
      ...config
    };
    
    this.manager = new SubagentManager(this.config);
  }
  
  async createSubagent(params: {
    name: string;
    description: string;
    tools?: string[];
    systemPrompt?: string;
    metadata?: Record<string, any>;
  }): Promise<string> {
    const agentConfig = {
      name: params.name,
      description: params.description,
      tools: params.tools || ['Read', 'Write', 'Edit'],
      model: this.config.model,
      timeout: this.config.timeout,
      systemPrompt: params.systemPrompt,
      ...params.metadata
    };
    
    return await this.manager.createAgent(agentConfig);
  }
  
  async spawnSubagent(agentName: string, task: string, context?: Record<string, any>): Promise<string> {
    return await this.manager.spawnAgent({
      agentName,
      task,
      context: context || {},
      timestamp: new Date().toISOString()
    });
  }
  
  async spawnParallelSubagents(tasks: SubagentTask[]): Promise<string[]> {
    const concurrencyLimit = this.config.maxParallel;
    const taskIds: string[] = [];
    
    // Process tasks in batches to respect concurrency limits
    for (let i = 0; i < tasks.length; i += concurrencyLimit) {
      const batch = tasks.slice(i, i + concurrencyLimit);
      const batchPromises = batch.map(task => 
        this.spawnSubagent(task.agentName, task.task, task.context)
      );
      
      const batchIds = await Promise.all(batchPromises);
      taskIds.push(...batchIds);
    }
    
    return taskIds;
  }
  
  async monitorSubagents(): Promise<Record<string, any>> {
    return await this.manager.getStatus();
  }
  
  async waitForCompletion(taskIds: string[], timeout?: number): Promise<Record<string, any>> {
    return await this.manager.waitForTasks(taskIds, timeout || this.config.timeout);
  }
  
  async streamSubagentOutput(taskId: string): AsyncGenerator<string, void, unknown> {
    for await (const chunk of this.manager.streamOutput(taskId)) {
      yield chunk;
    }
  }
}

// Usage Example
async function orchestrateSecurityAudit() {
  const orchestrator = new ClaudeSubagentOrchestrator({
    maxParallel: 5,
    timeout: 600000,
    configDir: process.env.CLAUDE_CONFIG_DIR || '/custom/claude'
  });
  
  // Create security auditor subagent
  await orchestrator.createSubagent({
    name: 'security-auditor',
    description: 'Comprehensive security analysis specialist',
    tools: ['Read', 'Grep', 'Bash', 'Write'],
    systemPrompt: `You are a security expert specializing in code audits.
    Focus on authentication, authorization, input validation, and OWASP compliance.`,
    metadata: {
      version: '2.0.0',
      team: 'security',
      reviewRequired: true
    }
  });
  
  // Define parallel security audit tasks
  const securityTasks: SubagentTask[] = [
    {
      agentName: 'security-auditor',
      task: 'Perform comprehensive authentication security audit',
      context: { 
        scope: 'authentication',
        paths: ['/src/auth/', '/src/middleware/auth.ts'],
        priority: 'high'
      }
    },
    {
      agentName: 'security-auditor', 
      task: 'Analyze API input validation and sanitization',
      context: {
        scope: 'input-validation',
        paths: ['/src/api/', '/src/validators/'],
        priority: 'high'
      }
    },
    {
      agentName: 'security-auditor',
      task: 'Review authorization and access control mechanisms',
      context: {
        scope: 'authorization', 
        paths: ['/src/rbac/', '/src/permissions/'],
        priority: 'medium'
      }
    }
  ];
  
  // Execute security audit in parallel
  console.log('Starting parallel security audit...');
  const taskIds = await orchestrator.spawnParallelSubagents(securityTasks);
  
  // Stream output from all tasks
  const streamPromises = taskIds.map(async (taskId, index) => {
    console.log(`\n=== Task ${index + 1} Output ===`);
    for await (const chunk of orchestrator.streamSubagentOutput(taskId)) {
      process.stdout.write(chunk);
    }
  });
  
  await Promise.all(streamPromises);
  
  // Wait for all tasks to complete
  const results = await orchestrator.waitForCompletion(taskIds);
  
  console.log('\n=== Security Audit Results ===');
  console.log(JSON.stringify(results, null, 2));
  
  return results;
}

// Execute the orchestration
orchestrateSecurityAudit()
  .then(results => console.log('Security audit completed successfully'))
  .catch(error => console.error('Security audit failed:', error));
```

## Production Deployment Patterns

### Docker Configuration

```dockerfile
FROM node:18-alpine

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Set up environment
ENV CLAUDE_CONFIG_DIR=/app/.claude
ENV CLAUDE_MAX_PARALLEL_SUBAGENTS=8
ENV CLAUDE_MEMORY_LIMIT=1024
ENV CLAUDE_TIMEOUT=600000
ENV CLAUDE_DEBUG=false
ENV CLAUDE_METRICS_ENABLED=true

# Create configuration directory
RUN mkdir -p /app/.claude/agents
WORKDIR /app

# Copy agent configurations
COPY .claude/agents/ /app/.claude/agents/
COPY .claude/settings.json /app/.claude/settings.json

# Set up entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/bash
# entrypoint.sh

# Validate environment
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable is required"
    exit 1
fi

# Set up configuration
claude config set --global apiKey "$ANTHROPIC_API_KEY"
claude config set --global maxSubagents "$CLAUDE_MAX_PARALLEL_SUBAGENTS"
claude config set --global timeout "$CLAUDE_TIMEOUT"

# Start Claude Code with monitoring
exec claude "$@"
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claude-code-subagents
  namespace: ai-tools
spec:
  replicas: 3
  selector:
    matchLabels:
      app: claude-code-subagents
  template:
    metadata:
      labels:
        app: claude-code-subagents
    spec:
      containers:
      - name: claude-code
        image: your-registry/claude-code:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: claude-secrets
              key: api-key
        - name: CLAUDE_CONFIG_DIR
          value: "/app/.claude"
        - name: CLAUDE_MAX_PARALLEL_SUBAGENTS
          value: "8"
        - name: CLAUDE_MEMORY_LIMIT
          value: "2048"
        - name: CLAUDE_TIMEOUT
          value: "900000"
        - name: CLAUDE_METRICS_ENABLED
          value: "true"
        - name: CLAUDE_AUDIT_LOG
          value: "true"
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: claude-config
          mountPath: /app/.claude
        - name: audit-logs
          mountPath: /var/log/claude
      volumes:
      - name: claude-config
        configMap:
          name: claude-config
      - name: audit-logs
        persistentVolumeClaim:
          claimName: claude-audit-logs

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: claude-config
  namespace: ai-tools
data:
  settings.json: |
    {
      "maxSubagents": 8,
      "timeout": 900000,
      "memoryLimit": 2048,
      "auditLogging": true,
      "metricsEnabled": true,
      "securityPolicy": "enterprise"
    }
```

### CI/CD Integration

```yaml
# .github/workflows/claude-subagents.yml
name: Claude Code Subagents CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-subagents:
    runs-on: ubuntu-latest
    
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      CLAUDE_CONFIG_DIR: ./.claude
      CLAUDE_MAX_PARALLEL_SUBAGENTS: 5
      CLAUDE_TIMEOUT: 300000
      CLAUDE_DEBUG: true
      
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Install Claude Code
      run: npm install -g @anthropic-ai/claude-code
      
    - name: Validate Agent Configurations
      run: |
        # Validate YAML frontmatter in agent files
        find .claude/agents -name "*.md" -exec claude validate-agent {} \;
        
    - name: Test Subagent Creation
      run: |
        # Test subagent creation and basic functionality
        claude --dry-run --test-mode create-agent test-agent "Test agent for CI"
        
    - name: Run Security Audit with Subagents
      run: |
        # Run parallel security audit using subagents
        claude --headless \
               --max-subagents 3 \
               --timeout 600 \
               --output-format json \
               security-audit-parallel
               
    - name: Validate Results
      run: |
        # Validate audit results and metrics
        python scripts/validate_audit_results.py
        
    - name: Upload Artifacts
      uses: actions/upload-artifact@v4
      with:
        name: claude-audit-results
        path: |
          audit-results.json
          subagent-metrics.json
          performance-profile.json
```

## Monitoring and Observability

### Metrics Collection

```python
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class SubagentMetrics:
    agent_name: str
    task_id: str
    start_time: datetime
    end_time: datetime = None
    duration_ms: int = None
    tokens_used: int = 0
    memory_peak_mb: int = 0
    cpu_usage_percent: float = 0.0
    status: str = "running"  # running|completed|failed|timeout
    error_message: str = None
    
class MetricsCollector:
    def __init__(self, output_file: str = None):
        self.metrics: List[SubagentMetrics] = []
        self.output_file = output_file or f"subagent-metrics-{int(time.time())}.json"
        
    def start_tracking(self, agent_name: str, task_id: str) -> SubagentMetrics:
        metric = SubagentMetrics(
            agent_name=agent_name,
            task_id=task_id,
            start_time=datetime.now()
        )
        self.metrics.append(metric)
        return metric
        
    def complete_tracking(self, task_id: str, 
                         tokens_used: int = 0, 
                         memory_peak_mb: int = 0,
                         status: str = "completed",
                         error_message: str = None):
        for metric in self.metrics:
            if metric.task_id == task_id:
                metric.end_time = datetime.now()
                metric.duration_ms = int((metric.end_time - metric.start_time).total_seconds() * 1000)
                metric.tokens_used = tokens_used
                metric.memory_peak_mb = memory_peak_mb
                metric.status = status
                metric.error_message = error_message
                break
                
    def export_metrics(self) -> Dict[str, Any]:
        # Convert metrics to serializable format
        serializable_metrics = []
        for metric in self.metrics:
            metric_dict = asdict(metric)
            metric_dict['start_time'] = metric.start_time.isoformat()
            if metric.end_time:
                metric_dict['end_time'] = metric.end_time.isoformat()
            serializable_metrics.append(metric_dict)
            
        # Calculate aggregate statistics
        completed_metrics = [m for m in self.metrics if m.status == "completed"]
        
        aggregates = {
            "total_tasks": len(self.metrics),
            "completed_tasks": len(completed_metrics),
            "failed_tasks": len([m for m in self.metrics if m.status == "failed"]),
            "average_duration_ms": sum(m.duration_ms for m in completed_metrics) / len(completed_metrics) if completed_metrics else 0,
            "total_tokens_used": sum(m.tokens_used for m in completed_metrics),
            "peak_memory_usage_mb": max((m.memory_peak_mb for m in completed_metrics), default=0),
            "success_rate": len(completed_metrics) / len(self.metrics) if self.metrics else 0
        }
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "metrics": serializable_metrics,
            "aggregates": aggregates
        }
        
        # Write to file
        with open(self.output_file, 'w') as f:
            json.dump(result, f, indent=2)
            
        return result

# Usage in subagent orchestration
def monitored_subagent_execution():
    collector = MetricsCollector("production-metrics.json")
    orchestrator = SubagentOrchestrator(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    tasks = [
        {"agent": "security-auditor", "task": "Audit authentication"},
        {"agent": "performance-analyzer", "task": "Profile database queries"},
        {"agent": "code-reviewer", "task": "Review recent changes"}
    ]
    
    task_ids = []
    for task_config in tasks:
        # Start tracking
        task_id = f"task-{int(time.time())}-{len(task_ids)}"
        metric = collector.start_tracking(task_config["agent"], task_id)
        
        # Execute subagent task
        try:
            result = orchestrator.spawn_subagent(
                task_config["agent"], 
                task_config["task"]
            )
            
            # Simulate completion (in real usage, this would come from the actual result)
            collector.complete_tracking(
                task_id=task_id,
                tokens_used=result.get('tokens_used', 0),
                memory_peak_mb=result.get('memory_peak_mb', 0),
                status="completed"
            )
            
        except Exception as e:
            collector.complete_tracking(
                task_id=task_id,
                status="failed", 
                error_message=str(e)
            )
            
        task_ids.append(task_id)
    
    # Export comprehensive metrics
    final_metrics = collector.export_metrics()
    print(f"Execution completed. Metrics saved to {collector.output_file}")
    return final_metrics
```

### Performance Monitoring Dashboard

```typescript
// monitoring-dashboard.ts
interface SubagentPerformanceMetrics {
  taskId: string;
  agentName: string;
  duration: number;
  tokensUsed: number;
  memoryPeak: number;
  status: 'running' | 'completed' | 'failed' | 'timeout';
  timestamp: string;
}

class SubagentMonitoringDashboard {
  private metrics: SubagentPerformanceMetrics[] = [];
  private metricsEndpoint: string;
  
  constructor(metricsEndpoint: string = '/api/metrics') {
    this.metricsEndpoint = metricsEndpoint;
    this.startPeriodicCollection();
  }
  
  private startPeriodicCollection(): void {
    setInterval(async () => {
      try {
        const response = await fetch(`${this.metricsEndpoint}/subagents`);
        const newMetrics = await response.json();
        this.updateMetrics(newMetrics);
      } catch (error) {
        console.error('Failed to collect metrics:', error);
      }
    }, 10000); // Collect every 10 seconds
  }
  
  private updateMetrics(newMetrics: SubagentPerformanceMetrics[]): void {
    this.metrics = [...this.metrics, ...newMetrics];
    // Keep only last 1000 metrics to prevent memory issues
    if (this.metrics.length > 1000) {
      this.metrics = this.metrics.slice(-1000);
    }
  }
  
  getAggregateMetrics(): {
    averageDuration: number;
    totalTokensUsed: number;
    successRate: number;
    peakMemoryUsage: number;
    activeSubagents: number;
  } {
    const completedTasks = this.metrics.filter(m => m.status === 'completed');
    const activeTasks = this.metrics.filter(m => m.status === 'running');
    
    return {
      averageDuration: completedTasks.reduce((sum, m) => sum + m.duration, 0) / completedTasks.length || 0,
      totalTokensUsed: completedTasks.reduce((sum, m) => sum + m.tokensUsed, 0),
      successRate: completedTasks.length / this.metrics.length || 0,
      peakMemoryUsage: Math.max(...this.metrics.map(m => m.memoryPeak), 0),
      activeSubagents: activeTasks.length
    };
  }
  
  getAgentPerformance(): Record<string, {
    taskCount: number;
    averageDuration: number;
    successRate: number;
    totalTokens: number;
  }> {
    const agentMetrics: Record<string, any> = {};
    
    for (const metric of this.metrics) {
      if (!agentMetrics[metric.agentName]) {
        agentMetrics[metric.agentName] = {
          tasks: [],
          completed: [],
          failed: []
        };
      }
      
      agentMetrics[metric.agentName].tasks.push(metric);
      if (metric.status === 'completed') {
        agentMetrics[metric.agentName].completed.push(metric);
      } else if (metric.status === 'failed') {
        agentMetrics[metric.agentName].failed.push(metric);
      }
    }
    
    const result: Record<string, any> = {};
    for (const [agentName, data] of Object.entries(agentMetrics)) {
      result[agentName] = {
        taskCount: data.tasks.length,
        averageDuration: data.completed.reduce((sum: number, m: any) => sum + m.duration, 0) / data.completed.length || 0,
        successRate: data.completed.length / data.tasks.length || 0,
        totalTokens: data.completed.reduce((sum: number, m: any) => sum + m.tokensUsed, 0)
      };
    }
    
    return result;
  }
  
  exportMetrics(): string {
    const aggregates = this.getAggregateMetrics();
    const agentPerformance = this.getAgentPerformance();
    
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      aggregates,
      agentPerformance,
      rawMetrics: this.metrics
    }, null, 2);
  }
}

// Usage
const dashboard = new SubagentMonitoringDashboard('https://api.company.com/metrics');

// Get real-time performance overview
setInterval(() => {
  const metrics = dashboard.getAggregateMetrics();
  console.log('Subagent Performance:', metrics);
}, 30000);

// Export metrics for analysis
const exportedMetrics = dashboard.exportMetrics();
console.log('Exported metrics:', exportedMetrics);
```

## Troubleshooting and Debugging

### Common Issues and Solutions

```bash
# Issue: Subagents not spawning
# Check environment and configuration
echo "CLAUDE_CONFIG_DIR: $CLAUDE_CONFIG_DIR"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:10}..."
ls -la ~/.claude/agents/
ls -la .claude/agents/

# Issue: Permission denied errors
# Fix file permissions
chmod -R 755 ~/.claude/
chmod -R 755 .claude/

# Issue: MCP resources not available to subagents (known bug #2169)
# Workaround: Use alternative tool access patterns
claude --allowed-tools Read,Write,Edit,Bash --disable-mcp-subagents

# Issue: Memory/resource exhaustion
# Monitor and limit resource usage
claude --memory-limit 512 --max-subagents 5 --timeout 300

# Issue: Context pollution between subagents
# Enable strict context isolation
claude --context-isolation strict --preserve-context false
```

### Debug Configuration

```bash
# Enable comprehensive debugging
export CLAUDE_DEBUG=true
export CLAUDE_LOG_LEVEL=debug
export CLAUDE_TRACE_SUBAGENTS=true
export ANTHROPIC_LOG=debug

# Run with verbose logging
claude --debug --verbose --log-file debug.log

# Profile subagent performance
claude --profile --memory-profiling --cpu-profiling
```

## Security and Best Practices

### Security Configuration

```yaml
# .claude/security-policy.yml
version: "1.0"
security:
  subagents:
    # Restrict tool access
    default_tools: ["Read", "Write", "Edit"]
    forbidden_tools: ["Terminal", "Network", "SystemInfo"]
    
    # Resource limits
    max_memory_mb: 1024
    max_cpu_percent: 50
    max_execution_time: 600
    
    # File system restrictions
    allowed_paths:
      - "/app/src/"
      - "/app/tests/"
      - "/tmp/claude-*"
    forbidden_paths:
      - "/etc/"
      - "/var/"
      - "/home/"
      - "/.ssh/"
    
    # Network restrictions
    network_access: false
    allowed_domains: []
    
    # Audit requirements
    audit_all_actions: true
    require_approval: false
    
  general:
    # API security
    rate_limiting: true
    requests_per_minute: 100
    
    # Data handling
    sanitize_inputs: true
    sanitize_outputs: true
    log_sensitive_data: false
```

### Production Best Practices

1. **Resource Management**
   - Set appropriate memory and CPU limits
   - Monitor resource usage continuously
   - Implement circuit breakers for failing subagents

2. **Security**
   - Use least-privilege tool access
   - Implement comprehensive audit logging
   - Regular security policy reviews

3. **Performance**
   - Optimize context window usage
   - Use caching for repeated operations
   - Monitor token consumption

4. **Reliability**
   - Implement retry mechanisms
   - Set appropriate timeouts
   - Plan for graceful degradation

5. **Observability**
   - Comprehensive metrics collection
   - Real-time monitoring dashboards
   - Alerting on failures and performance issues

## Conclusion

Claude Code's subagents feature provides powerful programmatic control for multi-agent AI workflows. Proper configuration using environment variables, command-line flags, and SDKs enables robust production deployments with comprehensive monitoring and security controls. The key to success lies in understanding the technical architecture, implementing proper resource management, and maintaining comprehensive observability across all subagent operations.

For the latest updates and additional features, consult the official Claude Code documentation and community resources.