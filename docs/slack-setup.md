# Running Slack App Setup

## Quick Start

After installing claude-mpm from PyPI, run the Slack setup script:

```bash
# One-line command to find and run the script
python3 -c "import claude_mpm, os, subprocess; subprocess.run(['bash', os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh')])"
```

## Step-by-Step Method

### 1. Find the Script Location

```bash
# Get the path to the setup script
python3 -c "import claude_mpm, os; print(os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh'))"
```

This will output something like:
```
/Users/username/.local/share/uv/tools/claude-mpm/lib/python3.12/site-packages/claude_mpm/scripts/setup/setup-slack-app.sh
```

### 2. Run the Script

```bash
# Copy the path from above and run it
bash /path/from/previous/command
```

## Convenience Alias (Optional)

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
# Alias for Slack setup
alias claude-mpm-setup-slack='python3 -c "import claude_mpm, os, subprocess; subprocess.run([\"bash\", os.path.join(os.path.dirname(claude_mpm.__file__), \"scripts/setup/setup-slack-app.sh\")])"'
```

Then simply run:
```bash
claude-mpm-setup-slack
```

## What the Script Does

The setup script will guide you through:

1. **Slack App Configuration**
   - Creating a new Slack app or using an existing one
   - Configuring OAuth scopes
   - Setting up event subscriptions

2. **Credential Storage**
   - Saving your Slack credentials securely
   - Setting up environment variables
   - Configuring workspace integration

3. **Connection Testing**
   - Verifying the Slack connection
   - Testing basic commands
   - Confirming workspace access

## Prerequisites

Before running the setup:

- [ ] Have access to create apps in your Slack workspace
- [ ] Have admin permissions (or get them from your workspace admin)
- [ ] Know your Slack workspace name/URL

## Troubleshooting

### Script Not Found

If you get "No such file or directory":

```bash
# Verify claude-mpm is installed
claude-mpm --version

# Check if the script exists
python3 -c "import claude_mpm, os; path = os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh'); print(f'Exists: {os.path.exists(path)}'); print(f'Path: {path}')"
```

If it says "Exists: False", you may have an older version:

```bash
# Upgrade to latest version (includes setup script)
uv tool upgrade claude-mpm
# or
pip install --upgrade claude-mpm
```

### Permission Denied

If you get "Permission denied":

```bash
# Make the script executable
python3 -c "import claude_mpm, os; script = os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh'); os.chmod(script, 0o755); print(f'Made executable: {script}')"
```

### Script Location in Development

If you're working from the source repository:

```bash
# Run directly from source
bash scripts/setup-slack-app.sh
```

## After Setup

Once setup is complete, you can:

- Start the Slack MPM client: `slack-mpm`
- Configure additional settings in `~/.claude-mpm/slack-config.yaml`
- Test the integration with `/mpm help` in Slack

## Version Requirements

The setup script is distributed starting from **v5.7.10**.

If you have an earlier version:
```bash
uv tool upgrade claude-mpm  # or pip install --upgrade claude-mpm
```

---

**Need Help?**
- Documentation: https://github.com/bobmatnyc/claude-mpm
- Issues: https://github.com/bobmatnyc/claude-mpm/issues
