from pathlib import Path

"""State Manager service for capturing and restoring execution state.

This service handles comprehensive state management for Claude Code,
enabling seamless restarts with preserved context.

Design Principles:
- Atomic state operations with write-to-temp-then-rename
- Automatic cleanup of old state files
- Privacy-preserving (sanitizes sensitive data)
- Platform-agnostic implementation
- Graceful degradation on failures
"""

import asyncio
import gzip
import json
import os
import pickle
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.models.state_models import (
    CompleteState,
    ConversationContext,
    ConversationState,
    ProcessState,
    ProjectState,
    RestartState,
    StateType,
)
from claude_mpm.services.core.base import BaseService
from claude_mpm.utils.platform_memory import get_process_memory


class StateManager(BaseService):
    """Service for managing Claude Code execution state across restarts."""

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize State Manager service.

        Args:
            state_dir: Directory for storing state files (default: ~/.claude-mpm/state)
        """
        super().__init__("StateManager")

        # State storage configuration
        self.state_dir = state_dir or Path.home() / ".claude-mpm" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # File naming
        self.current_state_file = self.state_dir / "current_state.json"
        self.compressed_state_file = self.state_dir / "current_state.json.gz"

        # Retention policy
        self.retention_days = 7
        self.max_state_files = 50

        # Claude conversation paths
        self.claude_config_dir = Path.home() / ".claude"
        self.claude_json_path = self.claude_config_dir / ".claude.json"

        # State tracking
        self.current_state: Optional[CompleteState] = None
        self.last_capture_time: float = 0
        self.capture_cooldown = 5.0  # Minimum seconds between captures

        # Statistics
        self.capture_count = 0
        self.restore_count = 0
        self.cleanup_count = 0

        self.log_info(
            f"State Manager initialized with state directory: {self.state_dir}"
        )

    async def initialize(self) -> bool:
        """Initialize the State Manager service.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing State Manager service")

            # Ensure state directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Cleanup old states on startup
            await self.cleanup_old_states()

            # Try to load existing state
            loaded_state = await self.load_state()
            if loaded_state:
                self.log_info(f"Loaded existing state: {loaded_state.state_id}")
                self.current_state = loaded_state

            self._initialized = True
            self.log_info("State Manager service initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize State Manager: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the State Manager service gracefully."""
        try:
            self.log_info("Shutting down State Manager service")

            # Capture final state before shutdown
            if self.current_state:
                await self.persist_state(self.current_state)

            self._shutdown = True
            self.log_info("State Manager service shutdown complete")

        except Exception as e:
            self.log_error(f"Error during State Manager shutdown: {e}")

    async def capture_state(
        self, restart_reason: str = "Manual"
    ) -> Optional[CompleteState]:
        """Capture current process and conversation state.

        Args:
            restart_reason: Reason for the state capture/restart

        Returns:
            CompleteState object or None if capture failed
        """
        try:
            # Check cooldown
            if time.time() - self.last_capture_time < self.capture_cooldown:
                self.log_debug("State capture skipped due to cooldown")
                return self.current_state

            self.log_info(f"Capturing state: {restart_reason}")

            # Capture process state
            process_state = await self._capture_process_state()

            # Capture conversation state
            conversation_state = await self._capture_conversation_state()

            # Capture project state
            project_state = await self._capture_project_state()

            # Create restart state
            restart_state = self._create_restart_state(restart_reason, process_state)

            # Create complete state
            state = CompleteState(
                process_state=process_state,
                conversation_state=conversation_state,
                project_state=project_state,
                restart_state=restart_state,
            )

            # Validate state
            issues = state.validate()
            if issues:
                for issue in issues:
                    self.log_warning(f"State validation issue: {issue}")

            # Update tracking
            self.current_state = state
            self.last_capture_time = time.time()
            self.capture_count += 1

            self.log_info(f"State captured successfully: {state.state_id}")
            return state

        except Exception as e:
            self.log_error(f"Failed to capture state: {e}")
            return None

    async def restore_state(self, state: Optional[CompleteState] = None) -> bool:
        """Restore state after process restart.

        Args:
            state: State to restore (default: load from disk)

        Returns:
            True if restoration successful
        """
        try:
            # Load state if not provided
            if state is None:
                state = await self.load_state()
                if state is None:
                    self.log_warning("No state available to restore")
                    return False

            self.log_info(f"Restoring state: {state.state_id}")

            # Restore working directory
            if state.process_state.working_directory:
                try:
                    os.chdir(state.process_state.working_directory)
                    self.log_debug(
                        f"Restored working directory: {state.process_state.working_directory}"
                    )
                except Exception as e:
                    self.log_warning(f"Could not restore working directory: {e}")

            # Restore environment variables (non-sensitive only)
            for key, value in state.process_state.environment.items():
                if value != "***REDACTED***":
                    os.environ[key] = value

            # Restore project-specific environment
            if state.project_state.environment_vars:
                for key, value in state.project_state.environment_vars.items():
                    if value != "***REDACTED***":
                        os.environ[key] = value

            # Log restoration summary
            self.log_info(f"State restoration complete:")
            self.log_info(
                f"  - Working directory: {state.process_state.working_directory}"
            )
            self.log_info(f"  - Git branch: {state.project_state.git_branch}")
            self.log_info(f"  - Open files: {len(state.conversation_state.open_files)}")
            self.log_info(
                f"  - Active conversation: {state.conversation_state.active_conversation_id}"
            )

            self.restore_count += 1
            return True

        except Exception as e:
            self.log_error(f"Failed to restore state: {e}")
            return False

    async def persist_state(self, state: CompleteState, compress: bool = True) -> bool:
        """Save state to disk atomically.

        Args:
            state: State to persist
            compress: Whether to compress the state file

        Returns:
            True if persistence successful
        """
        try:
            self.log_debug(f"Persisting state: {state.state_id}")

            # Convert state to dictionary
            state_dict = state.to_dict()

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.state_dir, suffix=".tmp", prefix="state_"
            )

            try:
                # Write state to temporary file
                if compress:
                    # Write compressed JSON
                    with gzip.open(temp_path, "wt", encoding="utf-8") as f:
                        json.dump(state_dict, f, indent=2)
                    target_path = self.compressed_state_file
                else:
                    # Write plain JSON
                    with os.fdopen(temp_fd, "w") as f:
                        json.dump(state_dict, f, indent=2)
                    target_path = self.current_state_file

                # Atomic rename
                temp_path_obj = Path(temp_path)
                temp_path_obj.replace(target_path)

                # Also create timestamped backup
                backup_name = f"state_{state.state_id}.json"
                if compress:
                    backup_name += ".gz"
                backup_path = self.state_dir / backup_name
                shutil.copy2(target_path, backup_path)

                self.log_debug(f"State persisted to {target_path}")
                return True

            finally:
                # Clean up temp file if it still exists
                if Path(temp_path).exists():
                    os.unlink(temp_path)

        except Exception as e:
            self.log_error(f"Failed to persist state: {e}")
            return False

    async def load_state(
        self, state_file: Optional[Path] = None
    ) -> Optional[CompleteState]:
        """Load state from disk with validation.

        Args:
            state_file: Path to state file (default: current_state.json[.gz])

        Returns:
            CompleteState object or None if load failed
        """
        try:
            # Determine which file to load
            if state_file is None:
                if self.compressed_state_file.exists():
                    state_file = self.compressed_state_file
                elif self.current_state_file.exists():
                    state_file = self.current_state_file
                else:
                    self.log_debug("No state file found")
                    return None

            self.log_debug(f"Loading state from {state_file}")

            # Read state file
            if str(state_file).endswith(".gz"):
                with gzip.open(state_file, "rt", encoding="utf-8") as f:
                    state_dict = json.load(f)
            else:
                with open(state_file, "r") as f:
                    state_dict = json.load(f)

            # Create state object
            state = CompleteState.from_dict(state_dict)

            # Validate state
            issues = state.validate()
            if issues:
                for issue in issues:
                    self.log_warning(f"State validation issue: {issue}")

            self.log_info(f"Loaded state: {state.state_id}")
            return state

        except Exception as e:
            self.log_error(f"Failed to load state: {e}")
            return None

    async def cleanup_old_states(self) -> int:
        """Remove states older than retention period.

        Returns:
            Number of files removed
        """
        try:
            self.log_debug("Cleaning up old state files")

            removed_count = 0
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)

            # Find all state files
            state_files = list(self.state_dir.glob("state_*.json*"))

            # Sort by modification time
            state_files.sort(key=lambda f: f.stat().st_mtime)

            # Remove old files
            for state_file in state_files:
                try:
                    # Check age
                    file_time = datetime.fromtimestamp(state_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        state_file.unlink()
                        removed_count += 1
                        self.log_debug(f"Removed old state file: {state_file.name}")
                except Exception as e:
                    self.log_warning(f"Could not remove state file {state_file}: {e}")

            # Also enforce max file limit
            remaining_files = list(self.state_dir.glob("state_*.json*"))
            if len(remaining_files) > self.max_state_files:
                # Remove oldest files
                remaining_files.sort(key=lambda f: f.stat().st_mtime)
                for state_file in remaining_files[: -self.max_state_files]:
                    try:
                        state_file.unlink()
                        removed_count += 1
                        self.log_debug(f"Removed excess state file: {state_file.name}")
                    except Exception as e:
                        self.log_warning(
                            f"Could not remove state file {state_file}: {e}"
                        )

            if removed_count > 0:
                self.log_info(f"Cleaned up {removed_count} old state files")

            self.cleanup_count += removed_count
            return removed_count

        except Exception as e:
            self.log_error(f"Error during state cleanup: {e}")
            return 0

    async def get_conversation_context(self) -> Optional[ConversationState]:
        """Extract relevant Claude conversation data.

        Returns:
            ConversationState object or None if extraction failed
        """
        try:
            # Check if Claude config exists
            if not self.claude_json_path.exists():
                self.log_debug("Claude configuration not found")
                return ConversationState(
                    active_conversation_id=None,
                    active_conversation=None,
                    recent_conversations=[],
                    total_conversations=0,
                    total_storage_mb=0.0,
                    preferences={},
                    open_files=[],
                    recent_files=[],
                    pinned_files=[],
                )

            # Get file size
            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

            # For large files, use streaming approach
            if file_size_mb > 100:
                self.log_warning(
                    f"Large Claude config file ({file_size_mb:.2f}MB), using minimal extraction"
                )
                return self._extract_minimal_conversation_state()

            # Load Claude configuration
            with open(self.claude_json_path, "r") as f:
                claude_data = json.load(f)

            # Extract conversation information
            conversations = claude_data.get("conversations", [])
            active_conv_id = claude_data.get("activeConversationId")

            # Find active conversation
            active_conv = None
            if active_conv_id:
                for conv in conversations:
                    if conv.get("id") == active_conv_id:
                        active_conv = ConversationContext(
                            conversation_id=conv.get("id", ""),
                            title=conv.get("title", "Untitled"),
                            created_at=conv.get("createdAt", 0),
                            updated_at=conv.get("updatedAt", 0),
                            message_count=len(conv.get("messages", [])),
                            total_tokens=conv.get("totalTokens", 0),
                            max_tokens=conv.get("maxTokens", 100000),
                            referenced_files=self._extract_referenced_files(conv),
                            open_tabs=conv.get("openTabs", []),
                            tags=conv.get("tags", []),
                            is_active=True,
                        )
                        break

            # Get recent conversations (last 5)
            recent_convs = []
            sorted_convs = sorted(
                conversations, key=lambda c: c.get("updatedAt", 0), reverse=True
            )[:5]

            for conv in sorted_convs:
                if conv.get("id") != active_conv_id:
                    recent_convs.append(
                        ConversationContext(
                            conversation_id=conv.get("id", ""),
                            title=conv.get("title", "Untitled"),
                            created_at=conv.get("createdAt", 0),
                            updated_at=conv.get("updatedAt", 0),
                            message_count=len(conv.get("messages", [])),
                            total_tokens=conv.get("totalTokens", 0),
                            max_tokens=conv.get("maxTokens", 100000),
                            referenced_files=self._extract_referenced_files(conv),
                            open_tabs=conv.get("openTabs", []),
                            tags=conv.get("tags", []),
                            is_active=False,
                        )
                    )

            # Extract preferences
            preferences = claude_data.get("preferences", {})

            # Extract file state
            open_files = claude_data.get("openFiles", [])
            recent_files = claude_data.get("recentFiles", [])
            pinned_files = claude_data.get("pinnedFiles", [])

            return ConversationState(
                active_conversation_id=active_conv_id,
                active_conversation=active_conv,
                recent_conversations=recent_convs,
                total_conversations=len(conversations),
                total_storage_mb=file_size_mb,
                preferences=preferences,
                open_files=open_files,
                recent_files=recent_files,
                pinned_files=pinned_files,
            )

        except Exception as e:
            self.log_error(f"Failed to extract conversation context: {e}")
            return None

    async def _capture_process_state(self) -> ProcessState:
        """Capture current process state."""
        try:
            pid = os.getpid()

            # Get memory info
            mem_info = get_process_memory(pid)
            memory_mb = mem_info.rss_mb if mem_info else 0.0
            cpu_percent = 0.0  # Would need psutil for accurate CPU%

            # Get command line
            if platform.system() != "Windows":
                try:
                    with open(f"/proc/{pid}/cmdline", "r") as f:
                        cmdline = f.read().replace("\0", " ").strip().split()
                except:
                    cmdline = sys.argv
            else:
                cmdline = sys.argv

            # Get open files (simplified - would need lsof or psutil for full list)
            open_files = []

            return ProcessState(
                pid=pid,
                parent_pid=os.getppid(),
                process_name=os.path.basename(sys.executable),
                command=cmdline[:1] if cmdline else [],
                args=cmdline[1:] if len(cmdline) > 1 else [],
                working_directory=os.getcwd(),
                environment=dict(os.environ),
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                open_files=open_files,
                start_time=time.time() - time.process_time(),
                capture_time=time.time(),
            )

        except Exception as e:
            self.log_error(f"Error capturing process state: {e}")
            # Return minimal state
            return ProcessState(
                pid=os.getpid(),
                parent_pid=os.getppid(),
                process_name="claude-mpm",
                command=sys.argv[:1],
                args=sys.argv[1:],
                working_directory=os.getcwd(),
                environment={},
                memory_mb=0.0,
                cpu_percent=0.0,
                open_files=[],
                start_time=time.time(),
                capture_time=time.time(),
            )

    async def _capture_conversation_state(self) -> ConversationState:
        """Capture conversation state from Claude."""
        conversation_state = await self.get_conversation_context()
        return conversation_state or ConversationState(
            active_conversation_id=None,
            active_conversation=None,
            recent_conversations=[],
            total_conversations=0,
            total_storage_mb=0.0,
            preferences={},
            open_files=[],
            recent_files=[],
            pinned_files=[],
        )

    async def _capture_project_state(self) -> ProjectState:
        """Capture project and Git state."""
        try:
            project_path = os.getcwd()
            project_name = os.path.basename(project_path)

            # Get Git information
            git_branch = None
            git_commit = None
            git_status = {}
            git_remotes = {}

            try:
                # Get current branch
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                )
                if result.returncode == 0:
                    git_branch = result.stdout.strip()

                # Get current commit
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                )
                if result.returncode == 0:
                    git_commit = result.stdout.strip()[:8]

                # Get status
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                )
                if result.returncode == 0:
                    staged = []
                    modified = []
                    untracked = []

                    for line in result.stdout.splitlines():
                        if line.startswith("??"):
                            untracked.append(line[3:])
                        elif line.startswith(" M"):
                            modified.append(line[3:])
                        elif line.startswith("M "):
                            staged.append(line[3:])

                    git_status = {
                        "staged": staged,
                        "modified": modified,
                        "untracked": untracked,
                    }

            except Exception as e:
                self.log_debug(f"Could not get Git information: {e}")

            # Detect project type
            project_type = self._detect_project_type(project_path)

            return ProjectState(
                project_path=project_path,
                project_name=project_name,
                git_branch=git_branch,
                git_commit=git_commit,
                git_status=git_status,
                git_remotes=git_remotes,
                modified_files=git_status.get("modified", []),
                open_editors=[],
                breakpoints={},
                project_type=project_type,
                dependencies={},
                environment_vars={},
                last_build_status=None,
                last_test_results=None,
            )

        except Exception as e:
            self.log_error(f"Error capturing project state: {e}")
            return ProjectState(
                project_path=os.getcwd(),
                project_name=os.path.basename(os.getcwd()),
                git_branch=None,
                git_commit=None,
                git_status={},
                git_remotes={},
                modified_files=[],
                open_editors=[],
                breakpoints={},
                project_type="unknown",
                dependencies={},
                environment_vars={},
                last_build_status=None,
                last_test_results=None,
            )

    def _create_restart_state(
        self, reason: str, process_state: ProcessState
    ) -> RestartState:
        """Create restart state information."""
        return RestartState(
            restart_id=str(uuid.uuid4()),
            restart_count=self.capture_count,
            timestamp=time.time(),
            previous_uptime=time.time() - process_state.start_time,
            reason=reason,
            trigger="manual",  # Will be updated by caller
            memory_mb=process_state.memory_mb,
            memory_limit_mb=2048.0,  # Default limit
            cpu_percent=process_state.cpu_percent,
            error_type=None,
            error_message=None,
            error_traceback=None,
            recovery_attempted=True,
            recovery_successful=False,  # Will be updated after restore
            data_preserved=["process", "conversation", "project"],
        )

    def _extract_referenced_files(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract file references from conversation."""
        files = set()

        # Extract from messages
        for message in conversation.get("messages", []):
            content = message.get("content", "")
            # Simple extraction - could be enhanced with regex
            if isinstance(content, str):
                # Look for file paths
                import re

                file_pattern = r'[\'"`]([^\'"`]+\.[a-zA-Z0-9]+)[\'"`]'
                matches = re.findall(file_pattern, content)
                files.update(matches)

        return list(files)[:100]  # Limit to prevent huge lists

    def _extract_minimal_conversation_state(self) -> ConversationState:
        """Extract minimal conversation state for large files."""
        try:
            # Just get basic metadata without loading full file
            file_size_mb = self.claude_json_path.stat().st_size / (1024 * 1024)

            return ConversationState(
                active_conversation_id="large_file",
                active_conversation=None,
                recent_conversations=[],
                total_conversations=-1,  # Unknown
                total_storage_mb=file_size_mb,
                preferences={},
                open_files=[],
                recent_files=[],
                pinned_files=[],
            )
        except:
            return ConversationState(
                active_conversation_id=None,
                active_conversation=None,
                recent_conversations=[],
                total_conversations=0,
                total_storage_mb=0.0,
                preferences={},
                open_files=[],
                recent_files=[],
                pinned_files=[],
            )

    def _detect_project_type(self, project_path: str) -> str:
        """Detect project type from files present."""
        path = Path(project_path)

        if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            return "python"
        elif (path / "package.json").exists():
            return "node"
        elif (path / "go.mod").exists():
            return "go"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "pom.xml").exists():
            return "java"
        else:
            return "unknown"

    def get_statistics(self) -> Dict[str, Any]:
        """Get state manager statistics.

        Returns:
            Dictionary containing statistics
        """
        state_files = list(self.state_dir.glob("state_*.json*"))
        total_size_mb = sum(f.stat().st_size for f in state_files) / (1024 * 1024)

        return {
            "capture_count": self.capture_count,
            "restore_count": self.restore_count,
            "cleanup_count": self.cleanup_count,
            "state_files": len(state_files),
            "total_size_mb": round(total_size_mb, 2),
            "state_directory": str(self.state_dir),
            "current_state_id": self.current_state.state_id
            if self.current_state
            else None,
            "last_capture_time": self.last_capture_time,
            "retention_days": self.retention_days,
            "max_state_files": self.max_state_files,
        }
