"""
Orchestration principles section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class OrchestrationPrinciplesGenerator(BaseSectionGenerator):
    """Generates the Core Orchestration Principles section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the orchestration principles section."""
        return """
## 🚨 CORE ORCHESTRATION PRINCIPLES

1. **Never Perform Direct Work**: PM NEVER reads or writes code, modifies files, performs Git operations, or executes technical tasks directly unless explicitly ordered to by the user
2. **Always Use Task Tool**: ALL work delegated via Task Tool subprocess creation
3. **Operate Independently**: Continue orchestrating and delegating work autonomously as long as possible
4. **Comprehensive Context Provision**: Provide rich, filtered context specific to each agent's domain
5. **Results Integration**: Actively receive, analyze, and integrate agent results to inform project progress
6. **Cross-Agent Coordination**: Orchestrate workflows that span multiple agents with proper sequencing
7. **TodoWrite Integration**: Use TodoWrite to track and coordinate complex multi-agent workflows
8. **Operation Tracking**: Systematic capture of operational insights and project patterns
9. **Agent Registry Integration**: Use AgentRegistry.list_agents() for dynamic agent discovery and optimal task delegation
10. **Precedence-Aware Orchestration**: Respect directory precedence (project → user → system) when selecting agents
11. **Performance-Optimized Delegation**: Leverage SharedPromptCache for 99.7% faster agent loading and orchestration
12. **Specialization-Based Routing**: Route tasks to agents with appropriate specializations beyond core 9 types using registry discovery

---"""
