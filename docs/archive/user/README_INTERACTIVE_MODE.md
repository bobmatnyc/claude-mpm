# Interactive Mode Fix - Using pexpect

## Problem
Claude's interactive CLI requires a proper terminal (TTY) environment. When using subprocess pipes, Claude doesn't get the terminal control it expects, causing it to exit immediately after showing the welcome screen.

## Solution
We've implemented a pexpect-based orchestrator that provides Claude with a pseudo-terminal (PTY), allowing proper interactive mode operation.

## Installation

### macOS with Homebrew Python
Due to PEP 668 restrictions, you need to either:

1. **Use pipx (Recommended)**:
   ```bash
   brew install pipx
   pipx install pexpect
   ```

2. **Use a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install pexpect
   ```

3. **Force install (Not recommended)**:
   ```bash
   pip install --break-system-packages --user pexpect
   ```

### Other Systems
```bash
pip install pexpect
```

## Usage

Once pexpect is installed, claude-mpm will automatically use the pexpect orchestrator for interactive mode:

```bash
# Interactive mode (uses pexpect)
claude-mpm

# Non-interactive mode (uses regular subprocess)
claude-mpm -i "Your prompt here"
```

## How It Works

1. **PexpectOrchestrator**: Creates a pseudo-terminal for Claude
2. **Terminal Control**: Claude gets the TTY environment it expects
3. **Framework Injection**: Still injects framework on first interaction
4. **Ticket Extraction**: Continues to extract tickets from responses
5. **Session Logging**: Maintains all logging capabilities

## Fallback Behavior

If pexpect is not installed, claude-mpm will:
1. Show a warning message
2. Fall back to the basic interactive mode
3. Suggest installing pexpect

## Benefits

- Proper interactive Claude experience
- No more "prompts not being submitted" issues
- Full terminal UI support
- Compatible with Claude's conversation management