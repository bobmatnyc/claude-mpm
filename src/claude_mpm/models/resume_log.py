"""Resume Log Data Model.

This module defines the data structure for session resume logs that enable
seamless context restoration when Claude hits token limits.

Design Philosophy:
- Target 10k tokens maximum per resume log
- Human-readable markdown format
- Structured sections with token budgets
- Optimized for Claude consumption on session resume
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ContextMetrics:
    """Context window usage metrics."""

    total_budget: int = 200000
    used_tokens: int = 0
    remaining_tokens: int = 0
    percentage_used: float = 0.0
    stop_reason: Optional[str] = None
    model: str = "claude-sonnet-4.5"
    session_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_budget": self.total_budget,
            "used_tokens": self.used_tokens,
            "remaining_tokens": self.remaining_tokens,
            "percentage_used": self.percentage_used,
            "stop_reason": self.stop_reason,
            "model": self.model,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextMetrics":
        """Create from dictionary."""
        return cls(
            total_budget=data.get("total_budget", 200000),
            used_tokens=data.get("used_tokens", 0),
            remaining_tokens=data.get("remaining_tokens", 0),
            percentage_used=data.get("percentage_used", 0.0),
            stop_reason=data.get("stop_reason"),
            model=data.get("model", "claude-sonnet-4.5"),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ResumeLog:
    """Resume log containing all information needed to restore session context.

    Token Budget Distribution (10k tokens total):
    - Context Metrics: 500 tokens
    - Mission Summary: 1,000 tokens
    - Accomplishments: 2,000 tokens
    - Key Findings: 2,500 tokens
    - Decisions & Rationale: 1,500 tokens
    - Next Steps: 1,500 tokens
    - Critical Context: 1,000 tokens
    """

    # Session identification
    session_id: str
    previous_session_id: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Context metrics
    context_metrics: ContextMetrics = field(default_factory=ContextMetrics)

    # Core content sections (with token budgets)
    mission_summary: str = ""  # 1,000 tokens - What was the overall goal?
    accomplishments: List[str] = field(
        default_factory=list
    )  # 2,000 tokens - What was completed?
    key_findings: List[str] = field(
        default_factory=list
    )  # 2,500 tokens - What was discovered?
    decisions_made: List[Dict[str, str]] = field(
        default_factory=list
    )  # 1,500 tokens - What choices were made and why?
    next_steps: List[str] = field(
        default_factory=list
    )  # 1,500 tokens - What needs to happen next?
    critical_context: Dict[str, Any] = field(
        default_factory=dict
    )  # 1,000 tokens - Essential state/data

    # Metadata
    files_modified: List[str] = field(default_factory=list)
    agents_used: Dict[str, int] = field(default_factory=dict)
    errors_encountered: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Generate markdown format for Claude consumption.

        Returns:
            Markdown-formatted resume log
        """
        sections = []

        # Header
        sections.append(f"# Session Resume Log: {self.session_id}\n")
        sections.append(f"**Created**: {self.created_at}")
        if self.previous_session_id:
            sections.append(f"**Previous Session**: {self.previous_session_id}")
        sections.append("")

        # Context Metrics (500 tokens)
        sections.append("## Context Metrics\n")
        sections.append(f"- **Model**: {self.context_metrics.model}")
        sections.append(
            f"- **Tokens Used**: {self.context_metrics.used_tokens:,} / {self.context_metrics.total_budget:,}"
        )
        sections.append(
            f"- **Percentage**: {self.context_metrics.percentage_used:.1f}%"
        )
        sections.append(
            f"- **Remaining**: {self.context_metrics.remaining_tokens:,} tokens"
        )
        if self.context_metrics.stop_reason:
            sections.append(f"- **Stop Reason**: {self.context_metrics.stop_reason}")
        sections.append("")

        # Mission Summary (1,000 tokens)
        sections.append("## Mission Summary\n")
        sections.append(
            self.mission_summary
            if self.mission_summary
            else "_No mission summary provided_"
        )
        sections.append("")

        # Accomplishments (2,000 tokens)
        sections.append("## Accomplishments\n")
        if self.accomplishments:
            for i, item in enumerate(self.accomplishments, 1):
                sections.append(f"{i}. {item}")
        else:
            sections.append("_No accomplishments recorded_")
        sections.append("")

        # Key Findings (2,500 tokens)
        sections.append("## Key Findings\n")
        if self.key_findings:
            for i, finding in enumerate(self.key_findings, 1):
                sections.append(f"{i}. {finding}")
        else:
            sections.append("_No key findings recorded_")
        sections.append("")

        # Decisions & Rationale (1,500 tokens)
        sections.append("## Decisions & Rationale\n")
        if self.decisions_made:
            for i, decision in enumerate(self.decisions_made, 1):
                decision_text = decision.get("decision", "")
                rationale = decision.get("rationale", "")
                sections.append(f"{i}. **Decision**: {decision_text}")
                if rationale:
                    sections.append(f"   **Rationale**: {rationale}")
        else:
            sections.append("_No decisions recorded_")
        sections.append("")

        # Next Steps (1,500 tokens)
        sections.append("## Next Steps\n")
        if self.next_steps:
            for i, step in enumerate(self.next_steps, 1):
                sections.append(f"{i}. {step}")
        else:
            sections.append("_No next steps defined_")
        sections.append("")

        # Critical Context (1,000 tokens)
        sections.append("## Critical Context\n")
        if self.critical_context:
            for key, value in self.critical_context.items():
                sections.append(f"- **{key}**: {value}")
        else:
            sections.append("_No critical context preserved_")
        sections.append("")

        # Metadata
        sections.append("## Session Metadata\n")
        if self.files_modified:
            sections.append(f"**Files Modified** ({len(self.files_modified)}):")
            for file in self.files_modified[:20]:  # Limit to first 20
                sections.append(f"- {file}")
            if len(self.files_modified) > 20:
                sections.append(f"- ... and {len(self.files_modified) - 20} more")
            sections.append("")

        if self.agents_used:
            sections.append("**Agents Used**:")
            for agent, count in self.agents_used.items():
                sections.append(f"- {agent}: {count} delegations")
            sections.append("")

        if self.errors_encountered:
            sections.append(f"**Errors** ({len(self.errors_encountered)}):")
            for error in self.errors_encountered[:5]:  # Limit to first 5
                sections.append(f"- {error}")
            sections.append("")

        if self.warnings:
            sections.append(f"**Warnings** ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Limit to first 5
                sections.append(f"- {warning}")
            sections.append("")

        return "\n".join(sections)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "previous_session_id": self.previous_session_id,
            "created_at": self.created_at,
            "context_metrics": self.context_metrics.to_dict(),
            "mission_summary": self.mission_summary,
            "accomplishments": self.accomplishments,
            "key_findings": self.key_findings,
            "decisions_made": self.decisions_made,
            "next_steps": self.next_steps,
            "critical_context": self.critical_context,
            "files_modified": self.files_modified,
            "agents_used": self.agents_used,
            "errors_encountered": self.errors_encountered,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeLog":
        """Create from dictionary."""
        context_metrics_data = data.get("context_metrics", {})
        context_metrics = ContextMetrics.from_dict(context_metrics_data)

        return cls(
            session_id=data.get("session_id", ""),
            previous_session_id=data.get("previous_session_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            context_metrics=context_metrics,
            mission_summary=data.get("mission_summary", ""),
            accomplishments=data.get("accomplishments", []),
            key_findings=data.get("key_findings", []),
            decisions_made=data.get("decisions_made", []),
            next_steps=data.get("next_steps", []),
            critical_context=data.get("critical_context", {}),
            files_modified=data.get("files_modified", []),
            agents_used=data.get("agents_used", {}),
            errors_encountered=data.get("errors_encountered", []),
            warnings=data.get("warnings", []),
        )

    def save(self, storage_dir: Optional[Path] = None) -> Path:
        """Save resume log to markdown file.

        Args:
            storage_dir: Directory to save the log (default: .claude-mpm/resume-logs)

        Returns:
            Path to saved file
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".claude-mpm" / "resume-logs"

        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        file_path = storage_dir / f"session-{self.session_id}.md"

        try:
            # Write markdown file
            markdown_content = self.to_markdown()
            file_path.write_text(markdown_content, encoding="utf-8")

            logger.info(f"Resume log saved: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save resume log: {e}")
            raise

    @classmethod
    def load(
        cls, session_id: str, storage_dir: Optional[Path] = None
    ) -> Optional["ResumeLog"]:
        """Load resume log from file.

        Args:
            session_id: Session ID to load
            storage_dir: Directory to load from (default: .claude-mpm/resume-logs)

        Returns:
            ResumeLog instance or None if not found
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".claude-mpm" / "resume-logs"

        file_path = storage_dir / f"session-{session_id}.md"

        if not file_path.exists():
            logger.debug(f"Resume log not found: {file_path}")
            return None

        try:
            # For now, we just return the markdown content
            # In the future, could parse markdown back to structured data
            _ = file_path.read_text(encoding="utf-8")
            logger.info(f"Resume log loaded: {file_path}")

            # Return a basic ResumeLog with the markdown content embedded
            return cls(
                session_id=session_id,
                mission_summary=f"Loaded from previous session. See full context in {file_path}",
            )

        except Exception as e:
            logger.error(f"Failed to load resume log: {e}")
            return None
