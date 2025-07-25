# First Run Tutorial

Welcome! This tutorial will walk you through your first experience with Claude MPM.

## Before You Begin

Make sure you've completed the [installation](installation.md) and have:
- Claude MPM installed
- Virtual environment activated
- Claude CLI working

## Your First Command

Let's start with a simple non-interactive command:

```bash
claude-mpm run -i "Hello Claude! Please introduce yourself." --non-interactive
```

You should see:
1. Claude MPM starting up
2. Framework instructions being loaded
3. Claude's response
4. Session information

## Understanding the Output

Claude MPM provides rich output with several sections:

```
=== Claude MPM Starting ===
Loading framework from: /path/to/framework
Launching Claude with subprocess orchestration...

=== Claude Response ===
Hello! I'm Claude, an AI assistant created by Anthropic...

=== Session Complete ===
Duration: 2.3 seconds
Model: claude-3-opus
Tickets created: 0
Session logged to: ~/.claude-mpm/sessions/session_20240125_093045.log
```

## Interactive Mode

Now let's try interactive mode:

```bash
claude-mpm
```

This launches Claude in an enhanced interactive session where you can:
- Have natural conversations
- Claude MPM monitors for tickets and delegations
- Everything is logged automatically

Try these prompts:
```
You: TODO: Create a Python function to calculate fibonacci numbers
You: Can you help me debug this code? [paste some code]
You: I need to implement user authentication for my web app
```

## Automatic Ticket Creation

Claude MPM automatically detects and creates tickets. Try this:

```bash
claude-mpm run -i "TODO: Implement a REST API for user management with authentication" --non-interactive
```

Check the created ticket:
```bash
# List recent tickets
claude-mpm tickets

# Or use the ticket command directly
./ticket list
```

## Agent Delegation

Claude MPM automatically delegates to specialized agents. Try:

```bash
claude-mpm run -i "Research the best practices for Python API development" --non-interactive
```

Watch as Claude MPM:
1. Detects this is a research task
2. Delegates to the Research Agent
3. Provides specialized results

## Session Logs

All your interactions are logged:

```bash
# View your session directory
ls ~/.claude-mpm/sessions/

# View the latest session
cat ~/.claude-mpm/sessions/session_*.log | tail -50
```

## Configuration Check

Verify your setup:

```bash
claude-mpm info
```

This shows:
- Claude MPM version
- Python version
- Claude CLI location
- Framework path
- Ticket directory

## Common First-Run Issues

### "Claude not found"

Ensure Claude CLI is in your PATH:
```bash
which claude
# If not found, add to PATH
export PATH="/path/to/claude:$PATH"
```

### No Tickets Created

Tickets are created from specific patterns:
- "TODO: ..."
- "TASK: ..."
- "BUG: ..."
- "FEATURE: ..."

### Interactive Mode Exits Immediately

Install pexpect for proper interactive mode:
```bash
pip install pexpect
```

### Framework Not Loading

Check the framework path:
```bash
claude-mpm info
# Look for "Framework path"
```

## Practice Exercises

Try these exercises to get familiar with Claude MPM:

### Exercise 1: Create a Ticket
```bash
claude-mpm run -i "TODO: Write unit tests for the authentication module" --non-interactive
./ticket list
```

### Exercise 2: Multi-Agent Task
```bash
claude-mpm run -i "Create a Python web server with tests and documentation" --non-interactive
```

### Exercise 3: Debug Code
```bash
claude-mpm run -i "Debug this Python code: def fib(n): return fib(n-1) + fib(n-2)" --non-interactive
```

### Exercise 4: Interactive Exploration
```bash
claude-mpm
# Then try:
# - Ask about best practices
# - Request code reviews
# - Plan a project
```

## Understanding the Workflow

1. **You provide a prompt** → Claude MPM intercepts it
2. **Framework instructions are injected** → Claude gets context
3. **Claude responds** → Output is monitored
4. **Patterns are detected** → Tickets created, agents invoked
5. **Everything is logged** → Full session history

## Tips for Effective Use

1. **Be specific in your requests** - Clear prompts get better results
2. **Use TODO patterns** - Automatically creates trackable tickets
3. **Leverage agents** - Let Claude MPM delegate to specialists
4. **Review logs** - Understand what happened in your session
5. **Use non-interactive for scripts** - Great for automation

## Next Steps

Now that you've completed your first run:

1. Learn about [Core Concepts](concepts.md)
2. Explore [Basic Usage](../02-guides/basic-usage.md) patterns
3. Master [Ticket Management](../02-guides/ticket-management.md)
4. Understand [Subprocess Orchestration](../02-guides/subprocess-orchestration.md)

## Quick Reference Card

```bash
# Interactive mode
claude-mpm

# Non-interactive command
claude-mpm run -i "prompt" --non-interactive

# List tickets
claude-mpm tickets
./ticket list

# View session info
claude-mpm info

# Debug mode
claude-mpm --debug

# Help
claude-mpm --help
```

Congratulations! You've successfully run Claude MPM. Continue exploring the documentation to unlock its full potential.