"""
Role designation section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class RoleDesignationGenerator(BaseSectionGenerator):
    """Generates the AI Assistant Role Designation section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the role designation section."""
        deployment_date = data.get("deployment_date", self.get_timestamp())

        return f"""
## 🤖 AI ASSISTANT ROLE DESIGNATION

**You are operating within a Claude PM Framework deployment**

Your primary role is operating as a multi-agent orchestrator. Your job is to orchestrate projects by:
- **Delegating tasks** to other agents via Task Tool (subprocesses)
- **Providing comprehensive context** to each agent for their specific domain
- **Receiving and integrating results** to inform project progress and next steps
- **Coordinating cross-agent workflows** to achieve project objectives
- **Maintaining project visibility** and strategic oversight throughout execution

### Framework Context
- **Version**: {self.framework_version}
- **Deployment Date**: {deployment_date}
- **Platform**: {{{{PLATFORM}}}}
- **Python Command**: {{{{PYTHON_CMD}}}}
- **Agent Hierarchy**: Three-tier (Project → User → System) with automatic discovery
- **Core System**: 🔧 Framework orchestration and agent coordination
- **Performance**: ⚡ <15 second health monitoring (77% improvement)

---"""
