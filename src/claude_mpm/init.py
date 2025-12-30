from pathlib import Path

"""Initialization module for claude-mpm.

Handles creation of necessary directories and configuration files.
"""

import json
import os
import shutil
import sys
from typing import Dict, Optional

import yaml

from claude_mpm.core.constants import NetworkConfig
from claude_mpm.core.logger import get_logger


class ProjectInitializer:
    """Handles initialization of claude-mpm directories and configuration."""

    def __init__(self):
        self.logger = get_logger("initializer")
        self.user_dir = Path.home() / ".claude-mpm"
        self.project_dir = None

    def initialize_user_directory(self) -> bool:
        """Initialize user-level .claude-mpm directory structure.

        Creates:
        - ~/.claude-mpm/
          - agents/
            - user-defined/
          - config/
          - logs/
          - templates/
          - registry/
        """
        try:
            # Create main user directory
            self.user_dir.mkdir(exist_ok=True)

            # Create subdirectories
            directories = [
                self.user_dir / "agents" / "user-defined",
                self.user_dir / "config",
                self.user_dir / "logs",
                self.user_dir / "templates",
                self.user_dir / "registry",
                self.user_dir / "memories",  # Add user-level memories directory
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Check for migration from old settings.json to new configuration.yaml
            old_config_file = self.user_dir / "config" / "settings.json"
            config_file = self.user_dir / "config" / "configuration.yaml"

            # Migrate if old file exists but new doesn't
            if old_config_file.exists() and not config_file.exists():
                self._migrate_json_to_yaml(old_config_file, config_file)
            elif not config_file.exists():
                # Create default configuration if it doesn't exist
                self._create_default_config(config_file)

            # Copy agent templates if they don't exist
            self._copy_agent_templates()

            self.logger.info(f"Initialized user directory at {self.user_dir}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize user directory: {e}")
            return False

    def initialize_project_directory(self, project_path: Optional[Path] = None) -> bool:
        """Initialize project-level .claude-mpm directory structure.

        Creates:
        - .claude-mpm/
          - agents/     (for project agent JSON files)
          - config/
          - responses/
          - logs/
        """
        try:
            # Find project root - always define project_root for consistent messaging
            if project_path:
                project_root = project_path
                self.project_dir = project_path / ".claude-mpm"
            else:
                # Check for the user's original working directory from launch script
                # The launch script sets CLAUDE_MPM_USER_PWD before changing to framework directory
                user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD")

                if user_pwd:
                    # Use the original user working directory
                    project_root = Path(user_pwd)
                    self.logger.debug(
                        f"Using user working directory from CLAUDE_MPM_USER_PWD: {project_root}"
                    )
                else:
                    # Fallback to current working directory (backward compatibility)
                    project_root = Path.cwd()
                    self.logger.debug(
                        f"CLAUDE_MPM_USER_PWD not set, using cwd: {project_root}"
                    )

                self.project_dir = project_root / ".claude-mpm"

            # Check if directory already exists
            directory_existed = self.project_dir.exists()

            # Migrate existing agents from project-specific subdirectory if needed
            self._migrate_project_agents()

            # Create project directory
            self.project_dir.mkdir(exist_ok=True)

            # Create subdirectories
            directories = [
                self.project_dir
                / "agents",  # Direct agents directory for project agents
                self.project_dir / "config",
                self.project_dir / "responses",
                self.project_dir / "logs",
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Create project configuration
            config_file = self.project_dir / "config" / "project.json"
            if not config_file.exists():
                self._create_project_config(config_file)

            # Create .gitignore for project directory
            gitignore = self.project_dir / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("logs/\n*.log\n*.pyc\n__pycache__/\n")

            # Log successful creation with details
            self.logger.info(f"Initialized project directory at {self.project_dir}")
            self.logger.debug("Created directories: agents, config, responses, logs")

            # Print appropriate message to console for visibility during startup
            # BUT: Don't print to stdout when running MCP server (interferes with JSON-RPC)
            is_mcp_mode = "mcp" in sys.argv and "start" in sys.argv

            if not is_mcp_mode:
                if directory_existed:
                    print(f"✓ Found existing .claude-mpm/ directory in {project_root}")
                else:
                    print(f"✓ Initialized .claude-mpm/ in {project_root}")

                # Check if migration happened
                agents_dir = self.project_dir / "agents"
                if agents_dir.exists() and any(agents_dir.glob("*.json")):
                    agent_count = len(list(agents_dir.glob("*.json")))
                    print(
                        f"✓ Found {agent_count} project agent(s) in .claude-mpm/agents/"
                    )

            # Verify and deploy PM skills (non-blocking)
            self._verify_and_deploy_pm_skills(project_root, is_mcp_mode)

            # Setup security hooks (auto-install pre-commit, detect-secrets)
            self._setup_security_hooks(project_root, is_mcp_mode)

            # Perform security checks (non-blocking)
            self._check_security_risks(project_root, is_mcp_mode)

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize project directory: {e}")
            print(f"✗ Failed to create .claude-mpm/ directory: {e}")
            return False

    def _verify_and_deploy_pm_skills(
        self, project_root: Path, is_mcp_mode: bool = False
    ) -> None:
        """Verify PM skills are deployed and auto-deploy if missing.

        Non-blocking operation that gracefully handles errors.

        Args:
            project_root: Project root directory
            is_mcp_mode: Whether running in MCP mode (suppress console output)
        """
        try:
            from claude_mpm.services.pm_skills_deployer import PMSkillsDeployerService

            deployer = PMSkillsDeployerService()
            result = deployer.verify_pm_skills(project_root)

            if not result.verified:
                # Log warnings
                for warning in result.warnings:
                    self.logger.warning(warning)

                # Auto-deploy PM skills
                self.logger.info("Auto-deploying PM skills...")
                deploy_result = deployer.deploy_pm_skills(project_root)

                if deploy_result.success:
                    self.logger.info(
                        f"PM skills deployed: {len(deploy_result.deployed)} deployed, "
                        f"{len(deploy_result.skipped)} skipped"
                    )

                    # Print to console if not in MCP mode
                    if not is_mcp_mode:
                        if deploy_result.deployed:
                            print(
                                f"✓ Deployed {len(deploy_result.deployed)} PM skill(s) "
                                f"to .claude-mpm/skills/pm/"
                            )
                else:
                    self.logger.warning(
                        f"PM skills deployment had errors: {len(deploy_result.errors)}"
                    )
                    if not is_mcp_mode and deploy_result.errors:
                        print(
                            f"⚠ PM skills deployment had {len(deploy_result.errors)} error(s)"
                        )
            else:
                # Skills verified successfully
                registry = deployer._load_registry(project_root)
                skill_count = len(registry.get("skills", []))
                self.logger.debug(f"PM skills verified: {skill_count} skills")

                if not is_mcp_mode and skill_count > 0:
                    print(f"✓ Verified {skill_count} PM skill(s)")

        except ImportError:
            self.logger.debug("PM skills deployer not available")
        except Exception as e:
            self.logger.warning(f"PM skills verification failed: {e}")
            # Don't print to console - this is a non-critical failure

    def _migrate_project_agents(self):
        """Migrate agents from old subdirectory structure to direct agents directory.

        WHY: We're simplifying the directory structure to match the deployment expectations.
        The old structure had a subdirectory but the deployment now looks for agents
        directly in .claude-mpm/agents/.
        """
        if not self.project_dir:
            return

        old_agents_dir = self.project_dir / "agents" / "project-specific"
        new_agents_dir = self.project_dir / "agents"

        # Check if old directory exists with JSON files
        if old_agents_dir.exists() and old_agents_dir.is_dir():
            json_files = list(old_agents_dir.glob("*.json"))
            if json_files:
                self.logger.info(
                    f"Migrating {len(json_files)} agents from old subdirectory"
                )

                # Ensure new agents directory exists
                new_agents_dir.mkdir(parents=True, exist_ok=True)

                # Move each JSON file
                migrated_count = 0
                for json_file in json_files:
                    try:
                        target_file = new_agents_dir / json_file.name
                        if not target_file.exists():
                            # Move the file
                            shutil.move(str(json_file), str(target_file))
                            migrated_count += 1
                            self.logger.debug(
                                f"Migrated {json_file.name} to agents directory"
                            )
                        else:
                            self.logger.debug(
                                f"Skipping {json_file.name} - already exists in target"
                            )
                    except Exception as e:
                        self.logger.error(f"Failed to migrate {json_file.name}: {e}")

                if migrated_count > 0:
                    # Don't print to stdout when running MCP server
                    is_mcp_mode = "mcp" in sys.argv and "start" in sys.argv
                    if not is_mcp_mode:
                        print(
                            f"✓ Migrated {migrated_count} agent(s) from old location to agents/"
                        )

                # Remove old directory if empty
                try:
                    if not any(old_agents_dir.iterdir()):
                        old_agents_dir.rmdir()
                        self.logger.debug("Removed empty old subdirectory")
                except Exception as e:
                    self.logger.debug(f"Could not remove old directory: {e}")

    def _find_project_root(self) -> Optional[Path]:
        """Find project root by looking for .git or other project markers."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            if (current / "pyproject.toml").exists():
                return current
            if (current / "setup.py").exists():
                return current
            current = current.parent
        return None

    def _migrate_json_to_yaml(self, old_file: Path, new_file: Path):
        """Migrate configuration from JSON to YAML format.

        Args:
            old_file: Path to existing settings.json
            new_file: Path to new configuration.yaml
        """
        try:
            # Read existing JSON configuration
            with old_file.open() as f:
                config = json.load(f)

            # Write as YAML
            with new_file.open("w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self.logger.info(
                f"Migrated configuration from {old_file.name} to {new_file.name}"
            )

            # Optionally rename old file to .backup
            backup_file = old_file.with_suffix(".json.backup")
            old_file.rename(backup_file)
            self.logger.info(f"Renamed old configuration to {backup_file.name}")

        except Exception as e:
            self.logger.error(f"Failed to migrate configuration: {e}")
            # Fall back to creating default config
            self._create_default_config(new_file)

    def _create_default_config(self, config_file: Path):
        """Create default user configuration in YAML format."""
        default_config = {
            "version": "1.0",
            "hooks": {
                "enabled": True,
                "port_range": list(NetworkConfig.SOCKETIO_PORT_RANGE),
            },
            "logging": {"level": "INFO", "max_size_mb": 100, "retention_days": 30},
            "agents": {
                "auto_discover": True,
                "precedence": ["project", "user", "system"],
            },
            "orchestration": {
                "default_mode": "subprocess",
                "enable_todo_hijacking": False,
            },
        }

        with config_file.open("w") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    def _create_project_config(self, config_file: Path):
        """Create default project configuration."""
        project_config = {
            "version": "1.0",
            "project_name": Path.cwd().name,
            "agents": {"enabled": True},
            "tickets": {"auto_create": True, "prefix": "TSK"},
        }

        with config_file.open("w") as f:
            json.dump(project_config, f, indent=2)

    def _copy_agent_templates(self):
        """Copy agent templates to user directory."""
        # Get the package directory
        package_dir = Path(__file__).parent
        templates_src = package_dir / "agents" / "templates"
        templates_dst = self.user_dir / "templates"

        if templates_src.exists():
            for template_file in templates_src.glob("*.md"):
                dst_file = templates_dst / template_file.name
                if not dst_file.exists():
                    shutil.copy2(template_file, dst_file)

    def _setup_security_hooks(
        self, project_root: Path, is_mcp_mode: bool = False
    ) -> None:
        """Automatically install pre-commit hooks for secret scanning.

        This method:
        1. Installs pre-commit and detect-secrets if missing
        2. Copies .pre-commit-config.yaml to project root
        3. Runs pre-commit install to set up git hooks
        4. Creates .secrets.baseline for detect-secrets

        Args:
            project_root: Project root directory
            is_mcp_mode: Whether running in MCP mode (suppress console output)
        """
        try:
            import subprocess

            # Only set up hooks if this is a git repository
            if not (project_root / ".git").exists():
                self.logger.debug("Not a git repository, skipping security hooks setup")
                return

            # Check/install pre-commit
            try:
                subprocess.run(
                    ["pre-commit", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=True,
                )
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ):
                self.logger.info("Installing pre-commit...")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "pre-commit"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=True,
                    )
                    self.logger.info("pre-commit installed successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install pre-commit: {e}")
                    return

            # Check/install detect-secrets
            try:
                subprocess.run(
                    ["detect-secrets", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=True,
                )
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                FileNotFoundError,
            ):
                self.logger.info("Installing detect-secrets...")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "detect-secrets"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=True,
                    )
                    self.logger.info("detect-secrets installed successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install detect-secrets: {e}")
                    return

            # Copy .pre-commit-config.yaml to project root if it doesn't exist
            precommit_config = project_root / ".pre-commit-config.yaml"
            if not precommit_config.exists():
                template_dir = Path(__file__).parent / "templates"
                template_config = template_dir / ".pre-commit-config.yaml"

                if template_config.exists():
                    shutil.copy2(template_config, precommit_config)
                    self.logger.info("Copied .pre-commit-config.yaml to project root")
                else:
                    self.logger.warning("Template .pre-commit-config.yaml not found")
                    return

            # Create .secrets.baseline if it doesn't exist
            secrets_baseline = project_root / ".secrets.baseline"
            if not secrets_baseline.exists():
                try:
                    subprocess.run(
                        ["detect-secrets", "scan", "--baseline", ".secrets.baseline"],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                    )
                    self.logger.info("Created .secrets.baseline")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to create .secrets.baseline: {e}")

            # Install git hooks
            try:
                subprocess.run(
                    ["pre-commit", "install"],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                self.logger.info("Pre-commit hooks installed in git repository")

                if not is_mcp_mode:
                    print("✓ Security hooks installed (pre-commit + detect-secrets)")

            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to install pre-commit hooks: {e}")

        except Exception as e:
            self.logger.debug(f"Security hooks setup failed: {e}")
            # Don't print to console - this is a non-critical failure

    def _check_security_risks(
        self, project_root: Path, is_mcp_mode: bool = False
    ) -> None:
        """Check for potential security risks like exposed config files.

        Non-blocking operation that warns about security issues.

        Args:
            project_root: Project root directory
            is_mcp_mode: Whether running in MCP mode (suppress console output)
        """
        try:
            import subprocess

            security_issues = []

            # Common secret file patterns to check
            secret_patterns = [
                ".mcp-vector-search/config.json",
                ".mcp/config.json",
                "openrouter.json",
                "anthropic-config.json",
                "credentials.json",
                "secrets.json",
                "api-keys.json",
            ]

            for pattern in secret_patterns:
                file_path = project_root / pattern
                if file_path.exists():
                    # Check if file is tracked by git
                    try:
                        result = subprocess.run(
                            ["git", "ls-files", str(file_path)],
                            check=False,
                            cwd=str(project_root),
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if result.stdout.strip():
                            security_issues.append(
                                f"⚠️  SECURITY: {pattern} is tracked by git (may contain secrets)"
                            )
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                    # Check if file is ignored by .gitignore
                    try:
                        result = subprocess.run(
                            ["git", "check-ignore", str(file_path)],
                            check=False,
                            cwd=str(project_root),
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if result.returncode != 0:  # File NOT ignored
                            security_issues.append(
                                f"⚠️  WARNING: {pattern} exists but not in .gitignore"
                            )
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

            # Print security warnings if not in MCP mode
            if security_issues and not is_mcp_mode:
                print("\n🔒 Security Check:")
                for issue in security_issues:
                    print(f"   {issue}")
                print()

        except Exception as e:
            self.logger.debug(f"Security check failed: {e}")
            # Don't print to console - this is a non-critical failure

    def validate_dependencies(self) -> Dict[str, bool]:
        """Validate that all required dependencies are available."""
        dependencies = {}

        # Check Python version
        dependencies["python"] = sys.version_info >= (3, 8)

        # Check Claude CLI
        dependencies["claude_cli"] = shutil.which("claude") is not None

        # Check required Python packages
        required_packages = [
            "ai_trackdown_pytools",
            "yaml",
            "dotenv",
            "click",
            "pexpect",
            "psutil",
            "requests",
            "flask",
            "watchdog",
            "tree_sitter",
        ]

        for package in required_packages:
            try:
                __import__(package)
                dependencies[package] = True
            except ImportError:
                dependencies[package] = False

        return dependencies

    def ensure_initialized(self) -> bool:
        """Ensure both user and project directories are initialized.

        Shows clear information about where directories are being created.
        """
        # Determine actual working directory
        user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD")
        if user_pwd:
            actual_wd = Path(user_pwd)
            self.logger.info(
                f"User working directory (from CLAUDE_MPM_USER_PWD): {actual_wd}"
            )
        else:
            actual_wd = Path.cwd()
            self.logger.info(f"Working directory: {actual_wd}")

        framework_path = Path(__file__).parent.parent.parent
        self.logger.info(f"Framework path: {framework_path}")

        # Initialize user directory (in home)
        user_ok = self.initialize_user_directory()

        # Initialize project directory (in user's actual working directory)
        self.logger.info(f"Checking for .claude-mpm/ in {actual_wd}")
        project_ok = self.initialize_project_directory()

        return user_ok and project_ok


def ensure_directories():
    """Convenience function to ensure directories are initialized."""
    initializer = ProjectInitializer()
    return initializer.ensure_initialized()


def validate_installation():
    """Validate that claude-mpm is properly installed."""
    initializer = ProjectInitializer()
    deps = initializer.validate_dependencies()

    all_ok = all(deps.values())

    if not all_ok:
        print("❌ Missing dependencies:")
        for dep, status in deps.items():
            if not status:
                print(f"  - {dep}")
    else:
        print("✅ All dependencies are installed")

    return all_ok
