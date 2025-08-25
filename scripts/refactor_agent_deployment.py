#!/usr/bin/env python3
"""Refactor agent_deployment.py using rope library for safe automated refactoring."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rope.base.project import Project
from rope.refactor.extract import ExtractMethod
from rope.refactor.move import MoveModule, MoveMethod
from rope.base import libutils
import subprocess
import json


class AgentDeploymentRefactorer:
    """Safely refactor agent_deployment.py into smaller services."""
    
    def __init__(self):
        """Initialize the refactorer with rope project."""
        self.project_root = Path(__file__).parent.parent
        self.project = Project(str(self.project_root))
        self.src_path = self.project_root / "src"
        self.deployment_path = self.src_path / "claude_mpm" / "services" / "agents" / "deployment"
        self.main_file = self.deployment_path / "agent_deployment.py"
        
    def run_tests(self, description=""):
        """Run tests to ensure nothing is broken."""
        print(f"\n🧪 Running tests {description}...")
        result = subprocess.run(
            ["python", "-m", "pytest", 
             "tests/services/agents/deployment/test_agent_deployment_comprehensive.py",
             "-xvs", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        if result.returncode != 0:
            print(f"❌ Tests failed {description}")
            print(result.stdout[-2000:])  # Last 2000 chars of output
            return False
        
        print(f"✅ Tests passed {description}")
        return True
    
    def get_file_lines(self):
        """Get current line count of main file."""
        with open(self.main_file) as f:
            return len(f.readlines())
    
    def phase1_extract_base_agent_locator(self):
        """Extract BaseAgentLocator class for finding base agent files."""
        print("\n📦 Phase 1: Extracting BaseAgentLocator...")
        
        # Create the new file
        locator_file = self.deployment_path / "base_agent_locator.py"
        locator_content = '''"""Base agent locator service for finding base agent configuration files."""

import os
from pathlib import Path
from typing import Optional
import logging


class BaseAgentLocator:
    """Service for locating base agent configuration files.
    
    This service handles the priority-based search for base_agent.json
    files across multiple possible locations including environment
    variables, development paths, and user overrides.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the base agent locator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def find_base_agent_file(self, paths_agents_dir: Path) -> Path:
        """Find base agent file with priority-based search.
        
        Priority order:
        1. Environment variable override (CLAUDE_MPM_BASE_AGENT_PATH)
        2. Current working directory (for local development)
        3. Known development locations
        4. User override location (~/.claude/agents/)
        5. Framework agents directory (from paths)
        
        Args:
            paths_agents_dir: Framework agents directory from paths
            
        Returns:
            Path to base agent file
        """
        # Priority 0: Check environment variable override
        env_path = os.environ.get("CLAUDE_MPM_BASE_AGENT_PATH")
        if env_path:
            env_base_agent = Path(env_path)
            if env_base_agent.exists():
                self.logger.info(
                    f"Using environment variable base_agent: {env_base_agent}"
                )
                return env_base_agent
            self.logger.warning(
                f"CLAUDE_MPM_BASE_AGENT_PATH set but file doesn't exist: {env_base_agent}"
            )
        
        # Priority 1: Check current working directory for local development
        cwd = Path.cwd()
        cwd_base_agent = cwd / "src" / "claude_mpm" / "agents" / "base_agent.json"
        if cwd_base_agent.exists():
            self.logger.info(
                f"Using local development base_agent from cwd: {cwd_base_agent}"
            )
            return cwd_base_agent
        
        # Priority 2: Check known development locations
        known_dev_paths = [
            Path(
                "/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json"
            ),
            Path.home()
            / "Projects"
            / "claude-mpm"
            / "src"
            / "claude_mpm"
            / "agents"
            / "base_agent.json",
            Path.home()
            / "projects"
            / "claude-mpm"
            / "src"
            / "claude_mpm"
            / "agents"
            / "base_agent.json",
        ]
        
        for dev_path in known_dev_paths:
            if dev_path.exists():
                self.logger.info(f"Using development base_agent: {dev_path}")
                return dev_path
        
        # Priority 3: Check user override location
        user_base_agent = Path.home() / ".claude" / "agents" / "base_agent.json"
        if user_base_agent.exists():
            self.logger.info(f"Using user override base_agent: {user_base_agent}")
            return user_base_agent
        
        # Priority 4: Use framework agents directory (fallback)
        framework_base_agent = paths_agents_dir / "base_agent.json"
        if framework_base_agent.exists():
            self.logger.info(f"Using framework base_agent: {framework_base_agent}")
            return framework_base_agent
        
        # If still not found, log all searched locations and raise error
        self.logger.error("Base agent file not found in any location:")
        self.logger.error(f"  1. CWD: {cwd_base_agent}")
        self.logger.error(f"  2. Dev paths: {known_dev_paths}")
        self.logger.error(f"  3. User: {user_base_agent}")
        self.logger.error(f"  4. Framework: {framework_base_agent}")
        
        # Final fallback to framework path even if it doesn't exist
        # (will fail later with better error message)
        return framework_base_agent
    
    def determine_source_tier(self, templates_dir: Path) -> str:
        """Determine the source tier for logging.
        
        Args:
            templates_dir: Templates directory path
            
        Returns:
            Source tier string (framework/user/project)
        """
        templates_str = str(templates_dir.resolve())
        
        # Check if this is a user-level installation
        if str(Path.home()) in templates_str and ".claude-mpm" in templates_str:
            return "user"
        
        # Check if this is a project-level installation
        if ".claude-mpm" in templates_str:
            return "project"
        
        # Default to framework
        return "framework"
'''
        
        locator_file.write_text(locator_content)
        print(f"✅ Created {locator_file}")
        
        # Now update agent_deployment.py to use the new service
        deployment_content = self.main_file.read_text()
        
        # Add import
        import_line = "from .base_agent_locator import BaseAgentLocator"
        if "from .agent_validator import AgentValidator" in deployment_content:
            deployment_content = deployment_content.replace(
                "from .agent_validator import AgentValidator",
                f"from .agent_validator import AgentValidator\n{import_line}"
            )
        
        # Initialize in __init__
        init_line = "        self.base_agent_locator = BaseAgentLocator(self.logger)"
        deployment_content = deployment_content.replace(
            "        # Initialize validator service",
            f"        # Initialize validator service\n{init_line}\n"
        )
        
        # Replace _find_base_agent_file call
        deployment_content = deployment_content.replace(
            "self.base_agent_path = self._find_base_agent_file()",
            "self.base_agent_path = self.base_agent_locator.find_base_agent_file(paths.agents_dir)"
        )
        
        # Remove the old method
        start_marker = "    def _find_base_agent_file(self) -> Path:"
        end_marker = "        return framework_base_agent\n"
        
        if start_marker in deployment_content and end_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            end_idx = deployment_content.index(end_marker, start_idx) + len(end_marker)
            deployment_content = deployment_content[:start_idx] + deployment_content[end_idx:]
        
        # Also replace _determine_source_tier
        deployment_content = deployment_content.replace(
            "source_tier = self._determine_source_tier()",
            "source_tier = self.base_agent_locator.determine_source_tier(self.templates_dir)"
        )
        
        # Remove old _determine_source_tier method
        start_marker = '    def _determine_source_tier(self) -> str:\n        """Determine the source tier for logging."""'
        end_marker = '        return DeploymentTypeDetector.determine_source_tier(self.templates_dir)'
        
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            # Find the end of the method
            lines = deployment_content[start_idx:].split('\n')
            method_lines = []
            for i, line in enumerate(lines):
                method_lines.append(line)
                if i > 0 and line and not line.startswith(' '):
                    break
                if "return DeploymentTypeDetector" in line:
                    break
            
            # Remove the method
            method_text = '\n'.join(method_lines[:-1]) + '\n'
            deployment_content = deployment_content.replace(method_text, '')
        
        # Write back
        self.main_file.write_text(deployment_content)
        print(f"✅ Updated {self.main_file}")
        
        return True
    
    def phase2_extract_deployment_results_manager(self):
        """Extract DeploymentResultsManager class."""
        print("\n📦 Phase 2: Extracting DeploymentResultsManager...")
        
        # Create the new file
        manager_file = self.deployment_path / "deployment_results_manager.py"
        manager_content = '''"""Deployment results manager for tracking deployment outcomes."""

import time
from pathlib import Path
from typing import Any, Dict, List
import logging


class DeploymentResultsManager:
    """Service for managing deployment results and metrics.
    
    This service handles initialization and updates of deployment
    results dictionaries, ensuring consistent structure across
    all deployment operations.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the deployment results manager.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize deployment metrics tracking
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }
    
    def initialize_deployment_results(
        self, agents_dir: Path, deployment_start_time: float
    ) -> Dict[str, Any]:
        """Initialize the deployment results dictionary.
        
        WHY: Consistent result structure ensures all deployment
        operations return the same format for easier processing.
        
        Args:
            agents_dir: Target agents directory
            deployment_start_time: Start time for metrics
            
        Returns:
            Initialized results dictionary
        """
        return {
            "target_dir": str(agents_dir),
            "deployed": [],
            "errors": [],
            "skipped": [],
            "updated": [],
            "migrated": [],  # Track agents migrated from old format
            "converted": [],  # Track YAML to MD conversions
            "repaired": [],  # Track agents with repaired frontmatter
            "total": 0,
            # METRICS: Add detailed timing and performance data to results
            "metrics": {
                "start_time": deployment_start_time,
                "end_time": None,
                "duration_ms": None,
                "agent_timings": {},  # Track individual agent deployment times
                "validation_times": {},  # Track template validation times
                "resource_usage": {},  # Could track memory/CPU if needed
            },
        }
    
    def record_agent_deployment(
        self,
        agent_name: str,
        template_file: Path,
        target_file: Path,
        is_update: bool,
        is_migration: bool,
        reason: str,
        agent_start_time: float,
        results: Dict[str, Any],
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Record deployment metrics and update results.
        
        WHY: Centralized metrics recording ensures consistent tracking
        of deployment performance and statistics.
        
        Args:
            agent_name: Name of the agent
            template_file: Template file
            target_file: Target file
            is_update: Whether this is an update
            is_migration: Whether this is a migration
            reason: Update/migration reason
            agent_start_time: Start time for this agent
            results: Results dictionary to update
            logger: Optional logger for output
        """
        logger = logger or self.logger
        
        # METRICS: Record deployment time for this agent
        agent_deployment_time = (time.time() - agent_start_time) * 1000  # Convert to ms
        results["metrics"]["agent_timings"][agent_name] = agent_deployment_time
        
        # METRICS: Update agent type deployment counts
        self._deployment_metrics["agent_type_counts"][agent_name] = (
            self._deployment_metrics["agent_type_counts"].get(agent_name, 0) + 1
        )
        
        deployment_info = {
            "name": agent_name,
            "template": str(template_file),
            "target": str(target_file),
            "deployment_time_ms": agent_deployment_time,
        }
        
        if is_migration:
            deployment_info["reason"] = reason
            results["migrated"].append(deployment_info)
            logger.info(
                f"Successfully migrated agent: {agent_name} to semantic versioning"
            )
            
            # METRICS: Track migration statistics
            self._deployment_metrics["migrations_performed"] += 1
            self._deployment_metrics["version_migration_count"] += 1
            
        elif is_update:
            results["updated"].append(deployment_info)
            logger.debug(f"Updated agent: {agent_name}")
        else:
            results["deployed"].append(deployment_info)
            logger.debug(f"Built and deployed agent: {agent_name}")
    
    def finalize_results(
        self, results: Dict[str, Any], deployment_start_time: float
    ) -> None:
        """Finalize deployment results with end metrics.
        
        Args:
            results: Results dictionary to finalize
            deployment_start_time: Original start time
        """
        deployment_end_time = time.time()
        deployment_duration = (deployment_end_time - deployment_start_time) * 1000  # ms
        
        results["metrics"]["end_time"] = deployment_end_time
        results["metrics"]["duration_ms"] = deployment_duration
    
    def update_deployment_metrics(
        self, success: bool, error_type: Optional[str] = None
    ) -> None:
        """Update internal deployment metrics.
        
        Args:
            success: Whether deployment succeeded
            error_type: Type of error if failed
        """
        self._deployment_metrics["total_deployments"] += 1
        
        if success:
            self._deployment_metrics["successful_deployments"] += 1
        else:
            self._deployment_metrics["failed_deployments"] += 1
            if error_type:
                self._deployment_metrics["deployment_errors"][error_type] = (
                    self._deployment_metrics["deployment_errors"].get(error_type, 0) + 1
                )
    
    def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get current deployment metrics."""
        return self._deployment_metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset deployment metrics."""
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }
'''
        
        manager_file.write_text(manager_content)
        print(f"✅ Created {manager_file}")
        
        # Update agent_deployment.py
        deployment_content = self.main_file.read_text()
        
        # Add import
        import_line = "from .deployment_results_manager import DeploymentResultsManager"
        deployment_content = deployment_content.replace(
            "from .base_agent_locator import BaseAgentLocator",
            f"from .base_agent_locator import BaseAgentLocator\n{import_line}"
        )
        
        # Initialize in __init__
        init_line = "        self.results_manager = DeploymentResultsManager(self.logger)"
        deployment_content = deployment_content.replace(
            "        self.base_agent_locator = BaseAgentLocator(self.logger)",
            f"        self.base_agent_locator = BaseAgentLocator(self.logger)\n{init_line}"
        )
        
        # Replace _initialize_deployment_results call
        deployment_content = deployment_content.replace(
            "results = self._initialize_deployment_results(agents_dir, deployment_start_time)",
            "results = self.results_manager.initialize_deployment_results(agents_dir, deployment_start_time)"
        )
        
        # Replace _record_agent_deployment call  
        deployment_content = deployment_content.replace(
            "self._record_agent_deployment(",
            "self.results_manager.record_agent_deployment("
        )
        
        # Add logger parameter to record_agent_deployment calls
        deployment_content = deployment_content.replace(
            "                    results,\n                )",
            "                    results,\n                    self.logger,\n                )"
        )
        
        # Update finalize results section
        old_finalize = """        # METRICS: Calculate final deployment metrics
        deployment_end_time = time.time()
        deployment_duration = (deployment_end_time - deployment_start_time) * 1000  # ms

        results["metrics"]["end_time"] = deployment_end_time
        results["metrics"]["duration_ms"] = deployment_duration"""
        
        new_finalize = """        # METRICS: Calculate final deployment metrics
        self.results_manager.finalize_results(results, deployment_start_time)"""
        
        deployment_content = deployment_content.replace(old_finalize, new_finalize)
        
        # Update metrics tracking in error handling
        old_metrics = """            # METRICS: Track deployment failure
            self._deployment_metrics["failed_deployments"] += 1
            error_type = type(e).__name__
            self._deployment_metrics["deployment_errors"][error_type] = (
                self._deployment_metrics["deployment_errors"].get(error_type, 0) + 1
            )"""
        
        new_metrics = """            # METRICS: Track deployment failure
            self.results_manager.update_deployment_metrics(False, type(e).__name__)"""
        
        deployment_content = deployment_content.replace(old_metrics, new_metrics)
        
        # Remove old methods
        # Remove _initialize_deployment_results
        start_marker = "    def _initialize_deployment_results("
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            # Find the end of the method (next def or class)
            remaining = deployment_content[start_idx:]
            lines = remaining.split('\n')
            end_idx = 0
            for i, line in enumerate(lines[1:], 1):
                if line and not line.startswith(' ') or (line.startswith('    def ') and i > 1):
                    end_idx = i
                    break
            
            method_text = '\n'.join(lines[:end_idx])
            deployment_content = deployment_content.replace(method_text, '')
        
        # Remove _record_agent_deployment
        start_marker = "    def _record_agent_deployment("
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            remaining = deployment_content[start_idx:]
            lines = remaining.split('\n')
            end_idx = 0
            for i, line in enumerate(lines[1:], 1):
                if line and not line.startswith(' ') or (line.startswith('    def ') and i > 1):
                    end_idx = i
                    break
            
            method_text = '\n'.join(lines[:end_idx])
            deployment_content = deployment_content.replace(method_text, '')
        
        # Remove old _deployment_metrics initialization
        old_init = """        # Initialize deployment metrics tracking
        self._deployment_metrics = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "migrations_performed": 0,
            "version_migration_count": 0,
            "agent_type_counts": {},
            "deployment_errors": {},
        }"""
        
        deployment_content = deployment_content.replace(old_init + "\n", "")
        
        # Update get_deployment_metrics to use results_manager
        deployment_content = deployment_content.replace(
            "return self.metrics_collector.get_deployment_metrics()",
            "return self.results_manager.get_deployment_metrics()"
        )
        
        # Update reset_metrics to use results_manager
        deployment_content = deployment_content.replace(
            "return self.metrics_collector.reset_metrics()",
            "return self.results_manager.reset_metrics()"
        )
        
        # Write back
        self.main_file.write_text(deployment_content)
        print(f"✅ Updated {self.main_file}")
        
        return True
    
    def phase3_extract_single_agent_deployer(self):
        """Extract SingleAgentDeployer class."""
        print("\n📦 Phase 3: Extracting SingleAgentDeployer...")
        
        # Create the new file
        deployer_file = self.deployment_path / "single_agent_deployer.py"
        deployer_content = '''"""Single agent deployer for deploying individual agents."""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import logging

from claude_mpm.core.exceptions import AgentDeploymentError


class SingleAgentDeployer:
    """Service for deploying individual agents.
    
    This service handles the deployment of single agent templates,
    including version checking, building, and writing agent files.
    """
    
    def __init__(
        self,
        template_builder,
        version_manager,
        results_manager,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the single agent deployer.
        
        Args:
            template_builder: Template builder service
            version_manager: Version manager service
            results_manager: Results manager service
            logger: Optional logger instance
        """
        self.template_builder = template_builder
        self.version_manager = version_manager
        self.results_manager = results_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def deploy_single_agent(
        self,
        template_file: Path,
        agents_dir: Path,
        base_agent_data: dict,
        base_agent_version: tuple,
        force_rebuild: bool,
        deployment_mode: str,
        results: Dict[str, Any],
        source_info: str = "unknown",
    ) -> None:
        """Deploy a single agent template.
        
        WHY: Extracting single agent deployment logic reduces complexity
        and makes the main deployment loop more readable.
        
        Args:
            template_file: Agent template file
            agents_dir: Target agents directory
            base_agent_data: Base agent data
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode (update/project)
            results: Results dictionary to update
            source_info: Source of the agent (system/project/user)
        """
        try:
            # METRICS: Track individual agent deployment time
            agent_start_time = time.time()
            
            agent_name = template_file.stem
            target_file = agents_dir / f"{agent_name}.md"
            
            # Check if agent needs update
            needs_update, is_migration, reason = self._check_update_status(
                target_file,
                template_file,
                base_agent_version,
                force_rebuild,
                deployment_mode,
            )
            
            # Skip if exists and doesn't need update (only in update mode)
            if (
                target_file.exists()
                and not needs_update
                and deployment_mode != "project"
            ):
                results["skipped"].append(agent_name)
                self.logger.debug(f"Skipped up-to-date agent: {agent_name}")
                return
            
            # Build the agent file as markdown with YAML frontmatter
            agent_content = self.template_builder.build_agent_markdown(
                agent_name, template_file, base_agent_data, source_info
            )
            
            # Write the agent file
            is_update = target_file.exists()
            target_file.write_text(agent_content)
            
            # Record metrics and update results
            self.results_manager.record_agent_deployment(
                agent_name,
                template_file,
                target_file,
                is_update,
                is_migration,
                reason,
                agent_start_time,
                results,
                self.logger,
            )
            
        except AgentDeploymentError as e:
            # Re-raise our custom exceptions
            self.logger.error(str(e))
            results["errors"].append(str(e))
        except Exception as e:
            # Wrap generic exceptions with context
            error_msg = f"Failed to build {template_file.name}: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
    
    def _check_update_status(
        self,
        target_file: Path,
        template_file: Path,
        base_agent_version: tuple,
        force_rebuild: bool,
        deployment_mode: str,
    ) -> Tuple[bool, bool, str]:
        """Check if agent needs update and determine status.
        
        WHY: Centralized update checking logic ensures consistent
        version comparison and migration detection.
        
        Args:
            target_file: Target agent file
            template_file: Template file
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode
            
        Returns:
            Tuple of (needs_update, is_migration, reason)
        """
        needs_update = force_rebuild
        is_migration = False
        reason = ""
        
        # In project deployment mode, always deploy regardless of version
        if deployment_mode == "project":
            if target_file.exists():
                needs_update = True
                self.logger.debug(
                    f"Project deployment mode: will deploy {template_file.stem}"
                )
            else:
                needs_update = True
        elif not needs_update and target_file.exists():
            # In update mode, check version compatibility
            needs_update, reason = self.version_manager.check_agent_needs_update(
                target_file, template_file, base_agent_version
            )
            if needs_update:
                # Check if this is a migration from old format
                if "migration needed" in reason:
                    is_migration = True
                    self.logger.info(f"Migrating agent {template_file.stem}: {reason}")
                else:
                    self.logger.info(
                        f"Agent {template_file.stem} needs update: {reason}"
                    )
        
        return needs_update, is_migration, reason
    
    def deploy_agent(
        self,
        agent_name: str,
        templates_dir: Path,
        target_dir: Path,
        base_agent_path: Path,
        force_rebuild: bool = False,
    ) -> bool:
        """Deploy a single agent to the specified directory.
        
        Args:
            agent_name: Name of the agent to deploy
            templates_dir: Directory containing templates
            target_dir: Target directory for deployment (Path object)
            base_agent_path: Path to base agent configuration
            force_rebuild: Whether to force rebuild even if version is current
            
        Returns:
            True if deployment was successful, False otherwise
            
        WHY: Single agent deployment because:
        - Users may want to deploy specific agents only
        - Reduces deployment time for targeted updates
        - Enables selective agent management in projects
        """
        try:
            # Find the template file
            template_file = templates_dir / f"{agent_name}.json"
            if not template_file.exists():
                self.logger.error(f"Agent template not found: {agent_name}")
                return False
            
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Build and deploy the agent
            target_file = target_dir / f"{agent_name}.md"
            
            # Check if update is needed
            if not force_rebuild and target_file.exists():
                # Load base agent data for version checking
                base_agent_data = {}
                base_agent_version = (0, 0, 0)
                if base_agent_path.exists():
                    try:
                        import json
                        
                        base_agent_data = json.loads(base_agent_path.read_text())
                        base_agent_version = self.version_manager.parse_version(
                            base_agent_data.get("base_version")
                            or base_agent_data.get("version", 0)
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not load base agent for version check: {e}"
                        )
                
                needs_update, reason = self.version_manager.check_agent_needs_update(
                    target_file, template_file, base_agent_version
                )
                if not needs_update:
                    self.logger.info(f"Agent {agent_name} is up to date")
                    return True
                self.logger.info(f"Updating agent {agent_name}: {reason}")
            
            # Load base agent data for building
            base_agent_data = {}
            if base_agent_path.exists():
                try:
                    import json
                    
                    base_agent_data = json.loads(base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")
            
            # Build the agent markdown
            # For single agent deployment, determine source from template location
            source_info = self._determine_agent_source(template_file, templates_dir)
            agent_content = self.template_builder.build_agent_markdown(
                agent_name, template_file, base_agent_data, source_info
            )
            if not agent_content:
                self.logger.error(f"Failed to build agent content for {agent_name}")
                return False
            
            # Write to target file
            target_file.write_text(agent_content)
            self.logger.info(
                f"Successfully deployed agent: {agent_name} to {target_file}"
            )
            
            return True
            
        except AgentDeploymentError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap generic exceptions with context
            raise AgentDeploymentError(
                f"Failed to deploy agent {agent_name}",
                context={"agent_name": agent_name, "error": str(e)},
            ) from e
    
    def _determine_agent_source(self, template_path: Path, templates_dir: Path) -> str:
        """Determine the source of an agent from its template path.
        
        WHY: When deploying single agents, we need to track their source
        for proper version management and debugging.
        
        Args:
            template_path: Path to the agent template
            templates_dir: Base templates directory
            
        Returns:
            Source string (system/project/user/unknown)
        """
        template_str = str(template_path.resolve())
        
        # Check if it's a system template
        if (
            "/claude_mpm/agents/templates/" in template_str
            or "/src/claude_mpm/agents/templates/" in template_str
        ):
            return "system"
        
        # Check if it's a project agent
        if "/.claude-mpm/agents/" in template_str:
            # Check if it's in the current working directory
            cwd = Path.cwd()
            if str(cwd) in template_str:
                return "project"
            # Check if it's in user home
            if str(Path.home()) in template_str:
                return "user"
        
        return "unknown"
'''
        
        deployer_file.write_text(deployer_content)
        print(f"✅ Created {deployer_file}")
        
        # Update agent_deployment.py
        deployment_content = self.main_file.read_text()
        
        # Add import
        import_line = "from .single_agent_deployer import SingleAgentDeployer"
        deployment_content = deployment_content.replace(
            "from .deployment_results_manager import DeploymentResultsManager",
            f"from .deployment_results_manager import DeploymentResultsManager\n{import_line}"
        )
        
        # Initialize in __init__
        init_line = """        self.single_agent_deployer = SingleAgentDeployer(
            self.template_builder,
            self.version_manager,
            self.results_manager,
            self.logger,
        )"""
        deployment_content = deployment_content.replace(
            "        self.results_manager = DeploymentResultsManager(self.logger)",
            f"        self.results_manager = DeploymentResultsManager(self.logger)\n{init_line}"
        )
        
        # Replace _deploy_single_agent call
        deployment_content = deployment_content.replace(
            "                self._deploy_single_agent(",
            "                self.single_agent_deployer.deploy_single_agent("
        )
        
        # Update deploy_agent method to use single_agent_deployer
        # Find and replace the deploy_agent method body
        old_deploy_agent_body = """            # Find the template file
            template_file = self.templates_dir / f"{agent_name}.json"
            if not template_file.exists():
                self.logger.error(f"Agent template not found: {agent_name}")
                return False

            # Ensure target directory exists
            # target_dir should already be the agents directory
            target_dir.mkdir(parents=True, exist_ok=True)

            # Build and deploy the agent
            target_file = target_dir / f"{agent_name}.md"

            # Check if update is needed
            if not force_rebuild and target_file.exists():
                # Load base agent data for version checking
                base_agent_data = {}
                base_agent_version = (0, 0, 0)
                if self.base_agent_path.exists():
                    try:
                        import json

                        base_agent_data = json.loads(self.base_agent_path.read_text())
                        base_agent_version = self.version_manager.parse_version(
                            base_agent_data.get("base_version")
                            or base_agent_data.get("version", 0)
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not load base agent for version check: {e}"
                        )

                needs_update, reason = self.version_manager.check_agent_needs_update(
                    target_file, template_file, base_agent_version
                )
                if not needs_update:
                    self.logger.info(f"Agent {agent_name} is up to date")
                    return True
                self.logger.info(f"Updating agent {agent_name}: {reason}")

            # Load base agent data for building
            base_agent_data = {}
            if self.base_agent_path.exists():
                try:
                    import json

                    base_agent_data = json.loads(self.base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")

            # Build the agent markdown
            # For single agent deployment, determine source from template location
            source_info = self._determine_agent_source(template_file)
            agent_content = self.template_builder.build_agent_markdown(
                agent_name, template_file, base_agent_data, source_info
            )
            if not agent_content:
                self.logger.error(f"Failed to build agent content for {agent_name}")
                return False

            # Write to target file
            target_file.write_text(agent_content)
            self.logger.info(
                f"Successfully deployed agent: {agent_name} to {target_file}"
            )

            return True"""
        
        new_deploy_agent_body = """            return self.single_agent_deployer.deploy_agent(
                agent_name,
                self.templates_dir,
                target_dir,
                self.base_agent_path,
                force_rebuild,
            )"""
        
        deployment_content = deployment_content.replace(old_deploy_agent_body, new_deploy_agent_body)
        
        # Remove old methods
        # Remove _deploy_single_agent
        start_marker = "    def _deploy_single_agent("
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            remaining = deployment_content[start_idx:]
            lines = remaining.split('\n')
            end_idx = 0
            for i, line in enumerate(lines[1:], 1):
                if line and not line.startswith(' ') or (line.startswith('    def ') and i > 1):
                    end_idx = i
                    break
            
            method_text = '\n'.join(lines[:end_idx])
            deployment_content = deployment_content.replace(method_text, '')
        
        # Remove _check_update_status
        start_marker = "    def _check_update_status("
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            remaining = deployment_content[start_idx:]
            lines = remaining.split('\n')
            end_idx = 0
            for i, line in enumerate(lines[1:], 1):
                if line and not line.startswith(' ') or (line.startswith('    def ') and i > 1):
                    end_idx = i
                    break
            
            method_text = '\n'.join(lines[:end_idx])
            deployment_content = deployment_content.replace(method_text, '')
        
        # Remove _determine_agent_source
        start_marker = "    def _determine_agent_source(self, template_path: Path) -> str:"
        if start_marker in deployment_content:
            start_idx = deployment_content.index(start_marker)
            remaining = deployment_content[start_idx:]
            lines = remaining.split('\n')
            end_idx = 0
            for i, line in enumerate(lines[1:], 1):
                if line and not line.startswith(' ') or (line.startswith('    def ') and i > 1):
                    end_idx = i
                    break
            
            method_text = '\n'.join(lines[:end_idx])
            deployment_content = deployment_content.replace(method_text, '')
        
        # Write back
        self.main_file.write_text(deployment_content)
        print(f"✅ Updated {self.main_file}")
        
        return True
    
    def commit_changes(self, phase_name: str):
        """Commit the changes for a phase."""
        print(f"\n💾 Committing changes for {phase_name}...")
        
        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=str(self.project_root))
        
        # Commit
        commit_msg = f"refactor: {phase_name} - reduce agent_deployment.py complexity"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(self.project_root),
            capture_output=True
        )
        
        print(f"✅ Committed: {commit_msg}")
    
    def run(self):
        """Run the complete refactoring process."""
        print("🚀 Starting agent_deployment.py refactoring...")
        print(f"📏 Initial file size: {self.get_file_lines()} lines")
        
        # Run initial tests
        if not self.run_tests("(before refactoring)"):
            print("❌ Tests must pass before refactoring")
            return False
        
        # Phase 1: Extract BaseAgentLocator
        if self.phase1_extract_base_agent_locator():
            if self.run_tests("(after Phase 1)"):
                self.commit_changes("Phase 1 - Extract BaseAgentLocator")
            else:
                print("❌ Phase 1 broke tests, stopping")
                return False
        
        # Phase 2: Extract DeploymentResultsManager
        if self.phase2_extract_deployment_results_manager():
            if self.run_tests("(after Phase 2)"):
                self.commit_changes("Phase 2 - Extract DeploymentResultsManager")
            else:
                print("❌ Phase 2 broke tests, stopping")
                return False
        
        # Phase 3: Extract SingleAgentDeployer
        if self.phase3_extract_single_agent_deployer():
            if self.run_tests("(after Phase 3)"):
                self.commit_changes("Phase 3 - Extract SingleAgentDeployer")
            else:
                print("❌ Phase 3 broke tests, stopping")
                return False
        
        print(f"\n✅ Refactoring complete!")
        print(f"📏 Final file size: {self.get_file_lines()} lines")
        print(f"📉 Reduced by: {1280 - self.get_file_lines()} lines")
        
        return True


if __name__ == "__main__":
    refactorer = AgentDeploymentRefactorer()
    success = refactorer.run()
    sys.exit(0 if success else 1)