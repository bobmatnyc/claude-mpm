# GitHub Pages Setup Instructions

## Quick Setup Guide

Follow these steps to enable GitHub Pages for your documentation:

### 1. Enable GitHub Pages in Repository Settings

1. Go to your repository on GitHub: https://github.com/bobmatnyc/claude-mpm
2. Click on **Settings** tab
3. Scroll down to **Pages** section in the left sidebar
4. Under **Source**, select **GitHub Actions**
5. Click **Save**

### 2. Push the Workflow to GitHub

```bash
# Add the new files
git add .github/
git add docs/api/requirements.txt
git add scripts/test_docs_build.sh

# Commit the changes
git commit -m "feat: add GitHub Pages deployment workflow for documentation

- Created GitHub Actions workflow for automated docs deployment
- Added documentation-specific requirements file
- Configured Sphinx build and deployment to gh-pages
- Added local testing script for documentation builds"

# Push to main branch
git push origin main
```

### 3. Trigger the First Build

After pushing, the workflow will automatically trigger. You can also manually trigger it:

1. Go to **Actions** tab in your repository
2. Select **Deploy Documentation** workflow
3. Click **Run workflow** button
4. Select **main** branch
5. Click **Run workflow**

### 4. Verify Deployment

1. Check the workflow status in the Actions tab
2. Once successful, your documentation will be available at:
   - **Main URL**: https://bobmatnyc.github.io/claude-mpm/
   - **API Docs**: https://bobmatnyc.github.io/claude-mpm/modules.html

### 5. Add Badge to README

Add this badge to your main README.md to show documentation status:

```markdown
[![Documentation](https://github.com/bobmatnyc/claude-mpm/actions/workflows/docs.yml/badge.svg)](https://bobmatnyc.github.io/claude-mpm/)
```

Or with more badges:

```markdown
[![Documentation](https://github.com/bobmatnyc/claude-mpm/actions/workflows/docs.yml/badge.svg)](https://bobmatnyc.github.io/claude-mpm/)
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://bobmatnyc.github.io/claude-mpm/)
[![Sphinx](https://img.shields.io/badge/docs-Sphinx-blue)](https://www.sphinx-doc.org/)
```

## Testing Locally Before Push

Run the test script to verify documentation builds correctly:

```bash
# From project root
./scripts/test_docs_build.sh
```

## Troubleshooting

### If the workflow fails:

1. **Check Action Logs**: 
   - Go to Actions tab
   - Click on the failed workflow run
   - Review the error messages

2. **Common Issues**:
   - **Import errors**: Ensure all dependencies are in pyproject.toml or requirements.txt
   - **Sphinx errors**: Check conf.py configuration
   - **Permission errors**: Verify GitHub Pages is enabled with "GitHub Actions" source

3. **Test Locally**:
   ```bash
   cd docs/api
   make clean
   make html
   # Check for errors in output
   ```

### If Pages doesn't show:

1. **Wait a few minutes**: First deployment can take 5-10 minutes
2. **Check Pages settings**: Ensure "GitHub Actions" is selected as source
3. **Check deployment**: Go to Actions > Deploy Documentation > deploy job
4. **Clear browser cache**: Try incognito/private browsing mode

## Workflow Features

- ✅ **Automatic triggers** on documentation changes
- ✅ **Manual trigger** option via workflow_dispatch
- ✅ **Dependency caching** for faster builds
- ✅ **PR testing** without deployment
- ✅ **Warning detection** to maintain quality
- ✅ **Artifact upload** for debugging
- ✅ **.nojekyll file** for proper GitHub Pages rendering

## Next Steps

After successful deployment:

1. **Monitor builds**: Set up notifications for workflow failures
2. **Customize theme**: Modify sphinx-rtd-theme settings in conf.py
3. **Add custom domain**: Configure custom domain in Pages settings
4. **Enable search**: Sphinx automatically includes search functionality
5. **Add Google Analytics**: Add tracking code to conf.py if needed

## Security Notes

- Workflow uses minimal required permissions
- No secrets or tokens needed (uses GITHUB_TOKEN)
- Dependencies are version-pinned for reproducibility
- Build artifacts are temporary and auto-deleted

## Support

For issues with:
- **Workflow**: Check .github/workflows/docs.yml
- **Sphinx build**: Review docs/api/conf.py
- **Dependencies**: Update docs/api/requirements.txt
- **GitHub Pages**: Check repository Settings > Pages