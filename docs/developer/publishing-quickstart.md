# PyPI Publishing - Quick Start

Quick reference for publishing Claude MPM to PyPI.

## First Time Setup

1. **Get PyPI API Token**
   - Visit: https://pypi.org/manage/account/token/
   - Create token for `claude-mpm` project
   - Copy token (starts with `pypi-`)

2. **Create .env.local**
   ```bash
   echo "PYPI_API_KEY=pypi-YOUR-TOKEN-HERE" > .env.local
   chmod 600 .env.local
   ```

3. **Verify Setup**
   ```bash
   ./scripts/verify_publish_setup.sh
   ```

## Publishing Workflow

### Standard Publish

```bash
# 1. Pre-publish cleanup and quality checks
make pre-publish

# 2. Build (with quality checks)
make safe-release-build

# 3. Publish to PyPI
make publish-pypi
```

**Note**: `make pre-publish` automatically runs cleanup to remove temporary files before publishing. See [Pre-Publish Cleanup](./pre-publish-cleanup.md) for details.

### Detailed Steps

```bash
# 1. Pre-publish cleanup and quality checks
make pre-publish

# 2. Build distribution
make safe-release-build

# 3. Verify build
ls -lh dist/

# 4. Verify setup
./scripts/verify_publish_setup.sh

# 5. Publish
make publish-pypi
# or: ./scripts/publish_to_pypi.sh
```

## Verification

After publishing, verify at:
- **PyPI Page**: https://pypi.org/project/claude-mpm/
- **Test Install**: `pip install --upgrade claude-mpm`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `.env.local` not found | Create it with your API key |
| Invalid token | Regenerate token on PyPI |
| Version exists | Increment version and rebuild |
| Files not found | Run `make safe-release-build` |

## Security Checklist

- [ ] `.env.local` has 600 permissions
- [ ] `.env.local` is gitignored
- [ ] API token is project-scoped
- [ ] Never commit `.env.local`
- [ ] Never share API token

## Full Documentation

- **Publishing Guide**: [docs/developer/publishing.md](docs/developer/publishing.md)
- **Pre-Publish Cleanup**: [docs/developer/pre-publish-cleanup.md](./pre-publish-cleanup.md)
- **Publishing Setup**: [docs/developer/publishing-setup.md](./publishing-setup.md)

## Commands Reference

```bash
# Pre-publish cleanup and quality checks
make pre-publish

# Individual cleanup targets
make clean-pre-publish    # Automated cleanup only
make clean-system-files   # Remove .DS_Store, __pycache__, *.pyc
make clean-test-artifacts # Remove test HTML/JSON files
make clean-deprecated     # Remove deprecated documentation

# Verify setup (safe, read-only)
./scripts/verify_publish_setup.sh

# Build with quality checks
make safe-release-build

# Publish to PyPI
make publish-pypi
./scripts/publish_to_pypi.sh

# View all Makefile targets
make help
```

## Support

- **Documentation**: `docs/developer/publishing.md`
- **Issues**: https://github.com/bobmatnyc/claude-mpm/issues
- **PyPI**: https://pypi.org/project/claude-mpm/
