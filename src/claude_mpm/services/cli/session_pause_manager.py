"""Session Pause Manager Service.

WHY: This service creates session pause documents that capture complete conversation
context, git state, todos, and working directory for seamless resume.

DESIGN DECISIONS:
- Three format output (JSON, YAML, Markdown) for different use cases
- Atomic file operations using StateStorage
- Git integration for automatic commits
- Compatible with SessionResumeHelper for resume workflow
- LATEST-SESSION.txt pointer for quick access
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from claude_mpm.core.logger import get_logger
from claude_mpm.storage.state_storage import StateStorage

logger = get_logger(__name__)


class SessionPauseManager:
    """Manages creating pause sessions and capturing state."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize session pause manager.

        Args:
            project_path: Project root path (default: current directory)
        """
        self.project_path = (project_path or Path.cwd()).resolve()
        # Use flattened structure: .claude-mpm/sessions/ instead of sessions/pause/
        self.pause_dir = self.project_path / ".claude-mpm" / "sessions"
        self.pause_dir.mkdir(parents=True, exist_ok=True)
        self.storage = StateStorage(self.pause_dir)

    def create_pause_session(
        self,
        message: Optional[str] = None,
        skip_commit: bool = False,
        export_path: Optional[str] = None,
    ) -> str:
        """Create a pause session with captured state.

        Args:
            message: Optional pause reason/context message
            skip_commit: Skip git commit of session state
            export_path: Optional export location for session file

        Returns:
            Session ID

        Raises:
            Exception: If session creation fails
        """
        logger.info("Creating pause session")

        # Generate session ID
        session_id = f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Capture state
        state = self._capture_state(session_id, message)

        # Save JSON format
        json_path = self.pause_dir / f"{session_id}.json"
        if not self.storage.write_json(state, json_path, atomic=True):
            raise RuntimeError(f"Failed to write JSON to {json_path}")
        logger.debug(f"Saved JSON: {json_path}")

        # Save YAML format
        yaml_path = self.pause_dir / f"{session_id}.yaml"
        self._save_yaml(state, yaml_path)
        logger.debug(f"Saved YAML: {yaml_path}")

        # Save Markdown format
        md_path = self.pause_dir / f"{session_id}.md"
        md_content = self._generate_markdown(state)
        md_path.write_text(md_content)
        logger.debug(f"Saved Markdown: {md_path}")

        # Update LATEST-SESSION.txt pointer
        self._update_latest_pointer(session_id)

        # Optional export
        if export_path:
            export_file = Path(export_path).resolve()
            if not self.storage.write_json(state, export_file, atomic=True):
                logger.warning(f"Failed to export to {export_file}")
            else:
                logger.info(f"Exported session to {export_file}")

        # Optional git commit
        if not skip_commit and self._is_git_repo():
            self._commit_pause_session(session_id, message)

        logger.info(f"Pause session created: {session_id}")
        return session_id

    def _capture_state(self, session_id: str, message: Optional[str]) -> Dict[str, Any]:
        """Capture current session state.

        Args:
            session_id: Session identifier
            message: Optional context message

        Returns:
            Complete state dictionary
        """
        # Get git context
        git_context = self._get_git_context()

        # Build state dictionary
        return {
            "session_id": session_id,
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "duration_hours": 0,  # Can be calculated if session start time known
            "context_usage": {
                "tokens_used": 0,  # Would need Claude API integration
                "tokens_total": 200000,
                "percentage": 0,
            },
            "conversation": {
                "primary_task": "Manual pause - see message below",
                "current_phase": "In progress",
                "summary": message or "No summary provided",
                "accomplishments": [],
                "next_steps": [],
            },
            "git_context": git_context,
            "active_context": {
                "working_directory": str(self.project_path),
            },
            "important_reminders": [],
            "resume_instructions": {
                "quick_start": [
                    f"Read {session_id}.md for full context",
                    "Run: git status to check current state",
                    "Run: cat .claude-mpm/sessions/LATEST-SESSION.txt",
                ],
                "files_to_review": [],
                "validation_commands": {
                    "check_git": "git status && git log -1 --stat",
                    "check_session": f"cat .claude-mpm/sessions/{session_id}.md",
                },
            },
            "open_questions": [],
            "performance_metrics": {},
            "todos": {"active": [], "completed": []},
            "version": self._get_project_version(),
            "build": "current",
            "project_path": str(self.project_path),
        }

    def _get_git_context(self) -> Dict[str, Any]:
        """Get git repository context.

        Returns:
            Git context dictionary
        """
        if not self._is_git_repo():
            return {
                "is_git_repo": False,
                "branch": None,
                "recent_commits": [],
                "status": {
                    "clean": True,
                    "modified_files": [],
                    "untracked_files": [],
                },
            }

        try:
            # Get current branch
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            # Get recent commits (last 5)
            commit_log = subprocess.check_output(
                ["git", "log", "-5", "--pretty=format:%h|%an|%ai|%s"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            recent_commits = []
            for line in commit_log.split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        recent_commits.append(
                            {
                                "sha": parts[0],
                                "author": parts[1],
                                "timestamp": parts[2],
                                "message": parts[3],
                            }
                        )

            # Get status
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            modified_files = []
            untracked_files = []
            if status_output:
                for line in status_output.split("\n"):
                    if line.startswith("??"):
                        untracked_files.append(line[3:])
                    elif line:
                        modified_files.append(line[3:])

            return {
                "is_git_repo": True,
                "branch": branch,
                "recent_commits": recent_commits,
                "status": {
                    "clean": len(modified_files) == 0 and len(untracked_files) == 0,
                    "modified_files": modified_files,
                    "untracked_files": untracked_files,
                },
            }

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command failed: {e}")
            return {
                "is_git_repo": True,
                "branch": "unknown",
                "recent_commits": [],
                "status": {"clean": True, "modified_files": [], "untracked_files": []},
            }

    def _is_git_repo(self) -> bool:
        """Check if directory is a git repository.

        Returns:
            True if git repository exists
        """
        return (self.project_path / ".git").exists()

    def _save_yaml(self, state: Dict[str, Any], yaml_path: Path) -> None:
        """Save state as YAML format.

        Args:
            state: State dictionary
            yaml_path: Target YAML file path
        """
        try:
            with yaml_path.open("w") as f:
                yaml.dump(
                    state,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
        except Exception as e:
            logger.error(f"Failed to write YAML to {yaml_path}: {e}")
            raise

    def _generate_markdown(self, state: Dict[str, Any]) -> str:
        """Generate human-readable markdown format.

        Args:
            state: State dictionary

        Returns:
            Markdown formatted string
        """
        session_id = state["session_id"]
        paused_at = state["paused_at"]
        conversation = state["conversation"]
        git_context = state["git_context"]
        active_context = state["active_context"]

        lines = [
            "# Claude MPM Session Pause Document",
            "",
            "## Session Metadata",
            "",
            f"**Session ID**: `{session_id}`",
            f"**Paused At**: {paused_at}",
            f"**Project**: `{state['project_path']}`",
            f"**Version**: {state.get('version', 'unknown')}",
            "",
            "## What You Were Working On",
            "",
            f"**Primary Task**: {conversation['primary_task']}",
            f"**Current Phase**: {conversation['current_phase']}",
            "",
            "**Summary**:",
            f"{conversation['summary']}",
            "",
        ]

        # Accomplishments
        if conversation.get("accomplishments"):
            lines.append("## Accomplishments This Session")
            lines.append("")
            for item in conversation["accomplishments"]:
                lines.append(f"- {item}")
            lines.append("")

        # Next steps
        if conversation.get("next_steps"):
            lines.append("## Next Steps (Priority Order)")
            lines.append("")
            for i, step in enumerate(conversation["next_steps"], 1):
                if isinstance(step, dict):
                    lines.append(
                        f"{i}. **{step.get('task', 'Unknown task')}** (Priority: {step.get('priority', '?')})"
                    )
                    if step.get("estimated_hours"):
                        lines.append(f"   - Est. time: {step['estimated_hours']}")
                    if step.get("status"):
                        lines.append(f"   - Status: {step['status']}")
                    if step.get("notes"):
                        lines.append(f"   - Notes: {step['notes']}")
                else:
                    lines.append(f"{i}. {step}")
            lines.append("")

        # Active context
        lines.extend(
            [
                "## Active Context",
                "",
                f"**Working Directory**: `{active_context['working_directory']}`",
                "",
            ]
        )

        # Git context
        lines.append("## Git Context")
        lines.append("")
        if git_context["is_git_repo"]:
            lines.append(f"**Branch**: `{git_context['branch']}`")
            lines.append(
                f"**Status**: {'Clean' if git_context['status']['clean'] else 'Modified'}"
            )
            lines.append("")

            if git_context["status"]["modified_files"]:
                lines.append("**Modified files**:")
                for f in git_context["status"]["modified_files"][:10]:
                    lines.append(f"- `{f}`")
                lines.append("")

            if git_context["recent_commits"]:
                lines.append("**Recent commits**:")
                for commit in git_context["recent_commits"]:
                    lines.append(
                        f"- `{commit['sha']}` - {commit['message']} ({commit['author']})"
                    )
                lines.append("")
        else:
            lines.append("*Not a git repository*")
            lines.append("")

        # Important reminders
        if state.get("important_reminders"):
            lines.append("## Important Reminders")
            lines.append("")
            for reminder in state["important_reminders"]:
                lines.append(f"- {reminder}")
            lines.append("")

        # Resume instructions
        lines.extend(
            [
                "## Resume Instructions",
                "",
                "### Quick Resume (5 minutes)",
                "",
            ]
        )
        for instruction in state["resume_instructions"]["quick_start"]:
            lines.append(f"1. {instruction}")
        lines.append("")

        if state["resume_instructions"]["validation_commands"]:
            lines.append("### Validation Commands")
            lines.append("")
            lines.append("```bash")
            for cmd in state["resume_instructions"]["validation_commands"].values():
                lines.append(cmd)
            lines.append("```")
            lines.append("")

        # Footer
        lines.extend(
            [
                "---",
                "",
                "Resume with: `/mpm-init resume` or `cat .claude-mpm/sessions/LATEST-SESSION.txt`",
                "",
            ]
        )

        return "\n".join(lines)

    def _update_latest_pointer(self, session_id: str) -> None:
        """Update LATEST-SESSION.txt pointer.

        Args:
            session_id: Session identifier
        """
        try:
            latest_file = self.pause_dir / "LATEST-SESSION.txt"
            content = f"""Latest Session: {session_id}
Paused At: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")}
Project: {self.project_path}

Files:
- {session_id}.json (machine-readable)
- {session_id}.yaml (human-readable config)
- {session_id}.md (documentation)

Quick Resume:
  /mpm-init resume

Full Context:
  cat .claude-mpm/sessions/{session_id}.md

Validation:
  git status && git log -1 --stat
"""
            latest_file.write_text(content)
            logger.debug(f"Updated LATEST-SESSION.txt: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update LATEST-SESSION.txt: {e}")

    def _commit_pause_session(self, session_id: str, message: Optional[str]) -> None:
        """Create git commit for pause session.

        Args:
            session_id: Session identifier
            message: Optional context message
        """
        try:
            # Add session files
            subprocess.run(
                ["git", "add", ".claude-mpm/sessions/"],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )

            # Build commit message
            commit_msg = f"session: pause at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\nSession ID: {session_id}"
            if message:
                commit_msg += f"\nContext: {message}"

            # Create commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )

            logger.info(f"Created git commit for pause session: {session_id}")

        except subprocess.CalledProcessError as e:
            # Non-fatal - pause still succeeded
            logger.warning(f"Failed to create git commit: {e.stderr.decode()}")

    def _get_project_version(self) -> str:
        """Get project version from pyproject.toml or package.

        Returns:
            Version string or 'unknown'
        """
        try:
            # Try pyproject.toml
            pyproject = self.project_path / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                for line in content.split("\n"):
                    if line.startswith("version"):
                        return line.split("=")[1].strip().strip('"')

            # Try package __version__
            import claude_mpm

            if hasattr(claude_mpm, "__version__"):
                return claude_mpm.__version__

        except Exception:
            pass

        return "unknown"
