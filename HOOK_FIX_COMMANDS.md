# Quick Fix: Hook Installation Issues

## Problem
Hooks are failing because they're **not installed** in Claude Code settings.

## Root Cause
The UV exec fix was applied to source code, but hooks were never installed to `~/.claude/settings.json`.

## Fix (Run These Commands)

```bash
# 1. Install hooks
cd /Users/masa/Projects/claude-mpm
uv run claude-mpm configure hooks --enable

# 2. Verify installation
cat ~/.claude/settings.json | jq '.hooks'
# Should show hook configuration (not null)

# 3. Clear old error logs
rm /tmp/claude-mpm-hook-error.log
rm /tmp/claude-mpm-hook.log

# 4. Test hooks (in one terminal)
export CLAUDE_MPM_HOOK_DEBUG=true
uv run claude-mpm run

# 5. In another terminal, run a Claude Code command
claude "list files"

# 6. Check hook logs (should see processing messages)
tail -f /tmp/claude-mpm-hook.log
```

## Expected Results

**After installation**, `~/.claude/settings.json` should contain:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{ "type": "command", "command": "/path/to/claude-hook-handler.sh" }]
    }],
    "PostToolUse": [{ ... }],
    "PreToolUse": [{ ... }]
  }
}
```

**After testing**, `/tmp/claude-mpm-hook.log` should show:

```
[2025-12-19T...] Claude hook handler starting...
[2025-12-19T...] PYTHON_CMD: uv run python
[2025-12-19T...] Processing hook event: PostToolUse (PID: 12345)
```

## If Still Failing

1. Check hook script is executable:
   ```bash
   ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh
   ```

2. Test hook script manually:
   ```bash
   echo '{"hook_event_name": "test"}' | /Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh
   ```

3. Check UV can import dependencies:
   ```bash
   uv run python -c "import yaml; print('pyyaml works')"
   ```

## Detailed Investigation

See: `docs/research/hook-failure-uv-python-investigation-2025-12-19.md`
