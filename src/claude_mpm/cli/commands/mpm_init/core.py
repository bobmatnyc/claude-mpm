"""Core MPMInitCommand class for project initialization.

This module contains the main command class responsible for orchestrating
the MPM project initialization process, including configuration generation,
agent delegation, and workflow management.
"""

import contextlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from claude_mpm.core.enums import OperationResult
from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.project.archive_manager import ArchiveManager
from claude_mpm.services.project.documentation_manager import DocumentationManager
from claude_mpm.services.project.enhanced_analyzer import EnhancedProjectAnalyzer
from claude_mpm.services.project.project_organizer import ProjectOrganizer
from claude_mpm.utils.display_helper import DisplayHelper

# Import from sibling modules in the mpm_init package
from . import display, git_activity, modes, prompts
from .knowledge_extractor import ProjectKnowledgeExtractor

logger = get_logger(__name__)


class MPMInitCommand:
    """Initialize projects for optimal Claude Code and Claude MPM usage."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the MPM-Init command."""
        self.project_path = project_path or Path.cwd()
        self.claude_mpm_dir = self.project_path / ".claude-mpm"
        self.claude_mpm_script = self._find_claude_mpm_script()
        self.console = Console()

        # Initialize service components
        self.doc_manager = DocumentationManager(self.project_path)
        self.organizer = ProjectOrganizer(self.project_path)
        self.archive_manager = ArchiveManager(self.project_path)
        self.analyzer = EnhancedProjectAnalyzer(self.project_path)
        self.display = DisplayHelper(self.console)

    def initialize_project(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        force: bool = False,
        verbose: bool = False,
        ast_analysis: bool = True,
        update_mode: bool = False,
        review_only: bool = False,
        organize_files: bool = False,
        preserve_custom: bool = True,
        skip_archive: bool = False,
        dry_run: bool = False,
        quick_update: bool = False,
        catchup: bool = False,
        non_interactive: bool = False,
        days: int = 30,
        export: Optional[str] = None,
    ) -> Dict:
        """
        Initialize project with Agentic Coder Optimizer standards.

        Args:
            project_type: Type of project (web, api, cli, library, etc.)
            framework: Specific framework if applicable
            force: Force initialization even if project already configured
            verbose: Show detailed output
            ast_analysis: Enable AST analysis for enhanced documentation
            update_mode: Update existing CLAUDE.md instead of recreating
            review_only: Review project state without making changes
            organize_files: Organize misplaced files into proper directories
            preserve_custom: Preserve custom sections when updating
            skip_archive: Skip archiving existing files
            dry_run: Show what would be done without making changes
            quick_update: Perform lightweight update based on recent git activity
            catchup: Show recent commit history from all branches for PM context
            non_interactive: Non-interactive mode - display report only without prompting
            days: Number of days for git history analysis (7, 14, 30, 60, or 90)
            export: Export report to file (path or "auto" for default location)

        Returns:
            Dict containing initialization results
        """
        try:
            # Determine initialization mode
            claude_md = self.project_path / "CLAUDE.md"
            has_existing = claude_md.exists()

            if review_only:
                return self._run_review_mode()

            if catchup:
                data = self._catchup()
                self._display_catchup(data)
                return {
                    "status": OperationResult.SUCCESS,
                    "mode": "catchup",
                    "catchup_data": data,
                }

            if quick_update:
                return self._run_quick_update_mode(
                    days=days,
                    non_interactive=non_interactive,
                    export=export,
                )

            if has_existing and not force and not update_mode:
                # Auto-select update mode if organize_files or dry_run is specified
                if organize_files or dry_run:
                    update_mode = True
                    self.console.print(
                        "[cyan]Auto-selecting update mode for organization tasks.[/cyan]\n"
                    )
                else:
                    # Offer update mode
                    self.console.print(
                        "[yellow]⚠️  Project already has CLAUDE.md file.[/yellow]\n"
                    )

                    # Show current documentation analysis
                    doc_analysis = self.doc_manager.analyze_existing_content()
                    self._display_documentation_status(doc_analysis)

                    # Ask user what to do
                    action = self._prompt_update_action()

                    if action == "update":
                        update_mode = True
                    elif action == "recreate":
                        force = True
                    elif action == "review":
                        return self._run_review_mode()
                    else:
                        return {
                            "status": OperationResult.CANCELLED,
                            "message": "Initialization cancelled",
                        }

            # Handle dry-run mode
            if dry_run:
                return self._run_dry_run_mode(organize_files, has_existing)

            # Run pre-initialization checks
            if not review_only:
                pre_check_result = self._run_pre_initialization_checks(
                    organize_files, skip_archive, has_existing
                )
                if pre_check_result.get("status") == OperationResult.ERROR:
                    return pre_check_result

            # Note: .gitignore recommendations are now shown in 'mpm config' command
            # instead of automatic updates during initialization

            # Build the delegation prompt
            if update_mode:
                prompt = self._build_update_prompt(
                    project_type, framework, ast_analysis, preserve_custom
                )
            else:
                prompt = self._build_initialization_prompt(
                    project_type, framework, ast_analysis
                )

            # Show appropriate plan based on mode
            if update_mode:
                self._show_update_plan(ast_analysis, preserve_custom)
            else:
                self._show_initialization_plan(ast_analysis)

            # Execute via claude-mpm run command
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task_desc = (
                    "[cyan]Updating documentation..."
                    if update_mode
                    else "[cyan]Delegating to Agentic Coder Optimizer..."
                )
                task = progress.add_task(task_desc, total=None)

                # Run the initialization through subprocess
                result = self._run_initialization(prompt, verbose, update_mode)

                complete_desc = (
                    "[green]✓ Update complete"
                    if update_mode
                    else "[green]✓ Initialization complete"
                )
                progress.update(task, description=complete_desc)

            # Post-processing for update mode
            if update_mode and result.get("status") == OperationResult.SUCCESS:
                self._handle_update_post_processing()

            # Deploy PM skills after successful initialization
            if result.get("status") == OperationResult.SUCCESS:
                self._deploy_pm_skills()

            return result

        except Exception as e:
            logger.error(f"Failed to initialize project: {e}")
            self.console.print(f"[red]❌ Error: {e}[/red]")
            return {"status": OperationResult.ERROR, "message": str(e)}

    def _find_claude_mpm_script(self) -> Path:
        """Find the claude-mpm script location."""
        # Try to find claude-mpm in the project scripts directory first
        project_root = Path(__file__).parent.parent.parent.parent.parent
        script_path = project_root / "scripts" / "claude-mpm"
        if script_path.exists():
            return script_path
        # Otherwise assume it's in PATH
        return Path("claude-mpm")

    def _build_claude_mpm_command(self, verbose: bool) -> List[str]:
        """Build the claude-mpm run command with appropriate arguments."""
        cmd = [str(self.claude_mpm_script)]

        # Add top-level flags that go before 'run' subcommand
        cmd.append("--no-check-dependencies")

        # Now add the run subcommand
        cmd.append("run")

        # Add non-interactive mode
        # We'll pass the prompt via stdin instead of -i flag
        cmd.append("--non-interactive")

        # Add verbose flag if requested (run subcommand argument)
        if verbose:
            cmd.append("--verbose")

        return cmd

    def _run_initialization(
        self,
        prompt: str,
        verbose: bool,
        update_mode: bool = False,
    ) -> Dict:
        """Run the initialization through subprocess calling claude-mpm."""
        try:
            # Write prompt to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as tmp_file:
                tmp_file.write(prompt)
                prompt_file = tmp_file.name

            try:
                # Build the command
                cmd = self._build_claude_mpm_command(verbose)
                # Add the input file flag
                cmd.extend(["-i", prompt_file])

                # Log the command if verbose
                if verbose:
                    self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
                    self.console.print(f"[dim]Prompt file: {prompt_file}[/dim]")

                # Execute the command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_path),
                    check=False,
                )
            finally:
                # Clean up temporary file
                with contextlib.suppress(Exception):
                    Path(prompt_file).unlink()

            # Display output if verbose
            if verbose and result.stdout:
                self.console.print(result.stdout)
            if verbose and result.stderr:
                self.console.print(f"[yellow]{result.stderr}[/yellow]")

            # Check result - be more lenient with return codes
            if result.returncode == 0 or (self.project_path / "CLAUDE.md").exists():
                response = {
                    "status": OperationResult.SUCCESS,
                    "message": "Project initialized successfully",
                    "files_created": [],
                    "files_updated": [],
                    "next_steps": [],
                }

                # Check if CLAUDE.md was created
                claude_md = self.project_path / "CLAUDE.md"
                if claude_md.exists():
                    response["files_created"].append("CLAUDE.md")

                # Check for other common files
                for file_name in ["CODE.md", "DEVELOPER.md", "STRUCTURE.md", "OPS.md"]:
                    file_path = self.project_path / file_name
                    if file_path.exists():
                        response["files_created"].append(file_name)

                # Add next steps
                response["next_steps"] = [
                    "Review the generated CLAUDE.md documentation",
                    "Verify the project structure meets your needs",
                    "Run 'claude-mpm run' to start using the optimized setup",
                ]

                # Display results
                self._display_results(response, verbose)

                return response

            # Extract meaningful error message
            error_msg = (
                result.stderr
                if result.stderr
                else result.stdout
                if result.stdout
                else "Unknown error occurred"
            )

            logger.error(f"claude-mpm run failed: {error_msg}")
            return {
                "status": OperationResult.ERROR,
                "message": f"Initialization failed: {error_msg}",
            }

        except FileNotFoundError:
            logger.error("claude-mpm command not found")
            self.console.print(
                "[red]Error: claude-mpm command not found. Ensure Claude MPM is properly installed.[/red]"
            )
            return {"status": OperationResult.ERROR, "message": "claude-mpm not found"}
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return {"status": OperationResult.ERROR, "message": str(e)}

    def _run_pre_initialization_checks(
        self, organize_files: bool, skip_archive: bool, has_existing: bool
    ) -> Dict:
        """Run pre-initialization checks and preparations."""
        checks_passed = []
        warnings = []

        # Run comprehensive project readiness check
        _ready, actions = self.organizer.ensure_project_ready(
            auto_organize=organize_files,
            safe_mode=True,  # Only perform safe operations by default
        )

        if actions:
            checks_passed.extend(actions)

        # Get structure validation report
        validation = self.organizer.validate_structure()
        if validation["warnings"]:
            warnings.extend(validation["warnings"])
        if validation["errors"]:
            warnings.extend(validation["errors"])

        # Show structure grade
        if validation.get("grade"):
            checks_passed.append(f"Structure validation: {validation['grade']}")

        # Archive existing documentation if needed
        if has_existing and not skip_archive:
            if self.archive_manager.auto_archive_before_update(
                self.project_path / "CLAUDE.md", update_reason="Before mpm-init update"
            ):
                checks_passed.append("Archived existing CLAUDE.md")

        # Check for issues in validation report
        if validation.get("issues"):
            for issue in validation["issues"]:
                warnings.append(issue["description"])

        if warnings:
            self.console.print("\n[yellow]⚠️  Project issues detected:[/yellow]")
            for warning in warnings[:5]:
                self.console.print(f"  • {warning}")
            self.console.print()

        if checks_passed:
            self.console.print("[green]✅ Pre-initialization checks:[/green]")
            for check in checks_passed:
                self.console.print(f"  • {check}")
            self.console.print()

        return {
            "status": OperationResult.SUCCESS,
            "checks_passed": checks_passed,
            "warnings": warnings,
        }

    def _build_initialization_prompt(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        ast_analysis: bool = True,
    ) -> str:
        """Build the initialization prompt for the agent."""
        return prompts.build_initialization_prompt(
            self.project_path, project_type, framework, ast_analysis
        )

    def _is_initialized(self) -> bool:
        """Check if project is already initialized with .claude-mpm directory."""
        return self.claude_mpm_dir.exists()

    def _build_update_prompt(
        self,
        project_type: Optional[str],
        framework: Optional[str],
        ast_analysis: bool,
        preserve_custom: bool,
    ) -> str:
        """Build prompt for update mode with optional knowledge extraction."""
        # Get existing content analysis
        doc_analysis = self.doc_manager.analyze_existing_content()

        # Check if project is initialized (.claude-mpm exists)
        # If so, use enhanced update mode with knowledge extraction
        if self._is_initialized():
            self.console.print(
                "[cyan]✓ Detected initialized project - activating enhanced update mode[/cyan]"
            )

            # Extract knowledge from all sources
            extractor = ProjectKnowledgeExtractor(self.project_path)

            self.console.print("[cyan]✓ Analyzing git history (last 90 days)...[/cyan]")
            git_insights = extractor.extract_from_git(days=90)

            if git_insights.get("available"):
                arch_count = len(git_insights.get("architectural_decisions", []))
                workflow_count = len(git_insights.get("workflow_patterns", []))
                self.console.print(f"  - Found {arch_count} architectural decisions")
                self.console.print(f"  - Detected {workflow_count} workflow patterns")

            self.console.print("[cyan]✓ Analyzing session logs...[/cyan]")
            log_insights = extractor.extract_from_logs()

            if log_insights.get("available"):
                learning_count = len(log_insights.get("learnings", []))
                self.console.print(f"  - Found {learning_count} learning entries")

            self.console.print("[cyan]✓ Analyzing memory files...[/cyan]")
            memory_insights = extractor.extract_from_memory()

            if memory_insights.get("available"):
                total_insights = (
                    len(memory_insights.get("architectural_knowledge", []))
                    + len(memory_insights.get("implementation_guidelines", []))
                    + len(memory_insights.get("common_mistakes", []))
                    + len(memory_insights.get("technical_context", []))
                )
                self.console.print(f"  - Found {total_insights} accumulated insights")

            self.console.print(
                "[green]✓ Knowledge extraction complete - building enhanced prompt[/green]\n"
            )

            # Build enhanced prompt with extracted knowledge
            return prompts.build_enhanced_update_prompt(
                self.project_path,
                doc_analysis,
                git_insights,
                log_insights,
                memory_insights,
                project_type,
                framework,
                ast_analysis,
                preserve_custom,
            )
        # Standard update mode (no .claude-mpm directory)
        return prompts.build_update_prompt(
            self.project_path,
            doc_analysis,
            project_type,
            framework,
            ast_analysis,
            preserve_custom,
        )

    def _display_documentation_status(self, analysis: Dict) -> None:
        """Display current documentation status."""
        display.display_documentation_status(self.display, analysis)

    def _prompt_update_action(self) -> str:
        """Prompt user for update action."""
        return modes.prompt_update_action(self.console)

    def _run_review_mode(self) -> Dict:
        """Run review mode to analyze project without changes."""
        return modes.run_review_mode(
            self.console,
            self.display,
            self.organizer,
            self.doc_manager,
            self.analyzer,
        )

    def _run_quick_update_mode(
        self,
        days: int = 30,
        non_interactive: bool = False,
        export: Optional[str] = None,
    ) -> Dict:
        """Run quick update mode - lightweight update based on recent git activity."""
        return modes.run_quick_update_mode(
            self.console,
            self.display,
            self.project_path,
            self.analyzer,
            self.doc_manager,
            self.archive_manager,
            days=days,
            non_interactive=non_interactive,
            export=export,
        )

    def _catchup(self) -> Dict[str, Any]:
        """Get recent commit history for PM context."""
        return git_activity.catchup(self.project_path)

    def _display_catchup(self, data: Dict[str, Any]) -> None:
        """Display catchup information to console.

        Args:
            data: Commit history data from _catchup()
        """
        display.display_catchup(self.display, self.console, data)

    def _run_dry_run_mode(self, organize_files: bool, has_existing: bool) -> Dict:
        """Run dry-run mode to show what would be done without making changes."""
        return modes.run_dry_run_mode(
            self.console,
            self.organizer,
            self.doc_manager,
            organize_files,
            has_existing,
        )

    def _show_update_plan(self, ast_analysis: bool, preserve_custom: bool) -> None:
        """Show update mode plan."""
        display.show_update_plan(self.console, ast_analysis, preserve_custom)

    def _show_initialization_plan(self, ast_analysis: bool) -> None:
        """Show standard initialization plan."""
        display.show_initialization_plan(self.console, ast_analysis)

    def _handle_update_post_processing(self) -> None:
        """Handle post-processing after successful update."""
        modes.handle_update_post_processing(
            self.console,
            self.project_path,
            self.doc_manager,
            self.archive_manager,
        )

        # Optimize CLAUDE.md with prompt-engineer if it exists
        claude_md = self.project_path / "CLAUDE.md"
        if claude_md.exists():
            self._optimize_claude_md_with_prompt_engineer()

    def _display_results(self, result: Dict, verbose: bool):
        """Display initialization results."""
        display.display_results(self.display, self.console, result, verbose)

    def handle_context(
        self,
        session_id: Optional[str] = None,
        list_sessions: bool = False,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Provide intelligent context for resuming work based on git history."""
        return git_activity.handle_context(
            self.project_path, session_id, list_sessions, days
        )

    def _build_research_context_prompt(
        self, git_analysis: Dict[str, Any], days: int
    ) -> str:
        """Build structured Research agent delegation prompt from git analysis."""
        return prompts.build_research_context_prompt(git_analysis, days)

    def _optimize_claude_md_with_prompt_engineer(self) -> None:
        """Optimize CLAUDE.md with prompt-engineer for conciseness and clarity."""
        claude_md_path = self.project_path / "CLAUDE.md"
        if not claude_md_path.exists():
            return

        try:
            # Read current content
            original_content = claude_md_path.read_text()
            original_tokens = self._estimate_tokens(original_content)

            # Create backup
            backup_path = self.archive_manager.auto_archive_before_update(
                claude_md_path, update_reason="Before prompt-engineer optimization"
            )

            if not backup_path:
                logger.warning("Could not create backup before optimization")
                self.console.print(
                    "[yellow]⚠️  Skipping optimization - backup failed[/yellow]"
                )
                return

            self.console.print(
                "\n[cyan]✓ Optimizing CLAUDE.md with prompt-engineer...[/cyan]"
            )
            self.console.print(f"  - Original: {original_tokens:,} tokens (estimated)")
            self.console.print(f"  - Backup created: {backup_path}")

            # Build optimization prompt
            prompt = prompts.build_prompt_engineer_optimization_prompt(
                original_content, original_tokens
            )

            # Run optimization through subprocess
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Running prompt-engineer optimization...", total=None
                )

                result = self._run_initialization(
                    prompt, verbose=False, update_mode=True
                )

                progress.update(task, description="[green]✓ Optimization complete")

            # Check if optimization succeeded
            if result.get("status") == OperationResult.SUCCESS:
                # Read optimized content
                optimized_content = claude_md_path.read_text()
                optimized_tokens = self._estimate_tokens(optimized_content)

                # Calculate reduction
                token_reduction = original_tokens - optimized_tokens
                reduction_percent = (
                    (token_reduction / original_tokens * 100)
                    if original_tokens > 0
                    else 0
                )

                self.console.print(
                    f"  - Optimized: {optimized_tokens:,} tokens ({reduction_percent:.1f}% reduction)"
                )
                self.console.print("[green]✓ CLAUDE.md optimization complete[/green]\n")
            # Restore from backup on failure
            elif backup_path and backup_path.exists():
                import shutil

                shutil.copy2(backup_path, claude_md_path)
                self.console.print(
                    "[yellow]⚠️  Optimization failed - restored from backup[/yellow]\n"
                )

        except Exception as e:
            logger.error(f"Failed to optimize CLAUDE.md: {e}")
            self.console.print(
                f"[yellow]⚠️  Could not optimize CLAUDE.md: {e}[/yellow]\n"
            )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation).

        Uses a simple heuristic: ~4 characters per token for English text.
        This is a rough estimate but sufficient for displaying progress.
        """
        return len(text) // 4

    def _deploy_pm_skills(self) -> None:
        """Deploy PM skills templates to project .claude-mpm directory.

        Copies PM skills from bundled templates to .claude-mpm/skills/pm/
        with version tracking and checksum validation.
        """
        try:
            from rich.progress import (
                BarColumn,
                Progress,
                TaskProgressColumn,
                TextColumn,
            )

            from claude_mpm.services.pm_skills_deployer import PMSkillsDeployerService

            deployer = PMSkillsDeployerService()

            # Use progress bar for deployment
            with Progress(
                TextColumn("[cyan]Deploying PM skills[/cyan]"),
                BarColumn(bar_width=30),
                TaskProgressColumn(),
                TextColumn("[dim]{task.description}[/dim]"),
                console=self.console,
            ) as progress:
                task = progress.add_task("", total=None)  # Unknown total initially

                def update_progress(skill_name: str, current: int, total: int) -> None:
                    progress.update(
                        task, total=total, completed=current, description=skill_name
                    )

                result = deployer.deploy_pm_skills(
                    self.project_path, progress_callback=update_progress
                )

            if result.success:
                if result.deployed:
                    self.console.print(
                        f"[green]✓ Deployed {len(result.deployed)} PM skills[/green]"
                    )

                if result.skipped:
                    self.console.print(
                        f"[dim]  Skipped {len(result.skipped)} (already deployed)[/dim]"
                    )

                if result.errors:
                    self.console.print(
                        f"[yellow]⚠️  {len(result.errors)} errors:[/yellow]"
                    )
                    for error in result.errors[:3]:  # Show first 3 errors
                        self.console.print(f"  • {error['skill']}: {error['error']}")
            else:
                self.console.print(
                    f"[yellow]⚠️  PM skills deployment had errors: {result.message}[/yellow]"
                )

        except ImportError as e:
            logger.warning(f"PM skills deployer not available: {e}")
            self.console.print(
                "[yellow]⚠️  PM skills deployment skipped (service not available)[/yellow]"
            )
        except Exception as e:
            logger.error(f"Failed to deploy PM skills: {e}")
            self.console.print(f"[yellow]⚠️  PM skills deployment failed: {e}[/yellow]")


__all__ = ["MPMInitCommand"]
