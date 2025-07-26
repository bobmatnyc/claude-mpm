# Slash Command Example: /commit

This example demonstrates how to implement a slash command following awesome-claude-code patterns.

## Command Definition

```markdown
# Claude Command: Commit

Create well-formatted commits with conventional commit messages and emoji.

## Usage

```
/commit [options]
/commit --no-verify
/commit --split
```

## Options

- `--no-verify`: Skip pre-commit checks
- `--split`: Force splitting into atomic commits
- `--type <type>`: Specify commit type (feat, fix, docs, etc.)

## What This Command Does

1. Run pre-commit checks (unless --no-verify)
2. Analyze staged changes
3. Determine appropriate commit type
4. Generate conventional commit message
5. Add relevant emoji
6. Optionally split into atomic commits
```

## Python Implementation

```python
# src/claude_mpm/commands/handlers/commit_command.py
from typing import List, Dict, Optional
from pathlib import Path
import subprocess
import re

class CommitCommand(BaseSlashCommand):
    """Smart conventional commit command."""
    
    name = "commit"
    description = "Create conventional commits with emoji"
    
    # Emoji mapping for commit types
    COMMIT_EMOJIS = {
        "feat": "✨",
        "fix": "🐛",
        "docs": "📝",
        "style": "💄",
        "refactor": "♻️",
        "perf": "⚡️",
        "test": "✅",
        "chore": "🔧",
        "build": "🏗️",
        "ci": "👷",
        "revert": "⏪️"
    }
    
    async def execute(self, args: List[str], context: CommandContext) -> CommandResult:
        """Execute the commit command."""
        # Parse arguments
        options = self._parse_args(args)
        
        # Step 1: Run pre-commit checks
        if not options.get("no_verify"):
            check_result = await self._run_pre_commit_checks()
            if not check_result.success:
                return CommandResult(
                    success=False,
                    message="Pre-commit checks failed. Use --no-verify to skip."
                )
        
        # Step 2: Get staged changes
        changes = await self._get_staged_changes()
        if not changes:
            # Auto-stage all changes
            await self._stage_all_changes()
            changes = await self._get_staged_changes()
            
        if not changes:
            return CommandResult(
                success=False,
                message="No changes to commit"
            )
        
        # Step 3: Analyze changes
        analysis = await self._analyze_changes(changes)
        
        # Step 4: Determine if we should split
        if options.get("split") or self._should_split_commits(analysis):
            return await self._create_split_commits(analysis)
        
        # Step 5: Create single commit
        commit_type = options.get("type") or analysis["primary_type"]
        message = await self._generate_commit_message(commit_type, analysis)
        
        return await self._create_commit(message)
    
    async def _run_pre_commit_checks(self) -> CommandResult:
        """Run pre-commit validation checks."""
        checks = [
            ("Linting", "pnpm lint"),
            ("Building", "pnpm build"),
            ("Testing", "pnpm test"),
            ("Docs", "pnpm generate:docs")
        ]
        
        for check_name, command in checks:
            result = subprocess.run(command, shell=True, capture_output=True)
            if result.returncode != 0:
                return CommandResult(
                    success=False,
                    message=f"{check_name} failed: {result.stderr.decode()}"
                )
                
        return CommandResult(success=True)
    
    async def _analyze_changes(self, changes: Dict[str, List[str]]) -> Dict:
        """Analyze changes to determine commit type and scope."""
        analysis = {
            "files": changes,
            "types_detected": [],
            "scopes": set(),
            "primary_type": "chore",
            "description_hints": []
        }
        
        # Analyze file patterns
        for file_path in changes.get("modified", []):
            path = Path(file_path)
            
            # Detect type from path
            if "test" in path.parts or path.name.startswith("test_"):
                analysis["types_detected"].append("test")
            elif path.suffix == ".md" or "docs" in path.parts:
                analysis["types_detected"].append("docs")
            elif "src" in path.parts:
                # Check if it's a new feature or fix
                diff = self._get_file_diff(file_path)
                if self._is_new_feature(diff):
                    analysis["types_detected"].append("feat")
                elif self._is_bug_fix(diff):
                    analysis["types_detected"].append("fix")
                else:
                    analysis["types_detected"].append("refactor")
            
            # Extract scope from path
            if "src" in path.parts and len(path.parts) > 2:
                scope = path.parts[path.parts.index("src") + 1]
                analysis["scopes"].add(scope)
        
        # Determine primary type
        if "feat" in analysis["types_detected"]:
            analysis["primary_type"] = "feat"
        elif "fix" in analysis["types_detected"]:
            analysis["primary_type"] = "fix"
        elif "test" in analysis["types_detected"]:
            analysis["primary_type"] = "test"
        elif "docs" in analysis["types_detected"]:
            analysis["primary_type"] = "docs"
        
        return analysis
    
    async def _generate_commit_message(self, 
                                     commit_type: str, 
                                     analysis: Dict) -> str:
        """Generate conventional commit message with emoji."""
        emoji = self.COMMIT_EMOJIS.get(commit_type, "🔧")
        
        # Generate scope
        scope = ""
        if analysis["scopes"]:
            scope = f"({', '.join(list(analysis['scopes'])[:2])})"
        
        # Generate description
        description = self._summarize_changes(analysis)
        
        # Build message
        message = f"{emoji} {commit_type}{scope}: {description}"
        
        # Add body if complex changes
        if len(analysis["files"].get("modified", [])) > 5:
            body = self._generate_commit_body(analysis)
            message += f"\n\n{body}"
        
        return message
    
    def _should_split_commits(self, analysis: Dict) -> bool:
        """Determine if commits should be split."""
        # Split if multiple distinct types detected
        if len(set(analysis["types_detected"])) > 2:
            return True
            
        # Split if changes span multiple scopes
        if len(analysis["scopes"]) > 3:
            return True
            
        # Split if too many files
        total_files = sum(len(files) for files in analysis["files"].values())
        if total_files > 10:
            return True
            
        return False
    
    async def _create_split_commits(self, analysis: Dict) -> CommandResult:
        """Create multiple atomic commits."""
        commits_created = []
        
        # Group changes by type and scope
        groups = self._group_changes_for_commits(analysis)
        
        for group in groups:
            # Stage only files for this group
            await self._stage_files(group["files"])
            
            # Generate message for this group
            message = await self._generate_commit_message(
                group["type"], 
                group["analysis"]
            )
            
            # Create commit
            result = await self._create_commit(message)
            if result.success:
                commits_created.append(message.split("\n")[0])
            else:
                return CommandResult(
                    success=False,
                    message=f"Failed to create commit: {result.message}"
                )
        
        return CommandResult(
            success=True,
            message=f"Created {len(commits_created)} commits:\n" + 
                   "\n".join(f"  - {msg}" for msg in commits_created)
        )
```

## Integration with Claude MPM

```python
# src/claude_mpm/commands/loader.py
class SlashCommandLoader:
    """Loads and manages slash commands."""
    
    def __init__(self, commands_dir: Path):
        self.commands_dir = commands_dir
        self.commands = {}
        
    def load_commands(self):
        """Load all commands from directory."""
        # Load built-in commands
        self.register_command(CommitCommand())
        
        # Load user-defined commands from .claude/commands/
        for cmd_file in self.commands_dir.glob("*.md"):
            command = self._load_markdown_command(cmd_file)
            self.register_command(command)
    
    def execute_command(self, prompt: str, context: CommandContext) -> Optional[CommandResult]:
        """Execute a slash command if present in prompt."""
        if not prompt.startswith("/"):
            return None
            
        parts = prompt.split()
        command_name = parts[0][1:]  # Remove leading /
        args = parts[1:]
        
        if command_name in self.commands:
            command = self.commands[command_name]
            return command.execute(args, context)
            
        return CommandResult(
            success=False,
            message=f"Unknown command: /{command_name}"
        )
```

## Usage Examples

```bash
# Basic commit
/commit

# Skip verification
/commit --no-verify

# Force splitting
/commit --split

# Specify type
/commit --type fix

# Example output:
# ✨ feat(agents): add slash command support
# 
# - Implement command loader and registry
# - Add built-in commit command
# - Support markdown command definitions
```

## Benefits

1. **Consistency**: All commits follow conventional format
2. **Automation**: Reduces manual work
3. **Quality**: Pre-commit checks ensure code quality
4. **Intelligence**: Analyzes changes to suggest appropriate types
5. **Flexibility**: Supports splitting complex changes

## Extension Points

1. **Custom Commit Types**: Add project-specific types
2. **Validation Rules**: Add custom pre-commit checks
3. **Templates**: Define commit message templates
4. **Integrations**: Hook into CI/CD pipelines