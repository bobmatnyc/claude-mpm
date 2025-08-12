# Claude Code Hooks - Complete Reference

## Overview

Claude Code hooks provide programmatic control over Claude's execution flow by intercepting key events during task execution. Hooks enable sophisticated context filtering, workflow orchestration, and behavioral modification without changing Claude Code's core functionality.

## Hook Types & Events

### Core Hook Events

#### PreToolUse
Fired before Claude attempts to use any tool.

```typescript
interface PreToolUseEvent {
  toolName: string;
  parameters: Record<string, any>;
  context: {
    conversationId: string;
    messageId: string;
    timestamp: string;
    userPrompt: string;
  };
}

// Hook handler example
function onPreToolUse(event: PreToolUseEvent): HookResponse {
  // Block certain tools based on context
  if (event.toolName === 'Terminal' && !isAuthorized(event.context)) {
    return {
      action: 'block',
      reason: 'Terminal access not authorized for this context',
      alternative: 'Use safer file operations instead'
    };
  }
  
  // Modify parameters
  if (event.toolName === 'Write') {
    return {
      action: 'modify',
      parameters: {
        ...event.parameters,
        backup: true // Always create backups
      }
    };
  }
  
  return { action: 'continue' };
}
```

#### PostToolUse
Fired after Claude completes tool usage.

```typescript
interface PostToolUseEvent {
  toolName: string;
  parameters: Record<string, any>;
  result: {
    success: boolean;
    output: string;
    error?: string;
    duration: number;
  };
  context: ExecutionContext;
}

function onPostToolUse(event: PostToolUseEvent): HookResponse {
  // Log tool usage for analysis
  logToolUsage({
    tool: event.toolName,
    success: event.result.success,
    duration: event.result.duration,
    timestamp: new Date().toISOString()
  });
  
  // Auto-create tickets for certain patterns
  if (event.toolName === 'Write' && event.result.output.includes('TODO:')) {
    return {
      action: 'trigger',
      sideEffect: 'createTicket',
      data: extractTodoItems(event.result.output)
    };
  }
  
  return { action: 'continue' };
}
```

#### UserPromptSubmit
Fired when user submits a prompt, before processing begins.

```typescript
interface UserPromptSubmitEvent {
  prompt: string;
  context: {
    conversationHistory: Message[];
    activeFiles: string[];
    workingDirectory: string;
    environmentVars: Record<string, string>;
  };
}

function onUserPromptSubmit(event: UserPromptSubmitEvent): HookResponse {
  // Inject additional context
  if (event.prompt.includes('security')) {
    return {
      action: 'enhance',
      enhancedPrompt: `${event.prompt}\n\nAdditional context: Follow OWASP security guidelines and perform security validation.`,
      metadata: { securityMode: true }
    };
  }
  
  // Block sensitive operations
  if (event.prompt.includes('delete production')) {
    return {
      action: 'block',
      reason: 'Production deletion requires explicit confirmation',
      requireConfirmation: true
    };
  }
  
  return { action: 'continue' };
}
```

### Advanced Hook Events

#### WorkflowStart
Fired at the beginning of multi-step workflows.

```typescript
interface WorkflowStartEvent {
  workflowId: string;
  steps: WorkflowStep[];
  estimatedDuration: number;
  context: ExecutionContext;
}

function onWorkflowStart(event: WorkflowStartEvent): HookResponse {
  // Set up workflow monitoring
  initializeWorkflowTracking(event.workflowId);
  
  // Validate prerequisites
  const validation = validateWorkflowPrerequisites(event.steps);
  if (!validation.valid) {
    return {
      action: 'block',
      reason: validation.reason,
      suggestions: validation.fixes
    };
  }
  
  return { action: 'continue' };
}
```

#### ContextSwitch
Fired when Claude switches between different contexts or agents.

```typescript
interface ContextSwitchEvent {
  fromContext: string;
  toContext: string;
  reason: 'delegation' | 'specialization' | 'error_recovery';
  preservedState: Record<string, any>;
}

function onContextSwitch(event: ContextSwitchEvent): HookResponse {
  // Filter context for security
  if (event.toContext === 'external_api') {
    return {
      action: 'filter',
      allowedState: filterSensitiveData(event.preservedState)
    };
  }
  
  return { action: 'continue' };
}
```

## Hook Response Types

### Action Types

```typescript
type HookAction = 
  | 'continue'           // Allow normal execution
  | 'block'              // Prevent execution
  | 'modify'             // Change parameters
  | 'enhance'            // Add additional context
  | 'redirect'           // Change execution flow
  | 'defer'              // Postpone execution
  | 'filter'             // Remove/modify data
  | 'trigger';           // Trigger side effects

interface HookResponse {
  action: HookAction;
  reason?: string;
  parameters?: Record<string, any>;
  enhancedPrompt?: string;
  metadata?: Record<string, any>;
  alternative?: string;
  suggestions?: string[];
  sideEffect?: string;
  data?: any;
  delay?: number;
  requireConfirmation?: boolean;
  suppressOutput?: boolean;
}
```

## Hook Implementation Patterns

### TDD Guard Pattern
From the Claude PM Framework documentation - monitors development workflow compliance.

```typescript
class TDDGuardHook {
  private testRunHistory: TestResult[] = [];
  private fileChangeHistory: FileChange[] = [];
  
  onPreToolUse(event: PreToolUseEvent): HookResponse {
    // Block code changes without tests
    if (event.toolName === 'Write' && this.isCodeFile(event.parameters.path)) {
      const hasRecentTests = this.checkRecentTestActivity();
      
      if (!hasRecentTests) {
        return {
          action: 'block',
          reason: 'TDD violation: Write tests before implementing code',
          suggestions: [
            'Create unit tests for the functionality',
            'Run existing tests to ensure they fail',
            'Then implement the code to make tests pass'
          ]
        };
      }
    }
    
    return { action: 'continue' };
  }
  
  onPostToolUse(event: PostToolUseEvent): HookResponse {
    // Track test runs and file changes
    if (event.toolName === 'Bash' && event.parameters.command?.includes('test')) {
      this.recordTestRun(event.result);
    }
    
    if (event.toolName === 'Write') {
      this.recordFileChange(event.parameters.path, event.result);
    }
    
    return { action: 'continue' };
  }
  
  private checkRecentTestActivity(): boolean {
    const recentTests = this.testRunHistory.filter(
      test => Date.now() - test.timestamp < 5 * 60 * 1000 // 5 minutes
    );
    return recentTests.length > 0;
  }
}
```

### Context Filtering Pattern
Implements sophisticated context filtering for agent specialization.

```typescript
class ContextFilterHook {
  private agentContextRules: Record<string, ContextRule[]> = {
    'security': [
      { allow: ['security_config', 'vulnerability_data'], priority: 'high' },
      { block: ['user_credentials', 'api_keys'], priority: 'critical' }
    ],
    'qa': [
      { allow: ['test_config', 'coverage_data'], priority: 'high' },
      { block: ['production_data'], priority: 'critical' }
    ]
  };
  
  onContextSwitch(event: ContextSwitchEvent): HookResponse {
    const rules = this.agentContextRules[event.toContext];
    if (!rules) return { action: 'continue' };
    
    const filteredState = this.applyContextRules(event.preservedState, rules);
    
    return {
      action: 'filter',
      allowedState: filteredState,
      metadata: { 
        filteredFields: this.getFilteredFields(event.preservedState, filteredState),
        securityLevel: this.getSecurityLevel(event.toContext)
      }
    };
  }
  
  private applyContextRules(state: Record<string, any>, rules: ContextRule[]): Record<string, any> {
    let filteredState = { ...state };
    
    // Apply blocking rules first (higher security)
    for (const rule of rules.filter(r => r.block)) {
      for (const field of rule.block!) {
        if (field in filteredState) {
          delete filteredState[field];
        }
      }
    }
    
    // Apply allow rules (whitelist remaining)
    const allowedFields = rules
      .filter(r => r.allow)
      .flatMap(r => r.allow!);
    
    if (allowedFields.length > 0) {
      filteredState = Object.fromEntries(
        Object.entries(filteredState).filter(([key]) => 
          allowedFields.some(pattern => this.matchesPattern(key, pattern))
        )
      );
    }
    
    return filteredState;
  }
}
```

### Workflow Orchestration Pattern
Coordinates multi-agent workflows with dependency management.

```typescript
class WorkflowOrchestrationHook {
  private activeWorkflows: Map<string, WorkflowState> = new Map();
  private dependencies: Map<string, string[]> = new Map();
  
  onWorkflowStart(event: WorkflowStartEvent): HookResponse {
    // Initialize workflow tracking
    this.activeWorkflows.set(event.workflowId, {
      id: event.workflowId,
      steps: event.steps,
      currentStep: 0,
      status: 'running',
      results: []
    });
    
    // Validate dependencies
    const unmetDependencies = this.checkDependencies(event.steps);
    if (unmetDependencies.length > 0) {
      return {
        action: 'defer',
        reason: 'Waiting for dependencies',
        data: { pendingDependencies: unmetDependencies },
        delay: 5000 // 5 second delay
      };
    }
    
    return { action: 'continue' };
  }
  
  onPostToolUse(event: PostToolUseEvent): HookResponse {
    // Update workflow progress
    const workflow = this.findWorkflowForEvent(event);
    if (workflow) {
      this.updateWorkflowProgress(workflow, event);
      
      // Trigger next step if current completed
      if (this.isStepComplete(workflow)) {
        return {
          action: 'trigger',
          sideEffect: 'nextWorkflowStep',
          data: { workflowId: workflow.id }
        };
      }
    }
    
    return { action: 'continue' };
  }
  
  private checkDependencies(steps: WorkflowStep[]): string[] {
    const unmet: string[] = [];
    
    for (const step of steps) {
      if (step.dependencies) {
        for (const dep of step.dependencies) {
          if (!this.isDependencyMet(dep)) {
            unmet.push(dep);
          }
        }
      }
    }
    
    return unmet;
  }
}
```

## Hook Configuration

### JSON Configuration
```json
{
  "hooks": {
    "preToolUse": [
      {
        "name": "security-filter",
        "enabled": true,
        "priority": 100,
        "conditions": {
          "tools": ["Terminal", "Bash", "Write"],
          "contexts": ["production", "sensitive"]
        },
        "handler": "./hooks/security-filter.js"
      },
      {
        "name": "tdd-guard",
        "enabled": true,
        "priority": 90,
        "conditions": {
          "filePatterns": ["*.js", "*.ts", "*.py"],
          "excludePaths": ["test/", "spec/"]
        },
        "handler": "./hooks/tdd-guard.js"
      }
    ],
    "postToolUse": [
      {
        "name": "ticket-creator",
        "enabled": true,
        "priority": 50,
        "conditions": {
          "outputPatterns": ["TODO:", "FIXME:", "BUG:"]
        },
        "handler": "./hooks/ticket-creator.js"
      }
    ],
    "userPromptSubmit": [
      {
        "name": "context-enhancer",
        "enabled": true,
        "priority": 80,
        "conditions": {
          "promptPatterns": ["security", "performance", "optimization"]
        },
        "handler": "./hooks/context-enhancer.js"
      }
    ]
  },
  "global": {
    "timeoutMs": 5000,
    "retryCount": 3,
    "logging": {
      "level": "info",
      "destination": "./logs/hooks.log"
    }
  }
}
```

### Environment Variables
```bash
# Hook system configuration
CLAUDE_HOOKS_ENABLED=true
CLAUDE_HOOKS_CONFIG_PATH=./config/hooks.json
CLAUDE_HOOKS_TIMEOUT=5000
CLAUDE_HOOKS_LOG_LEVEL=info

# Security hooks
CLAUDE_SECURITY_HOOKS_ENABLED=true
CLAUDE_SECURITY_WHITELIST="Read,Write,Edit"
CLAUDE_SECURITY_BLACKLIST="Terminal,Network"

# Development hooks
CLAUDE_TDD_HOOKS_ENABLED=true
CLAUDE_TDD_STRICT_MODE=false
CLAUDE_TDD_TEST_TIMEOUT=30000

# Workflow hooks
CLAUDE_WORKFLOW_HOOKS_ENABLED=true
CLAUDE_WORKFLOW_MAX_PARALLEL=5
CLAUDE_WORKFLOW_RETRY_ATTEMPTS=3
```

## Hook Development Best Practices

### Performance Considerations
```typescript
// ✅ Good: Async hooks with timeout
async function performantHook(event: HookEvent): Promise<HookResponse> {
  const timeoutPromise = new Promise<never>((_, reject) => 
    setTimeout(() => reject(new Error('Hook timeout')), 5000)
  );
  
  const workPromise = (async () => {
    // Expensive operation
    const result = await someExpensiveOperation(event);
    return { action: 'continue', data: result };
  })();
  
  return Promise.race([workPromise, timeoutPromise]);
}

// ❌ Bad: Synchronous blocking hook
function blockingHook(event: HookEvent): HookResponse {
  // Synchronous expensive operation blocks execution
  const result = expensiveSync

eneiveOperation(event);
  return { action: 'continue', data: result };
}
```

### Error Handling
```typescript
function robustHook(event: HookEvent): HookResponse {
  try {
    // Hook logic
    const result = processEvent(event);
    
    return {
      action: 'continue',
      data: result,
      metadata: { processed: true }
    };
  } catch (error) {
    // Log error but don't break execution
    console.error('Hook error:', error);
    
    return {
      action: 'continue', // Graceful degradation
      metadata: { 
        error: error.message,
        fallback: true 
      }
    };
  }
}
```

### Memory Management
```typescript
class StatefulHook {
  private cache = new Map<string, CacheEntry>();
  private readonly MAX_CACHE_SIZE = 1000;
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  
  onEvent(event: HookEvent): HookResponse {
    // Clean expired entries
    this.cleanExpiredCache();
    
    // Limit cache size
    if (this.cache.size > this.MAX_CACHE_SIZE) {
      this.evictOldestEntries();
    }
    
    // Process event...
    return { action: 'continue' };
  }
  
  private cleanExpiredCache(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.CACHE_TTL) {
        this.cache.delete(key);
      }
    }
  }
}
```

## Advanced Hook Patterns

### Hook Composition
```typescript
// Compose multiple hooks into a pipeline
class HookPipeline {
  private hooks: Hook[] = [];
  
  addHook(hook: Hook): void {
    this.hooks.push(hook);
  }
  
  async execute(event: HookEvent): Promise<HookResponse> {
    let currentEvent = event;
    let finalResponse: HookResponse = { action: 'continue' };
    
    for (const hook of this.hooks) {
      const response = await hook.handle(currentEvent);
      
      // If any hook blocks, stop execution
      if (response.action === 'block') {
        return response;
      }
      
      // Modify event for next hook if needed
      if (response.action === 'modify') {
        currentEvent = { ...currentEvent, ...response.parameters };
      }
      
      // Accumulate metadata
      finalResponse.metadata = {
        ...finalResponse.metadata,
        ...response.metadata
      };
    }
    
    return finalResponse;
  }
}
```

### Conditional Hook Execution
```typescript
interface HookCondition {
  evaluate(event: HookEvent): boolean;
}

class PatternCondition implements HookCondition {
  constructor(private patterns: string[]) {}
  
  evaluate(event: HookEvent): boolean {
    return this.patterns.some(pattern => 
      event.toString().includes(pattern)
    );
  }
}

class ConditionalHook {
  constructor(
    private condition: HookCondition,
    private hook: Hook
  ) {}
  
  async handle(event: HookEvent): Promise<HookResponse> {
    if (this.condition.evaluate(event)) {
      return this.hook.handle(event);
    }
    
    return { action: 'continue' };
  }
}
```

## Debugging and Monitoring

### Hook Debugging
```typescript
class DebuggableHook {
  constructor(private debugMode: boolean = false) {}
  
  async handle(event: HookEvent): Promise<HookResponse> {
    if (this.debugMode) {
      console.log('Hook input:', JSON.stringify(event, null, 2));
    }
    
    const startTime = Date.now();
    const response = await this.processEvent(event);
    const duration = Date.now() - startTime;
    
    if (this.debugMode) {
      console.log('Hook output:', JSON.stringify(response, null, 2));
      console.log('Hook duration:', duration, 'ms');
    }
    
    // Log performance metrics
    this.logMetrics({
      hookName: this.constructor.name,
      duration,
      success: response.action !== 'block',
      timestamp: new Date().toISOString()
    });
    
    return response;
  }
}
```

### Hook Monitoring Dashboard
```typescript
interface HookMetrics {
  hookName: string;
  executionCount: number;
  averageDuration: number;
  successRate: number;
  lastError?: string;
  errorCount: number;
}

class HookMonitor {
  private metrics: Map<string, HookMetrics> = new Map();
  
  recordExecution(hookName: string, duration: number, success: boolean, error?: string): void {
    const existing = this.metrics.get(hookName) || {
      hookName,
      executionCount: 0,
      averageDuration: 0,
      successRate: 1,
      errorCount: 0
    };
    
    existing.executionCount++;
    existing.averageDuration = (existing.averageDuration + duration) / 2;
    existing.successRate = (existing.successRate * (existing.executionCount - 1) + (success ? 1 : 0)) / existing.executionCount;
    
    if (!success) {
      existing.errorCount++;
      existing.lastError = error;
    }
    
    this.metrics.set(hookName, existing);
  }
  
  getMetrics(): HookMetrics[] {
    return Array.from(this.metrics.values());
  }
  
  exportMetrics(): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      hooks: this.getMetrics(),
      summary: {
        totalHooks: this.metrics.size,
        totalExecutions: Array.from(this.metrics.values()).reduce((sum, m) => sum + m.executionCount, 0),
        averageSuccessRate: Array.from(this.metrics.values()).reduce((sum, m) => sum + m.successRate, 0) / this.metrics.size
      }
    }, null, 2);
  }
}
```

## Integration Examples

### MCP Server Hook Integration
```typescript
// Hook integration with MCP servers
class MCPHookIntegration {
  async onPreToolUse(event: PreToolUseEvent): Promise<HookResponse> {
    // Check with MCP resources before tool use
    const resourceCheck = await this.checkMCPResources(event.toolName);
    
    if (!resourceCheck.available) {
      return {
        action: 'block',
        reason: 'MCP resource not available',
        alternative: resourceCheck.alternative
      };
    }
    
    return { action: 'continue' };
  }
  
  private async checkMCPResources(toolName: string): Promise<{available: boolean, alternative?: string}> {
    // Query MCP server for resource availability
    try {
      const response = await fetch('http://localhost:3000/mcp/resources/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolName })
      });
      
      return await response.json();
    } catch (error) {
      console.error('MCP check failed:', error);
      return { available: true }; // Fail open
    }
  }
}
```

This comprehensive reference covers all aspects of Claude Code hooks as detailed in the provided documentation, including implementation patterns, configuration options, best practices, and real-world examples from the Claude PM Framework.