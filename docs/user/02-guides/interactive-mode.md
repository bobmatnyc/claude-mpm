# Interactive Mode Guide

Master Claude MPM's interactive mode for natural conversations with enhanced project management features.

## Overview

Interactive mode provides a conversational interface to Claude with:
- Framework instructions automatically injected
- Real-time monitoring for tickets and delegations
- Session logging and history
- Natural Claude CLI experience

## Starting Interactive Mode

### Basic Launch

```bash
# Start interactive session
claude-mpm

# You'll see:
Welcome to Claude MPM Interactive Mode
Framework loaded. Starting Claude...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Then Claude's normal interface appears
```

### Launch Options

```bash
# With specific model
claude-mpm --model opus

# With debug logging
claude-mpm --debug

# Disable ticket creation
claude-mpm --no-tickets
```

## Interactive Mode Features

### 1. Automatic Framework Loading

Claude MPM injects framework instructions on the first interaction, teaching Claude about:
- Ticket patterns (TODO, TASK, BUG, FEATURE)
- Agent delegation
- Project management best practices

### 2. Ticket Detection

As you chat, Claude MPM monitors for ticket patterns:

```
You: I need to TODO: Add user authentication and TODO: Setup email service
Claude: I'll help you with both tasks...
[Claude MPM: Created tickets TSK-0001 and TSK-0002]
```

### 3. Session Logging

Every conversation is logged:
- Location: `~/.claude-mpm/sessions/`
- Format: `session_YYYYMMDD_HHMMSS.log`
- Includes: All inputs, outputs, timestamps

### 4. Context Preservation

Claude maintains context throughout the session, understanding:
- Previous requests
- Created tickets
- Project context
- Your preferences

## Effective Conversations

### Starting Strong

Begin with context:

```
You: I'm working on a Python web API using FastAPI. I need help 
     architecting the authentication system.

Claude: I'll help you design a robust authentication system for 
        your FastAPI application. Let me break this down...
```

### Creating Tickets

Use trigger words naturally:

```
You: TODO: Implement JWT token generation
     TODO: Add refresh token mechanism
     TODO: Create user session management

Claude: I'll help you implement these authentication components...
[Created: TSK-0001, TSK-0002, TSK-0003]
```

### Requesting Delegation

Ask for specialized help:

```
You: Can you research the best practices for storing refresh tokens?

Claude: I'll delegate this to our Research Agent for a thorough analysis...
[Delegation detected: Research Agent activated]
```

## Navigation and Commands

### Claude's Built-in Commands

Interactive mode supports all Claude CLI commands:

- `/help` - Show available commands
- `/clear` - Clear the screen
- `/save` - Save conversation
- `/model` - Switch models
- `/exit` - Exit Claude

### Conversation Management

```
# Save your work
You: /save auth-discussion

# Clear screen but keep context  
You: /clear

# Switch models mid-conversation
You: /model sonnet
```

## Common Workflows

### 1. Project Planning Session

```
claude-mpm

You: I need to build a task management application. Let's plan the 
     architecture and create tickets for the main components.

Claude: I'll help you architect a task management application. Let me
        break this down into components and create actionable tickets...

You: TODO: Design database schema for tasks and users
     TODO: Create REST API endpoints  
     TODO: Build React frontend
     TODO: Implement real-time updates

[Creates tickets automatically]
```

### 2. Debugging Session

```
claude-mpm

You: I'm getting a KeyError in my Python code. Here's the traceback:
     [paste error]

Claude: I can see the issue. The KeyError suggests...

You: Here's the relevant code:
     [paste code]

Claude: The problem is on line 23. You're trying to access...
```

### 3. Learning Session

```
claude-mpm

You: Explain how Python decorators work with practical examples

Claude: I'll explain Python decorators step by step...

You: Can you show me how to create a decorator for timing functions?

Claude: Here's a practical timing decorator...
```

### 4. Code Review Session

```
claude-mpm

You: Review this authentication module for security issues:
     [paste code]

Claude: I'll perform a security review of your authentication module.
        Here are my findings...

You: BUG: Password stored in plain text
     BUG: No rate limiting on login attempts
     TODO: Add input validation

[Creates bug tickets and tasks]
```

## Advanced Interactive Features

### Multi-turn Workflows

Build complex solutions iteratively:

```
You: Create a basic user model

Claude: Here's a basic User model...

You: Now add authentication methods

Claude: I'll extend the User model with authentication...

You: TODO: Add password reset functionality

Claude: I'll implement password reset...
[Creates: TSK-0004]
```

### Context-Aware Responses

Claude remembers your entire conversation:

```
You: Earlier you mentioned using bcrypt for passwords

Claude: Yes, I recommended bcrypt for password hashing. Building on
        that recommendation, here's how to implement it...
```

### Natural Delegation

Delegations happen automatically:

```
You: Research the best database for our chat application

Claude: I'll have our Research Agent investigate database options
        for real-time chat applications...
[Research Agent activated]
```

## Interactive Mode with pexpect

### Enhanced Terminal Support

If you have pexpect installed, Claude MPM provides better terminal handling:

```bash
# Install pexpect for better interactive support
pip install pexpect

# Now interactive mode has:
# - Better terminal emulation
# - Improved prompt handling  
# - More reliable I/O
```

### Troubleshooting pexpect

If interactive mode exits immediately:

```bash
# Check pexpect installation
python -c "import pexpect; print('pexpect available')"

# Reinstall if needed
pip install --upgrade pexpect
```

## Tips for Productive Sessions

### 1. Set Context Early

```
You: I'm working on [project type] using [technologies]. 
     My main goal is [objective].
```

### 2. Use Clear Ticket Patterns

```
You: TODO: Implement feature X with requirements Y and Z
```

### 3. Break Down Complex Tasks

```
You: Let's break down the authentication system into subtasks
Claude: I'll help you decompose this into manageable pieces...
```

### 4. Save Important Conversations

```
You: /save authentication-design
# Saves to Claude's conversation history
```

### 5. Review Session Logs

```bash
# After your session
cat ~/.claude-mpm/sessions/session_*.log | grep "TODO:"
```

## Common Issues and Solutions

### Issue: Prompts Not Submitting

**Symptom**: Type prompt, press Enter, nothing happens

**Solution**:
```bash
# Install pexpect
pip install pexpect

# Or use non-interactive mode for single commands
claude-mpm run -i "Your prompt" --non-interactive
```

### Issue: Framework Not Loading

**Symptom**: Claude doesn't understand tickets or agents

**Solution**:
```bash
# Check framework path
claude-mpm info

# Manually verify framework
cat $(claude-mpm info | grep "Framework path" | cut -d: -f2)
```

### Issue: Tickets Not Created

**Symptom**: Using TODO but no tickets appear

**Solution**:
- Ensure correct pattern: `TODO:` (with colon)
- Check ticket creation isn't disabled: Don't use `--no-tickets`
- Verify ticket directory exists: `ls tickets/tasks/`

### Issue: Session Not Logged

**Symptom**: No session files created

**Solution**:
```bash
# Check session directory
ls -la ~/.claude-mpm/sessions/

# Create if missing
mkdir -p ~/.claude-mpm/sessions/

# Check permissions
chmod 755 ~/.claude-mpm/sessions/
```

## Best Practices

### 1. Start with a Plan

Begin sessions with clear objectives:
```
You: Today I want to:
     1. Design the API structure
     2. Create tickets for implementation
     3. Plan the testing strategy
```

### 2. Use Ticket Patterns Naturally

Integrate ticket creation into conversation:
```
You: As we discussed, I'll TODO: Implement the user service first,
     then TODO: Add authentication middleware
```

### 3. Leverage Claude's Memory

Reference earlier points:
```
You: Based on the architecture we designed above, what's the best
     way to handle database connections?
```

### 4. End with a Summary

Before exiting:
```
You: Can you summarize what we accomplished and list all the 
     tickets we created?
```

## Interactive Mode vs Non-Interactive

### When to Use Interactive Mode

- Exploratory discussions
- Multi-step problem solving  
- Learning and research
- Iterative development
- Code reviews with discussion

### When to Use Non-Interactive

- Single specific tasks
- Automation and scripts
- CI/CD pipelines
- Batch processing
- Quick questions

## Integration with Workflow

### Morning Planning

```bash
#!/bin/bash
# morning-planning.sh
echo "Starting morning planning session..."
claude-mpm
# Have planning conversation
# Review created tickets after
./ticket list --limit 10
```

### End of Day Review

```bash
# Review today's sessions
find ~/.claude-mpm/sessions -name "session_$(date +%Y%m%d)*.log" \
  -exec echo "=== {} ===" \; -exec tail -20 {} \;
```

## Next Steps

- Explore [Automatic Tickets](../03-features/automatic-tickets.md) in detail
- Learn about [Agent Delegation](../03-features/agent-delegation.md)
- Master [Session Logging](../03-features/session-logging.md)
- See [Troubleshooting](../04-reference/troubleshooting.md) for more solutions