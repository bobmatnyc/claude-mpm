"""
Project Organizer Service for Claude MPM Project Initialization
===============================================================

This service verifies and creates standard project directory structures
for optimal Claude Code and Claude MPM usage.

Key Features:
- Standard directory structure verification
- Missing directory creation with proper permissions
- .gitignore configuration and updates
- Temporary directory management
- Project structure documentation generation

Author: Claude MPM Development Team
Created: 2025-01-26
"""

from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Tuple

from rich.console import Console

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)
console = Console()


class ProjectOrganizer:
    """Manages project directory structure and organization."""

    # Standard directory structure for Claude MPM projects
    STANDARD_DIRECTORIES: ClassVar[dict] = {
        "tmp": "Temporary files, test outputs, and experiments",
        "scripts": "Project scripts and automation tools",
        "docs": "Project documentation",
        "docs/_archive": "Archived documentation versions",
        "tests": "Test suites and test fixtures",
        ".claude-mpm": "Claude MPM configuration and data",
        ".claude-mpm/memories": "Agent memory storage",
        ".claude/agents": "Deployed agent configurations",
        "src": "Source code (for libraries/packages)",
    }

    # Comprehensive gitignore patterns for Claude MPM projects
    GITIGNORE_DIRS: ClassVar[dict] = {
        # Temporary and cache directories
        "tmp/",
        "temp/",
        "*.tmp",
        "*.temp",
        "*.cache",
        ".claude-mpm/cache/",
        ".claude-mpm/logs/",
        ".claude/cache/",
        # MCP service directories for local data
        ".mcp-vector-search/",
        ".kuzu-memory/",
        "kuzu-memories/",  # kuzu-memory database directory
        # User-specific config files (should NOT be committed)
        ".mcp.json",
        ".claude.json",
        ".claude/",
        # Python artifacts
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        "*.egg-info/",
        "*.egg",
        "dist/",
        "build/",
        "develop-eggs/",
        ".eggs/",
        "wheels/",
        "pip-wheel-metadata/",
        "*.manifest",
        "*.spec",
        # Testing and coverage
        ".pytest_cache/",
        ".coverage",
        ".coverage.*",
        "htmlcov/",
        ".tox/",
        ".nox/",
        "*.cover",
        ".hypothesis/",
        ".pytype/",
        "coverage.xml",
        "*.pytest_cache",
        # Virtual environments
        ".env",
        ".venv",
        "env/",
        "venv/",
        "ENV/",
        "env.bak/",
        "venv.bak/",
        "virtualenv/",
        ".conda/",
        "conda-env/",
        # IDE and editor files
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "*~",
        ".project",
        ".pydevproject",
        ".settings/",
        "*.sublime-workspace",
        "*.sublime-project",
        # OS-specific files
        ".DS_Store",
        "Thumbs.db",
        "ehthumbs.db",
        "Desktop.ini",
        "$RECYCLE.BIN/",
        "*.cab",
        "*.msi",
        "*.msm",
        "*.msp",
        "*.lnk",
        # Logs and databases
        "*.log",
        "*.sql",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
        "logs/",
        # Node/JavaScript
        "node_modules/",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
        ".npm",
        ".yarn/",
        # Documentation builds
        "_build/",
        "site/",
        "docs/_build/",
        # Security and credentials
        ".env.*",
        "*.pem",
        "*.key",
        "*.cert",
        "*.crt",
        ".secrets/",
        "credentials/",
        # Claude MPM specific
        ".claude-mpm/*.log",
        ".claude-mpm/sessions/",
        ".claude-mpm/tmp/",
        ".claude/sessions/",
        "*.mpm.tmp",
        # Backup files
        "*.bak",
        "*.backup",
        "*.old",
        "backup/",
        "backups/",
    }

    # Project type specific structures
    PROJECT_STRUCTURES: ClassVar[dict] = {
        "web": ["public", "src/components", "src/pages", "src/styles"],
        "api": ["src/routes", "src/models", "src/middleware", "src/services"],
        "cli": ["src/commands", "src/utils", "src/config"],
        "library": ["src", "examples", "benchmarks"],
        "mobile": ["src/screens", "src/components", "src/services", "assets"],
        "fullstack": ["frontend", "backend", "shared", "infrastructure"],
    }

    def __init__(self, project_path: Path):
        """Initialize the project organizer."""
        self.project_path = project_path
        self.gitignore_path = project_path / ".gitignore"
        self.structure_report = {}

    def verify_structure(self, project_type: Optional[str] = None) -> Dict:
        """Verify project structure and identify missing components."""
        report = {
            "project_path": str(self.project_path),
            "exists": [],
            "missing": [],
            "issues": [],
            "recommendations": [],
        }

        # Check standard directories
        for dir_name, description in self.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                report["exists"].append(
                    {
                        "path": dir_name,
                        "description": description,
                        "is_directory": dir_path.is_dir(),
                    }
                )
            else:
                report["missing"].append(
                    {
                        "path": dir_name,
                        "description": description,
                        "required": self._is_required_directory(dir_name, project_type),
                    }
                )

        # Check project-type specific directories
        if project_type and project_type in self.PROJECT_STRUCTURES:
            for dir_name in self.PROJECT_STRUCTURES[project_type]:
                dir_path = self.project_path / dir_name
                if not dir_path.exists():
                    report["missing"].append(
                        {
                            "path": dir_name,
                            "description": f"{project_type} specific directory",
                            "required": False,
                        }
                    )

        # Check for common issues
        report["issues"] = self._check_common_issues()

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        self.structure_report = report
        return report

    def _is_required_directory(
        self, dir_name: str, project_type: Optional[str]
    ) -> bool:
        """Determine if a directory is required for the project."""
        # Always required directories
        always_required = {"tmp", "scripts", "docs"}
        if dir_name in always_required:
            return True

        # Type-specific requirements
        if project_type:
            if project_type in ["library", "package"] and dir_name == "src":
                return True
            if project_type in ["web", "api", "fullstack"] and dir_name == "tests":
                return True

        return False

    def _check_common_issues(self) -> List[Dict]:
        """Check for common project organization issues."""
        issues = []

        # Check for files in wrong locations
        root_files = list(self.project_path.glob("*.py"))
        test_files_in_root = [f for f in root_files if "test" in f.name.lower()]
        if test_files_in_root:
            issues.append(
                {
                    "type": "misplaced_tests",
                    "description": "Test files found in project root",
                    "files": [str(f.name) for f in test_files_in_root],
                    "recommendation": "Move test files to tests/ directory",
                }
            )

        script_files_in_root = [
            f
            for f in root_files
            if f.name.lower().endswith((".sh", ".bash", ".py"))
            and not f.name.startswith(".")
            and f.name not in ["setup.py", "pyproject.toml"]
        ]
        if script_files_in_root:
            issues.append(
                {
                    "type": "misplaced_scripts",
                    "description": "Script files found in project root",
                    "files": [
                        str(f.name) for f in script_files_in_root[:5]
                    ],  # Limit to 5
                    "recommendation": "Move scripts to scripts/ directory",
                }
            )

        # Check for missing .gitignore
        if not self.gitignore_path.exists():
            issues.append(
                {
                    "type": "missing_gitignore",
                    "description": "No .gitignore file found",
                    "recommendation": "Create .gitignore with standard patterns",
                }
            )
        else:
            # Check .gitignore completeness
            gitignore_content = self.gitignore_path.read_text()
            missing_patterns = []
            for pattern in ["tmp/", "__pycache__", ".env", "*.log"]:
                if pattern not in gitignore_content:
                    missing_patterns.append(pattern)

            if missing_patterns:
                issues.append(
                    {
                        "type": "incomplete_gitignore",
                        "description": "Common patterns missing from .gitignore",
                        "patterns": missing_patterns,
                        "recommendation": "Update .gitignore with missing patterns",
                    }
                )

        # Check for large files that should be in tmp
        large_files = []
        for file in self.project_path.rglob("*"):
            if file.is_file() and not any(part.startswith(".") for part in file.parts):
                try:
                    size_mb = file.stat().st_size / (1024 * 1024)
                    if size_mb > 10:  # Files larger than 10MB
                        if "tmp" not in str(file) and "node_modules" not in str(file):
                            large_files.append(
                                {
                                    "path": str(file.relative_to(self.project_path)),
                                    "size_mb": round(size_mb, 2),
                                }
                            )
                except (OSError, PermissionError):
                    continue

        if large_files:
            issues.append(
                {
                    "type": "large_files",
                    "description": "Large files outside tmp/ directory",
                    "files": large_files[:5],  # Limit to 5
                    "recommendation": "Consider moving large files to tmp/ or adding to .gitignore",
                }
            )

        return issues

    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate recommendations based on verification report."""
        recommendations = []

        # Recommend creating missing required directories
        required_missing = [d for d in report["missing"] if d.get("required")]
        if required_missing:
            recommendations.append(
                f"Create {len(required_missing)} required directories: "
                + ", ".join(d["path"] for d in required_missing)
            )

        # Recommend fixing issues
        if report["issues"]:
            for issue in report["issues"]:
                recommendations.append(issue["recommendation"])

        # Recommend documentation
        if "docs" not in [d["path"] for d in report["exists"]]:
            recommendations.append("Create docs/ directory for project documentation")

        return recommendations

    def create_missing_directories(self, force: bool = False) -> Dict:
        """Create missing standard directories."""
        created = []
        skipped = []
        errors = []

        report = self.verify_structure()

        for dir_info in report["missing"]:
            dir_path = self.project_path / dir_info["path"]

            # Skip non-required unless force
            if not dir_info.get("required") and not force:
                skipped.append(dir_info["path"])
                continue

            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(dir_info["path"])
                logger.info(f"Created directory: {dir_path}")

                # Add README for certain directories
                self._add_directory_readme(dir_path, dir_info["description"])

            except Exception as e:
                errors.append({"path": dir_info["path"], "error": str(e)})
                logger.error(f"Failed to create {dir_path}: {e}")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }

    def _add_directory_readme(self, dir_path: Path, description: str) -> None:
        """Add README file to newly created directory."""
        readme_path = dir_path / "README.md"

        # Only add README for certain directories
        readme_dirs = ["tmp", "scripts", "docs/_archive", ".claude-mpm/memories"]
        if any(str(dir_path).endswith(d) for d in readme_dirs):
            if not readme_path.exists():
                content = f"""# {dir_path.name}

{description}

## Purpose

This directory is used for {description.lower()}.

## Usage Guidelines

"""
                if "tmp" in str(dir_path):
                    content += """- Place all temporary files and test outputs here
- This directory is gitignored - contents will not be committed
- Clean up old files periodically to save disk space
- Use subdirectories to organize different types of temporary files
"""
                elif "scripts" in str(dir_path):
                    content += """- All project scripts should be placed here
- Use descriptive names for scripts
- Include comments and usage instructions in scripts
- Make scripts executable with `chmod +x script_name.sh`
"""
                elif "_archive" in str(dir_path):
                    content += """- Archived documentation versions are stored here
- Files are timestamped when archived
- Preserve important historical documentation
- Review and clean up old archives periodically
"""
                elif "memories" in str(dir_path):
                    content += """- Agent memory files are stored here
- Each agent can have its own memory file
- Memories persist between sessions
- Update memories when project knowledge changes
"""

                readme_path.write_text(content)
                logger.debug(f"Created README in {dir_path}")

    def update_gitignore(self, additional_patterns: Optional[List[str]] = None) -> bool:
        """Update or create .gitignore file with standard patterns."""
        try:
            # Read existing content
            existing_patterns = set()
            if self.gitignore_path.exists():
                content = self.gitignore_path.read_text()
                existing_patterns = {
                    line.strip()
                    for line in content.splitlines()
                    if line.strip() and not line.startswith("#")
                }
            else:
                content = ""

            # Combine all patterns
            all_patterns = self.GITIGNORE_DIRS.copy()
            if additional_patterns:
                all_patterns.update(additional_patterns)

            # Find missing patterns
            missing = all_patterns - existing_patterns

            if missing:
                # Add section for new patterns
                new_section = "\n# Added by Claude MPM /mpm-init\n"
                for pattern in sorted(missing):
                    new_section += f"{pattern}\n"

                # Append to file
                if content and not content.endswith("\n"):
                    content += "\n"
                content += new_section

                # Write updated content
                self.gitignore_path.write_text(content)
                logger.info(f"Updated .gitignore with {len(missing)} patterns")
                return True
            logger.info(".gitignore already contains all standard patterns")
            return False

        except Exception as e:
            logger.error(f"Failed to update .gitignore: {e}")
            return False

    def organize_misplaced_files(
        self, dry_run: bool = True, auto_safe: bool = True
    ) -> Dict:
        """Organize misplaced files into proper directories.

        Args:
            dry_run: If True, only report what would be moved without moving
            auto_safe: If True, only move files that are clearly safe to move
        """
        moves = []
        skipped = []
        errors = []

        # Files that should never be moved from root
        protected_root_files = {
            "setup.py",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "requirements.txt",
            "Pipfile",
            "Pipfile.lock",
            "poetry.lock",
            "Makefile",
            "makefile",
            "Dockerfile",
            "docker-compose.yml",
            ".gitignore",
            ".gitattributes",
            "LICENSE",
            "README.md",
            "README.rst",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "CLAUDE.md",
            "CODE.md",
            "DEVELOPER.md",
            "STRUCTURE.md",
            "OPS.md",
            ".env.example",
            ".env.sample",
            "VERSION",
            "BUILD_NUMBER",
        }

        # Scan root directory for misplaced files
        root_files = list(self.project_path.glob("*"))
        for file in root_files:
            if file.is_file() and file.name not in protected_root_files:
                target_dir = None
                confidence = "low"  # low, medium, high
                reason = ""

                # Determine target directory based on file patterns
                file_lower = file.name.lower()

                # Test files (high confidence)
                if "test" in file_lower and file.suffix == ".py":
                    if file_lower.startswith("test_") or file_lower.endswith(
                        "_test.py"
                    ):
                        target_dir = "tests"
                        confidence = "high"
                        reason = "Test file pattern detected"

                # Script files (medium-high confidence)
                elif file.suffix in [".sh", ".bash"]:
                    target_dir = "scripts"
                    confidence = "high"
                    reason = "Shell script file"
                elif file.suffix == ".py" and any(
                    pattern in file_lower
                    for pattern in ["script", "run", "cli", "tool"]
                ):
                    target_dir = "scripts"
                    confidence = "medium"
                    reason = "Python script pattern detected"

                # Log and temporary files (high confidence)
                elif file.suffix in [".log", ".tmp", ".temp", ".cache"]:
                    target_dir = "tmp"
                    confidence = "high"
                    reason = "Temporary/log file"
                elif file_lower.startswith(("tmp_", "temp_", "test_output", "debug_")):
                    target_dir = "tmp"
                    confidence = "high"
                    reason = "Temporary file pattern"

                # Documentation files (medium confidence)
                elif (
                    file.suffix in [".md", ".rst", ".txt"]
                    and file.name not in protected_root_files
                ):
                    if any(
                        pattern in file_lower
                        for pattern in ["notes", "draft", "todo", "spec", "design"]
                    ):
                        target_dir = "docs"
                        confidence = "medium"
                        reason = "Documentation file pattern"

                # Data files (medium confidence)
                elif file.suffix in [".csv", ".json", ".xml", ".yaml", ".yml"]:
                    if file.suffix in [".yaml", ".yml"] and any(
                        pattern in file_lower for pattern in ["config", "settings"]
                    ):
                        # Config files might belong in root
                        confidence = "low"
                    else:
                        target_dir = "data"
                        confidence = "medium"
                        reason = "Data file"

                # Build artifacts (high confidence)
                elif file.suffix in [".whl", ".tar.gz", ".zip"] and "dist" not in str(
                    file.parent
                ):
                    target_dir = "dist"
                    confidence = "high"
                    reason = "Build artifact"

                # Example files (medium confidence)
                elif "example" in file_lower or "sample" in file_lower:
                    target_dir = "examples"
                    confidence = "medium"
                    reason = "Example file pattern"

                if target_dir:
                    # Check if we should move based on confidence and auto_safe setting
                    should_move = (
                        (confidence == "high")
                        if auto_safe
                        else (confidence in ["high", "medium"])
                    )

                    if should_move:
                        target_path = self.project_path / target_dir / file.name
                        moves.append(
                            {
                                "source": str(file.relative_to(self.project_path)),
                                "target": str(
                                    target_path.relative_to(self.project_path)
                                ),
                                "reason": reason,
                                "confidence": confidence,
                            }
                        )

                        if not dry_run:
                            try:
                                # Create target directory if needed
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                # Move file
                                file.rename(target_path)
                                logger.info(
                                    f"Moved {file.name} to {target_dir}/ ({reason})"
                                )
                            except Exception as e:
                                errors.append({"file": str(file.name), "error": str(e)})
                                logger.error(f"Failed to move {file.name}: {e}")
                    else:
                        skipped.append(
                            {
                                "file": str(file.name),
                                "suggested_dir": target_dir,
                                "confidence": confidence,
                                "reason": "Low confidence move - skipped (use --no-auto-safe to include)",
                            }
                        )

        # Also check for deeply nested test files that should be in tests/
        if not auto_safe:  # Only in non-safe mode
            for test_file in self.project_path.rglob("*test*.py"):
                # Skip if already in tests directory
                if "tests" in test_file.parts or "test" in test_file.parts:
                    continue
                # Skip if in node_modules or venv
                if any(
                    part in test_file.parts
                    for part in ["node_modules", "venv", ".venv", "site-packages"]
                ):
                    continue

                target_path = self.project_path / "tests" / test_file.name
                moves.append(
                    {
                        "source": str(test_file.relative_to(self.project_path)),
                        "target": str(target_path.relative_to(self.project_path)),
                        "reason": "Test file found outside tests directory",
                        "confidence": "medium",
                    }
                )

                if not dry_run:
                    try:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        test_file.rename(target_path)
                        logger.info(f"Moved {test_file.name} to tests/")
                    except Exception as e:
                        errors.append(
                            {
                                "file": str(test_file.relative_to(self.project_path)),
                                "error": str(e),
                            }
                        )

        return {
            "dry_run": dry_run,
            "auto_safe": auto_safe,
            "proposed_moves": moves if dry_run else [],
            "completed_moves": [] if dry_run else moves,
            "skipped": skipped,
            "errors": errors,
            "total": len(moves),
            "total_skipped": len(skipped),
            "total_errors": len(errors),
        }

    def generate_structure_documentation(self) -> str:
        """Generate markdown documentation of project structure."""
        doc = """# Project Structure Report

## Structure Validation

"""
        # Add validation summary
        validation = self.validate_structure()
        doc += f"**Overall Grade:** {validation.get('grade', 'Not evaluated')}\n"
        doc += f"**Score:** {validation.get('score', 0)}/100\n\n"

        if validation["errors"]:
            doc += "### 🔴 Critical Issues\n"
            for error in validation["errors"]:
                doc += f"- {error}\n"
            doc += "\n"

        if validation["warnings"]:
            doc += "### ⚠️  Warnings\n"
            for warning in validation["warnings"]:
                doc += f"- {warning}\n"
            doc += "\n"

        doc += "## Directory Organization\n\n"

        # Document existing structure
        for dir_name, description in self.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                doc += f"### ✅ `{dir_name}/`\n{description}\n\n"

                # List some contents
                try:
                    contents = list(dir_path.iterdir())[:5]
                    if contents:
                        doc += "**Contents:**\n"
                        for item in contents:
                            if item.is_dir():
                                doc += f"- {item.name}/ (directory)\n"
                            else:
                                doc += f"- {item.name}\n"
                        if len(list(dir_path.iterdir())) > 5:
                            doc += f"- ... and {len(list(dir_path.iterdir())) - 5} more items\n"
                        doc += "\n"
                except PermissionError:
                    doc += "*Permission denied to list contents*\n\n"
            else:
                doc += f"### ❌ `{dir_name}/` (Missing)\n{description}\n\n"

        # Document misplaced files
        organize_result = self.organize_misplaced_files(dry_run=True, auto_safe=True)
        if organize_result["proposed_moves"]:
            doc += "## 📦 Files to Reorganize\n\n"
            doc += "The following files could be better organized:\n\n"
            for move in organize_result["proposed_moves"][:10]:  # Limit to 10
                doc += f"- `{move['source']}` → `{move['target']}`\n"
                doc += f"  - Reason: {move['reason']}\n"
                doc += f"  - Confidence: {move['confidence']}\n"
            if len(organize_result["proposed_moves"]) > 10:
                doc += f"\n... and {len(organize_result['proposed_moves']) - 10} more files\n"
            doc += "\n"

        # Document gitignore status
        doc += "## .gitignore Configuration\n\n"
        if self.gitignore_path.exists():
            gitignore_content = self.gitignore_path.read_text()
            critical_patterns = [
                "tmp/",
                "__pycache__",
                ".env",
                "*.log",
                ".claude-mpm/cache/",
            ]
            doc += "### Critical Patterns Status:\n"
            for pattern in critical_patterns:
                status = "✅" if pattern in gitignore_content else "❌"
                doc += f"- {status} `{pattern}`\n"
            doc += "\n"
        else:
            doc += "❌ No .gitignore file found\n\n"

        # Add recommendations
        if self.structure_report and self.structure_report.get("recommendations"):
            doc += "## 💡 Recommendations\n\n"
            for rec in self.structure_report["recommendations"]:
                doc += f"- {rec}\n"
            doc += "\n"

        # Add quick fix commands
        doc += "## 🛠️ Quick Fix Commands\n\n"
        doc += "```bash\n"
        doc += "# Run complete initialization\n"
        doc += "claude-mpm mpm-init --organize\n\n"
        doc += "# Review without changes\n"
        doc += "claude-mpm mpm-init --review\n\n"
        doc += "# Update existing documentation\n"
        doc += "claude-mpm mpm-init --update\n"
        doc += "```\n"

        return doc

    def generate_structure_report_json(self) -> Dict:
        """Generate a comprehensive JSON structure report."""
        validation = self.validate_structure()
        organize_result = self.organize_misplaced_files(dry_run=True, auto_safe=True)

        report = {
            "timestamp": str(Path.cwd()),
            "project_path": str(self.project_path),
            "validation": validation,
            "directories": {},
            "misplaced_files": organize_result,
            "gitignore": {
                "exists": self.gitignore_path.exists(),
                "patterns_status": {},
            },
            "statistics": {
                "total_directories": 0,
                "total_files": 0,
                "misplaced_files": len(organize_result.get("proposed_moves", [])),
                "structure_score": validation.get("score", 0),
            },
        }

        # Check directory status
        for dir_name, description in self.STANDARD_DIRECTORIES.items():
            dir_path = self.project_path / dir_name
            report["directories"][dir_name] = {
                "exists": dir_path.exists(),
                "description": description,
                "file_count": len(list(dir_path.glob("*"))) if dir_path.exists() else 0,
                "is_directory": dir_path.is_dir() if dir_path.exists() else None,
            }
            if dir_path.exists():
                report["statistics"]["total_directories"] += 1

        # Check gitignore patterns
        if self.gitignore_path.exists():
            gitignore_content = self.gitignore_path.read_text()
            critical_patterns = [
                "tmp/",
                "__pycache__",
                ".env",
                "*.log",
                ".claude-mpm/cache/",
            ]
            for pattern in critical_patterns:
                report["gitignore"]["patterns_status"][pattern] = (
                    pattern in gitignore_content
                )

        # Count total files
        for item in self.project_path.rglob("*"):
            if item.is_file():
                report["statistics"]["total_files"] += 1

        return report

    def ensure_project_ready(
        self, auto_organize: bool = False, safe_mode: bool = True
    ) -> Tuple[bool, List[str]]:
        """Ensure project is ready for Claude MPM usage.

        Args:
            auto_organize: Automatically organize misplaced files
            safe_mode: Only perform safe operations
        """
        actions_taken = []
        issues_found = []

        # Verify structure first
        self.verify_structure()

        # Create required directories
        result = self.create_missing_directories(force=False)
        if result["created"]:
            actions_taken.append(f"Created {len(result['created'])} directories")

        # Create tmp directory with proper README if it doesn't exist
        tmp_dir = self.project_path / "tmp"
        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True, exist_ok=True)
            self._add_directory_readme(
                tmp_dir, "Temporary files, test outputs, and experiments"
            )
            actions_taken.append("Created tmp/ directory with README")

        # Update .gitignore with comprehensive patterns
        if self.update_gitignore():
            actions_taken.append("Updated .gitignore with comprehensive patterns")

        # Check if organization is needed
        organize_result = self.organize_misplaced_files(
            dry_run=True, auto_safe=safe_mode
        )
        if organize_result["proposed_moves"]:
            if auto_organize:
                # Perform the organization
                actual_result = self.organize_misplaced_files(
                    dry_run=False, auto_safe=safe_mode
                )
                if actual_result["completed_moves"]:
                    actions_taken.append(
                        f"Organized {len(actual_result['completed_moves'])} files into proper directories"
                    )
                if actual_result["errors"]:
                    issues_found.append(
                        f"Failed to move {len(actual_result['errors'])} files"
                    )
            else:
                actions_taken.append(
                    f"Identified {len(organize_result['proposed_moves'])} files to reorganize (use --organize to move)"
                )
                if organize_result["skipped"]:
                    actions_taken.append(
                        f"Skipped {len(organize_result['skipped'])} low-confidence moves"
                    )

        # Check for remaining issues
        if self.structure_report.get("issues"):
            for issue in self.structure_report["issues"]:
                if issue["type"] not in [
                    "misplaced_scripts",
                    "misplaced_tests",
                ]:  # These may be handled
                    issues_found.append(issue["description"])

        # Generate structure validation report
        validation_report = self.validate_structure()
        if not validation_report["is_valid"]:
            issues_found.extend(validation_report["errors"])

        ready = len(issues_found) == 0
        return ready, actions_taken

    def validate_structure(self) -> Dict:
        """Validate the project structure meets Claude MPM standards."""
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "score": 100,
        }

        # Check critical directories exist
        critical_dirs = ["tmp", "scripts", "docs"]
        for dir_name in critical_dirs:
            if not (self.project_path / dir_name).exists():
                validation["is_valid"] = False
                validation["errors"].append(f"Missing critical directory: {dir_name}/")
                validation["score"] -= 10

        # Check .gitignore completeness
        if not self.gitignore_path.exists():
            validation["is_valid"] = False
            validation["errors"].append("No .gitignore file found")
            validation["score"] -= 15
        else:
            gitignore_content = self.gitignore_path.read_text()
            critical_patterns = ["tmp/", "__pycache__", ".env", "*.log"]
            for pattern in critical_patterns:
                if pattern not in gitignore_content:
                    validation["warnings"].append(
                        f"Missing gitignore pattern: {pattern}"
                    )
                    validation["score"] -= 2

        # Check for files in wrong locations
        root_files = list(self.project_path.glob("*"))
        misplaced_count = 0
        for file in root_files:
            if file.is_file() and (
                ("test" in file.name.lower() and file.suffix == ".py")
                or (file.suffix in [".sh", ".bash"] and file.name not in ["Makefile"])
                or file.suffix in [".log", ".tmp", ".cache"]
            ):
                misplaced_count += 1

        if misplaced_count > 0:
            validation["warnings"].append(
                f"{misplaced_count} files potentially misplaced in root"
            )
            validation["score"] -= min(misplaced_count * 2, 20)

        # Score interpretation
        if validation["score"] >= 90:
            validation["grade"] = "A - Excellent structure"
        elif validation["score"] >= 80:
            validation["grade"] = "B - Good structure"
        elif validation["score"] >= 70:
            validation["grade"] = "C - Acceptable structure"
        elif validation["score"] >= 60:
            validation["grade"] = "D - Needs improvement"
        else:
            validation["grade"] = "F - Poor structure"

        return validation
