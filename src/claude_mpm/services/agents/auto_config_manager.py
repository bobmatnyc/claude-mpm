"""
Auto-Configuration Manager Service for Claude MPM Framework
===========================================================

WHY: Orchestrates the complete auto-configuration workflow from toolchain
analysis through agent deployment. Provides a single entry point for automated
project configuration with safety checks and rollback capabilities.

DESIGN DECISION: Implements the Facade pattern to simplify complex interactions
between ToolchainAnalyzer, AgentRecommender, and AgentDeployment services.
Uses Observer pattern for progress tracking and supports dry-run mode for
safe previewing.

Part of TSK-0054: Auto-Configuration Feature - Phase 4
"""

import shutil
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ...core.base_service import BaseService
from ...core.enums import OperationResult, ValidationSeverity
from ..core.interfaces.agent import IAgentRegistry, IAutoConfigManager
from ..core.models.agent_config import (
    AgentRecommendation,
    ConfigurationPreview,
    ConfigurationResult,
    ValidationIssue,
    ValidationResult,
)
from ..core.models.toolchain import ToolchainAnalysis
from .observers import IDeploymentObserver, NullObserver
from .recommender import AgentRecommenderService


class AutoConfigManagerService(BaseService, IAutoConfigManager):
    """
    Service for automated agent configuration and deployment.

    This service orchestrates:
    1. Toolchain analysis to understand project technology stack
    2. Agent recommendations based on detected toolchain
    3. Configuration validation with comprehensive checks
    4. User confirmation (optional) before deployment
    5. Agent deployment with progress tracking
    6. Rollback on failure to maintain consistency
    7. Configuration persistence for future reference

    Safety Features:
    - Minimum confidence threshold (default 0.5)
    - Dry-run mode for preview without changes
    - Validation gates to block invalid configurations
    - Rollback capability for failed deployments
    - User confirmation for destructive operations

    Performance:
    - Complete workflow: <30 seconds for typical projects
    - Validation: <1 second
    - Preview generation: <5 seconds
    - Uses caching where applicable
    """

    def __init__(
        self,
        toolchain_analyzer: Any | None = None,
        agent_recommender: AgentRecommenderService | None = None,
        agent_registry: IAgentRegistry | None = None,
        agent_deployment: Any | None = None,
        config: dict[str, Any] | None = None,
        container: Any | None = None,
    ):
        """
        Initialize the Auto-Configuration Manager Service.

        Args:
            toolchain_analyzer: Service for analyzing project toolchains
            agent_recommender: Service for recommending agents
            agent_registry: Service for agent discovery and metadata
            agent_deployment: Service for deploying agents
            config: Optional configuration dictionary
            container: Optional service container for dependency injection
        """
        super().__init__(
            name="AutoConfigManagerService",
            config=config,
            enable_enhanced_features=False,
            container=container,
        )

        # Store service dependencies
        self._toolchain_analyzer = toolchain_analyzer
        self._agent_recommender = agent_recommender
        self._agent_registry = agent_registry
        self._agent_deployment = agent_deployment

        # Configuration settings - use YAML-configured threshold (default 0.5)
        self._min_confidence_default = 0.5
        self._max_rollback_attempts = 3
        self._deployment_timeout_seconds = 300  # 5 minutes
        self._config_file_name = "auto-config.yaml"

        self.logger.info("AutoConfigManagerService initialized")

    async def _initialize(self) -> None:
        """Initialize the service (required by BaseService)."""
        # Lazy initialization of dependencies if needed
        if self._toolchain_analyzer is None:
            try:
                from ..project.toolchain_analyzer import ToolchainAnalyzerService

                self._toolchain_analyzer = ToolchainAnalyzerService()
                self.logger.info("Initialized ToolchainAnalyzerService")
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize ToolchainAnalyzerService: {e}"
                )

        if self._agent_recommender is None:
            try:
                self._agent_recommender = AgentRecommenderService()
                self.logger.info("Initialized AgentRecommenderService")
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize AgentRecommenderService: {e}"
                )

    async def _cleanup(self) -> None:
        """Cleanup service resources (required by BaseService)."""
        # Clear any cached data

    async def auto_configure(
        self,
        project_path: Path,
        confirmation_required: bool = True,
        dry_run: bool = False,
        min_confidence: float = 0.5,
        observer: IDeploymentObserver | None = None,
    ) -> ConfigurationResult:
        """
        Perform automated agent configuration.

        Complete end-to-end configuration workflow:
        1. Analyze project toolchain
        2. Generate agent recommendations
        3. Validate proposed configuration
        4. Request user confirmation (if required)
        5. Deploy approved agents
        6. Verify deployment success

        Args:
            project_path: Path to the project root directory
            confirmation_required: Whether to require user approval before deployment
            dry_run: If True, preview only without deploying
            min_confidence: Minimum confidence score for recommendations (0.0-1.0)
            observer: Optional observer for progress tracking

        Returns:
            ConfigurationResult: Complete configuration results including
                deployed agents, validation results, and any errors

        Raises:
            FileNotFoundError: If project_path does not exist
            PermissionError: If unable to write to project directory
            ValueError: If min_confidence is invalid
        """
        # Validate inputs
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError(
                f"min_confidence must be between 0.0 and 1.0, got {min_confidence}"
            )

        # Use NullObserver if none provided
        if observer is None:
            observer = NullObserver()

        start_time = time.time()
        self.logger.info(
            f"Starting auto-configuration for project: {project_path} "
            f"(dry_run={dry_run}, min_confidence={min_confidence})"
        )

        try:
            # Step 1: Analyze toolchain
            analysis_start = time.time()
            observer.on_analysis_started(str(project_path))

            toolchain = await self._analyze_toolchain(project_path)
            analysis_duration = (time.time() - analysis_start) * 1000

            observer.on_analysis_completed(toolchain, analysis_duration)
            self.logger.info(
                f"Toolchain analysis complete: {toolchain.primary_language} "
                f"with {len(toolchain.frameworks)} frameworks"
            )

            # Step 2: Generate recommendations
            rec_start = time.time()
            observer.on_recommendation_started()

            recommendations = await self._generate_recommendations(
                toolchain, min_confidence
            )
            rec_duration = (time.time() - rec_start) * 1000

            observer.on_recommendation_completed(recommendations, rec_duration)
            self.logger.info(f"Generated {len(recommendations)} agent recommendations")

            if not recommendations:
                return ConfigurationResult(
                    status=OperationResult.SUCCESS,
                    message="No agents recommended for this project configuration",
                    recommendations=recommendations,
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "dry_run": dry_run,
                    },
                )

            # Step 3: Validate configuration
            observer.on_validation_started()

            validation_result = self.validate_configuration(recommendations)

            observer.on_validation_completed(
                validation_result.is_valid,
                validation_result.error_count,
                validation_result.warning_count,
            )

            if not validation_result.is_valid:
                self.logger.error(
                    f"Validation failed with {validation_result.error_count} errors"
                )
                return ConfigurationResult(
                    status=OperationResult.ERROR,
                    validation_errors=[
                        issue.message for issue in validation_result.errors
                    ],
                    validation_warnings=[
                        issue.message for issue in validation_result.warnings
                    ],
                    recommendations=recommendations,
                    message="Configuration validation failed",
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "dry_run": dry_run,
                    },
                )

            # Step 4: Handle dry-run
            if dry_run:
                self.logger.info("Dry-run mode: skipping deployment")
                return ConfigurationResult(
                    status=OperationResult.SUCCESS,
                    validation_warnings=[
                        issue.message for issue in validation_result.warnings
                    ],
                    recommendations=recommendations,
                    message=f"Dry-run complete: would deploy {len(recommendations)} agents",
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "dry_run": True,
                    },
                )

            # Step 5: User confirmation
            if confirmation_required:
                confirmed = await self._request_confirmation(
                    recommendations, validation_result
                )
                if not confirmed:
                    self.logger.info("User cancelled auto-configuration")
                    return ConfigurationResult(
                        status=OperationResult.CANCELLED,
                        recommendations=recommendations,
                        message="Auto-configuration cancelled by user",
                        metadata={
                            "duration_ms": (time.time() - start_time) * 1000,
                            "dry_run": dry_run,
                        },
                    )

            # Step 6: Deploy agents
            deploy_start = time.time()
            observer.on_deployment_started(len(recommendations))

            deployed_agents, failed_agents, snapshot = await self._deploy_agents(
                project_path, recommendations, observer
            )
            deploy_duration = (time.time() - deploy_start) * 1000

            observer.on_deployment_completed(
                len(deployed_agents), len(failed_agents), deploy_duration
            )

            # Step 7: Handle deployment failures
            if failed_agents:
                self.logger.warning(
                    f"Deployment completed with {len(failed_agents)} failures"
                )

                # Attempt rollback - restore snapshot AND remove any partial writes
                if deployed_agents or snapshot:
                    observer.on_rollback_started(deployed_agents)
                    rollback_success = await self._rollback_deployment(
                        project_path, deployed_agents, snapshot=snapshot
                    )
                    observer.on_rollback_completed(rollback_success)

                return ConfigurationResult(
                    status=(
                        OperationResult.WARNING
                        if deployed_agents
                        else OperationResult.FAILED
                    ),
                    deployed_agents=deployed_agents,
                    failed_agents=failed_agents,
                    validation_warnings=[
                        issue.message for issue in validation_result.warnings
                    ],
                    recommendations=recommendations,
                    message=f"Deployment completed with issues: {len(deployed_agents)} succeeded, {len(failed_agents)} failed",
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "dry_run": dry_run,
                        "rollback_attempted": len(deployed_agents) > 0
                        or bool(snapshot),
                    },
                )

            # Step 7b: Post-deployment validation - verify files exist and parse.
            # If validation fails we treat it like a deployment failure: roll
            # back (restoring snapshot) so we don't leave a half-baked config.
            post_validation = await self._validate_post_deployment(
                project_path, deployed_agents
            )
            if not post_validation.is_valid:
                self.logger.error(
                    f"Post-deployment validation failed with "
                    f"{post_validation.error_count} error(s); rolling back"
                )
                observer.on_rollback_started(deployed_agents)
                rollback_success = await self._rollback_deployment(
                    project_path, deployed_agents, snapshot=snapshot
                )
                observer.on_rollback_completed(rollback_success)

                return ConfigurationResult(
                    status=OperationResult.FAILED,
                    deployed_agents=[],
                    failed_agents=deployed_agents,
                    validation_errors=[i.message for i in post_validation.errors],
                    validation_warnings=[
                        issue.message for issue in validation_result.warnings
                    ],
                    recommendations=recommendations,
                    message=(
                        "Deployment rolled back: post-deployment validation "
                        f"found {post_validation.error_count} error(s)"
                    ),
                    metadata={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "dry_run": dry_run,
                        "rollback_attempted": True,
                        "rollback_succeeded": rollback_success,
                        "phase": "post_deployment_validation",
                    },
                )

            # Step 8: Save configuration. Deployment succeeded; the snapshot
            # backups are no longer needed.
            self._cleanup_snapshot(snapshot)
            await self._save_configuration(project_path, toolchain, recommendations)

            # Success!
            total_duration = (time.time() - start_time) * 1000
            self.logger.info(
                f"Auto-configuration completed successfully in {total_duration:.0f}ms: "
                f"deployed {len(deployed_agents)} agents"
            )

            return ConfigurationResult(
                status=OperationResult.SUCCESS,
                deployed_agents=deployed_agents,
                validation_warnings=[
                    issue.message for issue in validation_result.warnings
                ],
                recommendations=recommendations,
                message=f"Successfully configured {len(deployed_agents)} agents",
                metadata={
                    "duration_ms": total_duration,
                    "dry_run": dry_run,
                },
            )

        except Exception as e:
            self.logger.error(f"Auto-configuration failed: {e}", exc_info=True)
            observer.on_error("auto-configuration", str(e), e)

            return ConfigurationResult(
                status=OperationResult.FAILED,
                message=f"Auto-configuration failed: {e}",
                metadata={
                    "duration_ms": (time.time() - start_time) * 1000,
                    "dry_run": dry_run,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

    def validate_configuration(
        self, recommendations: list[AgentRecommendation]
    ) -> ValidationResult:
        """
        Validate proposed configuration before deployment.

        Performs comprehensive validation:
        - Checks for agent existence
        - Verifies no conflicts (multiple agents for same role)
        - Validates minimum confidence threshold
        - Checks deployment prerequisites
        - Warns about unmatched toolchains

        Args:
            recommendations: List of agent recommendations to validate

        Returns:
            ValidationResult: Validation result with any warnings or errors

        Raises:
            ValueError: If recommendations list is empty or invalid
        """
        if not recommendations:
            raise ValueError("Cannot validate empty recommendations list")

        issues: list[ValidationIssue] = []
        validated_agents: list[str] = []

        # Track agent roles to detect conflicts
        role_agents: dict[str, list[str]] = {}

        for recommendation in recommendations:
            agent_id = recommendation.agent_id
            validated_agents.append(agent_id)

            # Check 1: Agent existence
            if self._agent_registry:
                try:
                    # Try to get agent metadata to verify it exists
                    agent = self._agent_registry.get_agent(agent_id)
                    if agent is None:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                message=f"Agent '{agent_id}' does not exist",
                                agent_id=agent_id,
                                suggested_fix="Remove this recommendation or ensure agent is installed",
                            )
                        )
                        continue
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Could not verify agent '{agent_id}': {e}",
                            agent_id=agent_id,
                        )
                    )

            # Check 2: Confidence threshold
            if recommendation.confidence_score < 0.5:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Low confidence score ({recommendation.confidence_score:.2f}) for agent '{agent_id}'",
                        agent_id=agent_id,
                        suggested_fix="Consider reviewing agent capabilities or adjusting threshold",
                    )
                )
            elif recommendation.confidence_score < 0.7:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        message=f"Moderate confidence score ({recommendation.confidence_score:.2f}) for agent '{agent_id}'",
                        agent_id=agent_id,
                    )
                )

            # Check 3: Track roles for conflict detection
            if recommendation.capabilities:
                for spec in recommendation.capabilities.specializations:
                    role = spec.value
                    if role not in role_agents:
                        role_agents[role] = []
                    role_agents[role].append(agent_id)

            # Check 4: Recommendation concerns
            if recommendation.has_concerns:
                for concern in recommendation.concerns:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            message=f"Concern for '{agent_id}': {concern}",
                            agent_id=agent_id,
                        )
                    )

        # Check 5: Role conflicts (multiple agents for same role)
        for role, agents in role_agents.items():
            if len(agents) > 1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Multiple agents ({', '.join(agents)}) recommended for role '{role}'",
                        suggested_fix="Consider selecting the highest confidence agent for this role",
                    )
                )

        # Determine if validation passes (no errors)
        is_valid = not any(
            issue.severity == ValidationSeverity.ERROR for issue in issues
        )

        self.logger.info(
            f"Validation complete: {len(validated_agents)} agents, "
            f"{len([i for i in issues if i.severity == ValidationSeverity.ERROR])} errors, "
            f"{len([i for i in issues if i.severity == ValidationSeverity.WARNING])} warnings"
        )

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            validated_agents=validated_agents,
            metadata={"validation_timestamp": datetime.now(UTC).isoformat()},
        )

    def preview_configuration(
        self, project_path: Path, min_confidence: float = 0.5
    ) -> ConfigurationPreview:
        """
        Preview what would be configured without applying changes.

        Performs analysis and recommendation without making any changes:
        - Analyzes project toolchain
        - Generates recommendations
        - Validates configuration
        - Returns preview of what would be deployed

        Args:
            project_path: Path to the project root directory
            min_confidence: Minimum confidence score for recommendations

        Returns:
            ConfigurationPreview: Preview of configuration that would be applied

        Raises:
            FileNotFoundError: If project_path does not exist
        """
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        self.logger.info(f"Generating configuration preview for: {project_path}")

        try:
            # Call underlying synchronous services directly.
            # The async wrappers (_analyze_toolchain, _generate_recommendations)
            # just delegate to these synchronous methods, so we bypass them
            # to avoid needing an event loop. This method may be called from
            # a worker thread (via asyncio.to_thread) where no event loop
            # is available.

            # Analyze toolchain
            if self._toolchain_analyzer is None:
                raise RuntimeError("ToolchainAnalyzer not initialized")
            toolchain = self._toolchain_analyzer.analyze_toolchain(project_path)

            # Generate recommendations
            if self._agent_recommender is None:
                raise RuntimeError("AgentRecommender not initialized")
            constraints = {"min_confidence": min_confidence}
            recommendations = self._agent_recommender.recommend_agents(
                toolchain, constraints
            )

            # Validate configuration
            validation_result = self.validate_configuration(recommendations)

            # Estimate deployment time (5 seconds per agent)
            estimated_time = len(recommendations) * 5.0

            # Determine what would be deployed
            would_deploy = [
                rec.agent_id
                for rec in recommendations
                if rec.confidence_score >= min_confidence
            ]
            would_skip = [
                rec.agent_id
                for rec in recommendations
                if rec.confidence_score < min_confidence
            ]

            preview = ConfigurationPreview(
                recommendations=recommendations,
                validation_result=validation_result,
                detected_toolchain=toolchain,
                estimated_deployment_time=estimated_time,
                would_deploy=would_deploy,
                would_skip=would_skip,
                requires_confirmation=True,
                metadata={
                    "preview_timestamp": datetime.now(UTC).isoformat(),
                    "toolchain_summary": {
                        "primary_language": toolchain.primary_language,
                        "frameworks": [fw.name for fw in toolchain.frameworks],
                        "deployment_target": (
                            toolchain.deployment_target.platform
                            if toolchain.deployment_target
                            else None
                        ),
                    },
                },
            )

            self.logger.info(
                f"Preview generated: {preview.deployment_count} agents would be deployed"
            )
            return preview

        except Exception as e:
            self.logger.error(f"Failed to generate preview: {e}", exc_info=True)
            raise

    # Private helper methods

    async def _analyze_toolchain(self, project_path: Path) -> ToolchainAnalysis:
        """Analyze project toolchain."""
        if self._toolchain_analyzer is None:
            raise RuntimeError("ToolchainAnalyzer not initialized")

        return self._toolchain_analyzer.analyze_toolchain(project_path)

    async def _generate_recommendations(
        self, toolchain: ToolchainAnalysis, min_confidence: float
    ) -> list[AgentRecommendation]:
        """Generate agent recommendations."""
        if self._agent_recommender is None:
            raise RuntimeError("AgentRecommender not initialized")

        constraints = {"min_confidence": min_confidence}
        return self._agent_recommender.recommend_agents(toolchain, constraints)

    async def _request_confirmation(
        self, recommendations: list[AgentRecommendation], validation: ValidationResult
    ) -> bool:
        """
        Request user confirmation before deployment.

        Presents the recommended agents and validation summary to the user
        and prompts for confirmation via stdin. Callers that want to bypass
        the prompt (CI, API handlers, ``--yes``-style flags) should pass
        ``confirmation_required=False`` to :meth:`auto_configure` so this
        method is never invoked.

        If stdin is not a TTY (non-interactive context like CI or a piped
        invocation) we fall back to auto-approving when validation passed
        and rejecting otherwise. This preserves the previous test-friendly
        behavior while making interactive sessions actually interactive.

        Args:
            recommendations: List of recommended agents
            validation: Validation results

        Returns:
            bool: True if user confirms, False otherwise
        """
        import sys

        # Build a concise summary of what we're about to do.
        lines = [
            "",
            "Auto-configuration proposes deploying the following agents:",
        ]
        for rec in recommendations:
            lines.append(
                f"  - {rec.agent_id} ({rec.agent_name}) "
                f"[confidence={rec.confidence_score:.2f}]"
            )

        if validation.warning_count:
            lines.append(
                f"Validation warnings: {validation.warning_count} "
                f"(errors: {validation.error_count})"
            )

        summary = "\n".join(lines)

        # Non-interactive fallback: keep prior behavior to avoid breaking
        # automated callers that forgot to pass confirmation_required=False.
        if not sys.stdin.isatty():
            self.logger.info(
                "Non-interactive stdin detected; auto-%s based on validation.",
                "approving" if validation.is_valid else "rejecting",
            )
            self.logger.info(summary)
            return validation.is_valid

        # Interactive prompt. Default to "no" to be safe.
        try:
            print(summary)
            response = input("Proceed with deployment? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.logger.info("User aborted confirmation prompt")
            return False

        confirmed = response in ("y", "yes")
        if not confirmed:
            self.logger.info("User declined auto-configuration deployment")
        return confirmed

    async def _deploy_agents(
        self,
        project_path: Path,
        recommendations: list[AgentRecommendation],
        observer: IDeploymentObserver,
    ) -> tuple[list[str], list[str], dict[str, Path]]:
        """
        Deploy recommended agents.

        Before any agent is written we snapshot any pre-existing agent files
        that share the same id, so a partial-failure rollback can restore
        the previous state instead of just deleting freshly written files.

        Args:
            project_path: Project root directory
            recommendations: List of recommendations to deploy
            observer: Observer for progress tracking

        Returns:
            Tuple of (deployed_agent_ids, failed_agent_ids, snapshot)
            where ``snapshot`` is a mapping of original file path -> backup
            path that callers can pass to :meth:`_restore_from_snapshot`
            (rollback) or :meth:`_cleanup_snapshot` (success).
        """
        deployed: list[str] = []
        failed: list[str] = []

        # Sort recommendations by deployment priority
        sorted_recs = sorted(recommendations, key=lambda r: r.deployment_priority)

        # Snapshot pre-existing files for the agents we are about to write.
        # This is best-effort: failures to snapshot are logged, not raised.
        snapshot = self._snapshot_existing_files(
            project_path, [r.agent_id for r in sorted_recs]
        )

        for index, recommendation in enumerate(sorted_recs, 1):
            agent_id = recommendation.agent_id
            agent_name = recommendation.agent_name

            try:
                observer.on_agent_deployment_started(
                    agent_id, agent_name, index, len(sorted_recs)
                )

                await self._deploy_single_agent(agent_id, project_path)

                observer.on_agent_deployment_completed(
                    agent_id, agent_name, success=True
                )
                deployed.append(agent_id)
                self.logger.debug(f"Successfully deployed agent: {agent_id}")

            except Exception as e:
                self.logger.error(
                    f"Failed to deploy agent '{agent_id}': {e}", exc_info=True
                )
                observer.on_agent_deployment_completed(
                    agent_id, agent_name, success=False, error=str(e)
                )
                failed.append(agent_id)

        return deployed, failed, snapshot

    def _get_deployment_service(self) -> Any:
        """
        Lazily resolve the agent deployment service.

        Uses the injected ``self._agent_deployment`` if provided (preferred,
        enables mocking in tests) and otherwise instantiates the project
        ``AgentDeploymentService``. The result is cached on the instance so
        repeated calls during a single auto-configure run share state.

        Returns:
            An object exposing ``deploy_agent(agent_name, target_dir, force_rebuild=False)``.
        """
        if self._agent_deployment is not None:
            return self._agent_deployment

        from .deployment.agent_deployment import AgentDeploymentService

        self._agent_deployment = AgentDeploymentService()
        self.logger.info("Initialized AgentDeploymentService (lazy)")
        return self._agent_deployment

    @staticmethod
    def _resolve_agents_dir(project_path: Path) -> Path:
        """Resolve the project's ``.claude/agents`` directory.

        Centralized so both deploy and rollback target the same location.
        """
        return project_path / ".claude" / "agents"

    @staticmethod
    def _agent_file_candidates(agents_dir: Path, agent_id: str) -> list[Path]:
        """Return all on-disk filename variants we know about for an agent.

        The deployment service may emit either ``.md`` or legacy ``.yaml``
        files. We consider both so snapshot/rollback covers either layout.
        """
        return [agents_dir / f"{agent_id}.md", agents_dir / f"{agent_id}.yaml"]

    def _snapshot_existing_files(
        self, project_path: Path, agent_ids: list[str]
    ) -> dict[str, Path]:
        """Snapshot any pre-existing agent files before deployment overwrites them.

        For each agent we are about to deploy, copy any existing ``.md``/``.yaml``
        file to a sibling ``.bak`` path. This lets ``_rollback_deployment``
        restore the previous state rather than just removing the freshly
        written file (which would silently delete user customizations).

        Args:
            project_path: Project root directory
            agent_ids: Agent identifiers about to be deployed

        Returns:
            Mapping of original file path (str) -> backup file path (Path)
            for files that actually existed and were snapshotted.
        """
        agents_dir = self._resolve_agents_dir(project_path)
        snapshot: dict[str, Path] = {}

        if not agents_dir.exists():
            return snapshot

        for agent_id in agent_ids:
            for original in self._agent_file_candidates(agents_dir, agent_id):
                if not original.exists():
                    continue
                backup = original.with_suffix(original.suffix + ".bak")
                try:
                    shutil.copy2(original, backup)
                    snapshot[str(original)] = backup
                    self.logger.debug(
                        f"Snapshotted existing agent file: {original} -> {backup}"
                    )
                except OSError as e:
                    # We log and continue. A best-effort snapshot is still
                    # better than none; deployment will proceed and rollback
                    # will only restore what we successfully captured.
                    self.logger.warning(
                        f"Failed to snapshot existing agent file {original}: {e}"
                    )

        if snapshot:
            self.logger.info(
                f"Snapshotted {len(snapshot)} existing agent file(s) before deployment"
            )
        return snapshot

    def _cleanup_snapshot(self, snapshot: dict[str, Path]) -> None:
        """Remove backup files created by ``_snapshot_existing_files``.

        Called on successful deployment so we don't leave ``.bak`` files
        cluttering the project. Failures are logged but never raised.
        """
        for backup in snapshot.values():
            try:
                if backup.exists():
                    backup.unlink()
            except OSError as e:
                self.logger.warning(f"Failed to remove backup file {backup}: {e}")

    def _restore_from_snapshot(self, snapshot: dict[str, Path]) -> bool:
        """Restore files from a snapshot taken before deployment.

        Args:
            snapshot: Mapping of original path (str) -> backup path (Path)

        Returns:
            True if all entries were restored (or snapshot empty),
            False if at least one restore failed.
        """
        if not snapshot:
            return True

        all_succeeded = True
        for original_str, backup in snapshot.items():
            original = Path(original_str)
            try:
                if backup.exists():
                    shutil.move(str(backup), str(original))
                    self.logger.info(f"Restored from snapshot: {original}")
            except OSError as e:
                all_succeeded = False
                self.logger.error(
                    f"Failed to restore {original} from snapshot {backup}: {e}"
                )
        return all_succeeded

    async def _validate_post_deployment(
        self, project_path: Path, deployed_agents: list[str]
    ) -> ValidationResult:
        """Verify deployed agent files exist and are parseable.

        Performs lightweight on-disk verification AFTER deployment to catch
        cases where the deployment service reported success but produced
        an empty or malformed file. This is the safety net mentioned in
        :meth:`auto_configure` step 6 ("Verify deployment success").

        Checks performed for each deployed agent:
        - At least one of the expected files exists (``.md`` or ``.yaml``)
        - The file is non-empty
        - For ``.md`` files: contains some content (basic sanity check)
        - For ``.yaml`` files: parses as valid YAML

        Args:
            project_path: Project root directory
            deployed_agents: List of agent IDs that were just deployed

        Returns:
            ValidationResult with one issue per problem found. The result
            is_valid is True iff every deployed agent has a parseable file.
        """
        issues: list[ValidationIssue] = []
        validated: list[str] = []
        agents_dir = self._resolve_agents_dir(project_path)

        for agent_id in deployed_agents:
            candidates = self._agent_file_candidates(agents_dir, agent_id)
            existing = [p for p in candidates if p.exists()]

            if not existing:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Post-deployment check: no agent file found for "
                            f"'{agent_id}' in {agents_dir}"
                        ),
                        agent_id=agent_id,
                    )
                )
                continue

            target = existing[0]
            try:
                content = target.read_text(encoding="utf-8")
            except OSError as e:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Post-deployment check: cannot read deployed file "
                            f"{target}: {e}"
                        ),
                        agent_id=agent_id,
                    )
                )
                continue

            if not content.strip():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Post-deployment check: deployed file {target} is empty"
                        ),
                        agent_id=agent_id,
                    )
                )
                continue

            # YAML-specific structural check. Markdown files with YAML
            # frontmatter are NOT validated as pure YAML here because the
            # body after the frontmatter is markdown, not YAML.
            if target.suffix == ".yaml":
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError as e:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Post-deployment check: {target} is not "
                                f"valid YAML: {e}"
                            ),
                            agent_id=agent_id,
                        )
                    )
                    continue

            validated.append(agent_id)

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            validated_agents=validated,
            metadata={
                "validation_timestamp": datetime.now(UTC).isoformat(),
                "phase": "post_deployment",
            },
        )
        self.logger.info(
            f"Post-deployment validation: {len(validated)}/{len(deployed_agents)} "
            f"agents verified, {len(issues)} issue(s)"
        )
        return result

    async def _deploy_single_agent(self, agent_id: str, project_path: Path) -> None:
        """
        Deploy a single agent to the project's ``.claude/agents`` directory.

        Delegates to ``AgentDeploymentService.deploy_agent`` which is the
        same code path used by the auto-config HTTP handler. The deployment
        call is synchronous/blocking I/O, so we run it in a worker thread
        via ``asyncio.to_thread`` to avoid stalling the event loop.

        Args:
            agent_id: Agent identifier (matches the template stem)
            project_path: Project root directory

        Raises:
            RuntimeError: If the deployment service reports failure.
            Exception: Propagates underlying deployment errors so the caller
                can record them in ``failed_agents`` and trigger rollback.
        """
        import asyncio

        service = self._get_deployment_service()
        agents_dir = self._resolve_agents_dir(project_path)
        agents_dir.mkdir(parents=True, exist_ok=True)

        def _do_deploy() -> bool:
            return bool(service.deploy_agent(agent_id, agents_dir, force_rebuild=False))

        success = await asyncio.to_thread(_do_deploy)
        if not success:
            # AgentDeploymentService returns False (rather than raising) for
            # certain non-exceptional failures; surface that as an error so
            # the caller treats this agent as failed.
            raise RuntimeError(
                f"AgentDeploymentService reported failure for agent '{agent_id}'"
            )

        self.logger.debug(f"Deployed agent {agent_id} to {agents_dir}")

    async def _rollback_deployment(
        self,
        project_path: Path,
        deployed_agents: list[str],
        snapshot: dict[str, Path] | None = None,
    ) -> bool:
        """
        Rollback deployed agents after a partial-failure deployment.

        Strategy:
        1. Delete files this run just wrote (agents in ``deployed_agents``).
        2. If ``snapshot`` was captured before deployment, restore those
           pre-existing files to their original location. This preserves
           user customizations that would otherwise be silently overwritten.
        3. If a ``BackupManager`` style full backup also exists upstream
           (e.g. in the auto-config HTTP handler), it can run alongside this
           method - they target different scopes.

        Missing files are treated as "already rolled back" and do not count
        as failures.

        Args:
            project_path: Project root directory
            deployed_agents: List of agent IDs to rollback
            snapshot: Optional mapping returned by ``_snapshot_existing_files``
                of pre-deployment files to restore.

        Returns:
            bool: True if all rollback steps succeeded (or nothing to do),
                False if at least one file could not be removed/restored.
        """
        if not deployed_agents and not snapshot:
            self.logger.info(
                "Rollback requested with no deployed agents and no snapshot; "
                "nothing to do"
            )
            return True

        self.logger.warning(
            f"Rolling back {len(deployed_agents)} deployed agents from {project_path}"
        )

        agents_dir = self._resolve_agents_dir(project_path)

        all_succeeded = True

        if agents_dir.exists():
            for agent_id in deployed_agents:
                removed_any = False
                for suffix in (".md", ".yaml"):
                    target = agents_dir / f"{agent_id}{suffix}"
                    if not target.exists():
                        continue
                    try:
                        target.unlink()
                        removed_any = True
                        self.logger.info(f"Rolled back agent file: {target}")
                    except OSError as e:
                        all_succeeded = False
                        self.logger.error(
                            f"Failed to remove agent file during rollback: "
                            f"{target}: {e}"
                        )

                if not removed_any:
                    # Not necessarily a failure - the file may never have been
                    # written if deployment failed before write. Log and continue.
                    self.logger.info(
                        f"No deployed file found for agent '{agent_id}'; "
                        "assuming rollback unnecessary"
                    )
        else:
            # Nothing to delete if the directory is gone already.
            self.logger.info(
                f"Agents directory does not exist, skipping deletion phase: "
                f"{agents_dir}"
            )

        # Restore any pre-existing files we snapshotted before deployment.
        # This must happen AFTER deletion so we don't immediately delete
        # what we just restored.
        if snapshot:
            restore_ok = self._restore_from_snapshot(snapshot)
            if not restore_ok:
                all_succeeded = False
                self.logger.error("Snapshot restore reported one or more failures")

        return all_succeeded

    async def _save_configuration(
        self,
        project_path: Path,
        toolchain: ToolchainAnalysis,
        recommendations: list[AgentRecommendation],
    ) -> None:
        """
        Save auto-configuration metadata to project.

        Args:
            project_path: Project root directory
            toolchain: Toolchain analysis results
            recommendations: Agent recommendations that were deployed
        """
        config_dir = project_path / ".claude-mpm"
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / self._config_file_name

        config_data = {
            "auto_config": {
                "enabled": True,
                "last_run": datetime.now(UTC).isoformat(),
                "toolchain_snapshot": {
                    "primary_language": toolchain.primary_language,
                    "frameworks": [fw.name for fw in toolchain.frameworks],
                    "deployment_targets": (
                        [toolchain.deployment_target.platform]
                        if toolchain.deployment_target
                        else []
                    ),
                },
                "deployed_agents": [
                    {
                        "agent_id": rec.agent_id,
                        "agent_name": rec.agent_name,
                        "confidence": rec.confidence_score,
                        "deployed_at": datetime.now(UTC).isoformat(),
                    }
                    for rec in recommendations
                ],
                "user_overrides": {"disabled_agents": [], "custom_agents": []},
            }
        }

        try:
            with config_file.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            self.logger.info(f"Saved auto-configuration to: {config_file}")

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}", exc_info=True)
            # Don't raise - configuration save is non-critical
