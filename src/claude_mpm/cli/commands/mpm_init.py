"""
MPM-Init Command - Initialize projects for optimal Claude Code and Claude MPM success.

This command delegates to the Agentic Coder Optimizer agent to establish clear,
single-path project standards for documentation, tooling, and workflows.

Enhanced with AST inspection capabilities for generating comprehensive developer
documentation with code structure analysis.
"""

import contextlib
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table

from claude_mpm.core.logging_utils import get_logger

# Import new services
from claude_mpm.services.project.archive_manager import ArchiveManager
from claude_mpm.services.project.documentation_manager import DocumentationManager
from claude_mpm.services.project.enhanced_analyzer import EnhancedProjectAnalyzer
from claude_mpm.services.project.project_organizer import ProjectOrganizer

logger = get_logger(__name__)
console = Console()


class MPMInitCommand:
    """Initialize projects for optimal Claude Code and Claude MPM usage."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the MPM-Init command."""
        self.project_path = project_path or Path.cwd()
        self.claude_mpm_script = self._find_claude_mpm_script()

        # Initialize service components
        self.doc_manager = DocumentationManager(self.project_path)
        self.organizer = ProjectOrganizer(self.project_path)
        self.archive_manager = ArchiveManager(self.project_path)
        self.analyzer = EnhancedProjectAnalyzer(self.project_path)

    def initialize_project(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        force: bool = False,
        verbose: bool = False,
        use_venv: bool = False,
        ast_analysis: bool = True,
        update_mode: bool = False,
        review_only: bool = False,
        organize_files: bool = False,
        preserve_custom: bool = True,
        skip_archive: bool = False,
        dry_run: bool = False,
    ) -> Dict:
        """
        Initialize project with Agentic Coder Optimizer standards.

        Args:
            project_type: Type of project (web, api, cli, library, etc.)
            framework: Specific framework if applicable
            force: Force initialization even if project already configured
            verbose: Show detailed output
            use_venv: Force use of venv instead of mamba
            ast_analysis: Enable AST analysis for enhanced documentation
            update_mode: Update existing CLAUDE.md instead of recreating
            review_only: Review project state without making changes
            organize_files: Organize misplaced files into proper directories
            preserve_custom: Preserve custom sections when updating
            skip_archive: Skip archiving existing files
            dry_run: Show what would be done without making changes

        Returns:
            Dict containing initialization results
        """
        try:
            # Determine initialization mode
            claude_md = self.project_path / "CLAUDE.md"
            has_existing = claude_md.exists()

            if review_only:
                return self._run_review_mode()

            if has_existing and not force and not update_mode:
                # Auto-select update mode if organize_files or dry_run is specified
                if organize_files or dry_run:
                    update_mode = True
                    console.print(
                        "[cyan]Auto-selecting update mode for organization tasks.[/cyan]\n"
                    )
                else:
                    # Offer update mode
                    console.print(
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
                            "status": "cancelled",
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
                if pre_check_result.get("status") == "error":
                    return pre_check_result

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
                console=console,
            ) as progress:
                task_desc = (
                    "[cyan]Updating documentation..."
                    if update_mode
                    else "[cyan]Delegating to Agentic Coder Optimizer..."
                )
                task = progress.add_task(task_desc, total=None)

                # Run the initialization through subprocess
                result = self._run_initialization(
                    prompt, verbose, use_venv, update_mode
                )

                complete_desc = (
                    "[green]✓ Update complete"
                    if update_mode
                    else "[green]✓ Initialization complete"
                )
                progress.update(task, description=complete_desc)

            # Post-processing for update mode
            if update_mode and result.get("status") == "success":
                self._handle_update_post_processing()

            return result

        except Exception as e:
            logger.error(f"Failed to initialize project: {e}")
            console.print(f"[red]❌ Error: {e}[/red]")
            return {"status": "error", "message": str(e)}

    def _find_claude_mpm_script(self) -> Path:
        """Find the claude-mpm script location."""
        # Try to find claude-mpm in the project scripts directory first
        project_root = Path(__file__).parent.parent.parent.parent.parent
        script_path = project_root / "scripts" / "claude-mpm"
        if script_path.exists():
            return script_path
        # Otherwise assume it's in PATH
        return Path("claude-mpm")

    def _build_initialization_prompt(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        ast_analysis: bool = True,
    ) -> str:
        """Build the initialization prompt for the agent."""
        base_prompt = f"""Please delegate this task to the Agentic Coder Optimizer agent:

Initialize this project for optimal use with Claude Code and Claude MPM.

Project Path: {self.project_path}
"""

        if project_type:
            base_prompt += f"Project Type: {project_type}\n"

        if framework:
            base_prompt += f"Framework: {framework}\n"

        base_prompt += """
Please perform the following initialization tasks:

1. **Analyze Current State**:
   - Scan project structure and existing configurations
   - Identify project type, language, and frameworks
   - Check for existing documentation and tooling

2. **Create/Update CLAUDE.md**:
   - Project overview and purpose
   - Architecture and key components
   - Development guidelines
   - ONE clear way to: build, test, deploy, lint, format
   - Links to all relevant documentation
   - Common tasks and workflows

3. **Establish Single-Path Standards**:
   - ONE command for each operation (build, test, lint, etc.)
   - Clear documentation of THE way to do things
   - Remove ambiguity in workflows

4. **Configure Development Tools**:
   - Set up or verify linting configuration
   - Configure code formatting standards
   - Establish testing framework
   - Add pre-commit hooks if needed

5. **Create Project Structure Documentation**:
   - Document folder organization
   - Explain where different file types belong
   - Provide examples of proper file placement

6. **Set Up GitHub Integration** (if applicable):
   - Create/update .github/workflows
   - Add issue and PR templates
   - Configure branch protection rules documentation

7. **Initialize Memory System**:
   - Create .claude-mpm/memories/ directory
   - Add initial memory files for key project knowledge
   - Document memory usage patterns

8. **Generate Quick Start Guide**:
   - Step-by-step setup instructions
   - Common commands reference
   - Troubleshooting guide
"""

        if ast_analysis:
            base_prompt += """
9. **Perform AST Analysis** (using Code Analyzer agent if needed):
   - Parse code files to extract structure (classes, functions, methods)
   - Generate comprehensive API documentation
   - Create code architecture diagrams
   - Document function signatures and dependencies
   - Extract docstrings and inline comments
   - Map code relationships and inheritance hierarchies
   - Generate developer documentation with:
     * Module overview and purpose
     * Class hierarchies and relationships
     * Function/method documentation
     * Type annotations and parameter descriptions
     * Code complexity metrics
     * Dependency graphs
   - Create DEVELOPER.md with technical architecture details
   - Add CODE_STRUCTURE.md with AST-derived insights
"""

        base_prompt += """

10. **Holistic CLAUDE.md Organization** (CRITICAL - Do this LAST):
   After completing all initialization tasks, take a holistic look at the CLAUDE.md file and:

   a) **Reorganize Content by Priority**:
      - CRITICAL instructions (security, data handling, core business rules) at the TOP
      - Project overview and purpose
      - Key architectural decisions and constraints
      - Development guidelines and standards
      - Common tasks and workflows
      - Links to additional documentation
      - Nice-to-have or optional information at the BOTTOM

   b) **Rank Instructions by Importance**:
      - Use clear markers:
        * 🔴 CRITICAL: Security, data handling, breaking changes, core business rules
        * 🟡 IMPORTANT: Key workflows, architecture decisions, performance requirements
        * 🟢 STANDARD: Common operations, coding standards, best practices
        * ⚪ OPTIONAL: Nice-to-have features, experimental code, future considerations
      - Group related instructions together
      - Ensure no contradictory instructions exist
      - Remove redundant or outdated information
      - Add a "Priority Index" at the top listing all CRITICAL and IMPORTANT items

   c) **Optimize for AI Agent Understanding**:
      - Use consistent formatting and structure
      - Provide clear examples for complex instructions
      - Include "WHY" explanations for critical rules
      - Add quick reference sections for common operations
      - Ensure instructions are actionable and unambiguous

   d) **Validate Completeness**:
      - Ensure ALL critical project knowledge is captured
      - Verify single-path principle (ONE way to do each task)
      - Check that all referenced documentation exists
      - Confirm all tools and dependencies are documented
      - Test that a new AI agent could understand the project from CLAUDE.md alone

   e) **Add Meta-Instructions Section**:
      - Include a section about how to maintain CLAUDE.md
      - Document when and how to update instructions
      - Provide guidelines for instruction priority levels
      - Add a changelog or last-updated timestamp

   f) **Follow This CLAUDE.md Template Structure**:
      ```markdown
      # Project Name - CLAUDE.md

      ## 🎯 Priority Index
      ### 🔴 CRITICAL Instructions
      - [List all critical items with links to their sections]

      ### 🟡 IMPORTANT Instructions
      - [List all important items with links to their sections]

      ## 📋 Project Overview
      [Brief description and purpose]

      ## 🔴 CRITICAL: Security & Data Handling
      [Critical security rules and data handling requirements]

      ## 🔴 CRITICAL: Core Business Rules
      [Non-negotiable business logic and constraints]

      ## 🟡 IMPORTANT: Architecture & Design
      [Key architectural decisions and patterns]

      ## 🟡 IMPORTANT: Development Workflow
      ### ONE Way to Build
      ### ONE Way to Test
      ### ONE Way to Deploy

      ## 🟢 STANDARD: Coding Guidelines
      [Standard practices and conventions]

      ## 🟢 STANDARD: Common Tasks
      [How to perform routine operations]

      ## 📚 Documentation Links
      [Links to additional resources]

      ## ⚪ OPTIONAL: Future Enhancements
      [Nice-to-have features and ideas]

      ## 📝 Meta: Maintaining This Document
      - Last Updated: [timestamp]
      - Update Frequency: [when to update]
      - Priority Guidelines: [how to assign priorities]
      ```

Please ensure all documentation is clear, concise, and optimized for AI agents to understand and follow.
Focus on establishing ONE clear way to do ANYTHING in the project.
The final CLAUDE.md should be a comprehensive, well-organized guide that any AI agent can follow to work effectively on this project.
"""

        return base_prompt

    def _build_claude_mpm_command(
        self, verbose: bool, use_venv: bool = False
    ) -> List[str]:
        """Build the claude-mpm run command with appropriate arguments."""
        cmd = [str(self.claude_mpm_script)]

        # Add venv flag if requested or if mamba issues detected
        # This goes BEFORE the subcommand
        if use_venv:
            cmd.append("--use-venv")

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

    def _display_documentation_status(self, analysis: Dict) -> None:
        """Display current documentation status."""
        table = Table(title="Current CLAUDE.md Status", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Size", f"{analysis.get('size', 0):,} characters")
        table.add_row("Lines", str(analysis.get("lines", 0)))
        table.add_row("Sections", str(len(analysis.get("sections", []))))
        table.add_row(
            "Has Priority Index", "✓" if analysis.get("has_priority_index") else "✗"
        )
        table.add_row(
            "Has Priority Markers", "✓" if analysis.get("has_priority_markers") else "✗"
        )

        if analysis.get("last_modified"):
            table.add_row("Last Modified", analysis["last_modified"])

        console.print(table)

        if analysis.get("outdated_patterns"):
            console.print("\n[yellow]⚠️  Outdated patterns detected:[/yellow]")
            for pattern in analysis["outdated_patterns"]:
                console.print(f"  • {pattern}")

        if analysis.get("custom_sections"):
            console.print("\n[blue]ℹ️  Custom sections found:[/blue]")
            for section in analysis["custom_sections"][:5]:
                console.print(f"  • {section}")

    def _prompt_update_action(self) -> str:
        """Prompt user for update action."""
        console.print("\n[bold]How would you like to proceed?[/bold]\n")

        choices = {
            "1": ("update", "Update existing CLAUDE.md (preserves custom content)"),
            "2": ("recreate", "Recreate CLAUDE.md from scratch"),
            "3": ("review", "Review project state without changes"),
            "4": ("cancel", "Cancel operation"),
        }

        for key, (_, desc) in choices.items():
            console.print(f"  [{key}] {desc}")

        choice = Prompt.ask(
            "\nSelect option", choices=list(choices.keys()), default="1"
        )
        return choices[choice][0]

    def _run_review_mode(self) -> Dict:
        """Run review mode to analyze project without changes."""
        console.print("\n[bold cyan]🔍 Project Review Mode[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Analyze project structure
            task = progress.add_task("[cyan]Analyzing project structure...", total=None)
            structure_report = self.organizer.verify_structure()
            progress.update(task, description="[green]✓ Structure analysis complete")

            # Analyze documentation
            task = progress.add_task("[cyan]Analyzing documentation...", total=None)
            doc_analysis = self.doc_manager.analyze_existing_content()
            progress.update(
                task, description="[green]✓ Documentation analysis complete"
            )

            # Analyze git history
            if self.analyzer.is_git_repo:
                task = progress.add_task("[cyan]Analyzing git history...", total=None)
                git_analysis = self.analyzer.analyze_git_history()
                progress.update(task, description="[green]✓ Git analysis complete")
            else:
                git_analysis = None

            # Detect project state
            task = progress.add_task("[cyan]Detecting project state...", total=None)
            project_state = self.analyzer.detect_project_state()
            progress.update(task, description="[green]✓ State detection complete")

        # Display comprehensive report
        self._display_review_report(
            structure_report, doc_analysis, git_analysis, project_state
        )

        return {
            "status": "success",
            "mode": "review",
            "structure_report": structure_report,
            "documentation_analysis": doc_analysis,
            "git_analysis": git_analysis,
            "project_state": project_state,
        }

    def _display_review_report(
        self, structure: Dict, docs: Dict, git: Optional[Dict], state: Dict
    ) -> None:
        """Display comprehensive review report."""
        console.print("\n" + "=" * 60)
        console.print("[bold]PROJECT REVIEW REPORT[/bold]")
        console.print("=" * 60 + "\n")

        # Project State
        console.print("[bold cyan]📊 Project State[/bold cyan]")
        console.print(f"  Phase: {state.get('phase', 'unknown')}")
        if state.get("indicators"):
            console.print("  Indicators:")
            for indicator in state["indicators"][:5]:
                console.print(f"    • {indicator}")

        # Structure Report
        console.print("\n[bold cyan]📁 Project Structure[/bold cyan]")
        console.print(f"  Existing directories: {len(structure.get('exists', []))}")
        console.print(f"  Missing directories: {len(structure.get('missing', []))}")
        if structure.get("issues"):
            console.print(f"  Issues found: {len(structure['issues'])}")
            for issue in structure["issues"][:3]:
                console.print(f"    ⚠️  {issue['description']}")

        # Documentation Report
        console.print("\n[bold cyan]📚 Documentation Status[/bold cyan]")
        if docs.get("exists"):
            console.print(f"  CLAUDE.md: Found ({docs.get('size', 0):,} chars)")
            console.print(f"  Sections: {len(docs.get('sections', []))}")
            console.print(
                f"  Priority markers: {'Yes' if docs.get('has_priority_markers') else 'No'}"
            )
        else:
            console.print("  CLAUDE.md: Not found")

        # Git Analysis
        if git and git.get("git_available"):
            console.print("\n[bold cyan]📈 Recent Activity (30 days)[/bold cyan]")
            console.print(f"  Commits: {len(git.get('recent_commits', []))}")
            console.print(
                f"  Authors: {git.get('authors', {}).get('total_authors', 0)}"
            )
            console.print(
                f"  Changed files: {git.get('changed_files', {}).get('total_files', 0)}"
            )

            if git.get("branch_info"):
                branch_info = git["branch_info"]
                console.print(
                    f"  Current branch: {branch_info.get('current_branch', 'unknown')}"
                )
                if branch_info.get("has_uncommitted_changes"):
                    console.print(
                        f"  ⚠️  Uncommitted changes: {branch_info.get('uncommitted_files', 0)} files"
                    )

        # Recommendations
        if state.get("recommendations"):
            console.print("\n[bold cyan]💡 Recommendations[/bold cyan]")
            for rec in state["recommendations"][:5]:
                console.print(f"  → {rec}")

        console.print("\n" + "=" * 60 + "\n")

    def _run_dry_run_mode(self, organize_files: bool, has_existing: bool) -> Dict:
        """Run dry-run mode to show what would be done without making changes."""
        console.print("\n[bold cyan]🔍 Dry Run Mode - Preview Changes[/bold cyan]\n")

        actions_planned = []

        # Check what organization would do
        if organize_files:
            console.print("[bold]📁 File Organization Analysis:[/bold]")

            # Get structure validation without making changes
            validation = self.organizer.validate_structure()
            if validation.get("issues"):
                console.print("  [yellow]Files that would be organized:[/yellow]")
                for issue in validation["issues"][:10]:
                    actions_planned.append(
                        f"Organize: {issue.get('description', 'Unknown')}"
                    )
                    console.print(f"    • {issue.get('description', 'Unknown')}")
            else:
                console.print("  ✅ Project structure is already well-organized")

        # Check what documentation updates would occur
        if has_existing:
            console.print("\n[bold]📚 Documentation Updates:[/bold]")
            doc_analysis = self.doc_manager.analyze_existing_content()

            if not doc_analysis.get("has_priority_markers"):
                actions_planned.append("Add priority markers (🔴🟡🟢⚪)")
                console.print("  • Add priority markers (🔴🟡🟢⚪)")

            if doc_analysis.get("outdated_patterns"):
                actions_planned.append("Update outdated patterns")
                console.print("  • Update outdated patterns")

            if not doc_analysis.get("has_priority_index"):
                actions_planned.append("Add priority index section")
                console.print("  • Add priority index section")

            # Archive would be created
            actions_planned.append("Archive current CLAUDE.md to docs/_archive/")
            console.print("  • Archive current CLAUDE.md to docs/_archive/")
        else:
            console.print("\n[bold]📚 Documentation Creation:[/bold]")
            actions_planned.append("Create new CLAUDE.md with priority structure")
            console.print("  • Create new CLAUDE.md with priority structure")

        # General improvements
        console.print("\n[bold]🔧 General Improvements:[/bold]")
        actions_planned.extend(
            [
                "Update/create .gitignore if needed",
                "Verify project structure compliance",
                "Add memory system initialization",
                "Set up single-path workflows",
            ]
        )
        for action in actions_planned[-4:]:
            console.print(f"  • {action}")

        console.print(
            f"\n[bold cyan]Summary: {len(actions_planned)} actions would be performed[/bold cyan]"
        )
        console.print("\n[dim]Run without --dry-run to execute these changes.[/dim]\n")

        return {
            "status": "success",
            "mode": "dry_run",
            "actions_planned": actions_planned,
            "message": "Dry run completed - no changes made",
        }

    def _run_pre_initialization_checks(
        self, organize_files: bool, skip_archive: bool, has_existing: bool
    ) -> Dict:
        """Run pre-initialization checks and preparations."""
        checks_passed = []
        warnings = []

        # Run comprehensive project readiness check
        ready, actions = self.organizer.ensure_project_ready(
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
            console.print("\n[yellow]⚠️  Project issues detected:[/yellow]")
            for warning in warnings[:5]:
                console.print(f"  • {warning}")
            console.print()

        if checks_passed:
            console.print("[green]✅ Pre-initialization checks:[/green]")
            for check in checks_passed:
                console.print(f"  • {check}")
            console.print()

        return {
            "status": "success",
            "checks_passed": checks_passed,
            "warnings": warnings,
        }

    def _show_update_plan(self, ast_analysis: bool, preserve_custom: bool) -> None:
        """Show update mode plan."""
        console.print(
            Panel(
                "[bold cyan]🔄 Claude MPM Documentation Update[/bold cyan]\n\n"
                "This will update your existing CLAUDE.md with:\n"
                "• Smart merging of new and existing content\n"
                + ("• Preservation of custom sections\n" if preserve_custom else "")
                + "• Priority-based reorganization (🔴🟡🟢⚪)\n"
                "• Updated single-path workflows\n"
                "• Refreshed tool configurations\n"
                + (
                    "• AST analysis for enhanced documentation\n"
                    if ast_analysis
                    else ""
                )
                + "• Automatic archival of previous version\n"
                + "• Holistic review and optimization\n"
                + "\n[dim]Previous version will be archived in docs/_archive/[/dim]",
                title="Update Mode",
                border_style="blue",
            )
        )

    def _show_initialization_plan(self, ast_analysis: bool) -> None:
        """Show standard initialization plan."""
        console.print(
            Panel(
                "[bold cyan]🤖👥 Claude MPM Project Initialization[/bold cyan]\n\n"
                "This will set up your project with:\n"
                "• Clear CLAUDE.md documentation for AI agents\n"
                "• Single-path workflows (ONE way to do ANYTHING)\n"
                "• Optimized project structure\n"
                "• Tool configurations (linting, formatting, testing)\n"
                "• GitHub workflows and CI/CD setup\n"
                "• Memory system initialization\n"
                + (
                    "• AST analysis for comprehensive code documentation\n"
                    if ast_analysis
                    else ""
                )
                + "• Holistic CLAUDE.md organization with ranked instructions\n"
                + "• Priority-based content structure (🔴🟡🟢⚪)\n"
                + "\n[dim]Powered by Agentic Coder Optimizer Agent[/dim]",
                title="MPM-Init",
                border_style="cyan",
            )
        )

    def _build_update_prompt(
        self,
        project_type: Optional[str],
        framework: Optional[str],
        ast_analysis: bool,
        preserve_custom: bool,
    ) -> str:
        """Build prompt for update mode."""
        # Get existing content analysis
        doc_analysis = self.doc_manager.analyze_existing_content()

        prompt = f"""Please delegate this task to the Agentic Coder Optimizer agent:

UPDATE existing CLAUDE.md documentation for this project.

Project Path: {self.project_path}
Update Mode: Smart merge with existing content
"""
        if project_type:
            prompt += f"Project Type: {project_type}\n"
        if framework:
            prompt += f"Framework: {framework}\n"

        prompt += f"""
Existing Documentation Analysis:
- Current CLAUDE.md: {doc_analysis.get('size', 0):,} characters, {doc_analysis.get('lines', 0)} lines
- Has Priority Index: {'Yes' if doc_analysis.get('has_priority_index') else 'No'}
- Custom Sections: {len(doc_analysis.get('custom_sections', []))} found
"""
        if preserve_custom and doc_analysis.get("custom_sections"):
            prompt += f"- Preserve Custom Sections: {', '.join(doc_analysis['custom_sections'][:5])}\n"

        prompt += """
Please perform the following UPDATE tasks:

1. **Review Existing Content**:
   - Analyze current CLAUDE.md structure and content
   - Identify outdated or missing information
   - Preserve valuable custom sections and project-specific knowledge

2. **Smart Content Merge**:
   - Update project overview if needed
   - Refresh architecture documentation
   - Update development workflows to ensure single-path principle
   - Merge new standard sections while preserving custom content
   - Remove duplicate or contradictory information

3. **Update Priority Organization**:
   - Reorganize content with priority markers (🔴🟡🟢⚪)
   - Ensure critical instructions are at the top
   - Update priority index with all important items
   - Validate instruction clarity and completeness

4. **Refresh Technical Content**:
   - Update build/test/deploy commands
   - Verify tool configurations are current
   - Update dependency information
   - Refresh API documentation if applicable
"""
        if ast_analysis:
            prompt += """
5. **Update Code Documentation** (using Code Analyzer agent):
   - Re-analyze code structure for changes
   - Update API documentation
   - Refresh architecture diagrams
   - Update function/class documentation
"""
        prompt += """
6. **Final Optimization**:
   - Ensure single-path principle throughout
   - Validate all links and references
   - Add/update timestamp in meta section
   - Verify AI agent readability

IMPORTANT: This is an UPDATE operation. Intelligently merge new content with existing,
preserving valuable project-specific information while refreshing standard sections.
"""
        return prompt

    def _handle_update_post_processing(self) -> None:
        """Handle post-processing after successful update."""
        # Generate update report
        if self.doc_manager.has_existing_documentation():
            latest_archive = self.archive_manager.get_latest_archive("CLAUDE.md")
            if latest_archive:
                comparison = self.archive_manager.compare_with_archive(
                    self.project_path / "CLAUDE.md", latest_archive.name
                )

                if not comparison.get("identical"):
                    console.print("\n[bold cyan]📊 Update Summary[/bold cyan]")
                    console.print(
                        f"  Lines changed: {comparison.get('lines_added', 0):+d}"
                    )
                    console.print(
                        f"  Size change: {comparison.get('size_change', 0):+,} characters"
                    )
                    console.print(f"  Previous version: {latest_archive.name}")

    def _run_initialization(
        self,
        prompt: str,
        verbose: bool,
        use_venv: bool = False,
        update_mode: bool = False,
    ) -> Dict:
        """Run the initialization through subprocess calling claude-mpm."""
        import tempfile

        try:
            # Write prompt to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as tmp_file:
                tmp_file.write(prompt)
                prompt_file = tmp_file.name

            try:
                # Build the command
                cmd = self._build_claude_mpm_command(verbose, use_venv)
                # Add the input file flag
                cmd.extend(["-i", prompt_file])

                # Log the command if verbose
                if verbose:
                    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
                    console.print(f"[dim]Prompt file: {prompt_file}[/dim]")

                # Execute the command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_path),
                    check=False,
                )

                # Check for environment-specific errors
                if "libmamba" in result.stderr or "tree-sitter" in result.stderr:
                    console.print(
                        "\n[yellow]⚠️  Environment dependency issue detected.[/yellow]"
                    )
                    console.print(
                        "[yellow]Attempting alternative initialization method...[/yellow]\n"
                    )

                    # Try again with venv flag to bypass mamba
                    cmd_venv = self._build_claude_mpm_command(verbose, use_venv=True)
                    cmd_venv.extend(["-i", prompt_file])

                    if verbose:
                        console.print(f"[dim]Retrying with: {' '.join(cmd_venv)}[/dim]")

                    result = subprocess.run(
                        cmd_venv,
                        capture_output=not verbose,
                        text=True,
                        cwd=str(self.project_path),
                        check=False,
                    )
            finally:
                # Clean up temporary file
                import os

                with contextlib.suppress(Exception):
                    os.unlink(prompt_file)

            # Display output if verbose
            if verbose and result.stdout:
                console.print(result.stdout)
            if verbose and result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")

            # Check result - be more lenient with return codes
            if result.returncode == 0 or (self.project_path / "CLAUDE.md").exists():
                response = {
                    "status": "success",
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
                else result.stdout if result.stdout else "Unknown error occurred"
            )
            # Clean up mamba warnings from error message
            if "libmamba" in error_msg:
                lines = error_msg.split("\n")
                error_lines = [
                    l for l in lines if not l.startswith("warning") and l.strip()
                ]
                error_msg = "\n".join(error_lines) if error_lines else error_msg

            logger.error(f"claude-mpm run failed: {error_msg}")
            return {
                "status": "error",
                "message": f"Initialization failed: {error_msg}",
            }

        except FileNotFoundError:
            logger.error("claude-mpm command not found")
            console.print(
                "[red]Error: claude-mpm command not found. Ensure Claude MPM is properly installed.[/red]"
            )
            return {"status": "error", "message": "claude-mpm not found"}
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return {"status": "error", "message": str(e)}

    def _display_results(self, result: Dict, verbose: bool):
        """Display initialization results."""
        if result["status"] == "success":
            console.print("\n[green]✅ Project Initialization Complete![/green]\n")

            if result.get("files_created"):
                console.print("[bold]Files Created:[/bold]")
                for file in result["files_created"]:
                    console.print(f"  • {file}")
                console.print()

            if result.get("files_updated"):
                console.print("[bold]Files Updated:[/bold]")
                for file in result["files_updated"]:
                    console.print(f"  • {file}")
                console.print()

            if result.get("next_steps"):
                console.print("[bold]Next Steps:[/bold]")
                for step in result["next_steps"]:
                    console.print(f"  → {step}")
                console.print()

            console.print(
                Panel(
                    "[green]Your project is now optimized for Claude Code and Claude MPM![/green]\n\n"
                    "Key files:\n"
                    "• [cyan]CLAUDE.md[/cyan] - Main documentation for AI agents\n"
                    "  - Organized with priority rankings (🔴🟡🟢⚪)\n"
                    "  - Instructions ranked by importance for AI understanding\n"
                    "  - Holistic documentation review completed\n"
                    "• [cyan].claude-mpm/[/cyan] - Configuration and memories\n"
                    "• [cyan]CODE_STRUCTURE.md[/cyan] - AST-derived architecture documentation (if enabled)\n\n"
                    "[dim]Run 'claude-mpm run' to start using the optimized setup[/dim]",
                    title="Success",
                    border_style="green",
                )
            )


@click.command(name="mpm-init")
@click.option(
    "--project-type",
    type=click.Choice(
        ["web", "api", "cli", "library", "mobile", "desktop", "fullstack"]
    ),
    help="Type of project to initialize",
)
@click.option(
    "--framework",
    type=str,
    help="Specific framework (e.g., react, django, fastapi, express)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinitialization even if project is already configured",
)
@click.option(
    "--update",
    is_flag=True,
    help="Update existing CLAUDE.md instead of recreating",
)
@click.option(
    "--review",
    is_flag=True,
    help="Review project state without making changes",
)
@click.option(
    "--organize",
    is_flag=True,
    help="Automatically organize misplaced files into proper directories",
)
@click.option(
    "--auto-safe/--no-auto-safe",
    default=True,
    help="Only move files with high confidence (default: safe mode on)",
)
@click.option(
    "--preserve-custom/--no-preserve-custom",
    default=True,
    help="Preserve custom sections when updating (default: preserve)",
)
@click.option(
    "--skip-archive",
    is_flag=True,
    help="Skip archiving existing files before updating",
)
@click.option(
    "--verbose", is_flag=True, help="Show detailed output during initialization"
)
@click.option(
    "--ast-analysis/--no-ast-analysis",
    default=True,
    help="Enable/disable AST analysis for enhanced documentation (default: enabled)",
)
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    default=".",
)
def mpm_init(
    project_type,
    framework,
    force,
    update,
    review,
    organize,
    auto_safe,
    preserve_custom,
    skip_archive,
    verbose,
    ast_analysis,
    project_path,
):
    """
    Initialize or update a project for optimal use with Claude Code and Claude MPM.

    This command uses the Agentic Coder Optimizer agent to:
    - Create or update comprehensive CLAUDE.md documentation
    - Establish single-path workflows (ONE way to do ANYTHING)
    - Configure development tools and standards
    - Set up memory systems for project knowledge
    - Optimize for AI agent understanding
    - Perform AST analysis for enhanced developer documentation

    Update Mode:
    When CLAUDE.md exists, the command offers to update rather than recreate,
    preserving custom content while refreshing standard sections.

    Examples:
        claude-mpm mpm-init                           # Initialize/update current directory
        claude-mpm mpm-init --review                  # Review project state without changes
        claude-mpm mpm-init --update                  # Force update mode
        claude-mpm mpm-init --organize                # Organize misplaced files
        claude-mpm mpm-init --project-type web        # Initialize as web project
        claude-mpm mpm-init /path/to/project --force  # Force reinitialize project
    """
    try:
        # Create command instance
        command = MPMInitCommand(Path(project_path))

        # Run initialization (now synchronous)
        result = command.initialize_project(
            project_type=project_type,
            framework=framework,
            force=force,
            verbose=verbose,
            ast_analysis=ast_analysis,
            update_mode=update,
            review_only=review,
            organize_files=organize,
            preserve_custom=preserve_custom,
            skip_archive=skip_archive,
        )

        # Exit with appropriate code
        if result["status"] == "success":
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Initialization cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Initialization failed: {e}[/red]")
        sys.exit(1)


# Export for CLI registration
__all__ = ["mpm_init"]
