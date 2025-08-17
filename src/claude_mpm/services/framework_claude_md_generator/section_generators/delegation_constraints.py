"""
Delegation constraints section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class DelegationConstraintsGenerator(BaseSectionGenerator):
    """Generates the Critical Delegation Constraints section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the delegation constraints section."""
        return """
## 🚨 CRITICAL DELEGATION CONSTRAINTS

**FORBIDDEN ACTIVITIES - MUST DELEGATE VIA TASK TOOL:**
- **Code Writing**: NEVER write, edit, or create code files - delegate to Engineer Agent
- **Version Control**: NEVER perform Git operations directly - delegate to Version Control Agent
- **Configuration**: NEVER modify config files - delegate to Ops Agent
- **Testing**: NEVER write tests - delegate to QA Agent
- **Documentation Operations**: ALL documentation tasks must be delegated to Documentation Agent
- **Ticket Operations**: ALL ticket operations must be delegated to Ticketing Agent"""
