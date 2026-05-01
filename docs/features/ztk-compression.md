# ZTK Shell Output Compression

## Overview

ZTK is a Zig-based binary that compresses shell command output before it reaches Claude, dramatically reducing token usage while maintaining full functionality. Claude MPM integrates ztk automatically via a `PreToolUse` hook that runs on every Bash tool call.

**Key Benefits:**
- **80–97% token reduction** on common dev commands (git, ls, grep, find, pytest)
- **Zero configuration** — enabled by default, works immediately
- **Transparent to users** — no changes to how you write commands
- **Graceful degradation** — if ztk isn't available, commands pass through unchanged
- **MIT licensed** — bundled binary from the open-source fork at [bobmatnyc/ztk](https://github.com/bobmatnyc/ztk)

**Overall Impact:**
- Across an 82-command session on the claude-mpm codebase, ztk achieved **82% token reduction**

| Command | Example | Token Reduction |
|---------|---------|-----------------|
| `find` | `find src/ -name '*.py'` | 98% |
| `grep -r` | `grep -r 'def '` | 95% |
| `ls` | `ls -la src/` | 82% |
| `git diff` | `git diff HEAD~10` | 64% |

---

## How It Works

### The Compression Process

1. **Command Interception** — Every Bash tool call is intercepted by the `PreToolUse` hook
2. **Command Rewriting** — If ztk is available, the command is rewritten to `ztk run <original-command>`
3. **Output Compression** — ztk executes the command and compresses output before returning to Claude
4. **Token Savings** — Claude receives the same information in 5–20% of the original tokens

### Example

```bash
# Original command
find src/ -type f -name "*.py" | head -100

# Rewritten by ztk hook
/path/to/ztk run find src/ -type f -name "*.py" | head -100

# Output is compressed before reaching Claude
# Same files listed, but with whitespace and redundancy removed
```

---

## Default Behavior

ZTK is **enabled by default** when available. No setup required for most users.

### Binary Resolution

The ztk binary is resolved in this order:

1. **System PATH** — If `ztk` is installed on your system (via `brew install ztk` or similar), that takes precedence
2. **Bundled in Wheel** — If no system ztk is found, the bundled binary shipped with claude-mpm is used

For **PyPI/Homebrew/Pipx installs**, the binary is automatically bundled — no additional installation needed.

### Verification

To verify ztk is working:

```bash
# Check system ztk (if installed)
which ztk

# Enable debug output to see ztk in action
export CLAUDE_MPM_ZTK_DEBUG=1
# Now run any Bash command in Claude Code and check stderr logs
```

With `CLAUDE_MPM_ZTK_DEBUG=1`, you'll see messages like:
```
[ztk-hook] using bundled ztk: /path/to/claude_mpm/bin/ztk
[ztk-hook] rewrote Bash command: find src/ -name '*.py' -> /path/to/ztk run ...
```

---

## Disabling ZTK

There are three ways to disable ztk compression:

### Option 1: CLI Flag (Recommended)

Pass `--no-ztk` directly to `claude-mpm run` (or to the top-level command):

```bash
# Disable for one session
claude-mpm --no-ztk run

# Or on the run subcommand
claude-mpm run --no-ztk
```

To explicitly **enable** ztk (useful to override a pre-set `CLAUDE_MPM_DISABLE_ZTK=1` environment variable):

```bash
# Explicitly enable ztk even if CLAUDE_MPM_DISABLE_ZTK=1 is set in the environment
claude-mpm --ztk run

# Or on the run subcommand
claude-mpm run --ztk
```

`--ztk` and `--no-ztk` are mutually exclusive. When neither is passed, the environment variable is left unchanged.

You can also enable debug logging via the CLI:

```bash
# Show ztk rewriting details on stderr
claude-mpm --debug-ztk run
```

### Option 2: Environment Variable (Session-Level)

Set `CLAUDE_MPM_DISABLE_ZTK=1` to disable for the current session:

```bash
# Disable for one session
export CLAUDE_MPM_DISABLE_ZTK=1
claude-mpm your-command

# Or inline
CLAUDE_MPM_DISABLE_ZTK=1 claude code

# Re-enable
unset CLAUDE_MPM_DISABLE_ZTK
```

### Option 3: Configuration File (Persistent)

Add to your `~/.claude-mpm/config/configuration.yaml`:

```yaml
hooks:
  ztk:
    enabled: false
```

This disables ztk for all future sessions.

---

## What Gets Compressed

### Commands That ARE Wrapped

All standard Bash commands are eligible for compression:

```bash
# All of these are wrapped and compressed
find src/ -name "*.py"
grep -r "pattern" .
ls -la src/
git diff HEAD~10
pytest tests/
ps aux
npm list
cat large-file.log
df -h
```

### Commands That Are NOT Wrapped

These commands are excluded from compression:

**Inline scripts** (contain `-c` or `-e` flags):
```bash
# NOT wrapped (ztk blocks these)
python3 -c 'print("hello")'
bash -c 'echo "test"'
sh -e 'command'
perl -e 'print'
```

**Multi-line compound commands** (contain newlines):
```bash
# NOT wrapped
find . -name "*.py" | \
  xargs grep -l "TODO"

# Also NOT wrapped (semicolons with complex logic)
if [ -f file ]; then echo yes; fi
```

**Already-wrapped commands**:
```bash
# If you manually wrap in ztk run, it won't double-wrap
ztk run find src/ -name "*.py"
```

---

## Troubleshooting

### ZTK Binary Not Found

**Symptom:** Commands run without compression even with `CLAUDE_MPM_ZTK_DEBUG=1` enabled.

**Solution:**

1. Check if system ztk is installed:
   ```bash
   which ztk
   ```

2. Check if bundled binary exists:
   ```bash
   python3 -c "from importlib import resources; print(resources.files('claude_mpm').joinpath('bin', 'ztk'))"
   ```

3. If neither is available, install system ztk:
   ```bash
   # macOS
   brew install ztk

   # Or from source
   cargo install --git https://github.com/bobmatnyc/ztk
   ```

4. Reinstall claude-mpm to get bundled binary:
   ```bash
   uv tool reinstall claude-mpm --python 3.13
   ```

### Debug Output Shows `pass-through` for Every Command

**Symptom:** `[ztk-hook] ztk not found (system or bundled); pass-through` appears repeatedly.

**Cause:** ztk binary cannot be resolved.

**Solution:** Follow the "ZTK Binary Not Found" section above.

### Command Fails After Wrapping

**Symptom:** A command works without `CLAUDE_MPM_ZTK_DEBUG=1` but fails when ztk tries to wrap it.

**Workaround:**

1. Add the command to the exclusion list by modifying your environment:
   ```bash
   CLAUDE_MPM_DISABLE_ZTK=1 <rerun your command>
   ```

2. Or disable ztk for the session and file an issue at [bobmatnyc/ztk](https://github.com/bobmatnyc/ztk)

3. Contact support with the command that failed and debug output

### Excessive Output Still Received

**Symptom:** Commands are being wrapped (`CLAUDE_MPM_ZTK_DEBUG=1` shows rewriting), but output is not compressed.

**Possible Causes:**

1. **Output redirected** — Piping to `> file` disables compression
   ```bash
   # Compressed
   find . -name "*.py"

   # NOT compressed (redirected to file)
   find . -name "*.py" > results.txt
   ```

2. **Command is in exclusion list** — Check debug output to see if the command was rewritten

3. **ZTK version mismatch** — Ensure you have the latest version:
   ```bash
   brew upgrade ztk
   ```

---

## How It's Distributed

### Bundled Binary

The ztk binary is shipped with claude-mpm in the Python wheel:

```
claude-mpm/
└── bin/
    └── ztk          # Binary bundled in the wheel
```

**License:** MIT (from [bobmatnyc/ztk](https://github.com/bobmatnyc/ztk) fork)

**Distribution Methods:**
- **PyPI** — Bundled in the wheel
- **Homebrew** — Bundled in the formula
- **Pipx** — Bundled in the installed package

### Building from Source

To use ztk from source instead of the bundled binary:

```bash
# Install from source (takes precedence over bundled)
cargo install --git https://github.com/bobmatnyc/ztk

# Verify it's on PATH
which ztk
```

---

## Performance Characteristics

### Compression Overhead

ztk adds minimal latency to each Bash invocation:

- **Typical overhead:** < 50ms per command
- **No impact on fast commands** — Compression savings exceed overhead for most commands
- **Most beneficial for:** Large output (git diffs, grep results, ls listings)

### Example: Token Savings vs. Overhead

```
Command: git diff HEAD~10
---
Original output: 45,000 tokens
Compressed output: 18,000 tokens
Tokens saved: 27,000 (60% reduction)
Execution overhead: ~20ms

Result: Substantial net savings
```

---

## Advanced Configuration

### Custom ZTK Path

To use a custom ztk binary:

```bash
# Add to ~/.bashrc or shell profile
export PATH="/path/to/custom/ztk:$PATH"

# The hook will find it via system PATH resolution
```

### Logging and Debugging

Enable detailed debug output:

```bash
# In your shell or via environment
export CLAUDE_MPM_ZTK_DEBUG=1

# Now run any Claude Code session and check stderr logs
# Each Bash command will show ztk rewriting
```

### Monitoring Compression Effectiveness

To measure token savings in your own sessions:

1. Run with `CLAUDE_MPM_ZTK_DEBUG=1` to see which commands are being compressed
2. Look at the Claude Code token count before/after commands
3. Commands showing `rewrote Bash command` should show significantly lower token usage

---

## FAQ

### Q: Will ztk break any of my commands?

**A:** Extremely unlikely. Commands that ztk cannot safely wrap are automatically excluded (inline scripts, multi-line commands). If a command breaks after ztk wrapping, it's a bug in ztk — please report it.

### Q: Can I use ztk with other compression tools?

**A:** Yes. ztk only compresses output; other tools that compress your commands (e.g., alias compression, shell history compression) will work alongside it.

### Q: Does ztk require network access?

**A:** No. ztk is a standalone binary that runs locally. All compression happens on your machine.

### Q: Can I customize compression settings?

**A:** Not currently. ztk provides sensible defaults optimized for development command output. If you need different compression behavior, please open an issue at [bobmatnyc/ztk](https://github.com/bobmatnyc/ztk).

### Q: What about privacy? Does ztk send data anywhere?

**A:** No. ztk is open-source and runs entirely locally. All command output remains on your machine.

### Q: Can ztk compress output from Python, Node, or other interpreters?

**A:** Only for Bash commands. Inline scripts (`python3 -c`, `node -e`) are explicitly excluded for safety. If you want to compress output from an interpreter, run it as a command:

```bash
# Wrapped (output compressed)
python3 script.py

# NOT wrapped (inline script)
python3 -c 'print("hello")'
```

---

## Related Documentation

- [PreToolUse Hooks System](../developer/hooks.md) — How hooks integrate into claude-mpm
- [Performance Optimization](../guides/performance.md) — Other ways to reduce token usage
- [ZTK Repository](https://github.com/bobmatnyc/ztk) — Upstream source and issues

---

[Back to Features](./README.md) | [Back to Documentation](../README.md)
