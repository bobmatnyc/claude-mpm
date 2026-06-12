"""Loader for framework instructions and configuration files."""

from pathlib import Path
from typing import Any

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.workflow_loader import load_workflow

from .file_loader import FileLoader
from .packaged_loader import PackagedLoader
from .workflow_constants import MEMORY_SYSTEM_REFERENCE, WORKFLOW_SYSTEM_REFERENCE


class InstructionLoader:
    """Handles loading of INSTRUCTIONS, WORKFLOW, and MEMORY files."""

    def __init__(self, framework_path: Path | None = None):
        """Initialize the instruction loader.

        Args:
            framework_path: Path to framework installation
        """
        self.logger = get_logger("instruction_loader")
        self.framework_path = framework_path
        self.file_loader = FileLoader()
        self.packaged_loader = PackagedLoader()
        self.current_dir = Path.cwd()

    def load_all_instructions(self, content: dict[str, Any]) -> None:
        """Load all instruction files into the content dictionary.

        WORKFLOW.md is lazy-loaded: instead of embedding the full ~1,150-token
        document in every session's system prompt, we inject a single-line
        reference.  The PM can Read the file on demand via the Read tool when it
        needs full phase detail for a complex task.  Project-level or user-level
        WORKFLOW.md overrides are still embedded verbatim (they are smaller and
        project-specific, so the cost is justified).

        Args:
            content: Dictionary to update with loaded instructions
        """
        # Load custom INSTRUCTIONS.md
        self.load_custom_instructions(content)

        # Load framework instructions
        self.load_framework_instructions(content)

        # Load AGENT_DELEGATION.md (after framework, before workflow)
        self.load_agent_delegation_instructions(content)

        # Load WORKFLOW.md — system-level is lazy (reference only); project/user
        # overrides are loaded verbatim so project customisations are honoured.
        self.load_workflow_instructions(content)

        # Load MEMORY.md (with memory backend auto-injection if applicable)
        self.load_memory_instructions(content)

        # The ``_loaded_from_deployed`` sentinel is an internal coordination
        # signal between the loaders above (it makes the subsidiary loaders skip
        # re-appending the system defaults that the merged DEPLOYED file already
        # carries).  All consumers have now run, so drop it: downstream
        # consumers (content_formatter, etc.) iterate ``content`` and must not
        # see this private key leak into the assembled prompt.
        content.pop("_loaded_from_deployed", None)

    def load_custom_instructions(self, content: dict[str, Any]) -> None:
        """Load custom INSTRUCTIONS.md from .claude-mpm directories.

        Args:
            content: Dictionary to update with loaded instructions
        """
        instructions, level = self.file_loader.load_instructions_file(self.current_dir)
        if instructions:
            content["custom_instructions"] = instructions
            content["custom_instructions_level"] = level

    def load_framework_instructions(self, content: dict[str, Any]) -> None:
        """Load framework INSTRUCTIONS.md or PM_INSTRUCTIONS.md.

        Args:
            content: Dictionary to update with framework instructions
        """
        if not self.framework_path:
            return

        # Check if this is a packaged installation
        if self.framework_path == Path("__PACKAGED__"):
            # Use packaged loader
            self.packaged_loader.load_framework_content(content)
        else:
            # Load from filesystem for development mode
            self._load_filesystem_framework_instructions(content)

        # Update framework metadata
        if self.file_loader.framework_version:
            content["instructions_version"] = self.file_loader.framework_version
            content["version"] = self.file_loader.framework_version
        if self.file_loader.framework_last_modified:
            content["instructions_last_modified"] = (
                self.file_loader.framework_last_modified
            )

        # Transfer metadata from packaged loader if available
        if self.packaged_loader.framework_version:
            content["instructions_version"] = self.packaged_loader.framework_version
            content["version"] = self.packaged_loader.framework_version
        if self.packaged_loader.framework_last_modified:
            content["instructions_last_modified"] = (
                self.packaged_loader.framework_last_modified
            )

    def _extract_version(self, file_content: str) -> int:
        """Extract version number from PM_INSTRUCTIONS_VERSION comment.

        Args:
            file_content: Content of the file to extract version from

        Returns:
            Version number as integer, or 0 if not found
        """
        import re

        match = re.search(r"PM_INSTRUCTIONS_VERSION:\s*(\d+)", file_content)
        if match:
            return int(match.group(1))
        return 0  # No version = oldest

    def _load_filesystem_framework_instructions(self, content: dict[str, Any]) -> None:
        """Load framework instructions from filesystem.

        Priority order:
        1. Deployed compiled file: .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md (if version >= source)
        2. Source file (development): src/claude_mpm/agents/PM_INSTRUCTIONS.md
        3. Legacy file (backward compat): src/claude_mpm/agents/INSTRUCTIONS.md

        Returns early if framework_path is not available.
        Version validation ensures deployed file is never stale compared to source.

        Args:
            content: Dictionary to update with framework instructions
        """
        if not self.framework_path:
            return

        # Define source path for version checking
        pm_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "PM_INSTRUCTIONS.md"
        )

        # PRIORITY 1: Check for compiled/deployed version in .claude-mpm/
        # This is the merged PM_INSTRUCTIONS.md + WORKFLOW.md + MEMORY.md
        deployed_path = self.current_dir / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
        if deployed_path.exists():
            # Validate version before using deployed file
            deployed_content = deployed_path.read_text()
            deployed_version = self._extract_version(deployed_content)

            # Check source version for comparison
            if pm_instructions_path.exists():
                source_content = pm_instructions_path.read_text()
                source_version = self._extract_version(source_content)

                if deployed_version < source_version:
                    self.logger.warning(
                        f"Deployed PM instructions v{deployed_version:04d} is stale, "
                        f"source is v{source_version:04d}. Using source instead."
                    )
                    # Fall through to source loading - don't return early
                else:
                    # Version OK, use deployed
                    content["framework_instructions"] = deployed_content
                    content["loaded"] = True
                    # Sentinel: the merged DEPLOYED file already contains the
                    # AGENT_DELEGATION + WORKFLOW-stub + MEMORY blocks (and any
                    # project/user overrides, which the deployer inlines).  The
                    # subsidiary loaders MUST NOT re-append the system defaults
                    # or the prompt would contain each block twice.
                    content["_loaded_from_deployed"] = True
                    self.logger.info(
                        f"Loaded PM_INSTRUCTIONS_DEPLOYED.md v{deployed_version:04d} from .claude-mpm/"
                    )
                    return  # Stop here - deployed version is current
            else:
                # Source doesn't exist, use deployed even without version check
                content["framework_instructions"] = deployed_content
                content["loaded"] = True
                content["_loaded_from_deployed"] = True
                self.logger.info("Loaded PM_INSTRUCTIONS_DEPLOYED.md from .claude-mpm/")
                return

        # PRIORITY 2: Development mode - load from source PM_INSTRUCTIONS.md
        framework_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )

        # Try loading new consolidated file (pm_instructions_path already defined above)
        if pm_instructions_path.exists():
            loaded_content = self.file_loader.try_load_file(
                pm_instructions_path, "source PM_INSTRUCTIONS.md (development mode)"
            )
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                self.logger.warning(
                    "Using source PM_INSTRUCTIONS.md - deployed version not found"
                )
        # PRIORITY 3: Fall back to legacy file for backward compatibility
        elif framework_instructions_path.exists():
            loaded_content = self.file_loader.try_load_file(
                framework_instructions_path, "framework INSTRUCTIONS.md (legacy)"
            )
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                self.logger.warning(
                    "Using legacy INSTRUCTIONS.md - consider migrating to PM_INSTRUCTIONS.md"
                )

        # Load BASE_PM.md for core framework requirements
        base_pm_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
        )
        if base_pm_path.exists():
            base_pm_content = self.file_loader.try_load_file(
                base_pm_path, "BASE_PM framework requirements"
            )
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

    def load_agent_delegation_instructions(self, content: dict[str, Any]) -> None:
        """Load AGENT_DELEGATION.md from appropriate location.

        Precedence: project .claude-mpm/ > user ~/.claude-mpm/ > system agents/

        When framework_instructions was loaded from PM_INSTRUCTIONS_DEPLOYED.md
        the merged file already contains the AGENT_DELEGATION block (overrides
        inlined by the deployer), so we skip re-appending it to avoid double
        injection.

        Args:
            content: Dictionary to update with agent delegation instructions
        """
        if not self.framework_path:
            return
        if content.get("_loaded_from_deployed"):
            return
        delegation, level = self.file_loader.load_agent_delegation_file(
            self.current_dir, self.framework_path
        )
        if delegation:
            content["agent_delegation"] = delegation
            content["agent_delegation_level"] = level

    def load_workflow_instructions(self, content: dict[str, Any]) -> None:
        """Load WORKFLOW.md from appropriate location.

        Lazy-loading strategy to reduce system-prompt token cost (~1,150 tokens):
        - Project-level (.claude-mpm/WORKFLOW.md): embedded verbatim — project
          customisations must be immediately available.
        - User-level (~/.claude-mpm/WORKFLOW.md): embedded verbatim — same
          rationale as project level.
        - System-level (src/claude_mpm/agents/WORKFLOW.md): replaced with a
          single-line reference.  The PM already has a compact 5-row workflow
          summary table in PM_INSTRUCTIONS.md; the full detail can be Read on
          demand via the Read tool for complex tasks.

        When framework_instructions was loaded from PM_INSTRUCTIONS_DEPLOYED.md
        the merged file already contains the WORKFLOW block (stub for the system
        default, or the inlined override), so we skip re-appending it to avoid
        double injection.

        Args:
            content: Dictionary to update with workflow instructions
        """
        if content.get("_loaded_from_deployed"):
            return
        workflow, level = load_workflow(self.current_dir, self.framework_path)
        if not workflow:
            return

        if level in ("project", "user"):
            # Project/user overrides are small, project-specific, and must be
            # available immediately — embed them in full.
            content["workflow_instructions"] = workflow
            content["workflow_instructions_level"] = level
            self.logger.info(
                f"Embedded {level}-level WORKFLOW.md ({len(workflow)} chars)"
            )
        else:
            # System default: inject a compact reference line instead of the
            # full document.  Saves ~1,150 tokens per session.
            content["workflow_instructions"] = WORKFLOW_SYSTEM_REFERENCE
            content["workflow_instructions_level"] = level
            self.logger.info(
                f"Lazy-loaded {level}-level WORKFLOW.md "
                f"(reference only, saved ~1,150 tokens)"
            )

    def _detect_kuzu_memory(self) -> bool:
        """Check if kuzu-memory CLI is available.

        Returns:
            True if kuzu-memory is installed and accessible, False otherwise
        """
        import shutil

        pipx_path = (
            Path.home()
            / ".local"
            / "pipx"
            / "venvs"
            / "kuzu-memory"
            / "bin"
            / "kuzu-memory"
        )
        return pipx_path.exists() or shutil.which("kuzu-memory") is not None

    def load_memory_instructions(self, content: dict[str, Any]) -> None:
        """Load MEMORY.md from appropriate location.

        Lazy-loading strategy (mirrors WORKFLOW.md, saves ~1,776 tokens):
        - Project-level (.claude-mpm/MEMORY.md): embedded verbatim — project
          customisations must be available immediately.
        - User-level (~/.claude-mpm/MEMORY.md): embedded verbatim — same
          rationale.
        - System-level (src/claude_mpm/agents/MEMORY.md): replaced with the
          compact ``MEMORY_SYSTEM_REFERENCE`` stub.  The stub preserves
          memory-trigger awareness (trigger phrases, categories, the
          ``mcp__trusty-memory__memory_remember`` tool, and a pointer to the
          full MEMORY.md), so the PM never misses a trigger.

        Two behaviours are preserved when framework_instructions was loaded
        from PM_INSTRUCTIONS_DEPLOYED.md (the ``_loaded_from_deployed`` sentinel):
        1. The static MEMORY block is NOT re-appended (the merged DEPLOYED file
           already contains it — re-appending would double-inject).
        2. The dynamic kuzu-memory augmentation STILL runs.  It is
           environment-dependent (depends on whether kuzu-memory is installed on
           *this* machine) and therefore cannot be baked into DEPLOYED.

        If kuzu-memory is detected AND no project-level .claude-mpm/MEMORY.md
        exists, prepends a legacy kuzu-memory notice.  trusty-memory is the
        primary recommended backend; kuzu-memory is a deprecated legacy fallback
        retained for backward compatibility.

        WHAT: Selects the correct MEMORY.md text using a three-tier precedence
              (project verbatim > user verbatim > system stub), skips re-loading the
              static block when the ``_loaded_from_deployed`` sentinel is set (to prevent
              double-injection from PM_INSTRUCTIONS_DEPLOYED.md), then unconditionally
              probes for a local kuzu-memory installation and prepends a legacy-backend
              notice when found so that sessions on machines with kuzu-memory still see
              memory-tool instructions even when the static block is suppressed.
        WHY: Embedding the full ~1,776-token MEMORY.md on every session is wasteful for
             the common case where memory tooling is not needed; the compact reference
             stub preserves trigger-phrase awareness at negligible cost.  The split
             static/dynamic approach is necessary because the kuzu-memory check is
             machine-specific and therefore cannot be precompiled into the DEPLOYED
             merged file.

        Args:
            content: Dictionary to update with memory instructions
        """
        from_deployed = bool(content.get("_loaded_from_deployed"))

        if from_deployed:
            # DEPLOYED already contains the static MEMORY block; do not re-load
            # it.  We still evaluate the dynamic, environment-dependent kuzu
            # augmentation below (it cannot be baked into DEPLOYED).
            memory, level = None, None
        else:
            memory, level = self.file_loader.load_memory_file(
                self.current_dir, self.framework_path or Path()
            )

            if level in ("project", "user"):
                # Project/user overrides are small and project-specific — embed
                # them verbatim so they are immediately available.
                self.logger.info(
                    f"Embedded {level}-level MEMORY.md ({len(memory)} chars)"
                )
            else:
                # System default: substitute the compact reference stub instead
                # of the full ~1,776-token document.
                memory = MEMORY_SYSTEM_REFERENCE
                level = "system"
                self.logger.info(
                    "Lazy-loaded system-level MEMORY.md "
                    "(reference only, saved ~1,776 tokens)"
                )

        # Auto-inject legacy kuzu-memory notice when detected and no project
        # override.  trusty-memory is primary; if the user has kuzu-memory
        # installed but not trusty-memory, surface a notice so they know memory
        # is still active.  This runs even in the DEPLOYED path because it is
        # environment-dependent and cannot be precompiled into DEPLOYED.
        if level != "project" and self._detect_kuzu_memory():
            kuzu_prefix = (
                "## Memory: kuzu-memory Active (legacy fallback)\n\n"
                "kuzu-memory is installed and active as a legacy memory backend.\n"
                "Use MCP tools for memory operations:\n"
                "- `mcp__kuzu-memory__kuzu_recall` — query memories before delegating research\n"
                "- `mcp__kuzu-memory__kuzu_learn` — store important decisions asynchronously\n"
                "- `mcp__kuzu-memory__kuzu_remember` — store facts immediately\n\n"
                "Consider migrating to trusty-memory (primary recommended backend).\n\n"
            )
            if from_deployed:
                # In the DEPLOYED path the static body is already present; only
                # the dynamic kuzu prefix is injected (NOT the static MEMORY.md
                # body, which would duplicate the merged content).
                memory = kuzu_prefix
                # ``level`` only labels this dynamic kuzu prefix for
                # ``memory_instructions_level`` below — the deployed static body
                # is unaffected by it; "system" is the correct, harmless label.
                level = "system"
            elif memory:
                memory = kuzu_prefix + memory
            else:
                memory = kuzu_prefix
                level = "system"

        if memory:
            content["memory_instructions"] = memory
            content["memory_instructions_level"] = level
