"""Agent selection service for minimal and auto-configure deployment modes.

WHY: Provide two agent selection strategies to simplify deployment:
1. Minimal Configuration: Deploy exactly 6 core agents for basic workflow
2. Auto-Configure: Detect toolchain and deploy matching specialized agents

Design Decision: Strategy Pattern with Composition

This service composes SingleTierDeploymentService and ToolchainDetector
rather than inheriting. Each deployment mode is a distinct strategy that
orchestrates the deployment service differently.

Trade-offs:
- Flexibility: Easy to add new selection modes (e.g., profile-based)
- Testability: Can mock deployment service and detector independently
- Complexity: Slightly more code than monolithic approach
- Clarity: Clear separation between selection logic and deployment mechanics

Architecture:
- AgentSelectionService orchestrates deployment strategies
- SingleTierDeploymentService handles Git sync and file copying
- ToolchainDetector provides toolchain analysis for auto-configure

Example Workflow:
    # Minimal mode
    service.deploy_minimal_configuration()
    -> Validate 6 core agents available
    -> Deploy each agent via deployment_service.deploy_agent()

    # Auto-configure mode
    service.deploy_auto_configure(project_path)
    -> Detect toolchain (languages, frameworks, tools)
    -> Recommend agents based on toolchain
    -> Merge with core agents
    -> Deploy recommended agents
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.claude_mpm.services.agents.single_tier_deployment_service import (
    SingleTierDeploymentService,
)
from src.claude_mpm.services.agents.toolchain_detector import ToolchainDetector

logger = logging.getLogger(__name__)


class AgentSelectionService:
    """Service for agent selection modes (minimal and auto-configure).

    Provides two deployment strategies:

    1. Minimal Configuration Mode:
       Deploy exactly 6 core agents needed for basic Claude MPM workflow:
       - engineer: General implementation
       - documentation: Documentation creation
       - qa: Quality assurance testing
       - research: Codebase analysis
       - ops: Deployment operations
       - ticketing: Ticket management

    2. Auto-Configure Mode:
       Detect project toolchain and deploy matching agents:
       - Scan project for languages, frameworks, build tools
       - Map toolchain to specialized agents
       - Include core agents for complete workflow
       - Deploy recommended agent set

    Usage:
        >>> config = AgentSourceConfiguration.load()
        >>> deployment = SingleTierDeploymentService(config, deployment_dir)
        >>> service = AgentSelectionService(deployment)
        >>>
        >>> # Minimal mode
        >>> result = service.deploy_minimal_configuration()
        >>> print(f"Deployed {result['deployed_count']} agents")
        >>>
        >>> # Auto-configure mode
        >>> result = service.deploy_auto_configure(project_path=Path("."))
        >>> print(f"Detected: {result['toolchain']}")
        >>> print(f"Deployed: {result['deployed_agents']}")
    """

    # Minimal configuration agents (6 core agents)
    MINIMAL_AGENTS = [
        "engineer",
        "documentation",
        "qa",
        "research",
        "ops",
        "ticketing",
    ]

    def __init__(self, deployment_service: SingleTierDeploymentService):
        """Initialize agent selection service.

        Args:
            deployment_service: Deployment service for agent operations
        """
        self.deployment_service = deployment_service
        self.toolchain_detector = ToolchainDetector()

        logger.info("AgentSelectionService initialized")

    def deploy_minimal_configuration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Deploy minimal configuration (6 core agents).

        Deploys exactly 6 agents required for basic Claude MPM workflow:
        engineer, documentation, qa, research, ops, ticketing.

        Workflow:
        1. Get available agents from deployment service
        2. Validate all 6 core agents are available
        3. Deploy each core agent individually
        4. Return deployment report with success/failure details

        Args:
            dry_run: Show what would be deployed without actually deploying

        Returns:
            Deployment report:
            {
                "status": "success" | "partial" | "error",
                "mode": "minimal",
                "deployed_count": 6,
                "failed_count": 0,
                "deployed_agents": ["engineer", "qa", ...],
                "failed_agents": [],
                "missing_agents": [],
                "dry_run": false,
                "details": [
                    {
                        "agent_name": "engineer",
                        "deployed": true,
                        "source": "bobmatnyc/claude-mpm-agents",
                        "priority": 100
                    },
                    ...
                ]
            }

        Error Handling:
        - Missing agents logged and included in missing_agents list
        - Failed deployments logged and included in failed_agents list
        - Returns "partial" status if some agents deployed successfully
        - Returns "error" status if no agents deployed
        """
        logger.info(f"Starting minimal configuration deployment (dry_run={dry_run})")

        # Step 1: Get available agents
        available_agents = self.deployment_service.list_available_agents()
        available_agent_ids = {agent["agent_id"].lower() for agent in available_agents}

        logger.debug(
            f"Available agents: {len(available_agents)} ({sorted(available_agent_ids)})"
        )

        # Step 2: Validate all minimal agents are available
        available_minimal, missing_minimal = self._validate_agent_availability(
            self.MINIMAL_AGENTS, available_agent_ids
        )

        if missing_minimal:
            logger.warning(
                f"Some minimal agents not available: {sorted(missing_minimal)}"
            )

        # Step 3: Deploy each available minimal agent
        deployed_agents: List[str] = []
        failed_agents: List[str] = []
        deployment_details: List[Dict[str, Any]] = []

        for agent_name in available_minimal:
            try:
                result = self.deployment_service.deploy_agent(
                    agent_name=agent_name, dry_run=dry_run
                )

                if result.get("deployed", False) or result.get("dry_run", False):
                    deployed_agents.append(agent_name)
                    deployment_details.append(result)
                    logger.info(f"✓ Deployed {agent_name}")
                else:
                    failed_agents.append(agent_name)
                    deployment_details.append(result)
                    logger.warning(
                        f"✗ Failed to deploy {agent_name}: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_agents.append(agent_name)
                logger.error(f"✗ Error deploying {agent_name}: {e}")
                deployment_details.append(
                    {
                        "agent_name": agent_name,
                        "deployed": False,
                        "error": str(e),
                    }
                )

        # Step 4: Build report
        deployed_count = len(deployed_agents)
        failed_count = len(failed_agents)
        missing_count = len(missing_minimal)

        if deployed_count == len(self.MINIMAL_AGENTS) and missing_count == 0:
            status = "success"
        elif deployed_count > 0:
            status = "partial"
        else:
            status = "error"

        report = {
            "status": status,
            "mode": "minimal",
            "deployed_count": deployed_count,
            "failed_count": failed_count,
            "missing_count": missing_count,
            "deployed_agents": sorted(deployed_agents),
            "failed_agents": sorted(failed_agents),
            "missing_agents": sorted(missing_minimal),
            "dry_run": dry_run,
            "details": deployment_details,
        }

        logger.info(
            f"Minimal configuration deployment complete: "
            f"{deployed_count} deployed, {failed_count} failed, "
            f"{missing_count} missing (status: {status})"
        )

        return report

    def deploy_auto_configure(
        self,
        project_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Auto-detect toolchain and deploy matching agents.

        Workflow:
        1. Detect toolchain (languages, frameworks, build tools)
        2. Map toolchain to recommended agents
        3. Merge recommended agents with core agents
        4. Validate agent availability
        5. Deploy recommended agents
        6. Return deployment report with toolchain analysis

        Args:
            project_path: Project root path (defaults to current directory)
            dry_run: Show what would be deployed without actually deploying

        Returns:
            Deployment report:
            {
                "status": "success" | "partial" | "error",
                "mode": "auto_configure",
                "deployed_count": 8,
                "failed_count": 0,
                "toolchain": {
                    "languages": ["python"],
                    "frameworks": ["fastapi"],
                    "build_tools": ["docker", "make"]
                },
                "recommended_agents": ["python-engineer", "ops", "qa", ...],
                "deployed_agents": ["python-engineer", "ops", "qa", ...],
                "failed_agents": [],
                "missing_agents": [],
                "dry_run": false,
                "details": [...]
            }

        Error Handling:
        - Invalid project path: Returns error status with message
        - Toolchain detection failure: Falls back to minimal configuration
        - Missing agents: Logged and included in report
        - Failed deployments: Logged and included in report
        """
        if project_path is None:
            project_path = Path.cwd()

        logger.info(
            f"Starting auto-configure deployment (project={project_path}, dry_run={dry_run})"
        )

        # Step 1: Validate project path
        if not project_path.exists() or not project_path.is_dir():
            logger.error(f"Invalid project path: {project_path}")
            return {
                "status": "error",
                "mode": "auto_configure",
                "error": f"Invalid project path: {project_path}",
                "deployed_count": 0,
                "failed_count": 0,
                "toolchain": {},
                "recommended_agents": [],
                "deployed_agents": [],
                "failed_agents": [],
                "missing_agents": [],
                "dry_run": dry_run,
            }

        # Step 2: Detect toolchain
        try:
            toolchain = self.toolchain_detector.detect_toolchain(project_path)
            logger.info(f"Detected toolchain: {toolchain}")
        except Exception as e:
            logger.error(f"Toolchain detection failed: {e}")
            return {
                "status": "error",
                "mode": "auto_configure",
                "error": f"Toolchain detection failed: {e}",
                "deployed_count": 0,
                "failed_count": 0,
                "toolchain": {},
                "recommended_agents": [],
                "deployed_agents": [],
                "failed_agents": [],
                "missing_agents": [],
                "dry_run": dry_run,
            }

        # Step 3: Recommend agents based on toolchain
        recommended_agents = self.toolchain_detector.recommend_agents(toolchain)
        logger.info(
            f"Recommended {len(recommended_agents)} agents: {recommended_agents}"
        )

        # Step 4: Get available agents and validate
        available_agents = self.deployment_service.list_available_agents()
        available_agent_ids = {agent["agent_id"].lower() for agent in available_agents}

        available_recommended, missing_recommended = self._validate_agent_availability(
            recommended_agents, available_agent_ids
        )

        if missing_recommended:
            logger.warning(
                f"Some recommended agents not available: {sorted(missing_recommended)}"
            )

        # Step 5: Deploy each available recommended agent
        deployed_agents: List[str] = []
        failed_agents: List[str] = []
        deployment_details: List[Dict[str, Any]] = []

        for agent_name in available_recommended:
            try:
                result = self.deployment_service.deploy_agent(
                    agent_name=agent_name, dry_run=dry_run
                )

                if result.get("deployed", False) or result.get("dry_run", False):
                    deployed_agents.append(agent_name)
                    deployment_details.append(result)
                    logger.info(f"✓ Deployed {agent_name}")
                else:
                    failed_agents.append(agent_name)
                    deployment_details.append(result)
                    logger.warning(
                        f"✗ Failed to deploy {agent_name}: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_agents.append(agent_name)
                logger.error(f"✗ Error deploying {agent_name}: {e}")
                deployment_details.append(
                    {
                        "agent_name": agent_name,
                        "deployed": False,
                        "error": str(e),
                    }
                )

        # Step 6: Build report
        deployed_count = len(deployed_agents)
        failed_count = len(failed_agents)
        missing_count = len(missing_recommended)

        if deployed_count > 0 and failed_count == 0 and missing_count == 0:
            status = "success"
        elif deployed_count > 0:
            status = "partial"
        else:
            status = "error"

        report = {
            "status": status,
            "mode": "auto_configure",
            "deployed_count": deployed_count,
            "failed_count": failed_count,
            "missing_count": missing_count,
            "toolchain": toolchain,
            "recommended_agents": sorted(recommended_agents),
            "deployed_agents": sorted(deployed_agents),
            "failed_agents": sorted(failed_agents),
            "missing_agents": sorted(missing_recommended),
            "dry_run": dry_run,
            "details": deployment_details,
        }

        logger.info(
            f"Auto-configure deployment complete: "
            f"{deployed_count} deployed, {failed_count} failed, "
            f"{missing_count} missing (status: {status})"
        )

        return report

    def _validate_agent_availability(
        self, required_agents: List[str], available_agents: Set[str]
    ) -> Tuple[List[str], List[str]]:
        """Validate which required agents are available.

        Args:
            required_agents: List of agent names needed
            available_agents: Set of available agent IDs

        Returns:
            Tuple of (available_list, missing_list)
            - available_list: Agents that are available
            - missing_list: Agents that are not available
        """
        available_list: List[str] = []
        missing_list: List[str] = []

        for agent_name in required_agents:
            agent_id = agent_name.lower().replace(" ", "-")
            if agent_id in available_agents:
                available_list.append(agent_name)
            else:
                missing_list.append(agent_name)

        return available_list, missing_list

    def get_available_selection_modes(self) -> List[Dict[str, Any]]:
        """Get information about available selection modes.

        Returns:
            List of selection mode metadata:
            [
                {
                    "mode": "minimal",
                    "description": "Deploy 6 core agents for basic workflow",
                    "agent_count": 6,
                    "agents": ["engineer", "documentation", "qa", ...]
                },
                {
                    "mode": "auto_configure",
                    "description": "Auto-detect toolchain and deploy matching agents",
                    "agent_count": "varies",
                    "requires_project_scan": true
                }
            ]
        """
        return [
            {
                "mode": "minimal",
                "description": "Deploy 6 core agents for basic workflow",
                "agent_count": len(self.MINIMAL_AGENTS),
                "agents": self.MINIMAL_AGENTS,
            },
            {
                "mode": "auto_configure",
                "description": "Auto-detect toolchain and deploy matching agents",
                "agent_count": "varies",
                "requires_project_scan": True,
                "toolchain_support": {
                    "languages": list(self.toolchain_detector.LANGUAGE_PATTERNS.keys()),
                    "frameworks": list(
                        self.toolchain_detector.FRAMEWORK_PATTERNS.keys()
                    ),
                    "build_tools": list(
                        self.toolchain_detector.BUILD_TOOL_PATTERNS.keys()
                    ),
                },
            },
        ]

    def __repr__(self) -> str:
        """Return string representation."""
        return f"AgentSelectionService(deployment_service={self.deployment_service})"
