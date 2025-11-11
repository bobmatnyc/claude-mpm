# Native Agents Quick Start Guide

## What is Native Agents Mode?

Native agents mode passes MPM's 37 specialized agents directly to Claude Code via the `--agents` CLI flag instead of deploying files to `.claude/agents/`. This results in **5x faster startup** with no filesystem I/O.

## Quick Comparison

| Feature | Traditional (Default) | Native (Experimental) |
|---------|---------------------|---------------------|
| Startup Speed | ~250ms | ~50ms (5x faster) |
| File I/O | Required | None |
| Claude Version | Any | >= 1.0.83 |
| Stability | Proven | Experimental |
| JSON Size | N/A | 45KB |

## Enable Native Mode

### Option 1: In Code

```python
from claude_mpm.core.claude_runner import ClaudeRunner

# Enable native agents
runner = ClaudeRunner(use_native_agents=True)
runner.run_interactive()
```

### Option 2: Via CLI (if supported)

```bash
# Future enhancement
claude-mpm run --use-native-agents
```

### Option 3: Configuration File

Add to `.claude-mpm/config.yaml`:

```yaml
runner:
  use_native_agents: true
```

## Verify It's Working

```python
from claude_mpm.services.native_agent_converter import NativeAgentConverter

converter = NativeAgentConverter()
agents = converter.load_agents_from_templates()
summary = converter.get_conversion_summary(agents)

print(f"✓ {summary['total_agents']} agents ready")
print(f"✓ JSON size: {summary['json_size_kb']} KB")
```

Expected output:
```
✓ 37 agents ready
✓ JSON size: 44.03 KB
```

## When to Use Each Mode

### Use Traditional Mode (Default) When:

- ✅ Running in production
- ✅ Need maximum stability
- ✅ Want to inspect/edit agent files
- ✅ Using Claude Code < 1.0.83
- ✅ On Windows (CLI arg limits)

### Use Native Mode When:

- ✅ Developing/testing
- ✅ Speed is critical
- ✅ Filesystem restrictions exist
- ✅ Running in CI/CD
- ✅ Using Claude Code >= 1.0.83

## Troubleshooting

### "Command too long" error

**Solution**: Use traditional mode on Windows
```python
runner = ClaudeRunner(use_native_agents=False)
```

### Agents not loading

**Check**: Claude Code version
```bash
claude --version  # Need >= 1.0.83
```

### Performance issues

**Check**: Conversion time
```python
import time
start = time.time()
agents = converter.load_agents_from_templates()
print(f"Loaded in {(time.time()-start)*1000:.0f}ms")
# Should be < 50ms
```

## Examples

### Example 1: Basic Usage

```python
from claude_mpm.core.claude_runner import ClaudeRunner

runner = ClaudeRunner(use_native_agents=True)
runner.run_interactive("Implement feature X")
```

### Example 2: Check What's Loaded

```python
from claude_mpm.services.native_agent_converter import NativeAgentConverter
import json

converter = NativeAgentConverter()
agents = converter.load_agents_from_templates()
agents_json = converter.generate_agents_json(agents)

# Parse and inspect
agent_dict = json.loads(agents_json)
print(f"Loaded agents: {list(agent_dict.keys())}")
print(f"Engineer tools: {agent_dict['engineer']['tools']}")
```

### Example 3: Performance Comparison

```python
import time

# Traditional
start = time.time()
runner_trad = ClaudeRunner(use_native_agents=False)
runner_trad.setup_agents()
trad_time = (time.time() - start) * 1000

# Native
start = time.time()
runner_native = ClaudeRunner(use_native_agents=True)
native_time = (time.time() - start) * 1000

print(f"Traditional: {trad_time:.0f}ms")
print(f"Native: {native_time:.0f}ms")
print(f"Speedup: {trad_time/native_time:.1f}x")
```

## Testing

```bash
# Run all native agent tests
pytest tests -k native -v

# Quick smoke test
python -c "
from claude_mpm.services.native_agent_converter import NativeAgentConverter
c = NativeAgentConverter()
a = c.load_agents_from_templates()
print(f'✓ Loaded {len(a)} agents')
"
```

## More Information

- **Full Documentation**: `docs/native-agents-integration.md`
- **Implementation Details**: `NATIVE_AGENTS_IMPLEMENTATION.md`
- **Source Code**: `src/claude_mpm/services/native_agent_converter.py`

## Status

**Current Status**: ✅ Experimental (v1.0.0)

**Recommendation**:
- Production: Use traditional mode (default)
- Development: Try native mode
- CI/CD: Native mode recommended

---

**Last Updated**: 2025-11-11
