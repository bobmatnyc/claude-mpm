# Basic Usage Guide

This guide covers the fundamental commands and patterns for using Claude MPM effectively.

## Command Structure

Claude MPM follows a simple command structure:

```bash
claude-mpm [command] [options]
```

Main commands:
- `run` - Execute a prompt
- `tickets` - List tickets
- `info` - Show configuration
- (no command) - Start interactive mode

## Running Commands

### Non-Interactive Mode

Perfect for single tasks, scripts, and automation:

```bash
# Basic usage
claude-mpm run -i "Explain Python decorators" --non-interactive

# Short form
claude-mpm run -i "What is REST API?" --non-interactive

# With specific model
claude-mpm run -i "Write a sorting algorithm" --model sonnet --non-interactive
```

### Interactive Mode

For conversations and exploratory work:

```bash
# Start interactive session
claude-mpm

# With debug logging
claude-mpm --debug

# With specific model
claude-mpm --model opus
```

## Working with Models

Claude MPM supports all Claude models:

```bash
# Use Opus (most capable, default)
claude-mpm run -i "Complex analysis task" --model opus

# Use Sonnet (balanced)
claude-mpm run -i "General coding task" --model sonnet  

# Use Haiku (fastest)
claude-mpm run -i "Simple question" --model haiku
```

## Essential Flags

### Output Control

```bash
# Suppress ticket creation
claude-mpm run -i "Quick question" --no-tickets

# Enable debug output
claude-mpm run -i "Debug this" --debug

# Quiet mode (minimal output)
claude-mpm run -i "Task" --quiet
```

### Process Control

```bash
# Use subprocess orchestration
claude-mpm run --subprocess -i "Complex task"

# Set timeout (in seconds)
claude-mpm run -i "Long task" --timeout 300

# Disable parallel execution
claude-mpm run --subprocess --no-parallel -i "Sequential tasks"
```

## Common Patterns

### 1. Quick Questions

For simple queries without ticket creation:

```bash
claude-mpm run -i "What's the syntax for Python list comprehension?" --no-tickets --non-interactive
```

### 2. Task Creation

Automatically create trackable tickets:

```bash
# Creates a ticket
claude-mpm run -i "TODO: Implement user registration endpoint" --non-interactive

# Multiple tasks
claude-mpm run -i "TODO: Add input validation, TODO: Write unit tests" --non-interactive
```

### 3. Code Review

Get code analysis and suggestions:

```bash
claude-mpm run -i "Review this code for security issues: $(cat app.py)" --non-interactive
```

### 4. Documentation Generation

```bash
claude-mpm run -i "Generate API documentation for this module: $(cat api.py)" --non-interactive
```

### 5. Debugging Sessions

```bash
# Start interactive debugging
claude-mpm
# Then: "I'm getting a KeyError in this code: [paste code]"
# Continue the conversation to debug
```

## Working with Files

### Input from Files

```bash
# Using cat
claude-mpm run -i "Explain this code: $(cat script.py)" --non-interactive

# Using file path in prompt
claude-mpm run -i "Review the code in /path/to/file.py" --non-interactive
```

### Output to Files

```bash
# Redirect output
claude-mpm run -i "Generate a README" --non-interactive > README.md

# Append to file
claude-mpm run -i "Add installation section" --non-interactive >> README.md
```

## Ticket Patterns

Claude MPM automatically detects these patterns:

| Pattern | Example | Creates |
|---------|---------|---------|
| TODO: | "TODO: Add error handling" | Task ticket |
| TASK: | "TASK: Refactor database layer" | Task ticket |
| BUG: | "BUG: Login fails on Chrome" | Bug ticket |
| FEATURE: | "FEATURE: Add dark mode" | Feature ticket |

## Session Management

### View Sessions

```bash
# List recent sessions
ls -la ~/.claude-mpm/sessions/

# View specific session
cat ~/.claude-mpm/sessions/session_20240125_*.log
```

### Search Sessions

```bash
# Find sessions mentioning specific terms
grep -r "authentication" ~/.claude-mpm/sessions/

# Find sessions from today
find ~/.claude-mpm/sessions -name "session_$(date +%Y%m%d)*.log"
```

## Productivity Tips

### 1. Use Aliases

Add to your shell config:

```bash
# Quick claude-mpm access
alias cm='claude-mpm'
alias cmr='claude-mpm run'
alias cmt='claude-mpm tickets'

# Common patterns
alias todo='claude-mpm run -i "TODO: $1" --non-interactive'
alias ask='claude-mpm run -i "$1" --no-tickets --non-interactive'
```

### 2. Shell Functions

```bash
# Review function
review() {
    claude-mpm run -i "Review this code: $(cat $1)" --non-interactive
}

# Document function
document() {
    claude-mpm run -i "Document this code: $(cat $1)" --non-interactive
}
```

### 3. Combine with Unix Tools

```bash
# Process multiple files
find . -name "*.py" -exec claude-mpm run -i "Add docstrings to {}" \;

# Pipe input
echo "def complex_function(): pass" | claude-mpm run -i "Explain this: $(cat)" 

# Use with git
git diff | claude-mpm run -i "Review these changes: $(cat)"
```

## Error Handling

### Common Issues

**"Claude not found"**:
```bash
# Check Claude installation
which claude

# Add to PATH if needed
export PATH="$PATH:/path/to/claude"
```

**"Framework not loaded"**:
```bash
# Check configuration
claude-mpm info

# Manually specify framework
claude-mpm --framework-path /path/to/framework
```

**Session errors**:
```bash
# Clear session cache
rm -rf ~/.claude-mpm/sessions/tmp/*

# Reset configuration
rm -rf ~/.claude-mpm/config/*
```

## Best Practices

### 1. Be Specific

```bash
# Good: Specific request
claude-mpm run -i "Create a Python function to validate email addresses using regex"

# Less effective: Vague request  
claude-mpm run -i "Make email checker"
```

### 2. Use Context

```bash
# Provide context
claude-mpm run -i "In a Django app, create a custom user model with email as username"

# Include constraints
claude-mpm run -i "Write a sorting algorithm in O(n log n) time complexity"
```

### 3. Batch Related Tasks

```bash
# Single command with multiple tasks
claude-mpm run -i "TODO: Create User model, TODO: Add authentication, TODO: Write tests"
```

### 4. Review and Iterate

```bash
# Initial implementation
claude-mpm run -i "Create a basic web server"

# Iterate with improvements
claude-mpm run -i "Add error handling to the web server code above"

# Final polish
claude-mpm run -i "Add comprehensive logging and tests"
```

## Advanced Usage

### Chaining Commands

```bash
# Create, test, and document
claude-mpm run -i "Create a fibonacci function" --non-interactive && \
claude-mpm run -i "Write tests for the fibonacci function" --non-interactive && \
claude-mpm run -i "Document the fibonacci function" --non-interactive
```

### Scripting

```bash
#!/bin/bash
# claude-review.sh - Automated code review

for file in $(git diff --name-only); do
    echo "Reviewing $file..."
    claude-mpm run -i "Review changes in $file: $(git diff $file)" --non-interactive
done
```

## Next Steps

- Learn about [Ticket Management](ticket-management.md)
- Explore [Subprocess Orchestration](subprocess-orchestration.md) 
- Master [Interactive Mode](interactive-mode.md)
- Understand [Features](../03-features/README.md) in depth