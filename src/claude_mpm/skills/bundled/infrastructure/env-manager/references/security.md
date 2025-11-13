# Environment Security Patterns

> **Part of**: [env-manager](../SKILL.md)
> **Category**: infrastructure
> **Reading Level**: Advanced

## Purpose

Comprehensive security patterns for environment variables: secret detection, exposure scanning, git history validation, and format verification.

## Security Principles

### Never Log Secrets
**Critical Rule**: NEVER log, print, or display actual secret values in any output.

```python
# ❌ NEVER DO THIS
print(f"API_KEY: {api_key}")
logging.info(f"Database password: {db_pass}")
error(f"Failed to connect with {credentials}")

# ✅ ALWAYS DO THIS
print(f"API_KEY: {'*' * len(api_key)}")
logging.info(f"Database credentials present: {bool(db_pass)}")
error(f"Failed to connect (credentials masked)")
```

### Defense in Depth
Multiple layers of secret protection:
1. **Prevention**: .gitignore, pre-commit hooks
2. **Detection**: Pattern scanning, entropy analysis
3. **Response**: Rotation procedures, incident handling
4. **Audit**: Git history scanning, access logs

## Secret Pattern Detection

### Common Secret Patterns

**AWS Credentials:**
```python
AWS_PATTERNS = {
    'aws_access_key': re.compile(r'AKIA[0-9A-Z]{16}'),
    'aws_secret_key': re.compile(r'[0-9a-zA-Z/+=]{40}'),
    'aws_account_id': re.compile(r'\d{12}')
}
```

**GitHub Tokens:**
```python
GITHUB_PATTERNS = {
    'personal_token': re.compile(r'ghp_[0-9a-zA-Z]{36}'),
    'oauth_token': re.compile(r'gho_[0-9a-zA-Z]{36}'),
    'app_token': re.compile(r'(ghu|ghs)_[0-9a-zA-Z]{36}')
}
```

**API Keys and Tokens:**
```python
GENERIC_PATTERNS = {
    'jwt': re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
    'slack': re.compile(r'xox[baprs]-[0-9A-Za-z-]{10,72}'),
    'stripe': re.compile(r'sk_(test|live)_[0-9a-zA-Z]{24,}'),
    'mailgun': re.compile(r'key-[0-9a-z]{32}'),
    'twilio': re.compile(r'SK[0-9a-f]{32}')
}
```

### Entropy-Based Detection

High entropy strings often indicate secrets:

```python
import math
from collections import Counter

def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0

    entropy = 0
    counter = Counter(data)
    length = len(data)

    for count in counter.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy

def is_high_entropy_secret(value: str, threshold: float = 4.5) -> bool:
    """Check if value has high entropy (likely a secret)."""
    # Skip short values
    if len(value) < 20:
        return False

    # Calculate entropy
    entropy = calculate_entropy(value)

    # High entropy suggests random generation
    return entropy > threshold
```

### Secret Scanner Implementation

```python
from pathlib import Path
from typing import List, Dict
import re

class SecretScanner:
    """Scan for exposed secrets in code and config files."""

    def __init__(self):
        self.patterns = {
            **AWS_PATTERNS,
            **GITHUB_PATTERNS,
            **GENERIC_PATTERNS
        }

    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for secrets."""
        findings = []

        try:
            with open(file_path) as f:
                for line_num, line in enumerate(f, 1):
                    # Check against patterns
                    for secret_type, pattern in self.patterns.items():
                        matches = pattern.finditer(line)
                        for match in matches:
                            findings.append({
                                'file': str(file_path),
                                'line': line_num,
                                'type': secret_type,
                                'matched': self._mask_secret(match.group()),
                                'context': line[:50] + '...' if len(line) > 50 else line
                            })

                    # Check entropy
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"\'')
                        if is_high_entropy_secret(value):
                            findings.append({
                                'file': str(file_path),
                                'line': line_num,
                                'type': 'high_entropy',
                                'key': key.strip(),
                                'entropy': calculate_entropy(value)
                            })

        except Exception as e:
            logging.error(f"Error scanning {file_path}: {e}")

        return findings

    def _mask_secret(self, secret: str) -> str:
        """Mask a secret for display."""
        if len(secret) <= 4:
            return '*' * len(secret)
        return secret[:2] + '*' * (len(secret) - 4) + secret[-2:]
```

## Git History Scanning

### Check for Historical Exposures

```python
def scan_git_history(repo_path: Path, patterns: Dict) -> List[Dict]:
    """Scan git history for exposed secrets."""
    try:
        import git
    except ImportError:
        logging.warning("GitPython not installed, skipping history scan")
        return []

    findings = []
    repo = git.Repo(repo_path)

    # Scan last 100 commits
    for commit in repo.iter_commits(max_count=100):
        for file_path in commit.stats.files:
            if file_path.endswith('.env'):
                findings.append({
                    'commit': commit.hexsha[:8],
                    'file': file_path,
                    'author': commit.author.name,
                    'date': commit.committed_datetime,
                    'message': 'SECURITY: .env file in commit history'
                })

    return findings
```

## Gitignore Validation

### Ensure Proper Gitignore Coverage

```python
def validate_gitignore(project_dir: Path) -> Dict:
    """Validate .gitignore covers sensitive files."""
    gitignore_path = project_dir / '.gitignore'

    if not gitignore_path.exists():
        return {
            'valid': False,
            'errors': ['.gitignore file not found']
        }

    required_patterns = [
        '.env',
        '.env.local',
        '.env.*.local',
        '*.env'
    ]

    with open(gitignore_path) as f:
        gitignore_content = f.read()

    missing = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing.append(pattern)

    # Check if any .env files are tracked
    tracked_env_files = []
    try:
        import git
        repo = git.Repo(project_dir)
        for item in repo.tree().traverse():
            if '.env' in item.path and not item.path.endswith('.example'):
                tracked_env_files.append(item.path)
    except:
        pass

    return {
        'valid': len(missing) == 0 and len(tracked_env_files) == 0,
        'missing_patterns': missing,
        'tracked_env_files': tracked_env_files
    }
```

## Format Validation

### Validate Secret Formats

```python
def validate_secret_formats(env_file: Path) -> List[Dict]:
    """Validate that secrets match expected formats."""
    errors = []

    format_rules = {
        'DATABASE_URL': r'^(postgres|mysql|mongodb)://',
        'JWT_SECRET': lambda v: len(v) >= 32,
        'API_KEY': lambda v: len(v) >= 20,
        'STRIPE_KEY': r'^sk_(test|live)_',
        'AWS_ACCESS_KEY_ID': r'^AKIA[0-9A-Z]{16}$'
    }

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            value = value.strip().strip('"\'')

            if key in format_rules:
                rule = format_rules[key]

                if callable(rule):
                    if not rule(value):
                        errors.append({
                            'line': line_num,
                            'key': key,
                            'error': f'{key} validation failed'
                        })
                elif isinstance(rule, str):
                    if not re.match(rule, value):
                        errors.append({
                            'line': line_num,
                            'key': key,
                            'error': f'{key} format invalid'
                        })

    return errors
```

## Security Best Practices

### Environment-Specific Secrets

**Development**:
```bash
# .env.local (gitignored, local development only)
DATABASE_URL=postgres://localhost:5432/dev
JWT_SECRET=dev-secret-not-for-production
```

**Production**:
```bash
# Set via platform (Vercel, Railway, etc.)
# NEVER commit production secrets
DATABASE_URL=<from_secret_manager>
JWT_SECRET=<from_secret_manager>
```

### Secret Rotation Procedures

```python
def check_secret_age(env_file: Path) -> Dict:
    """Check when secrets were last rotated."""
    import os
    from datetime import datetime, timedelta

    file_modified = datetime.fromtimestamp(os.path.getmtime(env_file))
    age_days = (datetime.now() - file_modified).days

    recommendations = []
    if age_days > 90:
        recommendations.append({
            'severity': 'warning',
            'message': f'Secrets are {age_days} days old. Consider rotation.'
        })
    if age_days > 180:
        recommendations.append({
            'severity': 'error',
            'message': f'Secrets are {age_days} days old. MUST rotate.'
        })

    return {
        'last_modified': file_modified.isoformat(),
        'age_days': age_days,
        'recommendations': recommendations
    }
```

## Incident Response

### Secret Exposure Recovery

**If secrets are exposed**:

1. **Immediate Actions**:
```bash
# Revoke exposed credentials
# Rotate all affected secrets
# Check access logs for unauthorized use
```

2. **Git History Cleanup**:
```bash
# Use BFG Repo-Cleaner to remove secrets from history
bfg --replace-text passwords.txt
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

3. **Platform Updates**:
```bash
# Update all deployment platforms
python scripts/sync_secrets.py --platform vercel --sync
python scripts/sync_secrets.py --platform railway --sync
```

## Validation Error Messages

### CRITICAL: Never Expose Values in Error Messages

**Security Fix (2025-11-13)**: All validation error messages have been hardened to prevent accidental secret exposure.

**Problem**: Error messages that include actual variable values can leak secrets in:
- CI/CD logs
- Error tracking systems (Sentry, etc.)
- Terminal output screenshots
- Bug reports

**Solution**: Error messages NEVER include actual values, only validation criteria.

```python
# ❌ NEVER DO THIS - Exposes actual value
f'Invalid value "{vars_dict["NODE_ENV"]}", expected one of {valid_values}'

# ✅ ALWAYS DO THIS - Safe message
f'Invalid value for NODE_ENV, expected one of {valid_values}'
```

**Validation Script Protection**:
The `validate_env.py` script has been hardened against value exposure:
- Line 365: NODE_ENV validation error message sanitized
- All error messages verified to exclude variable values
- Test coverage added: `test_no_secret_exposure_in_errors`

**Testing**:
```bash
# Verify no secret exposure
echo 'NODE_ENV=sk-proj-fake-secret' > test.env
python validate_env.py test.env --framework nodejs
# Output: "Invalid value for NODE_ENV, expected..."
# NOT: "Invalid value 'sk-proj-fake-secret', expected..."
```

## Summary

**Security Checklist**:
- [ ] Never log actual secret values
- [ ] Never expose values in error messages
- [ ] .env files in .gitignore
- [ ] No secrets in git history
- [ ] Pattern-based scanning enabled
- [ ] Entropy analysis for unknowns
- [ ] Secret format validation
- [ ] Regular secret rotation (90 days)
- [ ] Incident response plan ready

**Key Patterns**:
- ✅ Pattern-based detection (AWS, GitHub, etc.)
- ✅ Entropy analysis for random secrets
- ✅ Git history scanning
- ✅ .gitignore validation
- ✅ Format validation
- ✅ Secret masking in output

## Related References

- [Validation](validation.md): Environment validation workflows
- [Synchronization](synchronization.md): Secure platform sync
- [Troubleshooting](troubleshooting.md): Security issue recovery

---
**Lines**: 267 ✓ 200-280 range
