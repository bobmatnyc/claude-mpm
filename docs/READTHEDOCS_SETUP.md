# Read the Docs Setup Guide for claude-mpm

## Overview
This guide provides instructions for setting up and managing the Read the Docs deployment for claude-mpm documentation.

## Configuration Files Created

### 1. `.readthedocs.yaml`
The main configuration file for Read the Docs has been created with:
- Python 3.11 build environment
- Sphinx documentation builder
- PDF, EPUB, and HTML ZIP format support
- Automatic dependency installation
- Search functionality configuration
- Pre and post-build hooks

## Setting Up Read the Docs

### Step 1: Import the Project

1. Go to [Read the Docs](https://readthedocs.org/)
2. Sign in with your GitHub account
3. Click "Import a Project"
4. Select `bobmatnyc/claude-mpm` from your GitHub repositories
5. Click "Next"

### Step 2: Project Configuration

Configure the following settings:

1. **Name**: `claude-mpm`
2. **Repository URL**: `https://github.com/bobmatnyc/claude-mpm`
3. **Repository type**: Git
4. **Default branch**: `main`
5. **Documentation type**: Sphinx Html
6. **Language**: English
7. **Programming Language**: Python
8. **Project homepage**: `https://github.com/bobmatnyc/claude-mpm`

### Step 3: Advanced Settings

Navigate to Admin → Advanced Settings and configure:

1. **Privacy Level**: Public
2. **Single version**: Unchecked (to support multiple versions)
3. **Default version**: `latest`
4. **Show versions**: Check this option
5. **Enable PDF builds**: Yes
6. **Enable EPUB builds**: Yes

### Step 4: Environment Variables

Add the following environment variable in Admin → Environment Variables:

```
READTHEDOCS_API_TOKEN = c60cfe7df2a7ca7fb296ead903c4a393b5ba514c
```

### Step 5: Webhook Configuration

#### GitHub Webhook Setup

1. In Read the Docs, go to Admin → Integrations
2. Click "Add integration"
3. Select "GitHub incoming webhook"
4. Copy the webhook URL provided

In your GitHub repository:

1. Go to Settings → Webhooks
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: Paste the Read the Docs webhook URL
   - **Content type**: `application/json`
   - **Secret**: Leave empty (Read the Docs handles authentication)
   - **Events**: Select "Just the push event"
   - **Active**: Check this box
4. Click "Add webhook"

#### Automatic Build Triggers

The webhook will trigger builds on:
- Push to main branch
- New tag creation (for versioned documentation)
- Pull request updates (if PR builds are enabled)

### Step 6: Version Management

#### Activating Versions

1. Go to Versions in Read the Docs admin
2. Activate the following:
   - `latest` (main branch)
   - Any tagged versions (e.g., `v3.8.2`)
   - `stable` (latest tagged release)

#### Version Configuration

Edit each version to set:
- **Active**: Yes (for versions you want to build)
- **Hidden**: No (for public versions)
- **Privacy Level**: Public

### Step 7: Build Configuration

#### Initial Build

1. Go to Builds in the Read the Docs dashboard
2. Click "Build Version" for `latest`
3. Monitor the build output for any errors

#### Build Troubleshooting

Common issues and solutions:

1. **Missing dependencies**: Add to `docs/api/requirements.txt`
2. **Import errors**: Add modules to `autodoc_mock_imports` in `conf.py`
3. **Memory issues**: Contact Read the Docs support for build resource increases
4. **Timeout issues**: Optimize documentation generation or request extended build time

### Step 8: Custom Domain (Optional)

To use a custom domain like `docs.claude-mpm.io`:

1. Go to Admin → Domains
2. Click "Add Domain"
3. Enter your custom domain
4. Add the CNAME record to your DNS:
   ```
   docs.claude-mpm.io CNAME claude-mpm.readthedocs.io
   ```
5. Enable HTTPS (recommended)

## API Integration

### Using the Read the Docs API

With the provided API token, you can programmatically:

```python
import requests

# Base configuration
API_TOKEN = "c60cfe7df2a7ca7fb296ead903c4a393b5ba514c"
PROJECT_SLUG = "claude-mpm"
BASE_URL = "https://readthedocs.org/api/v3"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Trigger a build
def trigger_build(version="latest"):
    url = f"{BASE_URL}/projects/{PROJECT_SLUG}/versions/{version}/builds/"
    response = requests.post(url, headers=headers, json={})
    return response.json()

# Get build status
def get_build_status(build_id):
    url = f"{BASE_URL}/projects/{PROJECT_SLUG}/builds/{build_id}/"
    response = requests.get(url, headers=headers)
    return response.json()

# List all versions
def list_versions():
    url = f"{BASE_URL}/projects/{PROJECT_SLUG}/versions/"
    response = requests.get(url, headers=headers)
    return response.json()
```

## Monitoring and Maintenance

### Build Status Badge

Add to your README.md:

```markdown
[![Documentation Status](https://readthedocs.org/projects/claude-mpm/badge/?version=latest)](https://claude-mpm.readthedocs.io/en/latest/?badge=latest)
```

### Build Notifications

Configure build notifications in Admin → Notifications:
- Email notifications for failed builds
- Webhook notifications for CI/CD integration
- Slack/Discord integration for team notifications

### Regular Maintenance

1. **Weekly**: Review build logs for warnings
2. **Monthly**: Update documentation dependencies
3. **Quarterly**: Review and optimize build configuration
4. **Annually**: Review documentation structure and navigation

## Documentation URLs

Once configured, your documentation will be available at:

- **Latest (main branch)**: https://claude-mpm.readthedocs.io/en/latest/
- **Stable (latest release)**: https://claude-mpm.readthedocs.io/en/stable/
- **Specific version**: https://claude-mpm.readthedocs.io/en/v3.8.2/
- **PDF download**: https://claude-mpm.readthedocs.io/_/downloads/en/latest/pdf/
- **EPUB download**: https://claude-mpm.readthedocs.io/_/downloads/en/latest/epub/

## Search Configuration

The search functionality is automatically configured with:
- Full-text search across all documentation
- Boosted ranking for API reference pages
- Search suggestions and autocomplete
- Faceted search by version

## Troubleshooting

### Common Issues

1. **Build fails with "Module not found"**
   - Add the module to `autodoc_mock_imports` in `conf.py`
   - Or install the module in `docs/api/requirements.txt`

2. **Build times out**
   - Reduce the number of modules being documented
   - Use `:no-members:` directive for large modules
   - Contact Read the Docs support for extended build time

3. **Search not working properly**
   - Check that HTML files are being generated correctly
   - Verify search configuration in `.readthedocs.yaml`
   - Clear browser cache and try again

4. **Version not appearing**
   - Ensure the version is activated in Read the Docs admin
   - Check that the git tag exists in the repository
   - Verify the branch/tag naming convention

## Support

For additional help:
- Read the Docs documentation: https://docs.readthedocs.io/
- Read the Docs support: support@readthedocs.org
- GitHub issues: https://github.com/bobmatnyc/claude-mpm/issues

## Security Notes

- Keep the API token secure and never commit it to the repository
- Use environment variables for sensitive configuration
- Regularly rotate API tokens
- Monitor access logs for suspicious activity