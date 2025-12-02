"""
Observer Pattern for Auto-Configuration Progress Tracking
=========================================================

WHY: Auto-configuration involves multiple steps (analysis, recommendation,
deployment) that can take significant time. Observers enable real-time
progress tracking and user feedback.

DESIGN DECISION: Observer pattern allows decoupling of progress notification
from core business logic. Multiple observers can be attached for different
output targets (console, file, network).

Part of TSK-0054: Auto-Configuration Feature - Phase 4
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..core.models.agent_config import AgentRecommendation
from ..core.models.toolchain import ToolchainAnalysis


class IDeploymentObserver(ABC):
    """
    Observer interface for deployment events.

    WHY: Standardizes the observer interface to enable multiple observer
    implementations (console, GUI, logging, metrics) that all receive
    the same event notifications.

    DESIGN DECISION: Separate methods for each event type enable fine-grained
    control over which events observers handle. All methods are optional
    (have default implementations) to simplify observer creation.
    """

    @abstractmethod
    def on_analysis_started(self, project_path: str) -> None:
        """
        Called when toolchain analysis starts.

        Args:
            project_path: Path to the project being analyzed
        """

    @abstractmethod
    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """
        Called when toolchain analysis completes.

        Args:
            toolchain: Complete toolchain analysis result
            duration_ms: Analysis duration in milliseconds
        """

    @abstractmethod
    def on_recommendation_started(self) -> None:
        """Called when agent recommendation starts."""

    @abstractmethod
    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """
        Called when agent recommendation completes.

        Args:
            recommendations: List of agent recommendations
            duration_ms: Recommendation duration in milliseconds
        """

    @abstractmethod
    def on_validation_started(self) -> None:
        """Called when configuration validation starts."""

    @abstractmethod
    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """
        Called when configuration validation completes.

        Args:
            is_valid: Whether validation passed
            error_count: Number of validation errors
            warning_count: Number of validation warnings
        """

    @abstractmethod
    def on_deployment_started(self, total_agents: int) -> None:
        """
        Called when deployment of agents starts.

        Args:
            total_agents: Total number of agents to deploy
        """

    @abstractmethod
    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """
        Called when deployment of a specific agent starts.

        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
            index: Current agent index (1-based)
            total: Total number of agents being deployed
        """

    @abstractmethod
    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """
        Called to report progress of agent deployment.

        Args:
            agent_id: Agent identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
        """

    @abstractmethod
    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """
        Called when deployment of a specific agent completes.

        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
            success: Whether deployment succeeded
            error: Error message if deployment failed
        """

    @abstractmethod
    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """
        Called when all agent deployments complete.

        Args:
            success_count: Number of successfully deployed agents
            failure_count: Number of failed deployments
            duration_ms: Total deployment duration in milliseconds
        """

    @abstractmethod
    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """
        Called when rollback of failed deployments starts.

        Args:
            agent_ids: List of agent IDs to roll back
        """

    @abstractmethod
    def on_rollback_completed(self, success: bool) -> None:
        """
        Called when rollback completes.

        Args:
            success: Whether rollback succeeded
        """

    @abstractmethod
    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """
        Called when an error occurs during auto-configuration.

        Args:
            phase: Phase where error occurred (analysis, recommendation, deployment)
            error_message: Human-readable error message
            exception: Optional exception object
        """


class NullObserver(IDeploymentObserver):
    """
    Null Object pattern implementation of observer.

    WHY: Provides a no-op observer to simplify code when no observer is needed.
    Eliminates need for null checks before calling observer methods.

    DESIGN DECISION: All methods do nothing, making this a safe default observer.
    """

    def on_analysis_started(self, project_path: str) -> None:
        pass

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        pass

    def on_recommendation_started(self) -> None:
        pass

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        pass

    def on_validation_started(self) -> None:
        pass

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        pass

    def on_deployment_started(self, total_agents: int) -> None:
        pass

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        pass

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        pass

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        pass

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        pass

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        pass

    def on_rollback_completed(self, success: bool) -> None:
        pass

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        pass


class ConsoleProgressObserver(IDeploymentObserver):
    """
    Console-based progress observer with rich terminal output.

    WHY: Provides user-friendly progress feedback during auto-configuration.
    Uses rich library for enhanced terminal output with colors and progress bars.

    DESIGN DECISION: Conditionally imports rich library to avoid hard dependency.
    Falls back to simple print statements if rich is not available.
    """

    def __init__(self, use_rich: bool = True):
        """
        Initialize console observer.

        Args:
            use_rich: Whether to use rich library for enhanced output
        """
        self.use_rich = use_rich
        self._rich_available = False
        self._console = None
        self._progress = None
        self._task_id = None

        if self.use_rich:
            try:
                from rich.console import Console
                from rich.progress import (
                    BarColumn,
                    Progress,
                    SpinnerColumn,
                    TextColumn,
                    TimeRemainingColumn,
                )

                self._Console = Console
                self._Progress = Progress
                self._SpinnerColumn = SpinnerColumn
                self._TextColumn = TextColumn
                self._BarColumn = BarColumn
                self._TimeRemainingColumn = TimeRemainingColumn
                self._rich_available = True
                self._console = Console()
            except ImportError:
                self._rich_available = False

    def _print(self, message: str, style: str = "") -> None:
        """
        Print message with optional styling.

        Args:
            message: Message to print
            style: Rich style string (e.g., "bold green", "red")
        """
        if self._rich_available and self._console:
            self._console.print(message, style=style)
        else:
            print(message)

    def on_analysis_started(self, project_path: str) -> None:
        """Called when toolchain analysis starts."""
        self._print(f"\n🔍 Analyzing project toolchain: {project_path}", "bold cyan")

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """Called when toolchain analysis completes."""
        self._print(
            f"✓ Analysis complete ({duration_ms:.0f}ms): "
            f"{toolchain.primary_language} with {len(toolchain.frameworks)} frameworks",
            "bold green",
        )

    def on_recommendation_started(self) -> None:
        """Called when agent recommendation starts."""
        self._print("\n🤖 Generating agent recommendations...", "bold cyan")

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """Called when agent recommendation completes."""
        high_conf = sum(1 for r in recommendations if r.is_high_confidence)
        self._print(
            f"✓ Generated {len(recommendations)} recommendations ({duration_ms:.0f}ms): "
            f"{high_conf} high confidence",
            "bold green",
        )

    def on_validation_started(self) -> None:
        """Called when configuration validation starts."""
        self._print("\n✓ Validating configuration...", "bold cyan")

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """Called when configuration validation completes."""
        if is_valid:
            self._print(
                f"✓ Validation passed ({warning_count} warnings)",
                "bold green",
            )
        else:
            self._print(
                f"✗ Validation failed: {error_count} errors, {warning_count} warnings",
                "bold red",
            )

    def on_deployment_started(self, total_agents: int) -> None:
        """Called when deployment of agents starts."""
        self._print(f"\n🚀 Deploying {total_agents} agents...", "bold cyan")

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """Called when deployment of a specific agent starts."""
        self._print(f"  [{index}/{total}] Deploying {agent_name}...", "cyan")

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """Called to report progress of agent deployment."""
        # Progress updates are too noisy for console, skip them

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Called when deployment of a specific agent completes."""
        if success:
            self._print(f"    ✓ {agent_name} deployed successfully", "green")
        else:
            error_msg = f": {error}" if error else ""
            self._print(f"    ✗ {agent_name} deployment failed{error_msg}", "red")

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """Called when all agent deployments complete."""
        if failure_count == 0:
            self._print(
                f"\n✓ All {success_count} agents deployed successfully ({duration_ms / 1000:.1f}s)",
                "bold green",
            )
        else:
            self._print(
                f"\n⚠ Deployment completed with issues: "
                f"{success_count} succeeded, {failure_count} failed ({duration_ms / 1000:.1f}s)",
                "bold yellow",
            )

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """Called when rollback of failed deployments starts."""
        self._print(f"\n⏪ Rolling back {len(agent_ids)} agents...", "bold yellow")

    def on_rollback_completed(self, success: bool) -> None:
        """Called when rollback completes."""
        if success:
            self._print("✓ Rollback completed successfully", "green")
        else:
            self._print("✗ Rollback failed", "red")

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """Called when an error occurs during auto-configuration."""
        self._print(f"\n✗ Error in {phase}: {error_message}", "bold red")
        if exception:
            self._print(f"  Exception: {type(exception).__name__}: {exception}", "red")


class CompositeObserver(IDeploymentObserver):
    """
    Composite observer that broadcasts events to multiple observers.

    WHY: Enables simultaneous notification of multiple observers (e.g., console
    output + file logging + metrics collection) without coupling.

    DESIGN DECISION: Implements observer pattern by delegating all events to
    registered observers. Catches and logs exceptions from individual observers
    to prevent one failing observer from breaking others.
    """

    def __init__(self, observers: Optional[List[IDeploymentObserver]] = None):
        """
        Initialize composite observer.

        Args:
            observers: List of observers to notify
        """
        self._observers: List[IDeploymentObserver] = observers or []

    def add_observer(self, observer: IDeploymentObserver) -> None:
        """
        Add an observer to the composite.

        Args:
            observer: Observer to add
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: IDeploymentObserver) -> None:
        """
        Remove an observer from the composite.

        Args:
            observer: Observer to remove
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_all(self, method_name: str, *args, **kwargs) -> None:
        """
        Notify all observers by calling method on each.

        Args:
            method_name: Name of the observer method to call
            *args: Positional arguments to pass
            **kwargs: Keyword arguments to pass
        """
        for observer in self._observers:
            try:
                method = getattr(observer, method_name)
                method(*args, **kwargs)
            except Exception as e:
                # Log but don't re-raise to prevent one observer from breaking others
                print(
                    f"Error in observer {observer.__class__.__name__}.{method_name}: {e}"
                )

    def on_analysis_started(self, project_path: str) -> None:
        self._notify_all("on_analysis_started", project_path)

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        self._notify_all("on_analysis_completed", toolchain, duration_ms)

    def on_recommendation_started(self) -> None:
        self._notify_all("on_recommendation_started")

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        self._notify_all("on_recommendation_completed", recommendations, duration_ms)

    def on_validation_started(self) -> None:
        self._notify_all("on_validation_started")

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        self._notify_all(
            "on_validation_completed", is_valid, error_count, warning_count
        )

    def on_deployment_started(self, total_agents: int) -> None:
        self._notify_all("on_deployment_started", total_agents)

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        self._notify_all(
            "on_agent_deployment_started", agent_id, agent_name, index, total
        )

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        self._notify_all("on_agent_deployment_progress", agent_id, progress, message)

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        self._notify_all(
            "on_agent_deployment_completed", agent_id, agent_name, success, error
        )

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        self._notify_all(
            "on_deployment_completed", success_count, failure_count, duration_ms
        )

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        self._notify_all("on_rollback_started", agent_ids)

    def on_rollback_completed(self, success: bool) -> None:
        self._notify_all("on_rollback_completed", success)

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        self._notify_all("on_error", phase, error_message, exception)
