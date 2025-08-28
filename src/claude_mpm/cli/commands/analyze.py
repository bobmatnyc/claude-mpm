"""
Code analysis command implementation for claude-mpm.

WHY: This module provides code analysis capabilities with mermaid diagram
generation, allowing users to visualize and understand their codebase
architecture through automated analysis.

DESIGN DECISIONS:
- Use async for better performance with multiple diagram generation
- Extract mermaid blocks from agent responses automatically
- Save diagrams with timestamps for versioning
- Support multiple diagram types in single run
- Integrate with existing session management
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ...core.logging_config import get_logger
from ...services.cli.session_manager import SessionManager
from ..shared import BaseCommand, CommandResult


class AnalyzeCommand(BaseCommand):
    """Analyze command for code analysis with mermaid generation."""

    def __init__(self):
        super().__init__("analyze")
        self.logger = get_logger(__name__)
        self.session_manager = SessionManager()

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments.

        Args:
            args: Command arguments

        Returns:
            Error message if validation fails, None otherwise
        """
        # Validate target exists
        if not args.target.exists():
            return f"Target path does not exist: {args.target}"

        # Validate diagram output directory if saving
        if args.save_diagrams:
            diagram_dir = args.diagram_output or Path("./diagrams")
            if not diagram_dir.exists():
                try:
                    diagram_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return f"Cannot create diagram output directory: {e}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the analyze command.

        Args:
            args: Command arguments

        Returns:
            CommandResult with analysis results
        """
        try:
            # Run async analysis
            return asyncio.run(self._run_analysis(args))
        except KeyboardInterrupt:
            return CommandResult.error_result("Analysis interrupted by user")
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)
            return CommandResult.error_result(f"Analysis failed: {e}")

    async def _run_analysis(self, args) -> CommandResult:
        """Run the actual analysis asynchronously.

        Args:
            args: Command arguments

        Returns:
            CommandResult with analysis results
        """
        # Build analysis prompt
        prompt = self._build_analysis_prompt(args)

        # Setup session if needed
        session_id = None
        if not args.no_session:
            session_id = args.session_id or self._create_analysis_session()

        # Execute analysis via agent
        self.logger.info(f"Starting code analysis of {args.target}")
        response = await self._execute_agent_analysis(
            agent=args.agent, prompt=prompt, session_id=session_id, args=args
        )

        if not response:
            return CommandResult.error_result("No response from analysis agent")

        # Extract mermaid diagrams if enabled
        diagrams = []
        if args.mermaid:
            diagrams = self._extract_mermaid_diagrams(response)

            if args.save_diagrams:
                saved_files = self._save_diagrams(diagrams, args)
                self.logger.info(f"Saved {len(saved_files)} diagrams")

        # Format and return results
        result_data = {
            "target": str(args.target),
            "analysis": response,
            "diagrams_found": len(diagrams),
            "session_id": session_id,
        }

        if args.save_diagrams and diagrams:
            result_data["saved_diagrams"] = [str(f) for f in saved_files]

        # Handle output format
        output = self._format_output(result_data, args.format, diagrams)

        # Save to file if requested
        if args.output:
            self._save_output(output, args.output)

        return CommandResult.success_result(
            message=output if args.format == "text" else "Analysis completed",
            data=result_data,
        )

    def _build_analysis_prompt(self, args) -> str:
        """Build the analysis prompt based on arguments.

        Args:
            args: Command arguments

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Base analysis request
        prompt_parts.append(f"Analyze the code at: {args.target}")

        # Add custom prompt if provided
        if args.prompt:
            prompt_parts.append(f"\n{args.prompt}")

        # Add focus areas
        if args.focus:
            focus_list = args.focus if isinstance(args.focus, list) else [args.focus]
            focus_str = ", ".join(focus_list)
            prompt_parts.append(f"\nFocus on: {focus_str}")

        # Add mermaid diagram requests
        if args.mermaid:
            types_list = (
                args.mermaid_types
                if isinstance(args.mermaid_types, list)
                else [args.mermaid_types]
            )
            diagram_types = ", ".join(types_list)
            prompt_parts.append(
                f"\nGenerate mermaid diagrams for: {diagram_types}\n"
                "Ensure each diagram is in a separate ```mermaid code block."
            )

            # Add specific instructions per diagram type
            diagram_instructions = self._get_diagram_instructions(args.mermaid_types)
            if diagram_instructions:
                prompt_parts.append(diagram_instructions)

        return "\n".join(prompt_parts)

    def _get_diagram_instructions(self, diagram_types: List[str]) -> str:
        """Get specific instructions for requested diagram types.

        Args:
            diagram_types: List of diagram types

        Returns:
            Formatted instructions string
        """
        instructions = []

        type_instructions = {
            "entry_points": "Identify and map all entry points in the codebase",
            "class_diagram": "Create UML class diagrams showing relationships",
            "sequence": "Show sequence diagrams for key workflows",
            "flowchart": "Create flowcharts for main processes",
            "state": "Show state diagrams for stateful components",
            "entity_relationship": "Map database entities and relationships",
            "component": "Show high-level component architecture",
            "dependency_graph": "Map module and package dependencies",
            "call_graph": "Show function/method call relationships",
            "architecture": "Create overall system architecture diagram",
        }

        for dtype in diagram_types:
            if dtype in type_instructions:
                instructions.append(f"- {type_instructions[dtype]}")

        if instructions:
            return "\nDiagram requirements:\n" + "\n".join(instructions)
        return ""

    async def _execute_agent_analysis(
        self, agent: str, prompt: str, session_id: Optional[str], args
    ) -> Optional[str]:
        """Execute analysis using the specified agent.

        Args:
            agent: Agent ID to use
            prompt: Analysis prompt
            session_id: Session ID if using sessions
            args: Command arguments

        Returns:
            Agent response text or None if failed
        """
        try:
            # Import required modules
            from ...core.claude_runner import ClaudeRunner
            from ...services.agents.deployment.agent_deployment import (
                AgentDeploymentService,
            )

            # Deploy the analysis agent if not already deployed
            deployment_service = AgentDeploymentService()
            deployment_result = deployment_service.deploy_agent(agent, force=False)

            if not deployment_result["success"]:
                self.logger.error(
                    f"Failed to deploy agent {agent}: {deployment_result.get('error')}"
                )
                return None

            # Create a temporary file with the prompt
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # Build Claude args for analysis
                claude_args = []

                # Add input file
                claude_args.extend(["--input", prompt_file])

                # Add session if specified
                if session_id:
                    claude_args.extend(["--session", session_id])

                # Set working directory
                claude_args.extend(["--cwd", str(args.target)])

                # Disable hooks for cleaner output capture
                no_hooks = True

                # Initialize and run Claude runner
                ClaudeRunner(
                    enable_tickets=False,
                    launch_method="subprocess",
                    claude_args=claude_args,
                )

                # Set up environment
                env = os.environ.copy()
                env["CLAUDE_MPM_AGENT"] = agent

                # Build the full command
                scripts_dir = (
                    Path(__file__).parent.parent.parent.parent.parent / "scripts"
                )
                claude_mpm_script = scripts_dir / "claude-mpm"

                cmd = []
                if claude_mpm_script.exists():
                    cmd = [str(claude_mpm_script)]
                else:
                    # Fallback to using module execution
                    cmd = [sys.executable, "-m", "claude_mpm"]

                # Add subcommand and options
                cmd.extend(["run", "--no-tickets", "--input", prompt_file])

                if no_hooks:
                    cmd.append("--no-hooks")

                # Execute the command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(args.target),
                    env=env,
                    timeout=600,
                    check=False,  # 10 minute timeout
                )

                if result.returncode != 0:
                    self.logger.error(f"Claude execution failed: {result.stderr}")
                    # Return stdout even on error as it may contain partial results
                    return result.stdout if result.stdout else result.stderr

                return result.stdout

            finally:
                # Clean up temp file
                Path(prompt_file).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            self.logger.error("Analysis timed out after 10 minutes")
            return None
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}", exc_info=True)
            return None

    def _extract_mermaid_diagrams(self, response: str) -> List[Dict[str, str]]:
        """Extract mermaid diagram blocks from response.

        Args:
            response: Agent response text

        Returns:
            List of diagram dictionaries with content and optional titles
        """
        diagrams = []

        # Pattern to match mermaid code blocks
        pattern = r"```mermaid\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        for i, match in enumerate(matches):
            # Try to extract title from preceding line
            title = f"diagram_{i+1}"

            # Look for a title pattern before the diagram
            title_pattern = r"(?:#+\s*)?([^\n]+)\n+```mermaid"
            title_matches = re.findall(title_pattern, response)
            if i < len(title_matches):
                title = self._sanitize_filename(title_matches[i])

            diagrams.append({"title": title, "content": match.strip(), "index": i + 1})

        self.logger.info(f"Extracted {len(diagrams)} mermaid diagrams")
        return diagrams

    def _save_diagrams(self, diagrams: List[Dict[str, str]], args) -> List[Path]:
        """Save mermaid diagrams to files.

        Args:
            diagrams: List of diagram dictionaries
            args: Command arguments

        Returns:
            List of saved file paths
        """
        saved_files = []
        diagram_dir = args.diagram_output or Path("./diagrams")
        diagram_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for diagram in diagrams:
            filename = f"{timestamp}_{diagram['title']}.mermaid"
            filepath = diagram_dir / filename

            try:
                with open(filepath, "w") as f:
                    # Write mermaid header comment
                    f.write("// Generated by Claude MPM Code Analyzer\n")
                    f.write(f"// Timestamp: {timestamp}\n")
                    f.write(f"// Target: {args.target}\n")
                    f.write(f"// Title: {diagram['title']}\n\n")
                    f.write(diagram["content"])

                saved_files.append(filepath)
                self.logger.debug(f"Saved diagram to {filepath}")

            except Exception as e:
                self.logger.error(f"Failed to save diagram {diagram['title']}: {e}")

        return saved_files

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a string to be safe for filename.

        Args:
            title: Original title string

        Returns:
            Sanitized filename string
        """
        # Remove or replace unsafe characters
        safe_chars = re.sub(r"[^\w\s-]", "", title)
        safe_chars = re.sub(r"[-\s]+", "_", safe_chars)
        return safe_chars[:50].strip("_").lower()

    def _format_output(
        self, result_data: Dict, format_type: str, diagrams: List[Dict]
    ) -> str:
        """Format output based on requested format.

        Args:
            result_data: Analysis results
            format_type: Output format (text, json, markdown)
            diagrams: List of extracted diagrams

        Returns:
            Formatted output string
        """
        if format_type == "json":
            result_data["diagrams"] = diagrams
            return json.dumps(result_data, indent=2)

        if format_type == "markdown":
            output = "# Code Analysis Report\n\n"
            output += f"**Target:** `{result_data['target']}`\n"
            output += f"**Timestamp:** {datetime.now().isoformat()}\n"

            if result_data.get("session_id"):
                output += f"**Session ID:** {result_data['session_id']}\n"

            output += "\n## Analysis Results\n\n"
            output += result_data.get("analysis", "No analysis results")

            if diagrams:
                output += f"\n## Generated Diagrams ({len(diagrams)})\n\n"
                for diagram in diagrams:
                    output += f"### {diagram['title']}\n\n"
                    output += f"```mermaid\n{diagram['content']}\n```\n\n"

            if result_data.get("saved_diagrams"):
                output += "\n## Saved Files\n\n"
                for filepath in result_data["saved_diagrams"]:
                    output += f"- `{filepath}`\n"

            return output

        # text format
        output = f"Code Analysis Report\n{'='*50}\n\n"
        output += f"Target: {result_data['target']}\n"

        if diagrams:
            output += f"\n📊 Extracted {len(diagrams)} mermaid diagrams:\n"
            for diagram in diagrams:
                output += f"  • {diagram['title']}\n"

        if result_data.get("saved_diagrams"):
            output += "\n💾 Saved diagrams to:\n"
            for filepath in result_data["saved_diagrams"]:
                output += f"  • {filepath}\n"

        output += f"\n{'-'*50}\nAnalysis Results:\n{'-'*50}\n"
        output += result_data.get("analysis", "No analysis results")

        return output

    def _save_output(self, content: str, filepath: Path):
        """Save output content to file.

        Args:
            content: Content to save
            filepath: Target file path
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(content)
            self.logger.info(f"Saved output to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save output: {e}")

    def _create_analysis_session(self) -> str:
        """Create a new analysis session.

        Returns:
            Session ID
        """
        session_data = {
            "context": "code_analysis",
            "created_at": datetime.now().isoformat(),
            "type": "analysis",
        }
        session_id = self.session_manager.create_session(session_data)
        self.logger.debug(f"Created analysis session: {session_id}")
        return session_id


def analyze_command(args):
    """Entry point for analyze command.

    WHY: Provides a single entry point for code analysis with mermaid
    diagram generation, helping users visualize and understand their codebase.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    command = AnalyzeCommand()
    result = command.run(args)

    if result.success:
        if args.format == "json":
            print(json.dumps(result.data, indent=2))
        else:
            print(result.message)
        return 0
    print(f"❌ {result.message}", file=sys.stderr)
    return 1


# Optional: Standalone execution for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude MPM Code Analyzer")
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--mermaid", action="store_true")
    parser.add_argument("--mermaid-types", nargs="+", default=["entry_points"])
    parser.add_argument("--save-diagrams", action="store_true")
    parser.add_argument("--diagram-output", type=Path)
    parser.add_argument("--agent", default="code-analyzer")
    parser.add_argument("--prompt", type=str)
    parser.add_argument("--focus", nargs="+")
    parser.add_argument("--session-id", type=str)
    parser.add_argument("--no-session", action="store_true")
    parser.add_argument("--format", default="text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    sys.exit(analyze_command(args))
