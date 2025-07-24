"""
Troubleshooting section generator for framework CLAUDE.md.
"""

from typing import Dict, Any
from . import BaseSectionGenerator


class TroubleshootingGenerator(BaseSectionGenerator):
    """Generates the Troubleshooting section."""
    
    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the troubleshooting section."""
        return """
## 🚨 TROUBLESHOOTING

### Common Issues
1. **CLI Not Working**: Check claude-pm installation and path
2. **Python Import Errors**: Verify Python environment and dependencies
3. **Health Check Failures**: Run `claude-pm init --verify` for diagnostics
4. **Permission Issues**: Ensure proper file permissions on CLI executables

### claude-pm init and Agent Hierarchy Issues
5. **Missing .claude-pm Directories**: Run `claude-pm init --setup`
6. **Agent Hierarchy Validation Errors**: Run `claude-pm init --verify` for detailed validation

### Core System Issues
7. **Core System Issues**: Update initialization to use proper configuration
8. **Core System Not Working**: Verify API keys and network connectivity
9. **Core System Performance Issues**: Implement system optimization

### Agent Registry Issues
10. **Agent Registry Discovery Failures**: Run `python -c "from claude_pm.core.agent_registry import AgentRegistry; AgentRegistry().health_check()"`
11. **Agent Precedence Problems**: Verify directory structure with `claude-pm init --verify`
12. **Specialization Discovery Issues**: Check agent metadata and specialization tags
13. **Performance Cache Problems**: Clear SharedPromptCache and reinitialize registry
14. **Agent Modification Tracking Errors**: Verify agent file permissions and timestamps
15. **Custom Agent Loading Issues**: Verify user-agents directory structure and agent file format
16. **Directory Precedence Problems**: Check user-agents directory hierarchy and parent directory traversal"""