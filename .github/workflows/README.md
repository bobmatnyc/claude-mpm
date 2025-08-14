# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the claude-mpm project.

## Documentation Deployment Workflow (`docs.yml`)

Automatically builds and deploys Sphinx documentation to GitHub Pages.

### Features

- **Automatic Deployment**: Triggers on push to main branch when documentation changes
- **Manual Trigger**: Can be manually triggered via GitHub Actions UI
- **Caching**: Caches Python dependencies for faster builds
- **Artifact Upload**: Uploads built documentation as artifact before deployment
- **PR Testing**: Tests documentation builds on pull requests (without deployment)
- **Warning Detection**: Fails if Sphinx build contains warnings

### Triggers

The workflow runs when:
- Changes are pushed to `main` branch in:
  - `docs/` directory
  - `src/` directory (for API documentation)
  - `.github/workflows/docs.yml`
  - `pyproject.toml`
  - `requirements*.txt` files
- Manually triggered via workflow_dispatch

### Setup Instructions

1. **Enable GitHub Pages in Repository Settings**:
   - Go to Settings > Pages
   - Source: "GitHub Actions"
   - Branch: This is handled by the workflow

2. **Ensure Required Permissions**:
   The workflow needs these permissions (already configured in workflow):
   - `contents: read` - To checkout code
   - `pages: write` - To deploy to GitHub Pages
   - `id-token: write` - For OIDC token for deployment

3. **First Deployment**:
   - Push changes to main branch or manually trigger the workflow
   - The workflow will:
     1. Build documentation with Sphinx
     2. Upload as GitHub Pages artifact
     3. Deploy to GitHub Pages
   - Documentation will be available at: https://bobmatnyc.github.io/claude-mpm/

### Build Process

1. **Environment Setup**:
   - Uses Ubuntu latest
   - Python 3.11
   - Installs graphviz for diagrams

2. **Dependencies Installation**:
   - Installs package with `[docs]` extras
   - Installs additional requirements from `docs/api/requirements.txt`

3. **Documentation Build**:
   - Runs `make clean` to ensure clean build
   - Runs `make html` to build documentation
   - Adds `.nojekyll` file for GitHub Pages compatibility

4. **Verification**:
   - Checks that `index.html` exists
   - Verifies no warnings in build output

### Caching Strategy

The workflow uses pip caching based on:
- `pyproject.toml`
- `docs/api/requirements.txt`

This significantly speeds up subsequent builds.

### Troubleshooting

If the deployment fails:

1. **Check Build Logs**: Review the "Build Sphinx documentation" step
2. **Verify Dependencies**: Ensure all required packages are in requirements
3. **Check Sphinx Configuration**: Review `docs/api/conf.py`
4. **Pages Settings**: Verify GitHub Pages is enabled with "GitHub Actions" source

### Local Testing

To test the documentation build locally:

```bash
# Install dependencies
pip install -e .[docs]
pip install -r docs/api/requirements.txt

# Build documentation
cd docs/api
make clean
make html

# View locally
python -m http.server 8000 --directory _build/html
# Open http://localhost:8000
```

### URL Structure

After deployment, documentation will be available at:
- Main page: https://bobmatnyc.github.io/claude-mpm/
- API Reference: https://bobmatnyc.github.io/claude-mpm/modules.html
- Individual modules: https://bobmatnyc.github.io/claude-mpm/claude_mpm.html

### Build Status Badge

Add this badge to your main README.md:

```markdown
[![Documentation](https://github.com/bobmatnyc/claude-mpm/actions/workflows/docs.yml/badge.svg)](https://github.com/bobmatnyc/claude-mpm/actions/workflows/docs.yml)
```

### Security Notes

- The workflow uses latest stable versions of GitHub Actions
- Python dependencies are pinned with minimum versions
- GITHUB_TOKEN permissions are explicitly limited
- No secrets are exposed in the workflow