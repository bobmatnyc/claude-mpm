# Troubleshooting Guide

This guide helps you resolve common issues with Claude MPM.

## Installation Issues

### Claude Not Found

**Symptom**: `claude: command not found` or `FileNotFoundError`

**Solutions**:

1. **Verify Claude CLI is installed**:
   ```bash
   which claude
   # If not found, install Claude CLI first
   ```

2. **Add Claude to PATH**:
   ```bash
   # Find Claude location
   find / -name claude 2>/dev/null
   
   # Add to PATH in ~/.bashrc or ~/.zshrc
   export PATH="/path/to/claude:$PATH"
   
   # Reload shell
   source ~/.bashrc
   ```

3. **Set CLAUDE_PATH environment variable**:
   ```bash
   export CLAUDE_PATH="/usr/local/bin/claude"
   ```

### Python Dependencies

**Symptom**: `ModuleNotFoundError` or import errors

**Solutions**:

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Reinstall dependencies**:
   ```bash
   pip install -e .
   # Or
   pip install -r requirements.txt
   ```

3. **Check Python version**:
   ```bash
   python --version  # Should be 3.8+
   ```

### Permission Denied

**Symptom**: `Permission denied` errors

**Solutions**:

1. **Make scripts executable**:
   ```bash
   chmod +x claude-mpm
   chmod +x ticket
   chmod +x scripts/*
   ```

2. **Fix directory permissions**:
   ```bash
   chmod -R 755 ~/.claude-mpm
   ```

## Runtime Issues

### Interactive Mode Exits Immediately

**Symptom**: Claude starts but exits right away

**Solutions**:

1. **Install pexpect**:
   ```bash
   pip install pexpect
   ```

2. **Check terminal type**:
   ```bash
   echo $TERM
   # Should be a valid terminal type
   export TERM=xterm-256color
   ```

3. **Use non-interactive mode**:
   ```bash
   claude-mpm run -i "Your prompt" --non-interactive
   ```

### Framework Not Loading

**Symptom**: Claude doesn't understand tickets or agents

**Solutions**:

1. **Check framework path**:
   ```bash
   claude-mpm info | grep "Framework path"
   ```

2. **Verify framework exists**:
   ```bash
   ls -la $(claude-mpm info | grep "Framework path" | cut -d: -f2)
   ```

3. **Manually specify framework**:
   ```bash
   claude-mpm --framework-path /path/to/framework
   ```

### Tickets Not Created

**Symptom**: Using TODO patterns but no tickets appear

**Solutions**:

1. **Check pattern format**:
   ```
   ✓ TODO: Description (correct)
   ✗ TODO Description (missing colon)
   ✗ todo: Description (lowercase)
   ```

2. **Verify tickets not disabled**:
   ```bash
   # Don't use --no-tickets
   # Check environment
   echo $CLAUDE_MPM_NO_TICKETS  # Should be empty or false
   ```

3. **Check ticket directory**:
   ```bash
   ls -la tickets/tasks/
   # Create if missing
   mkdir -p tickets/tasks
   ```

4. **Verify ai-trackdown-pytools**:
   ```bash
   pip show ai-trackdown-pytools
   # Reinstall if needed
   pip install ai-trackdown-pytools
   ```

## Subprocess Issues

### Subprocess Mode Not Working

**Symptom**: `--subprocess` flag doesn't work

**Solutions**:

1. **Install required packages**:
   ```bash
   pip install pexpect psutil
   ```

2. **Check Python modules**:
   ```bash
   python -c "import pexpect, psutil; print('OK')"
   ```

3. **Use debug mode**:
   ```bash
   claude-mpm run --subprocess --logging DEBUG -i "Task"
   ```

### Memory Limit Exceeded

**Symptom**: Process terminated due to memory

**Solutions**:

1. **Increase memory limit**:
   ```bash
   claude-mpm run --subprocess --memory-limit 4096 -i "Task"
   ```

2. **Disable memory monitoring**:
   ```bash
   claude-mpm run --subprocess --no-memory-monitoring -i "Task"
   ```

3. **Use sequential execution**:
   ```bash
   claude-mpm run --subprocess --no-parallel -i "Task"
   ```

### Timeout Errors

**Symptom**: Commands timing out

**Solutions**:

1. **Increase timeout**:
   ```bash
   claude-mpm run --timeout 600 -i "Long task"
   ```

2. **Set environment variable**:
   ```bash
   export CLAUDE_MPM_TIMEOUT=900
   ```

3. **Disable timeout**:
   ```bash
   claude-mpm run --timeout 0 -i "Task"  # No timeout
   ```

## Session and Logging Issues

### Session Logs Not Created

**Symptom**: No logs in ~/.claude-mpm/sessions/

**Solutions**:

1. **Check directory exists**:
   ```bash
   mkdir -p ~/.claude-mpm/sessions
   chmod 755 ~/.claude-mpm/sessions
   ```

2. **Verify write permissions**:
   ```bash
   touch ~/.claude-mpm/sessions/test.log
   rm ~/.claude-mpm/sessions/test.log
   ```

3. **Check disk space**:
   ```bash
   df -h ~/
   ```

### Large Log Files

**Symptom**: Session logs consuming too much space

**Solutions**:

1. **Clean old logs**:
   ```bash
   # Remove logs older than 30 days
   find ~/.claude-mpm/sessions -name "*.log" -mtime +30 -delete
   ```

2. **Compress logs**:
   ```bash
   # Compress logs older than 7 days
   find ~/.claude-mpm/sessions -name "*.log" -mtime +7 -exec gzip {} \;
   ```

3. **Set up rotation**:
   ```bash
   # Add to crontab
   0 0 * * * find ~/.claude-mpm/sessions -name "*.log" -mtime +30 -delete
   ```

## Performance Issues

### Slow Startup

**Symptom**: Claude MPM takes long to start

**Solutions**:

1. **Check framework size**:
   ```bash
   du -sh ~/.claude-mpm/framework
   # If too large, optimize framework
   ```

2. **Clear cache**:
   ```bash
   rm -rf ~/.claude-mpm/cache/*
   ```

3. **Use faster model**:
   ```bash
   claude-mpm --model haiku
   ```

### High Memory Usage

**Symptom**: System becomes slow during use

**Solutions**:

1. **Monitor processes**:
   ```bash
   ps aux | grep claude
   htop  # or top
   ```

2. **Limit parallel processes**:
   ```bash
   claude-mpm run --subprocess --max-parallel 2 -i "Task"
   ```

3. **Use memory limits**:
   ```bash
   claude-mpm run --subprocess --memory-limit 1024 -i "Task"
   ```

## Configuration Issues

### Config Not Loading

**Symptom**: Settings not applied

**Solutions**:

1. **Check config syntax**:
   ```bash
   # Validate YAML
   python -c "import yaml; yaml.safe_load(open('.claude-mpm.yml'))"
   ```

2. **Verify config location**:
   ```bash
   claude-mpm config sources
   ```

3. **Check precedence**:
   ```bash
   claude-mpm config show --effective
   ```

### Environment Variables Not Working

**Symptom**: CLAUDE_MPM_* variables ignored

**Solutions**:

1. **Export variables**:
   ```bash
   # Wrong
   CLAUDE_MPM_MODEL=sonnet
   
   # Correct
   export CLAUDE_MPM_MODEL=sonnet
   ```

2. **Check in new shell**:
   ```bash
   # Variables might not persist
   echo $CLAUDE_MPM_MODEL
   ```

3. **Add to shell config**:
   ```bash
   echo 'export CLAUDE_MPM_MODEL=sonnet' >> ~/.bashrc
   source ~/.bashrc
   ```

## Common Error Messages

### "Context length exceeded"

**Cause**: Conversation too long

**Solution**:
```bash
# Start fresh session
claude-mpm

# Or use subprocess for isolation
claude-mpm run --subprocess -i "Task"
```

### "No module named 'claude_mpm'"

**Cause**: Package not installed properly

**Solution**:
```bash
# In project directory
pip install -e .

# Verify
python -c "import claude_mpm; print('OK')"
```

### "Broken pipe"

**Cause**: Claude process terminated unexpectedly

**Solution**:
```bash
# Use non-interactive mode
claude-mpm run -i "Task" --non-interactive

# Or increase timeout
claude-mpm run --timeout 600 -i "Task"
```

## FAQ

### Q: Why does interactive mode not accept my input?

**A**: Install pexpect for proper terminal emulation:
```bash
pip install pexpect
```

### Q: Can I use Claude MPM without Claude CLI?

**A**: No, Claude CLI must be installed. Claude MPM is an orchestration layer that requires Claude.

### Q: Why are my tickets not syncing with my team?

**A**: Claude MPM creates local tickets. For team sync:
- Use a shared git repository
- Commit ticket files
- Consider integration with issue trackers

### Q: How do I reset everything?

**A**: Complete reset:
```bash
# Backup important data first!
rm -rf ~/.claude-mpm
rm -rf ./tickets
rm -f .claude-mpm.yml
# Reinstall
pip install -e .
```

### Q: Can I use multiple Claude accounts?

**A**: Yes, through Claude CLI profiles:
```bash
# Switch Claude profile first
claude auth switch-profile work
# Then use claude-mpm
claude-mpm
```

## Debug Checklist

When encountering issues, check:

1. ✓ Claude CLI installed and working
2. ✓ Virtual environment activated
3. ✓ All dependencies installed
4. ✓ Correct permissions on files/directories
5. ✓ Valid configuration syntax
6. ✓ Sufficient disk space
7. ✓ Compatible Python version (3.8+)
8. ✓ Terminal supports required features

## Getting More Help

### Enable Debug Mode

```bash
# Maximum debugging
claude-mpm --debug run --subprocess --logging DEBUG -i "Task" 2>&1 | tee debug.log
```

### Collect System Info

```bash
# Create diagnostic report
claude-mpm info --verbose > diagnostic.txt
pip list >> diagnostic.txt
echo "Python: $(python --version)" >> diagnostic.txt
echo "OS: $(uname -a)" >> diagnostic.txt
```

### Check Logs

```bash
# Recent errors
grep -i error ~/.claude-mpm/logs/*.log | tail -20

# Session issues
tail -100 ~/.claude-mpm/sessions/latest.log
```

### Community Support

- Check GitHub issues
- Review documentation
- Ask in discussions

## Next Steps

- Review [CLI Commands](cli-commands.md) for proper usage
- Check [Configuration](configuration.md) for settings
- See [Basic Usage](../02-guides/basic-usage.md) for examples
- Explore [Features](../03-features/README.md) for capabilities