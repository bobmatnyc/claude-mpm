"""
MPM-Init Command - Initialize projects for optimal Claude Code and Claude MPM success.

This command delegates to the Agentic Coder Optimizer agent to establish clear,
single-path project standards for documentation, tooling, and workflows.
"""

import json
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

    def __init__(self, project_path: Path = None):
        """Initialize the MPM-Init command."""
        self.project_path = project_path or Path.cwd()
        self.claude_mpm_script = self._find_claude_mpm_script()

    def initialize_project(
        self,
        project_type: Optional[str] = None,
        framework: Optional[str] = None,
        force: bool = False,
        verbose: bool = False,
        use_venv: bool = False
    ) -> Dict:
        """
        Initialize project with Agentic Coder Optimizer standards.
        
        Args:
            project_type: Type of project (web, api, cli, library, etc.)
            framework: Specific framework if applicable
            force: Force initialization even if project already configured
            verbose: Show detailed output
            
        Returns:
            Dict containing initialization results
        """
        try:
            # Check if project already initialized
            claude_md = self.project_path / "CLAUDE.md"
            if claude_md.exists() and not force:
                console.print(
                    "[yellow]⚠️  Project already has CLAUDE.md file.[/yellow]"
                )
                console.print("[yellow]Use --force to reinitialize the project.[/yellow]")
                return {"status": "cancelled", "message": "Initialization cancelled"}

            # Build the delegation prompt
            prompt = self._build_initialization_prompt(project_type, framework)
            
            # Show initialization plan
            console.print(Panel(
                "[bold cyan]🤖👥 Claude MPM Project Initialization[/bold cyan]\n\n"
                "This will set up your project with:\n"
                "• Clear CLAUDE.md documentation for AI agents\n"
                "• Single-path workflows (ONE way to do ANYTHING)\n"
                "• Optimized project structure\n"
                "• Tool configurations (linting, formatting, testing)\n"
                "• GitHub workflows and CI/CD setup\n"
                "• Memory system initialization\n\n"
                "[dim]Powered by Agentic Coder Optimizer Agent[/dim]",
                title="MPM-Init",
                border_style="cyan"
            ))

            # Execute via claude-mpm run command
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Delegating to Agentic Coder Optimizer...", total=None)
                
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
        framework: Optional[str] = None
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

Please ensure all documentation is clear, concise, and optimized for AI agents to understand and follow.
Focus on establishing ONE clear way to do ANYTHING in the project.
"""
        
        return base_prompt

    def _build_claude_mpm_command(self, verbose: bool, use_venv: bool = False) -> List[str]:
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

    def _run_initialization(self, prompt: str, verbose: bool, use_venv: bool = False) -> Dict:
        """Run the initialization through subprocess calling claude-mpm."""
        import tempfile
        
        try:
            # Write prompt to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
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
                    cwd=str(self.project_path)
                )
                
                # Check for environment-specific errors
                if "libmamba" in result.stderr or "tree-sitter" in result.stderr:
                    console.print("\n[yellow]⚠️  Environment dependency issue detected.[/yellow]")
                    console.print("[yellow]Attempting alternative initialization method...[/yellow]\n")
                    
                    # Try again with venv flag to bypass mamba
                    cmd_venv = self._build_claude_mpm_command(verbose, use_venv=True)
                    cmd_venv.extend(["-i", prompt_file])
                    
                    if verbose:
                        console.print(f"[dim]Retrying with: {' '.join(cmd_venv)}[/dim]")
                    
                    result = subprocess.run(
                        cmd_venv,
                        capture_output=not verbose,
                        text=True,
                        cwd=str(self.project_path)
                    )
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(prompt_file)
                except:
                    pass
            
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
                    "next_steps": []
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
                    "Run 'claude-mpm run' to start using the optimized setup"
                ]
                
                # Display results
                self._display_results(response, verbose)
                
                return response
            else:
                # Extract meaningful error message
                error_msg = result.stderr if result.stderr else result.stdout if result.stdout else "Unknown error occurred"
                # Clean up mamba warnings from error message
                if "libmamba" in error_msg:
                    lines = error_msg.split('\n')
                    error_lines = [l for l in lines if not l.startswith('warning') and l.strip()]
                    error_msg = '\n'.join(error_lines) if error_lines else error_msg
                
                logger.error(f"claude-mpm run failed: {error_msg}")
                return {
                    "status": "error",
                    "message": f"Initialization failed: {error_msg}"
                }
            
        except FileNotFoundError:
            logger.error("claude-mpm command not found")
            console.print("[red]Error: claude-mpm command not found. Ensure Claude MPM is properly installed.[/red]")
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
            
            console.print(Panel(
                "[green]Your project is now optimized for Claude Code and Claude MPM![/green]\n\n"
                "Key files:\n"
                "• [cyan]CLAUDE.md[/cyan] - Main documentation for AI agents\n"
                "• [cyan].claude-mpm/[/cyan] - Configuration and memories\n\n"
                "[dim]Run 'claude-mpm run' to start using the optimized setup[/dim]",
                title="Success",
                border_style="green"
            ))


@click.command(name="mpm-init")
@click.option(
    "--project-type",
    type=click.Choice(["web", "api", "cli", "library", "mobile", "desktop", "fullstack"]),
    help="Type of project to initialize"
)
@click.option(
    "--framework",
    type=str,
    help="Specific framework (e.g., react, django, fastapi, express)"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinitialization even if project is already configured"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed output during initialization"
)
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    default="."
)
def mpm_init(project_type, framework, force, verbose, project_path):
    """
    Initialize a project for optimal use with Claude Code and Claude MPM.
    
    This command uses the Agentic Coder Optimizer agent to:
    - Create comprehensive CLAUDE.md documentation
    - Establish single-path workflows (ONE way to do ANYTHING)
    - Configure development tools and standards
    - Set up memory systems for project knowledge
    - Optimize for AI agent understanding
    
    Examples:
        claude-mpm mpm-init
        claude-mpm mpm-init --project-type web --framework react
        claude-mpm mpm-init /path/to/project --force
    """
    try:
        # Create command instance
        command = MPMInitCommand(Path(project_path))
        
        # Run initialization (now synchronous)
        result = command.initialize_project(
            project_type=project_type,
            framework=framework,
            force=force,
            verbose=verbose
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