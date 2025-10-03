# BASE PROMPT ENGINEER Agent Instructions

All Prompt Engineer agents inherit these common patterns and requirements for Claude 4.5 models.

## Claude 4.5 Architecture Understanding

### Model Selection Decision Matrix

**Default Choice: Claude Sonnet 4.5**
- All coding tasks (77.2% SWE-bench vs Opus 74.5%)
- Analysis and research tasks
- Autonomous agents (30-hour capacity vs Opus 7-hour)
- Interactive UIs requiring low latency
- Cost-sensitive deployments (5x cheaper than Opus)
- Multi-agent worker roles

**Strategic Choice: Claude Opus 4.1/4.5**
- Architectural design and strategic planning
- Deep multi-step logical inference
- Refactoring strategy and migration planning
- Multi-agent orchestrator role (90.2% improvement leading 3-5 Sonnet workers)
- High-level competition math problems
- Complex autonomous agents requiring advanced planning (OSWorld 61.4%)

**Cost Impact**: Hybrid approach (80% Sonnet, 20% Opus) = 65% cost reduction vs Opus-only

---

## Extended Thinking Configuration

### Strategic Activation Guidelines

**When to Enable Extended Thinking:**
- Complex reasoning tasks (math, logic, deep analysis)
- Multi-step coding projects requiring planning
- Extended agentic work across 30+ hour sessions
- Deep research requiring comprehensive investigation

**When to Disable Extended Thinking:**
- Simple tool use and instruction following
- High-throughput operations requiring speed
- Cost-sensitive batch processing
- When prompt caching is critical (extended thinking invalidates cache)

### Budget Configuration Strategy

```python
# Task-based budget allocation
thinking_budgets = {
    "simple": 0,           # Disabled for basic tasks
    "standard": 16_384,    # Baseline for complex reasoning
    "complex": 32_768,     # Deep analysis and planning
    "critical": 65_536     # Maximum for most critical decisions
}
```

**Critical Constraints:**
- Extended thinking invalidates prompt caching (90% cost savings lost)
- Cannot combine with temperature modifications
- Cannot use with forced tool use (`tool_choice`)
- Cannot use with response prefilling
- Requires streaming for max_tokens > 21,333

### Performance Optimization

**Cache-Aware Design:**
- Evaluate cache savings (90% cost + 85% latency) vs thinking quality gain
- For repeated contexts, consider disabling extended thinking
- Use batch processing for budgets >32k tokens

**Budget Monitoring:**
- Start at minimum viable budget (16k)
- Monitor actual token usage (Claude may not use full budget)
- Increment gradually based on task complexity
- Sonnet 4.5 includes built-in context awareness for budget tracking

---

## High-Level vs Prescriptive Guidance

### Core Principle
Claude 4 models perform 40% better with conceptual guidance than step-by-step prescriptive instructions.

### Anti-Pattern (Avoid)
```markdown
❌ "Follow these exact steps:
1. First, analyze the code structure
2. Then, identify potential issues
3. Next, propose solutions
4. Finally, implement fixes"
```

### Best Practice (Use)
```markdown
✅ "Analyze this codebase for architectural improvements.
Focus on: scalability, maintainability, performance.
Think deeply about trade-offs and provide principled recommendations."
```

**Rationale**: The model's creativity in approaching problems may exceed human ability to prescribe optimal thinking processes. Give Claude room to apply its reasoning capabilities.

---

## Explicit Behavior Specification

### Critical Change in Claude 4
Claude 4 requires explicit instructions for "above and beyond" behaviors that Claude 3 performed implicitly.

### Migration Pattern
```markdown
# Claude 3 (implicit) - NO LONGER SUFFICIENT
"Review this code"

# Claude 4 (explicit) - REQUIRED
"Review this code with comprehensive analysis:
- Go beyond the basics to create fully-featured implementation
- Consider edge cases and error handling
- Suggest architectural improvements
- Provide production-ready recommendations
- Include performance and security considerations"
```

**Key Learning**: Generic prompts like "be helpful" or "be thorough" are insufficient. Specify exact behaviors desired.

---

## Tool Integration Patterns

### Parallel Tool Execution

**Core Capability**: Claude 4 can call multiple independent tools simultaneously.

```markdown
# System prompt guidance
"""
You can call multiple independent tools simultaneously.
Analyze which tools don't depend on each other's results
and execute them in parallel to maximize efficiency.

Example: When analyzing a codebase:
- Run `grep` for patterns AND `git log` for history AND `test` suite
  ALL AT ONCE in a single response
"""
```

**Performance Impact**: Sonnet 4.5 excels at maximizing parallel bash commands and tool usage.

### The "Think" Tool Pattern

For tool-heavy workflows requiring mid-execution reflection:

```python
# Tool definition
{
    "name": "think",
    "description": "Use this to pause and reflect on whether you have all needed information before proceeding",
    "input_schema": {
        "type": "object",
        "properties": {
            "reflection": {"type": "string"}
        }
    }
}
```

**Optimized Prompt Pairing:**
```markdown
"""
After receiving tool results, carefully reflect on:
1. Quality and completeness of information
2. Optimal next steps based on findings
3. Any gaps requiring additional tool calls

Use <thinking> to plan, then execute best next action.
"""
```

### Sequential vs Parallel Decision Logic

**Principle**: Chain dependent tools sequentially; execute independent tools in parallel.

```python
# Decision tree
if tools_are_independent(tool_A, tool_B):
    execute_parallel([tool_A, tool_B])
else:
    result_A = execute(tool_A)
    result_B = execute(tool_B, input=result_A)
```

**Critical**: Never force parallel execution of dependent tools (Claude will guess parameters).

### Robust Error Handling

```markdown
# Tool execution pattern
"""
For each tool call:
1. Validate inputs before execution
2. Handle missing/invalid parameters gracefully
3. Implement timeout and retry logic
4. Provide alternative approaches on failure

Example error handling:
- If database query fails → try cached data
- If API times out → retry with exponential backoff
- If tool unavailable → use alternative tool

Always explain what went wrong and what you're trying next.
"""
```

---

## Multi-Agent Orchestration

### Orchestrator-Worker Pattern

**Proven Architecture**: 90.2% improvement over single-agent Opus.

```python
# Optimal configuration
{
    "orchestrator": "claude-opus-4",  # Strategic planning
    "workers": [
        "claude-sonnet-4",  # Coding tasks
        "claude-sonnet-4",  # Analysis tasks
        "claude-sonnet-4",  # Research tasks
    ],
    "pattern": "parallel_delegation",
    "tools_per_agent": 3  # Each subagent uses 3+ tools in parallel
}
```

**Orchestrator Prompt:**
```markdown
"""
You coordinate specialized subagents for complex tasks:
1. Analyze task and decompose into parallel workstreams
2. Spin up 3-5 subagents simultaneously
3. Each subagent should use multiple tools in parallel
4. Synthesize results into coherent solution
"""
```

**Use Cases:**
- Complex projects spanning multiple domains
- Extended autonomous work (30+ hours)
- Research systems requiring broad coverage
- Production systems requiring fault tolerance

---

## Structured Output Methods

### Method #1: Tool-Based JSON Schema (Most Reliable)

**Anthropic Recommended**: Use tool calling as structured output mechanism.

```python
# Define output structure as tool
{
    "name": "provide_analysis",
    "description": "Provide structured analysis results",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "recommendation": {"type": "string"}
                    },
                    "required": ["issue", "severity", "recommendation"]
                }
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["summary", "findings", "confidence"]
    }
}
```

**Why Most Reliable**: Claude Sonnet 3.5+ handles even most complex schemas excellently.

### Method #2: Response Prefilling

Bypass preambles and enforce format from first token:

```python
# API request structure
{
    "messages": [
        {"role": "user", "content": "Analyze this code"},
        {"role": "assistant", "content": "{\"analysis\": "}  # Prefill
    ]
}
```

**Benefits:**
- Skips conversational preamble
- Forces immediate structured output
- Ensures format compliance from first token

**Limitation**: Cannot use with extended thinking mode

### Method #3: XML Tags for Structure

```markdown
# Prompt template
"""
Provide your analysis in this structure:

<analysis>
  <summary>High-level findings</summary>
  <findings>
    <finding>
      <issue>Description</issue>
      <severity>Level</severity>
      <recommendation>Solution</recommendation>
    </finding>
  </findings>
  <confidence>0.0-1.0</confidence>
</analysis>

Use these exact tags. Do not add bold, headers, or other formatting.
"""
```

**Best Practices:**
- Keep tags flat (avoid deep nesting)
- Use consistent naming conventions
- Specify tag structure explicitly
- Avoid tags-inside-tags confusion

### Field Descriptions for Schema Clarity

Claude interprets field descriptions effectively:

```python
{
    "risk_score": {
        "type": "number",
        "description": "Overall risk assessment from 0.0 (no risk) to 1.0 (critical risk). Consider: code complexity, security vulnerabilities, maintainability issues, and performance bottlenecks."
    }
}
```

### Extended Thinking Structured Output Caveat

**Critical Limitation**: Sonnet 3.7+ structured output behaves differently with extended thinking enabled.

**Workaround:**
1. Use extended thinking for reasoning
2. Separate API call for structured output
3. OR use tool-based enforcement (works with extended thinking)

**Important**: Test structured output with extended thinking before production deployment.

---

## Context & Memory Management

### Prompt Caching for 90% Cost Savings

**Performance Impact:**
- 90% cost reduction for repeated context
- 85% latency reduction for long prompts
- 5-minute TTL (refreshed on each use)

```python
# Prompt caching configuration
{
    "system": [
        {
            "type": "text",
            "text": "You are an expert code reviewer...",
            "cache_control": {"type": "ephemeral"}  # Cache this
        }
    ],
    "messages": [...]
}
```

**Cache Design Principles:**
- Place static content first
- Use up to 4 cache breakpoints
- Minimum 1024 tokens for caching
- TTL default: 5 minutes (refreshed on use)

**Critical**: Extended thinking changes invalidate cached prompts.

### Sliding Window with Progressive Summarization

For processing large context (>100K tokens):

```python
# Sliding window configuration
window_config = {
    "size": 50_000,  # 50K tokens per segment
    "overlap": 15_000,  # 30% overlap for continuity
    "summary_carry": True  # Carry forward compact summaries
}
```

**Prompt Pattern:**
```markdown
"""
Process this document in segments:

Segment 1 (tokens 1-50K):
- Analyze and extract key points
- Generate compact summary (max 500 tokens)

Segment 2 (tokens 35K-85K):
- Reference: [Summary from Segment 1]
- Continue analysis with prior context
- Update summary

[Repeat with progressive summary accumulation]
"""
```

**Performance:**
- Preserves continuity across 200K context
- 76% prompt compression achieved
- 30% overlap ensures no information loss

### Strategic Anchor Labels

Use unique tags to reference earlier content without reloading:

```markdown
# Label important sections
<ANCHOR:architecture_decision_001>
We chose microservices because of:
- Team autonomy
- Independent scaling
- Technology flexibility
</ANCHOR>

# Later reference (100K tokens later)
"Referring to ANCHOR:architecture_decision_001, how does this new requirement align with our microservices decision?"
```

**Benefits:**
- Helps Claude recall specific sections
- Avoids reloading large context
- Maintains coherence across long conversations

### Hierarchical Summarization

For documents >100K tokens:

```python
# Stage 1: Chunk processing (50K chunks)
chunk_summaries = []
for chunk in document_chunks:
    summary = analyze(chunk, "Extract key points, max 200 tokens")
    chunk_summaries.append(summary)

# Stage 2: Aggregate summaries
section_summary = synthesize(chunk_summaries, "Create cohesive overview, max 500 tokens")

# Stage 3: Final synthesis
final_analysis = deep_analysis(section_summary, document_metadata)
```

### Context-Aware Token Budget Tracking (Sonnet 4.5)

**Unique to Sonnet 4.5**: Built-in context window tracking.

```markdown
"""
You have context awareness of your token budget.
Track your remaining window throughout this conversation.

When approaching limits:
1. Identify what context can be summarized
2. Preserve critical information
3. Archive less relevant details
4. Notify me before hitting limits

Manage context proactively for optimal task execution.
"""
```

---

## Chain-of-Thought with Self-Consistency

### Zero-Shot CoT Pattern

```markdown
"Let's think step by step:
1. [Identify problem components]
2. [Analyze relationships]
3. [Build solution incrementally]
4. [Verify conclusion]

Now provide your answer."
```

### Self-Consistency Enhancement

```markdown
"Generate 3 different reasoning approaches for this problem.
For each approach:
- State your reasoning chain
- Arrive at conclusion
- Explain confidence level

Then identify the most consistent answer across approaches."
```

**Performance Improvements:**
- GSM8K: +17.9%
- SVAMP: +11.0%
- AQuA: +12.2%

**Best For**: Multi-step reasoning, mathematical problem solving, logical inference

---

## Performance & Cost Optimization

### Hybrid Model Deployment Strategy

```python
# Optimal deployment
architecture = {
    "default": "sonnet-4.5",  # 80% of tasks
    "planning": "opus-4.1",   # 20% of strategic tasks
    "orchestrator": "opus-4.1",  # Multi-agent coordinator
    "workers": ["sonnet-4.5"] * 3  # Parallel execution agents
}
```

**Cost Savings**: 65% reduction vs Opus-only deployment

**Model Selection Routing:**
```python
def select_model(task):
    if task.type == "coding":
        return "sonnet-4.5"  # Better + cheaper
    elif task.type in ["refactor_strategy", "architecture_design", "complex_planning"]:
        return "opus-4.1"  # Deep reasoning
    elif task.type == "autonomous_agent" and task.duration > 20_hours:
        return "sonnet-4.5"  # 30-hour capacity
    else:
        return "sonnet-4.5"  # Default choice
```

### Batch Processing for Efficiency

For budgets >32k or high-volume tasks:

```python
# Batch configuration
batch_config = {
    "thinking_budget": 32_000,  # Use batching above this
    "requests_per_batch": 10,
    "parallel_execution": True
}
```

### Temperature and Tool Use Compatibility

**Critical Incompatibilities** with extended thinking:

```python
# ❌ Invalid configuration
{
    "thinking": {"type": "enabled", "budget_tokens": 16384},
    "temperature": 0.7,  # NOT COMPATIBLE
    "tool_choice": {"type": "tool", "name": "specific_tool"}  # NOT COMPATIBLE
}

# ✅ Valid configuration
{
    "thinking": {"type": "enabled", "budget_tokens": 16384}
    # No temperature modification
    # No forced tool use
    # No response prefilling
}
```

---

## Critical Anti-Patterns to Avoid

### Anti-Pattern #1: Over-Specification Paradox
- ❌ **DON'T**: Provide step-by-step prescriptive guidance
- ✅ **DO**: Give high-level instructions and let Claude's creativity approach problems
- **Impact**: 40% reduction in logic errors with proper thinking tag usage

### Anti-Pattern #2: Wrong Model Selection
- ❌ **DON'T**: Default to Opus for complex coding or assume higher cost = better results
- ✅ **DO**: Use Sonnet 4.5 for all coding tasks; reserve Opus for deep reasoning/planning
- **Impact**: 65% cost reduction with hybrid approach

### Anti-Pattern #3: Extended Thinking Configuration Mistakes
- ❌ **DON'T**: Enable extended thinking by default or use maximum budgets without testing
- ❌ **DON'T**: Combine extended thinking with temperature, forced tool use, or prefilling
- ✅ **DO**: Start with 16k budget, increment based on task complexity, disable for simple tasks
- **Impact**: Up to 90% cache savings lost, 2-5x response time increase

### Anti-Pattern #4: Generic "Be Helpful" Prompts
- ❌ **DON'T**: Rely on Claude 4 to automatically provide comprehensive responses
- ✅ **DO**: Explicitly specify all desired behaviors and quality standards
- **Impact**: Significant quality improvement with explicit instructions

### Anti-Pattern #5: Ignoring Cache Invalidation
- ❌ **DON'T**: Enable extended thinking when prompt caching is critical
- ✅ **DO**: Evaluate cache savings (90% cost + 85% latency) vs thinking quality gain
- **Impact**: Loss of 90% cost savings and 85% latency reduction

---

## Benchmark Performance Data

### SWE-bench (Coding Tasks)
- **Sonnet 4.5**: 77.2% (Winner)
- **Opus 4.1**: 74.5%

### OSWorld (Complex Agent Planning)
- **Opus 4.1**: 61.4% (Winner)
- **Sonnet 4.5**: 44.0%

### Cost Comparison
- **Sonnet 4.5**: $3/MTok input, $15/MTok output
- **Opus 4.1**: $15/MTok input, $75/MTok output
- **Ratio**: Opus is 5x more expensive

### Autonomous Operation Duration
- **Sonnet 4.5**: 30 hours
- **Opus 4**: 7 hours

---

## Prompt Engineering Evaluation Framework

### Quality Metrics

**Clarity Assessment:**
- Ambiguity detection and resolution
- Precision of language and terminology
- Logical flow and sequence coherence
- Absence of conflicting directives

**Effectiveness Indicators:**
- Actionability vs descriptive content ratio
- Measurable outcomes and success criteria
- Clear delegation boundaries
- Appropriate specificity levels

**Efficiency Measures:**
- Content density and information theory
- Redundancy elimination without information loss
- Optimal length for comprehension
- Strategic formatting and structure

### Cross-Model Testing

**Compatibility Metrics:**
- Response consistency across models
- Instruction following accuracy per model
- Format adherence and output compliance
- Model-specific feature utilization

**Performance Benchmarks:**
- Response quality scoring with rubrics
- Token efficiency and cost analysis
- Processing speed measurements
- Semantic accuracy validation

**Robustness Testing:**
- Edge case handling across models
- Adversarial prompt resistance
- Input variation sensitivity
- Failure mode identification

### A/B Testing Framework

**Test Design:**
1. Create prompt variations (2-5 alternatives)
2. Define measurable success criteria
3. Test across representative sample (n ≥ 30)
4. Measure: quality, consistency, cost, latency
5. Statistical analysis (confidence intervals, significance)

**Metrics Collection:**
- Response quality scores (1-5 scale)
- Task completion rate
- Token usage (input + output)
- Response time (latency)
- Error rate and failure modes

---

## Implementation Checklist

### Before Deploying Prompts

✅ **Model Selection Verified**
- Sonnet 4.5 for coding/analysis
- Opus for strategic planning only
- Cost/performance trade-off analyzed

✅ **Extended Thinking Configuration**
- Task complexity assessed
- Appropriate budget allocated (16k-64k)
- Cache invalidation impact considered
- Incompatibilities checked (temperature, tool_choice, prefilling)

✅ **Tool Integration**
- Parallel execution opportunities identified
- Tool dependencies mapped
- Error handling implemented
- "Think" tool added if needed

✅ **Structured Output Method**
- Tool-based schema preferred
- Prefilling configured if needed
- XML tags defined clearly
- Extended thinking compatibility tested

✅ **Context Management**
- Prompt caching configured
- Sliding window for >100K tokens
- Anchor labels for long conversations
- Progressive summarization planned

✅ **Explicit Behaviors Specified**
- All desired actions explicitly stated
- Quality standards clearly defined
- Edge cases and error handling covered
- Production-ready requirements listed

✅ **Testing Completed**
- Prompt tested on representative samples
- Cross-model compatibility verified (if applicable)
- Performance metrics collected
- Cost analysis completed

---

## Key Resources

### Official Anthropic Documentation
- Claude 4 Prompt Engineering Best Practices
- Extended Thinking Technical Guide
- Tool Use and Function Calling
- Prompt Caching Documentation
- Claude Sonnet 4.5 Release Notes
- Multi-Agent Research System Engineering

### Performance Benchmarks
- System Card: Claude Opus 4 & Sonnet 4
- SWE-bench Coding Evaluation
- OSWorld Agent Planning Benchmark
- Cost-Performance Analysis Studies

### Implementation Guides
- Claude Code Best Practices
- Enterprise AI Development with Claude
- Production Development with Claude
- AWS Bedrock Claude Integration Guide

---

## Version History

**v1.0.0** (October 2025)
- Initial BASE_PROMPT_ENGINEER.md creation
- Comprehensive Claude 4.5 best practices integration
- Extended thinking optimization guidelines
- Multi-model routing decision matrix
- Tool orchestration patterns
- Structured output enforcement methods
- Context management strategies (200K tokens)
- Performance and cost optimization techniques
- Anti-pattern identification and mitigation
