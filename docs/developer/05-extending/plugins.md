# Building Claude MPM Plugins

This guide explains how to build complete plugins that bundle orchestrators, hooks, and services together into cohesive extensions.

## Overview

Plugins are self-contained packages that can:
- Add multiple components (orchestrators, hooks, services)
- Provide configuration schemas
- Include documentation and examples
- Be distributed via PyPI or private repositories
- Integrate seamlessly with Claude MPM

## Plugin Structure

```
my-claude-plugin/
├── setup.py                    # Package setup
├── README.md                   # Plugin documentation
├── requirements.txt            # Dependencies
├── LICENSE                     # License file
├── my_claude_plugin/           # Main package
│   ├── __init__.py            # Package initialization
│   ├── plugin.py              # Plugin entry point
│   ├── orchestrators/         # Custom orchestrators
│   │   ├── __init__.py
│   │   └── custom_orchestrator.py
│   ├── hooks/                 # Custom hooks
│   │   ├── __init__.py
│   │   └── custom_hooks.py
│   ├── services/              # Custom services
│   │   ├── __init__.py
│   │   └── custom_service.py
│   ├── config/                # Configuration
│   │   ├── __init__.py
│   │   └── schema.py
│   └── templates/             # Templates and examples
│       └── example_config.yaml
├── tests/                     # Plugin tests
│   ├── test_orchestrator.py
│   ├── test_hooks.py
│   └── test_service.py
└── examples/                  # Usage examples
    └── basic_usage.py
```

## Plugin Entry Point

### plugin.py

```python
from typing import Dict, Any, List
from claude_mpm.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    """Example Claude MPM plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            name="my-claude-plugin",
            version="1.0.0",
            author="Your Name",
            description="A powerful extension for Claude MPM",
            homepage="https://github.com/username/my-claude-plugin",
            tags=["automation", "integration", "productivity"]
        )
    
    def get_orchestrators(self) -> Dict[str, type]:
        """Return available orchestrators."""
        from .orchestrators import CustomOrchestrator, RemoteOrchestrator
        
        return {
            "custom": CustomOrchestrator,
            "remote": RemoteOrchestrator
        }
    
    def get_hooks(self) -> List[type]:
        """Return available hooks."""
        from .hooks import (
            ValidationHook,
            LoggingHook,
            MetricsHook,
            NotificationHook
        )
        
        return [
            ValidationHook,
            LoggingHook,
            MetricsHook,
            NotificationHook
        ]
    
    def get_services(self) -> Dict[str, type]:
        """Return available services."""
        from .services import (
            DatabaseService,
            CacheService,
            NotificationService
        )
        
        return {
            "database": DatabaseService,
            "cache": CacheService,
            "notifications": NotificationService
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema."""
        from .config.schema import get_schema
        return get_schema()
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        from .config.schema import validate_config
        return validate_config(config)
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration."""
        if not self.validate_config(config):
            raise ValueError("Invalid plugin configuration")
        
        self.config = config
        self._setup_logging()
        self._setup_defaults()
    
    def _setup_logging(self):
        """Set up plugin logging."""
        import logging
        self.logger = logging.getLogger(self.metadata.name)
        
        if self.config.get("debug", False):
            self.logger.setLevel(logging.DEBUG)
    
    def _setup_defaults(self):
        """Set up default values."""
        self.config.setdefault("timeout", 300)
        self.config.setdefault("retry_attempts", 3)
```

## Configuration Schema

### config/schema.py

```python
from typing import Dict, Any
import jsonschema

def get_schema() -> Dict[str, Any]:
    """Get plugin configuration schema."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "enabled": {
                "type": "boolean",
                "description": "Enable the plugin",
                "default": True
            },
            "debug": {
                "type": "boolean",
                "description": "Enable debug logging",
                "default": False
            },
            "database": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Database connection URL"
                    },
                    "pool_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    }
                },
                "required": ["url"]
            },
            "notifications": {
                "type": "object",
                "properties": {
                    "webhook_url": {
                        "type": "string",
                        "format": "uri"
                    },
                    "email": {
                        "type": "object",
                        "properties": {
                            "smtp_host": {"type": "string"},
                            "smtp_port": {"type": "integer"},
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "from_address": {"type": "string", "format": "email"}
                        }
                    }
                }
            },
            "hooks": {
                "type": "object",
                "properties": {
                    "validation": {
                        "type": "object",
                        "properties": {
                            "max_length": {"type": "integer", "default": 10000},
                            "blocked_words": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "metrics": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean", "default": True},
                            "export_interval": {"type": "integer", "default": 60}
                        }
                    }
                }
            }
        },
        "required": ["enabled"]
    }

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration against schema."""
    try:
        jsonschema.validate(config, get_schema())
        return True
    except jsonschema.ValidationError:
        return False
```

## Complete Plugin Example

### Real-World Plugin: GitHub Integration

```python
# github_integration_plugin/plugin.py

from typing import Dict, Any, List, Optional
from claude_mpm.plugins import BasePlugin, PluginMetadata
import aiohttp

class GitHubIntegrationPlugin(BasePlugin):
    """GitHub integration plugin for Claude MPM."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="claude-mpm-github",
            version="2.0.0",
            author="Claude MPM Team",
            description="GitHub integration for automated issue and PR management",
            homepage="https://github.com/claude-mpm/github-plugin",
            tags=["github", "vcs", "automation", "issues", "pull-requests"]
        )
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin."""
        super().initialize(config)
        
        # Validate required config
        if not config.get("github", {}).get("token"):
            raise ValueError("GitHub token is required")
        
        self.token = config["github"]["token"]
        self.org = config["github"].get("org")
        self.repo = config["github"].get("repo")
    
    def get_orchestrators(self) -> Dict[str, type]:
        """Return GitHub-aware orchestrators."""
        from .orchestrators import GitHubOrchestrator
        
        return {
            "github": GitHubOrchestrator
        }
    
    def get_hooks(self) -> List[type]:
        """Return GitHub hooks."""
        from .hooks import (
            IssueCreationHook,
            PRCreationHook,
            CommitMessageHook,
            WorkflowTriggerHook
        )
        
        return [
            IssueCreationHook,
            PRCreationHook,
            CommitMessageHook,
            WorkflowTriggerHook
        ]
    
    def get_services(self) -> Dict[str, type]:
        """Return GitHub services."""
        from .services import GitHubService, CodeReviewService
        
        return {
            "github": GitHubService,
            "code_review": CodeReviewService
        }

# github_integration_plugin/orchestrators/github_orchestrator.py

from claude_mpm.orchestration.orchestrator import MPMOrchestrator
from typing import Optional
import re

class GitHubOrchestrator(MPMOrchestrator):
    """Orchestrator with GitHub integration."""
    
    def __init__(self, github_service, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.github_service = github_service
        self.issue_pattern = re.compile(r'\[ISSUE\]\s*(.+)')
        self.pr_pattern = re.compile(r'\[PR\]\s*(.+)')
    
    def _process_output_line(self, line: str):
        """Process output with GitHub integration."""
        # Check for issue creation
        issue_match = self.issue_pattern.match(line)
        if issue_match:
            self._create_issue(issue_match.group(1))
        
        # Check for PR creation
        pr_match = self.pr_pattern.match(line)
        if pr_match:
            self._create_pr(pr_match.group(1))
        
        # Continue normal processing
        super()._process_output_line(line)
    
    async def _create_issue(self, title: str):
        """Create GitHub issue."""
        try:
            issue = await self.github_service.create_issue(
                title=title,
                body=f"Created by Claude MPM\n\nSession: {self.session_id}",
                labels=["claude-mpm", "automated"]
            )
            self.logger.info(f"Created issue #{issue['number']}: {title}")
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
    
    async def _create_pr(self, description: str):
        """Create pull request."""
        # Parse PR info from description
        # Format: "branch_name: PR title"
        parts = description.split(":", 1)
        if len(parts) == 2:
            branch = parts[0].strip()
            title = parts[1].strip()
            
            try:
                pr = await self.github_service.create_pull_request(
                    title=title,
                    body="Created by Claude MPM",
                    head=branch,
                    base="main"
                )
                self.logger.info(f"Created PR #{pr['number']}: {title}")
            except Exception as e:
                self.logger.error(f"Failed to create PR: {e}")

# github_integration_plugin/hooks/issue_creation_hook.py

from claude_mpm.hooks.base_hook import TicketExtractionHook, HookContext, HookResult

class IssueCreationHook(TicketExtractionHook):
    """Create GitHub issues from extracted tickets."""
    
    def __init__(self, github_service, config: Dict[str, Any]):
        super().__init__(name="github-issue-creator", priority=50)
        self.github_service = github_service
        self.config = config
        self.auto_create = config.get("auto_create_issues", True)
    
    async def execute(self, context: HookContext) -> HookResult:
        """Create issue from ticket."""
        if not self.auto_create:
            return HookResult(success=True)
        
        ticket = context.data
        
        # Map ticket types to labels
        label_map = {
            "BUG": ["bug", "needs-triage"],
            "FEATURE": ["enhancement"],
            "TASK": ["task"],
            "DOCUMENTATION": ["documentation"]
        }
        
        labels = label_map.get(ticket.get("type", "TASK"), ["task"])
        
        try:
            issue = await self.github_service.create_issue(
                title=ticket["title"],
                body=self._format_issue_body(ticket),
                labels=labels
            )
            
            # Add issue URL to ticket
            ticket["github_issue_url"] = issue["html_url"]
            ticket["github_issue_number"] = issue["number"]
            
            return HookResult(
                success=True,
                data=ticket
            )
            
        except Exception as e:
            return HookResult(
                success=False,
                error=f"Failed to create issue: {e}"
            )
    
    def _format_issue_body(self, ticket: Dict[str, Any]) -> str:
        """Format issue body from ticket."""
        body = f"## Description\n\n{ticket.get('description', 'No description provided')}\n\n"
        body += f"## Metadata\n\n"
        body += f"- **Type**: {ticket.get('type', 'TASK')}\n"
        body += f"- **Source**: Claude MPM\n"
        body += f"- **Created**: {ticket.get('created_at', 'Unknown')}\n"
        
        if ticket.get('session_id'):
            body += f"- **Session**: {ticket['session_id']}\n"
        
        return body
```

## Plugin Installation

### setup.py

```python
from setuptools import setup, find_packages

setup(
    name="claude-mpm-github",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="GitHub integration plugin for Claude MPM",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/username/claude-mpm-github",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "claude-mpm>=1.0.0",
        "aiohttp>=3.8.0",
        "jsonschema>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ]
    },
    entry_points={
        "claude_mpm.plugins": [
            "github = github_integration_plugin.plugin:GitHubIntegrationPlugin",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
```

## Plugin Configuration

### User Configuration

```yaml
# ~/.claude-mpm/config.yaml
plugins:
  github:
    enabled: true
    config:
      github:
        token: ${GITHUB_TOKEN}  # Environment variable
        org: my-organization
        repo: my-repository
      
      auto_create_issues: true
      auto_create_prs: false
      
      issue_templates:
        bug: .github/ISSUE_TEMPLATE/bug_report.md
        feature: .github/ISSUE_TEMPLATE/feature_request.md
      
      hooks:
        validation:
          max_length: 5000
          blocked_words: ["password", "secret", "key"]
        
        metrics:
          enabled: true
          export_to: prometheus
          endpoint: /metrics
```

## Plugin Discovery

Claude MPM discovers plugins through:

1. **Entry Points**: Defined in setup.py
2. **Plugin Directory**: `~/.claude-mpm/plugins/`
3. **Environment Variable**: `CLAUDE_MPM_PLUGINS`

```python
# claude_mpm/plugin_loader.py

import pkg_resources
from typing import Dict, Type
from .plugins import BasePlugin

def discover_plugins() -> Dict[str, Type[BasePlugin]]:
    """Discover all available plugins."""
    plugins = {}
    
    # Load from entry points
    for entry_point in pkg_resources.iter_entry_points("claude_mpm.plugins"):
        try:
            plugin_class = entry_point.load()
            plugins[entry_point.name] = plugin_class
        except Exception as e:
            print(f"Failed to load plugin {entry_point.name}: {e}")
    
    return plugins

def load_plugin(name: str, config: Dict[str, Any]) -> BasePlugin:
    """Load and initialize a plugin."""
    plugins = discover_plugins()
    
    if name not in plugins:
        raise ValueError(f"Plugin '{name}' not found")
    
    plugin_class = plugins[name]
    plugin = plugin_class()
    plugin.initialize(config)
    
    return plugin
```

## Testing Plugins

### Test Structure

```python
# tests/test_plugin.py

import pytest
from github_integration_plugin.plugin import GitHubIntegrationPlugin

@pytest.fixture
def plugin_config():
    return {
        "enabled": True,
        "github": {
            "token": "test-token",
            "org": "test-org",
            "repo": "test-repo"
        }
    }

@pytest.fixture
def plugin(plugin_config):
    plugin = GitHubIntegrationPlugin()
    plugin.initialize(plugin_config)
    return plugin

def test_plugin_metadata(plugin):
    metadata = plugin.metadata
    assert metadata.name == "claude-mpm-github"
    assert metadata.version == "2.0.0"

def test_plugin_orchestrators(plugin):
    orchestrators = plugin.get_orchestrators()
    assert "github" in orchestrators

def test_plugin_hooks(plugin):
    hooks = plugin.get_hooks()
    assert len(hooks) > 0

def test_plugin_services(plugin):
    services = plugin.get_services()
    assert "github" in services

@pytest.mark.asyncio
async def test_github_orchestrator(plugin):
    from github_integration_plugin.services import GitHubService
    
    # Mock GitHub service
    github_service = GitHubService(
        token="test",
        org="test",
        repo="test"
    )
    
    orchestrators = plugin.get_orchestrators()
    GitHubOrchestrator = orchestrators["github"]
    
    orchestrator = GitHubOrchestrator(
        github_service=github_service,
        log_level="DEBUG"
    )
    
    # Test initialization
    assert orchestrator.github_service == github_service
```

## Plugin Best Practices

1. **Namespace Everything**: Use your plugin name as prefix
2. **Provide Defaults**: Include sensible default configurations
3. **Document Thoroughly**: Include README, examples, and API docs
4. **Version Carefully**: Follow semantic versioning
5. **Test Extensively**: Unit and integration tests
6. **Handle Errors**: Graceful degradation
7. **Log Appropriately**: Use plugin-specific logger
8. **Validate Config**: Use JSON Schema or similar
9. **Support Multiple Versions**: Of Claude MPM
10. **Provide Examples**: Show common use cases

## Distribution

### PyPI Release

```bash
# Build distribution
python setup.py sdist bdist_wheel

# Upload to PyPI
twine upload dist/*
```

### Private Repository

```bash
# Install from Git
pip install git+https://github.com/username/claude-mpm-plugin.git

# Install from private PyPI
pip install --index-url https://pypi.company.com claude-mpm-plugin
```

## Plugin Ecosystem

### Core Plugins

- **claude-mpm-github**: GitHub integration
- **claude-mpm-gitlab**: GitLab integration
- **claude-mpm-jira**: JIRA integration
- **claude-mpm-slack**: Slack notifications
- **claude-mpm-aws**: AWS service integration

### Community Plugins

Encourage community contributions by:
- Providing plugin template
- Maintaining plugin registry
- Showcasing exemplary plugins
- Offering development support

## Advanced Plugin Features

### Dynamic Loading

```python
class DynamicPlugin(BasePlugin):
    """Plugin that loads components dynamically."""
    
    def get_orchestrators(self) -> Dict[str, type]:
        """Dynamically load orchestrators based on config."""
        orchestrators = {}
        
        for name, module_path in self.config.get("orchestrators", {}).items():
            try:
                module = importlib.import_module(module_path)
                orchestrators[name] = module.Orchestrator
            except Exception as e:
                self.logger.error(f"Failed to load orchestrator {name}: {e}")
        
        return orchestrators
```

### Plugin Dependencies

```python
class DependentPlugin(BasePlugin):
    """Plugin with dependencies on other plugins."""
    
    @property
    def dependencies(self) -> List[str]:
        """List required plugins."""
        return ["claude-mpm-github", "claude-mpm-slack"]
    
    def initialize(self, config: Dict[str, Any], plugins: Dict[str, BasePlugin]) -> None:
        """Initialize with access to other plugins."""
        super().initialize(config)
        
        # Access other plugins
        self.github_plugin = plugins.get("github")
        self.slack_plugin = plugins.get("slack")
        
        if not all([self.github_plugin, self.slack_plugin]):
            raise RuntimeError("Required plugin dependencies not met")
```