"""
Agent Validation Service
========================

WHY: This service encapsulates all agent validation logic, including frontmatter
validation, file integrity checks, and deployment state validation. It provides
a clean interface for the CLI to validate and fix agent issues.

DESIGN DECISIONS:
- Uses FrontmatterValidator for low-level validation operations
- Provides high-level validation and fix operations for the CLI
- Generates detailed validation reports for user feedback
- Maintains separation between validation logic and CLI presentation
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ...agents.frontmatter_validator import FrontmatterValidator
from ...core.agent_registry import AgentRegistryAdapter
from ...core.logger import get_logger


class IAgentValidationService(ABC):
    """Interface for agent validation operations."""

    @abstractmethod
    def validate_agent(self, agent_name: str) -> Dict[str, Any]:
        """Validate a single agent."""

    @abstractmethod
    def validate_all_agents(self) -> Dict[str, Any]:
        """Validate all deployed agents."""

    @abstractmethod
    def fix_agent_frontmatter(
        self, agent_name: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Fix frontmatter issues for a single agent."""

    @abstractmethod
    def fix_all_agents(self, dry_run: bool = True) -> Dict[str, Any]:
        """Fix frontmatter issues for all agents."""

    @abstractmethod
    def check_agent_integrity(self, agent_name: str) -> Dict[str, Any]:
        """Verify agent file structure and content integrity."""

    @abstractmethod
    def validate_deployment_state(self) -> Dict[str, Any]:
        """Check deployment consistency across all agents."""


class AgentValidationService(IAgentValidationService):
    """Service for validating and fixing agent deployment issues."""

    def __init__(self):
        """Initialize the validation service."""
        self.logger = get_logger(__name__)
        self.validator = FrontmatterValidator()
        self._registry = None

    @property
    def registry(self):
        """Get agent registry instance (lazy loaded)."""
        if self._registry is None:
            try:
                adapter = AgentRegistryAdapter()
                self._registry = adapter.registry
            except Exception as e:
                self.logger.error(f"Failed to initialize agent registry: {e}")
                raise RuntimeError(f"Could not initialize agent registry: {e}")
        return self._registry

    def validate_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Validate a single agent.

        Args:
            agent_name: Name of the agent to validate

        Returns:
            Dictionary containing validation results
        """
        try:
            # Get agent from registry
            agent = self.registry.get_agent(agent_name)
            if not agent:
                return {
                    "success": False,
                    "agent": agent_name,
                    "error": f"Agent '{agent_name}' not found",
                    "available_agents": list(self.registry.list_agents().keys()),
                }

            # Validate agent file
            agent_path = Path(agent.path)
            if not agent_path.exists():
                return {
                    "success": False,
                    "agent": agent_name,
                    "path": str(agent_path),
                    "error": "Agent file not found",
                    "is_valid": False,
                }

            # Perform validation
            result = self.validator.validate_file(agent_path)

            return {
                "success": True,
                "agent": agent_name,
                "path": str(agent_path),
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "corrections_available": len(result.corrections) > 0,
                "corrections": result.corrections,
            }

        except Exception as e:
            self.logger.error(
                f"Error validating agent {agent_name}: {e}", exc_info=True
            )
            return {"success": False, "agent": agent_name, "error": str(e)}

    def validate_all_agents(self) -> Dict[str, Any]:
        """
        Validate all deployed agents.

        Returns:
            Dictionary containing validation results for all agents
        """
        try:
            all_agents = self.registry.list_agents()
            if not all_agents:
                return {
                    "success": True,
                    "message": "No agents found to validate",
                    "total_agents": 0,
                    "results": [],
                }

            results = []
            total_issues = 0
            total_errors = 0
            total_warnings = 0
            agents_with_issues = []

            for agent_id, metadata in all_agents.items():
                agent_path = Path(metadata["path"])

                # Check if file exists
                if not agent_path.exists():
                    results.append(
                        {
                            "agent": agent_id,
                            "path": str(agent_path),
                            "is_valid": False,
                            "error": "File not found",
                        }
                    )
                    total_errors += 1
                    agents_with_issues.append(agent_id)
                    continue

                # Validate the agent
                validation_result = self.validator.validate_file(agent_path)

                agent_result = {
                    "agent": agent_id,
                    "path": str(agent_path),
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "corrections_available": len(validation_result.corrections) > 0,
                }

                results.append(agent_result)

                if validation_result.errors:
                    total_errors += len(validation_result.errors)
                    total_issues += len(validation_result.errors)
                    agents_with_issues.append(agent_id)

                if validation_result.warnings:
                    total_warnings += len(validation_result.warnings)
                    total_issues += len(validation_result.warnings)
                    if agent_id not in agents_with_issues:
                        agents_with_issues.append(agent_id)

            return {
                "success": True,
                "total_agents": len(all_agents),
                "agents_checked": len(results),
                "total_issues": total_issues,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "agents_with_issues": agents_with_issues,
                "results": results,
            }

        except Exception as e:
            self.logger.error(f"Error validating all agents: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def fix_agent_frontmatter(
        self, agent_name: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Fix frontmatter issues for a single agent.

        Args:
            agent_name: Name of the agent to fix
            dry_run: If True, don't actually write changes

        Returns:
            Dictionary containing fix results
        """
        try:
            # Get agent from registry
            agent = self.registry.get_agent(agent_name)
            if not agent:
                return {
                    "success": False,
                    "agent": agent_name,
                    "error": f"Agent '{agent_name}' not found",
                }

            agent_path = Path(agent.path)
            if not agent_path.exists():
                return {
                    "success": False,
                    "agent": agent_name,
                    "path": str(agent_path),
                    "error": "Agent file not found",
                }

            # Fix the agent
            result = self.validator.correct_file(agent_path, dry_run=dry_run)

            return {
                "success": True,
                "agent": agent_name,
                "path": str(agent_path),
                "dry_run": dry_run,
                "was_valid": result.is_valid and not result.corrections,
                "errors_found": result.errors,
                "warnings_found": result.warnings,
                "corrections_made": result.corrections if not dry_run else [],
                "corrections_available": result.corrections if dry_run else [],
                "is_fixed": not dry_run and result.is_valid,
            }

        except Exception as e:
            self.logger.error(f"Error fixing agent {agent_name}: {e}", exc_info=True)
            return {"success": False, "agent": agent_name, "error": str(e)}

    def fix_all_agents(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Fix frontmatter issues for all agents.

        Args:
            dry_run: If True, don't actually write changes

        Returns:
            Dictionary containing fix results for all agents
        """
        try:
            all_agents = self.registry.list_agents()
            if not all_agents:
                return {
                    "success": True,
                    "message": "No agents found to fix",
                    "total_agents": 0,
                    "results": [],
                }

            results = []
            total_issues = 0
            total_fixed = 0
            agents_fixed = []
            agents_with_errors = []

            for agent_id, metadata in all_agents.items():
                agent_path = Path(metadata["path"])

                # Check if file exists
                if not agent_path.exists():
                    results.append(
                        {
                            "agent": agent_id,
                            "path": str(agent_path),
                            "skipped": True,
                            "reason": "File not found",
                        }
                    )
                    agents_with_errors.append(agent_id)
                    continue

                # Fix the agent
                fix_result = self.validator.correct_file(agent_path, dry_run=dry_run)

                agent_result = {
                    "agent": agent_id,
                    "path": str(agent_path),
                    "was_valid": fix_result.is_valid and not fix_result.corrections,
                    "errors_found": len(fix_result.errors),
                    "warnings_found": len(fix_result.warnings),
                    "corrections_made": (
                        len(fix_result.corrections) if not dry_run else 0
                    ),
                    "corrections_available": (
                        len(fix_result.corrections) if dry_run else 0
                    ),
                }

                results.append(agent_result)

                if fix_result.errors:
                    total_issues += len(fix_result.errors)

                if fix_result.warnings:
                    total_issues += len(fix_result.warnings)

                if fix_result.corrections and not dry_run:
                    total_fixed += len(fix_result.corrections)
                    agents_fixed.append(agent_id)

            return {
                "success": True,
                "dry_run": dry_run,
                "total_agents": len(all_agents),
                "agents_checked": len(results),
                "total_issues_found": total_issues,
                "total_corrections_made": total_fixed if not dry_run else 0,
                "total_corrections_available": total_fixed if dry_run else 0,
                "agents_fixed": agents_fixed,
                "agents_with_errors": agents_with_errors,
                "results": results,
            }

        except Exception as e:
            self.logger.error(f"Error fixing all agents: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def check_agent_integrity(self, agent_name: str) -> Dict[str, Any]:
        """
        Verify agent file structure and content integrity.

        Args:
            agent_name: Name of the agent to check

        Returns:
            Dictionary containing integrity check results
        """
        try:
            # Get agent from registry
            agent = self.registry.get_agent(agent_name)
            if not agent:
                return {
                    "success": False,
                    "agent": agent_name,
                    "error": f"Agent '{agent_name}' not found",
                }

            agent_path = Path(agent.path)
            checks = {
                "file_exists": False,
                "has_frontmatter": False,
                "has_content": False,
                "valid_frontmatter": False,
                "required_fields": [],
                "missing_fields": [],
                "file_size": 0,
                "line_count": 0,
            }

            # Check file existence
            if not agent_path.exists():
                return {
                    "success": True,
                    "agent": agent_name,
                    "path": str(agent_path),
                    "integrity": checks,
                    "is_valid": False,
                    "issues": ["File does not exist"],
                }

            checks["file_exists"] = True

            # Read file content
            try:
                content = agent_path.read_text()
                checks["file_size"] = len(content)
                checks["line_count"] = len(content.splitlines())
                checks["has_content"] = len(content.strip()) > 0
            except Exception as e:
                return {
                    "success": True,
                    "agent": agent_name,
                    "path": str(agent_path),
                    "integrity": checks,
                    "is_valid": False,
                    "issues": [f"Cannot read file: {e}"],
                }

            # Check for frontmatter
            if content.startswith("---"):
                checks["has_frontmatter"] = True

                # Validate frontmatter
                validation_result = self.validator.validate_file(agent_path)
                checks["valid_frontmatter"] = validation_result.is_valid

                # Extract frontmatter to check fields
                try:
                    frontmatter_match = self.validator._extract_frontmatter(content)
                    if frontmatter_match:
                        import yaml

                        frontmatter = yaml.safe_load(frontmatter_match[0])

                        # Check required fields
                        required = ["name", "type", "description"]
                        for field in required:
                            if field in frontmatter:
                                checks["required_fields"].append(field)
                            else:
                                checks["missing_fields"].append(field)
                except Exception:
                    pass

            # Determine overall validity
            issues = []
            if not checks["file_exists"]:
                issues.append("File does not exist")
            if not checks["has_content"]:
                issues.append("File is empty")
            if not checks["has_frontmatter"]:
                issues.append("No frontmatter found")
            if checks["has_frontmatter"] and not checks["valid_frontmatter"]:
                issues.append("Invalid frontmatter format")
            if checks["missing_fields"]:
                issues.append(
                    f"Missing required fields: {', '.join(checks['missing_fields'])}"
                )

            is_valid = len(issues) == 0

            return {
                "success": True,
                "agent": agent_name,
                "path": str(agent_path),
                "integrity": checks,
                "is_valid": is_valid,
                "issues": issues,
            }

        except Exception as e:
            self.logger.error(
                f"Error checking integrity for agent {agent_name}: {e}", exc_info=True
            )
            return {"success": False, "agent": agent_name, "error": str(e)}

    def validate_deployment_state(self) -> Dict[str, Any]:
        """
        Check deployment consistency across all agents.

        Returns:
            Dictionary containing deployment state validation results
        """
        try:
            deployment_state = {
                "total_registered": 0,
                "files_found": 0,
                "files_missing": [],
                "duplicate_names": {},
                "conflicting_paths": {},
                "deployment_issues": [],
            }

            all_agents = self.registry.list_agents()
            deployment_state["total_registered"] = len(all_agents)

            # Track agent names and paths for duplicate detection
            name_to_agents = {}
            path_to_agents = {}

            for agent_id, metadata in all_agents.items():
                agent_path = Path(metadata["path"])
                agent_name = metadata.get("name", agent_id)

                # Check file existence
                if agent_path.exists():
                    deployment_state["files_found"] += 1
                else:
                    deployment_state["files_missing"].append(
                        {"agent": agent_id, "path": str(agent_path)}
                    )

                # Track names for duplicates
                if agent_name in name_to_agents:
                    if agent_name not in deployment_state["duplicate_names"]:
                        deployment_state["duplicate_names"][agent_name] = []
                    deployment_state["duplicate_names"][agent_name].append(agent_id)
                    if (
                        name_to_agents[agent_name]
                        not in deployment_state["duplicate_names"][agent_name]
                    ):
                        deployment_state["duplicate_names"][agent_name].append(
                            name_to_agents[agent_name]
                        )
                else:
                    name_to_agents[agent_name] = agent_id

                # Track paths for conflicts
                path_str = str(agent_path)
                if path_str in path_to_agents:
                    if path_str not in deployment_state["conflicting_paths"]:
                        deployment_state["conflicting_paths"][path_str] = []
                    deployment_state["conflicting_paths"][path_str].append(agent_id)
                    if (
                        path_to_agents[path_str]
                        not in deployment_state["conflicting_paths"][path_str]
                    ):
                        deployment_state["conflicting_paths"][path_str].append(
                            path_to_agents[path_str]
                        )
                else:
                    path_to_agents[path_str] = agent_id

            # Identify deployment issues
            if deployment_state["files_missing"]:
                deployment_state["deployment_issues"].append(
                    f"{len(deployment_state['files_missing'])} agents have missing files"
                )

            if deployment_state["duplicate_names"]:
                deployment_state["deployment_issues"].append(
                    f"{len(deployment_state['duplicate_names'])} duplicate agent names found"
                )

            if deployment_state["conflicting_paths"]:
                deployment_state["deployment_issues"].append(
                    f"{len(deployment_state['conflicting_paths'])} path conflicts found"
                )

            # Determine if deployment is healthy
            is_healthy = (
                len(deployment_state["files_missing"]) == 0
                and len(deployment_state["duplicate_names"]) == 0
                and len(deployment_state["conflicting_paths"]) == 0
            )

            return {
                "success": True,
                "is_healthy": is_healthy,
                "deployment_state": deployment_state,
                "summary": {
                    "total_agents": deployment_state["total_registered"],
                    "healthy_agents": deployment_state["files_found"]
                    - len(deployment_state["duplicate_names"])
                    - len(deployment_state["conflicting_paths"]),
                    "issues_count": len(deployment_state["deployment_issues"]),
                },
            }

        except Exception as e:
            self.logger.error(f"Error validating deployment state: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _extract_frontmatter(self, content: str) -> Optional[Tuple[str, str]]:
        """
        Extract frontmatter and content from an agent file.

        Args:
            content: File content

        Returns:
            Tuple of (frontmatter, content) or None if no frontmatter
        """
        pattern = r"^---\n(.*?)\n---\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)
        if match:
            return match.groups()
        return None
