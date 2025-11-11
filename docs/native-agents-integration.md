# Native Claude Code --agents Flag Integration

## Overview

Claude Code 1.0.83+ supports a native `--agents` CLI flag for defining subagents dynamically. MPM now offers **two deployment methods** for its 37 specialized agents:

1. **Traditional**: Deploy agent markdown files to `.claude/agents/` (default)
2. **Native**: Pass agents via `--agents` CLI flag (experimental)

## Quick Start

### Using Native Agents Mode

```python
from claude_mpm.core.claude_runner import ClaudeRunner

# Enable native agents mode
runner = ClaudeRunner(use_native_agents=True)
runner.run_interactive()
```

### CLI Usage

```bash
# Traditional mode (default)
claude-mpm run

# Native mode (experimental)
claude-mpm run --use-native-agents
```

## How It Works

### Architecture

```
MPM Agent JSON → NativeAgentConverter → Claude --agents Flag
    (37 agents)        (conversion)         (45KB JSON)
```

### Conversion Process

1. **Load**: Read MPM agent templates from `src/claude_mpm/agents/templates/*.json`
2. **Convert**: Transform MPM schema → Claude native schema
3. **Generate**: Create compact JSON for CLI (optimized to 45KB)
4. **Execute**: Pass to Claude via `--agents '<json>'`

### Field Mapping

| MPM Field | Claude Field | Purpose |
|-----------|-------------|---------|
| `description` | `description` | Agent selection hint for Claude |
| `instructions` + `knowledge.base_instructions_file` | `prompt` | Agent behavior/instructions |
| `capabilities.tools` | `tools` | Tool restrictions |
| `capabilities.model` | `model` | Model tier (opus/sonnet/haiku) |

## Native Agent Converter

### Basic Usage

```python
from claude_mpm.services.native_agent_converter import NativeAgentConverter

converter = NativeAgentConverter()

# Load all MPM agents
agents = converter.load_agents_from_templates()

# Convert to native format
native_agent = converter.convert_mpm_agent_to_native(agents[0])

# Generate complete --agents JSON
agents_json = converter.generate_agents_json(agents)

# Build CLI flag
agents_flag = converter.build_agents_flag(agents)
# Returns: --agents '{"engineer": {...}, "qa": {...}, ...}'
```

### Conversion Summary

```python
summary = converter.get_conversion_summary(agents)
print(f"Total agents: {summary['total_agents']}")
print(f"JSON size: {summary['json_size_kb']} KB")
print(f"Model distribution: {summary['model_distribution']}")
```

Example output:
```
Total agents: 37
JSON size: 44.03 KB
Model distribution: {'opus': 0, 'sonnet': 37, 'haiku': 0}
```

## Configuration

### ClaudeRunner Parameters

```python
ClaudeRunner(
    enable_tickets=True,           # Enable ticket extraction (deprecated)
    log_level="OFF",               # Logging level
    claude_args=None,              # Additional Claude CLI args
    launch_method="exec",          # "exec" or "subprocess"
    enable_websocket=False,        # Enable WebSocket server
    websocket_port=8765,          # WebSocket port
    use_native_agents=False,      # Use --agents flag (NEW)
)
```

### Configuration File

Add to `.claude-mpm/config.yaml`:

```yaml
runner:
  use_native_agents: false  # Set to true to enable native mode
  launch_method: exec
  enable_websocket: false
```

## Traditional vs Native Mode

### Traditional Mode (Default)

**How it works:**
- Deploys agent `.md` files to `.claude/agents/`
- Claude discovers agents from filesystem
- Agents persist between sessions

**Pros:**
- Proven, stable approach
- Easy to debug (files visible on disk)
- Supports manual agent editing
- Works with all Claude Code versions

**Cons:**
- Requires file I/O (slower startup)
- File permission issues possible
- Agent updates need redeployment

**Use when:**
- Stability is critical
- You need to inspect/edit agents
- Running on systems with filesystem restrictions

### Native Mode (Experimental)

**How it works:**
- Converts agents to JSON at runtime
- Passes JSON via `--agents` CLI flag
- No filesystem interaction

**Pros:**
- Faster startup (no file I/O)
- No permission issues
- Cleaner (no `.claude/agents/` directory)
- Dynamic agent configuration
- Up to 10 concurrent agents (Claude limit)

**Cons:**
- Requires Claude Code >= 1.0.83
- CLI argument length limits (~100KB)
- Harder to debug (agents in memory)
- Experimental feature

**Use when:**
- Speed is priority
- Filesystem access is restricted
- Testing/development scenarios
- Using Claude Code 1.0.83+

## Performance Comparison

### Metrics

| Metric | Traditional | Native |
|--------|------------|--------|
| Agent Deployment Time | ~200-300ms | ~50ms |
| Startup Overhead | File I/O + parsing | JSON generation only |
| Memory Usage | Files on disk | JSON in memory |
| Claude Loading Time | Filesystem read | CLI argument parse |

### Benchmark Results

```python
# Traditional deployment
Time: 250ms (37 agents)
Operations: 37 file writes + metadata updates

# Native conversion
Time: 50ms (37 agents)
Operations: JSON generation only
```

**Result**: Native mode is **5x faster** for agent deployment.

## Technical Details

### JSON Size Optimization

**Original approach** (naive conversion):
- Included full domain expertise lists
- Included full best practices lists
- Result: **448KB** JSON (too large!)

**Optimized approach**:
- Reference BASE_*.md files only
- Limit instruction length to 300 chars
- Skip redundant knowledge sections
- Result: **45KB** JSON (90% reduction!)

### CLI Argument Limits

Different systems have different limits:

| OS | Limit | Status |
|----|-------|--------|
| macOS | ~260KB | ✅ Safe |
| Linux | ~2MB | ✅ Safe |
| Windows | ~32KB | ⚠️ Tight (may fail with all 37 agents) |

MPM's 45KB fits comfortably on macOS/Linux, but may exceed Windows limits.

### Agent Exclusions

The following agents are **never** included in `--agents` flag:

- `pm` (Project Manager) - This is the main Claude instance
- `project_manager` - Alias for PM

## Examples

### Example 1: Convert Single Agent

```python
from claude_mpm.services.native_agent_converter import NativeAgentConverter
import json

converter = NativeAgentConverter()

# MPM agent config
mpm_agent = {
    "agent_id": "engineer",
    "description": "Engineering specialist",
    "instructions": "Follow BASE_ENGINEER.md",
    "capabilities": {
        "model": "sonnet",
        "tools": ["Read", "Write", "Edit", "Bash"]
    },
    "knowledge": {
        "base_instructions_file": "BASE_ENGINEER.md"
    }
}

# Convert to native format
native_agent = converter.convert_mpm_agent_to_native(mpm_agent)

print(json.dumps(native_agent, indent=2))
```

Output:
```json
{
  "description": "Engineering specialist",
  "prompt": "Follow BASE_ENGINEER.md for all protocols.\nFollow BASE_ENGINEER.md",
  "tools": ["Read", "Write", "Edit", "Bash"],
  "model": "sonnet"
}
```

### Example 2: Generate Full CLI Command

```python
from claude_mpm.services.native_agent_converter import NativeAgentConverter

converter = NativeAgentConverter()
agents = converter.load_agents_from_templates()

# Build complete flag
agents_flag = converter.build_agents_flag(agents, escape_for_shell=True)

# Construct full command
cmd = f"claude --dangerously-skip-permissions {agents_flag}"

print(f"Command length: {len(cmd)} characters")
print(f"Command: {cmd[:200]}...")  # First 200 chars
```

### Example 3: Compare Both Modes

```python
import time
from claude_mpm.core.claude_runner import ClaudeRunner

# Measure traditional deployment
start = time.time()
runner_traditional = ClaudeRunner(use_native_agents=False)
runner_traditional.setup_agents()
traditional_time = time.time() - start

# Measure native conversion
start = time.time()
runner_native = ClaudeRunner(use_native_agents=True)
# Native mode doesn't call setup_agents() - conversion happens in command building
native_time = time.time() - start

print(f"Traditional: {traditional_time*1000:.0f}ms")
print(f"Native: {native_time*1000:.0f}ms")
print(f"Speedup: {traditional_time/native_time:.1f}x")
```

## Troubleshooting

### Issue: "Command too long" error

**Cause**: `--agents` JSON exceeds shell argument limit

**Solution**:
```python
# Check JSON size before running
from claude_mpm.services.native_agent_converter import NativeAgentConverter

converter = NativeAgentConverter()
agents = converter.load_agents_from_templates()
size = converter.estimate_json_size(agents)

if size > 50000:  # 50KB threshold
    print("Warning: JSON may be too large for Windows")
    print("Consider using traditional deployment mode")
```

### Issue: Agents not loading in Claude

**Cause**: Claude Code version < 1.0.83 doesn't support `--agents`

**Solution**:
```bash
# Check Claude version
claude --version

# Upgrade if needed
# Then verify support in code
```

### Issue: Missing agents in native mode

**Cause**: PM agent is excluded (it's the main instance)

**Expected**: PM is not a subagent, it's the orchestrator

### Issue: JSON parsing errors

**Cause**: Special characters not properly escaped

**Solution**: Use `build_agents_flag()` which handles escaping:
```python
# Don't manually build JSON
agents_json = json.dumps(agents)  # ❌ May break with quotes

# Use the converter
agents_flag = converter.build_agents_flag(agents)  # ✅ Handles escaping
```

## Testing

### Run Test Suite

```bash
# Unit tests
pytest tests/services/test_native_agent_converter.py -v

# Integration tests
pytest tests/integration/test_native_agents_integration.py -v

# All native agent tests
pytest tests -k native -v
```

### Manual Testing

```python
# Test conversion manually
from claude_mpm.services.native_agent_converter import NativeAgentConverter

converter = NativeAgentConverter()
agents = converter.load_agents_from_templates()

# Verify all agents converted
summary = converter.get_conversion_summary(agents)
assert summary["total_agents"] == 37
assert summary["json_size"] < 100000  # Under 100KB

print("✅ All agents converted successfully")
print(f"   Total: {summary['total_agents']} agents")
print(f"   Size: {summary['json_size_kb']} KB")
```

## API Reference

### NativeAgentConverter

#### Methods

**`convert_mpm_agent_to_native(agent_config: Dict, agent_id: Optional[str] = None) -> Dict`**

Convert single MPM agent to Claude native format.

**`generate_agents_json(agents: List[Dict]) -> str`**

Generate complete --agents JSON string.

**`build_agents_flag(agents: List[Dict], escape_for_shell: bool = True) -> str`**

Build complete --agents flag for CLI.

**`load_agents_from_templates(templates_dir: Optional[Path] = None) -> List[Dict]`**

Load all agent configs from templates directory.

**`estimate_json_size(agents: List[Dict]) -> int`**

Estimate size of --agents JSON output (bytes).

**`get_conversion_summary(agents: List[Dict]) -> Dict`**

Get summary with counts, size, model distribution, tool usage.

#### Constants

**`MODEL_TIER_MAP`**: Maps MPM model tiers to Claude models
```python
{
    "opus": "opus",
    "sonnet": "sonnet",
    "haiku": "haiku",
    "claude-3-opus": "opus",
    "claude-3-sonnet": "sonnet",
    "claude-3-haiku": "haiku",
}
```

**`TOOL_NAME_MAP`**: Maps MPM tools to Claude tools
```python
{
    "Read": "Read",
    "Write": "Write",
    "Edit": "Edit",
    # ... etc
}
```

## Future Enhancements

### Planned Features

1. **Selective Agent Loading**
   ```python
   # Load only specific agents
   runner = ClaudeRunner(
       use_native_agents=True,
       agents_filter=["engineer", "qa", "documentation"]
   )
   ```

2. **Dynamic Agent Updates**
   ```python
   # Update agents at runtime
   runner.update_native_agents(new_agents)
   ```

3. **Agent Caching**
   ```python
   # Cache converted agents to disk
   converter.cache_converted_agents()
   ```

4. **Compression**
   ```python
   # Compress JSON for even smaller size
   converter.generate_agents_json(agents, compress=True)
   ```

## Conclusion

Native `--agents` flag integration provides a faster, cleaner alternative to file-based agent deployment. While experimental, it offers significant performance improvements for systems with filesystem restrictions or high-speed requirements.

**Recommendation**:
- **Production**: Use traditional mode (default)
- **Development**: Try native mode for faster iteration
- **Testing**: Native mode for CI/CD pipelines

Both modes will continue to be supported, allowing users to choose based on their needs.

---

**Version**: 1.0.0
**Date**: 2025-11-11
**Status**: Experimental
