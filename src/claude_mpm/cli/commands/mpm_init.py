"""
MPM-Init Command - Initialize projects for optimal Claude Code and Claude MPM success.

This command delegates to the Agentic Coder Optimizer agent to establish clear,
single-path project standards for documentation, tooling, and workflows.

Enhanced with AST inspection capabilities for generating comprehensive developer
documentation with code structure analysis.
"""

import contextlib
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)
console = Console()


class MPMInitCommand:
    """Initialize projects for optimal Claude Code and Claude MPM usage."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the MPM-Init command."""
        self.project_path = project_path or Path.cwd()
        self.claude_mpm_script = self._find_claude_mpm_script()

    def initialize_project(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        force: bool = False,
        verbose: bool = False,
        use_venv: bool = False,
        ast_analysis: bool = True,
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

        Returns:
            Dict containing initialization results
        """
        try:
            # Check if project already initialized
            claude_md = self.project_path / "CLAUDE.md"
            if claude_md.exists() and not force:
                console.print("[yellow]⚠️  Project already has CLAUDE.md file.[/yellow]")
                console.print(
                    "[yellow]Use --force to reinitialize the project.[/yellow]"
                )
                return {"status": "cancelled", "message": "Initialization cancelled"}

            # Build the delegation prompt
            prompt = self._build_initialization_prompt(
                project_type, framework, ast_analysis
            )

            # Show initialization plan
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

            # Execute via claude-mpm run command
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Delegating to Agentic Coder Optimizer...", total=None
                )

                # Run the initialization through subprocess
                result = self._run_initialization(prompt, verbose, use_venv)

                progress.update(task, description="[green]✓ Initialization complete")

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

    def _run_initialization(
        self, prompt: str, verbose: bool, use_venv: bool = False
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
def mpm_init(project_type, framework, force, verbose, ast_analysis, project_path):
    """
    Initialize a project for optimal use with Claude Code and Claude MPM.

    This command uses the Agentic Coder Optimizer agent to:
    - Create comprehensive CLAUDE.md documentation
    - Establish single-path workflows (ONE way to do ANYTHING)
    - Configure development tools and standards
    - Set up memory systems for project knowledge
    - Optimize for AI agent understanding
    - Perform AST analysis for enhanced developer documentation

    Examples:
        claude-mpm mpm-init
        claude-mpm mpm-init --project-type web --framework react
        claude-mpm mpm-init /path/to/project --force
        claude-mpm mpm-init --ast-analysis  # Enable AST analysis (default)
        claude-mpm mpm-init --no-ast-analysis  # Disable AST analysis
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
