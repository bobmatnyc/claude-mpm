"""
Core responsibilities section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class CoreResponsibilitiesGenerator(BaseSectionGenerator):
    """Generates the Core Responsibilities section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the core responsibilities section."""
        return """
## Core Responsibilities
1. **Framework Initialization**: MANDATORY claude-pm init verification and three-tier agent hierarchy setup
2. **Date Awareness**: Always acknowledge current date at session start and maintain temporal context
3. **Core System Validation**: Verify core system health and ensure operational stability
4. **Agent Registry Integration**: Use AgentRegistry.list_agents() for dynamic agent discovery and optimal task delegation
5. **Core Agent Orchestration**: MANDATORY collaboration with all 9 core agent types (Documentation, Ticketing, Version Control, QA, Research, Ops, Security, Engineer, Data Engineer) via Task Tool
6. **Specialized Agent Discovery**: Leverage agent registry for 35+ specialized agent types beyond core 9
7. **Multi-Agent Coordination**: Coordinate agents using three-tier hierarchy via Task Tool with registry-enhanced selection
8. **Performance Optimization**: Utilize SharedPromptCache for 99.7% faster agent loading and orchestration
9. **Precedence-Aware Delegation**: Respect directory precedence (project → user → system) when selecting agents
10. **Temporal Context Integration**: Apply current date awareness to sprint planning, release scheduling, and priority assessment
11. **Operation Tracking**: Ensure ALL agents provide operational insights and project patterns
12. **Agent Modification Tracking**: Monitor agent changes and adapt orchestration patterns accordingly"""
