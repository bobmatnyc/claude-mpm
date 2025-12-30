# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in claude-mpm, please report it privately:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to the maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a detailed response within 7 days.

## Security Best Practices

### Protecting API Keys and Credentials

**CRITICAL**: Never commit API keys, tokens, or credentials to version control.

#### High-Risk Files (NEVER Commit)

These files commonly contain secrets and should ALWAYS be in `.gitignore`:

```
.mcp-vector-search/config.json      # OpenRouter, OpenAI API keys
.mcp/config.json                     # MCP server credentials
openrouter.json
anthropic-config.json
openai-config.json
credentials.json
secrets.json
api-keys.json
.env
.env.local
.env.*.local
```

#### Verification Before Committing

Before committing changes, verify sensitive files are protected:

```bash
# Check if file is ignored by .gitignore
git check-ignore .mcp-vector-search/config.json
# Exit code 0 = ignored (safe)
# Exit code 1 = NOT ignored (DANGER - add to .gitignore!)

# Check if file is tracked by git
git ls-files .mcp-vector-search/config.json
# Output present = tracked (CRITICAL - remove immediately!)
# No output = not tracked (safe if also in .gitignore)
```

### Pre-commit Hooks

Claude-mpm uses pre-commit hooks with `detect-secrets` to prevent accidental credential exposure.

#### Installation

```bash
# Install pre-commit and detect-secrets
pip install pre-commit detect-secrets

# Install hooks (run in repository root)
pre-commit install

# Verify installation
pre-commit run --all-files
```

#### Configuration

The project includes:
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.secrets.baseline` - Baseline of known false positives
- `.gitignore` - Patterns for sensitive files

### Incident Response: Exposed API Key

If you accidentally commit an API key to git:

#### 1. Immediately Rotate Credentials

**HIGHEST PRIORITY**: Rotate the exposed key before attempting cleanup.

- **OpenRouter**: https://openrouter.ai/settings/keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **OpenAI**: https://platform.openai.com/api-keys
- **GitHub**: https://github.com/settings/tokens

#### 2. Remove from Git History

**WARNING**: This is a destructive operation. Coordinate with team members.

```bash
# Method 1: Using git-filter-repo (recommended)
pip install git-filter-repo
git filter-repo --path .mcp-vector-search/config.json --invert-paths

# Method 2: Using git filter-branch (legacy)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .mcp-vector-search/config.json' \
  --prune-empty --tag-name-filter cat -- --all

# Force push to remote (removes history from GitHub)
git push origin --force --all
git push origin --force --tags
```

#### 3. Update .gitignore

```bash
# Add pattern to .gitignore
echo ".mcp-vector-search/" >> .gitignore
git add .gitignore
git commit -m "chore: add MCP config to gitignore"
git push
```

#### 4. Verify Cleanup

```bash
# Check git history for the exposed file
git log --all --full-history -- .mcp-vector-search/config.json
# Should return no results

# Verify file is now ignored
git check-ignore .mcp-vector-search/config.json
# Should exit with code 0 (ignored)
```

#### 5. Assess Impact

- Review access logs for unauthorized usage
- Check for unexpected charges or API calls
- Notify stakeholders if production systems were affected
- Document the incident for future prevention

### Security Scanning Tools

#### Automated Scanning (Pre-commit)

Runs automatically before each commit:

- **detect-secrets**: Scans for API keys, tokens, passwords
- **bandit**: Python security vulnerability scanner
- **ruff**: Code quality and security linting

#### Manual Security Audits

Run periodically or before releases:

```bash
# Scan for secrets
detect-secrets scan --baseline .secrets.baseline

# Python security audit
bandit -r src/

# Dependency vulnerability check
pip-audit

# Check for outdated dependencies
pip list --outdated
```

### Secure Development Guidelines

#### Environment Variables

Use environment variables for all secrets:

```python
# ❌ NEVER do this
API_KEY = "sk-1234567890abcdef"  # pragma: allowlist secret

# ✅ Always use environment variables
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

#### Configuration Files

```python
# Create .env.example template (safe to commit)
cat > .env.example << EOF
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_APP_NAME=your_app_name

# DO NOT commit .env files with real credentials
EOF

# Load from .env (add .env to .gitignore)
from dotenv import load_dotenv
load_dotenv()
```

#### Logging

Never log sensitive information:

```python
# ❌ NEVER log credentials
logger.info(f"Using API key: {api_key}")

# ✅ Log sanitized information
logger.info("API key configured successfully")

# ✅ Redact sensitive data
def sanitize(data):
    if 'api_key' in data:
        data['api_key'] = '***REDACTED***'
    return data

logger.info(f"Config: {sanitize(config)}")
```

## Security Checklist for Contributors

Before submitting a pull request:

- [ ] No hardcoded credentials or API keys
- [ ] Sensitive files are in `.gitignore`
- [ ] Pre-commit hooks pass without warnings
- [ ] No secrets in commit history (`git log --all`)
- [ ] Environment variables used for configuration
- [ ] No sensitive data in logs or error messages
- [ ] Dependencies are up-to-date and audited
- [ ] Input validation for user-provided data
- [ ] Authentication/authorization properly implemented

## Security Features in Claude-MPM

### Automatic Security Checks

When running `claude-mpm init`, the framework performs security checks:

1. Scans for common secret files (`.mcp-vector-search/config.json`, etc.)
2. Verifies files are properly ignored by `.gitignore`
3. Checks if files are tracked by git
4. Warns about potential security risks
5. Recommends installing pre-commit hooks

### Project Initialization Security

```python
# Security checks run automatically
from claude_mpm.init import ProjectInitializer

initializer = ProjectInitializer()
initializer.initialize_project_directory()
# Output:
# 🔒 Security Check:
#    ⚠️  WARNING: .mcp-vector-search/config.json exists but not in .gitignore
#    ℹ️  RECOMMENDED: Install pre-commit hooks for automatic secret scanning
```

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [pre-commit Hooks](https://pre-commit.com/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)

## Version History

- **v1.0** (2025-01-05): Initial security policy
  - Added secret detection with detect-secrets
  - Enhanced .gitignore for MCP config files
  - Added security checks to project initialization
  - Created incident response procedures
