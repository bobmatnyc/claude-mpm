"""
Claude-PM Init section generator for framework CLAUDE.md.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class ClaudePmInitGenerator(BaseSectionGenerator):
    """Generates the Claude-PM Init section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the claude-pm init section."""
        return """
## C) CLAUDE-PM INIT

### Core Initialization Commands

```bash
# Basic initialization check
claude-pm init

# Complete setup with directory creation
claude-pm init --setup

# Comprehensive verification of agent hierarchy
claude-pm init --verify
```

### 🚨 STARTUP PROTOCOL

**MANDATORY startup sequence for every PM session:**

1. **MANDATORY: Acknowledge Current Date**:
   ```
   "Today is [current date]. Setting temporal context for project planning and prioritization."
   ```

2. **MANDATORY: Verify claude-pm init status**:
   ```bash
   claude-pm init --verify
   ```

3. **MANDATORY: Core System Health Check**:
   ```bash
   python -c "from claude_mpm.core import validate_core_system; validate_core_system()"
   ```

4. **MANDATORY: Agent Registry Health Check**:
   ```bash
   python -c "from claude_mpm.core.agent_registry import AgentRegistry; registry = get_agent_registry(); print(f'Registry health: {registry.health_check()}')"
   ```

5. **MANDATORY: Initialize Core Agents with Registry Discovery**:
   ```
   Agent Registry: Discover available agents and build capability mapping across all directories

   Documentation Agent: Scan project documentation patterns and build operational understanding.

   Version Control Agent: Confirm availability and provide Git status summary.

   Data Engineer Agent: Verify data store connectivity and AI API availability.
   ```

6. **Review active tickets** using PM's direct ai-trackdown interface with date context
7. **Provide status summary** of current tasks, framework health, agent registry status, and core system status
8. **Ask** what specific tasks or framework operations to perform

### Directory Structure and Agent Hierarchy Setup

**Multi-Project Orchestrator Pattern:**

1. **Framework Directory** (`/Users/masa/Projects/claude-multiagent-pm/.claude-mpm/`)
   - Global user agents (shared across all projects)
   - Framework-level configuration

2. **Working Directory** (`$PWD/.claude-mpm/`)
   - Current session configuration
   - Working directory context

3. **Project Directory** (`$PROJECT_ROOT/.claude-mpm/`)
   - Project agents in `agents/`
   - User agents in `agents/user-agents/` with directory precedence
   - Project configuration

### Health Validation and Deployment Procedures

**Framework Health Monitoring:**
```bash
# Check framework protection status
python -c "from claude_mpm.services.health_monitor import HealthMonitor; HealthMonitor().check_framework_health()"

# Validate agent hierarchy
claude-pm init --verify

---"""
