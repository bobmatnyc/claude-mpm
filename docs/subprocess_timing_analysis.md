# Subprocess Orchestrator Timing Analysis

## Current Performance

### Measured Timing
- **Single `--print` call**: ~4.1 seconds (measured)
- **PM subprocess**: 30-second timeout, typically completes in 4-5 seconds
- **Agent subprocess**: 60-second timeout, typically completes in 4-5 seconds
- **Total for simple delegation**: ~8-10 seconds

### Parallel Execution
- Agent tasks run in parallel using `ThreadPoolExecutor(max_workers=8)`
- For N agents: Total time ≈ PM time + max(agent times)
- Example: 4 agents = ~8 seconds (not 16+ seconds)

## Performance Bottlenecks

### 1. `--print` Mode Overhead
Each `--print` call involves:
- Full Claude initialization
- Model loading
- Context processing
- Response generation
- Clean shutdown

### 2. No Context Reuse
- Each subprocess starts fresh
- No session ID reuse between PM and agents
- Framework instructions loaded every time

### 3. Sequential PM → Agent Flow
- Must wait for PM to complete before starting agents
- Can't stream PM output to detect delegations early

## Optimization Opportunities

### 1. Session ID Reuse ⚡ (High Impact)
```python
# Current: Each subprocess is independent
launcher.launch_oneshot(message=prompt)  # New session each time

# Optimized: Reuse session context
pm_session_id = generate_session_id()
launcher.launch_oneshot(message=pm_prompt, session_id=pm_session_id)
launcher.launch_oneshot(message=agent_prompt, session_id=pm_session_id)  # Reuse context
```

**Benefit**: Could reduce agent calls by 1-2 seconds each

### 2. Streaming Delegation Detection 🚀 (Medium Impact)
```python
# Instead of waiting for full PM response:
process = launcher.launch(mode=LaunchMode.PRINT, ...)
for line in process.stdout:
    if delegation := detect_delegation(line):
        # Start agent subprocess immediately
        submit_agent_task(delegation)
```

**Benefit**: Agents start ~2-3 seconds earlier

### 3. Interactive Mode with Multiplexing 📡 (Complex but Fast)
Replace `--print` with interactive mode + output parsing:
```python
# Single interactive Claude session
process = launcher.launch_interactive()
# Send PM prompt
process.stdin.write(pm_prompt)
# Parse output for delegations
# Send agent prompts in same session
```

**Benefit**: Near-instant delegation (no subprocess overhead)

### 4. Batch Agent Execution 📦 (Easy Win)
```python
# Instead of separate prompts, batch into one:
combined_prompt = f"""
Execute these tasks in parallel:

1. [Engineer Role]
{engineer_task}

2. [QA Role]
{qa_task}

Return results for each role separately.
"""
```

**Benefit**: Single subprocess for all agents

### 5. Caching Common Patterns 💾 (Quick Win)
```python
# Cache common delegation patterns
CACHED_DELEGATIONS = {
    "write.*function": ("Engineer", "implement {details}"),
    "test.*": ("QA", "write tests for {details}"),
}
```

**Benefit**: Skip PM call for predictable patterns

## Recommended Implementation Order

1. **Quick Win**: Add session ID reuse (1-2 hour implementation)
   - 20-30% speed improvement
   - Minimal code changes

2. **Medium Effort**: Implement delegation caching
   - Skip PM for common patterns
   - 50%+ improvement for cached cases

3. **Major Refactor**: Interactive mode multiplexing
   - 80%+ speed improvement
   - Requires significant architecture changes

## Timing Comparison

| Approach | PM Time | Agent Time | Total | Improvement |
|----------|---------|------------|-------|-------------|
| Current | 4s | 4s × N | 8s+ | Baseline |
| Session Reuse | 4s | 2s × N | 6s+ | 25% |
| Streaming | 4s | 4s (parallel) | 4-5s | 40% |
| Interactive | 0.5s | 0.5s × N | 1-2s | 75%+ |
| Cached | 0s | 4s × N | 4s | 50% |

## Trade-offs

### Current Approach
✅ Simple and robust
✅ Clean process isolation
✅ Easy to debug
❌ Slow for multiple delegations

### Optimized Approaches
✅ Much faster execution
✅ Better resource usage
❌ More complex error handling
❌ Harder to debug

## Conclusion

The `--print` mode is indeed slow, but the current implementation already uses parallel execution for agents. The main opportunities for improvement are:

1. Session ID reuse (easy, significant impact)
2. Caching common patterns (easy, high impact for repeated tasks)
3. Interactive mode refactor (complex, massive impact)

For most use cases, implementing session ID reuse and basic caching would provide a good balance of performance improvement vs. implementation complexity.