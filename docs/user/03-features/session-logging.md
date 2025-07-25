# Session Logging

Claude MPM provides comprehensive session logging to track all interactions, making it easy to review conversations, debug issues, and maintain project history.

## What Gets Logged

### Complete Interaction History

Every session captures:

1. **Timestamps** - When each interaction occurred
2. **User Inputs** - All prompts and commands
3. **Claude Responses** - Complete outputs
4. **System Events** - Framework loading, ticket creation
5. **Metadata** - Model used, session duration, settings

### Session Structure

```
=== Session Start: 2024-01-25 14:30:22 ===
Model: claude-3-opus
Mode: interactive
Framework: Loaded

[14:30:25] User: TODO: Implement user authentication
[14:30:27] System: Created ticket TSK-0001
[14:30:28] Claude: I'll help you implement user authentication...
[14:30:45] User: What about password hashing?
[14:30:47] Claude: For password hashing, I recommend...

=== Session End: 2024-01-25 14:45:12 ===
Duration: 14 minutes 50 seconds
Tickets Created: 1
Total Exchanges: 5
```

## Log Locations

### Directory Structure

```
~/.claude-mpm/
├── sessions/
│   ├── session_20240125_143022.log
│   ├── session_20240125_160515.log
│   └── ...
├── logs/
│   ├── debug_20240125.log
│   ├── orchestration.log
│   └── ...
└── config/
```

### Session File Naming

Format: `session_YYYYMMDD_HHMMSS.log`

- `YYYY` - Year (2024)
- `MM` - Month (01-12)
- `DD` - Day (01-31)
- `HH` - Hour (00-23)
- `MM` - Minute (00-59)
- `SS` - Second (00-59)

## Accessing Logs

### Recent Sessions

```bash
# List recent sessions
ls -lt ~/.claude-mpm/sessions/ | head -10

# View latest session
cat ~/.claude-mpm/sessions/session_*.log | tail -100

# Open in editor
vim ~/.claude-mpm/sessions/session_20240125_143022.log
```

### Searching Logs

```bash
# Find sessions mentioning specific topic
grep -r "authentication" ~/.claude-mpm/sessions/

# Find all TODO items created
grep -r "TODO:" ~/.claude-mpm/sessions/

# Find sessions from specific date
ls ~/.claude-mpm/sessions/session_20240125*.log

# Search with context
grep -C 3 "error" ~/.claude-mpm/sessions/*.log
```

### Log Analysis

```bash
# Count tickets created today
grep -h "Created ticket" ~/.claude-mpm/sessions/session_$(date +%Y%m%d)*.log | wc -l

# Find longest sessions
for f in ~/.claude-mpm/sessions/*.log; do
    echo "$(grep -c "User:" "$f") exchanges: $f"
done | sort -rn | head -5

# Extract all created tickets
grep -h "Created ticket TSK-" ~/.claude-mpm/sessions/*.log | sort -u
```

## Log Content Details

### User Interactions

```
[14:30:25] User: TODO: Implement user authentication with JWT
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           Full prompt captured with timestamp
```

### Claude Responses

```
[14:30:28] Claude: I'll help you implement JWT authentication.
                   Here's a comprehensive solution:

                   ```python
                   import jwt
                   from datetime import datetime, timedelta
                   
                   class JWTAuth:
                       def __init__(self, secret_key):
                           self.secret_key = secret_key
                   ```
                   
                   [Complete response logged]
```

### System Events

```
[14:30:22] System: Session started
[14:30:23] System: Framework loaded from /path/to/framework
[14:30:27] System: Created ticket TSK-0001: Implement user authentication
[14:30:27] System: Delegation detected: Engineer Agent
[14:45:12] System: Session ended (duration: 14m 50s)
```

### Metadata Section

```
=== Session Metadata ===
Start Time: 2024-01-25 14:30:22
End Time: 2024-01-25 14:45:12
Duration: 890 seconds
Model: claude-3-opus
Mode: interactive
Tickets Created: 3 (TSK-0001, TSK-0002, TSK-0003)
Delegations: 2 (Engineer, QA)
Total Tokens: ~4,500
```

## Privacy and Security

### What's Logged

- ✅ User prompts
- ✅ Claude responses
- ✅ Timestamps
- ✅ System events
- ❌ System passwords
- ❌ Environment secrets
- ❌ API keys

### Sensitive Information

**Best Practices**:

1. **Don't include secrets in prompts**:
   ```
   # Bad
   "My API key is sk-abc123..."
   
   # Good
   "I have an API key stored in environment variable"
   ```

2. **Sanitize logs if sharing**:
   ```bash
   # Remove potential secrets
   sed 's/password=.*/password=REDACTED/g' session.log
   ```

3. **Secure log directory**:
   ```bash
   chmod 700 ~/.claude-mpm/sessions/
   ```

## Log Rotation and Management

### Automatic Cleanup

Claude MPM can automatically manage old logs:

```bash
# Delete logs older than 30 days
find ~/.claude-mpm/sessions -name "*.log" -mtime +30 -delete

# Archive old logs
tar -czf sessions_202401.tar.gz ~/.claude-mpm/sessions/session_202401*.log
```

### Manual Cleanup

```bash
# Remove all session logs
rm -rf ~/.claude-mpm/sessions/*.log

# Keep only last 100 sessions
ls -t ~/.claude-mpm/sessions/*.log | tail -n +101 | xargs rm

# Remove large sessions (>10MB)
find ~/.claude-mpm/sessions -name "*.log" -size +10M -delete
```

## Using Logs Effectively

### 1. Project Documentation

Extract project decisions:

```bash
# Create project summary from logs
echo "# Project Decisions" > decisions.md
grep -h "DECISION:" ~/.claude-mpm/sessions/*.log >> decisions.md
```

### 2. Learning from Past Sessions

```bash
# Find successful solutions
grep -B5 -A5 "works perfectly" ~/.claude-mpm/sessions/*.log

# Extract code examples
grep -A20 "```python" ~/.claude-mpm/sessions/*.log > code_examples.py
```

### 3. Debugging Issues

```bash
# Find error occurrences
grep -C10 "error\|Error\|ERROR" ~/.claude-mpm/sessions/*.log

# Track issue resolution
grep -B20 "fixed\|resolved\|solved" ~/.claude-mpm/sessions/*.log
```

### 4. Team Collaboration

Share relevant sessions:

```bash
# Extract specific session
cp ~/.claude-mpm/sessions/session_20240125_143022.log ./auth_discussion.log

# Create summary
echo "# Authentication Implementation Discussion" > summary.md
echo "Date: 2024-01-25" >> summary.md
echo "Participants: Developer, Claude MPM" >> summary.md
grep "TODO\|DECISION\|AGREED" auth_discussion.log >> summary.md
```

## Advanced Log Analysis

### Session Statistics

```bash
#!/bin/bash
# session_stats.sh

SESSIONS_DIR="$HOME/.claude-mpm/sessions"

echo "=== Claude MPM Session Statistics ==="
echo "Total Sessions: $(ls $SESSIONS_DIR/*.log 2>/dev/null | wc -l)"
echo "Total Size: $(du -sh $SESSIONS_DIR | cut -f1)"
echo ""
echo "Sessions by Date:"
for date in $(ls $SESSIONS_DIR/session_*.log | cut -d_ -f2 | sort -u); do
    count=$(ls $SESSIONS_DIR/session_${date}_*.log | wc -l)
    echo "  $date: $count sessions"
done
```

### Ticket Tracking

```bash
#!/bin/bash
# track_tickets.sh

echo "=== Tickets Created via Claude MPM ==="
grep -h "Created ticket" ~/.claude-mpm/sessions/*.log | \
    sed 's/.*Created ticket //' | \
    sort -u | \
    while read ticket; do
        echo "$ticket"
        grep -h "$ticket" ~/.claude-mpm/sessions/*.log | \
            grep -v "Created ticket" | \
            head -3 | \
            sed 's/^/  /'
    done
```

### Model Usage Analysis

```bash
# Count sessions by model
echo "Model Usage:"
grep "Model:" ~/.claude-mpm/sessions/*.log | \
    cut -d: -f3 | \
    sort | uniq -c | sort -rn
```

## Integration with Other Tools

### Git Integration

```bash
# Add session reference to commits
git commit -m "Implement auth (see session_20240125_143022.log)"

# Include session summary in PR
echo "## Claude MPM Sessions" >> pr_description.md
echo "- [Auth Design](session_20240125_143022.log)" >> pr_description.md
```

### Export to Markdown

```bash
#!/bin/bash
# export_session.sh

session_file=$1
output_file="${session_file%.log}.md"

echo "# Claude MPM Session Export" > "$output_file"
echo "Date: $(basename $session_file | cut -d_ -f2)" >> "$output_file"
echo "" >> "$output_file"

# Convert log to markdown
sed 's/^\[.*\] User: /\n**You**: /' "$session_file" | \
sed 's/^\[.*\] Claude: /\n**Claude**: /' | \
sed 's/^\[.*\] System: /\n*System: /' >> "$output_file"
```

## Troubleshooting

### Logs Not Created

**Check permissions**:
```bash
ls -la ~/.claude-mpm/
chmod 755 ~/.claude-mpm/sessions/
```

**Verify directory exists**:
```bash
mkdir -p ~/.claude-mpm/sessions/
```

### Large Log Files

**Check sizes**:
```bash
du -h ~/.claude-mpm/sessions/*.log | sort -h | tail -10
```

**Compress old logs**:
```bash
gzip ~/.claude-mpm/sessions/session_2024012*.log
```

### Missing Session Data

**Check current session**:
```bash
# Find active session
ps aux | grep claude-mpm

# Monitor in real-time
tail -f ~/.claude-mpm/sessions/session_*.log
```

## Best Practices

### 1. Regular Review

- Review daily sessions for insights
- Extract important decisions
- Document key solutions

### 2. Organization

```bash
# Create project-specific directories
mkdir -p ~/projects/myapp/claude-sessions/
cp ~/.claude-mpm/sessions/session_*auth*.log ~/projects/myapp/claude-sessions/
```

### 3. Backup Important Sessions

```bash
# Backup critical sessions
tar -czf claude-sessions-backup-$(date +%Y%m).tar.gz ~/.claude-mpm/sessions/
```

### 4. Clean Sensitive Data

```bash
# Remove sensitive sessions
rm ~/.claude-mpm/sessions/session_*sensitive*.log

# Scrub sensitive data
sed -i 's/api_key=.*/api_key=REDACTED/g' session.log
```

## Next Steps

- Learn about [Memory Protection](memory-protection.md) for long sessions
- Explore [Automatic Tickets](automatic-tickets.md) tracking in logs
- See [Configuration](../04-reference/configuration.md) for logging options
- Check [Troubleshooting](../04-reference/troubleshooting.md) for common issues