"""Minimal framework loader for better performance."""

import contextlib
from pathlib import Path
from typing import Optional

try:
    from ..core.logger import get_logger
except ImportError:
    from core.logger import get_logger


class MinimalFrameworkLoader:
    """Load a minimal framework for non-interactive mode."""

    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
    ):
        """Initialize the minimal loader."""
        self.logger = get_logger("minimal_framework_loader")
        self.framework_path = framework_path or self._detect_framework_path()
        self.agents_dir = agents_dir

    def _detect_framework_path(self) -> Optional[Path]:
        """Detect the claude-mpm framework path."""
        # Same detection logic as main loader
        candidates = [
            Path.cwd() / "claude-mpm",
            Path.cwd().parent / "claude-mpm",
            Path.home() / "Projects" / "claude-mpm",
        ]

        for candidate in candidates:
            if candidate.exists() and (candidate / "src").exists():
                return candidate

        return None

    def get_framework_instructions(self) -> str:
        """Get minimal framework instructions."""
        # Load working directory INSTRUCTIONS.md (or legacy CLAUDE.md) if exists
        working_claude = ""
        working_instructions_path = Path.cwd() / "INSTRUCTIONS.md"
        working_claude_path = Path.cwd() / "CLAUDE.md"  # Legacy support

        if working_instructions_path.exists():
            with contextlib.suppress(Exception):
                working_claude = working_instructions_path.read_text()
        elif working_claude_path.exists():
            with contextlib.suppress(Exception):
                working_claude = working_claude_path.read_text()

        # Build minimal framework
        framework = """# Claude MPM Framework

You are a multi-agent orchestrator in the Claude MPM framework.

## Core Responsibilities
1. **Orchestrate** - Delegate ALL implementation work to specialized agents via Task Tool
2. **Coordinate** - Manage multi-agent workflows and cross-agent collaboration
3. **Track** - Extract TODO/BUG/FEATURE items for ticket creation
4. **Oversee** - Maintain project visibility and strategic oversight
5. **Never Implement** - You NEVER write code or perform direct implementation

## Available Agents
- **Engineer Agent**: Code implementation and development
- **QA Agent**: Testing and quality assurance
- **Documentation Agent**: Documentation and changelogs
- **Research Agent**: Investigation and analysis
- **Security Agent**: Security analysis and protection
- **Version Control Agent**: Git operations and version management
- **Ops Agent**: Deployment and operations
- **Data Engineer Agent**: Data management and AI API integration

## Task Tool Format
When delegating, use this format:
```
**[Agent Name]**: [Clear task description]

**Task**: [Detailed breakdown]
**Context**: [Relevant context]
**Expected Results**: [Specific deliverables]
```

## Ticket Patterns
Extract from: TODO:, BUG:, FEATURE:, ISSUE:

"""

        # Add working directory instructions if present
        if working_claude:
            framework += f"\n## Working Directory Instructions\n{working_claude}\n"

        return framework

    def get_agent_list(self) -> list:
        """Get list of available agents."""
        return [
            "engineer",
            "qa",
            "documentation",
            "research",
            "security",
            "version_control",
            "ops",
            "data_engineer",
        ]
