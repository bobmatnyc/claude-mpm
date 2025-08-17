"""
Environment configuration section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class EnvironmentConfigGenerator(BaseSectionGenerator):
    """Generates the Environment Configuration section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the environment configuration section."""
        return """
## 🚨 ENVIRONMENT CONFIGURATION

### Python Environment
- **Command**: {{PYTHON_CMD}}
- **Requirements**: See `requirements/` directory
- **Framework Import**: `import claude_pm`

### Platform-Specific Notes
{{PLATFORM_NOTES}}"""
