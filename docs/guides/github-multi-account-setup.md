# GitHub Multi-Account Setup

This project uses a project-specific GitHub account configuration to support working with multiple GitHub accounts (bobmatnyc and bob-duetto).

## Current Configuration

- **Git User**: Bob Matsuoka (bob@matsuoka.com)
- **GitHub Account**: bobmatnyc
- **SSH Key**: ~/.ssh/id_ed25519
- **gh CLI Account**: bobmatnyc (managed via `claude-mpm gh switch`)

## How It Works

### 1. Git Operations (SSH)

Git uses SSH configuration in `~/.ssh/config`:

```ssh
# GitHub default (use bobmatnyc as default)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Project-specific git configuration (`.git/config`):
```gitconfig
[user]
    name = Bob Matsuoka
    email = bob@matsuoka.com
[github]
    user = bobmatnyc
```

### 2. gh CLI Operations

The `.gh-account` file specifies which GitHub account to use for gh CLI commands:

```
bobmatnyc
```

Use `claude-mpm gh switch` to switch gh CLI to the account specified in `.gh-account`.

## Setting Up a New Project

### For bobmatnyc Projects

1. **Clone or initialize repository**:
   ```bash
   git clone git@github.com:bobmatnyc/your-project.git
   cd your-project
   ```

2. **Configure git for bobmatnyc**:
   ```bash
   git config --local user.name "Bob Matsuoka"
   git config --local user.email "bob@matsuoka.com"
   git config --local github.user "bobmatnyc"
   ```

3. **Create .gh-account file**:
   ```bash
   echo "bobmatnyc" > .gh-account
   ```

4. **Switch gh CLI account** (if needed):
   ```bash
   gh auth switch --user bobmatnyc
   ```

### For bob-duetto Projects

1. **Clone or initialize repository**:
   ```bash
   git clone git@github-duetto:bob-duetto/your-project.git
   cd your-project
   ```

2. **Configure git for bob-duetto**:
   ```bash
   git config --local user.name "Bob Matsuoka"
   git config --local user.email "bob.matsuoka@duettoresearchgroup.com"  # Use work email
   git config --local github.user "bob-duetto"
   ```

3. **Update git remote to use SSH alias**:
   ```bash
   git remote set-url origin git@github-duetto:bob-duetto/your-project.git
   ```

4. **Create .gh-account file**:
   ```bash
   echo "bob-duetto" > .gh-account
   ```

5. **Switch gh CLI account** (if needed):
   ```bash
   gh auth switch --user bob-duetto
   ```

## SSH Configuration Details

Your `~/.ssh/config` contains:

```ssh
# GitHub - bob-duetto (Duetto org)
Host github-duetto
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_duetto
    IdentitiesOnly yes

# GitHub - bobmatnyc (Personal projects)
Host github-bobmatnyc
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

# GitHub default (use bobmatnyc as default)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

This means:
- `git@github.com:...` uses bobmatnyc account (default)
- `git@github-duetto:...` uses bob-duetto account
- `git@github-bobmatnyc:...` uses bobmatnyc account (explicit)

## Claude MPM GitHub Commands

Claude MPM provides integrated GitHub account management commands:

### Available Commands

```bash
# Switch to account specified in .gh-account
claude-mpm gh switch

# Verify complete setup (git + gh CLI + SSH)
claude-mpm gh verify

# Show current configuration
claude-mpm gh status

# Interactive project setup
claude-mpm gh setup
```

### Manual Usage

```bash
# Run from project root
claude-mpm gh switch
```

### Automatic Usage

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
# Auto-switch gh CLI account on directory change
chpwd_gh_switch() {
    if [[ -f .gh-account ]]; then
        claude-mpm gh switch 2>/dev/null
    fi
}

# zsh hook
autoload -U add-zsh-hook
add-zsh-hook chpwd chpwd_gh_switch

# bash hook (if using bash)
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND$'\n'}chpwd_gh_switch"
```

## Verification

### Verify Git Configuration

```bash
# Check git user
git config user.email
git config user.name
git config github.user

# Check git remote
git remote -v

# Test SSH connection
ssh -T git@github.com
```

### Verify gh CLI Configuration

```bash
# Check active account
gh auth status

# Test API call
gh api user --jq '.login'

# Expected output: bobmatnyc (or bob-duetto for work projects)
```

## Troubleshooting

### Git Operations Use Wrong Account

Check SSH configuration:
```bash
ssh -T git@github.com
# Should show: Hi bobmatnyc! You've successfully authenticated...
```

If wrong, update git remote:
```bash
git remote set-url origin git@github.com:bobmatnyc/your-project.git
```

### gh CLI Uses Wrong Account

Switch using claude-mpm:
```bash
claude-mpm gh switch
```

Or manually with gh CLI:
```bash
gh auth switch --user bobmatnyc
```

### SSH Permission Denied

Check SSH key is added to GitHub:
```bash
# Add SSH key to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Test connection
ssh -T git@github.com
```

If not added to GitHub:
1. Copy public key: `cat ~/.ssh/id_ed25519.pub`
2. Add to GitHub: Settings → SSH and GPG keys → New SSH key

### Multiple Projects Workspace Organization

Organize projects by account:

```
~/Projects/
  ├── personal/          # bobmatnyc projects
  │   ├── claude-mpm/
  │   └── other-project/
  └── work/              # bob-duetto projects
      ├── work-project-1/
      └── work-project-2/
```

Use global git config with conditional includes in `~/.gitconfig`:

```gitconfig
[includeIf "gitdir:~/Projects/personal/"]
    path = ~/.gitconfig-bobmatnyc
[includeIf "gitdir:~/Projects/work/"]
    path = ~/.gitconfig-bob-duetto
```

Create `~/.gitconfig-bobmatnyc`:
```gitconfig
[user]
    name = Bob Matsuoka
    email = bob@matsuoka.com
[github]
    user = bobmatnyc
```

Create `~/.gitconfig-bob-duetto`:
```gitconfig
[user]
    name = Bob Matsuoka
    email = bob.matsuoka@duettoresearchgroup.com
[github]
    user = bob-duetto
```

## Benefits of This Setup

✅ **Automatic**: No manual switching needed once configured
✅ **Project-specific**: Each project uses correct account automatically
✅ **Simple**: Uses standard git/SSH features, no complex tools
✅ **Documented**: `.gh-account` file documents which account to use
✅ **Portable**: Works across different machines with same SSH setup

## Summary

- **Git operations**: Use SSH keys (bobmatnyc by default, bob-duetto via github-duetto host alias)
- **gh CLI**: Use `.gh-account` file + `claude-mpm gh switch` to switch accounts
- **New projects**: Set local git config + create .gh-account file, or use `claude-mpm gh setup` for interactive configuration
- **Verification**: Run `claude-mpm gh verify` to confirm complete setup

For questions or issues, refer to this documentation or run `claude-mpm gh status` to check your configuration.
