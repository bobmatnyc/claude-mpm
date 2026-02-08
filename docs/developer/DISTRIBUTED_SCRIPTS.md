# Distributed Scripts

Scripts that are included in the PyPI package and available to users after installation.

## User-Facing Setup Scripts

### Slack App Setup

**Location (after installation):** `claude_mpm/scripts/setup/setup-slack-app.sh`

**Purpose:** Interactive setup wizard for configuring Slack MPM integration

**Usage:**

One-line command:
```bash
python3 -c "import claude_mpm, os, subprocess; subprocess.run(['bash', os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh')])"
```

Or step-by-step:
```bash
# Find the script location
python3 -c "import claude_mpm, os; print(os.path.join(os.path.dirname(claude_mpm.__file__), 'scripts/setup/setup-slack-app.sh'))"

# Run the setup (use path from above)
bash /path/to/setup-slack-app.sh
```

See [docs/slack-setup.md](/docs/slack-setup.md) for detailed instructions.

**What it does:**
- Guides through Slack app configuration
- Sets up OAuth credentials
- Configures workspace integration
- Tests connection

## Hook Scripts (Already Distributed)

These scripts are referenced in Claude Code settings and are automatically distributed:

- `claude-hook-fast.sh` - Fast hook execution
- `claude-hook-handler.sh` - Main hook handler

**Location:** `claude_mpm/scripts/`

## Adding New Distributable Scripts

To add a new script that should be distributed with the package:

1. **Add to source:**
   ```bash
   cp your-script.sh src/claude_mpm/scripts/setup/
   chmod +x src/claude_mpm/scripts/setup/your-script.sh
   ```

2. **Update pyproject.toml** (if needed):
   ```toml
   [tool.setuptools.package-data]
   claude_mpm = [
       # ... existing entries ...
       "scripts/setup/*",  # Already includes all setup scripts
       "scripts/setup/*.sh",
   ]
   ```

3. **Rebuild and test:**
   ```bash
   python3 -m build --wheel
   unzip -l dist/claude_mpm-*.whl | grep your-script
   ```

## Development-Only Scripts (NOT Distributed)

The following scripts remain in the top-level `scripts/` directory and are NOT included in the package:

- `publish_to_pypi.sh` - Release automation
- `publish_to_npm.sh` - NPM publishing
- `deploy_local.sh` - Local deployment
- `install_dev.sh` - Development setup
- `setup-git-hooks.sh` - Git hooks setup
- `verify_publish_setup.sh` - Pre-release checks
- All test and CI scripts

These are for maintainers and contributors only.

## Script Organization

```
scripts/                          # Development scripts (NOT distributed)
├── setup-slack-app.sh           # Source (keep in sync)
├── publish_to_pypi.sh
└── ...

src/claude_mpm/scripts/          # Distributed scripts
├── __init__.py
├── claude-hook-fast.sh          # Hook scripts
├── claude-hook-handler.sh
├── mpm_doctor.py                # Python entry points
├── launch_monitor.py
└── setup/                       # User-facing setup scripts
    └── setup-slack-app.sh       # Distributed copy
```

## Keeping Scripts in Sync

The setup-slack-app.sh exists in two places:
1. **Source:** `scripts/setup-slack-app.sh` (for development)
2. **Distributed:** `src/claude_mpm/scripts/setup/setup-slack-app.sh` (for users)

When updating:
```bash
# Update both locations
vim scripts/setup-slack-app.sh
cp scripts/setup-slack-app.sh src/claude_mpm/scripts/setup/
```

## Verification

After releasing a new version, verify distributed scripts:

```bash
# Download from PyPI
pip download --no-deps claude-mpm==X.Y.Z

# Check contents
unzip -l claude_mpm-X.Y.Z-py3-none-any.whl | grep scripts/setup
```

---

**Last Updated:** 2026-02-08
**Package Version:** 5.7.9
