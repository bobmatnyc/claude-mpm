# /helloworld Hook Implementation

## Overview

This document describes the implementation of a UserPromptSubmit hook that intercepts the `/helloworld` command and returns "Hello World" without sending the prompt to the LLM.

## Key Design Decision

To avoid conflicts with existing hooks and ensure reliable interception, the `/helloworld` slash command expands to a unique trigger string `HELLOWORLD_HOOK_TRIGGER` instead of directly to "Hello World". This allows our hook to uniquely identify and intercept this specific command.

## Implementation Details

### Hook File: `.claude/hooks/helloworld_hook.js`

The hook is implemented as a Node.js script that:
1. Reads the event data from stdin
2. Checks if the prompt is `/helloworld`
3. If matched, returns a block action with "Hello World" as the alternative response
4. If not matched, returns a continue action to allow normal processing

### Hook Configuration

The hook is registered in two configuration files:

1. **`.claude/hooks.json`** - Claude MPM specific configuration
   ```json
   {
     "name": "helloworld-command",
     "enabled": true,
     "priority": 90,
     "conditions": {
       "promptPatterns": ["/helloworld"]
     },
     "handler": "/Users/masa/Projects/claude-mpm/.claude/hooks/helloworld_hook.js"
   }
   ```

2. **`.claude/settings.json`** - Claude Code configuration
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "node /Users/masa/Projects/claude-mpm/.claude/hooks/helloworld_hook.js"
             }
           ]
         }
       ]
     }
   }
   ```

## How It Works

1. When a user types `/helloworld` in Claude Code
2. The UserPromptSubmit event is triggered
3. Claude Code executes the configured hooks
4. The helloworld_hook.js receives the event data via stdin
5. The hook checks if the prompt matches `/helloworld`
6. If matched, it returns:
   ```json
   {
     "action": "block",
     "reason": "Handled by helloworld hook",
     "alternative": "Hello World",
     "suppressOutput": false
   }
   ```
7. Claude Code displays "Hello World" to the user without sending to the LLM

## Testing

Two test scripts are provided:

1. **`scripts/test_helloworld_hook.js`** - Tests the /helloworld command interception
2. **`scripts/test_helloworld_passthrough.js`** - Tests that other prompts pass through

Run tests with:
```bash
node scripts/test_helloworld_hook.js
node scripts/test_helloworld_passthrough.js
```

## Key Features

- **No LLM Processing**: The command is handled entirely by the hook
- **Fast Response**: Direct response without API calls
- **Passthrough**: Non-matching prompts continue to normal processing
- **Logging**: Debug logs written to `/tmp/helloworld-hook.log`

## Usage

In Claude Code, simply type:
```
/helloworld
```

The response will be:
```
Hello World
```

This response comes directly from the hook without any LLM processing.