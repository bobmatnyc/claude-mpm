# Subprocess Orchestration Design

## Problem
Claude's `--print` mode times out when generating code or using tools, making subprocess orchestration in non-interactive mode impractical.

## Findings

### Interactive Mode (Working)
- Claude uses built-in Task tool
- Creates real subprocesses with ~11.4k tokens each
- Runs in parallel with independent timing
- Each subprocess gets framework context

### Non-Interactive Mode Issues
- `claude --print` works for simple queries (e.g., "What is 2+2?" in ~4s)
- Times out for any code generation or complex tasks
- Debug shows Claude is working but tool usage adds overhead
- Requires `--dangerously-skip-permissions` flag to run

## Alternative Approaches

### 1. Use Claude's Conversation API
Instead of `--print`, use conversation management:
```bash
# Start conversation
claude --model opus -c "conversation_id" < prompt.txt

# Continue conversation
claude --continue conversation_id < next_prompt.txt
```

### 2. Use Interactive Mode with Expect
Use expect/pexpect to control interactive Claude sessions programmatically.

### 3. Mock Subprocess Mode
For testing/development:
- Detect delegations in PM response
- Show subprocess-like output
- But don't actually create subprocesses

### 4. Direct API Integration
Skip CLI entirely and use Claude's API directly (if available).

## Implementation Status

### Completed
1. ✅ SubprocessOrchestrator class with full functionality
2. ✅ Delegation detection for multiple formats
3. ✅ Parallel subprocess execution framework
4. ✅ Agent-specific prompt generation
5. ✅ CLI integration via `--subprocess` flag
6. ✅ Fixed command flags for permissions

### Current Status
- Implementation is complete but blocked by Claude CLI limitations
- Use interactive mode for real subprocess orchestration
- Keep implementation for future when Claude print mode improves

## Delegation Detection Patterns

The PM uses these formats:
- `**Engineer Agent**: Create a function...`
- `**QA**: Write tests for...`
- `I'll delegate this to the Engineer agent...`

We can parse these and show subprocess-style output even without real subprocesses.