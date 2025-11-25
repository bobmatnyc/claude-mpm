# Homebrew Tap Update Troubleshooting Guide

This guide covers common issues and solutions for Homebrew tap updates during the Claude MPM release process.

## Table of Contents

- [Quick Diagnosis](#quick-diagnosis)
- [Common Issues](#common-issues)
- [Error Messages](#error-messages)
- [Manual Recovery](#manual-recovery)
- [Prevention](#prevention)
- [Getting Help](#getting-help)

---

## Quick Diagnosis

### Check Update Status

```bash
# View last update log
cat /tmp/homebrew-tap-update.log

# Check Homebrew tap repository status
cd /tmp/homebrew-tools-update
git status
git log -1
```

### Test Update Without Changes

```bash
# Dry run to diagnose issues
make update-homebrew-tap-dry-run

# Or directly:
./scripts/update_homebrew_tap.sh $(cat VERSION) --dry-run
```

---

## Common Issues

### 1. PyPI Package Not Found

**Symptom**:
```
⚠️  PyPI package not yet available (attempt 1/10)
❌ PyPI package not found after 10 attempts
```

**Cause**: PyPI CDN propagation delay (can take up to 5 minutes)

**Solutions**:

A. **Wait and Retry** (recommended):
```bash
# Wait 5 minutes, then retry
sleep 300
make update-homebrew-tap
```

B. **Check PyPI Status**:
```bash
VERSION=$(cat VERSION)
curl -sf "https://pypi.org/pypi/claude-mpm/${VERSION}/json" | jq .
```

C. **Manual Verification**:
```bash
# Visit PyPI page directly
open "https://pypi.org/project/claude-mpm/$(cat VERSION)/"
```

**Prevention**: Use longer retry intervals in automation

---

### 2. Network Connection Failures

**Symptom**:
```
❌ Failed to fetch PyPI package info
❌ Failed to clone tap repository
```

**Cause**: Network connectivity issues, GitHub/PyPI outage

**Solutions**:

A. **Check Connectivity**:
```bash
# Test PyPI
curl -I https://pypi.org

# Test GitHub
curl -I https://github.com

# Check DNS
nslookup pypi.org
nslookup github.com
```

B. **Retry with Delay**:
```bash
# Wait and retry
sleep 60
make update-homebrew-tap
```

C. **Use VPN/Proxy** (if regional blocking):
```bash
# Configure git/curl to use proxy if needed
export https_proxy=http://proxy-address:port
```

**Prevention**: Ensure stable network connection before releases

---

### 3. Git Permission Denied

**Symptom**:
```
❌ Failed to push to GitHub
Permission denied (publickey)
```

**Cause**: SSH key not configured or GitHub authentication expired

**Solutions**:

A. **Check SSH Key**:
```bash
# Test GitHub authentication
ssh -T git@github.com

# Should respond with: "Hi username! You've successfully authenticated"
```

B. **Add/Update SSH Key**:
```bash
# Generate new SSH key if needed
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Copy public key to clipboard
pbcopy < ~/.ssh/id_ed25519.pub

# Add to GitHub: Settings → SSH and GPG keys → New SSH key
open "https://github.com/settings/keys"
```

C. **Use HTTPS Instead**:
```bash
# Change remote URL to HTTPS
cd /tmp/homebrew-tools-update
git remote set-url origin https://github.com/bobmatnyc/homebrew-tools.git

# Configure GitHub CLI for auth
gh auth login
```

**Prevention**: Keep SSH keys up to date and test before releases

---

### 4. Formula Syntax Errors

**Symptom**:
```
❌ Formula syntax check failed
```

**Cause**: Invalid Ruby syntax in updated formula

**Solutions**:

A. **Check Formula Syntax**:
```bash
cd /tmp/homebrew-tools-update
ruby -c Formula/claude-mpm.rb
```

B. **Inspect Changes**:
```bash
git diff Formula/claude-mpm.rb
```

C. **Manual Fix**:
```bash
# Edit formula
vim Formula/claude-mpm.rb

# Test syntax
ruby -c Formula/claude-mpm.rb

# If OK, commit and push
git add Formula/claude-mpm.rb
git commit -m "fix: correct formula syntax"
git push origin main
```

**Prevention**: Test formula updates in dry-run mode first

---

### 5. Homebrew Audit Warnings

**Symptom**:
```
⚠️  Homebrew audit reported warnings (non-blocking)
```

**Cause**: Formula doesn't meet Homebrew standards

**Solutions**:

A. **View Audit Details**:
```bash
cd /tmp/homebrew-tools-update
brew audit --strict Formula/claude-mpm.rb
```

B. **Common Audit Issues**:

- **Missing test block**: Add test do ... end
- **Outdated dependencies**: Update resource stanzas
- **URL format**: Use HTTPS URLs
- **SHA256 mismatch**: Verify SHA256 is correct

C. **Fix and Re-test**:
```bash
# Edit formula to fix issues
vim Formula/claude-mpm.rb

# Re-run audit
brew audit --strict Formula/claude-mpm.rb

# Test installation
brew install --build-from-source ./Formula/claude-mpm.rb
brew test claude-mpm
```

**Prevention**: Keep formula updated with Homebrew standards

---

### 6. Dependency Changes Not Detected

**Symptom**: Formula installs but missing new dependencies

**Cause**: Resource stanzas not regenerated after dependency changes

**Solutions**:

A. **Regenerate Resources**:
```bash
cd /path/to/homebrew-tools
python3 scripts/generate_resources.py > /tmp/new_resources.txt

# Compare with current resources
diff Formula/claude-mpm.rb /tmp/new_resources.txt
```

B. **Update Formula with New Resources**:
```bash
# Manually integrate new resources into formula
vim Formula/claude-mpm.rb

# Or use --regenerate-resources flag
./scripts/update_homebrew_tap.sh $(cat VERSION) --regenerate-resources
```

C. **Test Installation**:
```bash
brew install --build-from-source ./Formula/claude-mpm.rb
claude-mpm --version
```

**Prevention**: Always regenerate resources when dependencies change

---

### 7. Uncommitted Changes in Tap Repository

**Symptom**:
```
⚠️  Tap repository has uncommitted changes
❌ Cannot proceed with uncommitted changes
```

**Cause**: Previous update left uncommitted files

**Solutions**:

A. **Review Uncommitted Changes**:
```bash
cd /tmp/homebrew-tools-update
git status
git diff
```

B. **Commit or Discard**:
```bash
# Option 1: Commit changes
git add -A
git commit -m "chore: pending changes from previous update"
git push origin main

# Option 2: Discard changes
git reset --hard HEAD
git clean -fd
```

C. **Retry Update**:
```bash
make update-homebrew-tap
```

**Prevention**: Ensure updates complete fully or clean up properly

---

## Error Messages

### Exit Code Reference

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | No action needed |
| 1 | Non-critical error | Review logs, retry or manual fallback |
| 2 | Critical error | Fix issue before retrying |

### Common Error Patterns

#### "Invalid version format"
```bash
# Fix: Ensure VERSION file has correct format (X.Y.Z)
cat VERSION
# Should output: 4.8.0 (not v4.8.0 or 4.8.0-build.275)
```

#### "Failed to extract package URL from PyPI"
```bash
# Fix: PyPI response format changed or package missing
curl -sf "https://pypi.org/pypi/claude-mpm/$(cat VERSION)/json" | jq '.urls[] | select(.packagetype=="sdist")'
```

#### "Git conflict detected"
```bash
# Fix: Pull latest changes first
cd /tmp/homebrew-tools-update
git fetch origin
git reset --hard origin/main
```

---

## Manual Recovery

### Complete Manual Update Process

If automation completely fails, follow these steps:

1. **Clone Homebrew Tap**:
   ```bash
   git clone https://github.com/bobmatnyc/homebrew-tools.git /tmp/manual-homebrew-update
   cd /tmp/manual-homebrew-update
   ```

2. **Get Version Information**:
   ```bash
   VERSION=$(cat /path/to/claude-mpm/VERSION)
   echo "Updating to version: $VERSION"
   ```

3. **Fetch PyPI Package Info**:
   ```bash
   PYPI_JSON=$(curl -sf "https://pypi.org/pypi/claude-mpm/${VERSION}/json")

   PACKAGE_URL=$(echo "$PYPI_JSON" | python3 -c "
   import sys, json
   data = json.load(sys.stdin)
   for url_info in data['urls']:
       if url_info['packagetype'] == 'sdist':
           print(url_info['url'])
   ")

   PACKAGE_SHA256=$(echo "$PYPI_JSON" | python3 -c "
   import sys, json
   data = json.load(sys.stdin)
   for url_info in data['urls']:
       if url_info['packagetype'] == 'sdist':
           print(url_info['digests']['sha256'])
   ")

   echo "URL: $PACKAGE_URL"
   echo "SHA256: $PACKAGE_SHA256"
   ```

4. **Update Formula**:
   ```bash
   # Backup current formula
   cp Formula/claude-mpm.rb Formula/claude-mpm.rb.backup

   # Update URL
   sed -i '' "s|url \".*\"|url \"${PACKAGE_URL}\"|" Formula/claude-mpm.rb

   # Update SHA256
   sed -i '' "s|sha256 \".*\"|sha256 \"${PACKAGE_SHA256}\"|" Formula/claude-mpm.rb
   ```

5. **Test Formula**:
   ```bash
   # Syntax check
   ruby -c Formula/claude-mpm.rb

   # Homebrew audit
   brew audit --strict Formula/claude-mpm.rb

   # Test installation
   brew install --build-from-source ./Formula/claude-mpm.rb
   brew test claude-mpm
   claude-mpm --version
   ```

6. **Commit and Push**:
   ```bash
   git add Formula/claude-mpm.rb
   git commit -m "feat: update to v${VERSION}

   🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push origin main
   git tag "v${VERSION}"
   git push origin "v${VERSION}"
   ```

7. **Cleanup**:
   ```bash
   cd /
   rm -rf /tmp/manual-homebrew-update
   ```

---

## Prevention

### Pre-Release Checklist

Before running release:

- [ ] Stable network connection
- [ ] GitHub SSH key configured and tested
- [ ] Homebrew tap repository clean (no uncommitted changes)
- [ ] Test dry-run mode: `make update-homebrew-tap-dry-run`
- [ ] PyPI credentials verified: `.env.local` correct
- [ ] Recent formula tests pass: `brew install --build-from-source`

### Monitoring

Monitor Homebrew tap update health:

```bash
# Check last update log
tail -50 /tmp/homebrew-tap-update.log

# Check tap repository status
cd /tmp/homebrew-tools-update
git log -5 --oneline
git status
```

### Automation Health Check

```bash
# Test all components
make update-homebrew-tap-dry-run

# Verify script is executable
[ -x scripts/update_homebrew_tap.sh ] && echo "OK" || echo "NOT EXECUTABLE"

# Check dependencies
command -v ruby >/dev/null && echo "Ruby: OK" || echo "Ruby: MISSING"
command -v brew >/dev/null && echo "Homebrew: OK" || echo "Homebrew: MISSING"
command -v python3 >/dev/null && echo "Python: OK" || echo "Python: MISSING"
```

---

## Getting Help

### Gather Diagnostic Information

When reporting issues, include:

1. **Log File**:
   ```bash
   cat /tmp/homebrew-tap-update.log
   ```

2. **Version Info**:
   ```bash
   cat VERSION
   cat BUILD_NUMBER
   ```

3. **Git Status**:
   ```bash
   cd /tmp/homebrew-tools-update
   git status
   git log -3
   ```

4. **Environment**:
   ```bash
   uname -a
   brew --version
   python3 --version
   ruby --version
   ```

### Support Channels

- **GitHub Issues**: https://github.com/bobmatnyc/claude-mpm/issues
- **Homebrew Tap Issues**: https://github.com/bobmatnyc/homebrew-tools/issues
- **Documentation**: [docs/reference/DEPLOY.md](DEPLOY.md)

### Emergency Rollback

If bad formula is pushed:

```bash
cd /path/to/homebrew-tools
git revert HEAD
git push origin main
```

Or manually restore previous version:

```bash
git log --oneline
git checkout <previous-commit-sha> -- Formula/claude-mpm.rb
git commit -m "revert: restore formula to working version"
git push origin main
```

---

## Additional Resources

- **Main Deployment Guide**: [DEPLOY.md](DEPLOY.md)
- **Release Workflow**: [../../src/claude_mpm/agents/WORKFLOW.md](../../src/claude_mpm/agents/WORKFLOW.md)
- **Homebrew Documentation**: https://docs.brew.sh/Formula-Cookbook
- **PyPI Help**: https://pypi.org/help/

---

**Last Updated**: 2025-11-13
**Version**: 4.8.0
